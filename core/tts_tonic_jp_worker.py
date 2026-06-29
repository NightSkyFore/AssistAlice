import queue
import threading
import numpy as np
import sounddevice as sd
import sherpa_onnx
from PySide6.QtCore import QThread, Signal

TONIC_MODEL_PATH = "./model/tts-model/sherpa-onnx-supertonic-3-tts-int8-2026-05-11"

_POISON_PILL = object()

class TonicTTSWorker(QThread):
    tts_sentence_signal = Signal(str)

    def __init__(self, tts_queue: queue.Queue, tts_cpu: int = 3, **kwargs,):
        super().__init__()
        self.tts_queue = tts_queue

        self.play_queue = queue.Queue()
        self.play_thread = None

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

        self._start_playback_thread()

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

        self.play_queue.put(_POISON_PILL)
        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join()

    def _start_playback_thread(self):

        def play_worker():
            while True:
                try:
                    chunk = self.play_queue.get()

                    # global break. wake play_queue from blocked.
                    if chunk is _POISON_PILL:
                        self.play_queue.task_done()
                        break

                    if chunk is not None:
                        with sd.OutputStream(samplerate=self.sample_rate, channels=1, dtype='float32') as stream:
                            # In sentences in a complete answer, keep playing.
                            while True:
                                chunk = np.ascontiguousarray(np.array(chunk, dtype=np.float32).flatten())
                                stream.write(chunk)
                                self.play_queue.task_done()

                                try:
                                    chunk = self.play_queue.get(timeout=0.5)
                                    
                                    if chunk is _POISON_PILL:
                                        self.play_queue.task_done()
                                        return
                                except queue.Empty:
                                    break

                except Exception as e:
                    print(f"[PlayWorker]Audio Exception: {e}")
                    continue
                        
        self.play_thread = threading.Thread(target=play_worker, daemon=True)
        self.play_thread.start()

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
