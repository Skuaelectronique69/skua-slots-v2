from pydantic import BaseModel
from uuid import uuid4
from fastapi import APIRouter, Header
from services.game import spin
from services.player_store import get_or_create_player, update_player, log_spin
from services.auth_service import player_id_from_authorization
from services.wallet_service import apply_wallet_delta

router = APIRouter(tags=["spin"])

class SpinRequest(BaseModel):
    player_id: str | None = None

@router.post("/spin")
def post_spin(payload: SpinRequest, authorization: str = Header(default="")):
    player_id = player_id_from_authorization(authorization)

    if not player_id:
        player_id = payload.player_id or "DEV_OP"

    spin_id = str(uuid4())
    player = get_or_create_player(player_id)

    result = spin(
        player_id=player_id,
        energy=player["energy"],
        xp=player["xp"],
        credits=player["credits"],
    )

    if result.get("accepted"):
        update_player(
            player_id,
            result["energy_after"],
            result["xp_after"],
            result["credits_after"],
        )
        log_spin(
            player_id,
            result["reels"],
            result["result"],
            result["payout"],
            result["xp_gained"],
        )

    
    if result.get("accepted"):
        sku_delta = 10 if result.get("result") == "jackpot" else 2 if result.get("result") == "win" else 0
        wallet = apply_wallet_delta(
            player_id=player_id,
            delta=sku_delta,
            reason="spin_reward",
            ref=f"spin:{spin_id}",
            meta={
                "result": result.get("result"),
                "payout": result.get("payout"),
                "xp_gained": result.get("xp_gained"),
            }
        )
        result["spin_id"] = spin_id
        result["reward"] = {"sku_delta": sku_delta}
        result["wallet"] = {
            "balance_sku": wallet["balance_sku"],
            "updated_at": wallet["updated_at"],
        }

    return result
