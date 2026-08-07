import numpy as np

def calculate_volume_level(audio_chunk: np.ndarray, mode: str = "mic") -> float:
    if len(audio_chunk) == 0:
        return 0.0

    rms = np.sqrt(np.mean(np.square(audio_chunk)))

    if mode == "mic":
        # for microphone input
        max_input_rms = 0.04 
    elif mode == "tts":
        max_input_rms = 0.20
    elif mode == "speaker":
        max_input_rms = 0.08
    else:
        max_input_rms = 0.10

    normalized_vol = rms / max_input_rms
    normalized_vol = np.clip(normalized_vol, 0.0, 1.0)

    # for visual balance, from [0.01, 0.25] to [0.1, 0.5] 
    visual_volume = np.sqrt(normalized_vol)

    return float(visual_volume)
