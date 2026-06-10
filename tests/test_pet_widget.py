import os
import sys

os.environ["QT_QPA_PLATFORM"] = "xcb"

from PySide6.QtWidgets import QApplication, QMainWindow

from ui.pet_widget import DesktopPet

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("AI Assistant")
    win = QMainWindow()
    win.show()
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec())
