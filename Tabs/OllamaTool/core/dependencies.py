# -*- coding: utf-8 -*-
"""
Dependency Detection and Availability Flags
Checks for optional libraries and sets availability flags
"""
import os
import importlib.util

# Try to import drag-and-drop support
try:
    from tkinterdnd2 import DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_FILES = None
    DND_AVAILABLE = False

# Try to import requests
REQUESTS_AVAILABLE = False
REQUESTS_ERROR = None
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError as e:
    REQUESTS_AVAILABLE = False
    REQUESTS_ERROR = str(e)

# Try to import OCR libraries
EASYOCR_AVAILABLE = False
TESSERACT_AVAILABLE = False
PYMUPDF_AVAILABLE = False
PIL_AVAILABLE = False
PDFPLUMBER_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

# Try to import checkbox detection from MvrRunner
CHECKBOX_DETECTION_AVAILABLE = False
_detect_checkboxes_in_rightmost_columns = None

try:
    from Tabs.MvrRunner.shared import _detect_checkboxes_in_rightmost_columns
    CHECKBOX_DETECTION_AVAILABLE = True
except ImportError:
    try:
        # Fallback: try to load directly from file path
        _THIS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shared_path = os.path.join(_THIS_DIR, "MvrRunner", "shared.py")
        if os.path.isfile(shared_path):
            spec = importlib.util.spec_from_file_location("MvrRunner.shared", shared_path)
            shared_mod = importlib.util.module_from_spec(spec)
            if spec and spec.loader:
                spec.loader.exec_module(shared_mod)
                _detect_checkboxes_in_rightmost_columns = shared_mod._detect_checkboxes_in_rightmost_columns
                CHECKBOX_DETECTION_AVAILABLE = True
    except Exception:
        pass

# Ollama API state (global)
ollama_available = False
available_models = []

