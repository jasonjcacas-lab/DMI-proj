"""
Script to split MvrRunner.py into two mode-specific files:
- MvrRunner_CopyPaste.py: Copy-Paste mode (copy buttons always visible, no Run button)
- MvrRunner_Automation.py: Automation mode (Run button always visible, no copy buttons)
"""
import re

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def create_copypaste_version(content):
    """Create CopyPaste mode version"""
    # Replace imports to use shared module
    content = content.replace(
        '# Optional, show clear error if missing dependencies at runtime',
        '# Import shared utilities\nfrom MvrRunner_Shared import (\n    _IMPORT_ERRORS, _SIZE_PRESETS, _DEFAULT_UI_SETTINGS,\n    _load_mvr_settings, _save_mvr_settings, _load_ui_settings, _save_ui_settings,\n    _apply_display_size, _extract_text_from_pdf, _parse_mvr_fields, format_dob_value, DND_FILES\n)\n\n# Optional, show clear error if missing dependencies at runtime'
    )
    
    # Remove automation-related imports (playwright, etc. - but keep in shared)
    # Actually, we'll keep imports but remove automation functions
    
    # Remove toggle switch section (lines with copy_paste_mode_var, toggle_copy_paste_mode)
    # Make copy buttons always visible
    content = re.sub(
        r'# Top section: Copy-Paste Mode toggle switch.*?toggle_copy_paste_mode\(\)\s*\n',
        '# Copy-Paste Mode: Copy buttons always visible\n    copy_paste_mode_var = tk.BooleanVar(value=True)  # Always enabled\n    ',
        content,
        flags=re.DOTALL
    )
    
    # Remove toggle switch creation
    content = re.sub(
        r'# Create toggle switch.*?toggle_copy_paste_mode\s*\)\s*\n',
        '',
        content,
        flags=re.DOTALL
    )
    
    # Make copy buttons always visible
    content = content.replace(
        '# Show copy button if copy-paste mode is enabled\n        if copy_paste_mode_var.get():',
        '# Copy buttons always visible in Copy-Paste mode\n        # Always show copy button'
    )
    
    # Remove Run button section
    content = re.sub(
        r'# Run MVR\'s button below extracted fields.*?threading\.Thread\(target=work, daemon=True\)\.start\(\)\s*\n',
        '',
        content,
        flags=re.DOTALL
    )
    
    # Remove automation functions
    automation_funcs = [
        r'def _ensure_playwright_browsers_installed.*?\n\n',
        r'def _get_chrome_user_data_dir.*?\n\n',
        r'def _add_stealth_script.*?\n\n',
        r'def _launch_chrome_with_profile_for_mvr.*?\n\n',
        r'def _launch_chrome_with_profile.*?\n\n',
        r'def _fill_site_with_playwright.*?\n\n',
        r'def _run_mvr_automation.*?\n\n',
    ]
    
    for pattern in automation_funcs:
        content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # Update title
    content = content.replace(
        'title_label = ttk.Label(outer, text="MVR Runner"',
        'title_label = ttk.Label(outer, text="MVR Runner - Copy-Paste Mode"'
    )
    
    return content

def create_automation_version(content):
    """Create Automation mode version"""
    # Similar replacements but opposite
    content = content.replace(
        '# Optional, show clear error if missing dependencies at runtime',
        '# Import shared utilities\nfrom MvrRunner_Shared import (\n    _IMPORT_ERRORS, _SIZE_PRESETS, _DEFAULT_UI_SETTINGS,\n    _load_mvr_settings, _save_mvr_settings, _load_ui_settings, _save_ui_settings,\n    _apply_display_size, _extract_text_from_pdf, _parse_mvr_fields, format_dob_value, DND_FILES\n)\n\n# Optional, show clear error if missing dependencies at runtime'
    )
    
    # Remove toggle switch, always hide copy buttons
    content = re.sub(
        r'# Top section: Copy-Paste Mode toggle switch.*?toggle_copy_paste_mode\(\)\s*\n',
        '# Automation Mode: Copy buttons hidden, Run button always visible\n    copy_paste_mode_var = tk.BooleanVar(value=False)  # Always disabled\n    ',
        content,
        flags=re.DOTALL
    )
    
    # Remove toggle switch creation
    content = re.sub(
        r'# Create toggle switch.*?toggle_copy_paste_mode\s*\)\s*\n',
        '',
        content,
        flags=re.DOTALL
    )
    
    # Never show copy buttons
    content = content.replace(
        '# Show copy button if copy-paste mode is enabled\n        if copy_paste_mode_var.get():',
        '# Copy buttons hidden in Automation mode\n        # Never show copy button'
    )
    
    # Always show Run button (remove the hide logic)
    content = content.replace(
        '# Hide run button initially if Copy-Paste Mode is ON\n    if copy_paste_mode_var.get():\n        run_btn_frame.grid_remove()',
        '# Run button always visible in Automation mode'
    )
    
    # Update title
    content = content.replace(
        'title_label = ttk.Label(outer, text="MVR Runner"',
        'title_label = ttk.Label(outer, text="MVR Runner - Automation Mode"'
    )
    
    return content

if __name__ == '__main__':
    original = read_file('MvrRunner.py')
    
    copypaste = create_copypaste_version(original)
    write_file('MvrRunner_CopyPaste.py', copypaste)
    
    automation = create_automation_version(original)
    write_file('MvrRunner_Automation.py', automation)
    
    print("Files created successfully!")

