import sqlite3
from pathlib import Path
from typing import Dict, Any

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "skua_persistence.db"


def _count(cur, query: str, params=()):
    return cur.execute(query, params).fetchone()[0]


def get_persistence_status() -> Dict[str, Any]:
    reasons = []

    if not DB_PATH.exists():
        return {
            "persistence": {
                "sqlite": {
                    "path": str(DB_PATH),
                    "reachable": False,
                }
            },
            "health": {
                "status": "error",
                "reasons": ["sqlite_missing"],
            },
        }

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute("SELECT 1")

        tables = [
            "jobs",
            "job_events",
            "outbox",
            "dead_letter",
            "runtime_state",
        ]

        existing_tables = [
            row[0]
            for row in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]

        missing_tables = [t for t in tables if t not in existing_tables]
        reasons.extend([f"missing_table_{t}" for t in missing_tables])

        jobs_pending = _count(cur, "SELECT COUNT(*) FROM jobs WHERE status='pending'")
        jobs_running = _count(cur, "SELECT COUNT(*) FROM jobs WHERE status='running'")
        jobs_failed = _count(cur, "SELECT COUNT(*) FROM jobs WHERE status='failed'")
        jobs_done = _count(cur, "SELECT COUNT(*) FROM jobs WHERE status='done'")
        jobs_leased = _count(cur, "SELECT COUNT(*) FROM jobs WHERE lease_owner IS NOT NULL")

        outbox_pending = _count(cur, "SELECT COUNT(*) FROM outbox WHERE status='pending'")
        outbox_processed = _count(cur, "SELECT COUNT(*) FROM outbox WHERE status='processed'")

        dead_letter_count = _count(cur, "SELECT COUNT(*) FROM dead_letter")

        last_recovery = cur.execute(
            "SELECT value, updated_at FROM runtime_state WHERE key='last_recovery_boot'"
        ).fetchone()

        if jobs_failed > 0:
            reasons.append("failed_jobs_nonzero")
        if dead_letter_count > 0:
            reasons.append("dead_letter_nonzero")
        if outbox_pending > 0:
            reasons.append("outbox_pending_nonzero")
        if missing_tables:
            status = "error"
        elif reasons:
            status = "degraded"
        else:
            status = "ok"

        conn.close()

        return {
            "service": {
                "name": "skua-slots-v2",
                "component": "persistence",
            },
            "persistence": {
                "sqlite": {
                    "path": str(DB_PATH),
                    "reachable": True,
                    "schema_version": 1,
                    "wal_mode": False,
                },
                "recovery": {
                    "last_boot": {
                        "at": last_recovery[0] if last_recovery else None,
                        "updated_at": last_recovery[1] if last_recovery else None,
                        "status": "success" if last_recovery else "unknown",
                    }
                },
            },
            "queues": {
                "jobs": {
                    "pending": jobs_pending,
                    "running": jobs_running,
                    "failed": jobs_failed,
                    "done": jobs_done,
                    "leased": jobs_leased,
                },
                "outbox": {
                    "pending": outbox_pending,
                    "processed": outbox_processed,
                },
                "dead_letter": {
                    "count": dead_letter_count,
                },
            },
            "health": {
                "status": status,
                "reasons": reasons,
            },
        }

    except Exception as exc:
        return {
            "persistence": {
                "sqlite": {
                    "path": str(DB_PATH),
                    "reachable": False,
                }
            },
            "health": {
                "status": "error",
                "reasons": [f"sqlite_error:{type(exc).__name__}"],
            },
        }
