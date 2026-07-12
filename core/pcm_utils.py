import numpy as np

def calculate_volume_level(audio_chunk: np.ndarray) -> float:
    if len(audio_chunk) == 0:
        return 0.0

    rms = np.sqrt(np.mean(np.square(audio_chunk)))

    # for microphone input
    MAX_INPUT_RMS = 0.04 
    normalized_vol = rms / MAX_INPUT_RMS
    normalized_vol = np.clip(normalized_vol, 0.0, 1.0)

    # for visual balance, from [0.01, 0.25] to [0.1, 0.5] 
    visual_volume = np.sqrt(normalized_vol)

    return float(visual_volume)

def calculate_tts_volume_level(audio_chunk: np.ndarray) -> float:
        if len(audio_chunk) == 0:
            return 0.0

        rms = np.sqrt(np.mean(np.square(audio_chunk)))

        # TTS voice in [0.15, 0.25]
        MAX_TTS_RMS = 0.20 

        normalized_vol = rms / MAX_TTS_RMS
        normalized_vol = np.clip(normalized_vol, 0.0, 1.0)

        return float(np.sqrt(normalized_vol))
