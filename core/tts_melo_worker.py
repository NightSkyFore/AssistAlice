import queue
import numpy as np
import sherpa_onnx
from PySide6.QtCore import QThread, Signal

from core.text_utils import preprocess_text_for_zh_TTS

MELO_MODEL_PATH = "./model/tts-model/vits-melo-tts-zh_en"

_POISON_PILL = object()

class MeloTTSWorker(QThread):
    tts_sentence_signal = Signal(str)

    def __init__(self, tts_queue: queue.Queue, play_queue: queue.Queue, tts_cpu: int = 4, **kwargs,):
        super().__init__()
        self.tts_queue = tts_queue
        self.play_queue = play_queue

        rule_fsts_string = f"{MELO_MODEL_PATH}/date.fst,{MELO_MODEL_PATH}/number.fst,{MELO_MODEL_PATH}/new_heteronym.fst,{MELO_MODEL_PATH}/phone.fst"

        config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=f"{MELO_MODEL_PATH}/model.onnx",
                    tokens=f"{MELO_MODEL_PATH}/tokens.txt",
                    lexicon=f"{MELO_MODEL_PATH}/lexicon.txt"
                ),
                num_threads=tts_cpu,
                debug=False, 
            ),
            rule_fsts=rule_fsts_string, 
            max_num_sentences=1,
        )

        if not config.validate():
            raise RuntimeError("TTS config not valid...")
        self.tts = sherpa_onnx.OfflineTts(config)
        self.sample_rate = self.tts.sample_rate

        print(f"[TTSWorker]Melo ready with {tts_cpu} CPUs...")

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

        tts_text = preprocess_text_for_zh_TTS(text)
        audio_generated = self.tts.generate(tts_text, sid=0, speed=1.0)

        self.tts_sentence_signal.emit(text)

        if audio_generated and len(audio_generated.samples) > 0:
            self.play_queue.put(audio_generated.samples)

    def stop(self):
        self.tts_queue.put(_POISON_PILL)
        self.wait()
