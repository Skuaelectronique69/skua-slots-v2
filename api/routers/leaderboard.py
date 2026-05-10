from fastapi import APIRouter, Query
from db.database import get_conn

router = APIRouter(tags=["leaderboard"])

@router.get("/leaderboard")
def leaderboard(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                player_id,
                xp,
                credits,
                energy,
                updated_at
            FROM players
            ORDER BY xp DESC, credits DESC, player_id ASC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        ).fetchall()

        return {
            "period": "all_time",
            "ranking_rule": "xp_desc_credits_desc",
            "limit": limit,
            "offset": offset,
            "items": [
                {
                    "rank": offset + index + 1,
                    "player_id": row["player_id"],
                    "xp": row["xp"],
                    "credits": row["credits"],
                    "energy": row["energy"],
                    "updated_at": row["updated_at"],
                }
                for index, row in enumerate(rows)
            ]
        }

@router.get("/leaderboard/me/{player_id}")
def leaderboard_me(player_id: str):
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT player_id, xp, credits, energy, updated_at
            FROM players
            WHERE player_id = ?
            """,
            (player_id,)
        ).fetchone()

        if not row:
            return {"found": False, "player_id": player_id}

        higher = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM players
            WHERE
                xp > ?
                OR (xp = ? AND credits > ?)
                OR (xp = ? AND credits = ? AND player_id < ?)
            """,
            (
                row["xp"],
                row["xp"], row["credits"],
                row["xp"], row["credits"], row["player_id"],
            )
        ).fetchone()["count"]

        return {
            "found": True,
            "rank": higher + 1,
            "period": "all_time",
            "ranking_rule": "xp_desc_credits_desc",
            "player_id": row["player_id"],
            "xp": row["xp"],
            "credits": row["credits"],
            "energy": row["energy"],
            "updated_at": row["updated_at"],
        }
