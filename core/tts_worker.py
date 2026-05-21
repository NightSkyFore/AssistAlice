import os

# 告诉底层 C++ 库，PyTorch CPU 运算最多用几个线程
# 分 6 个给 TTS，避免PyTorch默认满开，cpu因上下文切换反而变慢
os.environ["OMP_NUM_THREADS"] = "6"
os.environ["MKL_NUM_THREADS"] = "6"
os.environ["OPENBLAS_NUM_THREADS"] = "6"
os.environ["VECLIB_MAXIMUM_THREADS"] = "6"
os.environ["NUMEXPR_NUM_THREADS"] = "6"

import queue
import traceback

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import sounddevice as sd
from PySide6.QtCore import QThread

TTS_MODEL_PATH = {
    "local_zh": "./model/tts-model/MeloTTS-Chinese",
    "local_en": "./model/tts-model/MeloTTS-English"
}

class MeloTTSWorker(QThread):
    def __init__(self, tts_queue, local_path: str = "local_zh"):
        # default 'local_zh' since it's ZH mix EN
        super().__init__()
        self.tts_queue = tts_queue
        self.is_running = False
        
        self.model = None 
        self.speaker_id = None
    
        self._config_file = os.path.join(TTS_MODEL_PATH[local_path], "config.json")
        self._ckpt_file = os.path.join(TTS_MODEL_PATH[local_path], "checkpoint.pth")

    def run(self):
        self.is_running = True

        # lazy import for fast startup
        import nltk
        import jieba
        import torch
        from melo.api import TTS

        torch.set_num_threads(6) 
        torch.set_num_interop_threads(6)

        # specified path to offline data and cache
        # nltk data
        NLTK_DATA_PATH = "./offline_data/nltk_data"
        nltk.data.path = [NLTK_DATA_PATH]
        # jieba cache
        JIEBA_CACHE_DIR = "./offline_data/jieba"
        jieba.dt.tmp_dir = JIEBA_CACHE_DIR

        # change 'ZH' to 'EN' if use English model
        self.model = TTS(language='ZH', device='cpu', config_path=self._config_file, ckpt_path=self._ckpt_file)
        self.speaker_id = self.model.hps.data.spk2id['ZH']

        _ = self.model.tts_to_file("啊", self.speaker_id, output_path=None, speed=1.0)

        while self.is_running:
            try:
                sentence = self.tts_queue.get(timeout=0.1)
                if sentence:
                    self._play_audio(sentence)
                    self.tts_queue.task_done()
            except queue.Empty:
                continue

    def _play_audio(self, text):
        try:
            audio_array = self.model.tts_to_file(text, self.speaker_id, output_path=None, speed=1.0)
            if audio_array is not None:
                sd.play(audio_array, samplerate=self.model.hps.data.sampling_rate)
                sd.wait() 
        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"[MeloTTSWorker]TTS play failed: {error_msg}")


    def stop(self):
        self.is_running = False
        self.wait()
