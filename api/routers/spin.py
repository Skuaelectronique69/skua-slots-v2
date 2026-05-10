from pydantic import BaseModel
from fastapi import APIRouter
from services.game import spin
from services.player_store import get_or_create_player, update_player, log_spin

router = APIRouter(tags=["spin"])

class SpinRequest(BaseModel):
    player_id: str = "DEV_OP"

@router.post("/spin")
def post_spin(payload: SpinRequest):
    player = get_or_create_player(payload.player_id)

    result = spin(
        player_id=payload.player_id,
        energy=player["energy"],
        xp=player["xp"],
        credits=player["credits"],
    )

    if result.get("accepted"):
        update_player(
            payload.player_id,
            result["energy_after"],
            result["xp_after"],
            result["credits_after"],
        )
        log_spin(
            payload.player_id,
            result["reels"],
            result["result"],
            result["payout"],
            result["xp_gained"],
        )

    return result

@router.get("/profile/{player_id}")
def profile(player_id: str):
    return get_or_create_player(player_id)
