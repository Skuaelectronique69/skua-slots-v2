import json
import sqlite3
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from db.database import get_conn
from services.wallet_service import init_wallet_tables, get_wallet_snapshot

STREAK_REWARD_BASE = 10

def utc_now():
    return datetime.now(timezone.utc)

def utc_now_iso():
    return utc_now().isoformat()

def claim_date():
    return utc_now().date().isoformat()

def init_streak_tables():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS streaks (
            player_id TEXT PRIMARY KEY,
            current_streak INTEGER NOT NULL DEFAULT 0,
            best_streak INTEGER NOT NULL DEFAULT 0,
            last_claim_date TEXT,
            updated_at TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_streaks_last_claim
        ON streaks(last_claim_date)
        """)

def get_streak(player_id: str):
    init_streak_tables()
    today = claim_date()

    with get_conn() as conn:
        now = utc_now_iso()

        conn.execute("""
        INSERT INTO streaks(player_id, current_streak, best_streak, last_claim_date, updated_at)
        VALUES (?, 0, 0, NULL, ?)
        ON CONFLICT(player_id) DO NOTHING
        """, (player_id, now))

        row = conn.execute(
            "SELECT * FROM streaks WHERE player_id = ?",
            (player_id,)
        ).fetchone()

        return {
            "player_id": player_id,
            "claim_date": today,
            "claimed_today": row["last_claim_date"] == today,
            "current_streak": row["current_streak"],
            "best_streak": row["best_streak"],
            "last_claim_date": row["last_claim_date"],
            "updated_at": row["updated_at"],
        }

def claim_streak(player_id: str):
    init_streak_tables()
    init_wallet_tables()

    today = claim_date()
    yesterday = (utc_now().date() - timedelta(days=1)).isoformat()
    now = utc_now_iso()
    ref = f"streak:{today}"
    reason = "streak_reward"

    with get_conn() as conn:
        try:
            conn.execute("BEGIN")

            conn.execute("""
            INSERT INTO streaks(player_id, current_streak, best_streak, last_claim_date, updated_at)
            VALUES (?, 0, 0, NULL, ?)
            ON CONFLICT(player_id) DO NOTHING
            """, (player_id, now))

            row = conn.execute(
                "SELECT * FROM streaks WHERE player_id = ?",
                (player_id,)
            ).fetchone()

            if row["last_claim_date"] == today:
                conn.rollback()
                wallet = get_wallet_snapshot(player_id)
                return {
                    "claimed": False,
                    "reason": "already_claimed_today",
                    "player_id": player_id,
                    "claim_date": today,
                    "current_streak": row["current_streak"],
                    "best_streak": row["best_streak"],
                    "reward": {
                        "sku_delta": 0,
                        "reason": reason,
                        "ref": ref,
                    },
                    "wallet": {
                        "balance_sku": wallet["balance_sku"],
                        "updated_at": wallet["updated_at"],
                    }
                }

            if row["last_claim_date"] == yesterday:
                new_current = row["current_streak"] + 1
            else:
                new_current = 1

            new_best = max(row["best_streak"], new_current)
            delta = min(STREAK_REWARD_BASE + new_current, 25)

            conn.execute("""
            INSERT INTO wallets(player_id, balance_sku, updated_at)
            VALUES (?, 0, ?)
            ON CONFLICT(player_id) DO NOTHING
            """, (player_id, now))

            conn.execute("""
            INSERT INTO wallet_transactions(id, player_id, delta, reason, ref, meta_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid4()),
                player_id,
                delta,
                reason,
                ref,
                json.dumps({"streak": new_current, "claim_date": today}),
                now
            ))

            conn.execute("""
            UPDATE wallets
            SET balance_sku = balance_sku + ?, updated_at = ?
            WHERE player_id = ?
            """, (delta, now, player_id))

            conn.execute("""
            UPDATE streaks
            SET current_streak = ?, best_streak = ?, last_claim_date = ?, updated_at = ?
            WHERE player_id = ?
            """, (new_current, new_best, today, now, player_id))

            conn.commit()

        except sqlite3.IntegrityError:
            conn.rollback()

            state = get_streak(player_id)
            wallet = get_wallet_snapshot(player_id)

            return {
                "claimed": False,
                "reason": "already_claimed_by_ledger",
                "player_id": player_id,
                "claim_date": today,
                "current_streak": state["current_streak"],
                "best_streak": state["best_streak"],
                "reward": {
                    "sku_delta": 0,
                    "reason": reason,
                    "ref": ref,
                },
                "wallet": {
                    "balance_sku": wallet["balance_sku"],
                    "updated_at": wallet["updated_at"],
                }
            }

    wallet = get_wallet_snapshot(player_id)

    return {
        "claimed": True,
        "player_id": player_id,
        "claim_date": today,
        "current_streak": new_current,
        "best_streak": new_best,
        "reward": {
            "sku_delta": delta,
            "reason": reason,
            "ref": ref,
        },
        "wallet": {
            "balance_sku": wallet["balance_sku"],
            "updated_at": wallet["updated_at"],
        }
    }
