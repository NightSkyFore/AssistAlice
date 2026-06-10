import os
import sys

os.environ["QT_QPA_PLATFORM"] = "xcb"

from PySide6.QtWidgets import QApplication, QMainWindow

from ui.osd_subtitle import OSDHandleWindow, OSDTextWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("AI Assistant")
    win = QMainWindow()
    win.show()
    osd = OSDTextWindow()
    handle = OSDHandleWindow(osd)
    win.show()
    osd.show()
    handle.show()

    sentences = [
        "你好！我是 Alice。",
        "这是一个非常非常长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长长的测试句子，",
        "用来测试滑动窗口是否能完美将超出两行的文字顶上去，",
        "并保持画面的整洁与极客感。希望你喜欢这个效果！"
    ]
    for s in sentences:
        osd.feed_sentence(s)

    sys.exit(app.exec())
