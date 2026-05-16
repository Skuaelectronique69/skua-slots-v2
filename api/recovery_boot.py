import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("api/data/skua_persistence.db")

def log(msg):
    print(f"[RECOVERY] {msg}")

def connect():
    return sqlite3.connect(DB_PATH)

def reclaim_expired_leases(conn):
    cur = conn.cursor()

    cur.execute("""
    UPDATE jobs
    SET lease_owner = NULL,
        lease_until = NULL,
        status = 'pending',
        updated_at = CURRENT_TIMESTAMP
    WHERE lease_until IS NOT NULL
      AND lease_until < CURRENT_TIMESTAMP
      AND status = 'running'
    """)

    count = cur.rowcount
    conn.commit()

    log(f"expired leases reclaimed: {count}")

def replay_outbox(conn):
    cur = conn.cursor()

    cur.execute("""
    SELECT id, event_type, payload
    FROM outbox
    WHERE status = 'pending'
    ORDER BY id ASC
    """)

    rows = cur.fetchall()

    for row in rows:
        outbox_id, event_type, payload = row

        log(f"replay outbox #{outbox_id} ({event_type})")

        cur.execute("""
        UPDATE outbox
        SET status = 'processed',
            processed_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (outbox_id,))

    conn.commit()

    log(f"outbox replayed: {len(rows)}")

def write_runtime_state(conn):
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO runtime_state(key, value, updated_at)
    VALUES(
        'last_recovery_boot',
        ?,
        CURRENT_TIMESTAMP
    )
    """, (datetime.utcnow().isoformat(),))

    conn.commit()

    log("runtime_state updated")

def main():
    log("boot sequence start")

    conn = connect()

    reclaim_expired_leases(conn)
    replay_outbox(conn)
    write_runtime_state(conn)

    conn.close()

    log("boot sequence complete")

if __name__ == "__main__":
    main()
