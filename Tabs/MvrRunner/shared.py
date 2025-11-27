import os
import re
import json
import sys
import socket
from typing import Dict, Tuple, Optional

# Optional, show clear error if missing dependencies at runtime
_IMPORT_ERRORS = []
try:
    import fitz  # PyMuPDF
except Exception as e:
    _IMPORT_ERRORS.append(("PyMuPDF (fitz)", str(e)))
    fitz = None  # type: ignore

try:
    from playwright.sync_api import sync_playwright
except Exception as e:
    _IMPORT_ERRORS.append(("playwright", str(e)))
    sync_playwright = None  # type: ignore

try:
    from legacy_form_helpers import set_select_dropdown_value, fill_text_input
except Exception as e:
    _IMPORT_ERRORS.append(("legacy_form_helpers", str(e)))
    set_select_dropdown_value = None  # type: ignore
    fill_text_input = None  # type: ignore

try:
    import psutil  # process detection
except Exception as e:
    _IMPORT_ERRORS.append(("psutil", str(e)))
    psutil = None  # type: ignore

try:
    from tkinterdnd2 import DND_FILES
except Exception as e:
    _IMPORT_ERRORS.append(("tkinterdnd2", str(e)))
    DND_FILES = None  # type: ignore

try:
    import cv2
    import numpy as np
except Exception as e:
    _IMPORT_ERRORS.append(("opencv-python", str(e)))
    cv2 = None  # type: ignore
    np = None  # type: ignore


# MVR Settings file path
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
_MVR_SETTINGS_PATH = os.path.join(_PROJECT_ROOT, "mvr_settings.json")
_MVR_UI_SETTINGS_PATH = os.path.join(_PROJECT_ROOT, "mvr_ui_settings.json")

# Display size presets (similar to Binder Splitter)
_SIZE_PRESETS = {
    "Small": {"font_size": 9, "button_padding": 2},
    "Medium": {"font_size": 10, "button_padding": 4},
    "Large": {"font_size": 11, "button_padding": 6},
}
_DEFAULT_UI_SETTINGS = {"display_size": "Medium", "directions_collapsed": False, "copy_paste_mode": False}

_DEFAULT_MVR_SETTINGS = {
    "url": "https://example.com/",
    "selectors": {
        "license_number": "input[name='license']",
        "last_name": "input[name='lastName']",
        "first_name": "input[name='firstName']",
        "dob": "input[name='dob']",
        "state": "#ddComboState",
        "order_type": "#OrderTypeCombo",
        "product": "#ProductTypeCombo",
        "purpose": "select[name='purposeCode']",
    },
    "use_existing_chrome": True,
    "debug_port": "9222",
    "account_id": "",
    "user_id": "",
    "password": "",
    "auto_click_recaptcha": True,
    "login_selectors": {
        "account_id": "",
        "user_id": "",
        "password": "",
    },
}


def _load_mvr_settings():
    """Load MVR settings from file"""
    try:
        if os.path.isfile(_MVR_SETTINGS_PATH):
            with open(_MVR_SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                settings = dict(_DEFAULT_MVR_SETTINGS)
                settings.update(data)
                if "selectors" not in settings:
                    settings["selectors"] = dict(_DEFAULT_MVR_SETTINGS["selectors"])
                else:
                    for key, val in _DEFAULT_MVR_SETTINGS["selectors"].items():
                        if key not in settings["selectors"]:
                            settings["selectors"][key] = val
                if "login_selectors" not in settings:
                    settings["login_selectors"] = dict(_DEFAULT_MVR_SETTINGS["login_selectors"])
                else:
                    for key, val in _DEFAULT_MVR_SETTINGS["login_selectors"].items():
                        if key not in settings["login_selectors"]:
                            settings["login_selectors"][key] = val
                if "account_id" in settings:
                    print(f"DEBUG: Loaded account_id: '{settings['account_id']}'")
                return settings
    except Exception as e:
        print(f"DEBUG: Error loading MVR settings: {e}")
    return dict(_DEFAULT_MVR_SETTINGS)


def _save_mvr_settings(settings):
    """Save MVR settings to file"""
    try:
        os.makedirs(os.path.dirname(_MVR_SETTINGS_PATH), exist_ok=True)
        account_id_to_save = settings.get("account_id", "")
        print(f"DEBUG: Saving account_id: '{account_id_to_save}'")
        with open(_MVR_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        try:
            with open(_MVR_SETTINGS_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
                saved_account_id = saved.get("account_id", "")
                print(f"DEBUG: Verified saved account_id: '{saved_account_id}'")
                if "account_id" in saved:
                    return True
        except Exception as e:
            print(f"DEBUG: Error verifying save: {e}")
    except Exception as e:
        print(f"DEBUG: Error saving MVR settings: {e}")
        return False
    return True


def _load_ui_settings():
    """Load UI settings (display size) from file"""
    try:
        if os.path.isfile(_MVR_UI_SETTINGS_PATH):
            with open(_MVR_UI_SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {**_DEFAULT_UI_SETTINGS, **data}
    except Exception:
        pass
    return dict(_DEFAULT_UI_SETTINGS)


def _save_ui_settings(settings):
    """Save UI settings to file"""
    try:
        os.makedirs(os.path.dirname(_MVR_UI_SETTINGS_PATH), exist_ok=True)
        with open(_MVR_UI_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _apply_display_size(root, size_key):
    """Apply display size settings to the window"""
    preset = _SIZE_PRESETS.get(size_key, _SIZE_PRESETS["Medium"])
    font_size = preset["font_size"]
    
    style = tk.ttk.Style(root)
    try:
        style.configure("TLabel", font=("Segoe UI", font_size))
        button_pad = preset["button_padding"]
        if size_key == "Large":
            extra_vertical = max(4, int(font_size * 0.5))
        else:
            extra_vertical = max(2, int(font_size * 0.3))
        style.configure("TButton", 
                       font=("Segoe UI", font_size), 
                       padding=(button_pad, button_pad + extra_vertical))
        style.configure("TEntry", font=("Segoe UI", font_size))
        style.configure("TCombobox", font=("Segoe UI", font_size))
        style.configure("TCheckbutton", font=("Segoe UI", font_size))
    except Exception:
        pass
    
    try:
        base_width = 1000
        base_height = 700
        scale_factors = {
            "Small": 0.85,
            "Medium": 1.0,
            "Large": 1.15
        }
        scale = scale_factors.get(size_key, 1.0)
        new_width = int(base_width * scale)
        new_height = int(base_height * scale)
        try:
            current_geom = root.geometry()
            if current_geom and "x" in current_geom:
                parts = current_geom.split("+")
                if len(parts) > 1:
                    pos = "+" + "+".join(parts[1:])
                    root.geometry(f"{new_width}x{new_height}{pos}")
                else:
                    root.geometry(f"{new_width}x{new_height}")
            else:
                root.geometry(f"{new_width}x{new_height}")
        except Exception:
            root.geometry(f"{new_width}x{new_height}")
    except Exception:
        pass


def _is_port_open(host: str, port: int, timeout: float = 0.25) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        return s.connect_ex((host, port)) == 0
    finally:
        try:
            s.close()
        except Exception:
            pass


def _is_chrome_running() -> bool:
    """Quick check if any Chrome process is running."""
    if not psutil:
        return False
    try:
        for p in psutil.process_iter(attrs=["name"]):
            name = (p.info.get("name") or "").lower()
            if "chrome" in name or "chrome.exe" in name:
                return True
    except Exception:
        pass
    return False


def _find_chrome_executable():
    """Find Chrome executable path on Windows"""
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get('LOCALAPPDATA', ''), r'Google\Chrome\Application\chrome.exe'),
        os.path.join(os.environ.get('PROGRAMFILES', ''), r'Google\Chrome\Application\chrome.exe'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), r'Google\Chrome\Application\chrome.exe'),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


def _get_chrome_user_data_dir():
    """Get the Chrome user data directory for the current user."""
    if os.name == 'nt':  # Windows
        user_data_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'User Data')
    else:  # macOS/Linux
        if os.name == 'posix':
            home = os.environ.get('HOME', '')
            if sys.platform == 'darwin':  # macOS
                user_data_dir = os.path.join(home, 'Library', 'Application Support', 'Google', 'Chrome')
            else:  # Linux
                user_data_dir = os.path.join(home, '.config', 'google-chrome')
        else:
            user_data_dir = None
    return user_data_dir if user_data_dir and os.path.exists(user_data_dir) else None


def _detect_checkboxes_in_pdf(pdf_path: str, page_num: int = 0, region: Tuple[float, float, float, float] = None) -> list:
    """
    Detect checkboxes in a PDF page using OpenCV.
    
    Args:
        pdf_path: Path to the PDF file
        page_num: Page number (0-indexed)
        region: Optional tuple (x_ratio, y_ratio, width_ratio, height_ratio) to limit search area
                Values are ratios of page dimensions (0.0 to 1.0)
                Example: (0.7, 0.0, 0.3, 1.0) = rightmost 30% of page
    
    Returns:
        List of dicts with checkbox info: [{'x': int, 'y': int, 'checked': bool, 'confidence': float}, ...]
    """
    if cv2 is None or np is None:
        print("OpenCV not available for checkbox detection")
        return []
    
    if not fitz:
        print("PyMuPDF not available for PDF rendering")
        return []
    
    try:
        doc = fitz.open(pdf_path)
        if page_num >= len(doc):
            doc.close()
            return []
        
        page = doc[page_num]
        
        # Render page to image at high DPI for better detection
        dpi = 200
        pix = page.get_pixmap(dpi=dpi)
        
        # Convert to numpy array for OpenCV
        img_data = pix.tobytes("png")
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        doc.close()
        
        if img is None:
            return []
        
        # Apply region filter if specified
        h, w = img.shape[:2]
        if region:
            x_start = int(region[0] * w)
            y_start = int(region[1] * h)
            region_w = int(region[2] * w)
            region_h = int(region[3] * h)
            img_region = img[y_start:y_start+region_h, x_start:x_start+region_w]
            offset_x, offset_y = x_start, y_start
        else:
            img_region = img
            offset_x, offset_y = 0, 0
        
        # Convert to grayscale
        gray = cv2.cvtColor(img_region, cv2.COLOR_BGR2GRAY)
        
        # Apply binary threshold
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        checkboxes = []
        
        # Scale factor based on DPI (checkboxes typically 10-20 pixels at 72 DPI)
        scale = dpi / 72.0
        min_size = int(10 * scale)
        max_size = int(40 * scale)
        
        for cnt in contours:
            x, y, box_w, box_h = cv2.boundingRect(cnt)
            
            # Filter by size (checkbox-like dimensions)
            if not (min_size < box_w < max_size and min_size < box_h < max_size):
                continue
            
            # Filter by aspect ratio (checkboxes are roughly square)
            aspect_ratio = box_w / float(box_h)
            if not (0.7 < aspect_ratio < 1.4):
                continue
            
            # Check if it's filled (checked) by analyzing pixel density inside
            roi = gray[y:y+box_h, x:x+box_w]
            if roi.size == 0:
                continue
            
            # Calculate how much of the interior is dark (filled)
            # Exclude the border by taking inner region
            margin = max(2, int(box_w * 0.15))
            inner = roi[margin:-margin, margin:-margin] if margin * 2 < min(box_w, box_h) else roi
            
            if inner.size == 0:
                continue
            
            dark_pixels = np.sum(inner < 128)
            total_pixels = inner.size
            fill_ratio = dark_pixels / total_pixels
            
            # Determine if checked based on fill ratio
            # Empty checkbox: ~0-15% fill, Checked: >25% fill
            is_checked = fill_ratio > 0.20
            confidence = min(1.0, fill_ratio * 2) if is_checked else min(1.0, (0.20 - fill_ratio) * 5)
            
            checkboxes.append({
                'x': x + offset_x,
                'y': y + offset_y,
                'width': box_w,
                'height': box_h,
                'checked': is_checked,
                'fill_ratio': round(fill_ratio, 3),
                'confidence': round(confidence, 2)
            })
        
        # Sort by position (top to bottom, then left to right)
        checkboxes.sort(key=lambda c: (c['y'] // 20, c['x']))
        
        return checkboxes
        
    except Exception as e:
        print(f"Checkbox detection error: {e}")
        return []


def _detect_checkboxes_in_rightmost_columns(pdf_path: str, page_num: int = 0, num_columns: int = 2) -> list:
    """
    Detect checkboxes specifically in the rightmost columns of a PDF page.
    Useful for forms where STATUS (FT/PT) and PERSONAL USE (Y/N) are in right columns.
    
    Args:
        pdf_path: Path to the PDF file
        page_num: Page number (0-indexed)
        num_columns: Number of rightmost columns to scan (default 2)
    
    Returns:
        List of checkbox info grouped by row
    """
    # Scan rightmost portion of page (adjust width based on num_columns)
    # Typically each column is ~10-15% of page width
    region_width = min(0.4, num_columns * 0.15)
    region = (1.0 - region_width, 0.0, region_width, 1.0)
    
    checkboxes = _detect_checkboxes_in_pdf(pdf_path, page_num, region)
    
    if not checkboxes:
        return []
    
    # Group checkboxes by row (similar y-coordinate)
    row_tolerance = 15  # pixels
    rows = []
    current_row = []
    last_y = -100
    
    for cb in checkboxes:
        if abs(cb['y'] - last_y) > row_tolerance:
            if current_row:
                rows.append(current_row)
            current_row = [cb]
        else:
            current_row.append(cb)
        last_y = cb['y']
    
    if current_row:
        rows.append(current_row)
    
    # For each row, sort checkboxes left to right
    for row in rows:
        row.sort(key=lambda c: c['x'])
    
    return rows


def _extract_text_from_pdf(pdf_path: str) -> str:
    """Fast extraction for text-based PDFs using PyMuPDF."""
    if not fitz:
        raise RuntimeError("PyMuPDF is not installed. Please install 'pymupdf'.")
    doc = fitz.open(pdf_path)
    try:
        parts = []
        for page in doc:
            parts.append(page.get_text("blocks"))
        lines = []
        for blocks in parts:
            for b in blocks:
                if len(b) >= 5 and isinstance(b[4], str):
                    lines.append(b[4].strip())
        return "\n".join([ln for ln in lines if ln])
    finally:
        doc.close()


def _parse_mvr_fields(text: str) -> Dict[str, str]:
    """Extract MVR fields: License Number, Last Name, First Name, DOB, and State."""
    results: Dict[str, str] = {}
    
    # License Number
    license_patterns = [
        (r"(?i)\b(Driver'?s?\s*License|DL|License\s*(?:No|Number|#)?\.?)\s*:?\s*([A-Z0-9\-]{4,})", 2),
        (r"(?i)\bLicense\s*:?\s*([A-Z0-9\-]{4,})", 1),
        (r"(?i)\bDL\s*:?\s*([A-Z0-9\-]{4,})", 1),
    ]
    for pat, group_idx in license_patterns:
        m = re.search(pat, text)
        if m:
            results["license_number"] = m.group(group_idx).strip()
            break
    
    # DOB
    dob_patterns = [
        (r"(?i)\b(DOB|Date\s+of\s+Birth|Birth\s+Date)\s*:?\s*([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4})", 2),
        (r"(?i)\bDOB\s*:?\s*([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4})", 1),
        (r"\b([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4})\b", 1),
    ]
    for pat, group_idx in dob_patterns:
        m = re.search(pat, text)
        if m:
            results["dob"] = m.group(group_idx).strip()
            break
    
    # Name
    name_patterns = [
        (r"(?i)\b(Name|Driver\s+Name|Full\s+Name)\s*:?\s*([A-Z][A-Za-z ,.'-]+)", 2),
        (r"(?i)\bName\s*:?\s*([A-Z][A-Za-z ,.'-]+)", 1),
    ]
    full_name = ""
    for pat, group_idx in name_patterns:
        m = re.search(pat, text)
        if m:
            full_name = m.group(group_idx).strip()
            break
    
    if full_name:
        suffixes = ["Jr", "Jr.", "Sr", "Sr.", "II", "III", "IV", "V", "Esq", "Esq."]
        if "," in full_name:
            parts = [p.strip() for p in full_name.split(",", 1)]
            if len(parts) == 2:
                results["last_name"] = parts[0].strip()
                first_part = parts[1].strip()
                first_words = first_part.split()
                results["first_name"] = first_words[0].strip() if first_words else ""
            else:
                results["last_name"] = full_name.strip()
                results["first_name"] = ""
        else:
            parts = full_name.split()
            if len(parts) >= 2:
                last_word = parts[-1].rstrip(".,")
                if last_word in suffixes and len(parts) >= 3:
                    results["last_name"] = " ".join(parts[-2:]).strip()
                    results["first_name"] = parts[0].strip()
                else:
                    results["last_name"] = parts[-1].strip()
                    results["first_name"] = parts[0].strip()
            elif len(parts) == 1:
                results["last_name"] = parts[0].strip()
                results["first_name"] = ""
    
    # State
    state_patterns = [
        (r"(?i)^\s*([A-Z][A-Z\s]+?)\s+Driver\s+Record\s*-\s*[A-Z0-9]+\s*$", 1),
        (r"(?i)([A-Z][A-Z\s]+?)\s+Driver\s+Record\s*-\s*[A-Z0-9]+", 1),
        (r"(?i)\b(State|State\s+of\s+Issue|Issuing\s+State|License\s+State|State\s+Code)\s*:?\s*([A-Z]{2})\b", 2),
        (r"(?i)\b(State|State\s+of\s+Issue|Issuing\s+State|License\s+State|State\s+Code)\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", 2),
        (r"\b([A-Z]{2})\s+(?:Driver|License|DL|MVR|Drivers?)\b", 1),
        (r"\b(?:Driver|License|DL|MVR|Drivers?)\s+([A-Z]{2})\b", 1),
        (r"\b([A-Z]{2})\s+[0-9]{4,}\b", 1),
        (r"(?i)\b(State|State\s+Code)\s*:?\s*([A-Z]{2})\b", 2),
        (r"(?i)\b(State|State\s+Code)\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", 2),
        (r"(?i)(?:License|DL|MVR|Driver).*?(?:State|State\s+of\s+Issue|Issuing\s+State)\s*:?\s*([A-Z]{2})\b", 1),
        (r"(?i)(?:License|DL|MVR|Driver).*?(?:State|State\s+of\s+Issue|Issuing\s+State)\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", 1),
    ]
    us_states_abbrev = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"]
    
    state_name_to_abbrev = {
        "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR", "CALIFORNIA": "CA",
        "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE", "FLORIDA": "FL", "GEORGIA": "GA",
        "HAWAII": "HI", "IDAHO": "ID", "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA",
        "KANSAS": "KS", "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
        "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS", "MISSOURI": "MO",
        "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV", "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ",
        "NEW MEXICO": "NM", "NEW YORK": "NY", "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH",
        "OKLAHOMA": "OK", "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC",
        "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT", "VERMONT": "VT",
        "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV", "WISCONSIN": "WI", "WYOMING": "WY",
        "DISTRICT OF COLUMBIA": "DC", "WASHINGTON DC": "DC", "DC": "DC"
    }
    
    for pat, group_idx in state_patterns:
        m = re.search(pat, text, re.MULTILINE)
        if m:
            state_candidate = m.group(group_idx).strip()
            state_candidate_upper = state_candidate.upper()
            state_candidate_upper = re.sub(r'\s+', ' ', state_candidate_upper)
            
            if len(state_candidate_upper) == 2 and state_candidate_upper in us_states_abbrev:
                results["state"] = state_candidate_upper
                break
            elif state_candidate_upper in state_name_to_abbrev:
                results["state"] = state_name_to_abbrev[state_candidate_upper]
                break
            else:
                matched = False
                for state_name, abbrev in state_name_to_abbrev.items():
                    if state_candidate_upper == state_name:
                        results["state"] = abbrev
                        matched = True
                        break
                
                if not matched:
                    for state_name, abbrev in state_name_to_abbrev.items():
                        if state_name.startswith(state_candidate_upper) or state_candidate_upper in state_name:
                            if len(state_candidate_upper) >= 3:
                                results["state"] = abbrev
                                matched = True
                                break
                
                if matched:
                    break
                break
    
    return results


def format_dob_value(value):
    """Format a DOB value to __/__/____ format"""
    if not value:
        return "__/__/____"
    digits = ''.join(filter(str.isdigit, value))
    if len(digits) == 0:
        return "__/__/____"
    digits = digits[:8]
    
    formatted = ""
    if len(digits) >= 1:
        formatted = digits[0]
    if len(digits) >= 2:
        formatted = digits[0:2]
    if len(digits) >= 3:
        formatted = digits[0:2] + "/" + digits[2]
    if len(digits) >= 4:
        formatted = digits[0:2] + "/" + digits[2:4]
    if len(digits) >= 5:
        formatted = digits[0:2] + "/" + digits[2:4] + "/" + digits[4]
    if len(digits) >= 6:
        formatted = digits[0:2] + "/" + digits[2:4] + "/" + digits[4:6]
    if len(digits) >= 7:
        formatted = digits[0:2] + "/" + digits[2:4] + "/" + digits[4:7]
    if len(digits) >= 8:
        formatted = digits[0:2] + "/" + digits[2:4] + "/" + digits[4:8]
    
    while len(formatted) < 10:
        if len(formatted) == 2:
            formatted += "/"
        elif len(formatted) == 5:
            formatted += "/"
        else:
            formatted += "_"
    
    return formatted


def _parse_mvr_with_checkboxes(pdf_path: str, page_num: int = 0) -> Dict[str, str]:
    """
    Extract MVR fields including checkbox-based STATUS and PERSONAL USE fields.
    
    This function:
    1. Extracts text from PDF and parses standard fields (name, DOB, license, state)
    2. Detects checkboxes in rightmost columns using OpenCV
    3. Maps checkbox states to STATUS (FT/PT) and PERSONAL USE (Y/N)
    
    Args:
        pdf_path: Path to the PDF file
        page_num: Page number to scan (0-indexed)
    
    Returns:
        Dict with all MVR fields including 'status' and 'personal_use'
    """
    # First, extract text-based fields
    text = _extract_text_from_pdf(pdf_path)
    results = _parse_mvr_fields(text)
    
    # Initialize checkbox fields with empty values
    results['status'] = ''
    results['personal_use'] = ''
    
    # Try to detect checkboxes in rightmost columns
    try:
        checkbox_rows = _detect_checkboxes_in_rightmost_columns(pdf_path, page_num, num_columns=2)
        
        if checkbox_rows:
            # Analyze checkbox layout
            # Typical MVR form has STATUS column (FT/PT) and PERSONAL USE column (Y/N)
            # Each row should have 2-4 checkboxes: [FT] [PT] | [Y] [N]
            
            # Find the first row with enough checkboxes to analyze
            for row in checkbox_rows:
                if len(row) >= 2:
                    # Sort by x-coordinate (left to right)
                    sorted_boxes = sorted(row, key=lambda c: c['x'])
                    
                    # Determine midpoint to split into STATUS and PERSONAL columns
                    if len(sorted_boxes) >= 4:
                        # 4+ checkboxes: assume [FT][PT][Y][N] layout
                        status_boxes = sorted_boxes[:2]
                        personal_boxes = sorted_boxes[2:4]
                    elif len(sorted_boxes) == 2:
                        # 2 checkboxes: could be STATUS only or PERSONAL only
                        # Check x-positions to determine which column
                        page_width = _get_pdf_page_width(pdf_path, page_num)
                        if page_width > 0:
                            midpoint = page_width * 0.85  # STATUS usually at ~80%, PERSONAL at ~90%
                            avg_x = sum(c['x'] for c in sorted_boxes) / len(sorted_boxes)
                            if avg_x < midpoint:
                                status_boxes = sorted_boxes
                                personal_boxes = []
                            else:
                                status_boxes = []
                                personal_boxes = sorted_boxes
                        else:
                            status_boxes = sorted_boxes
                            personal_boxes = []
                    else:
                        # 3 checkboxes: [FT][PT][Y] or [FT][Y][N] - ambiguous
                        status_boxes = sorted_boxes[:2]
                        personal_boxes = sorted_boxes[2:]
                    
                    # Determine STATUS (FT vs PT)
                    if len(status_boxes) >= 2:
                        # Two boxes for status: first is FT, second is PT
                        ft_checked = status_boxes[0].get('checked', False)
                        pt_checked = status_boxes[1].get('checked', False)
                        
                        if ft_checked and not pt_checked:
                            results['status'] = 'FT'
                        elif pt_checked and not ft_checked:
                            results['status'] = 'PT'
                        elif ft_checked and pt_checked:
                            # Both checked - use higher confidence
                            if status_boxes[0].get('confidence', 0) > status_boxes[1].get('confidence', 0):
                                results['status'] = 'FT'
                            else:
                                results['status'] = 'PT'
                    elif len(status_boxes) == 1:
                        # Single status checkbox - if checked, assume FT
                        if status_boxes[0].get('checked', False):
                            results['status'] = 'FT'
                    
                    # Determine PERSONAL USE (Y vs N)
                    if len(personal_boxes) >= 2:
                        # Two boxes for personal: first is Y, second is N
                        y_checked = personal_boxes[0].get('checked', False)
                        n_checked = personal_boxes[1].get('checked', False)
                        
                        if y_checked and not n_checked:
                            results['personal_use'] = 'Y'
                        elif n_checked and not y_checked:
                            results['personal_use'] = 'N'
                        elif y_checked and n_checked:
                            # Both checked - use higher confidence
                            if personal_boxes[0].get('confidence', 0) > personal_boxes[1].get('confidence', 0):
                                results['personal_use'] = 'Y'
                            else:
                                results['personal_use'] = 'N'
                    elif len(personal_boxes) == 1:
                        # Single personal checkbox - if checked, assume Y
                        if personal_boxes[0].get('checked', False):
                            results['personal_use'] = 'Y'
                        else:
                            results['personal_use'] = 'N'
                    
                    # Found valid row, stop searching
                    if results['status'] or results['personal_use']:
                        break
                        
    except Exception as e:
        print(f"Checkbox detection error in _parse_mvr_with_checkboxes: {e}")
    
    return results


def _get_pdf_page_width(pdf_path: str, page_num: int = 0) -> int:
    """Get the width of a PDF page in pixels (at 150 DPI)."""
    if not fitz:
        return 0
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        width = int(page.rect.width * 150 / 72)  # Convert points to pixels at 150 DPI
        doc.close()
        return width
    except Exception:
        return 0


# Export shared constants and functions
__all__ = [
    '_IMPORT_ERRORS', '_SIZE_PRESETS', '_DEFAULT_UI_SETTINGS', '_DEFAULT_MVR_SETTINGS',
    '_load_mvr_settings', '_save_mvr_settings', '_load_ui_settings', '_save_ui_settings',
    '_apply_display_size', '_is_port_open', '_is_chrome_running', '_find_chrome_executable',
    '_get_chrome_user_data_dir', '_extract_text_from_pdf', '_parse_mvr_fields', 
    '_parse_mvr_with_checkboxes', '_detect_checkboxes_in_rightmost_columns',
    'format_dob_value', 'DND_FILES'
]

