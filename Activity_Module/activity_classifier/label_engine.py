"""
Granular Label Engine — Application-Aware Activity Classification
=================================================================

Converts raw window titles + process names + behavioral signals into
highly specific labels like:

  "VS Code - Python (Debugging)"
  "Browser - arXiv.org (Research Paper)"
  "Discord - Voice Chat"
  "Excel - Financial Spreadsheet"
  "Entertainment - YouTube (Watching)"
  "Passive - Music Listening"
  "Development - Coding with Music"

API:
  detect_app_subactivity(process, title, ocr_text)
  classify_browser_tab(domain, page_title)
  detect_idle_nuance(signals, last_label)
  fuse_multi_app_context(primary_label, secondary_labels)
  apply_temporal_label(label, duration_seconds)
  parse_window_title(title, process)  → context dict

All functions are pure (no I/O, no ML) → 0ms overhead on the pipeline.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Dict, List, Optional, Tuple

from activity_classifier.app_signatures import (
    PROCESS_SIGNATURE_DB,
    DOMAIN_CATEGORY_MAP,
    _VSCODE_TITLE_RE,
    _EXT_TO_LANG,
    _DISCORD_CHANNEL_RE,
    _DISCORD_VOICE_RE,
    _DISCORD_DM_RE,
    _MEETING_TITLE_RE,
    _EXCEL_TITLE_RE,
    _WORD_TITLE_RE,
    _BROWSER_SUFFIX_RE,
    _SHOPPING_CONTEXT_RE,
    _YOUTUBE_TITLE_RE,
    _ARXIV_TITLE_RE,
    _TERMINAL_SSH_RE,
    _TERMINAL_GIT_RE,
    _TERMINAL_SERVER_RE,
    _TERMINAL_VENV_RE,
    get_file_lang,
    match_domain_label,
    extract_domain,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Duration thresholds for temporal refinement
_QUICK_CHECK_SECS = 90       # ≤ 90s → "Quick Check"
_EXTENDED_SECS    = 1800     # ≥ 30min → "Extended Session"
_BINGE_SECS       = 7200     # ≥ 2hrs → "Binge Watching"


# ===========================================================================
# 1. parse_window_title — structural context extraction
# ===========================================================================
def parse_window_title(title: str, process: str) -> Dict[str, Optional[str]]:
    """
    Extract structured context from a window title.

    Returns a dict with any of:
      app_name, file_name, folder, language, file_category, channel,
      dm_user, meeting_topic, page_title
    """
    ctx: Dict[str, Optional[str]] = {
        "app_name":      None,
        "file_name":     None,
        "folder":        None,
        "language":      None,
        "file_category": None,
        "channel":       None,
        "dm_user":       None,
        "meeting_topic": None,
        "page_title":    None,
    }
    if not title:
        return ctx

    proc = process.lower() if process else ""

    # ── VS Code ──────────────────────────────────────────────────────────────
    if proc in ("code.exe", "code", "cursor.exe"):
        ctx["app_name"] = "VS Code" if "cursor" not in proc else "Cursor"
        m = _VSCODE_TITLE_RE.match(title)
        if m:
            file_raw = (m.group("file") or "").strip().lstrip("● ◯ ")
            ctx["file_name"] = file_raw or None
            ctx["folder"]    = (m.group("folder") or "").strip() or None
            if file_raw:
                ctx["language"]      = _get_file_lang(file_raw)
                ctx["file_category"] = ctx["language"]
        return ctx

    # ── Discord ──────────────────────────────────────────────────────────────
    if proc in ("discord.exe", "discord"):
        ctx["app_name"] = "Discord"
        if _DISCORD_VOICE_RE.search(title):
            ctx["channel"] = "Voice"
        else:
            m_ch = _DISCORD_CHANNEL_RE.search(title)
            if m_ch:
                ctx["channel"] = m_ch.group("channel").strip()
            else:
                m_dm = _DISCORD_DM_RE.search(title)
                if m_dm:
                    ctx["dm_user"] = m_dm.group("user").strip()
        return ctx

    # ── Zoom / Teams ─────────────────────────────────────────────────────────
    if proc in ("zoom.exe", "teams.exe", "ms-teams.exe"):
        ctx["app_name"] = "Zoom" if "zoom" in proc else "Teams"
        m_mt = _MEETING_TITLE_RE.search(title)
        if m_mt:
            ctx["meeting_topic"] = m_mt.group("topic").strip()[:60]
        return ctx

    # ── Excel ────────────────────────────────────────────────────────────────
    if proc == "excel.exe":
        ctx["app_name"] = "Excel"
        m = _EXCEL_TITLE_RE.match(title)
        if m:
            fname = m.group("file").strip()
            ctx["file_name"]     = fname
            ctx["file_category"] = _get_file_lang(fname) or "Spreadsheet"
        return ctx

    # ── Word ─────────────────────────────────────────────────────────────────
    if proc == "winword.exe":
        ctx["app_name"] = "Word"
        m = _WORD_TITLE_RE.match(title)
        if m:
            fname = m.group("file").strip()
            ctx["file_name"]     = fname
            ctx["file_category"] = _get_file_lang(fname) or "Document"
        return ctx

    # ── Browsers: strip browser name → page_title ──────────────────────────
    if _is_browser_process(proc):
        page = _BROWSER_SUFFIX_RE.sub("", title).strip()
        ctx["app_name"]   = _browser_display_name(proc)
        ctx["page_title"] = page or title
        return ctx

    # ── Terminals ────────────────────────────────────────────────────────────
    if _is_terminal_process(proc):
        ctx["app_name"] = _terminal_display_name(proc)
        return ctx

    # ── Generic fallback: try "File - App" pattern ────────────────────────
    sig = PROCESS_SIGNATURE_DB.get(proc)
    if sig:
        ctx["app_name"] = sig[0]

    return ctx


# ===========================================================================
# 2. detect_app_subactivity — main entry point for desktop apps
# ===========================================================================
def detect_app_subactivity(
    process: str,
    title: str,
    ocr_text: str = "",
) -> Optional[str]:
    """
    Return a specific granular label for a known desktop application,
    or None if the process is unknown (caller should fall back to generic rules).

    Output format: "AppName - Specific Context"
    e.g. "VS Code - Python (Debugging)"
         "Discord - Voice Chat"
         "Excel - Financial Spreadsheet"
         "Zoom - Business Meeting"
         "Work - Terminal (SSH)"
    """
    proc = (process or "").lower().strip()
    title_lower = title.lower() if title else ""

    # ── VS Code ──────────────────────────────────────────────────────────────
    if proc in ("code.exe", "code", "cursor.exe"):
        return _classify_vscode(proc, title, title_lower, ocr_text)

    # ── JetBrains IDEs ───────────────────────────────────────────────────────
    if proc in ("pycharm64.exe", "idea64.exe", "webstorm64.exe",
                "rider64.exe", "clion64.exe", "phpstorm64.exe",
                "goland64.exe", "datagrip64.exe"):
        return _classify_jetbrains(proc, title, title_lower, ocr_text)

    # ── Discord ──────────────────────────────────────────────────────────────
    if proc in ("discord.exe", "discord"):
        return _classify_discord(title, title_lower)

    # ── Zoom ─────────────────────────────────────────────────────────────────
    if proc == "zoom.exe":
        return _classify_zoom(title, title_lower)

    # ── Microsoft Teams ──────────────────────────────────────────────────────
    if proc in ("teams.exe", "ms-teams.exe"):
        return _classify_teams(title, title_lower)

    # ── Excel ────────────────────────────────────────────────────────────────
    if proc == "excel.exe":
        return _classify_excel(title, title_lower, ocr_text)

    # ── Word ─────────────────────────────────────────────────────────────────
    if proc == "winword.exe":
        return _classify_word(title, title_lower)

    # ── Spotify (foreground) ─────────────────────────────────────────────────
    if proc == "spotify.exe":
        return _classify_spotify(title, title_lower)

    # ── Terminals / Shells ───────────────────────────────────────────────────
    if _is_terminal_process(proc):
        return _classify_terminal(proc, title, title_lower, ocr_text)

    # ── OBS Studio ───────────────────────────────────────────────────────────
    if proc in ("obs64.exe", "obs32.exe", "obs.exe"):
        if "streaming" in title_lower or "live" in title_lower:
            return "Creative - OBS Studio (Live Streaming)"
        return "Creative - OBS Studio (Screen Recording)"

    # ── Blender ──────────────────────────────────────────────────────────────
    if proc in ("blender.exe", "blender"):
        if "render" in title_lower:
            return "Creative - Blender (3D Rendering)"
        return "Creative - Blender (3D Modeling)"

    # ── DaVinci Resolve ───────────────────────────────────────────────────────
    if proc == "davinciresolve.exe":
        if "deliver" in title_lower or "render" in title_lower:
            return "Creative - DaVinci Resolve (Rendering)"
        if "color" in title_lower:
            return "Creative - DaVinci Resolve (Color Grading)"
        return "Creative - DaVinci Resolve (Video Editing)"

    # ── GitHub Desktop ───────────────────────────────────────────────────────
    if proc == "githubdesktop.exe":
        if "pull request" in title_lower or "pr" in title_lower:
            return "Work - GitHub Desktop"
        if "history" in title_lower or "diff" in title_lower:
            return "Work - GitHub Desktop"
        return "Work - GitHub Desktop"

    # ── File Explorer ────────────────────────────────────────────────────────
    if proc == "explorer.exe":
        return _classify_explorer(title, title_lower)

    # ── Task Manager ─────────────────────────────────────────────────────────
    if proc == "taskmgr.exe":
        return "System - Task Manager (Performance Monitoring)"

    # ── Microsoft Store ───────────────────────────────────────────────────────
    if proc in ("winstore.app.exe", "ms-windows-store.exe", "microsoftstore.exe",
                "windowsstore.exe"):
        if "update" in title_lower or "updates" in title_lower:
            return "System - Microsoft Store"
        if "library" in title_lower or "installed" in title_lower:
            return "Shopping - Microsoft Store"
        if "download" in title_lower or "installing" in title_lower:
            return "Shopping - Microsoft Store"
        return "Shopping - Microsoft Store"

    # ── Windows Settings ──────────────────────────────────────────────────────
    if proc in ("systemsettings.exe", "windowssettings.exe", "ms-settings.exe",
                "windows.immersivecontrolpanel.exe"):
        for kw, ctx in [
            (["display", "resolution", "brightness"], "Display"),
            (["network", "wifi", "bluetooth", "internet"], "Network"),
            (["privacy", "permissions", "camera access"], "Privacy"),
            (["update", "windows update"], "Updates"),
            (["account", "sign in"], "Accounts"),
            (["sound", "audio", "volume"], "Sound"),
            (["apps", "default", "uninstall"], "Apps & Features"),
        ]:
            if any(k in title_lower for k in kw):
                return f"System - Windows Settings"
        return "System - Windows Settings"

    # ── Calculator ────────────────────────────────────────────────────────────
    if proc in ("calculatorapp.exe", "calculator.exe", "windowscalculator.exe"):
        for kw, ctx in [
            (["scientific"], "Scientific"), (["programmer"], "Programmer"),
            (["graphing"], "Graphing"),
            (["currency", "unit", "temperature", "converter"], "Converter"),
        ]:
            if any(k in title_lower for k in kw):
                return f"Utility - Calculator"
        return "Utility - Calculator"

    # ── Notepad / WordPad ─────────────────────────────────────────────────────
    if proc in ("notepad.exe", "notepad2.exe", "wordpad.exe"):
        app = "WordPad" if "wordpad" in proc else "Notepad"
        if title and title_lower not in ("untitled - notepad", "notepad", ""):
            fname = title.split(" - ")[0].strip()
            return f"Work - Notepad"
        return f"Work - Notepad"

    # ── Paint / Paint 3D ─────────────────────────────────────────────────────
    if proc in ("mspaint.exe", "paint.exe"):
        app = "Paint 3D" if proc == "paint.exe" else "MS Paint"
        return f"Creative - {app} (Drawing)"

    # ── Windows Photos ────────────────────────────────────────────────────────
    if proc in ("photos.exe", "microsoft.photos.exe"):
        if any(kw in title_lower for kw in ["video", "movie"]):
            return "Entertainment - Photos"
        if any(kw in title_lower for kw in ["edit", "crop", "filter", "enhance"]):
            return "Creative - Photos"
        return "Creative - Photos"

    # ── Windows Camera ────────────────────────────────────────────────────────
    if proc == "windowscamera.exe":
        return "Creative - Camera (Photo/Video Capture)"

    # ── Movies & TV / Streaming Apps ─────────────────────────────────────────
    if proc in ("video.ui.exe", "zunevideo.exe", "microsoftvideo.exe",
                "netflix.exe", "disneyplus.exe", "primevideo.exe"):
        app_names = {
            "netflix.exe": "Netflix", "disneyplus.exe": "Disney+",
            "primevideo.exe": "Prime Video"
        }
        app = app_names.get(proc, "Movies & TV")
        return f"Entertainment - {app} (Streaming)"

    # ── Kodi / Plex / Jellyfin ───────────────────────────────────────────────
    if proc in ("kodi.exe", "plex.exe", "plexmediaplayer.exe", "jellyfin.exe", "emby.exe"):
        app_names = {"kodi.exe": "Kodi", "plex.exe": "Plex",
                     "plexmediaplayer.exe": "Plex", "jellyfin.exe": "Jellyfin", "emby.exe": "Emby"}
        app = app_names.get(proc, "Media Center")
        if "music" in title_lower or "audio" in title_lower:
            return f"Entertainment - {app} (Music)"
        return f"Entertainment - {app} (Video)"

    # ── Xbox App / Game Bar ───────────────────────────────────────────────────
    if proc in ("xbox.exe", "xboxapp.exe"):
        if "game pass" in title_lower:
            return "Entertainment - Xbox (Game Pass)"
        if "store" in title_lower or "shop" in title_lower:
            return "Shopping - Xbox Store"
        return "Entertainment - Xbox (Gaming)"
    if proc in ("gamebar.exe", "microsoftgameapp.exe", "xboxgamemonitorapp.exe"):
        return "Entertainment - Xbox Game Bar (Recording/Overlay)"

    # ── Music Players (foreground) ────────────────────────────────────────────
    if proc in ("aimp.exe", "foobar2000.exe", "musicbee.exe", "tidal.exe",
                "deezer.exe", "itunes.exe", "groove.exe", "zunemusic.exe"):
        app_names = {"aimp.exe": "AIMP", "foobar2000.exe": "foobar2000",
                     "musicbee.exe": "MusicBee", "tidal.exe": "Tidal",
                     "deezer.exe": "Deezer", "itunes.exe": "iTunes",
                     "groove.exe": "Groove Music", "zunemusic.exe": "Groove Music"}
        app = app_names.get(proc, "Music Player")
        if title and title_lower not in (proc.replace(".exe", ""), ""):
            return f"Entertainment - {app} (Playing: {title[:40]})"
        return f"Entertainment - {app} (Music)"

    # ── Screen Recorders / Streaming ─────────────────────────────────────────
    if proc in ("bandicam.exe", "fraps.exe", "xsplit.exe", "shadowplay.exe"):
        app_names = {"bandicam.exe": "Bandicam", "fraps.exe": "FRAPS",
                     "xsplit.exe": "XSplit", "shadowplay.exe": "ShadowPlay"}
        return f"Creative - {app_names.get(proc, 'Screen Recorder')} (Recording)"
    if proc == "loom.exe":
        return "Communication - Loom (Screen Recording)"

    # ── Screenshot Tools ──────────────────────────────────────────────────────
    if proc in ("snippingtool.exe", "screensketch.exe", "snipandsketchwm.exe",
                "sharex.exe", "greenshot.exe", "lightshot.exe"):
        app_names = {
            "snippingtool.exe": "Snipping Tool", "screensketch.exe": "Snip & Sketch",
            "snipandsketchwm.exe": "Snip & Sketch", "sharex.exe": "ShareX",
            "greenshot.exe": "Greenshot", "lightshot.exe": "Lightshot"
        }
        return f"System - {app_names.get(proc, 'Screenshot Tool')} (Screenshot)"

    # ── VPN Tools ─────────────────────────────────────────────────────────────
    if proc in ("nordvpn.exe", "expressvpn.exe", "protonvpn.exe",
                "surfshark.exe", "mullvad.exe", "openvpn.exe", "wireguard.exe"):
        vpn_names = {
            "nordvpn.exe": "NordVPN", "expressvpn.exe": "ExpressVPN",
            "protonvpn.exe": "ProtonVPN", "surfshark.exe": "Surfshark",
            "mullvad.exe": "Mullvad", "openvpn.exe": "OpenVPN", "wireguard.exe": "WireGuard"
        }
        return f"Utility - {vpn_names.get(proc, 'VPN')} (VPN Active)"

    # ── Password Managers ─────────────────────────────────────────────────────
    if proc in ("bitwarden.exe", "keepass.exe", "1password.exe", "lastpass.exe"):
        pm_names = {"bitwarden.exe": "Bitwarden", "keepass.exe": "KeePass",
                    "1password.exe": "1Password", "lastpass.exe": "LastPass"}
        return f"Utility - {pm_names.get(proc, 'Password Manager')} (Password Management)"

    # ── Security / Network Diagnostics ───────────────────────────────────────
    if proc == "malwarebytes.exe":
        return "System - Malwarebytes (Security Scan)"
    if proc == "wireshark.exe":
        return "Development - Wireshark (Network Analysis)"
    if proc in ("putty.exe", "mobaxterm.exe"):
        return f"Development - {proc.replace('.exe','').capitalize()} (SSH Session)"

    # ── Virtual Machines ──────────────────────────────────────────────────────
    if proc in ("vmware.exe", "vmwareworkstation.exe", "virtualboxvm.exe",
                "virtualbox.exe", "hyperv.exe"):
        vm_names = {
            "vmware.exe": "VMware", "vmwareworkstation.exe": "VMware Workstation",
            "virtualboxvm.exe": "VirtualBox", "virtualbox.exe": "VirtualBox",
            "hyperv.exe": "Hyper-V"
        }
        return f"System - {vm_names.get(proc, 'VM')} (Virtual Machine)"

    # ── Remote Desktop ────────────────────────────────────────────────────────
    if proc == "mstsc.exe":
        return "System - Remote Desktop (RDP Session)"
    if proc == "anydesk.exe":
        return "System - AnyDesk (Remote Session)"
    if proc == "teamviewer.exe":
        return "System - TeamViewer (Remote Session)"
    if proc in ("vnc.exe", "vncviewer.exe"):
        return "System - VNC (Remote Session)"

    # ── E-Readers ─────────────────────────────────────────────────────────────
    if proc in ("kindle.exe", "calibre.exe", "bookviser.exe", "kobo.exe"):
        app_names = {"kindle.exe": "Kindle", "calibre.exe": "Calibre",
                     "bookviser.exe": "Bookviser", "kobo.exe": "Kobo"}
        app = app_names.get(proc, "eBook Reader")
        if title and title_lower not in (app.lower(), ""):
            book_title = title.split(" - ")[0].strip()[:50]
            return f"Learning - {app} (Reading: {book_title})"
        return f"Learning - {app} (Book Reading)"

    # ── Game Engines ──────────────────────────────────────────────────────────
    if proc in ("unity.exe", "unreal.exe", "unrealengine.exe", "godot.exe", "gamemaker.exe"):
        engine_names = {
            "unity.exe": "Unity", "unreal.exe": "Unreal Engine",
            "unrealengine.exe": "Unreal Engine", "godot.exe": "Godot", "gamemaker.exe": "GameMaker"
        }
        engine = engine_names.get(proc, "Game Engine")
        if any(kw in title_lower for kw in ["render", "build", "compile"]):
            return f"Development - {engine} (Building/Rendering)"
        if any(kw in title_lower for kw in ["editor", "scene"]):
            return f"Development - {engine} (Scene Editor)"
        return f"Development - {engine} (Game Development)"

    # ── 3D / CAD / Photo ─────────────────────────────────────────────────────
    if proc in ("autocad.exe", "acad.exe"):
        return "Creative - AutoCAD (CAD Design)"
    if proc == "fusion360.exe":
        return "Creative - Fusion 360 (3D CAD/Design)"
    if proc in ("maya.exe", "cinema4d.exe", "houdini.exe", "3dsmax.exe"):
        app_names = {"maya.exe": "Maya", "cinema4d.exe": "Cinema 4D",
                     "houdini.exe": "Houdini", "3dsmax.exe": "3ds Max"}
        return f"Creative - {app_names.get(proc, '3D App')} (3D Modeling)"
    if proc == "zbrush.exe":
        return "Creative - ZBrush (3D Sculpting)"
    if proc in ("lightroom.exe", "lightroomclassic.exe"):
        return "Creative - Lightroom (Photo Editing)"
    if proc in ("irfanview.exe", "xnviewmp.exe", "faststone.exe", "jpegview.exe"):
        return "Creative - Image Viewer (Photo Browsing)"
    if proc in ("rawtherapee.exe", "darktable.exe"):
        return "Creative - RAW Photo Editor"

    # ── Utilities ─────────────────────────────────────────────────────────────
    if proc == "powertoys.exe":
        return "Utility - PowerToys (Windows Utilities)"
    if proc == "autohotkey.exe":
        return "Utility - AutoHotkey (Automation/Macro)"
    if proc in ("everything.exe", "flow.launcher.exe", "keypirinha.exe"):
        return "Utility - File/App Search"
    if proc in ("rufus.exe", "etcher.exe"):
        return "System - USB Boot Creator"
    if proc in ("cpu-z.exe", "gpu-z.exe", "hwinfo64.exe", "hwmonitor.exe",
                "afterburner.exe", "msi afterburner.exe", "speccy.exe", "crystaldiskinfo.exe"):
        return "System - Hardware Monitor"
    if proc in ("ccleaner.exe", "cleanmgr.exe", "defraggler.exe"):
        return "System - System Cleanup"
    if proc in ("ditto.exe", "agent.exe"):
        return "Utility - Clipboard Manager"
    if proc == "windowsalarms.exe":
        return "Utility - Alarms & Clock"
    if proc == "windowsmaps.exe":
        return "Information - Windows Maps (Navigation)"
    if proc in ("searchhost.exe", "searchui.exe"):
        return "Information - Windows Search"
    if proc == "cortana.exe":
        return "Information - Cortana (Voice Assistant)"
    if proc in ("lockapp.exe", "logonui.exe", "winlogon.exe"):
        return "Idle - Screen Locked"
    if proc in ("shellexperiencehost.exe", "startmenuexperiencehost.exe"):
        return "System - Start Menu"

    # ── Generic lookup from PROCESS_SIGNATURE_DB ──────────────────────────────
    if _is_browser_process(proc):
        # We skip generic lookup for browsers so that classifier.py 
        # can run the more specialized classify_browser_tab() logic.
        return None

    sig = PROCESS_SIGNATURE_DB.get(proc)
    if sig:
        return sig[1]  # base_label

    # ── Universal Content Heuristic (uses OCR if available) ──────────────────
    universal = match_universal_keywords(ocr_text or title)
    if universal:
        return universal

    return None  # unknown process — caller handles fallback


# ===========================================================================
# 3. classify_browser_tab — domain-aware browser classification
# ===========================================================================
# --- Dynamic Browser Rules (Revised) ---

_SHOPPING_DOMAINS = ["amazon", "flipkart", "ebay", "aliexpress", "olx", "daraz", "alibaba", "walmart", "target"]
_SHOPPING_KEYWORDS = ["buy", "shop", "cart", "checkout", "product", "price"]

_RESEARCH_DOMAINS = ["arxiv", "ieee", "pubmed", "sciencedirect", "springer", "jstor", "researchgate", "scholar", "acm.org"]
_RESEARCH_KEYWORDS = ["paper", "article", "journal", "conference", "proceedings"]

_EMAIL_DOMAINS = ["gmail", "outlook", "mail.yahoo", "protonmail"]

_VIDEO_DOMAINS = ["youtube", "netflix", "hulu", "hotstar", "vimeo", "dailymotion", "twitch"]
_VIDEO_KEYWORDS = ["watch", "video", "stream", "episode", "movie"]

_MUSIC_DOMAINS = ["spotify", "soundcloud", "apple music"]

_LEARNING_DOMAINS = ["coursera", "udemy", "edx", "khanacademy", "codecademy", "udacity"]

_DEV_DOMAINS = ["github", "gitlab", "stackoverflow", "stack overflow", "medium/dev"]

_SOCIAL_DOMAINS = ["reddit", "twitter", "instagram", "facebook", "linkedin", "discord", "x.com"]

_NEWS_DOMAINS = ["cnn", "bbc", "nytimes", "wsj", "reuters", "aljazeera"]

_WORK_DOMAINS = ["docs.google", "google docs", "office", "notion", "miro", "trello", "asana", "jira"]

_FINANCIAL_DOMAINS = ["banking", "icici", "hdfc", "chase", "wellsfargo", "paypal", "binance"]

_INFO_DOMAINS = ["wikipedia", "quora", "medium"]


def classify_browser_tab(
    domain: str,
    page_title: str,
    browser_name: str = "Browser",
) -> str:
    """
    Dynamic Browser Classification Engine.
    Evaluates Domain + Title Keywords against a prioritized rule set.
    """
    t = (page_title or "").lower()
    
    # 1. Title Normalization (strip common suffixes to avoid interference)
    for suffix in ["google chrome", "microsoft edge", "firefox", "brave", "opera", "safari"]:
        t = t.replace(f" - {suffix}", "").replace(f" | {suffix}", "").strip()

    # Special Cases - Google / Microsoft
    if "docs.google" in t or "google docs" in t or "word online" in t:
        return "Work - Documentation"
    if "sheets.google" in t or "google sheets" in t or "excel online" in t:
        return "Work - Data Analysis"
    if "slides.google" in t or "google slides" in t or "powerpoint online" in t:
        return "Work - Presentation"
    if "meet.google" in t or "google meet" in t or "zoom" in t:
        return "Communication - Video Call"
    if "calendar" in t and ("google" in t or "outlook" in t):
        return "Work - Planning"
    if "teams" in t:
        return "Communication - Meeting"
        
    # PDF
    if t.endswith(".pdf") or "pdf" in t:
        return "Research - Reading Paper"
        
    # New Tab
    if "new tab" in t or not t:
        return "Browsing - Web"
        
    # Check Shopping
    if any(d in t for d in _SHOPPING_DOMAINS) or any(k in t for k in _SHOPPING_KEYWORDS):
        return "Shopping - Ecommerce"
        
    # Check Research
    if any(d in t for d in _RESEARCH_DOMAINS) or any(k in t for k in _RESEARCH_KEYWORDS):
        return "Research - Academic"
        
    # Check Email
    if any(d in t for d in _EMAIL_DOMAINS):
        return "Communication - Email"
        
    # Check Entertainment - Video / Music
    if "youtube" in t:
        if "music" in t or "song" in t or "hale dil" in t:
            return "Entertainment - Music"
        return "Entertainment - Video"
        
    if any(d in t for d in _VIDEO_DOMAINS) or any(k in t for k in _VIDEO_KEYWORDS):
        return "Entertainment - Video"
        
    if any(d in t for d in _MUSIC_DOMAINS):
        return "Entertainment - Music"
        
    # Check Learning
    if any(d in t for d in _LEARNING_DOMAINS):
        return "Learning - Tutorial"
        
    # Check Development
    if "github" in t:
        return "Development - GitHub"
    if any(d in t for d in _DEV_DOMAINS):
        return "Development - Coding Reference"
        
    # Check Social Media
    if any(d in t for d in _SOCIAL_DOMAINS):
        if "chat" in t or "discord" in t:
            return "Social Media - Chat"
        return "Social Media - Browsing"
        
    # Check News
    if any(d in t for d in _NEWS_DOMAINS):
        return "News - Reading"
        
    # Check Work
    if any(d in t for d in _WORK_DOMAINS) or "figma" in t or "canva" in t:
        if "figma" in t or "canva" in t:
             return "Creative - Design"
        if "trello" in t or "jira" in t:
             return "Work - Planning"
        return "Work - Documentation"
        
    # Check Financial
    if any(d in t for d in _FINANCIAL_DOMAINS):
        return "Financial - Banking"
        
    # Check Info
    if any(d in t for d in _INFO_DOMAINS):
        return "Information - Reading"
        
    # Default fallthrough
    return "Browsing - Web"

def detect_idle_nuance(
    signals,               # BehavioralSignals
    last_primary_label: str,
) -> str:
    """
    Replace plain Idle with Route C and Route D handling.
    """
    bg = getattr(signals, "background_activities", [])
    
    # Route C - Background Processes Priority Check
    bg_lower = " ".join(bg).lower()
    if "download" in bg_lower or "torrent" in bg_lower:
        return "Background - Downloading"
    if "update" in bg_lower:
        return "Background - System Update"
    if "scan" in bg_lower or "antivirus" in bg_lower or "defender" in bg_lower:
        return "Background - Security Scan"
    if "copy" in bg_lower or "transfer" in bg_lower:
        return "Background - File Transfer"
    if "render" in bg_lower:
        return "Background - Rendering"
    if "build" in bg_lower or "compile" in bg_lower:
        return "Background - Building"

    # Route D - Passive/Idle state based on last activity
    lp = (last_primary_label or "").lower()
    if "watching" in lp or "netflix" in lp or "youtube" in lp:
        return "Passive - Watching"
    if "music" in lp or "spotify" in lp or "listen" in lp:
        return "Passive - Listening"
    
    if getattr(signals, 'screen_locked', False):
        return "Idle - Screen Locked"
    
    return "Idle - Away From Keyboard"


# ===========================================================================
# 5. fuse_multi_app_context — combined activity labels
# ===========================================================================
def fuse_multi_app_context(
    primary_label: str,
    secondary_labels: List[str],
) -> Optional[str]:
    """
    Hybrid Activity Output.
    Takes primary context and appends significant secondary logic (Route D fusion).
    Format: "Primary Output + Secondary Action"
    """
    if not secondary_labels:
        return None

    s_lower = " ".join(secondary_labels).lower()
    
    secondary_suffix = None
    if "discord" in s_lower:
        if "voice chat" in s_lower or "rtc connected" in s_lower:
            secondary_suffix = "Discord Voice"
        else:
            secondary_suffix = "Discord Chat"
    elif "zoom" in s_lower or "teams" in s_lower or "meet" in s_lower:
        secondary_suffix = "Meeting Call"
    elif "spotify" in s_lower or "music" in s_lower:
        secondary_suffix = "Background Music"
    elif "download" in s_lower:
        secondary_suffix = "Downloading"
    elif "youtube" in s_lower or "netflix" in s_lower:
        secondary_suffix = "Video Playing"

    if secondary_suffix:
        return f"{primary_label} + {secondary_suffix}"
        
    return None


# ===========================================================================
# 6. apply_active_passive_state — duration and input-aware refinement
# ===========================================================================
def apply_active_passive_state(label: str, signals) -> str:
    """
    Refine a label based on sensory engagement (Media, Controller, Load).
    Prevents "Idle" during passive consumption or active building.
    """
    if not label:
        return label
        
    idle_time = getattr(signals, 'idle_seconds', 0.0)
    label_lower = label.lower()
    
    # Engagement Overrides (Sensory Activity)
    media_active = getattr(signals, 'media_playing', False)
    ctrl_active = getattr(signals, 'controller_active', False)
    
    # 1. Media: Active vs Passive
    is_media = any(m in label_lower for m in ["spotify", "music", "watching", "netflix", "youtube", "media", "video", "entertainment"])
    if is_media:
        if media_active:
            # Active viewing/listening override
            if idle_time > 300:
                return label.replace("Watching -", "Passive -").replace("Music -", "Passive -")
            return label.replace("Watching -", "Active -").replace("Music -", "Active -")
        elif idle_time > 60:
            return f"Paused - {label.split(' - ')[-1]}"

    # 2. Gaming: Active vs Away
    if "gaming" in label_lower:
         if ctrl_active:
             return label # Maintain active label if controller is moving
         if idle_time > 300:
             return "Gaming - Away / Cutscene"

    # 3. Creative Phase: Thinking vs Doing
    if "creative -" in label_lower:
        if idle_time > 120 and idle_time < 600:
             return f"{label} (Thinking)"
             
    # 4. Development Phase: Waiting on builds
    if "development -" in label_lower or "building" in label_lower:
        if getattr(signals, 'cpu_percent', 0.0) > 40:
             return f"{label} (Building)"
        if idle_time > 120 and "coding" in label_lower:
             return label.replace("Coding", "Thinking / Reading")

    return label


# ===========================================================================
# 7. get_process_base_label — fast process-only lookup
# ===========================================================================
def get_process_base_label(process: str) -> Optional[str]:
    """Return base label for a process name, checking PROCESS_SIGNATURE_DB."""
    proc = (process or "").lower().strip()
    sig = PROCESS_SIGNATURE_DB.get(proc)
    if sig:
        return sig[1]
    return None


# ===========================================================================
# Private helpers
# ===========================================================================

def _is_dev_activity(label_lower: str) -> bool:
    return any(kw in label_lower for kw in ("vs code", "code", "development", "coding", "pycharm", "intellij",
                                              "jupyter", "git", "postman", "terminal", "bash", "powershell"))


def _is_work_activity(label_lower: str) -> bool:
    return any(kw in label_lower for kw in ("work", "excel", "word", "powerpoint", "outlook", "document",
                                              "spreadsheet", "presentation", "project", "notion", "obsidian"))


def _is_meeting_activity(label_lower: str) -> bool:
    return any(kw in label_lower for kw in ("zoom", "teams", "meet", "meeting", "call", "conference", "webinar"))


def _is_browser_process(proc: str) -> bool:
    return any(b in proc for b in ("chrome", "msedge", "firefox", "brave", "opera", "safari", "vivaldi", "arc"))


def _is_terminal_process(proc: str) -> bool:
    return any(t in proc for t in ("cmd.exe", "powershell.exe", "pwsh.exe", "wt.exe",
                                    "windowsterminal.exe", "git-bash.exe", "bash.exe"))


def _browser_display_name(proc: str) -> str:
    mapping = {
        "chrome.exe": "Chrome",
        "msedge.exe": "Edge",
        "firefox.exe": "Firefox",
        "brave.exe": "Brave",
        "opera.exe": "Opera",
        "vivaldi.exe": "Vivaldi",
        "arc.exe": "Arc",
    }
    return mapping.get(proc, "Browser")


def _terminal_display_name(proc: str) -> str:
    if "powershell" in proc or "pwsh" in proc:
        return "PowerShell"
    if "git-bash" in proc:
        return "Git Bash"
    return "Terminal"


def _classify_vscode(proc: str, title: str, title_lower: str, ocr_text: str) -> str:
    """Classify VS Code with Deep Context."""
    # Build/Debug/Git commands from OCR or Title
    full_text = f"{title_lower} {ocr_text.lower()}"
    if "debug" in full_text or "breakpoint" in full_text:
        return "Development - Debugging"
    if any(k in full_text for k in ["git", "pull request", "merge"]):
        return "Development - Code Review"
    if any(k in full_text for k in ["build", "compile", "make"]):
        return "Development - Building"
    if any(k in full_text for k in ["npm ", "pip ", "conda "]):
        return "Development - Package Management"
    
    # Extension-based
    ext = _extract_vscode_lang(title)
    if ext:
        if ext.lower() in ["markdown", "text"]:
            return "Work - Writing Documentation"
        if ext.lower() in ["jupyter", "jupyter notebook"]:
            return "Data Science - Jupyter Notebook"
        return f"Development - Coding in {ext}"
    
    return "Development - VS Code"


def _extract_vscode_lang(title: str) -> Optional[str]:
    """Extract programming language name from VS Code window title."""
    m = _VSCODE_TITLE_RE.match(title)
    if m:
        file_raw = (m.group("file") or "").strip().lstrip("● ◯ ")
        if file_raw:
            return get_file_lang(file_raw)
    return None


def _extract_vscode_file(title: str) -> Optional[str]:
    """Extract filename from VS Code window title."""
    m = _VSCODE_TITLE_RE.match(title)
    if m:
        f = (m.group("file") or "").strip().lstrip("● ◯ ")
        return f or None
    return None


def _classify_jetbrains(proc: str, title: str, title_lower: str, ocr_text: str) -> str:
    """Classify JetBrains IDEs."""
    ide_map = {
        "pycharm64.exe": "PyCharm",
        "idea64.exe":    "IntelliJ",
        "webstorm64.exe":"IntelliJ",
        "rider64.exe":   "IntelliJ",
        "clion64.exe":   "IntelliJ",
        "phpstorm64.exe":"IntelliJ",
        "goland64.exe":  "IntelliJ",
        "datagrip64.exe":"IntelliJ",
    }
    return f"Work - {ide_map.get(proc, 'IntelliJ')}"


def _classify_discord(title: str, title_lower: str) -> str:
    """Classify Discord with Deep Context."""
    # Voice/Screen/Typing heuristics from title
    if "voice connected" in title_lower or "rtc connected" in title_lower:
        return "Communication - Discord Voice Chat"
    if "screen share" in title_lower or "live" in title_lower:
        return "Collaboration - Screen Sharing"
    if "typing" in title_lower or "#" in title_lower or "@" in title_lower:
        return "Communication - Discord Text Chat"
    return "Communication - Discord"


def _classify_zoom(title: str, title_lower: str) -> str:
    """Classify Zoom meeting context."""
    if "presenting" in title_lower or "sharing" in title_lower:
        return "Meeting - Presenting"
    if "chat" in title_lower:
        return "Meeting - Chatting"
    if "webinar" in title_lower:
        return "Meeting - Active Participant"
    return "Meeting - In Call"


def _classify_teams(title: str, title_lower: str) -> str:
    """Classify Microsoft Teams context."""
    if "presenting" in title_lower or "sharing" in title_lower:
        return "Meeting - Presenting"
    if "chat" in title_lower:
        return "Meeting - Chatting"
    return "Meeting - In Call"


def _classify_excel(title: str, title_lower: str, ocr_text: str) -> str:
    """Classify Excel."""
    return "Work - Excel"


def _classify_word(title: str, title_lower: str) -> str:
    """Classify Word."""
    if "document" in title_lower or "docx" in title_lower:
        return "Work - Microsoft Word"
    return "Work - Microsoft Word"


def _classify_spotify(title: str, title_lower: str) -> str:
    """Classify Spotify."""
    if "paused" in title_lower:
        return "Media - Paused"
    if "podcast" in title_lower:
        return "Information - Podcast"
    if title_lower and title_lower not in ["spotify", "spotify premium", "spotify free"]:
        return "Media - Active Listening"
    return "Media - Spotify"


def _classify_terminal(proc: str, title: str, title_lower: str, ocr_text: str) -> str:
    """Classify terminal with Deep Context."""
    full_text = f"{title_lower} {ocr_text.lower()}"
    if "git " in full_text or "commit" in full_text:
        return "Development - Git Operations"
    if "docker" in full_text or "kubectl" in full_text:
        return "Development - Container Management"
    if any(k in full_text for k in ["npm ", "pip ", "conda "]):
        return "Development - Package Management"
    if "ssh " in full_text:
        return "Development - Remote Server"
    if "cd " in full_text or "dir " in full_text or "ls " in full_text:
        return "System - File Navigation"
    return "System - Terminal"


def _classify_explorer(title: str, title_lower: str) -> str:
    """Classify File Explorer context."""
    if any(k in title_lower for k in ["copying", "moving", "transferring", "% complete", "calculating"]):
        return "System - Transferring Files"
    if "search" in title_lower or "results in" in title_lower:
        return "System - Searching Files"
    if "organize" in title_lower or "rename" in title_lower:
        return "System - Organizing Files"
    return "System - Browsing Files"


def _refine_youtube_label(page_title: str, base_label: str) -> str:
    """Add YouTube context: music video, shorts, etc."""
    return base_label


def match_universal_keywords(text: str) -> Optional[str]:
    """
    Catch-all keyword engine that scans any text (Window Title, OCR, Title)
    for high-intent keywords across all taxonomy categories.
    Returns standardized '[Category] - [Specific Activity]'.
    """
    if not text or len(text) < 3:
        return None
    
    t = text.lower()
    
    # ── Financial / Trading ──────────────────────────────────────────────────
    if any(kw in t for kw in ["candlestick", "order book", "leverage", "margin", "pnl", "long/short", "tradingview", "binance", "metatrader", "forex", "stock market", "share price", "portfolio", "bitcoin", "crypto"]):
        return "Financial - Banking" # Using Banking as the subcategory from taxonomy
    
    # ── Shopping / E-Commerce ───────────────────────────────────────────────
    if any(kw in t for kw in ["daraz", "amazon", "ebay", "walmart", "checkout", "shopping cart", "add to cart", "buy now"]):
        return "Shopping - E-commerce"

    # ── Entertainment ──────────────────────────────────────────────────────────
    if any(kw in t for kw in ["netflix"]):
        return "Entertainment - Netflix"
    if any(kw in t for kw in ["youtube", "vimeo", "bilibili"]):
        return "Entertainment - YouTube"
    if any(kw in t for kw in ["twitch", "live stream"]):
        return "Entertainment - Twitch"
    if any(kw in t for kw in ["spotify", "soundcloud", "music"]):
        return "Entertainment - Spotify"
    if any(kw in t for kw in ["gaming", "steam", "epic games", "roblox", "minecraft"]):
        return "Gaming - Steam"
    if any(kw in t for kw in ["reddit"]):
        return "Social - Reddit"
    if any(kw in t for kw in ["tiktok", "instagram", "facebook"]):
        return "Social - Facebook/Instagram"
    
    # ── Work / Productivity ────────────────────────────────────────────────
    if any(kw in t for kw in ["zoom meeting", "zoom"]):
        return "Meeting - Video Call"
    if any(kw in t for kw in ["teams call", "microsoft teams"]):
        return "Meeting - Video Call"
    if any(kw in t for kw in ["slack"]):
        return "Communication - Slack"
    if any(kw in t for kw in ["notion"]):
        return "Work - Notion"
    if any(kw in t for kw in ["jira", "trello", "kanban"]):
        return "Work - Project Management"
    if any(kw in t for kw in ["document", "proposal", "contract", "word"]):
        return "Work - Microsoft Word"
    if any(kw in t for kw in ["spreadsheet", "invoice", "excel"]):
        return "Work - Excel"
    if any(kw in t for kw in ["presentation", "slides", "powerpoint"]):
        return "Work - PowerPoint"
    
    # ── Research / Academic ────────────────────────────────────────────────
    if any(kw in t for kw in ["abstract", "references", "cite", "journal", "arxiv", "scholar", "pubmed"]):
        return "Research - Reading Paper"
    
    # ── Learning ─────────────────────────────────────────────────────────
    if any(kw in t for kw in ["tutorial", "how to", "lecture", "online course", "udemy", "coursera", "khan academy"]):
        return "Learning - Coursera"
    
    # ── Information / News / Search ────────────────────────────────────────
    if any(kw in t for kw in ["breaking news", "opinion", "wikipedia", "quora", "news site"]):
        return "Information - News Site"
    
    # ── Development / Coding ───────────────────────────────────────────────
    if any(kw in t for kw in ["github", "gitlab"]):
        return "Development - GitHub"
    if any(kw in t for kw in ["vs code", "pycharm", "intellij", "jupyter", "coding", "debugger"]):
        return "Development - Code Editor"
    
    # ── Terminal / OCR ──────────────────────────────────────────────────
    if any(kw in t for kw in [r"c:\users", r"ps c:\ ", "ubuntu@", "root@", "-bash", "npm install", "pip install", "docker run"]):
        return "System - Terminal"
    
    # ── Communication / AI ────────────────────────────────────────────────
    if any(kw in t for kw in ["chatgpt", "openai", "claude", "gemini", "bard", "perplexity", "ai chat"]):
        return "Information - AI Assistant"
    if any(kw in t for kw in ["whatsapp", "telegram", "messenger", "signal", "chat", "direct message"]):
        return "Communication - Messaging"

    return None



def match_generic_keywords(title_lower: str) -> Optional[str]:
    """
    Catch-all keyword matcher for titles. Consolidates with match_universal_keywords
    for maximum coverage and consistency.
    """
    # 1. Broad universal check first (handles Trading, Shopping, etc. dynamically)
    universal = match_universal_keywords(title_lower)
    if universal:
        return universal

    # 2. Specific Windows/System overrides
    rules = [
        (["microsoft store", "app store", "windows store", "ms store"], "System - Microsoft Store"),
        (["windows settings", "system settings", "personalization", "display settings"], "System - Settings"),
        (["calculator"], "System - Settings"),
        (["snipping tool", "snip & sketch"], "System - File Explorer"),
        (["alarms", "clock", "timer"], "System - Settings"),
        (["lock screen", "screensaver", "afk", "sign in", "login"], "Idle - Locked Screen"),
        (["file explorer", "this pc", "my computer", "documents", "downloads"], "System - File Explorer"),
        (["task manager", "process explorer"], "System - Task Manager"),
        (["powershell", "cmd", "command prompt", "terminal", "bash", "ubuntu", r"c:\\", r"d:\\", ".exe"], "Work - Terminal"),
        (["python", "node", "npm ", "pip ", "conda "], "Work - Terminal"),
    ]

    t = title_lower.lower()
    for keywords, label in rules:
        if any(kw in t for kw in keywords):
            return label

    return None

def _get_file_lang(file_path: str) -> Optional[str]:
    """Infers human-readable language/type from filename/extension."""
    if not file_path:
        return None
    _, ext = os.path.splitext(file_path.lower())
    return _EXT_TO_LANG.get(ext)