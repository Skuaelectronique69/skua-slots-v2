import os

from fastapi import FastAPI
from src.core.runtime_registry import load_runtime_registry
from src.core.persistence_status import get_persistence_status

from fastapi.middleware.cors import CORSMiddleware
from routers.spin import router as spin_router
from routers.daily import router as daily_router
from routers.leaderboard import router as leaderboard_router
from routers.auth import router as auth_router
from routers.wallet import router as wallet_router
from routers.streak import router as streak_router
from db.database import init_db

app = FastAPI(title="SkuaSlots API", version="1.3.0")

cors_allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "SKUA_SLOTS_CORS_ORIGINS",
        "http://127.0.0.1:5179,http://localhost:5179",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins,
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


@app.get("/api/v1/registry")
def runtime_registry():
    return load_runtime_registry()


@app.get("/api/v1/persistence/status")
def persistence_status():
    return get_persistence_status()
