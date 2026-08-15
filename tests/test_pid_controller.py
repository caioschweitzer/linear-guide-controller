import os
import math
import ctypes
import pytest


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


def load_pid_lib():
    so_path = os.path.join(os.path.dirname(__file__), "libpid_controller.so")
    if not os.path.exists(so_path):
        import subprocess
        src = os.path.join(os.path.dirname(__file__), "..", "main", "pid_controller.c")
        inc = os.path.join(os.path.dirname(__file__), "..", "main")
        subprocess.run(["gcc", "-shared", "-fPIC", "-O2", src, "-o", so_path, f"-I{inc}"], check=True)

    lib = ctypes.CDLL(so_path)

    lib.pid_init.argtypes = [ctypes.POINTER(PIDControllerStruct), ctypes.POINTER(PIDConfigStruct)]
    lib.pid_init.restype = None

    lib.pid_reset.argtypes = [ctypes.POINTER(PIDControllerStruct)]
    lib.pid_reset.restype = None

    lib.pid_set_gains.argtypes = [ctypes.POINTER(PIDControllerStruct), ctypes.c_float, ctypes.c_float, ctypes.c_float]
    lib.pid_set_gains.restype = None

    lib.pid_compute.argtypes = [
        ctypes.POINTER(PIDControllerStruct),
        ctypes.c_float,
        ctypes.c_float,
        ctypes.c_float,
    ]
    lib.pid_compute.restype = ctypes.c_float

    return lib


@pytest.fixture(scope="module")
def pid_lib():
    return load_pid_lib()


@pytest.fixture
def pid_ctx(pid_lib):
    ctx = PIDControllerStruct()
    pid_lib.pid_init(ctypes.byref(ctx), None)
    yield ctx
    pid_lib.pid_reset(ctypes.byref(ctx))


def test_proportional_response(pid_lib, pid_ctx):
    # Scenario 1: Kp = 2.0, Ki = 0.0, Kd = 0.0, error = 10.0 mm
    pid_lib.pid_set_gains(ctypes.byref(pid_ctx), 2.0, 0.0, 0.0)
    output = pid_lib.pid_compute(ctypes.byref(pid_ctx), 10.0, 0.0, 0.01)
    assert pytest.approx(output, 0.01) == 20.0


def test_conditional_anti_windup(pid_lib, pid_ctx):
    # Scenario 2: High Ki to force saturation, test anti-windup freezing and fast recovery
    pid_lib.pid_set_gains(ctypes.byref(pid_ctx), 2.0, 50.0, 0.0)

    # Force saturation at +100.0% for 10 iterations
    for i in range(10):
        output = pid_lib.pid_compute(ctypes.byref(pid_ctx), 10.0, 0.0, 0.1)

    # Verify output is saturated at 100.0%
    assert pytest.approx(output, 0.01) == 100.0

    # Reverse error sign (setpoint 0.0, current_pos 10.0 -> error -10.0)
    reversed_output = pid_lib.pid_compute(ctypes.byref(pid_ctx), 0.0, 10.0, 0.1)

    # Output should immediately drop below 100.0 without windup lag
    assert reversed_output < 100.0


def test_derivative_kick_avoidance(pid_lib, pid_ctx):
    # Scenario 3: Kd = 5.0, Kp = 0.0, Ki = 0.0
    pid_lib.pid_set_gains(ctypes.byref(pid_ctx), 0.0, 0.0, 5.0)

    # First run at position 0.0
    pid_lib.pid_compute(ctypes.byref(pid_ctx), 0.0, 0.0, 0.01)

    # Step setpoint to 100.0 mm while position remains 0.0 mm
    out_step = pid_lib.pid_compute(ctypes.byref(pid_ctx), 100.0, 0.0, 0.01)

    # Derivative action MUST be 0.0 because position did not change (no derivative kick)
    assert pytest.approx(out_step, 0.001) == 0.0


def test_in_position_deadband(pid_lib, pid_ctx):
    # Scenario 4: Deadband = 0.05 mm. Setpoint 10.0, pos 9.97 (error 0.03 mm < 0.05 mm)
    pid_lib.pid_set_gains(ctypes.byref(pid_ctx), 10.0, 1.0, 0.1)
    output = pid_lib.pid_compute(ctypes.byref(pid_ctx), 10.0, 9.97, 0.01)
    assert output == 0.0


def test_numerical_guardrails(pid_lib, pid_ctx):
    # Scenario 5: dt = 0.0 (division by zero protection)
    pid_lib.pid_set_gains(ctypes.byref(pid_ctx), 2.0, 0.0, 1.0)
    output_dt_zero = pid_lib.pid_compute(ctypes.byref(pid_ctx), 10.0, 0.0, 0.0)
    assert not math.isnan(output_dt_zero)
    assert not math.isinf(output_dt_zero)

    # NaN input protection
    output_nan = pid_lib.pid_compute(ctypes.byref(pid_ctx), float("nan"), 0.0, 0.01)
    assert output_nan == 0.0

    # INF input protection
    output_inf = pid_lib.pid_compute(ctypes.byref(pid_ctx), 10.0, float("inf"), 0.01)
    assert output_inf == 0.0
