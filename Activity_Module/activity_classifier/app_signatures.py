"""
App Signatures Database — Application-Aware Activity Classification
===================================================================

Three data structures that power granular label detection:

  PROCESS_SIGNATURE_DB  — process name → (app_name, base_label, sub_activities[])
  DOMAIN_CATEGORY_MAP   — domain fragment → specific activity label
  WINDOW_TITLE_PARSERS  — per-app compiled regex patterns for context extraction

Zero runtime overhead (no ML, no I/O — pure dict/regex lookups).
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
# AppSignature: (app_display_name, base_label, [possible_sub_activities])
AppSignature = Tuple[str, str, List[str]]


# ===========================================================================
# 1. PROCESS SIGNATURE DATABASE
#    Key: lowercase process name (no path)
#    Value: (app_display_name, base_label, [possible sub-activities])
# ===========================================================================
PROCESS_SIGNATURE_DB: Dict[str, AppSignature] = {

    # ── IDEs / Code Editors ─────────────────────────────────────────────────
    "code.exe":             ("VS Code",        "Development - VS Code",          ["Active Coding", "Debugging", "Code Review", "Reading Code"]),
    "code":             ("VS Code",        "Development - VS Code",          ["Active Coding", "Debugging", "Code Review", "Reading Code"]),
    "cursor.exe":             ("Cursor",        "Work - VS Code",          ["Active Coding", "AI Assist", "Debugging"]),
    "pycharm64.exe":             ("PyCharm",        "Development - PyCharm",          ["Active Coding", "Debugging", "Testing"]),
    "idea64.exe":             ("IntelliJ IDEA",        "Development - IntelliJ IDEA",          ["Active Coding", "Debugging", "Refactoring"]),
    "webstorm64.exe":             ("WebStorm",        "Development - WebStorm",          ["Active Coding", "Debugging"]),
    "rider64.exe":             ("Rider",        "Development - Rider",          ["Active Coding", "Debugging"]),
    "clion64.exe":             ("CLion",        "Development - CLion",          ["Active Coding", "Debugging"]),
    "phpstorm64.exe":             ("PhpStorm",        "Development - PhpStorm",          ["Active Coding", "Debugging"]),
    "goland64.exe":             ("GoLand",        "Development - GoLand",          ["Active Coding", "Debugging"]),
    "datagrip64.exe":             ("DataGrip",        "Development - DataGrip",          ["Database Query", "Schema Design"]),
    "sublime_text.exe":             ("Sublime Text",        "Development - Sublime Text",          ["Editing", "Note Taking"]),
    "notepad++.exe":             ("Notepad++",        "Utilities - Notepad++",          ["Text Editing", "Code Viewing"]),
    "zed.exe":             ("Zed",        "Development - Zed",          ["Active Coding", "Collaboration"]),
    "vim.exe":             ("Vim",        "Development - Vim",          ["Active Coding"]),
    "nvim.exe":             ("Neovim",        "Development - Neovim",          ["Active Coding"]),
    "atom.exe":             ("Atom",        "Development - Atom",          ["Active Coding"]),
    "eclipse.exe":             ("Eclipse",        "Development - Eclipse",          ["Active Coding", "Debugging"]),
    "devenv.exe":             ("Visual Studio",        "Work - VS Code",          ["Active Coding", "Debugging", "Profiling"]),

    # ── Terminals / Shells ──────────────────────────────────────────────────
    "cmd.exe":             ("Command Prompt",        "Work - Terminal",          ["Running Commands", "Scripting"]),
    "powershell.exe":             ("PowerShell",        "System - PowerShell",          ["Scripting", "System Administration"]),
    "pwsh.exe":             ("PowerShell 7",        "System - PowerShell 7",          ["Scripting", "System Administration"]),
    "wt.exe":             ("Windows Terminal",        "System - Windows Terminal",          ["Running Commands", "Scripting", "SSH"]),
    "windowsterminal.exe":             ("Windows Terminal",        "System - Windows Terminal",          ["Running Commands", "Scripting"]),
    "conhost.exe":             ("Console Host",        "Work - Terminal",          ["Running Commands", "Scripting"]),
    "openconsole.exe":             ("OpenConsole",        "Work - Terminal",          ["Running Commands", "Scripting"]),
    "git-bash.exe":             ("Git Bash",        "Work - Terminal",          ["Git Operations", "Scripting"]),
    "bash.exe":             ("Bash",        "Work - Terminal",          ["Running Commands"]),
    "python.exe":             ("Python",        "Work - VS Code",          ["Script Execution", "REPL"]),
    "python3.exe":             ("Python 3",        "Work - VS Code",          ["Script Execution"]),
    "node.exe":             ("Node.js",        "Work - VS Code",          ["Script Execution", "Server"]),

    # ── Browsers ────────────────────────────────────────────────────────────
    "chrome.exe":             ("Chrome",        "Browsing - Chrome",          ["Web Browsing"]),
    "msedge.exe":             ("Edge",        "Browsing - Edge",          ["Web Browsing"]),
    "firefox.exe":             ("Firefox",        "Browsing - Firefox",          ["Web Browsing"]),
    "brave.exe":             ("Brave",        "Browsing - Brave",          ["Web Browsing", "Crypto"]),
    "opera.exe":             ("Opera",        "Browsing - Opera",          ["Web Browsing"]),
    "vivaldi.exe":             ("Vivaldi",        "Browsing - Vivaldi",          ["Web Browsing"]),
    "arc.exe":             ("Arc",        "Browsing - Arc",          ["Web Browsing"]),

    # ── Office / Productivity ────────────────────────────────────────────────
    "winword.exe":             ("Microsoft Word",        "Work - Microsoft Word",          ["Document Writing", "Editing", "Review"]),
    "excel.exe":             ("Microsoft Excel",        "Work - Microsoft Excel",          ["Data Entry", "Data Analysis", "Financial Modeling"]),
    "powerpnt.exe":             ("PowerPoint",        "Work - PowerPoint",          ["Creating Slides", "Editing"]),
    "onenote.exe":             ("OneNote",        "Work - OneNote",          ["Note Taking", "Meeting Notes"]),
    "outlook.exe":             ("Outlook",        "Work - Outlook",          ["Reading Email", "Composing Email", "Calendar"]),
    "soffice.exe":             ("LibreOffice",        "Work - Microsoft Word",          ["Document Writing", "Spreadsheet"]),
    "acrobat.exe":             ("Adobe Acrobat",        "Work - Microsoft Word",          ["PDF Editing", "Annotation"]),
    "acrord32.exe":             ("Acrobat Reader",        "Research - arXiv",          ["Reading Document", "Research"]),
    "foxit reader.exe":             ("Foxit Reader",        "Research - arXiv",          ["Reading Document"]),
    "sumatrapdf.exe":             ("SumatraPDF",        "Research - arXiv",          ["Reading Document"]),
    "obsidian.exe":             ("Obsidian",        "Work - Notion",          ["Note Taking", "Knowledge Base", "Writing"]),
    "notion.exe":             ("Notion",        "Work - Notion",          ["Note Taking", "Project Management", "Docs"]),

    # ── Communication ────────────────────────────────────────────────────────
    "discord.exe":             ("Discord",        "Communication - Discord",          ["Text Chat", "Voice Chat", "Screen Share"]),
    "discord":             ("Discord",        "Communication - Discord",          ["Text Chat", "Voice Chat"]),
    "slack.exe":             ("Slack",        "Communication - Slack",          ["Messaging", "Huddle"]),
    "slack":             ("Slack",        "Communication - Slack",          ["Messaging"]),
    "teams.exe":             ("Microsoft Teams",        "Communication - Microsoft Teams",          ["Video Call", "Chat", "Screen Share"]),
    "ms-teams.exe":             ("Microsoft Teams",        "Communication - Microsoft Teams",          ["Video Call", "Chat"]),
    "zoom.exe":             ("Zoom",        "Communication - Zoom",          ["Video Call", "Webinar", "Screen Share"]),
    "skype.exe":             ("Skype",        "Communication - Skype",          ["Video Call", "Voice Call", "Messaging"]),
    "telegram.exe":             ("Telegram",        "Communication - Telegram",          ["Messaging", "Channels"]),
    "whatsapp.exe":             ("WhatsApp",        "Communication - WhatsApp",          ["Messaging", "Voice Call"]),
    "signal.exe":             ("Signal",        "Communication - Signal",          ["Messaging", "Secure Chat"]),
    "thunderbird.exe":             ("Thunderbird",        "Work - Outlook",          ["Reading Email", "Composing Email"]),

    # ── Jupyter / Data Science ──────────────────────────────────────────────
    "jupyter-lab.exe":             ("JupyterLab",        "Work - Jupyter Notebook",          ["Data Analysis", "ML Notebook", "Visualization"]),
    "jupyter.exe":             ("Jupyter",        "Work - Jupyter Notebook",          ["Data Analysis", "ML Notebook"]),

    # ── Creative Tools ───────────────────────────────────────────────────────
    "photoshop.exe":             ("Photoshop",        "Creative - Photoshop",          ["Image Editing", "Photo Retouching", "Design"]),
    "illustrator.exe":             ("Illustrator",        "Creative - Illustrator",          ["Vector Design", "Logo Design"]),
    "gimp.exe":             ("GIMP",        "Creative - Photoshop",          ["Image Editing"]),
    "inkscape.exe":             ("Inkscape",        "Creative - Photoshop",          ["Vector Design"]),
    "figma.exe":             ("Figma",        "Creative - Figma",          ["UI Design", "Prototyping", "Design Review"]),
    "blender.exe":             ("Blender",        "Creative - Blender",          ["3D Modeling", "Rendering", "Animation"]),
    "blender":             ("Blender",        "Creative - Blender",          ["3D Modeling", "Rendering"]),
    "premiere pro.exe":             ("Premiere Pro",        "Creative - Premiere Pro",          ["Video Editing", "Color Grading"]),
    "afterfx.exe":             ("After Effects",        "Creative - Premiere Pro",          ["Motion Graphics", "VFX"]),
    "davinciresolve.exe":             ("DaVinci Resolve",        "Creative - DaVinci Resolve",          ["Video Editing", "Color Grading", "Rendering"]),
    "kdenlive.exe":             ("Kdenlive",        "Creative - Premiere Pro",          ["Video Editing"]),
    "audacity.exe":             ("Audacity",        "Creative - FL Studio",          ["Audio Editing", "Recording", "Podcast"]),
    "fl studio.exe":             ("FL Studio",        "Creative - FL Studio",          ["Music Production", "Beat Making"]),
    "ableton live.exe":             ("Ableton Live",        "Creative - FL Studio",          ["Music Production", "Live Performance"]),
    "lmms.exe":             ("LMMS",        "Creative - FL Studio",          ["Music Production"]),
    "obs64.exe":             ("OBS Studio",        "Entertainment - Twitch",          ["Live Streaming", "Screen Recording"]),
    "obs32.exe":             ("OBS Studio",        "Entertainment - Twitch",          ["Live Streaming"]),

    # ── Media Players ────────────────────────────────────────────────────────
    "vlc.exe":             ("VLC",        "Media - VLC",          ["Watching Video", "Watching Movie"]),
    "mpv.exe":             ("mpv",        "Entertainment - Netflix",          ["Watching Video"]),
    "mpc-hc64.exe":             ("MPC-HC",        "Entertainment - Netflix",          ["Watching Video"]),
    "wmplayer.exe":             ("Windows Media Player",        "Entertainment - Spotify",          ["Watching Video", "Listening Music"]),
    "spotify.exe":          ("Spotify",         "Entertainment - Spotify",""),  # active foreground  # noqa

    # ── Games / Game Launchers ────────────────────────────────────────────────
    "anti-gravity.exe":     ("Anti-Gravity",    "Entertainment - Anti-Gravity", ["Visualization", "Gaming"]),
    "steam.exe":             ("Steam",        "Gaming - Steam",          ["Browsing Library", "Downloading", "Playing Game"]),
    "epicgameslauncher.exe":             ("Epic Games",        "Gaming - Epic Games",          ["Browsing Library", "Downloading"]),
    "riotclientservices.exe":             ("Riot Client",        "Gaming - Riot Client",          ["Launching Game"]),
    "battlenet.exe":             ("Battle.net",        "Gaming - Battle.net",          ["Browsing Library"]),
    "gog galaxy.exe":             ("GOG Galaxy",        "Gaming - GOG Galaxy",          ["Browsing Library"]),

    # ── System Tools ─────────────────────────────────────────────────────────
    "taskmgr.exe":             ("Task Manager",        "System - Task Manager",          ["Performance Monitoring", "Ending Process"]),
    "procexp64.exe":             ("Process Explorer",        "System - Process Explorer",          ["Performance Monitoring"]),
    "procexp.exe":             ("Process Explorer",        "System - Process Explorer",          ["Performance Monitoring"]),
    "perfmon.exe":             ("Performance Monitor",        "Browsing - Performance Monitor",          ["CPU Monitoring", "Memory Analysis"]),
    "regedit.exe":             ("Registry Editor",        "System - Registry Editor",          ["System Configuration"]),
    "mmc.exe":             ("MMC",        "System - Settings",          ["System Administration"]),
    "explorer.exe":             ("File Explorer",        "System - File Explorer",          ["File Browsing", "File Transfer", "File Organization"]),
    "msiexec.exe":             ("Installer",        "System - Settings",          ["Software Installation"]),
    "winrar.exe":             ("WinRAR",        "System - File Explorer",          ["Archiving", "Extracting"]),
    "7zfm.exe":             ("7-Zip",        "System - File Explorer",          ["Archiving", "Extracting"]),
    "control.exe":             ("Control Panel",        "System - Control Panel",          ["System Configuration"]),
    "msconfig.exe":             ("System Config",        "System - Settings",          ["Startup Management"]),
    "diskmgmt.msc":             ("Disk Management",        "System - Settings",          ["Partition Management"]),
    "dfrgui.exe":             ("Defragmenter",        "System - Disk Cleanup",          ["Disk Optimization"]),
    "cleanmgr.exe":             ("Disk Cleanup",        "System - Disk Cleanup",          ["Disk Cleanup"]),
    "taskschd.msc":             ("Task Scheduler",        "System - Task Manager",          ["Task Automation"]),
    "eventvwr.exe":             ("Event Viewer",        "System - Event Viewer",          ["Log Analysis"]),
    "devmgmt.msc":             ("Device Manager",        "System - Settings",          ["Driver Management"]),
    "gpedit.msc":             ("Group Policy",        "System - Settings",          ["Policy Configuration"]),
    "snippingtool.exe":             ("Snipping Tool",        "System - Snipping Tool",          ["Screenshot"]),
    "snipandsketchwm.exe":             ("Snip & Sketch",        "System - Snip & Sketch",          ["Screenshot", "Annotation"]),
    "screensketch.exe":             ("Snip & Sketch",        "System - Snip & Sketch",          ["Screenshot"]),
    "dxdiag.exe":             ("DirectX Diag",        "System - Settings",          ["Hardware Info"]),
    "chkdsk.exe":             ("Check Disk",        "System - Settings",          ["Disk Repair"]),
    "sfc.exe":             ("System File Checker",        "System - Settings",          ["System Repair"]),
    "powercfg.exe":             ("Power Config",        "System - Settings",          ["Battery Management"]),

    # ── Windows Built-in Apps ─────────────────────────────────────────────────
    "winstore.app.exe":             ("Microsoft Store",        "Browsing - Microsoft Store",          ["App Browsing", "App Download", "Updates"]),
    "ms-windows-store.exe":             ("Microsoft Store",        "Browsing - Microsoft Store",          ["App Browsing"]),
    "microsoftstore.exe":             ("Microsoft Store",        "Browsing - Microsoft Store",          ["App Browsing"]),
    "systemsettings.exe":             ("Windows Settings",        "System - Settings",          ["Display", "Network", "Privacy", "Update"]),
    "windowssettings.exe":             ("Windows Settings",        "System - Settings",          ["System Configuration"]),
    "ms-settings.exe":             ("Windows Settings",        "System - Settings",          ["System Configuration"]),
    "calculatorapp.exe":             ("Calculator",        "System - Settings",          ["Calculation", "Converter"]),
    "calculator.exe":             ("Calculator",        "System - Settings",          ["Calculation"]),
    "notepad.exe":             ("Notepad",        "Utilities - Notepad",          ["Text Editing", "Quick Notes"]),
    "notepad2.exe":             ("Notepad2",        "Utilities - Notepad2",          ["Text Editing"]),
    "wordpad.exe":             ("WordPad",        "Work - WordPad",          ["Document Writing"]),
    "mspaint.exe":             ("Paint",        "Creative - Photoshop",          ["Drawing", "Image Editing"]),
    "paint.exe":             ("Paint 3D",        "Creative - Blender",          ["3D Drawing", "Design"]),
    "photos.exe":             ("Windows Photos",        "Creative - Photoshop",          ["Viewing Photos", "Editing Photos"]),
    "microsoft.photos.exe":             ("Windows Photos",        "Creative - Photoshop",          ["Viewing Photos"]),
    "windowscamera.exe":             ("Camera",        "Creative - Photoshop",          ["Photo Capture", "Video Capture"]),
    "windowsmaps.exe":             ("Maps",        "Information - Wikipedia",          ["Navigation", "Directions"]),
    "windowsalarms.exe":             ("Alarms & Clock",        "Utilities - Alarms & Clock",          ["Timer", "Alarm", "Worldclock"]),
    "windowscalculator.exe":             ("Calculator",        "System - Settings",          ["Math", "Converter"]),
    "windowsstore.exe":             ("Microsoft Store",        "Browsing - Microsoft Store",          ["App Browsing"]),
    "lockapp.exe":             ("Lock Screen",        "Idle - Locked Screen",          ["Locked"]),
    "logonui.exe":             ("Login Screen",        "Idle - Locked Screen",          ["Authentication"]),
    "winlogon.exe":             ("Windows Logon",        "Idle - Locked Screen",          ["Authentication"]),
    "dwm.exe":             ("Desktop Manager",        "Idle - System Idle",          ["Idle"]),
    "shellexperiencehost.exe":             ("Start Menu",        "System - File Explorer",          ["App Launch"]),
    "startmenuexperiencehost.exe":             ("Start Menu",        "System - File Explorer",          ["App Launch"]),
    "searchhost.exe":             ("Windows Search",        "Browsing - Windows Search",          ["Searching"]),
    "searchui.exe":             ("Windows Search",        "Browsing - Windows Search",          ["Searching"]),
    "cortana.exe":             ("Cortana",        "Information - Wikipedia",          ["Voice Search", "Tasks"]),
    "widgets.exe":             ("Windows Widgets",        "Information - Wikipedia",          ["News", "Weather", "Calendar"]),
    "microsoftedgecp.exe":             ("Edge",        "Browsing - Edge",          ["Web Browsing"]),
    "msedgewebview2.exe":             ("WebView2",        "Information - Wikipedia",          ["Embedded Browser"]),
    "mail.exe":             ("Windows Mail",        "Communication - Telegram",          ["Reading Email", "Composing Email"]),
    "hxoutlook.exe":             ("Windows Mail",        "Communication - Telegram",          ["Reading Email"]),
    "hxcalendarappimm.exe":             ("Calendar",        "Utilities - Calendar",          ["Scheduling", "Events"]),
    "people.exe":             ("People App",        "Communication - Telegram",          ["Contacts"]),
    "windows.immersivecontrolpanel.exe":             ("Settings",        "System - Settings",          ["Configuration"]),
    "xbox.exe":             ("Xbox App",        "Gaming - Xbox App",          ["Game Library", "Game Pass"]),
    "xboxapp.exe":             ("Xbox App",        "Gaming - Xbox App",          ["Game Library"]),
    "microsoftgameapp.exe":             ("Xbox Game Bar",        "Gaming - Xbox Game Bar",          ["Performance Overlay"]),
    "gamebar.exe":             ("Game Bar",        "Entertainment - Steam Gaming",          ["Game Recording"]),
    "xboxgamemonitorapp.exe":             ("Xbox Game Bar",        "Gaming - Xbox Game Bar",          ["Overlay"]),
    "groove.exe":             ("Groove Music",        "Media - Groove Music",          ["Music Listening"]),
    "zunemusic.exe":             ("Groove Music",        "Media - Groove Music",          ["Music Listening"]),
    "zunevideo.exe":             ("Movies & TV",        "Unknown - Unknown App",          ["Watching Movie", "Watching TV"]),
    "video.ui.exe":             ("Movies & TV",        "Unknown - Unknown App",          ["Watching Movie"]),
    "microsoftvideo.exe":             ("Movies & TV",        "Unknown - Unknown App",          ["Watching Movie"]),
    "solitaire.exe":             ("Microsoft Solitaire",        "Entertainment - Steam Gaming",          ["Card Game"]),
    "microsoftsolitaire.exe":             ("Solitaire",        "Entertainment - Steam Gaming",          ["Card Game"]),
    "metatrader4.exe":             ("MetaTrader 4",        "Financial - TradingView",          ["Trading"]),
    "terminal.exe":             ("MetaTrader 4",        "Financial - TradingView",          ["Trading"]),
    "metatrader5.exe":             ("MetaTrader 5",        "Financial - TradingView",          ["Trading"]),
    "terminal64.exe":             ("MetaTrader 5",        "Financial - TradingView",          ["Trading"]),
    "binance.exe":             ("Binance",        "Financial - TradingView",          ["Crypto"]),
    "tradingview.exe":             ("TradingView",        "Financial - TradingView",          ["Charts"]),
    "exness.exe":             ("Exness",        "Financial - TradingView",          ["Forex"]),
    "octafx.exe":             ("OctaFX",        "Financial - TradingView",          ["Forex"]),
    "minecraftlauncher.exe":             ("Minecraft",        "Gaming - Minecraft",          ["Playing Game"]),
    "minecraft.exe":             ("Minecraft",        "Gaming - Minecraft",          ["Playing Game"]),
    "feedback.exe":             ("Feedback Hub",        "System - Settings",          ["Bug Reporting"]),
    "microsofttranslator.exe":             ("Translator",        "Browsing - Translator",          ["Translation"]),
    "windows.media.player.exe":             ("Media Player",        "Entertainment - Netflix",          ["Watching Video"]),

    # ── Finance / Trading ─────────────────────────────────────────────────────
    "mt4.exe":             ("MetaTrader 4",        "Financial - TradingView",          ["Forex Trading", "Chart Analysis"]),
    "mt5.exe":             ("MetaTrader 5",        "Financial - TradingView",          ["Trading", "Chart Analysis"]),
    "thinkorswim.exe":             ("thinkorswim",        "Financial - TradingView",          ["Stock Trading", "Options Analysis"]),
    "ninjatrader.exe":             ("NinjaTrader",        "Financial - TradingView",          ["Futures Trading", "Chart Analysis"]),
    "tradingview.exe":             ("TradingView",        "Financial - TradingView",          ["Chart Analysis", "Market Watch"]),
    "quicken.exe":             ("Quicken",        "Financial - QuickBooks",          ["Budgeting", "Expense Tracking"]),

    # ── Downloads ─────────────────────────────────────────────────────────────
    "qbittorrent.exe":             ("qBittorrent",        "Browsing - qBittorrent",          ["Downloading"]),
    "utorrent.exe":             ("µTorrent",        "Browsing - µTorrent",          ["Downloading"]),
    "internetdownloadmanager.exe":             ("IDM",        "Background - Downloading",          ["Downloading"]),
    "idman.exe":             ("IDM",        "Background - Downloading",          ["Downloading"]),
    "wget.exe":             ("Wget",        "Background - Downloading",          ["CLI Download"]),
    "aria2c.exe":             ("aria2",        "Background - Downloading",          ["CLI Download"]),
    "jdownloader.exe":             ("JDownloader",        "Background - Downloading",          ["Downloading"]),

    # ── Version Control ───────────────────────────────────────────────────────
    "githubdesktop.exe":             ("GitHub Desktop",        "Unknown - Unknown App",          ["Code Review", "Committing", "Pull Request"]),
    "sourcetree.exe":             ("Sourcetree",        "Unknown - Unknown App",          ["Code Review", "Git Operations"]),
    "gitkraken.exe":             ("GitKraken",        "Unknown - Unknown App",          ["Code Review", "Git Operations"]),
    "fork.exe":             ("Fork",        "Unknown - Unknown App",          ["Git Operations", "Code Review"]),
    "smartgit.exe":             ("SmartGit",        "Unknown - Unknown App",          ["Git Operations"]),

    # ── Database / API Tools ───────────────────────────────────────────────────
    "dbeaver.exe":             ("DBeaver",        "Unknown - Unknown App",          ["Database Query", "Schema Design"]),
    "tableplus.exe":             ("TablePlus",        "Unknown - Unknown App",          ["Database Query"]),
    "postman.exe":             ("Postman",        "Unknown - Unknown App",          ["API Testing", "API Design"]),
    "insomnia.exe":             ("Insomnia",        "Unknown - Unknown App",          ["API Testing"]),
    "heidisql.exe":             ("HeidiSQL",        "Unknown - Unknown App",          ["Database Query"]),
    "mongodbcompass.exe":             ("MongoDB Compass",        "Unknown - Unknown App",          ["Database Query", "Schema Design"]),
    "robo3t.exe":             ("Robo 3T",        "Unknown - Unknown App",          ["Database Query"]),
    "sqldeveloper64w.exe":             ("SQL Developer",        "Unknown - Unknown App",          ["Database Query", "PL/SQL"]),
    "ssms.exe":             ("SQL Server MGMT",        "Unknown - Unknown App",          ["Database Administration"]),

    # ── Note Taking ────────────────────────────────────────────────────────────
    "logseq.exe":             ("Logseq",        "Work - Notion",          ["Note Taking", "Knowledge Base"]),
    "roamresearch":             ("Roam Research",        "Browsing - Roam Research",          ["Note Taking"]),
    "zettlr.exe":             ("Zettlr",        "Work - Microsoft Word",          ["Academic Writing", "Research Notes"]),
    "anki.exe":             ("Anki",        "Learning - Coursera",          ["Reviewing Flashcards", "Studying"]),
    "typora.exe":             ("Typora",        "Work - Notion",          ["Markdown Writing", "Note Taking"]),
    "marktext.exe":             ("Mark Text",        "Work - Notion",          ["Markdown Writing"]),
    "ghostwriter.exe":             ("Ghostwriter",        "Work - Notion",          ["Markdown Writing"]),
    "simplenote.exe":             ("Simplenote",        "Work - Notion",          ["Note Taking"]),
    "standardnotes.exe":             ("Standard Notes",        "Work - Notion",          ["Note Taking", "Encrypted Notes"]),
    "bear.exe":             ("Bear",        "Work - Notion",          ["Note Taking"]),
    "evernote.exe":             ("Evernote",        "Work - Notion",          ["Note Taking", "Clipping"]),
    "joplin.exe":             ("Joplin",        "Work - Notion",          ["Note Taking", "Encrypted Notes"]),

    # ── Virtual Machines / Remote ─────────────────────────────────────────────
    "vmware.exe":             ("VMware",        "Virtual - VMware",          ["Virtual Machine"]),
    "vmwareworkstation.exe":             ("VMware Workstation",        "Virtual - VMware Workstation",          ["Virtual Machine"]),
    "virtualboxvm.exe":             ("VirtualBox",        "Virtual - VirtualBox",          ["Virtual Machine"]),
    "virtualbox.exe":             ("VirtualBox",        "Virtual - VirtualBox",          ["Virtual Machine"]),
    "hyperv.exe":             ("Hyper-V",        "Virtual - Hyper-V",          ["Virtual Machine"]),
    "mstsc.exe":             ("Remote Desktop",        "System - Settings",          ["Remote Access"]),
    "vnc.exe":             ("VNC Viewer",        "System - Settings",          ["Remote Access"]),
    "vncviewer.exe":             ("VNC Viewer",        "System - Settings",          ["Remote Access"]),
    "anydesk.exe":             ("AnyDesk",        "System - Settings",          ["Remote Support"]),
    "teamviewer.exe":             ("TeamViewer",        "System - Settings",          ["Remote Support"]),
    "wsl.exe":             ("WSL",        "Virtual - WSL",          ["Linux Terminal", "Development"]),
    "ubuntu.exe":             ("Ubuntu (WSL)",        "Virtual - Ubuntu (WSL)",          ["Linux Terminal"]),
    "debian.exe":             ("Debian (WSL)",        "Virtual - Debian (WSL)",          ["Linux Terminal"]),
    "kali.exe":             ("Kali Linux (WSL)",        "Virtual - Kali Linux (WSL)",          ["Security Tools", "Linux Terminal"]),

    # ── Security & VPN ────────────────────────────────────────────────────────
    "nordvpn.exe":             ("NordVPN",        "System - Settings",          ["VPN Connection"]),
    "expressvpn.exe":             ("ExpressVPN",        "System - Settings",          ["VPN Connection"]),
    "protonvpn.exe":             ("ProtonVPN",        "System - Settings",          ["VPN Connection"]),
    "surfshark.exe":             ("Surfshark",        "System - Settings",          ["VPN Connection"]),
    "mullvad.exe":             ("Mullvad VPN",        "System - Settings",          ["VPN Connection"]),
    "openvpn.exe":             ("OpenVPN",        "System - Settings",          ["VPN Connection"]),
    "wireguard.exe":             ("WireGuard",        "System - Settings",          ["VPN Connection"]),
    "bitwarden.exe":             ("Bitwarden",        "System - Settings",          ["Password Management"]),
    "keepass.exe":             ("KeePass",        "System - Settings",          ["Password Management"]),
    "1password.exe":             ("1Password",        "Work - 1Password",          ["Password Management"]),
    "lastpass.exe":             ("LastPass",        "System - Settings",          ["Password Management"]),
    "malwarebytes.exe":             ("Malwarebytes",        "System - Settings",          ["Malware Scan"]),
    "msmpeng.exe":             ("Windows Defender",        "System - Settings",          ["Security Scan"]),
    "wireshark.exe":             ("Wireshark",        "Unknown - Unknown App",          ["Network Analysis", "Packet Capture"]),
    "putty.exe":             ("PuTTY",        "Unknown - Unknown App",          ["SSH Session", "Remote Access"]),
    "winscp.exe":             ("WinSCP",        "Unknown - Unknown App",          ["File Transfer", "SSH"]),
    "filezilla.exe":             ("FileZilla",        "Unknown - Unknown App",          ["File Transfer", "FTP"]),
    "mobaxterm.exe":             ("MobaXterm",        "Unknown - Unknown App",          ["SSH Session", "Remote Desktop"]),
    "nmap.exe":             ("Nmap",        "Unknown - Unknown App",          ["Network Scanning"]),
    "hashcat.exe":             ("Hashcat",        "Unknown - Unknown App",          ["Security Testing"]),
    "burpsuite.exe":             ("Burp Suite",        "Unknown - Unknown App",          ["Security Testing", "Web Pentesting"]),

    # ── Screen Recording / Streaming ──────────────────────────────────────────
    "obs64.exe":             ("OBS Studio",        "Entertainment - Twitch",          ["Live Streaming", "Screen Recording"]),
    "obs32.exe":             ("OBS Studio",        "Entertainment - Twitch",          ["Live Streaming"]),
    "obs.exe":             ("OBS Studio",        "Entertainment - Twitch",          ["Screen Recording"]),
    "bandicam.exe":             ("Bandicam",        "Creative - Photoshop",          ["Screen Recording", "Game Recording"]),
    "fraps.exe":             ("FRAPS",        "Creative - Photoshop",          ["Game Recording"]),
    "shadowplay.exe":             ("ShadowPlay",        "Unknown - Unknown App",          ["Game Recording"]),
    "xsplit.exe":             ("XSplit",        "Creative - Photoshop",          ["Live Streaming"]),
    "loom.exe":             ("Loom",        "Communication - Telegram",          ["Screen Recording", "Video Message"]),
    "clipchamp.exe":             ("Clipchamp",        "Creative - Premiere Pro",          ["Video Editing"]),

    # ── Media & Entertainment ─────────────────────────────────────────────────
    "plex.exe":             ("Plex",        "Unknown - Unknown App",          ["Watching Movie", "Watching TV"]),
    "plexmediaplayer.exe":             ("Plex Player",        "Unknown - Unknown App",          ["Watching Movie"]),
    "kodi.exe":             ("Kodi",        "Unknown - Unknown App",          ["Watching Movie", "Watching TV"]),
    "emby.exe":             ("Emby",        "Unknown - Unknown App",          ["Watching Movie"]),
    "jellyfin.exe":             ("Jellyfin",        "Unknown - Unknown App",          ["Watching Movie", "Watching TV"]),
    "mpc-hc.exe":             ("MPC-HC",        "Unknown - Unknown App",          ["Watching Video"]),
    "mpc-be.exe":             ("MPC-BE",        "Unknown - Unknown App",          ["Watching Video"]),
    "potplayer.exe":             ("PotPlayer",        "Media - PotPlayer",          ["Watching Video"]),
    "netflix.exe":             ("Netflix",        "Unknown - Unknown App",          ["Watching Movie", "Watching TV Show"]),
    "disneyplus.exe":             ("Disney+",        "Unknown - Unknown App",          ["Watching Movie"]),
    "primevideo.exe":             ("Prime Video",        "Unknown - Unknown App",          ["Watching Movie"]),
    "twitch.exe":             ("Twitch",        "Unknown - Unknown App",          ["Watching Stream"]),
    "amazonmusic.exe":             ("Amazon Music",        "Media - Amazon Music",          ["Music Listening"]),
    "applemusic.exe":             ("Apple Music",        "Media - Apple Music",          ["Music Listening"]),
    "itunes.exe":             ("iTunes",        "Media - iTunes",          ["Music Listening", "Podcast"]),
    "tidal.exe":             ("Tidal",        "Media - Tidal",          ["Music Listening"]),
    "deezer.exe":             ("Deezer",        "Media - Deezer",          ["Music Listening"]),
    "aimp.exe":             ("AIMP",        "Media - AIMP",          ["Music Listening"]),
    "foobar2000.exe":             ("foobar2000",        "Unknown - Unknown App",          ["Music Listening"]),
    "musicbee.exe":             ("MusicBee",        "Media - MusicBee",          ["Music Listening"]),

    # ── Image Viewers / Photo Editing ─────────────────────────────────────────
    "irfanview.exe":             ("IrfanView",        "Creative - Photoshop",          ["Viewing Images"]),
    "xnviewmp.exe":             ("XnView",        "Creative - Photoshop",          ["Viewing Images"]),
    "faststone.exe":             ("FastStone",        "Creative - Photoshop",          ["Viewing Images", "Image Editing"]),
    "jpegview.exe":             ("JPEGView",        "Creative - Photoshop",          ["Viewing Images"]),
    "imagemagick.exe":             ("ImageMagick",        "Creative - Photoshop",          ["Image Processing"]),
    "rawtherapee.exe":             ("RawTherapee",        "Creative - Photoshop",          ["Photo Editing", "RAW Processing"]),
    "darktable.exe":             ("darktable",        "Creative - Photoshop",          ["Photo Editing"]),
    "capture1.exe":             ("Capture One",        "Creative - Photoshop",          ["Photo Editing", "RAW Processing"]),
    "lightroom.exe":             ("Lightroom",        "Creative - Photoshop",          ["Photo Editing", "Photo Management"]),
    "lightroomclassic.exe":             ("Lightroom Classic",        "Creative - Photoshop",          ["Photo Editing"]),

    # ── 3D / CAD ─────────────────────────────────────────────────────────────
    "autocad.exe":             ("AutoCAD",        "Creative - AutoCAD",          ["2D Drawing", "Technical Drawing"]),
    "acad.exe":             ("AutoCAD",        "Creative - AutoCAD",          ["2D Drawing"]),
    "fusion360.exe":             ("Fusion 360",        "Creative - Blender",          ["3D Modeling", "CAD Design"]),
    "sketchup.exe":             ("SketchUp",        "Creative - Blender",          ["3D Modeling"]),
    "cinema4d.exe":             ("Cinema 4D",        "Creative - Blender",          ["3D Modeling", "Motion Graphics"]),
    "houdini.exe":             ("Houdini",        "Creative - Blender",          ["VFX", "3D Simulation"]),
    "maya.exe":             ("Maya",        "Creative - Maya",          ["3D Modeling", "Animation"]),
    "3dsmax.exe":             ("3ds Max",        "Creative - Blender",          ["3D Modeling", "Rendering"]),
    "zbrush.exe":             ("ZBrush",        "Creative - Blender",          ["3D Sculpting"]),
    "substancepainter.exe":             ("Substance Painter",        "Creative - Photoshop",          ["3D Texturing"]),
    "unreal.exe":             ("Unreal Engine",        "Unknown - Unknown App",          ["Game Development", "3D Rendering"]),
    "unity.exe":             ("Unity",        "Creative - Unity",          ["Game Development", "3D Scene"]),
    "unrealengine.exe":             ("Unreal Engine",        "Unknown - Unknown App",          ["Game Development"]),
    "godot.exe":             ("Godot Engine",        "Unknown - Unknown App",          ["Game Development"]),
    "gamemaker.exe":             ("GameMaker",        "Unknown - Unknown App",          ["Game Development"]),
    "rpgmaker.exe":             ("RPG Maker",        "Unknown - Unknown App",          ["Game Development"]),

    # ── E-Readers / Books ─────────────────────────────────────────────────────
    "kindle.exe":             ("Kindle",        "Learning - Coursera",          ["Reading Book", "Reading"]),
    "calibre.exe":             ("Calibre",        "Learning - Coursera",          ["Book Management", "Reading"]),
    "bookviser.exe":             ("Bookviser",        "Learning - Coursera",          ["Reading Book"]),
    "kobo.exe":             ("Kobo",        "Learning - Coursera",          ["Reading Book"]),

    # ── Communication — Extra ──────────────────────────────────────────────────
    "viber.exe":             ("Viber",        "Communication - Viber",          ["Messaging", "Voice Call"]),
    "lineclient.exe":             ("LINE",        "Communication - WhatsApp",          ["Messaging"]),
    "kakaopc.exe":             ("KakaoTalk",        "Communication - WhatsApp",          ["Messaging"]),
    "wechat.exe":             ("WeChat",        "Communication - WeChat",          ["Messaging", "Social"]),
    "oicapp.exe":             ("QQ",        "Communication - WhatsApp",          ["Messaging"]),
    "icq.exe":             ("ICQ",        "Communication - WhatsApp",          ["Messaging"]),
    "mattermost.exe":             ("Mattermost",        "Communication - Mattermost",          ["Work Messaging"]),
    "rocketchat.exe":             ("Rocket.Chat",        "Work - Microsoft Word",          ["Work Messaging"]),
    "gather.exe":             ("Gather",        "Communication - Telegram",          ["Virtual Meeting"]),
    "flock.exe":             ("Flock",        "Communication - WhatsApp",          ["Work Messaging"]),

    # ── Finance / Trading ─────────────────────────────────────────────────────
    "mt4.exe":             ("MetaTrader 4",        "Financial - TradingView",          ["Forex Trading", "Chart Analysis"]),
    "mt5.exe":             ("MetaTrader 5",        "Financial - TradingView",          ["Trading", "Chart Analysis"]),
    "thinkorswim.exe":             ("thinkorswim",        "Financial - TradingView",          ["Stock Trading", "Options Analysis"]),
    "ninjatrader.exe":             ("NinjaTrader",        "Financial - TradingView",          ["Futures Trading", "Chart Analysis"]),

    # ── Misc Utilities ────────────────────────────────────────────────────────
    "autohotkey.exe":             ("AutoHotkey",        "System - Settings",          ["Automation", "Macro"]),
    "keypirinha.exe":             ("Keypirinha",        "System - Settings",          ["App Launch"]),
    "powertoys.exe":             ("PowerToys",        "System - Settings",          ["Productivity Tools"]),
    "flow.launcher.exe":             ("Flow Launcher",        "System - Settings",          ["App Launch", "Searching"]),
    "everything.exe":             ("Everything",        "System - Settings",          ["File Search"]),
    "agent.exe":             ("Clipboard Manager",        "System - Settings",          ["Clipboard"]),
    "ditto.exe":             ("Ditto (Clipboard)",        "System - Settings",          ["Clipboard Management"]),
    "greenshot.exe":             ("Greenshot",        "System - Settings",          ["Screenshot"]),
    "sharex.exe":             ("ShareX",        "System - Settings",          ["Screenshot", "Screen Recording"]),
    "lightshot.exe":             ("Lightshot",        "System - Settings",          ["Screenshot"]),
    "flux.exe":             ("f.lux",        "System - Settings",          ["Eye Care"]),
    "rainmeter.exe":             ("Rainmeter",        "System - Settings",          ["Desktop Customization"]),
    "fancyzones.exe":             ("FancyZones",        "System - Settings",          ["Window Management"]),
    "displayfusion.exe":             ("DisplayFusion",        "System - Settings",          ["Display Management"]),
    "f.lux.exe":             ("f.lux",        "System - Settings",          ["Eye Care"]),
    "barrier.exe":             ("Barrier",        "System - Settings",          ["Multi-Machine"]),
    "synergy.exe":             ("Synergy",        "System - Settings",          ["Multi-Machine"]),
    "cursor.exe":             ("Cursor IDE",        "Unknown - Unknown App",          ["Active Coding", "AI Assist", "Debugging"]),
    "mousewithoutwalls.exe":             ("Mouse Without Walls",        "System - Settings",          ["Multi-Machine"]),
    "cpu-z.exe":             ("CPU-Z",        "System - Settings",          ["Hardware Info"]),
    "gpu-z.exe":             ("GPU-Z",        "System - Settings",          ["Hardware Info"]),
    "hwinfo64.exe":             ("HWiNFO64",        "System - Settings",          ["Hardware Monitoring"]),
    "hwmonitor.exe":             ("HWMonitor",        "Browsing - HWMonitor",          ["Temperature Monitoring"]),
    "msi afterburner.exe":             ("MSI Afterburner",        "System - Settings",          ["GPU Overclocking", "GPU Monitoring"]),
    "afterburner.exe":             ("MSI Afterburner",        "System - Settings",          ["GPU Monitoring"]),
    "speccy.exe":             ("Speccy",        "System - Settings",          ["Hardware Info"]),
    "crystaldiskinfo.exe":             ("CrystalDiskInfo",        "System - Settings",          ["Drive Health"]),
    "ccleaner.exe":             ("CCleaner",        "System - Settings",          ["System Optimization", "Temp Cleanup"]),
    "defraggler.exe":             ("Defraggler",        "System - Disk Cleanup",          ["Disk Defragment"]),
    "recuva.exe":             ("Recuva",        "System - Settings",          ["File Recovery"]),
    "ultraiso.exe":             ("UltraISO",        "System - Settings",          ["ISO Management"]),
    "rufus.exe":             ("Rufus",        "System - Settings",          ["USB Creation"]),
    "etcher.exe":             ("Etcher",        "System - Settings",          ["USB Creation"]),
}


# ===========================================================================
# 2. DOMAIN → SPECIFIC ACTIVITY MAP
#    Key: domain fragment (lowercase, no www.) — first match wins
#    Value: specific activity label
# ===========================================================================
DOMAIN_CATEGORY_MAP: Dict[str, str] = {

    # ── Productivity & Work ─────────────────────────────────────────────────
    "docs.google.com":          "Work - Microsoft Word",
    "sheets.google.com":        "Work - Excel",
    "slides.google.com":        "Work - PowerPoint",
    "drive.google.com":         "System - File Explorer",
    "calendar.google.com":      "Work - Outlook",
    "meet.google.com":          "Work - Zoom Meeting",
    "workspace.google.com":     "Work - Outlook",
    "office.com":               "Work - Outlook",
    "onedrive.live.com":        "Work - Outlook",
    "notion.so":                "Work - Notion",
    "airtable.com":             "Work - Excel",
    "clickup.com":              "Work - Jira",
    "asana.com":                "Work - Jira",
    "trello.com":               "Work - Trello",
    "monday.com":               "Work - Jira",
    "jira.atlassian.net":       "Work - Jira",
    "confluence.atlassian.net": "Work - Jira",
    "linear.app":               "Work - Jira",
    "basecamp.com":             "Work - Jira",
    "figma.com":                "Work - Figma",
    "canva.com":                "Creative - Canva",
    "miro.com":                 "Work - Notion",
    "excalidraw.com":           "Work - Notion",
    "lucidchart.com":           "Work - Notion",

    # ── Development & DevOps ─────────────────────────────────────────────────
    "github.com":               "Work - VS Code",
    "gitlab.com":               "Work - VS Code",
    "bitbucket.org":            "Work - VS Code",
    "stackoverflow.com":        "Information - Stack Overflow",
    "stackexchange.com":        "Information - Stack Overflow",
    "developer.mozilla.org":    "Information - Wikipedia",
    "devdocs.io":               "Information - Wikipedia",
    "npmjs.com":                "Work - Terminal",
    "pypi.org":                 "Work - Terminal",
    "hub.docker.com":           "Work - Terminal",
    "cloud.google.com":         "System - Settings",
    "console.aws.amazon.com":   "System - Settings",
    "portal.azure.com":         "System - Settings",
    "vercel.com":               "System - Windows Update",
    "netlify.com":              "System - Windows Update",
    "railway.app":              "System - Windows Update",
    "render.com":               "System - Windows Update",
    "replit.com":               "Work - VS Code",
    "codepen.io":               "Work - VS Code",
    "codesandbox.io":           "Work - VS Code",
    "wandb.ai":                 "Work - VS Code",
    "huggingface.co":           "Work - VS Code",
    "kaggle.com":               "Work - VS Code",
    "colab.research.google.com":"Work - VS Code",
    "localhost:":               "Work - VS Code",
    "127.0.0.1":                "Work - VS Code",

    # ── Entertainment: Streaming ─────────────────────────────────────────────
    "youtube.com":              "Entertainment - YouTube",
    "youtu.be":                 "Entertainment - YouTube",
    "netflix.com":              "Entertainment - Netflix",
    "twitch.tv":                "Entertainment - Twitch",
    "primevideo.com":           "Entertainment - Netflix",
    "disneyplus.com":           "Entertainment - Netflix",
    "hulu.com":                 "Entertainment - Netflix",
    "hbomax.com":               "Entertainment - Netflix",
    "max.com":                  "Entertainment - Netflix",
    "peacocktv.com":            "Entertainment - Netflix",
    "paramountplus.com":        "Entertainment - Netflix",
    "vimeo.com":                "Entertainment - YouTube",
    "crunchyroll.com":          "Entertainment - Netflix",
    "bilibili.com":             "Entertainment - YouTube",
    "dailymotion.com":          "Entertainment - YouTube",

    # ── Entertainment: Music ─────────────────────────────────────────────────
    "open.spotify.com":         "Entertainment - Spotify",
    "music.apple.com":          "Entertainment - Spotify",
    "soundcloud.com":           "Entertainment - Spotify",
    "deezer.com":               "Entertainment - Spotify",
    "tidal.com":                "Entertainment - Spotify",
    "bandcamp.com":             "Entertainment - Spotify",
    "last.fm":                  "Entertainment - Spotify",

    # ── Entertainment: Gaming ─────────────────────────────────────────────────
    "store.steampowered.com":   "Entertainment - Steam Gaming",
    "steampowered.com":         "Entertainment - Steam Gaming",
    "epicgames.com":            "Entertainment - Steam Gaming",
    "gog.com":                  "Entertainment - Steam Gaming",
    "itch.io":                  "Entertainment - Steam Gaming",
    "chess.com":                "Entertainment - Gaming",
    "lichess.org":              "Entertainment - Gaming",

    # ── Social Media ─────────────────────────────────────────────────────────
    "reddit.com":               "Entertainment - Reddit",
    "twitter.com":              "Entertainment - Social Media",
    "x.com":                    "Entertainment - Social Media",
    "instagram.com":            "Entertainment - TikTok",
    "facebook.com":             "Entertainment - Social Media",
    "linkedin.com":             "Work - Slack",
    "tiktok.com":               "Entertainment - TikTok",
    "pinterest.com":            "Entertainment - Social Media",
    "tumblr.com":               "Entertainment - Social Media",
    "mastodon.social":          "Entertainment - Social Media",

    # ── Research & Academic ───────────────────────────────────────────────────
    "arxiv.org":                "Research - arXiv",
    "scholar.google.com":       "Research - Google Scholar",
    "researchgate.net":         "Research - arXiv",
    "sciencedirect.com":        "Research - arXiv",
    "springer.com":             "Research - arXiv",
    "nature.com":               "Research - arXiv",
    "pubmed.ncbi.nlm.nih.gov":  "Research - PubMed",
    "ieee.org":                 "Research - arXiv",
    "acm.org":                  "Research - arXiv",
    "jstor.org":                "Research - arXiv",
    "semanticscholar.org":      "Research - arXiv",
    "philpapers.org":           "Research - arXiv",
    "ssrn.com":                 "Research - arXiv",
    "unpaywall.org":            "Research - arXiv",
    "sci-hub":                  "Research - arXiv",

    # ── Learning & Education ──────────────────────────────────────────────────
    "coursera.org":             "Learning - Coursera",
    "udemy.com":                "Learning - Udemy",
    "edx.org":                  "Learning - Coursera",
    "khanacademy.org":          "Learning - Khan Academy",
    "pluralsight.com":          "Learning - Coursera",
    "linkedin.com/learning":    "Learning - Coursera",
    "skillshare.com":           "Learning - Coursera",
    "brilliant.org":            "Learning - Coursera",
    "duolingo.com":             "Learning - Duolingo",
    "leetcode.com":             "Learning - Khan Academy",
    "hackerrank.com":           "Learning - Khan Academy",
    "codewars.com":             "Learning - Khan Academy",
    "exercism.io":              "Learning - Khan Academy",
    "freecodecamp.org":         "Learning - Coursera",
    "theodinproject.com":       "Learning - Coursera",
    "w3schools.com":            "Learning - Coursera",
    "docs.python.org":          "Learning - Coursera",
    "readthedocs.io":           "Learning - Coursera",
    "medium.com":               "Information - Medium",
    "dev.to":                   "Information - Medium",
    "hashnode.com":             "Information - Medium",
    "substack.com":             "Information - News Site",

    # ── Communication ─────────────────────────────────────────────────────────
    "mail.google.com":          "Work - Outlook",
    "gmail.com":                "Work - Outlook",
    "outlook.com":              "Work - Outlook",
    "outlook.live.com":         "Work - Outlook",
    "mail.yahoo.com":           "Work - Outlook",
    "proton.me":                "Work - Outlook",
    "protonmail.com":           "Work - Outlook",
    "discord.com":              "Communication - Discord",
    "slack.com":                "Communication - Slack",
    "teams.microsoft.com":      "Communication - Teams Chat",
    "web.whatsapp.com":         "Communication - WhatsApp",
    "telegram.org":             "Communication - Telegram",
    "messenger.com":            "Communication - Messenger",
    "messages.google.com":      "Communication - Messenger",

    # ── Finance & Banking ─────────────────────────────────────────────────────
    "tradingview.com":          "Financial - TradingView",
    "binance.com":              "Financial - Binance",
    "coinbase.com":             "Financial - Coinbase",
    "kraken.com":               "Financial - Binance",
    "robinhood.com":            "Financial - TradingView",
    "etrade.com":               "Financial - TradingView",
    "interactivebrokers.com":   "Financial - TradingView",
    "finance.yahoo.com":        "Financial - TradingView",
    "investing.com":            "Financial - TradingView",
    "marketwatch.com":          "Financial - TradingView",
    "bloomberg.com":            "Financial - TradingView",
    "mint.com":                 "Financial - Banking Portal",
    "paypal.com":               "Financial - PayPal",
    "wise.com":                 "Financial - Banking Portal",
    "revolut.com":              "Financial - Banking Portal",

    # ── Shopping ──────────────────────────────────────────────────────────────
    "amazon.com":               "Shopping - Amazon",
    "amazon.co.uk":             "Shopping - Amazon",
    "ebay.com":                 "Shopping - eBay",
    "aliexpress.com":           "Shopping - Amazon",
    "walmart.com":              "Shopping - Walmart",
    "target.com":               "Shopping - Walmart",
    "etsy.com":                 "Shopping - Etsy",
    "shopify.com":              "Shopping - Walmart",
    "daraz.pk":                 "Shopping - Amazon",
    "daraz.com":                "Shopping - Amazon",
    "daraz.lk":                 "Shopping - Amazon",
    "daraz.com.np":             "Shopping - Amazon",
    "olx.com.pk":               "Shopping - Walmart",
    "olx.com":                  "Shopping - Walmart",
    "goto.com.pk":              "Shopping - Walmart",
    "islo.pk":                  "Shopping - Walmart",
    "telemart.pk":              "Shopping - Walmart",
    "shophive.com":             "Shopping - Walmart",
    "homeshopping.pk":          "Shopping - Walmart",
    "flipkart.com":             "Shopping - Walmart",
    "bestbuy.com":              "Shopping - Best Buy",
    "newegg.com":               "Shopping - Best Buy",
    "store.microsoft.com":      "System - Microsoft Store",
    "play.google.com":          "System - Microsoft Store",

    # ── News & Information ────────────────────────────────────────────────────
    "cnn.com":                  "Information - News Site",
    "bbc.com":                  "Information - News Site",
    "bbc.co.uk":                "Information - News Site",
    "nytimes.com":              "Information - News Site",
    "reuters.com":              "Information - News Site",
    "theguardian.com":          "Information - News Site",
    "apnews.com":               "Information - News Site",
    "techcrunch.com":           "Information - News Site",
    "theverge.com":             "Information - News Site",
    "arstechnica.com":          "Information - News Site",
    "wired.com":                "Information - News Site",
    "hackernews.ycombinator.com":"Information - News Site",
    "news.ycombinator.com":     "Information - News Site",
    "wikipedia.org":            "Information - Wikipedia",
    "quora.com":                "Information - Quora",

    # ── AI / ML Tools ─────────────────────────────────────────────────────────
    "chat.openai.com":          "Work - ChatGPT",
    "chatgpt.com":              "Work - ChatGPT",
    "claude.ai":                "Work - ChatGPT",
    "gemini.google.com":        "Work - ChatGPT",
    "bard.google.com":          "Work - ChatGPT",
    "perplexity.ai":            "Work - ChatGPT",
    "copilot.microsoft.com":    "Work - ChatGPT",
    "gamma.app":                "Work - ChatGPT",
    "midjourney.com":           "Creative - Photoshop",
    "stablediffusionweb.com":   "Creative - Photoshop",

    # ── Search Engines ─────────────────────────────────────────────────────────
    "google.com/search":        "Information - Web Search",
    "google.com":               "Information - Web Search",
    "google.com.pk":            "Information - Web Search",
    "google.pk":                "Information - Web Search",
    "bing.com":                 "Information - Web Search",
    "duckduckgo.com":           "Information - Web Search",
    "yahoo.com":                "Information - Web Search",
    "baidu.com":                "Information - Web Search",
    "yandex.com":               "Information - Web Search",

    # ── Cloud Storage ─────────────────────────────────────────────────────────
    "dropbox.com":              "System - File Explorer",
    "box.com":                  "System - File Explorer",
    "icloud.com":               "System - File Explorer",
}


# ===========================================================================
# 3. WINDOW TITLE PARSERS
#    Per-application compiled regex patterns to extract structured context.
#    Each entry: process_name → list of (regex_pattern, context_key_map)
# ===========================================================================

# VS Code title patterns:
# "main.py - VS Code" → file=main.py, lang=Python
# "● main.py - utils - VS Code" → file=main.py (● = unsaved changes)
# "Welcome - VS Code" → new session
# "Untitled-1 - VS Code" → new untitled file
_VSCODE_TITLE_RE = re.compile(
    r"^([●◯]?\s*)?(?P<file>[^-|]+?)\s*[-–]\s*(?:(?P<folder>[^-|]+?)\s*[-–]\s*)?(?:VS\s*Code|Visual\s*Studio\s*Code)\s*$",
    re.IGNORECASE,
)

# File extension → human‐readable language label
_EXT_TO_LANG: Dict[str, str] = {
    ".py":     "Python",
    ".js":     "JavaScript",
    ".ts":     "TypeScript",
    ".jsx":    "React (JSX)",
    ".tsx":    "React (TSX)",
    ".go":     "Go",
    ".rs":     "Rust",
    ".cpp":    "C++",
    ".c":      "C",
    ".cs":     "C#",
    ".java":   "Java",
    ".rb":     "Ruby",
    ".php":    "PHP",
    ".swift":  "Swift",
    ".kt":     "Kotlin",
    ".lua":    "Lua",
    ".r":      "R",
    ".sh":     "Shell Script",
    ".ps1":    "PowerShell",
    ".sql":    "SQL",
    ".html":   "HTML",
    ".css":    "CSS",
    ".scss":   "SCSS",
    ".json":   "JSON",
    ".yaml":   "YAML",
    ".yml":    "YAML",
    ".toml":   "TOML",
    ".md":     "Markdown",
    ".ipynb":  "Jupyter Notebook",
    ".tf":     "Terraform",
    ".dockerfile": "Docker",
}

# Discord title patterns
_DISCORD_CHANNEL_RE = re.compile(
    r"Discord\s*\|\s*#?(?P<channel>[^\|]+)", re.IGNORECASE
)
_DISCORD_VOICE_RE = re.compile(
    r"(?:voice connected|voice call|connected to voice|in voice)", re.IGNORECASE
)
_DISCORD_DM_RE = re.compile(
    r"Discord\s*\|\s*@?(?P<user>[A-Za-z0-9_\-\.]+)\s*$", re.IGNORECASE
)

# Zoom/Teams meeting detection
_MEETING_TITLE_RE = re.compile(
    r"(?:meeting with|zoom meeting|teams meeting|call with|webinar|conference)\s*(?:[-–:]\s*)?(?P<topic>.+)",
    re.IGNORECASE,
)

# Excel file context
_EXCEL_TITLE_RE = re.compile(
    r"^(?P<file>.+?)\s*[-–]\s*(?:Microsoft\s*Excel|Excel)\s*$",
    re.IGNORECASE,
)

# Word file context
_WORD_TITLE_RE = re.compile(
    r"^(?P<file>.+?)\s*[-–]\s*(?:Microsoft\s*Word|Word)\s*$",
    re.IGNORECASE,
)

# Browser page extraction (strip browser name suffix)
_BROWSER_SUFFIX_RE = re.compile(
    r"\s*[-–—|]\s*(?:Google Chrome|Chromium|Mozilla Firefox|Firefox|"
    r"Microsoft Edge|Edge|Opera|Brave|Safari|Vivaldi|Arc)\s*$",
    re.IGNORECASE,
)

# Generic "File - AppName" pattern (fallback)
_GENERIC_APP_FILE_RE = re.compile(
    r"^(?P<file>.+?)\s*[-–]\s*(?P<app>.+)$"
)

# Checkout/cart detection in browser page title
_SHOPPING_CONTEXT_RE = re.compile(
    r"\b(?:checkout|shopping\s*cart|order\s*confirmation|place\s*order|payment|buy\s*now)\b",
    re.IGNORECASE,
)

# YouTube specific titles
_YOUTUBE_TITLE_RE = re.compile(
    r"(?P<video_title>.+?)\s*[-–]\s*YouTube\s*$", re.IGNORECASE
)

# arXiv paper ID detection
_ARXIV_TITLE_RE = re.compile(
    r"arxiv\s*[:\s]+\d{4}\.\d{4,5}",
    re.IGNORECASE,
)

# Terminal/shell command context clues in title bar
_TERMINAL_SSH_RE = re.compile(r"\bssh\b|\b@\b.+\broot\b|\broot@", re.IGNORECASE)
_TERMINAL_VENV_RE = re.compile(r"\([a-zA-Z0-9_\-]+\)", re.IGNORECASE)  # (.venv)
_TERMINAL_GIT_RE = re.compile(r"\bgit\b|\(main\)|\(master\)|\(HEAD\)", re.IGNORECASE)
_TERMINAL_SERVER_RE = re.compile(r"\buvicorn\b|\bfastapi\b|\bdjango\b|\bflask\b|\bnpm\s+start\b|\bnpm\s+run\b", re.IGNORECASE)

# File category inference from extension
_FILE_CATEGORIES: Dict[str, str] = {
    ".xlsx": "Spreadsheet",
    ".xls": "Spreadsheet",
    ".csv": "Data File",
    ".docx": "Document",
    ".doc": "Document",
    ".pptx": "Presentation",
    ".ppt": "Presentation",
    ".pdf": "PDF Document",
    ".mp4": "Video File",
    ".mkv": "Video File",
    ".mp3": "Audio File",
    ".psd": "Photoshop File",
    ".fig": "Figma File",
    ".blend": "Blender File",
}


def get_file_lang(filename: str) -> Optional[str]:
    """Return human-readable language from a file extension, or None."""
    if not filename:
        return None
    ext = ""
    dot_idx = filename.rfind(".")
    if dot_idx != -1:
        ext = filename[dot_idx:].lower()
    return _EXT_TO_LANG.get(ext) or _FILE_CATEGORIES.get(ext)


def extract_domain(page_title_or_url: str) -> Optional[str]:
    """
    Try to extract a domain string from a window title or URL fragment.
    E.g. 'Stack Overflow - Where Developers Learn' → 'stackoverflow.com' won't work;
    this is used as a secondary heuristic when behavioral.py injects the URL.
    """
    # Simple heuristic: look for known tld patterns
    tld_re = re.compile(r"(?:https?://)?(?:www\.)?([a-zA-Z0-9\-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)", re.IGNORECASE)
    m = tld_re.search(page_title_or_url)
    if m:
        return m.group(1).lower()
    return None


def match_domain_label(domain: str) -> Optional[str]:
    """
    Look up the most specific domain label from DOMAIN_CATEGORY_MAP.
    Tries exact match first, then suffix matching.
    """
    if not domain:
        return None
    domain = domain.lower().lstrip("www.")
    # Exact match first
    if domain in DOMAIN_CATEGORY_MAP:
        return DOMAIN_CATEGORY_MAP[domain]
    # Suffix match: check if domain ends with any key
    for key, label in DOMAIN_CATEGORY_MAP.items():
        if domain.endswith(key) or domain == key:
            return label
    # Prefix match for broad domains like "localhost:"
    for key, label in DOMAIN_CATEGORY_MAP.items():
        if key in domain:
            return label
    return None
