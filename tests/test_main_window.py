import os
import sys

os.environ["QT_QPA_PLATFORM"] = "xcb"

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("AI Assistant")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
