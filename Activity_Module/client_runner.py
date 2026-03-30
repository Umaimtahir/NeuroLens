import sys
import time
import io
import re
import warnings
import requests
import mss
import os
from datetime import datetime
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
import pywinctl as pwc

# Suppress pywinctl warnings for unreadable titles
warnings.filterwarnings("ignore", category=UserWarning)

POLL_INTERVAL = 2.0


# ═══════════════════════════════════════════════════════════════════════════
# LOCAL FAST-PATH CLASSIFIER — resolves ~95% of activities instantly
# No network call needed. Uses window title only.
# ═══════════════════════════════════════════════════════════════════════════

# Browser suffixes to strip from titles
_BROWSER_SUFFIXES = [
    # Must be ordered longest-first for proper matching
    " - Personal - Microsoft Edge", " - Work - Microsoft Edge",
    " and 2 more pages - Google Chrome", " and 1 more page - Google Chrome",
    " and 2 more pages - Microsoft Edge", " and 1 more page - Microsoft Edge",
    " - Google Chrome", " - Microsoft Edge", " - Mozilla Firefox",
    " - Brave", " - Opera", " - Safari", " — Mozilla Firefox",
    " - Chromium", " | Google Chrome", " | Microsoft Edge",
]

def _strip_browser_suffix(title: str) -> str:
    """Remove browser name suffix from window title."""
    t = title
    for suffix in _BROWSER_SUFFIXES:
        if t.endswith(suffix):
            t = t[:-len(suffix)].strip()
            break
    return t

def _is_browser_title(title: str) -> bool:
    """Check if title belongs to a browser window."""
    if any(title.endswith(s) for s in _BROWSER_SUFFIXES):
        return True
    t = title.lower()
    if any(k in t for k in ["google chrome", "microsoft edge", "mozilla firefox",
                             "brave browser"]):
        return True
    return False


def _classify_youtube(video_title: str) -> str:
    """Deep YouTube genre classification from the actual video title."""
    vt = video_title.lower()

    # YouTube-specific pages (not watching a video)
    if not vt or vt in ("youtube", "youtube.com", "home", "home - youtube"):
        return "YouTube - Browsing"

    if any(k in vt for k in ["search results", "subscriptions", "trending",
                              "watch later", "history", "library",
                              "liked videos", "your videos"]):
        return "YouTube - Browsing"

    # Shorts
    if "shorts" in vt or "#shorts" in vt:
        return "YouTube - Shorts"

    # Live streams
    if any(k in vt for k in ["live", "🔴", "streaming now", "premiere"]):
        return "YouTube - Live"

    # Music
    if any(k in vt for k in ["music", "song", "lyrics", "official audio",
                              "official video", " mv ", "album", "remix",
                              "feat.", "ft.", " ost", "soundtrack",
                              "karaoke", "playlist", "lofi", "lo-fi",
                              "slowed", "reverb", "bass boosted"]):
        return "YouTube - Music"

    # Tutorial / Educational
    if any(k in vt for k in ["tutorial", "how to", "learn", "course",
                              "lecture", "lesson", "explained",
                              "for beginners", "step by step",
                              "crash course", "masterclass",
                              "full course", "bootcamp", "guide to",
                              "introduction to", "what is "]):
        return "YouTube - Tutorial"

    # Drama / Series / Episodes
    if any(k in vt for k in ["drama", "serial", "episode", "ep ",
                              "ep.", "season", "s01", "s02", "s1", "s2",
                              "kdrama", "web series", "ertugrul",
                              "kurulus", "part ", "pt.", "chapter",
                              "dubbed", "eng sub", "urdu sub"]):
        return "YouTube - Drama"

    # Sports
    if any(k in vt for k in ["match", "cricket", "football", "soccer",
                              "highlights", "goal", "world cup",
                              "psl", "ipl", "nba", "nfl",
                              "tennis", "boxing", "ufc", "mma",
                              "f1", "formula 1", "race",
                              "vs ", "versus", "semifinal", "final",
                              "innings", "wicket", "batting", "bowling",
                              "penalty", "championship"]):
        return "YouTube - Sports"

    # Gaming
    if any(k in vt for k in ["gameplay", "walkthrough", "gaming",
                              "let's play", "lets play", "playthrough",
                              "speedrun", "fortnite", "minecraft",
                              "gta", "valorant", "cod ", "pubg",
                              "among us", "apex", "elden ring",
                              "boss fight", "game review"]):
        return "YouTube - Gaming"

    # Comedy / Entertainment
    if any(k in vt for k in ["comedy", "funny", "standup", "stand-up",
                              "prank", "meme", "roast", "sketch",
                              "parody", "blooper", "try not to laugh",
                              "reaction", "challenge"]):
        return "YouTube - Entertainment"

    # News / Politics
    if any(k in vt for k in ["news", "breaking", "politics",
                              "election", "debate", "press conference",
                              "headline", "geo news", "ary news",
                              "dawn news", "bbc", "cnn", "al jazeera"]):
        return "YouTube - News"

    # Vlog / Lifestyle
    if any(k in vt for k in ["vlog", "daily", "routine", "day in",
                              "travel", "trip", "tour", "haul",
                              "grwm", "get ready", "room tour"]):
        return "YouTube - Vlog"

    # Review / Unboxing
    if any(k in vt for k in ["review", "unboxing", "hands on",
                              "comparison", "best ", "top 10",
                              "top 5", "worth it"]):
        return "YouTube - Review"

    # Podcast / Interview
    if any(k in vt for k in ["podcast", "interview", "talk show",
                              "conversation with"]):
        return "YouTube - Podcast"

    # Cooking / Food
    if any(k in vt for k in ["recipe", "cooking", "kitchen", "food",
                              "baking", "chef", "meal"]):
        return "YouTube - Cooking"

    # Fitness
    if any(k in vt for k in ["workout", "exercise", "fitness", "yoga",
                              "gym", "weight loss"]):
        return "YouTube - Fitness"

    # Documentary
    if any(k in vt for k in ["documentary", "history of", "the story of",
                              "how ", "why ", "explained"]):
        return "YouTube - Documentary"

    # Religious
    if any(k in vt for k in ["quran", "islamic", "bayan", "tariq jameel",
                              "naat", "nasheed", "tilawat", "jumma",
                              "ramadan", "prayer"]):
        return "YouTube - Religious"

    # Default: user is watching a video
    return "YouTube - Video"


def _extract_domain_label(page: str) -> str:
    """Extract a clean domain-based label from a URL-like page title."""
    url_clean = page.replace("https://", "").replace("http://", "").replace("www.", "")
    domain_part = url_clean.split("/")[0].split("?")[0]

    # Known research/academic domains
    research_domains = ["arxiv", "scholar", "pubmed", "ieee", "acm",
                        "springer", "neurips", "proceedings", "sciencedirect",
                        "researchgate", "semanticscholar", "openreview"]
    if any(k in domain_part for k in research_domains):
        return "Research Paper - Reading"

    # PDF files
    if ".pdf" in page:
        return "Research Paper - Reading"

    # Extract readable domain name (e.g., "neurips" from "proceedings.neurips.cc")
    parts = domain_part.replace("-", ".").split(".")
    # Pick the most meaningful part (usually 2nd-to-last or the longest)
    meaningful = [p for p in parts if len(p) > 2 and p not in ("com", "org", "net",
                  "io", "cc", "pk", "in", "co", "uk", "www", "en")]
    if meaningful:
        name = max(meaningful, key=len)  # Pick longest meaningful part
        return f"{name.capitalize()} - Browsing"

    return "Browser - Web"


def _classify_local(title: str):
    """
    Instant local classification from window title alone.
    Returns a label or None if remote inference is needed.
    """
    if not title:
        return None

    t_lower = title.lower()

    # ── Non-Browser Apps (detect by window title patterns) ────────────
    # Terminal
    if any(k in t_lower for k in ["powershell", "command prompt", "cmd.exe",
                                    "windows terminal", "bash", "ubuntu",
                                    "administrator:", "windows powershell",
                                    "select administrator"]):
        return "Terminal - Command"

    # VS Code
    if "visual studio code" in t_lower or t_lower.endswith("- code"):
        if "debug" in t_lower or "breakpoint" in t_lower:
            return "VS Code - Debugging"
        if "git" in t_lower or "merge" in t_lower:
            return "VS Code - Version Control"
        return "VS Code - Coding"

    # Discord
    if "discord" in t_lower and not _is_browser_title(title):
        if "voice" in t_lower:
            return "Discord - Voice"
        return "Discord - Chat"

    # Spotify (desktop app)
    if "spotify" in t_lower and not _is_browser_title(title):
        if "podcast" in t_lower:
            return "Spotify - Podcast"
        return "Spotify - Music"

    # Zoom
    if "zoom" in t_lower and ("meeting" in t_lower or t_lower.startswith("zoom")):
        if "sharing" in t_lower or "presenting" in t_lower:
            return "Zoom - Screen Share"
        return "Zoom - Meeting"

    # Teams
    if "microsoft teams" in t_lower or ("teams" in t_lower and "chat" in t_lower):
        if "chat" in t_lower:
            return "Teams - Chat"
        return "Teams - Meeting"

    # Word
    if "- word" in t_lower or "microsoft word" in t_lower:
        if "review" in t_lower:
            return "Word - Reviewing"
        return "Word - Writing"

    # Excel
    if "- excel" in t_lower or "microsoft excel" in t_lower:
        return "Excel - Data Entry"

    # PowerPoint
    if "powerpoint" in t_lower:
        if "slide show" in t_lower:
            return "PowerPoint - Presenting"
        return "PowerPoint - Creating"

    # File Explorer
    if t_lower in ["file explorer", "this pc", "downloads", "documents", "desktop"]:
        return "File Explorer - Browsing"

    # Task Manager
    if "task manager" in t_lower:
        return "Task Manager - Monitoring"

    # Photoshop
    if "photoshop" in t_lower:
        return "Photoshop - Editing"

    # Figma (desktop)
    if "figma" in t_lower and not _is_browser_title(title):
        return "Figma - Designing"

    # Blender
    if "blender" in t_lower:
        if "render" in t_lower:
            return "Blender - Rendering"
        return "Blender - Modeling"

    # Premiere Pro
    if "premiere pro" in t_lower:
        return "Premiere Pro - Editing"

    # Notepad
    if "notepad" in t_lower:
        return "Notepad - Editing"

    # VLC
    if "vlc" in t_lower:
        return "VLC - Video"

    # Settings
    if "settings" in t_lower and ("windows" in t_lower or "system" in t_lower):
        return "Settings - Configuring"

    # ══════════════════════════════════════════════════════════════════
    # BROWSER APPS — Deep website + intent classification
    # ══════════════════════════════════════════════════════════════════
    if _is_browser_title(title):
        page = _strip_browser_suffix(title).strip()
        page_lower = page.lower()

        # ── URL DETECTION: don't output raw URLs ─────────────────────
        is_url = any(k in page_lower for k in ["://", ".com/", ".org/", ".net/",
                                                 ".io/", ".cc/", ".pk/", ".in/",
                                                 ".edu/"])
        if is_url:
            return _extract_domain_label(page_lower)

        # ── YOUTUBE — Deep Genre Classification ──────────────────────
        if "youtube" in page_lower:
            # Strip "- YouTube" suffix to get the actual video title
            video_title = page
            for yt_suffix in ["- YouTube", "| YouTube", "— YouTube",
                              "- youtube", "| youtube", "— youtube"]:
                if yt_suffix in page:
                    video_title = page[:page.rfind(yt_suffix)].strip()
                    break

            # If only "youtube" or empty, user is on homepage
            if not video_title or video_title.lower() in ("youtube", "youtube.com", "home"):
                return "YouTube - Browsing"

            return _classify_youtube(video_title)

        # ── Netflix ──────────────────────────────────────────────────
        if "netflix" in page_lower:
            return "Netflix - Watching"

        # ── Amazon (check before generic shopping) ───────────────────
        if "amazon" in page_lower:
            if any(k in page_lower for k in ["checkout", "cart"]):
                return "Amazon - Checkout"
            return "Amazon - Shopping"

        # ── Shopping Sites ───────────────────────────────────────────
        if "olx" in page_lower:
            return "OLX - Shopping"
        if "daraz" in page_lower:
            return "Daraz - Shopping"
        if "flipkart" in page_lower:
            return "Flipkart - Shopping"
        if "ebay" in page_lower:
            return "eBay - Shopping"
        if "walmart" in page_lower:
            return "Walmart - Shopping"
        if "aliexpress" in page_lower:
            return "AliExpress - Shopping"

        # ── GitHub ───────────────────────────────────────────────────
        if "github" in page_lower:
            if "pull request" in page_lower or "/pull/" in page_lower:
                return "GitHub - PR Review"
            if any(k in page_lower for k in [".py", ".js", ".ts", "blob/"]):
                return "GitHub - Code Review"
            return "GitHub - Browsing"

        # ── Gmail ────────────────────────────────────────────────────
        if "gmail" in page_lower or ("inbox" in page_lower and "google" in page_lower):
            if "compose" in page_lower or "new message" in page_lower:
                return "Gmail - Composing"
            return "Gmail - Reading"

        # ── Google Meet ──────────────────────────────────────────────
        if "meet.google" in page_lower or "google meet" in page_lower:
            return "Google Meet - Meeting"

        # ── Google Docs / Sheets / Slides ────────────────────────────
        if "google docs" in page_lower or "docs.google" in page_lower:
            return "Google Docs - Writing"
        if "google sheets" in page_lower or "sheets.google" in page_lower:
            return "Google Sheets - Editing"
        if "google slides" in page_lower or "slides.google" in page_lower:
            return "Google Slides - Editing"

        # ── Kaggle ───────────────────────────────────────────────────
        if "kaggle" in page_lower:
            if "notebook" in page_lower or "kernel" in page_lower:
                return "Kaggle - Notebook"
            return "Kaggle - Browsing"

        # ── Reddit ───────────────────────────────────────────────────
        if "reddit" in page_lower:
            if "comment" in page_lower:
                return "Reddit - Comments"
            return "Reddit - Browsing"

        # ── Twitter / X (strict matching) ────────────────────────────
        if "twitter" in page_lower:
            return "Twitter - Browsing"
        # X.com titles look like "(2) Home / X" or similar
        if page_lower.endswith("/ x") or page_lower.endswith("| x"):
            return "Twitter - Browsing"

        # ── Stack Overflow ───────────────────────────────────────────
        if "stack overflow" in page_lower or "stackoverflow" in page_lower:
            return "Stack Overflow - Problem Solving"

        # ── LinkedIn ─────────────────────────────────────────────────
        if "linkedin" in page_lower:
            return "LinkedIn - Browsing"

        # ── Learning Platforms ───────────────────────────────────────
        if "coursera" in page_lower:
            if "quiz" in page_lower or "assignment" in page_lower:
                return "Coursera - Quiz"
            return "Coursera - Lecture"
        if "udemy" in page_lower:
            return "Udemy - Lecture"
        if any(k in page_lower for k in ["khanacademy", "khan academy"]):
            return "Khan Academy - Lecture"
        if "edx" in page_lower:
            return "edX - Lecture"

        # ── Coding Platforms ─────────────────────────────────────────
        if "leetcode" in page_lower:
            return "LeetCode - Coding Practice"
        if "hackerrank" in page_lower:
            return "HackerRank - Practice"

        # ── AI / ChatGPT ─────────────────────────────────────────────
        if any(k in page_lower for k in ["chatgpt", "claude", "gemini", "perplexity"]):
            return "ChatGPT - AI Chat"

        # ── Messaging ────────────────────────────────────────────────
        if "whatsapp" in page_lower:
            return "WhatsApp - Chat"

        # ── Wikipedia ────────────────────────────────────────────────
        if "wikipedia" in page_lower:
            return "Wikipedia - Reading"

        # ── Medium / Blog ────────────────────────────────────────────
        if "medium" in page_lower:
            return "Medium - Reading"

        # ── Design Tools ─────────────────────────────────────────────
        if "figma" in page_lower:
            return "Figma - Designing"
        if "canva" in page_lower:
            return "Canva - Designing"

        # ── Social Media ─────────────────────────────────────────────
        if "instagram" in page_lower:
            return "Instagram - Browsing"
        if "facebook" in page_lower:
            return "Facebook - Browsing"
        if "tiktok" in page_lower:
            return "TikTok - Browsing"

        # ── Streaming ────────────────────────────────────────────────
        if "twitch" in page_lower:
            return "Twitch - Watching"
        if any(k in page_lower for k in ["hotstar", "disney+", "disneyplus"]):
            return "Disney+ - Watching"
        if "primevideo" in page_lower or "prime video" in page_lower:
            return "Prime Video - Watching"
        if "dazn" in page_lower:
            return "DAZN - Sports"
        if "spotify" in page_lower:
            if "podcast" in page_lower:
                return "Spotify - Podcast"
            return "Spotify - Music"

        # ── Research / Academic ──────────────────────────────────────
        if "arxiv" in page_lower:
            return "arXiv - Reading Paper"
        if any(k in page_lower for k in ["ieee", "springer", "researchgate",
                                          "sciencedirect", "pubmed", "scholar",
                                          "semanticscholar"]):
            return "Research Paper - Reading"
        if ".pdf" in page_lower:
            return "Research Paper - Reading"

        # ── Banking ──────────────────────────────────────────────────
        if any(k in page_lower for k in ["banking", "net banking", "bank "]):
            return "Banking - Account"

        # ── Work Tools (web) ─────────────────────────────────────────
        if "notion" in page_lower:
            return "Notion - Writing"
        if "slack" in page_lower:
            return "Slack - Chat"
        if "trello" in page_lower:
            return "Trello - Project Management"
        if "jira" in page_lower:
            return "Jira - Project Management"

        # ── Other Sites ──────────────────────────────────────────────
        if "pinterest" in page_lower:
            return "Pinterest - Browsing"
        if "quora" in page_lower:
            return "Quora - Reading"
        if "google" in page_lower:
            return "Google - Searching"

        # ── New Tab ──────────────────────────────────────────────────
        if "new tab" in page_lower or not page_lower.strip():
            return "Browser - Web"

        # ── Smart Unknown: extract clean site name ───────────────────
        # Strip common suffixes
        clean = page_lower
        for suffix in [" - home", " | home", " - login", " - sign in",
                       " | official", " - official", " - search"]:
            if clean.endswith(suffix):
                clean = clean[:clean.rfind(suffix)].strip()

        words = clean.strip().split()
        if words:
            first_word = words[0].strip('.-_|/\\:')
            skip_words = {"the", "a", "an", "and", "or", "is", "to", "in",
                         "of", "for", "on", "at", "by", "it", "this", "you",
                         "my", "no", "we", "how", "what", "just", "page",
                         "web", "home", "sign", "log", "welcome", "loading",
                         "error", "untitled", "http", "https", "www"}
            has_url = "/" in first_word or "?" in first_word or "=" in first_word
            if (first_word not in skip_words
                    and len(first_word) > 2
                    and not has_url
                    and not first_word.replace(".", "").isdigit()):
                return f"{first_word.capitalize()} - Browsing"

        return "Browser - Web"

    # Unknown app -> need remote inference
    return None


class ClientRunner:
    def __init__(self, endpoint_url: str):
        self.endpoint_url = endpoint_url.rstrip("/") + "/analyze/remote"
        self.sct = mss.mss()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self._is_sending = False
        print(f"🚀 NeuroLens Client Started [Poll: {POLL_INTERVAL}s]")
        print("-" * 40)
        
    def _get_active_window_title(self) -> str:
        try:
            active_win = pwc.getActiveWindow()
            return active_win.title if active_win and active_win.title else ""
        except Exception:
            return ""

    def _capture_screen(self) -> Image.Image:
        monitor = self.sct.monitors[1]
        sct_img = self.sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        return img

    def _send_payload(self, img: Image.Image, title: str):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        buf.seek(0)

        try:
            files = {"file": ("screenshot.jpg", buf, "image/jpeg")}
            data = {"window_title": title}
            resp = requests.post(self.endpoint_url, files=files, data=data, timeout=10)
            
            if resp.status_code == 200:
                res = resp.json()
                label = res.get("content", {}).get("activity", "")
                if label and label not in ("Unknown", "Unknown - Processing"):
                    ts = datetime.now().strftime("%H:%M:%S")
                    print(f"[{ts}]  {label}")

        except Exception:
            pass
        finally:
            self._is_sending = False

    def capture_and_send_async(self):
        if self._is_sending:
            return

        title = self._get_active_window_title()

        # ── FAST PATH: Try local classification first (instant, no network) ──
        local_label = _classify_local(title)
        if local_label:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}]  {local_label}")
            return

        # ── SLOW PATH: Unknown activity, use Kaggle AI inference ──
        img = self._capture_screen()
        self._is_sending = True
        self.executor.submit(self._send_payload, img, title)

    def run(self):
        try:
            while True:
                start = time.time()
                self.capture_and_send_async()
                elapsed = time.time() - start
                
                sleep_time = max(0.1, POLL_INTERVAL - elapsed)
                time.sleep(sleep_time)
        except KeyboardInterrupt:
            print("\n🛑 Stopped NeuroLens Client")
            self.executor.shutdown(wait=False)
            sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python client_runner.py <SERVER_URL>")
        sys.exit(1)
        
    url = sys.argv[1]
    runner = ClientRunner(url)
    runner.run()
