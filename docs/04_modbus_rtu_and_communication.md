# Chapter 4: Industrial Modbus RTU Protocol Specification

## 1. Protocol Parameters

The controller implements a full slave stack based on the standard `esp_modbus` library:

| Parameter | Configuration |
| :--- | :--- |
| **Interface** | RS485 (UART0: `GPIO 43` TX, `GPIO 44` RX) |
| **Baud Rate** | 115,200 Baud |
| **Data Format** | 8 Data Bits, No Parity, 1 Stop Bit (8N1) |
| **Default Slave ID** | `1` (0x01) |
| **Supported Function Codes** | FC 0x01 (Read Coils), FC 0x02 (Read Discrete Inputs), FC 0x03 (Read Holding Regs), FC 0x04 (Read Input Regs), FC 0x05 (Write Single Coil), FC 0x06 (Write Single Reg), FC 0x10 (Write Multiple Regs) |

---

## 2. Complete Modbus 4-Table Register Map

### 2.1 Coils (Binary Read/Write - FC 0x01 / FC 0x05)

| Address | Name | Description | Access |
| :--- | :--- | :--- | :--- |
| `0x0000` | `Status LED` | Physical Status LED output (`GPIO 7`). Write 1 to turn ON, 0 for OFF. | R/W |
| `0x0001` | `Remote E-Stop` | Write 1 to trigger Remote Emergency Stop transition. | Write-Only |
| `0x0002` | `Remote Start` | Write 1 to trigger Remote Start transition (if safe). | Write-Only |

### 2.2 Discrete Inputs (Binary Read-Only - FC 0x02)

| Address | Name | Description | Access |
| :--- | :--- | :--- | :--- |
| `0x0000` | `E-Stop Button Pin` | Physical Emergency Button (`GPIO 12`). 0 = Pressed, 1 = Normal. | Read-Only |
| `0x0001` | `Start Button Pin` | Physical Start Button (`GPIO 11`). 1 = Pressed, 0 = Normal. | Read-Only |
| `0x0002` | `Safety Enable Pin` | Motor Hardware Enable Line (`GPIO 13`). 1 = Enabled, 0 = Disabled. | Read-Only |

### 2.3 Holding Registers (Word Read/Write - FC 0x03 / FC 0x06 / FC 0x10)

| Address | Parameter | Format | Unit / Values | Description |
| :--- | :--- | :--- | :--- | :--- |
| `0x0000` - `0x0001` | `position_setpoint` | Float32 (Big-Endian) | mm | Target linear position setpoint (0.0 to 424.115 mm). |
| `0x0002` | `command` | uint16 | Enumerated | `1` = START, `2` = STOP, `3` = RESET, `99` = EMERGENCY |

### 2.4 Input Registers (Word Read-Only - FC 0x04)

| Address | Parameter | Format | Unit / Values | Description |
| :--- | :--- | :--- | :--- | :--- |
| `0x0000` - `0x0001` | `current_position` | Float32 (Big-Endian) | mm | Real-time position from encoder feedback. |
| `0x0002` - `0x0003` | `current_velocity` | Float32 (Big-Endian) | mm/s | EMA-filtered linear velocity. |
| `0x0004` | `machine_state` | uint16 | Enumerated | `0` = IDLE, `1` = MOVING, `2` = EMERGENCY |

---

## 3. Communication Data Flow Diagrams

### 3.1 Holding Register Write Transaction (Setpoint Update)

```
 [ PLC / Host ]                  [ Core 0: Modbus Slave ]         [ Core 1: Control Loop ]
       │                                     │                               │
       │─── Write Float32 Setpoint ─────────▶│                               │
       │    (FC 0x10, Reg 0x0000)            │                               │
       │                                     │─── Lock g_system_mutex ──────▶│
       │                                     │    Update position_setpoint   │
       │                                     │    Unlock g_system_mutex      │
       │                                     │                               │
       │                                     │                               │─── Lock g_system_mutex ──────▶
       │                                     │                               │    Read position_setpoint
       │                                     │                               │    Compute PID Effort
       │◄── ACK Response (0x10) ─────────────│                               │    Drive Motor PWM
```

### 3.2 Discrete Input Read Transaction (Safety Polling)

```
 [ PLC / Host ]                  [ Core 0: Modbus Slave ]         [ GPIO Pins ]
       │                                     │                          │
       │─── Read Discrete Inputs ───────────▶│                          │
       │    (FC 0x02, Reg 0x0000, 3 bits)    │                          │
       │                                     │─── Sample Pin States ───▶│ (GPIO 12, 11, 13)
       │                                     │◄── Return Pin Levels ────│
       │                                     │                          │
       │◄── Return Bit Mask Response ────────│                          │
```
