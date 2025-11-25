# -*- coding: utf-8 -*-
"""
Ollama AI Tool - Chat interface for Ollama models
"""
import os
import sys
import threading
import json
import re
from typing import Optional, List, Dict

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

# Try to import drag-and-drop support
try:
    from tkinterdnd2 import DND_FILES
    _DND_AVAILABLE = True
except ImportError:
    DND_FILES = None
    _DND_AVAILABLE = False

# Try to import requests
_REQUESTS_AVAILABLE = False
_REQUESTS_ERROR = None
try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError as e:
    _REQUESTS_AVAILABLE = False
    _REQUESTS_ERROR = str(e)

# Try to import OCR libraries
_EASYOCR_AVAILABLE = False
_TESSERACT_AVAILABLE = False
_PYMUPDF_AVAILABLE = False
_PIL_AVAILABLE = False
_PDFPLUMBER_AVAILABLE = False

try:
    import easyocr
    _EASYOCR_AVAILABLE = True
except ImportError:
    _EASYOCR_AVAILABLE = False

try:
    import pytesseract
    _TESSERACT_AVAILABLE = True
except ImportError:
    _TESSERACT_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    _PYMUPDF_AVAILABLE = True
except ImportError:
    _PYMUPDF_AVAILABLE = False

try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

try:
    import pdfplumber
    _PDFPLUMBER_AVAILABLE = True
except ImportError:
    _PDFPLUMBER_AVAILABLE = False

# ------------------ Paths ------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
_SETTINGS_PATH = os.path.join(_PROJECT_ROOT, "ollama_settings.json")

# Default settings
_DEFAULT_SETTINGS = {
    "api_url": "http://localhost:11434",
    "model": "gemma2",
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 512,
    "ocr_engine": "tesseract",  # "tesseract", "easyocr", or "ollama_vision"
    "vision_model": "llava",  # Vision model for Ollama (llava, granit-vision, etc.)
}

# Ollama API state
_ollama_available = False
_available_models = []


def _clean_ocr_text(text: str) -> str:
    """Clean OCR text to fix common issues:
    - Fix dates: 2/4/1999 → 02/04/1999
    - Remove checkbox marks: EFT → FT, DPT → PT, XY → Y, XN → N
    """
    if not text:
        return text
    
    import re
    
    # Fix dates: normalize MM/DD/YYYY format
    # Pattern: one or two digits / one or two digits / four digits
    # Examples: 2/4/1999 → 02/04/1999, 12/25/2000 → 12/25/2000
    def fix_date(match):
        month, day, year = match.groups()
        # Validate year is 4 digits and reasonable (1900-2099)
        if len(year) == 4 and 1900 <= int(year) <= 2099:
            # Pad with zeros if single digit
            month = month.zfill(2)
            day = day.zfill(2)
            return f"{month}/{day}/{year}"
        return match.group(0)  # Return original if year is invalid
    
    # Fix dates where slashes are misread as "1" (e.g., "2111/2003" → "02/11/2003")
    # Pattern: 3-4 digits, then /, then 4 digits (year)
    # Examples: "2111/2003" → "02/11/2003", "1211/2003" → "12/11/2003", "211/2003" → "02/11/2003"
    def fix_slash_as_one(match):
        first_part = match.group(1)  # Could be "2111", "1211", "211", etc.
        year = match.group(2)
        
        # Validate year is 4 digits and reasonable (1900-2099)
        if len(year) != 4 or not (1900 <= int(year) <= 2099):
            return match.group(0)  # Don't fix if year is invalid
        
        # Try to split first_part into month and day
        # If 4 digits: first 1-2 digits = month, last 1-2 digits = day
        # If 3 digits: first 1 digit = month, last 2 digits = day
        if len(first_part) == 4:
            # Try splitting as 1+2 (e.g., "2111" → "2" + "11")
            if first_part[0] in '12' and 1 <= int(first_part[1:3]) <= 31:
                month = first_part[0]
                day = first_part[1:3]
            # Try splitting as 2+2 (e.g., "1211" → "12" + "11")
            elif 1 <= int(first_part[0:2]) <= 12 and 1 <= int(first_part[2:4]) <= 31:
                month = first_part[0:2]
                day = first_part[2:4]
            else:
                # Default: assume 1+2 split
                month = first_part[0]
                day = first_part[1:3]
        elif len(first_part) == 3:
            # Split as 1+2 (e.g., "211" → "2" + "11")
            month = first_part[0]
            day = first_part[1:3]
        else:
            # Can't fix, return original
            return match.group(0)
        
        # Validate: month 1-12, day 1-31
        if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
            return f"{month.zfill(2)}/{day.zfill(2)}/{year}"
        else:
            return match.group(0)
    
    # IMPORTANT: Process dates in order of specificity to avoid false matches
    # CRITICAL: We must avoid processing dates multiple times
    # Strategy: Process dates in a single pass, most specific patterns first
    
    # First, fix dates where slash is misread as 1: "2111/2003" pattern
    # This must come BEFORE the normal date fix to catch malformed dates first
    # Only match if the year part looks like a valid 4-digit year (1900-2099)
    text = re.sub(r'\b(\d{3,4})/(\d{4})\b', fix_slash_as_one, text)
    
    # Then fix normal dates with slashes (most common case: M/D/YYYY)
    # Only process if year is valid (1900-2099) to avoid corrupting valid dates
    # Use word boundaries to ensure we match complete dates, not parts
    # CRITICAL: This pattern should match "2/4/1999" and convert to "02/04/1999"
    # But we must ensure it doesn't match parts of already-processed dates
    text = re.sub(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', fix_date, text)
    
    # DO NOT process "missing slash" patterns - they cause double-processing
    # If a date is already in M/D/YYYY format, the above pattern handles it
    # The "missing slash" pattern was causing dates like "2/4/1999" to become "02/01/04/1999"
    
    # NOTE: We do NOT attempt to "correct" or modify years in any way.
    # Years are passed through exactly as OCR reads them.
    # We only normalize month/day padding (e.g., "2/4" → "02/04").
    # If OCR misreads a year, that's an OCR accuracy issue, not something we should guess at.
    
    # Fix common OCR errors in state codes (2-letter abbreviations)
    # OCR often misreads similar-looking characters in short text like "IL"
    # This is especially problematic for "IL" where "I" looks like "1" and "L" looks like "1"
    
    # Comprehensive list of state code misreadings
    state_corrections = {
        # IL (Illinois) - most commonly misread, many variations
        "1L": "IL",  # "I" misread as "1"
        "I1": "IL",  # "L" misread as "1"
        "|L": "IL",  # "I" misread as "|"
        "|1": "IL",  # Both misread
        "IL.": "IL",  # Extra period
        "1l": "IL",  # Lowercase version
        "i1": "IL",  # Lowercase version
        "|l": "IL",  # Lowercase version
        "1|": "IL",  # Alternative misreading
        "|I": "IL",  # Alternative misreading
        # Other common misreadings
        "N1": "NY",  # "Y" misread as "1" (New York)
        "C4": "CA",  # "A" misread as "4" (California)
        "P4": "PA",  # "A" misread as "4" (Pennsylvania)
        "F1": "FL",  # "L" misread as "1" (Florida)
        "0H": "OH",  # "O" misread as "0" (Ohio)
        "M1": "MI",  # "I" misread as "1" (Michigan)
    }
    
    # Apply corrections for known OCR errors in state codes
    # Use word boundaries and case-insensitive matching
    # Apply multiple times to catch all variations
    for wrong, correct in state_corrections.items():
        # Match standalone codes (word boundaries)
        text = re.sub(r'\b' + re.escape(wrong) + r'\b', correct, text, flags=re.IGNORECASE)
        # Also match codes that might be part of "STATE" column context
        # Look for patterns like "STATE 1L" or "State I1"
        text = re.sub(r'\b(STATE|State)\s+' + re.escape(wrong) + r'\b', 
                     r'\1 ' + correct, text, flags=re.IGNORECASE)
    
    # Clean checkbox marks from STATUS field (FT/PT)
    # Patterns: XFT, EFT, DPT, XPT, etc. → FT or PT
    # Look for FT or PT that might have a character before it (checkbox mark)
    text = re.sub(r'\b[EXD]?FT\b', 'FT', text, flags=re.IGNORECASE)
    text = re.sub(r'\b[EXD]?PT\b', 'PT', text, flags=re.IGNORECASE)
    # Also handle cases where checkbox is separate: "X FT" → "FT"
    text = re.sub(r'\b[EXD]\s*FT\b', 'FT', text, flags=re.IGNORECASE)
    text = re.sub(r'\b[EXD]\s*PT\b', 'PT', text, flags=re.IGNORECASE)
    
    # Clean checkbox marks from PERSONAL USE field (Y/N)
    # Patterns: XY, XN, EY, EN, etc. → Y or N
    text = re.sub(r'\b[EXD]?Y\b(?=\s|$)', 'Y', text, flags=re.IGNORECASE)
    text = re.sub(r'\b[EXD]?N\b(?=\s|$)', 'N', text, flags=re.IGNORECASE)
    # Handle cases where checkbox is separate: "X Y" → "Y"
    text = re.sub(r'\b[EXD]\s*Y\b(?=\s|$)', 'Y', text, flags=re.IGNORECASE)
    text = re.sub(r'\b[EXD]\s*N\b(?=\s|$)', 'N', text, flags=re.IGNORECASE)
    
    return text


def _ensure_dir(path):
    """Ensure directory exists"""
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


def _load_settings():
    """Load settings from file"""
    try:
        if os.path.isfile(_SETTINGS_PATH):
            with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    settings = dict(_DEFAULT_SETTINGS)
                    settings.update(data)
                    return settings
    except Exception:
        pass
    return dict(_DEFAULT_SETTINGS)


def _save_settings(settings):
    """Save settings to file"""
    try:
        _ensure_dir(os.path.dirname(_SETTINGS_PATH))
        with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _check_ollama_connection(api_url: str) -> bool:
    """Check if Ollama is running and accessible"""
    global _ollama_available
    if not _REQUESTS_AVAILABLE:
        return False
    
    try:
        response = requests.get(f"{api_url}/api/tags", timeout=2)
        if response.status_code == 200:
            _ollama_available = True
            return True
    except Exception:
        pass
    
    _ollama_available = False
    return False


def _get_available_models(api_url: str) -> List[str]:
    """Get list of available Ollama models"""
    global _available_models
    if not _REQUESTS_AVAILABLE:
        return []
    
    try:
        response = requests.get(f"{api_url}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = []
            if "models" in data:
                for model in data["models"]:
                    model_name = model.get("name", "")
                    if model_name:
                        models.append(model_name)
            _available_models = models
            return models
    except Exception as e:
        pass
    
    return []


def _chat_with_ollama(api_url: str, model: str, messages: List[Dict], settings: Dict, callback):
    """Send chat request to Ollama API"""
    if not _REQUESTS_AVAILABLE:
        callback(False, "requests library not installed")
        return
    
    try:
        # Prepare the request
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": settings.get("temperature", 0.7),
                "top_p": settings.get("top_p", 0.9),
                "num_predict": settings.get("max_tokens", 512),
            }
        }
        
        response = requests.post(
            f"{api_url}/api/chat",
            json=payload,
            timeout=120  # 2 minute timeout for responses
        )
        
        if response.status_code == 200:
            data = response.json()
            if "message" in data and "content" in data["message"]:
                callback(True, data["message"]["content"])
            else:
                callback(False, f"Unexpected response format: {data}")
        else:
            callback(False, f"API error: {response.status_code} - {response.text}")
    
    except requests.exceptions.ConnectionError:
        callback(False, "Cannot connect to Ollama. Make sure Ollama is running.")
    except requests.exceptions.Timeout:
        callback(False, "Request timed out. The model may be taking too long to respond.")
    except Exception as e:
        callback(False, f"Error: {str(e)}")


def _extract_text_with_tesseract(file_path: str) -> str:
    """Extract text from PDF or image using Tesseract OCR"""
    if not _TESSERACT_AVAILABLE:
        return None
    
    try:
        text_parts = []
        
        # Check if it's a PDF
        if file_path.lower().endswith('.pdf') and _PYMUPDF_AVAILABLE:
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                # Convert PDF page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
                img_data = pix.tobytes("png")
                
                # Use PIL to open the image
                if _PIL_AVAILABLE:
                    from io import BytesIO
                    img = Image.open(BytesIO(img_data))
                    page_text = pytesseract.image_to_string(img, lang='eng')
                    if page_text.strip():
                        text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
            doc.close()
        elif _PIL_AVAILABLE:
            # It's an image file
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img, lang='eng')
            if text.strip():
                text_parts.append(text)
        
        return "\n\n".join(text_parts) if text_parts else None
    
    except Exception as e:
        return f"Tesseract OCR error: {str(e)}"


def _extract_text_with_easyocr(file_path: str) -> str:
    """Extract text from PDF or image using EasyOCR"""
    if not _EASYOCR_AVAILABLE:
        return None
    
    try:
        import numpy as np
        # Initialize EasyOCR reader (English, no GPU)
        reader = easyocr.Reader(['en'], gpu=False)
        text_parts = []
        
        # Check if it's a PDF
        if file_path.lower().endswith('.pdf') and _PYMUPDF_AVAILABLE:
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                # Convert PDF page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
                img_data = pix.tobytes("png")
                
                # Use PIL to open the image
                if _PIL_AVAILABLE:
                    from io import BytesIO
                    img = Image.open(BytesIO(img_data))
                    # Convert PIL image to numpy array for EasyOCR
                    img_array = np.array(img)
                    
                    # Run OCR - EasyOCR returns [(bbox, text, confidence), ...]
                    # detail=1 returns detailed info with bboxes - needed for table detection
                    # mag_ratio=1.5: Magnify image 1.5x to better detect small text like "IL"
                    # min_size=10: Lower minimum text size to detect smaller text (default is 20)
                    # width_ths and height_ths adjusted for better detection of short text
                    result = reader.readtext(img_array, detail=1, mag_ratio=1.5, min_size=10, width_ths=0.3, height_ths=0.3)
                    if result:
                        page_text = "\n".join([line[1] for line in result if len(line) > 1])
                        if page_text.strip():
                            text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
            doc.close()
        elif _PIL_AVAILABLE:
            # It's an image file
            img = Image.open(file_path)
            img_array = np.array(img)
            
            # Run OCR
            # detail=1 returns detailed info with bboxes
            # mag_ratio=1.5: Magnify image 1.5x to better detect small text like "IL"
            # min_size=10: Lower minimum text size to detect smaller text (default is 20)
            # width_ths and height_ths adjusted for better detection of short text
            result = reader.readtext(img_array, detail=1, mag_ratio=1.5, min_size=10, width_ths=0.3, height_ths=0.3)
            if result:
                text = "\n".join([line[1] for line in result if len(line) > 1])
                if text.strip():
                    text_parts.append(text)
        
        return "\n\n".join(text_parts) if text_parts else None
    
    except Exception as e:
        return f"EasyOCR error: {str(e)}"


def _extract_text_with_ollama_vision(file_path: str, api_url: str, vision_model: str, settings: Dict) -> str:
    """Extract text from PDF or image using Ollama's vision models"""
    if not _REQUESTS_AVAILABLE:
        return "requests library not installed"
    
    if not _PYMUPDF_AVAILABLE and file_path.lower().endswith('.pdf'):
        return "PyMuPDF not available for PDF processing"
    
    if not _PIL_AVAILABLE:
        return "PIL/Pillow not available for image processing"
    
    try:
        import base64
        from io import BytesIO
        
        text_parts = []
        images_to_process = []
        
        # Convert PDF pages or single image to base64
        if file_path.lower().endswith('.pdf'):
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                # Convert PDF page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                img_data = pix.tobytes("png")
                images_to_process.append((page_num + 1, img_data))
            doc.close()
        else:
            # It's an image file
            img = Image.open(file_path)
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            images_to_process.append((1, img_bytes.getvalue()))
        
        # Process each image with Ollama vision model
        for page_num, img_data in images_to_process:
            # Convert image to base64
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            # Prepare message for vision model
            messages = [
                {
                    "role": "user",
                    "content": "Extract all text from this image. Return only the extracted text, preserving the structure and layout as much as possible.",
                    "images": [img_base64]
                }
            ]
            
            # Call Ollama API
            payload = {
                "model": vision_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": settings.get("temperature", 0.7),
                    "num_predict": settings.get("max_tokens", 2048),  # More tokens for text extraction
                }
            }
            
            response = requests.post(
                f"{api_url}/api/chat",
                json=payload,
                timeout=180  # 3 minute timeout for vision processing
            )
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "content" in data["message"]:
                    page_text = data["message"]["content"]
                    if page_text.strip():
                        if len(images_to_process) > 1:
                            text_parts.append(f"--- Page {page_num} ---\n{page_text}")
                        else:
                            text_parts.append(page_text)
            else:
                return f"Ollama API error: {response.status_code} - {response.text}"
        
        return "\n\n".join(text_parts) if text_parts else "No text could be extracted."
    
    except requests.exceptions.ConnectionError:
        return "Cannot connect to Ollama. Make sure Ollama is running and the vision model is installed."
    except Exception as e:
        return f"Ollama vision error: {str(e)}"


def extract_tables_from_pdf(file_path: str, use_ocr: bool = False) -> List[Dict]:
    """
    Extract tables from PDF.
    For text-based PDFs: uses pdfplumber
    For scanned PDFs: uses EasyOCR table recognition
    
    Returns list of tables, each as a dict with 'page', 'table' (2D list), and 'method'
    """
    tables = []
    
    if not _PYMUPDF_AVAILABLE:
        return tables
    
    # First, try text-based extraction with pdfplumber
    if _PDFPLUMBER_AVAILABLE and not use_ocr:
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = page.extract_tables()
                    for table in page_tables:
                        if table and len(table) > 0:
                            tables.append({
                                "page": page_num,
                                "table": table,
                                "method": "pdfplumber"
                            })
        except Exception as e:
            # Fall back to OCR if pdfplumber fails
            use_ocr = True
    
    # For scanned PDFs or if pdfplumber found no tables, use EasyOCR table recognition
    if use_ocr or (not tables and _EASYOCR_AVAILABLE):
        try:
            import numpy as np
            from io import BytesIO
            
            # Initialize EasyOCR reader
            reader = easyocr.Reader(['en'], gpu=False)
            
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                # Convert PDF page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                img_data = pix.tobytes("png")
                
                if _PIL_AVAILABLE:
                    img = Image.open(BytesIO(img_data))
                    img_array = np.array(img)
                    
                    # Run OCR with table structure recognition
                    # EasyOCR returns: [(bbox, text, confidence), ...]
                    # detail=1 returns detailed info with bboxes - needed for table detection
                    # mag_ratio=1.5: Magnify image 1.5x to better detect small text like "IL"
                    # min_size=10: Lower minimum text size to detect smaller text (default is 20)
                    # width_ths and height_ths adjusted for better detection of short text
                    result = reader.readtext(img_array, detail=1, mag_ratio=1.5, min_size=10, width_ths=0.3, height_ths=0.3)
                    
                    if result:
                        # Try to detect table structure from OCR results
                        # Group text by approximate Y coordinates to form rows
                        lines = []
                        for line_result in result:
                            if line_result and len(line_result) >= 2:
                                bbox = line_result[0]  # Bounding box
                                text = line_result[1]  # Text
                                # Calculate center Y coordinate
                                if bbox and len(bbox) >= 4:
                                    y_center = sum([point[1] for point in bbox]) / len(bbox)
                                    lines.append((y_center, text, bbox))
                        
                        # Group lines into rows (lines with similar Y coordinates)
                        if lines:
                            lines.sort(key=lambda x: x[0])  # Sort by Y coordinate
                            rows = []
                            current_row = []
                            current_y = None
                            y_threshold = 20  # Pixels
                            
                            for y, text, bbox in lines:
                                if current_y is None or abs(y - current_y) < y_threshold:
                                    # Same row
                                    current_row.append((text, bbox))
                                    current_y = y
                                else:
                                    # New row
                                    if current_row:
                                        # Sort by X coordinate within row
                                        current_row.sort(key=lambda x: sum([p[0] for p in x[1]]) / len(x[1]))
                                        rows.append([cell[0] for cell in current_row])
                                    current_row = [(text, bbox)]
                                    current_y = y
                            
                            # Add last row
                            if current_row:
                                current_row.sort(key=lambda x: sum([p[0] for p in x[1]]) / len(x[1]))
                                rows.append([cell[0] for cell in current_row])
                            
                            if rows:
                                tables.append({
                                    "page": page_num + 1,
                                    "table": rows,
                                    "method": "easyocr"
                                })
            
            doc.close()
        except Exception as e:
            pass  # Table extraction failed
    
    return tables


def format_table_as_text(table_data: List[List[str]]) -> str:
    """Format a 2D table as readable text"""
    if not table_data:
        return ""
    
    # Calculate column widths
    max_cols = max(len(row) for row in table_data) if table_data else 0
    col_widths = [0] * max_cols
    
    for row in table_data:
        for i, cell in enumerate(row):
            if i < max_cols:
                col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Format rows
    formatted_rows = []
    for row in table_data:
        formatted_cells = []
        for i in range(max_cols):
            cell = str(row[i]) if i < len(row) else ""
            formatted_cells.append(cell.ljust(col_widths[i]))
        formatted_rows.append(" | ".join(formatted_cells))
    
    return "\n".join(formatted_rows)


def extract_tables_from_pdf(file_path: str, use_ocr: bool = False) -> List[Dict]:
    """
    Extract tables from PDF.
    For text-based PDFs: uses pdfplumber
    For scanned PDFs: uses EasyOCR table recognition
    
    Returns list of tables, each as a dict with 'page', 'table' (2D list), and 'method'
    """
    tables = []
    
    if not _PYMUPDF_AVAILABLE:
        return tables
    
    # First, try text-based extraction with pdfplumber
    if _PDFPLUMBER_AVAILABLE and not use_ocr:
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = page.extract_tables()
                    for table in page_tables:
                        if table and len(table) > 0:
                            tables.append({
                                "page": page_num,
                                "table": table,
                                "method": "pdfplumber"
                            })
        except Exception:
            # Fall back to OCR if pdfplumber fails
            use_ocr = True
    
    # For scanned PDFs or if pdfplumber found no tables, use EasyOCR table recognition
    if use_ocr or (not tables and _EASYOCR_AVAILABLE):
        try:
            import numpy as np
            from io import BytesIO
            
            # Initialize EasyOCR reader
            reader = easyocr.Reader(['en'], gpu=False)
            
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                # Convert PDF page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                img_data = pix.tobytes("png")
                
                if _PIL_AVAILABLE:
                    img = Image.open(BytesIO(img_data))
                    img_array = np.array(img)
                    
                    # Run OCR with table structure recognition
                    # EasyOCR returns: [(bbox, text, confidence), ...]
                    # detail=1 returns detailed info with bboxes - needed for table detection
                    # mag_ratio=1.5: Magnify image 1.5x to better detect small text like "IL"
                    # min_size=10: Lower minimum text size to detect smaller text (default is 20)
                    # width_ths and height_ths adjusted for better detection of short text
                    result = reader.readtext(img_array, detail=1, mag_ratio=1.5, min_size=10, width_ths=0.3, height_ths=0.3)
                    
                    if result:
                        # Try to detect table structure from OCR results
                        # Group text by approximate Y coordinates to form rows
                        lines = []
                        for line_result in result:
                            if line_result and len(line_result) >= 2:
                                bbox = line_result[0]  # Bounding box
                                text = line_result[1]  # Text
                                # Calculate center Y coordinate
                                if bbox and len(bbox) >= 4:
                                    y_center = sum([point[1] for point in bbox]) / len(bbox)
                                    lines.append((y_center, text, bbox))
                        
                        # Group lines into rows (lines with similar Y coordinates)
                        if lines:
                            lines.sort(key=lambda x: x[0])  # Sort by Y coordinate
                            rows = []
                            current_row = []
                            current_y = None
                            y_threshold = 20  # Pixels
                            
                            for y, text, bbox in lines:
                                if current_y is None or abs(y - current_y) < y_threshold:
                                    # Same row
                                    current_row.append((text, bbox))
                                    current_y = y
                                else:
                                    # New row
                                    if current_row:
                                        # Sort by X coordinate within row
                                        current_row.sort(key=lambda x: sum([p[0] for p in x[1]]) / len(x[1]))
                                        rows.append([cell[0] for cell in current_row])
                                    current_row = [(text, bbox)]
                                    current_y = y
                            
                            # Add last row
                            if current_row:
                                current_row.sort(key=lambda x: sum([p[0] for p in x[1]]) / len(x[1]))
                                rows.append([cell[0] for cell in current_row])
                            
                            if rows:
                                tables.append({
                                    "page": page_num + 1,
                                    "table": rows,
                                    "method": "easyocr"
                                })
            
            doc.close()
        except Exception:
            pass  # Table extraction failed
    
    return tables


def format_table_as_text(table_data: List[List[str]]) -> str:
    """Format a 2D table as readable text"""
    if not table_data:
        return ""
    
    # Calculate column widths
    max_cols = max(len(row) for row in table_data) if table_data else 0
    col_widths = [0] * max_cols
    
    for row in table_data:
        for i, cell in enumerate(row):
            if i < max_cols:
                col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Format rows
    formatted_rows = []
    for row in table_data:
        formatted_cells = []
        for i in range(max_cols):
            cell = str(row[i]) if i < len(row) else ""
            formatted_cells.append(cell.ljust(col_widths[i]))
        formatted_rows.append(" | ".join(formatted_cells))
    
    return "\n".join(formatted_rows)


def extract_text_from_document(file_path: str, ocr_engine: str = "tesseract", api_url: str = None, vision_model: str = None, settings: Dict = None) -> str:
    """Extract text from a document (PDF or image) using the specified method"""
    if not os.path.isfile(file_path):
        return f"File not found: {file_path}"
    
    # Try to extract text directly from PDF first (if it has text layer)
    if file_path.lower().endswith('.pdf') and _PYMUPDF_AVAILABLE:
        try:
            doc = fitz.open(file_path)
            text_parts = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
            doc.close()
            
            # If we got substantial text, return it (no OCR needed)
            full_text = "\n\n".join(text_parts)
            if len(full_text.strip()) > 100:  # If we have substantial text
                return full_text
        except Exception:
            pass  # Fall through to OCR/vision
    
    # Use OCR or vision model
    if ocr_engine.lower() == "ollama_vision":
        if not api_url:
            api_url = "http://localhost:11434"
        if not vision_model:
            vision_model = "llava"
        if not settings:
            settings = {}
        result = _extract_text_with_ollama_vision(file_path, api_url, vision_model, settings)
    elif ocr_engine.lower() == "easyocr":
        result = _extract_text_with_easyocr(file_path)
    else:  # Default to tesseract
        result = _extract_text_with_tesseract(file_path)
    
    return result if result else "No text could be extracted from the document."


def build_tab(parent):
    """
    Create the Ollama AI Tool tab.
    """
    outer = ttk.Frame(parent)
    
    settings = _load_settings()
    
    # Check if requests is available
    if not _REQUESTS_AVAILABLE:
        error_frame = ttk.Frame(outer)
        error_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ttk.Label(
            error_frame,
            text="Ollama AI Tool",
            font=("Segoe UI", 12, "bold")
        ).pack(pady=(0, 10))
        
        # Get Python executable path for diagnostic
        python_path = sys.executable if hasattr(sys, 'executable') else "python"
        
        error_text = (
            "requests library is not installed.\n\n"
            "Please install it with:\n"
            f'"{python_path}" -m pip install requests\n\n'
            "Or if that doesn't work, try:\n"
            "python -m pip install requests\n"
            "pythonw -m pip install requests\n\n"
            "Then restart the application."
        )
        
        error_label = ttk.Label(
            error_frame,
            text=error_text,
            font=("Segoe UI", 9),
            foreground="red",
            justify="left"
        )
        error_label.pack(pady=10)
        
        # Add diagnostic info
        if _REQUESTS_ERROR:
            diag_text = f"\nImport error: {_REQUESTS_ERROR}\nPython: {python_path}"
            ttk.Label(
                error_frame,
                text=diag_text,
                font=("Segoe UI", 8),
                foreground="gray",
                justify="left"
            ).pack(pady=5)
        
        return outer
    
    # Title
    title_frame = ttk.Frame(outer)
    title_frame.pack(fill="x", padx=16, pady=(10, 5))
    
    ttk.Label(
        title_frame,
        text="Ollama AI Tool",
        font=("Segoe UI", 12, "bold")
    ).pack(side="left")
    
    # Status label
    status_var = tk.StringVar(value="Checking Ollama connection...")
    status_label = ttk.Label(
        title_frame,
        textvariable=status_var,
        font=("Segoe UI", 9)
    )
    status_label.pack(side="right")
    
    # Main content area with PanedWindow for resizable panels
    paned = ttk.PanedWindow(outer, orient="vertical")
    paned.pack(fill="both", expand=True, padx=16, pady=5)
    
    # Chat display area
    chat_frame = ttk.Frame(paned)
    paned.add(chat_frame, weight=3)
    
    ttk.Label(
        chat_frame,
        text="Conversation",
        font=("Segoe UI", 10, "bold")
    ).pack(anchor="w", padx=5, pady=(5, 2))
    
    chat_display = scrolledtext.ScrolledText(
        chat_frame,
        wrap=tk.WORD,
        font=("Segoe UI", 10),
        state="disabled",
        relief="solid",
        borderwidth=1,
        bg="white",
        fg="black"
    )
    chat_display.pack(fill="both", expand=True, padx=5, pady=(0, 5))
    
    # Configure tags for styling messages
    chat_display.tag_config("user", foreground="blue", font=("Segoe UI", 10, "bold"))
    chat_display.tag_config("assistant", foreground="green")
    chat_display.tag_config("system", foreground="gray", font=("Segoe UI", 9, "italic"))
    
    # Add drag-and-drop support for documents
    def on_drop(event):
        """Handle dropped files"""
        try:
            files = outer.tk.splitlist(event.data)
            for file_path in files:
                # Remove curly braces if present (Windows path format)
                file_path = file_path.strip('{}')
                if os.path.isfile(file_path):
                    # Check if it's a supported file type
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                        process_document(file_path)
                    else:
                        append_to_chat("system", f"Unsupported file type: {file_path}")
        except Exception as e:
            append_to_chat("system", f"Error handling dropped file: {str(e)}")
    
    if _DND_AVAILABLE and DND_FILES:
        try:
            chat_frame.drop_target_register(DND_FILES)
            chat_frame.dnd_bind("<<Drop>>", on_drop)
            chat_display.drop_target_register(DND_FILES)
            chat_display.dnd_bind("<<Drop>>", on_drop)
            # Also enable on input area
            input_frame.drop_target_register(DND_FILES)
            input_frame.dnd_bind("<<Drop>>", on_drop)
            input_text.drop_target_register(DND_FILES)
            input_text.dnd_bind("<<Drop>>", on_drop)
        except Exception:
            pass  # Drag-and-drop not critical
    
    # Input area
    input_frame = ttk.Frame(paned)
    paned.add(input_frame, weight=1)
    
    ttk.Label(
        input_frame,
        text="Your message",
        font=("Segoe UI", 10, "bold")
    ).pack(anchor="w", padx=5, pady=(5, 2))
    
    input_text = scrolledtext.ScrolledText(
        input_frame,
        height=4,
        wrap=tk.WORD,
        font=("Segoe UI", 10),
        relief="solid",
        borderwidth=1
    )
    input_text.pack(fill="both", expand=True, padx=5, pady=(0, 5))
    
    # Button frame
    button_frame = ttk.Frame(input_frame)
    button_frame.pack(fill="x", padx=5, pady=(0, 5))
    
    # Conversation history
    conversation_history: List[Dict] = []
    
    # Model loading state
    ollama_connected = False
    chat_thread = None
    
    # Document context (extracted text from uploaded documents)
    document_context: List[str] = []
    
    def update_status(text):
        """Update status label"""
        try:
            status_var.set(text)
            status_label.update_idletasks()
        except Exception:
            pass
    
    def append_to_chat(role: str, content: str):
        """Append message to chat display"""
        try:
            chat_display.config(state="normal")
            
            if role == "user":
                chat_display.insert("end", "You: ", "user")
                chat_display.insert("end", content + "\n\n")
            elif role == "assistant":
                chat_display.insert("end", "Ollama: ", "assistant")
                chat_display.insert("end", content + "\n\n")
            elif role == "system":
                chat_display.insert("end", content + "\n", "system")
            
            chat_display.see("end")
            chat_display.config(state="disabled")
        except Exception:
            pass
    
    def chat_callback(success: bool, result: str):
        """Callback for chat completion"""
        nonlocal chat_thread
        
        if success:
            append_to_chat("assistant", result)
            conversation_history.append({"role": "assistant", "content": result})
            update_status("Ready")
        else:
            error_msg = f"Error: {result}"
            append_to_chat("system", error_msg)
            update_status(f"Error: {result[:50]}")
            messagebox.showerror("Chat Error", result)
        
        chat_thread = None
    
    def extract_mvr_with_ai():
        """Use AI to extract MVR fields from document context and import to MVR Runner"""
        nonlocal ollama_connected, chat_thread
        
        if not document_context:
            messagebox.showwarning("No Document", "Please upload a document first to extract MVR information.")
            return
        
        if not ollama_connected:
            messagebox.showwarning(
                "Ollama Not Connected",
                "Cannot connect to Ollama. Make sure Ollama is running."
            )
            return
        
        if chat_thread and chat_thread.is_alive():
            messagebox.showwarning("Already Processing", "Please wait for the current response to complete.")
            return
        
        def extract_worker():
            try:
                update_status("Extracting MVR fields with AI...")
                
                # Combine all document context
                combined_text = "\n\n".join(document_context)
                
                # Create a prompt for AI to extract MVR fields - look for multiple employees
                extraction_prompt = """Extract ALL MVR (Motor Vehicle Record) information from the following document text. 
This document may contain an employee list or multiple people. Extract EVERY person you find.

Return ONLY a JSON array of objects, where each object has these exact fields (use empty strings if not found):
[
  {
    "license_number": "",
    "last_name": "",
    "first_name": "",
    "dob": "",
    "state": ""
  }
]

CRITICAL EXTRACTION RULES:
1. Extract EVERY row/person in the table/list - do not skip any entries
2. For EACH person, extract ALL available fields - do not leave any as "Not Specified" or empty if the data exists
3. Look carefully at each row - sometimes data is in different columns or positions
4. State abbreviations: Look for 2-letter codes (CA, IL, NY, etc.) or convert full state names to abbreviations
   - CRITICAL: The state field is REQUIRED if you see any state information
   - If you see "IL", "1L", "I1", "|L", or similar in the STATE column, extract it as "IL"
   - Do NOT leave the state field empty if you see any state code or abbreviation
5. DOB format: Extract dates as MM/DD/YYYY or MM-DD-YYYY format
6. License numbers: Extract the full license/driver's license number if present

IMPORTANT NAME PARSING RULES:
- first_name: Extract ONLY the FIRST word of the person's name
  Examples:
  - "John Smith" → first_name="John"
  - "John Michael Smith" → first_name="John"
  - "Jason Smith Cacas" → first_name="Jason" (NOT "Jason Smith")
- last_name: Extract ONLY the LAST word of the person's name (even if it looks unusual)
  Examples:
  - "John Smith" → last_name="Smith"
  - "John Michael Smith" → last_name="Smith"
  - "Jason Smith Cacas" → last_name="Cacas" (NOT "Smith" - Cacas is the last word)
  - "John Smith Jr." → last_name="Jr."
- CRITICAL: The LAST word is ALWAYS the last_name, even if it's not a typical surname
- Do NOT include middle names in either field
- Do NOT confuse parts of the name with license numbers
- CRITICAL: Do NOT confuse the POSITION field (like "Sales", "Mec", "Manager") with the last_name
  - If you see "Alexander nick Bueglar" in the NAME column, the last_name is "Bueglar" (the last word in the NAME field)
  - The POSITION column is separate and contains job titles like "Sales", "Mec", "Manager", etc.
  - The last_name comes ONLY from the NAME column, never from the POSITION column

FIELD EXTRACTION GUIDELINES:
- license_number: Look for driver's license numbers, license #, DL#, etc.
  - License numbers are typically NUMERIC or ALPHANUMERIC codes (e.g., "12345678", "CA1234567", "DL-12345")
  - License numbers are NOT words or names (e.g., "Cacas" is NOT a license number - it's part of a name)
  - If you see a name like "Jason Smith Cacas", "Cacas" is the last_name, NOT the license_number
  - Look for actual license number patterns in separate columns or fields
- state: Look for 2-letter state codes (CA, IL, NY, TX, PA, etc.) - these are often in the same row as the person
  - State codes are ALWAYS 2 uppercase letters (IL, NY, CA, PA, TX, etc.)
  - If you see "IL" in the STATE column, extract it as "IL" (not "Illinois" or empty)
  - State codes are typically in a separate column labeled "STATE" or "State"
  - Do NOT skip the state field - if you see a 2-letter code, extract it
  - CRITICAL: OCR often misreads state codes, especially "IL" which may appear as:
    * "1L" (I misread as 1) → interpret as "IL"
    * "I1" (L misread as 1) → interpret as "IL"
    * "|L" (I misread as |) → interpret as "IL"
    * "|1" (both misread) → interpret as "IL"
  - If you see a 2-character code in the STATE column that looks like a state code but has OCR errors,
    use your intelligence to interpret what the correct state code should be
  - Common state codes: AL, AK, AZ, AR, CA, CO, CT, DE, FL, GA, HI, ID, IL, IN, IA, KS, KY, LA, ME, MD, MA, MI, MN, MS, MO, MT, NE, NV, NH, NJ, NM, NY, NC, ND, OH, OK, OR, PA, RI, SC, SD, TN, TX, UT, VT, VA, WA, WV, WI, WY
- dob: Look for dates of birth - format should be MM/DD/YYYY or MM-DD-YYYY
  - Dates are normalized to 2-digit month and day (e.g., "2/4/1999" = "02/04/1999", "12/25/2000" = "12/25/2000")
  - If you see "214/1999" or similar malformed dates, it's likely "02/14/1999" (missing slash)
  - CRITICAL: If you see dates with invalid years (like "0419" instead of "2019", "0120" instead of "2003"), 
    you MUST interpret and correct them to valid years. For example:
    - "0419" should be interpreted as "2019" (the "20" was misread as "04")
    - "0120" should be interpreted as "2003" (OCR error)
    - "0020" should be interpreted as "2000"
    - Always return the CORRECTED year, not the raw OCR text. Use your intelligence to interpret what the year should be.
- STATUS field: Look for "FT" (Full-Time) or "PT" (Part-Time) - these may appear with checkbox marks
  - OCR may read checked boxes as "EFT", "DPT", "XFT", "XPT" - these should be interpreted as "FT" or "PT"
  - The checked box is indicated by an X mark to the left of FT or PT
- PERSONAL USE field: Look for "Y" (Yes) or "N" (No) - these may appear with checkbox marks
  - OCR may read checked boxes as "XY", "XN", "EY", "EN" - these should be interpreted as "Y" or "N"
  - The checked box is indicated by an X mark to the left of Y or N
- If you see a table with multiple columns, check ALL columns for each person's information
- Do NOT assume fields are "Not Specified" - look carefully at the entire row for each person
- Do NOT confuse name parts with license numbers - names are words, license numbers are codes

Look for employee lists, driver lists, or any tables with names, license numbers, dates of birth, and states.
Extract ALL entries you find, not just one. For each entry, extract ALL available information.

NOTE: The document may also contain additional information like:
- STATUS: "FT" (Full-Time) or "PT" (Part-Time) checkboxes
- PERSONAL USE: "Y" (Yes) or "N" (No) checkboxes
These fields are not needed for MVR extraction but are part of the employee information.

Document text:
""" + combined_text[:15000] + """

IMPORTANT: When you see the STATE column, look VERY carefully at what comes after it.
If you see "1L", "I1", "|L", "|1", or any 2-character code that might be a state abbreviation,
you MUST extract it. Even if it looks wrong, extract it - we will fix OCR errors in post-processing.
Do NOT skip the state field if you see ANY text in the STATE column.
"""
                
                # Prepare messages for API
                api_messages = [
                    {"role": "user", "content": extraction_prompt}
                ]
                
                # Call Ollama API
                if not _REQUESTS_AVAILABLE:
                    append_to_chat("system", "Error: requests library not available")
                    return
                
                payload = {
                    "model": settings["model"],
                    "messages": api_messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower temperature for more consistent extraction
                        "num_predict": 2000,  # Increased for multiple entries
                    }
                }
                
                response = requests.post(
                    f"{settings['api_url']}/api/chat",
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "message" in data and "content" in data["message"]:
                        ai_response = data["message"]["content"].strip()
                        
                        # Log raw response for debugging (truncated)
                        append_to_chat("system", f"AI response length: {len(ai_response)} characters")
                        if len(ai_response) > 500:
                            append_to_chat("system", f"AI response preview: {ai_response[:500]}...")
                        else:
                            append_to_chat("system", f"AI response: {ai_response}")
                        
                        # Try to extract JSON from response (could be array or single object)
                        import re
                        mvr_data_list = None
                        json_str = None
                        
                        # Helper function to find balanced JSON array
                        def find_json_array(text):
                            """Find a JSON array with balanced brackets"""
                            start = text.find('[')
                            if start == -1:
                                return None
                            
                            bracket_count = 0
                            in_string = False
                            escape_next = False
                            
                            for i in range(start, len(text)):
                                char = text[i]
                                
                                if escape_next:
                                    escape_next = False
                                    continue
                                
                                if char == '\\':
                                    escape_next = True
                                    continue
                                
                                if char == '"' and not escape_next:
                                    in_string = not in_string
                                    continue
                                
                                if not in_string:
                                    if char == '[':
                                        bracket_count += 1
                                    elif char == ']':
                                        bracket_count -= 1
                                        if bracket_count == 0:
                                            return text[start:i+1]
                            
                            return None
                        
                        # Try to find JSON array using balanced bracket matching
                        json_str = find_json_array(ai_response)
                        
                        if not json_str:
                            # Try to find JSON in code blocks (array)
                            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', ai_response, re.DOTALL)
                            if json_match:
                                json_str = json_match.group(1)
                            else:
                                # Try single object (backward compatibility)
                                json_match = re.search(r'\{[^{}]*"license_number"[^{}]*\}', ai_response, re.DOTALL)
                                if json_match:
                                    json_str = json_match.group(0)
                                else:
                                    # Try code block with single object
                                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
                                    if json_match:
                                        json_str = json_match.group(1)
                        
                        if json_str:
                            try:
                                mvr_data_list = json.loads(json_str)
                                # Ensure it's a list (handle single object case)
                                if not isinstance(mvr_data_list, list):
                                    mvr_data_list = [mvr_data_list]
                                
                                # Post-process extracted data to fix common issues
                                def fix_state_code_in_data(state_value):
                                    """Fix state codes that might have OCR errors"""
                                    if not state_value or not isinstance(state_value, str):
                                        return state_value
                                    
                                    state_value = state_value.strip().upper()
                                    
                                    # State code corrections (same as in _clean_ocr_text)
                                    state_corrections = {
                                        "1L": "IL", "I1": "IL", "|L": "IL", "|1": "IL",
                                        "1l": "IL", "i1": "IL", "|l": "IL",
                                        "N1": "NY", "C4": "CA", "P4": "PA",
                                        "F1": "FL", "0H": "OH", "M1": "MI",
                                    }
                                    
                                    # Check if it's a known misreading
                                    if state_value in state_corrections:
                                        return state_corrections[state_value]
                                    
                                    # If it's already a valid 2-letter state code, return it
                                    if len(state_value) == 2 and state_value.isalpha():
                                        return state_value
                                    
                                    # If it looks like a misread state code (has digits or special chars)
                                    if len(state_value) == 2:
                                        # Try to fix common patterns
                                        if state_value[0] in "1|" and state_value[1] == "L":
                                            return "IL"
                                        if state_value[0] == "I" and state_value[1] in "1|":
                                            return "IL"
                                    
                                    return state_value
                                
                                # Apply state code fixes to all entries
                                for idx, entry in enumerate(mvr_data_list, 1):
                                    # Check if state exists and is not empty
                                    raw_state = entry.get('state', '')
                                    if raw_state is None:
                                        raw_state = ''
                                    original_state = str(raw_state).strip() if raw_state else ''
                                    append_to_chat("system", f"Entry {idx}: Raw state from AI: '{original_state}' (type: {type(raw_state).__name__})")
                                    
                                    if original_state:
                                        fixed_state = fix_state_code_in_data(original_state)
                                        if fixed_state != original_state:
                                            append_to_chat("system", f"Entry {idx}: Fixed state code: '{original_state}' → '{fixed_state}'")
                                        entry['state'] = fixed_state
                                    else:
                                        # State is missing - try to find it in the cleaned text
                                        append_to_chat("system", f"Entry {idx}: WARNING - State field is empty/missing")
                                        # Log what the AI saw for this entry
                                        name = f"{entry.get('first_name', '')} {entry.get('last_name', '')}".strip()
                                        append_to_chat("system", f"  Entry data: {entry}")
                                        
                                        # Try to find state in the text using fallback extraction
                                        # Look for state codes near this entry's name or other fields
                                        try:
                                            # Import the state extraction function from MvrRunner
                                            try:
                                                from Tabs.MvrRunner import _parse_mvr_fields
                                            except ImportError:
                                                # Fallback import
                                                import importlib.util
                                                mvr_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Tabs", "MvrRunner.py")
                                                if os.path.isfile(mvr_path):
                                                    spec = importlib.util.spec_from_file_location("Tabs.MvrRunner", mvr_path)
                                                    mvr_mod = importlib.util.module_from_spec(spec)
                                                    if spec and spec.loader:
                                                        spec.loader.exec_module(mvr_mod)
                                                        _parse_mvr_fields = mvr_mod._parse_mvr_fields
                                                else:
                                                    raise ImportError("MvrRunner not found")
                                            
                                            # Create a context around this entry to search for state
                                            # Look for text that includes the person's name or license number
                                            search_context = ""
                                            if name:
                                                    # Find the name in the combined text and get surrounding context
                                                    name_parts = name.split()
                                                    if name_parts:
                                                        # Search for first name or last name in text
                                                        first_name = entry.get('first_name', '').strip()
                                                        last_name = entry.get('last_name', '').strip()
                                                        license_num = entry.get('license_number', '').strip()
                                                        
                                                        # Build search patterns
                                                        search_patterns = []
                                                        if first_name:
                                                            search_patterns.append(re.escape(first_name))
                                                        if last_name:
                                                            search_patterns.append(re.escape(last_name))
                                                        if license_num:
                                                            search_patterns.append(re.escape(license_num))
                                                        
                                                        if search_patterns:
                                                            # Find context around this entry (200 chars before and after)
                                                            pattern = '|'.join(search_patterns)
                                                            matches = list(re.finditer(pattern, combined_text, re.IGNORECASE))
                                                            if matches:
                                                                # Try each match to find the one with a state in its context
                                                                found_state_for_entry = None
                                                                for match_idx, match in enumerate(matches):
                                                                    start = max(0, match.start() - 300)
                                                                    end = min(len(combined_text), match.end() + 300)
                                                                    search_context = combined_text[start:end]
                                                                    
                                                                    # Try to extract state from this specific context
                                                                    context_results = _parse_mvr_fields(search_context)
                                                                    if context_results.get('state'):
                                                                        found_state_for_entry = context_results['state']
                                                                        break  # Found state for this entry, stop searching
                                                                
                                                                if found_state_for_entry:
                                                                    fixed_state = fix_state_code_in_data(found_state_for_entry)
                                                                    entry['state'] = fixed_state
                                                                    append_to_chat("system", f"  ✓ Found state in context: '{found_state_for_entry}' → '{fixed_state}'")
                                                                else:
                                                                    # No state found in any context - try to find state in same line/row
                                                                    # Look for table structure: name and state on same line
                                                                    for match in matches:
                                                                        # Get the line containing this match
                                                                        line_start = combined_text.rfind('\n', 0, match.start())
                                                                        line_end = combined_text.find('\n', match.end())
                                                                        if line_end == -1:
                                                                            line_end = len(combined_text)
                                                                        line_text = combined_text[line_start:line_end]
                                                                        
                                                                        # Look for state code in this line
                                                                        state_in_line = re.search(r'\b([A-Z0-9|]{2})\b', line_text.upper())
                                                                        if state_in_line:
                                                                            potential_state = state_in_line.group(1)
                                                                            # Check if it's a valid state (with OCR corrections)
                                                                            fixed_potential = fix_state_code_in_data(potential_state)
                                                                            # Verify it's a valid state code
                                                                            valid_states = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"]
                                                                            if fixed_potential in valid_states:
                                                                                entry['state'] = fixed_potential
                                                                                append_to_chat("system", f"  ✓ Found state in same line: '{potential_state}' → '{fixed_potential}'")
                                                                                found_state_for_entry = fixed_potential
                                                                                break
                                                                    
                                                                    if not found_state_for_entry:
                                                                        # Last resort: search entire text for any state code
                                                                        all_results = _parse_mvr_fields(combined_text)
                                                                        if all_results.get('state'):
                                                                            found_state = all_results['state']
                                                                            fixed_state = fix_state_code_in_data(found_state)
                                                                            entry['state'] = fixed_state
                                                                            append_to_chat("system", f"  ⚠ Using state from full text (may not be entry-specific): '{found_state}' → '{fixed_state}'")
                                                            else:
                                                                # No name match - try full text search
                                                                all_results = _parse_mvr_fields(combined_text)
                                                                if all_results.get('state'):
                                                                    found_state = all_results['state']
                                                                    fixed_state = fix_state_code_in_data(found_state)
                                                                    entry['state'] = fixed_state
                                                                    append_to_chat("system", f"  ✓ Found state in full text (no name match): '{found_state}' → '{fixed_state}'")
                                                        else:
                                                            # No searchable fields - try full text
                                                            all_results = _parse_mvr_fields(combined_text)
                                                            if all_results.get('state'):
                                                                found_state = all_results['state']
                                                                fixed_state = fix_state_code_in_data(found_state)
                                                                entry['state'] = fixed_state
                                                                append_to_chat("system", f"  ✓ Found state in full text: '{found_state}' → '{fixed_state}'")
                                            else:
                                                # No name available - try full text search
                                                all_results = _parse_mvr_fields(combined_text)
                                                if all_results.get('state'):
                                                    found_state = all_results['state']
                                                    fixed_state = fix_state_code_in_data(found_state)
                                                    entry['state'] = fixed_state
                                                    append_to_chat("system", f"  ✓ Found state in full text (no name): '{found_state}' → '{fixed_state}'")
                                        except Exception as fallback_err:
                                            append_to_chat("system", f"  ⚠ Fallback state search failed: {str(fallback_err)[:100]}")
                                
                                # Log what was extracted for debugging
                                append_to_chat("system", f"AI extracted {len(mvr_data_list)} entr{'y' if len(mvr_data_list) == 1 else 'ies'} from JSON")
                                
                                # Log the raw JSON for debugging (especially DOB and state values)
                                for idx, entry in enumerate(mvr_data_list, 1):
                                    dob_value = entry.get('dob', '')
                                    state_value = entry.get('state', '')
                                    name = f"{entry.get('first_name', '')} {entry.get('last_name', '')}".strip()
                                    append_to_chat("system", f"Entry {idx} ({name}):")
                                    if dob_value:
                                        append_to_chat("system", f"  DOB: '{dob_value}'")
                                    if state_value:
                                        append_to_chat("system", f"  State (before fix): '{state_value}'")
                                    else:
                                        append_to_chat("system", f"  State: MISSING/EMPTY")
                                
                                # Import to MVR Runner
                                def import_to_mvr():
                                    try:
                                        # Try to import MvrRunner and add the entry
                                        mvr_module = None
                                        try:
                                            from Tabs import MvrRunner
                                            mvr_module = MvrRunner
                                            callback = getattr(MvrRunner, '_add_mvr_entry_callback', None)
                                        except (ImportError, AttributeError):
                                            # Try alternative import
                                            import importlib
                                            mvr_module = importlib.import_module('Tabs.MvrRunner')
                                            callback = getattr(mvr_module, '_add_mvr_entry_callback', None)
                                        
                                        if callback:
                                            imported_count = 0
                                            skipped_count = 0
                                            total_entries = len(mvr_data_list)
                                            append_to_chat("system", f"Processing {total_entries} MVR entr{'y' if total_entries == 1 else 'ies'}...")
                                            
                                            for idx, mvr_data in enumerate(mvr_data_list, 1):
                                                # Log what we're trying to import
                                                name_info = f"{mvr_data.get('first_name', '')} {mvr_data.get('last_name', '')}".strip()
                                                if not name_info:
                                                    name_info = f"Entry {idx} (no name)"
                                                
                                                # Show full data being imported - explicitly show state
                                                state_before_import = mvr_data.get('state', '')
                                                data_preview = {k: v for k, v in mvr_data.items() if v}
                                                append_to_chat("system", f"Processing entry {idx}/{total_entries}: {name_info}")
                                                append_to_chat("system", f"  State before import: '{state_before_import}'")
                                                append_to_chat("system", f"  Full data: {data_preview}")
                                                
                                                # Make a copy to avoid any mutation issues
                                                import copy
                                                mvr_data_copy = copy.deepcopy(mvr_data)
                                                
                                                try:
                                                    success, message = callback(mvr_data_copy, source="Ollama AI")
                                                    if success:
                                                        imported_count += 1
                                                        append_to_chat("system", f"✓ Imported entry {idx}: {name_info}")
                                                    else:
                                                        skipped_count += 1
                                                        append_to_chat("system", f"⚠ Skipped entry {idx}: {name_info} - {message}")
                                                except Exception as e:
                                                    skipped_count += 1
                                                    append_to_chat("system", f"✗ Error importing entry {idx}: {name_info} - {str(e)}")
                                                    import traceback
                                                    append_to_chat("system", f"  Error details: {traceback.format_exc()[:200]}")
                                            
                                            if imported_count > 0:
                                                append_to_chat("system", f"✓ Successfully imported {imported_count} of {total_entries} MVR entr{'y' if imported_count == 1 else 'ies'} to MVR Runner")
                                                if skipped_count > 0:
                                                    append_to_chat("system", f"⚠ {skipped_count} entr{'y' if skipped_count == 1 else 'ies'} skipped (likely duplicates)")
                                                
                                                # Scroll listbox to top so user can see all entries
                                                try:
                                                    if mvr_module:
                                                        scroll_func = getattr(mvr_module, '_scroll_listbox_to_top', None)
                                                        if scroll_func:
                                                            scroll_func()
                                                except Exception:
                                                    pass
                                                
                                                update_status(f"MVR data imported: {imported_count}/{total_entries} entr{'y' if imported_count == 1 else 'ies'} - check MVR Runner tab")
                                            else:
                                                append_to_chat("system", f"⚠ No entries imported ({skipped_count} skipped - likely all duplicates)")
                                                update_status("MVR extraction completed - see chat for details")
                                        else:
                                            # Fallback: show the data and instructions
                                            for idx, mvr_data in enumerate(mvr_data_list, 1):
                                                data_str = "\n".join([f"{k}: {v}" for k, v in mvr_data.items() if v])
                                                append_to_chat("system", f"Entry {idx}:\n{data_str}")
                                            append_to_chat("system", f"\nSwitch to MVR Runner tab and manually enter this data.")
                                            update_status("MVR data extracted - see chat for details")
                                    except Exception as e:
                                        # Fallback: display extracted data
                                        for idx, mvr_data in enumerate(mvr_data_list, 1):
                                            data_str = "\n".join([f"{k}: {v}" for k, v in mvr_data.items() if v])
                                            append_to_chat("system", f"Entry {idx}:\n{data_str}")
                                        append_to_chat("system", f"\nPlease manually enter this in MVR Runner tab.")
                                        append_to_chat("system", f"Error importing automatically: {str(e)}")
                                        update_status("MVR data extracted - see chat")
                                
                                outer.after(0, import_to_mvr)
                            except json.JSONDecodeError as e:
                                append_to_chat("system", f"AI response format error: {str(e)}\nResponse: {ai_response[:200]}")
                                update_status("Extraction failed - invalid format")
                        else:
                            append_to_chat("system", f"Could not find JSON in AI response:\n{ai_response[:500]}")
                            update_status("Extraction failed - no JSON found")
                    else:
                        append_to_chat("system", "Unexpected API response format")
                        update_status("Extraction failed")
                else:
                    append_to_chat("system", f"API error: {response.status_code}")
                    update_status("Extraction failed")
            except Exception as e:
                append_to_chat("system", f"Error extracting MVR: {str(e)}")
                update_status("Extraction error")
        
        chat_thread = threading.Thread(target=extract_worker, daemon=True)
        chat_thread.start()
    
    def send_message():
        """Send message to Ollama"""
        nonlocal ollama_connected, chat_thread
        
        # Get input text
        user_input = input_text.get("1.0", "end-1c").strip()
        if not user_input:
            return
        
        # Check if Ollama is connected
        if not ollama_connected:
            messagebox.showwarning(
                "Ollama Not Connected",
                "Cannot connect to Ollama. Make sure Ollama is running.\n\n"
                "You can start Ollama from the Start Menu or run 'ollama serve' in a terminal."
            )
            return
        
        # Check if already processing
        if chat_thread and chat_thread.is_alive():
            messagebox.showwarning(
                "Already Processing",
                "Please wait for the current response to complete."
            )
            return
        
        # Clear input
        input_text.delete("1.0", "end")
        
        # Add document context if available
        full_message = user_input
        if document_context:
            context_text = "\n\n".join([f"--- Document Content ---\n{ctx}" for ctx in document_context[-3:]])  # Include last 3 documents
            full_message = f"{context_text}\n\n--- User Question ---\n{user_input}"
            # Clear document context after using it (optional - remove this line if you want to keep context)
            # document_context.clear()
        
        # Add to conversation
        append_to_chat("user", user_input)
        conversation_history.append({"role": "user", "content": full_message})
        
        # Prepare messages for API (keep last 20 messages for context)
        api_messages = conversation_history[-20:]
        
        # Update status
        update_status("Thinking...")
        
        # Run chat in background thread
        chat_thread = threading.Thread(
            target=_chat_with_ollama,
            args=(settings["api_url"], settings["model"], api_messages, settings, chat_callback),
            daemon=True
        )
        chat_thread.start()
    
    def clear_conversation():
        """Clear conversation history"""
        nonlocal conversation_history, document_context
        
        conversation_history.clear()
        document_context.clear()
        chat_display.config(state="normal")
        chat_display.delete("1.0", "end")
        append_to_chat("system", "Conversation cleared.")
        chat_display.config(state="disabled")
    
    def check_connection():
        """Check Ollama connection and update UI"""
        nonlocal ollama_connected
        
        update_status("Checking connection...")
        if _check_ollama_connection(settings["api_url"]):
            ollama_connected = True
            models = _get_available_models(settings["api_url"])
            if models:
                update_status(f"Connected - {len(models)} model(s) available")
                append_to_chat("system", f"Connected to Ollama. Available models: {', '.join(models)}")
                
                # Update model dropdown if it exists
                if hasattr(outer, '_model_var'):
                    current_model = settings.get("model", "")
                    if current_model not in models and models:
                        # Use first available model if current not found
                        settings["model"] = models[0]
                        outer._model_var.set(models[0])
                        _save_settings(settings)
            else:
                update_status("Connected - No models found")
                append_to_chat("system", "Connected to Ollama, but no models are installed.")
        else:
            ollama_connected = False
            update_status("Not connected - Start Ollama")
            append_to_chat("system", "Cannot connect to Ollama. Make sure Ollama is running.")
    
    # OCR processing state
    ocr_thread = None
    
    def process_document(file_path: str):
        """Process a document with OCR/Vision and add to chat"""
        nonlocal ocr_thread
        
        if ocr_thread and ocr_thread.is_alive():
            messagebox.showwarning("Already Processing", "Please wait for the current processing to complete.")
            return
        
        def ocr_worker():
            try:
                update_status("Extracting text from document...")
                ocr_engine = settings.get("ocr_engine", "tesseract")
                
                # Check availability
                if ocr_engine == "ollama_vision":
                    if not ollama_connected:
                        append_to_chat("system", "Ollama is not connected. Cannot use vision model. Falling back to Tesseract.")
                        ocr_engine = "tesseract"
                    else:
                        # Check if vision model is available
                        vision_model = settings.get("vision_model", "llava")
                        models = _get_available_models(settings["api_url"])
                        if vision_model not in models:
                            append_to_chat("system", f"Vision model '{vision_model}' not found. Install it with: ollama pull {vision_model}")
                            append_to_chat("system", "Falling back to Tesseract.")
                            ocr_engine = "tesseract"
                
                if ocr_engine == "easyocr" and not _EASYOCR_AVAILABLE:
                    append_to_chat("system", "EasyOCR is not installed. Falling back to Tesseract.")
                    ocr_engine = "tesseract"
                
                if ocr_engine == "tesseract" and not _TESSERACT_AVAILABLE:
                    append_to_chat("system", "Tesseract OCR is not installed. Please install pytesseract and Tesseract.")
                    update_status("OCR not available")
                    return
                
                # Extract text
                if ocr_engine == "ollama_vision":
                    extracted_text = extract_text_from_document(
                        file_path,
                        ocr_engine,
                        api_url=settings["api_url"],
                        vision_model=settings.get("vision_model", "llava"),
                        settings=settings
                    )
                else:
                    extracted_text = extract_text_from_document(file_path, ocr_engine)
                
                if extracted_text and not extracted_text.startswith("Error") and not extracted_text.startswith("Tesseract OCR error") and not extracted_text.startswith("EasyOCR error") and not extracted_text.startswith("Ollama vision error"):
                    # Clean OCR text and store in document context (don't display in input)
                    cleaned_text = _clean_ocr_text(extracted_text)
                    document_context.append(cleaned_text)
                    
                    # Try to extract tables from PDF
                    tables = []
                    if file_path.lower().endswith('.pdf'):
                        try:
                            # First try text-based extraction
                            tables = extract_tables_from_pdf(file_path, use_ocr=False)
                            # If no tables found and it's likely scanned, try OCR-based
                            if not tables:
                                # Check if PDF has text layer
                                doc = fitz.open(file_path)
                                has_text = False
                                for page in doc:
                                    if page.get_text().strip():
                                        has_text = True
                                        break
                                doc.close()
                                if not has_text:
                                    # Likely scanned, use OCR
                                    tables = extract_tables_from_pdf(file_path, use_ocr=True)
                        except Exception:
                            pass
                    
                    # Update UI in main thread
                    def update_ui():
                        msg = f"Document processed: {os.path.basename(file_path)} ({len(extracted_text)} characters extracted)"
                        if tables:
                            msg += f"\nFound {len(tables)} table(s)"
                            for table_info in tables:
                                table_text = format_table_as_text(table_info["table"])
                                if table_text:
                                    append_to_chat("system", f"Table from page {table_info['page']} ({table_info['method']}):\n{table_text[:500]}...")
                        append_to_chat("system", msg)
                        update_status("Ready - Document ready for analysis")
                    
                    outer.after(0, update_ui)
                else:
                    error_msg = extracted_text if extracted_text else "Failed to extract text from document."
                    append_to_chat("system", f"OCR Error: {error_msg}")
                    update_status("OCR failed")
            except Exception as e:
                append_to_chat("system", f"Error processing document: {str(e)}")
                update_status("Error")
        
        ocr_thread = threading.Thread(target=ocr_worker, daemon=True)
        ocr_thread.start()
    
    def upload_document():
        """Open file dialog to select a document"""
        file_path = filedialog.askopenfilename(
            title="Select Document",
            filetypes=[
                ("All Supported", "*.pdf;*.png;*.jpg;*.jpeg;*.tiff;*.bmp"),
                ("PDF files", "*.pdf"),
                ("Image files", "*.png;*.jpg;*.jpeg;*.tiff;*.bmp"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            process_document(file_path)
    
    # Buttons
    send_btn = ttk.Button(
        button_frame,
        text="Send (Enter)",
        command=send_message
    )
    send_btn.pack(side="left", padx=(0, 5))
    
    upload_btn = ttk.Button(
        button_frame,
        text="Upload Document",
        command=upload_document
    )
    upload_btn.pack(side="left", padx=5)
    
    extract_mvr_btn = ttk.Button(
        button_frame,
        text="Extract MVR → MVR Runner",
        command=extract_mvr_with_ai
    )
    extract_mvr_btn.pack(side="left", padx=5)
    
    # Add paste image from clipboard functionality
    def paste_image_from_clipboard():
        """Paste image from clipboard and process with OCR"""
        nonlocal ocr_thread
        
        if ocr_thread and ocr_thread.is_alive():
            messagebox.showwarning("Already Processing", "Please wait for the current OCR to complete.")
            return
        
        try:
            # Try to get image from clipboard
            clipboard_image = None
            try:
                # Try PIL Image from clipboard
                if _PIL_AVAILABLE:
                    from PIL import ImageGrab
                    clipboard_image = ImageGrab.grabclipboard()
                    if clipboard_image and isinstance(clipboard_image, Image.Image):
                        pass  # Got it
                    else:
                        clipboard_image = None
            except:
                pass
            
            if not clipboard_image:
                messagebox.showwarning("No Image", "No image found in clipboard. Copy an image first (Ctrl+C or screenshot).")
                return
            
            def process_clipboard_image():
                try:
                    update_status("Processing image from clipboard...")
                    
                    # Import numpy - check if available
                    try:
                        import numpy as np
                        numpy_available = True
                    except ImportError:
                        numpy_available = False
                        append_to_chat("system", "Error: numpy is not installed. Please install it with: pip install numpy")
                        update_status("numpy not installed")
                        return
                    
                    if _PIL_AVAILABLE and isinstance(clipboard_image, Image.Image):
                        img = clipboard_image
                        # Convert image to RGB mode (required for Tesseract and EasyOCR)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                    else:
                        append_to_chat("system", "Error: Could not process clipboard image.")
                        update_status("Image processing failed")
                        return
                    
                    # Convert to numpy array for OCR (for EasyOCR)
                    img_array = None
                    if _EASYOCR_AVAILABLE:
                        img_array = np.array(img)
                    
                    # Determine OCR engine
                    ocr_engine = settings.get("ocr_engine", "tesseract")
                    
                    extracted_text = None
                    easyocr_text = None
                    tesseract_text = None
                    ocr_used = None
                    tables = []
                    
                    # Try EasyOCR first (better for tables)
                    # Note: For very short text like "IL", Tesseract with PSM 8 might work better
                    if _EASYOCR_AVAILABLE and img_array is not None:
                        try:
                            # Initialize EasyOCR reader (reuse if possible, but create new for each image to avoid issues)
                            reader = easyocr.Reader(['en'], gpu=False)
                            # EasyOCR returns: [(bbox, text, confidence), ...]
                            # bbox format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                            # For better accuracy on short text, we can adjust parameters
                            # detail=1 returns detailed info with bboxes - needed for table detection
                            # paragraph=False helps with short text
                            # mag_ratio=1.5: Magnify image 1.5x to better detect small text like "IL"
                            # min_size=10: Lower minimum text size to detect smaller text (default is 20)
                            # width_ths and height_ths adjusted for better detection of short text
                            result = reader.readtext(img_array, detail=1, paragraph=False, mag_ratio=1.5, min_size=10, width_ths=0.3, height_ths=0.3)
                            
                            if result:
                                # Extract text - EasyOCR result structure is simpler
                                text_lines = []
                                lines = []  # For table detection
                                
                                for line_result in result:
                                    if line_result and len(line_result) >= 2:
                                        # line_result[0] is bbox, line_result[1] is text, line_result[2] is confidence
                                        text = line_result[1] if isinstance(line_result[1], str) else str(line_result[1])
                                        
                                        if text and text.strip():
                                            text_lines.append(text.strip())
                                            
                                            # For table detection
                                            bbox = line_result[0]
                                            if bbox and len(bbox) >= 4:
                                                # Calculate center Y coordinate
                                                y_center = sum([point[1] for point in bbox]) / len(bbox)
                                                lines.append((y_center, text.strip(), bbox))
                                
                                easyocr_text = "\n".join(text_lines) if text_lines else None
                                
                                # Debug: log extraction details
                                if easyocr_text:
                                    append_to_chat("system", f"✓ EasyOCR extracted {len(text_lines)} text line(s), {len(easyocr_text)} total characters")
                                    # Log the actual extracted text for debugging state codes
                                    append_to_chat("system", f"EasyOCR raw text: {easyocr_text[:500]}")  # First 500 chars
                                    # Specifically look for state-like patterns
                                    state_patterns = re.findall(r'\b([A-Z0-9|]{2})\b', easyocr_text)
                                    if state_patterns:
                                        append_to_chat("system", f"EasyOCR found potential state codes: {state_patterns}")
                                    
                                    # Look specifically for "STATE" column and what follows it
                                    state_column_matches = re.findall(r'\bSTATE\s+([A-Z0-9|]{1,3})\b', easyocr_text, re.IGNORECASE)
                                    if state_column_matches:
                                        append_to_chat("system", f"EasyOCR found text after 'STATE' label: {state_column_matches}")
                                    
                                    # Look for common IL misreadings specifically
                                    il_patterns = re.findall(r'\b([1|I][1|L]|[I1][L1])\b', easyocr_text, re.IGNORECASE)
                                    if il_patterns:
                                        append_to_chat("system", f"EasyOCR found potential IL misreadings: {il_patterns}")
                                
                                # Try to detect table structure
                                if lines:
                                    lines.sort(key=lambda x: x[0])
                                    rows = []
                                    current_row = []
                                    current_y = None
                                    y_threshold = 20
                                    
                                    for y, text, bbox in lines:
                                        if current_y is None or abs(y - current_y) < y_threshold:
                                            current_row.append((text, bbox))
                                            current_y = y
                                        else:
                                            if current_row:
                                                current_row.sort(key=lambda x: sum([p[0] for p in x[1]]) / len(x[1]))
                                                rows.append([cell[0] for cell in current_row])
                                            current_row = [(text, bbox)]
                                            current_y = y
                                    
                                    if current_row:
                                        current_row.sort(key=lambda x: sum([p[0] for p in x[1]]) / len(x[1]))
                                        rows.append([cell[0] for cell in current_row])
                                    
                                    if len(rows) > 1:  # Has multiple rows, likely a table
                                        tables.append({
                                            "page": 1,
                                            "table": rows,
                                            "method": "easyocr"
                                        })
                        except Exception as e:
                            # Log the error for debugging
                            error_msg = f"EasyOCR error: {str(e)}"
                            append_to_chat("system", error_msg)
                            import traceback
                            error_details = traceback.format_exc()
                            append_to_chat("system", f"EasyOCR traceback:\n{error_details[:500]}")
                    
                    # ALWAYS try Tesseract to combine results with EasyOCR
                    # Tesseract with PSM 8 (single word) is better for short text like "IL"
                    # We'll combine results from both engines to catch everything
                    if _TESSERACT_AVAILABLE:
                        # Log that we're running Tesseract to combine with EasyOCR
                        if easyocr_text:
                            append_to_chat("system", "Running Tesseract OCR to combine with EasyOCR results...")
                        elif not _EASYOCR_AVAILABLE:
                            append_to_chat("system", "EasyOCR not available - using Tesseract OCR...")
                        else:
                            append_to_chat("system", "EasyOCR didn't extract text - trying Tesseract OCR...")
                        
                        try:
                            # Try different PSM modes for better detection
                            # PSM 8 = single word (best for short codes like "IL")
                            # PSM 7 = single text line
                            # PSM 6 = uniform block of text, PSM 11 = sparse text, PSM 4 = single column
                            psm_modes = [('8', 'single word'), ('7', 'single line'), ('6', 'uniform block'), ('11', 'sparse text'), ('4', 'single column'), ('3', 'fully automatic')]
                            
                            for psm, desc in psm_modes:
                                try:
                                    # Ensure image is RGB for Tesseract
                                    tesseract_img = img
                                    if tesseract_img.mode != 'RGB':
                                        tesseract_img = tesseract_img.convert('RGB')
                                    
                                    result_text = pytesseract.image_to_string(
                                        tesseract_img, 
                                        lang='eng', 
                                        config=f'--psm {psm}'
                                    )
                                    if result_text and result_text.strip():
                                        tesseract_text = result_text
                                        append_to_chat("system", f"✓ Tesseract (PSM {psm} - {desc}) extracted {len(tesseract_text.strip())} characters")
                                        # Log the actual extracted text for debugging state codes
                                        append_to_chat("system", f"Tesseract raw text: {tesseract_text[:500]}")  # First 500 chars
                                        # Specifically look for state-like patterns
                                        state_patterns = re.findall(r'\b([A-Z0-9|]{2})\b', tesseract_text)
                                        if state_patterns:
                                            append_to_chat("system", f"Tesseract found potential state codes: {state_patterns}")
                                        
                                        # Look specifically for "STATE" column and what follows it
                                        state_column_matches = re.findall(r'\bSTATE\s+([A-Z0-9|]{1,3})\b', tesseract_text, re.IGNORECASE)
                                        if state_column_matches:
                                            append_to_chat("system", f"Tesseract found text after 'STATE' label: {state_column_matches}")
                                        
                                        # Look for common IL misreadings specifically
                                        il_patterns = re.findall(r'\b([1|I][1|L]|[I1][L1])\b', tesseract_text, re.IGNORECASE)
                                        if il_patterns:
                                            append_to_chat("system", f"Tesseract found potential IL misreadings: {il_patterns}")
                                        ocr_used = "tesseract"
                                        break
                                except Exception as e:
                                    # Continue to next PSM mode
                                    error_str = str(e)
                                    if "Unsupported image format" not in error_str and "format/type" not in error_str:
                                        # Only log non-format errors
                                        append_to_chat("system", f"Tesseract PSM {psm} error: {error_str}")
                                    continue
                            
                            # If still no text, try without specific PSM (default)
                            if not tesseract_text or not tesseract_text.strip():
                                try:
                                    # Ensure image is in correct format for Tesseract
                                    # Tesseract works best with RGB images
                                    tesseract_img = img
                                    if tesseract_img.mode != 'RGB':
                                        tesseract_img = tesseract_img.convert('RGB')
                                    
                                    result_text = pytesseract.image_to_string(tesseract_img, lang='eng')
                                    if result_text and result_text.strip():
                                        tesseract_text = result_text
                                        append_to_chat("system", f"✓ Tesseract (default) extracted {len(tesseract_text.strip())} characters")
                                        ocr_used = "tesseract"
                                except Exception as e:
                                    error_detail = str(e)
                                    # Provide more helpful error message
                                    if "Unsupported image format" in error_detail or "format/type" in error_detail:
                                        append_to_chat("system", f"Tesseract image format error. Trying to convert image...")
                                        try:
                                            # Try saving to bytes and reloading
                                            from io import BytesIO
                                            img_bytes = BytesIO()
                                            img.save(img_bytes, format='PNG')
                                            img_bytes.seek(0)
                                            reloaded_img = Image.open(img_bytes)
                                            reloaded_img = reloaded_img.convert('RGB')
                                            result_text = pytesseract.image_to_string(reloaded_img, lang='eng')
                                            if result_text and result_text.strip():
                                                tesseract_text = result_text
                                                append_to_chat("system", f"✓ Tesseract (after conversion) extracted {len(tesseract_text.strip())} characters")
                                                ocr_used = "tesseract"
                                            else:
                                                append_to_chat("system", f"Tesseract: Image converted but no text found")
                                        except Exception as e2:
                                            append_to_chat("system", f"Tesseract conversion error: {str(e2)}")
                                    else:
                                        append_to_chat("system", f"Tesseract default mode error: {error_detail}")
                                    
                        except Exception as e:
                            error_msg = f"Tesseract error: {str(e)}"
                            append_to_chat("system", error_msg)
                            import traceback
                            traceback.print_exc()
                    elif not _TESSERACT_AVAILABLE:
                        append_to_chat("system", "Tesseract not available. Please install pytesseract and Tesseract OCR.")
                    
                    # Combine results from both OCR engines
                    # Merge EasyOCR and Tesseract text, prioritizing unique content
                    def combine_ocr_results(easy_text, tess_text):
                        """Combine text from both OCR engines, avoiding duplicates"""
                        if not easy_text and not tess_text:
                            return None
                        if not easy_text:
                            return tess_text
                        if not tess_text:
                            return easy_text
                        
                        # Split into lines for comparison
                        easy_lines = set(line.strip() for line in easy_text.split('\n') if line.strip())
                        tess_lines = set(line.strip() for line in tess_text.split('\n') if line.strip())
                        
                        # Combine unique lines
                        combined_lines = list(easy_lines | tess_lines)  # Union of both sets
                        
                        # Try to preserve order (prefer EasyOCR order, add Tesseract unique lines)
                        result_lines = []
                        seen = set()
                        
                        # Add EasyOCR lines first
                        for line in easy_text.split('\n'):
                            line_stripped = line.strip()
                            if line_stripped and line_stripped not in seen:
                                result_lines.append(line)
                                seen.add(line_stripped)
                        
                        # Add Tesseract unique lines
                        for line in tess_text.split('\n'):
                            line_stripped = line.strip()
                            if line_stripped and line_stripped not in seen:
                                result_lines.append(line)
                                seen.add(line_stripped)
                        
                        combined = '\n'.join(result_lines)
                        append_to_chat("system", f"Combined OCR results: {len(easy_lines)} EasyOCR lines + {len(tess_lines)} Tesseract lines = {len(result_lines)} unique lines")
                        return combined
                    
                    # Combine both OCR results
                    extracted_text = combine_ocr_results(easyocr_text, tesseract_text)
                    
                    # Update UI
                    def update_ui():
                        # Capture extracted_text from outer scope
                        nonlocal extracted_text
                        if extracted_text and extracted_text.strip():
                            # Clean OCR text to fix common issues (dates, checkbox marks)
                            cleaned_text = _clean_ocr_text(extracted_text)
                            document_context.append(cleaned_text)
                            # Use cleaned version for all display purposes
                            msg = f"Image processed from clipboard ({len(cleaned_text)} characters extracted)"
                            if tables:
                                msg += f"\nFound {len(tables)} table(s)"
                                for table_info in tables:
                                    table_text = format_table_as_text(table_info["table"])
                                    if table_text:
                                        append_to_chat("system", f"Table from clipboard ({table_info['method']}):\n{table_text[:1000]}...")
                            
                            # Display the extracted text so AI can see it
                            append_to_chat("system", msg)
                            
                            # Check if checkbox information is present and add context (use cleaned text)
                            checkbox_note = ""
                            if "FT" in cleaned_text or "PT" in cleaned_text:
                                checkbox_note += "\nNote: STATUS checkboxes detected (FT=Full-Time, PT=Part-Time). "
                            if (" Y " in cleaned_text or " N " in cleaned_text or 
                                cleaned_text.startswith("Y ") or cleaned_text.startswith("N ") or
                                " Y\n" in cleaned_text or " N\n" in cleaned_text):
                                checkbox_note += "PERSONAL USE checkboxes detected (Y=Yes, N=No)."
                            
                            # Show extracted text (truncate if very long, but show enough for context)
                            display_text = cleaned_text
                            if len(display_text) > 2000:
                                display_text = display_text[:2000] + "\n... (truncated, full text available for MVR extraction)"
                            
                            append_to_chat("system", f"Extracted text:\n{display_text}")
                            if checkbox_note:
                                append_to_chat("system", checkbox_note.strip())
                            update_status("Ready - Image processed")
                        else:
                            # Provide more detailed error message
                            error_details = []
                            if not _EASYOCR_AVAILABLE and not _TESSERACT_AVAILABLE:
                                error_details.append("No OCR engines available. Install EasyOCR or Tesseract.")
                            elif not _EASYOCR_AVAILABLE:
                                error_details.append("EasyOCR not available.")
                            elif not _TESSERACT_AVAILABLE:
                                error_details.append("Tesseract not available.")
                            else:
                                error_details.append("OCR engines available but no text extracted. Image may be blank or unreadable.")
                            
                            error_msg = "Could not extract text from clipboard image."
                            if error_details:
                                error_msg += f"\n{error_details[0]}"
                            
                            append_to_chat("system", error_msg)
                            update_status("Image processing failed - no text extracted")
                    
                    outer.after(0, update_ui)
                except Exception as e:
                    error_msg = f"Error processing clipboard image: {str(e)}"
                    append_to_chat("system", error_msg)
                    update_status(f"Error: {str(e)[:50]}")
                    # Also log full error for debugging
                    import traceback
                    traceback.print_exc()
            
            ocr_thread = threading.Thread(target=process_clipboard_image, daemon=True)
            ocr_thread.start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to paste image: {str(e)}")
    
    paste_image_btn = ttk.Button(
        button_frame,
        text="Paste Image (OCR)",
        command=paste_image_from_clipboard
    )
    paste_image_btn.pack(side="left", padx=5)
    
    clear_btn = ttk.Button(
        button_frame,
        text="Clear Conversation",
        command=clear_conversation
    )
    clear_btn.pack(side="left", padx=5)
    
    refresh_btn = ttk.Button(
        button_frame,
        text="Refresh Connection",
        command=check_connection
    )
    refresh_btn.pack(side="left", padx=5)
    
    # Settings button
    def show_settings():
        """Show settings dialog"""
        settings_window = tk.Toplevel(outer.winfo_toplevel())
        settings_window.title("Ollama Settings")
        settings_window.geometry("500x550")
        settings_window.transient(outer.winfo_toplevel())
        settings_window.grab_set()
        
        settings_frame = ttk.Frame(settings_window, padding=20)
        settings_frame.pack(fill="both", expand=True)
        
        # API URL
        ttk.Label(settings_frame, text="Ollama API URL:", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w", pady=5
        )
        api_url_var = tk.StringVar(value=settings.get("api_url", "http://localhost:11434"))
        api_url_entry = ttk.Entry(settings_frame, textvariable=api_url_var, width=40)
        api_url_entry.grid(row=0, column=1, columnspan=2, sticky="ew", pady=5, padx=5)
        
        # Model selection
        ttk.Label(settings_frame, text="Model:", font=("Segoe UI", 9, "bold")).grid(
            row=1, column=0, sticky="w", pady=5
        )
        model_var = tk.StringVar(value=settings.get("model", "gemma2"))
        model_combo = ttk.Combobox(settings_frame, textvariable=model_var, width=37, state="readonly")
        model_combo.grid(row=1, column=1, columnspan=2, sticky="ew", pady=5, padx=5)
        
        # Store reference for updating
        outer._model_var = model_var
        
        def refresh_models():
            """Refresh available models"""
            api_url = api_url_var.get()
            models = _get_available_models(api_url)
            if models:
                model_combo['values'] = models
                if model_var.get() not in models and models:
                    model_var.set(models[0])
                messagebox.showinfo("Models Refreshed", f"Found {len(models)} model(s)")
            else:
                model_combo['values'] = []
                messagebox.showwarning("No Models", "No models found. Make sure Ollama is running and models are installed.")
        
        refresh_models_btn = ttk.Button(settings_frame, text="Refresh Models", command=refresh_models)
        refresh_models_btn.grid(row=1, column=3, padx=5)
        
        # Temperature
        ttk.Label(settings_frame, text="Temperature:", font=("Segoe UI", 9, "bold")).grid(
            row=2, column=0, sticky="w", pady=5
        )
        temp_var = tk.DoubleVar(value=settings.get("temperature", 0.7))
        temp_scale = ttk.Scale(
            settings_frame,
            from_=0.1,
            to=2.0,
            variable=temp_var,
            orient="horizontal"
        )
        temp_scale.grid(row=2, column=1, columnspan=2, sticky="ew", pady=5, padx=5)
        temp_label = ttk.Label(settings_frame, text=f"{temp_var.get():.2f}")
        temp_label.grid(row=2, column=3, padx=5)
        
        def update_temp_label(*args):
            temp_label.config(text=f"{temp_var.get():.2f}")
        
        temp_var.trace("w", update_temp_label)
        
        # Top P
        ttk.Label(settings_frame, text="Top P:", font=("Segoe UI", 9, "bold")).grid(
            row=3, column=0, sticky="w", pady=5
        )
        top_p_var = tk.DoubleVar(value=settings.get("top_p", 0.9))
        top_p_scale = ttk.Scale(
            settings_frame,
            from_=0.1,
            to=1.0,
            variable=top_p_var,
            orient="horizontal"
        )
        top_p_scale.grid(row=3, column=1, columnspan=2, sticky="ew", pady=5, padx=5)
        top_p_label = ttk.Label(settings_frame, text=f"{top_p_var.get():.2f}")
        top_p_label.grid(row=3, column=3, padx=5)
        
        def update_top_p_label(*args):
            top_p_label.config(text=f"{top_p_var.get():.2f}")
        
        top_p_var.trace("w", update_top_p_label)
        
        # Max tokens
        ttk.Label(settings_frame, text="Max Tokens:", font=("Segoe UI", 9, "bold")).grid(
            row=4, column=0, sticky="w", pady=5
        )
        max_tokens_var = tk.IntVar(value=settings.get("max_tokens", 512))
        max_tokens_entry = ttk.Entry(settings_frame, textvariable=max_tokens_var, width=20)
        max_tokens_entry.grid(row=4, column=1, sticky="w", pady=5, padx=5)
        
        # OCR Engine selection
        ttk.Label(settings_frame, text="Document Processing:", font=("Segoe UI", 9, "bold")).grid(
            row=5, column=0, sticky="w", pady=5
        )
        ocr_engine_var = tk.StringVar(value=settings.get("ocr_engine", "tesseract"))
        ocr_engine_combo = ttk.Combobox(
            settings_frame,
            textvariable=ocr_engine_var,
            values=["tesseract", "easyocr", "ollama_vision"],
            state="readonly",
            width=37
        )
        ocr_engine_combo.grid(row=5, column=1, columnspan=2, sticky="ew", pady=5, padx=5)
        
        # Vision model selection (only shown when ollama_vision is selected)
        vision_model_label = ttk.Label(settings_frame, text="Vision Model:", font=("Segoe UI", 9, "bold"))
        vision_model_var = tk.StringVar(value=settings.get("vision_model", "llava"))
        vision_model_combo = ttk.Combobox(
            settings_frame,
            textvariable=vision_model_var,
            values=["llava", "llava:13b", "granit-vision", "bakllava"],
            state="readonly",
            width=37
        )
        
        def update_vision_model_visibility(*args):
            if ocr_engine_var.get() == "ollama_vision":
                vision_model_label.grid(row=6, column=0, sticky="w", pady=5)
                vision_model_combo.grid(row=6, column=1, columnspan=2, sticky="ew", pady=5, padx=5)
            else:
                vision_model_label.grid_remove()
                vision_model_combo.grid_remove()
        
        ocr_engine_var.trace("w", update_vision_model_visibility)
        update_vision_model_visibility()  # Initial state
        
        # OCR status label
        ocr_status_text = []
        if _TESSERACT_AVAILABLE:
            ocr_status_text.append("Tesseract: ✓")
        else:
            ocr_status_text.append("Tesseract: ✗")
        if _EASYOCR_AVAILABLE:
            ocr_status_text.append("EasyOCR: ✓")
        else:
            ocr_status_text.append("EasyOCR: ✗")
        ocr_status_text.append("Ollama Vision: Available")
        
        ocr_status_label = ttk.Label(
            settings_frame,
            text=" | ".join(ocr_status_text),
            font=("Segoe UI", 8),
            foreground="gray"
        )
        ocr_status_label.grid(row=5, column=3, padx=5, sticky="w")
        
        # Buttons
        button_frame2 = ttk.Frame(settings_frame)
        button_frame2.grid(row=7, column=0, columnspan=4, pady=20)
        
        def save_settings_and_close():
            new_settings = dict(settings)
            new_settings["api_url"] = api_url_var.get()
            new_settings["model"] = model_var.get()
            new_settings["temperature"] = temp_var.get()
            new_settings["top_p"] = top_p_var.get()
            new_settings["max_tokens"] = max_tokens_var.get()
            new_settings["ocr_engine"] = ocr_engine_var.get()
            new_settings["vision_model"] = vision_model_var.get()
            
            _save_settings(new_settings)
            settings.update(new_settings)
            
            # Recheck connection
            check_connection()
            
            settings_window.destroy()
        
        ttk.Button(button_frame2, text="Save", command=save_settings_and_close).pack(
            side="left", padx=5
        )
        ttk.Button(button_frame2, text="Cancel", command=settings_window.destroy).pack(
            side="left", padx=5
        )
        
        settings_frame.columnconfigure(1, weight=1)
    
    ttk.Button(
        button_frame,
        text="Settings...",
        command=show_settings
    ).pack(side="right", padx=5)
    
    # Bind Enter key to send (Shift+Enter for newline)
    def on_input_key(event):
        if event.keysym == "Return":
            if event.state & 0x1:  # Shift+Enter = newline
                return None
            else:  # Enter = send
                send_message()
                return "break"
    
    input_text.bind("<KeyPress>", on_input_key)
    
    # Add Ctrl+F search functionality
    search_window = None
    search_entry = None
    search_results = []
    current_search_index = -1
    
    def show_search_dialog():
        """Show search dialog"""
        nonlocal search_window, search_entry, search_results, current_search_index
        
        if search_window and search_window.winfo_exists():
            search_window.lift()
            if search_entry:
                search_entry.focus()
            return
        
        search_window = tk.Toplevel(outer.winfo_toplevel())
        search_window.title("Search")
        search_window.geometry("400x120")
        search_window.transient(outer.winfo_toplevel())
        search_window.resizable(False, False)
        
        # Position near chat display
        try:
            x = outer.winfo_rootx() + 50
            y = outer.winfo_rooty() + 50
            search_window.geometry(f"400x120+{x}+{y}")
        except:
            pass
        
        search_frame = ttk.Frame(search_window, padding=10)
        search_frame.pack(fill="both", expand=True)
        
        ttk.Label(search_frame, text="Search in conversation:", font=("Segoe UI", 9)).pack(anchor="w")
        
        search_entry = ttk.Entry(search_frame, width=40, font=("Segoe UI", 10))
        search_entry.pack(fill="x", pady=5)
        search_entry.focus()
        
        def do_search(event=None):
            nonlocal search_results, current_search_index
            query = search_entry.get().strip()
            if not query:
                return
            
            # Get all text from chat display
            chat_display.config(state="normal")
            all_text = chat_display.get("1.0", "end-1c")
            chat_display.config(state="disabled")
            
            # Find all occurrences (case-insensitive)
            search_results = []
            start = "1.0"
            while True:
                pos = chat_display.search(query, start, "end", nocase=True)
                if not pos:
                    break
                end_pos = f"{pos}+{len(query)}c"
                search_results.append((pos, end_pos))
                start = end_pos
            
            if search_results:
                current_search_index = 0
                highlight_search_result()
                status_label.config(text=f"Found {len(search_results)} result(s)")
            else:
                status_label.config(text="No results found")
                current_search_index = -1
        
        def highlight_search_result():
            """Highlight current search result"""
            if not search_results or current_search_index < 0:
                return
            
            # Remove previous highlights
            chat_display.tag_remove("search_highlight", "1.0", "end")
            
            # Highlight current result
            pos, end_pos = search_results[current_search_index]
            chat_display.tag_add("search_highlight", pos, end_pos)
            chat_display.tag_config("search_highlight", background="yellow", foreground="black")
            
            # Scroll to result
            chat_display.see(pos)
            chat_display.mark_set("insert", pos)
            
            status_label.config(text=f"Result {current_search_index + 1} of {len(search_results)}")
        
        def next_result():
            nonlocal current_search_index
            if search_results:
                current_search_index = (current_search_index + 1) % len(search_results)
                highlight_search_result()
        
        def prev_result():
            nonlocal current_search_index
            if search_results:
                current_search_index = (current_search_index - 1) % len(search_results)
                highlight_search_result()
        
        button_frame = ttk.Frame(search_frame)
        button_frame.pack(fill="x", pady=5)
        
        ttk.Button(button_frame, text="Find", command=do_search).pack(side="left", padx=2)
        ttk.Button(button_frame, text="Next", command=next_result).pack(side="left", padx=2)
        ttk.Button(button_frame, text="Previous", command=prev_result).pack(side="left", padx=2)
        ttk.Button(button_frame, text="Close", command=search_window.destroy).pack(side="right", padx=2)
        
        status_label = ttk.Label(search_frame, text="", font=("Segoe UI", 8))
        status_label.pack(anchor="w", pady=2)
        
        search_entry.bind("<Return>", do_search)
        search_entry.bind("<Escape>", lambda e: search_window.destroy())
        
        # Close search window when main window closes
        def on_search_close():
            nonlocal search_window
            if search_window:
                chat_display.tag_remove("search_highlight", "1.0", "end")
            search_window = None
        
        search_window.protocol("WM_DELETE_WINDOW", on_search_close)
    
    # Bind Ctrl+F to search
    def on_ctrl_f(event):
        show_search_dialog()
        return "break"
    
    chat_display.bind("<Control-f>", on_ctrl_f)
    chat_display.bind("<Control-F>", on_ctrl_f)
    outer.bind("<Control-f>", on_ctrl_f)
    outer.bind("<Control-F>", on_ctrl_f)
    
    # Also bind Ctrl+V in input area to check for images
    def on_paste(event):
        """Handle paste - check if it's an image, otherwise allow normal paste"""
        # Check clipboard for image BEFORE allowing normal paste
        try:
            if _PIL_AVAILABLE:
                from PIL import ImageGrab
                # Check if clipboard contains an image
                clipboard_content = ImageGrab.grabclipboard()
                if clipboard_content and isinstance(clipboard_content, Image.Image):
                    # It's an image, process it and prevent normal paste
                    paste_image_from_clipboard()
                    return "break"  # Prevent normal paste
        except Exception as e:
            # If checking clipboard fails, allow normal paste
            # Don't show error to user - just allow normal paste
            pass
        
        # Allow normal text paste if not an image or if check failed
        # Return None to allow default paste behavior (don't prevent default)
        return None
    
    # Bind paste events with add="+" to not override default behavior completely
    # This way normal paste still works if no image detected
    input_text.bind_class("Text", "<Control-v>", on_paste, add="+")
    input_text.bind_class("Text", "<Control-V>", on_paste, add="+")
    
    # Also bind directly to this widget
    input_text.bind("<Control-v>", on_paste, add="+")
    input_text.bind("<Control-V>", on_paste, add="+")
    
    # Check connection on startup
    check_thread = threading.Thread(target=check_connection, daemon=True)
    check_thread.start()
    
    return outer

