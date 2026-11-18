"""Unit tests for configurable open-loop PWM Modbus writes and multi-curve normalization."""

import os
import time
from unittest.mock import MagicMock, patch
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog

from tools.supervisory.curve_utils import compute_normalized_curve, compute_sine_setpoint
from tools.supervisory.modbus_worker import ModbusWorker, float_to_registers
from tools.supervisory.ui_main import SupervisoryMainWindow


def test_modbus_worker_writes_pwm_before_open_loop_command():
    worker = ModbusWorker()
    mock_client = MagicMock()
    ok_res = MagicMock()
    ok_res.isError.return_value = False
    mock_client.write_registers.return_value = ok_res
    mock_client.write_register.return_value = ok_res

    worker._client = mock_client
    worker._connected = True

    worker.queue_open_loop_test(65.0, mode=1, coast_pos_mm=350.0)
    worker._process_command_queue()

    pwm_hi, pwm_lo = float_to_registers(65.0)
    coast_hi, coast_lo = float_to_registers(350.0)
    mock_client.write_registers.assert_called_once_with(
        address=0x000A, values=[pwm_hi, pwm_lo, 1, coast_hi, coast_lo], slave=worker.slave_id
    )
    mock_client.write_register.assert_called_once_with(
        address=0x0002, value=5, slave=worker.slave_id
    )
    assert worker._last_open_loop_pwm == 65.0


def test_modbus_worker_clamps_pwm_and_tags_burst_samples():
    worker = ModbusWorker()
    mock_client = MagicMock()
    ok_res = MagicMock()
    ok_res.isError.return_value = False
    mock_client.write_registers.return_value = ok_res
    mock_client.write_register.return_value = ok_res

    # Mock 2 samples in burst buffer: sample 0 with 45.5% duty, sample 1 with 0.0% duty (coast)
    pos_hi, pos_lo = float_to_registers(10.0)
    vel_hi, vel_lo = float_to_registers(100.0)
    duty_hi_1, duty_lo_1 = float_to_registers(45.5)
    duty_hi_2, duty_lo_2 = float_to_registers(0.0)

    sample_res_1 = MagicMock()
    sample_res_1.isError.return_value = False
    sample_res_1.registers = [0, 100, pos_hi, pos_lo, vel_hi, vel_lo, duty_hi_1, duty_lo_1]

    sample_res_2 = MagicMock()
    sample_res_2.isError.return_value = False
    sample_res_2.registers = [0, 110, pos_hi, pos_lo, vel_hi, vel_lo, duty_hi_2, duty_lo_2]

    mock_client.read_input_registers.side_effect = [sample_res_1, sample_res_2]

    worker._client = mock_client
    worker._connected = True

    # Out-of-range high PWM should clamp to 100.0
    worker.queue_open_loop_test(140.0)
    worker._process_command_queue()
    assert worker._last_open_loop_pwm == 100.0

    # Valid 45.5% PWM in coast mode
    worker.queue_open_loop_test(45.5, mode=1, coast_pos_mm=380.0)
    worker._process_command_queue()

    received = []
    worker.burst_data_ready.connect(received.append)
    worker._do_download_burst_buffer(2)

    assert len(received) == 1
    assert received[0][0]["duty_pct"] == 45.5
    assert received[0][1]["duty_pct"] == 0.0


def test_compute_normalized_curve_single_curve():
    curve = [
        {"time_s": 0.0, "position_mm": 0.0, "velocity_mm_s": 0.0, "duty_pct": 80.0},
        {"time_s": 0.01, "position_mm": 50.0, "velocity_mm_s": 200.0, "duty_pct": 80.0},
        {"time_s": 0.02, "position_mm": 100.0, "velocity_mm_s": 100.0, "duty_pct": 80.0},
    ]
    norm = compute_normalized_curve([curve], duty_pct=80.0)
    assert len(norm) == 3
    assert norm[0]["position_norm"] == 0.0
    assert norm[1]["position_norm"] == 0.5
    assert norm[2]["position_norm"] == 1.0
    assert norm[1]["velocity_norm"] == 1.0
    assert norm[2]["velocity_norm"] == 0.5
    assert norm[0]["duty_pct"] == 80.0
    assert norm[0]["curve_count"] == 1


def test_compute_normalized_curve_multiple_unequal_lengths():
    c1 = [
        {"time_s": 0.0, "position_mm": 0.0, "velocity_mm_s": 0.0},
        {"time_s": 0.01, "position_mm": 10.0, "velocity_mm_s": 100.0},
        {"time_s": 0.02, "position_mm": 30.0, "velocity_mm_s": 200.0},
        {"time_s": 0.03, "position_mm": 60.0, "velocity_mm_s": 300.0},
    ]
    c2 = [
        {"time_s": 0.0, "position_mm": 0.0, "velocity_mm_s": 0.0},
        {"time_s": 0.01, "position_mm": 20.0, "velocity_mm_s": 100.0},
        {"time_s": 0.02, "position_mm": 50.0, "velocity_mm_s": 200.0},
    ]
    norm = compute_normalized_curve([c1, c2], duty_pct=60.0)
    # Truncated to min length = 3
    assert len(norm) == 3
    assert norm[0]["position_mean_mm"] == 0.0
    assert norm[1]["position_mean_mm"] == 15.0
    assert norm[2]["position_mean_mm"] == 40.0
    assert norm[0]["position_norm"] == 0.0
    assert norm[1]["position_norm"] == pytest.approx(15.0 / 40.0, abs=1e-6)
    assert norm[2]["position_norm"] == 1.0
    assert norm[0]["curve_count"] == 2
    assert norm[0]["duty_pct"] == 60.0


def test_compute_normalized_curve_constant_and_empty():
    assert compute_normalized_curve([], duty_pct=50.0) == []

    const_curve = [
        {"time_s": 0.0, "position_mm": 5.0, "velocity_mm_s": 0.0},
        {"time_s": 0.01, "position_mm": 5.0, "velocity_mm_s": 0.0},
    ]
    norm = compute_normalized_curve([const_curve], duty_pct=50.0)
    assert len(norm) == 2
    assert norm[0]["position_norm"] == 0.0
    assert norm[1]["position_norm"] == 0.0
    assert norm[0]["velocity_norm"] == 0.0


def test_ui_multi_curve_controls_and_batch_sequence(tmp_path):
    app = QApplication.instance() or QApplication(["--platform", "offscreen"])
    win = SupervisoryMainWindow()
    try:
        assert win.spin_ol_pwm.value() == 100.0
        assert win.spin_ol_curves.value() == 1
        assert not win.btn_export_norm_csv.isEnabled()

        win.spin_ol_pwm.setValue(70.0)
        win.spin_ol_curves.setValue(2)
        assert "2 CURVES" in win.btn_open_loop.text()
        assert "70.0% PWM" in win.btn_open_loop.text()
        assert not win.spin_ol_coast_pos.isEnabled()

        # Select Coast-to-Stop mode
        win.combo_ol_mode.setCurrentIndex(1)
        assert win.spin_ol_coast_pos.isEnabled()
        win.spin_ol_coast_pos.setValue(350.0)
        assert "350 mm -> 0%" in win.btn_open_loop.text()

        # Simulate connected & IDLE at 0 mm
        win.modbus_worker._connected = True
        win.latest_position = 0.0
        win.latest_machine_state = 0

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes), \
             patch.object(win.modbus_worker, "queue_open_loop_test") as mock_ol, \
             patch.object(win.modbus_worker, "queue_command") as mock_cmd:

            win.start_open_loop_test()
            assert win._batch_active is True
            assert win._batch_total == 2
            mock_ol.assert_called_once_with(70.0, 1, 350.0)

            curve_1 = [
                {"time_s": 0.0, "position_mm": 0.0, "velocity_mm_s": 0.0, "duty_pct": 70.0},
                {"time_s": 0.01, "position_mm": 20.0, "velocity_mm_s": 200.0, "duty_pct": 70.0},
            ]
            curve_2 = [
                {"time_s": 0.0, "position_mm": 0.0, "velocity_mm_s": 0.0, "duty_pct": 70.0},
                {"time_s": 0.01, "position_mm": 24.0, "velocity_mm_s": 240.0, "duty_pct": 70.0},
            ]

            # Curve 1 finishes -> should command CMD_HOME (4)
            win.on_burst_data_ready(curve_1)
            assert win._batch_phase == "WAITING_HOME"
            mock_cmd.assert_called_once_with(4)

            # Simulate homing complete -> transitions to SETTLING, then next run
            win.on_telemetry_updated({
                "timestamp": time.time(),
                "target_setpoint": 0.0,
                "current_position": 0.5,
                "current_velocity": 0.0,
                "duty_cycle": 0.0,
                "machine_state": 0,
                "estop_button": False,
                "start_button": False,
                "safety_enable": True,
                "home_sensor": True,
                "led_status": False,
                "kp": 2.0,
                "ki": 0.5,
                "kd": 0.05,
                "burst_status": 0,
                "burst_sample_count": 0,
            })
            assert win._batch_phase == "SETTLING"
            win._start_next_batch_run()
            assert mock_ol.call_count == 2

            # Curve 2 finishes -> batch completes and exports normalized CSV
            out_csv = tmp_path / "norm.csv"
            with patch.object(QFileDialog, "getSaveFileName", return_value=(str(out_csv), "CSV")), \
                 patch.object(QMessageBox, "information"):
                win.on_burst_data_ready(curve_2)

            assert win._batch_active is False
            assert out_csv.exists()
            content = out_csv.read_text(encoding="utf-8")
            assert "position_norm" in content
            assert "70.0,2" in content
    finally:
        win.close()


def test_compute_sine_setpoint_and_clamping():
    # t = 0 -> center
    assert compute_sine_setpoint(0.0, 300.0, 100.0, 0.5) == pytest.approx(300.0)
    # t = 0.5 s at 0.5 Hz (1/4 period) -> peak = 400.0
    assert compute_sine_setpoint(0.5, 300.0, 100.0, 0.5) == pytest.approx(400.0)
    # t = 1.5 s at 0.5 Hz (3/4 period) -> trough = 200.0
    assert compute_sine_setpoint(1.5, 300.0, 100.0, 0.5) == pytest.approx(200.0)
    # Clamped to [0.0, 670.0]
    assert compute_sine_setpoint(0.5, 600.0, 200.0, 0.5) == 670.0
    assert compute_sine_setpoint(1.5, 50.0, 200.0, 0.5) == 0.0


def test_ui_sine_wave_trajectory_control():
    app = QApplication.instance() or QApplication(["--platform", "offscreen"])
    win = SupervisoryMainWindow()
    try:
        win.modbus_worker._connected = True
        win.latest_machine_state = 0
        win.spin_sine_center.setValue(250.0)
        win.spin_sine_amp.setValue(100.0)
        win.spin_sine_freq.setValue(0.5)
        win.spin_sine_cycles.setValue(1)

        with patch.object(win.modbus_worker, "queue_setpoint") as mock_sp, \
             patch.object(win.modbus_worker, "queue_command") as mock_cmd:
            win.start_sine_wave()
            assert win._sine_active is True
            assert win.btn_sine_stop.isEnabled()
            mock_sp.assert_called_with(250.0)
            mock_cmd.assert_called_once_with(1)

            # Simulate tick at 0.5s (peak = 350.0)
            win._sine_start_time = time.time() - 0.5
            win._on_sine_tick()
            assert mock_sp.call_args[0][0] == pytest.approx(350.0, abs=5.0)

            # Simulate cycle completion (>= 2.0s at 0.5 Hz = 1 cycle)
            win._sine_start_time = time.time() - 2.1
            win._on_sine_tick()
            assert win._sine_active is False
            assert not win.btn_sine_stop.isEnabled()
    finally:
        win.close()

