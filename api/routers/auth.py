from fastapi import APIRouter, Header
from db.database import get_conn
from services.player_store import get_or_create_player
from uuid import uuid4
from datetime import datetime, timedelta

router = APIRouter(tags=["auth"])

@router.post("/auth/dev-login/{player_id}")
def dev_login(player_id: str):
    get_or_create_player(player_id)
    token = str(uuid4())
    expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()

    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            player_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL
        )
        """)
        conn.execute(
            "INSERT INTO sessions (token, player_id, expires_at) VALUES (?, ?, ?)",
            (token, player_id, expires_at)
        )

    return {
        "access_token": token,
        "token_type": "bearer",
        "player_id": player_id,
        "expires_at": expires_at
    }

@router.get("/me")
def me(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        return {"authenticated": False, "reason": "missing_bearer_token"}

    token = authorization.replace("Bearer ", "").strip()

    with get_conn() as conn:
        row = conn.execute(
            "SELECT player_id, expires_at FROM sessions WHERE token = ?",
            (token,)
        ).fetchone()

        if not row:
            return {"authenticated": False, "reason": "invalid_token"}

        if datetime.utcnow() > datetime.fromisoformat(row["expires_at"]):
            return {"authenticated": False, "reason": "expired_token"}

        player = get_or_create_player(row["player_id"])

        return {
            "authenticated": True,
            "player_id": player["player_id"],
            "energy": player["energy"],
            "xp": player["xp"],
            "credits": player["credits"],
            "updated_at": player["updated_at"],
            "last_daily_at": player["last_daily_at"] if "last_daily_at" in player.keys() else None
        }
