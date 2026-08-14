import sys
from PySide6.QtWidgets import QApplication, QMainWindow

from core.stt_streaming_worker import XASRStreamingWorker

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.stt_worker = XASRStreamingWorker()
        self.stt_worker.text_signal.connect(self.on_streaming_text)
        self.stt_worker.start()
    
    def on_streaming_text(self, text: str):
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