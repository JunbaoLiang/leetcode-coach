from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import attempts, hints, plan, problems, profile, stats

app = FastAPI(title="LeetCode Coach API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router_module in (profile, problems, plan, attempts, hints, stats):
    app.include_router(router_module.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
