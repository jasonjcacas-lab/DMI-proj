"""
MVR Runner UI Dialogs Module
Contains settings dialog functions for MVR Runner.
"""

import tkinter as tk
from tkinter import ttk, messagebox

import os
import sys
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

try:
    # Try relative imports first (when loaded as Tabs.MvrRunner package)
    from .shared import (
        _load_mvr_settings, _save_mvr_settings
    )
except (ImportError, ValueError):
    # Fallback for direct file execution
    from shared import (
        _load_mvr_settings, _save_mvr_settings
    )


def show_site_automation_dialog(outer, url_var, sel_vars, use_existing_var, debug_port_var):
    """Open full-screen dialog for site automation settings"""
    root = outer.winfo_toplevel()
    dialog = tk.Toplevel(root)
    dialog.title("Site Automation Settings")
    # Make it large and centered
    dialog.geometry("900x700")
    dialog.transient(root)
    dialog.grab_set()  # Make it modal
    
    # Center the dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (900 // 2)
    y = (dialog.winfo_screenheight() // 2) - (700 // 2)
    dialog.geometry(f"900x700+{x}+{y}")
    
    # Main container
    main_frame = ttk.Frame(dialog, padding=20)
    main_frame.pack(fill="both", expand=True)
    
    ttk.Label(main_frame, text="Site Automation Settings", font=("Segoe UI", 14, "bold")).pack(pady=(0, 20))
    
    # URL setting
    url_frame = ttk.LabelFrame(main_frame, text="Target URL", padding=10)
    url_frame.pack(fill="x", pady=(0, 15))
    ttk.Label(url_frame, text="URL:").pack(anchor="w")
    url_entry = ttk.Entry(url_frame, textvariable=url_var, width=60)
    url_entry.pack(fill="x", pady=(5, 0))
    
    # CSS Selectors
    selectors_frame = ttk.LabelFrame(main_frame, text="CSS Selectors", padding=10)
    selectors_frame.pack(fill="both", expand=True, pady=(0, 15))
    
    selector_grid = ttk.Frame(selectors_frame)
    selector_grid.pack(fill="both", expand=True)
    
    ttk.Label(selector_grid, text="Field", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=5)
    ttk.Label(selector_grid, text="CSS Selector", font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="w", padx=5, pady=5)
    
    for i, (label, key) in enumerate([
        ("License #", "license_number"), 
        ("Last Name", "last_name"), 
        ("First Name", "first_name"), 
        ("DOB", "dob"), 
        ("State", "state"),
        ("Order Type", "order_type"),
        ("Product", "product"),
        ("Purpose", "purpose")
    ], start=1):
        ttk.Label(selector_grid, text=label).grid(row=i, column=0, sticky="e", padx=5, pady=5)
        entry = ttk.Entry(selector_grid, textvariable=sel_vars[key], width=50)
        entry.grid(row=i, column=1, sticky="we", padx=5, pady=5)
    
    selector_grid.columnconfigure(1, weight=1)
    
    # Buttons
    btn_frame = ttk.Frame(main_frame)
    btn_frame.pack(fill="x")
    def on_save_site_settings():
        # Save site automation settings
        settings = _load_mvr_settings()
        settings["url"] = url_var.get().strip()
        settings["selectors"] = {
            "license_number": sel_vars["license_number"].get().strip(),
            "last_name": sel_vars["last_name"].get().strip(),
            "first_name": sel_vars["first_name"].get().strip(),
            "dob": sel_vars["dob"].get().strip(),
            "state": sel_vars["state"].get().strip(),
            "order_type": sel_vars["order_type"].get().strip(),
            "product": sel_vars["product"].get().strip(),
            "purpose": sel_vars["purpose"].get().strip(),
        }
        settings["use_existing_chrome"] = use_existing_var.get()
        settings["debug_port"] = debug_port_var.get().strip()
        _save_mvr_settings(settings)
        dialog.destroy()
    ttk.Button(btn_frame, text="Save", command=on_save_site_settings, width=15).pack(side="right", padx=(5, 0))
    ttk.Button(btn_frame, text="Cancel", command=lambda: dialog.destroy(), width=15).pack(side="right")


def show_login_settings_dialog(outer, account_id_var, user_id_var, password_var, auto_click_recaptcha_var, login_sel_vars):
    """Open dialog for login settings"""
    root = outer.winfo_toplevel()
    dialog = tk.Toplevel(root)
    dialog.title("Login Settings")
    dialog.geometry("700x650")  # Increased size to ensure buttons are visible
    dialog.transient(root)
    dialog.grab_set()  # Make it modal
    
    # Center the dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (700 // 2)
    y = (dialog.winfo_screenheight() // 2) - (650 // 2)
    dialog.geometry(f"700x650+{x}+{y}")
    
    # Create a container with scrollable content area and fixed button area
    outer_container = ttk.Frame(dialog)
    outer_container.pack(fill="both", expand=True, padx=0, pady=0)
    
    # Scrollable content area
    canvas = tk.Canvas(outer_container)
    scrollbar = ttk.Scrollbar(outer_container, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Main content frame inside scrollable area
    main_frame = ttk.Frame(scrollable_frame, padding=20)
    main_frame.pack(fill="both", expand=True)
    
    ttk.Label(main_frame, text="Login Settings", font=("Segoe UI", 14, "bold")).pack(pady=(0, 20))
    
    # Login credentials
    login_frame = ttk.LabelFrame(main_frame, text="Login Credentials", padding=15)
    login_frame.pack(fill="x", pady=(0, 15))
    
    # Account ID
    ttk.Label(login_frame, text="Account ID:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    account_entry = ttk.Entry(login_frame, textvariable=account_id_var, width=40)
    account_entry.grid(row=0, column=1, sticky="we", padx=5, pady=5)
    # Ensure the entry field updates the variable
    account_entry.bind('<KeyRelease>', lambda e: account_id_var.set(account_entry.get()))
    
    # User ID/User Name
    ttk.Label(login_frame, text="User ID/User Name:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    user_entry = ttk.Entry(login_frame, textvariable=user_id_var, width=40)
    user_entry.grid(row=1, column=1, sticky="we", padx=5, pady=5)
    
    # Password
    ttk.Label(login_frame, text="Password:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    password_entry = ttk.Entry(login_frame, textvariable=password_var, width=40, show="*")
    password_entry.grid(row=2, column=1, sticky="we", padx=5, pady=5)
    
    # Auto-click reCAPTCHA checkbox
    recaptcha_checkbox = ttk.Checkbutton(login_frame, text="Automatically click 'I'm not a robot' checkbox", 
                                         variable=auto_click_recaptcha_var)
    recaptcha_checkbox.grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=10)
    
    login_frame.columnconfigure(1, weight=1)
    
    # Save button right under Password field
    def on_save_login_settings():
        # Save login settings
        try:
            settings = _load_mvr_settings()
            
            # Get values from entry fields
            account_id_value = account_id_var.get().strip()
            user_id_value = user_id_var.get().strip()
            password_value = password_var.get().strip()
            
            # Update settings
            settings["account_id"] = account_id_value
            settings["user_id"] = user_id_value
            settings["password"] = password_value
            settings["auto_click_recaptcha"] = auto_click_recaptcha_var.get()
            settings["login_selectors"] = {
                "account_id": login_sel_vars["account_id"].get().strip(),
                "user_id": login_sel_vars["user_id"].get().strip(),
                "password": login_sel_vars["password"].get().strip(),
            }
            
            # Save to file
            save_success = _save_mvr_settings(settings)
            
            if save_success:
                # Verify account_id was actually saved
                verify_settings = _load_mvr_settings()
                if verify_settings.get("account_id") == account_id_value:
                    # Show confirmation
                    import tkinter.messagebox as mb
                    mb.showinfo("Settings Saved", "Login settings have been saved successfully.")
                else:
                    import tkinter.messagebox as mb
                    mb.showwarning("Save Warning", "Settings may not have saved correctly. Please try again.")
            else:
                import tkinter.messagebox as mb
                mb.showerror("Save Error", "Failed to save settings. Please check file permissions.")
            
            dialog.destroy()
        except Exception as e:
            import tkinter.messagebox as mb
            mb.showerror("Save Error", f"Failed to save settings: {str(e)}")
    
    # Save button frame - placed right after reCAPTCHA checkbox
    save_btn_frame = ttk.Frame(login_frame)
    save_btn_frame.grid(row=4, column=0, columnspan=2, pady=(15, 5), sticky="e")
    
    save_btn = ttk.Button(save_btn_frame, text="Save", command=on_save_login_settings, width=15)
    save_btn.pack(side="right", padx=(5, 0))
    
    cancel_btn = ttk.Button(save_btn_frame, text="Cancel", command=lambda: dialog.destroy(), width=15)
    cancel_btn.pack(side="right")
    
    # CSS Selectors for login fields
    selectors_frame = ttk.LabelFrame(main_frame, text="CSS Selectors for Login Fields (Optional)", padding=15)
    selectors_frame.pack(fill="x", pady=(0, 15))
    
    # Use a separate frame for the info label to avoid grid/pack conflict
    info_frame = ttk.Frame(selectors_frame)
    info_frame.grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=(0, 10))
    ttk.Label(info_frame, text="If your login form uses non-standard field names, specify CSS selectors here.\nLeave empty to use automatic detection.", 
             font=("Segoe UI", 9), foreground="gray").pack(anchor="w")
    
    # Account ID Selector
    ttk.Label(selectors_frame, text="Account ID Selector:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    account_sel_entry = ttk.Entry(selectors_frame, textvariable=login_sel_vars["account_id"], width=45)
    account_sel_entry.grid(row=1, column=1, sticky="we", padx=5, pady=5)
    
    # User ID Selector
    ttk.Label(selectors_frame, text="User ID Selector:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    user_sel_entry = ttk.Entry(selectors_frame, textvariable=login_sel_vars["user_id"], width=45)
    user_sel_entry.grid(row=2, column=1, sticky="we", padx=5, pady=5)
    
    # Password Selector
    ttk.Label(selectors_frame, text="Password Selector:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
    password_sel_entry = ttk.Entry(selectors_frame, textvariable=login_sel_vars["password"], width=45)
    password_sel_entry.grid(row=3, column=1, sticky="we", padx=5, pady=5)
    
    selectors_frame.columnconfigure(1, weight=1)
    
    # Update scroll region
    canvas.update_idletasks()
    canvas.configure(scrollregion=canvas.bbox("all"))
    
    # Ensure dialog is properly sized
    dialog.update_idletasks()
    dialog.minsize(700, 500)
