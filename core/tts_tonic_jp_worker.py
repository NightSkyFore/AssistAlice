import queue
import numpy as np
import sherpa_onnx
from PySide6.QtCore import QThread, Signal

TONIC_MODEL_PATH = "./model/tts-model/sherpa-onnx-supertonic-3-tts-int8-2026-05-11"

_POISON_PILL = object()

class TonicTTSWorker(QThread):
    tts_sentence_signal = Signal(str)

    def __init__(self, tts_queue: queue.Queue, play_queue: queue.Queue, tts_cpu: int = 3, **kwargs,):
        super().__init__()
        self.tts_queue = tts_queue
        self.play_queue = play_queue

        config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                supertonic=sherpa_onnx.OfflineTtsSupertonicModelConfig(
                    duration_predictor=f"{TONIC_MODEL_PATH}/duration_predictor.int8.onnx",
                    text_encoder=f"{TONIC_MODEL_PATH}/text_encoder.int8.onnx",
                    vector_estimator=f"{TONIC_MODEL_PATH}/vector_estimator.int8.onnx",
                    vocoder=f"{TONIC_MODEL_PATH}/vocoder.int8.onnx",
                    tts_json=f"{TONIC_MODEL_PATH}/tts.json",
                    unicode_indexer=f"{TONIC_MODEL_PATH}/unicode_indexer.bin",
                    voice_style=f"{TONIC_MODEL_PATH}/voice.bin",
                ),
                debug=False,
                num_threads=tts_cpu,
                provider="cpu",
            ),
        )

        if not config.validate():
            raise RuntimeError("TTS config not valid...")
        self.tts = sherpa_onnx.OfflineTts(config)
        self.sample_rate = self.tts.sample_rate

        self.gen_config = sherpa_onnx.GenerationConfig()
        self.gen_config.sid = 0
        self.gen_config.num_steps = 8
        self.gen_config.speed = 1.0
        self.gen_config.extra["lang"] = "ja"

        print(f"[TTSWorker]SuperTonic ready with {tts_cpu} CPUs...")

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

        audio_generated = self.tts.generate(text, self.gen_config)

        self.tts_sentence_signal.emit(text)

        if audio_generated and len(audio_generated.samples) > 0:
            self.play_queue.put(audio_generated.samples)

    def stop(self):
        self.tts_queue.put(_POISON_PILL)
        self.wait()
