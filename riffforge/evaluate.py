import json
from pathlib import Path

import mir_eval.transcription
import numpy as np

from .engine import transcribe


def metrics(reference, predicted):
    def intervals(notes):
        return np.array([[n["start"], n["end"]] for n in notes], dtype=float).reshape(
            -1, 2
        )

    def frequencies(notes):
        return np.array([440 * 2 ** ((n["pitch"] - 69) / 12) for n in notes])

    args = (
        intervals(reference),
        frequencies(reference),
        intervals(predicted),
        frequencies(predicted),
    )
    onset = mir_eval.transcription.precision_recall_f1_overlap(*args, offset_ratio=None)
    offset = mir_eval.transcription.precision_recall_f1_overlap(*args, offset_ratio=0.2)
    return {
        "onset_precision": float(onset[0]),
        "onset_recall": float(onset[1]),
        "onset_f1": float(onset[2]),
        "onset_offset_f1": float(offset[2]),
        "reference_notes": len(reference),
        "predicted_notes": len(predicted),
        "onset_tolerance_ms": 50,
        "pitch_tolerance_cents": 50,
        "offset_tolerance": "max(50ms, 20% of reference duration)",
    }


if __name__ == "__main__":
    result = transcribe(Path("tests/fixtures/reference.wav"))
    reference = json.loads(Path("tests/fixtures/reference.json").read_text())
    report = {
        **metrics(reference, result["raw_notes"]),
        "seconds": result["seconds"],
        "model": result["model"],
        "model_sha256": result["model_sha256"],
        "dataset": "One self-authored synthetic plucked-string riff. Not a real-guitar benchmark.",
    }
    Path("docs").mkdir(exist_ok=True)
    Path("docs/evaluation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
