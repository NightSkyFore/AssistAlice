import queue
import sounddevice as sd
import sherpa_onnx
from PySide6.QtCore import QThread, Signal

X_ASR_MODEL_PATH = "./model/stt-model/sherpa-onnx-x-asr-480ms-streaming-zipformer-transducer-zh-en-punct-int8-2026-06-05"

_POISON_PILL = object()

class XASRStreamingWorker(QThread):
    text_signal = Signal(str)
    speech_silence_signal = Signal()

    def __init__(self, stt_cpu: int = 2, **kwargs,):
        self.sample_rate = 16000

        self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=f"{X_ASR_MODEL_PATH}/tokens.txt",
            encoder=f"{X_ASR_MODEL_PATH}/encoder.int8.onnx",
            decoder=f"{X_ASR_MODEL_PATH}/decoder.onnx",
            joiner=f"{X_ASR_MODEL_PATH}/joiner.int8.onnx",
            num_threads=stt_cpu,
            sample_rate=self.sample_rate,
            feature_dim=80,
            enable_endpoint_detection=True,
            rule1_min_trailing_silence=2.4,
            rule2_min_trailing_silence=2.4,
            rule3_min_utterance_length=30,
            decoding_method="greedy_search",
            debug=False
        )

        self.stream = self.recognizer.create_stream()
        self.last_text = ""
        self.audio_queue = queue.Queue()

    def run(self):
        with sd.InputStream(samplerate=self.sample_rate, 
                            channels=1, 
                            dtype='float32',
                            callback=self._audio_callback):
            while True:
                try:
                    audio_chunk = self.audio_queue.get()
                    if audio_chunk is _POISON_PILL:
                        self.audio_queue.task_done()
                        break
                    self._process_audio_chunk(audio_chunk)
                    self.audio_queue.task_done()
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"[STTWorker]Exception: {e}")

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"[STTWorker] Audio Status Exception: {status}")
        self.audio_queue.put(indata.copy().flatten())

    def _process_audio_chunk(self, audio_chunk):
        self.stream.accept_waveform(self.sample_rate, audio_chunk)

        while self.recognizer.is_ready(self.stream):
            self.recognizer.decode_stream(self.stream)

        current_text = self.recognizer.get_result(self.stream).strip()
        if current_text and current_text != self.last_text:
            self.text_signal.emit(current_text)
            self.last_text = current_text

        if self.recognizer.is_endpoint(self.stream):
            if self.last_text:
                self.speech_silence_signal.emit()

            self.recognizer.reset(self.stream)
            self.last_text = ""

    def stop(self):
        self.msg_queue.put(_POISON_PILL)
        self.wait()
