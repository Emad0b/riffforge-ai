import hashlib
import time
from functools import lru_cache
from basic_pitch import FilenameSuffix, build_icassp_2022_model_path
from basic_pitch.inference import Model, predict
from .tab import dominant_line


@lru_cache(maxsize=1)
def model():
    return Model(build_icassp_2022_model_path(FilenameSuffix.onnx))


def transcribe(path):
    started = time.perf_counter()
    _, _, events = predict(path, model(), minimum_frequency=80, maximum_frequency=1400)
    raw = [
        {
            "id": str(i),
            "start": round(float(s), 4),
            "end": round(float(e), 4),
            "pitch": int(p),
            "confidence": round(float(v), 4),
        }
        for i, (s, e, p, v, _) in enumerate(events)
    ]
    notes = dominant_line(raw)
    model_path = build_icassp_2022_model_path(FilenameSuffix.onnx)
    return {
        "raw_notes": raw,
        "notes": notes,
        "model": "basic-pitch-0.4.0-onnx",
        "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "seconds": round(time.perf_counter() - started, 3),
        "tuning": [40, 45, 50, 55, 59, 64],
        "warnings": ["Confidence is an uncalibrated model activation."]
        + (
            [
                "Overlapping or out-of-range predictions were excluded from the monophonic tab; raw notes remain available."
            ]
            if len(raw) != len(notes)
            else []
        ),
    }
