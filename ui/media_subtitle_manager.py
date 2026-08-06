from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget, QApplication

from ui.osd_subtitle import OSDHandleWindow, OSDTextWindow

class MediaSubtitleManager(QObject):
    def __init__(self, parent: QWidget = None):
        super().__init__()

        self.osd = OSDTextWindow(parent)
        self.osd_handle = OSDHandleWindow(self.osd, parent)
        self._move_above_general_osd()
        self.hide_media_subtitle()

    def show_media_subtitle(self):
        self.osd.show()
        self.osd_handle.show()

    def hide_media_subtitle(self):
        self.osd.hide()
        self.osd_handle.hide()

    def osd_on_streaming(self, text: str):
        self.osd.feed_streaming(text)

    def _move_above_general_osd(self):
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        margin = 30
        target_x = (screen_geometry.width() - self.osd.width() - margin) / 2
        target_y = screen_geometry.height() - self.osd.height() * 2 - margin
        self.osd.move(target_x, target_y)
        self.osd_handle.move(target_x+self.osd.width(), target_y)
