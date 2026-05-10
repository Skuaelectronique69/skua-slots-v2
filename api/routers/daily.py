from fastapi import APIRouter
from db.database import get_conn
from datetime import datetime, timedelta

router = APIRouter(tags=["daily"])

DAILY_ENERGY = 100
DAILY_CREDITS = 50

@router.post("/daily/claim/{player_id}")
def claim_daily(player_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE player_id = ?",
            (player_id,)
        ).fetchone()

        if not row:
            return {"accepted": False, "reason": "player_not_found"}

        now = datetime.utcnow()
        last_daily = row["last_daily_at"]

        if last_daily:
            last_daily_dt = datetime.fromisoformat(last_daily)
            if now - last_daily_dt < timedelta(hours=24):
                remaining = timedelta(hours=24) - (now - last_daily_dt)
                return {
                    "accepted": False,
                    "reason": "daily_already_claimed",
                    "remaining_seconds": int(remaining.total_seconds())
                }

        new_energy = row["energy"] + DAILY_ENERGY
        new_credits = row["credits"] + DAILY_CREDITS

        conn.execute(
            """
            UPDATE players
            SET energy = ?, credits = ?, last_daily_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE player_id = ?
            """,
            (new_energy, new_credits, now.isoformat(), player_id)
        )

        return {
            "accepted": True,
            "player_id": player_id,
            "energy_after": new_energy,
            "credits_after": new_credits,
            "daily_energy": DAILY_ENERGY,
            "daily_credits": DAILY_CREDITS
        }
