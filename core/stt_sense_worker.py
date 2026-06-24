import time
import queue
import numpy
import sherpa_onnx
import sounddevice as sd
from PySide6.QtCore import QThread, Signal

SENSEVOICE_MODEL_PATH = "./model/stt-model/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09"

VAD_MODEL_PATH = "./model/stt-model/VAD/silero_vad.onnx"

_POISON_PILL = object()

class SenseVoiceSTTWorker(QThread):
    text_signal = Signal(str)
    speech_silence_signal = Signal()

    def __init__(self, lang: str = "zh", stt_cpu: int = 2, **kwargs,):
        super().__init__()
        self.sample_rate = 16000
        self.min_silence = 0.5
        self.speech_silence = 2.4

        self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=f"{SENSEVOICE_MODEL_PATH}/model.int8.onnx",
            tokens=f"{SENSEVOICE_MODEL_PATH}/tokens.txt",
            num_threads=stt_cpu,
            sample_rate=self.sample_rate,
            feature_dim=80,
            debug=False,
            language=lang if lang in ["zh", "en", "ja", "ko", "yue", "auto"] else "auto",
            use_itn=True,
        )

        vad_config = sherpa_onnx.VadModelConfig()
        vad_config.silero_vad.model = VAD_MODEL_PATH
        vad_config.silero_vad.min_silence_duration = self.min_silence
        vad_config.sample_rate = self.sample_rate
        self.vad = sherpa_onnx.VoiceActivityDetector(vad_config, buffer_size_in_seconds=30)

        self.audio_queue = queue.Queue()
        self.last_speech_time = time.time()
        self.is_speaking = False
        self.has_unprocessed_text = False

        print(f"[SenseVoice]Ready with {stt_cpu} CPUs...")

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
        # upscale for normal voice in working
        audio_chunk = audio_chunk * 2.0
        audio_chunk = numpy.clip(audio_chunk, -1.0, 1.0)

        self.vad.accept_waveform(audio_chunk)

        # when speaking
        if self.vad.is_speech_detected():
            self.is_speaking = True
        is_speech_finished = False
        while not self.vad.empty():
            segment = self.vad.front
            self.vad.pop()
            self._trigger_transcription(segment.samples)
            is_speech_finished = True

        # when stop speaking
        if is_speech_finished:
            self.is_speaking = False
            self.last_speech_time = time.time() - self.min_silence

        # when keep silence
        if not self.is_speaking:
            silence_duration = time.time() - self.last_speech_time
            if self.has_unprocessed_text and silence_duration > self.speech_silence:
                self.speech_silence_signal.emit()
                self.has_unprocessed_text = False

    def _trigger_transcription(self, samples):
        stream = self.recognizer.create_stream()
        stream.accept_waveform(self.sample_rate, samples)
        self.recognizer.decode_stream(stream)

        raw_text = stream.result.text
        if raw_text.strip():
            text = raw_text + "，"
            self.text_signal.emit(text)
            self.has_unprocessed_text = True

    def stop(self):
        self.audio_queue.put(_POISON_PILL)
        self.wait()
