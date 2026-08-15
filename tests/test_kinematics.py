import os
import ctypes
import pytest

# Physical system constants matching linear_kinematics.h
MM_PER_COUNT = 0.0424115
DEFAULT_EMA_ALPHA = 0.2
MIN_DT_SECONDS = 0.0001


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


def load_kinematics_lib():
    so_path = os.path.join(os.path.dirname(__file__), "libkinematics.so")
    if not os.path.exists(so_path):
        import subprocess
        src = os.path.join(os.path.dirname(__file__), "..", "main", "linear_kinematics.c")
        inc = os.path.join(os.path.dirname(__file__), "..", "main")
        subprocess.run(["gcc", "-shared", "-fPIC", "-O2", src, "-o", so_path, "-lm", f"-I{inc}"], check=True)

    lib = ctypes.CDLL(so_path)

    lib.kinematics_init.argtypes = [ctypes.POINTER(KinematicsStruct), ctypes.c_int32, ctypes.c_int8, ctypes.c_float]
    lib.kinematics_init.restype = None

    lib.kinematics_reset.argtypes = [ctypes.POINTER(KinematicsStruct)]
    lib.kinematics_reset.restype = None

    lib.kinematics_set_zero_offset.argtypes = [ctypes.POINTER(KinematicsStruct), ctypes.c_int32]
    lib.kinematics_set_zero_offset.restype = None

    lib.kinematics_set_direction.argtypes = [ctypes.POINTER(KinematicsStruct), ctypes.c_int8]
    lib.kinematics_set_direction.restype = None

    lib.kinematics_calculate_position.argtypes = [ctypes.POINTER(KinematicsStruct), ctypes.c_int32]
    lib.kinematics_calculate_position.restype = ctypes.c_float

    lib.kinematics_calculate_velocity.argtypes = [ctypes.POINTER(KinematicsStruct), ctypes.c_float, ctypes.c_float]
    lib.kinematics_calculate_velocity.restype = ctypes.c_float

    lib.kinematics_update.argtypes = [ctypes.POINTER(KinematicsStruct), ctypes.c_int32, ctypes.c_float, ctypes.POINTER(ctypes.c_float)]
    lib.kinematics_update.restype = ctypes.c_float

    lib.kinematics_to_modbus_i16.argtypes = [ctypes.c_float, ctypes.c_float]
    lib.kinematics_to_modbus_i16.restype = ctypes.c_int16

    lib.kinematics_to_modbus_i32.argtypes = [ctypes.c_float, ctypes.c_float]
    lib.kinematics_to_modbus_i32.restype = ctypes.c_int32

    lib.kinematics_modbus_i16_to_float.argtypes = [ctypes.c_int16, ctypes.c_float]
    lib.kinematics_modbus_i16_to_float.restype = ctypes.c_float

    return lib


@pytest.fixture(scope="module")
def kin_lib():
    return load_kinematics_lib()


@pytest.fixture
def kin_ctx(kin_lib):
    ctx = KinematicsStruct()
    kin_lib.kinematics_init(ctypes.byref(ctx), 0, 1, 0.2)
    return ctx


def test_absolute_position_calculation_and_calibration(kin_lib, kin_ctx):
    # Scenario 1: Standard position calculation without offset (1000 counts -> 42.4115 mm)
    pos = kin_lib.kinematics_calculate_position(ctypes.byref(kin_ctx), 1000)
    assert pos == pytest.approx(42.4115, rel=1e-5)

    # Calibrated position with zero offset
    kin_lib.kinematics_set_zero_offset(ctypes.byref(kin_ctx), 100)
    pos_offset = kin_lib.kinematics_calculate_position(ctypes.byref(kin_ctx), 1100)
    assert pos_offset == pytest.approx(42.4115, rel=1e-5)

    # Inverted direction (-1)
    kin_lib.kinematics_set_direction(ctypes.byref(kin_ctx), -1)
    pos_inv = kin_lib.kinematics_calculate_position(ctypes.byref(kin_ctx), 1100)
    assert pos_inv == pytest.approx(-42.4115, rel=1e-5)


def test_dt_guardrail_and_startup_spike_prevention(kin_lib, kin_ctx):
    # Scenario 2: Startup Spike Prevention
    initial_pos = kin_lib.kinematics_calculate_position(ctypes.byref(kin_ctx), 10000)
    v_start = kin_lib.kinematics_calculate_velocity(ctypes.byref(kin_ctx), initial_pos, 0.1)
    assert v_start == pytest.approx(0.0)

    # Normal step velocity
    v_normal = kin_lib.kinematics_calculate_velocity(ctypes.byref(kin_ctx), initial_pos + 10.0, 0.1)
    assert v_normal > 0.0

    # Guardrail against dt = 0.0 s
    v_zero_dt = kin_lib.kinematics_calculate_velocity(ctypes.byref(kin_ctx), initial_pos + 20.0, 0.0)
    assert v_zero_dt == pytest.approx(v_normal)
    assert not (v_zero_dt != v_zero_dt)  # Not NaN
    assert abs(v_zero_dt) < 1e6  # Not INF


def test_differential_kinematics_and_ema_filter(kin_lib, kin_ctx):
    # Scenario 3: 500 counts change in 0.1s -> theoretical position step = 21.20575 mm
    dt = 0.1
    counts_step = 500
    alpha = 0.2

    kin_lib.kinematics_init(ctypes.byref(kin_ctx), 0, 1, alpha)

    # First cycle
    v0 = kin_lib.kinematics_calculate_velocity(ctypes.byref(kin_ctx), 0.0, dt)
    assert v0 == 0.0

    # Step changes
    current_count = 0
    velocities = []
    for step in range(1, 36):
        current_count += counts_step
        pos = kin_lib.kinematics_calculate_position(ctypes.byref(kin_ctx), current_count)
        v = kin_lib.kinematics_calculate_velocity(ctypes.byref(kin_ctx), pos, dt)
        velocities.append(v)


    target_v = (counts_step * MM_PER_COUNT) / dt  # 212.0575 mm/s

    assert velocities[0] == pytest.approx(alpha * target_v)
    assert velocities[-1] == pytest.approx(target_v, rel=1e-2)


def test_modbus_fixed_point_serialization(kin_lib):
    # Scenario 4: Fixed-point scaling
    pos = 42.4115
    reg_val = kin_lib.kinematics_to_modbus_i16(pos, 100.0)
    assert reg_val == 4241

    converted_back = kin_lib.kinematics_modbus_i16_to_float(reg_val, 100.0)
    assert converted_back == pytest.approx(42.41, rel=1e-3)

    vel = -212.0575
    reg_val_32 = kin_lib.kinematics_to_modbus_i32(vel, 100.0)
    assert reg_val_32 == -21206
