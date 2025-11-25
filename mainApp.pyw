# -*- coding: utf-8 -*-
import os
import sys
import importlib
import importlib.util

import tkinter as tk
from tkinter import ttk, messagebox

# Try to use TkinterDnD for drag-and-drop support
try:
    from tkinterdnd2 import TkinterDnD
    _USE_DND = True
except Exception:
    TkinterDnD = None
    _USE_DND = False

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.append(APP_DIR)

def _import_splitter():
    """
    Try multiple strategies to import Splitter:
    1) Normal import (module on sys.path)
    2) From Tabs package: from Tabs import Splitter
    3) Directly load Splitter.py (or splitter.py) from APP_DIR or APP_DIR/Tabs
    Returns the imported module, or raises SystemExit with a helpful message.
    """
    # 1) Normal import
    try:
        import Splitter  # noqa
        return Splitter
    except Exception:
        pass

    # 2) From a Tabs package (e.g., Tabs/Splitter.py with __init__.py or namespace)
    try:
        from Tabs import Splitter  # noqa
        return Splitter
    except Exception:
        pass

    # 3) Direct file load (case-insensitive filename check) in likely locations
    search_dirs = [APP_DIR, os.path.join(APP_DIR, "Tabs")]
    candidate_names = ["Splitter.py", "splitter.py"]

    tried_paths = []
    for d in search_dirs:
        for name in candidate_names:
            p = os.path.join(d, name)
            if os.path.isfile(p):
                try:
                    spec = importlib.util.spec_from_file_location("Splitter", p)
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules["Splitter"] = mod
                    assert spec.loader is not None
                    spec.loader.exec_module(mod)
                    return mod
                except Exception as e:
                    tried_paths.append(f"{p} -> {e}")
            else:
                tried_paths.append(f"{p} (not found)")

    msg = [
        "Failed to import Splitter.py.",
        "Searched these locations:",
        *["  - " + t for t in tried_paths],
        "",
        "Fixes to try:",
        "  • Ensure the file is actually named 'Splitter.py' (capital S) or 'splitter.py'.",
        "  • If it's in a 'Tabs' folder, keep it at: <project>/Tabs/Splitter.py",
        "  • Run mainApp.py from the same folder as Splitter.py (or use the shortcut you made).",
        "  • On case-sensitive filesystems (Linux/macOS), the exact casing must match.",
        "",
        "(Continuing without the Binder Splitter tab.)",
    ]
    try:
        # Try to show a notice if a Tk root exists later
        sys.stderr.write("\n".join(msg) + "\n")
    except Exception:
        pass
    return None


# Try to import the Splitter module (optional)
Splitter = _import_splitter()

def on_close(root):
    try:
        # Cancel any ongoing processing
        if Splitter is not None and hasattr(Splitter, 'set_cancelled'):
            Splitter.set_cancelled(True)
        # Wait a moment for cancellation to take effect, then close
        def try_close():
            try:
                if root.winfo_exists():
                    root.destroy()
            except Exception:
                pass
        root.after(200, try_close)
        # If still running after a moment, force close
        root.after(500, lambda: os._exit(0) if root.winfo_exists() else None)
    except Exception:
        os._exit(0)

def main():
    # Use TkinterDnD.Tk() if available for drag-and-drop support, otherwise fall back to tk.Tk()
    if _USE_DND and TkinterDnD:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    root.title("DMI Tool Suite")
    root.geometry("980x720+120+80")

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # Create menu bar
    menubar = tk.Menu(root)
    root.config(menu=menubar)

    # Settings menu
    settings_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Settings", menu=settings_menu)
    if Splitter is not None and hasattr(Splitter, "show_ssa_settings_dialog"):
        def show_ssa_dialog():
            Splitter.show_ssa_settings_dialog(root)
        settings_menu.add_command(label="SSA Rule Selection...", command=show_ssa_dialog)

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)

    # Build the Splitter tab if available
    if Splitter is not None and hasattr(Splitter, "build_tab"):
        try:
            splitter_tab = Splitter.build_tab(notebook)
            notebook.add(splitter_tab, text="Binder Splitter")
        except Exception as e:
            messagebox.showwarning("Splitter Unavailable", f"Binder Splitter tab disabled:\n{e}")

    # Add MVR Runner tab (optional if module exists)
    try:
        from Tabs import MvrRunner  # type: ignore
        mvr_tab = MvrRunner.build_tab(notebook)
        notebook.add(mvr_tab, text="MVR Runner")
    except Exception as e:
        # Fallback: try to load directly from file path
        try:
            mvr_path = os.path.join(APP_DIR, "Tabs", "MvrRunner.py")
            if os.path.isfile(mvr_path):
                spec = importlib.util.spec_from_file_location("Tabs.MvrRunner", mvr_path)
                mvr_mod = importlib.util.module_from_spec(spec)  # type: ignore
                assert spec is not None and spec.loader is not None
                spec.loader.exec_module(mvr_mod)  # type: ignore
                mvr_tab = mvr_mod.build_tab(notebook)  # type: ignore
                notebook.add(mvr_tab, text="MVR Runner")
        except Exception as e2:
            # Show error message instead of silently failing
            try:
                error_msg = f"Failed to load MvrRunner: {e}\nFallback also failed: {e2}"
                sys.stderr.write(error_msg + "\n")
                messagebox.showwarning("MVR Runner Unavailable", f"MVR Runner tab disabled:\n{error_msg}")
            except Exception:
                pass

    # Add Ollama AI Tool tab (optional if module exists)
    try:
        from Tabs import OllamaTool  # type: ignore
        ollama_tab = OllamaTool.build_tab(notebook)
        notebook.add(ollama_tab, text="Ollama AI")
    except Exception as e:
        # Fallback: try to load directly from file path
        try:
            ollama_path = os.path.join(APP_DIR, "Tabs", "OllamaTool.py")
            if os.path.isfile(ollama_path):
                spec = importlib.util.spec_from_file_location("Tabs.OllamaTool", ollama_path)
                ollama_mod = importlib.util.module_from_spec(spec)  # type: ignore
                assert spec is not None and spec.loader is not None
                spec.loader.exec_module(ollama_mod)  # type: ignore
                ollama_tab = ollama_mod.build_tab(notebook)  # type: ignore
                notebook.add(ollama_tab, text="Ollama AI")
            else:
                # File doesn't exist
                try:
                    sys.stderr.write(f"OllamaTool.py not found at {ollama_path}\n")
                except Exception:
                    pass
        except Exception as e2:
            # Show error message to help debug
            try:
                import traceback
                error_details = f"Failed to load Ollama AI tab:\n\nPrimary error: {e}\n\nFallback error: {e2}\n\nTraceback:\n{traceback.format_exc()}"
                sys.stderr.write(error_details + "\n")
                # Show a messagebox so user knows what happened
                try:
                    messagebox.showwarning("Ollama AI Tab Unavailable", 
                        f"Ollama AI tab could not be loaded:\n\n{str(e)}\n\nCheck console for details.")
                except Exception:
                    pass
            except Exception:
                pass

    root.protocol("WM_DELETE_WINDOW", lambda: on_close(root))
    root.mainloop()

if __name__ == "__main__":
    main()
