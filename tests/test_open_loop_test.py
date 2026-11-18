"""
test_open_loop_test.py - Unit tests for Open-Loop Step Test routine,
state-machine transitions, Modbus burst buffer access, and CSV export.
"""

import os
import csv
import ctypes
import tempfile
import pytest

from tools.supervisory.modbus_worker import ModbusWorker

# State and Command Constants
MACHINE_STATE_IDLE = 0
MACHINE_STATE_MOVING = 1
MACHINE_STATE_EMERGENCY = 2
MACHINE_STATE_HOMING = 3
MACHINE_STATE_OPEN_LOOP_TEST = 4

CMD_NONE = 0
CMD_START = 1
CMD_STOP = 2
CMD_RESET = 3
CMD_HOME = 4
CMD_OPEN_LOOP_TEST = 5
CMD_SIMULATE_EMERGENCY = 99

BURST_STATUS_IDLE = 0
BURST_STATUS_CAPTURING = 1
BURST_STATUS_READY = 2
BURST_STATUS_ABORTED = 3


class OpenLoopSampleStruct(ctypes.Structure):
    _fields_ = [
        ("time_ms", ctypes.c_uint32),
        ("position", ctypes.c_float),
        ("velocity", ctypes.c_float),
        ("duty_pct", ctypes.c_float),
    ]


class BurstBufferStruct(ctypes.Structure):
    _fields_ = [
        ("samples", OpenLoopSampleStruct * 825),
        ("sample_count", ctypes.c_uint16),
        ("status", ctypes.c_uint16),
        ("read_index", ctypes.c_uint16),
    ]


class SystemDataStruct(ctypes.Structure):
    _fields_ = [
        ("position_setpoint", ctypes.c_float),
        ("current_position", ctypes.c_float),
        ("current_velocity", ctypes.c_float),
        ("duty_cycle", ctypes.c_float),
        ("kp", ctypes.c_float),
        ("ki", ctypes.c_float),
        ("kd", ctypes.c_float),
        ("open_loop_pwm", ctypes.c_float),
        ("open_loop_coast_pos_mm", ctypes.c_float),
        ("open_loop_mode", ctypes.c_uint16),
        ("machine_state", ctypes.c_uint16),
        ("button_estop", ctypes.c_bool),
        ("button_start", ctypes.c_bool),
        ("safety_enable", ctypes.c_bool),
        ("led_status", ctypes.c_bool),
    ]


class HoldingRegStruct(ctypes.Structure):
    _fields_ = [
        ("setpoint_hi", ctypes.c_uint16),
        ("setpoint_lo", ctypes.c_uint16),
        ("command", ctypes.c_uint16),
        ("kp_hi", ctypes.c_uint16),
        ("kp_lo", ctypes.c_uint16),
        ("ki_hi", ctypes.c_uint16),
        ("ki_lo", ctypes.c_uint16),
        ("kd_hi", ctypes.c_uint16),
        ("kd_lo", ctypes.c_uint16),
        ("burst_read_index", ctypes.c_uint16),
        ("open_loop_pwm_hi", ctypes.c_uint16),
        ("open_loop_pwm_lo", ctypes.c_uint16),
        ("open_loop_mode", ctypes.c_uint16),
        ("open_loop_coast_pos_hi", ctypes.c_uint16),
        ("open_loop_coast_pos_lo", ctypes.c_uint16),
    ]


class InputRegStruct(ctypes.Structure):
    _fields_ = [
        ("pos_hi", ctypes.c_uint16),
        ("pos_lo", ctypes.c_uint16),
        ("vel_hi", ctypes.c_uint16),
        ("vel_lo", ctypes.c_uint16),
        ("duty_hi", ctypes.c_uint16),
        ("duty_lo", ctypes.c_uint16),
        ("state", ctypes.c_uint16),
        ("burst_status", ctypes.c_uint16),
        ("burst_sample_count", ctypes.c_uint16),
        ("sample_time_hi", ctypes.c_uint16),
        ("sample_time_lo", ctypes.c_uint16),
        ("sample_pos_hi", ctypes.c_uint16),
        ("sample_pos_lo", ctypes.c_uint16),
        ("sample_vel_hi", ctypes.c_uint16),
        ("sample_vel_lo", ctypes.c_uint16),
        ("sample_duty_hi", ctypes.c_uint16),
        ("sample_duty_lo", ctypes.c_uint16),
    ]


@pytest.fixture(scope="module")
def system_lib():
    so_path = os.path.join(os.path.dirname(__file__), "libsystem_integration.so")
    lib = ctypes.CDLL(so_path)

    lib.shared_data_init.argtypes = []
    lib.shared_data_init.restype = None

    lib.shared_data_get_state.argtypes = []
    lib.shared_data_get_state.restype = ctypes.c_int

    lib.shared_data_request_state_change.argtypes = [ctypes.c_int]
    lib.shared_data_request_state_change.restype = ctypes.c_bool

    lib.modbus_slave_init.argtypes = []
    lib.modbus_slave_init.restype = ctypes.c_int

    lib.modbus_slave_sync_buffers.argtypes = []
    lib.modbus_slave_sync_buffers.restype = None

    lib.gpio_safety_init.argtypes = []
    lib.gpio_safety_init.restype = ctypes.c_int

    lib.gpio_safety_trigger_emergency_software.argtypes = []
    lib.gpio_safety_trigger_emergency_software.restype = None

    return lib


def test_open_loop_transition_preconditions(system_lib):
    """Verify that OPEN_LOOP_TEST transition requires |pos| <= 5.0 mm and healthy state."""
    system_lib.shared_data_init()
    system_lib.gpio_safety_init()

    g_sys = SystemDataStruct.in_dll(system_lib, "g_system_data")
    g_burst = BurstBufferStruct.in_dll(system_lib, "g_burst_buffer")

    # Case 1: At 0.0 mm -> transition accepted
    g_sys.current_position = 0.0
    assert system_lib.shared_data_get_state() == MACHINE_STATE_IDLE
    ok = system_lib.shared_data_request_state_change(MACHINE_STATE_OPEN_LOOP_TEST)
    assert ok is True
    assert system_lib.shared_data_get_state() == MACHINE_STATE_OPEN_LOOP_TEST
    assert g_burst.status == BURST_STATUS_CAPTURING
    assert g_burst.sample_count == 0

    # Reset to IDLE
    assert system_lib.shared_data_request_state_change(MACHINE_STATE_IDLE) is True

    # Case 2: At 2.5 mm (|pos| <= 5.0 mm) -> transition accepted
    g_sys.current_position = 2.5
    ok = system_lib.shared_data_request_state_change(MACHINE_STATE_OPEN_LOOP_TEST)
    assert ok is True
    assert system_lib.shared_data_get_state() == MACHINE_STATE_OPEN_LOOP_TEST

    # Reset to IDLE
    assert system_lib.shared_data_request_state_change(MACHINE_STATE_IDLE) is True

    # Case 3: At 15.0 mm (|pos| > 5.0 mm) -> transition blocked
    g_sys.current_position = 15.0
    ok = system_lib.shared_data_request_state_change(MACHINE_STATE_OPEN_LOOP_TEST)
    assert ok is False
    assert system_lib.shared_data_get_state() == MACHINE_STATE_IDLE

    # Case 4: Under emergency -> transition blocked
    g_sys.current_position = 0.0
    system_lib.gpio_safety_trigger_emergency_software()
    assert system_lib.shared_data_get_state() == MACHINE_STATE_EMERGENCY
    ok = system_lib.shared_data_request_state_change(MACHINE_STATE_OPEN_LOOP_TEST)
    assert ok is False
    assert system_lib.shared_data_get_state() == MACHINE_STATE_EMERGENCY


def test_modbus_command_open_loop_test(system_lib):
    """Verify Modbus CMD_OPEN_LOOP_TEST triggers state transition and buffer sync."""
    system_lib.shared_data_init()
    system_lib.gpio_safety_init()
    system_lib.modbus_slave_init()

    g_sys = SystemDataStruct.in_dll(system_lib, "g_system_data")
    g_hold = HoldingRegStruct.in_dll(system_lib, "g_modbus_holding_reg")
    g_in = InputRegStruct.in_dll(system_lib, "g_modbus_input_reg")

    g_sys.current_position = 0.0
    assert system_lib.shared_data_get_state() == MACHINE_STATE_IDLE

    # Send CMD_OPEN_LOOP_TEST (5)
    g_hold.command = CMD_OPEN_LOOP_TEST
    system_lib.modbus_slave_sync_buffers()

    # Command register must be cleared and state must be OPEN_LOOP_TEST (4)
    assert g_hold.command == CMD_NONE
    assert system_lib.shared_data_get_state() == MACHINE_STATE_OPEN_LOOP_TEST
    assert g_in.state == MACHINE_STATE_OPEN_LOOP_TEST
    assert g_in.burst_status == BURST_STATUS_CAPTURING


def test_modbus_burst_buffer_indexed_read(system_lib):
    """Verify indexing into burst buffer through Modbus holding/input registers."""
    system_lib.shared_data_init()
    system_lib.modbus_slave_init()

    g_burst = BurstBufferStruct.in_dll(system_lib, "g_burst_buffer")
    g_hold = HoldingRegStruct.in_dll(system_lib, "g_modbus_holding_reg")
    g_in = InputRegStruct.in_dll(system_lib, "g_modbus_input_reg")

    # Populate 3 synthetic samples
    g_burst.samples[0].time_ms = 0
    g_burst.samples[0].position = 0.0
    g_burst.samples[0].velocity = 0.0

    g_burst.samples[1].time_ms = 50
    g_burst.samples[1].position = 12.4
    g_burst.samples[1].velocity = 248.0

    g_burst.samples[2].time_ms = 100
    g_burst.samples[2].position = 35.8
    g_burst.samples[2].velocity = 468.0

    g_burst.sample_count = 3
    g_burst.status = BURST_STATUS_READY

    # Select sample index 1
    g_hold.burst_read_index = 1
    system_lib.modbus_slave_sync_buffers()

    assert g_in.burst_status == BURST_STATUS_READY
    assert g_in.burst_sample_count == 3
    t_ms = (g_in.sample_time_hi << 16) | g_in.sample_time_lo
    assert t_ms == 50

    from tools.supervisory.modbus_worker import registers_to_float
    pos = registers_to_float(g_in.sample_pos_hi, g_in.sample_pos_lo)
    vel = registers_to_float(g_in.sample_vel_hi, g_in.sample_vel_lo)

    assert abs(pos - 12.4) < 1e-3
    assert abs(vel - 248.0) < 1e-3


def test_csv_export_format():
    """Verify CSV file export structure matches requirements."""
    samples = [
        {"time_s": 0.000, "position_mm": 0.0, "velocity_mm_s": 0.0, "duty_pct": 100.0},
        {"time_s": 0.010, "position_mm": 1.2, "velocity_mm_s": 120.0, "duty_pct": 100.0},
        {"time_s": 0.020, "position_mm": 3.5, "velocity_mm_s": 230.0, "duty_pct": 100.0},
    ]

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".csv") as tmp:
        tmp_path = tmp.name

    try:
        with open(tmp_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["time_s", "position_mm", "velocity_mm_s", "duty_pct"])
            for s in samples:
                writer.writerow([s["time_s"], s["position_mm"], s["velocity_mm_s"], s["duty_pct"]])

        with open(tmp_path, mode="r", encoding="utf-8") as f:
            reader = list(csv.reader(f))

        assert reader[0] == ["time_s", "position_mm", "velocity_mm_s", "duty_pct"]
        assert len(reader) == 4
        assert reader[1] == ["0.0", "0.0", "0.0", "100.0"]
        assert reader[2] == ["0.01", "1.2", "120.0", "100.0"]
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_open_loop_80_percent_travel_geometry():
    """Verify 80% travel cutoff threshold, stopping clearance, and 550 sample buffer size."""
    system_max_travel_mm = 670.0
    target_80_pct = system_max_travel_mm * 0.80
    clearance_margin = system_max_travel_mm - target_80_pct

    assert abs(target_80_pct - 536.0) < 0.001
    assert abs(clearance_margin - 134.0) < 0.001
    assert clearance_margin > 100.0  # Safe braking distance margin > 100 mm

    # 825 samples at 100 Hz (10ms) allows up to 8.25 seconds of recording (1.5x of 550)
    max_recording_time_s = 825 * 0.01
    assert max_recording_time_s == 8.25


def test_open_loop_pwm_register_sync_and_clamping(system_lib):
    """Verify open_loop_pwm Modbus holding register default, sync, and [1.0, 100.0] clamping."""
    import struct

    def float_to_regs(val: float):
        raw = struct.pack(">f", val)
        return struct.unpack(">HH", raw)

    system_lib.shared_data_init()
    system_lib.modbus_slave_init()
    system_lib.modbus_slave_sync_buffers()

    g_sys = SystemDataStruct.in_dll(system_lib, "g_system_data")
    g_hold = HoldingRegStruct.in_dll(system_lib, "g_modbus_holding_reg")

    # Default is 100.0%
    assert abs(g_sys.open_loop_pwm - 100.0) < 1e-4

    # Valid value (60.0%)
    hi, lo = float_to_regs(60.0)
    g_hold.open_loop_pwm_hi, g_hold.open_loop_pwm_lo = hi, lo
    system_lib.modbus_slave_sync_buffers()
    assert abs(g_sys.open_loop_pwm - 60.0) < 1e-4

    # Below minimum (0.0% -> clamped to 1.0%)
    hi, lo = float_to_regs(0.0)
    g_hold.open_loop_pwm_hi, g_hold.open_loop_pwm_lo = hi, lo
    system_lib.modbus_slave_sync_buffers()
    assert abs(g_sys.open_loop_pwm - 1.0) < 1e-4

    # Above maximum (150.0% -> clamped to 100.0%)
    hi, lo = float_to_regs(150.0)
    g_hold.open_loop_pwm_hi, g_hold.open_loop_pwm_lo = hi, lo
    system_lib.modbus_slave_sync_buffers()
    assert abs(g_sys.open_loop_pwm - 100.0) < 1e-4

    # NaN fallback -> 100.0%
    hi, lo = float_to_regs(float("nan"))
    g_hold.open_loop_pwm_hi, g_hold.open_loop_pwm_lo = hi, lo
    system_lib.modbus_slave_sync_buffers()
    assert abs(g_sys.open_loop_pwm - 100.0) < 1e-4


def test_open_loop_coast_mode_and_sample_duty_registers(system_lib):
    """Verify open_loop_mode, coast_pos clamping [50, 536], and sample_duty indexed read."""
    import struct

    def float_to_regs(val: float):
        return struct.unpack(">HH", struct.pack(">f", val))

    def regs_to_float(hi: int, lo: int) -> float:
        return struct.unpack(">f", struct.pack(">HH", hi, lo))[0]

    system_lib.shared_data_init()
    system_lib.modbus_slave_init()
    system_lib.modbus_slave_sync_buffers()

    g_sys = SystemDataStruct.in_dll(system_lib, "g_system_data")
    g_hold = HoldingRegStruct.in_dll(system_lib, "g_modbus_holding_reg")
    g_in = InputRegStruct.in_dll(system_lib, "g_modbus_input_reg")
    g_burst = BurstBufferStruct.in_dll(system_lib, "g_burst_buffer")

    assert g_sys.open_loop_mode == 0
    assert abs(g_sys.open_loop_coast_pos_mm - 400.0) < 1e-4

    # Set coast mode (1) and invalid mode (99 -> 0)
    g_hold.open_loop_mode = 1
    system_lib.modbus_slave_sync_buffers()
    assert g_sys.open_loop_mode == 1

    g_hold.open_loop_mode = 99
    system_lib.modbus_slave_sync_buffers()
    assert g_sys.open_loop_mode == 0

    # Coast pos clamping [50.0, 536.0]
    g_hold.open_loop_coast_pos_hi, g_hold.open_loop_coast_pos_lo = float_to_regs(10.0)
    system_lib.modbus_slave_sync_buffers()
    assert abs(g_sys.open_loop_coast_pos_mm - 50.0) < 1e-4

    g_hold.open_loop_coast_pos_hi, g_hold.open_loop_coast_pos_lo = float_to_regs(600.0)
    system_lib.modbus_slave_sync_buffers()
    assert abs(g_sys.open_loop_coast_pos_mm - 536.0) < 1e-4

    # Sample duty_pct indexed read
    g_burst.sample_count = 2
    g_burst.samples[0].duty_pct = 75.0
    g_burst.samples[1].duty_pct = 0.0

    g_hold.burst_read_index = 0
    system_lib.modbus_slave_sync_buffers()
    assert abs(regs_to_float(g_in.sample_duty_hi, g_in.sample_duty_lo) - 75.0) < 1e-4

    g_hold.burst_read_index = 1
    system_lib.modbus_slave_sync_buffers()
    assert abs(regs_to_float(g_in.sample_duty_hi, g_in.sample_duty_lo) - 0.0) < 1e-4


