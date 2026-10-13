import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(os.getenv("RIFFFORGE_DATA", "runtime")).resolve()
ROOT.mkdir(parents=True, exist_ok=True)


@contextmanager
def db():
    connection = sqlite3.connect(ROOT / "jobs.sqlite", timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, created REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, owner TEXT NOT NULL,
      name TEXT NOT NULL, duration REAL NOT NULL, state TEXT NOT NULL,
      result TEXT, error TEXT, version INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL,
      started REAL, lease TEXT);
    """)
    if "lease" not in [row[1] for row in connection.execute("PRAGMA table_info(jobs)")]:
        connection.execute("ALTER TABLE jobs ADD COLUMN lease TEXT")
    try:
        with connection:
            yield connection
    finally:
        connection.close()
