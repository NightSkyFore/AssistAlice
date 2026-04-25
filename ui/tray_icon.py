from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal

class TrayIcon(QSystemTrayIcon):
    show_main = Signal()
    show_pet = Signal()
    tray_quit = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon("./assets/tray_icon.png"))
        self.setToolTip("Alice AI Assistant")

        menu = QMenu()
        main_act = menu.addAction("General Mode")
        pet_act = menu.addAction("Desktop Pet Mode")
        menu.addSeparator()
        quit_act = menu.addAction("Quit")

        main_act.triggered.connect(self.show_main)
        pet_act.triggered.connect(self.show_pet)
        quit_act.triggered.connect(self.tray_quit)

        self.setContextMenu(menu)

        self.record_status = False

    def change_status(self):
        self.record_status = not self.record_status
        if self.record_status:
            self.setIcon(QIcon("./assets/tray_icon_record.png"))   
        else:
            self.setIcon(QIcon("./assets/tray_icon.png"))