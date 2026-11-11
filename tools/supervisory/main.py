#!/usr/bin/env python3
"""
Linear Guide Actuator - Modbus RTU (USB Serial) Supervisory (SCADA) UI Entry Point
"""
import sys
from PyQt6.QtWidgets import QApplication
from tools.supervisory.ui_main import SupervisoryMainWindow


def main():
    app = QApplication(sys.argv)
    window = SupervisoryMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
