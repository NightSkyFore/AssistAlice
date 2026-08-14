import sys
from PySide6.QtWidgets import QWidget, QApplication

from core.stt_nemotron_worker import NemotronSTTWorker

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)
        self.stt_worker = NemotronSTTWorker()
        self.stt_worker.text_signal.connect(self.on_streaming_text)
        self.stt_worker.start()

    def on_streaming_text(self, text):
        print(text)

    def closeEvent(self, event):
        self.stt_worker.stop()
        return super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("AI Assistant")
    win = TestWindow()
    win.show()
    sys.exit(app.exec())