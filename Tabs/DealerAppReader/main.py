# -*- coding: utf-8 -*-
"""
Dealer Application Reader - Focused tool for extracting employee data from Dealer Applications.

This module:
1. Accepts a dealer application PDF
2. Identifies page 2 (BUSINESS PERSONNEL / NON-BUSINESS PERSONNEL tables)
3. OCRs that specific page
4. Parses and displays the employee data

No AI required - direct OCR and parsing for speed and reliability.
"""
import os
import re
import threading
from typing import List, Dict, Optional

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Try to import required libraries
_PYMUPDF_AVAILABLE = False
_PIL_AVAILABLE = False
_TESSERACT_AVAILABLE = False
_EASYOCR_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    _PYMUPDF_AVAILABLE = True
except ImportError:
    pass

try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    pass

try:
    import pytesseract
    _TESSERACT_AVAILABLE = True
except ImportError:
    pass

try:
    import easyocr
    _EASYOCR_AVAILABLE = True
except ImportError:
    pass

# Try drag-and-drop support
try:
    from tkinterdnd2 import DND_FILES
    _DND_AVAILABLE = True
except ImportError:
    DND_FILES = None
    _DND_AVAILABLE = False


# ==================== DEALER APPLICATION DETECTION ====================
# Same cues as Binder Splitter

_DEALER_APP_CUES = [
    r'(?i)\bDEALER\s+APPLICATION\b',
    r'(?i)\bNEW\s+BUSINESS\s+QUOTE\b',
    r'(?i)\bRENEWAL\s+OF\s+POL\b',
]

_EMPLOYEE_TABLE_CUES = [
    r'(?i)\bBUSINESS\s+PERSONNEL\b',
    r'(?i)\bNON\s*-?\s*BUSINESS\s+PERSONNEL\b',
]


def _find_employee_table_page(file_path: str) -> Optional[int]:
    """
    Find the page number containing employee tables.
    Returns 0-indexed page number, or None if not found.
    """
    if not _PYMUPDF_AVAILABLE:
        return None
    
    try:
        doc = fitz.open(file_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text().upper()
            
            # Check for employee table headers
            if 'BUSINESS PERSONNEL' in text or 'NON-BUSINESS PERSONNEL' in text or 'NON BUSINESS PERSONNEL' in text:
                doc.close()
                return page_num
        
        doc.close()
        
        # Default to page 2 (index 1) if not found but document has 2+ pages
        if len(doc) >= 2:
            return 1
        
        return None
        
    except Exception:
        return None


def _ocr_page(file_path: str, page_num: int) -> List[Dict]:
    """
    OCR a specific page and return text items with positions.
    
    Returns list of: [{'text': str, 'x': float, 'y': float, 'width': float, 'height': float}, ...]
    """
    if not _PYMUPDF_AVAILABLE or not _PIL_AVAILABLE:
        return []
    
    try:
        from io import BytesIO
        
        doc = fitz.open(file_path)
        if page_num >= len(doc):
            doc.close()
            return []
        
        page = doc[page_num]
        
        # Convert to image
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom
        img_data = pix.tobytes("png")
        img = Image.open(BytesIO(img_data))
        
        doc.close()
        
        results = []
        
        # Try Tesseract first (faster, better positioned data)
        if _TESSERACT_AVAILABLE:
            try:
                data = pytesseract.image_to_data(img, lang='eng', output_type=pytesseract.Output.DICT)
                
                for i in range(len(data['text'])):
                    text = data['text'][i]
                    conf = data['conf'][i]
                    
                    if text and text.strip() and conf > 30:
                        results.append({
                            'text': text.strip(),
                            'x': data['left'][i],
                            'y': data['top'][i],
                            'width': data['width'][i],
                            'height': data['height'][i],
                            'conf': conf
                        })
                
                if results:
                    return results
            except Exception as e:
                print(f"Tesseract OCR error: {e}")
        
        # Fallback to EasyOCR if Tesseract failed or not available
        if _EASYOCR_AVAILABLE:
            try:
                import numpy as np
                img_array = np.array(img)
                reader = easyocr.Reader(['en'], gpu=False)
                ocr_result = reader.readtext(img_array, detail=1)
                
                for item in ocr_result:
                    if len(item) >= 2:
                        bbox = item[0]  # Bounding box coordinates
                        text = item[1]  # Text
                        conf = item[2] if len(item) > 2 else 0.5  # Confidence
                        
                        if text and text.strip() and conf > 0.3:
                            # Calculate center and dimensions from bbox
                            x_coords = [p[0] for p in bbox]
                            y_coords = [p[1] for p in bbox]
                            x = min(x_coords)
                            y = min(y_coords)
                            width = max(x_coords) - x
                            height = max(y_coords) - y
                            
                            results.append({
                                'text': text.strip(),
                                'x': x,
                                'y': y,
                                'width': width,
                                'height': height,
                                'conf': conf * 100
                            })
                
                if results:
                    return results
            except Exception as e:
                print(f"EasyOCR error: {e}")
        
        return results
        
    except Exception as e:
        print(f"OCR error: {e}")
        import traceback
        traceback.print_exc()
        return []


def _parse_employee_tables(ocr_items: List[Dict], img_height: int = 2000) -> Dict:
    """
    Parse OCR results into BUSINESS PERSONNEL and NON-BUSINESS PERSONNEL tables.
    
    Returns:
    {
        'business_personnel': [
            {'name': str, 'dob': str, 'license': str, 'state': str, 'position': str, ...},
            ...
        ],
        'non_business_personnel': [
            {'name': str, 'dob': str, 'license': str, 'state': str, 'relationship': str, ...},
            ...
        ]
    }
    """
    result = {
        'business_personnel': [],
        'non_business_personnel': [],
        'raw_text': ''
    }
    
    if not ocr_items:
        return result
    
    # Find section headers
    business_header_y = None
    non_business_header_y = None
    
    for item in ocr_items:
        text_upper = item['text'].upper()
        y = item['y']
        
        if 'BUSINESS' in text_upper and 'PERSONNEL' in text_upper:
            if 'NON' in text_upper or business_header_y is not None:
                non_business_header_y = y
            else:
                business_header_y = y
    
    # Sort items by Y then X
    sorted_items = sorted(ocr_items, key=lambda i: (i['y'], i['x']))
    
    # Build raw text for display
    result['raw_text'] = '\n'.join(item['text'] for item in sorted_items)
    
    # Group into rows
    rows = []
    current_row = []
    current_y = None
    row_threshold = 20
    
    for item in sorted_items:
        if current_y is None or abs(item['y'] - current_y) <= row_threshold:
            current_row.append(item)
            current_y = item['y'] if current_y is None else current_y
        else:
            if current_row:
                current_row.sort(key=lambda i: i['x'])
                rows.append({'y': current_y, 'items': current_row})
            current_row = [item]
            current_y = item['y']
    
    if current_row:
        current_row.sort(key=lambda i: i['x'])
        rows.append({'y': current_y, 'items': current_row})
    
    # Parse rows into employee records
    for row in rows:
        y = row['y']
        texts = [item['text'] for item in row['items']]
        row_text = ' '.join(texts)
        
        # Skip header rows
        if any(h in row_text.upper() for h in ['NAME', 'LICENSE', 'POSITION', 'PERSONNEL', 'OWNERS', 'OFFICERS', 'SPOUSES', 'HOUSEHOLD', 'RELATIONSHIP']):
            continue
        
        # Skip rows with too few items or no letters (likely checkbox artifacts)
        if len(texts) < 2:
            continue
        if not any(any(c.isalpha() for c in t) for t in texts):
            continue
        
        # Apply state corrections to individual text items (only 2-char items that might be states)
        # This fixes OCR errors like "1L" → "IL" without breaking date formats
        texts_corrected = []
        for text_item in texts:
            # Only apply state corrections to 2-character items (likely state codes)
            if len(text_item.strip()) == 2:
                corrected = _normalize_state(text_item)
                if corrected:
                    texts_corrected.append(corrected)
                else:
                    texts_corrected.append(text_item)  # Keep original if not a state
            else:
                texts_corrected.append(text_item)  # Keep all other items as-is (preserves dates)
        
        # Try to parse as employee record (use corrected texts)
        record = _parse_row_as_employee(texts_corrected)
        if record:
            # Determine which section this belongs to
            if non_business_header_y and y > non_business_header_y:
                result['non_business_personnel'].append(record)
            elif business_header_y and y > business_header_y:
                result['business_personnel'].append(record)
    
    return result


def _normalize_date(date_str: str) -> str:
    """
    Normalize date string to MM/DD/YYYY format, handling OCR errors.
    
    Examples:
    - "2/11/1995" → "02/11/1995"
    - "21/11/995" → "02/11/1995" (OCR error: "2" and "1" combined, year truncated)
    - "2111/995" → "02/11/1995" (OCR error: missing slashes)
    - "2/11/95" → "02/11/1995" (2-digit year)
    """
    if not date_str:
        return ""
    
    # Remove trailing underscores and clean
    date_str = date_str.strip().rstrip('_').rstrip()
    
    # Handle dates where slash is misread (e.g., "2111/995" → "2/11/1995")
    # Pattern: 3-4 digits, then /, then 3-4 digits (year)
    slash_misread = re.match(r'^(\d{3,4})/(\d{3,4})$', date_str)
    if slash_misread:
        first_part = slash_misread.group(1)
        year_part = slash_misread.group(2)
        
        # Try to split first_part into month and day
        if len(first_part) == 4:
            # Try 1+2 split (e.g., "2111" → "2" + "11")
            if first_part[0] in '12' and 1 <= int(first_part[1:3]) <= 31:
                month = first_part[0]
                day = first_part[1:3]
            # Try 2+2 split (e.g., "1211" → "12" + "11")
            elif 1 <= int(first_part[0:2]) <= 12 and 1 <= int(first_part[2:4]) <= 31:
                month = first_part[0:2]
                day = first_part[2:4]
            else:
                # Default: assume 1+2 split
                month = first_part[0]
                day = first_part[1:3]
        elif len(first_part) == 3:
            month = first_part[0]
            day = first_part[1:3]
        else:
            return date_str  # Can't parse
        
        # Fix year (add missing "1" or "19" prefix if truncated)
        if len(year_part) == 3:
            # "995" → "1995"
            year = "1" + year_part
        elif len(year_part) == 2:
            # "95" → "1995" (if > 50) or "2095" (if <= 50)
            year = "19" + year_part if int(year_part) > 50 else "20" + year_part
        else:
            year = year_part
        
        # Validate and format
        if 1 <= int(month) <= 12 and 1 <= int(day) <= 31 and 1900 <= int(year) <= 2099:
            return f"{month.zfill(2)}/{day.zfill(2)}/{year}"
    
    # Handle normal date format M/D/YYYY or MM/DD/YYYY
    # Also handle cases where month is > 12 (OCR combined digits, e.g., "21/11/995")
    date_match = re.match(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})', date_str)
    if date_match:
        month, day, year = date_match.groups()
        
        # Fix OCR errors where month is > 12 (e.g., "21/11/995" → month="21" should be "2")
        # This happens when "2" and "1" are combined
        month_int = int(month)
        if month_int > 12:
            # Try splitting: if month is 21-31, it might be "2" + "1" (day)
            # But we need to check if day makes sense
            day_int = int(day)
            if month_int >= 21 and month_int <= 31 and day_int <= 12:
                # Swap: "21/11" might be "2/11" with first digit of day combined
                # Actually, "21/11" is likely "2/11" where "2" and "1" got combined
                # Split month: take first digit
                month = str(month_int // 10)  # "21" → "2"
                # Day stays the same if it's valid
            elif month_int >= 13 and month_int <= 19:
                # "13" through "19" might be "1" + "3" (month=1, day starts with 3)
                # But this is ambiguous, so try first digit
                month = month[0]
        
        # Fix truncated years
        if len(year) == 3:
            # "995" → "1995"
            year = "1" + year
        elif len(year) == 2:
            # "95" → "1995" (if > 50) or "2095" (if <= 50)
            year = "19" + year if int(year) > 50 else "20" + year
        
        # Validate
        month_int = int(month)
        day_int = int(day)
        year_int = int(year)
        if 1 <= month_int <= 12 and 1 <= day_int <= 31 and 1900 <= year_int <= 2099:
            return f"{month.zfill(2)}/{day.zfill(2)}/{year}"
    
    return date_str  # Return original if can't parse


def _apply_state_corrections_to_text(text: str) -> str:
    """
    Apply state code corrections to entire text (same approach as OllamaTool's _clean_ocr_text).
    This fixes OCR errors like "1L" → "IL" globally before parsing.
    """
    if not text:
        return text
    
    # Comprehensive state code corrections (same as OllamaTool)
    state_corrections = {
        # IL (Illinois) - most commonly misread
        "1L": "IL", "I1": "IL", "|L": "IL", "|1": "IL", "11": "IL",
        "1l": "IL", "i1": "IL", "|l": "IL", "1|": "IL", "|I": "IL",
        "IL.": "IL", "IL,": "IL",
        # Other common misreadings
        "N1": "NY", "NY.": "NY", "NY,": "NY",
        "C4": "CA", "CA.": "CA", "CA,": "CA",
        "P4": "PA", "PA.": "PA", "PA,": "PA",
        "F1": "FL", "FL.": "FL", "FL,": "FL",
        "0H": "OH", "OH.": "OH", "OH,": "OH",
        "M1": "MI", "MI.": "MI", "MI,": "MI",
        "TX.": "TX", "TX,": "TX",
    }
    
    # Apply corrections using word boundaries (same as OllamaTool)
    for wrong, correct in state_corrections.items():
        # Match standalone codes (word boundaries)
        text = re.sub(r'\b' + re.escape(wrong) + r'\b', correct, text, flags=re.IGNORECASE)
        # Also match codes that might be part of "STATE" column context
        text = re.sub(r'\b(STATE|State)\s+' + re.escape(wrong) + r'\b', 
                     r'\1 ' + correct, text, flags=re.IGNORECASE)
    
    return text


def _normalize_state(state_str: str) -> str:
    """
    Normalize state code, handling OCR errors.
    
    Examples:
    - "IL" → "IL"
    - "1L" → "IL" (I misread as 1)
    - "I1" → "IL" (L misread as 1)
    - "|L" → "IL" (I misread as |)
    - "1l" → "IL" (lowercase)
    - "IL." → "IL" (extra period)
    """
    if not state_str:
        return ""
    
    # Remove trailing periods, underscores, and clean
    state_str = state_str.strip().rstrip('._- ').upper()
    
    if not state_str:
        return ""
    
    # Valid US state codes
    valid_states = ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY']
    
    # Check if it's already a valid state
    if state_str in valid_states:
        return state_str
    
    # Comprehensive OCR error corrections (especially for IL)
    ocr_corrections = {
        # Illinois - most commonly misread
        '1L': 'IL',   # "I" misread as "1"
        'I1': 'IL',   # "L" misread as "1"
        '|L': 'IL',   # "I" misread as "|"
        '|1': 'IL',   # Both misread
        '1l': 'IL',   # Lowercase
        'i1': 'IL',   # Lowercase
        '|l': 'IL',   # Lowercase
        '1|': 'IL',   # Alternative
        '|I': 'IL',   # Alternative
        'IL.': 'IL',  # Extra period
        'IL,': 'IL',  # Extra comma
        # Other common misreadings
        'N1': 'NY',   # New York - "Y" misread as "1"
        'NY.': 'NY',  # Extra period
        'C4': 'CA',   # California - "A" misread as "4"
        'CA.': 'CA',  # Extra period
        'P4': 'PA',   # Pennsylvania - "A" misread as "4"
        'PA.': 'PA',  # Extra period
        'F1': 'FL',   # Florida - "L" misread as "1"
        'FL.': 'FL',  # Extra period
        '0H': 'OH',   # Ohio - "O" misread as "0"
        'OH.': 'OH',  # Extra period
        'M1': 'MI',   # Michigan - "I" misread as "1"
        'MI.': 'MI',  # Extra period
        'TX.': 'TX',  # Texas - extra period
        'TX,': 'TX',  # Extra comma
    }
    
    # Try direct OCR correction
    if state_str in ocr_corrections:
        return ocr_corrections[state_str]
    
    # Try pattern matching for common OCR errors (only if exactly 2 chars)
    if len(state_str) == 2:
        # Replace common OCR misreadings: 1→I, |→I, 0→O
        corrected = state_str.replace('1', 'I').replace('|', 'I').replace('0', 'O')
        if corrected in valid_states:
            return corrected
        
        # Try reverse: if it looks like IL but with swapped characters
        # e.g., "L1" might be "IL" with characters swapped
        if state_str[0] == 'L' and state_str[1] in '1I|':
            # Could be IL with first char misread
            if 'I' + state_str[1].replace('1', 'I').replace('|', 'I') in valid_states:
                return 'IL'
        
        # Try if first char is 1/| and second is L
        if state_str[0] in '1|' and state_str[1] == 'L':
            return 'IL'
        
        # Try if first char is I and second is 1/|
        if state_str[0] == 'I' and state_str[1] in '1|':
            return 'IL'
    
    return ""


def _parse_row_as_employee(texts: List[str]) -> Optional[Dict]:
    """
    Parse a row of OCR texts into an employee record.
    
    Expected columns (approximately):
    NAME | LICENSE # | STATE | DOB | POSITION | STATUS | PERSONAL USE
    """
    if len(texts) < 2:
        return None
    
    record = {
        'name': '',
        'dob': '',
        'license': '',
        'state': '',
        'position': '',
        'status': '',
        'personal_use': '',
        'raw': ' | '.join(texts)
    }
    
    # First text is usually the name (if it has letters and is long enough)
    first = texts[0]
    if len(first) >= 3 and any(c.isalpha() for c in first):
        record['name'] = first
    else:
        return None  # Not a valid employee row
    
    # Look for patterns in remaining texts
    # Process in priority order: DOB first (most reliable), then state, then license
    for text in texts[1:]:
        text_clean = text.strip().rstrip('_').rstrip()
        text_upper = text_clean.upper()
        
        # Date pattern (DOB) - try multiple formats (highest priority)
        if re.search(r'\d[/\-]\d', text_clean) or re.search(r'\d{3,4}/\d{3,4}', text_clean):
            print(f"[DEBUG] Found potential date: '{text_clean}'")
            normalized_dob = _normalize_date(text_clean)
            print(f"[DEBUG] Normalized date '{text_clean}' to '{normalized_dob}'")
            if normalized_dob and not record['dob']:
                record['dob'] = normalized_dob
                print(f"[DEBUG] Set DOB to: {normalized_dob}")
                continue  # Skip other checks for this text
        
        # State code detection - improved to catch IL and other states
        if not record['state']:
            # First, try exact 2-character match
            if len(text_clean) == 2:
                print(f"[DEBUG] Checking 2-char text for state: '{text_clean}'")
                normalized_state = _normalize_state(text_clean)
                print(f"[DEBUG] Normalized '{text_clean}' to '{normalized_state}'")
                if normalized_state:
                    print(f"[DEBUG] Found state via exact match: {normalized_state}")
                    record['state'] = normalized_state
                    continue  # Found state, skip other checks for this text
            
            # If not found, check if text contains a state code pattern
            # Look for 2-character codes that could be states (including OCR errors)
            # Pattern: exactly 2 chars of letters, numbers, or | (common OCR error)
            state_match = re.search(r'\b([A-Z0-9|]{2})\b', text_upper)
            if state_match:
                potential_state = state_match.group(1)
                print(f"[DEBUG] Found potential state in text '{text_clean}': '{potential_state}'")
                normalized_state = _normalize_state(potential_state)
                print(f"[DEBUG] Normalized '{potential_state}' to '{normalized_state}'")
                if normalized_state:
                    print(f"[DEBUG] Found state via pattern match: {normalized_state}")
                    record['state'] = normalized_state
                    continue  # Found state, skip other checks for this text
        
        # License number (alphanumeric, 5+ chars, not a date)
        if not record['license'] and len(text_clean) >= 5 and re.match(r'^[A-Z0-9]+$', text_upper) and not re.search(r'\d[/\-]\d', text_clean):
            record['license'] = text_clean
        # FT/PT status
        elif not record['status'] and text_upper in ['FT', 'PT', 'FULL', 'PART']:
            record['status'] = 'FT' if 'F' in text_upper else 'PT'
        # Personal use Y/N
        elif not record['personal_use'] and text_upper in ['Y', 'N', 'YES', 'NO']:
            record['personal_use'] = 'Y' if text_upper.startswith('Y') else 'N'
        # Position (common job titles)
        elif not record['position'] and text_upper in ['OWNER', 'SALES', 'MANAGER', 'DRIVER', 'MECHANIC', 'MEC', 'OFFICE', 'ADMIN', 'BROTHER']:
            record['position'] = text_clean
        # Other text might be position or relationship
        elif not record['position'] and len(text_clean) >= 3 and any(c.isalpha() for c in text_clean):
            record['position'] = text_clean
    
    # FALLBACK: If no state found yet, search the entire row text for any valid 2-letter state code
    # This is the same approach MVR Runner uses - catches cases where "IL" appears but wasn't matched above
    if not record['state']:
        # Combine all texts into a single string for searching
        row_text = ' '.join([t.strip() for t in texts])
        
        # Apply state corrections to the entire row text FIRST (same as OllamaTool's _clean_ocr_text)
        # This fixes OCR errors like "1L" → "IL" globally before searching
        row_text_corrected = _apply_state_corrections_to_text(row_text)
        row_text_upper = row_text_corrected.upper()
        
        # DEBUG: Print what we're searching
        print(f"[DEBUG] State fallback - original row text: {row_text}")
        print(f"[DEBUG] State fallback - corrected row text: {row_text_corrected}")
        
        # Find all 2-letter codes in the corrected row text
        all_two_letter_codes = re.findall(r'\b([A-Z0-9|]{2})\b', row_text_upper)
        print(f"[DEBUG] Found 2-letter codes: {all_two_letter_codes}")
        
        # Valid US state codes
        valid_states = ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY']
        
        # Check each 2-letter code
        for code in all_two_letter_codes:
            # Normalize the code (handles any remaining OCR errors)
            normalized_code = _normalize_state(code)
            print(f"[DEBUG] Code '{code}' normalized to '{normalized_code}'")
            if normalized_code and normalized_code in valid_states:
                print(f"[DEBUG] Found valid state: {normalized_code}")
                record['state'] = normalized_code
                break  # Found a valid state, stop searching
        else:
            print(f"[DEBUG] No valid state found in codes: {all_two_letter_codes}")
    
    return record


def build_tab(parent):
    """
    Create the Dealer Application Reader tab.
    """
    outer = ttk.Frame(parent)
    
    # Check dependencies
    missing = []
    if not _PYMUPDF_AVAILABLE:
        missing.append("PyMuPDF (fitz)")
    if not _PIL_AVAILABLE:
        missing.append("Pillow (PIL)")
    if not _TESSERACT_AVAILABLE and not _EASYOCR_AVAILABLE:
        missing.append("pytesseract or easyocr")
    
    if missing:
        error_frame = ttk.Frame(outer)
        error_frame.pack(fill="both", expand=True, padx=20, pady=20)
        ttk.Label(error_frame, text="Missing Dependencies", font=("Segoe UI", 12, "bold")).pack(pady=10)
        ttk.Label(error_frame, text=f"Please install: {', '.join(missing)}").pack(pady=5)
        return outer
    
    # ==================== UI ====================
    
    # Title
    title_frame = ttk.Frame(outer)
    title_frame.pack(fill="x", padx=10, pady=5)
    ttk.Label(title_frame, text="Dealer Application Reader", font=("Segoe UI", 14, "bold")).pack(side="left")
    ttk.Label(title_frame, text="Extract employee data from page 2", font=("Segoe UI", 9)).pack(side="left", padx=10)
    
    # File selection
    file_frame = ttk.LabelFrame(outer, text="1. Select Dealer Application PDF")
    file_frame.pack(fill="x", padx=10, pady=5)
    
    file_path_var = tk.StringVar()
    file_entry = ttk.Entry(file_frame, textvariable=file_path_var, state="readonly")
    file_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
    
    # Results display
    results_frame = ttk.LabelFrame(outer, text="2. Extracted Employee Data")
    results_frame.pack(fill="both", expand=True, padx=10, pady=5)
    
    # Create text widget for results
    results_text = tk.Text(results_frame, wrap="word", font=("Consolas", 10))
    results_scroll = ttk.Scrollbar(results_frame, orient="vertical", command=results_text.yview)
    results_text.configure(yscrollcommand=results_scroll.set)
    results_scroll.pack(side="right", fill="y")
    results_text.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Status bar
    status_var = tk.StringVar(value="Ready - Drop a PDF or click Browse")
    status_label = ttk.Label(outer, textvariable=status_var, relief="sunken", anchor="w")
    status_label.pack(fill="x", side="bottom", padx=10, pady=5)
    
    # Processing state
    processing = False
    extracted_data = None  # Store extracted data for export
    
    def update_status(msg: str):
        status_var.set(msg)
        outer.update_idletasks()
    
    def display_results(data: Dict):
        nonlocal extracted_data
        extracted_data = data  # Store for export
        """Display extracted employee data."""
        results_text.config(state="normal")
        results_text.delete("1.0", "end")
        
        # Header
        results_text.insert("end", "=" * 60 + "\n")
        results_text.insert("end", "EXTRACTED EMPLOYEE DATA\n")
        results_text.insert("end", "=" * 60 + "\n\n")
        
        # Business Personnel
        results_text.insert("end", "--- BUSINESS PERSONNEL ---\n")
        results_text.insert("end", "(Owners, Officers, Employees, Drivers, Contractors)\n\n")
        
        if data['business_personnel']:
            for i, emp in enumerate(data['business_personnel'], 1):
                results_text.insert("end", f"Employee {i}:\n")
                results_text.insert("end", f"  Name:     {emp.get('name', 'N/A')}\n")
                results_text.insert("end", f"  DOB:      {emp.get('dob', 'N/A')}\n")
                results_text.insert("end", f"  License:  {emp.get('license', 'N/A')}\n")
                results_text.insert("end", f"  State:    {emp.get('state', 'N/A')}\n")
                results_text.insert("end", f"  Position: {emp.get('position', 'N/A')}\n")
                results_text.insert("end", f"  Status:   {emp.get('status', 'N/A')}\n")
                results_text.insert("end", f"  Personal Use: {emp.get('personal_use', 'N/A')}\n")
                results_text.insert("end", f"  [Raw: {emp.get('raw', '')}]\n\n")
        else:
            results_text.insert("end", "  No employees found.\n\n")
        
        # Non-Business Personnel
        results_text.insert("end", "--- NON-BUSINESS PERSONNEL ---\n")
        results_text.insert("end", "(Spouses, Family Members, Children 14-25)\n\n")
        
        if data['non_business_personnel']:
            for i, person in enumerate(data['non_business_personnel'], 1):
                results_text.insert("end", f"Family Member {i}:\n")
                results_text.insert("end", f"  Name:     {person.get('name', 'N/A')}\n")
                results_text.insert("end", f"  DOB:      {person.get('dob', 'N/A')}\n")
                results_text.insert("end", f"  License:  {person.get('license', 'N/A')}\n")
                results_text.insert("end", f"  State:    {person.get('state', 'N/A')}\n")
                results_text.insert("end", f"  Relationship: {person.get('position', 'N/A')}\n")
                results_text.insert("end", f"  [Raw: {person.get('raw', '')}]\n\n")
        else:
            results_text.insert("end", "  No family members found.\n\n")
        
        # Summary
        total = len(data['business_personnel']) + len(data['non_business_personnel'])
        results_text.insert("end", "=" * 60 + "\n")
        results_text.insert("end", f"TOTAL: {len(data['business_personnel'])} employees + {len(data['non_business_personnel'])} family = {total} people\n")
        results_text.insert("end", "=" * 60 + "\n")
        
        results_text.config(state="disabled")
    
    def process_pdf(file_path: str):
        """Process a dealer application PDF."""
        nonlocal processing
        
        if processing:
            return
        processing = True
        
        def worker():
            nonlocal processing
            try:
                # Check if file exists
                if not os.path.isfile(file_path):
                    outer.after(0, lambda: messagebox.showerror("File Not Found", f"The file does not exist:\n{file_path}"))
                    update_status("Error: File not found")
                    processing = False
                    return
                
                update_status("Finding employee table page...")
                
                # Find the page with employee tables
                page_num = _find_employee_table_page(file_path)
                if page_num is None:
                    outer.after(0, lambda: messagebox.showwarning("Page Not Found", "Could not find employee tables in PDF.\nTrying page 2 by default..."))
                    # Try page 2 (index 1) as fallback
                    try:
                        doc = fitz.open(file_path)
                        if len(doc) >= 2:
                            page_num = 1
                        doc.close()
                    except:
                        pass
                    
                    if page_num is None:
                        update_status("Error: Could not find employee tables and PDF has less than 2 pages")
                        processing = False
                        return
                
                update_status(f"OCR scanning page {page_num + 1}...")
                
                # Check OCR availability
                if not _TESSERACT_AVAILABLE and not _EASYOCR_AVAILABLE:
                    outer.after(0, lambda: messagebox.showerror("OCR Not Available", "Neither Tesseract nor EasyOCR is installed.\nPlease install one:\npip install pytesseract\nOR\npip install easyocr"))
                    update_status("Error: No OCR engine available")
                    processing = False
                    return
                
                # OCR the page
                ocr_items = _ocr_page(file_path, page_num)
                if not ocr_items:
                    outer.after(0, lambda: messagebox.showwarning("OCR Failed", "OCR did not extract any text from the page.\nThe page might be blank, corrupted, or the image quality is too low."))
                    update_status("Error: OCR failed - no text extracted")
                    processing = False
                    return
                
                update_status(f"Parsing {len(ocr_items)} text items...")
                
                # Parse into employee records
                data = _parse_employee_tables(ocr_items)
                
                # Display results
                outer.after(0, lambda: display_results(data))
                
                total = len(data['business_personnel']) + len(data['non_business_personnel'])
                if total == 0:
                    outer.after(0, lambda: messagebox.showinfo("No Employees Found", "The page was scanned but no employee data was found.\nThe table format might be different than expected."))
                    update_status("Warning: No employees found in extracted text")
                else:
                    update_status(f"Done! Found {total} people on page {page_num + 1}")
                
            except Exception as e:
                import traceback
                error_msg = str(e)
                error_details = traceback.format_exc()
                print(f"Extraction error: {error_msg}\n{error_details}")
                outer.after(0, lambda: messagebox.showerror("Extraction Error", f"An error occurred during extraction:\n\n{error_msg}\n\nCheck console for details."))
                update_status(f"Error: {error_msg}")
            finally:
                processing = False
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
    
    def browse_file():
        file_path = filedialog.askopenfilename(
            title="Select Dealer Application PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if file_path:
            file_path_var.set(file_path)
            process_pdf(file_path)
    
    def handle_drop(event):
        """Handle drag-and-drop file."""
        file_path = event.data
        # Clean up path (remove braces on some systems)
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]
        file_path = file_path.strip()
        
        if file_path.lower().endswith('.pdf'):
            file_path_var.set(file_path)
            process_pdf(file_path)
        else:
            messagebox.showwarning("Invalid File", "Please drop a PDF file.")
    
    # Buttons
    btn_frame = ttk.Frame(file_frame)
    btn_frame.pack(side="right", padx=5)
    
    browse_btn = ttk.Button(btn_frame, text="Browse...", command=browse_file)
    browse_btn.pack(side="left", padx=2)
    
    extract_btn = ttk.Button(btn_frame, text="Extract", command=lambda: process_pdf(file_path_var.get()) if file_path_var.get() else messagebox.showwarning("No File", "Please select a PDF file first."))
    extract_btn.pack(side="left", padx=2)
    
    def export_to_mvr():
        """Export extracted employee data to MVR Runner."""
        nonlocal extracted_data
        
        if not extracted_data:
            messagebox.showwarning("No Data", "Please extract employee data first.")
            return
        
        # Try to get MVR Runner callback (same method as OllamaTool)
        callback = None
        try:
            from Tabs import MvrRunner
            callback = getattr(MvrRunner, '_add_mvr_entry_callback', None)
        except (ImportError, AttributeError):
            try:
                import importlib
                mvr_module = importlib.import_module('Tabs.MvrRunner')
                callback = getattr(mvr_module, '_add_mvr_entry_callback', None)
            except Exception:
                pass
        
        if not callback:
            messagebox.showerror("MVR Runner Not Available", "Could not connect to MVR Runner. Make sure the MVR Runner tab is loaded.")
            return
        
        # Export all business personnel
        imported = 0
        skipped = 0
        
        for emp in extracted_data.get('business_personnel', []):
            # Parse name (first word = first name, last word = last name)
            name_parts = emp.get('name', '').strip().split()
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[-1] if len(name_parts) > 1 else ''
            
            mvr_data = {
                'first_name': first_name,
                'last_name': last_name,
                'license_number': emp.get('license', ''),
                'state': emp.get('state', ''),
                'dob': emp.get('dob', ''),
                'status': emp.get('status', ''),
                'personal_use': emp.get('personal_use', ''),
                'extracted_text': f"Dealer Application Reader\nName: {emp.get('name')}\nLicense: {emp.get('license')}\nState: {emp.get('state')}\nDOB: {emp.get('dob')}"
            }
            
            try:
                success, message = callback(mvr_data, source="Dealer App Reader")
                if success:
                    imported += 1
                else:
                    skipped += 1
            except Exception as e:
                skipped += 1
        
        # Show results
        if imported > 0:
            messagebox.showinfo("Export Complete", f"Successfully exported {imported} employee(s) to MVR Runner.\n{skipped} skipped (duplicates or errors).")
        else:
            messagebox.showwarning("Export Failed", f"No employees exported. {skipped} skipped (may be duplicates or missing required fields).")
    
    export_btn = ttk.Button(btn_frame, text="Export to MVR", command=export_to_mvr)
    export_btn.pack(side="left", padx=2)
    
    # Enable drag-and-drop if available
    if _DND_AVAILABLE and DND_FILES:
        try:
            outer.drop_target_register(DND_FILES)
            outer.dnd_bind('<<Drop>>', handle_drop)
            file_entry.drop_target_register(DND_FILES)
            file_entry.dnd_bind('<<Drop>>', handle_drop)
        except Exception:
            pass
    
    return outer

