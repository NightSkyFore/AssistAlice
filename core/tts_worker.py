import os
import queue
import traceback

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import threading
import sounddevice as sd
from PySide6.QtCore import QThread

TTS_MODEL_PATH = {
    "zh": {
        "model_path": "./model/tts-model/MeloTTS-Chinese",
        "bert_path": "./model/tts-model/bert-base-multilingual-uncased"
    },
    "en": {
        "model_path": "./model/tts-model/MeloTTS-English",
        "bert_path": "./model/tts-model/bert-base-uncased"
    },
    "jp": {
        "model_path": "./model/tts-model/MeloTTS-Japanese",
        "bert_path": "./model/tts-model/bert-base-japanese-v3"
    }
}

_POISON_PILL = object()

class MeloTTSWorker(QThread):
    def __init__(self, tts_queue: queue.Queue, lang: str = "en", tts_cpu: int = 4, **kwargs,):
        super().__init__()
        self.tts_queue = tts_queue

        self.play_queue = queue.Queue()
        self.play_thread = None
        
        self.model = None 
        self.speaker = None

        if lang == "zh" or lang == "jp":
            self.lang = lang.upper()
            self.speaker_id = self.lang
        else:
            # default to en_us.
            self.lang = "EN"
            self.speaker_id = "EN-US"
    
        self._config_file = os.path.join(TTS_MODEL_PATH[lang]["model_path"], "config.json")
        self._ckpt_file = os.path.join(TTS_MODEL_PATH[lang]["model_path"], "checkpoint.pth")
        self._bert_path = TTS_MODEL_PATH[lang]["bert_path"]
        self.num_threads = tts_cpu

    def run(self):
        # lazy import for fast startup
        import nltk
        import jieba
        from builtin_melo.api import TTS

        # specified path to offline data and cache
        # nltk data
        NLTK_DATA_PATH = "./offline_data/nltk_data"
        nltk.data.path = [NLTK_DATA_PATH]
        # jieba cache
        JIEBA_CACHE_DIR = "./offline_data/jieba"
        jieba.dt.tmp_dir = JIEBA_CACHE_DIR

        self.model = TTS(
            language=self.lang,
            device='cpu',
            config_path=self._config_file,
            ckpt_path=self._ckpt_file,
            bert_path=self._bert_path,
            num_threads=self.num_threads
        )
        self.speaker = self.model.hps.data.spk2id[self.speaker_id]
        self._start_playback_thread()
        print(f"[TTSWorker]Ready with {self.num_threads} CPUs...")

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
            sampling_rate = self.model.hps.data.sampling_rate
            
            while True:
                try:
                    chunk = self.play_queue.get()
                    
                    # global break. wake play_queue from blocked.
                    if chunk is _POISON_PILL:
                        self.play_queue.task_done()
                        break
                        
                    if chunk is not None and chunk.size > 0:
                        with sd.OutputStream(samplerate=sampling_rate, channels=1, dtype='float32') as stream:
                            # In sentences in a complete answer, keep playing.
                            while True:
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
        try:
            audio_array = self.model.tts_to_file(text, self.speaker, output_path=None, speed=1.0, quiet=True)
            if audio_array is not None:
                self.play_queue.put(audio_array)
        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"[MeloTTSWorker]TTS play failed: {error_msg}")

    def stop(self):
        self.tts_queue.put(_POISON_PILL)
        self.wait()
