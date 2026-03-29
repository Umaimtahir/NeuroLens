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
            return "OBS Studio - Streaming"
        return "OBS Studio - Recording"

    # ── Blender ──────────────────────────────────────────────────────────────
    if proc in ("blender.exe", "blender"):
        if "render" in title_lower:
            return "Blender - Rendering"
        return "Blender - Modeling"

    # ── DaVinci Resolve ───────────────────────────────────────────────────────
    if proc == "davinciresolve.exe":
        if "export" in title_lower or "deliver" in title_lower:
            return "DaVinci Resolve - Exporting"
        return "DaVinci Resolve - Editing"

    # ── GitHub Desktop ───────────────────────────────────────────────────────
    if proc == "githubdesktop.exe":
        return "GitHub Desktop - Version Control"

    # ── File Explorer ────────────────────────────────────────────────────────
    if proc == "explorer.exe":
        return _classify_explorer(title, title_lower)

    # ── Task Manager ─────────────────────────────────────────────────────────
    if proc == "taskmgr.exe":
        return "Task Manager - Monitoring"

    # ── Microsoft Store ───────────────────────────────────────────────────────
    if proc in ("winstore.app.exe", "ms-windows-store.exe", "microsoftstore.exe",
                "windowsstore.exe"):
        if "download" in title_lower or "installing" in title_lower:
            return "Microsoft Store - Installing"
        return "Microsoft Store - Browsing"

    # ── Windows Settings ──────────────────────────────────────────────────────
    if proc in ("systemsettings.exe", "windowssettings.exe", "ms-settings.exe",
                "windows.immersivecontrolpanel.exe"):
        return "Settings - Configuring"

    # ── Calculator ────────────────────────────────────────────────────────────
    if proc in ("calculatorapp.exe", "calculator.exe", "windowscalculator.exe"):
        return "Calculator - Using"

    # ── Notepad / WordPad ─────────────────────────────────────────────────────
    if proc in ("notepad.exe", "notepad2.exe", "wordpad.exe"):
        return "Notepad - Editing"

    # ── Paint / Paint 3D ─────────────────────────────────────────────────────
    if proc in ("mspaint.exe", "paint.exe"):
        return "Paint - Drawing"

    # ── Windows Photos ────────────────────────────────────────────────────────
    if proc in ("photos.exe", "microsoft.photos.exe"):
        return "Photos - Viewing"

    # ── Windows Camera ────────────────────────────────────────────────────────
    if proc == "windowscamera.exe":
        return "Camera - Photo/Video Capture"

    # ── Movies & TV / Streaming Apps ─────────────────────────────────────────
    if proc in ("video.ui.exe", "zunevideo.exe", "microsoftvideo.exe",
                "netflix.exe", "disneyplus.exe", "primevideo.exe"):
        app_names = {
            "netflix.exe": "Netflix", "disneyplus.exe": "Disney+",
            "primevideo.exe": "Prime Video"
        }
        app = app_names.get(proc, "Movies & TV")
        return f"{app} - Series"

    # ── Kodi / Plex / Jellyfin ───────────────────────────────────────────────
    if proc in ("kodi.exe", "plex.exe", "plexmediaplayer.exe", "jellyfin.exe", "emby.exe"):
        app_names = {"kodi.exe": "Kodi", "plex.exe": "Plex",
                     "plexmediaplayer.exe": "Plex", "jellyfin.exe": "Jellyfin", "emby.exe": "Emby"}
        app = app_names.get(proc, "Media Center")
        if "music" in title_lower or "audio" in title_lower:
            return f"{app} - Listening to Music"
        return f"{app} - Watching Video"

    # ── Xbox App / Game Bar ───────────────────────────────────────────────────
    if proc in ("xbox.exe", "xboxapp.exe"):
        if "game pass" in title_lower:
            return "Xbox - Game Shopping"
        if "store" in title_lower or "shop" in title_lower:
            return "Xbox - Game Shopping"
        return "Xbox - Gaming"
    if proc in ("gamebar.exe", "microsoftgameapp.exe", "xboxgamemonitorapp.exe"):
        return "Xbox Game Bar - Recording"

    # ── Music Players (foreground) ────────────────────────────────────────────
    if proc in ("aimp.exe", "foobar2000.exe", "musicbee.exe", "tidal.exe",
                "deezer.exe", "itunes.exe", "groove.exe", "zunemusic.exe"):
        app_names = {"aimp.exe": "AIMP", "foobar2000.exe": "foobar2000",
                     "musicbee.exe": "MusicBee", "tidal.exe": "Tidal",
                     "deezer.exe": "Deezer", "itunes.exe": "iTunes",
                     "groove.exe": "Groove Music", "zunemusic.exe": "Groove Music"}
        app = app_names.get(proc, "Music Player")
        return f"{app} - Listening to Music"

    # ── Screen Recorders / Streaming ─────────────────────────────────────────
    if proc in ("bandicam.exe", "fraps.exe", "xsplit.exe", "shadowplay.exe"):
        app_names = {"bandicam.exe": "Bandicam", "fraps.exe": "FRAPS",
                     "xsplit.exe": "XSplit", "shadowplay.exe": "ShadowPlay"}
        return f"{app_names.get(proc, 'Screen Recorder')} - Screen Recording"
    if proc == "loom.exe":
        return "Loom - Screen Recording"

    # ── Screenshot Tools ──────────────────────────────────────────────────────
    if proc in ("snippingtool.exe", "screensketch.exe", "snipandsketchwm.exe",
                "sharex.exe", "greenshot.exe", "lightshot.exe"):
        app_names = {
            "snippingtool.exe": "Snipping Tool", "screensketch.exe": "Snip & Sketch",
            "snipandsketchwm.exe": "Snip & Sketch", "sharex.exe": "ShareX",
            "greenshot.exe": "Greenshot", "lightshot.exe": "Lightshot"
        }
        return f"{app_names.get(proc, 'Screenshot Tool')} - Screenshot"

    # ── VPN Tools ─────────────────────────────────────────────────────────────
    if proc in ("nordvpn.exe", "expressvpn.exe", "protonvpn.exe",
                "surfshark.exe", "mullvad.exe", "openvpn.exe", "wireguard.exe"):
        vpn_names = {
            "nordvpn.exe": "NordVPN", "expressvpn.exe": "ExpressVPN",
            "protonvpn.exe": "ProtonVPN", "surfshark.exe": "Surfshark",
            "mullvad.exe": "Mullvad", "openvpn.exe": "OpenVPN", "wireguard.exe": "WireGuard"
        }
        return f"{vpn_names.get(proc, 'VPN')} - VPN Active"

    # ── Password Managers ─────────────────────────────────────────────────────
    if proc in ("bitwarden.exe", "keepass.exe", "1password.exe", "lastpass.exe"):
        pm_names = {"bitwarden.exe": "Bitwarden", "keepass.exe": "KeePass",
                    "1password.exe": "1Password", "lastpass.exe": "LastPass"}
        return f"{pm_names.get(proc, 'Password Manager')} - Password Management"

    # ── Security / Network Diagnostics ───────────────────────────────────────
    if proc == "malwarebytes.exe":
        return "Malwarebytes - Security Scan"
    if proc == "wireshark.exe":
        return "Wireshark - Network Analysis"
    if proc in ("putty.exe", "mobaxterm.exe"):
        return f"{proc.replace('.exe','').capitalize()} - SSH Session"

    # ── Virtual Machines ──────────────────────────────────────────────────────
    if proc in ("vmware.exe", "vmwareworkstation.exe", "virtualboxvm.exe",
                "virtualbox.exe", "hyperv.exe"):
        vm_names = {
            "vmware.exe": "VMware", "vmwareworkstation.exe": "VMware Workstation",
            "virtualboxvm.exe": "VirtualBox", "virtualbox.exe": "VirtualBox",
            "hyperv.exe": "Hyper-V"
        }
        return f"{vm_names.get(proc, 'VM')} - Virtual Machine"

    # ── Remote Desktop ────────────────────────────────────────────────────────
    if proc == "mstsc.exe":
        return "Remote Desktop - RDP Session"
    if proc == "anydesk.exe":
        return "AnyDesk - Remote Session"
    if proc == "teamviewer.exe":
        return "TeamViewer - Remote Session"
    if proc in ("vnc.exe", "vncviewer.exe"):
        return "VNC - Remote Session"

    # ── E-Readers ─────────────────────────────────────────────────────────────
    if proc in ("kindle.exe", "calibre.exe", "bookviser.exe", "kobo.exe"):
        app_names = {"kindle.exe": "Kindle", "calibre.exe": "Calibre",
                     "bookviser.exe": "Bookviser", "kobo.exe": "Kobo"}
        app = app_names.get(proc, "eBook Reader")
        return f"{app} - Reading"

    # ── Game Engines ──────────────────────────────────────────────────────────
    if proc in ("unity.exe", "unreal.exe", "unrealengine.exe", "godot.exe", "gamemaker.exe"):
        engine_names = {
            "unity.exe": "Unity", "unreal.exe": "Unreal Engine",
            "unrealengine.exe": "Unreal Engine", "godot.exe": "Godot", "gamemaker.exe": "GameMaker"
        }
        engine = engine_names.get(proc, "Game Engine")
        if any(kw in title_lower for kw in ["render", "build", "compile"]):
            return f"{engine} - Building"
        if any(kw in title_lower for kw in ["editor", "scene"]):
            return f"{engine} - Scene Editor"
        return f"{engine} - Game Development"

    # ── 3D / CAD / Photo ─────────────────────────────────────────────────────
    if proc in ("autocad.exe", "acad.exe"):
        return "AutoCAD - CAD Design"
    if proc == "fusion360.exe":
        return "Fusion 360 - 3D CAD Design"
    if proc in ("maya.exe", "cinema4d.exe", "houdini.exe", "3dsmax.exe"):
        app_names = {"maya.exe": "Maya", "cinema4d.exe": "Cinema 4D",
                     "houdini.exe": "Houdini", "3dsmax.exe": "3ds Max"}
        return f"{app_names.get(proc, '3D App')} - 3D Modeling"
    if proc == "zbrush.exe":
        return "ZBrush - 3D Sculpting"
    if proc in ("lightroom.exe", "lightroomclassic.exe"):
        return "Lightroom - Photo Editing"
    if proc in ("irfanview.exe", "xnviewmp.exe", "faststone.exe", "jpegview.exe"):
        return "Image Viewer - Photo Browsing"
    if proc in ("rawtherapee.exe", "darktable.exe"):
        return "RAW Editor - Photo Editing"

    # ── Utilities ─────────────────────────────────────────────────────────────
    if proc == "powertoys.exe":
        return "PowerToys - Windows Utilities"
    if proc == "autohotkey.exe":
        return "AutoHotkey - Automation"
    if proc in ("everything.exe", "flow.launcher.exe", "keypirinha.exe"):
        return "File Explorer - Searching"
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
    Deep Browser Classification Engine — Site-Specific + Intent-Specific.
    Outputs labels like: YouTube - Video, Amazon - Product Browsing, GitHub - PR Review
    """
    t = (page_title or "").lower()
    
    # 1. Title Normalization (strip browser suffixes)
    for suffix in ["google chrome", "microsoft edge", "firefox", "brave", "opera", "safari"]:
        t = t.replace(f" - {suffix}", "").replace(f" | {suffix}", "").strip()

    # ── YouTube (Deep) ───────────────────────────────────────────────────
    if "youtube.com" in domain or "youtu.be" in domain or "youtube" in t:
        if "shorts" in t or "#shorts" in t:
            return "YouTube - Shorts"
        if "live" in t or "🔴" in t:
            return "YouTube - Live"
        if any(k in t for k in ["music", "song", "lyrics", "audio"]):
            return "YouTube - Music"
        if any(k in t for k in ["@", "podcast", "tutorial", "course", "lecture", "how to", "learn"]):
            return "YouTube - Tutorial"
        if any(k in t for k in ["youtube", "youtube.com", "my channel", "subscriptions", "search", "results", "channel", "subscribe"]):
            return "YouTube - Browsing"
        return "YouTube - Video"

    # ── Netflix ──────────────────────────────────────────────────────────
    if "netflix.com" in domain or "netflix" in t:
        if any(k in t for k in ["movie", "film"]):
            return "Netflix - Movie"
        if any(k in t for k in ["episode", "season"]) or (t != "netflix" and "browse" not in t):
            return "Netflix - Watching"
        return "Netflix - Browsing"
    if any(k in t for k in ["hotstar", "disney+", "disneyplus"]):
        return "Disney+ - Watching"
    if any(k in t for k in ["prime video", "primevideo"]):
        return "Prime Video - Watching"

    # ── Amazon / Shopping ────────────────────────────────────────────────
    if "amazon" in domain or "amazon" in t:
        if any(k in t for k in ["checkout", "payment", "place order", "buy now"]):
            return "Amazon - Checkout"
        if any(k in t for k in ["your orders", "track", "delivery"]):
            return "Amazon - Order Tracking"
        if "search" in t or "results" in t:
            return "Amazon - Searching"
        return "Amazon - Shopping"

    shopping_domains = ["flipkart.com", "ebay.com", "daraz.pk", "aliexpress.com", "olx.com", "walmart.com"]
    if any(d in domain for d in shopping_domains) or any(s in t for s in ["flipkart", "ebay", "daraz", "olx", "aliexpress", "walmart"]):
        site_map = [
            ("olx", "OLX"), ("daraz", "Daraz"), ("flipkart", "Flipkart"),
            ("ebay", "eBay"), ("walmart", "Walmart"), ("aliexpress", "AliExpress"),
        ]
        site = "Shopping"
        for keyword, name in site_map:
            if keyword in domain or keyword in t:
                site = name
                break
        if any(k in t for k in ["checkout", "payment", "cart"]):
            return f"{site} - Checkout"
        return f"{site} - Shopping"

    # ── GitHub ───────────────────────────────────────────────────────────
    if "github.com" in domain or "github" in t:
        if any(k in t for k in ["pull request", "/pull/", "pr #"]):
            return "GitHub - PR Review"
        if "issue" in t or "/issues/" in t:
            return "GitHub - Issue"
        if "commit" in t or "history" in t:
            return "GitHub - Commit"
        if any(k in t for k in [".py", ".js", ".ts", ".java", ".cpp", "blob/"]):
            return "GitHub - Code"
        return "GitHub - Browsing"

    # ── Stack Overflow ───────────────────────────────────────────────────
    if "stackoverflow.com" in domain or "stack overflow" in t:
        if "answer" in t:
            return "Stack Overflow - Answering"
        return "Stack Overflow - Problem Solving"

    # ── Gmail / Email ────────────────────────────────────────────────────
    if any(d in t for d in ["gmail", "inbox"]):
        if "compose" in t or "new message" in t or "draft" in t:
            return "Gmail - Composing"
        if "search" in t:
            return "Gmail - Searching"
        return "Gmail - Reading"
    if any(d in t for d in ["outlook", "mail.yahoo", "protonmail"]):
        return "Outlook - Reading"

    # ── Google Docs / Sheets / Slides / Drive ────────────────────────────
    if "docs.google" in t or "google docs" in t or "word online" in t:
        if "comment" in t or "suggest" in t:
            return "Google Docs - Reviewing"
        return "Google Docs - Writing"
    if "sheets.google" in t or "google sheets" in t or "excel online" in t:
        return "Google Sheets - Editing"
    if "slides.google" in t or "google slides" in t or "powerpoint online" in t:
        return "Google Slides - Editing"
    if "drive.google" in t or "google drive" in t:
        return "Google Drive - Browsing"

    # ── Google Meet / Zoom / Teams ────────────────────────────────────────
    if any(k in t for k in ["meet.google", "google meet", "online meeting"]):
        return "Google Meet - Meeting"
    # Google Meet often shows just "Meet" or "Meeting in progress" in the title
    if t.startswith("meet") and ("google" in t or len(t.split()) <= 3):
        return "Google Meet - Meeting"
    if "zoom" in t:
        return "Zoom - Meeting"
    if "teams" in t:
        return "Teams - Meeting"
    if "calendar" in t and ("google" in t or "outlook" in t):
        return "Google Docs - Collaboration"
    
    # ── Kaggle / DS Notebooks ─────────────────────────────────────────────
    if "kaggle.com" in domain or "kaggle" in t:
        if "notebook" in t or "editor" in t or "kernel" in t:
            return "Kaggle - Notebook"
        if "dataset" in t:
            return "Kaggle - Dataset"
        if "competition" in t:
            return "Kaggle - Competition"
        return "Kaggle - Browsing"

    # ── arXiv / Research ─────────────────────────────────────────────────
    if "arxiv" in t:
        if "abs/" in t or "abstract" in t:
            return "arXiv - Reading Abstract"
        if "search" in t or "list" in t:
            return "arXiv - Searching Papers"
        return "arXiv - Reading Paper"
    if any(d in t for d in _RESEARCH_DOMAINS):
        return "arXiv - Reading Paper"

    # ── Learning Platforms ───────────────────────────────────────────────
    if "coursera" in t:
        if "quiz" in t or "exam" in t or "assignment" in t:
            return "Coursera - Quiz"
        if "discussion" in t or "forum" in t:
            return "Coursera - Discussion"
        return "Coursera - Lecture"
    if "udemy" in t:
        return "Udemy - Lecture"
    if any(d in t for d in ["edx", "khanacademy", "khan academy"]):
        return "Khan Academy - Lecture"
    if "codecademy" in t:
        return "Codecademy - Practice"
    if "leetcode" in t:
        if "contest" in t:
            return "LeetCode - Contest"
        if "discuss" in t:
            return "LeetCode - Discussion"
        if any(k in t for k in ["problem", "solution"]):
            return "LeetCode - Coding Practice"
        return "LeetCode - Coding Practice"
    if "hackerrank" in t:
        return "HackerRank - Practice"

    # ── Reddit ───────────────────────────────────────────────────────────
    if "reddit" in t:
        if "comment" in t:
            return "Reddit - Comments"
        if any(k in t for k in ["r/", "post", "thread"]):
            return "Reddit - Post"
        return "Reddit - Browsing"

    # ── Twitter/X ────────────────────────────────────────────────────────
    if any(d in domain for d in ["twitter.com", "x.com", "threads.net"]) or any(k in t for k in ["twitter", "x.com", "threads"]):
        if any(k in t for k in ["compose", "tweet", "post"]):
            return "Twitter - Composing"
        if "thread" in t:
            return "Twitter - Thread"
        return "Twitter - Browsing"

    # ── LinkedIn ─────────────────────────────────────────────────────────
    if "linkedin" in t:
        if "job" in t or "career" in t or "apply" in t:
            return "LinkedIn - Job Hunting"
        if "message" in t or "messaging" in t:
            return "LinkedIn - Networking"
        return "LinkedIn - Browsing"

    # ── Social Media (other) ─────────────────────────────────────────────
    if "instagram" in t:
        return "Instagram - Browsing"
    if "facebook" in t:
        return "Facebook - Browsing"
    if "tiktok" in t:
        return "TikTok - Browsing"
    if "snapchat" in t:
        return "Snapchat - Browsing"

    # ── Figma / Canva ────────────────────────────────────────────────────
    if "figma" in t:
        if "prototype" in t:
            return "Figma - Prototyping"
        return "Figma - Designing"
    if "canva" in t:
        return "Canva - Designing"

    # ── Twitch ───────────────────────────────────────────────────────────
    if "twitch" in t:
        if "chat" in t:
            return "Twitch - Chatting"
        if "browse" in t or "directory" in t:
            return "Twitch - Browsing"
        return "Twitch - Watching"

    # ── Spotify (Web) ────────────────────────────────────────────────────
    if "spotify" in t:
        if "podcast" in t:
            return "Spotify - Podcast"
        if "playlist" in t:
            return "Spotify - Playlist"
        return "Spotify - Music"

    # ── Wikipedia ────────────────────────────────────────────────────────
    if "wikipedia" in t:
        if "search" in t:
            return "Wikipedia - Searching"
        return "Wikipedia - Reading"

    # ── Medium ───────────────────────────────────────────────────────────
    if "medium" in t:
        if "write" in t or "draft" in t or "new story" in t:
            return "Medium - Writing"
        return "Medium - Reading"

    # ── Quora ────────────────────────────────────────────────────────────
    if "quora" in t:
        return "Wikipedia - Reading"

    # ── Financial / Trading ──────────────────────────────────────────────
    if "tradingview" in t:
        return "TradingView - Market Analysis"
    if "binance" in t:
        return "Binance - Trading"
    if any(d in t for d in ["banking", "bank", "icici", "hdfc", "chase", "wellsfargo"]):
        if any(k in t for k in ["transfer", "pay", "send"]):
            return "Banking - Transaction"
        if any(k in t for k in ["statement", "history"]):
            return "Banking - Statement"
        return "Banking - Account"
    if "paypal" in t:
        return "PayPal - Account"

    # ── News ─────────────────────────────────────────────────────────────
    if any(d in t for d in _NEWS_DOMAINS):
        return "News - Reading"

    # ── AI Assistants ────────────────────────────────────────────────────
    if any(k in t for k in ["chatgpt", "claude", "gemini", "perplexity", "copilot"]):
        return "ChatGPT - AI Chat"

    # ── Messaging ────────────────────────────────────────────────────────
    if "whatsapp" in t:
        return "WhatsApp - Chat"
    if "telegram" in t:
        return "Telegram - Chat"
    if "slack" in t:
        return "Slack - Chat"

    # ── Notion / Work tools ──────────────────────────────────────────────
    if "notion" in t:
        return "Notion - Note Taking"
    if "trello" in t or "jira" in t:
        return "Notion - Project Management"

    # ── CodePen / StackBlitz ─────────────────────────────────────────────
    if any(k in t for k in ["codepen", "stackblitz", "codesandbox"]):
        return "LeetCode - Coding Practice"

    # ── PDF ──────────────────────────────────────────────────────────────
    if t.endswith(".pdf") or "pdf" in t:
        return "arXiv - Reading Paper"

    # ── New Tab / Empty ──────────────────────────────────────────────────
    if "new tab" in t or not t:
        return "Browser - Web"

    # ── Shopping keyword fallback ────────────────────────────────────────
    if any(k in t for k in ["buy", "shop", "cart", "checkout", "product", "price"]):
        return "Amazon - Shopping"

    # ── Research keyword fallback ────────────────────────────────────────
    if any(k in t for k in ["paper", "article", "journal", "conference"]):
        return "arXiv - Reading Paper"

    # ── Default: return None so CLIP/OCR pipeline can analyze ─────────────
    return None

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
        return "Idle - Away from Keyboard"
    if "update" in bg_lower:
        return "Idle - Away from Keyboard"
    if "scan" in bg_lower or "antivirus" in bg_lower or "defender" in bg_lower:
        return "Idle - Away from Keyboard"
    if "copy" in bg_lower or "transfer" in bg_lower:
        return "Idle - Away from Keyboard"
    if "render" in bg_lower:
        return "Idle - Away from Keyboard"
    if "build" in bg_lower or "compile" in bg_lower:
        return "Idle - Away from Keyboard"

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
    """VS Code: Coding / Debugging / Version Control."""
    full_text = f"{title_lower} {ocr_text.lower()}"
    if "debug" in full_text or "breakpoint" in full_text:
        return "VS Code - Debugging"
    if any(k in full_text for k in ["git", "pull request", "merge", "commit"]):
        return "VS Code - Version Control"
    return "VS Code - Coding"


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
    """JetBrains: [IDE] - Coding / Debugging."""
    ide_map = {
        "pycharm64.exe": "PyCharm",
        "idea64.exe":    "IntelliJ",
        "webstorm64.exe":"WebStorm",
        "rider64.exe":   "Rider",
        "clion64.exe":   "CLion",
        "phpstorm64.exe":"PhpStorm",
        "goland64.exe":  "GoLand",
        "datagrip64.exe":"DataGrip",
    }
    ide = ide_map.get(proc, "IntelliJ")
    full_text = f"{title_lower} {ocr_text.lower()}"
    if "debug" in full_text or "breakpoint" in full_text:
        return f"{ide} - Debugging"
    return f"{ide} - Coding"


def _classify_discord(title: str, title_lower: str) -> str:
    """Discord: Chat / Voice / Voice Gaming."""
    if "voice connected" in title_lower or "rtc connected" in title_lower:
        if any(k in title_lower for k in ["game", "gaming", "play"]):
            return "Discord - Voice Gaming"
        return "Discord - Voice"
    if "screen share" in title_lower or "live" in title_lower:
        return "Discord - Voice"
    return "Discord - Chat"


def _classify_zoom(title: str, title_lower: str) -> str:
    """Zoom: Meeting / Screen Share."""
    if "presenting" in title_lower or "sharing" in title_lower:
        return "Zoom - Screen Share"
    return "Zoom - Meeting"


def _classify_teams(title: str, title_lower: str) -> str:
    """Teams: Chat / Meeting."""
    if "chat" in title_lower or "message" in title_lower:
        return "Teams - Chat"
    return "Teams - Meeting"


def _classify_excel(title: str, title_lower: str, ocr_text: str) -> str:
    """Excel: Data Entry / Analysis."""
    full_text = f"{title_lower} {ocr_text.lower()}"
    if any(k in full_text for k in ["formula", "pivot", "analysis", "vlookup", "chart", "graph"]):
        return "Excel - Analysis"
    return "Excel - Data Entry"


def _classify_word(title: str, title_lower: str) -> str:
    """Classify Word with App-Specific + Intent-Specific labels."""
    if any(k in title_lower for k in ["review", "track change", "comment"]):
        return "Word - Reviewing"
    if any(k in title_lower for k in ["print", "layout", "format"]):
        return "Word - Formatting"
    return "Word - Writing"


def _classify_spotify(title: str, title_lower: str) -> str:
    """Spotify: always [App] - [Intent]."""
    if "podcast" in title_lower:
        return "Spotify - Podcast"
    return "Spotify - Music"


def _classify_terminal(proc: str, title: str, title_lower: str, ocr_text: str) -> str:
    """Terminal: always [App] - [Intent]."""
    return "Terminal - Command"


def _classify_explorer(title: str, title_lower: str) -> str:
    """File Explorer: always [App] - [Intent]."""
    if any(k in title_lower for k in ["copying", "moving", "transferring", "% complete"]):
        return "File Explorer - Managing"
    return "File Explorer - Browsing"


def _refine_youtube_label(page_title: str, base_label: str) -> str:
    """Add YouTube context: music video, shorts, etc."""
    return base_label


def match_universal_keywords(text: str) -> Optional[str]:
    """
    Catch-all keyword engine — App-Specific + Intent-Specific.
    Scans any text (Window Title, OCR, Title) for high-intent keywords.
    Returns standardized '[App] - [Specific Intent]' labels.
    """
    if not text or len(text) < 3:
        return None
    
    t = text.lower()
    
    # ── Financial / Trading ──────────────────────────────────────────────────
    if any(kw in t for kw in ["tradingview", "metatrader"]):
        return "TradingView - Market Analysis"
    if any(kw in t for kw in ["binance", "coinbase"]):
        return "Binance - Trading"
    if any(kw in t for kw in ["candlestick", "order book", "leverage", "margin", "pnl",
                               "forex", "stock market", "share price", "portfolio", "bitcoin", "crypto"]):
        return "TradingView - Market Analysis"
    
    # ── Shopping / E-Commerce ───────────────────────────────────────────────
    if any(kw in t for kw in ["daraz"]):
        return "Daraz - Shopping"
    if any(kw in t for kw in ["amazon"]):
        return "Amazon - Shopping"
    if any(kw in t for kw in ["ebay"]):
        return "eBay - Shopping"
    if any(kw in t for kw in ["checkout", "shopping cart", "add to cart", "buy now"]):
        return "Amazon - Checkout"

    # ── Entertainment ──────────────────────────────────────────────────────────
    if "netflix" in t:
        return "Netflix - Watching"
    if any(kw in t for kw in ["youtube", "vimeo"]):
        return "YouTube - Video"
    if any(kw in t for kw in ["twitch", "live stream"]):
        return "Twitch - Watching"
    if any(kw in t for kw in ["spotify", "soundcloud"]):
        return "Spotify - Music"
    if any(kw in t for kw in ["gaming", "steam", "epic games", "roblox", "minecraft"]):
        return "Steam - Gaming"
    if "reddit" in t:
        return "Reddit - Browsing"
    if any(kw in t for kw in ["twitter", "x.com", "threads"]):
        return "Twitter - Browsing"
    if "tiktok" in t:
        return "TikTok - Browsing"
    if "instagram" in t:
        return "Instagram - Browsing"
    if "facebook" in t:
        return "Facebook - Browsing"
    
    # ── Work / Productivity ────────────────────────────────────────────────
    if any(kw in t for kw in ["zoom meeting", "zoom"]):
        return "Zoom - Meeting"
    if any(kw in t for kw in ["teams call", "microsoft teams"]):
        return "Teams - Meeting"
    if "slack" in t:
        return "Slack - Chat"
    if "notion" in t:
        return "Notion - Writing"
    if any(kw in t for kw in ["jira", "trello", "kanban"]):
        return "Jira - Project Management"
    if any(kw in t for kw in ["document", "proposal", "contract", "word"]):
        return "Word - Writing"
    if any(kw in t for kw in ["spreadsheet", "invoice", "excel"]):
        return "Excel - Data Entry"
    if any(kw in t for kw in ["presentation", "slides", "powerpoint"]):
        return "PowerPoint - Creating"
    
    # ── Research / Academic ────────────────────────────────────────────────
    if any(kw in t for kw in ["abstract", "references", "cite", "journal", "arxiv", "scholar", "pubmed"]):
        return "arXiv - Reading Paper"
    
    # ── Learning ─────────────────────────────────────────────────────────
    if any(kw in t for kw in ["tutorial", "how to", "lecture", "online course", "udemy", "coursera", "khan academy"]):
        return "Coursera - Lecture"
    
    # ── Information / News / Search ────────────────────────────────────────
    if any(kw in t for kw in ["wikipedia", "quora"]):
        return "Wikipedia - Reading"
    if any(kw in t for kw in ["breaking news", "opinion", "news site"]):
        return "News - Reading"
    
    # ── Development / Coding ───────────────────────────────────────────────
    if any(kw in t for kw in ["github", "gitlab"]):
        return "GitHub - Browsing"
    if any(kw in t for kw in ["vs code", "pycharm", "intellij", "jupyter", "debugger"]):
        return "VS Code - Coding"
    
    # ── Terminal / OCR ──────────────────────────────────────────────────
    if any(kw in t for kw in [r"c:\users", r"ps c:\ ", "ubuntu@", "root@", "-bash",
                               "npm install", "pip install", "docker run"]):
        return "Terminal - Command"
    
    # ── Communication / AI ────────────────────────────────────────────────
    if any(kw in t for kw in ["chatgpt", "openai", "claude", "gemini", "bard", "perplexity", "ai chat"]):
        return "ChatGPT - AI Chat"
    if any(kw in t for kw in ["whatsapp"]):
        return "WhatsApp - Chat"
    if any(kw in t for kw in ["telegram"]):
        return "Telegram - Chat"
    if any(kw in t for kw in ["messenger", "signal", "direct message"]):
        return "WhatsApp - Chat"

    return None



def match_generic_keywords(title_lower: str) -> Optional[str]:
    """
    Catch-all keyword matcher for titles — App-Specific + Intent-Specific.
    Consolidates with match_universal_keywords for maximum coverage.
    """
    # 1. Broad universal check first
    universal = match_universal_keywords(title_lower)
    if universal:
        return universal

    # 2. Specific Windows/System overrides
    rules = [
        (["microsoft store", "app store", "windows store", "ms store"], "Microsoft Store - Browsing"),
        (["windows settings", "system settings", "personalization", "display settings"], "Settings - Configuring"),
        (["calculator"], "Calculator - Using"),
        (["snipping tool", "snip & sketch"], "Snipping Tool - Screenshot"),
        (["alarms", "clock", "timer"], "Clock - Using"),
        (["lock screen", "screensaver", "afk", "sign in", "login"], "Idle - Locked"),
        (["file explorer", "this pc", "my computer", "documents", "downloads"], "File Explorer - Browsing"),
        (["task manager", "process explorer"], "Task Manager - Monitoring"),
        (["powershell", "cmd", "command prompt", "terminal", "bash", "ubuntu", r"c:\\", r"d:\\", ".exe"], "Terminal - Command"),
        (["python", "node", "npm ", "pip ", "conda "], "Terminal - Command"),
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