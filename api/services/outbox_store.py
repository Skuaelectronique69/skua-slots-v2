import json
import sqlite3
import time
import uuid
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "skua_persistence.db"


def now_ms():
    return int(time.time() * 1000)


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def ensure_outbox_schema():
    conn = connect()
    cur = conn.cursor()

    existing = [row["name"] for row in cur.execute("PRAGMA table_info(outbox)").fetchall()]

    columns = {
        "event_id": "TEXT",
        "routing_key": "TEXT",
        "lease_owner": "TEXT",
        "lease_token": "TEXT",
        "lease_expires_at": "INTEGER",
        "next_attempt_at": "INTEGER DEFAULT 0",
        "max_attempts": "INTEGER NOT NULL DEFAULT 10",
    }

    for name, ddl in columns.items():
        if name not in existing:
            cur.execute(f"ALTER TABLE outbox ADD COLUMN {name} {ddl}")

    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_outbox_event_id ON outbox(event_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_outbox_claim ON outbox(status, next_attempt_at, lease_expires_at)")

    conn.commit()
    conn.close()


def enqueue_event(event_type, payload=None, routing_key=None, event_id=None):
    ensure_outbox_schema()

    payload = payload or {}
    event_id = event_id or str(uuid.uuid4())

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO outbox(event_id, event_type, routing_key, payload, status)
    VALUES (?, ?, ?, ?, 'pending')
    """, (event_id, event_type, routing_key, json.dumps(payload)))

    conn.commit()
    conn.close()

    return event_id


def claim_outbox(worker_id, lease_ttl_ms=300000):
    ensure_outbox_schema()

    token = str(uuid.uuid4())
    ts = now_ms()

    conn = connect()
    cur = conn.cursor()
    cur.execute("BEGIN IMMEDIATE")

    row = cur.execute("""
    WITH candidate AS (
        SELECT id
        FROM outbox
        WHERE status IN ('pending', 'failed')
          AND attempts < max_attempts
          AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
          AND (
            lease_expires_at IS NULL
            OR lease_expires_at <= ?
          )
        ORDER BY created_at ASC
        LIMIT 1
    )
    UPDATE outbox
    SET status = 'sending',
        lease_owner = ?,
        lease_token = ?,
        lease_expires_at = ?,
        attempts = attempts + 1
    WHERE id = (SELECT id FROM candidate)
    RETURNING *
    """, (ts, ts, worker_id, token, ts + lease_ttl_ms)).fetchone()

    conn.commit()
    conn.close()

    return dict(row) if row else None


def mark_sent(outbox_id, worker_id, lease_token):
    conn = connect()
    row = conn.execute("""
    UPDATE outbox
    SET status = 'sent',
        lease_owner = NULL,
        lease_token = NULL,
        lease_expires_at = NULL,
        processed_at = CURRENT_TIMESTAMP
    WHERE id = ?
      AND status = 'sending'
      AND lease_owner = ?
      AND lease_token = ?
    RETURNING id
    """, (outbox_id, worker_id, lease_token)).fetchone()

    conn.commit()
    conn.close()
    return row is not None


def mark_failed(outbox_id, worker_id, lease_token, error, backoff_ms=5000):
    ts = now_ms()
    conn = connect()
    row = conn.execute("""
    UPDATE outbox
    SET status = CASE
            WHEN attempts >= max_attempts THEN 'failed'
            ELSE 'pending'
        END,
        lease_owner = NULL,
        lease_token = NULL,
        lease_expires_at = NULL,
        last_error = ?,
        next_attempt_at = ?
    WHERE id = ?
      AND status = 'sending'
      AND lease_owner = ?
      AND lease_token = ?
    RETURNING id
    """, (error, ts + backoff_ms, outbox_id, worker_id, lease_token)).fetchone()

    conn.commit()
    conn.close()
    return row is not None


def reclaim_outbox_leases():
    ts = now_ms()
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    UPDATE outbox
    SET status = 'pending',
        lease_owner = NULL,
        lease_token = NULL,
        lease_expires_at = NULL
    WHERE status = 'sending'
      AND lease_expires_at IS NOT NULL
      AND lease_expires_at <= ?
    """, (ts,))

    count = cur.rowcount
    conn.commit()
    conn.close()
    return count
