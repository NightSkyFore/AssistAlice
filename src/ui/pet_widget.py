import os
import sys

os.environ["QT_QPA_PLATFORM"] = "xcb"

from PySide6.QtWidgets import QApplication, QWidget, QMainWindow
from PySide6.QtGui import QPixmap, QPainter, QMouseEvent, QWheelEvent
from PySide6.QtCore import Qt

EMOTIONS = {
    "general": "./assets/Elf-Alice-general.png",
    "smile": "./assets/Elf-Alice-smile.png",
    "sad": "./assets/Elf-Alice-cry.png",
    "angry": "./assets/Elf-Alice-angry.png",
    "confuse": "./assets/Elf-Alice-confuse.png",
    "think": "./assets/Elf-Alice-think.png"
}

class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()

        # FramelessWindowHint: 剥离操作系统的窗口边框（标题栏等）
        # WindowStaysOnTopHint: 永远置顶
        # Tool: 作为一个工具窗口存在
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        # 透明窗口
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.raw_pixmap = QPixmap(EMOTIONS["general"])
        if self.raw_pixmap.isNull():
            print(f"Error: No image!")
            sys.exit(1)
        self.scale = 0.3 
        self.min_scale = 0.2
        self.max_scale = 2.0
        self.update_pet_size()
        self.move_to_bottom_right()

    def update_pet_size(self):
        width = int(self.raw_pixmap.width() * self.scale)
        height = int(self.raw_pixmap.height() * self.scale)

        # 缩放图片（使用平滑缩放算法）
        self.pixmap = self.raw_pixmap.scaled(
            width, height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.resize(width, height)
        # self.pixmap.mask() 会提取 PNG 图片中非透明的像素轮廓。
        # setMask 会强制将窗口的“输入区域 (Input Region)”设定为这个轮廓。       
        self.setMask(self.pixmap.mask())
        # force render
        self.update()
    
    def move_to_bottom_right(self):
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        margin_x = 30
        target_x = screen_geometry.width() - self.width() - margin_x
        target_y = screen_geometry.height() - self.height()
        self.move(target_x, target_y)

    def paintEvent(self, event):
        """
        每当窗口需要重绘时（例如初次显示、被遮挡后露出、或者手动调用 self.update() 时），
        系统会自动调用这个函数。
        """
        painter = QPainter(self)
        
        # 开启抗锯齿（如果你后续对图片进行旋转或缩放，这会让边缘更平滑）
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # 开启平滑像素变换
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        # 在当前 Widget 的 (0, 0) 坐标处，把 pixmap 画上去
        painter.drawPixmap(0, 0, self.pixmap)

    def mousePressEvent(self, event: QMouseEvent):
        # 当左键按下时，直接呼叫底层操作系统（KWin）接管拖拽操作
        if event.button() == Qt.MouseButton.LeftButton:
            # 获取当前窗口的系统底层句柄，并启动系统级移动
            window = self.windowHandle()
            if window:
                window.startSystemMove()
            event.accept()
    
    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() == Qt.ControlModifier:
            angle = event.angleDelta().y()
            if angle > 0:
                self.scale += 0.1
            else:
                self.scale -= 0.1
            self.scale = max(self.min_scale, min(self.max_scale, self.scale))
            self.update_pet_size()
            event.accept()
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("AIAssistant")
    win = QMainWindow()
    win.show()
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec())
