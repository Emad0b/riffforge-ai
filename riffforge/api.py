import hashlib
import io
import json
import secrets
import shutil
import time
import uuid
import os
import logging
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from .audio import MAX_BYTES, decode
from .store import ROOT, db
from .tab import TUNING

app = FastAPI(title="RiffForge AI", version="0.1.0")


def owner(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "A workspace session is required.")
    token = hashlib.sha256(authorization[7:].encode()).hexdigest()
    with db() as connection:
        session = connection.execute(
            "SELECT created FROM sessions WHERE token=?", (token,)
        ).fetchone()
    if not session or session["created"] < time.time() - 86400:
        raise HTTPException(401, "Workspace session expired.")
    return token


def owned(job_id, user):
    with db() as connection:
        job = connection.execute(
            "SELECT * FROM jobs WHERE id=? AND owner=?", (job_id, user)
        ).fetchone()
    if not job:
        raise HTTPException(404, "Transcription not found.")
    return dict(job)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "queue": "celery-redis" if os.getenv("RIFFFORGE_BROKER") else "sqlite-durable",
        "scope": "phase-1-clean-monophonic",
    }


@app.post("/api/session")
def session():
    token = secrets.token_urlsafe(32)
    with db() as connection:
        connection.execute(
            "INSERT INTO sessions VALUES (?,?)",
            (hashlib.sha256(token.encode()).hexdigest(), time.time()),
        )
    return {"token": token, "expires_in": 86400}


async def enqueue(file, user):
    with db() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM jobs WHERE owner=?", (user,)
        ).fetchone()[0]
    if count >= 20:
        raise HTTPException(
            429, "Workspace limit reached. Delete a transcription first."
        )
    job_id = uuid.uuid4().hex
    directory = ROOT / job_id
    directory.mkdir()
    source = directory / "upload.bin"
    try:
        size = 0
        with source.open("wb") as output:
            while chunk := await file.read(65536):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(413, "Upload exceeds 20 MB.")
                output.write(chunk)
        from starlette.concurrency import run_in_threadpool

        duration = await run_in_threadpool(decode, source, directory / "audio.wav")
        source.unlink()
        name = (
            (file.filename or "Untitled riff").replace("\\", "/").split("/")[-1][:120]
        )
        with db() as connection:
            connection.execute(
                "INSERT INTO jobs(id,owner,name,duration,state,created) VALUES (?,?,?,?,?,?)",
                (job_id, user, name, duration, "queued", time.time()),
            )
        if os.getenv("RIFFFORGE_BROKER"):
            try:
                from .tasks import process

                await run_in_threadpool(process.apply_async, args=[job_id], retry=False)
            except Exception:
                logging.warning(
                    "Broker unavailable; durable queue will be reconciled.",
                    exc_info=True,
                )
        return {"id": job_id, "state": "queued"}
    except ValueError as error:
        shutil.rmtree(directory, ignore_errors=True)
        raise HTTPException(400, str(error)) from error
    except Exception:
        shutil.rmtree(directory, ignore_errors=True)
        raise


@app.post("/api/transcriptions", status_code=202)
async def upload(file: UploadFile = File(...), user=Depends(owner)):
    return await enqueue(file, user)


@app.post("/api/demo", status_code=202)
async def demo(user=Depends(owner)):
    path = __import__("pathlib").Path("tests/fixtures/reference.wav")
    return await enqueue(
        UploadFile(
            filename="Synthetic reference riff.wav", file=io.BytesIO(path.read_bytes())
        ),
        user,
    )


@app.get("/api/transcriptions")
def list_jobs(user=Depends(owner)):
    with db() as connection:
        return [
            dict(row)
            for row in connection.execute(
                "SELECT id,name,duration,state,version FROM jobs WHERE owner=? ORDER BY created DESC",
                (user,),
            )
        ]


@app.get("/api/transcriptions/{job_id}")
def get_job(job_id: str, user=Depends(owner)):
    job = owned(job_id, user)
    job.pop("owner")
    job["result"] = json.loads(job["result"]) if job["result"] else None
    return job


@app.get("/api/transcriptions/{job_id}/audio")
def audio(job_id: str, user=Depends(owner)):
    owned(job_id, user)
    return FileResponse(
        ROOT / job_id / "audio.wav",
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"},
    )


class Note(BaseModel):
    id: str
    start: float = Field(ge=0, le=30)
    end: float = Field(gt=0, le=30)
    pitch: int = Field(ge=40, le=88)
    confidence: float = Field(ge=0, le=1)
    string: int = Field(ge=1, le=6)
    fret: int = Field(ge=0, le=24)


class Correction(BaseModel):
    version: int
    notes: list[Note] = Field(max_length=500)


@app.patch("/api/transcriptions/{job_id}")
def correct(job_id: str, change: Correction, user=Depends(owner)):
    job = owned(job_id, user)
    if job["state"] != "complete":
        raise HTTPException(409, "Transcription is not complete.")
    notes = [n.model_dump() for n in change.notes]
    if len({n["id"] for n in notes}) != len(notes):
        raise HTTPException(422, "Note identifiers must be unique.")
    for i, note in enumerate(notes):
        if (
            note["start"] >= note["end"]
            or note["end"] > job["duration"]
            or TUNING[6 - note["string"]] + note["fret"] != note["pitch"]
        ):
            raise HTTPException(
                422, "Invalid timing or string/fret does not match pitch."
            )
        if i and note["start"] < notes[i - 1]["end"] - 0.06:
            raise HTTPException(422, "Phase 1 tabs must be ordered and monophonic.")
    result = json.loads(job["result"])
    result.setdefault("original_tab", result["notes"])
    result["notes"] = notes
    with db() as connection:
        changed = connection.execute(
            "UPDATE jobs SET result=?,version=version+1 WHERE id=? AND owner=? AND version=?",
            (json.dumps(result), job_id, user, change.version),
        ).rowcount
    if not changed:
        raise HTTPException(409, "A newer edit exists. Reload before saving.")
    return {"version": change.version + 1}


@app.get("/api/transcriptions/{job_id}/export/{format}")
def export(job_id: str, format: str, user=Depends(owner)):
    job = owned(job_id, user)
    if not job["result"]:
        raise HTTPException(409, "Transcription is not ready.")
    result = json.loads(job["result"])
    headers = {
        "Content-Disposition": f'attachment; filename="riff.{format}"',
        "Cache-Control": "no-store",
    }
    if format == "json":
        return Response(
            json.dumps(result, indent=2), media_type="application/json", headers=headers
        )
    if format == "mid":
        import pretty_midi

        midi = pretty_midi.PrettyMIDI()
        guitar = pretty_midi.Instrument(program=27)
        for n in result["notes"]:
            guitar.notes.append(
                pretty_midi.Note(
                    velocity=max(1, int(n["confidence"] * 127)),
                    pitch=n["pitch"],
                    start=n["start"],
                    end=n["end"],
                )
            )
        midi.instruments.append(guitar)
        buffer = io.BytesIO()
        midi.write(buffer)
        return Response(buffer.getvalue(), media_type="audio/midi", headers=headers)
    raise HTTPException(404, "Supported formats: json, mid")


@app.delete("/api/transcriptions/{job_id}", status_code=204)
def delete(job_id: str, user=Depends(owner)):
    owned(job_id, user)
    with db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        job = connection.execute(
            "SELECT state FROM jobs WHERE id=? AND owner=?", (job_id, user)
        ).fetchone()
        if job and job["state"] == "running":
            raise HTTPException(409, "Wait for the active job before deleting.")
        connection.execute("DELETE FROM jobs WHERE id=? AND owner=?", (job_id, user))
    shutil.rmtree(ROOT / job_id, ignore_errors=True)
