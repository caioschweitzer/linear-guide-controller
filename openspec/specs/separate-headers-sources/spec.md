# separate-headers-sources Specification

## Purpose
TBD - created by archiving change separate-headers-sources. Update Purpose after archive.
## Requirements
### Requirement: Modular Directory Organization
The system firmware build layout SHALL organize public interface headers into `main/include/` and module source implementations into `main/src/`.

#### Scenario: Header and Source Separation Verification
- **WHEN** the firmware project directory structure is inspected
- **THEN** all `.h` headers reside inside `main/include/` and all `.c` sources reside inside `main/src/`

### Requirement: Build System Path Resolution
The ESP-IDF build system (`CMakeLists.txt`) and host GCC test scripts SHALL successfully resolve header includes from `main/include/` and source compilation from `main/src/`.

#### Scenario: Automated Compilation and Flash
- **WHEN** `idf.py build` and `pytest tests/` are executed
- **THEN** compilation succeeds without header resolution errors and all host integration tests pass

