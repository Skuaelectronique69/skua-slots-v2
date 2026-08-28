from fastapi import APIRouter, Header
from services.auth_service import require_player_id
from services.streak_service import get_streak, claim_streak

router = APIRouter(tags=["streak"])

@router.get("/streak")
def streak(authorization: str = Header(default="")):
    player_id = require_player_id(authorization)
    return get_streak(player_id)

@router.post("/streak/claim")
def streak_claim(authorization: str = Header(default="")):
    player_id = require_player_id(authorization)
    return claim_streak(player_id)
