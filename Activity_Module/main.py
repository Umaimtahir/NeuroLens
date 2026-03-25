"""
NeuroLens — Activity Classifier Service
Entry point: uvicorn main:app --reload --port 8001
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api_routes.router import router as activity_router
from activity_classifier.models import preload_all

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="NeuroLens Activity Classifier",
    description=(
        "Zero-Shot Focus-Aware Activity Classification pipeline.\n\n"
        "**Pipeline**: CLIP Visual Gate → Florence-2 OCR/Caption → Qwen2.5 Reasoning"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow Flutter desktop app (localhost) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(activity_router)


# ---------------------------------------------------------------------------
# Startup / Shutdown lifecycle
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup() -> None:
    """Pre-load all models into RAM/VRAM at startup."""
    import os
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    logger.info("Starting NeuroLens Activity Classifier …")

    if os.environ.get("SKIP_PRELOAD"):
        logger.info("SKIP_PRELOAD is set — skipping model preload (cache population mode).")
        return

    loop = asyncio.get_event_loop()
    # Load models in a thread so the event loop isn't blocked
    with ThreadPoolExecutor(max_workers=1) as pool:
        await loop.run_in_executor(pool, preload_all)
    logger.info("All models loaded. Service is ready.")



@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("Shutting down NeuroLens Activity Classifier.")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Meta"])
async def health() -> dict:
    return {"status": "ok", "service": "neurolens-activity-classifier"}


# ---------------------------------------------------------------------------
# Dev runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
