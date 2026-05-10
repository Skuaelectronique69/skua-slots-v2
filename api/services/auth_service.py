from datetime import datetime
from db.database import get_conn

def player_id_from_authorization(authorization: str):
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "").strip()

    with get_conn() as conn:
        row = conn.execute(
            "SELECT player_id, expires_at FROM sessions WHERE token = ?",
            (token,)
        ).fetchone()

        if not row:
            return None

        if datetime.utcnow() > datetime.fromisoformat(row["expires_at"]):
            return None

        return row["player_id"]
