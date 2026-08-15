## 1. Directory Reorganization & CMake Configuration

- [x] 1.1 Create `main/include/` and `main/src/` directories and move `.h` headers into `main/include/` and `.c` sources into `main/src/`
- [x] 1.2 Update `main/CMakeLists.txt` to register sources under `src/` and set `INCLUDE_DIRS` to `"include"`

## 2. Host Test Framework & Firmware Validation

- [x] 2.1 Update `tests/test_system_integration.py` to compile source files from `main/src/` with header include flag `-Imain/include`
- [x] 2.2 Rebuild `libsystem_integration.so` and verify that all 32 pytest integration test cases pass
- [x] 2.3 Compile firmware via `idf.py build` and flash connected ESP32-S3 via `idf.py flash`
