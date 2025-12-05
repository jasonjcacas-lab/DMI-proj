# DMI Project Organization Plan

## Current State Analysis

### Root Directory Issues
- **Mixed concerns**: Configuration files, scripts, test files, and documentation all at root
- **Unclear structure**: Hard to find specific functionality
- **Test/debug files**: `debug_checkboxes.py`, `test_easyocr.py`, `minimal_reproducible_example.py` at root
- **Legacy files**: `legacy_form_helpers.py`, `profile_binding.py`, `Reader` (unclear purpose)
- **Multiple entry points**: `main.py`, `mainApp.pyw` (unclear which is primary)

### Proposed Organization Structure

```
DMI-proj/
├── README.md                          # Main project documentation
├── requirements.txt                   # Python dependencies
├── .gitignore                         # Git ignore rules
│
├── docs/                              # 📚 Documentation
│   ├── INSTALLATION.md                # Installation guide
│   ├── USER_GUIDE.md                  # User manual
│   ├── DEVELOPER_GUIDE.md             # Developer documentation
│   └── ARCHITECTURE.md                # System architecture
│
├── src/                               # 🎯 Source Code (or keep root)
│   ├── mainApp.pyw                    # Main application entry point
│   ├── Tabs/                          # Application tabs/modules
│   │   ├── Splitter/                  # Binder Splitter
│   │   ├── MvrRunner/                 # MVR Runner
│   │   ├── OllamaTool/                # Ollama AI Tool (refactored)
│   │   ├── DealerAppReader/           # Dealer App Reader
│   │   └── FutureTool/                # Future tool (or remove)
│   └── utils/                         # Shared utilities
│       ├── __init__.py
│       └── helpers.py                 # Common helper functions
│
├── config/                            # ⚙️ Configuration Files
│   ├── ollama_settings.json
│   ├── mvr_ui_settings.json
│   └── ui_settings.json
│
├── scripts/                           # 🔧 Utility Scripts
│   ├── run_dmi_tool.bat              # Windows batch launcher
│   ├── run_dmi_tool.ps1               # PowerShell launcher
│   └── setup_git.ps1                  # Git setup script
│
├── tests/                             # 🧪 Test Files
│   ├── test_easyocr.py
│   ├── test_checkboxes.py             # Renamed from debug_checkboxes.py
│   └── minimal_reproducible_example.py
│
├── installers/                        # 💿 Installer Files (keep as-is)
│   └── [installer files]
│
├── data/                              # 📁 Data & Sample Files
│   ├── samples/                       # Sample PDFs for testing
│   │   └── [sample PDFs]
│   ├── output/                        # Generated output
│   │   └── Bindocs_output/
│   └── cache/                         # Cache directory
│       ├── ocr/
│       └── templates/
│
├── legacy/                            # 🗄️ Legacy/Deprecated Code
│   ├── legacy_form_helpers.py
│   ├── profile_binding.py
│   └── Reader                         # If deprecated
│
└── other_files/                       # 📄 Other Files (keep as-is or move)
    └── [various PDFs and documents]
```

## Detailed Organization Plan

### 1. Documentation (`docs/`)
**Purpose**: Centralized documentation
- Move `WINDOWS_INSTALLATION_GUIDE.md` → `docs/INSTALLATION.md`
- Create `docs/USER_GUIDE.md` for end-user documentation
- Create `docs/DEVELOPER_GUIDE.md` for development setup
- Create `docs/ARCHITECTURE.md` for system design

### 2. Source Code Organization
**Current**: Mixed at root
**Proposed**: 
- Keep `mainApp.pyw` at root (primary entry point)
- Keep `Tabs/` at root (or move to `src/Tabs/` if we create `src/`)
- Create `utils/` for shared utilities if needed

### 3. Configuration Files (`config/`)
**Purpose**: Centralized configuration
- Move `ollama_settings.json` → `config/`
- Move `mvr_ui_settings.json` → `config/`
- Move `ui_settings.json` → `config/`
- Update code to reference new paths

### 4. Scripts (`scripts/`)
**Purpose**: Utility and launcher scripts
- Move `run_dmi_tool.bat` → `scripts/`
- Move `run_dmi_tool.ps1` → `scripts/`
- Move `setup_git.ps1` → `scripts/`
- Update shortcuts/aliases if needed

### 5. Tests (`tests/`)
**Purpose**: Test files and debugging utilities
- Move `test_easyocr.py` → `tests/`
- Move `debug_checkboxes.py` → `tests/test_checkboxes.py`
- Move `minimal_reproducible_example.py` → `tests/`
- Create `tests/__init__.py` for test package

### 6. Data (`data/`)
**Purpose**: Sample files, output, and cache
- Move `Bindocs_output/` → `data/output/`
- Move `Cache/` → `data/cache/`
- Optionally move sample PDFs to `data/samples/`
- Keep `Bindocs/` at root or move to `data/samples/`

### 7. Legacy (`legacy/`)
**Purpose**: Deprecated code (keep for reference)
- Move `legacy_form_helpers.py` → `legacy/`
- Move `profile_binding.py` → `legacy/` (if deprecated)
- Move `Reader` → `legacy/` (if deprecated)
- Add README explaining what's deprecated

### 8. Root Directory Cleanup
**Keep at root**:
- `mainApp.pyw` (primary entry point)
- `README.md`
- `requirements.txt`
- `.gitignore`
- `DMI Tool.pyproj` (if still used)

**Remove or move**:
- `main.py` (if duplicate of mainApp.pyw)
- Test/debug files → `tests/`
- Config files → `config/`
- Scripts → `scripts/`

## Migration Strategy

### Phase 1: Create New Structure
1. Create new directories
2. Move files to new locations
3. Update imports and paths in code
4. Test that everything still works

### Phase 2: Update References
1. Update all file paths in code
2. Update documentation
3. Update scripts/launchers
4. Update `.gitignore` if needed

### Phase 3: Cleanup
1. Remove empty directories
2. Update README with new structure
3. Verify all functionality works

## Benefits

1. **Clarity**: Easy to find files by purpose
2. **Maintainability**: Related files grouped together
3. **Scalability**: Easy to add new features
4. **Professional**: Standard project structure
5. **Documentation**: Centralized docs location

## Considerations

- **Backward Compatibility**: Ensure existing shortcuts/scripts still work
- **Git History**: Consider using `git mv` to preserve history
- **Dependencies**: Update any hardcoded paths
- **Testing**: Test thoroughly after reorganization

## Questions to Resolve

1. Should we create a `src/` directory or keep code at root?
2. Is `main.py` still needed or can it be removed?
3. What is the purpose of `Reader` file? Is it deprecated?
4. Should `Bindocs/` stay at root or move to `data/samples/`?
5. Are there any external dependencies on current file locations?

