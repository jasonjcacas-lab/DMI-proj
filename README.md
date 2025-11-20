# DMI Tool Suite

A Python-based tool suite for document processing and automation.

## Features

- **Binder Splitter**: Split and process binder documents
- **MVR Runner**: Automated MVR (Motor Vehicle Record) processing

## Setup

### Prerequisites

- Python 3.7+
- Git (for version control)

### Installation

1. Install required Python packages:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers (for automation):
```bash
playwright install
```

### Git Setup

To set up GitHub backups:

1. **Install Git** (if not already installed):
   - Download from: https://git-scm.com/download/win
   - Or install GitHub Desktop: https://desktop.github.com/

2. **Run the setup script**:
   ```powershell
   .\setup_git.ps1
   ```

3. **Configure Git user** (if not already configured):
   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "your.email@example.com"
   ```

4. **Push to GitHub**:
   ```bash
   git push -u origin main
   ```
   
   Note: You may be prompted for GitHub credentials. If you use two-factor authentication, use a Personal Access Token as your password.

## Usage

Run the main application:
```bash
python mainApp.pyw
```

Or use the command-line interface:
```bash
python main.py
```

## Project Structure

```
DMI Tool/
├── mainApp.pyw          # Main GUI application
├── main.py              # Command-line interface
├── Tabs/                # Tab modules
│   ├── Splitter.py      # Binder Splitter functionality
│   └── MvrRunner.py     # MVR Runner functionality
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Configuration

- MVR settings: `mvr_settings.json`
- UI settings: `ui_settings.json`

## License

[Add your license here]

