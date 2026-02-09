"""
Lightweight Window Detector & Activity Classifier
Extracted from screen_classifer.py - NO ML dependencies (no transformers, torch, PIL, etc.)
Only uses Python stdlib: ctypes, os, re
"""

import os
import re
import ctypes
from ctypes import wintypes
from typing import Dict


# ============================================================================
# Activity Classifier
# ============================================================================

class ActivityClassifier:
    """Classifies what type of activity the user is performing."""

    ACTIVITIES = {
        'WRITING': {
            'emoji': '✍️',
            'keywords': [
                'compose', 'edit', 'draft', 'write', 'typing', 'new document',
                'new email', 'reply', 'untitled', 'document', 'notepad',
                'editor', 'word processor', 'memo', 'notes'
            ],
            'apps': [
                'notepad', 'notepad++', 'word', 'winword', 'writer', 'typora',
                'marktext', 'notion', 'obsidian', 'evernote', 'onenote', 'bear',
                'craft', 'logseq', 'roam', 'scrivener', 'ulysses', 'ia writer'
            ],
            'title_patterns': [
                r'new\s+\w+', r'untitled', r'compose', r'edit', r'draft',
                r'writing', r'reply', r'new message', r'new post'
            ],
            'categories': ['DOCUMENT/PRODUCTIVITY'],
        },
        'READING': {
            'emoji': '📖',
            'keywords': [
                'reading', 'article', 'blog', 'news', 'post', 'story',
                'content', 'page', 'chapter', 'book', 'ebook', 'pdf',
                'documentation', 'docs', 'readme', 'wiki'
            ],
            'apps': [
                'acrobat', 'acrord32', 'foxit', 'sumatrapdf', 'kindle',
                'calibre', 'epub', 'reader'
            ],
            'title_patterns': [
                r'article', r'blog', r'post', r'news', r'story', r'\.pdf',
                r'readme', r'documentation', r'wiki', r'chapter'
            ],
            'categories': ['NEWS', 'EDUCATION'],
        },
        'WATCHING': {
            'emoji': '👀',
            'keywords': [
                'watching', 'video', 'movie', 'film', 'episode', 'stream',
                'live', 'show', 'series', 'trailer', 'clip', 'play',
                'playing', 'watch', 'viewing'
            ],
            'apps': [
                'vlc', 'mpv', 'mpc-hc', 'mpc-be', 'potplayer', 'kmplayer',
                'gom', 'wmplayer', 'media player', 'netflix', 'plex',
                'kodi', 'stremio', 'jellyfin', 'emby', 'twitch'
            ],
            'title_patterns': [
                r'video', r'movie', r'episode', r's\d+e\d+', r'720p', r'1080p',
                r'4k', r'hdr', r'stream', r'live', r'watch', r'playing'
            ],
            'categories': ['VIDEO/STREAMING'],
        },
        'CODING': {
            'emoji': '💻',
            'keywords': [
                'code', 'coding', 'programming', 'develop', 'debug', 'compile',
                'function', 'class', 'module', 'script', 'terminal', 'console',
                'commit', 'push', 'pull', 'merge', 'branch', 'git'
            ],
            'apps': [
                'code', 'cursor', 'antigravity', 'pycharm', 'pycharm64', 'intellij',
                'idea64', 'webstorm', 'phpstorm', 'rider', 'clion', 'goland',
                'sublime', 'sublime_text', 'atom', 'vim', 'nvim', 'neovim',
                'emacs', 'eclipse', 'netbeans', 'jupyter', 'spyder', 'rstudio',
                'cmd', 'powershell', 'pwsh', 'terminal', 'windowsterminal', 'wt',
                'mintty', 'conemu', 'cmder', 'hyper', 'alacritty', 'kitty'
            ],
            'title_patterns': [
                r'\.py', r'\.js', r'\.ts', r'\.java', r'\.cpp', r'\.cs', r'\.go',
                r'\.rs', r'\.rb', r'\.php', r'\.html', r'\.css', r'\.json',
                r'\.xml', r'\.yml', r'\.yaml', r'\.sql', r'\.sh', r'\.ps1',
                r'git', r'npm', r'pip', r'docker', r'debug', r'console'
            ],
            'categories': ['CODING/DEVELOPMENT', 'DATABASE', 'DEVOPS', 'API TESTING'],
        },
        'BROWSING': {
            'emoji': '🌐',
            'keywords': [
                'browser', 'browsing', 'web', 'internet', 'search', 'google',
                'bing', 'homepage', 'bookmark', 'tab', 'new tab'
            ],
            'apps': [
                'chrome', 'firefox', 'edge', 'msedge', 'opera', 'brave',
                'vivaldi', 'safari', 'chromium', 'waterfox', 'tor'
            ],
            'title_patterns': [
                r'google', r'bing', r'yahoo', r'duckduckgo', r'search',
                r'new tab', r'browser', r'homepage'
            ],
            'categories': ['WEB BROWSING'],
        },
        'GAMING': {
            'emoji': '🎮',
            'keywords': [
                'game', 'gaming', 'play', 'playing', 'level', 'score',
                'player', 'quest', 'mission', 'match', 'round', 'inventory',
                'character', 'health', 'damage', 'xp'
            ],
            'apps': [
                'steam', 'epicgameslauncher', 'origin', 'eadesktop', 'battlenet',
                'uplay', 'gog', 'minecraft', 'javaw', 'roblox', 'valorant',
                'fortnite', 'csgo', 'cs2', 'dota', 'apex', 'cod', 'overwatch',
                'wow', 'diablo', 'hearthstone', 'pubg', 'gta', 'fifa'
            ],
            'title_patterns': [
                r'level', r'score', r'health', r'damage', r'quest', r'mission',
                r'game', r'play', r'match', r'round'
            ],
            'categories': ['GAMING'],
        },
        'DESIGNING': {
            'emoji': '🎨',
            'keywords': [
                'design', 'designing', 'edit', 'editing', 'image', 'photo',
                'graphic', 'draw', 'drawing', 'paint', 'painting', 'layer',
                'canvas', 'brush', 'color', 'filter', 'effect', 'render'
            ],
            'apps': [
                'photoshop', 'illustrator', 'indesign', 'premiere', 'aftereffects',
                'lightroom', 'figma', 'sketch', 'canva', 'gimp', 'inkscape',
                'krita', 'paint', 'mspaint', 'paintdotnet', 'affinity', 'coreldraw',
                'davinci', 'resolve', 'vegas', 'filmora', 'capcut', 'aseprite',
                'blender', 'unity', 'unreal', 'godot'
            ],
            'title_patterns': [
                r'\.psd', r'\.ai', r'\.svg', r'\.png', r'\.jpg', r'\.jpeg',
                r'\.gif', r'\.webp', r'project', r'design', r'layer', r'canvas'
            ],
            'categories': ['IMAGE/DESIGN'],
        },
        'COMMUNICATING': {
            'emoji': '💬',
            'keywords': [
                'chat', 'message', 'messaging', 'call', 'calling', 'meeting',
                'conference', 'email', 'mail', 'inbox', 'conversation', 'dm',
                'direct message', 'voice', 'video call', 'text'
            ],
            'apps': [
                'discord', 'slack', 'teams', 'msteams', 'zoom', 'skype',
                'telegram', 'whatsapp', 'signal', 'viber', 'wechat', 'line',
                'element', 'outlook', 'thunderbird', 'messenger', 'webex'
            ],
            'title_patterns': [
                r'chat', r'message', r'call', r'meeting', r'inbox', r'email',
                r'conversation', r'channel', r'dm', r'voic'
            ],
            'categories': ['COMMUNICATION'],
        },
        'LISTENING': {
            'emoji': '🎧',
            'keywords': [
                'music', 'listening', 'song', 'track', 'album', 'playlist',
                'audio', 'podcast', 'radio', 'play', 'playing', 'artist',
                'spotify', 'soundcloud'
            ],
            'apps': [
                'spotify', 'itunes', 'foobar', 'foobar2000', 'winamp',
                'musicbee', 'aimp', 'clementine', 'rhythmbox', 'audacity',
                'amazon music', 'tidal', 'deezer', 'pandora'
            ],
            'title_patterns': [
                r'song', r'track', r'album', r'playlist', r'artist', r'band',
                r'music', r'spotify', r'now playing', r'♪', r'♫'
            ],
            'categories': ['MUSIC'],
        },
        'SEARCHING': {
            'emoji': '🔍',
            'keywords': [
                'search', 'searching', 'find', 'finding', 'lookup', 'query',
                'results', 'google', 'bing', 'yahoo', 'duckduckgo'
            ],
            'apps': [],
            'title_patterns': [
                r'search', r'find', r'google', r'bing', r'yahoo', r'duckduckgo',
                r'results for', r'query'
            ],
            'categories': [],
        },
        'SHOPPING': {
            'emoji': '🛒',
            'keywords': [
                'shopping', 'shop', 'buy', 'purchase', 'cart', 'checkout',
                'order', 'product', 'price', 'deal', 'sale', 'discount',
                'shipping', 'delivery'
            ],
            'apps': [],
            'title_patterns': [
                r'cart', r'checkout', r'order', r'buy', r'shop', r'product',
                r'price', r'\$\d+', r'amazon', r'ebay', r'walmart'
            ],
            'categories': ['SHOPPING', 'FINANCE'],
        },
        'LEARNING': {
            'emoji': '📚',
            'keywords': [
                'learn', 'learning', 'study', 'studying', 'course', 'lesson',
                'tutorial', 'lecture', 'education', 'class', 'quiz', 'test',
                'homework', 'assignment', 'training'
            ],
            'apps': [],
            'title_patterns': [
                r'course', r'lesson', r'tutorial', r'lecture', r'learn',
                r'study', r'class', r'module', r'chapter', r'quiz'
            ],
            'categories': ['EDUCATION'],
        },
    }

    def __init__(self):
        print("✅ Activity classifier ready!")

    def classify(self, app_name: str, window_title: str, category: str,
                 visual_caption: str = "", ocr_text: str = "") -> Dict:
        """
        Classify the user's current activity.
        Returns dict with 'activity', 'emoji', 'confidence', 'score', 'reason'
        """
        scores = {}
        reasons = {}

        app_lower = app_name.lower() if app_name else ""
        title_lower = window_title.lower() if window_title else ""
        caption_lower = visual_caption.lower() if visual_caption else ""
        ocr_lower = ocr_text.lower() if ocr_text else ""
        category_upper = category.upper() if category else ""

        for activity, config in self.ACTIVITIES.items():
            score = 0
            reason_parts = []

            # Check apps (highest weight - 4 points)
            if any(app in app_lower for app in config['apps']):
                score += 4
                reason_parts.append("app match")

            # Check category (3 points)
            if category_upper in config['categories']:
                score += 3
                reason_parts.append("category match")

            # Check title patterns (2 points each, max 4)
            title_matches = sum(1 for p in config['title_patterns'] if re.search(p, title_lower))
            if title_matches > 0:
                score += min(title_matches * 2, 4)
                reason_parts.append("title pattern")

            # Check keywords in title (1 point each, max 3)
            keyword_matches = sum(1 for kw in config['keywords'] if kw in title_lower)
            if keyword_matches > 0:
                score += min(keyword_matches, 3)
                reason_parts.append("keywords")

            # Check OCR text (1 point each, max 2)
            if ocr_lower:
                ocr_keywords = config.get('ocr_keywords', [])
                ocr_matches = sum(1 for kw in ocr_keywords if kw in ocr_lower)
                if ocr_matches > 0:
                    score += min(ocr_matches, 2)
                    reason_parts.append("ocr text")

            # Check visual caption (1 point)
            if caption_lower and any(kw in caption_lower for kw in config['keywords'][:5]):
                score += 1
                reason_parts.append("visual")

            if score > 0:
                scores[activity] = score
                reasons[activity] = ", ".join(reason_parts)

        if scores:
            best_activity = max(scores, key=scores.get)
            best_score = scores[best_activity]

            if best_score >= 8:
                confidence = "Very High"
            elif best_score >= 5:
                confidence = "High"
            elif best_score >= 3:
                confidence = "Medium"
            else:
                confidence = "Low"

            return {
                'activity': best_activity,
                'emoji': self.ACTIVITIES[best_activity]['emoji'],
                'confidence': confidence,
                'score': best_score,
                'reason': reasons[best_activity]
            }

        return {
            'activity': 'BROWSING',
            'emoji': '🌐',
            'confidence': 'Low',
            'score': 0,
            'reason': 'default'
        }


# ============================================================================
# Windows API - Active Window Detection (200+ apps/websites)
# ============================================================================

class WindowsAPI:
    """Windows API utilities with 200+ app/website detection."""

    APP_CATEGORIES = {
        # ===== Browsers =====
        "chrome": ("WEB BROWSING", "🌐"),
        "firefox": ("WEB BROWSING", "🌐"),
        "edge": ("WEB BROWSING", "🌐"),
        "msedge": ("WEB BROWSING", "🌐"),
        "opera": ("WEB BROWSING", "🌐"),
        "brave": ("WEB BROWSING", "🌐"),
        "vivaldi": ("WEB BROWSING", "🌐"),
        "safari": ("WEB BROWSING", "🌐"),
        "chromium": ("WEB BROWSING", "🌐"),
        "waterfox": ("WEB BROWSING", "🌐"),
        "tor": ("WEB BROWSING", "🌐"),

        # ===== Code Editors & IDEs =====
        "code": ("CODING/DEVELOPMENT", "💻"),
        "cursor": ("CODING/DEVELOPMENT", "💻"),
        "antigravity": ("CODING/DEVELOPMENT", "💻"),
        "visual studio": ("CODING/DEVELOPMENT", "💻"),
        "devenv": ("CODING/DEVELOPMENT", "💻"),
        "pycharm": ("CODING/DEVELOPMENT", "💻"),
        "pycharm64": ("CODING/DEVELOPMENT", "💻"),
        "intellij": ("CODING/DEVELOPMENT", "💻"),
        "idea64": ("CODING/DEVELOPMENT", "💻"),
        "webstorm": ("CODING/DEVELOPMENT", "💻"),
        "webstorm64": ("CODING/DEVELOPMENT", "💻"),
        "phpstorm": ("CODING/DEVELOPMENT", "💻"),
        "rider": ("CODING/DEVELOPMENT", "💻"),
        "clion": ("CODING/DEVELOPMENT", "💻"),
        "goland": ("CODING/DEVELOPMENT", "💻"),
        "rubymine": ("CODING/DEVELOPMENT", "💻"),
        "datagrip": ("CODING/DEVELOPMENT", "💻"),
        "android studio": ("CODING/DEVELOPMENT", "💻"),
        "studio64": ("CODING/DEVELOPMENT", "💻"),
        "sublime": ("CODING/DEVELOPMENT", "💻"),
        "sublime_text": ("CODING/DEVELOPMENT", "💻"),
        "notepad++": ("CODING/DEVELOPMENT", "💻"),
        "atom": ("CODING/DEVELOPMENT", "💻"),
        "brackets": ("CODING/DEVELOPMENT", "💻"),
        "vim": ("CODING/DEVELOPMENT", "💻"),
        "nvim": ("CODING/DEVELOPMENT", "💻"),
        "neovim": ("CODING/DEVELOPMENT", "💻"),
        "gvim": ("CODING/DEVELOPMENT", "💻"),
        "emacs": ("CODING/DEVELOPMENT", "💻"),
        "eclipse": ("CODING/DEVELOPMENT", "💻"),
        "netbeans": ("CODING/DEVELOPMENT", "💻"),
        "codeblocks": ("CODING/DEVELOPMENT", "💻"),
        "xcode": ("CODING/DEVELOPMENT", "💻"),
        "jupyter": ("CODING/DEVELOPMENT", "💻"),
        "spyder": ("CODING/DEVELOPMENT", "💻"),
        "rstudio": ("CODING/DEVELOPMENT", "💻"),
        "matlab": ("CODING/DEVELOPMENT", "💻"),
        "unity": ("CODING/DEVELOPMENT", "💻"),
        "unreal": ("CODING/DEVELOPMENT", "💻"),
        "godot": ("CODING/DEVELOPMENT", "💻"),
        "blender": ("CODING/DEVELOPMENT", "💻"),
        "zed": ("CODING/DEVELOPMENT", "💻"),
        "lapce": ("CODING/DEVELOPMENT", "💻"),
        "helix": ("CODING/DEVELOPMENT", "💻"),

        # ===== Terminals =====
        "cmd": ("CODING/DEVELOPMENT", "💻"),
        "powershell": ("CODING/DEVELOPMENT", "💻"),
        "pwsh": ("CODING/DEVELOPMENT", "💻"),
        "terminal": ("CODING/DEVELOPMENT", "💻"),
        "windowsterminal": ("CODING/DEVELOPMENT", "💻"),
        "wt": ("CODING/DEVELOPMENT", "💻"),
        "mintty": ("CODING/DEVELOPMENT", "💻"),
        "conemu": ("CODING/DEVELOPMENT", "💻"),
        "cmder": ("CODING/DEVELOPMENT", "💻"),
        "hyper": ("CODING/DEVELOPMENT", "💻"),
        "alacritty": ("CODING/DEVELOPMENT", "💻"),
        "kitty": ("CODING/DEVELOPMENT", "💻"),
        "wezterm": ("CODING/DEVELOPMENT", "💻"),
        "iterm": ("CODING/DEVELOPMENT", "💻"),
        "putty": ("CODING/DEVELOPMENT", "💻"),
        "mobaxterm": ("CODING/DEVELOPMENT", "💻"),
        "securecrt": ("CODING/DEVELOPMENT", "💻"),

        # ===== Communication =====
        "discord": ("COMMUNICATION", "💬"),
        "slack": ("COMMUNICATION", "💬"),
        "teams": ("COMMUNICATION", "💬"),
        "msteams": ("COMMUNICATION", "💬"),
        "zoom": ("COMMUNICATION", "💬"),
        "skype": ("COMMUNICATION", "💬"),
        "telegram": ("COMMUNICATION", "💬"),
        "whatsapp": ("COMMUNICATION", "💬"),
        "signal": ("COMMUNICATION", "💬"),
        "viber": ("COMMUNICATION", "💬"),
        "wechat": ("COMMUNICATION", "💬"),
        "line": ("COMMUNICATION", "💬"),
        "element": ("COMMUNICATION", "💬"),
        "matrix": ("COMMUNICATION", "💬"),
        "outlook": ("COMMUNICATION", "💬"),
        "thunderbird": ("COMMUNICATION", "💬"),
        "mailspring": ("COMMUNICATION", "💬"),
        "spark": ("COMMUNICATION", "💬"),
        "webex": ("COMMUNICATION", "💬"),
        "bluejeans": ("COMMUNICATION", "💬"),
        "gotomeeting": ("COMMUNICATION", "💬"),
        "meet": ("COMMUNICATION", "💬"),
        "messenger": ("COMMUNICATION", "💬"),

        # ===== Video/Streaming =====
        "vlc": ("VIDEO/STREAMING", "🎬"),
        "netflix": ("VIDEO/STREAMING", "🎬"),
        "prime video": ("VIDEO/STREAMING", "🎬"),
        "disney": ("VIDEO/STREAMING", "🎬"),
        "hbo": ("VIDEO/STREAMING", "🎬"),
        "hulu": ("VIDEO/STREAMING", "🎬"),
        "twitch": ("VIDEO/STREAMING", "🎬"),
        "plex": ("VIDEO/STREAMING", "🎬"),
        "kodi": ("VIDEO/STREAMING", "🎬"),
        "mpv": ("VIDEO/STREAMING", "🎬"),
        "mpc-hc": ("VIDEO/STREAMING", "🎬"),
        "mpc-be": ("VIDEO/STREAMING", "🎬"),
        "potplayer": ("VIDEO/STREAMING", "🎬"),
        "kmplayer": ("VIDEO/STREAMING", "🎬"),
        "gom": ("VIDEO/STREAMING", "🎬"),
        "media player": ("VIDEO/STREAMING", "🎬"),
        "wmplayer": ("VIDEO/STREAMING", "🎬"),
        "cinema": ("VIDEO/STREAMING", "🎬"),
        "movies": ("VIDEO/STREAMING", "🎬"),
        "stremio": ("VIDEO/STREAMING", "🎬"),
        "jellyfin": ("VIDEO/STREAMING", "🎬"),
        "emby": ("VIDEO/STREAMING", "🎬"),
        "obs": ("VIDEO/STREAMING", "🎬"),
        "obs64": ("VIDEO/STREAMING", "🎬"),
        "streamlabs": ("VIDEO/STREAMING", "🎬"),
        "xsplit": ("VIDEO/STREAMING", "🎬"),

        # ===== Social Media =====
        "twitter": ("SOCIAL MEDIA", "📱"),
        "facebook": ("SOCIAL MEDIA", "📱"),
        "instagram": ("SOCIAL MEDIA", "📱"),
        "reddit": ("SOCIAL MEDIA", "📱"),
        "linkedin": ("SOCIAL MEDIA", "📱"),
        "tiktok": ("SOCIAL MEDIA", "📱"),
        "snapchat": ("SOCIAL MEDIA", "📱"),
        "pinterest": ("SOCIAL MEDIA", "📱"),
        "tumblr": ("SOCIAL MEDIA", "📱"),

        # ===== Gaming =====
        "steam": ("GAMING", "🎮"),
        "steamwebhelper": ("GAMING", "🎮"),
        "epic": ("GAMING", "🎮"),
        "epicgameslauncher": ("GAMING", "🎮"),
        "origin": ("GAMING", "🎮"),
        "ea": ("GAMING", "🎮"),
        "eadesktop": ("GAMING", "🎮"),
        "battle.net": ("GAMING", "🎮"),
        "battlenet": ("GAMING", "🎮"),
        "uplay": ("GAMING", "🎮"),
        "ubisoft": ("GAMING", "🎮"),
        "gog": ("GAMING", "🎮"),
        "galaxy": ("GAMING", "🎮"),
        "minecraft": ("GAMING", "🎮"),
        "javaw": ("GAMING", "🎮"),
        "roblox": ("GAMING", "🎮"),
        "robloxplayer": ("GAMING", "🎮"),
        "valorant": ("GAMING", "🎮"),
        "valorant-win64-shipping": ("GAMING", "🎮"),
        "fortnite": ("GAMING", "🎮"),
        "fortniteclient": ("GAMING", "🎮"),
        "league": ("GAMING", "🎮"),
        "leagueclient": ("GAMING", "🎮"),
        "genshin": ("GAMING", "🎮"),
        "genshinimpact": ("GAMING", "🎮"),
        "csgo": ("GAMING", "🎮"),
        "cs2": ("GAMING", "🎮"),
        "dota": ("GAMING", "🎮"),
        "apex": ("GAMING", "🎮"),
        "cod": ("GAMING", "🎮"),
        "overwatch": ("GAMING", "🎮"),
        "destiny": ("GAMING", "🎮"),
        "wow": ("GAMING", "🎮"),
        "diablo": ("GAMING", "🎮"),
        "hearthstone": ("GAMING", "🎮"),
        "amongus": ("GAMING", "🎮"),
        "fallguys": ("GAMING", "🎮"),
        "pubg": ("GAMING", "🎮"),
        "ark": ("GAMING", "🎮"),
        "terraria": ("GAMING", "🎮"),
        "stardew": ("GAMING", "🎮"),
        "factorio": ("GAMING", "🎮"),
        "rimworld": ("GAMING", "🎮"),
        "civ": ("GAMING", "🎮"),
        "civilization": ("GAMING", "🎮"),
        "stellaris": ("GAMING", "🎮"),
        "europa": ("GAMING", "🎮"),
        "crusader": ("GAMING", "🎮"),
        "hoi": ("GAMING", "🎮"),
        "eldenring": ("GAMING", "🎮"),
        "darksouls": ("GAMING", "🎮"),
        "sekiro": ("GAMING", "🎮"),
        "gta": ("GAMING", "🎮"),
        "rdr": ("GAMING", "🎮"),
        "fifa": ("GAMING", "🎮"),
        "nba": ("GAMING", "🎮"),
        "madden": ("GAMING", "🎮"),
        "hogwarts": ("GAMING", "🎮"),
        "spiderman": ("GAMING", "🎮"),
        "cyberpunk": ("GAMING", "🎮"),
        "witcher": ("GAMING", "🎮"),
        "baldur": ("GAMING", "🎮"),
        "bg3": ("GAMING", "🎮"),
        "xbox": ("GAMING", "🎮"),
        "playnite": ("GAMING", "🎮"),

        # ===== Productivity/Documents =====
        "word": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "winword": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "excel": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "powerpoint": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "powerpnt": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "onenote": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "access": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "msaccess": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "publisher": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "mspub": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "visio": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "project": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "notion": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "obsidian": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "evernote": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "roam": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "logseq": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "craft": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "bear": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "typora": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "marktext": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "acrobat": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "acrord32": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "foxit": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "sumatrapdf": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "pdf": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "libreoffice": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "soffice": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "calc": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "writer": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "impress": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "wps": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "airtable": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "asana": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "trello": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "jira": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "monday": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "clickup": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "todoist": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "ticktick": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "things": ("DOCUMENT/PRODUCTIVITY", "📄"),

        # ===== Music =====
        "spotify": ("MUSIC", "🎵"),
        "apple music": ("MUSIC", "🎵"),
        "itunes": ("MUSIC", "🎵"),
        "soundcloud": ("MUSIC", "🎵"),
        "deezer": ("MUSIC", "🎵"),
        "tidal": ("MUSIC", "🎵"),
        "pandora": ("MUSIC", "🎵"),
        "amazon music": ("MUSIC", "🎵"),
        "foobar": ("MUSIC", "🎵"),
        "foobar2000": ("MUSIC", "🎵"),
        "winamp": ("MUSIC", "🎵"),
        "musicbee": ("MUSIC", "🎵"),
        "aimp": ("MUSIC", "🎵"),
        "clementine": ("MUSIC", "🎵"),
        "rhythmbox": ("MUSIC", "🎵"),
        "audacity": ("MUSIC", "🎵"),

        # ===== Image/Design =====
        "photoshop": ("IMAGE/DESIGN", "🎨"),
        "illustrator": ("IMAGE/DESIGN", "🎨"),
        "indesign": ("IMAGE/DESIGN", "🎨"),
        "xd": ("IMAGE/DESIGN", "🎨"),
        "premiere": ("IMAGE/DESIGN", "🎨"),
        "aftereffects": ("IMAGE/DESIGN", "🎨"),
        "lightroom": ("IMAGE/DESIGN", "🎨"),
        "figma": ("IMAGE/DESIGN", "🎨"),
        "sketch": ("IMAGE/DESIGN", "🎨"),
        "canva": ("IMAGE/DESIGN", "🎨"),
        "gimp": ("IMAGE/DESIGN", "🎨"),
        "gimp-2": ("IMAGE/DESIGN", "🎨"),
        "inkscape": ("IMAGE/DESIGN", "🎨"),
        "krita": ("IMAGE/DESIGN", "🎨"),
        "paint": ("IMAGE/DESIGN", "🎨"),
        "mspaint": ("IMAGE/DESIGN", "🎨"),
        "paint.net": ("IMAGE/DESIGN", "🎨"),
        "paintdotnet": ("IMAGE/DESIGN", "🎨"),
        "affinity": ("IMAGE/DESIGN", "🎨"),
        "coreldraw": ("IMAGE/DESIGN", "🎨"),
        "davinci": ("IMAGE/DESIGN", "🎨"),
        "resolve": ("IMAGE/DESIGN", "🎨"),
        "vegas": ("IMAGE/DESIGN", "🎨"),
        "filmora": ("IMAGE/DESIGN", "🎨"),
        "capcut": ("IMAGE/DESIGN", "🎨"),
        "shotcut": ("IMAGE/DESIGN", "🎨"),
        "kdenlive": ("IMAGE/DESIGN", "🎨"),
        "clip studio": ("IMAGE/DESIGN", "🎨"),
        "procreate": ("IMAGE/DESIGN", "🎨"),
        "aseprite": ("IMAGE/DESIGN", "🎨"),
        "pixelmator": ("IMAGE/DESIGN", "🎨"),
        "snagit": ("IMAGE/DESIGN", "🎨"),
        "greenshot": ("IMAGE/DESIGN", "🎨"),
        "sharex": ("IMAGE/DESIGN", "🎨"),

        # ===== File Management =====
        "explorer": ("FILE MANAGEMENT", "📁"),
        "file explorer": ("FILE MANAGEMENT", "📁"),
        "totalcmd": ("FILE MANAGEMENT", "📁"),
        "totalcommander": ("FILE MANAGEMENT", "📁"),
        "dopus": ("FILE MANAGEMENT", "📁"),
        "doublecmd": ("FILE MANAGEMENT", "📁"),
        "xyplorer": ("FILE MANAGEMENT", "📁"),
        "files": ("FILE MANAGEMENT", "📁"),
        "7zfm": ("FILE MANAGEMENT", "📁"),
        "winrar": ("FILE MANAGEMENT", "📁"),
        "winzip": ("FILE MANAGEMENT", "📁"),
        "bandizip": ("FILE MANAGEMENT", "📁"),
        "filezilla": ("FILE MANAGEMENT", "📁"),
        "winscp": ("FILE MANAGEMENT", "📁"),
        "cyberduck": ("FILE MANAGEMENT", "📁"),

        # ===== Database/DevOps =====
        "dbeaver": ("DATABASE", "🗄️"),
        "pgadmin": ("DATABASE", "🗄️"),
        "mysql workbench": ("DATABASE", "🗄️"),
        "mongodb compass": ("DATABASE", "🗄️"),
        "datagrip": ("DATABASE", "🗄️"),
        "ssms": ("DATABASE", "🗄️"),
        "tableplus": ("DATABASE", "🗄️"),
        "docker": ("DEVOPS", "🐳"),
        "docker desktop": ("DEVOPS", "🐳"),
        "podman": ("DEVOPS", "🐳"),
        "kubernetes": ("DEVOPS", "🐳"),
        "lens": ("DEVOPS", "🐳"),
        "postman": ("API TESTING", "📮"),
        "insomnia": ("API TESTING", "📮"),
        "bruno": ("API TESTING", "📮"),

        # ===== System/Utilities =====
        "taskmgr": ("SYSTEM", "⚙️"),
        "msconfig": ("SYSTEM", "⚙️"),
        "control": ("SYSTEM", "⚙️"),
        "settings": ("SYSTEM", "⚙️"),
        "systemsettings": ("SYSTEM", "⚙️"),
        "regedit": ("SYSTEM", "⚙️"),
        "perfmon": ("SYSTEM", "⚙️"),
        "resmon": ("SYSTEM", "⚙️"),
        "eventvwr": ("SYSTEM", "⚙️"),
        "mmc": ("SYSTEM", "⚙️"),
        "calculator": ("UTILITIES", "🔧"),
        "calc": ("UTILITIES", "🔧"),
        "notepad": ("UTILITIES", "🔧"),
        "wordpad": ("UTILITIES", "🔧"),
        "snipping": ("UTILITIES", "🔧"),
        "snippingtool": ("UTILITIES", "🔧"),
    }

    WEBSITE_CATEGORIES = {
        # Video
        "youtube": ("VIDEO/STREAMING", "🎬"),
        "netflix": ("VIDEO/STREAMING", "🎬"),
        "prime video": ("VIDEO/STREAMING", "🎬"),
        "disney+": ("VIDEO/STREAMING", "🎬"),
        "hbo max": ("VIDEO/STREAMING", "🎬"),
        "hulu": ("VIDEO/STREAMING", "🎬"),
        "twitch": ("VIDEO/STREAMING", "🎬"),
        "vimeo": ("VIDEO/STREAMING", "🎬"),
        "dailymotion": ("VIDEO/STREAMING", "🎬"),
        "crunchyroll": ("VIDEO/STREAMING", "🎬"),
        "funimation": ("VIDEO/STREAMING", "🎬"),
        "peacock": ("VIDEO/STREAMING", "🎬"),
        "paramount+": ("VIDEO/STREAMING", "🎬"),

        # Social
        "twitter": ("SOCIAL MEDIA", "📱"),
        "x.com": ("SOCIAL MEDIA", "📱"),
        "facebook": ("SOCIAL MEDIA", "📱"),
        "instagram": ("SOCIAL MEDIA", "📱"),
        "reddit": ("SOCIAL MEDIA", "📱"),
        "linkedin": ("SOCIAL MEDIA", "📱"),
        "tiktok": ("SOCIAL MEDIA", "📱"),
        "pinterest": ("SOCIAL MEDIA", "📱"),
        "tumblr": ("SOCIAL MEDIA", "📱"),
        "quora": ("SOCIAL MEDIA", "📱"),
        "mastodon": ("SOCIAL MEDIA", "📱"),
        "threads": ("SOCIAL MEDIA", "📱"),
        "bluesky": ("SOCIAL MEDIA", "📱"),

        # Coding
        "github": ("CODING/DEVELOPMENT", "💻"),
        "gitlab": ("CODING/DEVELOPMENT", "💻"),
        "bitbucket": ("CODING/DEVELOPMENT", "💻"),
        "stackoverflow": ("CODING/DEVELOPMENT", "💻"),
        "stack overflow": ("CODING/DEVELOPMENT", "💻"),
        "leetcode": ("CODING/DEVELOPMENT", "💻"),
        "hackerrank": ("CODING/DEVELOPMENT", "💻"),
        "codewars": ("CODING/DEVELOPMENT", "💻"),
        "codeforces": ("CODING/DEVELOPMENT", "💻"),
        "codepen": ("CODING/DEVELOPMENT", "💻"),
        "codesandbox": ("CODING/DEVELOPMENT", "💻"),
        "replit": ("CODING/DEVELOPMENT", "💻"),
        "jsfiddle": ("CODING/DEVELOPMENT", "💻"),
        "glitch": ("CODING/DEVELOPMENT", "💻"),
        "stackblitz": ("CODING/DEVELOPMENT", "💻"),
        "dev.to": ("CODING/DEVELOPMENT", "💻"),
        "medium": ("CODING/DEVELOPMENT", "💻"),
        "hashnode": ("CODING/DEVELOPMENT", "💻"),
        "hacker news": ("CODING/DEVELOPMENT", "💻"),
        "lobste.rs": ("CODING/DEVELOPMENT", "💻"),
        "geeksforgeeks": ("CODING/DEVELOPMENT", "💻"),
        "w3schools": ("CODING/DEVELOPMENT", "💻"),
        "mdn": ("CODING/DEVELOPMENT", "💻"),
        "docs.python": ("CODING/DEVELOPMENT", "💻"),
        "npmjs": ("CODING/DEVELOPMENT", "💻"),
        "pypi": ("CODING/DEVELOPMENT", "💻"),
        "docker hub": ("CODING/DEVELOPMENT", "💻"),
        "vercel": ("CODING/DEVELOPMENT", "💻"),
        "netlify": ("CODING/DEVELOPMENT", "💻"),
        "heroku": ("CODING/DEVELOPMENT", "💻"),
        "aws": ("CODING/DEVELOPMENT", "💻"),
        "azure": ("CODING/DEVELOPMENT", "💻"),
        "google cloud": ("CODING/DEVELOPMENT", "💻"),

        # Shopping
        "amazon": ("SHOPPING", "🛒"),
        "ebay": ("SHOPPING", "🛒"),
        "aliexpress": ("SHOPPING", "🛒"),
        "walmart": ("SHOPPING", "🛒"),
        "target": ("SHOPPING", "🛒"),
        "costco": ("SHOPPING", "🛒"),
        "bestbuy": ("SHOPPING", "🛒"),
        "newegg": ("SHOPPING", "🛒"),
        "etsy": ("SHOPPING", "🛒"),
        "shopify": ("SHOPPING", "🛒"),
        "wish": ("SHOPPING", "🛒"),
        "flipkart": ("SHOPPING", "🛒"),
        "daraz": ("SHOPPING", "🛒"),
        "lazada": ("SHOPPING", "🛒"),
        "shopee": ("SHOPPING", "🛒"),

        # News
        "cnn": ("NEWS", "📰"),
        "bbc": ("NEWS", "📰"),
        "reuters": ("NEWS", "📰"),
        "news": ("NEWS", "📰"),
        "nytimes": ("NEWS", "📰"),
        "washingtonpost": ("NEWS", "📰"),
        "guardian": ("NEWS", "📰"),
        "aljazeera": ("NEWS", "📰"),
        "fox": ("NEWS", "📰"),
        "msnbc": ("NEWS", "📰"),
        "npr": ("NEWS", "📰"),
        "time": ("NEWS", "📰"),
        "huffpost": ("NEWS", "📰"),
        "buzzfeed": ("NEWS", "📰"),
        "vice": ("NEWS", "📰"),
        "techcrunch": ("NEWS", "📰"),
        "wired": ("NEWS", "📰"),
        "arstechnica": ("NEWS", "📰"),
        "theverge": ("NEWS", "📰"),
        "engadget": ("NEWS", "📰"),

        # Education
        "coursera": ("EDUCATION", "📚"),
        "udemy": ("EDUCATION", "📚"),
        "udacity": ("EDUCATION", "📚"),
        "edx": ("EDUCATION", "📚"),
        "khan academy": ("EDUCATION", "📚"),
        "skillshare": ("EDUCATION", "📚"),
        "linkedin learning": ("EDUCATION", "📚"),
        "pluralsight": ("EDUCATION", "📚"),
        "codecademy": ("EDUCATION", "📚"),
        "freecodecamp": ("EDUCATION", "📚"),
        "brilliant": ("EDUCATION", "📚"),
        "duolingo": ("EDUCATION", "📚"),
        "memrise": ("EDUCATION", "📚"),
        "wikipedia": ("EDUCATION", "📚"),
        "quizlet": ("EDUCATION", "📚"),
        "studocu": ("EDUCATION", "📚"),
        "chegg": ("EDUCATION", "📚"),

        # Email
        "gmail": ("COMMUNICATION", "💬"),
        "outlook": ("COMMUNICATION", "💬"),
        "mail": ("COMMUNICATION", "💬"),
        "yahoo mail": ("COMMUNICATION", "💬"),
        "protonmail": ("COMMUNICATION", "💬"),
        "proton": ("COMMUNICATION", "💬"),
        "zoho": ("COMMUNICATION", "💬"),

        # Music
        "spotify": ("MUSIC", "🎵"),
        "soundcloud": ("MUSIC", "🎵"),
        "apple music": ("MUSIC", "🎵"),
        "deezer": ("MUSIC", "🎵"),
        "tidal": ("MUSIC", "🎵"),
        "pandora": ("MUSIC", "🎵"),
        "last.fm": ("MUSIC", "🎵"),
        "bandcamp": ("MUSIC", "🎵"),

        # AI Tools
        "chatgpt": ("AI ASSISTANT", "🤖"),
        "chat.openai": ("AI ASSISTANT", "🤖"),
        "claude": ("AI ASSISTANT", "🤖"),
        "anthropic": ("AI ASSISTANT", "🤖"),
        "gemini": ("AI ASSISTANT", "🤖"),
        "bard": ("AI ASSISTANT", "🤖"),
        "copilot": ("AI ASSISTANT", "🤖"),
        "bing chat": ("AI ASSISTANT", "🤖"),
        "perplexity": ("AI ASSISTANT", "🤖"),
        "you.com": ("AI ASSISTANT", "🤖"),
        "phind": ("AI ASSISTANT", "🤖"),
        "poe": ("AI ASSISTANT", "🤖"),
        "huggingface": ("AI ASSISTANT", "🤖"),
        "midjourney": ("AI ASSISTANT", "🤖"),
        "dalle": ("AI ASSISTANT", "🤖"),
        "stable diffusion": ("AI ASSISTANT", "🤖"),
        "leonardo.ai": ("AI ASSISTANT", "🤖"),

        # Finance/Banking
        "bank": ("FINANCE", "💰"),
        "paypal": ("FINANCE", "💰"),
        "venmo": ("FINANCE", "💰"),
        "stripe": ("FINANCE", "💰"),
        "robinhood": ("FINANCE", "💰"),
        "coinbase": ("FINANCE", "💰"),
        "binance": ("FINANCE", "💰"),
        "kraken": ("FINANCE", "💰"),
        "fidelity": ("FINANCE", "💰"),
        "schwab": ("FINANCE", "💰"),
        "vanguard": ("FINANCE", "💰"),
        "mint": ("FINANCE", "💰"),
        "ynab": ("FINANCE", "💰"),

        # Productivity
        "google docs": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "google sheets": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "google slides": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "drive.google": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "dropbox": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "onedrive": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "box": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "notion": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "airtable": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "trello": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "asana": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "monday": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "jira": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "confluence": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "miro": ("DOCUMENT/PRODUCTIVITY", "📄"),
        "figma": ("IMAGE/DESIGN", "🎨"),
        "canva": ("IMAGE/DESIGN", "🎨"),
    }

    IGNORED_APPS = [
        'claude_front', 'neurolens', 'flutter', 'dart', 'monitoring', 'camera',
    ]

    IGNORED_TITLES = [
        'claude_front', 'neurolens', 'analyzing', 'recording', 'camera',
        'emotion detection', 'mental well-being', 'dashboard', 'monitoring',
    ]

    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self._last_valid_result = None

    def get_active_window_title(self) -> str:
        hwnd = self.user32.GetForegroundWindow()
        length = self.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value

    def get_active_process_name(self) -> str:
        hwnd = self.user32.GetForegroundWindow()
        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = self.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)

        if handle:
            buf = ctypes.create_unicode_buffer(260)
            size = wintypes.DWORD(260)
            self.kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size))
            self.kernel32.CloseHandle(handle)
            path = buf.value
            if path:
                return os.path.basename(path).lower().replace('.exe', '')
        return ""

    def categorize_from_window(self) -> Dict:
        title = self.get_active_window_title().lower()
        process = self.get_active_process_name()

        # Check if this is an ignored app (the monitoring app itself)
        is_ignored = any(ignored in process for ignored in self.IGNORED_APPS) or \
                     any(ignored in title for ignored in self.IGNORED_TITLES)

        if is_ignored:
            if self._last_valid_result:
                cached = self._last_valid_result.copy()
                cached['source'] = 'cached'
                return cached
            return {
                'app': 'monitoring',
                'title': 'NeuroLens Active',
                'category': 'MONITORING',
                'emoji': '📱',
                'confidence': 'Low',
                'source': 'monitoring_app'
            }

        result = {
            'app': process,
            'title': self.get_active_window_title(),
            'category': None,
            'emoji': '🏷️',
            'confidence': 'Low',
            'source': 'window_api'
        }

        # Check process name
        for app_key, (category, emoji) in self.APP_CATEGORIES.items():
            if app_key in process:
                result['category'] = category
                result['emoji'] = emoji
                result['confidence'] = 'Very High'
                self._last_valid_result = result.copy()
                return result

        # Check window title for websites
        for site_key, (category, emoji) in self.WEBSITE_CATEGORIES.items():
            if site_key in title:
                result['category'] = category
                result['emoji'] = emoji
                result['confidence'] = 'High'
                self._last_valid_result = result.copy()
                return result

        # Check title against app categories
        for app_key, (category, emoji) in self.APP_CATEGORIES.items():
            if app_key in title:
                result['category'] = category
                result['emoji'] = emoji
                result['confidence'] = 'High'
                self._last_valid_result = result.copy()
                return result

        # No category match but valid app
        if result['app']:
            result['category'] = 'OTHER'
            self._last_valid_result = result.copy()

        return result
