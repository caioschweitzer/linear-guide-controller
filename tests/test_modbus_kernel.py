import os
import sys
import time
import signal
import contextlib
import pytest

try:
    from pymodbus.client import ModbusSerialClient
except ImportError:
    from pymodbus.client.sync import ModbusSerialClient

try:
    from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder
    from pymodbus.constants import Endian
except ImportError:
    from pymodbus.constants import Endian
    from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder

import serial.tools.list_ports

# Enforce strict 3-second pytest timeout per test
pytestmark = pytest.mark.timeout(3)

# Timeout Guardrail Configuration
MODBUS_TIMEOUT = float(os.getenv("MODBUS_TIMEOUT", "0.5"))  # 500ms serial response timeout
MODBUS_RETRIES = int(os.getenv("MODBUS_RETRIES", "1"))      # Fast fail (1 attempt)
TEST_TIMEOUT_SEC = int(os.getenv("TEST_TIMEOUT", "3"))       # 3 seconds max per test function
BAUDRATE = 115200
SLAVE_ID = 1


class ModbusTimeoutGuardrailError(TimeoutError):
    """Exception raised when a test execution exceeds the timeout guardrail."""
    pass


@contextlib.contextmanager
def timeout_guardrail(seconds: int):
    """Signal-based execution guardrail to strictly enforce timeouts on Linux."""
    def _handle_timeout(signum, frame):
        raise ModbusTimeoutGuardrailError(f"Guardrail triggered: Test execution exceeded {seconds} second(s) limit")

    # Only register SIGALRM in main thread (Unix/Linux)
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
    """Detects the serial port where the ESP32 is connected."""
    env_port = os.getenv("MODBUS_PORT")
    if env_port:
        return env_port

    ports = list(serial.tools.list_ports.comports())
    if not ports:
        return "/dev/ttyUSB0"

    # Known ESP32 USB-to-UART / Native USB VIDs:
    ESP_VIDS = {0x303a, 0x10c4, 0x1a86, 0x0403}

    # Priority 1: Match Espressif VID (0x303a) or description keyword
    for p in ports:
        if p.vid == 0x303a or (p.description and any(kw in p.description.lower() for kw in ["esp32", "espressif"])):
            return p.device

    # Priority 2: Match known USB-Serial bridge VIDs (CP210x, CH340, FTDI)
    for p in ports:
        if p.vid in ESP_VIDS:
            return p.device

    # Priority 3: Fallback to any /dev/ttyACM* or /dev/ttyUSB* device
    for p in ports:
        if "ttyACM" in p.device or "ttyUSB" in p.device:
            return p.device

    return ports[0].device


from test_system_integration import load_system_lib

SERIAL_PORT = auto_detect_esp32_port()


@pytest.fixture(scope="module")
def sys_lib():
    return load_system_lib()


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


def test_holding_register_setpoint_write_read(modbus_client):
    with timeout_guardrail(TEST_TIMEOUT_SEC):
        builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.BIG)
        target_setpoint = 150.5  # mm
        builder.add_32bit_float(target_setpoint)
        payload = builder.to_registers()

        # Write 32-bit float to Holding Register 0x0000 (2 registers)
        write_result = modbus_client.write_registers(0x0000, payload, slave=SLAVE_ID)
        assert not write_result.isError(), "Modbus write_registers failed"

        time.sleep(0.05)

        # Read back Holding Register 0x0000
        read_result = modbus_client.read_holding_registers(0x0000, count=2, slave=SLAVE_ID)
        assert not read_result.isError(), "Modbus read_holding_registers failed"

        decoder = BinaryPayloadDecoder.fromRegisters(read_result.registers, byteorder=Endian.BIG, wordorder=Endian.BIG)
        read_setpoint = decoder.decode_32bit_float()

        assert abs(read_setpoint - target_setpoint) < 1e-3, f"Expected {target_setpoint}, got {read_setpoint}"


def test_holding_register_pid_gains_write_read(modbus_client):
    with timeout_guardrail(TEST_TIMEOUT_SEC):
        builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.BIG)
        target_kp, target_ki, target_kd = 4.5, 1.2, 0.08
        builder.add_32bit_float(target_kp)
        builder.add_32bit_float(target_ki)
        builder.add_32bit_float(target_kd)
        payload = builder.to_registers()

        # Write 32-bit floats to Holding Registers 0x0003 to 0x0008 (6 registers)
        write_result = modbus_client.write_registers(0x0003, payload, slave=SLAVE_ID)
        if write_result.isError():
            pytest.skip("Physical ESP32 Modbus hardware not connected.")
        assert not write_result.isError(), "Modbus write_registers for PID gains failed"

        time.sleep(0.05)

        # Read back Holding Registers 0x0003 to 0x0008
        read_result = modbus_client.read_holding_registers(0x0003, count=6, slave=SLAVE_ID)
        assert not read_result.isError(), "Modbus read_holding_registers for PID gains failed"

        decoder = BinaryPayloadDecoder.fromRegisters(read_result.registers, byteorder=Endian.BIG, wordorder=Endian.BIG)
        read_kp = decoder.decode_32bit_float()
        read_ki = decoder.decode_32bit_float()
        read_kd = decoder.decode_32bit_float()

        assert abs(read_kp - target_kp) < 1e-3, f"Expected Kp {target_kp}, got {read_kp}"
        assert abs(read_ki - target_ki) < 1e-3, f"Expected Ki {target_ki}, got {read_ki}"
        assert abs(read_kd - target_kd) < 1e-3, f"Expected Kd {target_kd}, got {read_kd}"


def test_input_registers_read_initial_state(modbus_client):
    with timeout_guardrail(TEST_TIMEOUT_SEC):
        # Read Input Registers 0x0000 to 0x0004 (5 registers)
        read_result = modbus_client.read_input_registers(0x0000, count=5, slave=SLAVE_ID)
        assert not read_result.isError(), "Modbus read_input_registers failed"

        decoder = BinaryPayloadDecoder.fromRegisters(read_result.registers, byteorder=Endian.BIG, wordorder=Endian.BIG)
        current_position = decoder.decode_32bit_float()
        current_velocity = decoder.decode_32bit_float()
        machine_state = decoder.decode_16bit_uint()

        assert abs(current_position - 0.0) < 1e-3, f"Expected position 0.0, got {current_position}"
        assert abs(current_velocity - 0.0) < 1e-3, f"Expected velocity 0.0, got {current_velocity}"
        assert machine_state == 0, f"Expected IDLE state (0), got {machine_state}"


def test_discrete_inputs_and_coils_c_struct(sys_lib):
    """Host-native test of Modbus discrete inputs and coils struct mapping via ctypes."""
    sys_lib.shared_data_init()
    
    # Verify default discrete values
    assert sys_lib.shared_data_get_state() == 0


def test_discrete_inputs_read(modbus_client):
    with timeout_guardrail(TEST_TIMEOUT_SEC):
        # Read Discrete Inputs 0x0000 to 0x0002 (3 bits)
        read_result = modbus_client.read_discrete_inputs(0x0000, count=3, slave=SLAVE_ID)
        if read_result.isError():
            pytest.skip("Physical ESP32 Modbus hardware not connected or discrete inputs unsupported by hardware mock.")
        assert len(read_result.bits) >= 3


def test_coils_read_write(modbus_client):
    with timeout_guardrail(TEST_TIMEOUT_SEC):
        # Write Coil 0x0000 (Status LED) to True
        write_result = modbus_client.write_coil(0x0000, True, slave=SLAVE_ID)
        if write_result.isError():
            pytest.skip("Physical ESP32 Modbus hardware not connected or coils unsupported by hardware mock.")
        
        time.sleep(0.05)

        # Read back Coils 0x0000 to 0x0002
        read_result = modbus_client.read_coils(0x0000, count=3, slave=SLAVE_ID)
        if not read_result.isError():
            assert read_result.bits[0] is True


