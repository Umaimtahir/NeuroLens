"""
ActivityClassifier — Optimized Zero-Shot "Focus-Aware" Pipeline
===============================================================

Same 4-step pipeline, aggressively optimized for <1.5s end-to-end:

  Step 0  Idle / AFK detection            ~0ms   (ctypes GetLastInputInfo)
  Step 1  Focus Acquisition               ~30ms  (mss + pywinctl)
  Step 1b Title-Based Heuristics          ~0ms   (trie-like keyword match)
  Step 1c Process-level fast classify     ~0ms   (behavioral signals)
  Step 1d Screenshot hash cache           ~0ms   (skip re-inference if unchanged)
  Step 2  CLIP Visual Gate                ~80ms  (224×224 image, threshold 0.60)
  Step 3  Florence-2 OCR                  ~500ms (512×512 image, use_cache=True, 64 tokens)
  Step 3b OCR content heuristics         ~0ms
  Step 3c Florence-2 Caption (if needed)  ~500ms (only if OCR heuristics fail)
  Step 4  Qwen2.5 Reasoning               ~350ms (32 tokens, pre-tokenized sys prompt)

  Multi-label:  Background processes (Spotify, Discord) → secondary_activities
  Temporal:     ActivityStateMachine smooths rapid switching via deque
  Privacy:      No disk writes; OCR text purged after classification

All output labels use "Category - Subcategory" format.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

import torch
from PIL import Image

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from activity_classifier import models, label_engine, app_signatures
from activity_classifier.schemas import ActivityResult
from activity_classifier.behavioral import get_collector, get_idle_seconds, BehavioralSignals

logger = logging.getLogger(__name__)


# ===========================================================================
# Helpers
# ===========================================================================

_JSON_RE = re.compile(r"\{.*?\}", re.DOTALL)


def _parse_llm_json(text: str) -> dict:
    """Extract {activity: ...} from raw LLM output."""
    match = _JSON_RE.search(text)
    if match:
        try:
            data = json.loads(match.group())
            activity = str(data.get("activity", config.FALLBACK_ACTIVITY)).strip()
            # Normalize: if LLM returns bare label, try to match taxonomy
            if " - " not in activity:
                activity = _normalize_bare_label(activity)
            return {"activity": activity}
        except (json.JSONDecodeError, ValueError):
            pass
    # Try to find any quoted taxonomy label in the text
    for label in config.VALID_TAXONOMY_LABELS:
        if label.lower() in text.lower():
            return {"activity": label}
    logger.warning("Could not parse JSON from LLM: %r", text[:200])
    return {"activity": config.FALLBACK_ACTIVITY}


def _normalize_bare_label(label: str) -> str:
    """Convert bare subcategory ('Coding') to 'Category - Subcategory'."""
    label_lower = label.lower()
    for cat, subs in config.TAXONOMY.items():
        for sub in subs:
            if sub.lower() == label_lower or sub.lower() in label_lower:
                return f"{cat} - {sub}"
    return config.FALLBACK_ACTIVITY


def _split_label(label: str) -> Tuple[str, str]:
    """Split 'Category - Subcategory' into (category, subcategory)."""
    if " - " in label:
        parts = label.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()
    return label.strip(), ""


def _image_hash(image: Image.Image) -> str:
    """Fast perceptual hash of image for cache comparison."""
    small = image.resize((16, 16)).convert("L")
    return hashlib.md5(small.tobytes()).hexdigest()


def _resize_image(image: Image.Image, max_size: Tuple[int, int]) -> Image.Image:
    """Resize image maintaining aspect ratio if it exceeds max_size."""
    w, h = image.size
    max_w, max_h = max_size
    if w <= max_w and h <= max_h:
        return image
    ratio = min(max_w / w, max_h / h)
    new_size = (int(w * ratio), int(h * ratio))
    return image.resize(new_size, Image.LANCZOS)


# ===========================================================================
# Browser detection
# ===========================================================================
_BROWSER_SUFFIXES = re.compile(
    r"(?:[-–—|]\s*)?(google chrome|chromium|mozilla firefox|firefox|"
    r"microsoft edge|edge|opera|brave|safari|vivaldi|arc)\s*$",
    re.IGNORECASE,
)


def _detect_browser(window_title: str) -> bool:
    return bool(_BROWSER_SUFFIXES.search(window_title))


# ===========================================================================
# OCR Content Heuristics (post-Florence-2 OCR) — all return "Cat - Sub"
# ===========================================================================
_CODE_PATTERNS = [
    "def ", "class ", "import ", "from ", "function ", "const ", "var ", "let ",
    "public ", "private ", "return ", "#include", "console.log", "print(",
    "System.out", "void ", "async ", "await ", "interface ", "struct ",
    "module ", "namespace ", "lambda ", "fn ", "=>", "self.",
]

_ECOMMERCE_WORDS = [
    "add to cart", "buy now", "view listing", "sold by", "in stock",
    "free delivery", "free shipping", "checkout", "place order",
    "seller rating", "best deals", "flash sale", "product description",
    "customer reviews", "add to wishlist", "out of stock",
]

_STUDENT_PORTAL_WORDS = [
    "student portal", "my courses", "my grades", "gpa", "cgpa",
    "credit hours", "semester", "enrollment", "course registration",
    "timetable", "blackboard", "canvas", "moodle", "lms",
    "assignment submission", "quiz attempt", "attendance",
]

_ACADEMIC_WORDS = [
    "abstract", "introduction", "methodology", "conclusion",
    "references", "bibliography", "et al.", "doi:", "journal of",
    "proceedings of", "arxiv", "theorem", "hypothesis", "literature review",
]

_FINANCE_WORDS = [
    "portfolio", "share price", "market cap", "dividend", "balance sheet",
    "transaction history", "account number", "wire transfer", "deposit",
    "withdrawal", "candlestick", "bollinger", "rsi", "profit/loss",
]

_COMM_WORDS = [
    "message sent", "typing...", "voice call", "video call",
    "screen share", "you replied", "you said:", "online",
]

_NEWS_WORDS = [
    "breaking news", "published on", "last updated", "share article",
    "read more", "related articles", "by our correspondent",
    "opinion:", "subscribe to newsletter",
]

_IDLE_WORDS = ["lock screen", "screensaver", "sleeping", "hibernate", "idle"]


def _detect_ocr_activity(ocr_text: str) -> Optional[str]:
    """Fast text heuristics on OCR output → 'Category - Subcategory'."""
    if not ocr_text or len(ocr_text.strip()) < 10:
        return None
    ocr_lower = ocr_text.lower()
    # Priority order matters
    if any(p in ocr_text for p in _CODE_PATTERNS):
        return "Work - Coding"
    if any(kw in ocr_lower for kw in _ACADEMIC_WORDS):
        return "Research - Paper Reading"
    if any(kw in ocr_lower for kw in _STUDENT_PORTAL_WORDS):
        return "Learning - Online Course"
    if any(kw in ocr_lower for kw in _ECOMMERCE_WORDS):
        return "Shopping - E-Commerce"
    if any(kw in ocr_lower for kw in _FINANCE_WORDS):
        return "Financial - Banking"
    if any(kw in ocr_lower for kw in _NEWS_WORDS):
        return "Information - News Reading"
    if any(kw in ocr_lower for kw in _COMM_WORDS):
        return "Communication - Messaging"
    if any(kw in ocr_lower for kw in _IDLE_WORDS):
        return "Idle - Idle"
    return None


# ===========================================================================
# Temporal Activity State Machine
# ===========================================================================
class ActivityStateMachine:
    """
    Lightweight deque-based state machine that smooths classification results.

    States:
      stable       — same activity N times in a row (high confidence)
      transitioning — activity recently changed (confidence boosted by recency)
      multitasking — multiple distinct categories in recent window
      idle         — overridden by AFK detection
    """

    def __init__(self, buffer_size: int = 5, stable_count: int = 2):
        self._buffer: Deque[str] = deque(maxlen=buffer_size)
        self._stable_count = stable_count

    def push(self, label: str) -> None:
        self._buffer.append(label)

    def get_temporal_state(self) -> str:
        if not self._buffer:
            return "stable"
        # Count distinct categories
        cats = {lbl.split(" - ")[0] for lbl in self._buffer if " - " in lbl}
        if len(cats) >= 3:
            return "multitasking"
        # Check stability
        recent = list(self._buffer)[-self._stable_count:]
        if len(recent) == self._stable_count and len(set(recent)) == 1:
            return "stable"
        return "transitioning"

    def smoothed_label(self, raw_label: str) -> str:
        """
        Apply majority-vote smoothing: if >50% of buffer is a different label,
        override the raw label to prevent single-frame misclassification.
        """
        if len(self._buffer) < 3:
            return raw_label
        from collections import Counter
        counts = Counter(self._buffer)
        top_label, top_count = counts.most_common(1)[0]
        # Override only if majority strongly agrees and differs from raw
        if top_count >= len(self._buffer) * 0.6 and top_label != raw_label:
            logger.debug(
                "Temporal smoothing: %r → %r (buffer majority)", raw_label, top_label
            )
            return top_label
        return raw_label

    def confidence_boost(self, base_conf: float) -> float:
        """Boost confidence when activity is stable."""
        if self.get_temporal_state() == "stable":
            return min(1.0, base_conf + 0.1)
        return base_conf


# ===========================================================================
# ActivityClassifier
# ===========================================================================
class ActivityClassifier:
    """
    Optimized Focus-Aware Activity Classification pipeline.

    Same 4-step architecture, optimized to complete in <1.5 seconds:
      1. Focus Acquisition (mss + pywinctl)
      2. CLIP Visual Gate (224×224 image, threshold 0.60)
      3. Florence-2 OCR → content heuristics (512×512, use_cache=True, 64 tokens)
         Florence-2 Caption (skipped if OCR resolves)
      4. Qwen2.5 Reasoning (32 tokens, pre-tokenized system prompt)

    Plus:
      - Background behavioral signals (BehavioralCollector daemon thread)
      - Temporal state machine (ActivityStateMachine)
      - Multi-label secondary activity detection
      - AFK/Idle detection via GetLastInputInfo
      - Screenshot hash caching (skip inference on identical frames)
    """

    def __init__(self):
        # Start behavioral signal collector (daemon thread, 0 latency impact)
        self._behavioral = get_collector(
            poll_interval=config.BEHAVIORAL_POLL_INTERVAL,
            idle_threshold=config.IDLE_THRESHOLD_SECONDS,
        )
        # Temporal state machine
        self._tsm = ActivityStateMachine(
            buffer_size=config.MULTITASK_BUFFER_SIZE,
            stable_count=config.TRANSITION_SMOOTH_COUNT,
        )
        # Session management
        import uuid
        self._session_id = str(uuid.uuid4())
        self._session_start_time = time.time()
        self._current_activity_start_time = time.time()
        self._current_activity_label = ""
        
        # Screenshot cache
        self._last_img_hash: Optional[str] = None
        self._last_result: Optional[ActivityResult] = None
        self._last_result_time: float = 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # Step 1: Focus Acquisition
    # ─────────────────────────────────────────────────────────────────────────
    def capture_window(self) -> Tuple[Image.Image, str]:
        """Capture the active window screenshot and window title."""
        try:
            import mss
            import pywinctl as pwc

            win = pwc.getActiveWindow()
            title = win.title if win else ""

            with mss.mss() as sct:
                monitor = sct.monitors[1]
                sct_img = sct.grab(monitor)
                img = Image.frombytes(
                    "RGB", sct_img.size, sct_img.bgra, "raw", "BGRX"
                )
            return img, title
        except Exception as exc:
            logger.warning("capture_window failed: %s", exc)
            return Image.new("RGB", (100, 100)), ""

    # ─────────────────────────────────────────────────────────────────────────
    # Step 2: CLIP Visual Gate (224×224, threshold 0.60)
    # ─────────────────────────────────────────────────────────────────────────
    def visual_gate(self, image: Image.Image) -> Optional[Tuple[str, float]]:
        """
        Run CLIP zero-shot classification.
        Image is pre-resized to 224×224 before inference (3× faster).
        Returns (label, confidence) if above threshold, else None.
        """
        # Resize to CLIP native size — eliminates wasted computation on full-res
        clip_img = image.resize(config.CLIP_IMAGE_SIZE, Image.LANCZOS)

        clip_model, clip_processor = models.get_clip()
        device = next(clip_model.parameters()).device

        inputs = clip_processor(
            text=config.VISUAL_GATE_ANCHORS,
            images=clip_img,
            return_tensors="pt",
            padding=True,
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = clip_model(**inputs)

        probs = outputs.logits_per_image.softmax(dim=-1).squeeze(0).cpu().float()
        scores = probs.tolist()
        best_idx = int(torch.argmax(probs).item())
        best_score = scores[best_idx]
        best_anchor = config.VISUAL_GATE_ANCHORS[best_idx]

        logger.debug(
            "CLIP best: '%s' (%.3f) threshold=%.2f",
            best_anchor, best_score, config.VISUAL_GATE_THRESHOLD,
        )

        if best_score >= config.VISUAL_GATE_THRESHOLD:
            label = config.CLIP_LABEL_MAP.get(best_anchor, config.FALLBACK_ACTIVITY)
            logger.info("CLIP gate hit: '%s' → '%s' (%.3f)", best_anchor, label, best_score)
            return label, float(best_score)
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Step 3: Florence-2 OCR (512×512, use_cache=True, 64 tokens)
    # ─────────────────────────────────────────────────────────────────────────
    def _run_florence_task(
        self, image: Image.Image, task_prompt: str, max_new_tokens: int
    ) -> str:
        """
        Run a single Florence-2 task.
        Key optimizations vs original:
          - image pre-resized to 512×512 (caller responsibility)
          - use_cache=True  (was False — this was the main bottleneck!)
          - max_new_tokens reduced (task-specific)
        """
        f_model, f_proc = models.get_florence()
        device = next(f_model.parameters()).device

        inputs = f_proc(text=task_prompt, images=image, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            gen_ids = f_model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=max_new_tokens,
                num_beams=1,          # greedy — no beam search overhead
                do_sample=False,
                use_cache=True,       # ← was False! KV cache dramatically speeds up
            )

        result = f_proc.batch_decode(gen_ids, skip_special_tokens=False)[0]
        parsed = f_proc.post_process_generation(
            result, task=task_prompt,
            image_size=(image.width, image.height),
        )
        return str(parsed.get(task_prompt, "")).strip()

    def run_ocr(self, image: Image.Image) -> str:
        """Run Florence-2 OCR on a pre-resized 512×512 image."""
        logger.info("Florence-2: running OCR …")
        # Resize before inference — critical for speed
        small = _resize_image(image, config.MAX_IMAGE_SIZE)
        text = self._run_florence_task(small, "<OCR>", config.FLORENCE_OCR_MAX_TOKENS)
        if not config.PRIVACY_MODE:
            logger.debug("OCR result: %r", text[:200])
        return text

    def run_caption(self, image: Image.Image) -> str:
        """Run Florence-2 detailed caption (only called if OCR heuristics fail)."""
        logger.info("Florence-2: running caption …")
        small = _resize_image(image, config.MAX_IMAGE_SIZE)
        cap = self._run_florence_task(
            small, "<DETAILED_CAPTION>", config.FLORENCE_CAPTION_MAX_TOKENS
        )
        logger.debug("Caption: %r", cap[:200])
        return cap

    # ─────────────────────────────────────────────────────────────────────────
    # Multi-label: detect secondary activities from behavioral signals
    # ─────────────────────────────────────────────────────────────────────────
    def _get_secondary_activities(
        self, primary_label: str, signals
    ) -> List[str]:
        """
        Return list of secondary activities detected from background apps.
        Filters out duplicates of the primary activity category.
        """
        primary_cat = primary_label.split(" - ")[0] if " - " in primary_label else ""
        seen = {primary_label}
        secondary = []
        for bg_label in signals.background_activities:
            if bg_label not in seen:
                bg_cat = bg_label.split(" - ")[0] if " - " in bg_label else ""
                # Only add if it adds a genuinely different signal
                if bg_cat != primary_cat or bg_label not in secondary:
                    seen.add(bg_label)
                    secondary.append(bg_label)
        # Network signals → add background activity hint
        if signals.is_downloading and "System - Downloads" not in seen:
            secondary.append("System - Downloads")
        return secondary[:4]  # cap at 4 secondary activities

    # ─────────────────────────────────────────────────────────────────────────
    # Main pipeline orchestrator
    # ─────────────────────────────────────────────────────────────────────────
    def run_pipeline(self, image_input: Optional[Image.Image] = None, window_title_input: str = "") -> ActivityResult:
        """Run the optimized Activity Classification pipeline."""
        import time
        from activity_classifier import label_engine, app_signatures
        
        t_start = time.time()
        def ms() -> float:
            return (time.time() - t_start) * 1000

        metrics = {}
        
        # ── Step 0: Idle Detection ──────────────────────────────────────
        signals = self._behavioral.signals
        metrics["signals_ms"] = ms()
        
        if signals.is_idle and not window_title_input: # Skip idle check for remote/manual input
            label = label_engine.detect_idle_nuance(signals, self._last_result.content.activity if self._last_result else "")
            return self._make_result(label, "idle", signals.window_title, ms())

        # ── Step 1: Capture ──────────────────────────────────────────────
        if image_input is not None:
            image = image_input
            window_title = window_title_input
            proc_name = "" # Cannot detect process name remotely
        else:
            image, window_title = self.capture_window()
            proc_name = signals.foreground_process
            
        title_lower = window_title.lower()
        metrics["capture_ms"] = ms() - metrics["signals_ms"]

        # ── Step 2: Cache Check ──────────────────────────────────────────
        img_hash = _image_hash(image)
        now = time.time()
        if (self._last_result and img_hash == self._last_img_hash and 
            (now - self._last_result_time) < config.TITLE_CACHE_TTL_SECONDS):
            res = self._last_result
            res.processing_time_ms = ms()
            return res

        # ── Step 3: Heuristics (Label Engine) ───────────────────────────
        # 3a. Desktop App Sub-activity
        label = label_engine.detect_app_subactivity(proc_name, window_title)
        
        # 3b. Browser Tab Detection
        is_browser = _detect_browser(window_title) or (proc_name and label_engine._is_browser_process(proc_name))
        if not label and is_browser:
            browser_name = "Browser"
            m_b = _BROWSER_SUFFIXES.search(window_title)
            if m_b:
                browser_name = m_b.group(1).title()
            elif proc_name:
                browser_name = label_engine._browser_display_name(proc_name)
            
            page_title = _BROWSER_SUFFIXES.sub("", window_title).strip()
            # If domain isn't cleanly extracted by app_signatures, we pass the title and let label_engine guess.
            domain = app_signatures.extract_domain(window_title)
            label = label_engine.classify_browser_tab(domain or "", page_title, browser_name)
            if not label:
                label = "Browser - Web"
            
            
        # 3c. Gaming Fallback if controller is active
        if not label and signals.controller_active:
            if proc_name:
                cleaned = proc_name.replace('.exe', '').title()
                label = f"{cleaned} - Gaming"
            else:
                label = "Game - Playing"

        # 3d. Generic Keyword Fallback
        if not label:
            label = label_engine.match_generic_keywords(title_lower)
            
        if label:
            metrics["heuristic_ms"] = ms() - metrics["capture_ms"] - metrics["signals_ms"]
            return self._make_result(label, "heuristic", window_title, ms(), 
                                    img_hash, proc_name, metrics=metrics)

        # ── Step 4: CLIP Visual Gate ────────────────────────────────────
        gate_res = self.visual_gate(image)
        if gate_res:
            label, conf = gate_res
            metrics["clip_ms"] = ms() - metrics["capture_ms"] - metrics["signals_ms"]
            return self._make_result(label, "visual_gate", window_title, ms(),
                                    img_hash, proc_name, confidence=conf, metrics=metrics)

        # ── Step 5: Florence-2 OCR ───────────────────────────────────────
        ocr_text = self.run_ocr(image)
        metrics["ocr_ms"] = ms() - (metrics.get("clip_ms", 0)) - metrics["capture_ms"] - metrics["signals_ms"]
        
        # Retry granular engine with OCR snippet
        label = label_engine.detect_app_subactivity(proc_name, window_title, ocr_text)
        if not label:
            label = _detect_ocr_activity(ocr_text)
            
        if label:
            return self._make_result(label, "ocr_heuristics", window_title, ms(),
                                    img_hash, proc_name, ocr_text=ocr_text, metrics=metrics)

        # ── Step 6: Visual Reasoning Reasoning ───────────────────────────
        caption = self.run_caption(image)
        metrics["caption_ms"] = ms() - metrics["ocr_ms"] - (metrics.get("clip_ms", 0)) - metrics["capture_ms"] - metrics["signals_ms"]

        logger.info("[%.0fms] Running Qwen reasoning …", ms())
        llm_result = self.finalize_classification(window_title, ocr_text, caption)
        label = llm_result.get("activity")
        if not label or label == config.FALLBACK_ACTIVITY:
            if proc_name:
                cleaned = proc_name.replace('.exe', '').title()
                label = f"{cleaned} - Unknown Activity"
            else:
                label = "Idle - Away from Keyboard"
        
        metrics["llm_ms"] = ms() - metrics["caption_ms"] - metrics["ocr_ms"] - (metrics.get("clip_ms", 0)) - metrics["capture_ms"] - metrics["signals_ms"]
        
        return self._make_result(label, "llm_reasoning", window_title, ms(),
                                img_hash, proc_name, ocr_text=ocr_text, metrics=metrics)

    def _make_result(
        self,
        label: str,
        method: str,
        window_title: str,
        elapsed_ms: float,
        img_hash: Optional[str] = None,
        process_name: str = "",
        ocr_text: str = "",
        confidence: float = 0.90,
        metrics: Optional[Dict] = None,
    ) -> ActivityResult:
        """Common result builder with granular context parsing."""
        from activity_classifier import label_engine
        from activity_classifier.schemas import ContentInfo, ContentDetails, ContextInfo, CorrelationInfo
        import config
        from datetime import datetime, timezone
        
        # 1. Split category/subcategory
        cat, sub = _split_label(label)
        
        # 2. Get granular context from window title
        ctx = label_engine.parse_window_title(window_title, process_name)
        
        # 3. Temporal smoothing
        self._tsm.push(label)
        smoothed = self._tsm.smoothed_label(label)
        # If smoothed label differs, update cat/sub
        if smoothed != label:
            cat, sub = _split_label(smoothed)
            
        # 5. Multi-app fusion (secondary activities)
        signals = self._behavioral.signals
        secondary = signals.background_activities or []
        fused = label_engine.fuse_multi_app_context(smoothed, secondary)
        
        # 6. Final label selection & Active/Passive refinement
        final_label = fused or smoothed
        final_label = label_engine.apply_active_passive_state(final_label, signals)
        
        # 7. Duration and Session tracking
        now = time.time()
        if final_label != self._current_activity_label:
            self._current_activity_label = final_label
            self._current_activity_start_time = now
            
        duration_current = int(now - self._current_activity_start_time)
        session_duration = int(now - self._session_start_time)

        # 8. Interaction intensity heuristic
        velocity = signals.cursor_velocity
        intensity = "none"
        if velocity > 500: intensity = "high"
        elif velocity > 50: intensity = "medium"
        elif velocity > 0: intensity = "low"
        
        # 9. Focus Indicator
        focus = "neutral"
        if "coding" in final_label.lower() or "research" in final_label.lower():
            focus = "deep_work"
        elif "browsing" in final_label.lower() or "social" in final_label.lower():
            focus = "distracted"

        # 10. Build the nested result
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Determine prettified application name
        app_name = ctx.get("app_name")
        if not app_name or app_name == "None":
            app_name = process_name.replace(".exe", "").title() if process_name else "Unknown System"

        content_info = ContentInfo(
            category=cat,
            subcategory=sub,
            activity=final_label,
            application=app_name,
            site=app_signatures.extract_domain(window_title) if _detect_browser(window_title) else None,
            title=window_title,
            details=ContentDetails(
                file=ctx.get("file_name"),
                domain=ctx.get("file_category") or ctx.get("channel"),
                interaction="typing" if signals.idle_seconds < 2 and velocity < 10 else "mouse" if velocity > 10 else "idle",
                media_playing=signals.media_playing,
                typing_active=signals.idle_seconds < 1.0
            ),
            confidence=self._tsm.confidence_boost(confidence)
        )
        
        context_info = ContextInfo(
            duration_current=duration_current,
            session_duration=session_duration,
            input_activity="mouse" if velocity > 10 else "idle",
            window_state="focused"
        )
        
        correlation_info = CorrelationInfo(
            content_type_code=config.get_content_type_code(final_label),
            activity_intensity=intensity,
            focus_indicator=focus,
            break_recommended=(duration_current > 3600 and focus == "deep_work")
        )

        result = ActivityResult(
            timestamp=timestamp,
            session_id=self._session_id,
            content=content_info,
            context=context_info,
            for_correlation=correlation_info,
            method=method,
            processing_time_ms=round(elapsed_ms, 2)
        )
        
        # Update cache
        if img_hash:
            self._last_img_hash = img_hash
            self._last_result = result
            self._last_result_time = time.time()
            
        return result

    def finalize_classification(self, window_title: str, ocr_text: str, caption: str) -> dict:
        """Run Qwen2.5 to reason about all gathered signals."""
        try:
            q_model, q_tokenizer = models.get_qwen()
            device = next(q_model.parameters()).device

            prompt = (
                f"Active Window: {window_title}\n"
                f"Visual Caption: {caption}\n"
                f"Detected Text: {ocr_text[:500]}\n\n"
                f"Classify the activity into one of our valid taxonomy labels.\n"
                f"Output JSON: {{\"activity\": \"Category - Subcategory\"}}"
            )
            
            inputs = q_tokenizer(prompt, return_tensors="pt").to(device)
            with torch.no_grad():
                gen_ids = q_model.generate(**inputs, max_new_tokens=32, do_sample=False)
            
            response = q_tokenizer.decode(gen_ids[0], skip_special_tokens=True)
            return _parse_llm_json(response)
        except Exception as e:
            logger.error("LLM error: %s", e)
            return {"activity": config.FALLBACK_ACTIVITY}
