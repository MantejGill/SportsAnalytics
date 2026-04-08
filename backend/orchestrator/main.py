"""Auto-Negotiate Backend — FastAPI entry point."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure backend root is on sys.path so absolute imports work
_BACKEND_ROOT = str(Path(__file__).resolve().parent.parent)
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from orchestrator.config import settings
from orchestrator.routers.negotiate import router as negotiate_router

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Activate advanced implementations (with safe fallbacks to defaults)
# ---------------------------------------------------------------------------

from agents.adapters import set_checker, set_predictor, AdvancedConstraintChecker, MLPredictor

try:
    set_checker(AdvancedConstraintChecker())
    logger.info("Activated advanced constraint checker")
except Exception as exc:
    logger.warning("Failed to activate advanced constraint checker, using default: %s", exc)

try:
    set_predictor(MLPredictor())
    logger.info("Activated ML market predictor")
except Exception as exc:
    logger.warning("Failed to activate ML predictor, using default: %s", exc)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Auto-Negotiate",
    description="Autonomous sports contract negotiation powered by LangGraph + GPT-4o-mini",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(negotiate_router)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "auto-negotiate",
        "model": settings.OPENAI_MODEL,
    }


# ---------------------------------------------------------------------------
# Dev runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "orchestrator.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
