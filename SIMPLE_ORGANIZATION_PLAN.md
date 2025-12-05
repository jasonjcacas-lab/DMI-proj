# Simple Organization Plan

## The Problem
Right now, everything is mixed together at the root. It's hard to find things.

## The Solution
Organize files into folders by what they do.

## Step-by-Step Plan

### Step 1: Create Folders
Make these new folders:
- `docs/` - All documentation files
- `config/` - All settings files
- `scripts/` - All launcher scripts
- `tests/` - All test/debug files
- `data/` - Sample files and output
- `legacy/` - Old code we don't use anymore

### Step 2: Move Files

#### Move Documentation → `docs/`
- `WINDOWS_INSTALLATION_GUIDE.md` → `docs/INSTALLATION.md`

#### Move Settings → `config/`
- `ollama_settings.json` → `config/`
- `mvr_ui_settings.json` → `config/`
- `ui_settings.json` → `config/`

#### Move Scripts → `scripts/`
- `run_dmi_tool.bat` → `scripts/`
- `run_dmi_tool.ps1` → `scripts/`
- `setup_git.ps1` → `scripts/`

#### Move Test Files → `tests/`
- `test_easyocr.py` → `tests/`
- `debug_checkboxes.py` → `tests/test_checkboxes.py`
- `minimal_reproducible_example.py` → `tests/`

#### Move Data → `data/`
- `Bindocs_output/` → `data/output/`
- `Cache/` → `data/cache/`

#### Move Old Code → `legacy/`
- `legacy_form_helpers.py` → `legacy/`
- `profile_binding.py` → `legacy/` (if not used)
- `Reader` → `legacy/` (if not used)

### Step 3: Update Code
Update all file paths in the code to point to new locations.

### Step 4: Keep at Root
These stay at the root (main entry points):
- `mainApp.pyw` - Main application
- `README.md` - Main readme
- `requirements.txt` - Dependencies
- `Tabs/` - All application tabs

## Visual Structure

```
DMI-proj/
├── mainApp.pyw          ← Main app (stays here)
├── README.md            ← Main docs (stays here)
├── requirements.txt     ← Dependencies (stays here)
│
├── Tabs/                ← All tabs (stays here)
│   ├── Splitter/
│   ├── MvrRunner/
│   ├── OllamaTool/
│   └── DealerAppReader/
│
├── docs/                ← NEW: All documentation
│   └── INSTALLATION.md
│
├── config/              ← NEW: All settings
│   ├── ollama_settings.json
│   └── mvr_ui_settings.json
│
├── scripts/             ← NEW: All launcher scripts
│   ├── run_dmi_tool.bat
│   └── run_dmi_tool.ps1
│
├── tests/               ← NEW: All test files
│   ├── test_easyocr.py
│   └── test_checkboxes.py
│
├── data/                ← NEW: Sample files & output
│   ├── output/
│   └── cache/
│
└── legacy/              ← NEW: Old unused code
    └── legacy_form_helpers.py
```

## Benefits

1. **Easy to Find**: Know where to look for things
2. **Clean Root**: Root folder isn't cluttered
3. **Organized**: Related files are together
4. **Professional**: Standard project structure

## What We'll Do

1. Create the folders
2. Move the files
3. Update code paths
4. Test everything works
5. Update documentation

## Questions to Answer First

1. Is `main.py` still needed? (or can we remove it?)
2. Is `Reader` file still used? (or can we move to legacy?)
3. Is `profile_binding.py` still used? (or can we move to legacy?)
4. Should `Bindocs/` folder stay at root or move to `data/samples/`?

