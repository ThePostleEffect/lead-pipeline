"""FastAPI application factory — wraps the existing pipeline as an HTTP API."""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()  # Load .env from project root before anything else

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import exports, health, leads, rules, runs, schedules


def create_app() -> FastAPI:
    app = FastAPI(
        title="Lead Pipeline API",
        version="0.1.0",
        description="Web API wrapper for the Lead Pipeline CLI tool.",
    )

    # CORS — allow Vite dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(runs.router, prefix="/runs", tags=["runs"])
    app.include_router(leads.router, prefix="/leads", tags=["leads"])
    app.include_router(rules.router, prefix="/rules", tags=["rules"])
    app.include_router(exports.router, prefix="/exports", tags=["exports"])
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(schedules.router, prefix="/schedules", tags=["schedules"])

    @app.on_event("startup")
    def _start_scheduler() -> None:
        from api.scheduler import start_scheduler
        start_scheduler()

    @app.get("/health")
    def health_check() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
