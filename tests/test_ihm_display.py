import os
import math
import ctypes
import pytest

# Machine states enum mapping from shared_data.h
MACHINE_STATE_IDLE = 0
MACHINE_STATE_MOVING = 1
MACHINE_STATE_EMERGENCY = 2


class IHMConfigStruct(ctypes.Structure):
    _fields_ = [
        ("sda_gpio", ctypes.c_int),
        ("scl_gpio", ctypes.c_int),
        ("led_gpio", ctypes.c_int),
        ("i2c_address", ctypes.c_uint8),
        ("i2c_clk_speed", ctypes.c_uint32),
    ]


class IHMDisplayStruct(ctypes.Structure):
    _fields_ = [
        ("config", IHMConfigStruct),
        ("is_connected", ctypes.c_bool),
        ("led_state", ctypes.c_bool),
        ("last_led_toggle_ms", ctypes.c_uint32),
        ("last_reconnect_attempt_ms", ctypes.c_uint32),
    ]


def load_ihm_lib():
    so_path = os.path.join(os.path.dirname(__file__), "libihm_display.so")
    if not os.path.exists(so_path):
        import subprocess
        src = os.path.join(os.path.dirname(__file__), "..", "main", "ihm_display.c")
        inc = os.path.join(os.path.dirname(__file__), "..", "main")
        subprocess.run(["gcc", "-shared", "-fPIC", "-O2", "-DHOST_TEST", src, "-o", so_path, f"-I{inc}"], check=True)

    lib = ctypes.CDLL(so_path)

    lib.ihm_init.argtypes = [ctypes.POINTER(IHMDisplayStruct), ctypes.POINTER(IHMConfigStruct)]
    lib.ihm_init.restype = None

    lib.ihm_state_to_str.argtypes = [ctypes.c_int]
    lib.ihm_state_to_str.restype = ctypes.c_char_p

    lib.ihm_format_lines.argtypes = [
        ctypes.c_float,
        ctypes.c_float,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_char_p,
    ]
    lib.ihm_format_lines.restype = None

    lib.ihm_update_led.argtypes = [ctypes.POINTER(IHMDisplayStruct), ctypes.c_int, ctypes.c_uint32]
    lib.ihm_update_led.restype = ctypes.c_bool

    lib.ihm_write_lcd.argtypes = [ctypes.POINTER(IHMDisplayStruct), ctypes.c_char_p, ctypes.c_char_p]
    lib.ihm_write_lcd.restype = ctypes.c_bool

    lib.ihm_update.argtypes = [
        ctypes.POINTER(IHMDisplayStruct),
        ctypes.c_float,
        ctypes.c_float,
        ctypes.c_int,
        ctypes.c_uint32,
    ]
    lib.ihm_update.restype = None

    return lib


@pytest.fixture(scope="module")
def ihm_lib():
    return load_ihm_lib()


@pytest.fixture
def ihm_ctx(ihm_lib):
    ctx = IHMDisplayStruct()
    ihm_lib.ihm_init(ctypes.byref(ctx), None)
    return ctx


def test_lcd_formatting_normal_and_extreme(ihm_lib):
    line1 = ctypes.create_string_buffer(17)
    line2 = ctypes.create_string_buffer(17)

    # Test Normal Formatting
    ihm_lib.ihm_format_lines(120.45, 12.5, MACHINE_STATE_MOVING, line1, line2)
    s1 = line1.value.decode("utf-8")
    s2 = line2.value.decode("utf-8")

    assert len(s1) == 16
    assert len(s2) == 16
    assert s1 == "P: 120.45 mm    "
    assert s2 == "V: 12.5 S:MOVING"

    # Test Extreme Values Formatting & Truncation
    ihm_lib.ihm_format_lines(12345.678, 999.9, MACHINE_STATE_EMERGENCY, line1, line2)
    s1_ext = line1.value.decode("utf-8")
    s2_ext = line2.value.decode("utf-8")

    assert len(s1_ext) == 16
    assert len(s2_ext) == 16
    assert s2_ext.endswith("EMERG ")

    # Test NaN / INF Guardrails
    ihm_lib.ihm_format_lines(float("nan"), float("inf"), MACHINE_STATE_IDLE, line1, line2)
    s1_nan = line1.value.decode("utf-8")
    s2_nan = line2.value.decode("utf-8")

    assert len(s1_nan) == 16
    assert len(s2_nan) == 16


def test_led_timing_and_state_transitions(ihm_lib, ihm_ctx):
    # Test IDLE state -> Solid ON
    ihm_lib.ihm_update_led(ctypes.byref(ihm_ctx), MACHINE_STATE_IDLE, 0)
    assert ihm_ctx.led_state is True

    # Test MOVING state -> 1 Hz blink (500 ms toggle interval)
    ihm_ctx.last_led_toggle_ms = 0
    ihm_ctx.led_state = True

    # Call at 250 ms -> no toggle
    ihm_lib.ihm_update_led(ctypes.byref(ihm_ctx), MACHINE_STATE_MOVING, 250)
    assert ihm_ctx.led_state is True

    # Call at 500 ms -> toggles to False
    ihm_lib.ihm_update_led(ctypes.byref(ihm_ctx), MACHINE_STATE_MOVING, 500)
    assert ihm_ctx.led_state is False

    # Call at 1000 ms -> toggles back to True
    ihm_lib.ihm_update_led(ctypes.byref(ihm_ctx), MACHINE_STATE_MOVING, 1000)
    assert ihm_ctx.led_state is True

    # Test EMERGENCY state -> 5 Hz blink (100 ms toggle interval)
    ihm_ctx.last_led_toggle_ms = 0
    ihm_ctx.led_state = False

    # Call at 50 ms -> no toggle
    ihm_lib.ihm_update_led(ctypes.byref(ihm_ctx), MACHINE_STATE_EMERGENCY, 50)
    assert ihm_ctx.led_state is False

    # Call at 100 ms -> toggles to True
    ihm_lib.ihm_update_led(ctypes.byref(ihm_ctx), MACHINE_STATE_EMERGENCY, 100)
    assert ihm_ctx.led_state is True

    # Call at 200 ms -> toggles back to False
    ihm_lib.ihm_update_led(ctypes.byref(ihm_ctx), MACHINE_STATE_EMERGENCY, 200)
    assert ihm_ctx.led_state is False


def test_ihm_update_routine(ihm_lib, ihm_ctx):
    assert ihm_ctx.is_connected is True

    # Execute periodic update
    ihm_lib.ihm_update(ctypes.byref(ihm_ctx), 50.0, 5.0, MACHINE_STATE_MOVING, 100)

    # Disconnect flag handling test
    ihm_ctx.is_connected = False
    written = ihm_lib.ihm_write_lcd(ctypes.byref(ihm_ctx), b"P:  50.00 mm   ", b"V:  5.0 S:MOVING")
    assert written is False
