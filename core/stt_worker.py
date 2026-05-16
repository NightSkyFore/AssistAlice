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
    text_signal = Signal(str)
    silence_duration_signal = Signal(float)

    def __init__(self, local_path: str = "small"):
        super().__init__()
        self.is_running = False
        self.sample_rate = 16000
        # 能量阈值：低于此值视为静音。根据环境噪音调整，通常在 0.005 - 0.02 之间
        self.volume_threshold = 0.005 
        
        self.model = WhisperModel(
            WHISPER_MODEL_PATH[local_path],
            device="cpu", 
            compute_type="int8",
            cpu_threads=2
        )
        
        self.audio_buffer = []
        self.last_speech_time = time.time()
        self.is_speaking = False

    def audio_callback(self, indata, frames, time_info, status):
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
            self.silence_duration_signal.emit(silence_duration)

            # 【断句逻辑】：停顿超过 0.8s 且 buffer 里有东西，触发转录。避免攒一堆长句
            if self.is_speaking and silence_duration > 0.8:
                self.trigger_transcription()
                self.is_speaking = False

    def trigger_transcription(self):
        if not self.audio_buffer:
            return
        full_audio = np.concatenate(self.audio_buffer)
        self.audio_buffer = [] 

        magic_prompt = "这是一段中文和英文混合的日常对话。包含常用词汇如：Hello, OK, Python, UI, Bug, Linux, Alice。"
        
        segments, _ = self.model.transcribe(
            full_audio, 
            beam_size=1, 
            language="zh",
            task="transcribe",      
            vad_filter=True,
            initial_prompt=magic_prompt,
            condition_on_previous_text=False, 
            temperature=[0.0, 0.2, 0.4]
        )
        
        text = "".join([s.text for s in segments])
        if text.strip():
            self.text_signal.emit(text)

    def run(self):
        self.is_running = True
        with sd.InputStream(samplerate=self.sample_rate, 
                            channels=1, 
                            dtype='float32',
                            callback=self.audio_callback):
            while self.is_running:
                sd.sleep(500) 

    def stop(self):
        self.is_running = False
        self.wait()
