# Phase 1 architecture

## Ingestion

Upload names are display-only: private storage uses server-generated UUID directories. The API reads bounded chunks, checks a 20 MB limit and accepted audio signatures, and invokes FFmpeg with no shell, no stdin, an allowlist of local protocols and a 25-second deadline. FFmpeg decodes at most 31 seconds; clips beyond the 30-second product limit are rejected, not silently cropped. Output is PCM16, mono, 22,050 Hz. This converts channels and sample format; it does not claim loudness normalization. A malformed upload never becomes queued work.

## Model path

The CPU worker loads Spotify's bundled ICASSP 2022 ONNX model once. Basic Pitch provides MIDI onset, offset, pitch and activation events. Original predictions remain in `raw_notes`. No reference fixture labels enter inference. The adapter records the exact model artifact hash and elapsed inference/postprocessing time.

For Phase 1, overlapping predictions are reduced to a dominant line. The selector prefers activation strength for near-simultaneous attacks and otherwise retains the earlier accepted event. This heuristic can miss a real melody in polyphonic input; a warning accompanies excluded notes. It is not source separation.

## Fingerings

Tuning is represented low-to-high as MIDI `[40,45,50,55,59,64]`. String numbers follow guitar convention: string 1 is high E, string 6 is low E. Every candidate has `pitch = tuning[6-string] + fret`, with fret 0–24.

Dynamic programming minimizes total transition cost `abs(fret delta) + 0.8*abs(string delta)` plus `0.06*fret` at each note. An exhaustive small-phrase test proves agreement with the minimum across all candidate paths. This encourages practical movement but is not an ergonomic hand model, and it does not infer authentic player technique.

## Jobs and recovery

API ingestion persists queued jobs. Docker sends job IDs through Redis to Celery. Beat schedules reconciliation every 10 seconds, so a persisted job survives a broker outage. Claims use an immediate SQLite transaction. Five-minute leases permit recovery after a crash; unique lease tokens fence stale workers from overwriting newer results. Model failures become a failed state with a safe public error and detailed worker logs.

Development runs a separate polling process against the same durable database. No inference runs in the HTTP event loop. SQLite WAL and local files suit a single-host Phase 1 demo; PostgreSQL, S3, outbox dispatch, distributed quotas and multiple worker hosts require a later migration.

## Review and playback

The browser retrieves owned audio as an authenticated blob and plays it through WaveSurfer. Original timing drives current-note highlighting. Tab columns follow event order, with onset labels in seconds; they are not rhythmic notation. Edits validate timing, guitar pitch mapping, note IDs and monophonic ordering, then compare the stored edit version atomically. `raw_notes` and the original generated tab survive corrections. Export uses current notes; the JSON also contains provenance and originals.

## Next milestones

Collect licensed real-guitar recordings and separate training, tuning and holdout manifests. Add beat quantization and scored notation; evaluate bends and overlapping attacks before claiming polyphony. Introduce PostgreSQL, object storage and account authentication before scaling. Only then add source separation, model comparisons, dataset tracking and gated model releases.
