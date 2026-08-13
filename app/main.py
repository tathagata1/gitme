"""Qt application bootstrap."""

import sys

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("Git Visual")
    application.setOrganizationName("Git Visual")
    window = MainWindow()
    window.show()
    return application.exec()

