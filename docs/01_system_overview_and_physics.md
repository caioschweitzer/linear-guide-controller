# Chapter 1: System Overview & Physical Kinematics

## 1. Executive Summary & Problem Statement

The ESP32-S3 Linear Actuator Controller is an industrial embedded positioning system designed to achieve high-precision closed-loop linear motion control. 

Linear actuators driven by DC motors paired with optical quadrature encoders present several classic control engineering challenges:
1. **Kinematic Scale Conversion**: High-frequency quadrature pulse counting must be mapped continuously and deterministically into real-world physical displacement (millimeters).
2. **Velocity Estimation & Noise Filtering**: Numerical differentiation of discrete position ticks introduces high-frequency derivative noise. Exponential Moving Average (EMA) filtering is required to yield clean velocity feedback for the PID controller.
3. **Overrun & Mechanical Safety**: Physical hard stops at $L_{\text{max}} = 424.115\text{ mm}$ must be protected against via software deadbands, software emergency lockouts, and hardware-level power cutoffs.

---

## 2. Mechanical System Parameters & Physical Geometry

The system is calibrated around a lead-screw linear guide driven by a DC motor equipped with an optical quadrature encoder and position limit/home sensors:

### 2.1 Kinematic & Motion Parameters

| Mechanical Property | Symbol | Numerical Value | Physical Unit |
| :--- | :--- | :--- | :--- |
| Lead Screw Pitch | $P$ | `42.4115` | mm / revolution |
| Maximum Linear Travel | $L_{\text{max}}$ | `424.115` | mm |
| Encoder Resolution | $N$ | `1000` | Pulses Per Rev (PPR) |
| Encoder Quadrature Multiplier | $Q$ | `4` | Edges per pulse (x4 mode) |
| Effective Edges per Rev | $N_{\text{quad}}$ | `4000` | Counts / revolution |
| Minimum Deadband Threshold | $e_{\text{dead}}$ | `0.1` | mm |

### 2.2 Mechanical Structural & Sensor Spatial Dimensions

| Component / Physical Feature | Dimension | Physical Unit | Description / Notes |
| :--- | :--- | :--- | :--- |
| **Linear Guide Total Length** | `800.00` | mm (`80 cm`) | Total physical structural length of the rail |
| **Motor Shaft Inner Diameter** | `13.50` | mm | Shaft bore / coupling inner diameter |
| **Motor Shaft Outer Diameter** | `16.04` | mm | Shaft external diameter |
| **Sensor Physical Dimension** | `24.30` | mm | Physical size / width of sensor housing |
| **Start Datum to Home Sensor** | `37.68` | mm | Distance from physical start datum to Home sensor |
| **Start Datum to FC0 Sensor** | `700.00` | mm (`70 cm`) | Distance from physical start datum to limit switch FC0 |
| **Inter-Sensor Distance (FC0 to FC1)** | `9.18` | mm | Separation distance between limit switches FC0 and FC1 |
| **End of Guide to FC1 Sensor** | `38.58` | mm | Distance from physical rail end to limit switch FC1 |

---

## 3. Mathematical Kinematics & Scale Factors

### 3.1 Linear Scale Factor ($K_{\text{scale}}$)

The direct relation between raw PCNT hardware quadrature counts ($C$) and physical linear position ($x$) is defined by:

$$K_{\text{scale}} = \frac{P}{N \times Q} = \frac{42.4115\text{ mm}}{4000\text{ counts}} = 0.010602875\text{ mm / count}$$

$$\text{Position (mm)}: x(t) = C(t) \times K_{\text{scale}}$$

### 3.2 Velocity Estimation & Differential Derivative

The instantaneous velocity $v_{\text{raw}}(t)$ is derived via first-order numerical differentiation over the 100 Hz control tick period ($\Delta t = 0.010\text{ s}$):

$$v_{\text{raw}}(k) = \frac{x(k) - x(k-1)}{\Delta t}$$

To eliminate measurement spikes during startup and step changes, a guardrail bounds $\Delta t$:
$$\Delta t_{\text{guarded}} = \max(\Delta t, 0.001\text{ s})$$

### 3.3 Exponential Moving Average (EMA) Velocity Filter

Raw differential velocity is smoothed using a discrete Exponential Moving Average (EMA) filter with smoothing coefficient $\alpha = 0.20$:

$$v_{\text{filtered}}(k) = \alpha \cdot v_{\text{raw}}(k) + (1 - \alpha) \cdot v_{\text{filtered}}(k-1)$$

---

## 4. Closed-Loop Position Control & Fixed-Point Modbus Serialization

### 4.1 Fixed-Point Serialization

Modbus RTU Holding and Input registers transmit 32-bit floating-point metrics (`position` and `velocity`) split across two 16-bit registers using Big-Endian byte order.

Additionally, internal telemetry structures convert millimeters to fixed-point integer micro-units ($10^{-3}\text{ mm}$) for atomic transport when required:

$$x_{\text{fixed}} = \text{round}(x(t) \times 1000.0)$$

---

## 5. Control Loop Specifications

- **Control Loop Frequency**: 100 Hz (10 ms period, executed on Core 1).
- **Position Deadband**: $\pm 0.1\text{ mm}$ (when $|x_{\text{setpoint}} - x(t)| \le 0.1\text{ mm}$, motor effort is forced to $0.0\%$).
- **Maximum PWM Output**: $\pm 100.0\%$ duty cycle driven via ESP32-S3 MCPWM peripheral.
