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
        
        # Use Tesseract (faster)
        if _TESSERACT_AVAILABLE:
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
        
        return results
        
    except Exception as e:
        print(f"OCR error: {e}")
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
        
        # Try to parse as employee record
        record = _parse_row_as_employee(texts)
        if record:
            # Determine which section this belongs to
            if non_business_header_y and y > non_business_header_y:
                result['non_business_personnel'].append(record)
            elif business_header_y and y > business_header_y:
                result['business_personnel'].append(record)
    
    return result


def _parse_row_as_employee(texts: List[str]) -> Optional[Dict]:
    """
    Parse a row of OCR texts into an employee record.
    
    Expected columns (approximately):
    NAME | DOB | LICENSE # | STATE | POSITION | FT/PT | PERSONAL USE | YRS EXP
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
    for text in texts[1:]:
        text_clean = text.strip()
        text_upper = text_clean.upper()
        
        # Date pattern (DOB)
        if re.match(r'\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}', text_clean):
            record['dob'] = text_clean
        # State code (2 letters)
        elif re.match(r'^[A-Z]{2}$', text_upper) and text_upper in ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY']:
            record['state'] = text_upper
        # License number (alphanumeric, 5+ chars)
        elif len(text_clean) >= 5 and re.match(r'^[A-Z0-9]+$', text_upper):
            record['license'] = text_clean
        # FT/PT status
        elif text_upper in ['FT', 'PT', 'FULL', 'PART']:
            record['status'] = 'FT' if 'F' in text_upper else 'PT'
        # Personal use Y/N
        elif text_upper in ['Y', 'N', 'YES', 'NO']:
            record['personal_use'] = 'Y' if text_upper.startswith('Y') else 'N'
        # Position (common job titles)
        elif text_upper in ['OWNER', 'SALES', 'MANAGER', 'DRIVER', 'MECHANIC', 'MEC', 'OFFICE', 'ADMIN']:
            record['position'] = text_clean
        # Other text might be position or relationship
        elif len(text_clean) >= 3 and any(c.isalpha() for c in text_clean):
            if not record['position']:
                record['position'] = text_clean
    
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
    
    def update_status(msg: str):
        status_var.set(msg)
        outer.update_idletasks()
    
    def display_results(data: Dict):
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
                update_status("Finding employee table page...")
                
                # Find the page with employee tables
                page_num = _find_employee_table_page(file_path)
                if page_num is None:
                    update_status("Error: Could not find employee tables in PDF")
                    processing = False
                    return
                
                update_status(f"OCR scanning page {page_num + 1}...")
                
                # OCR the page
                ocr_items = _ocr_page(file_path, page_num)
                if not ocr_items:
                    update_status("Error: OCR failed - no text extracted")
                    processing = False
                    return
                
                update_status(f"Parsing {len(ocr_items)} text items...")
                
                # Parse into employee records
                data = _parse_employee_tables(ocr_items)
                
                # Display results
                outer.after(0, lambda: display_results(data))
                
                total = len(data['business_personnel']) + len(data['non_business_personnel'])
                update_status(f"Done! Found {total} people on page {page_num + 1}")
                
            except Exception as e:
                update_status(f"Error: {str(e)}")
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

