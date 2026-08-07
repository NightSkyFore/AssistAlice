import queue
import numpy as np
import sherpa_onnx
from PySide6.QtCore import QThread, Signal

VITS_MODEL_PATH = "./model/tts-model/vits-piper-en_US-amy-medium"

_POISON_PILL = object()

class VitsTTSWorker(QThread):
    tts_sentence_signal = Signal(str)

    def __init__(self, tts_queue: queue.Queue, play_queue: queue.Queue, tts_cpu: int = 2, **kwargs,):
        super().__init__()
        self.tts_queue = tts_queue
        self.play_queue = play_queue

        config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=f"{VITS_MODEL_PATH}/en_US-amy-medium.onnx",
                    tokens=f"{VITS_MODEL_PATH}/tokens.txt",
                    data_dir=f"{VITS_MODEL_PATH}/espeak-ng-data",
                ),
                num_threads=tts_cpu,
                debug=False, 
            ),
            max_num_sentences=1,
        )

        if not config.validate():
            raise RuntimeError("TTS config not valid...")
        self.tts = sherpa_onnx.OfflineTts(config)
        self.sample_rate = self.tts.sample_rate

        print(f"[TTSWorker]VITS-en ready with {tts_cpu} CPUs...")

    def run(self):
        while True:
            try:
                sentence = self.tts_queue.get()

                if sentence is _POISON_PILL:
                    self.tts_queue.task_done()
                    break

                if sentence:
                    self._generate_audio(sentence)
                    self.tts_queue.task_done()
            except queue.Empty:
                continue

    def _generate_audio(self, text):
        text = text.strip()
        if not text:
            return

        audio_generated = self.tts.generate(text, sid=0, speed=1.0)

        self.tts_sentence_signal.emit(text)

        if audio_generated and len(audio_generated.samples) > 0:
            self.play_queue.put(audio_generated.samples)

    def stop(self):
        self.tts_queue.put(_POISON_PILL)
        self.wait()
