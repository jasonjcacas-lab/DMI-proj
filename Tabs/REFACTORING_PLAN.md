# MvrRunner Refactoring Plan

## Current State
- `MvrRunner.py`: 4893 lines
- `MvrRunner_Automation.py`: 4783 lines  
- `MvrRunner_CopyPaste.py`: 1861 lines
- `MvrRunner_Shared.py`: 445 lines (already well-organized)

## Proposed Structure

### New Modules to Create:

1. **MvrRunner_BrowserUtils.py** ✅ (Created)
   - `_is_port_open()`
   - `_is_chrome_running()`
   - `_find_chrome_executable()`
   - `_get_chrome_user_data_dir()`

2. **MvrRunner_AutomationCore.py** (To Create)
   - `_ensure_playwright_browsers_installed()`
   - `_add_stealth_script()`
   - `_launch_chrome_with_profile_for_mvr()`
   - `_launch_chrome_with_profile()`
   - `_fill_site_with_playwright()`
   - `_run_mvr_automation()`

3. **MvrRunner_UI_Components.py** (To Create)
   - `show_site_automation_dialog()`
   - `show_login_settings_dialog()`

4. **MvrRunner_FileManager.py** (To Create - Optional)
   - File list management
   - Drag-drop handlers
   - File operations

5. **MvrRunner_FieldManager.py** (To Create - Optional)
   - Field UI components
   - Copy button functionality
   - Clipboard operations

## Benefits
- Reduced file sizes (main files will be ~2000-3000 lines instead of 4000-5000)
- Better organization and maintainability
- Easier to find and modify specific functionality
- Reusable components across different modes

## Implementation Strategy
1. Create new modules with extracted functions
2. Update main files to import from new modules
3. Maintain same public interface (`build_tab()` function)
4. Test to ensure functionality is preserved

