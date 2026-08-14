import os
import time
import signal
import contextlib
import pytest

try:
    from pymodbus.client import ModbusSerialClient
except ImportError:
    from pymodbus.client.sync import ModbusSerialClient

import serial.tools.list_ports

pytestmark = pytest.mark.timeout(3)

MODBUS_TIMEOUT = float(os.getenv("MODBUS_TIMEOUT", "0.5"))
MODBUS_RETRIES = int(os.getenv("MODBUS_RETRIES", "1"))
TEST_TIMEOUT_SEC = int(os.getenv("TEST_TIMEOUT", "3"))
BAUDRATE = 115200
SLAVE_ID = 1

# Command Register Flags
CMD_NONE = 0
CMD_START = 1
CMD_STOP = 2
CMD_RESET = 3
CMD_SIMULATE_EMERGENCY = 99

# State Register Values
STATE_IDLE = 0
STATE_MOVING = 1
STATE_EMERGENCY = 2


class ModbusTimeoutGuardrailError(TimeoutError):
    """Exception raised when a test execution exceeds the timeout guardrail."""
    pass


@contextlib.contextmanager
def timeout_guardrail(seconds: int):
    """Signal-based execution guardrail to strictly enforce timeouts on Linux."""
    def _handle_timeout(signum, frame):
        raise ModbusTimeoutGuardrailError(f"Guardrail triggered: Test execution exceeded {seconds} second(s) limit")

    if hasattr(signal, 'SIGALRM'):
        old_handler = signal.signal(signal.SIGALRM, _handle_timeout)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        yield


def auto_detect_esp32_port() -> str:
    env_port = os.getenv("MODBUS_PORT")
    if env_port:
        return env_port

    ports = list(serial.tools.list_ports.comports())
    if not ports:
        return "/dev/ttyUSB0"

    ESP_VIDS = {0x303a, 0x10c4, 0x1a86, 0x0403}
    for p in ports:
        if p.vid == 0x303a or (p.description and any(kw in p.description.lower() for kw in ["esp32", "espressif"])):
            return p.device
    for p in ports:
        if p.vid in ESP_VIDS:
            return p.device
    for p in ports:
        if "ttyACM" in p.device or "ttyUSB" in p.device:
            return p.device

    return ports[0].device


SERIAL_PORT = auto_detect_esp32_port()


@pytest.fixture(scope="module")
def modbus_client():
    client = ModbusSerialClient(
        port=SERIAL_PORT,
        baudrate=BAUDRATE,
        parity='N',
        stopbits=1,
        bytesize=8,
        timeout=MODBUS_TIMEOUT,
        retries=MODBUS_RETRIES
    )
    with timeout_guardrail(TEST_TIMEOUT_SEC):
        connected = False
        try:
            connected = client.connect()
        except Exception as e:
            pytest.fail(f"Serial port connection to {SERIAL_PORT} failed: {e}")

        if not connected:
            pytest.fail(f"Could not connect to serial port {SERIAL_PORT} (timeout: {MODBUS_TIMEOUT}s)")

    yield client
    client.close()


def read_machine_state(client) -> int:
    """Helper to read Input Register 0x0004 (State)."""
    result = client.read_input_registers(0x0004, count=1, slave=SLAVE_ID)
    assert not result.isError(), f"Failed to read machine state input register: {result}"
    return result.registers[0]


def send_modbus_command(client, command_val: int):
    """Helper to write Command to Holding Register 0x0002."""
    result = client.write_registers(0x0002, [command_val], slave=SLAVE_ID)
    assert not result.isError(), f"Failed to send command {command_val}: {result}"


def test_state_machine_normal_flow(modbus_client):
    with timeout_guardrail(TEST_TIMEOUT_SEC):
        # 1. Reset state to IDLE first if needed
        send_modbus_command(modbus_client, CMD_RESET)
        time.sleep(0.05)

        # 2. Check initial state is IDLE (0)
        current_state = read_machine_state(modbus_client)
        assert current_state == STATE_IDLE, f"Expected state IDLE (0), got {current_state}"

        # 3. Send START command (1)
        send_modbus_command(modbus_client, CMD_START)
        time.sleep(0.05)

        # 4. Verify transition to MOVING (1)
        current_state = read_machine_state(modbus_client)
        assert current_state == STATE_MOVING, f"Expected state MOVING (1), got {current_state}"


def test_state_machine_emergency_lockout_rejection(modbus_client):
    with timeout_guardrail(TEST_TIMEOUT_SEC):
        # 1. Trigger simulated Emergency (99)
        send_modbus_command(modbus_client, CMD_SIMULATE_EMERGENCY)
        time.sleep(0.05)

        # 2. Confirm state is EMERGENCY (2)
        current_state = read_machine_state(modbus_client)
        assert current_state == STATE_EMERGENCY, f"Expected state EMERGENCY (2), got {current_state}"

        # 3. Attempt invalid transition to MOVING (1) while in EMERGENCY
        send_modbus_command(modbus_client, CMD_START)
        time.sleep(0.05)

        # 4. Confirm transition was REJECTED and state remains EMERGENCY (2)
        current_state = read_machine_state(modbus_client)
        assert current_state == STATE_EMERGENCY, f"Expected state to remain EMERGENCY (2), got {current_state}"


def test_state_machine_safe_reset(modbus_client):
    with timeout_guardrail(TEST_TIMEOUT_SEC):
        # 1. Send RESET command (3)
        send_modbus_command(modbus_client, CMD_RESET)
        time.sleep(0.05)

        # 2. Confirm transition back to IDLE (0)
        current_state = read_machine_state(modbus_client)
        assert current_state == STATE_IDLE, f"Expected state IDLE (0) after RESET, got {current_state}"
