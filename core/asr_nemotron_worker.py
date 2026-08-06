import queue
import numpy as np
import soundcard as sc
import sherpa_onnx
from PySide6.QtCore import QThread, Signal

from core.pcm_utils import calculate_volume_level

EN_MODEL_PATH = "./model/stt-model/sherpa-onnx-nemotron-3.5-asr-streaming-0.6b-560ms-int8-2026-06-11"

class ASRNemotronWorker(QThread):
    text_signal = Signal(str)
    speech_silence_signal = Signal()
    volume_signal = Signal(float)

    def __init__(self, lang: str = "en", stt_cpu: int = 2, **kwargs,):
        super().__init__()
        self.sample_rate = 16000
        self.is_running = False
        self.frame_counter = 0

        self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=f"{EN_MODEL_PATH}/tokens.txt",
            encoder=f"{EN_MODEL_PATH}/encoder.int8.onnx",
            decoder=f"{EN_MODEL_PATH}/decoder.int8.onnx",
            joiner=f"{EN_MODEL_PATH}/joiner.int8.onnx",
            num_threads=stt_cpu,
            sample_rate=self.sample_rate,
            feature_dim=80,
            enable_endpoint_detection=True,
            rule1_min_trailing_silence=1.2,
            rule2_min_trailing_silence=0.8,
            rule3_min_utterance_length=15,
            decoding_method="greedy_search",
            debug=False
        )

        self.stream = self.recognizer.create_stream()
        self.stream.set_option("language", lang)
        self.last_text = ""
        self.audio_queue = queue.Queue()

        print(f"[Nemotron]Ready with {stt_cpu} CPUs...")

    def run(self):
        try:
            default_speaker = sc.default_speaker()
            all_mics = sc.all_microphones(include_loopback=True)
            print(all_mics)

            loopback_mic = None
            # same in Windows, but appending "monitor" in Linux
            expected_monitor_id = f"{default_speaker.id}.monitor"

            for mic in all_mics:
                if mic.id == expected_monitor_id:
                    loopback_mic = mic
                    break
                elif mic.isloopback and mic.name == default_speaker.name:
                    loopback_mic = mic
                    break
                else:
                    raise Exception("[SpeakerASR]loopback not found.")
            print(f"[SpeakerASR]listening loopback: {loopback_mic.name}")
        except Exception as e:
            print(f"[SpeakerASR]loopback Exception: {e}")
            return

        # for every 100ms
        chunk_frames = int(self.sample_rate * 0.1)

        self.is_running = True
        try:
            with loopback_mic.recorder(samplerate=self.sample_rate) as mic:
                while self.is_running:
                    data = mic.record(numframes=chunk_frames)

                    # 扬声器双声道转换为单声道
                    if data.ndim > 1:
                        data = data.mean(axis=1)

                    audio_array = np.ascontiguousarray(data, dtype=np.float32)
                    self._process_audio_chunk(audio_array)

        except Exception as e:
            print(f"[SpeakerASR]ASR Exception: {e}")

    def _process_audio_chunk(self, audio_chunk):
        # voice to wave
        vol = calculate_volume_level(audio_chunk.flatten())
        if vol > 0.003:
            self.frame_counter += 1
            if self.frame_counter & 3 == 0:
                self.volume_signal.emit(vol)

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
        self.is_running = False
        self.wait()
