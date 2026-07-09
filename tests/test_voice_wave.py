import sys
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from core.stt_streaming_worker import XASRStreamingWorker
from ui.voice_wave import VoiceWaveWidget

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        self.wave = VoiceWaveWidget()

        self.stt_worker = XASRStreamingWorker()
        self.stt_worker.text_signal.connect(self.on_voice_text)
        self.stt_worker.volume_signal.connect(self.wave.set_amplitude)
        self.stt_worker.start()
        
        self.label = QLabel()

        layout = QVBoxLayout(self)
        layout.addWidget(self.wave)
        layout.addWidget(self.label)
    
    def on_voice_text(self,text):
        self.label.setText(text)
    
    def closeEvent(self, event):
        self.stt_worker.stop()
        return super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
