# Simple Organization Steps

## What We're Doing
Organize files into folders so it's easier to find things.

## The Steps

### Step 1: Create These Folders
```
docs/      - Documentation files
config/    - Settings files  
scripts/   - Launcher scripts
tests/     - Test/debug files
data/      - Sample files and output
legacy/    - Old unused code
```

### Step 2: Move Files

**Documentation → `docs/`**
- `WINDOWS_INSTALLATION_GUIDE.md` → `docs/INSTALLATION.md`

**Settings → `config/`**
- `ollama_settings.json`
- `mvr_ui_settings.json`
- `ui_settings.json`

**Scripts → `scripts/`**
- `run_dmi_tool.bat`
- `run_dmi_tool.ps1`
- `setup_git.ps1`

**Tests → `tests/`**
- `test_easyocr.py`
- `debug_checkboxes.py` → `tests/test_checkboxes.py`
- `minimal_reproducible_example.py`
- `main.py` (it's an example script, not the main app)

**Data → `data/`**
- `Bindocs_output/` → `data/output/`
- `Cache/` → `data/cache/`

**Old Code → `legacy/`**
- `profile_binding.py` (not used anywhere)
- `Reader` (might be used, need to check)

### Step 3: Update Code
Change file paths in code to point to new locations.

### Step 4: Keep at Root
These stay where they are:
- `mainApp.pyw` (main application)
- `README.md`
- `requirements.txt`
- `Tabs/` (all tabs)
- `Bindocs/` (sample PDFs - or move to `data/samples/`)

## Summary
1. Create folders
2. Move files
3. Update paths in code
4. Test everything works

## Questions
1. Move `Bindocs/` to `data/samples/` or keep at root?
2. Is `Reader` file still used? (checking...)

