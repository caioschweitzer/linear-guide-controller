import os
import math
import ctypes
import pytest


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


def load_motor_lib():
    so_path = os.path.join(os.path.dirname(__file__), "libmotor_mcpwm.so")
    if not os.path.exists(so_path):
        import subprocess
        src = os.path.join(os.path.dirname(__file__), "..", "main", "motor_mcpwm.c")
        inc = os.path.join(os.path.dirname(__file__), "..", "main")
        subprocess.run(["gcc", "-shared", "-fPIC", "-O2", "-DHOST_TEST", src, "-o", so_path, f"-I{inc}"], check=True)

    lib = ctypes.CDLL(so_path)

    lib.motor_init.argtypes = [ctypes.POINTER(MotorDriverStruct), ctypes.c_void_p]
    lib.motor_init.restype = ctypes.c_int

    lib.motor_deinit.argtypes = [ctypes.POINTER(MotorDriverStruct)]
    lib.motor_deinit.restype = ctypes.c_int

    lib.motor_set_effort.argtypes = [ctypes.POINTER(MotorDriverStruct), ctypes.c_float]
    lib.motor_set_effort.restype = ctypes.c_int

    lib.motor_brake.argtypes = [ctypes.POINTER(MotorDriverStruct)]
    lib.motor_brake.restype = ctypes.c_int

    return lib


@pytest.fixture(scope="module")
def motor_lib():
    return load_motor_lib()


@pytest.fixture
def motor_ctx(motor_lib):
    ctx = MotorDriverStruct()
    res = motor_lib.motor_init(ctypes.byref(ctx), None)
    assert res == 0
    yield ctx
    motor_lib.motor_deinit(ctypes.byref(ctx))


def test_forward_effort(motor_lib, motor_ctx):
    # Scenario 1: Forward effort (+50.0%)
    res = motor_lib.motor_set_effort(ctypes.byref(motor_ctx), 50.0)
    assert res == 0
    assert motor_ctx.sim_in1 == 1
    assert motor_ctx.sim_in2 == 0
    assert pytest.approx(motor_ctx.sim_duty_percent, 0.01) == 50.0
    assert motor_ctx.last_direction == 1


def test_reverse_effort(motor_lib, motor_ctx):
    # Scenario 2: Reverse effort (-50.0%)
    res = motor_lib.motor_set_effort(ctypes.byref(motor_ctx), -50.0)
    assert res == 0
    assert motor_ctx.sim_in1 == 0
    assert motor_ctx.sim_in2 == 1
    assert pytest.approx(motor_ctx.sim_duty_percent, 0.01) == 50.0
    assert motor_ctx.last_direction == -1


def test_passive_brake_and_zero_stop(motor_lib, motor_ctx):
    # Scenario 3: Effort = 0.0% (passive brake)
    res = motor_lib.motor_set_effort(ctypes.byref(motor_ctx), 0.0)
    assert res == 0
    assert motor_ctx.sim_in1 == 0
    assert motor_ctx.sim_in2 == 0
    assert pytest.approx(motor_ctx.sim_duty_percent, 0.01) == 0.0
    assert motor_ctx.last_direction == 0


def test_effort_clamping_and_failsafe(motor_lib, motor_ctx):
    # Scenario 4: Over-range effort (+150.0%) -> clamped to 100.0%
    res = motor_lib.motor_set_effort(ctypes.byref(motor_ctx), 150.0)
    assert res == 0
    assert motor_ctx.sim_in1 == 1
    assert motor_ctx.sim_in2 == 0
    assert pytest.approx(motor_ctx.sim_duty_percent, 0.01) == 100.0

    # Over-range effort (-200.0%) -> clamped to -100.0%
    res = motor_lib.motor_set_effort(ctypes.byref(motor_ctx), -200.0)
    assert res == 0
    assert motor_ctx.sim_in1 == 0
    assert motor_ctx.sim_in2 == 1
    assert pytest.approx(motor_ctx.sim_duty_percent, 0.01) == 100.0

    # NaN fail-safe -> forces brake
    res = motor_lib.motor_set_effort(ctypes.byref(motor_ctx), float("nan"))
    assert res == 0
    assert motor_ctx.sim_in1 == 0
    assert motor_ctx.sim_in2 == 0
    assert pytest.approx(motor_ctx.sim_duty_percent, 0.01) == 0.0

    # INF fail-safe -> forces brake
    res = motor_lib.motor_set_effort(ctypes.byref(motor_ctx), float("inf"))
    assert res == 0
    assert motor_ctx.sim_in1 == 0
    assert motor_ctx.sim_in2 == 0
    assert pytest.approx(motor_ctx.sim_duty_percent, 0.01) == 0.0


def test_direction_reversal_brake_transition(motor_lib, motor_ctx):
    # Scenario 5: Forward +80% -> Reverse -80% triggers short brake phase
    motor_lib.motor_set_effort(ctypes.byref(motor_ctx), 80.0)
    assert motor_ctx.last_direction == 1
    brake_count_before = motor_ctx.sim_brake_transitions

    # Reverse direction
    motor_lib.motor_set_effort(ctypes.byref(motor_ctx), -80.0)
    assert motor_ctx.sim_brake_transitions == brake_count_before + 1
    assert motor_ctx.sim_in1 == 0
    assert motor_ctx.sim_in2 == 1
    assert pytest.approx(motor_ctx.sim_duty_percent, 0.01) == 80.0
    assert motor_ctx.last_direction == -1
