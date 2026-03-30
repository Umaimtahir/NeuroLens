import sys
import os
from unittest.mock import MagicMock

# 1. Bulk mock all requirements
requirements = [
    "fastapi", "uvicorn", "sqlalchemy", "psycopg2", "dotenv", "jose", "passlib", 
    "argon2", "pydantic", "pydantic_settings", "cryptography", "multipart", 
    "email_validator", "pywinctl", "mss", "PIL", "torch", "torchvision", 
    "transformers", "accelerate", "sentencepiece", "einops", "timm", "cv2", "numpy"
]
for mod in requirements:
    sys.modules[mod] = MagicMock()

# 2. Add path and run
sys.path.append(os.path.abspath(r"d:\NeuroLens"))
sys.path.append(os.path.abspath(r"d:\NeuroLens\Activity_Module"))

try:
    from Activity_Module.activity_classifier import label_engine
except Exception as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def test_scenario(name, proc, title, domain="", ocr=""):
    # 1. Try browser classification if domain is provided
    if domain:
        result = label_engine.classify_browser_tab(domain, title)
    else:
        # 2. Try app-specific classification (Takes 3 args: proc, title, ocr)
        result = label_engine.detect_app_subactivity(proc, title, ocr)
        
        # 3. Fallback to keyword matchers if app-specific returned None
        if not result:
            result = label_engine.match_generic_keywords(title.lower() if title else "")
            
    print(f"[TEST] {name:35} | {result}")
    return result

def run_all_tests():
    print("=== NEUROLENS DEEP TAXONOMY VALIDATION ===\n")
    print(f"{'SCENARIO':35} | {'LABEL'}")
    print("-" * 75)
    
    # 1. VS Code Scenarios
    test_scenario("VS Code Python", "code.exe", "main.py - NeuroLens - Visual Studio Code")
    test_scenario("VS Code JS", "code.exe", "index.js - Project - Visual Studio Code")
    test_scenario("VS Code Debug", "code.exe", "Debug - main.py - Visual Studio Code")
    test_scenario("VS Code Building", "code.exe", "Terminal - Building - Visual Studio Code")
    
    # 2. Browser Scenarios (YouTube)
    test_scenario("YouTube Browsing", "chrome.exe", "YouTube", "youtube.com")
    test_scenario("YouTube Search", "chrome.exe", "search results - YouTube", "youtube.com")
    test_scenario("YouTube Video", "chrome.exe", "Python Tutorial for Beginners - YouTube", "youtube.com")
    test_scenario("YouTube Music", "chrome.exe", "Official Music Video - YouTube", "youtube.com")
    test_scenario("YouTube Shorts", "chrome.exe", "Crazy Experiment #shorts - YouTube", "youtube.com")
    
    # 3. Browser Scenarios (Shopping)
    test_scenario("Amazon Browsing", "msedge.exe", "Gaming Laptop - Amazon.com", "amazon.com")
    test_scenario("Amazon Checkout", "msedge.exe", "Checkout Page - Amazon.com", "amazon.com")
    test_scenario("Daraz Searching", "msedge.exe", "Search results for Phone - Daraz.pk", "daraz.pk")
    test_scenario("Flipkart Browsing", "chrome.exe", "Realme 12 Pro - Flipkart", "flipkart.com")
    
    # 4. Terminal Scenarios
    test_scenario("Terminal Git", "powershell.exe", "Windows PowerShell", "", "git commit -m 'update'")
    test_scenario("Terminal Python", "cmd.exe", "Command Prompt", "", "python train.py")
    test_scenario("Terminal Building", "cmd.exe", "Command Prompt", "", "npm run build")
    
    # 5. Productivity Scenarios
    test_scenario("Excel Analysis", "excel.exe", "Quarterly_Report.xlsx - Excel", "", "pivot table analysis")
    test_scenario("Word Writing", "winword.exe", "Thesis_Final.docx - Word")
    
    # 6. Meeting Scenarios
    test_scenario("Zoom Meeting", "zoom.exe", "Zoom Meeting")
    test_scenario("Teams Chat", "teams.exe", "Chat with Ali | Microsoft Teams")
    
    # 7. Creative Scenarios
    test_scenario("Blender Modeling", "blender.exe", "Scene_01 - Blender")
    test_scenario("OBS Recording", "obs64.exe", "OBS Studio 30.0.0")
    test_scenario("DaVinci Editing", "davinciresolve.exe", "Project_Final - DaVinci Resolve")
    
    # 8. Misc Scenarios
    test_scenario("Spotify Music", "spotify.exe", "Stay - Justin Bieber")
    test_scenario("ChatGPT AI", "chrome.exe", "ChatGPT - OpenAI", "chatgpt.com")
    test_scenario("Twitter Feed", "chrome.exe", "Home / X", "twitter.com")
    test_scenario("LinkedIn Jobs", "chrome.exe", "Jobs | LinkedIn", "linkedin.com")
    test_scenario("GitHub PR", "chrome.exe", "PR #123: Update labels - GitHub", "github.com")
    
    # 9. Kaggle & Meet (The "Bad Results" Fixes)
    test_scenario("Kaggle Notebook", "chrome.exe", "NeuroLens_Inference | Kaggle", "kaggle.com")
    test_scenario("Google Meet", "msedge.exe", "Weekly Sync - Google Meet", "meet.google.com")
    test_scenario("Generic Site", "chrome.exe", "Some Random News", "news.com")

if __name__ == "__main__":
    run_all_tests()
