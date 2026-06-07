import sys

from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
from PySide6.QtCore import QTimer, Qt

from ui.subtitle_label import SubtitleLabel

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.SubWindow |
            Qt.Tool
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = SubtitleLabel(parent=self)
        layout.addWidget(self.label)

        self.resize(900, 100)

        self.full_text = ""
        self.char_queue = []      # 等待打印的字符队列
        self.type_speed_ms = 40   # 每个字的弹出间隔（毫秒）
        self.type_timer = QTimer(self)
        self.type_timer.timeout.connect(self._type_next_char)

    def feed_sentence(self, sentence: str):
        self.char_queue.extend(list(sentence))
        
        # 如果打字机没在工作，启动它
        if not self.type_timer.isActive():
            self.type_timer.start(self.type_speed_ms)

    def _type_next_char(self):
        if self.char_queue:
            char = self.char_queue.pop(0)
            self.full_text += char
            self.label.set_text(self.full_text)
        else:
            self.type_timer.stop()
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("AI Assistant")
    win = TestWindow()
    win.show()

    sentences = [
        "你好！我是 Alice。",
        "这是一个非常非常长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长的测试句子，",
        "用来测试滑动窗口是否能完美将超出两行的文字顶上去，",
        "并保持画面的整洁与极客感。希望你喜欢这个效果！"
    ]
    for s in sentences:
        win.feed_sentence(s)


    sys.exit(app.exec())