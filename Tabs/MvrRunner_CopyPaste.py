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

# Note: Automation functions are not imported as this is Copy-Paste mode only
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
    title_label = ttk.Label(outer, text="MVR Runner - Copy-Paste Mode", font=("Segoe UI", 12, "bold"))
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
    
    # Copy-Paste Mode: Copy buttons always visible, no toggle needed
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
    
    # Store copy buttons and field frames (for display size updates)
    copy_buttons = {}
    field_frames = {}
    
    def update_copy_button_texts():
        """Update copy button texts based on current display size"""
        current_size = ui_settings.get("display_size", "Medium")
        for key, copy_btn in copy_buttons.items():
            if current_size == "Small":
                # Small display: icon only, no text
                copy_btn.configure(text="📋", width=3)
            else:
                # Medium/Large display: icon + text
                copy_btn.configure(text="📋 Copy", width=10)
            copy_btn.update_idletasks()
            copy_btn.update()
    
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
        
        # Copy button (shown if copy-paste mode is enabled)
        # Determine button text based on display size
        current_size = ui_settings.get("display_size", "Medium")
        if current_size == "Small":
            # Small display: icon only, no text
            copy_btn_text = "📋"
            copy_btn_width = 3  # Narrow width for icon only
        else:
            # Medium/Large display: icon + text
            copy_btn_text = "📋 Copy"
            copy_btn_width = 10
        
        copy_btn = ttk.Button(
            r, 
            text=copy_btn_text, 
            width=copy_btn_width,
            command=lambda: copy_to_clipboard(var.get(), key)
        )
        copy_buttons[key] = copy_btn
        
        # Copy buttons always visible in Copy-Paste mode
        copy_btn.pack(side="right", padx=(5, 0))
        
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
    
        # Status function for compatibility
    def set_status(msg: str):
        # Status messages not displayed in Copy-Paste mode
        pass

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





