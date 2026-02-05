"""
Screen Content Classifier v5.1 - MAXIMUM ACCURACY VERSION
Combines Windows API + BLIP AI + Sentiment + Translation + OCR + Activity + ML Productivity

Features:
- Active window title detection via Windows API (99% accuracy)
- BLIP vision model for visual content description
- OCR text extraction for enhanced content analysis
- Sentiment analysis (Positive/Negative/Neutral)
- Language detection and automatic translation to English
- Activity Classification (Writing/Reading/Watching/Coding/etc.)
- ML-Based Productivity Classification (Productive/Neutral/Unproductive)
- 200+ apps/websites in detection database
"""

import os
import sys
import time
import ctypes
import re
from ctypes import wintypes
from datetime import datetime
from typing import Optional, Tuple, Dict, List

# Screen capture
import mss
from PIL import Image

# AI Models
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration
from transformers import pipeline

# Language detection and translation
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator

# OCR
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("⚠️ pytesseract not installed. OCR features disabled.")

# ============================================================================
# Model Cache Configuration - Save all models in the same folder as this code
# ============================================================================
MODEL_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models_cache")
os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
os.environ["TRANSFORMERS_CACHE"] = MODEL_CACHE_DIR
os.environ["HF_HOME"] = MODEL_CACHE_DIR
print(f"📁 Model cache directory: {MODEL_CACHE_DIR}")


# ============================================================================
# OCR Text Extractor
# ============================================================================

class OCRExtractor:
    """Extracts text from screenshots using Tesseract OCR."""
    
    def __init__(self):
        self.available = OCR_AVAILABLE
        if self.available:
            # Try to find Tesseract
            tesseract_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                r"C:\Tesseract-OCR\tesseract.exe",
            ]
            for path in tesseract_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    break
            
            print("🔄 Testing OCR capability...")
            try:
                # Test OCR
                test_img = Image.new('RGB', (100, 30), color='white')
                pytesseract.image_to_string(test_img)
                print("✅ OCR ready!")
            except Exception as e:
                self.available = False
                print(f"⚠️ OCR not available: {e}")
                print("   Install Tesseract from: https://github.com/tesseract-ocr/tesseract")
    
    def extract_text(self, image: Image.Image, max_chars: int = 500) -> str:
        """Extract text from image using OCR."""
        if not self.available:
            return ""
        
        try:
            # Resize for faster OCR
            ratio = 1920 / max(image.size)
            if ratio < 1:
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Extract text
            text = pytesseract.image_to_string(image, timeout=5)
            
            # Clean up text
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:max_chars]
        except Exception:
            return ""


# ============================================================================
# Sentiment Analyzer
# ============================================================================

class SentimentAnalyzer:
    """Analyzes sentiment with context-awareness for different content types."""
    
    # Technical/neutral patterns - these shouldn't have emotional sentiment
    NEUTRAL_PATTERNS = [
        # File extensions
        r'\.\w{2,4}$', r'\.py', r'\.js', r'\.ts', r'\.cpp', r'\.java', r'\.html', r'\.css',
        r'\.json', r'\.xml', r'\.md', r'\.txt', r'\.exe', r'\.dll', r'\.pdf',
        # Code/dev terms
        r'code', r'script', r'function', r'class', r'module', r'package', r'debug',
        r'compile', r'build', r'test', r'deploy', r'config', r'settings',
        r'git', r'commit', r'push', r'pull', r'merge', r'branch',
        # IDE/Editor names
        r'visual studio', r'pycharm', r'intellij', r'sublime', r'notepad',
        r'antigravity', r'cursor', r'vscode', r'terminal', r'powershell', r'cmd',
        # System
        r'explorer', r'system', r'admin', r'properties', r'folder', r'directory',
    ]
    
    # Categories that should be NEUTRAL by default
    NEUTRAL_CATEGORIES = [
        'CODING/DEVELOPMENT', 'FILE MANAGEMENT', 'SYSTEM', 'UTILITIES',
        'DATABASE', 'DEVOPS', 'API TESTING'
    ]
    
    def __init__(self):
        print("🔄 Loading sentiment analysis model...")
        self.analyzer = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
            framework="pt",
            device=0 if torch.cuda.is_available() else -1,
            model_kwargs={"cache_dir": MODEL_CACHE_DIR}
        )
        print("✅ Sentiment model loaded!")
    
    def analyze(self, text: str, category: str = None) -> Dict:
        """
        Analyze sentiment of text with context-awareness.
        
        Args:
            text: Text to analyze
            category: Content category (optional) - technical categories = NEUTRAL
        """
        if not text or len(text.strip()) < 3:
            return {'sentiment': 'NEUTRAL', 'score': 0.5, 'emoji': '😐'}
        
        # Check if category is technical (should be neutral)
        if category and category in self.NEUTRAL_CATEGORIES:
            return {'sentiment': 'NEUTRAL', 'score': 0.5, 'emoji': '💻'}
        
        # Check for technical patterns in text
        text_lower = text.lower()
        for pattern in self.NEUTRAL_PATTERNS:
            if re.search(pattern, text_lower):
                return {'sentiment': 'NEUTRAL', 'score': 0.5, 'emoji': '💻'}
        
        try:
            clean_text = re.sub(r'[^\w\s]', '', text)[:512]
            
            if len(clean_text.strip()) < 3:
                return {'sentiment': 'NEUTRAL', 'score': 0.5, 'emoji': '😐'}
            
            result = self.analyzer(clean_text)[0]
            
            sentiment = result['label']
            score = result['score']
            
            if sentiment == 'POSITIVE':
                if score > 0.9:
                    emoji = '😄'
                elif score > 0.7:
                    emoji = '🙂'
                else:
                    emoji = '😊'
            else:
                if score > 0.9:
                    emoji = '😢'
                elif score > 0.7:
                    emoji = '😕'
                else:
                    emoji = '😐'
            
            return {'sentiment': sentiment, 'score': score, 'emoji': emoji}
        except Exception:
            return {'sentiment': 'NEUTRAL', 'score': 0.5, 'emoji': '😐'}



# ============================================================================
# Activity Classifier
# ============================================================================

class ActivityClassifier:
    """Classifies what type of activity the user is performing."""
    
    # Activity definitions with keywords, apps, and categories
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
            'ocr_keywords': ['type here', 'enter text', 'compose', 'write']
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
            'ocr_keywords': ['read more', 'continue reading', 'scroll', 'page']
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
            'ocr_keywords': ['play', 'pause', 'volume', 'fullscreen', 'subtitles']
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
            'ocr_keywords': ['def ', 'class ', 'function', 'import ', 'const ', 'let ', 'var ']
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
            'ocr_keywords': ['search', 'google', 'browse', 'home']
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
            'ocr_keywords': ['health', 'mana', 'score', 'level', 'xp', 'quest']
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
            'ocr_keywords': ['layer', 'brush', 'color', 'filter', 'canvas', 'tool']
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
            'ocr_keywords': ['send', 'reply', 'message', 'call', 'inbox', 'chat']
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
            'ocr_keywords': ['play', 'pause', 'skip', 'shuffle', 'repeat', 'volume']
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
            'ocr_keywords': ['search', 'results', 'found', 'pages', 'showing']
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
            'ocr_keywords': ['add to cart', 'buy now', 'checkout', 'price', '$']
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
            'ocr_keywords': ['lesson', 'module', 'chapter', 'quiz', 'continue', 'progress']
        },
    }
    
    def __init__(self):
        print("✅ Activity classifier ready!")
    
    def classify(self, app_name: str, window_title: str, category: str,
                 visual_caption: str = "", ocr_text: str = "") -> Dict:
        """
        Classify the user's current activity.
        
        Returns:
            Dict with 'activity', 'emoji', 'confidence', and 'reason'
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
            ocr_matches = sum(1 for kw in config['ocr_keywords'] if kw in ocr_lower)
            if ocr_matches > 0:
                score += min(ocr_matches, 2)
                reason_parts.append("ocr text")
            
            # Check visual caption (1 point)
            if any(kw in caption_lower for kw in config['keywords'][:5]):
                score += 1
                reason_parts.append("visual")
            
            if score > 0:
                scores[activity] = score
                reasons[activity] = ", ".join(reason_parts)
        
        # Get best match
        if scores:
            best_activity = max(scores, key=scores.get)
            best_score = scores[best_activity]
            
            # Determine confidence
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
        
        # Default fallback
        return {
            'activity': 'BROWSING',
            'emoji': '🌐',
            'confidence': 'Low',
            'score': 0,
            'reason': 'default'
        }


# ============================================================================
# Activity Productivity Classifier (ML-Based)
# ============================================================================

class ActivityProductivityClassifier:
    """
    ML-based classifier for determining if user's activity is 
    PRODUCTIVE (positive), NEUTRAL, or UNPRODUCTIVE (negative).
    
    Uses zero-shot classification for intelligent, context-aware analysis
    instead of hardcoded rules.
    """
    
    # Classification labels for zero-shot
    PRODUCTIVITY_LABELS = [
        "productive work activity",
        "neutral activity", 
        "unproductive entertainment activity"
    ]
    
    # More detailed labels for higher accuracy
    DETAILED_LABELS = [
        "programming and software development",
        "learning and education",
        "writing and content creation",
        "professional work and productivity",
        "communication and collaboration",
        "casual web browsing",
        "entertainment and gaming",
        "social media and distraction",
        "online shopping"
    ]
    
    # Map detailed labels to productivity categories
    LABEL_MAPPING = {
        "programming and software development": ("PRODUCTIVE", "✅", 5),
        "learning and education": ("PRODUCTIVE", "✅", 5),
        "writing and content creation": ("PRODUCTIVE", "✅", 4),
        "professional work and productivity": ("PRODUCTIVE", "✅", 4),
        "communication and collaboration": ("NEUTRAL", "➖", 0),
        "casual web browsing": ("NEUTRAL", "➖", 0),
        "entertainment and gaming": ("UNPRODUCTIVE", "⚠️", -3),
        "social media and distraction": ("UNPRODUCTIVE", "⚠️", -2),
        "online shopping": ("NEUTRAL", "➖", -1),
    }
    
    def __init__(self):
        print("🔄 Loading zero-shot classification model for productivity...")
        try:
            self.classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                framework="pt",
                device=0 if torch.cuda.is_available() else -1,
                model_kwargs={"cache_dir": MODEL_CACHE_DIR}
            )
            self.model_available = True
            print("✅ Productivity classification model loaded!")
        except Exception as e:
            print(f"⚠️ Zero-shot model not available: {e}")
            print("   Falling back to rule-based classification")
            self.model_available = False
            self.classifier = None
    
    def _build_context(self, activity: str, category: str, app_name: str,
                       window_title: str, ocr_text: str = "") -> str:
        """Build a context string for the classifier."""
        parts = []
        
        if app_name:
            parts.append(f"Using {app_name}")
        if activity:
            parts.append(f"Activity: {activity}")
        if category:
            parts.append(f"Category: {category}")
        if window_title:
            # Clean the title
            clean_title = window_title[:100]
            parts.append(f"Window: {clean_title}")
        if ocr_text:
            parts.append(f"Content: {ocr_text[:100]}")
        
        return ". ".join(parts)
    
    def classify(self, activity: str, category: str, app_name: str,
                 window_title: str, ocr_text: str = "") -> Dict:
        """
        Classify whether the user's activity is productive using ML.
        
        Returns:
            Dict with 'classification', 'emoji', 'score', 'confidence', 'reason'
        """
        context = self._build_context(activity, category, app_name, window_title, ocr_text)
        
        if not self.model_available or not context.strip():
            return self._fallback_classify(activity, category)
        
        try:
            # Use detailed labels for more accurate classification
            result = self.classifier(
                context,
                candidate_labels=self.DETAILED_LABELS,
                multi_label=False
            )
            
            top_label = result['labels'][0]
            top_score = result['scores'][0]
            
            # Map to productivity category
            if top_label in self.LABEL_MAPPING:
                classification, emoji, score = self.LABEL_MAPPING[top_label]
            else:
                classification, emoji, score = "NEUTRAL", "➖", 0
            
            # Determine confidence based on model score
            if top_score >= 0.7:
                confidence = "Very High"
            elif top_score >= 0.5:
                confidence = "High"
            elif top_score >= 0.3:
                confidence = "Medium"
            else:
                confidence = "Low"
            
            return {
                'classification': classification,
                'emoji': emoji,
                'score': score,
                'confidence': confidence,
                'reason': f"{top_label} ({top_score:.0%})"
            }
            
        except Exception as e:
            return self._fallback_classify(activity, category)
    
    def _fallback_classify(self, activity: str, category: str) -> Dict:
        """Fallback rule-based classification if ML fails."""
        activity_upper = activity.upper() if activity else ""
        category_upper = category.upper() if category else ""
        
        # Basic activity-based classification
        productive_activities = ['CODING', 'LEARNING', 'WRITING', 'READING', 'DESIGNING']
        unproductive_activities = ['GAMING', 'WATCHING', 'SHOPPING']
        
        productive_categories = ['CODING/DEVELOPMENT', 'EDUCATION', 'DOCUMENT/PRODUCTIVITY']
        unproductive_categories = ['GAMING', 'VIDEO/STREAMING', 'SOCIAL MEDIA']
        
        if activity_upper in productive_activities or category_upper in productive_categories:
            return {
                'classification': "PRODUCTIVE",
                'emoji': "✅",
                'score': 3,
                'confidence': "Medium",
                'reason': f"{activity_upper} activity (fallback)"
            }
        elif activity_upper in unproductive_activities or category_upper in unproductive_categories:
            return {
                'classification': "UNPRODUCTIVE", 
                'emoji': "⚠️",
                'score': -2,
                'confidence': "Medium",
                'reason': f"{activity_upper} activity (fallback)"
            }
        else:
            return {
                'classification': "NEUTRAL",
                'emoji': "➖",
                'score': 0,
                'confidence': "Low",
                'reason': "general activity (fallback)"
            }


# ============================================================================
# Language Detector and Translator
# ============================================================================

class LanguageProcessor:
    """Detects language and translates to English using ML models."""
    
    LANGUAGE_NAMES = {
        'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
        'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian', 'ja': 'Japanese',
        'ko': 'Korean', 'zh-cn': 'Chinese', 'zh-tw': 'Chinese', 'ar': 'Arabic', 
        'hi': 'Hindi', 'ur': 'Urdu', 'bn': 'Bengali', 'pa': 'Punjabi', 
        'ta': 'Tamil', 'te': 'Telugu', 'th': 'Thai', 'vi': 'Vietnamese', 
        'id': 'Indonesian', 'ms': 'Malay', 'tr': 'Turkish', 'nl': 'Dutch', 
        'pl': 'Polish', 'uk': 'Ukrainian', 'cs': 'Czech', 'sv': 'Swedish', 
        'da': 'Danish', 'no': 'Norwegian', 'fi': 'Finnish', 'el': 'Greek', 
        'he': 'Hebrew', 'fa': 'Persian', 'sw': 'Swahili', 'hu': 'Hungarian', 
        'ro': 'Romanian', 'af': 'Afrikaans',
    }
    
    # Common Hindi/Urdu/Hinglish words for detection
    HINDI_URDU_KEYWORDS = [
        'lamhein', 'lamhe', 'dil', 'pyar', 'ishq', 'mohabbat', 'zindagi', 
        'dard', 'deewana', 'sanam', 'jaane', 'naina', 'aankhen', 'sapne',
        'khwaab', 'tera', 'mera', 'tere', 'mere', 'humein', 'tumhe', 
        'beetein', 'beete', 'yaadein', 'yaad', 'alvida', 'judaai', 'milna',
        'chahun', 'chahat', 'ashiqui', 'dhadkan', 'saathi', 'junoon',
        'kaise', 'kyun', 'kahan', 'kabhi', 'abhi', 'phir', 'fir', 'kabse',
        'rishta', 'bandhan', 'milan', 'virah', 'judaai', 'intezaar',
        'mashup', 'lofi', 'slowed', 'reverb', 'arijit', 'atif', 'rahat',
        'nusrat', 'sonu', 'nigam', 'kumar', 'sanu', 'kishore', 'lata',
        'asha', 'rafi', 'mukesh', 'hemant', 'jagjit', 'pankaj', 'udhas',
        'bollywood', 'pakistani', 'coke studio', 'ost', 'drama',
        'kya', 'hai', 'hain', 'nahi', 'nahin', 'acha', 'accha', 'theek',
        'karo', 'karna', 'jao', 'aao', 'bhai', 'yaar', 'beta', 'beti',
    ]
    
    def __init__(self):
        print("🔄 Initializing language processor...")
        
        # Google Translate for non-Hindi languages
        self.translator = GoogleTranslator(source='auto', target='en')
        
        # Load Hinglish translator model for romanized Hindi
        print("🔄 Loading Hinglish translation model...")
        try:
            self.hinglish_translator = pipeline(
                "text2text-generation",
                model="rudrashah/RLM-hinglish-translator",
                framework="pt",
                device=0 if torch.cuda.is_available() else -1,
                model_kwargs={"cache_dir": MODEL_CACHE_DIR}
            )
            self.hinglish_available = True
            print("✅ Hinglish translation model loaded!")
        except Exception as e:
            print(f"⚠️ Hinglish model not available: {e}")
            print("   Falling back to Google Translate")
            self.hinglish_available = False
        
        print("✅ Language processor ready!")
    
    def detect_language(self, text: str) -> str:
        """Detect language with special handling for Hindi/Urdu."""
        if not text or len(text.strip()) < 3:
            return 'en'
        
        text_lower = text.lower()
        
        # Check for Hindi/Urdu keywords first
        hindi_score = sum(1 for kw in self.HINDI_URDU_KEYWORDS if kw in text_lower)
        if hindi_score >= 1:
            return 'hi'  # Hindi
        
        try:
            detected = detect(text)
            # Correct common misdetections
            # 'af' (Afrikaans) is often wrongly detected for Hindi song titles
            if detected == 'af' and any(kw in text_lower for kw in self.HINDI_URDU_KEYWORDS):
                return 'hi'
            return detected
        except LangDetectException:
            return 'en'
    
    def get_language_name(self, lang_code: str) -> str:
        return self.LANGUAGE_NAMES.get(lang_code, lang_code.upper())
    
    def translate_to_english(self, text: str) -> Dict:
        """Translate text to English using ML models."""
        if not text or len(text.strip()) < 3:
            return {
                'original': text, 'translated': text, 'source_lang': 'en',
                'language_name': 'English', 'was_translated': False
            }
        
        try:
            lang = self.detect_language(text)
            lang_name = self.get_language_name(lang)
            
            if lang == 'en':
                return {
                    'original': text, 'translated': text, 'source_lang': 'en',
                    'language_name': 'English', 'was_translated': False
                }
            
            # For Hindi/Urdu: Use Hinglish ML model (handles romanized Hindi)
            if lang in ['hi', 'ur'] and self.hinglish_available:
                try:
                    # Use the ML model
                    result = self.hinglish_translator(text, max_length=256)[0]
                    translated = result.get('generated_text', text)
                    
                    if translated and translated.lower() != text.lower():
                        return {
                            'original': text, 'translated': translated, 'source_lang': lang,
                            'language_name': lang_name, 'was_translated': True
                        }
                except Exception:
                    pass  # Fall through to Google Translate
            
            # Try Google Translate for other languages
            try:
                translated = self.translator.translate(text)
                if translated and translated.lower() != text.lower():
                    return {
                        'original': text, 'translated': translated, 'source_lang': lang,
                        'language_name': lang_name, 'was_translated': True
                    }
            except Exception:
                pass
            
            # Fallback: return original with language tag
            return {
                'original': text, 'translated': f"[{lang_name}] {text}", 
                'source_lang': lang, 'language_name': lang_name, 'was_translated': True
            }
            
        except Exception:
            return {
                'original': text, 'translated': text, 'source_lang': 'unknown',
                'language_name': 'Unknown', 'was_translated': False
            }



# ============================================================================
# Windows API for Active Window Detection - EXPANDED DATABASE
# ============================================================================

class WindowsAPI:
    """Windows API utilities with 200+ app/website detection."""
    
    # EXPANDED App category mappings - 200+ apps
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
    
    # EXPANDED Website category mappings
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
    
    # Apps/windows to IGNORE when detecting content (these are the monitoring apps themselves)
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
        self._last_valid_result = None  # Cache last valid (non-ignored) result
    
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
            # Return cached result if available
            if self._last_valid_result:
                cached = self._last_valid_result.copy()
                cached['source'] = 'cached'
                return cached
            # No cache, return generic
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
        
        # No category match but valid app - cache as OTHER
        if result['app']:
            result['category'] = 'OTHER'
            self._last_valid_result = result.copy()
        
        return result


# ============================================================================
# Screen Capture
# ============================================================================

class ScreenCapture:
    def __init__(self, monitor_index: int = 1):
        self.sct = mss.mss()
        self.monitor_index = monitor_index
    
    def capture(self) -> Image.Image:
        monitor = self.sct.monitors[self.monitor_index]
        screenshot = self.sct.grab(monitor)
        return Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)
    
    def close(self):
        self.sct.close()


# ============================================================================
# BLIP Visual Classifier
# ============================================================================

class VisualClassifier:
    def __init__(self, device: Optional[str] = None):
        print("🔄 Loading BLIP vision model...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu" if device is None else device
        print(f"   Using device: {self.device}")
        
        self.processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base", cache_dir=MODEL_CACHE_DIR)
        self.model = BlipForConditionalGeneration.from_pretrained(
            "Salesforce/blip-image-captioning-base",
            cache_dir=MODEL_CACHE_DIR
        ).to(self.device)
        print("✅ BLIP model loaded!")
    
    def generate_caption(self, image: Image.Image) -> str:
        ratio = 384 / max(image.size)
        if ratio < 1:
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        inputs = self.processor(image, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            output = self.model.generate(**inputs, max_length=50, num_beams=5, early_stopping=True)
        
        return self.processor.decode(output[0], skip_special_tokens=True)


# ============================================================================
# Hybrid Content Analyzer - ENHANCED
# ============================================================================

class HybridAnalyzer:
    """Enhanced analyzer with OCR support and activity classification."""
    
    def __init__(self, enable_ocr: bool = True):
        self.windows_api = WindowsAPI()
        self.visual_classifier = VisualClassifier()
        self.screen_capture = ScreenCapture()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.language_processor = LanguageProcessor()
        self.activity_classifier = ActivityClassifier()
        self.productivity_classifier = ActivityProductivityClassifier()
        
        if enable_ocr:
            self.ocr = OCRExtractor()
        else:
            self.ocr = None
        
        print("\n✅ All models loaded! Starting monitoring...\n")
    
    def analyze(self) -> Dict:
        window_result = self.windows_api.categorize_from_window()
        screenshot = self.screen_capture.capture()
        visual_caption = self.visual_classifier.generate_caption(screenshot)
        
        # OCR text extraction
        ocr_text = ""
        if self.ocr and self.ocr.available:
            ocr_text = self.ocr.extract_text(screenshot)
        
        # Category determination (needed for sentiment context)
        if window_result['category'] is not None:
            category = window_result['category']
            emoji = window_result['emoji']
            confidence = window_result['confidence']
            source = 'hybrid'
        else:
            # Try OCR-based detection
            ocr_category = self._detect_from_ocr(ocr_text)
            if ocr_category:
                category, emoji = ocr_category
                confidence = 'High'
                source = 'ocr'
            else:
                category, emoji = self._infer_from_caption(visual_caption)
                confidence = 'Medium'
                source = 'visual_only'
        
        # Combine title + OCR text for better analysis
        combined_text = window_result['title']
        if ocr_text:
            combined_text = f"{window_result['title']} {ocr_text[:200]}"
        
        # Language and translation
        title_lang = self.language_processor.translate_to_english(window_result['title'])
        
        # Sentiment on combined text (pass category for context-aware analysis)
        text_for_sentiment = title_lang['translated'] if title_lang['was_translated'] else combined_text
        sentiment = self.sentiment_analyzer.analyze(text_for_sentiment, category=category)
        
        # Activity classification
        activity = self.activity_classifier.classify(
            app_name=window_result['app'],
            window_title=window_result['title'],
            category=category,
            visual_caption=visual_caption,
            ocr_text=ocr_text
        )
        
        # Productivity classification (positive/neutral/negative)
        productivity = self.productivity_classifier.classify(
            activity=activity['activity'],
            category=category,
            app_name=window_result['app'],
            window_title=window_result['title'],
            ocr_text=ocr_text
        )
        
        return {
            'app_name': window_result['app'],
            'window_title': window_result['title'],
            'visual_description': visual_caption,
            'ocr_text': ocr_text[:100] + '...' if len(ocr_text) > 100 else ocr_text,
            'category': category,
            'emoji': emoji,
            'confidence': confidence,
            'analysis_source': source,
            'original_language': title_lang['language_name'],
            'was_translated': title_lang['was_translated'],
            'translated_title': title_lang['translated'] if title_lang['was_translated'] else None,
            'sentiment': sentiment['sentiment'],
            'sentiment_score': sentiment['score'],
            'sentiment_emoji': sentiment['emoji'],
            'activity': activity['activity'],
            'activity_emoji': activity['emoji'],
            'activity_confidence': activity['confidence'],
            'productivity': productivity['classification'],
            'productivity_emoji': productivity['emoji'],
            'productivity_confidence': productivity['confidence'],
            'productivity_reason': productivity['reason'],
        }
    
    def _detect_from_ocr(self, ocr_text: str) -> Optional[Tuple[str, str]]:
        """Detect category from OCR text."""
        if not ocr_text:
            return None
        
        text_lower = ocr_text.lower()
        
        # Keywords to detect
        detections = {
            ("python", "java", "javascript", "function", "class", "import", "def ", "const ", "var ", "public", "private"): ("CODING/DEVELOPMENT", "💻"),
            ("subscribe", "views", "likes", "video", "watch", "play", "pause"): ("VIDEO/STREAMING", "🎬"),
            ("tweet", "retweet", "follower", "following", "post", "share", "like"): ("SOCIAL MEDIA", "📱"),
            ("health", "damage", "level", "score", "player", "quest", "inventory"): ("GAMING", "🎮"),
            ("inbox", "compose", "send", "reply", "forward", "email"): ("COMMUNICATION", "💬"),
            ("cart", "checkout", "buy", "price", "$", "add to", "shipping"): ("SHOPPING", "🛒"),
            ("breaking", "headline", "reporter", "exclusive", "update"): ("NEWS", "📰"),
            ("learn", "course", "lesson", "quiz", "chapter", "module"): ("EDUCATION", "📚"),
        }
        
        for keywords, result in detections.items():
            if any(kw in text_lower for kw in keywords):
                return result
        
        return None
    
    def _infer_from_caption(self, caption: str) -> Tuple[str, str]:
        caption_lower = caption.lower()
        
        inferences = {
            ("game", "gaming", "player", "score"): ("GAMING", "🎮"),
            ("video", "movie", "film", "watching", "streaming"): ("VIDEO/STREAMING", "🎬"),
            ("code", "programming", "terminal", "editor"): ("CODING/DEVELOPMENT", "💻"),
            ("document", "text", "writing", "word"): ("DOCUMENT/PRODUCTIVITY", "📄"),
            ("photo", "image", "picture", "design"): ("IMAGE/DESIGN", "🎨"),
            ("chat", "message", "conversation", "email"): ("COMMUNICATION", "💬"),
            ("music", "audio", "song", "playing"): ("MUSIC", "🎵"),
        }
        
        for keywords, (cat, emoji) in inferences.items():
            if any(kw in caption_lower for kw in keywords):
                return (cat, emoji)
        
        return ("OTHER", "🏷️")
    
    def close(self):
        self.screen_capture.close()


# ============================================================================
# Main Application
# ============================================================================

class ScreenMonitor:
    def __init__(self, interval: float = 3.0, enable_ocr: bool = True):
        self.interval = interval
        self.analyzer = HybridAnalyzer(enable_ocr=enable_ocr)
        self.running = False
    
    def print_header(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print("╔════════════════════════════════════════════════════════════════════════════════╗")
        print("║              🖥️  SCREEN CONTENT CLASSIFIER v5.1 (ML ENHANCED)                 ║")
        print("║       Windows API + BLIP AI + OCR + Activity + ML Productivity           ║")
        print("║       200+ Apps | Zero-Shot ML Classification | Ctrl+C to stop           ║")
        print("╚════════════════════════════════════════════════════════════════════════════════╝")
        print()
    
    def print_result(self, result: Dict):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Truncate long strings
        app_name = (result['app_name'][:18] + '...') if len(result['app_name']) > 21 else result['app_name']
        window_title = (result['window_title'][:42] + '...') if len(result['window_title']) > 45 else result['window_title']
        visual_desc = (result['visual_description'][:42] + '...') if len(result['visual_description']) > 45 else result['visual_description']
        ocr_text = result.get('ocr_text', '')[:42]
        if len(result.get('ocr_text', '')) > 45:
            ocr_text += '...'
        category = result['category'] or 'UNKNOWN'
        
        print(f"[{timestamp}] Analysis Complete")
        print("┌────────────────────────────────────────────────────────────────────────────────────┐")
        print(f"│ 📌 App: {app_name:<72} │")
        print(f"│ 📝 Title: {window_title:<70} │")
        print(f"│ 👁️  Visual: {visual_desc:<68} │")
        if ocr_text:
            print(f"│ 📖 OCR: {ocr_text:<72} │")
        print("├────────────────────────────────────────────────────────────────────────────────────┤")
        print(f"│ {result['emoji']} Category: {category:<59} │")
        
        # Activity type (WRITING, READING, WATCHING, etc.)
        activity = result.get('activity', 'UNKNOWN')
        activity_emoji = result.get('activity_emoji', '🏷️')
        activity_conf = result.get('activity_confidence', 'Low')
        activity_text = f"{activity} ({activity_conf})"
        print(f"│ {activity_emoji} Activity: {activity_text:<59} │")
        
        print(f"│ 📊 Confidence: {result['confidence']:<50} ({result['analysis_source']}) │")
        print("├────────────────────────────────────────────────────────────────────────────────────┤")
        
        if result['was_translated']:
            translated = (result['translated_title'][:42] + '...') if len(result['translated_title']) > 45 else result['translated_title']
            print(f"│ 🌍 Language: {result['original_language']:<67} │")
            print(f"│ 🔄 Translated: {translated:<65} │")
        else:
            print(f"│ 🌍 Language: {result['original_language']:<67} │")
        
        sentiment_text = f"{result['sentiment']} ({result['sentiment_score']:.0%})"
        print(f"│ {result['sentiment_emoji']} Sentiment: {sentiment_text:<58} │")
        print("├────────────────────────────────────────────────────────────────────────────────────┤")
        
        # Productivity classification (ML-based)
        productivity = result.get('productivity', 'UNKNOWN')
        prod_emoji = result.get('productivity_emoji', '➖')
        prod_conf = result.get('productivity_confidence', 'Low')
        prod_reason = result.get('productivity_reason', '')[:40]
        prod_text = f"{productivity} ({prod_conf})"
        print(f"│ {prod_emoji} Productivity: {prod_text:<55} │")
        if prod_reason:
            print(f"│    Reason: {prod_reason:<69} │")
        print("└────────────────────────────────────────────────────────────────────────────────────┘")
        print()
    
    def run(self):
        self.running = True
        self.print_header()
        
        try:
            while self.running:
                result = self.analyzer.analyze()
                self.print_result(result)
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user.")
        finally:
            self.analyzer.close()
            print("👋 Goodbye!")
    
    def stop(self):
        self.running = False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Screen Content Classifier v4.0 - Maximum Accuracy")
    parser.add_argument("-i", "--interval", type=float, default=3.0, help="Seconds between analysis (default: 3.0)")
    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR (faster but less accurate)")
    
    args = parser.parse_args()
    
    print("=" * 84)
    print("       🖥️  SCREEN CONTENT CLASSIFIER v5.0")
    print("       Maximum Accuracy: 200+ Apps | OCR | Sentiment | Activity Detection")
    print("=" * 84)
    print()
    
    monitor = ScreenMonitor(interval=args.interval, enable_ocr=not args.no_ocr)
    monitor.run()


if __name__ == "__main__":
    main()
