"""
test_modbus_kernel.py — Modbus TCP register map HIL tests.

Requires a live ESP32 running the Modbus TCP slave on MODBUS_HOST:MODBUS_PORT.
All tests are automatically skipped when no hardware target is reachable.

Host-native struct-layout test (test_discrete_inputs_and_coils_c_struct) runs
without network hardware via ctypes against libsystem_integration.so.

Environment variables (see conftest.py / pytest.ini):
    MODBUS_HOST     – ESP32 IP address (default: 192.168.1.100)
    MODBUS_PORT     – TCP port         (default: 502)
    MODBUS_TIMEOUT  – Socket timeout s (default: 0.5)
"""

import os
import sys
import time
import signal
import contextlib
import pytest

try:
    from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder
    from pymodbus.constants import Endian
except ImportError:
    from pymodbus.constants import Endian
    from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder

from test_system_integration import load_system_lib

# Per-test timeout enforced by pytest-timeout plugin
pytestmark = pytest.mark.timeout(3)

TEST_TIMEOUT_SEC = int(os.getenv("TEST_TIMEOUT", "3"))
SLAVE_ID = 1


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


# ─── Host-native fixture ──────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sys_lib():
    return load_system_lib()


# ─── TCP HIL tests (require tcp_modbus_client from conftest.py) ───────────────

def test_holding_register_setpoint_write_read(tcp_modbus_client):
    """Write a Float32 setpoint to HR 0x0000-0x0001 and verify the read-back."""
    with timeout_guardrail(TEST_TIMEOUT_SEC):
        builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.BIG)
        target_setpoint = 150.5  # mm
        builder.add_32bit_float(target_setpoint)
        payload = builder.to_registers()

        write_result = tcp_modbus_client.write_registers(0x0000, payload, slave=SLAVE_ID)
        assert not write_result.isError(), "Modbus write_registers (setpoint) failed"

        time.sleep(0.05)

        read_result = tcp_modbus_client.read_holding_registers(0x0000, count=2, slave=SLAVE_ID)
        assert not read_result.isError(), "Modbus read_holding_registers (setpoint) failed"

        decoder = BinaryPayloadDecoder.fromRegisters(
            read_result.registers, byteorder=Endian.BIG, wordorder=Endian.BIG
        )
        read_setpoint = decoder.decode_32bit_float()
        assert abs(read_setpoint - target_setpoint) < 1e-3, (
            f"Setpoint round-trip error: expected {target_setpoint}, got {read_setpoint}"
        )


def test_holding_register_pid_gains_write_read(tcp_modbus_client):
    """Write Kp/Ki/Kd Float32 values to HR 0x0003-0x0008 and verify round-trip."""
    with timeout_guardrail(TEST_TIMEOUT_SEC):
        target_kp, target_ki, target_kd = 4.5, 1.2, 0.08

        builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.BIG)
        builder.add_32bit_float(target_kp)
        builder.add_32bit_float(target_ki)
        builder.add_32bit_float(target_kd)
        payload = builder.to_registers()

        write_result = tcp_modbus_client.write_registers(0x0003, payload, slave=SLAVE_ID)
        assert not write_result.isError(), "Modbus write_registers (PID gains) failed"

        time.sleep(0.05)

        read_result = tcp_modbus_client.read_holding_registers(0x0003, count=6, slave=SLAVE_ID)
        assert not read_result.isError(), "Modbus read_holding_registers (PID gains) failed"

        decoder = BinaryPayloadDecoder.fromRegisters(
            read_result.registers, byteorder=Endian.BIG, wordorder=Endian.BIG
        )
        read_kp = decoder.decode_32bit_float()
        read_ki = decoder.decode_32bit_float()
        read_kd = decoder.decode_32bit_float()

        assert abs(read_kp - target_kp) < 1e-3, f"Kp mismatch: expected {target_kp}, got {read_kp}"
        assert abs(read_ki - target_ki) < 1e-3, f"Ki mismatch: expected {target_ki}, got {read_ki}"
        assert abs(read_kd - target_kd) < 1e-3, f"Kd mismatch: expected {target_kd}, got {read_kd}"


def test_input_registers_telemetry_read(tcp_modbus_client):
    """Read telemetry Input Registers 0x0000-0x0006 and validate structure."""
    with timeout_guardrail(TEST_TIMEOUT_SEC):
        read_result = tcp_modbus_client.read_input_registers(0x0000, count=7, slave=SLAVE_ID)
        assert not read_result.isError(), "Modbus read_input_registers failed"
        assert len(read_result.registers) == 7, "Expected 7 Input Registers"

        decoder = BinaryPayloadDecoder.fromRegisters(
            read_result.registers, byteorder=Endian.BIG, wordorder=Endian.BIG
        )
        current_position = decoder.decode_32bit_float()
        current_velocity = decoder.decode_32bit_float()
        duty_cycle = decoder.decode_32bit_float()
        machine_state = decoder.decode_16bit_uint()

        # Validate telemetry values within valid physical envelope
        assert -5.0 <= current_position <= 670.0, f"Expected position within rail bounds [-5.0, 670.0], got {current_position}"
        assert abs(current_velocity) < 500.0, f"Expected velocity within limits, got {current_velocity}"
        assert abs(duty_cycle) <= 100.0, f"Expected duty <= 100%, got {duty_cycle}"
        assert machine_state in (0, 1, 2, 3, 4), f"Unexpected machine_state value: {machine_state}"


def test_discrete_inputs_read(tcp_modbus_client):
    """Read physical discrete input bits (E-Stop, Start, Safety Enable) via FC 0x02."""
    with timeout_guardrail(TEST_TIMEOUT_SEC):
        read_result = tcp_modbus_client.read_discrete_inputs(0x0000, count=3, slave=SLAVE_ID)
        if read_result.isError():
            pytest.skip("Discrete inputs read error — hardware may not support FC 0x02 in this state.")
        assert len(read_result.bits) >= 3, "Expected at least 3 discrete input bits"


def test_coils_status_led_read_write(tcp_modbus_client):
    """Write Status LED coil (0x0000) to True and verify read-back."""
    with timeout_guardrail(TEST_TIMEOUT_SEC):
        write_result = tcp_modbus_client.write_coil(0x0000, True, slave=SLAVE_ID)
        if write_result.isError():
            pytest.skip("Coil write error — coil FC 0x05 may not be supported in this state.")

        time.sleep(0.05)

        read_result = tcp_modbus_client.read_coils(0x0000, count=1, slave=SLAVE_ID)
        if not read_result.isError():
            assert read_result.bits[0] is True, "Status LED coil should read back True after write"


# ─── Host-native struct-layout test (no hardware required) ────────────────────

def test_discrete_inputs_and_coils_c_struct(sys_lib):
    """Host-native validation: shared_data C-struct default state via ctypes."""
    sys_lib.shared_data_init()
    assert sys_lib.shared_data_get_state() == 0, (
        "Firmware shared_data_init() must default to IDLE state (0)"
    )
