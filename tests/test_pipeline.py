import hashlib
import io
import itertools
import json
import os
import tempfile
from pathlib import Path

os.environ["RIFFFORGE_DATA"] = tempfile.mkdtemp(prefix="riffforge-test-")
from fastapi.testclient import TestClient
from riffforge.api import app
from riffforge.tab import assign, positions, movement, dominant_line
from riffforge.store import db, ROOT

client = TestClient(app)


def session():
    return {"Authorization": "Bearer " + client.post("/api/session").json()["token"]}


def upload(headers, data=None):
    data = data or Path("tests/fixtures/reference.wav").read_bytes()
    return client.post(
        "/api/transcriptions",
        headers=headers,
        files={"file": ("riff.wav", data, "audio/wav")},
    )


def test_fret_mapping_and_global_optimum():
    assert positions(40) == [(6, 0)]
    assert (1, 0) in positions(64)
    assert positions(90) == []
    notes = [{"pitch": p} for p in [64, 65, 69, 64]]
    actual = assign(notes)

    def cost(path):
        return sum(0.06 * p[1] for p in path) + sum(
            movement(a, b) for a, b in zip(path, path[1:])
        )

    best = min(
        cost(p) for p in itertools.product(*(positions(n["pitch"]) for n in notes))
    )
    assert abs(cost([(n["string"], n["fret"]) for n in actual]) - best) < 1e-9
    for n in actual:
        assert [40, 45, 50, 55, 59, 64][6 - n["string"]] + n["fret"] == n["pitch"]


def test_dominant_line_preserves_monophonic_scope():
    raw = [
        {"pitch": 52, "start": 0, "end": 1, "confidence": 0.9},
        {"pitch": 64, "start": 0, "end": 1, "confidence": 0.4},
        {"pitch": 55, "start": 1.1, "end": 2, "confidence": 0.8},
    ]
    assert [n["pitch"] for n in dominant_line(raw)] == [52, 55]
    assert len(raw) == 3


def test_upload_validation_auth_and_ownership():
    a, b = session(), session()
    assert upload({}).status_code == 401
    assert upload(a, b"not an audio file").status_code == 400
    assert upload(a, b"RIFF" + b"0" * 200).status_code == 400
    r = upload(a)
    assert r.status_code == 202
    job = r.json()["id"]
    assert client.get("/api/transcriptions/" + job, headers=a).status_code == 200
    for suffix in ["", "/audio", "/export/json"]:
        assert (
            client.get("/api/transcriptions/" + job + suffix, headers=b).status_code
            == 404
        )
    assert client.delete("/api/transcriptions/" + job, headers=b).status_code == 404
    assert (
        client.patch(
            "/api/transcriptions/" + job, headers=b, json={"version": 0, "notes": []}
        ).status_code
        == 404
    )
    assert client.get(
        "/api/transcriptions/" + job + "/audio", headers=a
    ).content.startswith(b"RIFF")
    assert client.delete("/api/transcriptions/" + job, headers=a).status_code == 204
    assert not (ROOT / job).exists()


def test_duration_limit():
    import wave

    audio = io.BytesIO()
    with wave.open(audio, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(22050)
        wav.writeframes(b"\0\0" * (22050 * 32))
    assert upload(session(), audio.getvalue()).status_code == 400


def test_edits_concurrency_and_immutable_raw():
    headers = session()
    job = upload(headers).json()["id"]
    note = {
        "id": "0",
        "pitch": 52,
        "start": 0.1,
        "end": 0.7,
        "confidence": 0.8,
        "string": 5,
        "fret": 7,
    }
    original = {"raw_notes": [note.copy()], "notes": [note.copy()]}
    with db() as connection:
        connection.execute(
            "UPDATE jobs SET state='complete', result=? WHERE id=?",
            (json.dumps(original), job),
        )
    note["string"] = 4
    note["fret"] = 2
    payload = {"version": 0, "notes": [note]}
    r = client.patch("/api/transcriptions/" + job, headers=headers, json=payload)
    assert r.status_code == 200
    assert (
        client.patch(
            "/api/transcriptions/" + job, headers=headers, json=payload
        ).status_code
        == 409
    )
    result = client.get("/api/transcriptions/" + job, headers=headers).json()["result"]
    assert result["raw_notes"] == original["raw_notes"]
    assert result["original_tab"] == original["notes"]
    payload["version"] = 1
    payload["notes"][0]["fret"] = 3
    assert (
        client.patch(
            "/api/transcriptions/" + job, headers=headers, json=payload
        ).status_code
        == 422
    )
    assert client.get(
        "/api/transcriptions/" + job + "/export/mid", headers=headers
    ).content.startswith(b"MThd")


def test_metrics_detect_missed_and_wrong_notes():
    from riffforge.evaluate import metrics

    ref = [
        {"start": 0.1, "end": 0.7, "pitch": 52},
        {"start": 1, "end": 1.5, "pitch": 55},
    ]
    assert metrics(ref, ref)["onset_f1"] == 1
    assert metrics(ref, ref[:1])["onset_recall"] == 0.5
    assert metrics(ref, [{**ref[0], "pitch": 53}])["onset_f1"] == 0


def test_real_model_reference():
    from riffforge.engine import transcribe
    from riffforge.evaluate import metrics

    result = transcribe(Path("tests/fixtures/reference.wav"))
    reference = json.loads(Path("tests/fixtures/reference.json").read_text())
    score = metrics(reference, result["raw_notes"])
    assert score["onset_f1"] >= 0.9, score
    assert score["onset_offset_f1"] >= 0.8, score
    assert len(result["model_sha256"]) == 64
    assert all(n["start"] < n["end"] for n in result["notes"])
