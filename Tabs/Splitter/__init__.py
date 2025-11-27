# Splitter Package
# Exports build_tab and other functions for use by mainApp.pyw

from .main import build_tab, set_cancelled, show_ssa_settings_dialog

__all__ = ['build_tab', 'set_cancelled', 'show_ssa_settings_dialog']

