"""
Behavioral Signal Collector — runs in a background thread.

Collects lightweight OS/process signals at 1Hz (no ML needed).
These signals boost classification accuracy without adding to latency
because they run in parallel to the main pipeline.

Signals collected:
  - Foreground process name (via psutil + ctypes)
  - Background running apps (Discord, Spotify, etc.)
  - Network I/O rate (streaming vs downloading vs idle)
  - CPU usage (gaming/rendering detection)
  - Cursor position delta (mouse activity)
  - Seconds since last user input (AFK detection)
"""
from __future__ import annotations

import ctypes
import logging
import os
import sys
import threading
import time
from collections import deque
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known background app → "Category - Subcategory" secondary activity maps
# These processes running in background add to secondary_activities
# ---------------------------------------------------------------------------
_BACKGROUND_APP_MAP: Dict[str, str] = {
    # Music
    "spotify.exe":              "Entertainment - Spotify",
    "spotify":                  "Entertainment - Spotify",
    "musicbee.exe":             "Entertainment - Music",
    "foobar2000.exe":           "Entertainment - Music",
    "aimp.exe":                 "Entertainment - Music",
    "itunes.exe":               "Entertainment - Music",
    "tidal.exe":                "Entertainment - Music",
    "deezer.exe":               "Entertainment - Music",
    "groove.exe":               "Entertainment - Music",
    "zunemusic.exe":            "Entertainment - Music",
    "vlc.exe":                  "Entertainment - Music",
    "potplayer.exe":            "Entertainment - Music",
    "mpc-hc.exe":               "Entertainment - Music",
    # Communication
    "discord.exe":              "Communication - Discord",
    "discord":                  "Communication - Discord",
    "slack.exe":                "Communication - Slack",
    "slack":                    "Communication - Slack",
    "teams.exe":                "Communication - Teams Chat",
    "ms-teams.exe":             "Communication - Teams Chat",
    "zoom.exe":                 "Communication - Zoom",
    "telegram.exe":             "Communication - Telegram",
    "whatsapp.exe":             "Communication - WhatsApp",
    "signal.exe":               "Communication - Signal",
    "skype.exe":                "Communication - Skype",
    "viber.exe":                "Communication - Viber",
    "wechat.exe":               "Communication - WeChat",
    "mattermost.exe":           "Communication - Mattermost",
    # Downloads
    "qbittorrent.exe":          "System - Downloads",
    "utorrent.exe":             "System - Downloads",
    "transmission":             "System - Downloads",
    "wget.exe":                 "System - Downloads",
    "curl.exe":                 "System - Downloads",
    "idman.exe":                "System - Downloads",
    "jdownloader.exe":          "System - Downloads",
    "aria2c.exe":               "System - Downloads",
    # System
    "antimalware":              "System - Windows Defender",
    "windowsupdate":            "System - Windows Update",
    "msiexec.exe":              "System - Windows Update",
    "wuauclt.exe":              "System - Windows Update",
    "usocoreworker.exe":        "System - Windows Update",
    "tiworker.exe":             "System - Windows Update",
    # Rendering
    "handbrake.exe":            "Work - Video Editing",
    "ffmpeg.exe":               "Work - Video Editing",
    "davinciresolve.exe":       "Work - Video Editing",
    "premierepcl.exe":          "Work - Video Editing",
    "blender.exe":              "Work - Blender",
    # Gaming helpers
    "steam.exe":                "Entertainment - Steam Gaming",
    "epicgameslauncher.exe":    "Entertainment - Steam Gaming",
    "riotclientservices.exe":   "Entertainment - Steam Gaming",
    "battlenet.exe":            "Entertainment - Steam Gaming",
    "gog galaxy.exe":           "Entertainment - Steam Gaming",
    "origin.exe":               "Entertainment - Steam Gaming",
    "uplay.exe":                "Entertainment - Steam Gaming",
    "xboxapp.exe":              "Entertainment - Steam Gaming",
    # VPN (background)
    "nordvpn.exe":              "System - VPN",
    "expressvpn.exe":           "System - VPN",
    "protonvpn.exe":            "System - VPN",
    "openvpn.exe":              "System - VPN",
    "wireguard.exe":            "System - VPN",
    "surfshark.exe":            "System - VPN",
}

# Known foreground process → "Category - Subcategory" (for process-level fast classify)
_FOREGROUND_APP_MAP: Dict[str, str] = {
    # ── IDEs / Dev Tools ──────────────────────────────────────────────────────
    "code.exe":                 "Work - VS Code",
    "code":                     "Work - VS Code",
    "pycharm64.exe":            "Work - PyCharm",
    "idea64.exe":               "Work - IntelliJ",
    "webstorm64.exe":           "Work - VS Code",
    "rider64.exe":              "Work - IntelliJ",
    "clion64.exe":              "Work - IntelliJ",
    "phpstorm64.exe":           "Work - IntelliJ",
    "goland64.exe":             "Work - IntelliJ",
    "datagrip64.exe":           "Work - IntelliJ",
    "sublime_text.exe":         "Work - VS Code",
    "notepad++.exe":            "Work - VS Code",
    "zed.exe":                  "Work - VS Code",
    "cursor.exe":               "Work - VS Code",
    "vim.exe":                  "Work - VS Code",
    "nvim.exe":                 "Work - VS Code",
    "atom.exe":                 "Work - VS Code",
    "eclipse.exe":              "Work - VS Code",
    "devenv.exe":               "Work - VS Code",
    # ── Terminals / Shells ────────────────────────────────────────────────────
    "cmd.exe":                  "Work - Terminal",
    "powershell.exe":           "System - PowerShell",
    "pwsh.exe":                 "System - PowerShell",
    "wt.exe":                   "Work - Terminal",
    "windowsterminal.exe":      "Work - Terminal",
    "git-bash.exe":             "Development - Git Bash",
    "bash.exe":                 "Development - Bash",
    "python.exe":               "Development - Python Script",
    "python3":                  "Development - Python Script",
    "node.exe":                 "Development - Node.js",
    "wsl.exe":                  "Development - WSL (Linux)",
    "ubuntu.exe":               "Development - WSL (Ubuntu)",
    # ── Version Control ───────────────────────────────────────────────────────
    "githubdesktop.exe":        "Development - GitHub Desktop",
    "sourcetree.exe":           "Development - Sourcetree",
    "gitkraken.exe":            "Development - GitKraken",
    "fork.exe":                 "Development - Fork (Git)",
    # ── Data Tools ───────────────────────────────────────────────────────────
    "jupyter-lab.exe":          "Development - JupyterLab",
    "jupyter.exe":              "Development - Jupyter Notebook",
    "dbeaver.exe":              "Development - DBeaver",
    "tableplus.exe":            "Development - TablePlus",
    "postman.exe":              "Development - Postman",
    "insomnia.exe":             "Development - Insomnia",
    "wireshark.exe":            "Development - Wireshark (Network)",
    "putty.exe":                "Development - PuTTY (SSH)",
    "winscp.exe":               "Development - WinSCP (SFTP)",
    "filezilla.exe":            "Development - FileZilla (FTP)",
    # ── Game Engines ───────────────────────────────────────────────────────────
    "unity.exe":                "Development - Unity (Game Dev)",
    "unreal.exe":               "Development - Unreal Engine",
    "godot.exe":                "Development - Godot (Game Dev)",
    # ── Office / Productivity ──────────────────────────────────────────────────
    "winword.exe":              "Work - Word (Document Writing)",
    "soffice.exe":              "Work - Document Processing",
    "excel.exe":                "Work - Excel",
    "powerpnt.exe":             "Work - PowerPoint (Presentation)",
    "onenote.exe":              "Work - OneNote (Note Taking)",
    "acrobat.exe":              "Learning - PDF Reading",
    "acrord32.exe":             "Learning - PDF Reading",
    "foxit reader.exe":         "Learning - PDF Reading",
    "sumatrapdf.exe":           "Learning - PDF Reading",
    "obsidian.exe":             "Work - Obsidian (Note Taking)",
    "notion.exe":               "Work - Notion",
    "evernote.exe":             "Work - Evernote (Note Taking)",
    "typora.exe":               "Work - Typora (Markdown)",
    "anki.exe":                 "Learning - Anki (Flashcards)",
    "kindle.exe":               "Learning - Kindle (Book Reading)",
    "calibre.exe":              "Learning - Calibre (eBooks)",
    # ── Windows Built-in Apps ──────────────────────────────────────────────────
    "notepad.exe":              "Work - Notepad (Text Editing)",
    "wordpad.exe":              "Work - WordPad (Document)",
    "mspaint.exe":              "Creative - MS Paint (Drawing)",
    "paint.exe":                "Creative - Paint 3D",
    "photos.exe":               "Creative - Photos (Viewer)",
    "microsoft.photos.exe":     "Creative - Photos (Viewer)",
    "windowscamera.exe":        "Creative - Camera",
    "winstore.app.exe":         "Shopping - Microsoft Store",
    "microsoftstore.exe":       "Shopping - Microsoft Store",
    "systemsettings.exe":       "System - Windows Settings",
    "windowssettings.exe":      "System - Windows Settings",
    "calculatorapp.exe":        "Utility - Calculator",
    "calculator.exe":           "Utility - Calculator",
    "windowscalculator.exe":    "Utility - Calculator",
    "snippingtool.exe":         "System - Snipping Tool",
    "screensketch.exe":         "System - Snip & Sketch",
    "snipandsketchwm.exe":      "System - Snip & Sketch",
    "windowsmaps.exe":          "Information - Windows Maps",
    "windowsalarms.exe":        "Utility - Alarms & Clock",
    "mail.exe":                 "Communication - Windows Mail (Email)",
    "hxoutlook.exe":            "Communication - Windows Mail (Email)",
    "hxcalendarappimm.exe":     "Work - Windows Calendar",
    "cortana.exe":              "Information - Cortana (Search)",
    "searchhost.exe":           "Information - Windows Search",
    "searchui.exe":             "Information - Windows Search",
    "shellexperiencehost.exe":  "System - Start Menu",
    "startmenuexperiencehost.exe": "System - Start Menu",
    "xbox.exe":                 "Entertainment - Xbox (Gaming)",
    "xboxapp.exe":              "Entertainment - Xbox (Gaming)",
    "gamebar.exe":              "Entertainment - Xbox Game Bar",
    "groove.exe":               "Entertainment - Groove Music",
    "zunemusic.exe":            "Entertainment - Groove Music",
    "zunevideo.exe":            "Entertainment - Movies & TV (Video)",
    "video.ui.exe":             "Entertainment - Movies & TV (Video)",
    "microsoftsolitaire.exe":   "Entertainment - Solitaire (Game)",
    "solitaire.exe":            "Entertainment - Solitaire (Game)",
    "minecraftlauncher.exe":    "Entertainment - Gaming (Minecraft)",
    "minecraft.exe":            "Entertainment - Gaming (Minecraft)",
    "lockapp.exe":              "Idle - Screen Locked",
    "logonui.exe":              "Idle - Login Screen",
    # ── Creative ───────────────────────────────────────────────────────────────
    "photoshop.exe":            "Creative - Photoshop",
    "illustrator.exe":          "Creative - Illustrator",
    "gimp.exe":                 "Creative - GIMP",
    "inkscape.exe":             "Creative - Inkscape",
    "figma.exe":                "Creative - Figma (UI Design)",
    "blender.exe":              "Creative - Blender (3D)",
    "blender":                  "Creative - Blender (3D)",
    "premiere pro.exe":         "Creative - Premiere Pro",
    "afterfx.exe":              "Creative - After Effects",
    "davinciresolve.exe":       "Creative - DaVinci Resolve",
    "kdenlive.exe":             "Creative - Kdenlive",
    "audacity.exe":             "Creative - Audacity",
    "fl studio.exe":            "Creative - FL Studio",
    "obs64.exe":                "Creative - OBS Studio",
    "obs.exe":                  "Creative - OBS Studio",
    "obs32.exe":                "Creative - OBS Studio",
    "loom.exe":                 "Communication - Loom (Screen Recording)",
    "lightroom.exe":            "Creative - Lightroom",
    "autocad.exe":              "Creative - AutoCAD",
    "fusion360.exe":            "Creative - Fusion 360 (3D CAD)",
    "maya.exe":                 "Creative - Maya (3D)",
    "cinema4d.exe":             "Creative - Cinema 4D (3D)",
    "zbrush.exe":               "Creative - ZBrush (3D Sculpt)",
    "irfanview.exe":            "Creative - IrfanView (Image Viewer)",
    "faststone.exe":            "Creative - FastStone (Image Viewer)",
    "sharex.exe":               "System - ShareX (Screenshot)",
    "greenshot.exe":            "System - Greenshot (Screenshot)",
    "bandicam.exe":             "Creative - Bandicam (Recording)",
    "clipchamp.exe":            "Creative - Clipchamp (Video Edit)",
    # ── Media Players (foreground) ─────────────────────────────────────────────
    "vlc.exe":                  "Entertainment - VLC (Video)",
    "mpv.exe":                  "Entertainment - mpv (Video)",
    "mpc-hc64.exe":             "Entertainment - MPC-HC (Video)",
    "mpc-hc.exe":               "Entertainment - MPC-HC (Video)",
    "potplayer.exe":            "Entertainment - PotPlayer (Video)",
    "wmplayer.exe":             "Entertainment - Windows Media Player",
    "kodi.exe":                 "Entertainment - Kodi (Media Center)",
    "plex.exe":                 "Entertainment - Plex (Media)",
    "jellyfin.exe":             "Entertainment - Jellyfin (Media)",
    "spotify.exe":              "Entertainment - Spotify (Music)",
    "itunes.exe":               "Entertainment - iTunes (Music)",
    "aimp.exe":                 "Entertainment - AIMP (Music Player)",
    "foobar2000.exe":           "Entertainment - foobar2000 (Music)",
    "musicbee.exe":             "Entertainment - MusicBee (Music)",
    "tidal.exe":                "Entertainment - Tidal (Music)",
    "deezer.exe":               "Entertainment - Deezer (Music)",
    "netflix.exe":              "Entertainment - Netflix (Streaming)",
    "disneyplus.exe":           "Entertainment - Disney+ (Streaming)",
    "twitch.exe":               "Entertainment - Twitch (Live Stream)",
    # ── Communication (foreground) ─────────────────────────────────────────────
    "teams.exe":                "Communication - Teams Meeting",
    "ms-teams.exe":             "Communication - Teams Meeting",
    "zoom.exe":                 "Communication - Zoom Meeting",
    "discord.exe":              "Communication - Discord",
    "slack.exe":                "Communication - Slack (Messaging)",
    "telegram.exe":             "Communication - Telegram",
    "signal.exe":               "Communication - Signal",
    "thunderbird.exe":          "Communication - Email",
    "outlook.exe":              "Communication - Email",
    "whatsapp.exe":             "Communication - WhatsApp",
    "viber.exe":                "Communication - Viber (Messaging)",
    "wechat.exe":               "Communication - WeChat (Messaging)",
    "skype.exe":                "Communication - Skype",
    "mattermost.exe":           "Communication - Mattermost (Work Chat)",
    # ── System Management ──────────────────────────────────────────────────────
    "taskmgr.exe":              "System - Task Manager",
    "procexp64.exe":            "System - Process Explorer",
    "procexp.exe":              "System - Process Explorer",
    "regedit.exe":              "System - Registry Editor",
    "mmc.exe":                  "System - Management Console",
    "explorer.exe":             "System - File Explorer",
    "msconfig.exe":             "System - System Configuration",
    "eventvwr.exe":             "System - Event Viewer",
    "control.exe":              "System - Control Panel",
    "mstsc.exe":                "System - Remote Desktop",
    "anydesk.exe":              "System - AnyDesk (Remote)",
    "teamviewer.exe":           "System - TeamViewer (Remote)",
    "vmware.exe":               "System - VMware",
    "virtualboxvm.exe":         "System - VirtualBox",
    "winrar.exe":               "System - WinRAR",
    "7zfm.exe":                 "System - 7-Zip",
    "ccleaner.exe":             "System - CCleaner",
    "malwarebytes.exe":         "System - Malwarebytes (Security)",
    "nordvpn.exe":              "Utility - NordVPN",
    "expressvpn.exe":           "Utility - ExpressVPN",
    "protonvpn.exe":            "Utility - ProtonVPN",
    "bitwarden.exe":            "Utility - Bitwarden (Password Manager)",
    "keepass.exe":              "Utility - KeePass (Password Manager)",
    "autohotkey.exe":           "Utility - AutoHotkey (Automation)",
    "powertoys.exe":            "Utility - PowerToys",
    "everything.exe":           "Utility - Everything (File Search)",
    "sharex.exe":               "System - ShareX (Screenshot)",
    "rufus.exe":                "System - Rufus (USB Boot)",
    # ── Financial ─────────────────────────────────────────────────────────────
    "mt4.exe":                  "Financial - MetaTrader 4 (Trading)",
    "mt5.exe":                  "Financial - MetaTrader 5 (Trading)",
    "thinkorswim.exe":          "Financial - thinkorswim (Trading)",
    "ninjatrader.exe":          "Financial - NinjaTrader (Trading)",
    "tradingview.exe":          "Financial - TradingView (Charts)",
}


# ---------------------------------------------------------------------------
# Windows AFK detection via GetLastInputInfo
# ---------------------------------------------------------------------------
class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_idle_seconds() -> float:
    """Return seconds since last keyboard/mouse input. Windows only."""
    try:
        if sys.platform != "win32":
            return 0.0
        lii = _LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(lii)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return max(0.0, millis / 1000.0)
    except Exception:
        return 0.0


def get_cursor_delta() -> float:
    """Return approximate cursor velocity (pixels/second). Windows only."""
    try:
        if sys.platform != "win32":
            return 0.0
        pt1 = ctypes.wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt1))
        time.sleep(0.05)
        pt2 = ctypes.wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt2))
        dx = pt2.x - pt1.x
        dy = pt2.y - pt1.y
        return ((dx**2 + dy**2) ** 0.5) / 0.05  # px/sec
    except Exception:
        return 0.0


def is_controller_active() -> bool:
    """Check if an Xbox controller is connected and has had recent input."""
    if sys.platform != "win32":
        return False
    try:
        xinput = ctypes.windll.XInput1_4
        class XINPUT_GAMEPAD(ctypes.Structure):
            _fields_ = [
                ("wButtons", ctypes.c_ushort), ("bLeftTrigger", ctypes.c_ubyte),
                ("bRightTrigger", ctypes.c_ubyte), ("sThumbLX", ctypes.c_short),
                ("sThumbLY", ctypes.c_short), ("sThumbRX", ctypes.c_short),
                ("sThumbRY", ctypes.c_short),
            ]
        class XINPUT_STATE(ctypes.Structure):
            _fields_ = [("dwPacketNumber", ctypes.c_ulong), ("Gamepad", XINPUT_GAMEPAD)]
        
        state = XINPUT_STATE()
        res = xinput.XInputGetState(0, ctypes.byref(state))
        return res == 0
    except Exception:
        return False


def is_audio_playing() -> bool:
    """Check if audio is currently playing using pycaw."""
    if sys.platform != "win32":
        return False
    try:
        from pycaw.pycaw import AudioUtilities
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            if session.Process and session.State == 1: # 1 is Active
                return True
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# BehavioralSignals — snapshot of current system state
# ---------------------------------------------------------------------------
class BehavioralSignals:
    __slots__ = (
        "foreground_process",        # str: "code.exe"
        "window_title",              # str: "main.py - VS Code"
        "foreground_activity",       # Optional[str]: "Work - Coding"
        "background_activities",     # List[str]: secondary activities from BG apps
        "idle_seconds",              # float
        "is_idle",                   # bool
        "net_bytes_per_sec",         # float
        "cpu_percent",               # float
        "gpu_percent",               # float (new)
        "cursor_velocity",           # float (px/sec)
        "is_streaming",              # bool: high inbound network = streaming
        "is_downloading",            # bool: very high network = background download
        "controller_active",         # bool: whether gamepad is active
        "media_playing",             # bool: whether audio is playing actively
        "screen_locked",             # bool: whether the screen is locked
        "timestamp",                 # float
    )

    def __init__(self):
        self.foreground_process = ""
        self.window_title = ""
        self.foreground_activity = None
        self.background_activities: List[str] = []
        self.idle_seconds = 0.0
        self.is_idle = False
        self.net_bytes_per_sec = 0.0
        self.cpu_percent = 0.0
        self.gpu_percent = 0.0
        self.cursor_velocity = 0.0
        self.is_streaming = False
        self.is_downloading = False
        self.controller_active = False
        self.media_playing = False
        self.screen_locked = False
        self.timestamp = time.time()


# ---------------------------------------------------------------------------
# BehavioralCollector — background thread
# ---------------------------------------------------------------------------
class BehavioralCollector:
    """
    Runs a daemon thread at ~1Hz collecting psutil/ctypes signals.
    The latest snapshot is always available via `.signals` (lock-free read).
    """

    def __init__(self, poll_interval: float = 1.0, idle_threshold: float = 60.0):
        self._poll_interval = poll_interval
        self._idle_threshold = idle_threshold
        self._signals = BehavioralSignals()
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        # Network baseline for delta calculation
        self._last_net_bytes = 0
        self._last_net_time = time.time()
        
        # GPU detection (optional, depends on GPUtil or subprocess)
        self._has_gpu_util = False
        try:
            import GPUtil
            self._has_gpu_util = True
        except ImportError:
            pass

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._collect_loop,
            name="behavioral_collector",
            daemon=True,
        )
        self._thread.start()
        logger.info("BehavioralCollector started (poll_interval=%.1fs)", self._poll_interval)

    def stop(self) -> None:
        self._running = False

    @property
    def signals(self) -> BehavioralSignals:
        """Thread-safe read of the latest snapshot."""
        with self._lock:
            return self._signals

    def _collect_loop(self) -> None:
        while self._running:
            try:
                snap = self._collect_snapshot()
                with self._lock:
                    self._signals = snap
            except Exception as exc:
                logger.debug("BehavioralCollector error: %s", exc)
            time.sleep(self._poll_interval)

    def _collect_snapshot(self) -> BehavioralSignals:
        import psutil

        snap = BehavioralSignals()
        snap.timestamp = time.time()

        # ── Idle detection ────────────────────────────────────────────────
        snap.idle_seconds = get_idle_seconds()

        # ── Network I/O rate ─────────────────────────────────────────────
        try:
            net = psutil.net_io_counters()
            now = time.time()
            total_bytes = net.bytes_recv + net.bytes_sent
            dt = max(now - self._last_net_time, 0.001)
            snap.net_bytes_per_sec = (total_bytes - self._last_net_bytes) / dt
            self._last_net_bytes = total_bytes
            self._last_net_time = now
        except Exception:
            snap.net_bytes_per_sec = 0.0

        snap.is_streaming   = 200_000 <= snap.net_bytes_per_sec < 2_000_000
        snap.is_downloading = snap.net_bytes_per_sec >= 2_000_000

        # ── CPU & GPU ────────────────────────────────────────────────────
        try:
            snap.cpu_percent = psutil.cpu_percent(interval=None)
            if self._has_gpu_util:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    snap.gpu_percent = max(gpu.load * 100 for gpu in gpus)
        except Exception:
            snap.cpu_percent = 0.0

        # ── Cursor velocity ───────────────────────────────────────────────
        snap.cursor_velocity = get_cursor_delta()

        # ── Controller & Audio & Lock ─────────────────────────────────────
        snap.controller_active = is_controller_active()
        snap.media_playing = is_audio_playing()

        # ── Process list ─────────────────────────────────────────────────
        try:
            running_names: Set[str] = set()
            for proc in psutil.process_iter(["name"]):
                try:
                    pname = (proc.info.get("name") or "").lower().strip()
                    if pname:
                        running_names.add(pname)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            snap.screen_locked = ("lockapp.exe" in running_names or "logonui.exe" in running_names)

            # Foreground process
            try:
                import ctypes as _ct
                import pywinctl as pwc
                if sys.platform == "win32":
                    hwnd = _ct.windll.user32.GetForegroundWindow()
                    pid = ctypes.c_ulong(0)
                    _ct.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    fg_proc = psutil.Process(pid.value)
                    snap.foreground_process = fg_proc.name().lower()
                    
                    win = pwc.Window(hwnd)
                    if win:
                        snap.window_title = win.title
                    
                    snap.foreground_activity = _FOREGROUND_APP_MAP.get(snap.foreground_process)
            except Exception:
                pass

            # Background secondary activities
            seen_labels: Set[str] = set()
            for pname in running_names:
                label = _BACKGROUND_APP_MAP.get(pname)
                if label and label not in seen_labels:
                    if label != snap.foreground_activity:
                        seen_labels.add(label)
                        snap.background_activities.append(label)
                        
            # Refined Idle Logic:
            # ONLY true if screen locked OR (no input AND no passive media AND no controller AND no system load)
            raw_afk = snap.idle_seconds >= self._idle_threshold
            
            # System load check (prevent idle while rendering/building)
            is_system_busy = snap.cpu_percent > 85 or snap.gpu_percent > 15
            
            if snap.screen_locked:
                snap.is_idle = True
            elif raw_afk and not snap.controller_active and not snap.media_playing and not is_system_busy:
                snap.is_idle = True
            else:
                snap.is_idle = False

        except Exception as exc:
            logger.debug("Process scan error: %s", exc)

        return snap


# ---------------------------------------------------------------------------
# Module-level singleton (created in classifier.py)
# ---------------------------------------------------------------------------
_collector: Optional[BehavioralCollector] = None


def get_collector(poll_interval: float = 1.0, idle_threshold: float = 60.0) -> BehavioralCollector:
    """Return (and auto-start) the module-level singleton collector."""
    global _collector
    if _collector is None:
        _collector = BehavioralCollector(poll_interval, idle_threshold)
        _collector.start()
    return _collector

