# -*- coding: utf-8 -*-
"""
Ollama AI Tool - Chat interface for Ollama models
"""
import os
import sys
import threading
import json
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
_PADDLEOCR_AVAILABLE = False
_TESSERACT_AVAILABLE = False
_PYMUPDF_AVAILABLE = False
_PIL_AVAILABLE = False
_PDFPLUMBER_AVAILABLE = False

try:
    from paddleocr import PaddleOCR
    _PADDLEOCR_AVAILABLE = True
except ImportError:
    _PADDLEOCR_AVAILABLE = False

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
    "ocr_engine": "tesseract",  # "tesseract", "paddleocr", or "ollama_vision"
    "vision_model": "llava",  # Vision model for Ollama (llava, granit-vision, etc.)
}

# Ollama API state
_ollama_available = False
_available_models = []


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


def _extract_text_with_paddleocr(file_path: str) -> str:
    """Extract text from PDF or image using PaddleOCR"""
    if not _PADDLEOCR_AVAILABLE:
        return None
    
    try:
        import numpy as np
        # Initialize PaddleOCR (use_angle_cls=True for better accuracy)
        ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
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
                    # Convert PIL image to numpy array for PaddleOCR
                    img_array = np.array(img)
                    
                    # Run OCR
                    result = ocr.ocr(img_array, cls=True)
                    if result and result[0]:
                        page_text = "\n".join([line[1][0] for line in result[0] if line])
                        if page_text.strip():
                            text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
            doc.close()
        elif _PIL_AVAILABLE:
            # It's an image file
            img = Image.open(file_path)
            img_array = np.array(img)
            
            # Run OCR
            result = ocr.ocr(img_array, cls=True)
            if result and result[0]:
                text = "\n".join([line[1][0] for line in result[0] if line])
                if text.strip():
                    text_parts.append(text)
        
        return "\n\n".join(text_parts) if text_parts else None
    
    except Exception as e:
        return f"PaddleOCR error: {str(e)}"


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
    For scanned PDFs: uses PaddleOCR table recognition
    
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
    
    # For scanned PDFs or if pdfplumber found no tables, use PaddleOCR table recognition
    if use_ocr or (not tables and _PADDLEOCR_AVAILABLE):
        try:
            import numpy as np
            from io import BytesIO
            
            # Initialize PaddleOCR with table recognition
            ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False, use_gpu=False)
            
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
                    # Note: PaddleOCR's table recognition requires specific model
                    # For now, we'll extract text and try to structure it as a table
                    result = ocr.ocr(img_array, cls=True)
                    
                    if result and result[0]:
                        # Try to detect table structure from OCR results
                        # Group text by approximate Y coordinates to form rows
                        lines = []
                        for line_result in result[0]:
                            if line_result:
                                bbox = line_result[0]  # Bounding box
                                text = line_result[1][0]  # Text
                                # Calculate center Y coordinate
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
                                    "method": "paddleocr"
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
    For scanned PDFs: uses PaddleOCR table recognition
    
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
    
    # For scanned PDFs or if pdfplumber found no tables, use PaddleOCR table recognition
    if use_ocr or (not tables and _PADDLEOCR_AVAILABLE):
        try:
            import numpy as np
            from io import BytesIO
            
            # Initialize PaddleOCR with table recognition
            ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False, use_gpu=False)
            
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
                    result = ocr.ocr(img_array, cls=True)
                    
                    if result and result[0]:
                        # Try to detect table structure from OCR results
                        # Group text by approximate Y coordinates to form rows
                        lines = []
                        for line_result in result[0]:
                            if line_result:
                                bbox = line_result[0]  # Bounding box
                                text = line_result[1][0]  # Text
                                # Calculate center Y coordinate
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
                                    "method": "paddleocr"
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
    elif ocr_engine.lower() == "paddleocr":
        result = _extract_text_with_paddleocr(file_path)
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
                
                # Create a prompt for AI to extract MVR fields
                extraction_prompt = """Extract MVR (Motor Vehicle Record) information from the following document text. 
Return ONLY a JSON object with these exact fields (use empty strings if not found):
{
  "license_number": "",
  "last_name": "",
  "first_name": "",
  "dob": "",
  "state": ""
}

IMPORTANT NAME PARSING RULES:
- first_name: Extract ONLY the FIRST word of the person's name (e.g., "John" from "John Michael Smith")
- last_name: Extract ONLY the LAST word of the person's name (e.g., "Smith" from "John Michael Smith" or "Smith" from "John Michael Smith Jr.")
- If the name is "John Smith", first_name="John", last_name="Smith"
- If the name is "John Michael Smith", first_name="John", last_name="Smith"
- If the name is "John Smith Jr.", first_name="John", last_name="Jr."
- Do NOT include middle names in either field

Format DOB as MM/DD/YYYY or MM-DD-YYYY. State should be 2-letter abbreviation (e.g., "CA", "NY").
If you find a full state name, convert it to abbreviation.

Document text:
""" + combined_text[:5000]  # Limit to first 5000 chars
                
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
                        "num_predict": 500,
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
                        
                        # Try to extract JSON from response
                        import re
                        json_match = re.search(r'\{[^{}]*"license_number"[^{}]*\}', ai_response, re.DOTALL)
                        if not json_match:
                            # Try to find JSON in code blocks
                            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
                            if json_match:
                                json_match = json_match.group(1)
                            else:
                                json_match = re.search(r'\{.*?"license_number".*?\}', ai_response, re.DOTALL)
                        
                        if json_match:
                            json_str = json_match.group(0) if isinstance(json_match, re.Match) else json_match
                            try:
                                mvr_data = json.loads(json_str)
                                
                                # Import to MVR Runner
                                def import_to_mvr():
                                    try:
                                        # Try to import MvrRunner and add the entry
                                        try:
                                            from Tabs import MvrRunner
                                            callback = getattr(MvrRunner, '_add_mvr_entry_callback', None)
                                        except (ImportError, AttributeError):
                                            # Try alternative import
                                            import importlib
                                            mvr_module = importlib.import_module('Tabs.MvrRunner')
                                            callback = getattr(mvr_module, '_add_mvr_entry_callback', None)
                                        
                                        if callback:
                                            success, message = callback(mvr_data, source="Ollama AI")
                                            if success:
                                                append_to_chat("system", f"✓ MVR data imported to MVR Runner: {mvr_data.get('last_name', '')}, {mvr_data.get('first_name', '')}")
                                                update_status("MVR data imported successfully - check MVR Runner tab")
                                            else:
                                                append_to_chat("system", f"⚠ {message}")
                                                # Still show the data
                                                data_str = "\n".join([f"{k}: {v}" for k, v in mvr_data.items() if v])
                                                append_to_chat("system", f"Extracted MVR data:\n{data_str}")
                                                update_status("MVR data extracted - see chat")
                                        else:
                                            # Fallback: show the data and instructions
                                            data_str = "\n".join([f"{k}: {v}" for k, v in mvr_data.items() if v])
                                            append_to_chat("system", f"Extracted MVR data:\n{data_str}\n\nSwitch to MVR Runner tab and manually enter this data.")
                                            update_status("MVR data extracted - see chat for details")
                                    except Exception as e:
                                        # Fallback: display extracted data
                                        data_str = "\n".join([f"{k}: {v}" for k, v in mvr_data.items() if v])
                                        append_to_chat("system", f"Extracted MVR data:\n{data_str}\n\nPlease manually enter this in MVR Runner tab.")
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
                
                if ocr_engine == "paddleocr" and not _PADDLEOCR_AVAILABLE:
                    append_to_chat("system", "PaddleOCR is not installed. Falling back to Tesseract.")
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
                
                if extracted_text and not extracted_text.startswith("Error") and not extracted_text.startswith("Tesseract OCR error") and not extracted_text.startswith("PaddleOCR error") and not extracted_text.startswith("Ollama vision error"):
                    # Store extracted text in document context (don't display in input)
                    document_context.append(extracted_text)
                    
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
                        # Convert image to RGB mode (required for Tesseract and better for PaddleOCR)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                    else:
                        append_to_chat("system", "Error: Could not process clipboard image.")
                        update_status("Image processing failed")
                        return
                    
                    # Convert to numpy array for OCR (only if using PaddleOCR)
                    img_array = None
                    if _PADDLEOCR_AVAILABLE:
                        img_array = np.array(img)
                    
                    # Determine OCR engine
                    ocr_engine = settings.get("ocr_engine", "tesseract")
                    
                    extracted_text = None
                    tables = []
                    
                    # Try PaddleOCR first (better for tables)
                    if _PADDLEOCR_AVAILABLE and img_array is not None:
                        try:
                            ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False, use_gpu=False)
                            result = ocr.ocr(img_array, cls=True)
                            
                            if result and result[0]:
                                # Extract text
                                text_lines = []
                                for line_result in result[0]:
                                    if line_result and len(line_result) > 1:
                                        text = line_result[1][0] if isinstance(line_result[1], (list, tuple)) else str(line_result[1])
                                        if text:
                                            text_lines.append(text)
                                extracted_text = "\n".join(text_lines) if text_lines else None
                                
                                # Try to detect table structure
                                lines = []
                                for line_result in result[0]:
                                    if line_result and len(line_result) >= 2:
                                        try:
                                            bbox = line_result[0]
                                            text_data = line_result[1]
                                            if isinstance(text_data, (list, tuple)) and len(text_data) > 0:
                                                text = text_data[0]
                                            else:
                                                text = str(text_data)
                                            
                                            if bbox and len(bbox) > 0:
                                                y_center = sum([point[1] for point in bbox]) / len(bbox)
                                                lines.append((y_center, text, bbox))
                                        except Exception:
                                            pass  # Skip malformed entries
                                
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
                                            "method": "paddleocr"
                                        })
                        except Exception as e:
                            # Log the error for debugging
                            error_msg = f"PaddleOCR error: {str(e)}"
                            append_to_chat("system", error_msg)
                            import traceback
                            traceback.print_exc()
                    
                    # Use Tesseract if PaddleOCR not available or didn't work
                    # IMPORTANT: Always try Tesseract if no text extracted yet
                    if (not extracted_text or not extracted_text.strip()) and _TESSERACT_AVAILABLE:
                        # Log which OCR we're using
                        if not _PADDLEOCR_AVAILABLE:
                            append_to_chat("system", "PaddleOCR not available - using Tesseract OCR...")
                        elif not extracted_text:
                            append_to_chat("system", "PaddleOCR didn't extract text - trying Tesseract OCR...")
                        
                        try:
                            # Try different PSM modes for better table detection
                            # PSM 6 = uniform block of text, PSM 11 = sparse text, PSM 4 = single column
                            psm_modes = [('6', 'uniform block'), ('11', 'sparse text'), ('4', 'single column'), ('3', 'fully automatic')]
                            
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
                                        extracted_text = result_text
                                        append_to_chat("system", f"✓ Tesseract (PSM {psm} - {desc}) extracted {len(extracted_text.strip())} characters")
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
                            if not extracted_text or not extracted_text.strip():
                                try:
                                    # Ensure image is in correct format for Tesseract
                                    # Tesseract works best with RGB images
                                    tesseract_img = img
                                    if tesseract_img.mode != 'RGB':
                                        tesseract_img = tesseract_img.convert('RGB')
                                    
                                    result_text = pytesseract.image_to_string(tesseract_img, lang='eng')
                                    if result_text and result_text.strip():
                                        extracted_text = result_text
                                        append_to_chat("system", f"✓ Tesseract (default) extracted {len(extracted_text.strip())} characters")
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
                                                extracted_text = result_text
                                                append_to_chat("system", f"✓ Tesseract (after conversion) extracted {len(extracted_text.strip())} characters")
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
                    
                    # Update UI
                    def update_ui():
                        if extracted_text and extracted_text.strip():
                            document_context.append(extracted_text)
                            msg = f"Image processed from clipboard ({len(extracted_text)} characters extracted)"
                            if tables:
                                msg += f"\nFound {len(tables)} table(s)"
                                for table_info in tables:
                                    table_text = format_table_as_text(table_info["table"])
                                    if table_text:
                                        append_to_chat("system", f"Table from clipboard ({table_info['method']}):\n{table_text[:1000]}...")
                            append_to_chat("system", msg)
                            update_status("Ready - Image processed")
                        else:
                            # Provide more detailed error message
                            error_details = []
                            if not _PADDLEOCR_AVAILABLE and not _TESSERACT_AVAILABLE:
                                error_details.append("No OCR engines available. Install PaddleOCR or Tesseract.")
                            elif not _PADDLEOCR_AVAILABLE:
                                error_details.append("PaddleOCR not available.")
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
            values=["tesseract", "paddleocr", "ollama_vision"],
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
        if _PADDLEOCR_AVAILABLE:
            ocr_status_text.append("PaddleOCR: ✓")
        else:
            ocr_status_text.append("PaddleOCR: ✗")
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
        # Return None to allow default paste behavior
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

