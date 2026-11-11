import os
import time
from unittest.mock import patch
import pytest
from PyQt6.QtWidgets import QApplication, QFileDialog

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from tools.supervisory.modbus_worker import (
    ModbusWorker, registers_to_float, float_to_registers
)
from tools.supervisory.ui_main import DigitalDisplayCard, SupervisoryMainWindow


@pytest.fixture(scope="session")
def qapp():
    """Ensure a headless QApplication instance exists for PyQt widgets and signals."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(["--platform", "offscreen"])
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


def test_digital_display_card_widget(qapp):
    """Test DigitalDisplayCard initialization, values, units and colors."""
    card = DigitalDisplayCard("Posição Atual", unit="mm", accent_color="#A6E3A1")
    assert card.title_text == "Posição Atual"
    assert card.get_unit() == "mm"
    assert card.get_value() == "--"

    # Set value
    card.set_value("123.45")
    assert card.get_value() == "123.45"
    assert card._current_color == "#A6E3A1"

    # Set value with custom color (e.g. green for in-position)
    card.set_value("+0.02", custom_color="#A6E3A1")
    assert card.get_value() == "+0.02"
    assert card._current_color == "#A6E3A1"

    # Set value with error alert color
    card.set_value("+15.30", custom_color="#F9E2AF")
    assert card.get_value() == "+15.30"
    assert card._current_color == "#F9E2AF"


def test_supervisory_telemetry_display_updates(qapp):
    """Test SupervisoryMainWindow displays live telemetry and computes error correctly."""
    win = SupervisoryMainWindow()
    try:
        assert win.card_pos.get_value() == "--"
        assert win.card_sp.get_value() == "--"
        assert win.card_err.get_value() == "--"
        assert win.card_vel.get_value() == "--"
        assert win.card_duty.get_value() == "--"

        # Case 1: In-position (|error| <= 0.1 mm)
        data_in_pos = {
            "timestamp": time.time(),
            "target_setpoint": 200.0,
            "current_position": 199.95,
            "current_velocity": 0.0,
            "duty_cycle": 5.0,
            "machine_state": 1,
            "estop_button": 1,
            "start_button": 1,
            "home_sensor": 0,
            "safety_enable": 1,
            "led_status": 1
        }
        win.on_telemetry_updated(data_in_pos)

        assert win.card_sp.get_value() == "200.00"
        assert win.card_pos.get_value() == "199.95"
        assert win.card_err.get_value() == "+0.05"
        assert win.card_err._current_color == "#A6E3A1"  # In-position green
        assert win.card_vel.get_value() == "0.0"
        assert win.card_duty.get_value() == "+5.0"

        # Case 2: Tracking with larger error (|error| > 0.1 mm)
        data_moving = dict(data_in_pos, current_position=150.0, current_velocity=35.4, duty_cycle=85.0)
        win.on_telemetry_updated(data_moving)

        assert win.card_pos.get_value() == "150.00"
        assert win.card_err.get_value() == "+50.00"
        assert win.card_err._current_color == "#F9E2AF"  # Yellow tracking color
        assert win.card_vel.get_value() == "35.4"
        assert win.card_duty.get_value() == "+85.0"

    finally:
        win.modbus_worker.stop_thread()


def test_supervisory_circular_buffer_rolling_and_resizing(qapp):
    """Test dynamic buffer resizing and FIFO circular rolling behavior."""
    win = SupervisoryMainWindow()
    try:
        # Default max_points is 300
        assert win.max_points == 300
        assert win.spin_max_points.value() == 300

        # Change buffer limit to 100 points
        win.spin_max_points.setValue(100)
        assert win.max_points == 100
        assert win.time_history.maxlen == 100
        assert win.position_history.maxlen == 100

        # Feed 150 samples to test circular discard of oldest 50 samples
        base_time = time.time()
        for i in range(150):
            data = {
                "timestamp": base_time + i * 0.1,
                "target_setpoint": 100.0,
                "current_position": float(i),
                "current_velocity": 10.0,
                "duty_cycle": 20.0,
                "machine_state": 1,
                "estop_button": 1,
                "start_button": 1,
                "home_sensor": 0,
                "safety_enable": 1,
                "led_status": 1
            }
            win.on_telemetry_updated(data)

        # Deque size should be capped at 100
        assert len(win.time_history) == 100
        assert len(win.position_history) == 100
        # Oldest kept point should be 50.0 (0..49 discarded)
        assert win.position_history[0] == 50.0
        # Newest point should be 149.0
        assert win.position_history[-1] == 149.0
        assert win.lbl_points_info.text() == "Pontos exibidos: 100 / 100"

        # Resize buffer to 200 points
        win.spin_max_points.setValue(200)
        assert win.max_points == 200
        assert win.time_history.maxlen == 200
        assert len(win.position_history) == 100  # Previous 100 preserved!

        # Clear graphs
        win.clear_graphs()
        assert len(win.time_history) == 0
        assert len(win.position_history) == 0
        assert win.lbl_points_info.text() == "Pontos exibidos: 0 / 200"

    finally:
        win.modbus_worker.stop_thread()


def test_supervisory_burst_auto_expansion(qapp, monkeypatch):
    """Test that open-loop burst buffer automatically expands graph buffer if needed."""
    win = SupervisoryMainWindow()
    try:
        # Mock file dialog so on_burst_data_ready does not prompt
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: ("", ""))

        # Current buffer size is 300
        assert win.max_points == 300

        # Generate 550 dummy samples (matching standard 670mm open-loop test)
        burst_samples = [
            {"time_s": i * 0.01, "position_mm": i * 0.9, "velocity_mm_s": 90.0, "duty_pct": 100.0}
            for i in range(550)
        ]

        win.on_burst_data_ready(burst_samples)

        # Buffer should have auto-expanded to at least 550
        assert win.max_points >= 550
        assert win.spin_max_points.value() >= 550
        assert len(win.time_history) == 550
        assert len(win.position_history) == 550
        assert win.lbl_points_info.text() == f"Pontos exibidos: 550 / {win.max_points}"

    finally:
        win.modbus_worker.stop_thread()
