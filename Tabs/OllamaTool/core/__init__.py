# -*- coding: utf-8 -*-
"""
OllamaTool Core Module
Configuration, settings, API communication, and utility functions
"""
from .config import (
    load_settings,
    save_settings,
    ensure_dir,
    SETTINGS_PATH,
    DEFAULT_SETTINGS,
    THIS_DIR,
    TABS_DIR,
    PROJECT_ROOT,
)
from .dependencies import (
    DND_AVAILABLE,
    DND_FILES,
    REQUESTS_AVAILABLE,
    REQUESTS_ERROR,
    EASYOCR_AVAILABLE,
    TESSERACT_AVAILABLE,
    PYMUPDF_AVAILABLE,
    PIL_AVAILABLE,
    PDFPLUMBER_AVAILABLE,
    CHECKBOX_DETECTION_AVAILABLE,
    _detect_checkboxes_in_rightmost_columns,
    ollama_available,
    available_models,
)
from .api import (
    check_ollama_connection,
    get_available_models,
    chat_with_ollama,
)

__all__ = [
    # Config
    'load_settings',
    'save_settings',
    'ensure_dir',
    'SETTINGS_PATH',
    'DEFAULT_SETTINGS',
    'THIS_DIR',
    'TABS_DIR',
    'PROJECT_ROOT',
    # Dependencies
    'DND_AVAILABLE',
    'DND_FILES',
    'REQUESTS_AVAILABLE',
    'REQUESTS_ERROR',
    'EASYOCR_AVAILABLE',
    'TESSERACT_AVAILABLE',
    'PYMUPDF_AVAILABLE',
    'PIL_AVAILABLE',
    'PDFPLUMBER_AVAILABLE',
    'CHECKBOX_DETECTION_AVAILABLE',
    '_detect_checkboxes_in_rightmost_columns',
    'ollama_available',
    'available_models',
    # API
    'check_ollama_connection',
    'get_available_models',
    'chat_with_ollama',
]
