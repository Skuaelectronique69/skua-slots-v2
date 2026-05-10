import json
from db.database import get_conn

def get_or_create_player(player_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE player_id = ?",
            (player_id,)
        ).fetchone()

        if row:
            return dict(row)

        conn.execute(
            "INSERT INTO players (player_id, energy, xp, credits) VALUES (?, 100, 0, 500)",
            (player_id,)
        )
        row = conn.execute(
            "SELECT * FROM players WHERE player_id = ?",
            (player_id,)
        ).fetchone()
        return dict(row)

def update_player(player_id: str, energy: int, xp: int, credits: int):
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE players
            SET energy = ?, xp = ?, credits = ?, updated_at = CURRENT_TIMESTAMP
            WHERE player_id = ?
            """,
            (energy, xp, credits, player_id)
        )

def log_spin(player_id: str, reels, result: str, payout: int, xp_gained: int):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO spins (player_id, reels, result, payout, xp_gained)
            VALUES (?, ?, ?, ?, ?)
            """,
            (player_id, json.dumps(reels), result, payout, xp_gained)
        )
