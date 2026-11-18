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

from tools.supervisory.modbus_worker import (
    ModbusWorker, list_serial_ports, DEFAULT_SERIAL_PORT, DEFAULT_BAUDRATE
)
from tools.supervisory.curve_utils import compute_normalized_curve, compute_sine_setpoint

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

# Light Theme QSS Stylesheet
LIGHT_STYLESHEET = """
QMainWindow {
    background-color: #F0F2F6;
}
QWidget {
    background-color: #F8F9FB;
    color: #24273A;
    font-family: "Segoe UI", "Roboto", "Helvetica Neue", sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #CCD0DA;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
    color: #1E66F5;
    background-color: #FFFFFF;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 8px;
    background-color: #E6E9EF;
    border-radius: 4px;
    color: #1E66F5;
}
QPushButton {
    background-color: #E6E9EF;
    color: #24273A;
    border: 1px solid #BCC0CC;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #DCE0E8;
    border-color: #1E66F5;
}
QPushButton:pressed {
    background-color: #CCD0DA;
}
QPushButton#theme_btn {
    background-color: #E6E9EF;
    color: #24273A;
    border: 1px solid #BCC0CC;
    font-size: 12px;
    padding: 6px 10px;
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
    background-color: #E6E9EF;
    color: #9CA0B0;
    border-color: #DCE0E8;
}
QPushButton#export_btn {
    background-color: #00796B;
    color: #FFFFFF;
}
QPushButton#export_btn:hover {
    background-color: #00897B;
}
QPushButton#export_btn:disabled {
    background-color: #E6E9EF;
    color: #9CA0B0;
}
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #CCD0DA;
    border-radius: 4px;
    padding: 4px 8px;
    color: #24273A;
}
QComboBox::drop-down {
    border: none;
}
QTextEdit {
    background-color: #FFFFFF;
    border: 1px solid #CCD0DA;
    border-radius: 6px;
    color: #313244;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
}
QSlider::groove:horizontal {
    border: 1px solid #CCD0DA;
    height: 8px;
    background: #E6E9EF;
    border-radius: 4px;
}
QSlider::sub-page:horizontal {
    background: #1E66F5;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #7287FD;
    border: 1px solid #1E66F5;
    width: 18px;
    margin-top: -6px;
    margin-bottom: -6px;
    border-radius: 9px;
}
"""


class StatusBadge(QLabel):
    """Custom pill badge widget for visual status rendering."""

    STATE_MAP_DARK = {
        0: ("IDLE", "#6C7086", "#181825"),
        1: ("MOVING", "#A6E3A1", "#1E3A29"),
        2: ("EMERGENCY", "#F38BA8", "#3A1E24"),
        3: ("HOMING", "#89B4FA", "#1E2A38"),
        4: ("OPEN_LOOP", "#FAB387", "#3A281E")
    }

    STATE_MAP_LIGHT = {
        0: ("IDLE", "#5C5F77", "#E6E9EF"),
        1: ("MOVING", "#1B8A38", "#E8F5E9"),
        2: ("EMERGENCY", "#D20F39", "#FFEBEE"),
        3: ("HOMING", "#1E66F5", "#E3F2FD"),
        4: ("OPEN_LOOP", "#DF8E1D", "#FFF3E0")
    }

    def __init__(self, text="DISCONNECTED", text_color="#CDD6F4", bg_color="#313244", parent=None):
        super().__init__(text, parent)
        self.current_theme = "dark"
        self._last_state = 0
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_colors(text_color, bg_color)
        self.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))

    def set_theme(self, theme: str):
        self.current_theme = theme

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
        self._last_state = state_code
        state_map = self.STATE_MAP_LIGHT if self.current_theme == "light" else self.STATE_MAP_DARK
        text, fg, bg = state_map.get(state_code, (f"UNKNOWN ({state_code})", "#F9E2AF", "#3A3524"))
        self.setText(f"STATE: {text}")
        self.set_colors(fg, bg)

class DigitalDisplayCard(QFrame):
    """Modern digital telemetry meter card displaying a metric value and engineering unit."""

    def __init__(self, title: str, unit: str = "", accent_color: str = "#89B4FA", parent=None):
        super().__init__(parent)
        self.title_text = title
        self.unit_text = unit
        self.accent_color = accent_color
        self._current_color = accent_color
        self.current_theme = "dark"

        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        # Title Label
        self.title_label = QLabel(title.upper())
        self.title_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # Value & Unit Row
        val_unit_layout = QHBoxLayout()
        val_unit_layout.setSpacing(4)
        val_unit_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.value_label = QLabel("--")
        self.value_label.setFont(QFont("Consolas", 18, QFont.Weight.Bold))
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val_unit_layout.addWidget(self.value_label)

        if unit:
            self.unit_label = QLabel(unit)
            self.unit_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Normal))
            self.unit_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
            val_unit_layout.addWidget(self.unit_label)
        else:
            self.unit_label = None

        layout.addLayout(val_unit_layout)

        self.set_theme("dark")

    def set_theme(self, theme: str):
        self.current_theme = theme
        bg = "#FFFFFF" if theme == "light" else "#181825"
        border = "#CCD0DA" if theme == "light" else "#313244"
        title_color = "#5C5F77" if theme == "light" else "#A6ADC8"
        unit_color = "#7C7F93" if theme == "light" else "#6C7086"
        self.setStyleSheet(f"""
            DigitalDisplayCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-top: 3px solid {self._current_color};
                border-radius: 8px;
                padding: 4px;
            }}
        """)
        self.title_label.setStyleSheet(f"color: {title_color}; background: transparent; border: none;")
        self.value_label.setStyleSheet(f"color: {self._current_color}; background: transparent; border: none;")
        if self.unit_label:
            self.unit_label.setStyleSheet(f"color: {unit_color}; background: transparent; border: none;")

    def set_value(self, val_text: str, custom_color: str | None = None):
        self.value_label.setText(val_text)
        color = custom_color if custom_color else self.accent_color
        if color != self._current_color:
            self._current_color = color
            self.value_label.setStyleSheet(f"color: {color}; background: transparent; border: none;")
            self.set_theme(self.current_theme)

    def get_value(self) -> str:
        return self.value_label.text()

    def get_unit(self) -> str:
        return self.unit_label.text() if self.unit_label else ""


class SupervisoryMainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Linear Guide Actuator - Modbus RTU (USB Serial) Supervisory (SCADA)")
        self.resize(1280, 800)

        # Theme Tracking ("dark" or "light")
        self.current_theme = "dark"

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
        self.modbus_worker.burst_status_changed.connect(self.on_burst_status_changed)
        self.modbus_worker.log_message.connect(self.append_log)
        self.modbus_worker.start()

        # Open-Loop Test State
        self.last_burst_samples: List[Dict[str, Any]] = []
        self.collected_curves: List[List[Dict[str, Any]]] = []
        self.latest_position: float = 0.0
        self.latest_machine_state: int = 0
        self._batch_active: bool = False
        self._batch_total: int = 1
        self._batch_pwm: float = 100.0
        self._batch_mode: int = 0
        self._batch_coast_pos: float = 400.0
        self._batch_phase: str = "IDLE"

        # Sine Wave Trajectory State (Closed-Loop)
        self._sine_active: bool = False
        self._sine_start_time: float = 0.0
        self._sine_timer = QTimer(self)
        self._sine_timer.setInterval(50)  # 20 Hz setpoint stream
        self._sine_timer.timeout.connect(self._on_sine_tick)

        # Build UI layout
        self.init_ui()
        self.append_log("🔌 Supervisório pronto (Modbus RTU via USB). Conecte o cabo USB-C do ESP32 e selecione a porta serial.")

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
        self.title_label = QLabel("🔌 LINEAR GUIDE SUPERVISORY (MODBUS RTU / USB)")
        self.title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #89B4FA;")
        layout.addWidget(self.title_label)

        layout.addStretch()

        # Serial Port ComboBox (editable, auto-populated with USB-UART devices)
        layout.addWidget(QLabel("Serial:"))
        self.serial_combo = QComboBox()
        self.serial_combo.setEditable(True)
        self.serial_combo.setMinimumWidth(150)
        self.serial_combo.setToolTip("Porta serial USB do ESP32 (ex: /dev/ttyUSB0, /dev/ttyACM0)")
        layout.addWidget(self.serial_combo)

        self.refresh_ports_btn = QPushButton("⟳")
        self.refresh_ports_btn.setToolTip("Atualizar lista de portas seriais")
        self.refresh_ports_btn.setFixedWidth(36)
        self.refresh_ports_btn.clicked.connect(self.refresh_serial_ports)
        layout.addWidget(self.refresh_ports_btn)

        # Baudrate ComboBox
        layout.addWidget(QLabel("Baud:"))
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400"])
        self.baud_combo.setCurrentText(str(DEFAULT_BAUDRATE))
        layout.addWidget(self.baud_combo)

        self.refresh_serial_ports()

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

        # Theme Toggle Button (Light Mode / Dark Mode)
        self.theme_btn = QPushButton("☀️ Modo Claro")
        self.theme_btn.setObjectName("theme_btn")
        self.theme_btn.setToolTip("Alternar para o Modo Claro")
        self.theme_btn.clicked.connect(self.toggle_theme)
        layout.addWidget(self.theme_btn)

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

        # A2. Sine Wave Trajectory Group Box (Closed-Loop Setpoint Stream)
        sine_box = QGroupBox("Trajetória Senoidal (Malha Fechada)")
        sine_layout = QVBoxLayout(sine_box)

        sine_grid = QGridLayout()
        sine_grid.addWidget(QLabel("Centro (mm):"), 0, 0)
        self.spin_sine_center = QDoubleSpinBox()
        self.spin_sine_center.setRange(0.0, 670.0)
        self.spin_sine_center.setSingleStep(10.0)
        self.spin_sine_center.setDecimals(1)
        self.spin_sine_center.setValue(300.0)
        sine_grid.addWidget(self.spin_sine_center, 0, 1)

        sine_grid.addWidget(QLabel("Amplitude (mm):"), 0, 2)
        self.spin_sine_amp = QDoubleSpinBox()
        self.spin_sine_amp.setRange(1.0, 335.0)
        self.spin_sine_amp.setSingleStep(10.0)
        self.spin_sine_amp.setDecimals(1)
        self.spin_sine_amp.setValue(150.0)
        sine_grid.addWidget(self.spin_sine_amp, 0, 3)

        sine_grid.addWidget(QLabel("Freq (Hz):"), 1, 0)
        self.spin_sine_freq = QDoubleSpinBox()
        self.spin_sine_freq.setRange(0.05, 2.00)
        self.spin_sine_freq.setSingleStep(0.05)
        self.spin_sine_freq.setDecimals(2)
        self.spin_sine_freq.setValue(0.20)
        sine_grid.addWidget(self.spin_sine_freq, 1, 1)

        sine_grid.addWidget(QLabel("Ciclos (0=∞):"), 1, 2)
        self.spin_sine_cycles = QSpinBox()
        self.spin_sine_cycles.setRange(0, 100)
        self.spin_sine_cycles.setValue(0)
        sine_grid.addWidget(self.spin_sine_cycles, 1, 3)
        sine_layout.addLayout(sine_grid)

        sine_btn_layout = QHBoxLayout()
        self.btn_sine_start = QPushButton("〰️ Iniciar Senoide")
        self.btn_sine_start.setObjectName("start_btn")
        self.btn_sine_start.clicked.connect(self.start_sine_wave)
        sine_btn_layout.addWidget(self.btn_sine_start)

        self.btn_sine_stop = QPushButton("⏹ Parar Senoide")
        self.btn_sine_stop.setEnabled(False)
        self.btn_sine_stop.clicked.connect(lambda: self.stop_sine_wave("Parada solicitada pelo operador."))
        sine_btn_layout.addWidget(self.btn_sine_stop)
        sine_layout.addLayout(sine_btn_layout)

        self.lbl_sine_status = QLabel("Senoide: Inativa")
        self.lbl_sine_status.setStyleSheet("color: #A6ADC8; font-size: 11px;")
        sine_layout.addWidget(self.lbl_sine_status)

        layout.addWidget(sine_box)

        # Open-Loop Step Response Group Box (System Identification)
        open_loop_box = QGroupBox("Open-Loop Step Test (System Identification)")
        ol_layout = QVBoxLayout(open_loop_box)

        self.lbl_open_loop_cond = QLabel("Condition: Waiting for telemetry (|pos| <= 5.0 mm and IDLE)...")
        self.lbl_open_loop_cond.setStyleSheet("color: #A6ADC8; font-size: 11px;")
        ol_layout.addWidget(self.lbl_open_loop_cond)

        ol_params_layout = QHBoxLayout()
        ol_params_layout.addWidget(QLabel("Degrau PWM:"))
        self.spin_ol_pwm = QDoubleSpinBox()
        self.spin_ol_pwm.setRange(1.0, 100.0)
        self.spin_ol_pwm.setSingleStep(5.0)
        self.spin_ol_pwm.setDecimals(1)
        self.spin_ol_pwm.setValue(100.0)
        self.spin_ol_pwm.setSuffix(" %")
        self.spin_ol_pwm.valueChanged.connect(self._update_open_loop_button_label)
        ol_params_layout.addWidget(self.spin_ol_pwm)

        ol_params_layout.addWidget(QLabel("Curvas (N):"))
        self.spin_ol_curves = QSpinBox()
        self.spin_ol_curves.setRange(1, 50)
        self.spin_ol_curves.setValue(1)
        self.spin_ol_curves.valueChanged.connect(self._update_open_loop_button_label)
        ol_params_layout.addWidget(self.spin_ol_curves)
        ol_layout.addLayout(ol_params_layout)

        ol_mode_layout = QHBoxLayout()
        ol_mode_layout.addWidget(QLabel("Modo:"))
        self.combo_ol_mode = QComboBox()
        self.combo_ol_mode.addItem("Freio Ativo (536 mm)", 0)
        self.combo_ol_mode.addItem("Parada Natural (Degrau -> 0%)", 1)
        self.combo_ol_mode.currentIndexChanged.connect(self._on_open_loop_mode_changed)
        ol_mode_layout.addWidget(self.combo_ol_mode, stretch=2)

        ol_mode_layout.addWidget(QLabel("Corte 0%:"))
        self.spin_ol_coast_pos = QDoubleSpinBox()
        self.spin_ol_coast_pos.setRange(50.0, 536.0)
        self.spin_ol_coast_pos.setSingleStep(10.0)
        self.spin_ol_coast_pos.setDecimals(1)
        self.spin_ol_coast_pos.setValue(400.0)
        self.spin_ol_coast_pos.setSuffix(" mm")
        self.spin_ol_coast_pos.setEnabled(False)
        self.spin_ol_coast_pos.valueChanged.connect(self._update_open_loop_button_label)
        ol_mode_layout.addWidget(self.spin_ol_coast_pos, stretch=1)
        ol_layout.addLayout(ol_mode_layout)

        ol_btn_layout = QHBoxLayout()
        self.btn_open_loop = QPushButton("🚀 RUN STEP TEST (100.0% PWM -> 536 mm / 80%)")
        self.btn_open_loop.setObjectName("openloop_btn")
        self.btn_open_loop.setEnabled(False)
        self.btn_open_loop.clicked.connect(self.start_open_loop_test)
        ol_btn_layout.addWidget(self.btn_open_loop, stretch=2)

        self.btn_export_csv = QPushButton("💾 Export CSV")
        self.btn_export_csv.setObjectName("export_btn")
        self.btn_export_csv.setEnabled(False)
        self.btn_export_csv.clicked.connect(self.export_csv_manually)
        ol_btn_layout.addWidget(self.btn_export_csv, stretch=1)

        self.btn_export_norm_csv = QPushButton("📈 Export Normalizada")
        self.btn_export_norm_csv.setObjectName("export_btn")
        self.btn_export_norm_csv.setEnabled(False)
        self.btn_export_norm_csv.clicked.connect(self.export_normalized_csv_manually)
        ol_btn_layout.addWidget(self.btn_export_norm_csv, stretch=1)

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
        layout.setSpacing(10)

        # 1. Top Real-Time Digital Telemetry Display Cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(8)

        self.card_pos = DigitalDisplayCard("Posição Atual", unit="mm", accent_color="#A6E3A1")
        self.card_sp = DigitalDisplayCard("Setpoint Alvo", unit="mm", accent_color="#89B4FA")
        self.card_err = DigitalDisplayCard("Erro (SP - PV)", unit="mm", accent_color="#F9E2AF")
        self.card_vel = DigitalDisplayCard("Velocidade", unit="mm/s", accent_color="#FAB387")
        self.card_duty = DigitalDisplayCard("Esforço PWM", unit="%", accent_color="#CBA6F7")

        cards_layout.addWidget(self.card_pos)
        cards_layout.addWidget(self.card_sp)
        cards_layout.addWidget(self.card_err)
        cards_layout.addWidget(self.card_vel)
        cards_layout.addWidget(self.card_duty)

        layout.addLayout(cards_layout)

        # 2. Graph Controls Toolbar (Max Points SpinBox & Clear Button)
        graph_toolbar = QHBoxLayout()
        graph_toolbar.setSpacing(10)

        self.lbl_buffer = QLabel("Buffer dos Gráficos:")
        self.lbl_buffer.setStyleSheet("color: #A6ADC8; font-weight: bold;")
        graph_toolbar.addWidget(self.lbl_buffer)

        self.spin_max_points = QSpinBox()
        self.spin_max_points.setRange(50, 3000)
        self.spin_max_points.setValue(self.max_points)
        self.spin_max_points.setSingleStep(50)
        self.spin_max_points.setSuffix(" pts")
        self.spin_max_points.setToolTip("Quantidade máxima de pontos mantidos no histórico dos gráficos (FIFO circular)")
        self.spin_max_points.valueChanged.connect(self.on_max_points_changed)
        graph_toolbar.addWidget(self.spin_max_points)

        self.btn_clear_graphs = QPushButton("🗑️ Limpar Gráficos")
        self.btn_clear_graphs.setToolTip("Limpar histórico e traçados dos gráficos")
        self.btn_clear_graphs.clicked.connect(self.clear_graphs)
        graph_toolbar.addWidget(self.btn_clear_graphs)

        graph_toolbar.addStretch()

        self.lbl_points_info = QLabel(f"Pontos exibidos: 0 / {self.max_points}")
        self.lbl_points_info.setStyleSheet("color: #6C7086; font-size: 11px;")
        graph_toolbar.addWidget(self.lbl_points_info)

        layout.addLayout(graph_toolbar)

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

    def refresh_serial_ports(self):
        current = self.serial_combo.currentText().strip()
        ports = list_serial_ports()
        self.serial_combo.clear()
        self.serial_combo.addItems(ports if ports else [DEFAULT_SERIAL_PORT])
        if current:
            self.serial_combo.setCurrentText(current)

    def toggle_theme(self):
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self.set_theme(new_theme)

    def set_theme(self, theme_name: str):
        self.current_theme = theme_name
        is_light = (theme_name == "light")
        self.setStyleSheet(LIGHT_STYLESHEET if is_light else DARK_STYLESHEET)

        # Update button text & tooltip
        if hasattr(self, 'theme_btn'):
            self.theme_btn.setText("🌙 Modo Escuro" if is_light else "☀️ Modo Claro")
            self.theme_btn.setToolTip("Alternar para o Modo Escuro" if is_light else "Alternar para o Modo Claro")

        # Update title colors
        if hasattr(self, 'title_label'):
            title_color = "#1E66F5" if is_light else "#89B4FA"
            self.title_label.setStyleSheet(f"color: {title_color};")
        if hasattr(self, 'sp_val_label'):
            sp_color = "#1E66F5" if is_light else "#89B4FA"
            self.sp_val_label.setStyleSheet(f"color: {sp_color}; font-weight: bold;")
        if hasattr(self, 'lbl_buffer'):
            buf_color = "#4C4F69" if is_light else "#A6ADC8"
            self.lbl_buffer.setStyleSheet(f"color: {buf_color}; font-weight: bold;")
        if hasattr(self, 'lbl_points_info'):
            pts_color = "#5C5F77" if is_light else "#6C7086"
            self.lbl_points_info.setStyleSheet(f"color: {pts_color}; font-size: 11px;")

        # Update DigitalDisplayCards
        if hasattr(self, 'card_pos'):
            for card in [self.card_pos, self.card_sp, self.card_err, self.card_vel, self.card_duty]:
                card.set_theme(theme_name)

        # Update Badges
        if hasattr(self, 'conn_badge'):
            self.conn_badge.set_theme(theme_name)
            if self.modbus_worker._connected:
                self.conn_badge.setText("CONNECTED")
                self.conn_badge.set_colors("#1B8A38" if is_light else "#A6E3A1", "#E8F5E9" if is_light else "#1E3A29")
            else:
                self.conn_badge.setText("DISCONNECTED")
                self.conn_badge.set_colors("#D20F39" if is_light else "#F38BA8", "#FFEBEE" if is_light else "#313244")

        if hasattr(self, 'state_badge'):
            self.state_badge.set_theme(theme_name)
            self.state_badge.update_machine_state(self.latest_machine_state)

        # Update PyQtGraph background & foreground
        if hasattr(self, 'graph_widget'):
            bg_color = '#FFFFFF' if is_light else '#181825'
            fg_color = '#24273A' if is_light else '#CDD6F4'
            grid_alpha = 0.2 if is_light else 0.3

            self.graph_widget.setBackground(bg_color)
            for plot in [self.plot_pos, self.plot_vel, self.plot_duty]:
                plot.getAxis('left').setTextPen(fg_color)
                plot.getAxis('left').setPen(fg_color)
                plot.getAxis('bottom').setTextPen(fg_color)
                plot.getAxis('bottom').setPen(fg_color)
                plot.showGrid(x=True, y=True, alpha=grid_alpha)

            # Update curve pens
            sp_color = '#1E66F5' if is_light else '#89B4FA'
            pos_color = '#1B8A38' if is_light else '#A6E3A1'
            vel_color = '#D9730D' if is_light else '#FAB387'
            duty_color = '#8839EF' if is_light else '#CBA6F7'
            self.curve_setpoint.setPen(pg.mkPen(color=sp_color, width=2, style=Qt.PenStyle.DashLine))
            self.curve_position.setPen(pg.mkPen(color=pos_color, width=2.5))
            self.curve_velocity.setPen(pg.mkPen(color=vel_color, width=2))
            self.curve_duty.setPen(pg.mkPen(color=duty_color, width=2))

        self.append_log(f"🎨 Tema alterado para: {'Modo Claro' if is_light else 'Modo Escuro'}.")

    def toggle_connection(self):
        if not self.modbus_worker._user_wants_connected and not self.modbus_worker._connected:
            serial_port = self.serial_combo.currentText().strip()
            baudrate = int(self.baud_combo.currentText())
            slave_id = self.slave_spin.value()
            self.modbus_worker.set_connection_params(serial_port, baudrate, slave_id)
            self.modbus_worker.connect_modbus()
        else:
            self.modbus_worker.disconnect_modbus()

    @pyqtSlot(bool, str)
    def on_connection_status_changed(self, connected: bool, msg: str):
        is_light = (self.current_theme == "light")
        if connected:
            self.connect_btn.setText("DISCONNECT")
            self.connect_btn.setObjectName("disconnect_btn")
            self.conn_badge.setText("CONNECTED")
            self.conn_badge.set_colors("#1B8A38" if is_light else "#A6E3A1", "#E8F5E9" if is_light else "#1E3A29")
        else:
            self.connect_btn.setText("CONNECT")
            self.connect_btn.setObjectName("connect_btn")
            self.conn_badge.setText("DISCONNECTED")
            self.conn_badge.set_colors("#D20F39" if is_light else "#F38BA8", "#FFEBEE" if is_light else "#313244")
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

        # Update Digital Telemetry Display Cards
        error = sp - pos
        self.card_pos.set_value(f"{pos:.2f}")
        self.card_sp.set_value(f"{sp:.2f}")
        is_light = (self.current_theme == "light")
        in_pos_color = "#1B8A38" if is_light else "#A6E3A1"
        err_alert_color = "#DF8E1D" if is_light else "#F9E2AF"
        err_color = in_pos_color if abs(error) <= 0.1 else err_alert_color
        self.card_err.set_value(f"{error:+.2f}", custom_color=err_color)
        self.card_vel.set_value(f"{vel:.1f}")
        self.card_duty.set_value(f"{duty:+.1f}")

        # Update points count label
        if hasattr(self, 'lbl_points_info'):
            self.lbl_points_info.setText(f"Pontos exibidos: {len(self.time_history)} / {self.max_points}")

        # Update Machine State Badge
        self.state_badge.update_machine_state(state)

        # Update Hardware Status Labels (Active-HIGH hardware pin logic: 1 = Pressed/Tripped, 0 = Safe/Released)
        estop_tripped = bool(data["estop_button"])
        estop_str = "ACTIVE 🚨" if estop_tripped else "OK"
        is_light = (self.current_theme == "light")
        if estop_tripped:
            estop_color = "#D20F39" if is_light else "#F38BA8"
        else:
            estop_color = "#1B8A38" if is_light else "#A6E3A1"
        self.lbl_hw_estop.setText(f"E-Stop Pin: <font color='{estop_color}'><b>{estop_str}</b></font>")

        start_pressed = bool(data["start_button"])
        start_str = "PRESSED" if start_pressed else "RELEASED"
        start_color = "#1E66F5" if (start_pressed and is_light) else "#89B4FA" if start_pressed else ("#5C5F77" if is_light else "#CDD6F4")
        self.lbl_hw_start.setText(f"Start Pin: <font color='{start_color}'><b>{start_str}</b></font>")

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
        if self._sine_active and (state == 2 or not self.modbus_worker._connected):
            self.stop_sine_wave("Emergência ou desconexão detectada.")
        can_start_ol = (abs(pos) <= 5.0) and (state == 0) and self.modbus_worker._connected and (not self._batch_active)
        self.btn_open_loop.setEnabled(can_start_ol)
        self.spin_ol_pwm.setEnabled(not self._batch_active)
        self.spin_ol_curves.setEnabled(not self._batch_active)
        self.combo_ol_mode.setEnabled(not self._batch_active)
        self.spin_ol_coast_pos.setEnabled((not self._batch_active) and (self.combo_ol_mode.currentData() == 1))

        if self._batch_active:
            if state == 2:
                self._abort_batch("Emergência detectada durante coleta em lote.")
            elif self._batch_phase == "WAITING_HOME":
                self.lbl_open_loop_cond.setText(
                    f"Status: <font color='#89B4FA'><b>Curva {len(self.collected_curves)}/{self._batch_total} — Retornando ao Home...</b></font>"
                )
                if state == 0 and abs(pos) <= 5.0:
                    self._batch_phase = "SETTLING"
                    QTimer.singleShot(500, self._start_next_batch_run)
            elif self._batch_phase == "SETTLING":
                self.lbl_open_loop_cond.setText(
                    f"Status: <font color='#89B4FA'><b>Estabilizando para curva {len(self.collected_curves) + 1}/{self._batch_total}...</b></font>"
                )
            else:
                self.lbl_open_loop_cond.setText(
                    f"Status: <font color='#FAB387'><b>Coletando curva {len(self.collected_curves) + 1}/{self._batch_total} ({self._batch_pwm:.1f}% PWM)...</b></font>"
                )
        elif state == 4:
            self.lbl_open_loop_cond.setText(f"Status: <font color='#FAB387'><b>TEST RUNNING ({self.spin_ol_pwm.value():.1f}% PWM -> 536 mm / 80%)...</b></font>")
        elif can_start_ol:
            self.lbl_open_loop_cond.setText("Condition: <font color='#A6E3A1'><b>READY (|pos| <= 5.0 mm and IDLE)</b></font>")
        elif abs(pos) > 5.0:
            self.lbl_open_loop_cond.setText(f"Condition: <font color='#F38BA8'>Blocked (|pos| = {pos:.2f} mm > 5.0 mm, move to 0)</font>")
        elif state != 0:
            self.lbl_open_loop_cond.setText("Condition: <font color='#F9E2AF'>Blocked (machine must be in IDLE)</font>")
        else:
            self.lbl_open_loop_cond.setText("Condition: <font color='#6C7086'>Waiting for connection...</font>")

    def _on_open_loop_mode_changed(self):
        is_coast = (self.combo_ol_mode.currentData() == 1)
        self.spin_ol_coast_pos.setEnabled((not self._batch_active) and is_coast)
        self._update_open_loop_button_label()

    def _update_open_loop_button_label(self):
        pwm = self.spin_ol_pwm.value()
        n = self.spin_ol_curves.value()
        is_coast = (self.combo_ol_mode.currentData() == 1)
        target_str = f"{self.spin_ol_coast_pos.value():.0f} mm -> 0%" if is_coast else "536 mm / 80%"
        if n > 1:
            self.btn_open_loop.setText(f"🚀 RUN {n} CURVES ({pwm:.1f}% PWM -> {target_str})")
        else:
            self.btn_open_loop.setText(f"🚀 RUN STEP TEST ({pwm:.1f}% PWM -> {target_str})")

    def _abort_batch(self, reason: str):
        if not self._batch_active:
            return
        self._batch_active = False
        self._batch_phase = "IDLE"
        self.spin_ol_pwm.setEnabled(True)
        self.spin_ol_curves.setEnabled(True)
        self.combo_ol_mode.setEnabled(True)
        self.spin_ol_coast_pos.setEnabled(self.combo_ol_mode.currentData() == 1)
        self.append_log(f"⚠️ Coleta em lote interrompida ({len(self.collected_curves)}/{self._batch_total} curvas): {reason}")

    def _start_next_batch_run(self):
        if not self._batch_active or self._batch_phase != "SETTLING":
            return
        if not self.modbus_worker._connected or self.latest_machine_state != 0 or abs(self.latest_position) > 5.0:
            self._abort_batch("Condição de partida não atendida após Homing.")
            return
        next_idx = len(self.collected_curves) + 1
        self._batch_phase = "RUNNING_TEST"
        self.modbus_worker.queue_open_loop_test(self._batch_pwm, self._batch_mode, self._batch_coast_pos)
        self.append_log(f"🚀 Iniciando curva {next_idx}/{self._batch_total} ({self._batch_pwm:.1f}% PWM)...")

    @pyqtSlot(int, int)
    def on_burst_status_changed(self, burst_status: int, burst_count: int):
        if self._batch_active and burst_status == 3:
            self._abort_batch("Ensaio abortado pelo firmware (timeout ou emergência).")

    def start_open_loop_test(self):
        if not self.modbus_worker._connected:
            QMessageBox.warning(self, "Disconnected", "Connect to the Modbus RTU slave (USB serial) first.")
            return

        if abs(self.latest_position) > 5.0:
            QMessageBox.warning(
                self,
                "Position Pre-condition Blocked",
                f"Actuator position must be near zero (|pos| <= 5.0 mm).\nCurrent position: {self.latest_position:.2f} mm.\nPlease perform Homing or move near 0 mm."
            )
            return

        pwm_pct = self.spin_ol_pwm.value()
        num_curves = self.spin_ol_curves.value()
        mode = int(self.combo_ol_mode.currentData())
        coast_pos = self.spin_ol_coast_pos.value()
        batch_msg = f"Serão coletadas {num_curves} curvas consecutivas com retorno automático ao Home." if num_curves > 1 else "Será coletada 1 curva."
        mode_msg = (
            f"Modo: Parada Natural (degrau para 0% em {coast_pos:.1f} mm, sem freio ativo)."
            if mode == 1 else
            "Modo: Freio Ativo ao atingir 80% do curso (536.0 mm)."
        )

        reply = QMessageBox.question(
            self,
            "Confirm Open-Loop Step Test",
            f"Deseja iniciar o ensaio de malha aberta?\n\nNível de PWM: {pwm_pct:.1f}%\n{mode_msg}\n{batch_msg}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.collected_curves = []
            self._batch_active = True
            self._batch_total = num_curves
            self._batch_pwm = pwm_pct
            self._batch_mode = mode
            self._batch_coast_pos = coast_pos
            self._batch_phase = "RUNNING_TEST"
            self.modbus_worker.queue_open_loop_test(pwm_pct, mode, coast_pos)
            self.append_log(f"🚀 Iniciado ensaio de malha aberta (Curva 1/{num_curves}, {pwm_pct:.1f}% PWM, modo={'COAST' if mode == 1 else 'BRAKE'}).")

    @pyqtSlot(int)
    def on_max_points_changed(self, new_max: int):
        self.max_points = new_max
        self.time_history = deque(self.time_history, maxlen=new_max)
        self.setpoint_history = deque(self.setpoint_history, maxlen=new_max)
        self.position_history = deque(self.position_history, maxlen=new_max)
        self.velocity_history = deque(self.velocity_history, maxlen=new_max)
        self.duty_history = deque(self.duty_history, maxlen=new_max)

        # Refresh plots with resized data
        self.curve_setpoint.setData(list(self.time_history), list(self.setpoint_history))
        self.curve_position.setData(list(self.time_history), list(self.position_history))
        self.curve_velocity.setData(list(self.time_history), list(self.velocity_history))
        self.curve_duty.setData(list(self.time_history), list(self.duty_history))

        if hasattr(self, 'lbl_points_info'):
            self.lbl_points_info.setText(f"Pontos exibidos: {len(self.time_history)} / {self.max_points}")

    def clear_graphs(self):
        self.time_history.clear()
        self.setpoint_history.clear()
        self.position_history.clear()
        self.velocity_history.clear()
        self.duty_history.clear()

        self.curve_setpoint.setData([], [])
        self.curve_position.setData([], [])
        self.curve_velocity.setData([], [])
        self.curve_duty.setData([], [])

        if hasattr(self, 'lbl_points_info'):
            self.lbl_points_info.setText(f"Pontos exibidos: 0 / {self.max_points}")
        self.append_log("🧹 Gráficos de telemetria limpos pelo operador.")

    @pyqtSlot(list)
    def on_burst_data_ready(self, samples: List[Dict[str, Any]]):
        self.last_burst_samples = samples
        self.btn_export_csv.setEnabled(len(samples) > 0)
        self.append_log(f"📊 Recebidas {len(samples)} amostras de malha aberta do ESP32.")

        if samples:
            self._plot_burst_samples(samples)

        if self._batch_active:
            if samples:
                self.collected_curves.append(samples)
                self.btn_export_norm_csv.setEnabled(True)
            done_count = len(self.collected_curves)
            if done_count < self._batch_total:
                self.append_log(f"✅ Curva {done_count}/{self._batch_total} concluída. Retornando ao Home para a próxima...")
                self._batch_phase = "WAITING_HOME"
                self.modbus_worker.queue_command(4)  # CMD_HOME
                return

            # All N curves collected
            self._batch_active = False
            self._batch_phase = "IDLE"
            self.spin_ol_pwm.setEnabled(True)
            self.spin_ol_curves.setEnabled(True)
            self.combo_ol_mode.setEnabled(True)
            self.spin_ol_coast_pos.setEnabled(self.combo_ol_mode.currentData() == 1)

            if self._batch_total > 1:
                self.append_log(f"🎉 Coleta de {done_count} curvas concluída! Gerando curva normalizada...")
                self.export_normalized_csv_manually()
                return

        if samples:
            self.collected_curves = [samples]
            self.btn_export_norm_csv.setEnabled(True)
            # Prompt for file save (single curve)
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "Salvar Curva de Malha Aberta",
                "curva_malha_aberta.csv",
                "Arquivos CSV (*.csv);;Todos os Arquivos (*)"
            )
            if filepath:
                self._write_csv_file(filepath, samples)

    def _plot_burst_samples(self, samples: List[Dict[str, Any]]):
        # Auto-expand buffer capacity if incoming burst exceeds current max_points
        if len(samples) > self.max_points:
            if len(samples) > self.spin_max_points.maximum():
                self.spin_max_points.setMaximum(len(samples))
            self.spin_max_points.setValue(len(samples))

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

        if hasattr(self, 'lbl_points_info'):
            self.lbl_points_info.setText(f"Pontos exibidos: {len(self.time_history)} / {self.max_points}")

    def export_normalized_csv_manually(self):
        curves = self.collected_curves if self.collected_curves else ([self.last_burst_samples] if self.last_burst_samples else [])
        if not curves:
            QMessageBox.information(self, "Sem Dados", "Nenhuma curva coletada até o momento.")
            return

        pwm_val = self._batch_pwm if self.collected_curves else self.spin_ol_pwm.value()
        norm_samples = compute_normalized_curve(curves, duty_pct=pwm_val)
        if not norm_samples:
            QMessageBox.warning(self, "Sem Dados", "Não foi possível gerar a curva normalizada.")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Curva Normalizada",
            "curva_malha_aberta_normalizada.csv",
            "Arquivos CSV (*.csv);;Todos os Arquivos (*)"
        )
        if filepath:
            self._write_normalized_csv_file(filepath, norm_samples)

    def _write_normalized_csv_file(self, filepath: str, norm_samples: List[Dict[str, Any]]):
        try:
            with open(filepath, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "time_s", "position_mean_mm", "velocity_mean_mm_s",
                    "position_norm", "velocity_norm", "duty_pct", "curve_count"
                ])
                for s in norm_samples:
                    writer.writerow([
                        s["time_s"], s["position_mean_mm"], s["velocity_mean_mm_s"],
                        s["position_norm"], s["velocity_norm"], s["duty_pct"], s["curve_count"]
                    ])
            self.append_log(f"📈 Curva normalizada salva com sucesso em {filepath}")
            QMessageBox.information(
                self,
                "Exportação Concluída",
                f"Curva normalizada salva com sucesso:\n{filepath}\nCurvas: {norm_samples[0]['curve_count']} | Pontos: {len(norm_samples)}"
            )
        except Exception as e:
            self.append_log(f"❌ Erro ao salvar curva normalizada: {e}")
            QMessageBox.critical(self, "Erro de Exportação", f"Não foi possível salvar o arquivo:\n{e}")

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
        if self._sine_active and cmd_code in (2, 3, 4):
            self.stop_sine_wave(f"Interrompida pelo comando {cmd_code}.")
        if cmd_code == 2 and self._batch_active:
            self._abort_batch("Parada manual solicitada pelo operador.")
        # Transmit target setpoint value first if starting motion
        if cmd_code == 1:
            target_sp = self.sp_spinbox.value()
            self.modbus_worker.queue_setpoint(target_sp)

        self.modbus_worker.queue_command(cmd_code)

    def send_emergency_stop(self):
        if self._sine_active:
            self.stop_sine_wave("Emergência acionada pelo operador.")
        if self._batch_active:
            self._abort_batch("Emergência acionada pelo operador.")
        self.modbus_worker.queue_emergency()
        self.append_log("🚨 EMERGENCY STOP ACTIVATED FROM SUPERVISORY UI!")

    def start_sine_wave(self):
        if not self.modbus_worker._connected:
            QMessageBox.warning(self, "Disconnected", "Connect to the Modbus RTU slave first.")
            return
        if self._batch_active or self.latest_machine_state in (2, 3, 4):
            QMessageBox.warning(self, "Blocked", "Machine must be in IDLE or MOVING (no fault/homing/open-loop active).")
            return

        center = self.spin_sine_center.value()
        amp = self.spin_sine_amp.value()
        freq = self.spin_sine_freq.value()
        cycles = self.spin_sine_cycles.value()

        self._sine_active = True
        self._sine_start_time = time.time()
        self.btn_sine_start.setEnabled(False)
        self.btn_sine_stop.setEnabled(True)
        self.spin_sine_center.setEnabled(False)
        self.spin_sine_amp.setEnabled(False)
        self.spin_sine_freq.setEnabled(False)
        self.spin_sine_cycles.setEnabled(False)

        sp0 = compute_sine_setpoint(0.0, center, amp, freq)
        self.sp_spinbox.setValue(sp0)
        self.modbus_worker.queue_setpoint(sp0)
        if self.latest_machine_state != 1:
            self.modbus_worker.queue_command(1)  # CMD_START
        self._sine_timer.start()
        cyc_str = f"{cycles} ciclos" if cycles > 0 else "contínuo"
        self.lbl_sine_status.setText(f"Senoide: <font color='#A6E3A1'><b>ATIVA ({center:.1f} ± {amp:.1f} mm @ {freq:.2f} Hz, {cyc_str})</b></font>")
        self.append_log(f"〰️ Senoide iniciada: centro={center:.1f} mm, amp={amp:.1f} mm, freq={freq:.2f} Hz ({cyc_str}).")

    def stop_sine_wave(self, reason: str = ""):
        if not self._sine_active:
            return
        self._sine_timer.stop()
        self._sine_active = False
        self.btn_sine_start.setEnabled(True)
        self.btn_sine_stop.setEnabled(False)
        self.spin_sine_center.setEnabled(True)
        self.spin_sine_amp.setEnabled(True)
        self.spin_sine_freq.setEnabled(True)
        self.spin_sine_cycles.setEnabled(True)
        self.lbl_sine_status.setText("Senoide: Inativa")
        if reason:
            self.append_log(f"⏹ Senoide encerrada: {reason}")

    def _on_sine_tick(self):
        if not self._sine_active:
            return
        elapsed = time.time() - self._sine_start_time
        center = self.spin_sine_center.value()
        amp = self.spin_sine_amp.value()
        freq = self.spin_sine_freq.value()
        cycles = self.spin_sine_cycles.value()

        if cycles > 0 and elapsed * freq >= cycles:
            final_sp = compute_sine_setpoint(0.0, center, amp, freq)
            self.sp_spinbox.setValue(final_sp)
            self.modbus_worker.queue_setpoint(final_sp)
            self.stop_sine_wave(f"{cycles} ciclo(s) concluído(s).")
            return

        sp = compute_sine_setpoint(elapsed, center, amp, freq)
        self.sp_spinbox.setValue(sp)
        self.modbus_worker.queue_setpoint(sp)

    def apply_pid_gains(self):
        kp = self.kp_spin.value()
        ki = self.ki_spin.value()
        kd = self.kd_spin.value()
        self.modbus_worker.queue_pid_gains(kp, ki, kd)

    def append_log(self, text: str):
        timestamp_str = time.strftime("[%H:%M:%S]")
        self.log_console.append(f"{timestamp_str} {text}")

    def closeEvent(self, event):
        if self._sine_active:
            self._sine_timer.stop()
            self._sine_active = False
        self.modbus_worker.stop_thread()
        event.accept()
