#!/usr/bin/env python3
"""
Quick test script to see what EasyOCR extracts from an image
Usage: python test_easyocr.py <image_path>
"""
import sys
import os

try:
    import easyocr
    from PIL import Image
    import numpy as np
except ImportError as e:
    print(f"Error: Missing required library: {e}")
    print("Please install: pip install easyocr pillow numpy")
    sys.exit(1)

def test_easyocr(image_path):
    """Test what EasyOCR extracts from an image"""
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        return
    
    print(f"Loading image: {image_path}")
    print("Initializing EasyOCR reader...")
    
    # Initialize EasyOCR reader
    reader = easyocr.Reader(['en'], gpu=False)
    
    # Load image
    img = Image.open(image_path)
    img_array = np.array(img)
    
    print("Running EasyOCR...")
    print("-" * 60)
    
    # Run OCR
    results = reader.readtext(img_array)
    
    print(f"EasyOCR found {len(results)} text detections:")
    print("-" * 60)
    
    for idx, (bbox, text, confidence) in enumerate(results, 1):
        print(f"\nDetection {idx}:")
        print(f"  Text: '{text}'")
        print(f"  Confidence: {confidence:.2%}")
        print(f"  Bounding box: {bbox}")
    
    print("\n" + "-" * 60)
    print("Full extracted text (all detections combined):")
    print("-" * 60)
    all_text = " ".join([text for _, text, _ in results])
    print(all_text)
    
    print("\n" + "-" * 60)
    print("Text with line breaks (preserving structure):")
    print("-" * 60)
    # Try to preserve some structure by grouping nearby detections
    lines = []
    current_line = []
    last_y = None
    
    # Sort by Y coordinate (top to bottom)
    sorted_results = sorted(results, key=lambda x: sum([p[1] for p in x[0]]) / len(x[0]))
    
    for bbox, text, confidence in sorted_results:
        avg_y = sum([p[1] for p in bbox]) / len(bbox)
        if last_y is None or abs(avg_y - last_y) < 20:  # Same line if Y is close
            current_line.append(text)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [text]
        last_y = avg_y
    
    if current_line:
        lines.append(" ".join(current_line))
    
    for line in lines:
        print(line)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_easyocr.py <image_path>")
        print("\nExample:")
        print("  python test_easyocr.py screenshot.png")
        print("  python test_easyocr.py C:\\Users\\Gamer\\Desktop\\table.png")
        sys.exit(1)
    
    image_path = sys.argv[1]
    test_easyocr(image_path)

