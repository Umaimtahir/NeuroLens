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
    "a video game with HUD or game interface":        "Entertainment - Gaming",
    "a video player showing a movie or YouTube":      "Entertainment - YouTube",
    "social media feed with posts and images":        "Entertainment - Social Media",
    "music player application":                       "Entertainment - Spotify",
    "a code editor or IDE with source code":          "Work - VS Code",
    "a text document or word processor":              "Work - Microsoft Word",
    "a spreadsheet with data and cells":              "Work - Excel",
    "a video conference or online meeting":           "Work - Zoom Meeting",
    "a PDF document or research paper":               "Research - arXiv",
    "an online course or tutorial video":             "Learning - Coursera",
    "a chat application with messages":               "Communication - Discord",
    "a blank screen, desktop, or screensaver":        "Idle - AFK",
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
    "Shopping": ["Shopping - Ecommerce"],
    "Research": ["Research - Academic", "Research - Reading Paper"],
    "Communication": ["Communication - Email", "Communication - Video Call", "Communication - Meeting"],
    "Entertainment": ["Entertainment - Video", "Entertainment - Music"],
    "Learning": ["Learning - Tutorial"],
    "Development": ["Development - Coding Reference", "Development - GitHub", "Development - Code"],
    "Social Media": ["Social Media - Browsing", "Social Media - Chat"],
    "News": ["News - Reading"],
    "Work": ["Work - Documentation", "Work - Data Analysis", "Work - Presentation", "Work - Planning"],
    "Financial": ["Financial - Banking"],
    "Information": ["Information - Reading"],
    "Creative": ["Creative - Design"],
    "Browsing": ["Browsing - Web"],
    "System": ["System - Terminal", "System - File Explorer"],
    "Gaming": ["Gaming - Steam", "Gaming - Epic Games"],
    "Idle": ["Idle - System Idle"]
}

# In Hybrid mode, strict validation is relaxed to allow dynamic strings 
# (e.g. "Development - Coding in Python + Background Music")
VALID_TAXONOMY_LABELS = [
    f"{cat} - {sub}"
    for cat, subs in TAXONOMY.items()
    for sub in subs
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
FALLBACK_ACTIVITY   = "Idle - System Idle"
FALLBACK_CONFIDENCE = 0.0

# ---------------------------------------------------------------------------
# NeuroLens Content Type Codes (for Emotion Correlation)
# ---------------------------------------------------------------------------
CONTENT_TYPE_CODES = {
    # Educational
    "Educational - Research":           "EDU_RESEARCH",
    "Research - Reading Paper":         "EDU_RESEARCH",
    "Research - arXiv":                 "EDU_RESEARCH",
    "Learning - Online Course":         "EDU_COURSE",
    "Learning - Coursera":               "EDU_COURSE",
    "Learning - Udemy":                 "EDU_COURSE",
    
    # Professional
    "Work - Coding":                    "PRO_CODING",
    "Development - Coding":             "PRO_CODING",
    "Work - VS Code":                   "PRO_CODING",
    "Work - Document Work":             "PRO_DOCUMENT",
    "Work - Microsoft Word":             "PRO_DOCUMENT",
    "Work - Excel":                     "PRO_DOCUMENT",
    "Work - Document":                   "PRO_DOCUMENT",
    "Work - Notion":                    "PRO_DOCUMENT",
    "Professional - Email":              "PRO_EMAIL",
    "Work - Outlook":                   "PRO_EMAIL",
    "Communication - Email":            "PRO_EMAIL",
    "Professional - Meeting":            "PRO_MEETING",
    "Work - Zoom Meeting":              "PRO_MEETING",
    "Work - Teams Meeting":              "PRO_MEETING",
    "Meeting - In Call":                "PRO_MEETING",
    
    # Communication
    "Communication - Messaging":         "COMM_CHAT",
    "Communication - Discord Chat":     "COMM_CHAT",
    "Communication - Slack":            "COMM_CHAT",
    "Communication - Voice Chat":        "COMM_VOICE",
    "Communication - Discord Voice":     "COMM_VOICE",
    
    # Entertainment
    "Entertainment - Video Streaming":   "ENT_VIDEO",
    "Entertainment - YouTube":           "ENT_VIDEO",
    "Entertainment - Netflix":           "ENT_VIDEO",
    "Entertainment - Music":             "ENT_MUSIC",
    "Entertainment - Spotify":           "ENT_MUSIC",
    "Entertainment - Gaming":            "ENT_GAMING",
    "Gaming - Unknown Game":             "ENT_GAMING",
    "Entertainment - Social Media":      "ENT_SOCIAL",
    "Social - Reddit":                  "ENT_SOCIAL",
    "Social - Twitter":                 "ENT_SOCIAL",
    
    # Shopping
    "Shopping - E-commerce":            "SHOP_ONLINE",
    "Shopping - Amazon":                "SHOP_ONLINE",
    "Shopping - eBay":                  "SHOP_ONLINE",
    
    # Financial
    "Financial - Banking":              "FIN_BANKING",
    "Financial - Trading":              "FIN_BANKING",
    
    # System
    "System - File Management":         "SYS_FILE",
    "System - File Explorer":           "SYS_FILE",
    "System - Command Line":            "SYS_TERMINAL",
    "System - Terminal":                "SYS_TERMINAL",
    "System - PowerShell":              "SYS_TERMINAL",
    "System - Configuration":           "SYS_CONFIG",
    "System - Task Manager":            "SYS_CONFIG",
    "System - Windows Settings":        "SYS_CONFIG",
    
    # Creative
    "Creative - Design":                "CR_DESIGN",
    "Creative - Photoshop":             "CR_DESIGN",
    "Creative - Figma":                 "CR_DESIGN",
    "Creative - Video Editing":          "CR_VIDEO",
    "Creative - Premiere Pro":          "CR_VIDEO",
    "Creative - DaVinci Resolve":       "CR_VIDEO",
    
    # Idle
    "Idle - Away":                      "IDLE_AWAY",
    "Idle - System Idle":               "IDLE_AWAY",
    "Idle - Away From Keyboard":        "IDLE_AWAY",
    "Idle - Screen Locked":             "IDLE_AWAY",
    "Idle - Passive Viewing":           "IDLE_PASSIVE",
    "Passive - Watching":               "IDLE_PASSIVE",
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

