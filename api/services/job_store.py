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


def apply_lease_migration():
    conn = connect()
    cur = conn.cursor()

    existing = [row["name"] for row in cur.execute("PRAGMA table_info(jobs)").fetchall()]

    columns = {
        "lease_token": "TEXT",
        "lease_heartbeat_at": "INTEGER",
        "lease_expires_at": "INTEGER",
        "max_attempts": "INTEGER NOT NULL DEFAULT 25",
    }

    for name, ddl in columns.items():
        if name not in existing:
            cur.execute(f"ALTER TABLE jobs ADD COLUMN {name} {ddl}")

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_jobs_claim
    ON jobs(status, lease_expires_at, retry_count)
    """)

    conn.commit()
    conn.close()


def create_job(job_id, job_type, payload=None):
    payload = payload or {}
    conn = connect()
    conn.execute("""
    INSERT INTO jobs(id, type, status, payload)
    VALUES (?, ?, 'pending', ?)
    """, (job_id, job_type, json.dumps(payload)))
    conn.commit()
    conn.close()


def claim_job(worker_id, lease_ttl_ms=300000):
    apply_lease_migration()

    token = str(uuid.uuid4())
    ts = now_ms()

    conn = connect()
    cur = conn.cursor()
    cur.execute("BEGIN IMMEDIATE")

    row = cur.execute("""
    WITH candidate AS (
        SELECT id
        FROM jobs
        WHERE status IN ('pending', 'running')
          AND (
            status = 'pending'
            OR lease_expires_at IS NULL
            OR lease_expires_at <= ?
          )
          AND retry_count < max_attempts
        ORDER BY created_at ASC
        LIMIT 1
    )
    UPDATE jobs
    SET status = 'running',
        lease_owner = ?,
        lease_token = ?,
        lease_heartbeat_at = ?,
        lease_expires_at = ?,
        retry_count = CASE
            WHEN status = 'pending' THEN retry_count
            ELSE retry_count + 1
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = (SELECT id FROM candidate)
    RETURNING *
    """, (ts, worker_id, token, ts, ts + lease_ttl_ms)).fetchone()

    conn.commit()
    conn.close()

    return dict(row) if row else None


def heartbeat_lease(job_id, worker_id, lease_token, lease_ttl_ms=300000):
    ts = now_ms()
    conn = connect()
    row = conn.execute("""
    UPDATE jobs
    SET lease_heartbeat_at = ?,
        lease_expires_at = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
      AND status = 'running'
      AND lease_owner = ?
      AND lease_token = ?
    RETURNING id
    """, (ts, ts + lease_ttl_ms, job_id, worker_id, lease_token)).fetchone()

    conn.commit()
    conn.close()
    return row is not None


def release_job(job_id, worker_id, lease_token, success=True, error=None):
    conn = connect()

    if success:
        row = conn.execute("""
        UPDATE jobs
        SET status = 'done',
            lease_owner = NULL,
            lease_token = NULL,
            lease_heartbeat_at = NULL,
            lease_expires_at = NULL,
            completed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
          AND status = 'running'
          AND lease_owner = ?
          AND lease_token = ?
        RETURNING id
        """, (job_id, worker_id, lease_token)).fetchone()
    else:
        row = conn.execute("""
        UPDATE jobs
        SET status = CASE
              WHEN retry_count + 1 >= max_attempts THEN 'failed'
              ELSE 'pending'
            END,
            lease_owner = NULL,
            lease_token = NULL,
            lease_heartbeat_at = NULL,
            lease_expires_at = NULL,
            retry_count = retry_count + 1,
            last_error = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
          AND status = 'running'
          AND lease_owner = ?
          AND lease_token = ?
        RETURNING id
        """, (error, job_id, worker_id, lease_token)).fetchone()

    conn.commit()
    conn.close()
    return row is not None


def reclaim_expired_leases():
    ts = now_ms()
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    UPDATE jobs
    SET status = 'pending',
        lease_owner = NULL,
        lease_token = NULL,
        lease_heartbeat_at = NULL,
        lease_expires_at = NULL,
        updated_at = CURRENT_TIMESTAMP
    WHERE status = 'running'
      AND lease_expires_at IS NOT NULL
      AND lease_expires_at <= ?
    """, (ts,))
    count = cur.rowcount
    conn.commit()
    conn.close()
    return count
