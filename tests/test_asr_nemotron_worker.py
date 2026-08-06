import sys
from PySide6.QtWidgets import QApplication, QMainWindow

from core.asr_nemotron_worker import ASRNemotronWorker
from ui.media_subtitle_manager import MediaSubtitleManager

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._cur_subtitle = ""
        self._previous_subtitle = ""
        self.worker = ASRNemotronWorker()
        self.worker.text_signal.connect(self.on_streaming_text)
        self.worker.speech_silence_signal.connect(self.on_silence)
        self.worker.start()

        self.media = MediaSubtitleManager(self)
        self.media.show_media_subtitle()

    def on_streaming_text(self, text: str):
        print(text)
        self._cur_subtitle = text
        self.media.osd_on_streaming(f"{self._previous_subtitle}, {self._cur_subtitle}")

    def on_silence(self):
        if self._cur_subtitle:
            self._previous_subtitle = self._cur_subtitle
            self._cur_subtitle = ""

    def closeEvent(self, event):
        self.worker.stop()
        return super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("AI Assistant")
    win = TestWindow()
    win.show()
    sys.exit(app.exec())
