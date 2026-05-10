import random
from datetime import datetime, timezone

SYMBOLS = ["⚙️", "⚡", "🌊", "🛰️", "💎"]
SPIN_COST = 10

def grade_from_xp(xp: int) -> str:
    if xp >= 500:
        return "COMMANDER"
    if xp >= 200:
        return "OPERATOR"
    if xp >= 80:
        return "TECHNICIAN"
    return "RECRUIT"

def spin(player_id: str, energy: int = 100, xp: int = 0, credits: int = 500):
    if energy < SPIN_COST:
        return {
            "accepted": False,
            "reason": "not_enough_energy",
            "energy_after": energy,
            "xp_after": xp,
            "credits_after": credits,
            "grade": grade_from_xp(xp),
            "server_time": datetime.now(timezone.utc).isoformat(),
        }

    reels = [random.choice(SYMBOLS) for _ in range(3)]
    unique = len(set(reels))

    if unique == 1:
        payout = 100
        xp_gained = 25
        result = "jackpot"
    elif unique == 2:
        payout = 25
        xp_gained = 8
        result = "win"
    else:
        payout = 0
        xp_gained = 2
        result = "miss"

    energy_after = energy - SPIN_COST
    xp_after = xp + xp_gained
    credits_after = credits + payout

    return {
        "accepted": True,
        "player_id": player_id,
        "reels": reels,
        "result": result,
        "payout": payout,
        "xp_gained": xp_gained,
        "energy_after": energy_after,
        "xp_after": xp_after,
        "credits_after": credits_after,
        "grade": grade_from_xp(xp_after),
        "spin_cost": SPIN_COST,
        "rng_version": "skua-rng-v1",
        "server_time": datetime.now(timezone.utc).isoformat(),
    }
