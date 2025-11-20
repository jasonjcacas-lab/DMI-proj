import os
import re
import json
import sys
import threading
from typing import Dict, Tuple, Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import socket

# Import shared utilities
from MvrRunner_Shared import (
    _IMPORT_ERRORS, _SIZE_PRESETS, _DEFAULT_UI_SETTINGS,
    _load_mvr_settings, _save_mvr_settings, _load_ui_settings, _save_ui_settings,
    _apply_display_size, _extract_text_from_pdf, _parse_mvr_fields, format_dob_value, DND_FILES
)

# Import automation dependencies (not in shared module)
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
        "order_type": "#OrderTypeCombo",  # ID selector for faster access
        "product": "#ProductTypeCombo",  # ID selector for faster access
        "purpose": "select[name='purposeCode']",  # Purpose dropdown - will select "Insurance"
    },
    "use_existing_chrome": True,
    "debug_port": "9222",
    "account_id": "",
    "user_id": "",
    "password": "",
    "auto_click_recaptcha": True,  # Enable/disable automatic "I'm not a robot" clicking
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
                # Merge with defaults to ensure all keys exist
                settings = dict(_DEFAULT_MVR_SETTINGS)
                settings.update(data)
                # Ensure selectors dict exists and is merged
                if "selectors" not in settings:
                    settings["selectors"] = dict(_DEFAULT_MVR_SETTINGS["selectors"])
                else:
                    # Merge selector defaults
                    for key, val in _DEFAULT_MVR_SETTINGS["selectors"].items():
                        if key not in settings["selectors"]:
                            settings["selectors"][key] = val
                # Ensure login_selectors dict exists and is merged
                if "login_selectors" not in settings:
                    settings["login_selectors"] = dict(_DEFAULT_MVR_SETTINGS["login_selectors"])
                else:
                    # Merge login selector defaults
                    for key, val in _DEFAULT_MVR_SETTINGS["login_selectors"].items():
                        if key not in settings["login_selectors"]:
                            settings["login_selectors"][key] = val
                # Debug: verify account_id is loaded
                if "account_id" in settings:
                    print(f"DEBUG: Loaded account_id: '{settings['account_id']}'")
                return settings
    except Exception as e:
        print(f"DEBUG: Error loading MVR settings: {e}")
    return dict(_DEFAULT_MVR_SETTINGS)


def _save_mvr_settings(settings):
    """Save MVR settings to file"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(_MVR_SETTINGS_PATH), exist_ok=True)
        # Debug: print what we're saving
        account_id_to_save = settings.get("account_id", "")
        print(f"DEBUG: Saving account_id: '{account_id_to_save}'")
        # Write settings to file
        with open(_MVR_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        # Verify the file was written by reading it back
        try:
            with open(_MVR_SETTINGS_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
                # Verify account_id was saved
                saved_account_id = saved.get("account_id", "")
                print(f"DEBUG: Verified saved account_id: '{saved_account_id}'")
                if "account_id" in saved:
                    return True
        except Exception as e:
            print(f"DEBUG: Error verifying save: {e}")
    except Exception as e:
        # Log error but don't crash
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
    
    # Apply font size to ttk styles
    style = ttk.Style(root)
    try:
        style.configure("TLabel", font=("Segoe UI", font_size))
        # Configure button with padding tuple: (horizontal, vertical)
        # Ensure vertical padding keeps text centered and visible
        button_pad = preset["button_padding"]
        # Use tuple format: (horizontal, vertical)
        # Increase vertical padding significantly to ensure text is visible and properly centered
        # Add extra vertical padding based on font size to prevent text from being cut off
        # For Large display, add even more padding to prevent text cropping at the bottom
        if size_key == "Large":
            # Extra padding for Large to prevent text from being cropped and move it up
            extra_vertical = max(4, int(font_size * 0.5))  # More aggressive for Large
        else:
            extra_vertical = max(2, int(font_size * 0.3))  # Scale extra padding with font size
        style.configure("TButton", 
                       font=("Segoe UI", font_size), 
                       padding=(button_pad, button_pad + extra_vertical))  # Extra vertical padding
        style.configure("TEntry", font=("Segoe UI", font_size))
        style.configure("TCombobox", font=("Segoe UI", font_size))
        style.configure("TCheckbutton", font=("Segoe UI", font_size))
    except Exception:
        pass
    
    # Resize window based on display size
    try:
        # Base window size (for Medium)
        base_width = 1000
        base_height = 700
        
        # Scale factors for different sizes
        scale_factors = {
            "Small": 0.85,
            "Medium": 1.0,
            "Large": 1.15
        }
        scale = scale_factors.get(size_key, 1.0)
        
        # Calculate new size
        new_width = int(base_width * scale)
        new_height = int(base_height * scale)
        
        # Get current window geometry
        try:
            current_geom = root.geometry()
            if current_geom and "x" in current_geom:
                # Extract position if present
                parts = current_geom.split("+")
                if len(parts) > 1:
                    pos = "+" + "+".join(parts[1:])
                    root.geometry(f"{new_width}x{new_height}{pos}")
                else:
                    root.geometry(f"{new_width}x{new_height}")
            else:
                root.geometry(f"{new_width}x{new_height}")
        except Exception:
            # If geometry fails, just set size
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
    """
    Quick check if any Chrome process is running.
    """
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
    """
    Fast extraction for text-based PDFs using PyMuPDF.
    """
    if not fitz:
        raise RuntimeError("PyMuPDF is not installed. Please install 'pymupdf'.")
    doc = fitz.open(pdf_path)
    try:
        parts = []
        for page in doc:
            # Use blocks to preserve reading order better than plain text
            parts.append(page.get_text("blocks"))
        # Flatten blocks into lines; each block is a tuple (x0, y0, x1, y1, text, block_no, block_type)
        lines = []
        for blocks in parts:
            for b in blocks:
                if len(b) >= 5 and isinstance(b[4], str):
                    lines.append(b[4].strip())
        return "\n".join([ln for ln in lines if ln])
    finally:
        doc.close()


def _parse_mvr_fields(text: str) -> Dict[str, str]:
    """
    Extract MVR fields: License Number, Last Name, First Name, DOB, and State.
    Heuristic parsing - may need tuning for specific MVR formats.
    Users can edit results in the UI.
    """
    results: Dict[str, str] = {}
    
    # License Number - try multiple patterns
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
    
    # DOB - multiple date formats
    dob_patterns = [
        (r"(?i)\b(DOB|Date\s+of\s+Birth|Birth\s+Date)\s*:?\s*([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4})", 2),
        (r"(?i)\bDOB\s*:?\s*([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4})", 1),
        (r"\b([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4})\b", 1),  # Any date-like pattern
    ]
    for pat, group_idx in dob_patterns:
        m = re.search(pat, text)
        if m:
            results["dob"] = m.group(group_idx).strip()
            break
    
    # Name - try to split into Last, First
    # Handles: middle names, multiple last names, suffixes (Jr., Sr., III, etc.)
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
        # Common suffixes that should be part of last name
        suffixes = ["Jr", "Jr.", "Sr", "Sr.", "II", "III", "IV", "V", "Esq", "Esq."]
        
        # Try "LAST, FIRST MIDDLE" format first (comma-separated)
        if "," in full_name:
            parts = [p.strip() for p in full_name.split(",", 1)]
            if len(parts) == 2:
                results["last_name"] = parts[0].strip()
                # First name = first word only (ignore middle names)
                first_part = parts[1].strip()
                first_words = first_part.split()
                results["first_name"] = first_words[0].strip() if first_words else ""
            else:
                # Fallback: treat as single name
                results["last_name"] = full_name.strip()
                results["first_name"] = ""
        else:
            # No comma: assume "FIRST MIDDLE LAST" or "FIRST LAST LAST" format
            # First name = first word only, Last name = last word(s)
            parts = full_name.split()
            if len(parts) >= 2:
                # Check if last word is a suffix - if so, include it with last name
                last_word = parts[-1].rstrip(".,")
                if last_word in suffixes and len(parts) >= 3:
                    # Last name includes suffix: "Smith Jr." or "Garcia Lopez Jr."
                    results["last_name"] = " ".join(parts[-2:]).strip()
                    results["first_name"] = parts[0].strip()  # First word only
                else:
                    # Standard case: first word = first name, last word = last name
                    # Handles: "CHERRI DANIELLE JACKSON" -> First: "CHERRI", Last: "JACKSON"
                    # Handles: "John Michael Smith" -> First: "John", Last: "Smith"
                    # For multiple last names (e.g., "Maria Garcia Lopez"), 
                    # user can manually combine them if needed
                    results["last_name"] = parts[-1].strip()
                    results["first_name"] = parts[0].strip()  # First word only
            elif len(parts) == 1:
                # Single name - put in last name as fallback
                results["last_name"] = parts[0].strip()
                results["first_name"] = ""
    
    # State - try multiple patterns
    # US state abbreviations (2 letters) and full state names
    state_patterns = [
        # HIGHEST PRIORITY: SambaSafety format - "[State Name] Driver Record - [Account ID]"
        (r"(?i)^\s*([A-Z][A-Z\s]+?)\s+Driver\s+Record\s*-\s*[A-Z0-9]+\s*$", 1),  # Full state name before "Driver Record -"
        (r"(?i)([A-Z][A-Z\s]+?)\s+Driver\s+Record\s*-\s*[A-Z0-9]+", 1),  # Full state name before "Driver Record -" (anywhere in text)
        # Patterns with explicit "State" label
        (r"(?i)\b(State|State\s+of\s+Issue|Issuing\s+State|License\s+State|State\s+Code)\s*:?\s*([A-Z]{2})\b", 2),  # 2-letter abbreviation with label
        (r"(?i)\b(State|State\s+of\s+Issue|Issuing\s+State|License\s+State|State\s+Code)\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", 2),  # Full state name with label
        # Patterns without explicit label (context-based)
        (r"\b([A-Z]{2})\s+(?:Driver|License|DL|MVR|Drivers?)\b", 1),  # State abbreviation before "Driver" or "License"
        (r"\b(?:Driver|License|DL|MVR|Drivers?)\s+([A-Z]{2})\b", 1),  # State abbreviation after "Driver" or "License"
        (r"\b([A-Z]{2})\s+[0-9]{4,}\b", 1),  # State abbreviation followed by numbers (likely license number)
        # Standalone state abbreviations in common contexts
        (r"(?i)\b(State|State\s+Code)\s*:?\s*([A-Z]{2})\b", 2),  # Just "State:" or "State Code:" followed by abbreviation
        (r"(?i)\b(State|State\s+Code)\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", 2),  # Just "State:" or "State Code:" followed by full name
        # Look for state names/abbreviations near other license fields
        (r"(?i)(?:License|DL|MVR|Driver).*?(?:State|State\s+of\s+Issue|Issuing\s+State)\s*:?\s*([A-Z]{2})\b", 1),  # State abbrev near license keywords
        (r"(?i)(?:License|DL|MVR|Driver).*?(?:State|State\s+of\s+Issue|Issuing\s+State)\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", 1),  # State name near license keywords
    ]
    # Also check for common state abbreviations in context
    us_states_abbrev = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"]
    
    # Mapping from full state names to abbreviations
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
            
            # Clean up the state candidate - remove extra whitespace
            state_candidate_upper = re.sub(r'\s+', ' ', state_candidate_upper)
            
            # If it's a 2-letter code, verify it's a valid state
            if len(state_candidate_upper) == 2 and state_candidate_upper in us_states_abbrev:
                results["state"] = state_candidate_upper
                break
            # If it's a full state name, convert to abbreviation
            elif state_candidate_upper in state_name_to_abbrev:
                results["state"] = state_name_to_abbrev[state_candidate_upper]
                break
            # Try exact match first (for multi-word states like "NEW YORK")
            else:
                # Check if any state name matches exactly (case-insensitive)
                matched = False
                for state_name, abbrev in state_name_to_abbrev.items():
                    if state_candidate_upper == state_name:
                        results["state"] = abbrev
                        matched = True
                        break
                
                if not matched:
                    # Try partial match for state names (e.g., "New York" might be captured as "New" or "York")
                    # Check if any state name contains this candidate (case-insensitive)
                    for state_name, abbrev in state_name_to_abbrev.items():
                        # Check if candidate is at the start of state name (for multi-word states)
                        if state_name.startswith(state_candidate_upper) or state_candidate_upper in state_name:
                            # Make sure it's a reasonable match (not too short)
                            if len(state_candidate_upper) >= 3:  # At least 3 characters to avoid false matches
                                results["state"] = abbrev
                                matched = True
                                break
                
                if matched:
                    break
                break
    
    return results


def _ensure_playwright_browsers_installed(status_cb=None) -> None:
    """
    Make sure Playwright has installed browsers. If not, attempt a one-time install.
    """
    if sync_playwright is None:
        raise RuntimeError("playwright is not installed. Run: pip install playwright && playwright install")
    try:
        with sync_playwright() as p:
            # Try launching quickly; if missing browsers, it will throw
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception:
        # Try to install browsers
        if status_cb:
            status_cb("Installing Playwright browsers (one-time)...")
        # Fallback: use Python API to install via CLI module
        import subprocess, sys
        try:
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            raise RuntimeError(f"Failed to install Playwright browsers: {e}")


def _get_chrome_user_data_dir():
    """Get the Chrome user data directory for the current user"""
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

def _add_stealth_script(context):
    """Add stealth script to hide automation"""
    context.add_init_script("""
        // Remove webdriver property completely
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Override plugins to look more realistic
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        // Override languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        
        // Mock chrome object
        window.chrome = {
            runtime: {}
        };
        
        // Remove automation indicators
        delete navigator.__proto__.webdriver;
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Override getParameter to hide automation
        const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return originalGetParameter.call(this, parameter);
        };
        
        // Override toString to hide automation
        const originalToString = Function.prototype.toString;
        Function.prototype.toString = function() {
            if (this === navigator.webdriver) {
                return 'function webdriver() { [native code] }';
            }
            return originalToString.call(this);
        };
    """)

def _launch_chrome_with_profile_for_mvr(p, status_cb):
    """Launch Chrome using the user's profile directory to access saved passwords and login sessions"""
    user_data_dir = _get_chrome_user_data_dir()
    
    if not user_data_dir:
        if status_cb:
            status_cb("Chrome profile not found. Will launch Chrome without saved passwords...")
        return None
    
    # Check if Chrome is already running - if so, we can't use the profile
    if _is_chrome_running():
        if status_cb:
            status_cb("Chrome is already running. Cannot use profile (would conflict).")
            status_cb("Close Chrome and try again, or use CDP connection with remote debugging.")
        return None
    
    if status_cb:
        status_cb(f"Using your Chrome profile: {user_data_dir}")
        status_cb("This will use your saved passwords and login sessions!")
    
    try:
        # Try method 1: launch_persistent_context (preferred for profile access)
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="chrome",
                headless=False,
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/Los_Angeles",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-site-isolation-trials",
                ],
                ignore_default_args=["--enable-automation"],  # Remove automation flag
            )
            _add_stealth_script(context)
            if status_cb:
                status_cb("âœ“ Chrome launched with your profile (persistent context) - saved passwords available!")
            return context
        except Exception as e1:
            if status_cb:
                status_cb(f"Persistent context failed: {str(e1)[:100]}")
                status_cb("Trying alternative method with user-data-dir argument...")
            
            # Method 2: Regular launch with user-data-dir argument (alternative approach)
            browser = p.chromium.launch(
                channel="chrome",
                headless=False,
                args=[
                    f"--user-data-dir={user_data_dir}",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-site-isolation-trials",
                ],
                ignore_default_args=["--enable-automation"],
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/Los_Angeles",
            )
            _add_stealth_script(context)
            if status_cb:
                status_cb("âœ“ Chrome launched with your profile (user-data-dir) - saved passwords available!")
            return context
    except Exception as e:
        if status_cb:
            status_cb(f"Could not use Chrome profile: {str(e)[:100]}")
            status_cb("Will launch Chrome without profile...")
        return None

def _launch_chrome_with_profile(p, status_cb, url=None, field_to_selector=None, data=None):
    """Launch Chrome using the user's profile directory to access saved passwords"""
    user_data_dir = _get_chrome_user_data_dir()
    
    if user_data_dir:
        if status_cb:
            status_cb(f"Using your Chrome profile: {user_data_dir}")
        try:
            # Use launch_persistent_context to use the actual Chrome profile
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="chrome",
                headless=False,
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/Los_Angeles",
            )
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                window.chrome = { runtime: {} };
            """)
            if url and field_to_selector and data:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(url, wait_until="load")
                if status_cb:
                    status_cb("Filling form fields...")
                for field_name, selector in field_to_selector.items():
                    if selector and data.get(field_name):
                        try:
                            page.fill(selector, data[field_name])
                        except Exception:
                            pass
                if status_cb:
                    status_cb("Form filled. Please review and submit manually.")
            else:
                if status_cb:
                    status_cb("Chrome launched with your profile. You can now use saved passwords.")
            return context
        except Exception as e:
            if status_cb:
                status_cb(f"Could not use Chrome profile (Chrome may be running): {str(e)[:100]}")
                status_cb("Launching Chrome without profile...")
            # Fall through to regular launch
    else:
        if status_cb:
            status_cb("Chrome profile not found. Launching Chrome without saved passwords...")
    
    # Fallback: launch Chrome without profile
    browser = p.chromium.launch(headless=False, channel="chrome")
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        locale="en-US",
        timezone_id="America/Los_Angeles",
    )
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        window.chrome = { runtime: {} };
    """)
    if url and field_to_selector and data:
        page = context.new_page()
        page.goto(url, wait_until="load")
        if status_cb:
            status_cb("Filling form fields...")
        for field_name, selector in field_to_selector.items():
            if selector and data.get(field_name):
                try:
                    page.fill(selector, data[field_name])
                except Exception:
                    pass
        if status_cb:
            status_cb("Form filled. Please review and submit manually.")
    return context

def _fill_site_with_playwright(url: str, field_to_selector: Dict[str, str], data: Dict[str, str], status_cb=None, cdp_endpoint: Optional[str] = None) -> None:
    """
    Open Chromium and fill fields per provided CSS selectors.
    If cdp_endpoint is provided and reachable, attach to an existing Chrome via CDP.
    """
    if status_cb:
        status_cb("Starting browser...")
    with sync_playwright() as p:
        browser = None
        context = None
        if cdp_endpoint and _is_port_open("127.0.0.1", int(cdp_endpoint.rsplit(":", 1)[-1])):
            try:
                browser = p.chromium.connect_over_cdp(cdp_endpoint)
                # reuse an existing context if available; otherwise create one
                if browser.contexts:
                    context = browser.contexts[0]
                    # Add stealth script to existing context
                    try:
                        context.add_init_script("""
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => undefined
                            });
                            Object.defineProperty(navigator, 'plugins', {
                                get: () => [1, 2, 3, 4, 5]
                            });
                            Object.defineProperty(navigator, 'languages', {
                                get: () => ['en-US', 'en']
                            });
                            window.chrome = { runtime: {} };
                        """)
                    except:
                        pass  # If context already has pages, init script might fail
                else:
                    context = browser.new_context(
                        viewport={"width": 1280, "height": 720},
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        locale="en-US",
                        timezone_id="America/Los_Angeles",
                    )
                    context.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                        window.chrome = { runtime: {} };
                    """)
                if status_cb:
                    status_cb("Attached to existing Chrome via CDP.")
            except Exception:
                # fallback to launching - use system Chrome with your profile
                _launch_chrome_with_profile(p, status_cb)
                return  # _launch_chrome_with_profile handles everything
        else:
            # Use system Chrome with your profile (saved passwords and login sessions)
            _launch_chrome_with_profile(p, status_cb, url, field_to_selector, data)
            return  # _launch_chrome_with_profile handles everything
        page = context.new_page()
        page.goto(url, wait_until="load")
        if status_cb:
            status_cb("Page loaded. Filling fields...")
        for field, selector in field_to_selector.items():
            value = data.get(field, "")
            if not selector or not value:
                continue
            try:
                page.fill(selector, value, timeout=10000)
            except Exception as e:
                # Try click then type as fallback
                try:
                    page.click(selector, timeout=5000)
                    page.keyboard.type(value)
                except Exception as e2:
                    if status_cb:
                        status_cb(f"âš  Warning: Could not fill {field} field: {str(e2)}")
                    pass
        if status_cb:
            status_cb("Done. Leaving browser open for review.")
        # keep browser open for user; do not close immediately


def _run_mvr_automation(url: str, field_to_selector: Dict[str, str], data: Dict[str, str], 
                        account_id: str, user_id: str, password: str, 
                        status_cb=None, cdp_endpoint: Optional[str] = None, skip_login: bool = False,
                        login_selectors: Optional[Dict[str, str]] = None, auto_click_recaptcha: bool = True) -> None:
    """
    Run MVR automation: login to site, then fill MVR fields.
    """
    if status_cb:
        status_cb("Starting browser...")
    with sync_playwright() as p:
        # Launch a fresh Playwright Chromium browser (blue icon)
        if status_cb:
            status_cb("Launching Chromium browser...")
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
            ignore_default_args=["--enable-automation"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/Los_Angeles",
        )
        _add_stealth_script(context)
        
        # Close the auto-created about:blank page if it exists
        if context.pages:
            try:
                blank_page = context.pages[0]
                if blank_page.url == "about:blank" or "about:blank" in blank_page.url:
                    blank_page.close()
            except:
                pass
        
        # Create a new page and navigate
        page = context.new_page()
            if status_cb:
            status_cb(f"Navigating to: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        if status_cb:
            status_cb(f"✓ Navigated to: {page.url}")
        
        # No wait - start immediately
        
        # Bring browser to front (Windows) - after navigation so page is loaded
        try:
            import ctypes
            from ctypes import wintypes
            
            # Bring browser to front using Playwright's method
            page.bring_to_front()
        except Exception as e:
            # Fallback: use Playwright's bring_to_front
            try:
                page.bring_to_front()
            except Exception:
                pass
        
        # Initialize skip_login and login_successful variables
        skip_login = False
        login_successful = False
        
        # Fast check if already logged in BEFORE attempting login
        try:
            current_url = page.url
            if "NewOrderMasterPage.jsp" in current_url:
                if status_cb:
                    status_cb("✓ Already logged in and on MVR page - skipping login")
                skip_login = True
                login_successful = True
                # Skip directly to field filling - no need to navigate or wait
                # This will be handled in the login_successful block below
            except Exception:
                pass
        
        # Login - only if not skipping
        if not skip_login:
            if status_cb:
                status_cb("Filling login credentials...")
            
            import random
            
            # Build selector lists - use custom selectors first if provided, then fall back to defaults
            default_selectors = {
                "account_id": [
                    "input[name='accountId']", "input[name='account_id']", "input[name='accountId']",
                    "input[id*='account' i]", "input[id*='Account']",
                    "#accountId", "#account-id", "#account_id",
                    "input[placeholder*='account' i]", "input[placeholder*='Account' i]",
                    "input[type='text'][name*='account' i]", "input[type='text'][id*='account' i]",
                ],
                "user_id": [
                    "input[name='username']", "input[name='userId']", "input[name='user_id']",
                    "input[name='userName']", "input[name='user_name']", "input[name='user']",
                    "input[id*='user' i]", "input[id*='User']",
                    "#username", "#userId", "#user_id", "#userName", "#user",
                    "input[placeholder*='user' i]", "input[placeholder*='User' i]",
                    "input[type='text'][name*='user' i]", "input[type='text'][id*='user' i]",
                ],
                "password": [
                    "input[name='password']", "input[type='password']",
                    "input[id*='password' i]", "input[id*='Password']",
                    "#password", "#pass",
                    "input[placeholder*='password' i]", "input[placeholder*='Password' i]",
                ],
            }
            
            # Build final selector lists - custom first, then defaults
            login_selector_lists = {}
            for field_name in ["account_id", "user_id", "password"]:
                selector_list = []
                # Add custom selector first if provided
                if login_selectors and login_selectors.get(field_name):
                    custom_sel = login_selectors[field_name].strip()
                    if custom_sel:
                        selector_list.append(custom_sel)
                # Add default selectors
                selector_list.extend(default_selectors[field_name])
                login_selector_lists[field_name] = selector_list
            
            # Quick scan for fields (only if no custom selectors provided)
            if not (login_selectors and any(login_selectors.values())):
                if status_cb:
                    status_cb("Quick scan for login fields...")
                try:
                    # Quick check for password field
                    if page.locator("input[type='password']").count() > 0:
                        login_selector_lists["password"].insert(0, "input[type='password']")
                except:
                    pass
            
            login_data = {
                "account_id": account_id,
                "user_id": user_id,
                "password": password,
            }
            
            # Humanized field filling - sequential typing with delays and mouse movements
            import random
            filled_fields = {}
            
            def find_field(selector_list):
                """Find the first visible field from a list of selectors"""
                for selector in selector_list:
                    try:
                        locator = page.locator(selector).first
                        if locator.is_visible(timeout=500):
                            return locator
                    except:
                        continue
                return None
            
            def human_type(locator, text, field_name):
                """Type text with minimal delays for speed"""
                try:
                    # Click the field first
                    locator.click(timeout=2000)
                    
                    # Clear existing value
                    locator.press("Control+a", timeout=500)
                    
                    # Type with minimal delay for speed
                    locator.type(text, delay=10)  # Minimal delay for speed
                    return True
                except Exception:
                    return False
            
            # Fill Account ID
            if account_id:
                account_locator = find_field(login_selector_lists["account_id"])
                if not account_locator:
                    # Fallback: try first text input
                    try:
                        account_locator = page.locator("input[type='text'], input:not([type])").first
                        if account_locator.is_visible(timeout=500):
                            pass
                        else:
                            account_locator = None
                    except:
                        account_locator = None
                
                if account_locator:
                    if human_type(account_locator, account_id, "account_id"):
                        filled_fields["account_id"] = True
            
            # Fill User ID
            if user_id:
                user_locator = find_field(login_selector_lists["user_id"])
                if not user_locator:
                    # Fallback: try second text input
                    try:
                        user_locator = page.locator("input[type='text'], input:not([type])").nth(1)
                        if user_locator.is_visible(timeout=500):
                            pass
                        else:
                            user_locator = None
            except:
                        user_locator = None
                
                if user_locator:
                    if human_type(user_locator, user_id, "user_id"):
                        filled_fields["user_id"] = True
            
            # Fill Password
                    if password:
                password_locator = find_field(login_selector_lists["password"])
                if not password_locator:
                    # Fallback: try password input
                    try:
                        password_locator = page.locator("input[type='password']").first
                        if password_locator.is_visible(timeout=500):
                            pass
                        else:
                            password_locator = None
                    except:
                        password_locator = None
                
                if password_locator:
                    if human_type(password_locator, password, "password"):
                        filled_fields["password"] = True
            
            # Report which fields were filled
            if status_cb:
                filled_count = len(filled_fields)
                if filled_count == 3:
                    status_cb("âœ“ All login fields filled")
                elif filled_count > 0:
                    status_cb(f"âš  Filled {filled_count} of 3 fields")
                else:
                    status_cb("âœ— Could not fill login fields - check selectors")
            
            # Automatically click "I'm not a robot" checkbox (if enabled)
            checkbox_verified = False
            checkbox_clicked = False
            
            if auto_click_recaptcha:
            if status_cb:
                    status_cb("Clicking 'I'm not a robot' checkbox...")
            
            # Wait a moment for reCAPTCHA to load
                page.wait_for_timeout(500)
                
                # Try to find and click the reCAPTCHA checkbox
                try:
                    # Method 1: Find checkbox in reCAPTCHA iframe
                    recaptcha_frames = page.frames
                    for frame in recaptcha_frames:
                        try:
                            frame_url = frame.url
                            if 'recaptcha' in frame_url.lower() or 'google.com/recaptcha' in frame_url.lower():
                                # Try to click the checkbox
                                checkbox = frame.locator("#recaptcha-anchor, .recaptcha-checkbox")
                                if checkbox.count() > 0:
                                    checkbox.first.click(timeout=2000)
                                    checkbox_clicked = True
                                    if status_cb:
                                        status_cb("✓ Clicked reCAPTCHA checkbox")
                                    page.wait_for_timeout(random.randint(300, 600))  # Wait for verification
                                    break
                        except:
                            continue
                    
                    # Method 2: Try clicking via iframe selector
                    if not checkbox_clicked:
                        try:
                            recaptcha_iframe = page.locator("iframe[src*='recaptcha'], iframe[title*='recaptcha']").first
                            if recaptcha_iframe.is_visible(timeout=2000):
                                # Click the iframe area (which should trigger the checkbox)
                                box = recaptcha_iframe.bounding_box()
                                if box:
                                    # Click near the center of the iframe (where checkbox usually is)
                                    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                                    checkbox_clicked = True
                                    if status_cb:
                                        status_cb("✓ Clicked reCAPTCHA checkbox (via iframe)")
                                    page.wait_for_timeout(random.randint(300, 600))
                        except:
                            pass
                    
                    # Method 3: Try JavaScript click
                    if not checkbox_clicked:
                        try:
                            page.evaluate("""
                                (function() {
                                    var frames = document.querySelectorAll('iframe[src*="recaptcha"]');
                                    for (var i = 0; i < frames.length; i++) {
                                        try {
                                            var frameDoc = frames[i].contentDocument || frames[i].contentWindow.document;
                                            var checkbox = frameDoc.querySelector('#recaptcha-anchor, .recaptcha-checkbox');
                                            if (checkbox) {
                                                checkbox.click();
                                                return true;
                                            }
                                        } catch(e) {}
                                    }
                                    return false;
                                })();
                            """)
                            checkbox_clicked = True
                            if status_cb:
                                status_cb("✓ Clicked reCAPTCHA checkbox (via JS)")
                            page.wait_for_timeout(random.randint(300, 600))
                        except:
                            pass
                    
                    if not checkbox_clicked:
                        if status_cb:
                            status_cb("âš  Could not auto-click checkbox - please click manually")
                except:
                    pass
            else:
                if status_cb:
                    status_cb("Auto-click reCAPTCHA disabled - please click 'I'm not a robot' manually")
                # Still wait a moment for user to manually click
                page.wait_for_timeout(500)
            
            # Check if challenge popup appears (image selection prompt)
            has_challenge = False
            try:
                challenge_iframes = page.locator("iframe[src*='bframe'], iframe[title*='recaptcha challenge' i]")
                if challenge_iframes.count() > 0:
                    try:
                        if challenge_iframes.first.is_visible(timeout=1000):
                            has_challenge = True
                    except:
                        pass
            except:
                pass
            
            # If challenge popup appears, wait for user to complete it
            if has_challenge:
                if status_cb:
                    status_cb("reCAPTCHA challenge detected - please complete image selection...")
            
            # Wait for checkbox to be verified (checkmark appears)
            if not has_challenge:
                page.wait_for_timeout(1000)  # Brief wait for auto-verification
            
            # Check more frequently if challenge is present (user is actively working on it)
            if has_challenge:
                check_interval = 0.5  # Check every 0.5 seconds when challenge is active
                max_wait_time = 300  # 5 minutes
            else:
                check_interval = 1.0  # Check every 1 second if no challenge
                max_wait_time = 10  # Only wait 10 seconds if no challenge (should auto-verify quickly)
            
            elapsed = 0
            
            if status_cb:
                if has_challenge:
                    status_cb("Waiting for reCAPTCHA verification (checkmark)...")
                else:
                    status_cb("Checking for reCAPTCHA checkmark...")
            
            while elapsed < max_wait_time and not checkbox_verified:
                page.wait_for_timeout(int(check_interval * 1000))
                elapsed += check_interval
                
                # Check if checkbox has checkmark (is verified)
                try:
                    # Method 1: Check reCAPTCHA checkbox in iframes for checkmark
                    recaptcha_frames = page.frames
                    for frame in recaptcha_frames:
                        try:
                            frame_url = frame.url
                            if 'recaptcha' in frame_url.lower() or 'google.com/recaptcha' in frame_url.lower():
                                # Check if checkbox has checkmark (verified state)
                                checked = frame.evaluate("""
                                    (function() {
                                        var cb = document.querySelector('#recaptcha-anchor');
                                        if (cb) {
                                            var ariaChecked = cb.getAttribute('aria-checked');
                                            var hasCheckedClass = cb.classList.contains('recaptcha-checkbox-checked');
                                            // Also check for checkmark icon
                                            var hasCheckmark = cb.querySelector('.recaptcha-checkbox-checkmark') !== null;
                                            return ariaChecked === 'true' || hasCheckedClass || hasCheckmark;
                                        }
                                        return false;
                                    })();
                                """)
                                if checked:
                                    checkbox_verified = True
                                    if status_cb:
                                        status_cb("âœ“ Checkmark detected! Clicking login button...")
                                    break
                        except:
                            continue
                    
                    # Method 2: Check for reCAPTCHA response token (most reliable)
                    if not checkbox_verified:
                        try:
                            token_result = page.evaluate("""
                                (function() {
                                    // Check for reCAPTCHA response token in textarea
                                    var textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                                    var hasTextareaToken = textarea && textarea.value && textarea.value.length > 0;
                                    
                                    // Check grecaptcha API
                                    var hasApiToken = false;
                                    if (typeof grecaptcha !== 'undefined') {
                                        try {
                                            var response = grecaptcha.getResponse();
                                            hasApiToken = response && response.length > 0;
                                        } catch(e) {}
                                    }
                                    
                                    return {
                                        verified: hasTextareaToken || hasApiToken,
                                        textareaToken: hasTextareaToken,
                                        apiToken: hasApiToken,
                                        tokenLength: textarea ? (textarea.value ? textarea.value.length : 0) : 0
                                    };
                                })();
                            """)
                            if token_result and token_result.get('verified'):
                                checkbox_verified = True
                                if status_cb:
                                    status_cb(f"âœ“ reCAPTCHA verified! Token length: {token_result.get('tokenLength', 0)}")
                        except:
                            pass
                    
                    if checkbox_verified:
                        break
                except:
                    pass
                
                # Also check if we've navigated away (login succeeded)
                try:
                    current_url = page.url
                    if url not in current_url:
                        checkbox_verified = True
                        if status_cb:
                            status_cb("Login detected, continuing...")
                        break
                except Exception:
                    pass
            
            # Always wait for checkmark before clicking login (both scenarios)
            # Scenario 1: No challenge - wait for auto-verification checkmark, then auto-click login
            # Scenario 2: Challenge appears - wait for user to complete and checkmark appears
            if not checkbox_verified:
                if status_cb:
                    status_cb("âš  Timeout waiting for checkmark - you may need to verify manually")
            
            # Initialize login_clicked variable (used later in the code)
            login_clicked = False
            
            # If no challenge appeared and checkbox is verified, automatically click login
            if checkbox_verified and not has_challenge:
                if status_cb:
                    status_cb("âœ“ No challenge detected - automatically clicking login button...")
                # Small delay before clicking (human behavior)
                page.wait_for_timeout(random.randint(200, 400))
                # Click login button automatically
                submit_selectors = [
                    "form[name='LoginMain'] button:has-text('LOGIN')",
                    "form[name='LoginMain'] button:has-text('Login')",
                    "form[name='LoginMain'] button[type='submit']",
                    "button:has-text('LOGIN')",
                    "button:has-text('LOG IN')",
                    "button[id*='login' i]",
                    "input[type='submit'][value*='LOGIN' i]",
                    "input[type='submit'][value*='Login' i]",
                ]
                
                for selector in submit_selectors:
                    try:
                        login_btn = page.locator(selector).first
                        if login_btn.is_visible(timeout=1000):
                            login_btn.click(timeout=2000)
                            login_clicked = True
                            if status_cb:
                                status_cb("✓ Login button clicked automatically")
                            break
                    except:
                        continue
                
                if not login_clicked:
                    if status_cb:
                        status_cb("⚠ Could not find login button - please click manually")
            
            # Only click login button if checkbox is verified (has checkmark) AND challenge appeared
            if checkbox_verified and has_challenge:
                if status_cb:
                    status_cb("âœ“ Checkmark detected! Waiting for reCAPTCHA to fully process...")
                
                # Wait for reCAPTCHA to fully process and any overlays/popups to clear
                # This is critical - reCAPTCHA can block clicks if not fully cleared
                max_wait_attempts = 10
                for attempt in range(max_wait_attempts):
                    page.wait_for_timeout(500)  # Check every 500ms
                    
                    # Check if reCAPTCHA challenge popup is still visible
                    challenge_still_visible = False
                    try:
                        # Check for challenge iframes
                        challenge_iframes = page.locator("iframe[title*='recaptcha challenge'], iframe[src*='bframe'], iframe[title*='recaptcha expires']")
                        if challenge_iframes.count() > 0:
                            for i in range(challenge_iframes.count()):
                                iframe = challenge_iframes.nth(i)
                                try:
                                    if iframe.is_visible(timeout=300):
                                        # Check if iframe is actually visible on screen (not hidden)
                                        box = iframe.bounding_box()
                                        if box and box['width'] > 0 and box['height'] > 0:
                                            # Check if it's positioned off-screen (hidden)
                                            if box['x'] > -10000 or box['y'] > -10000:
                                                continue  # It's hidden, skip
                                            challenge_still_visible = True
                                            break
                                except:
                                    pass
                        
                        # Also check for reCAPTCHA overlay divs
                        if not challenge_still_visible:
                            overlay_divs = page.locator("div[style*='z-index'][style*='2000000000'], div.g-recaptcha-bubble-arrow")
                            if overlay_divs.count() > 0:
                                for i in range(overlay_divs.count()):
                                    div = overlay_divs.nth(i)
                                    try:
                                        if div.is_visible(timeout=300):
                                            box = div.bounding_box()
                                            if box and box['width'] > 0 and box['height'] > 0:
                                                # Check opacity and visibility
                                                style = div.evaluate("el => window.getComputedStyle(el).opacity + '|' + window.getComputedStyle(el).visibility")
                                                if style and '0' not in style.split('|')[0] and 'hidden' not in style:
                                                    challenge_still_visible = True
                                                    break
                                    except:
                                        pass
                    except:
                        pass
                    
                    if not challenge_still_visible:
                        if status_cb and attempt > 0:
                            status_cb("reCAPTCHA cleared, proceeding to click login...")
                        break
                    elif attempt < max_wait_attempts - 1:
                        if status_cb:
                            status_cb(f"Waiting for reCAPTCHA to clear... ({attempt + 1}/{max_wait_attempts})")
                
                # Final wait to ensure everything is settled
                page.wait_for_timeout(1000)
                
                # CRITICAL: Verify reCAPTCHA token is actually present before clicking login
                if status_cb:
                    status_cb("Verifying reCAPTCHA token before login...")
                
                token_verified = False
                for verify_attempt in range(5):
                    try:
                        token_check = page.evaluate("""
                            (function() {
                                // Check textarea token
                                var textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                                var hasTextareaToken = textarea && textarea.value && textarea.value.length > 20; // Token should be at least 20 chars
                                
                                // Check grecaptcha API
                                var hasApiToken = false;
                                if (typeof grecaptcha !== 'undefined') {
                                    try {
                                        var response = grecaptcha.getResponse();
                                        hasApiToken = response && response.length > 20;
                                    } catch(e) {}
                                }
                                
                                return {
                                    verified: hasTextareaToken || hasApiToken,
                                    textareaToken: hasTextareaToken,
                                    apiToken: hasApiToken,
                                    tokenValue: textarea ? (textarea.value || '') : ''
                                };
                            })();
                        """)
                        
                        if token_check and token_check.get('verified'):
                            token_verified = True
                            if status_cb:
                                token_info = []
                                if token_check.get('textareaToken'):
                                    token_info.append("textarea token present")
                                if token_check.get('apiToken'):
                                    token_info.append("API token present")
                                status_cb(f"âœ“ reCAPTCHA token verified: {', '.join(token_info)}")
                            break
                        else:
                            if status_cb and verify_attempt < 4:
                                status_cb(f"Waiting for reCAPTCHA token... ({verify_attempt + 1}/5)")
                            page.wait_for_timeout(1000)
                    except:
                        page.wait_for_timeout(1000)
                
                if not token_verified:
                    if status_cb:
                        status_cb("âš  WARNING: reCAPTCHA token not verified!")
                        status_cb("Waiting additional 3 seconds for token...")
                    page.wait_for_timeout(3000)
                    # Check one more time
                    try:
                        final_check = page.evaluate("""
                            (function() {
                                var textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                                return textarea && textarea.value && textarea.value.length > 20;
                            })();
                        """)
                        if final_check:
                            token_verified = True
                            if status_cb:
                                status_cb("âœ“ reCAPTCHA token found on final check")
                    except:
                        pass
                
                # If token still not verified, ask user to click login manually
                if not token_verified:
                    if status_cb:
                        status_cb("âš  reCAPTCHA token not found - please click LOGIN button manually")
                        status_cb("Waiting for you to click LOGIN button in the browser...")
                        status_cb("The tool will continue automatically once you've logged in.")
                    
                    # Wait for user to click login manually - monitor for URL change
                    if status_cb:
                        status_cb("Monitoring for login completion...")
                    
                    login_url_base = url.split('?')[0].split('#')[0]
                    max_manual_wait = 120  # Wait up to 2 minutes for manual login
                    check_count = 0
                    manual_login_detected = False
                    
                    while check_count < max_manual_wait and not manual_login_detected:
                        page.wait_for_timeout(2000)  # Check every 2 seconds
                        check_count += 2
                        
                        try:
                            current_url = page.url
                            # If we've navigated away from login URL, login succeeded
                            if login_url_base not in current_url and url not in current_url:
                                manual_login_detected = True
                                if status_cb:
                                    status_cb("âœ“ Manual login detected! Continuing...")
                                break
                        except Exception:
                            pass
                    
                    if manual_login_detected:
                        # User manually logged in - set flags to proceed
                        login_clicked = True
                        checkbox_verified = True  # Assume verified since user completed it
                        if status_cb:
                            status_cb("âœ“ Manual login completed - proceeding to fill MVR fields...")
                    else:
                        if status_cb:
                            status_cb("âš  Timeout waiting for manual login - proceeding anyway...")
                        # Still set flags to proceed (user might have logged in)
                        login_clicked = True
                        checkbox_verified = True
                else:
                    if status_cb:
                        status_cb("Clicking login button automatically...")
                
                # Define submit_selectors outside the if block so it's always available
                submit_selectors = [
                    # Try form-specific selectors first (LoginMain form)
                    "form[name='LoginMain'] button:has-text('LOGIN')",
                    "form[name='LoginMain'] button:has-text('Login')",
                    "form[name='LoginMain'] input[value='LOGIN']",
                    "form[name='LoginMain'] input[value='Login']",
                    "form[name='LoginMain'] button[type='submit']",
                    "form[name='LoginMain'] input[type='submit']",
                    "form[name='LoginMain'] button",
                    "form[name='LoginMain'] input[type='button']",
                    # Try exact "LOGIN" text first (all caps)
                    "button:has-text('LOGIN')",
                    "button:has-text('LOG IN')",
                    "button:has-text('SIGN IN')",
                    # Try case-insensitive
                    "button:has-text('Login')",
                    "button:has-text('Sign In')",
                    "button:has-text('Log In')",
                    # Try by type
                    "button[type='submit']",
                    "input[type='submit']",
                    # Try by ID/class
                    "#login-button",
                    "#submit",
                    "#login",
                    "button[id*='login' i]",
                    "button[id*='submit' i]",
                    "button[class*='login' i]",
                    "button[class*='submit' i]",
                    "input[value*='Login' i]",
                    "input[value*='LOGIN' i]",
                    "input[value*='LOGIN']",
                    "input[value*='Sign In' i]",
                ]
                
                login_clicked = False
                login_button_found = False
                
                # Only try to auto-click if token was verified
                if token_verified:
                    # Debug: List all buttons on page to help identify login button
                    try:
                        all_buttons = page.evaluate("""
                            (function() {
                                var buttons = document.querySelectorAll('button, input[type="submit"], input[type="button"]');
                                var result = [];
                                for (var i = 0; i < buttons.length; i++) {
                                    var btn = buttons[i];
                                    if (btn.offsetParent !== null) {
                                        var rect = btn.getBoundingClientRect();
                                        result.push({
                                            text: (btn.textContent || btn.innerText || btn.value || '').trim(),
                                            id: btn.id || '',
                                            className: btn.className || '',
                                            type: btn.type || '',
                                            tagName: btn.tagName || '',
                                            x: Math.round(rect.left),
                                            y: Math.round(rect.top)
                                        });
                                    }
                                }
                                return result;
                            })();
                        """)
                        if status_cb and all_buttons:
                            # Show all buttons with their details
                            for btn in all_buttons:
                                btn_str = f"Text:'{btn['text']}' ID:'{btn['id']}' Class:'{btn['className'][:30]}'"
                                status_cb(f"Button: {btn_str}")
                    except Exception as e:
                        if status_cb:
                            status_cb(f"Debug error: {str(e)[:50]}")
                    
                    # Try Playwright selectors first
                    for selector in submit_selectors:
                        try:
                            login_btn = page.locator(selector).first
                            if login_btn.is_visible(timeout=2000):
                                # Check if button is enabled (not disabled)
                                is_enabled = True
                                try:
                                    is_enabled = login_btn.is_enabled(timeout=500)
                                except:
                                    pass
                                
                                if not is_enabled:
                                    if status_cb:
                                        status_cb(f"Login button found but disabled - waiting...")
                                    # Wait a bit more for button to become enabled
                                    page.wait_for_timeout(2000)
                                    # Check again
                                    try:
                                        is_enabled = login_btn.is_enabled(timeout=500)
                                    except:
                                        pass
                                
                                login_button_found = True
                                if status_cb:
                                    status_cb(f"Found login button: {selector} (enabled: {is_enabled})")
                                try:
                                    # Get button text for confirmation
                                    btn_text = login_btn.text_content()
                                    if status_cb:
                                        status_cb(f"Button text: '{btn_text}'")
                                    
                                    # Scroll into view and focus before clicking
                                    login_btn.scroll_into_view_if_needed()
                                    page.wait_for_timeout(200)
                                    
                                    # Check if button is covered by reCAPTCHA or another element
                                    try:
                                        # Get button's bounding box
                                        box = login_btn.bounding_box()
                                        if box:
                                            # Check if element at that position is the button or something else
                                            element_at_point = page.evaluate(f"""
                                                (function() {{
                                                    var x = {box['x'] + box['width']/2};
                                                    var y = {box['y'] + box['height']/2};
                                                    var elem = document.elementFromPoint(x, y);
                                                    if (elem) {{
                                                        var tag = elem.tagName;
                                                        var id = elem.id ? '#' + elem.id : '';
                                                        var cls = elem.className ? '.' + elem.className.split(' ')[0] : '';
                                                        var zIndex = window.getComputedStyle(elem).zIndex;
                                                        // Check if it's a reCAPTCHA overlay
                                                        var isRecaptcha = tag === 'IFRAME' && (elem.src.indexOf('recaptcha') !== -1 || elem.src.indexOf('bframe') !== -1);
                                                        var isOverlay = zIndex && parseInt(zIndex) > 1000000;
                                                        return tag + id + cls + (isRecaptcha ? ' [RECAPTCHA]' : '') + (isOverlay ? ' [HIGH-Z-INDEX:' + zIndex + ']' : '');
                                                    }}
                                                    return null;
                                                }})();
                                            """)
                                            if status_cb and element_at_point:
                                                if 'RECAPTCHA' in element_at_point or 'HIGH-Z-INDEX' in element_at_point:
                                                    status_cb(f"âš  Button may be blocked by: {element_at_point}")
                                                    # Try to hide reCAPTCHA overlays
                                                    try:
                                                        page.evaluate("""
                                                            (function() {
                                                                // Hide reCAPTCHA overlays that might be blocking
                                                                var overlays = document.querySelectorAll('div[style*="z-index"][style*="2000000000"], div.g-recaptcha-bubble-arrow');
                                                                for (var i = 0; i < overlays.length; i++) {
                                                                    var style = window.getComputedStyle(overlays[i]);
                                                                    if (style.opacity !== '0' && style.visibility !== 'hidden') {
                                                                        overlays[i].style.display = 'none';
                                                                    }
                                                                }
                                                            })();
                                                        """)
                                                        page.wait_for_timeout(500)
                                                        if status_cb:
                                                            status_cb("Attempted to hide reCAPTCHA overlays")
                                                    except:
                                                        pass
                                                else:
                                                    status_cb(f"Element at button position: {element_at_point}")
                                    except:
                                        pass
                                    
                                    login_btn.focus()
                                    page.wait_for_timeout(200)
                                    
                                    # Try multiple click methods
                                    try:
                                        if is_enabled:
                                            login_btn.click(timeout=2000)
                                        else:
                                            # Try force click if disabled
                                            login_btn.click(force=True, timeout=2000)
                                    except:
                                        # Try force click as fallback
                                        login_btn.click(force=True, timeout=2000)
                                    
                                    login_clicked = True
                                    if status_cb:
                                        status_cb("âœ“ Clicked login button (Playwright)")
                                    # Wait to ensure click registered
                                    page.wait_for_timeout(1000)
                                    break
                                except Exception as e:
                                    if status_cb:
                                        status_cb(f"Playwright click failed: {str(e)[:80]}")
                                    continue
                        except Exception as e:
                            if status_cb:
                                status_cb(f"Selector '{selector}' failed: {str(e)[:50]}")
                            continue
                
                # Fallback: Use JavaScript to find and click login button
                if not login_clicked:
                    try:
                        if status_cb:
                            status_cb("Trying JavaScript method to click login button...")
                        js_login = """
                        (function() {
                            // First, try to find button in LoginMain form
                            try {
                                var form = document.querySelector('form[name="LoginMain"]');
                                if (form) {
                                    var formButtons = form.querySelectorAll('button, input[type="submit"], input[type="button"]');
                                    for (var i = 0; i < formButtons.length; i++) {
                                        var btn = formButtons[i];
                                        if (btn.offsetParent === null) continue;
                                        var text = (btn.textContent || btn.innerText || btn.value || '').trim();
                                        if (text === 'LOGIN' || text === 'Login' || text.toUpperCase() === 'LOGIN') {
                                            console.log('Found LOGIN button in LoginMain form, clicking...');
                                            btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                                            setTimeout(function() {
                                                btn.focus();
                                                btn.click();
                                                // Also try dispatchEvent as backup
                                                var clickEvent = new MouseEvent('click', {
                                                    bubbles: true,
                                                    cancelable: true,
                                                    view: window
                                                });
                                                btn.dispatchEvent(clickEvent);
                                            }, 200);
                                            return true;
                                        }
                                    }
                                    // If no button found with LOGIN text, try first submit button in form
                                    for (var i = 0; i < formButtons.length; i++) {
                                        var btn = formButtons[i];
                                        if (btn.offsetParent !== null && (btn.type === 'submit' || btn.tagName === 'BUTTON')) {
                                            console.log('Found submit button in LoginMain form, clicking...');
                                            btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                                            setTimeout(function() {
                                                btn.focus();
                                                btn.click();
                                            }, 200);
                                            return true;
                                        }
                                    }
                                }
                            } catch(e) {
                                console.log('LoginMain form error:', e);
                            }
                            
                            // Fallback: try to find button with exact "LOGIN" text (all caps) anywhere on page
                            var buttons = document.querySelectorAll('button, input[type="submit"], input[type="button"]');
                            for (var i = 0; i < buttons.length; i++) {
                                var btn = buttons[i];
                                if (btn.offsetParent === null) continue;
                                var text = (btn.textContent || btn.innerText || btn.value || '').trim();
                                // Check for exact "LOGIN" match first (case-sensitive)
                                if (text === 'LOGIN' || text === 'LOG IN' || text.toUpperCase() === 'LOGIN') {
                                    console.log('Found LOGIN button, clicking...');
                                    btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                                    setTimeout(function() {
                                        btn.focus();
                                        btn.click();
                                        // Also try dispatchEvent as backup
                                        var clickEvent = new MouseEvent('click', {
                                            bubbles: true,
                                            cancelable: true,
                                            view: window
                                        });
                                        btn.dispatchEvent(clickEvent);
                                    }, 200);
                                    return true;
                                }
                            }
                            
                            // Try querySelector with valid CSS selectors
                            var selectors = [
                                'button[type="submit"]',
                                'input[type="submit"]',
                                '#login-button',
                                '#submit',
                                '#login',
                                'button[id*="login" i]',
                                'button[id*="submit" i]',
                                'button[class*="login" i]',
                                'button[class*="submit" i]'
                            ];
                            
                            for (var i = 0; i < selectors.length; i++) {
                                try {
                                    var btn = document.querySelector(selectors[i]);
                                    if (btn && btn.offsetParent !== null) {
                                        btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                                        btn.focus();
                                        setTimeout(function() { btn.click(); }, 100);
                                        return true;
                                    }
                                } catch(e) {}
                            }
                            
                            // Try finding by text content (case-insensitive)
                            buttons = document.querySelectorAll('button, input[type="submit"]');
                            for (var i = 0; i < buttons.length; i++) {
                                var btn = buttons[i];
                                if (btn.offsetParent === null) continue;
                                var text = (btn.textContent || btn.innerText || btn.value || '').toLowerCase();
                                if (text.indexOf('login') !== -1 || text.indexOf('sign in') !== -1 || text.indexOf('log in') !== -1) {
                                    btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                                    btn.focus();
                                    setTimeout(function() { btn.click(); }, 100);
                                    return true;
                                }
                            }
                            
                            // Try to find button to the right of reCAPTCHA (position-based)
                            try {
                                var recaptcha = document.querySelector('iframe[src*="recaptcha"], div[class*="recaptcha"]');
                                if (recaptcha) {
                                    var recaptchaRect = recaptcha.getBoundingClientRect();
                                    buttons = document.querySelectorAll('button, input[type="submit"]');
                                    for (var i = 0; i < buttons.length; i++) {
                                        var btn = buttons[i];
                                        if (btn.offsetParent === null) continue;
                                        var btnRect = btn.getBoundingClientRect();
                                        // Check if button is to the right of reCAPTCHA (within reasonable distance)
                                        if (btnRect.left > recaptchaRect.right && 
                                            Math.abs(btnRect.top - recaptchaRect.top) < 100) {
                                            btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                                            btn.focus();
                                            setTimeout(function() { btn.click(); }, 100);
                                            return true;
                                        }
                                    }
                                }
                            } catch(e) {}
                            
                            // Last resort: click first visible submit button
                            var submit = document.querySelector('button[type="submit"], input[type="submit"]');
                            if (submit && submit.offsetParent !== null) {
                                submit.scrollIntoView({behavior: 'smooth', block: 'center'});
                                submit.focus();
                                setTimeout(function() { submit.click(); }, 100);
                                return true;
                            }
                            
                            return false;
                        })();
                        """
                        result = page.evaluate(js_login)
                        if result:
                            login_clicked = True
                            if status_cb:
                                status_cb("âœ“ Clicked login button (JavaScript)")
                            # Wait to ensure click registered
                            page.wait_for_timeout(700)  # Wait for setTimeout(100) + processing
                        else:
                            if status_cb:
                                status_cb("âš  JavaScript could not find login button")
                    except Exception as e:
                        if status_cb:
                            status_cb(f"Login button JS error: {str(e)[:50]}")
                
                # If still not clicked and token was verified, try submitting the form directly
                if not login_clicked and token_verified:
                    try:
                        # Try to find and submit the LoginMain form directly
                        login_form = page.locator("form[name='LoginMain']").first
                        if login_form.is_visible(timeout=2000):
                            if status_cb:
                                status_cb("Found LoginMain form, trying to submit...")
                            # Try to find submit button in form
                            submit_btn = login_form.locator("button[type='submit'], input[type='submit'], button:has-text('LOGIN'), button:has-text('Login')").first
                            if submit_btn.is_visible(timeout=2000):
                                submit_btn.click(timeout=2000)
                                login_clicked = True
                                if status_cb:
                                    status_cb("âœ“ Clicked submit button in LoginMain form")
                            else:
                                # Submit form directly using JavaScript
                                try:
                                    login_form.evaluate("form => form.submit()")
                                    login_clicked = True
                                    if status_cb:
                                        status_cb("âœ“ Submitted LoginMain form directly")
                                except:
                                    # Try alternative form submission
                                    page.evaluate("""
                                        (function() {
                                            var form = document.querySelector('form[name="LoginMain"]');
                                            if (form) {
                                                form.submit();
                                                return true;
                                            }
                                            return false;
                                        })();
                                    """)
                                    login_clicked = True
                                    if status_cb:
                                        status_cb("âœ“ Submitted LoginMain form (alternative method)")
                    except Exception as e:
                        if status_cb:
                            status_cb(f"Form submit attempt: {str(e)[:50]}")
                
                if not login_clicked:
                    if status_cb:
                        if not login_button_found:
                            status_cb("âš  Could not find login button - please click it manually")
                        else:
                            status_cb("âš  Login button found but click failed - please click it manually")
            else:
                if status_cb:
                    status_cb("âš  Waiting for reCAPTCHA checkmark before clicking login...")
            
            # Wait for login to complete (only if we clicked login or user manually logged in)
            login_successful = False
            if checkbox_verified and login_clicked:
                if status_cb:
                    status_cb("Waiting for login to complete...")
                
                # IMMEDIATE check first (no wait) - login might be instant
                try:
                    current_url = page.url
                    if "NewOrderMasterPage.jsp" in current_url:
                        login_successful = True
                        if status_cb:
                            status_cb("✓ Login successful! (instant)")
                    else:
                        # Not ready yet - check frequently with minimal delay
                login_url_base = url.split('?')[0].split('#')[0]
                        max_login_wait = 10  # Reduced to 10 seconds
                check_count = 0
                        check_interval = 100  # Check every 100ms for faster detection (was 200ms)
                
                        while check_count < (max_login_wait * 10) and not login_successful:  # 10 seconds * 10 = 100 checks
                            page.wait_for_timeout(check_interval)
                    check_count += 1
                    
                    try:
                        current_url = page.url
                        # If we've navigated away from login URL, login succeeded
                        # Also check if we're on the MVR input page
                                if "NewOrderMasterPage.jsp" in current_url:
                                    login_successful = True
                                    if status_cb:
                                        status_cb("✓ Login successful!")
                                    break
                                elif login_url_base not in current_url and url not in current_url:
                            login_successful = True
                            if status_cb:
                                status_cb("✓ Login successful!")
                            break
                    except Exception:
                        pass
                            if login_successful:
                                break
                except:
                    pass
                if not login_successful:
                    # Check one more time if we're on the MVR page
                    try:
                        current_url = page.url
                        if "NewOrderMasterPage.jsp" in current_url:
                            login_successful = True
                            if status_cb:
                                status_cb("âœ“ Already on MVR page - login successful!")
                        else:
                            if status_cb:
                                status_cb("âš  Login may not have completed - proceeding anyway...")
                            login_successful = True  # Proceed anyway
                    except:
                        if status_cb:
                            status_cb("âš  Login may not have completed - proceeding anyway...")
                        login_successful = True  # Proceed anyway
            elif checkbox_verified and not login_clicked:
                # Checkmark detected but login button wasn't clicked - wait for manual login
                if status_cb:
                    status_cb("âš  Waiting for manual login...")
                # Check frequently for manual login (every 500ms for 10 seconds)
                login_url_base = url.split('?')[0].split('#')[0]
                for _ in range(20):  # 20 checks * 500ms = 10 seconds
                    page.wait_for_timeout(500)
                try:
                    current_url = page.url
                        if "NewOrderMasterPage.jsp" in current_url:
                        login_successful = True
                        if status_cb:
                            status_cb("✓ Manual login detected!")
                            break
                        elif login_url_base not in current_url and url not in current_url:
                            login_successful = True
                        if status_cb:
                                status_cb("✓ Manual login detected!")
                            break
                except:
                        pass
                    if login_successful:
                        break
                
                if not login_successful:
                    login_successful = True  # Proceed anyway
            if status_cb:
                        status_cb("âš  Proceeding - please ensure you're logged in")
            else:
                # No checkmark - but if user manually logged in, proceed anyway
                # Check if we're already on a different page (user might have logged in manually)
                try:
                    current_url = page.url
                    if "NewOrderMasterPage.jsp" in current_url:
                        login_successful = True
                        if status_cb:
                            status_cb("âœ“ Already on MVR page - proceeding...")
                    else:
                        login_successful = False
                        if status_cb:
                            status_cb("âš  Cannot proceed - reCAPTCHA not verified")
                except:
                    login_successful = False
                    if status_cb:
                        status_cb("âš  Cannot proceed - reCAPTCHA not verified")
        else:
            # If skipping login, just navigate to the URL (should already be logged in)
            if status_cb:
                status_cb("Already logged in, navigating...")
            login_successful = True
        
        # Only fill MVR fields after successful login
        if login_successful:
            # Get the state selector immediately (no delay)
            state_selector = field_to_selector.get("state", "#ddComboState")
            if not state_selector:
                state_selector = "#ddComboState"  # Fallback to default
            
            # IMMEDIATE check: Try to detect if page is already ready (fastest path)
            page_ready = False
            try:
                # Instant check - if state dropdown already exists, we're ready NOW
                state_element = page.locator(state_selector).first
                if state_element.count() > 0:
                    page_ready = True
            if status_cb:
                        status_cb("Page ready (instant) - starting immediately")
            except Exception:
                pass
            
            # Only navigate if not ready AND not on the right page
            if not page_ready:
                try:
            current_url = page.url
            mvr_page_url = "https://www.webmvr.com/neworder/NewOrderMasterPage.jsp?Id=new"
            
            # Check if we're already on the MVR input page
            if "NewOrderMasterPage.jsp" not in current_url:
                if status_cb:
                            status_cb(f"Navigating to MVR page...")
                try:
                    # Use "commit" for fastest navigation - don't wait for DOM
                            # We'll check readiness immediately after
                    page.goto(mvr_page_url, wait_until="commit", timeout=30000)
                except Exception as nav_err:
                    if status_cb:
                        status_cb(f"⚠ Navigation error: {str(nav_err)[:80]}")
            
                    # IMMEDIATE readiness check after navigation (or if already on page)
                    # Check multiple times quickly instead of one long wait
                    for quick_check in range(10):  # 10 quick checks
                        try:
                            state_element = page.locator(state_selector).first
                            if state_element.count() > 0:
                                page_ready = True
            if status_cb:
                                    status_cb("Page ready - starting immediately")
                                break
                        except Exception:
                            pass
                        
                        if not page_ready:
                            # Very short wait between checks (50ms)
                            page.wait_for_timeout(50)
                    
                    # If still not ready, do one final wait with timeout
                    if not page_ready:
                        try:
                            page.wait_for_selector(state_selector, state="attached", timeout=2000)
                            page_ready = True
                if status_cb:
                                status_cb("Page ready")
                        except Exception:
                            # Last resort: check for any form field
                            try:
                                page.wait_for_selector("select, input", state="attached", timeout=1000)
                if status_cb:
                                    status_cb("Page ready (fallback)")
                            except Exception:
                                if status_cb:
                                    status_cb("⚠ Proceeding - page may still be loading")
                except Exception:
                    # If navigation/readiness check fails, proceed anyway
                    if status_cb:
                        status_cb("⚠ Navigation/readiness check failed - proceeding")
            
            # Helper function to fill searchable dropdown (click, type, select)
            def fill_dropdown(field_name: str, selector: str, value: str) -> bool:
                """Fill a dropdown - tries select_option() first for standard selects, then searchable dropdowns"""
                if not selector or not value:
                    return False
                
                value_upper = value.upper().strip()
                
                try:
                    # Wait for dropdown to be ready
                    dropdown_locator = page.locator(selector)
                    # Check if element exists first
                    element_count = dropdown_locator.count()
                    if element_count == 0:
                    if status_cb:
                            status_cb(f"⚠ {field_name} dropdown not found with selector: {selector}")
                        return False
                    
                    dropdown_locator.wait_for(state="attached", timeout=5000)
                    
                    if status_cb:
                        status_cb(f"Filling {field_name}: {value_upper}...")
                    
                    # FIRST: Try Playwright's select_option() for standard <select> elements
                    # This is the most reliable method for standard HTML selects (like OrderTypeCombo, ProductTypeCombo)
                    try:
                        # Try selecting by exact value first
                        dropdown_locator.select_option(value=value_upper, timeout=2000)
                        page.wait_for_timeout(100)  # Minimal wait
                        # Verify selection by checking the actual selected value
                        try:
                            selected_value = dropdown_locator.evaluate("el => el.value", timeout=500)
                            if value_upper == selected_value.upper():
                                if status_cb:
                                    status_cb(f"✓ {field_name}: {value_upper} (select_option)")
                                return True
                        except:
                            # If verification fails but no exception, assume success
                            if status_cb:
                                status_cb(f"✓ {field_name}: {value_upper} (select_option)")
                            return True
                    except Exception:
                        # select_option() by value failed, try selecting by label/text
                        try:
                            dropdown_locator.select_option(label=value_upper, timeout=2000)
                            page.wait_for_timeout(100)  # Minimal wait
                            if status_cb:
                                status_cb(f"✓ {field_name}: {value_upper} (select_option by label)")
                            return True
                        except Exception:
                            # select_option() didn't work, fall back to searchable dropdown method
                            pass
                    
                    # FALLBACK: Handle as searchable dropdown (click, type, select)
                    # Step 1: Click the dropdown to open it
                    dropdown_locator.click(timeout=3000)
                    page.wait_for_timeout(100)  # Minimal wait for dropdown to open
                    
                    # Step 2: Find the input/search field inside the dropdown and type into it
                    # Many dropdowns have a separate input field for filtering
                    input_found = False
                    input_selectors = [
                        f"{selector} input",
                        f"{selector} input[type='text']",
                        f"{selector} input[type='search']",
                        "input[role='combobox']",
                        "input[aria-autocomplete='list']",
                        ".dropdown-input",
                        ".select-input",
                        "input:focus",  # The currently focused input
                    ]
                    
                    input_locator = None
                    for input_sel in input_selectors:
                        try:
                            input_locator = page.locator(input_sel).first
                            if input_locator.is_visible(timeout=500):
                                input_found = True
                                break
                        except Exception:
                    continue
                
                    # If no separate input found, use the dropdown itself
                    if not input_found:
                        input_locator = dropdown_locator
                        dropdown_locator.focus(timeout=1000)
                    
                    # Clear any existing value first
                    try:
                        input_locator.press("Control+a", timeout=500)  # Select all
                        input_locator.press("Delete", timeout=500)  # Delete
                    except Exception:
                        try:
                            input_locator.clear(timeout=500)
                        except Exception:
                            pass
                    
                    # Type the abbreviation with minimal delay
                    input_locator.focus(timeout=1000)
                    page.keyboard.type(value_upper, delay=20)  # Reduced delay for speed
                    page.wait_for_timeout(200)  # Minimal wait for filtering to complete
                    
                    # Step 3: Select the filtered option using keyboard navigation
                    # After typing, the first matching option should already be highlighted
                    # Just press Enter to select it (don't press ArrowDown as it moves to next item)
                    try:
                        page.keyboard.press("Enter", delay=50)  # Select the highlighted option
                        page.wait_for_timeout(200)  # Minimal wait for selection to register
                        # Verify the selection was made by checking the dropdown value
                        try:
                            # Check if the value appears in the dropdown's text or value
                            current_value = dropdown_locator.input_value(timeout=1000)
                            if value_upper in current_value.upper() or current_value:
                            if status_cb:
                                    status_cb(f"✓ {field_name}: {value_upper}")
                                return True
                        except:
                            # Also try getting text content as fallback verification
                            try:
                                current_text = dropdown_locator.text_content(timeout=500)
                                if value_upper in current_text.upper() or current_text:
                                    if status_cb:
                                        status_cb(f"✓ {field_name}: {value_upper}")
                                    return True
                            except:
                                pass
                        # If we can't verify, assume success if no exception was raised
                        if status_cb:
                            status_cb(f"✓ {field_name}: {value_upper} (assumed success)")
                        return True
                    except Exception as e1:
                        # If keyboard navigation fails, try clicking the filtered option directly
                        try:
                            # Look for option elements or list items that contain the state abbreviation
                            # Try multiple selectors for different dropdown implementations
                            # Try exact match first, then partial match (e.g., "PW" in "Policy Writer (PW)")
                            option_selectors = [
                                f"{selector} option[value='{value_upper}']",  # Exact value match first
                                f"{selector} option:has-text('{value_upper}')",  # Exact text match
                                f"{selector} option:has-text('{value_upper}' i)",  # Case-insensitive
                                f"li:has-text('{value_upper}')",
                                f"li:has-text('{value_upper}' i)",  # Case-insensitive
                                f"[role='option']:has-text('{value_upper}')",
                                f"[role='option']:has-text('{value_upper}' i)",  # Case-insensitive
                                f"div[role='option']:has-text('{value_upper}')",
                                f"div[role='option']:has-text('{value_upper}' i)",  # Case-insensitive
                                f"*:has-text('{value_upper}'):visible",
                                f"*:has-text('{value_upper}' i):visible"  # Case-insensitive
                            ]
                            
                            for opt_sel in option_selectors:
                                try:
                                    option = page.locator(opt_sel).first
                                    if option.is_visible(timeout=500):
                                        option.click(timeout=2000)
                                        page.wait_for_timeout(100)  # Minimal wait
                                        if status_cb:
                                            status_cb(f"✓ {field_name}: {value_upper}")
                                        return True
                                except Exception:
                                    continue
                        except Exception as e2:
                            if status_cb:
                                status_cb(f"⚠ {field_name}: Selection failed - {str(e2)[:30]}")
                            pass
                    
                    # If all else fails, try JavaScript helper
                        if set_select_dropdown_value:
                        element_id = selector.lstrip("#")
                        success = set_select_dropdown_value(page, element_id, value_upper)
                            if success:
                                if status_cb:
                                status_cb(f"✓ {field_name}: {value_upper} (JS)")
                            return True
                    
                    if status_cb:
                        status_cb(f"⚠ {field_name}: Could not select {value_upper}")
                    return False
                    
                except Exception as e:
                    if status_cb:
                        status_cb(f"⚠ {field_name} dropdown error: {str(e)[:50]}")
                    return False
            
            # Step 1: Fill state dropdown FIRST (required before other fields appear)
            state_selector = field_to_selector.get("state")
            state_value = data.get("state", "")
            if not state_selector or not state_selector.strip():
                # Use default if not configured
                state_selector = "#ddComboState"
                if status_cb:
                    status_cb(f"⚠ State selector not configured, using default: {state_selector}")
            
            # Debug: Show what state value we're using
            if status_cb:
                if state_value:
                    status_cb(f"Using extracted state value: '{state_value}'")
                            else:
                    status_cb(f"⚠ No state value in data - state field is empty")
            
            if state_selector and state_value:
                                if status_cb:
                    status_cb(f"Step 1: Filling state dropdown (selector: {state_selector}, value: {state_value})...")
                
                # Check if element exists before trying to fill
                                try:
                    state_element = page.locator(state_selector).first
                    if state_element.count() == 0:
                                    if status_cb:
                            status_cb(f"⚠ State dropdown not found with selector: {state_selector}")
                        return False
                    else:
                        # For state dropdown, try to match full state name from dropdown options
                        state_value_to_use = state_value
                        try:
                            # Get all available options from the dropdown
                            available_options = page.evaluate(f"""
                                () => {{
                                    const dropdown = document.querySelector('{state_selector}');
                                    if (!dropdown || dropdown.tagName !== 'SELECT') return [];
                                    const opts = [];
                                    for (let i = 0; i < dropdown.options.length; i++) {{
                                        const opt = dropdown.options[i];
                                        if (opt.value && opt.value !== '' && opt.text.trim() !== '----- Select -----' && opt.text.trim() !== '------ Select ------') {{
                                            opts.push({{value: opt.value, text: opt.text.trim()}});
                                        }}
                                    }}
                                    return opts;
                                }}
                            """)
                            
                            if available_options:
                                state_abbr = state_value.upper().strip()
                                
                                # Mapping from abbreviations to full state names
                                abbrev_to_full = {
                                    "AL": "ALABAMA", "AK": "ALASKA", "AZ": "ARIZONA", "AR": "ARKANSAS", "CA": "CALIFORNIA",
                                    "CO": "COLORADO", "CT": "CONNECTICUT", "DE": "DELAWARE", "FL": "FLORIDA", "GA": "GEORGIA",
                                    "HI": "HAWAII", "ID": "IDAHO", "IL": "ILLINOIS", "IN": "INDIANA", "IA": "IOWA",
                                    "KS": "KANSAS", "KY": "KENTUCKY", "LA": "LOUISIANA", "ME": "MAINE", "MD": "MARYLAND",
                                    "MA": "MASSACHUSETTS", "MI": "MICHIGAN", "MN": "MINNESOTA", "MS": "MISSISSIPPI", "MO": "MISSOURI",
                                    "MT": "MONTANA", "NE": "NEBRASKA", "NV": "NEVADA", "NH": "NEW HAMPSHIRE", "NJ": "NEW JERSEY",
                                    "NM": "NEW MEXICO", "NY": "NEW YORK", "NC": "NORTH CAROLINA", "ND": "NORTH DAKOTA", "OH": "OHIO",
                                    "OK": "OKLAHOMA", "OR": "OREGON", "PA": "PENNSYLVANIA", "RI": "RHODE ISLAND", "SC": "SOUTH CAROLINA",
                                    "SD": "SOUTH DAKOTA", "TN": "TENNESSEE", "TX": "TEXAS", "UT": "UTAH", "VT": "VERMONT",
                                    "VA": "VIRGINIA", "WA": "WASHINGTON", "WV": "WEST VIRGINIA", "WI": "WISCONSIN", "WY": "WYOMING",
                                    "DC": "DISTRICT OF COLUMBIA"
                                }
                                
                                # If we have an abbreviation, try to find the full state name in dropdown options
                                if state_abbr in abbrev_to_full:
                                    full_state_name = abbrev_to_full[state_abbr]
                                    # Try to find matching option (case-insensitive, partial match)
                                    for opt in available_options:
                                        opt_text_upper = opt["text"].upper()
                                        # Check if option text contains the full state name or abbreviation
                                        if full_state_name in opt_text_upper or state_abbr in opt_text_upper:
                                            state_value_to_use = opt["text"]  # Use the exact text from dropdown
                                    if status_cb:
                                                status_cb(f"Found matching state option: '{state_value_to_use}'")
                                            break
                                
                                # If we already have a full state name, try to match it directly
                                if state_value_to_use == state_value:
                                    for opt in available_options:
                                        opt_text_upper = opt["text"].upper()
                                        state_value_upper = state_value.upper()
                                        # Check if option text matches (case-insensitive, partial match)
                                        if state_value_upper in opt_text_upper or opt_text_upper in state_value_upper:
                                            state_value_to_use = opt["text"]  # Use the exact text from dropdown
                                            if status_cb:
                                                status_cb(f"Found matching state option: '{state_value_to_use}'")
                                            break
                        except Exception as e:
                            # If getting options fails, just use the original value
                            if status_cb:
                                status_cb(f"Could not get dropdown options, using original value: {str(e)[:50]}")
                        
                        fill_dropdown("State", state_selector, state_value_to_use)
                        
                        # Minimal wait - just check if fields are ready quickly, don't block
                        if status_cb:
                            status_cb("Checking form readiness...")
                        try:
                            # Quick check - if fields are already there, great. If not, proceed anyway
                            page.wait_for_selector("input[name='license'], input[name='lastName'], input[name='firstName']", 
                                                  state="attached", timeout=500)  # Reduced timeout for speed
                            if status_cb:
                                status_cb("✓ Form fields ready")
                        except Exception:
                            # Fields not ready yet, but proceed anyway - they'll be ready by the time we need them
                            if status_cb:
                                status_cb("Form fields will be ready shortly...")
                except Exception as e:
                    if status_cb:
                        status_cb(f"⚠ Error locating state dropdown: {str(e)[:50]}")
                        else:
                            if status_cb:
                            status_cb(f"⚠ Skipping state - selector: '{state_selector}', value: '{state_value}'")
            
            # Step 2: Fill order_type dropdown IMMEDIATELY after state selection
            # Don't wait - let fill_dropdown handle retries internally for maximum speed
            order_type_selector = field_to_selector.get("order_type")
            if not order_type_selector or not order_type_selector.strip():
                # Use ID selector directly (faster than attribute selectors)
                order_type_selector = "#OrderTypeCombo"
                if status_cb:
                    status_cb(f"Using default Order Type selector: {order_type_selector}")
            else:
                if status_cb:
                    status_cb(f"Using configured Order Type selector: {order_type_selector}")
            
            if order_type_selector and order_type_selector.strip():
                if status_cb:
                    status_cb(f"Step 2: Filling order type dropdown (selector: {order_type_selector})...")
                
                # Check if element exists
                try:
                    order_type_element = page.locator(order_type_selector).first
                    if order_type_element.count() == 0:
                                if status_cb:
                            status_cb(f"⚠ Order Type dropdown not found with selector: {order_type_selector}")
                        return False
                    else:
                                if status_cb:
                            status_cb(f"✓ Order Type dropdown found")
                except Exception as e:
                    if status_cb:
                        status_cb(f"⚠ Error locating Order Type dropdown: {str(e)[:50]}")
                
                # Check if "PW" option exists first before trying (faster than retrying)
                pw_exists = False
                try:
                    order_type_element = page.locator(order_type_selector).first
                    if order_type_element.count() > 0:
                        # Quick check if "PW" option exists
                        available_options = order_type_element.evaluate("""
                            (select) => {
                                const opts = [];
                                for (let i = 0; i < select.options.length; i++) {
                                    const opt = select.options[i];
                                    if (opt.text && opt.text.trim()) {
                                        opts.push(opt.text.trim().toUpperCase());
                                    }
                                }
                                return opts;
                            }
                        """)
                        if available_options:
                            # Check if any option contains "PW"
                            pw_exists = any("PW" in opt for opt in available_options)
                    if status_cb:
                                status_cb(f"Order Type options: {available_options[:5]}")
                                if pw_exists:
                                    status_cb("Found PW option, selecting...")
                                else:
                                    status_cb("PW option not found, will try DL...")
                except Exception:
                    pass  # If check fails, just try PW anyway
                
                pw_success = False
                if pw_exists:
                    # Only try PW if it exists, with minimal retries
                    max_retries = 2  # Reduced from 3
                    for attempt in range(max_retries):
                        pw_success = fill_dropdown("Order Type", order_type_selector, "PW")
                        if pw_success:
                            break
                        if attempt < max_retries - 1:
                            page.wait_for_timeout(50)  # Reduced wait
                else:
                    if status_cb:
                        status_cb("PW not found in options, trying DL...")
                
                    # If "PW" not available or failed, try "DL" as fallback
                    if not pw_success:
                        if status_cb and pw_exists:
                            status_cb("PW selection failed, trying DL...")
                        dl_success = False
                        max_retries = 2  # Reduced from 3
                        for attempt in range(max_retries):
                            dl_success = fill_dropdown("Order Type", order_type_selector, "DL")
                        if dl_success:
                            break
                        if attempt < max_retries - 1:
                            page.wait_for_timeout(50)  # Reduced wait
                    
                    if not dl_success:
                if status_cb:
                            status_cb("⚠ Could not select Order Type (tried PW and DL)")
                
                # Minimal wait - just enough for selection to register
                page.wait_for_timeout(100)  # Reduced wait
        if status_cb:
                    status_cb("✓ Order Type dropdown complete")
            else:
        if status_cb:
                    status_cb("⚠ Skipping Order Type - no selector configured")
            
            # Step 3: Fill product dropdown with priority selection
            # Default selector based on inspection: ProductTypeCombo
            product_selector = field_to_selector.get("product")
            if not product_selector or not product_selector.strip():
                # Use ID selector directly (faster than attribute selectors)
                product_selector = "#ProductTypeCombo"
        if status_cb:
                    status_cb(f"Using default Product selector: {product_selector}")
            else:
        if status_cb:
                    status_cb(f"Using configured Product selector: {product_selector}")
            
            if product_selector and product_selector.strip():
        if status_cb:
                    status_cb(f"Step 3: Filling product dropdown (selector: {product_selector})...")
                
                # Check if element exists
                try:
                    product_element = page.locator(product_selector).first
                    if product_element.count() == 0:
                if status_cb:
                            status_cb(f"âš  Product dropdown not found with selector: {product_selector}")
                    else:
                if status_cb:
                            status_cb(f"✓ Product dropdown found")
                    except Exception as e:
                        if status_cb:
                        status_cb(f"âš  Error locating Product dropdown: {str(e)[:50]}")
                
                # Get state abbreviation for product selection
                state_abbr = state_value.upper().strip() if state_value else ""
                
                # Helper function to get available options from dropdown
                def get_dropdown_options(sel: str) -> list:
                    """Get list of available option texts from dropdown"""
                    try:
                        options = page.evaluate(f"""
                            () => {{
                                const dropdown = document.querySelector('{sel}');
                                if (!dropdown) return [];
                                const opts = [];
                                if (dropdown.tagName === 'SELECT') {{
                                    for (let i = 0; i < dropdown.options.length; i++) {{
                                        const opt = dropdown.options[i];
                                        if (opt.value && opt.value !== '' && opt.text.trim() !== '----- Select -----' && opt.text.trim() !== '------ Select ------') {{
                                            opts.push(opt.text.trim());
                                        }}
                                    }}
                                }}
                                return opts;
                            }}
                        """)
                        return options if isinstance(options, list) else []
                    except Exception:
                        return []
                
                # Helper function to check if dropdown already has correct value selected
                def is_product_already_selected(sel: str, priority_options: list) -> Tuple[bool, str]:
                    """Check if product dropdown already has a matching priority option selected. Returns (is_selected, current_value)"""
                    try:
                        result = page.evaluate(f"""
                            () => {{
                                const dropdown = document.querySelector('{sel}');
                                if (!dropdown || dropdown.tagName !== 'SELECT') return {{selected: false, value: null}};
                                const selectedOption = dropdown.options[dropdown.selectedIndex];
                                if (!selectedOption || !selectedOption.value || selectedOption.value === '' || 
                                    selectedOption.text.trim() === '----- Select -----' || 
                                    selectedOption.text.trim() === '------ Select ------') {{
                                    return {{selected: false, value: null}};
                                }}
                                return {{selected: true, value: selectedOption.text.trim()}};
                            }}
                        """)
                        if result and result.get("selected") and result.get("value"):
                            current_value = result.get("value")
                            # Check if current value matches any priority option
                            for priority_option in priority_options:
                                if priority_option.upper() in current_value.upper():
                                    return (True, current_value)
                            # If only one option exists and it's selected, that's fine too
                            return (True, current_value)
                        return (False, None)
                    except Exception:
                        return (False, None)
                
                # Start selection immediately - fill_dropdown will retry if options aren't ready yet
                max_retries = 3
                product_selected = False
                
                # Priority list: try each option in order
                priority_options = []
                if state_abbr:
                    priority_options = [
                        f"{state_abbr} PolicyWatch 3Y FULL",
                        f"{state_abbr} PolicyWatch 3Y Instant",
                        f"{state_abbr} DL 3Y Instant"
                    ]
                
                # IMMEDIATE CHECK: See if dropdown already has correct value (fastest path)
                is_selected, current_value = is_product_already_selected(product_selector, priority_options)
                if is_selected and current_value:
            if status_cb:
                        status_cb(f"âœ“ Product already selected: {current_value}")
                    product_selected = True
                else:
                    # Quick check: if there's only one option, select it immediately and skip all retry logic
                    try:
                        # Very quick check - don't wait long
                        page.wait_for_selector(product_selector, state="attached", timeout=500)  # Reduced from 2000 to 500
                        available_options = get_dropdown_options(product_selector)
                        if len(available_options) == 1:
                            # Only one option - select it immediately and move on
                    if status_cb:
                                status_cb(f"Only one product option, selecting: {available_options[0]}")
                            product_selected = fill_dropdown("Product", product_selector, available_options[0])
                            if product_selected:
                                # Skip all retry logic - we're done
                                pass
                    except:
                        # If quick check fails, fall through to retry logic
                        pass
                
                # Only do retry logic if we haven't selected yet
                if not product_selected:
                    # Try to get options and select based on priority
                    for attempt in range(max_retries):
                        try:
                            # Wait for dropdown to be populated (quick check)
                            page.wait_for_selector(product_selector, state="attached", timeout=1000)  # Reduced from 3000 to 1000
                            
                            # Get available options immediately (don't wait for multiple options - one is enough)
                            available_options = get_dropdown_options(product_selector)
                            
                            # If we have at least one valid option (not just placeholder), proceed
                            if len(available_options) == 0:
                                # Options not ready yet, wait briefly and retry
                                if attempt < max_retries - 1:
                                    page.wait_for_timeout(100)  # Reduced wait
                                    continue
                            
                            # Check again if it's already selected (in case it got populated between checks)
                            is_selected, current_value = is_product_already_selected(product_selector, priority_options)
                            if is_selected and current_value:
                        if status_cb:
                                    status_cb(f"âœ“ Product already selected: {current_value}")
                                product_selected = True
                                break
                            
                            # If only one option, check if it's already selected before trying to select it
                            if len(available_options) == 1:
                                # Double-check if it's already selected
                                is_selected, current_value = is_product_already_selected(product_selector, priority_options)
                                if is_selected:
                            if status_cb:
                                        status_cb(f"âœ“ Product already selected: {available_options[0]}")
                                    product_selected = True
                                    break
                                
                                # If not already selected, select it
                        if status_cb:
                                    status_cb(f"Selecting product: {available_options[0]}")
                                product_selected = fill_dropdown("Product", product_selector, available_options[0])
                                if product_selected:
                                    break
                            
                            # If multiple options, try priority options in order
                            if len(available_options) > 1:
                                # Try priority options in order
                                for priority_option in priority_options:
                                    # Check if this option exists (case-insensitive, partial match)
                                    matching_option = None
                                    for opt in available_options:
                                        if priority_option.upper() in opt.upper():
                                            matching_option = opt
                                            break
                                    
                                    if matching_option:
                                if status_cb:
                                            status_cb(f"Selecting: {matching_option}")
                                        product_selected = fill_dropdown("Product", product_selector, matching_option)
                                        if product_selected:
                                            break
                                
                                # If we found a match, break out of retry loop
                                if product_selected:
                                    break
                                
                                # If no priority match found, try to select first available option
                                if not product_selected and available_options:
                            if status_cb:
                                        status_cb(f"No priority match found, selecting first option: {available_options[0]}")
                                    product_selected = fill_dropdown("Product", product_selector, available_options[0])
                                    if product_selected:
                                        break
                            
                            # If we got here and still not selected, retry
                            if not product_selected and attempt < max_retries - 1:
                                page.wait_for_timeout(100)  # Reduced wait
                        
                        except Exception as e:
                            # Only show error if it's the last attempt or if it's not a timeout (which is expected during retries)
                            error_str = str(e).lower()
                            is_timeout = "timeout" in error_str
                            if not is_timeout or attempt == max_retries - 1:
                        if status_cb:
                                    status_cb(f"âš  Product dropdown error (attempt {attempt + 1}): {str(e)[:50]}")
                            if attempt < max_retries - 1:
                                page.wait_for_timeout(100)  # Reduced wait
                
                # Only show error if selection actually failed
                if not product_selected:
            if status_cb:
                        status_cb("âš  Could not select Product dropdown")
                        else:
                    # Selection succeeded, no error message needed
                    pass
                
                # No wait needed - if selection succeeded, form is ready immediately
                # Only wait if we need to ensure form has updated (but we'll check that in Step 4)
        if status_cb:
                    status_cb("✓ Product dropdown complete")
            else:
        if status_cb:
                    status_cb("âš  Skipping Product - no selector configured")
            
            # Step 4: Fill Purpose dropdown with "Insurance"
            # Wait a bit for form to be fully ready after Product dropdown
            page.wait_for_timeout(300)
            
            # Wait for JavaScript functions to complete (onload="retainProductType_Subproduct()")
            try:
                # Wait for the function to be defined and potentially executed
                page.wait_for_function("""
                    () => {
                        return typeof retainProductType_Subproduct === 'function' || 
                               document.querySelector('select[name="purposeCode"]') !== null;
                    }
                """, timeout=2000)
        if status_cb:
                    status_cb("✓ Page JavaScript functions ready")
                    except Exception:
                pass  # Function might not be needed or already executed
            
            purpose_selector = field_to_selector.get("purpose")
            if not purpose_selector or not purpose_selector.strip():
                # Use name selector directly (based on inspection: name='purposeCode')
                purpose_selector = "select[name='purposeCode']"
        if status_cb:
                    status_cb(f"Using default Purpose selector: {purpose_selector}")
            else:
        if status_cb:
                    status_cb(f"Using configured Purpose selector: {purpose_selector}")
            
            if purpose_selector and purpose_selector.strip():
        if status_cb:
                    status_cb(f"Step 4: Filling Purpose dropdown (selector: {purpose_selector})...")
                
                # Wait for Purpose dropdown to be in DOM first, then visible
                try:
                    # First wait for it to be in the DOM (attached)
                    page.wait_for_selector(purpose_selector, timeout=5000, state="attached")
            if status_cb:
                        status_cb(f"✓ Purpose dropdown found in DOM")
                    # Then wait for it to be visible
                    page.wait_for_selector(purpose_selector, timeout=3000, state="visible")
            if status_cb:
                        status_cb(f"✓ Purpose dropdown is visible and ready")
                except Exception as e:
            if status_cb:
                        status_cb(f"⚠ Purpose dropdown not ready: {str(e)[:60]}")
                    # Try to find it anyway - might be there but timing issue
                
                # Try direct selection by value first (we know from inspection: value='AA' for Insurance)
                purpose_success = False
                try:
                    # Try to find the dropdown - use multiple methods
                    purpose_element = None
                    
                    # Method 1: Try the configured selector
                    try:
                        purpose_element = page.locator(purpose_selector).first
                        if purpose_element.count() == 0:
                            purpose_element = None
                    except Exception:
                        purpose_element = None
                    
                    # Method 2: If selector failed, try finding by name attribute directly
                    if purpose_element is None or purpose_element.count() == 0:
                if status_cb:
                            status_cb("Trying alternative method to find Purpose dropdown...")
                        try:
                            # Use JavaScript to find it
                            found_element = page.evaluate("""
                                () => {
                                    const select = document.querySelector('select[name="purposeCode"]');
                                    return select ? true : false;
                                }
                            """)
                            if found_element:
                                purpose_element = page.locator("select[name='purposeCode']").first
                        if status_cb:
                                    status_cb("✓ Found Purpose dropdown using JavaScript query")
                        except Exception:
                            pass
                    
                    # Method 3: Try finding all select.commonfont and check which one has "Insurance"
                    if purpose_element is None or (purpose_element.count() == 0):
                if status_cb:
                            status_cb("Trying to find Purpose dropdown by checking all selects...")
                        try:
                            all_selects = page.locator("select.commonfont").all()
                            for select_elem in all_selects:
                                try:
                                    select_name = select_elem.evaluate("el => el.name", timeout=500)
                                    if select_name == "purposeCode":
                                        purpose_element = select_elem
                                if status_cb:
                                            status_cb(f"✓ Found Purpose dropdown by checking select.commonfont elements")
                                        break
                                except Exception:
                                    continue
                        except Exception:
                            pass
                    
                    if purpose_element is None or purpose_element.count() == 0:
                if status_cb:
                            status_cb(f"⚠ Could not find Purpose dropdown with any method")
                        # Debug: show what selects are available
                        try:
                            all_selects_info = page.evaluate("""
                                () => {
                                    const selects = document.querySelectorAll('select');
                                    const info = [];
                                    for (let i = 0; i < selects.length; i++) {
                                        const sel = selects[i];
                                        info.push({
                                            name: sel.name || '',
                                            id: sel.id || '',
                                            class: sel.className || '',
                                            visible: sel.offsetParent !== null
                                        });
                                    }
                                    return info;
                                }
                            """)
                            if status_cb and all_selects_info:
                                select_info_str = ", ".join([f"name='{s['name']}', id='{s['id']}', visible={s['visible']}" for s in all_selects_info[:5]])
                                status_cb(f"Available selects on page: {select_info_str}")
                        except Exception:
                            pass
                    
                    if purpose_element is not None and purpose_element.count() > 0:
                        # Wait for element to be attached and visible
                        purpose_element.wait_for(state="attached", timeout=2000)
                        purpose_element.wait_for(state="visible", timeout=2000)
                        
                        # Verify we have the correct element by checking its name attribute
                        element_name = purpose_element.evaluate("el => el.name", timeout=500)
                        if element_name != "purposeCode":
                    if status_cb:
                                status_cb(f"⚠ Wrong element! Expected name='purposeCode', got name='{element_name}' - skipping Purpose dropdown")
                            purpose_success = False
        else:
                            # Verify element count
                            if purpose_element.count() > 0:
                                # Check if dropdown is disabled - if so, wait a bit
                                is_disabled = purpose_element.evaluate("el => el.disabled", timeout=500)
                                if is_disabled:
            if status_cb:
                                        status_cb("Purpose dropdown is disabled, waiting...")
                                    page.wait_for_timeout(500)
                                    # Check again
                                    is_disabled = purpose_element.evaluate("el => el.disabled", timeout=500)
                                    if is_disabled:
                                if status_cb:
                                            status_cb("⚠ Purpose dropdown is still disabled")
                                
                                # Focus and click the dropdown first to ensure it's active
                                try:
                                    purpose_element.focus(timeout=1000)
                                    purpose_element.click(timeout=1000)
                                    page.wait_for_timeout(100)
                                except Exception:
                                    pass  # Click/focus might not be needed, but try it anyway
                                
                        if status_cb:
                                    status_cb("Attempting to select Insurance by value 'AA'...")
                                
                                # Method 1: Try selecting by value 'AA' directly (fastest method)
                                try:
                                    purpose_element.select_option(value="AA", timeout=3000)
                                    page.wait_for_timeout(200)  # Give it time to register
                                    # Verify selection
                                    selected_value = purpose_element.evaluate("el => el.value", timeout=500)
                                    selected_text = purpose_element.evaluate("el => el.options[el.selectedIndex].text.trim()", timeout=500)
                                    if selected_value == "AA":
                                if status_cb:
                                            status_cb(f"✓ Purpose dropdown: Insurance (by value AA) - verified value={selected_value}, text={selected_text}")
                                        purpose_success = True
                                    else:
                                if status_cb:
                                            status_cb(f"Value selection failed: expected AA, got {selected_value}, text={selected_text}")
                                except Exception as e1:
                            if status_cb:
                                        status_cb(f"Method 1 (value AA) failed: {str(e1)[:100]}")
                                
                                # Method 2: Try by label "Insurance" (case-sensitive)
                                if not purpose_success:
                                    try:
                                if status_cb:
                                            status_cb("Attempting to select Insurance by label...")
                                        purpose_element.select_option(label="Insurance", timeout=3000)
                                        page.wait_for_timeout(500)  # Longer wait for selection to register
                                        # Verify by checking both value and text - try multiple times
                                        selected_value = None
                                        selected_text = None
                                        for verify_attempt in range(3):
                                            try:
                                                selected_value = purpose_element.evaluate("el => el.value", timeout=500)
                                                selected_text = purpose_element.evaluate("el => el.options[el.selectedIndex].text.trim()", timeout=500)
                                                if selected_value == "AA" or (selected_text and "Insurance" in selected_text):
                                                    break
                                                if verify_attempt < 2:
                                                    page.wait_for_timeout(100)  # Wait a bit more and retry
                                            except Exception:
                                                if verify_attempt < 2:
                                                    page.wait_for_timeout(100)
                                        
                                        if selected_value == "AA" or (selected_text and "Insurance" in selected_text):
                                    if status_cb:
                                                status_cb(f"✓ Purpose dropdown: {selected_text} (by label) - verified value={selected_value}")
                                            purpose_success = True
                                        else:
                                    if status_cb:
                                                status_cb(f"Label selection verification failed: got value='{selected_value}', text='{selected_text}' - will try next method")
                                    except Exception as e2:
                                if status_cb:
                                            status_cb(f"Method 2 (label) failed: {str(e2)[:100]}")
                                
                                # Method 3: Try finding by text and selecting by index
                                if not purpose_success:
                                    try:
                                if status_cb:
                                            status_cb("Attempting to select Insurance by finding option index...")
                                        insurance_options = purpose_element.evaluate("""
                                            (select) => {
                                                const opts = [];
                                                for (let i = 0; i < select.options.length; i++) {
                                                    const opt = select.options[i];
                                                    const text = opt.text ? opt.text.trim() : '';
                                                    if (text === 'Insurance' || text.includes('Insurance')) {
                                                        opts.push({text: text, value: opt.value, index: i});
                                                        break;
                                                    }
                                                }
                                                return opts;
                                            }
                                        """)
                                        
                                        if insurance_options and len(insurance_options) > 0:
                                            insurance_opt = insurance_options[0]
                                    if status_cb:
                                                status_cb(f"Found Insurance option: value='{insurance_opt['value']}', index={insurance_opt['index']}")
                                            purpose_element.select_option(index=insurance_opt['index'], timeout=3000)
                                            page.wait_for_timeout(100)
                                            # Verify
                                            selected_index = purpose_element.evaluate("el => el.selectedIndex", timeout=500)
                                            if selected_index == insurance_opt['index']:
                                        if status_cb:
                                                    status_cb(f"✓ Purpose dropdown: {insurance_opt['text']} (by index)")
                                                purpose_success = True
                                            else:
                                        if status_cb:
                                                    status_cb(f"Index selection failed: expected index {insurance_opt['index']}, got {selected_index}")
                                        else:
                                    if status_cb:
                                                status_cb("⚠ Could not find 'Insurance' option in dropdown")
                                            # Debug: show all available options
                                            all_options = purpose_element.evaluate("""
                                                (select) => {
                                                    const opts = [];
                                                    for (let i = 0; i < select.options.length; i++) {
                                                        opts.push({text: select.options[i].text.trim(), value: select.options[i].value});
                                                    }
                                                    return opts;
                                                }
                                            """)
                                            if status_cb and all_options:
                                                status_cb(f"Available Purpose options: {[opt['text'] for opt in all_options[:10]]}")
                                    except Exception as e3:
                                if status_cb:
                                            status_cb(f"Method 3 (index) failed: {str(e3)[:50]}")
                                
                                # Method 4: Try JavaScript direct assignment with all events
                                if not purpose_success:
                                    try:
                                if status_cb:
                                            status_cb("Attempting to select Insurance via JavaScript with all events...")
                                        result = purpose_element.evaluate("""
                                            (select) => {
                                                // Find the Insurance option
                                                for (let i = 0; i < select.options.length; i++) {
                                                    const opt = select.options[i];
                                                    if (opt.value === 'AA' || (opt.text && opt.text.trim() === 'Insurance')) {
                                                        // Set selectedIndex
                                                        select.selectedIndex = i;
                                                        
                                                        // Trigger all possible events
                                                        select.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
                                                        select.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
                                                        select.dispatchEvent(new MouseEvent('change', { bubbles: true, cancelable: true }));
                                                        
                                                        // Also trigger on the option if possible
                                                        if (opt) {
                                                            opt.selected = true;
                                                        }
                                                        
                                                        // Return success info
                                                        return {success: true, value: select.value, text: select.options[select.selectedIndex].text.trim()};
                                                    }
                                                }
                                                return {success: false, value: select.value, text: ''};
                                            }
                                        """)
                                        page.wait_for_timeout(200)
                                        
                                        if result and result.get('success'):
                                            # Verify again from the page
                                            selected_value = purpose_element.evaluate("el => el.value", timeout=500)
                                            selected_text = purpose_element.evaluate("el => el.options[el.selectedIndex].text.trim()", timeout=500)
                                            if selected_value == "AA" or (selected_text and "Insurance" in selected_text):
                                        if status_cb:
                                                    status_cb(f"✓ Purpose dropdown: {selected_text} (via JavaScript) - value={selected_value}")
                                                purpose_success = True
                                            else:
                                        if status_cb:
                                                    status_cb(f"JavaScript selection failed: value={selected_value}, text={selected_text}, JS result={result}")
                                        else:
                                            # Check what we got
                                            selected_value = purpose_element.evaluate("el => el.value", timeout=500)
                                            selected_text = purpose_element.evaluate("el => el.options[el.selectedIndex].text.trim()", timeout=500)
                                    if status_cb:
                                                status_cb(f"JavaScript selection failed: value={selected_value}, text={selected_text}, JS result={result}")
                                    except Exception as e4:
                                if status_cb:
                                            status_cb(f"Method 4 (JavaScript) failed: {str(e4)[:100]}")
                            else:
                        if status_cb:
                                    status_cb(f"⚠ Purpose dropdown element count is 0")
                except Exception as e:
            if status_cb:
                        status_cb(f"Error accessing Purpose dropdown: {str(e)[:100]}")
                
                # If direct methods failed, use fill_dropdown with retries (same pattern as other dropdowns)
                if not purpose_success:
            if status_cb:
                        status_cb("Trying fill_dropdown as fallback...")
                    max_retries = 3
                    for attempt in range(max_retries):
                        purpose_success = fill_dropdown("Purpose", purpose_selector, "Insurance")
                        if purpose_success:
                            break
                        if attempt < max_retries - 1:
                    if status_cb:
                                status_cb(f"Retry {attempt + 1}/{max_retries} for Purpose dropdown...")
                            page.wait_for_timeout(200)
                    
                    if purpose_success:
                if status_cb:
                            status_cb("✓ Purpose dropdown: Insurance (via fill_dropdown)")
                        page.wait_for_timeout(100)
                    else:
                        # Final check - maybe it was selected but verification failed
                        try:
                            purpose_element = page.locator(purpose_selector).first
                            final_value = purpose_element.evaluate("el => el.value", timeout=500)
                            final_text = purpose_element.evaluate("el => el.options[el.selectedIndex].text.trim()", timeout=500)
                            if final_value == "AA" or (final_text and "Insurance" in final_text):
                        if status_cb:
                                    status_cb(f"✓ Purpose dropdown: {final_text} (final check - was already selected)")
                                purpose_success = True
                            else:
                        if status_cb:
                                    status_cb(f"⚠ Could not select Purpose: Insurance after all methods (final value={final_value}, text={final_text})")
                        except Exception:
                    if status_cb:
                                status_cb("⚠ Could not select Purpose: Insurance after all methods")
                else:
                    page.wait_for_timeout(100)
            else:
        if status_cb:
                    status_cb("⚠ Skipping Purpose - no selector configured")
            
            # IMPORTANT: Wait for all dropdowns to complete before filling input fields
            # This ensures the form is fully ready
            # No wait needed - if dropdowns completed successfully, form is ready immediately
            if status_cb:
                status_cb("Filling input fields (license, name, DOB)...")
            
            # Step 5: Fill all other fields (license, first name, last name, DOB)
            # These MUST come after all dropdowns are complete
            # Fill fields quickly with minimal delays
            
            for field, selector in field_to_selector.items():
                # Skip fields we've already handled
                if field in ("state", "order_type", "product", "purpose"):
                    continue
                
                value = data.get(field, "")
                # Clean DOB - remove underscores
                if field == "dob":
                    value = value.replace("_", "")
                
                if not selector:
            if status_cb:
                        status_cb(f"âš  Skipping {field} - no selector configured")
                    continue
                if not value:
            if status_cb:
                        status_cb(f"âš  Skipping {field} - no value to fill")
                    continue
                
                # Regular field handling - prioritize Playwright's native method
                # Special handling for DOB - need to click first and type character by character for auto-formatting
                # Special handling for first_name - if not found, skip it (don't block)
                filled = False
                
                # Check if field exists before trying to fill (especially for first_name)
                if field == "first_name":
                    try:
                        field_locator = page.locator(selector)
                        if field_locator.count() == 0:
                    if status_cb:
                                status_cb(f"⚠ First Name field not found - skipping")
                            continue
                    except Exception:
                if status_cb:
                            status_cb(f"⚠ First Name field error - skipping")
                        continue
                
                try:
                    # For DOB field, click it first to make it visible/appear
                    if field == "dob":
                        try:
                            field_locator = page.locator(selector)
                            field_locator.click(timeout=5000)
                            # No wait - click should be enough, typing will trigger field activation
                            
                            # Type DOB character by character to trigger automatic slash insertion
                            # Remove any existing slashes from value (e.g., "01/01/1990" -> "01011990")
                            dob_digits = ''.join(c for c in value if c.isdigit())
                            if dob_digits:
                                # Type each digit with minimal delay to allow auto-formatting
                                for digit in dob_digits:
                                    page.keyboard.type(digit, delay=2)  # Minimal delay for speed
                                
                                filled = True
                        if status_cb:
                                    status_cb(f"âœ“ DOB: {value}")
                        except Exception as e:
                    if status_cb:
                                status_cb(f"âš  DOB typing error: {str(e)[:50]}")
                            # Fall through to try regular fill method
                    
                    # For non-DOB fields, use regular fill method with reduced timeout
                    if not filled and field != "dob":
                        page.fill(selector, value, timeout=5000)  # Reduced timeout from 10000 to 5000
                        filled = True
                except Exception as e:
                    # If Playwright fails, try legacy helper as fallback
                    if fill_text_input:
                        try:
                            success = fill_text_input(page, selector, value, use_js=False)
                            if success:
                                filled = True
                        except Exception:
                            pass  # Legacy helper also failed, continue to next fallback
                    # Final fallback: click then type
                    if not filled:
                        try:
                            page.click(selector, timeout=3000)  # Reduced timeout from 5000 to 3000
                            # No wait after click - type immediately
                            if field == "dob":
                                # For DOB, type character by character even in fallback
                                dob_digits = ''.join(c for c in value if c.isdigit())
                                for digit in dob_digits:
                                    page.keyboard.type(digit, delay=2)  # Minimal delay for speed
                            else:
                                page.keyboard.type(value, delay=0)  # Type fast for other fields
                            filled = True
                        except Exception as e2:
                    if status_cb:
                                status_cb(f"âš  Warning: Could not fill {field} field (selector: {selector}): {str(e2)}")
                            pass
        else:
            if status_cb:
                status_cb("âš  Cannot fill MVR fields - login was not successful")
        
        if status_cb:
            status_cb("Done. Browser will stay open - you can close it manually when done.")
        # Keep browser open - the context manager will keep it alive
        # Browser will close when the function exits (when user closes the app or stops automation)
        # For now, add a long wait to keep browser open
        try:
            # Wait to keep browser open (user can close manually)
            # The browser stays open as long as this function is running
            if status_cb:
                status_cb("Browser will remain open. Close it manually when finished.")
            page.wait_for_timeout(3600000)  # Wait up to 1 hour (keeps browser open)
        except Exception as e:
            # If page closes or error occurs, that's okay - don't propagate
            # Common exceptions: TargetClosedError, TimeoutError, etc.
            if status_cb:
                error_str = str(e).lower()
                if "target closed" not in error_str and "timeout" not in error_str:
                    # Only log unexpected errors, don't show popup
                    status_cb(f"Browser closed or error: {str(e)[:50]}")
            pass


def build_tab(parent):
    """
    Create the MVR Runner tab.
    """
    outer = ttk.Frame(parent)

    # Load UI settings
    ui_settings = _load_ui_settings()
    size_key = ui_settings.get("display_size", "Medium")
    
    # Apply display size
    root = outer.winfo_toplevel()
    _apply_display_size(root, size_key)

    # Title
    title_label = ttk.Label(outer, text="MVR Runner - Automation Mode", font=("Segoe UI", 12, "bold"))
    title_label.pack(pady=(10, 2))
    
    # Directions section - shown/hidden based on saved state
    directions_frame = ttk.Frame(outer)
    
    # Load saved directions state - remember if user left it shown or hidden
    directions_collapsed = ui_settings.get("directions_collapsed", False)
    
    # Directions content - only show if not collapsed
    if not directions_collapsed:
        directions_frame.pack(fill="x", padx=16, pady=(0, 6))
        
        directions_label = ttk.Label(
            directions_frame,
        text="1) Drag & drop or choose MVR PDF(s) - supports multiple files\n2) Select a file and extract License, Last Name, First Name, DOB\n3) Configure selectors and Fill in Chrome"
        )
        directions_label.pack()  # Centered
        
        # Save state when user manually hides/shows (we'll add a way to toggle if needed)
        # For now, just remember the last state
        ui_settings["directions_collapsed"] = False
        _save_ui_settings(ui_settings)

    if _IMPORT_ERRORS:
        msg = "Missing dependencies:\n" + "\n".join([f"â€¢ {name}: {err}" for name, err in _IMPORT_ERRORS])
        warn = ttk.Label(outer, text=msg, foreground="#b00")
        warn.pack(pady=(6, 6))

    # Display size selector (similar to Binder Splitter)
    size_frame = ttk.Frame(outer)
    size_frame.pack(fill="x", padx=16, pady=(0, 6))
    ttk.Label(size_frame, text="Display size:").pack(side="left")
    size_var = tk.StringVar(value=size_key)
    size_combo = ttk.Combobox(size_frame, textvariable=size_var, values=list(_SIZE_PRESETS.keys()), state="readonly", width=8)
    size_combo.pack(side="left", padx=6)
    
    # Store references for updater functions (will be set later)
    button_layout_updater_ref = [None]
    enforce_visibility_ref = [None]
    
    def apply_selected_size():
        selected = size_var.get()
        # Update button widths FIRST, before applying display size
        # This ensures buttons are ready for the new font size
        try:
            if button_layout_updater_ref[0] is not None:
                # Temporarily update ui_settings so button updater uses correct size
                old_size = ui_settings.get("display_size", "Medium")
                ui_settings["display_size"] = selected
                button_layout_updater_ref[0]()
        except Exception:
            pass
        
        # Now apply the display size (fonts, padding, window size)
        _apply_display_size(root, selected)
        ui_settings["display_size"] = selected
        _save_ui_settings(ui_settings)
        
        # Update buttons again after display size is applied to ensure proper sizing
        try:
            if button_layout_updater_ref[0] is not None:
                button_layout_updater_ref[0]()
        except Exception:
            pass
        
        # Enforce minimum sizes when switching from Medium/Large to Small (or vice versa)
        # This prevents the frame from shrinking too much when switching to Small
        try:
            if enforce_visibility_ref[0] is not None:
                # Force immediate enforcement of minimum sizes
                enforce_visibility_ref[0]()
                # Also do a delayed check after layout settles to ensure minimums are maintained
                root_window = outer.winfo_toplevel()
                root_window.after(100, enforce_visibility_ref[0])
        except Exception:
            pass
        
        # Update copy button texts based on new display size (if function exists and buttons are created)
        try:
            if copy_buttons:  # Only update if buttons have been created
                update_copy_button_texts()
        except Exception:
            pass
        
        # Update listbox size and minimums based on new display size
        try:
            # Update listbox height based on display size
            if selected == "Small":
                # Small display: show more items
                pdf_listbox.configure(height=5)
                # Update minimum height for small display (must match initial setup: 360)
                new_listbox_min = 360  # 3x original: 120 * 3
            else:
                # Medium/Large: show fewer items but maintain minimum
                pdf_listbox.configure(height=1)
                # Update minimum height for medium/large display (must match initial setup: 120)
                new_listbox_min = 120  # 3x original: 40 * 3
            
            # Update minimum sizes for the file section
            new_min_file_height = new_listbox_min + title_and_padding
            button_height_estimate = 60
            new_total_min = new_min_file_height + button_height_estimate
            
            # Update paned window minimum
            try:
                main_paned.paneconfigure(file_section_frame, minsize=new_total_min)
                # Also trigger enforce_visibility to ensure consistency
                enforce_visibility()
            except Exception:
                pass
            
            # Force visibility enforcement to apply new minimums
            try:
                enforce_visibility()
            except Exception:
                pass
        except Exception:
            pass
    
    size_combo.bind("<<ComboboxSelected>>", lambda _=None: apply_selected_size())

    # Main vertical paned window for adjustable height
    main_paned = ttk.PanedWindow(outer, orient="vertical")
    main_paned.pack(fill="both", expand=True, padx=16, pady=10)
    
    # Container for file list and buttons
    file_section_frame = ttk.Frame(main_paned)
    
    # File list container (adjustable height) - only contains the listbox now
    file_list_frame = ttk.LabelFrame(file_section_frame, text="MVR Files")
    
    # Calculate minimum height based on display size
    # Small display needs larger listbox, Medium/Large can be smaller
    current_size = ui_settings.get("display_size", "Medium")
    if current_size == "Small":
        # Small display: larger listbox to show more items (about 4-5 items visible)
        # Increase minimum to prevent shrinking too much when switching from Medium/Large
        listbox_min_height = 360  # ~360px for small display (3x original: 120 * 3)
    else:
        # Medium/Large display: standard minimum (1-2 items visible)
        listbox_min_height = 120  # Minimum for listbox to show at least 1 file item clearly (3x original: 40 * 3)
    
    title_and_padding = 55  # Label frame title + padding
    min_file_height = listbox_min_height + title_and_padding  # Total height for listbox frame
    
    # Listbox fills the entire file_list_frame - frame directly connected to listbox with no gap
    file_list_frame.pack(fill="both", expand=True, padx=6, pady=(6, 0))  # No bottom padding to connect to listbox
    
    # Store references for enforcement function (will be set later when frames are created)
    list_scroll_frame_ref = [None]
    file_btn_frame_ref = [None]
    
    # Add file section to paned window
    main_paned.add(file_section_frame, weight=1)
    
    # Set minimum size after adding to ensure listbox is always visible
    try:
        main_paned.paneconfigure(file_section_frame, minsize=min_file_height + 60)  # Add space for buttons below
        
        # Additional enforcement: ensure listbox is always visible
        def enforce_visibility():
            """Ensure listbox is always visible by enforcing minimum frame height based on display size"""
            try:
                # Get current display-size-specific minimums
                current_size = ui_settings.get("display_size", "Medium")
                if current_size == "Small":
                    current_listbox_min = 360  # Small display: larger minimum (3x original: 120 * 3)
                    # Ensure it doesn't shrink below this when switching from Medium/Large
                else:
                    current_listbox_min = 120  # Medium/Large: standard minimum (3x original: 40 * 3)
                
                current_min_file_height = current_listbox_min + title_and_padding
                current_total_min = current_min_file_height + 60  # Add button space
                
                # Update paned window minimum to current display size requirements
                try:
                    main_paned.paneconfigure(file_section_frame, minsize=current_total_min)
                except Exception:
                    pass
                
                # Get current actual height of the frame
                file_list_frame.update_idletasks()
                current_height = file_list_frame.winfo_height()
                
                # Calculate maximum allowed shrink (negative value limit)
                # This is the maximum amount the frame can be reduced from its natural size
                # We want to prevent it from shrinking beyond the minimum
                max_shrink_allowed = current_min_file_height  # Can't shrink below this
                
                # Check if frame has been shrunk too much (beyond negative limit)
                if current_height < max_shrink_allowed:
                    # Frame has been dragged up too far - enforce minimum
                    # This prevents the "negative" movement from going past the limit
                    try:
                        main_paned.paneconfigure(file_section_frame, minsize=current_total_min)
                        # Force the frame to maintain minimum size
                        file_list_frame.update_idletasks()
                    except Exception:
                        pass
                
                # Also check that listbox area is visible
                if list_scroll_frame_ref[0] is not None:
                    try:
                        list_scroll_frame_ref[0].update_idletasks()
                        listbox_height = list_scroll_frame_ref[0].winfo_height()
                        # Maximum shrink for listbox itself (can't go below this)
                        max_listbox_shrink = current_listbox_min
                        if listbox_height < max_listbox_shrink:
                            # Listbox has been shrunk too much - enforce minimum
                            try:
                                list_scroll_frame_ref[0].configure(height=max_listbox_shrink)
                                list_scroll_frame_ref[0].update_idletasks()
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                pass
        
        # Bind to paned window resize events to enforce minimums
        main_paned.bind("<ButtonRelease-1>", lambda e: enforce_visibility())
        main_paned.bind("<B1-Motion>", lambda e: enforce_visibility())  # Also check during drag
    except Exception:
        # Fallback: if paneconfigure doesn't work, try setting minimum height on the frame itself
        pass
    
    # Listbox with scrollbar for multiple files (scrollable area)
    # Frame directly connected to the listbox with no gap
    list_scroll_frame = ttk.Frame(file_list_frame)
    list_scroll_frame_ref[0] = list_scroll_frame  # Store reference for enforcement function
    list_scroll_frame.pack(fill="both", expand=True, padx=6, pady=(0, 0))  # No padding to connect directly to listbox
    
    # Set listbox height based on display size
    # Small display: show more items (height=5), Medium/Large: show fewer (height=1)
    if current_size == "Small":
        listbox_initial_height = 5  # Show about 5 items on small display
    else:
        listbox_initial_height = 1  # Show 1 item minimum on medium/large
    
    pdf_listbox = tk.Listbox(list_scroll_frame, height=listbox_initial_height, selectmode=tk.SINGLE, exportselection=False)
    
    # Ensure listbox frame maintains minimum height to show at least one file item
    list_scroll_frame.update_idletasks()
    list_scroll_frame.pack_propagate(False)  # Prevent listbox area from shrinking below minimum
    pdf_listbox.pack(side="left", fill="both", expand=True)
    
    scrollbar = ttk.Scrollbar(list_scroll_frame, orient="vertical", command=pdf_listbox.yview)
    scrollbar.pack(side="right", fill="y")
    pdf_listbox.config(yscrollcommand=scrollbar.set)
    
    # Store file paths (list of full paths, indexed by listbox position)
    pdf_files = []  # List of full file paths
    
    # Store extracted/edited data per file: {filepath: {license_number: "", last_name: "", first_name: "", dob: "", state: ""}}
    file_data = {}  # Dictionary mapping file paths to their extracted/edited data
    
    # Store currently selected file path (persists even when listbox loses focus)
    current_selected_file = None
    
    # Initialize listbox with empty message
    pdf_listbox.insert(tk.END, "(No files - drag & drop or click 'Add Files...')")
    
    def update_listbox_display():
        """Update the listbox to show current files"""
        pdf_listbox.delete(0, tk.END)
        if pdf_files:
        for i, filepath in enumerate(pdf_files):
            filename = os.path.basename(filepath)
            pdf_listbox.insert(tk.END, f"{i+1}. {filename}")
        else:
            # Always show at least one row, even if empty
            pdf_listbox.insert(tk.END, "(No files - drag & drop or click 'Add Files...')")
    
    def add_files(file_paths):
        """Add one or more files to the list (avoid duplicates)"""
        added = False
        for p in file_paths:
            if p and os.path.isfile(p) and p.lower().endswith(".pdf"):
                # Avoid duplicates
                if p not in pdf_files:
                    pdf_files.append(p)
                    added = True
        if added:
            update_listbox_display()
        return added
    
    def choose_pdf():
        """Open file dialog to choose multiple PDFs"""
        files = filedialog.askopenfilenames(
            title="Select MVR PDF files",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if files:
            add_files(files)
    
    def remove_selected_file():
        """Remove the selected file from the list"""
        nonlocal current_selected_file
        selection = pdf_listbox.curselection()
        if selection:
            idx = selection[0]
            if 0 <= idx < len(pdf_files):
                filepath = pdf_files.pop(idx)
                # Also remove saved data for this file
                if filepath in file_data:
                    del file_data[filepath]
                # Clear stored selection if this was the selected file
                if current_selected_file == filepath:
                    current_selected_file = None
                update_listbox_display()
                # Clear fields if this was the selected file
                clear_fields()
    
    def clear_all_files():
        """Clear all files from the list"""
        nonlocal current_selected_file
        pdf_files.clear()
        file_data.clear()
        current_selected_file = None
        update_listbox_display()
        clear_fields()
    
    def clear_fields():
        """Clear all field values"""
        for key, var in fields.items():
            if key == "dob":
                var.set("__/__/____")
            else:
                var.set("")
        txt.delete("1.0", "end")
    
    def format_dob_value(value):
        """Format a DOB value to __/__/____ format"""
        if not value:
            return "__/__/____"
        # Remove all non-digits
        digits = ''.join(filter(str.isdigit, value))
        if len(digits) == 0:
            return "__/__/____"
        # Limit to 8 digits (MMDDYYYY)
        digits = digits[:8]
        
        # Build formatted string
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
        
        # Fill remaining with underscores to maintain format
        while len(formatted) < 10:
            if len(formatted) == 2:
                formatted += "/"
            elif len(formatted) == 5:
                formatted += "/"
            else:
                formatted += "_"
        
        return formatted
    
    def load_file_data(filepath):
        """Load saved data for a file into the fields"""
        if filepath in file_data:
            data = file_data[filepath]
            for key, var in fields.items():
                if key == "dob":
                    # Format DOB when loading
                    dob_value = data.get(key, "")
                    var.set(format_dob_value(dob_value))
                else:
                    var.set(data.get(key, ""))
            # Also load extracted text if available
            if "extracted_text" in data:
                txt.delete("1.0", "end")
                txt.insert("1.0", data["extracted_text"])
        else:
            clear_fields()
    
    def save_file_data(filepath):
        """Save current field values to file_data"""
        if filepath:
            # Clean DOB - remove underscores, keep digits and slashes
            dob_value = fields["dob"].get().strip().replace("_", "")
            file_data[filepath] = {
                "license_number": fields["license_number"].get().strip(),
                "last_name": fields["last_name"].get().strip(),
                "first_name": fields["first_name"].get().strip(),
                "dob": dob_value,
                "state": fields["state"].get().strip(),
                "extracted_text": txt.get("1.0", "end-1c")
            }
    
    # File management buttons (always visible, not shrinkable) - directly below the list frame
    file_btn_frame = ttk.Frame(file_section_frame)
    file_btn_frame_ref[0] = file_btn_frame  # Store reference for enforcement function
    file_btn_frame.pack(fill="x", padx=6, pady=(0, 6))  # No top padding - directly connected to list frame
    file_btn_frame.grid_columnconfigure(0, weight=1)
    
    # First row: Site Automation, Add Files, Remove, Clear All
    file_mgmt_row = ttk.Frame(file_btn_frame)
    file_mgmt_row.pack(fill="x", pady=(2, 4))  # Added top padding to shift buttons up
    
    # Load saved settings
    saved_settings = _load_mvr_settings()
    
    # Site Automation settings variables (will be used in dialog)
    url_var = tk.StringVar(value=saved_settings.get("url", "https://example.com/"))
    sel_vars: Dict[str, tk.StringVar] = {
        "license_number": tk.StringVar(value=saved_settings.get("selectors", {}).get("license_number", "input[name='license']")),
        "last_name": tk.StringVar(value=saved_settings.get("selectors", {}).get("last_name", "input[name='lastName']")),
        "first_name": tk.StringVar(value=saved_settings.get("selectors", {}).get("first_name", "input[name='firstName']")),
        "dob": tk.StringVar(value=saved_settings.get("selectors", {}).get("dob", "input[name='dob']")),
        "state": tk.StringVar(value=saved_settings.get("selectors", {}).get("state", "#ddComboState")),
        "order_type": tk.StringVar(value=saved_settings.get("selectors", {}).get("order_type", "")),
        "product": tk.StringVar(value=saved_settings.get("selectors", {}).get("product", "")),
        "purpose": tk.StringVar(value=saved_settings.get("selectors", {}).get("purpose", "")),
    }
    use_existing_var = tk.BooleanVar(value=saved_settings.get("use_existing_chrome", True))
    debug_port_var = tk.StringVar(value=saved_settings.get("debug_port", "9222"))
    
    # Login settings variables
    account_id_var = tk.StringVar(value=saved_settings.get("account_id", ""))
    user_id_var = tk.StringVar(value=saved_settings.get("user_id", ""))
    password_var = tk.StringVar(value=saved_settings.get("password", ""))
    auto_click_recaptcha_var = tk.BooleanVar(value=saved_settings.get("auto_click_recaptcha", True))
    login_sel_vars: Dict[str, tk.StringVar] = {
        "account_id": tk.StringVar(value=saved_settings.get("login_selectors", {}).get("account_id", "")),
        "user_id": tk.StringVar(value=saved_settings.get("login_selectors", {}).get("user_id", "")),
        "password": tk.StringVar(value=saved_settings.get("login_selectors", {}).get("password", "")),
    }
    
    def show_site_automation_dialog():
        """Open full-screen dialog for site automation settings"""
        root = outer.winfo_toplevel()
        dialog = tk.Toplevel(root)
        dialog.title("Site Automation Settings")
        # Make it large and centered
        dialog.geometry("900x700")
        dialog.transient(root)
        dialog.grab_set()  # Make it modal
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (900 // 2)
        y = (dialog.winfo_screenheight() // 2) - (700 // 2)
        dialog.geometry(f"900x700+{x}+{y}")
        
        # Main container
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(main_frame, text="Site Automation Settings", font=("Segoe UI", 14, "bold")).pack(pady=(0, 20))
        
        # URL setting
        url_frame = ttk.LabelFrame(main_frame, text="Target URL", padding=10)
        url_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(url_frame, text="URL:").pack(anchor="w")
        url_entry = ttk.Entry(url_frame, textvariable=url_var, width=60)
        url_entry.pack(fill="x", pady=(5, 0))
        
        # CSS Selectors
        selectors_frame = ttk.LabelFrame(main_frame, text="CSS Selectors", padding=10)
        selectors_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        selector_grid = ttk.Frame(selectors_frame)
        selector_grid.pack(fill="both", expand=True)
        
        ttk.Label(selector_grid, text="Field", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Label(selector_grid, text="CSS Selector", font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        for i, (label, key) in enumerate([
            ("License #", "license_number"), 
            ("Last Name", "last_name"), 
            ("First Name", "first_name"), 
            ("DOB", "dob"), 
            ("State", "state"),
            ("Order Type", "order_type"),
            ("Product", "product"),
            ("Purpose", "purpose")
        ], start=1):
            ttk.Label(selector_grid, text=label).grid(row=i, column=0, sticky="e", padx=5, pady=5)
            entry = ttk.Entry(selector_grid, textvariable=sel_vars[key], width=50)
            entry.grid(row=i, column=1, sticky="we", padx=5, pady=5)
        
        selector_grid.columnconfigure(1, weight=1)
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x")
        def on_save_site_settings():
            # Save site automation settings
            settings = _load_mvr_settings()
            settings["url"] = url_var.get().strip()
            settings["selectors"] = {
                "license_number": sel_vars["license_number"].get().strip(),
                "last_name": sel_vars["last_name"].get().strip(),
                "first_name": sel_vars["first_name"].get().strip(),
                "dob": sel_vars["dob"].get().strip(),
                "state": sel_vars["state"].get().strip(),
                "order_type": sel_vars["order_type"].get().strip(),
                "product": sel_vars["product"].get().strip(),
                "purpose": sel_vars["purpose"].get().strip(),
            }
            settings["use_existing_chrome"] = use_existing_var.get()
            settings["debug_port"] = debug_port_var.get().strip()
            _save_mvr_settings(settings)
            dialog.destroy()
        ttk.Button(btn_frame, text="Save", command=on_save_site_settings, width=15).pack(side="right", padx=(5, 0))
        ttk.Button(btn_frame, text="Cancel", command=lambda: dialog.destroy(), width=15).pack(side="right")
    
    def show_login_settings_dialog():
        """Open dialog for login settings"""
        root = outer.winfo_toplevel()
        dialog = tk.Toplevel(root)
        dialog.title("Login Settings")
        dialog.geometry("700x650")  # Increased size to ensure buttons are visible
        dialog.transient(root)
        dialog.grab_set()  # Make it modal
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (700 // 2)
        y = (dialog.winfo_screenheight() // 2) - (650 // 2)
        dialog.geometry(f"700x650+{x}+{y}")
        
        # Create a container with scrollable content area and fixed button area
        outer_container = ttk.Frame(dialog)
        outer_container.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Scrollable content area
        canvas = tk.Canvas(outer_container)
        scrollbar = ttk.Scrollbar(outer_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Main content frame inside scrollable area
        main_frame = ttk.Frame(scrollable_frame, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(main_frame, text="Login Settings", font=("Segoe UI", 14, "bold")).pack(pady=(0, 20))
        
        # Login credentials
        login_frame = ttk.LabelFrame(main_frame, text="Login Credentials", padding=15)
        login_frame.pack(fill="x", pady=(0, 15))
        
        # Account ID
        ttk.Label(login_frame, text="Account ID:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        account_entry = ttk.Entry(login_frame, textvariable=account_id_var, width=40)
        account_entry.grid(row=0, column=1, sticky="we", padx=5, pady=5)
        # Ensure the entry field updates the variable
        account_entry.bind('<KeyRelease>', lambda e: account_id_var.set(account_entry.get()))
        
        # User ID/User Name
        ttk.Label(login_frame, text="User ID/User Name:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        user_entry = ttk.Entry(login_frame, textvariable=user_id_var, width=40)
        user_entry.grid(row=1, column=1, sticky="we", padx=5, pady=5)
        
        # Password
        ttk.Label(login_frame, text="Password:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        password_entry = ttk.Entry(login_frame, textvariable=password_var, width=40, show="*")
        password_entry.grid(row=2, column=1, sticky="we", padx=5, pady=5)
        
        # Auto-click reCAPTCHA checkbox
        recaptcha_checkbox = ttk.Checkbutton(login_frame, text="Automatically click 'I'm not a robot' checkbox", 
                                             variable=auto_click_recaptcha_var)
        recaptcha_checkbox.grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=10)
        
        login_frame.columnconfigure(1, weight=1)
        
        # Save button right under Password field
        def on_save_login_settings():
            # Save login settings
            try:
                settings = _load_mvr_settings()
                
                # Get values from entry fields
                account_id_value = account_id_var.get().strip()
                user_id_value = user_id_var.get().strip()
                password_value = password_var.get().strip()
                
                # Update settings
                settings["account_id"] = account_id_value
                settings["user_id"] = user_id_value
                settings["password"] = password_value
                settings["auto_click_recaptcha"] = auto_click_recaptcha_var.get()
                settings["login_selectors"] = {
                    "account_id": login_sel_vars["account_id"].get().strip(),
                    "user_id": login_sel_vars["user_id"].get().strip(),
                    "password": login_sel_vars["password"].get().strip(),
                }
                
                # Save to file
                save_success = _save_mvr_settings(settings)
                
                if save_success:
                    # Verify account_id was actually saved
                    verify_settings = _load_mvr_settings()
                    if verify_settings.get("account_id") == account_id_value:
                        # Show confirmation
                        import tkinter.messagebox as mb
                        mb.showinfo("Settings Saved", "Login settings have been saved successfully.")
                    else:
                        import tkinter.messagebox as mb
                        mb.showwarning("Save Warning", "Settings may not have saved correctly. Please try again.")
                else:
                    import tkinter.messagebox as mb
                    mb.showerror("Save Error", "Failed to save settings. Please check file permissions.")
                
                dialog.destroy()
            except Exception as e:
                import tkinter.messagebox as mb
                mb.showerror("Save Error", f"Failed to save settings: {str(e)}")
        
        # Save button frame - placed right after reCAPTCHA checkbox
        save_btn_frame = ttk.Frame(login_frame)
        save_btn_frame.grid(row=4, column=0, columnspan=2, pady=(15, 5), sticky="e")
        
        save_btn = ttk.Button(save_btn_frame, text="Save", command=on_save_login_settings, width=15)
        save_btn.pack(side="right", padx=(5, 0))
        
        cancel_btn = ttk.Button(save_btn_frame, text="Cancel", command=lambda: dialog.destroy(), width=15)
        cancel_btn.pack(side="right")
        
        # CSS Selectors for login fields
        selectors_frame = ttk.LabelFrame(main_frame, text="CSS Selectors for Login Fields (Optional)", padding=15)
        selectors_frame.pack(fill="x", pady=(0, 15))
        
        # Use a separate frame for the info label to avoid grid/pack conflict
        info_frame = ttk.Frame(selectors_frame)
        info_frame.grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=(0, 10))
        ttk.Label(info_frame, text="If your login form uses non-standard field names, specify CSS selectors here.\nLeave empty to use automatic detection.", 
                 font=("Segoe UI", 9), foreground="gray").pack(anchor="w")
        
        # Account ID Selector
        ttk.Label(selectors_frame, text="Account ID Selector:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        account_sel_entry = ttk.Entry(selectors_frame, textvariable=login_sel_vars["account_id"], width=45)
        account_sel_entry.grid(row=1, column=1, sticky="we", padx=5, pady=5)
        
        # User ID Selector
        ttk.Label(selectors_frame, text="User ID Selector:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        user_sel_entry = ttk.Entry(selectors_frame, textvariable=login_sel_vars["user_id"], width=45)
        user_sel_entry.grid(row=2, column=1, sticky="we", padx=5, pady=5)
        
        # Password Selector
        ttk.Label(selectors_frame, text="Password Selector:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        password_sel_entry = ttk.Entry(selectors_frame, textvariable=login_sel_vars["password"], width=45)
        password_sel_entry.grid(row=3, column=1, sticky="we", padx=5, pady=5)
        
        selectors_frame.columnconfigure(1, weight=1)
        
        # Update scroll region
        canvas.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        
        # Ensure dialog is properly sized
        dialog.update_idletasks()
        dialog.minsize(700, 500)
    
    # Button widths scale with display size - use relative widths instead of fixed
    # Store button references for dynamic resizing
    add_files_btn = ttk.Button(file_mgmt_row, text="Add Files...", command=choose_pdf)
    remove_btn = ttk.Button(file_mgmt_row, text="Remove", command=remove_selected_file)
    clear_all_btn = ttk.Button(file_mgmt_row, text="Clear All", command=clear_all_files)
    login_settings_btn = ttk.Button(file_mgmt_row, text="Login Settings", command=show_login_settings_dialog)
    site_automation_btn = ttk.Button(file_mgmt_row, text="Site Automation Settings", command=show_site_automation_dialog)
    
    # Pack buttons with appropriate spacing and vertical padding to ensure text is visible
    add_files_btn.pack(side="left", padx=(0, 4), pady=2)
    remove_btn.pack(side="left", padx=(0, 4), pady=2)
    clear_all_btn.pack(side="left", pady=2)
    login_settings_btn.pack(side="right", padx=(4, 4), pady=2)
    site_automation_btn.pack(side="right", padx=(0, 0), pady=2)
    
    # Function to update button widths based on display size
    def update_button_widths():
        """Update button widths based on current display size - ensures text is always readable"""
        try:
            current_size = ui_settings.get("display_size", "Medium")
            preset = _SIZE_PRESETS.get(current_size, _SIZE_PRESETS["Medium"])
            font_size = preset["font_size"]
            button_padding = preset["button_padding"]
            
            # Button text and their base character widths (for Medium font_size=10)
            # These are the minimum widths needed to display the text comfortably
            button_configs = [
                (add_files_btn, "Add Files...", 12),
                (remove_btn, "Remove", 12),
                (clear_all_btn, "Clear All", 10),
                (login_settings_btn, "Login Settings", 18),
                (site_automation_btn, "Site Automation Settings", 22)
            ]
            
            # Calculate scale factor based on font size
            # For tkinter buttons, width is in characters, but font size affects character width
            # We need to scale more aggressively to account for larger fonts taking more space
            base_font_size = 10.0  # Medium baseline
            font_scale = font_size / base_font_size
            
            # Account for padding changes - larger padding needs more width
            base_padding = 4.0  # Medium baseline padding
            padding_scale = button_padding / base_padding if base_padding > 0 else 1.0
            
            # More aggressive scaling: font size has a bigger impact on character width
            # Use a weighted approach: 80% font scale, 20% padding scale (increased font weight)
            combined_scale = (font_scale * 0.8) + (padding_scale * 0.2)
            
            # Update each button with properly scaled width
            for btn, text, base_width in button_configs:
                # Calculate new width: base width scaled by font and padding
                scaled_width = base_width * combined_scale
                
                # For larger fonts, add extra width to prevent text compression
                if font_size > base_font_size:
                    # More aggressive: 20% extra width per point above baseline (increased from 15%)
                    extra_scale = 1.0 + ((font_size - base_font_size) * 0.20)
                    scaled_width *= extra_scale
                
                # For smaller fonts, ensure we still have enough width
                elif font_size < base_font_size:
                    # Don't shrink too much - maintain readability
                    scaled_width = max(scaled_width, base_width * 0.95)  # Increased from 0.9
                
                # Ensure minimum width based on text length with very generous padding
                text_length = len(text)
                # Very generous padding: text length + 6 chars for better spacing (increased from 4)
                # Also scale minimum width by font size to account for wider characters
                min_width_text = (text_length + 6) * font_scale
                min_width = max(int(min_width_text), int(base_width * 0.9))
                
                # Final width is the maximum of scaled width and minimum width
                new_width = max(int(scaled_width), min_width)
                
                # Configure button with new width
                btn.configure(width=new_width)
                
                # Force immediate update to prevent warping
                btn.update_idletasks()
                # Also force a full update to ensure layout is recalculated
                btn.update()
        except Exception as e:
            # If there's an error, try to set reasonable defaults
            try:
                for btn, text, base_width in button_configs:
                    # Fallback: use text length + generous padding
                    min_width = len(text) + 6
                    btn.configure(width=max(base_width, min_width))
            except Exception:
                pass
    
    # Store button update function for later use
    button_width_updater = update_button_widths
    
    # Initial button width setup
    update_button_widths()
    
    # After buttons are packed, ensure frames maintain their size and buttons are always visible
    file_list_frame.update_idletasks()
    file_btn_frame.update_idletasks()
    file_mgmt_row.update_idletasks()
    
    # Get the actual required height of the button row to ensure it's always visible
    try:
        actual_button_height = file_mgmt_row.winfo_reqheight()
        if actual_button_height > 0:
            # Set minimum height on the button row frame to match actual button height + padding
            button_frame_min = actual_button_height + 10  # Add padding for frame (top + bottom)
            # Update the grid row minimum if needed to ensure buttons are fully visible
            if button_frame_min > button_row_min_height:
                # Update the minimum size for the button row - CRITICAL for button visibility
                file_list_frame.grid_rowconfigure(1, minsize=button_frame_min)
                # Update paned window minimum to match - ensures buttons are never hidden
                new_min_height = button_frame_min + listbox_min_height + title_and_padding
                try:
                    main_paned.paneconfigure(file_list_frame, minsize=new_min_height)
                except Exception:
                    pass
    except Exception:
        pass
    
    # CRITICAL: Ensure buttons are always visible
    # First, make sure buttons are actually displayed by forcing an update
    file_mgmt_row.update_idletasks()
    file_btn_frame.update_idletasks()
    file_list_frame.update_idletasks()
    
    # Verify buttons are visible - if not, there's a layout issue
    try:
        # Check if button row has content
        natural_height = file_mgmt_row.winfo_reqheight()
        if natural_height == 0:
            # Buttons might not be visible - force a refresh
            file_mgmt_row.update()
            file_btn_frame.update()
            natural_height = file_mgmt_row.winfo_reqheight()
        
        # Set pack_propagate to prevent shrinking, but only if we have content
        if natural_height > 0:
            file_mgmt_row.pack_propagate(False)  # Prevent shrinking - ensures button row maintains size
        else:
            # If height is still 0, don't set pack_propagate as it might hide buttons
            # This shouldn't happen, but just in case
            pass
    except Exception:
        # If there's an error, still try to set pack_propagate to prevent shrinking
        file_mgmt_row.pack_propagate(False)
    
    # Ensure the button frame maintains its size
    try:
        btn_frame_height = file_btn_frame.winfo_reqheight()
        if btn_frame_height > 0:
            file_btn_frame.pack_propagate(False)  # Prevent shrinking - ensures button frame maintains size
        else:
            # Force update and check again
            file_btn_frame.update()
            btn_frame_height = file_btn_frame.winfo_reqheight()
            if btn_frame_height > 0:
                file_btn_frame.pack_propagate(False)
    except Exception:
        file_btn_frame.pack_propagate(False)  # Set anyway to prevent shrinking
    
    # Enhanced function to update button layout when display size changes
    def update_button_layout():
        """Update button widths and refresh layout when display size changes"""
        try:
            # Update button widths first (function is defined earlier in the same scope)
            update_button_widths()
            
            # Update copy button texts if they exist
            try:
                update_copy_button_texts()
            except Exception:
                pass
            
            # Force immediate update of all button frames to prevent warping
            # Also reconfigure button padding to ensure text is visible
            buttons_to_update = [
                add_files_btn, remove_btn, clear_all_btn, 
                login_settings_btn, site_automation_btn
            ]
            for btn in buttons_to_update:
                btn.update_idletasks()
                # Re-apply padding to ensure text is properly positioned
                try:
                    # Get current style padding and ensure it's applied
                    btn.update()
                except Exception:
                    pass
                btn.update()
            
            # Also update Run button width if it exists
            try:
                # Try to call update_run_button_width if it exists in the scope
                # This will be set up after the button is created
                pass  # Will be handled by the enhanced_updater if set up
            except Exception:
                pass
            
            # Update copy buttons if they exist
            try:
                for copy_btn in copy_buttons.values():
                    copy_btn.update_idletasks()
                    copy_btn.update()
            except Exception:
                pass
            
            # Force layout refresh at multiple levels - do idletasks first, then full update
            file_mgmt_row.update_idletasks()
            file_mgmt_row.update()
            file_btn_frame.update_idletasks()
            file_btn_frame.update()
            file_section_frame.update_idletasks()
            file_section_frame.update()
            
            # Wait a moment for layout to settle, then update again
            try:
                # Get root window from any widget
                root_window = file_section_frame.winfo_toplevel()
                root_window.after(50, lambda: [
                    file_mgmt_row.update_idletasks(),
                    file_btn_frame.update_idletasks(),
                    file_section_frame.update_idletasks()
                ])
            except Exception:
                pass
            
            # Recalculate minimum sizes based on new button sizes
            try:
                file_mgmt_row.update_idletasks()
                actual_button_height = file_mgmt_row.winfo_reqheight()
                if actual_button_height > 0:
                    button_frame_min = actual_button_height + 10
                    # Get current listbox min based on display size
                    current_size = ui_settings.get("display_size", "Medium")
                    if current_size == "Small":
                        current_listbox_min = 360
                    else:
                        current_listbox_min = 120
                    new_min_height = button_frame_min + current_listbox_min + title_and_padding
                    try:
                        main_paned.paneconfigure(file_section_frame, minsize=new_min_height)
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass
    
    # Store the enhanced updater for use by display size changer
    button_layout_updater_ref[0] = update_button_layout

    # Middle: extracted text and parsed fields (part of main paned window)
    content_frame = ttk.Frame(main_paned)
    
    # Calculate minimum height for content frame to show all fields (License, Last Name, First Name, DOB, State)
    # Each field row: ~30px, Label "Extracted Fields": ~25px, Copy-Paste toggle: ~30px, Status + Run button: ~60px
    # Total: 5 fields (150px) + label (25px) + toggle (30px) + bottom section (60px) = ~265px minimum
    # But we also need space for the extracted text area AND the horizontal paned window to function properly
    # The horizontal paned window needs enough space to show both left and right panes with their content
    # Minimum height: fields section (265px) + extracted text label (~25px) + text area minimum (~150px) + padding = ~450px
    # This ensures the horizontal paned window divider is always visible and functional
    content_min_height = 450  # Minimum to show all fields, buttons, and ensure horizontal paned window is always visible
    
    main_paned.add(content_frame, weight=3)
    
    # Set minimum size to ensure all fields (including DOB and State) are always visible
    # AND ensure the horizontal paned window inside is always functional and visible
    try:
        main_paned.paneconfigure(content_frame, minsize=content_min_height)
    except Exception:
        pass
    
    panes = ttk.PanedWindow(content_frame, orient="horizontal")
    panes.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    # Extracted text view
    left = ttk.Frame(panes)
    panes.add(left, weight=3)
    ttk.Label(left, text="Extracted Text").pack(anchor="w")
    txt = tk.Text(left, height=16, wrap="word", relief="solid", borderwidth=1)
    txt.pack(fill="both", expand=True)

    # Parsed fields editor
    right = ttk.Frame(panes)
    panes.add(right, weight=2)
    
    # Calculate minimum width for right pane to ensure buttons and fields are always visible
    # Field labels (16 chars ~120px) + entry fields (min 100px) + copy buttons (10 width ~80px) + Run button (20 width ~150px) + padding (40px)
    # Need at least 320px width to show all elements properly, especially the Run button
    right_pane_min_width = 320  # Minimum width to show all fields and buttons - prevents horizontal collapse
    
    # Set minimum size on the right pane to prevent collapsing and hiding buttons
    try:
        panes.paneconfigure(right, minsize=right_pane_min_width)
    except Exception:
        pass
    
    # Use grid for better control - button at bottom, fields in middle, toggle at top
    # Ensure bottom section (status + Run button) has fixed minimum to always be visible
    right.grid_rowconfigure(1, weight=1)  # Fields area can expand
    # Bottom section minimum size - adjusted for no status label
    # When Copy-Paste Mode is ON, button is hidden, so minimum is smaller
    right.grid_rowconfigure(2, weight=0, minsize=0)  # No minimum when hidden, will expand as needed
    right.grid_columnconfigure(0, weight=1)
    
    # Automation Mode: Run button always visible, no copy buttons
    # Middle section: Fields area (scrollable if needed)
    fields_container = ttk.Frame(right)
    fields_container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
    fields_container.grid_rowconfigure(0, weight=0)  # Label doesn't expand
    fields_container.grid_columnconfigure(0, weight=1)
    
    ttk.Label(fields_container, text="Extracted Fields").grid(row=0, column=0, sticky="w", pady=(5, 5))
    
    # Fields frame (scrollable) - minimum height to show all 5 fields (License, Last Name, First Name, DOB, State)
    # Each field row is ~30px, so 5 fields = 150px minimum
    fields_frame = ttk.Frame(fields_container)
    fields_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
    fields_container.grid_rowconfigure(1, weight=1, minsize=150)  # Fields frame can expand but minimum to show all 5 fields

    fields = {
        "license_number": tk.StringVar(),
        "last_name": tk.StringVar(),
        "first_name": tk.StringVar(),
        "dob": tk.StringVar(),
        "state": tk.StringVar(),
    }
    
    # Clipboard copy function with auto-paste setup
    auto_paste_enabled = False
    last_copied_value = None
    
    def copy_to_clipboard(value, field_name):
        """Copy value to clipboard and set up auto-paste on next click"""
        nonlocal auto_paste_enabled, last_copied_value
        
        if not value or value.strip() == "" or value == "__/__/____":
            return
        
        # Clean DOB value (remove underscores)
        if field_name == "dob":
            value = value.replace("_", "")
        
        try:
            # Copy to clipboard
            outer.clipboard_clear()
            outer.clipboard_append(value)
            outer.update()  # Ensure clipboard is updated
            
            last_copied_value = value
            auto_paste_enabled = True
            
            # Restart mouse listener if needed
            if pynput_available:
                if mouse_listener is None:
                    start_mouse_listener()
            
            # Show brief feedback
            field_label = field_name.replace("_", " ").title()
            if pynput_available:
                set_status(f"Copied {field_label}: {value} - Next click will auto-paste")
            else:
                set_status(f"Copied {field_label}: {value} - Press Ctrl+V to paste")
        except Exception as e:
            messagebox.showerror("Copy Error", f"Failed to copy to clipboard: {str(e)}")
    
    # Auto-paste on next click using global mouse hook
    mouse_listener = None
    try:
        from pynput import mouse
        from pynput.mouse import Listener as MouseListener
        pynput_available = True
    except ImportError:
        pynput_available = False
        mouse = None
        MouseListener = None
    
    def on_mouse_click(x, y, button, pressed):
        """Handle mouse click - if copy was done, paste on next click"""
        nonlocal auto_paste_enabled, mouse_listener
        
        if pressed and auto_paste_enabled and last_copied_value:
            # User clicked after copying - send Ctrl+V
            try:
                import pyautogui
                # Small delay to ensure click completes first
                import time
                time.sleep(0.1)
                pyautogui.hotkey('ctrl', 'v')
                auto_paste_enabled = False
                # Update UI from main thread
                outer.after(0, lambda: set_status("Auto-pasted! Copy another field to paste again"))
                # Stop listening after paste
                if mouse_listener:
                    mouse_listener.stop()
                    mouse_listener = None
            except ImportError:
                # Fallback: just notify user to press Ctrl+V
                outer.after(0, lambda: set_status("Please press Ctrl+V to paste (pyautogui not available)"))
                auto_paste_enabled = False
                if mouse_listener:
                    mouse_listener.stop()
                    mouse_listener = None
    
    def start_mouse_listener():
        """Start listening for mouse clicks"""
        nonlocal mouse_listener
        if pynput_available and mouse_listener is None:
            try:
                mouse_listener = MouseListener(on_click=on_mouse_click)
                mouse_listener.start()
                return True
            except Exception:
                return False
        return False
    
    # Start mouse listener if available
    if pynput_available:
        try:
            start_mouse_listener()
        except Exception:
            pass
    
    # DOB formatting function
    def format_dob_input(event):
        """Format DOB input as __/__/____ with automatic slashes"""
        widget = event.widget
        current = widget.get()
        
        # Remove all non-digits and underscores
        digits = ''.join(filter(str.isdigit, current))
        
        # Limit to 8 digits (MMDDYYYY)
        digits = digits[:8]
        
        # Format with slashes using the helper function
        formatted = format_dob_value(digits)
        
        # Update the field
        fields["dob"].set(formatted)
        
        # Position cursor appropriately after the last digit
        digit_count = len(digits)
        if digit_count == 0:
            widget.icursor(0)
        elif digit_count <= 2:
            widget.icursor(digit_count)
        elif digit_count <= 4:
            widget.icursor(digit_count + 1)  # +1 for the first slash
        else:
            widget.icursor(digit_count + 2)  # +2 for both slashes

    def row(parent_row, label, var, key, is_dob=False):
        r = ttk.Frame(parent_row)
        r.pack(fill="x", pady=2)
        field_frames[key] = r  # Store frame for mode switching
        
        ttk.Label(r, text=label, width=16).pack(side="left")
        entry = ttk.Entry(r, textvariable=var)
        entry.pack(side="left", fill="x", expand=True)
        
        # Copy buttons not shown in Automation mode
        
        # After widgets are packed, prevent frame from shrinking
        r.update_idletasks()
        r.pack_propagate(False)  # Prevent shrinking - keep buttons visible
        
        if is_dob:
            # Bind key events for DOB formatting
            entry.bind("<KeyRelease>", format_dob_input)
            entry.bind("<FocusIn>", lambda e: entry.icursor(0) if not entry.get() or entry.get() == "__/__/____" else None)
            # Set initial placeholder
            var.set("__/__/____")
        return entry
    
    dob_entry = None
    for label, key in [("License #", "license_number"), ("Last Name", "last_name"), ("First Name", "first_name"), ("DOB", "dob"), ("State", "state")]:
        if key == "dob":
            dob_entry = row(fields_frame, label, fields[key], key, is_dob=True)
        else:
            row(fields_frame, label, fields[key], key)
    
    # Run MVR's button below extracted fields
    def run_mvrs():
        """Run MVR automation for all files - auto-extracts if needed"""
        if not pdf_files:
            messagebox.showwarning("No Files", "Please add MVR files first.")
            return
        
        # Get login credentials
        account_id = account_id_var.get().strip()
        user_id = user_id_var.get().strip()
        password = password_var.get().strip()
        
        if not account_id or not user_id or not password:
            messagebox.showwarning("Missing Login", "Please configure Login Settings first.")
            return
        
        url = url_var.get().strip()
        if not url or url == "https://example.com/":
            messagebox.showwarning("Missing URL", "Please configure Site Automation Settings first.")
            return
        
        def work():
            try:
                set_status("Extracting data from all MVR files...")
                _ensure_playwright_browsers_installed(set_status)
                
                # Auto-extract data for all files that don't have data yet
                files_to_process = []
                for filepath in pdf_files:
                    if filepath not in file_data:
                        # Extract data for this file
                        try:
                            set_status(f"Extracting: {os.path.basename(filepath)}...")
                            text = _extract_text_from_pdf(filepath)
                            parsed = _parse_mvr_fields(text)
                            # Format DOB
                            if "dob" in parsed:
                                parsed["dob"] = format_dob_value(parsed["dob"])
                            # Debug: Show extracted state
                            extracted_state = parsed.get("state", "")
                            if extracted_state:
                                set_status(f"âœ“ Extracted state: {extracted_state}")
                            else:
                                set_status(f"âš  No state extracted from {os.path.basename(filepath)}")
                            # Save to file_data
                            file_data[filepath] = {
                                "license_number": parsed.get("license_number", ""),
                                "last_name": parsed.get("last_name", ""),
                                "first_name": parsed.get("first_name", ""),
                                "dob": parsed.get("dob", "").replace("_", ""),  # Clean DOB
                                "state": extracted_state,
                                "extracted_text": text
                            }
                        except Exception as e:
                            set_status(f"Error extracting {os.path.basename(filepath)}: {str(e)}")
                            continue
                    
                    # Add to processing list if we have valid data
                    if filepath in file_data:
                        data = file_data[filepath]
                        # Check if we have at least some data
                        if any(data.get(k, "") for k in ["license_number", "last_name", "first_name", "dob", "state"]):
                            files_to_process.append(filepath)
                
                if not files_to_process:
                    messagebox.showwarning("No Data", "Could not extract data from any files.")
                    set_status("No data extracted")
                    return
                
                set_status(f"Processing {len(files_to_process)} file(s)...")
                
                selectors = {k: v.get().strip() for k, v in sel_vars.items()}
                login_selectors_dict = {
                    "account_id": login_sel_vars["account_id"].get().strip(),
                    "user_id": login_sel_vars["user_id"].get().strip(),
                    "password": login_sel_vars["password"].get().strip(),
                }
                
                # Process all files sequentially
                for idx, filepath in enumerate(files_to_process, 1):
                    set_status(f"Processing file {idx}/{len(files_to_process)}: {os.path.basename(filepath)}...")
                    data = file_data[filepath]
                    # Run automation with login (only login once on first file)
                    try:
                    _run_mvr_automation(
                        url, selectors, data, account_id, user_id, password, 
                            set_status, cdp_endpoint=None, 
                        skip_login=(idx > 1),  # Skip login after first file
                            login_selectors=login_selectors_dict if any(login_selectors_dict.values()) else None,
                            auto_click_recaptcha=auto_click_recaptcha_var.get()
                        )
                    except Exception as automation_error:
                        error_msg = str(automation_error)
                        set_status(f"Automation error: {error_msg}")
                        # For errors, continue or show error
                        if "timeout" not in error_msg.lower() and "closed" not in error_msg.lower():
                            messagebox.showerror("Automation Error", error_msg)
                        raise  # Re-raise to be caught by outer exception handler
                    # Small delay between files
                    if idx < len(files_to_process):
                        import time
                        time.sleep(1)
                
                set_status(f"Automation complete - processed {len(files_to_process)} file(s)")
            except Exception as e:
                error_msg = str(e)
                set_status(f"Error during automation: {error_msg}")
                # Only show popup for significant errors, not minor exceptions
                # Skip popup for expected errors like browser closing, timeouts, etc.
                if "timeout" not in error_msg.lower() and "closed" not in error_msg.lower() and "navigation" not in error_msg.lower():
                    messagebox.showerror("Automation Error", error_msg)
        threading.Thread(target=work, daemon=True).start()
    
    # Bottom section: Run button (status removed - always visible)
    bottom_frame = ttk.Frame(right)
    # Reduced top padding since status label is removed
    bottom_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=(0, 0))
    bottom_frame.grid_columnconfigure(0, weight=1)
    # Note: minsize is set on right.grid_rowconfigure(2) above to ensure this section is always visible
    
    # Status label (hidden to give buttons more room - set_status still works but doesn't display)
    status_lbl = ttk.Label(bottom_frame, text="")
    status_lbl.grid_remove()  # Hidden - not displayed to give buttons more room

    def set_status(msg: str):
        # Status label is hidden to give buttons more room
        # Function kept for compatibility but doesn't display anything
        try:
            # Optionally log status messages for debugging if needed
            # print(f"Status: {msg}")  # Uncomment if you want console logging
            pass
        except Exception:
            pass
    
    # Run button frame (always visible, not shrinkable)
    run_btn_frame = ttk.Frame(bottom_frame)
    run_btn_frame_ref[0] = run_btn_frame  # Store reference for toggle function
    run_btn_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)  # Moved to row 0 since status is removed
    run_btn_frame.grid_columnconfigure(0, weight=1)
    # Create Run button with proper width to prevent text cropping
    run_btn = ttk.Button(run_btn_frame, text="Run MVR's", command=run_mvrs, width=20)
    run_btn.pack()
    
    # Update button width based on display size to prevent text cropping
    def update_run_button_width():
        try:
            current_size = ui_settings.get("display_size", "Medium")
            preset = _SIZE_PRESETS.get(current_size, _SIZE_PRESETS["Medium"])
            font_size = preset["font_size"]
            button_padding = preset["button_padding"]
            
            # Calculate appropriate width based on font size and text length
            base_font_size = 10.0
            font_scale = font_size / base_font_size
            base_padding = 4.0
            padding_scale = button_padding / base_padding if base_padding > 0 else 1.0
            
            # More aggressive scaling for larger fonts
            combined_scale = (font_scale * 0.8) + (padding_scale * 0.2)
            base_width = 20
            scaled_width = base_width * combined_scale
            
            # Add extra width for larger fonts
            if font_size > base_font_size:
                extra_scale = 1.0 + ((font_size - base_font_size) * 0.25)  # Increased from 0.20
                scaled_width *= extra_scale
            
            # Ensure minimum width based on text length with generous padding
            text_length = len("Run MVR's")
            min_width_text = (text_length + 8) * font_scale  # Increased from 6 to 8
            min_width = max(int(min_width_text), int(base_width * 0.95))  # Increased from 0.9
            
            new_width = max(int(scaled_width), min_width)
            run_btn.configure(width=new_width)
            run_btn.update_idletasks()
            run_btn.update()
            
            # Also update the frame to ensure proper layout
            run_btn_frame.update_idletasks()
            run_btn_frame.update()
        except Exception:
            pass
    
    # Update button width when display size changes
    if button_layout_updater_ref[0] is not None:
        original_updater = button_layout_updater_ref[0]
        def enhanced_updater():
            original_updater()
            update_run_button_width()
        button_layout_updater_ref[0] = enhanced_updater
    
    # Initial width update
    update_run_button_width()
    # After button is packed, prevent frame from shrinking
    run_btn_frame.update_idletasks()
    run_btn_frame.pack_propagate(False)  # Prevent shrinking
    
    # Run button always visible in Automation mode

    def get_selected_file():
        """Get the currently selected file from the listbox or stored selection"""
        nonlocal current_selected_file
        selection = pdf_listbox.curselection()
        if selection:
            idx = selection[0]
            if 0 <= idx < len(pdf_files):
                current_selected_file = pdf_files[idx]  # Update stored selection
                return pdf_files[idx]
        # If no listbox selection, use stored selection
        if current_selected_file and current_selected_file in pdf_files:
            return current_selected_file
        return None
    
    def on_extract():
        p = get_selected_file()
        if not p or not os.path.isfile(p):
            messagebox.showwarning("No File Selected", "Please select a file from the list above.")
            return
        def work():
            try:
                set_status("Extracting text...")
                text = _extract_text_from_pdf(p)
                txt.delete("1.0", "end")
                txt.insert("1.0", text)
                set_status("Parsing fields...")
                parsed = _parse_mvr_fields(text)
                for k, v in parsed.items():
                    if k in fields:
                        if k == "dob":
                            # Format DOB when setting from extraction
                            fields[k].set(format_dob_value(v))
                        else:
                            fields[k].set(v)
                # Save extracted data
                save_file_data(p)
                set_status("Ready - Review extracted fields above")
            except Exception as e:
                set_status("Error")
                messagebox.showerror("Extraction Error", str(e))
        threading.Thread(target=work, daemon=True).start()
    
    def on_save():
        """Save current field values for the selected file"""
        p = get_selected_file()
        if not p or not os.path.isfile(p):
            messagebox.showwarning("No File Selected", "Please select a file from the list above.")
            return
        
        save_file_data(p)
        set_status("Data saved for this file")
        messagebox.showinfo("Saved", "Data has been saved for this file.")
    
    # Save button row
    save_row = ttk.Frame(file_btn_frame)
    save_row.pack(fill="x")
    ttk.Button(save_row, text="Save", command=on_save, width=12).pack(side="left")
    
    # Drag and drop handler - supports multiple files
    def on_drop(e):
        data = (e.data or "").strip()
        if not data:
            return
        
        file_paths = []
        
        # Strategy 1: Handle curly braces format - each file wrapped in {}
        # Pattern: {C:/path/to/file.pdf} or {C:\path\to\file.pdf}
        # Split by } { to separate multiple files
        if "{" in data and "}" in data:
            # Split by } followed by optional whitespace and {
            parts = re.split(r'\}\s*\{', data)
            for part in parts:
                # Remove leading { and trailing }
                path = part.strip().strip('{').strip('}').strip()
                # Normalize forward slashes to backslashes for Windows
                path = path.replace('/', '\\')
                if path and os.path.isfile(path) and path.lower().endswith(".pdf"):
                    if path not in file_paths:
                        file_paths.append(path)
        
        # Strategy 2: If no curly braces, try quoted paths
        if not file_paths:
            # Pattern 1: Quoted paths: "C:\path with spaces\file.pdf" or "C:/path/file.pdf"
            quoted_pattern = r'"([A-Za-z]:[^"]+\.pdf)"'
            quoted_matches = re.finditer(quoted_pattern, data, re.IGNORECASE)
            for match in quoted_matches:
                path = match.group(1).replace('/', '\\')
                if os.path.isfile(path) and path.lower().endswith(".pdf"):
                    if path not in file_paths:
                        file_paths.append(path)
        
        # Strategy 3: Unquoted paths (no spaces): C:\path\to\file.pdf or C:/path/file.pdf
        if not file_paths:
            unquoted_pattern = r'(?:^|\s)([A-Za-z]:[^\s"]+\.pdf)(?=\s|$)'
            unquoted_matches = re.finditer(unquoted_pattern, data, re.IGNORECASE)
            for match in unquoted_matches:
                path = match.group(1).strip().replace('/', '\\')
                if os.path.isfile(path) and path.lower().endswith(".pdf"):
                    if path not in file_paths:
                        file_paths.append(path)
        
        # Strategy 4: Try as single file (fallback)
        if not file_paths:
            test_path = data.strip().strip('"').strip('{').strip('}').replace('/', '\\')
            if os.path.isfile(test_path) and test_path.lower().endswith(".pdf"):
                file_paths.append(test_path)
        
        if file_paths:
            added = add_files(file_paths)
            if added:
                # Auto-select the first newly added file
                if pdf_files:
                    nonlocal current_selected_file
                    pdf_listbox.selection_clear(0, tk.END)
                    pdf_listbox.selection_set(0)
                    pdf_listbox.see(0)
                    current_selected_file = pdf_files[0]  # Store the selected file
        else:
            # Debug: show what we received
            debug_msg = f"Could not parse dropped files.\nReceived: {data[:200]}..."
            messagebox.showerror("Invalid File", "Please drop valid PDF file(s).\n\n" + debug_msg)
    
    # Enable drag and drop if available
    if DND_FILES:
        try:
            # Register on multiple widgets for better coverage
            outer.drop_target_register(DND_FILES)
            outer.dnd_bind("<<Drop>>", on_drop)
            file_list_frame.drop_target_register(DND_FILES)
            file_list_frame.dnd_bind("<<Drop>>", on_drop)
            list_scroll_frame.drop_target_register(DND_FILES)
            list_scroll_frame.dnd_bind("<<Drop>>", on_drop)
            try:
                pdf_listbox.drop_target_register(DND_FILES)
                pdf_listbox.dnd_bind("<<Drop>>", on_drop)
            except Exception:
                # Listbox might not support drop, that's okay
                pass
        except Exception as ex:
            # Log but don't fail - drag and drop is optional
            try:
                import sys
                sys.stderr.write(f"Drag-and-drop registration warning: {ex}\n")
            except Exception:
                pass

    def on_fill():
        url = url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Enter a target URL.")
            return
        # Build data dict from fields
        data = {k: v.get().strip() for k, v in fields.items()}
        selectors = {k: v.get().strip() for k, v in sel_vars.items()}
        def work():
            try:
                set_status("Checking Playwright...")
                _ensure_playwright_browsers_installed(set_status)
                cdp_endpoint = None
                if use_existing_var.get():
                    port_str = (debug_port_var.get() or "").strip()
                    try:
                        port = int(port_str)
                    except Exception:
                        port = 9222
                    # Note: existing Chrome must be started with --remote-debugging-port=PORT
                    if _is_chrome_running():
                        if _is_port_open("127.0.0.1", port):
                            cdp_endpoint = f"http://127.0.0.1:{port}"
                            set_status(f"Trying to attach to Chrome on {cdp_endpoint}...")
                        else:
                            set_status(f"Chrome running, but port {port} not open. Will launch new instance.")
                    else:
                        set_status("No Chrome detected. Will launch a new instance.")
                else:
                    set_status("Launching new Chromium instance...")
                _fill_site_with_playwright(url, selectors, data, set_status, cdp_endpoint=cdp_endpoint)
                set_status("Automation complete")
            except Exception as e:
                set_status("Error during automation")
                messagebox.showerror("Automation Error", str(e))
        threading.Thread(target=work, daemon=True).start()

    # Selection handler - auto-load saved data or auto-extract when file is selected
    def on_listbox_select(e):
        """Auto-load saved data or auto-extract when a file is selected"""
        p = get_selected_file()
        if not p:
            return
        
        if p in file_data:
            # File has saved data, load it
            load_file_data(p)
            set_status("Loaded saved data for selected file")
        else:
            # No saved data, auto-extract
            def work():
                try:
                    set_status("Auto-extracting...")
                    text = _extract_text_from_pdf(p)
                    txt.delete("1.0", "end")
                    txt.insert("1.0", text)
                    set_status("Parsing fields...")
                    parsed = _parse_mvr_fields(text)
                    for k, v in parsed.items():
                        if k in fields:
                            if k == "dob":
                                # Format DOB when setting from extraction
                                fields[k].set(format_dob_value(v))
                            else:
                                fields[k].set(v)
                    # Save extracted data
                    save_file_data(p)
                    set_status("Auto-extracted and saved")
                except Exception as e:
                    set_status("Extraction Error")
                    messagebox.showerror("Extraction Error", str(e))
            threading.Thread(target=work, daemon=True).start()
    
    pdf_listbox.bind("<<ListboxSelect>>", on_listbox_select)
    
    return outer





