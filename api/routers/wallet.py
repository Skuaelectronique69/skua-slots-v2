from fastapi import APIRouter, Header, Query
from services.auth_service import player_id_from_authorization
from services.wallet_service import get_wallet_snapshot, apply_wallet_delta
from db.database import get_conn
from uuid import uuid4

router = APIRouter(tags=["wallet"])

@router.get("/wallet")
def wallet(authorization: str = Header(default="")):
    player_id = player_id_from_authorization(authorization) or "DEV_OP"
    return get_wallet_snapshot(player_id)

@router.get("/wallet/history")
def wallet_history(
    authorization: str = Header(default=""),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    player_id = player_id_from_authorization(authorization) or "DEV_OP"

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, delta, reason, ref, meta_json, created_at
            FROM wallet_transactions
            WHERE player_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (player_id, limit, offset)
        ).fetchall()

    return {
        "player_id": player_id,
        "limit": limit,
        "offset": offset,
        "rows": [dict(row) for row in rows],
    }

@router.post("/wallet/dev-mint")
def wallet_dev_mint(authorization: str = Header(default="")):
    player_id = player_id_from_authorization(authorization) or "DEV_OP"
    ref = f"dev-mint:{uuid4()}"
    return apply_wallet_delta(
        player_id=player_id,
        delta=100,
        reason="admin_mint",
        ref=ref,
        meta={"source": "dev"}
    )
