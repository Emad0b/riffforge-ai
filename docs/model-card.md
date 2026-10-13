# Model and evaluation card

Model: Spotify Basic Pitch 0.4.0 / ICASSP 2022, bundled ONNX serialization, CPU runtime. Artifact SHA-256: `2c3c1d144bfa61ad236e92e169c13535c880469a12a047d4e73451f2c059a0ec`.

Default inference thresholds: onset 0.5, frame 0.3, minimum event length 127.7 ms. This adapter restricts frequency to 80–1400 Hz; final playable pitches must fit standard tuning and a 24-fret instrument. Basic Pitch supports overlapping events; Phase 1 tab postprocessing chooses a monophonic line and preserves the raw predictions.

The regression fixture contains 14 self-authored MIDI pitches rendered with six sine harmonics, a short attack and exponentially decaying amplitude. It lasts 15 seconds at 22,050 Hz, PCM16. `python -m riffforge.fixture` regenerates it. The reference manifest labels the generator's start, end and MIDI pitch; it does not encode the chosen fingering.

`python -m riffforge.evaluate` runs real inference and evaluates one-to-one pitch/onset/offset matches with mir_eval. The committed measurement is a reproducible smoke test, not a representative benchmark. Regression floors are onset F1 ≥0.90 and onset+offset F1 ≥0.80 on this one fixed fixture. Metrics tests also verify missed and wrong-pitch notes lower the scores.

Known limitations: distorted attacks, vibrato, pitch bends, ringing strings, harmonics, detuning, chords and backing tracks may produce errors. Activation values are uncalibrated. The fingering cost does not represent finger reach, hand posture, articulation or the guitarist's intent. Audio playback and manual review are central to the workflow.

Before broader accuracy claims, add licensed clean electric-guitar recordings across players, pickup/effect settings, speeds and note ranges. Report held-out onset and offset F1, cents error, fingering validity, edit rate and cold/warm latency distributions. Do not tune thresholds on the held-out set or merge synthetic and recorded metrics without separating them.
