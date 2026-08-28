from datetime import datetime
import hashlib
import hmac
import json
import os
import time
from urllib.parse import parse_qsl

from fastapi import HTTPException

from db.database import get_conn


TELEGRAM_MAX_AGE_SECONDS = 86400


def validate_telegram_init_data(
    init_data: str,
    bot_token: str,
    *,
    now: int | None = None,
    max_age_seconds: int = TELEGRAM_MAX_AGE_SECONDS,
) -> dict:
    """Validate Telegram WebApp initData and return its signed user object."""
    if not bot_token:
        raise ValueError("telegram authentication is not configured")

    data = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise ValueError("missing hash")

    try:
        auth_date = int(data.get("auth_date", "0"))
    except ValueError as exc:
        raise ValueError("invalid auth_date") from exc

    checked_at = int(time.time()) if now is None else now
    age = checked_at - auth_date
    if auth_date <= 0 or age < -30 or age > max_age_seconds:
        raise ValueError("expired auth_date")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise ValueError("invalid hash")

    try:
        user = json.loads(data["user"])
        telegram_id = int(user["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("invalid user") from exc
    if telegram_id <= 0:
        raise ValueError("invalid user")
    return user


def create_session(player_id: str) -> dict:
    from datetime import timedelta
    from uuid import uuid4

    token = str(uuid4())
    expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                player_id TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO sessions (token, player_id, expires_at) VALUES (?, ?, ?)",
            (token, player_id, expires_at),
        )
    return {
        "access_token": token,
        "token_type": "bearer",
        "player_id": player_id,
        "expires_at": expires_at,
    }

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


def require_player_id(authorization: str) -> str:
    player_id = player_id_from_authorization(authorization)
    if not player_id:
        raise HTTPException(status_code=401, detail="valid bearer token required")
    return player_id


def dev_auth_enabled() -> bool:
    return os.getenv("SKUA_SLOTS_ALLOW_DEV_AUTH", "false").lower() == "true"
