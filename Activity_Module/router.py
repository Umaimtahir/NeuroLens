"""
FastAPI router for the Activity Classifier.

Routes
------
POST /analyze/activity    — full pipeline (server captures screen)
POST /classify/title      — title-only fast path (no image, <5ms)
                            Used by Kaggle remote mode to avoid image upload
                            when heuristics can resolve from window title alone.
"""
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from PIL import Image as PILImage
import io
from pydantic import BaseModel

from activity_classifier.classifier import (
    ActivityClassifier,
    _detect_browser,
    _BROWSER_SUFFIXES,
    _split_label,
)
from activity_classifier.schemas import ActivityResult, ErrorResponse
import config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Activity"])

# One shared classifier instance
_classifier = ActivityClassifier()

# Thread pool for heavy inference
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="activity_worker")


# ──────────────────────────────────────────────────────────────────────────────
# POST /classify/title — instant title-only classification (no image needed)
# Used by Kaggle remote client to get fast results without uploading a screenshot.
# ──────────────────────────────────────────────────────────────────────────────
class TitleRequest(BaseModel):
    window_title: str = ""


@router.post(
    "/classify/title",
    response_model=ActivityResult,
    summary="Instant title-only classification (no image upload)",
)
async def classify_by_title(req: TitleRequest) -> ActivityResult:
    """Zero-image, granular classification from window title."""
    import time
    from activity_classifier import label_engine, app_signatures
    
    t = time.perf_counter()
    title = req.window_title or ""
    
    # Get foreground process from behavioral signal collector if available
    # (since this endpoint is title-only, we usually don't have the process name,
    # but we can try to guess it from signatures or just use title-based engine)
    
    # ── GUESS PROCESS FROM TITLE ──
    t_lower = title.lower()
    proc_guess = None
    if "- visual studio code" in t_lower or "- vs code" in t_lower: proc_guess = "code.exe"
    elif "- discord" in t_lower or "discord |" in t_lower: proc_guess = "discord.exe"
    elif "zoom meeting" in t_lower: proc_guess = "zoom.exe"
    elif "microsoft teams" in t_lower: proc_guess = "teams.exe"
    elif "spotify" in t_lower: proc_guess = "spotify.exe"
    elif "administrator: windows powershell" in t_lower or "command prompt" in t_lower or "ubuntu" in t_lower or "terminal" in t_lower or "bash" in t_lower: proc_guess = "openconsole.exe"
    elif "- excel" in t_lower: proc_guess = "excel.exe"
    elif "- word" in t_lower: proc_guess = "winword.exe"
    elif "github desktop" in t_lower: proc_guess = "githubdesktop.exe"
    elif "task manager" in t_lower: proc_guess = "taskmgr.exe"
    elif r"c:-users" in t_lower.replace("\\", "-") or ".exe" in t_lower: proc_guess = "openconsole.exe"

    label = label_engine.detect_app_subactivity(proc_guess, title)
    
    if not label:
        if _detect_browser(title):
            browser_name = "Browser"
            m_b = _BROWSER_SUFFIXES.search(title)
            if m_b:
                browser_name = m_b.group(1).title()
            
            page = _BROWSER_SUFFIXES.sub("", title).strip(" -–—|")
            domain = app_signatures.extract_domain(title)
            
            # GUESS DOMAIN FROM TITLE if missing
            if not domain:
                p_lower = page.lower()
                if "youtube" in p_lower: domain = "youtube.com"
                elif "netflix" in p_lower: domain = "netflix.com"
                elif "amazon.com" in p_lower or "amazon" in p_lower or "daraz" in p_lower or "ebay" in p_lower or "walmart" in p_lower or "flipkart" in p_lower or "aliexpress" in p_lower: 
                    domain = "amazon.com" # Mock generic shopping domain to trigger the shopping branch
                    if "daraz" in p_lower: domain = "daraz.pk"
                    elif "ebay" in p_lower: domain = "ebay.com"
                    elif "walmart" in p_lower: domain = "walmart.com"
                    elif "flipkart" in p_lower: domain = "flipkart.com"
                    elif "aliexpress" in p_lower: domain = "aliexpress.com"
                elif "github" in p_lower: domain = "github.com"
                elif "arxiv" in p_lower: domain = "arxiv.org"
                elif "coursera" in p_lower: domain = "coursera.org"
                elif "reddit" in p_lower: domain = "reddit.com"
                elif "twitter" in p_lower or " x " in p_lower: domain = "twitter.com"
                elif "instagram" in p_lower: domain = "instagram.com"
                elif "linkedin" in p_lower: domain = "linkedin.com"
                elif "hotstar" in p_lower: domain = "hotstar.com"
                elif "espn" in p_lower: domain = "espn.com"
                elif "chatgpt" in p_lower or "openai" in p_lower: domain = "chatgpt.com"
                elif "tradingview" in p_lower or "binance" in p_lower: domain = "tradingview.com"
                
            label = label_engine.classify_browser_tab(domain or "", page, browser_name)
        else:
            label = label_engine.match_generic_keywords(title.lower())

    if not label:
        label = config.FALLBACK_ACTIVITY

    elapsed = (time.perf_counter() - t) * 1000
    
    # Use the classifier's result builder to follow the same logic
    return _classifier._make_result(
        label=label,
        method="heuristic",
        window_title=title,
        elapsed_ms=elapsed,
        confidence=0.92,
        process_name="" # we don't have it here
    )


# ──────────────────────────────────────────────────────────────────────────────
# POST /analyze/activity — full pipeline (server captures its own screen)
# ──────────────────────────────────────────────────────────────────────────────
@router.post(
    "/analyze/activity",
    response_model=ActivityResult,
    responses={500: {"model": ErrorResponse}},
    summary="Full pipeline — server captures and classifies active window",
)
async def analyze_activity() -> ActivityResult:
    loop = asyncio.get_event_loop()
    try:
        result: ActivityResult = await loop.run_in_executor(
            _executor, _classifier.run_pipeline
        )
        return result
    except Exception as exc:
        logger.exception("Activity pipeline failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/analyze/remote",
    response_model=ActivityResult,
    summary="Remote pipeline — client uploads screenshot and window title",
)
async def analyze_remote(
    file: UploadFile = File(...),
    window_title: str = Form(""),
) -> ActivityResult:
    """Classify an uploaded image and title (used by remote clients)."""
    loop = asyncio.get_event_loop()
    try:
        # Read file content and open as PIL Image
        content = await file.read()
        image = PILImage.open(io.BytesIO(content)).convert("RGB")
        
        result: ActivityResult = await loop.run_in_executor(
            _executor, _classifier.run_pipeline, image, window_title
        )
        return result
    except Exception as exc:
        logger.exception("Remote pipeline failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
