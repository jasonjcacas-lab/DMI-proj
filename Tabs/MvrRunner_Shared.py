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


# Export shared constants and functions
__all__ = [
    '_IMPORT_ERRORS', '_SIZE_PRESETS', '_DEFAULT_UI_SETTINGS', '_DEFAULT_MVR_SETTINGS',
    '_load_mvr_settings', '_save_mvr_settings', '_load_ui_settings', '_save_ui_settings',
    '_apply_display_size', '_is_port_open', '_is_chrome_running', '_find_chrome_executable',
    '_extract_text_from_pdf', '_parse_mvr_fields', 'format_dob_value', 'DND_FILES'
]

