import time
import numpy as np
import sounddevice as sd
from PySide6.QtCore import QThread, Signal
from faster_whisper import WhisperModel

WHISPER_MODEL_PATH = {
    "base": "./model/stt-model/faster-whisper-base",
    "small": "./model/stt-model/faster-whisper-small"
}

class WhisperSTTWorker(QThread):
    """
    It's reserved as optional if anyone want to use for another test.
    Execute `pip install faster_whisper` and then change the code in main_window.py as following:

        def start_stt(self):
            self.stt_worker = WhisperSTTWorker(**self._custom_config)
            self.stt_worker.text_signal.connect(self.on_vad_voice_input)
            self.stt_worker.speech_silence_signal.connect(self.handle_silence)
            self.stt_worker.start()
    """
    text_signal = Signal(str)
    speech_silence_signal = Signal()

    def __init__(self, stt_model_size: str = "small", lang: str = "en", stt_cpu: int = 2, **kwargs,):
        super().__init__()
        self.is_running = False
        self.sample_rate = 16000
        # 能量阈值：低于此值视为静音。根据环境噪音调整，通常在 0.005 - 0.02 之间
        self.volume_threshold = 0.005 
        self.min_silence = 0.5
        self.speech_silence = 2.4

        self.model = WhisperModel(
            WHISPER_MODEL_PATH[stt_model_size],
            device="cpu", 
            compute_type="int8",
            cpu_threads=stt_cpu
        )

        self.transcribe_config = {
            "zh": "这是一段中文和英文混合的日常对话。包含常用词汇如：Hello, OK, Python, UI, Bug, Linux, Alice。",
            "en": "This is a casual conversation. Here are some common words: Hello, okay, Python, UI, bug, Linux, Alice.",
            "jp": "これは日本語と英語が混ざった日常会話です。ええと、よく使う言葉：こんにちは、OK、Python、UI、バグ、Linux、Alice、アリス。"
        }
        self.lang = lang if lang in self.transcribe_config.keys() else "en"

        self.audio_buffer = []
        self.last_speech_time = time.time()
        self.is_speaking = False
        self.has_unprocessed_text = False

    def run(self):
        self.is_running = True
        with sd.InputStream(samplerate=self.sample_rate, 
                            channels=1, 
                            dtype='float32',
                            callback=self._audio_callback):
            while self.is_running:
                sd.sleep(100)

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"[WhisperSTTWorker]Callback Exception: {status}")

        audio_data = indata.copy().flatten()

        rms = np.sqrt(np.mean(audio_data**2))
        if rms > self.volume_threshold:
            self.is_speaking = True
            self.last_speech_time = time.time()
            self.audio_buffer.append(audio_data)
        else:
            if self.is_speaking:
                self.audio_buffer.append(audio_data) # 保留一点尾音

            silence_duration = time.time() - self.last_speech_time
            if self.has_unprocessed_text and silence_duration > self.speech_silence:
                self.speech_silence_signal.emit()
                self.has_unprocessed_text = False

            # 【断句逻辑】：停顿超过 0.8s 且 buffer 里有东西，触发转录。避免攒一堆长句
            if self.is_speaking and silence_duration > self.min_silence:
                self._trigger_transcription()
                self.is_speaking = False

    def _trigger_transcription(self):
        if not self.audio_buffer:
            return
        full_audio = np.concatenate(self.audio_buffer)
        self.audio_buffer = [] 

        segments, _ = self.model.transcribe(
            full_audio, 
            beam_size=1, 
            language=self.lang,
            task="transcribe",      
            vad_filter=True,
            initial_prompt=self.transcribe_config[self.lang],
            condition_on_previous_text=False, 
            temperature=[0.0, 0.2, 0.4]
        )

        text = "".join([s.text for s in segments])
        if text.strip():
            self.text_signal.emit(text)
            self.has_unprocessed_text = True

    def stop(self):
        self.is_running = False
        self.wait()
