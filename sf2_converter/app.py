"""PySide6 application bootstrap."""

import sys

from PySide6.QtWidgets import QApplication

from .gui.main_window import MainWindow


def run():
    app = QApplication(sys.argv)
    app.setApplicationName("SF2 to SLI/SLC Converter")
    app.setOrganizationName("Spectralis2Tools")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run()
