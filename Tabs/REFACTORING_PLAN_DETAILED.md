# Detailed Refactoring Plan - Target: <1500 lines per file

## Current File Sizes
- `MvrRunner.py`: 4893 lines
- `MvrRunner_Automation.py`: 4783 lines
- `MvrRunner_CopyPaste.py`: 1861 lines

## Target Structure

### New Modules to Create:

1. **MvrRunner_BrowserUtils.py** ✅ (Created ~100 lines)
   - `_is_port_open()`
   - `_is_chrome_running()`
   - `_find_chrome_executable()`
   - `_get_chrome_user_data_dir()`

2. **MvrRunner_AutomationCore.py** (~2000 lines)
   - `_ensure_playwright_browsers_installed()`
   - `_add_stealth_script()`
   - `_launch_chrome_with_profile_for_mvr()`
   - `_launch_chrome_with_profile()`
   - `_fill_site_with_playwright()`
   - `_run_mvr_automation()` (very large ~1000+ lines)

3. **MvrRunner_UI_Dialogs.py** (~400 lines)
   - `show_site_automation_dialog()`
   - `show_login_settings_dialog()`

4. **MvrRunner_FileManager.py** (~500 lines)
   - File list management
   - Drag-drop handlers
   - File operations (add, remove, clear)
   - File data storage

5. **MvrRunner_FieldManager.py** (~600 lines)
   - Field UI components
   - Copy button functionality
   - Clipboard operations
   - DOB formatting
   - Auto-paste setup

6. **MvrRunner_UI_Layout.py** (~400 lines)
   - Button width management
   - Display size handling
   - Layout enforcement functions
   - UI update helpers

## Expected Results

After refactoring:
- `MvrRunner.py`: ~1200-1400 lines (just build_tab + orchestration)
- `MvrRunner_Automation.py`: ~1200-1400 lines (just build_tab + orchestration)
- `MvrRunner_CopyPaste.py`: ~800-1000 lines (just build_tab + orchestration)

All files will be under 1500 lines!

