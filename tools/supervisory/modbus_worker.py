import time
import struct
import queue
import logging
from typing import List, Optional, Tuple, Dict, Any

from PyQt6.QtCore import QThread, pyqtSignal

try:
    from pymodbus.client import ModbusSerialClient
except ImportError:
    from pymodbus.client.sync import ModbusSerialClient  # Fallback for older pymodbus

try:
    from serial.tools import list_ports
except ImportError:  # pyserial not installed
    list_ports = None


DEFAULT_SERIAL_PORT = "/dev/ttyUSB0"
DEFAULT_BAUDRATE = 115200


def list_serial_ports() -> List[str]:
    """Returns available serial ports (USB-UART bridges first)."""
    if list_ports is None:
        return []
    ports = [p.device for p in list_ports.comports()]
    ports.sort(key=lambda d: (not ("ttyUSB" in d or "ttyACM" in d), d))
    return ports


def registers_to_float(hi: int, lo: int) -> float:
    """Decodes 2 x 16-bit Big-Endian uint16 registers into a 32-bit IEEE 754 float."""
    raw_bytes = struct.pack(">HH", hi & 0xFFFF, lo & 0xFFFF)
    return struct.unpack(">f", raw_bytes)[0]


def float_to_registers(val: float) -> Tuple[int, int]:
    """Encodes a 32-bit IEEE 754 float into 2 x 16-bit Big-Endian uint16 registers."""
    raw_bytes = struct.pack(">f", float(val))
    hi, lo = struct.unpack(">HH", raw_bytes)
    return (hi, lo)


class ModbusWorker(QThread):
    """
    Dedicated QThread worker for executing Modbus RTU serial (USB-UART) I/O asynchronously.
    Prevents blocking the PyQt6 GUI main event loop and supports non-blocking auto-reconnect.
    """
    telemetry_updated = pyqtSignal(dict)
    connection_status_changed = pyqtSignal(bool, str)
    log_message = pyqtSignal(str)
    burst_data_ready = pyqtSignal(list)
    burst_status_changed = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.serial_port: str = DEFAULT_SERIAL_PORT
        self.baudrate: int = DEFAULT_BAUDRATE
        self.slave_id: int = 1
        self.poll_interval_sec: float = 0.05  # 20Hz polling interval (50ms)
        self.reconnect_interval_sec: float = 2.0  # Retry connection every 2 seconds

        self._running: bool = False
        self._connected: bool = False
        self._user_wants_connected: bool = False
        self._last_reconnect_attempt: float = 0.0
        self._client: Optional[ModbusSerialClient] = None
        self._command_queue: queue.Queue = queue.Queue()
        self._last_burst_status: int = 0
        self._is_downloading_burst: bool = False
        self._last_open_loop_pwm: float = 100.0

    def set_connection_params(self, serial_port: str = DEFAULT_SERIAL_PORT,
                              baudrate: int = DEFAULT_BAUDRATE, slave_id: int = 1):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.slave_id = slave_id

    def connect_modbus(self):
        """Signals worker thread to initiate connection."""
        self._user_wants_connected = True
        self._command_queue.put({"action": "CONNECT"})

    def disconnect_modbus(self):
        """Signals worker thread to disconnect."""
        self._user_wants_connected = False
        self._command_queue.put({"action": "DISCONNECT"})

    def queue_setpoint(self, setpoint_mm: float):
        self._command_queue.put({"action": "WRITE_SETPOINT", "value": setpoint_mm})

    def queue_command(self, cmd_code: int):
        self._command_queue.put({"action": "WRITE_COMMAND", "value": cmd_code})

    def queue_open_loop_test(self, pwm_pct: float = 100.0, mode: int = 0, coast_pos_mm: float = 400.0):
        clamped_pwm = max(1.0, min(100.0, float(pwm_pct)))
        valid_mode = 1 if int(mode) == 1 else 0
        clamped_coast = max(50.0, min(536.0, float(coast_pos_mm)))
        self._command_queue.put({
            "action": "OPEN_LOOP_TEST",
            "pwm": clamped_pwm,
            "mode": valid_mode,
            "coast_pos_mm": clamped_coast,
        })

    def queue_emergency(self):
        self._command_queue.put({"action": "WRITE_EMERGENCY"})

    def queue_pid_gains(self, kp: float, ki: float, kd: float):
        self._command_queue.put({"action": "WRITE_PID", "kp": kp, "ki": ki, "kd": kd})

    def stop_thread(self):
        self._running = False
        self.disconnect_modbus()
        self.wait(1000)

    def run(self):
        self._running = True
        self.log_message.emit("Modbus RTU worker thread started.")

        while self._running:
            # Process queued action requests first
            self._process_command_queue()

            # Handle automatic reconnection if user activated connection but socket dropped
            now = time.time()
            if self._user_wants_connected and not self._connected:
                if now - self._last_reconnect_attempt >= self.reconnect_interval_sec:
                    self._last_reconnect_attempt = now
                    self._do_connect()

            # Perform routine telemetry polling if connected
            if self._connected and self._client:
                try:
                    telemetry = self._poll_telemetry()
                    if telemetry:
                        self.telemetry_updated.emit(telemetry)
                except Exception as e:
                    self.log_message.emit(f"Error during Modbus RTU polling: {e}")
                    self._handle_disconnect(f"Communication error: {e}")

            time.sleep(self.poll_interval_sec)

        self._cleanup_client()
        self.log_message.emit("Modbus RTU worker thread stopped.")

    def _process_command_queue(self):
        while not self._command_queue.empty():
            try:
                cmd = self._command_queue.get_nowait()
                action = cmd.get("action")

                if action == "CONNECT":
                    self._do_connect()
                elif action == "DISCONNECT":
                    self._do_disconnect()
                elif action == "WRITE_SETPOINT" and self._connected:
                    self._do_write_setpoint(cmd["value"])
                elif action == "WRITE_COMMAND" and self._connected:
                    self._do_write_command(cmd["value"])
                elif action == "WRITE_EMERGENCY" and self._connected:
                    self._do_write_emergency()
                elif action == "OPEN_LOOP_TEST" and self._connected:
                    pwm_pct = cmd.get("pwm", 100.0)
                    mode = cmd.get("mode", 0)
                    coast_pos = cmd.get("coast_pos_mm", 400.0)
                    self._do_write_open_loop_params(pwm_pct, mode, coast_pos)
                    self._do_write_command(5)
                elif action == "WRITE_PID" and self._connected:
                    self._do_write_pid(cmd["kp"], cmd["ki"], cmd["kd"])
            except queue.Empty:
                break
            except Exception as e:
                self.log_message.emit(f"Command execution error ({action}): {e}")

    def _do_connect(self):
        if not self.serial_port:
            self.connection_status_changed.emit(False, "No serial port specified")
            return

        self._cleanup_client()
        target = f"{self.serial_port} @ {self.baudrate} 8N1"
        self.log_message.emit(f"Opening Modbus RTU serial slave on {target} (Slave ID: {self.slave_id})...")

        try:
            self._client = ModbusSerialClient(
                port=self.serial_port,
                baudrate=self.baudrate,
                bytesize=8,
                parity="N",
                stopbits=1,
                timeout=0.5,
                retries=1
            )
            connected = self._client.connect()
            if connected:
                self._connected = True
                self.connection_status_changed.emit(True, f"Connected ({target})")
                self.log_message.emit(f"Serial port {target} opened successfully.")
            else:
                self._connected = False
                self.connection_status_changed.emit(False, f"Connection failed ({target})")
                if self._user_wants_connected:
                    self.log_message.emit(f"Serial port open failed (check cable / permissions on dialout group). Will retry in {self.reconnect_interval_sec}s...")
        except Exception as e:
            self._connected = False
            self.connection_status_changed.emit(False, f"Connection error: {e}")
            if self._user_wants_connected:
                self.log_message.emit(f"Exception opening {target}: {e}. Retrying...")

    def _do_disconnect(self):
        if self._connected or self._client:
            self._cleanup_client()
            self._connected = False
            self.connection_status_changed.emit(False, "Disconnected")
            self.log_message.emit("Serial port closed.")

    def _handle_disconnect(self, reason: str):
        self._cleanup_client()
        self._connected = False
        self.connection_status_changed.emit(False, reason)
        if self._user_wants_connected:
            self.log_message.emit(f"Connection lost ({reason}). Auto-reconnect active, retrying in {self.reconnect_interval_sec}s...")

    def _cleanup_client(self):
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def _do_write_setpoint(self, val_mm: float):
        hi, lo = float_to_registers(val_mm)
        res = self._client.write_registers(address=0x0000, values=[hi, lo], slave=self.slave_id)
        if hasattr(res, "isError") and res.isError():
            self.log_message.emit(f"Failed to write setpoint {val_mm:.2f} mm")
        else:
            self.log_message.emit(f"Set Target Position -> {val_mm:.2f} mm")

    def _do_write_command(self, cmd_code: int):
        cmd_names = {1: "START", 2: "STOP", 3: "RESET", 4: "HOME", 5: "OPEN_LOOP_TEST", 99: "SIMULATE_EMERGENCY"}
        name = cmd_names.get(cmd_code, f"CMD_{cmd_code}")
        res = self._client.write_register(address=0x0002, value=cmd_code, slave=self.slave_id)
        if hasattr(res, "isError") and res.isError():
            self.log_message.emit(f"Failed to write command {name}")
        else:
            self.log_message.emit(f"Sent Command -> {name} ({cmd_code})")

    def _do_write_emergency(self):
        # Write command 99 (SIMULATE_EMERGENCY) to Holding Reg 0x0002
        self._do_write_command(99)
        # Also set Remote Emergency Coil (Coil Bit 1)
        try:
            self._client.write_coil(address=0x0001, value=True, slave=self.slave_id)
            self.log_message.emit("Triggered Remote Emergency Stop Coil (Coil 1).")
        except Exception as e:
            self.log_message.emit(f"Emergency coil trigger warning: {e}")

    def _do_write_open_loop_params(self, pwm_pct: float, mode: int = 0, coast_pos_mm: float = 400.0):
        clamped = max(1.0, min(100.0, float(pwm_pct)))
        valid_mode = 1 if int(mode) == 1 else 0
        clamped_coast = max(50.0, min(536.0, float(coast_pos_mm)))

        pwm_hi, pwm_lo = float_to_registers(clamped)
        coast_hi, coast_lo = float_to_registers(clamped_coast)
        payload = [pwm_hi, pwm_lo, valid_mode, coast_hi, coast_lo]
        res = self._client.write_registers(address=0x000A, values=payload, slave=self.slave_id)
        if hasattr(res, "isError") and res.isError():
            self.log_message.emit(f"Failed to write open-loop params (PWM {clamped:.1f}%, mode {valid_mode})")
        else:
            self._last_open_loop_pwm = clamped
            mode_str = "COAST" if valid_mode == 1 else "BRAKE"
            self.log_message.emit(
                f"Set Open-Loop -> PWM: {clamped:.1f}%, Mode: {mode_str}, CutPos: {clamped_coast:.1f} mm"
            )

    def _do_write_pid(self, kp: float, ki: float, kd: float):
        kp_hi, kp_lo = float_to_registers(kp)
        ki_hi, ki_lo = float_to_registers(ki)
        kd_hi, kd_lo = float_to_registers(kd)
        payload = [kp_hi, kp_lo, ki_hi, ki_lo, kd_hi, kd_lo]

        res = self._client.write_registers(address=0x0003, values=payload, slave=self.slave_id)
        if hasattr(res, "isError") and res.isError():
            self.log_message.emit("Failed to update PID gains via Modbus.")
        else:
            self.log_message.emit(f"Updated PID Gains -> Kp: {kp:.3f}, Ki: {ki:.3f}, Kd: {kd:.4f}")

    def _do_download_burst_buffer(self, count: int):
        if not self._client or not self._connected or count <= 0:
            return
        self._is_downloading_burst = True
        self.log_message.emit(f"📥 Descarregando buffer de malha aberta ({count} amostras) do ESP32...")
        samples = []
        try:
            for i in range(count):
                # Write sample index to holding register 0x0009
                self._client.write_register(address=0x0009, value=i, slave=self.slave_id)
                # Read sample input registers (0x0009 to 0x0010: 8 registers: time, pos, vel, duty)
                res = self._client.read_input_registers(address=0x0009, count=8, slave=self.slave_id)
                if hasattr(res, "isError") and res.isError():
                    continue
                regs = res.registers
                time_ms = ((regs[0] & 0xFFFF) << 16) | (regs[1] & 0xFFFF)
                pos = registers_to_float(regs[2], regs[3])
                vel = registers_to_float(regs[4], regs[5])
                sample_duty = registers_to_float(regs[6], regs[7]) if len(regs) >= 8 else self._last_open_loop_pwm
                samples.append({
                    "time_s": round(time_ms / 1000.0, 3),
                    "position_mm": round(pos, 3),
                    "velocity_mm_s": round(vel, 3),
                    "duty_pct": round(sample_duty, 2)
                })
            self.log_message.emit(f"✅ Download concluído: {len(samples)} pontos recebidos com sucesso.")
            self.burst_data_ready.emit(samples)
        except Exception as e:
            self.log_message.emit(f"❌ Erro no download do buffer de malha aberta: {e}")
        finally:
            self._is_downloading_burst = False

    def _poll_telemetry(self) -> Optional[Dict[str, Any]]:
        if not self._client or not self._connected:
            return None

        # 1. Read Input Registers 0x0000 to 0x0008 (9 registers: Pos, Vel, Duty, State, Burst Status, Burst Count)
        res_in = self._client.read_input_registers(address=0x0000, count=9, slave=self.slave_id)
        if hasattr(res_in, "isError") and res_in.isError():
            self.log_message.emit(f"⚠️ Erro ao ler Input Registers (0x0000-0x0008): {res_in}")
            return None

        pos = registers_to_float(res_in.registers[0], res_in.registers[1])
        vel = registers_to_float(res_in.registers[2], res_in.registers[3])
        duty = registers_to_float(res_in.registers[4], res_in.registers[5])
        state = res_in.registers[6]
        burst_status = res_in.registers[7] if len(res_in.registers) > 7 else 0
        burst_count = res_in.registers[8] if len(res_in.registers) > 8 else 0

        if burst_status != self._last_burst_status:
            self.burst_status_changed.emit(burst_status, burst_count)
            if burst_status == 2 and not self._is_downloading_burst and burst_count > 0:
                self._do_download_burst_buffer(burst_count)
            elif burst_status == 3:
                self.log_message.emit("⚠️ Ensaio de malha aberta abortado (timeout ou emergência).")
            self._last_burst_status = burst_status
        # 2. Read Holding Registers 0x0000 to 0x0008 (9 registers: setpoint, command, kp, ki, kd)
        res_hold = self._client.read_holding_registers(address=0x0000, count=9, slave=self.slave_id)
        setpoint = 0.0
        kp, ki, kd = 2.0, 0.5, 0.05
        if not (hasattr(res_hold, "isError") and res_hold.isError()):
            setpoint = registers_to_float(res_hold.registers[0], res_hold.registers[1])
            kp = registers_to_float(res_hold.registers[3], res_hold.registers[4])
            ki = registers_to_float(res_hold.registers[5], res_hold.registers[6])
            kd = registers_to_float(res_hold.registers[7], res_hold.registers[8])

        # 3. Read Discrete Inputs 0x0000 (4 bits)
        res_disc = self._client.read_discrete_inputs(address=0x0000, count=4, slave=self.slave_id)
        estop_btn, start_btn, safety_enable, home_sensor = False, False, False, False
        if not (hasattr(res_disc, "isError") and res_disc.isError()):
            bits = res_disc.bits
            estop_btn = bits[0] if len(bits) > 0 else False
            start_btn = bits[1] if len(bits) > 1 else False
            safety_enable = bits[2] if len(bits) > 2 else False
            home_sensor = bits[3] if len(bits) > 3 else False

        # 4. Read Coils 0x0000 (1 bit for Status LED)
        res_coils = self._client.read_coils(address=0x0000, count=1, slave=self.slave_id)
        led_status = False
        if not (hasattr(res_coils, "isError") and res_coils.isError()):
            led_status = res_coils.bits[0] if len(res_coils.bits) > 0 else False

        return {
            "timestamp": time.time(),
            "target_setpoint": setpoint,
            "current_position": pos,
            "current_velocity": vel,
            "duty_cycle": duty,
            "machine_state": state,
            "estop_button": estop_btn,
            "start_button": start_btn,
            "safety_enable": safety_enable,
            "home_sensor": home_sensor,
            "led_status": led_status,
            "kp": kp,
            "ki": ki,
            "kd": kd,
            "burst_status": burst_status,
            "burst_sample_count": burst_count
        }
