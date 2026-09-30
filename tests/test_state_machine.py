"""
test_state_machine.py — State-machine transition HIL tests over Modbus TCP.

Requires a live ESP32 running the Modbus TCP slave on MODBUS_HOST:MODBUS_PORT.
All tests are automatically skipped when no hardware target is reachable.

Tests the legal state transitions of the safety state machine:
    IDLE → MOVING → EMERGENCY → IDLE (via RESET)

Environment variables (see conftest.py / pytest.ini):
    MODBUS_HOST  – ESP32 IP address (default: 192.168.1.100)
    MODBUS_PORT  – TCP port         (default: 502)
"""

import os
import time
import signal
import contextlib
import pytest

# Per-test timeout enforced by pytest-timeout plugin
pytestmark = pytest.mark.timeout(3)

TEST_TIMEOUT_SEC = int(os.getenv("TEST_TIMEOUT", "3"))
SLAVE_ID = 1

# ─── Command Register Flags ───────────────────────────────────────────────────
CMD_NONE              = 0
CMD_START             = 1
CMD_STOP              = 2
CMD_RESET             = 3
CMD_SIMULATE_EMERGENCY = 99

# ─── Machine State Values ─────────────────────────────────────────────────────
STATE_IDLE      = 0
STATE_MOVING    = 1
STATE_EMERGENCY = 2


# ─── Timeout guardrail ────────────────────────────────────────────────────────

@contextlib.contextmanager
def timeout_guardrail(seconds: int):
    """Signal-based guardrail to enforce hard deadlines on Linux."""
    def _handler(signum, frame):
        raise TimeoutError(f"Guardrail triggered: exceeded {seconds}s limit")

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


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _read_machine_state(client) -> int:
    """Read Input Register 0x0006 (machine_state uint16)."""
    result = client.read_input_registers(0x0006, count=1, slave=SLAVE_ID)
    assert not result.isError(), f"read_input_registers (state) failed: {result}"
    return result.registers[0]


def _send_command(client, command_val: int):
    """Write command uint16 to Holding Register 0x0002."""
    result = client.write_registers(0x0002, [command_val], slave=SLAVE_ID)
    assert not result.isError(), f"write_registers (cmd={command_val}) failed: {result}"


# ─── HIL tests (require tcp_modbus_client from conftest.py) ──────────────────

def test_state_machine_normal_flow(tcp_modbus_client):
    """IDLE → START → MOVING: verify legal forward transition."""
    with timeout_guardrail(TEST_TIMEOUT_SEC):
        # Reset to IDLE first in case a prior test left the machine in another state
        _send_command(tcp_modbus_client, CMD_RESET)
        time.sleep(0.05)

        state = _read_machine_state(tcp_modbus_client)
        assert state == STATE_IDLE, f"Expected IDLE (0) after RESET, got {state}"

        _send_command(tcp_modbus_client, CMD_START)
        time.sleep(0.05)

        state = _read_machine_state(tcp_modbus_client)
        assert state == STATE_MOVING, f"Expected MOVING (1) after START, got {state}"


def test_state_machine_emergency_lockout_rejection(tcp_modbus_client):
    """EMERGENCY state must reject all START commands (safety interlock)."""
    with timeout_guardrail(TEST_TIMEOUT_SEC):
        _send_command(tcp_modbus_client, CMD_SIMULATE_EMERGENCY)
        time.sleep(0.05)

        state = _read_machine_state(tcp_modbus_client)
        assert state == STATE_EMERGENCY, f"Expected EMERGENCY (2) after simulate, got {state}"

        # Attempt to illegally transition to MOVING while in EMERGENCY
        _send_command(tcp_modbus_client, CMD_START)
        time.sleep(0.05)

        state = _read_machine_state(tcp_modbus_client)
        assert state == STATE_EMERGENCY, (
            f"EMERGENCY lockout violated — START was accepted, state={state}"
        )


def test_state_machine_safe_reset(tcp_modbus_client):
    """RESET command must return the machine from EMERGENCY back to IDLE."""
    with timeout_guardrail(TEST_TIMEOUT_SEC):
        # Ensure we are in EMERGENCY first (may already be from previous test)
        _send_command(tcp_modbus_client, CMD_SIMULATE_EMERGENCY)
        time.sleep(0.05)

        _send_command(tcp_modbus_client, CMD_RESET)
        time.sleep(0.05)

        state = _read_machine_state(tcp_modbus_client)
        assert state == STATE_IDLE, f"Expected IDLE (0) after RESET, got {state}"
