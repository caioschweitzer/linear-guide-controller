import sys
import time
import csv
from collections import deque
from typing import Dict, Any, List

from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QPalette
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QSlider,
    QTextEdit, QGroupBox, QFrame, QMessageBox, QApplication, QFileDialog
)

import pyqtgraph as pg

from tools.supervisory.modbus_worker import ModbusWorker

# Dark Theme QSS Stylesheet
DARK_STYLESHEET = """
QMainWindow {
    background-color: #12131C;
}
QWidget {
    background-color: #1E1E2E;
    color: #CDD6F4;
    font-family: "Segoe UI", "Roboto", "Helvetica Neue", sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #45475A;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
    color: #89B4FA;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 8px;
    background-color: #181825;
    border-radius: 4px;
}
QPushButton {
    background-color: #313244;
    color: #CDD6F4;
    border: 1px solid #45475A;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #45475A;
    border-color: #89B4FA;
}
QPushButton:pressed {
    background-color: #585B70;
}
QPushButton#connect_btn {
    background-color: #2E7D32;
    color: #FFFFFF;
}
QPushButton#connect_btn:hover {
    background-color: #388E3C;
}
QPushButton#disconnect_btn {
    background-color: #C62828;
    color: #FFFFFF;
}
QPushButton#estop_btn {
    background-color: #D32F2F;
    color: #FFFFFF;
    font-size: 16px;
    font-weight: 900;
    border: 2px solid #FF5252;
    border-radius: 8px;
    padding: 12px;
}
QPushButton#estop_btn:hover {
    background-color: #E53935;
    border-color: #FF8A80;
}
QPushButton#start_btn {
    background-color: #1565C0;
    color: #FFFFFF;
}
QPushButton#start_btn:hover {
    background-color: #1976D2;
}
QPushButton#home_btn {
    background-color: #0288D1;
    color: #FFFFFF;
}
QPushButton#home_btn:hover {
    background-color: #039BE5;
}
QPushButton#pid_btn {
    background-color: #7B1FA2;
    color: #FFFFFF;
}
QPushButton#pid_btn:hover {
    background-color: #8E24AA;
}
QPushButton#openloop_btn {
    background-color: #E65100;
    color: #FFFFFF;
    font-weight: bold;
    padding: 8px;
}
QPushButton#openloop_btn:hover {
    background-color: #F57C00;
}
QPushButton#openloop_btn:disabled {
    background-color: #313244;
    color: #6C7086;
    border-color: #45475A;
}
QPushButton#export_btn {
    background-color: #00796B;
    color: #FFFFFF;
}
QPushButton#export_btn:hover {
    background-color: #00897B;
}
QPushButton#export_btn:disabled {
    background-color: #313244;
    color: #6C7086;
}
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #181825;
    border: 1px solid #45475A;
    border-radius: 4px;
    padding: 4px 8px;
    color: #CDD6F4;
}
QComboBox::drop-down {
    border: none;
}
QTextEdit {
    background-color: #11111B;
    border: 1px solid #313244;
    border-radius: 6px;
    color: #A6ADC8;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
}
QSlider::groove:horizontal {
    border: 1px solid #45475A;
    height: 8px;
    background: #181825;
    border-radius: 4px;
}
QSlider::sub-page:horizontal {
    background: #89B4FA;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #B4BEFE;
    border: 1px solid #89B4FA;
    width: 18px;
    margin-top: -6px;
    margin-bottom: -6px;
    border-radius: 9px;
}
"""


class StatusBadge(QLabel):
    """Custom pill badge widget for visual status rendering."""

    STATE_MAP = {
        0: ("IDLE", "#6C7086", "#181825"),
        1: ("MOVING", "#A6E3A1", "#1E3A29"),
        2: ("EMERGENCY", "#F38BA8", "#3A1E24"),
        3: ("HOMING", "#89B4FA", "#1E2A38"),
        4: ("OPEN_LOOP", "#FAB387", "#3A281E")
    }

    def __init__(self, text="DISCONNECTED", text_color="#CDD6F4", bg_color="#313244", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_colors(text_color, bg_color)
        self.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))

    def set_colors(self, text_color: str, bg_color: str):
        self.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                background-color: {bg_color};
                border: 1px solid {text_color};
                border-radius: 12px;
                padding: 4px 12px;
                font-weight: bold;
            }}
        """)

    def update_machine_state(self, state_code: int):
        text, fg, bg = self.STATE_MAP.get(state_code, (f"UNKNOWN ({state_code})", "#F9E2AF", "#3A3524"))
        self.setText(f"STATE: {text}")
        self.set_colors(fg, bg)


class SupervisoryMainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Linear Guide Actuator - Modbus TCP Supervisory (SCADA)")
        self.resize(1280, 800)

        # Apply dark mode stylesheet
        self.setStyleSheet(DARK_STYLESHEET)

        # Telemetry History Deques for PyQtGraph (rolling buffer)
        self.max_points = 300
        self.time_history = deque(maxlen=self.max_points)
        self.setpoint_history = deque(maxlen=self.max_points)
        self.position_history = deque(maxlen=self.max_points)
        self.velocity_history = deque(maxlen=self.max_points)
        self.duty_history = deque(maxlen=self.max_points)
        self.start_timestamp = time.time()

        # Initialize Modbus Worker QThread
        self.modbus_worker = ModbusWorker()
        self.modbus_worker.telemetry_updated.connect(self.on_telemetry_updated)
        self.modbus_worker.connection_status_changed.connect(self.on_connection_status_changed)
        self.modbus_worker.burst_data_ready.connect(self.on_burst_data_ready)
        self.modbus_worker.log_message.connect(self.append_log)
        self.modbus_worker.start()

        # Open-Loop Test State
        self.last_burst_samples: List[Dict[str, Any]] = []
        self.latest_position: float = 0.0
        self.latest_machine_state: int = 0

        # Build UI layout
        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Top Connection Bar & Status Header
        top_bar = self._create_top_bar()
        main_layout.addLayout(top_bar)

        # 2. Main Content Splitter Layout (Left: Controls, Right: Telemetry Graphs)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(12)

        left_controls_panel = self._create_left_controls_panel()
        right_telemetry_panel = self._create_right_telemetry_panel()

        content_layout.addLayout(left_controls_panel, stretch=2)
        content_layout.addLayout(right_telemetry_panel, stretch=3)

        main_layout.addLayout(content_layout, stretch=1)

        # 3. Bottom Log Console Panel
        bottom_log_panel = self._create_log_console_panel()
        main_layout.addWidget(bottom_log_panel, stretch=0)

    def _create_top_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(10)

        # Title Label
        title_label = QLabel("🌐 LINEAR GUIDE SUPERVISORY (MODBUS TCP)")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #89B4FA;")
        layout.addWidget(title_label)

        layout.addStretch()

        # IP Address Input LineEdit
        layout.addWidget(QLabel("IP Addr:"))
        self.ip_input = QLineEdit("192.168.1.100")
        self.ip_input.setMinimumWidth(130)
        layout.addWidget(self.ip_input)

        # TCP Port SpinBox
        layout.addWidget(QLabel("Port:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(502)
        self.port_spin.setMinimumWidth(75)
        layout.addWidget(self.port_spin)

        # Slave ID SpinBox
        layout.addWidget(QLabel("Slave ID:"))
        self.slave_spin = QSpinBox()
        self.slave_spin.setRange(1, 247)
        self.slave_spin.setValue(1)
        layout.addWidget(self.slave_spin)

        # Connect / Disconnect Button
        self.connect_btn = QPushButton("CONNECT")
        self.connect_btn.setObjectName("connect_btn")
        self.connect_btn.clicked.connect(self.toggle_connection)
        layout.addWidget(self.connect_btn)

        # Connection Status Badge
        self.conn_badge = StatusBadge("DISCONNECTED", "#F38BA8", "#313244")
        layout.addWidget(self.conn_badge)

        # Machine State Status Badge
        self.state_badge = StatusBadge("STATE: IDLE", "#6C7086", "#181825")
        layout.addWidget(self.state_badge)

        return layout

    def _create_left_controls_panel(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # A. Motion Control Group Box
        motion_box = QGroupBox("Motion Control & Commands")
        motion_layout = QVBoxLayout(motion_box)

        # Position Setpoint Controls (Spinbox + Slider)
        sp_label_layout = QHBoxLayout()
        sp_label_layout.addWidget(QLabel("Target Setpoint Position (mm):"))
        self.sp_val_label = QLabel("0.00 mm")
        self.sp_val_label.setStyleSheet("color: #89B4FA; font-weight: bold;")
        sp_label_layout.addWidget(self.sp_val_label)
        motion_layout.addLayout(sp_label_layout)

        sp_input_layout = QHBoxLayout()
        self.sp_spinbox = QDoubleSpinBox()
        self.sp_spinbox.setRange(0.0, 670.0)
        self.sp_spinbox.setSingleStep(1.0)
        self.sp_spinbox.setDecimals(2)
        self.sp_spinbox.valueChanged.connect(self.on_setpoint_spinbox_changed)
        sp_input_layout.addWidget(self.sp_spinbox, stretch=1)

        self.sp_slider = QSlider(Qt.Orientation.Horizontal)
        self.sp_slider.setRange(0, 6700)  # 0.0 to 670.0 mm (scaled by 10)
        self.sp_slider.valueChanged.connect(self.on_setpoint_slider_changed)
        sp_input_layout.addWidget(self.sp_slider, stretch=2)
        motion_layout.addLayout(sp_input_layout)

        # Motion Command Buttons Grid
        cmd_grid = QGridLayout()
        self.btn_start = QPushButton("▶ START MOTION")
        self.btn_start.setObjectName("start_btn")
        self.btn_start.clicked.connect(lambda: self.send_command(1))

        self.btn_stop = QPushButton("⏸ STOP")
        self.btn_stop.clicked.connect(lambda: self.send_command(2))

        self.btn_home = QPushButton("🏠 FIND HOME")
        self.btn_home.setObjectName("home_btn")
        self.btn_home.clicked.connect(lambda: self.send_command(4))

        self.btn_reset = QPushButton("🔄 RESET FAULT")
        self.btn_reset.clicked.connect(lambda: self.send_command(3))

        cmd_grid.addWidget(self.btn_start, 0, 0)
        cmd_grid.addWidget(self.btn_stop, 0, 1)
        cmd_grid.addWidget(self.btn_home, 1, 0)
        cmd_grid.addWidget(self.btn_reset, 1, 1)
        motion_layout.addLayout(cmd_grid)

        # Prominent Emergency Stop Button
        self.btn_estop = QPushButton("🚨 EMERGENCY STOP")
        self.btn_estop.setObjectName("estop_btn")
        self.btn_estop.clicked.connect(self.send_emergency_stop)
        motion_layout.addWidget(self.btn_estop)

        layout.addWidget(motion_box)

        # Open-Loop Step Response Group Box (System Identification)
        open_loop_box = QGroupBox("Open-Loop Step Test (System Identification)")
        ol_layout = QVBoxLayout(open_loop_box)

        self.lbl_open_loop_cond = QLabel("Condition: Waiting for telemetry (|pos| <= 5.0 mm and IDLE)...")
        self.lbl_open_loop_cond.setStyleSheet("color: #A6ADC8; font-size: 11px;")
        ol_layout.addWidget(self.lbl_open_loop_cond)

        ol_btn_layout = QHBoxLayout()
        self.btn_open_loop = QPushButton("🚀 RUN STEP TEST (100% PWM -> 536 mm / 80%)")
        self.btn_open_loop.setObjectName("openloop_btn")
        self.btn_open_loop.setEnabled(False)
        self.btn_open_loop.clicked.connect(self.start_open_loop_test)
        ol_btn_layout.addWidget(self.btn_open_loop, stretch=2)

        self.btn_export_csv = QPushButton("💾 Export CSV")
        self.btn_export_csv.setObjectName("export_btn")
        self.btn_export_csv.setEnabled(False)
        self.btn_export_csv.clicked.connect(self.export_csv_manually)
        ol_btn_layout.addWidget(self.btn_export_csv, stretch=1)

        ol_layout.addLayout(ol_btn_layout)
        layout.addWidget(open_loop_box)

        # B. PID Control Tuning Group Box
        pid_box = QGroupBox("PID Closed-Loop Gain Tuning")
        pid_layout = QGridLayout(pid_box)

        pid_layout.addWidget(QLabel("Kp (Proportional):"), 0, 0)
        self.kp_spin = QDoubleSpinBox()
        self.kp_spin.setRange(0.0, 1000000.0)
        self.kp_spin.setSingleStep(0.1)
        self.kp_spin.setValue(2.0)
        pid_layout.addWidget(self.kp_spin, 0, 1)

        pid_layout.addWidget(QLabel("Ki (Integral):"), 1, 0)
        self.ki_spin = QDoubleSpinBox()
        self.ki_spin.setRange(0.0, 1000000.0)
        self.ki_spin.setSingleStep(0.05)
        self.ki_spin.setValue(0.5)
        pid_layout.addWidget(self.ki_spin, 1, 1)

        pid_layout.addWidget(QLabel("Kd (Derivative):"), 2, 0)
        self.kd_spin = QDoubleSpinBox()
        self.kd_spin.setRange(0.0, 1000000.0)
        self.kd_spin.setSingleStep(0.005)
        self.kd_spin.setDecimals(4)
        self.kd_spin.setValue(0.05)
        pid_layout.addWidget(self.kd_spin, 2, 1)

        self.btn_apply_pid = QPushButton("⚡ APPLY PID GAINS")
        self.btn_apply_pid.setObjectName("pid_btn")
        self.btn_apply_pid.clicked.connect(self.apply_pid_gains)
        pid_layout.addWidget(self.btn_apply_pid, 3, 0, 1, 2)

        layout.addWidget(pid_box)

        # C. Hardware Signals & Status Indicators Group Box
        signals_box = QGroupBox("Hardware Safety & Signals Status")
        signals_layout = QGridLayout(signals_box)

        self.lbl_hw_estop = QLabel("E-Stop Pin: --")
        self.lbl_hw_start = QLabel("Start Pin: --")
        self.lbl_hw_home = QLabel("Home Sensor: --")
        self.lbl_hw_safety = QLabel("Safety Enable: --")
        self.lbl_hw_led = QLabel("Status LED: --")
        self.lbl_hw_duty = QLabel("Motor Duty Cycle: --")

        signals_layout.addWidget(self.lbl_hw_estop, 0, 0)
        signals_layout.addWidget(self.lbl_hw_start, 0, 1)
        signals_layout.addWidget(self.lbl_hw_home, 1, 0)
        signals_layout.addWidget(self.lbl_hw_safety, 1, 1)
        signals_layout.addWidget(self.lbl_hw_duty, 2, 0)
        signals_layout.addWidget(self.lbl_hw_led, 2, 1)

        layout.addWidget(signals_box)
        layout.addStretch()

        return layout

    def _create_right_telemetry_panel(self) -> QVBoxLayout:
        layout = QVBoxLayout()

        # Configure PyQtGraph Dark Theme
        pg.setConfigOption('background', '#181825')
        pg.setConfigOption('foreground', '#CDD6F4')

        # Graphics Layout Widget (3 plots stacked vertically)
        self.graph_widget = pg.GraphicsLayoutWidget()

        # 1. Position Telemetry Plot
        self.plot_pos = self.graph_widget.addPlot(title="<b>Position Tracking (mm)</b>")
        self.plot_pos.showGrid(x=True, y=True, alpha=0.3)
        self.plot_pos.setLabel('left', 'Position', units='mm')
        self.plot_pos.setLabel('bottom', 'Time', units='s')
        self.plot_pos.addLegend(offset=(-10, 10))

        self.curve_setpoint = self.plot_pos.plot(pen=pg.mkPen(color='#89B4FA', width=2, style=Qt.PenStyle.DashLine), name="Setpoint")
        self.curve_position = self.plot_pos.plot(pen=pg.mkPen(color='#A6E3A1', width=2.5), name="Actual Pos")

        self.graph_widget.nextRow()

        # 2. Velocity Telemetry Plot
        self.plot_vel = self.graph_widget.addPlot(title="<b>Velocity Telemetry (mm/s)</b>")
        self.plot_vel.showGrid(x=True, y=True, alpha=0.3)
        self.plot_vel.setLabel('left', 'Velocity', units='mm/s')
        self.plot_vel.setLabel('bottom', 'Time', units='s')

        self.curve_velocity = self.plot_vel.plot(pen=pg.mkPen(color='#FAB387', width=2), name="Velocity")

        self.graph_widget.nextRow()

        # 3. Motor Duty Cycle Plot
        self.plot_duty = self.graph_widget.addPlot(title="<b>Calculated Motor Duty Cycle (%)</b>")
        self.plot_duty.showGrid(x=True, y=True, alpha=0.3)
        self.plot_duty.setLabel('left', 'Effort', units='%')
        self.plot_duty.setLabel('bottom', 'Time', units='s')

        self.curve_duty = self.plot_duty.plot(pen=pg.mkPen(color='#CBA6F7', width=2), name="Duty Cycle")

        layout.addWidget(self.graph_widget)
        return layout

    def _create_log_console_panel(self) -> QGroupBox:
        box = QGroupBox("Activity & Modbus Event Log")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 8, 8, 8)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumHeight(120)
        layout.addWidget(self.log_console)

        return box

    def toggle_connection(self):
        if not self.modbus_worker._user_wants_connected and not self.modbus_worker._connected:
            host = self.ip_input.text().strip()
            port = self.port_spin.value()
            slave_id = self.slave_spin.value()
            self.modbus_worker.set_connection_params(host, port, slave_id)
            self.modbus_worker.connect_modbus()
        else:
            self.modbus_worker.disconnect_modbus()

    @pyqtSlot(bool, str)
    def on_connection_status_changed(self, connected: bool, msg: str):
        if connected:
            self.connect_btn.setText("DISCONNECT")
            self.connect_btn.setObjectName("disconnect_btn")
            self.conn_badge.setText("CONNECTED")
            self.conn_badge.set_colors("#A6E3A1", "#1E3A29")
        else:
            self.connect_btn.setText("CONNECT")
            self.connect_btn.setObjectName("connect_btn")
            self.conn_badge.setText("DISCONNECTED")
            self.conn_badge.set_colors("#F38BA8", "#313244")
            self.state_badge.update_machine_state(0)

        # Force stylesheet update on connect_btn
        self.connect_btn.setStyle(self.connect_btn.style())

    @pyqtSlot(dict)
    def on_telemetry_updated(self, data: Dict[str, Any]):
        t = data["timestamp"] - self.start_timestamp
        sp = data["target_setpoint"]
        pos = data["current_position"]
        vel = data["current_velocity"]
        duty = data.get("duty_cycle", 0.0)
        state = data["machine_state"]

        # Append data to graph deques
        self.time_history.append(t)
        self.setpoint_history.append(sp)
        self.position_history.append(pos)
        self.velocity_history.append(vel)
        self.duty_history.append(duty)

        # Update PyQtGraph curves
        self.curve_setpoint.setData(list(self.time_history), list(self.setpoint_history))
        self.curve_position.setData(list(self.time_history), list(self.position_history))
        self.curve_velocity.setData(list(self.time_history), list(self.velocity_history))
        self.curve_duty.setData(list(self.time_history), list(self.duty_history))

        # Update Machine State Badge
        self.state_badge.update_machine_state(state)

        # Update Hardware Status Labels (Active-LOW hardware pin logic: 0 = Pressed/Tripped, 1 = Safe/Released)
        estop_tripped = not data["estop_button"]
        estop_str = "ACTIVE 🚨" if estop_tripped else "OK"
        estop_color = "#F38BA8" if estop_tripped else "#A6E3A1"
        self.lbl_hw_estop.setText(f"E-Stop Pin: <font color='{estop_color}'><b>{estop_str}</b></font>")

        start_pressed = not data["start_button"]
        start_str = "PRESSED" if start_pressed else "RELEASED"
        self.lbl_hw_start.setText(f"Start Pin: <b>{start_str}</b>")

        home_triggered = bool(data.get("home_sensor", False))
        home_str = "DETECTED 🎯" if home_triggered else "CLEAR"
        home_color = "#89B4FA" if home_triggered else "#6C7086"
        self.lbl_hw_home.setText(f"Home Sensor: <font color='{home_color}'><b>{home_str}</b></font>")

        safety_str = "ENABLED ✅" if data["safety_enable"] else "DISABLED ❌"
        safety_color = "#A6E3A1" if data["safety_enable"] else "#F38BA8"
        self.lbl_hw_safety.setText(f"Safety Enable: <font color='{safety_color}'><b>{safety_str}</b></font>")

        self.lbl_hw_duty.setText(f"Motor Duty: <b>{duty:+.1f} %</b>")

        led_str = "ON 💡" if data["led_status"] else "OFF"
        self.lbl_hw_led.setText(f"Status LED: <b>{led_str}</b>")

        # Update Open-Loop Step Test Interlocks
        self.latest_position = pos
        self.latest_machine_state = state
        can_start_ol = (abs(pos) <= 5.0) and (state == 0) and self.modbus_worker._connected
        self.btn_open_loop.setEnabled(can_start_ol)

        if state == 4:
            self.lbl_open_loop_cond.setText("Status: <font color='#FAB387'><b>TEST RUNNING (100% PWM -> 536 mm / 80%)...</b></font>")
        elif can_start_ol:
            self.lbl_open_loop_cond.setText("Condition: <font color='#A6E3A1'><b>READY (|pos| <= 5.0 mm and IDLE)</b></font>")
        elif abs(pos) > 5.0:
            self.lbl_open_loop_cond.setText(f"Condition: <font color='#F38BA8'>Blocked (|pos| = {pos:.2f} mm > 5.0 mm, move to 0)</font>")
        elif state != 0:
            self.lbl_open_loop_cond.setText("Condition: <font color='#F9E2AF'>Blocked (machine must be in IDLE)</font>")
        else:
            self.lbl_open_loop_cond.setText("Condition: <font color='#6C7086'>Waiting for connection...</font>")

    def start_open_loop_test(self):
        if not self.modbus_worker._connected:
            QMessageBox.warning(self, "Disconnected", "Connect to Modbus TCP slave first.")
            return

        if abs(self.latest_position) > 5.0:
            QMessageBox.warning(
                self,
                "Position Pre-condition Blocked",
                f"Actuator position must be near zero (|pos| <= 5.0 mm).\nCurrent position: {self.latest_position:.2f} mm.\nPlease perform Homing or move near 0 mm."
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirm Open-Loop Step Test",
            "Deseja iniciar o ensaio de malha aberta?\n\nO motor será acionado em 100% de esforço até atingir 80% do curso (536.0 mm).\nA frenagem eletrodinâmica ativa será aplicada instantaneamente, restando mais de 134 mm de margem livre.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.modbus_worker.queue_open_loop_test()
            self.append_log("🚀 Iniciado ensaio de malha aberta (100% PWM até 536 mm / 80% do curso).")

    @pyqtSlot(list)
    def on_burst_data_ready(self, samples: List[Dict[str, Any]]):
        self.last_burst_samples = samples
        self.btn_export_csv.setEnabled(len(samples) > 0)
        self.append_log(f"📊 Recebidas {len(samples)} amostras de malha aberta do ESP32.")

        if samples:
            times = [s["time_s"] for s in samples]
            positions = [s["position_mm"] for s in samples]
            velocities = [s["velocity_mm_s"] for s in samples]
            duties = [s["duty_pct"] for s in samples]

            self.time_history.clear()
            self.setpoint_history.clear()
            self.position_history.clear()
            self.velocity_history.clear()
            self.duty_history.clear()

            for t, p, v, d in zip(times, positions, velocities, duties):
                self.time_history.append(t)
                self.setpoint_history.append(536.0)
                self.position_history.append(p)
                self.velocity_history.append(v)
                self.duty_history.append(d)

            self.curve_setpoint.setData(list(self.time_history), list(self.setpoint_history))
            self.curve_position.setData(list(self.time_history), list(self.position_history))
            self.curve_velocity.setData(list(self.time_history), list(self.velocity_history))
            self.curve_duty.setData(list(self.time_history), list(self.duty_history))

            # Prompt for file save
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "Salvar Curva de Malha Aberta",
                "curva_malha_aberta.csv",
                "Arquivos CSV (*.csv);;Todos os Arquivos (*)"
            )
            if filepath:
                self._write_csv_file(filepath, samples)

    def export_csv_manually(self):
        if not self.last_burst_samples:
            QMessageBox.information(self, "Sem Dados", "Nenhum dado de ensaio gravado até o momento.")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Curva de Malha Aberta",
            "curva_malha_aberta.csv",
            "Arquivos CSV (*.csv);;Todos os Arquivos (*)"
        )
        if filepath:
            self._write_csv_file(filepath, self.last_burst_samples)

    def _write_csv_file(self, filepath: str, samples: List[Dict[str, Any]]):
        try:
            with open(filepath, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["time_s", "position_mm", "velocity_mm_s", "duty_pct"])
                for s in samples:
                    writer.writerow([s["time_s"], s["position_mm"], s["velocity_mm_s"], s["duty_pct"]])
            self.append_log(f"💾 Dados salvos com sucesso em {filepath}")
            QMessageBox.information(self, "Exportação Concluída", f"Arquivo CSV salvo com sucesso:\n{filepath}\nTotal de pontos: {len(samples)}")
        except Exception as e:
            self.append_log(f"❌ Erro ao salvar arquivo CSV: {e}")
            QMessageBox.critical(self, "Erro de Exportação", f"Não foi possível salvar o arquivo:\n{e}")

    def on_setpoint_spinbox_changed(self, val: float):
        self.sp_val_label.setText(f"{val:.2f} mm")
        slider_val = int(val * 10.0)
        if self.sp_slider.value() != slider_val:
            self.sp_slider.blockSignals(True)
            self.sp_slider.setValue(slider_val)
            self.sp_slider.blockSignals(False)

    def on_setpoint_slider_changed(self, val_x10: int):
        val = val_x10 / 10.0
        self.sp_val_label.setText(f"{val:.2f} mm")
        if abs(self.sp_spinbox.value() - val) > 1e-2:
            self.sp_spinbox.blockSignals(True)
            self.sp_spinbox.setValue(val)
            self.sp_spinbox.blockSignals(False)

    def send_command(self, cmd_code: int):
        # Transmit target setpoint value first if starting motion
        if cmd_code == 1:
            target_sp = self.sp_spinbox.value()
            self.modbus_worker.queue_setpoint(target_sp)

        self.modbus_worker.queue_command(cmd_code)

    def send_emergency_stop(self):
        self.modbus_worker.queue_emergency()
        self.append_log("🚨 EMERGENCY STOP ACTIVATED FROM SUPERVISORY UI!")

    def apply_pid_gains(self):
        kp = self.kp_spin.value()
        ki = self.ki_spin.value()
        kd = self.kd_spin.value()
        self.modbus_worker.queue_pid_gains(kp, ki, kd)

    def append_log(self, text: str):
        timestamp_str = time.strftime("[%H:%M:%S]")
        self.log_console.append(f"{timestamp_str} {text}")

    def closeEvent(self, event):
        self.modbus_worker.stop_thread()
        event.accept()
