# -*- coding: utf-8 -*-
"""
Configuration and Settings Management
Handles paths, default settings, and settings persistence
"""
import os
import json

# ------------------ Paths ------------------
_THIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TABS_DIR = os.path.dirname(_THIS_DIR)
_PROJECT_ROOT = os.path.dirname(_TABS_DIR)
_SETTINGS_PATH = os.path.join(_PROJECT_ROOT, "config", "ollama_settings.json")

# Export paths
THIS_DIR = _THIS_DIR
TABS_DIR = _TABS_DIR
PROJECT_ROOT = _PROJECT_ROOT
SETTINGS_PATH = _SETTINGS_PATH

# Default settings
DEFAULT_SETTINGS = {
    "api_url": "http://localhost:11434",
    "model": "gemma2",
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 512,
    "ocr_engine": "tesseract",  # "tesseract", "easyocr", or "ollama_vision"
    "vision_model": "llava",  # Vision model for Ollama (llava, granit-vision, etc.)
}


def ensure_dir(path):
    """Ensure directory exists"""
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


def load_settings():
    """Load settings from file"""
    try:
        if os.path.isfile(_SETTINGS_PATH):
            with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    settings = dict(DEFAULT_SETTINGS)
                    settings.update(data)
                    return settings
    except Exception:
        pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    """Save settings to file"""
    try:
        ensure_dir(os.path.dirname(_SETTINGS_PATH))
        with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

