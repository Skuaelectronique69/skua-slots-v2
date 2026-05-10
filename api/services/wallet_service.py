import json
import sqlite3
from uuid import uuid4
from datetime import datetime
from db.database import get_conn

def utc_now():
    return datetime.utcnow().isoformat()

def init_wallet_tables():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS wallets (
            player_id TEXT PRIMARY KEY,
            balance_sku INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS wallet_transactions (
            id TEXT PRIMARY KEY,
            player_id TEXT NOT NULL,
            delta INTEGER NOT NULL,
            reason TEXT NOT NULL,
            ref TEXT NOT NULL,
            meta_json TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(player_id, ref)
        )
        """)
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_wallet_tx_player_time
        ON wallet_transactions(player_id, created_at DESC)
        """)

def get_wallet_snapshot(player_id: str, limit: int = 10):
    init_wallet_tables()
    with get_conn() as conn:
        wallet = conn.execute(
            "SELECT player_id, balance_sku, updated_at FROM wallets WHERE player_id = ?",
            (player_id,)
        ).fetchone()

        if not wallet:
            now = utc_now()
            conn.execute(
                "INSERT INTO wallets(player_id, balance_sku, updated_at) VALUES (?, 0, ?)",
                (player_id, now)
            )
            wallet = conn.execute(
                "SELECT player_id, balance_sku, updated_at FROM wallets WHERE player_id = ?",
                (player_id,)
            ).fetchone()

        txs = conn.execute(
            """
            SELECT id, delta, reason, ref, meta_json, created_at
            FROM wallet_transactions
            WHERE player_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (player_id, limit)
        ).fetchall()

        return {
            "player_id": wallet["player_id"],
            "balance_sku": wallet["balance_sku"],
            "updated_at": wallet["updated_at"],
            "recent": [dict(tx) for tx in txs],
        }

def apply_wallet_delta(player_id: str, delta: int, reason: str, ref: str, meta: dict | None = None):
    init_wallet_tables()
    now = utc_now()

    with get_conn() as conn:
        try:
            conn.execute("BEGIN")

            conn.execute(
                """
                INSERT INTO wallets(player_id, balance_sku, updated_at)
                VALUES (?, 0, ?)
                ON CONFLICT(player_id) DO NOTHING
                """,
                (player_id, now)
            )

            tx_id = str(uuid4())

            conn.execute(
                """
                INSERT INTO wallet_transactions(id, player_id, delta, reason, ref, meta_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tx_id,
                    player_id,
                    delta,
                    reason,
                    ref,
                    json.dumps(meta) if meta else None,
                    now
                )
            )

            conn.execute(
                """
                UPDATE wallets
                SET balance_sku = balance_sku + ?, updated_at = ?
                WHERE player_id = ?
                """,
                (delta, now, player_id)
            )

            conn.commit()

        except sqlite3.IntegrityError:
            conn.rollback()

    return get_wallet_snapshot(player_id)
