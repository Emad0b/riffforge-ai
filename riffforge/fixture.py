"""Self-authored synthetic plucked-string reference, not a recorded guitar."""

import json
from pathlib import Path

import numpy as np
import soundfile as sf


def generate(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    rate = 22050
    audio = np.zeros(rate * 15)
    notes = []
    pitches = [52, 55, 57, 59, 57, 55, 52, 50, 52, 55, 59, 64, 62, 59]
    for i, pitch in enumerate(pitches):
        start = 0.4 + i
        duration = 0.65
        t = np.arange(int(rate * duration)) / rate
        f = 440 * 2 ** ((pitch - 69) / 12)
        envelope = (
            np.minimum(t / 0.008, 1)
            * np.exp(-3 * t)
            * np.minimum((duration - t) / 0.03, 1)
        )
        wave = sum(
            np.sin(2 * np.pi * f * harmonic * t) / harmonic**2
            for harmonic in range(1, 7)
        )
        offset = int(start * rate)
        audio[offset : offset + len(t)] += wave * envelope * 0.6
        notes.append({"start": start, "end": start + duration, "pitch": pitch})
    sf.write(directory / "reference.wav", audio, rate, subtype="PCM_16")
    (directory / "reference.json").write_text(json.dumps(notes, indent=2))
    return directory / "reference.wav"


if __name__ == "__main__":
    generate("tests/fixtures")
