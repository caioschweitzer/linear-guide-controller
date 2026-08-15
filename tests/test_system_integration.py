import os
import ctypes
import pytest

# System state constants
MACHINE_STATE_IDLE = 0
MACHINE_STATE_MOVING = 1
MACHINE_STATE_EMERGENCY = 2

# Physical Constants
PULSES_PER_REV = 1000
MM_PER_REV = 42.4115
SYSTEM_MAX_TRAVEL_MM = 424.115


class SystemDataStruct(ctypes.Structure):
    _fields_ = [
        ("position_setpoint", ctypes.c_float),
        ("current_position", ctypes.c_float),
        ("current_velocity", ctypes.c_float),
        ("kp", ctypes.c_float),
        ("ki", ctypes.c_float),
        ("kd", ctypes.c_float),
        ("machine_state", ctypes.c_uint16),
    ]


class KinematicsStruct(ctypes.Structure):
    _fields_ = [
        ("zero_offset", ctypes.c_int32),
        ("direction", ctypes.c_int8),
        ("alpha", ctypes.c_float),
        ("is_initialized", ctypes.c_bool),
        ("last_position", ctypes.c_float),
        ("last_velocity", ctypes.c_float),
        ("filtered_velocity", ctypes.c_float),
    ]


class PIDConfigStruct(ctypes.Structure):
    _fields_ = [
        ("kp", ctypes.c_float),
        ("ki", ctypes.c_float),
        ("kd", ctypes.c_float),
        ("output_min", ctypes.c_float),
        ("output_max", ctypes.c_float),
        ("deadband_mm", ctypes.c_float),
        ("alpha_d", ctypes.c_float),
    ]


class PIDControllerStruct(ctypes.Structure):
    _fields_ = [
        ("config", PIDConfigStruct),
        ("integral_accumulator", ctypes.c_float),
        ("prev_position", ctypes.c_float),
        ("prev_derivative_filtered", ctypes.c_float),
        ("last_output", ctypes.c_float),
        ("is_first_run", ctypes.c_bool),
        ("is_initialized", ctypes.c_bool),
    ]


class EncoderDriverStruct(ctypes.Structure):
    _fields_ = [
        ("accumulated_overflows", ctypes.c_int32),
        ("is_initialized", ctypes.c_bool),
        ("simulated_raw_count", ctypes.c_int32),
    ]


class MotorDriverStruct(ctypes.Structure):
    _fields_ = [
        ("current_effort", ctypes.c_float),
        ("last_direction", ctypes.c_int),
        ("is_initialized", ctypes.c_bool),
        ("sim_in1", ctypes.c_int),
        ("sim_in2", ctypes.c_int),
        ("sim_duty_percent", ctypes.c_float),
        ("sim_brake_transitions", ctypes.c_int),
    ]


def load_system_lib():
    so_path = os.path.join(os.path.dirname(__file__), "libsystem_integration.so")
    if not os.path.exists(so_path):
        import subprocess
        src_dir = os.path.join(os.path.dirname(__file__), "..", "main", "src")
        inc_dir = os.path.join(os.path.dirname(__file__), "..", "main", "include")
        c_files = [
            os.path.join(src_dir, f) for f in [
                "shared_data.c", "gpio_safety.c", "linear_kinematics.c",
                "encoder_pcnt.c", "motor_mcpwm.c", "pid_controller.c",
                "ihm_display.c", "modbus_slave.c"
            ]
        ]
        cmd = ["gcc", "-shared", "-fPIC", "-O2", "-DHOST_TEST"] + c_files + ["-o", so_path, f"-I{inc_dir}"]
        subprocess.run(cmd, check=True)

    lib = ctypes.CDLL(so_path)

    # Function Signatures
    lib.shared_data_init.argtypes = []
    lib.shared_data_init.restype = None

    lib.shared_data_get_state.argtypes = []
    lib.shared_data_get_state.restype = ctypes.c_int

    lib.shared_data_request_state_change.argtypes = [ctypes.c_int]
    lib.shared_data_request_state_change.restype = ctypes.c_bool

    lib.gpio_safety_init.argtypes = []
    lib.gpio_safety_init.restype = ctypes.c_int

    lib.gpio_safety_trigger_emergency_software.argtypes = []
    lib.gpio_safety_trigger_emergency_software.restype = None

    lib.gpio_safety_is_emergency_active.argtypes = []
    lib.gpio_safety_is_emergency_active.restype = ctypes.c_bool

    lib.kinematics_init.argtypes = [ctypes.POINTER(KinematicsStruct), ctypes.c_int32, ctypes.c_int8, ctypes.c_float]
    lib.kinematics_init.restype = None

    lib.kinematics_update.argtypes = [
        ctypes.POINTER(KinematicsStruct),
        ctypes.c_int32,
        ctypes.c_float,
        ctypes.POINTER(ctypes.c_float)
    ]
    lib.kinematics_update.restype = ctypes.c_float

    lib.encoder_init.argtypes = [ctypes.POINTER(EncoderDriverStruct), ctypes.c_void_p]
    lib.encoder_init.restype = ctypes.c_int

    lib.encoder_get_count.argtypes = [ctypes.POINTER(EncoderDriverStruct), ctypes.POINTER(ctypes.c_int32)]
    lib.encoder_get_count.restype = ctypes.c_int

    lib.encoder_sim_add_count.argtypes = [ctypes.POINTER(EncoderDriverStruct), ctypes.c_int32]
    lib.encoder_sim_add_count.restype = None

    lib.motor_init.argtypes = [ctypes.POINTER(MotorDriverStruct), ctypes.c_void_p]
    lib.motor_init.restype = ctypes.c_int

    lib.motor_set_effort.argtypes = [ctypes.POINTER(MotorDriverStruct), ctypes.c_float]
    lib.motor_set_effort.restype = ctypes.c_int

    lib.motor_brake.argtypes = [ctypes.POINTER(MotorDriverStruct)]
    lib.motor_brake.restype = ctypes.c_int

    lib.pid_init.argtypes = [ctypes.POINTER(PIDControllerStruct), ctypes.c_void_p]
    lib.pid_init.restype = None

    lib.pid_compute.argtypes = [
        ctypes.POINTER(PIDControllerStruct),
        ctypes.c_float,
        ctypes.c_float,
        ctypes.c_float
    ]
    lib.pid_compute.restype = ctypes.c_float

    lib.pid_reset.argtypes = [ctypes.POINTER(PIDControllerStruct)]
    lib.pid_reset.restype = None

    return lib


@pytest.fixture(scope="module")
def sys_lib():
    return load_system_lib()


@pytest.fixture
def pid_ctrl(sys_lib):
    pid = PIDControllerStruct()
    sys_lib.pid_init(ctypes.byref(pid), None)
    return pid


@pytest.fixture
def kin_ctx(sys_lib):
    kin = KinematicsStruct()
    sys_lib.kinematics_init(ctypes.byref(kin), 0, 1, 0.2)
    return kin


@pytest.fixture
def enc_drv(sys_lib):
    enc = EncoderDriverStruct()
    sys_lib.encoder_init(ctypes.byref(enc), None)
    return enc


@pytest.fixture
def mtr_drv(sys_lib):
    mtr = MotorDriverStruct()
    sys_lib.motor_init(ctypes.byref(mtr), None)
    return mtr


def test_system_boot_sequence(sys_lib, kin_ctx, enc_drv, mtr_drv):
    # Initialize all firmware subsystems
    sys_lib.shared_data_init()
    sys_lib.gpio_safety_init()

    # Initial machine state MUST be IDLE
    assert sys_lib.shared_data_get_state() == MACHINE_STATE_IDLE

    # Motor duty MUST be 0.0%
    assert mtr_drv.sim_duty_percent == 0.0


def test_closed_loop_moving_state(sys_lib, pid_ctrl, kin_ctx, enc_drv, mtr_drv):
    sys_lib.shared_data_init()
    sys_lib.gpio_safety_init()

    # Transition to MOVING state
    success = sys_lib.shared_data_request_state_change(MACHINE_STATE_MOVING)
    assert success is True
    assert sys_lib.shared_data_get_state() == MACHINE_STATE_MOVING

    # Set setpoint to 100.0 mm
    setpoint = 100.0

    # Simulate 10 control loop iterations (100 ms virtual time)
    for _ in range(10):
        raw_count = ctypes.c_int32(0)
        sys_lib.encoder_get_count(ctypes.byref(enc_drv), ctypes.byref(raw_count))

        vel_out = ctypes.c_float(0.0)
        pos_mm = sys_lib.kinematics_update(ctypes.byref(kin_ctx), raw_count.value, 0.01, ctypes.byref(vel_out))

        duty_out = sys_lib.pid_compute(ctypes.byref(pid_ctrl), setpoint, pos_mm, 0.01)
        sys_lib.motor_set_effort(ctypes.byref(mtr_drv), duty_out)

    # Duty cycle should be positive & bounded to 100%
    assert mtr_drv.sim_duty_percent > 0.0
    assert mtr_drv.sim_duty_percent <= 100.0


def test_emergency_estop_interruption(sys_lib, pid_ctrl, kin_ctx, enc_drv, mtr_drv):
    sys_lib.shared_data_init()
    sys_lib.gpio_safety_init()

    # Move to MOVING state
    sys_lib.shared_data_request_state_change(MACHINE_STATE_MOVING)
    assert sys_lib.shared_data_get_state() == MACHINE_STATE_MOVING

    # Compute positive motor effort
    duty_out = sys_lib.pid_compute(ctypes.byref(pid_ctrl), 100.0, 0.0, 0.01)
    sys_lib.motor_set_effort(ctypes.byref(mtr_drv), duty_out)

    # Trigger software Emergency interrupt
    sys_lib.gpio_safety_trigger_emergency_software()

    # State MUST be EMERGENCY
    assert sys_lib.shared_data_get_state() == MACHINE_STATE_EMERGENCY
    assert sys_lib.gpio_safety_is_emergency_active() is True

    # Simulate Emergency handling in control loop cycle
    sys_lib.pid_reset(ctypes.byref(pid_ctrl))
    sys_lib.motor_brake(ctypes.byref(mtr_drv))
    sys_lib.motor_set_effort(ctypes.byref(mtr_drv), 0.0)

    # Verify motor duty cycle dropped immediately to 0.0%
    assert mtr_drv.sim_duty_percent == 0.0

    # Attempts to transition back to MOVING without reset MUST be rejected
    rejected = sys_lib.shared_data_request_state_change(MACHINE_STATE_MOVING)
    assert rejected is False
    assert sys_lib.shared_data_get_state() == MACHINE_STATE_EMERGENCY
