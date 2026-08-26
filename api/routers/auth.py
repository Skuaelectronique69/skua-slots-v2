import os

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from db.database import get_conn
from services.player_store import get_or_create_player
from services.auth_service import create_session, dev_auth_enabled, validate_telegram_init_data
from datetime import datetime

router = APIRouter(tags=["auth"])


class TelegramLoginRequest(BaseModel):
    init_data: str


@router.post("/auth/telegram")
def telegram_login(payload: TelegramLoginRequest):
    try:
        user = validate_telegram_init_data(
            payload.init_data,
            os.getenv("TELEGRAM_BOT_TOKEN", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    player_id = str(user["id"])
    get_or_create_player(player_id)
    return create_session(player_id)

@router.post("/auth/dev-login/{player_id}")
def dev_login(player_id: str):
    if not dev_auth_enabled():
        raise HTTPException(status_code=404, detail="not found")
    get_or_create_player(player_id)
    return create_session(player_id)

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
