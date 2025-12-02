# Windows Installation Guide for DMI Tool

This guide will help you set up the DMI Tool on a fresh Windows installation.

## Prerequisites

### 1. Python 3.8 or Higher
- **Download:** https://www.python.org/downloads/
- **Installation:**
  - Download the latest Python 3.x Windows installer
  - **IMPORTANT:** Check "Add Python to PATH" during installation
  - Choose "Install for all users" if you have admin rights
- **Verify:** Open Command Prompt and run:
  ```cmd
  python --version
  ```

### 2. Git (for cloning the repository)
- **Download:** https://git-scm.com/download/win
- **Installation:** Use default settings
- **Verify:** Open Command Prompt and run:
  ```cmd
  git --version
  ```

## System Dependencies

### 3. Tesseract OCR
- **Download:** https://github.com/UB-Mannheim/tesseract/wiki
  - Direct link: https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe
- **Installation:**
  - Run the installer
  - **IMPORTANT:** Note the installation path (usually `C:\Program Files\Tesseract-OCR`)
  - Add to PATH: Add `C:\Program Files\Tesseract-OCR` to your system PATH environment variable
- **Verify:** Open Command Prompt and run:
  ```cmd
  tesseract --version
  ```

### 4. Visual C++ Redistributable (for some Python packages)
- **Download:** https://aka.ms/vs/17/release/vc_redist.x64.exe
- **Installation:** Run the installer (required for some compiled Python packages)

## Project Setup

### 5. Clone the Repository
```cmd
cd C:\Users\YourUsername\Desktop
git clone https://github.com/yourusername/DMI-proj.git
cd DMI-proj
```

### 6. Create Virtual Environment
```cmd
python -m venv .venv
```

### 7. Activate Virtual Environment
```cmd
.venv\Scripts\activate
```
You should see `(.venv)` in your command prompt.

### 8. Install Python Dependencies
```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

**Note:** This will install:
- playwright>=1.49.0
- pymupdf>=1.24.9
- psutil>=5.9.8
- tkinterdnd2>=0.4.2
- llama-cpp-python>=0.2.0
- requests>=2.31.0
- pytesseract>=0.3.10
- easyocr>=1.7.0
- Pillow>=10.0.0
- numpy>=1.24.0
- pdfplumber>=0.10.0
- opencv-python>=4.8.0

### 9. Install Playwright Browsers
```cmd
playwright install
```
This installs Chromium, Firefox, and WebKit browsers needed for automation.

### 10. Install EasyOCR Models (First Run)
EasyOCR will automatically download models on first use, but you can pre-download:
```cmd
python -c "import easyocr; reader = easyocr.Reader(['en'], gpu=False)"
```
This may take a few minutes as it downloads the English model.

## Optional: Ollama Setup (for AI features)

### 11. Install Ollama
- **Download:** https://ollama.ai/download
- **Installation:** Run the Windows installer
- **Verify:** Open Command Prompt and run:
  ```cmd
  ollama --version
  ```

### 12. Pull Required Models
```cmd
ollama pull llama3.1
ollama pull gemma2
ollama pull phi3:mini
```

## Running the Application

### Option 1: Using the Batch File
```cmd
cd C:\Users\YourUsername\Desktop\DMI-proj
run_dmi_tool.bat
```

### Option 2: Manual Start
```cmd
cd C:\Users\YourUsername\Desktop\DMI-proj
.venv\Scripts\activate
python mainApp.pyw
```

## Troubleshooting

### Tesseract Not Found
- Ensure Tesseract is installed and in PATH
- If not in PATH, you can set it manually in the code or environment:
  ```cmd
  set TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata
  ```

### EasyOCR Installation Issues
- Ensure Visual C++ Redistributable is installed
- Try installing with: `pip install easyocr --no-cache-dir`

### Playwright Issues
- Run: `playwright install --force`
- Ensure you have internet connection for first-time browser downloads

### Import Errors
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`

### GUI Not Appearing
- Ensure tkinter is available (usually comes with Python)
- Try: `python -c "import tkinter; tkinter._test()"`

## Quick Verification Checklist

- [ ] Python 3.8+ installed and in PATH
- [ ] Git installed
- [ ] Tesseract OCR installed and in PATH
- [ ] Virtual environment created and activated
- [ ] All Python packages installed (`pip list` shows all requirements)
- [ ] Playwright browsers installed
- [ ] EasyOCR models downloaded (will happen on first use)
- [ ] Application runs without errors

## Notes

- **First Run:** The application may be slower on first launch as EasyOCR downloads models
- **Windows Defender:** May flag some Python packages; you may need to allow them
- **Firewall:** Playwright may need firewall permissions for browser automation
- **GPU:** EasyOCR can use GPU if CUDA is installed, but CPU mode works fine

## Support

If you encounter issues:
1. Check that all dependencies are installed correctly
2. Verify PATH environment variables
3. Ensure virtual environment is activated
4. Check Python version compatibility
5. Review error messages in the console

