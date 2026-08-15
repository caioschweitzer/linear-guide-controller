import os
import ctypes
import pytest


class EncoderDriverStruct(ctypes.Structure):
    _fields_ = [
        ("accumulated_overflows", ctypes.c_int32),
        ("is_initialized", ctypes.c_bool),
        ("simulated_raw_count", ctypes.c_int32),
    ]


def load_encoder_lib():
    so_path = os.path.join(os.path.dirname(__file__), "libencoder_pcnt.so")
    if not os.path.exists(so_path):
        import subprocess
        src = os.path.join(os.path.dirname(__file__), "..", "main", "encoder_pcnt.c")
        inc = os.path.join(os.path.dirname(__file__), "..", "main")
        subprocess.run(["gcc", "-shared", "-fPIC", "-O2", "-DHOST_TEST", src, "-o", so_path, f"-I{inc}"], check=True)

    lib = ctypes.CDLL(so_path)

    lib.encoder_init.argtypes = [ctypes.POINTER(EncoderDriverStruct), ctypes.c_void_p]
    lib.encoder_init.restype = ctypes.c_int

    lib.encoder_deinit.argtypes = [ctypes.POINTER(EncoderDriverStruct)]
    lib.encoder_deinit.restype = ctypes.c_int

    lib.encoder_get_count.argtypes = [ctypes.POINTER(EncoderDriverStruct), ctypes.POINTER(ctypes.c_int32)]
    lib.encoder_get_count.restype = ctypes.c_int

    lib.encoder_clear_count.argtypes = [ctypes.POINTER(EncoderDriverStruct)]
    lib.encoder_clear_count.restype = ctypes.c_int

    lib.encoder_sim_add_count.argtypes = [ctypes.POINTER(EncoderDriverStruct), ctypes.c_int32]
    lib.encoder_sim_add_count.restype = None

    return lib


@pytest.fixture(scope="module")
def encoder_lib():
    return load_encoder_lib()


@pytest.fixture
def encoder_ctx(encoder_lib):
    ctx = EncoderDriverStruct()
    res = encoder_lib.encoder_init(ctypes.byref(ctx), None)
    assert res == 0
    yield ctx
    encoder_lib.encoder_deinit(ctypes.byref(ctx))


def test_encoder_initialization_and_zero_reading(encoder_lib, encoder_ctx):
    # Scenario 1: Initial reading must be zero
    count = ctypes.c_int32()
    res = encoder_lib.encoder_get_count(ctypes.byref(encoder_ctx), ctypes.byref(count))
    assert res == 0
    assert count.value == 0


def test_quadrature_forward_and_reverse_counting(encoder_lib, encoder_ctx):
    # Scenario 2: Forward 1000 counts (1 revolution)
    encoder_lib.encoder_sim_add_count(ctypes.byref(encoder_ctx), 1000)
    count = ctypes.c_int32()
    encoder_lib.encoder_get_count(ctypes.byref(encoder_ctx), ctypes.byref(count))
    assert count.value == 1000

    # Reverse 500 counts
    encoder_lib.encoder_sim_add_count(ctypes.byref(encoder_ctx), -500)
    encoder_lib.encoder_get_count(ctypes.byref(encoder_ctx), ctypes.byref(count))
    assert count.value == 500


def test_16bit_hardware_overflow_accumulation(encoder_lib, encoder_ctx):
    # Scenario 3: Exceed 30,000 counts (16-bit watch point limit)
    count = ctypes.c_int32()

    # Add 35,000 counts -> should trigger 1 overflow (+30,000) and remainder 5,000
    encoder_lib.encoder_sim_add_count(ctypes.byref(encoder_ctx), 35000)
    encoder_lib.encoder_get_count(ctypes.byref(encoder_ctx), ctypes.byref(count))
    assert count.value == 35000
    assert encoder_ctx.accumulated_overflows == 1

    # Add 100,000 more counts -> total 135,000 counts (4 overflows + remainder)
    encoder_lib.encoder_sim_add_count(ctypes.byref(encoder_ctx), 100000)
    encoder_lib.encoder_get_count(ctypes.byref(encoder_ctx), ctypes.byref(count))
    assert count.value == 135000
    assert encoder_ctx.accumulated_overflows == 4

    # Reverse 150,000 counts -> total -15,000 counts
    encoder_lib.encoder_sim_add_count(ctypes.byref(encoder_ctx), -150000)
    encoder_lib.encoder_get_count(ctypes.byref(encoder_ctx), ctypes.byref(count))
    assert count.value == -15000


def test_atomic_zero_reset(encoder_lib, encoder_ctx):
    # Scenario 4: High count -> clear_count -> returns 0
    count = ctypes.c_int32()
    encoder_lib.encoder_sim_add_count(ctypes.byref(encoder_ctx), 125000)

    encoder_lib.encoder_get_count(ctypes.byref(encoder_ctx), ctypes.byref(count))
    assert count.value == 125000

    # Clear count
    res = encoder_lib.encoder_clear_count(ctypes.byref(encoder_ctx))
    assert res == 0

    encoder_lib.encoder_get_count(ctypes.byref(encoder_ctx), ctypes.byref(count))
    assert count.value == 0
    assert encoder_ctx.accumulated_overflows == 0
    assert encoder_ctx.simulated_raw_count == 0
