from fastapi import APIRouter, Header
from services.auth_service import player_id_from_authorization
from services.streak_service import get_streak, claim_streak

router = APIRouter(tags=["streak"])

@router.get("/streak")
def streak(authorization: str = Header(default="")):
    player_id = player_id_from_authorization(authorization) or "DEV_OP"
    return get_streak(player_id)

@router.post("/streak/claim")
def streak_claim(authorization: str = Header(default="")):
    player_id = player_id_from_authorization(authorization) or "DEV_OP"
    return claim_streak(player_id)
