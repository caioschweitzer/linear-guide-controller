import time
import pytest
from PyQt6.QtCore import QCoreApplication

from tools.supervisory.modbus_worker import (
    ModbusWorker, registers_to_float, float_to_registers
)


@pytest.fixture(scope="module")
def qapp():
    """Ensure a QCoreApplication instance exists for PyQt signals."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    yield app


def test_ieee754_float_conversion_roundtrip():
    """Test 32-bit float encoding to 2 x uint16 registers and back."""
    test_values = [0.0, 150.5, 3.14159, -42.0, 0.0001, 999.999]

    for val in test_values:
        hi, lo = float_to_registers(val)
        decoded = registers_to_float(hi, lo)
        assert abs(decoded - val) < 1e-4, f"Expected {val}, got {decoded}"


def test_modbus_worker_connection_params():
    """Test setting Modbus TCP connection parameters."""
    worker = ModbusWorker()
    worker.set_connection_params("192.168.1.50", port=5020, slave_id=2)
    assert worker.host == "192.168.1.50"
    assert worker.port == 5020
    assert worker.slave_id == 2


def test_modbus_worker_command_queue(qapp):
    """Test ModbusWorker queueing actions and signal slots."""
    worker = ModbusWorker()
    worker.set_connection_params("127.0.0.1", port=502, slave_id=1)

    # Queue setpoint, commands, and PID gains
    worker.queue_setpoint(200.0)
    worker.queue_command(1)  # START
    worker.queue_pid_gains(4.0, 1.2, 0.08)
    worker.queue_emergency()

    assert not worker._command_queue.empty()
    assert worker._command_queue.qsize() == 4

    cmd1 = worker._command_queue.get_nowait()
    assert cmd1["action"] == "WRITE_SETPOINT"
    assert cmd1["value"] == 200.0

    cmd2 = worker._command_queue.get_nowait()
    assert cmd2["action"] == "WRITE_COMMAND"
    assert cmd2["value"] == 1

    cmd3 = worker._command_queue.get_nowait()
    assert cmd3["action"] == "WRITE_PID"
    assert cmd3["kp"] == 4.0

    cmd4 = worker._command_queue.get_nowait()
    assert cmd4["action"] == "WRITE_EMERGENCY"


def test_modbus_worker_lifecycle(qapp):
    """Test start and graceful shutdown of worker thread."""
    worker = ModbusWorker()
    received_logs = []

    worker.log_message.connect(lambda msg: received_logs.append(msg))
    worker.start()

    time.sleep(0.15)
    qapp.processEvents()
    assert worker.isRunning()

    worker.stop_thread()
    qapp.processEvents()
    assert not worker.isRunning()
    assert len(received_logs) >= 2
