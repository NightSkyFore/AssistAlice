from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal

class TrayIcon(QSystemTrayIcon):
    show_main = Signal()
    show_pet = Signal()
    tray_quit = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_map = {
            "normal": "./assets/tray_icon.png",
            "record": "./assets/tray_icon_record.png",
            "rest": "./assets/tray_icon_rest.png",
            "leaving": "./assets/tray_icon_leave.png",
        }
        self.setIcon(QIcon(self.icon_map["normal"]))
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

    def toggle_record_status(self, checked: bool):
        if checked:
            self.setIcon(QIcon(self.icon_map["record"]))   
            self.record_status = True
        else:
            self.setIcon(QIcon(self.icon_map["normal"]))
            self.record_status = False

    def toggle_leave_status(self, status: str):
        if self.record_status:
            return
        if status not in self.icon_map.keys():
            status = "normal"
        else:
            self.setIcon(QIcon(self.icon_map[status]))
