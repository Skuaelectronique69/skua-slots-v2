from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.spin import router as spin_router
from routers.daily import router as daily_router
from routers.leaderboard import router as leaderboard_router
from routers.auth import router as auth_router
from routers.wallet import router as wallet_router
from routers.streak import router as streak_router
from db.database import init_db

app = FastAPI(title="SkuaSlots API", version="1.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "ok", "service": "skua-slots-api", "version": "1.3.0"}

app.include_router(spin_router, prefix="/api")
app.include_router(daily_router, prefix="/api")
app.include_router(leaderboard_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(wallet_router, prefix="/api")
app.include_router(streak_router, prefix="/api")
