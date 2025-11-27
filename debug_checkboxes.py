#!/usr/bin/env python3
"""
Debug script to test checkbox detection on a PDF.
Usage: python debug_checkboxes.py /path/to/your.pdf
"""
import sys
import os
import cv2
import numpy as np

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Tabs.MvrRunner.shared import _detect_checkboxes_in_pdf, _detect_checkboxes_in_rightmost_columns
import fitz

def analyze_all_contours(pdf_path: str):
    """Analyze ALL contours in the PDF to see what shapes exist"""
    print("\nTEST 0: Analyzing ALL shapes in PDF...")
    print("-" * 40)
    
    doc = fitz.open(pdf_path)
    page = doc[0]
    
    dpi = 200
    pix = page.get_pixmap(dpi=dpi)
    img_data = pix.tobytes("png")
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    doc.close()
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Try different thresholds
    for thresh_val in [127, 150, 180, 200, 220]:
        _, thresh = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        # Count contours by size
        sizes = {'tiny (<10)': 0, 'small (10-30)': 0, 'medium (30-60)': 0, 'large (60-100)': 0, 'huge (>100)': 0}
        square_like = 0
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w < 10:
                sizes['tiny (<10)'] += 1
            elif w < 30:
                sizes['small (10-30)'] += 1
            elif w < 60:
                sizes['medium (30-60)'] += 1
            elif w < 100:
                sizes['large (60-100)'] += 1
            else:
                sizes['huge (>100)'] += 1
            
            # Check if square-ish
            if w > 5 and h > 5:
                aspect = w / float(h)
                if 0.7 < aspect < 1.4:
                    square_like += 1
        
        print(f"  Threshold {thresh_val}: {len(contours)} contours, {square_like} square-ish")
        print(f"    Sizes: {sizes}")
    
    # Save debug image with potential checkboxes highlighted
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    debug_img = img.copy()
    checkbox_candidates = []
    
    scale = dpi / 72.0
    min_size = int(8 * scale)  # More lenient
    max_size = int(50 * scale)
    
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / float(h) if h > 0 else 0
        
        if min_size < w < max_size and min_size < h < max_size and 0.6 < aspect < 1.6:
            checkbox_candidates.append((x, y, w, h))
            cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
    
    print(f"\n  Potential checkbox candidates (lenient): {len(checkbox_candidates)}")
    if checkbox_candidates:
        print(f"  First 10:")
        for i, (x, y, w, h) in enumerate(checkbox_candidates[:10]):
            print(f"    #{i+1}: pos=({x},{y}), size={w}x{h}")
    
    # Save debug image
    debug_path = "checkbox_debug.png"
    cv2.imwrite(debug_path, debug_img)
    print(f"\n  Debug image saved to: {debug_path}")
    print(f"  (Green rectangles = potential checkbox candidates)")

def debug_checkbox_detection(pdf_path: str):
    print(f"\n{'='*60}")
    print(f"CHECKBOX DETECTION DEBUG")
    print(f"PDF: {pdf_path}")
    print(f"{'='*60}\n")
    
    if not os.path.exists(pdf_path):
        print(f"ERROR: File not found: {pdf_path}")
        return
    
    # Test 0: Analyze all shapes
    try:
        analyze_all_contours(pdf_path)
    except Exception as e:
        print(f"Shape analysis error: {e}")
    
    # Test 1: Full page detection
    print("TEST 1: Detecting ALL checkboxes on full page...")
    print("-" * 40)
    try:
        all_checkboxes = _detect_checkboxes_in_pdf(pdf_path, page_num=0, region=None)
        print(f"Found {len(all_checkboxes)} checkbox candidates on full page")
        
        if all_checkboxes:
            print("\nCheckbox details:")
            for i, cb in enumerate(all_checkboxes):
                status = "CHECKED" if cb.get('checked', False) else "UNCHECKED"
                print(f"  #{i+1}: x={cb['x']}, y={cb['y']}, size={cb.get('w', '?')}x{cb.get('h', '?')}, "
                      f"fill={cb.get('fill_ratio', 0):.1%}, {status}")
        else:
            print("  No checkboxes found!")
            print("\n  Possible issues:")
            print("  - Checkboxes might be too small (< 15px) or too large (> 60px)")
            print("  - Checkboxes might not be square-ish (aspect ratio issue)")
            print("  - PDF might be low resolution")
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test 2: Rightmost columns detection
    print("\n" + "-" * 40)
    print("TEST 2: Detecting checkboxes in RIGHTMOST COLUMNS...")
    print("-" * 40)
    try:
        rightmost_rows = _detect_checkboxes_in_rightmost_columns(pdf_path, page_num=0, num_columns=2)
        print(f"Found {len(rightmost_rows)} rows with checkboxes in rightmost columns")
        
        if rightmost_rows:
            print("\nRow details:")
            for row_idx, row in enumerate(rightmost_rows):
                print(f"  Row {row_idx + 1}: {len(row)} checkbox(es)")
                for cb in row:
                    status = "CHECKED" if cb.get('checked', False) else "UNCHECKED"
                    print(f"    - x={cb['x']}, y={cb['y']}, fill={cb.get('fill_ratio', 0):.1%}, {status}")
        else:
            print("  No checkboxes found in rightmost columns!")
            print("\n  Possible issues:")
            print("  - Checkboxes might not be in the right 30% of the page")
            print("  - Try full page scan (TEST 1) to see where they are")
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Test 3: Get PDF dimensions
    print("\n" + "-" * 40)
    print("TEST 3: PDF page info...")
    print("-" * 40)
    try:
        import fitz
        doc = fitz.open(pdf_path)
        page = doc[0]
        print(f"Page size: {page.rect.width:.0f} x {page.rect.height:.0f} points")
        print(f"At 150 DPI: {page.rect.width * 150 / 72:.0f} x {page.rect.height * 150 / 72:.0f} pixels")
        
        # Check if page has text
        text = page.get_text()
        print(f"Text content: {len(text)} characters")
        doc.close()
    except Exception as e:
        print(f"ERROR: {e}")
    
    print(f"\n{'='*60}")
    print("DEBUG COMPLETE")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_checkboxes.py /path/to/your.pdf")
        print("\nLooking for PDFs in current directory...")
        pdfs = [f for f in os.listdir('.') if f.lower().endswith('.pdf')]
        if pdfs:
            print(f"Found: {pdfs}")
        sys.exit(1)
    
    debug_checkbox_detection(sys.argv[1])

