"""Durable SQLite development queue. Claims are transactional and leases recover."""

import json
import logging
import shutil
import time
import uuid

from .store import ROOT, db


def run_once(job_id=None):
    lease = uuid.uuid4().hex
    with db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "UPDATE jobs SET state='queued' WHERE state='running' AND started < ?",
            (time.time() - 300,),
        )
        expired = connection.execute(
            "SELECT id FROM jobs WHERE created<? AND state!='running'",
            (time.time() - 86400,),
        ).fetchall()
        for row in expired:
            connection.execute("DELETE FROM jobs WHERE id=?", (row["id"],))
            shutil.rmtree(ROOT / row["id"], ignore_errors=True)
        connection.execute(
            "DELETE FROM sessions WHERE created<?", (time.time() - 86400,)
        )
        job = connection.execute(
            "SELECT * FROM jobs WHERE state='queued' AND (? IS NULL OR id=?) ORDER BY created LIMIT 1",
            (job_id, job_id),
        ).fetchone()
        if not job:
            return False
        connection.execute(
            "UPDATE jobs SET state='running', started=?,lease=? WHERE id=?",
            (time.time(), lease, job["id"]),
        )
    try:
        from .engine import transcribe

        result = transcribe(ROOT / job["id"] / "audio.wav")
        with db() as connection:
            connection.execute(
                "UPDATE jobs SET state='complete', result=? WHERE id=? AND state='running' AND lease=?",
                (json.dumps(result), job["id"], lease),
            )
    except Exception:
        logging.getLogger(__name__).exception("Transcription failed for %s", job["id"])
        with db() as connection:
            connection.execute(
                "UPDATE jobs SET state='failed', error=? WHERE id=? AND lease=?",
                (
                    "Transcription failed. Check worker logs and retry the upload.",
                    job["id"],
                    lease,
                ),
            )
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    while True:
        if not run_once():
            time.sleep(0.5)
