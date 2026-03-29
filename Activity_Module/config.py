"""
NeuroLens - Activity Classifier Configuration
Central place for all model IDs, thresholds, and constants.
"""

# ---------------------------------------------------------------------------
# Model Identifiers  (base / lightweight — runs locally on CPU or a single GPU)
# ---------------------------------------------------------------------------
CLIP_MODEL_ID     = "openai/clip-vit-base-patch32"        # 150M — standard CLIP
FLORENCE_MODEL_ID = "microsoft/Florence-2-base-ft"         # 230M — fine-tuned base
QWEN_MODEL_ID     = "Qwen/Qwen2.5-0.5B-Instruct"          # 0.5B — lightweight

# ---------------------------------------------------------------------------
# Image Size Constraints (CRITICAL for latency reduction)
# ---------------------------------------------------------------------------
# Resize input images before model inference — massive speed improvement
# Resize input images before model inference — massive speed improvement
CLIP_IMAGE_SIZE   = (224, 224)   # CLIP native input size
MAX_IMAGE_SIZE    = (512, 512)   # Florence-2 max

# ---------------------------------------------------------------------------
# Visual Gate (Step 2 — CLIP) Settings
# ---------------------------------------------------------------------------
VISUAL_GATE_THRESHOLD = 0.55  # Slightly lowered for faster hit rate

VISUAL_GATE_ANCHORS = [
    "a video game with HUD or game interface",
    "a video player showing a movie or YouTube",
    "social media feed with posts and images",
    "music player application",
    "a code editor or IDE with source code",
    "a text document or word processor",
    "a spreadsheet with data and cells",
    "a video conference or online meeting",
    "a PDF document or research paper",
    "an online course or tutorial video",
    "a chat application with messages",
    "a blank screen, desktop, or screensaver",
]

CLIP_LABEL_MAP = {
    "a video game with HUD or game interface":        "Steam - Gaming",
    "a video player showing a movie or YouTube":      "YouTube - Video",
    "social media feed with posts and images":        "Twitter - Browsing Feed",
    "music player application":                       "Spotify - Music",
    "a code editor or IDE with source code":          "VS Code - Python Development",
    "a text document or word processor":              "Word - Writing",
    "a spreadsheet with data and cells":              "Excel - Data Entry",
    "a video conference or online meeting":           "Zoom - Meeting",
    "a PDF document or research paper":               "arXiv - Reading Paper",
    "an online course or tutorial video":             "Coursera - Watching Lecture",
    "a chat application with messages":               "Discord - Text Chat",
    "a blank screen, desktop, or screensaver":        "Idle - Away from Keyboard",
}

# ---------------------------------------------------------------------------
# Florence-2 Optimizations (Step 3)
# ---------------------------------------------------------------------------
FLORENCE_OCR_MAX_TOKENS     = 64
FLORENCE_CAPTION_MAX_TOKENS = 80
FLORENCE_SKIP_CAPTION_IF_RESOLVED = True

# ---------------------------------------------------------------------------
# LLM Generation Settings (Step 4 — Qwen)
# ---------------------------------------------------------------------------
QWEN_MAX_NEW_TOKENS = 32
QWEN_TEMPERATURE    = 0.05

# ---------------------------------------------------------------------------
# Taxonomy of Activity Types
# Simplified Output Format: [Category] - [Specific Activity]
# ---------------------------------------------------------------------------
TAXONOMY = {
    # Development Environments
    "VS Code": ["Python Development", "JavaScript Development", "Java Development",
                "Debugging", "Code Review", "Building", "Documentation", "Data Analysis", "Idle"],
    "IntelliJ": ["Java Development", "Kotlin Development", "Debugging", "Building"],
    "PyCharm": ["Python Development", "Django Development", "Debugging"],
    "Android Studio": ["UI Design", "Coding", "Testing", "Debugging"],
    "Visual Studio": ["C# Development", "Building", "Debugging"],
    "Sublime Text": ["Editing"],
    "Xcode": ["iOS Development", "UI Design", "Testing"],
    # Terminal
    "Terminal": ["Git Operations", "Package Installation", "Container Management",
                 "Remote Server", "Python Script Execution", "Compilation",
                 "File Navigation", "Building", "Command Line", "SSH Connection",
                 "Docker Management", "System Management"],
    # Browser-based
    "YouTube": ["Video", "Shorts", "Browsing", "Searching", "Learning Video",
                "Music Video", "Live Stream", "Channel Browsing"],
    "Netflix": ["Movie", "Series", "Browsing"],
    "Amazon": ["Product Browsing", "Checkout", "Searching", "Order Tracking"],
    "GitHub": ["Code Review", "PR Review", "Issue Tracking", "Repository Browsing", "Version History"],
    "Stack Overflow": ["Problem Solving", "Answering", "Searching"],
    "Gmail": ["Reading Emails", "Composing Email", "Searching", "Configuration"],
    "Google Docs": ["Writing", "Reading", "Reviewing", "Collaboration"],
    "Google Sheets": ["Data Entry", "Analysis", "Visualization"],
    "Google Drive": ["File Management", "Uploading"],
    "arXiv": ["Reading Abstract", "Reading Paper", "Searching Papers"],
    "Coursera": ["Watching Lecture", "Taking Quiz", "Doing Assignment", "Discussion"],
    "Reddit": ["Browsing Feed", "Reading Post", "Reading Comments", "Posting"],
    "Twitter": ["Browsing Feed", "Composing", "Reading Thread"],
    "LinkedIn": ["Job Hunting", "Browsing", "Networking"],
    "Wikipedia": ["Reading", "Searching"],
    "Medium": ["Reading", "Writing"],
    "Figma": ["UI Design", "Prototyping", "Collaboration"],
    "Canva": ["Template Browsing", "Designing", "Exporting"],
    "LeetCode": ["Coding Practice", "Discussion", "Contest"],
    "Spotify": ["Listening to Music", "Searching", "Curating Playlist", "Listening Podcast"],
    "Twitch": ["Watching Stream", "Chatting", "Browsing"],
    "TradingView": ["Market Analysis"],
    "Binance": ["Trading", "Portfolio Review"],
    # Document & Office
    "Word": ["Writing", "Reviewing", "Editing", "Formatting"],
    "Excel": ["Data Entry", "Formula Editing", "Creating Charts", "Data Analysis", "VBA Programming"],
    "PowerPoint": ["Creating Slides", "Presenting", "Organizing", "Adding Animations"],
    "Notion": ["Note Taking", "Database Management", "Reading", "Project Management"],
    "OneNote": ["Note Taking", "Clipping Content"],
    "Obsidian": ["Writing Notes", "Knowledge Graph", "Configuration"],
    # Creative
    "Photoshop": ["Photo Editing", "Adding Text", "Layer Management", "Exporting"],
    "Blender": ["3D Modeling", "Sculpting", "Animation", "Rendering"],
    "Premiere Pro": ["Video Editing", "Adding Effects", "Exporting"],
    "After Effects": ["Motion Graphics", "Animation"],
    "DaVinci Resolve": ["Color Grading", "Video Editing"],
    "Audacity": ["Audio Recording", "Audio Editing", "Audio Processing"],
    "FL Studio": ["Beat Making", "Mixing"],
    # Communication
    "Discord": ["Text Chat", "Voice Chat", "Screen Sharing", "Gaming with Voice"],
    "Slack": ["Team Chat", "Direct Message", "Reading Thread", "Voice Huddle"],
    "Teams": ["Chat", "Meeting", "File Review"],
    "WhatsApp": ["Messaging", "Voice Call"],
    "Telegram": ["Messaging", "Reading Channel"],
    "Zoom": ["Meeting", "Screen Sharing", "Breakout Session", "Chat", "Waiting"],
    "Google Meet": ["Meeting", "Presenting", "Chat"],
    # Entertainment
    "YouTube Music": ["Listening"],
    "VLC": ["Watching Video", "Listening to Music"],
    "Steam": ["Browsing Games", "Game Shopping", "Gaming"],
    "Epic Games": ["Gaming", "Browsing"],
    # System
    "File Explorer": ["Browsing Files", "Copying Files", "Searching", "File Properties"],
    "Task Manager": ["Performance Monitoring", "Managing Processes"],
    "Settings": ["System Configuration", "Customizing"],
    "Microsoft Store": ["App Browsing", "Installing"],
    # Gaming
    "Game": ["Playing", "Menu", "Loading", "Watching Cutscene", "Matchmaking", "Paused"],
    # Idle & Passive
    "Idle": ["Away from Keyboard", "Screen Locked", "Screensaver"],
    "Passive": ["Watching", "Listening"],
    "Thinking": ["Paused"],
}

# In Hybrid mode, strict validation is relaxed to allow dynamic strings 
# (e.g. "VS Code - Python Development + Background Music")
VALID_TAXONOMY_LABELS = [
    f"{app} - {intent}"
    for app, intents in TAXONOMY.items()
    for intent in intents
]

# ---------------------------------------------------------------------------
# Quantization / Memory Settings
# ---------------------------------------------------------------------------
FLORENCE_LOAD_IN_8BIT = False   # Enable on GPU for speed
QWEN_LOAD_IN_4BIT     = False   # Enable on GPU for significant speed boost

# ---------------------------------------------------------------------------
# Privacy Settings
# ---------------------------------------------------------------------------
# When True: suppress OCR content and window titles from logs
PRIVACY_MODE = False

# ---------------------------------------------------------------------------
# Behavioral & Idle Settings
# ---------------------------------------------------------------------------
BEHAVIORAL_POLL_INTERVAL = 1.0   # Frequency of background app scanning (seconds)
IDLE_THRESHOLD_SECONDS  = 60.0  # Time before system is marked 'Idle'

# ---------------------------------------------------------------------------
# Temporal Dynamics (Smoothing)
# ---------------------------------------------------------------------------
MULTITASK_BUFFER_SIZE    = 5    # Deque size for temporal state machine
TRANSITION_SMOOTH_COUNT = 2    # Number of stable frames required for high confidence

# ---------------------------------------------------------------------------
# Result Caching
# ---------------------------------------------------------------------------
# Cache last result for N seconds if window title unchanged (avoids redundant inference)
TITLE_CACHE_TTL_SECONDS = 1.5   # Cache valid for 1.5s (matches polling interval)

# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------
FALLBACK_ACTIVITY   = "Idle - Away from Keyboard"
FALLBACK_CONFIDENCE = 0.0

# ---------------------------------------------------------------------------
# NeuroLens Content Type Codes (for Emotion Correlation)
# ---------------------------------------------------------------------------
CONTENT_TYPE_CODES = {
    # Educational / Research
    "arXiv - Reading Abstract":          "EDU_RESEARCH",
    "arXiv - Reading Paper":             "EDU_RESEARCH",
    "arXiv - Searching Papers":          "EDU_RESEARCH",
    "Wikipedia - Reading":               "EDU_RESEARCH",
    "Wikipedia - Searching":             "EDU_RESEARCH",
    "Coursera - Watching Lecture":        "EDU_COURSE",
    "Coursera - Taking Quiz":            "EDU_COURSE",
    "Coursera - Doing Assignment":       "EDU_COURSE",
    "Coursera - Discussion":             "EDU_COURSE",
    "LeetCode - Coding Practice":        "EDU_COURSE",
    "LeetCode - Contest":                "EDU_COURSE",
    
    # Professional - Development
    "VS Code - Python Development":      "PRO_CODING",
    "VS Code - JavaScript Development":  "PRO_CODING",
    "VS Code - Java Development":        "PRO_CODING",
    "VS Code - Debugging":               "PRO_CODING",
    "VS Code - Code Review":             "PRO_CODING",
    "VS Code - Building":                "PRO_CODING",
    "VS Code - Documentation":           "PRO_DOCUMENT",
    "VS Code - Data Analysis":           "PRO_CODING",
    "IntelliJ - Java Development":       "PRO_CODING",
    "IntelliJ - Kotlin Development":     "PRO_CODING",
    "IntelliJ - Debugging":              "PRO_CODING",
    "PyCharm - Python Development":      "PRO_CODING",
    "PyCharm - Django Development":      "PRO_CODING",
    "PyCharm - Debugging":               "PRO_CODING",
    "Android Studio - UI Design":        "PRO_CODING",
    "Android Studio - Coding":           "PRO_CODING",
    "Android Studio - Testing":          "PRO_CODING",
    "Android Studio - Debugging":        "PRO_CODING",
    "Visual Studio - C# Development":    "PRO_CODING",
    "Visual Studio - Building":          "PRO_CODING",
    "Visual Studio - Debugging":         "PRO_CODING",
    "GitHub - Code Review":              "PRO_CODING",
    "GitHub - PR Review":                "PRO_CODING",
    "GitHub - Issue Tracking":           "PRO_CODING",
    "GitHub - Repository Browsing":      "PRO_CODING",
    "Stack Overflow - Problem Solving":  "PRO_CODING",
    "Stack Overflow - Searching":        "PRO_CODING",
    
    # Professional - Documents
    "Word - Writing":                    "PRO_DOCUMENT",
    "Word - Reviewing":                  "PRO_DOCUMENT",
    "Word - Editing":                    "PRO_DOCUMENT",
    "Word - Formatting":                 "PRO_DOCUMENT",
    "Excel - Data Entry":                "PRO_DOCUMENT",
    "Excel - Formula Editing":           "PRO_DOCUMENT",
    "Excel - Creating Charts":           "PRO_DOCUMENT",
    "Excel - Data Analysis":             "PRO_DOCUMENT",
    "Excel - VBA Programming":           "PRO_CODING",
    "PowerPoint - Creating Slides":      "PRO_DOCUMENT",
    "PowerPoint - Presenting":           "PRO_DOCUMENT",
    "Google Docs - Writing":             "PRO_DOCUMENT",
    "Google Docs - Reading":             "PRO_DOCUMENT",
    "Google Docs - Reviewing":           "PRO_DOCUMENT",
    "Google Sheets - Data Entry":        "PRO_DOCUMENT",
    "Google Sheets - Analysis":          "PRO_DOCUMENT",
    "Notion - Note Taking":              "PRO_DOCUMENT",
    "Notion - Project Management":       "PRO_DOCUMENT",
    "Obsidian - Writing Notes":          "PRO_DOCUMENT",
    
    # Professional - Email
    "Gmail - Reading Emails":            "PRO_EMAIL",
    "Gmail - Composing Email":           "PRO_EMAIL",
    "Gmail - Searching":                 "PRO_EMAIL",
    
    # Professional - Meetings
    "Zoom - Meeting":                    "PRO_MEETING",
    "Zoom - Screen Sharing":             "PRO_MEETING",
    "Zoom - Chat":                       "PRO_MEETING",
    "Google Meet - Meeting":             "PRO_MEETING",
    "Google Meet - Presenting":          "PRO_MEETING",
    "Teams - Meeting":                   "PRO_MEETING",
    "Teams - Chat":                      "PRO_MEETING",
    
    # Communication
    "Discord - Text Chat":               "COMM_CHAT",
    "Discord - Voice Chat":              "COMM_VOICE",
    "Discord - Screen Sharing":          "COMM_CHAT",
    "Slack - Team Chat":                 "COMM_CHAT",
    "Slack - Direct Message":            "COMM_CHAT",
    "Slack - Voice Huddle":              "COMM_VOICE",
    "WhatsApp - Messaging":              "COMM_CHAT",
    "WhatsApp - Voice Call":             "COMM_VOICE",
    "Telegram - Messaging":              "COMM_CHAT",
    
    # Entertainment - Video
    "YouTube - Video":                   "ENT_VIDEO",
    "YouTube - Shorts":                  "ENT_VIDEO",
    "YouTube - Learning Video":          "ENT_VIDEO",
    "YouTube - Live Stream":             "ENT_VIDEO",
    "YouTube - Music Video":             "ENT_MUSIC",
    "Netflix - Movie":                   "ENT_VIDEO",
    "Netflix - Series":                  "ENT_VIDEO",
    "Netflix - Browsing":                "ENT_VIDEO",
    "Twitch - Watching Stream":          "ENT_VIDEO",
    "VLC - Watching Video":              "ENT_VIDEO",
    
    # Entertainment - Music
    "Spotify - Music":                   "ENT_MUSIC",
    "Spotify - Podcast":                 "ENT_PODCAST",
    "Spotify - Listening Podcast":       "ENT_MUSIC",
    "Spotify - Curating Playlist":       "ENT_MUSIC",
    "VLC - Listening to Music":          "ENT_MUSIC",
    "YouTube Music - Listening":         "ENT_MUSIC",
    
    # Entertainment - Gaming
    "Steam - Gaming":                    "ENT_GAMING",
    "Epic Games - Gaming":               "ENT_GAMING",
    
    # Entertainment - Social
    "Reddit - Browsing Feed":            "ENT_SOCIAL",
    "Reddit - Reading Post":             "ENT_SOCIAL",
    "Twitter - Browsing Feed":           "ENT_SOCIAL",
    "Twitter - Composing":               "ENT_SOCIAL",
    "LinkedIn - Browsing":               "ENT_SOCIAL",
    "LinkedIn - Job Hunting":            "ENT_SOCIAL",
    "Medium - Reading":                  "ENT_SOCIAL",
    
    # Shopping
    "Amazon - Product Browsing":         "SHOP_ONLINE",
    "Amazon - Checkout":                 "SHOP_ONLINE",
    "Amazon - Searching":                "SHOP_ONLINE",
    "Amazon - Order Tracking":           "SHOP_ONLINE",
    
    # Financial
    "TradingView - Market Analysis":     "FIN_BANKING",
    "Binance - Trading":                 "FIN_BANKING",
    "Binance - Portfolio Review":         "FIN_BANKING",
    
    # System
    "File Explorer - Browsing Files":    "SYS_FILE",
    "File Explorer - Copying Files":     "SYS_FILE",
    "File Explorer - Searching":         "SYS_FILE",
    "Terminal - Git Operations":          "SYS_TERMINAL",
    "Terminal - Package Installation":    "SYS_TERMINAL",
    "Terminal - Script Execution":        "SYS_TERMINAL",
    "Terminal - Python Script Execution": "SYS_TERMINAL",
    "Terminal - Compilation":             "SYS_TERMINAL",
    "Terminal - Command Line":            "SYS_TERMINAL",
    "Terminal - SSH Connection":          "SYS_TERMINAL",
    "Terminal - Docker Management":       "SYS_TERMINAL",
    "Terminal - System Management":       "SYS_TERMINAL",
    "Terminal - File Navigation":         "SYS_TERMINAL",
    "Terminal - Remote Server":           "SYS_TERMINAL",
    "Terminal - Container Management":    "SYS_TERMINAL",
    "Task Manager - Performance Monitoring": "SYS_CONFIG",
    "Settings - System Configuration":   "SYS_CONFIG",
    
    # Creative
    "Figma - UI Design":                 "CR_DESIGN",
    "Figma - Prototyping":               "CR_DESIGN",
    "Canva - Designing":                 "CR_DESIGN",
    "Photoshop - Photo Editing":         "CR_DESIGN",
    "Blender - 3D Modeling":             "CR_DESIGN",
    "Premiere Pro - Video Editing":      "CR_VIDEO",
    "DaVinci Resolve - Video Editing":   "CR_VIDEO",
    "DaVinci Resolve - Color Grading":   "CR_VIDEO",
    "After Effects - Motion Graphics":   "CR_VIDEO",
    "Audacity - Audio Editing":          "CR_AUDIO",
    "FL Studio - Beat Making":           "CR_AUDIO",
    
    # Idle
    "Idle - Away from Keyboard":         "IDLE_AWAY",
    "Idle - Screen Locked":              "IDLE_AWAY",
    "Idle - Screensaver":                "IDLE_AWAY",
    "Passive - Watching":                "IDLE_PASSIVE",
    "Passive - Listening":               "IDLE_PASSIVE",
    "Thinking - Paused":                 "IDLE_PASSIVE",
}

def get_content_type_code(label: str) -> str:
    """Safely map any activity label to a NeuroLens content type code."""
    # Try exact match first
    if label in CONTENT_TYPE_CODES:
        return CONTENT_TYPE_CODES[label]
        
    # Try matching by category (prefix)
    cat = label.split(" - ")[0] if " - " in label else label
    for k, v in CONTENT_TYPE_CODES.items():
        if k.startswith(cat + " - "):
            return v
            
    return "UNKNOWN"

