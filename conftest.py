"""
conftest.py – Project-wide pytest fixtures and shared library build automation.

Ensures all host-native .so shared libraries are rebuilt whenever the
corresponding C source files are newer than the compiled artifact, so that
test runs always exercise the current firmware source code.

TCP HIL fixtures (requiring a live ESP32 on the network) are defined here as
session-scoped so they can be shared across test_modbus_kernel.py and
test_state_machine.py without duplicate connections.
"""

import os
import subprocess
import sys
import contextlib
import signal
import pytest

# ─── Root paths ──────────────────────────────────────────────────────────────

ROOT = os.path.dirname(__file__)
TESTS_DIR = os.path.join(ROOT, "tests")
SRC_DIR = os.path.join(ROOT, "main", "src")
INC_DIR = os.path.join(ROOT, "main", "include")


# ─── Shared library auto-rebuild ─────────────────────────────────────────────

def _is_stale(so_path: str, src_files: list[str]) -> bool:
    """Return True when .so does not exist or any source is newer than .so."""
    if not os.path.exists(so_path):
        return True
    so_mtime = os.path.getmtime(so_path)
    return any(os.path.getmtime(f) > so_mtime for f in src_files if os.path.exists(f))


def _build_so(so_path: str, src_files: list[str], extra_flags: list[str] | None = None):
    cmd = ["gcc", "-shared", "-fPIC", "-O2", "-DHOST_TEST"] + src_files
    if extra_flags:
        cmd += extra_flags
    cmd += ["-o", so_path, f"-I{INC_DIR}", f"-I{SRC_DIR}", "-lm"]
    subprocess.run(cmd, check=True)


def _maybe_rebuild(name: str, srcs: list[str], flags: list[str] | None = None):
    so_path = os.path.join(TESTS_DIR, f"{name}.so")
    full_srcs = [os.path.join(SRC_DIR, s) for s in srcs]
    headers = [os.path.join(INC_DIR, f) for f in os.listdir(INC_DIR) if f.endswith(".h")]
    if _is_stale(so_path, full_srcs + headers):
        print(f"\n[conftest] Rebuilding {name}.so …")
        _build_so(so_path, full_srcs, flags)


def pytest_configure(config):
    """Auto-rebuild stale shared libraries before any test is collected."""
    _maybe_rebuild("libencoder_pcnt",     ["encoder_pcnt.c"])
    _maybe_rebuild("libihm_display",      ["ihm_display.c"])
    _maybe_rebuild("libkinematics",       ["linear_kinematics.c"])
    _maybe_rebuild("libmotor_mcpwm",      ["motor_mcpwm.c"])
    _maybe_rebuild("libpid_controller",   ["pid_controller.c"])
    _maybe_rebuild(
        "libsystem_integration",
        [
            "shared_data.c", "gpio_safety.c", "linear_kinematics.c",
            "encoder_pcnt.c", "motor_mcpwm.c", "pid_controller.c",
            "ihm_display.c", "modbus_slave.c",
        ],
    )


# ─── Modbus connection parameters (env-configurable) ─────────────────────────

MODBUS_SERIAL_PORT = os.getenv("MODBUS_SERIAL_PORT", "/dev/ttyUSB0")
MODBUS_BAUDRATE = int(os.getenv("MODBUS_BAUDRATE", "115200"))
MODBUS_TIMEOUT = float(os.getenv("MODBUS_TIMEOUT", "0.5"))
MODBUS_RETRIES = int(os.getenv("MODBUS_RETRIES", "1"))
SLAVE_ID = 1


# ─── Timeout guardrail helper ─────────────────────────────────────────────────

@contextlib.contextmanager
def timeout_guardrail(seconds: int):
    """Signal-based execution guardrail (Linux only)."""
    def _handler(signum, frame):
        raise TimeoutError(f"Test guardrail: exceeded {seconds}s limit")

    if hasattr(signal, "SIGALRM"):
        old = signal.signal(signal.SIGALRM, _handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
    else:
        yield


# ─── Session-scoped Modbus RTU / Serial client fixture ────────────────────────

@pytest.fixture(scope="session")
def tcp_modbus_client():
    """
    Session-scoped Modbus client shared across all HIL test modules.
    Configured for Modbus RTU over USB serial (e.g. /dev/ttyUSB0 at 115200 baud).

    Automatically skipped when no live ESP32 target is reachable at
    MODBUS_SERIAL_PORT — allows the full test suite to run in CI
    without physical hardware.
    """
    try:
        from pymodbus.client import ModbusSerialClient
    except ImportError:
        from pymodbus.client.sync import ModbusSerialClient

    client = ModbusSerialClient(
        port=MODBUS_SERIAL_PORT,
        baudrate=MODBUS_BAUDRATE,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=MODBUS_TIMEOUT,
        retries=MODBUS_RETRIES,
    )
    try:
        connected = client.connect()
    except Exception as exc:
        pytest.skip(f"Modbus Serial target {MODBUS_SERIAL_PORT} unreachable: {exc}")

    if not connected:
        pytest.skip(f"Could not connect to Modbus Serial port {MODBUS_SERIAL_PORT}")

    yield client
    client.close()


@pytest.fixture(scope="session")
def modbus_client(tcp_modbus_client):
    """Alias for tcp_modbus_client."""
    return tcp_modbus_client
