from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    attempts,
    auth,
    hints,
    mock,
    plan,
    problems,
    profile,
    reports,
    review,
    stats,
    teachback,
)

app = FastAPI(title="LeetCode Coach API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router_module in (
    auth,
    profile,
    problems,
    plan,
    attempts,
    hints,
    stats,
    review,
    teachback,
    reports,
    mock,
):
    app.include_router(router_module.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
