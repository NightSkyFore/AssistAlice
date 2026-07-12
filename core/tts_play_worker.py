import queue
import sounddevice as sd
import numpy as np

from PySide6.QtCore import QThread, Signal

from core.pcm_utils import calculate_tts_volume_level

_POISON_PILL = object()

class TTSPlayWorker(QThread):
    volume_signal = Signal(float)
    
    def __init__(self, sample_rate: int = 44100):
        super().__init__()
        self.sample_rate = sample_rate
        self.play_queue = queue.Queue()

    def run(self):
        # 100ms
        chunk_size = int(self.sample_rate * 0.1)
        while True:
            try:
                chunk = self.play_queue.get()

                # global break. wake play_queue from blocked.
                if chunk is _POISON_PILL:
                    self.play_queue.task_done()
                    break

                if chunk is not None:
                    with sd.OutputStream(samplerate=self.sample_rate, channels=1, dtype='float32') as stream:
                        # For sentences in one LLM response, keep playing.
                        while True:
                            audio_array = np.ascontiguousarray(np.array(chunk, dtype=np.float32).flatten())
                            for i in range(0, len(audio_array), chunk_size):
                                np_chunk = audio_array[i : i + chunk_size]
                                stream.write(np_chunk)

                                vol = calculate_tts_volume_level(np_chunk)
                                self.volume_signal.emit(vol)

                            self.volume_signal.emit(0.0)
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

    def put_audio(self, audio_data):
        self.play_queue.put(audio_data)

    def stop(self):
        self.play_queue.put(_POISON_PILL)
        self.wait()
