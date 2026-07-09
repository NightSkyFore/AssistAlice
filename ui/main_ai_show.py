import sys
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter

class AIShow(QWidget):
    def __init__(self):
        super().__init__()
        self.pixmap = QPixmap("./assets/Elf-Alice.png")
        if self.pixmap.isNull():
            print(f"Error: No image!")
            sys.exit(1)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        pixmap_rect = self.pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        ).rect()

        # 居中画
        x = (self.width() - pixmap_rect.width()) / 2
        y = (self.height() - pixmap_rect.height()) / 2

        painter.drawPixmap(x, y, pixmap_rect.width(), pixmap_rect.height(), self.pixmap)

