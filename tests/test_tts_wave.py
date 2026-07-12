import queue
import sys
from PySide6.QtWidgets import QApplication, QPushButton, QTextEdit, QVBoxLayout, QWidget

from core.tts_melo_worker import MeloTTSWorker
from core.tts_play_worker import TTSPlayWorker
from ui.voice_wave import VoiceWaveWidget

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        self.wave = VoiceWaveWidget()
        
        self.input = QTextEdit()
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.on_text_send)

        layout = QVBoxLayout(self)
        layout.addWidget(self.wave)
        layout.addWidget(self.input)
        layout.addWidget(self.send_btn)

        self.tts_queue = queue.Queue()
        self.tts_worker = MeloTTSWorker(self.tts_queue)
        self.play_worker = TTSPlayWorker()
        self.tts_worker.tts_audio_signal.connect(self.play_worker.put_audio)
        self.play_worker.volume_signal.connect(self.wave.set_amplitude)
        self.tts_worker.start()
        self.play_worker.start()
    
    def on_text_send(self):
        text = self.input.toPlainText().strip()
        if text:
            self.tts_queue.put(text)
        self.input.clear()
    
    def closeEvent(self, event):
        self.tts_worker.stop()
        self.play_worker.stop()
        return super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
