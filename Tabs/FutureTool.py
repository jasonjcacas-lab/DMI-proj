# -*- coding: utf-8 -*-
"""
Future Tool - Placeholder for future functionality
"""
import tkinter as tk
from tkinter import ttk


def build_tab(parent):
    """
    Create the Future Tool tab.
    """
    outer = ttk.Frame(parent)
    
    # Title
    title_label = ttk.Label(outer, text="Future Tool", font=("Segoe UI", 12, "bold"))
    title_label.pack(pady=(20, 10))
    
    # Placeholder content
    placeholder_label = ttk.Label(
        outer, 
        text="This is a placeholder for future functionality.\n\nAdd your tools here!",
        font=("Segoe UI", 10)
    )
    placeholder_label.pack(pady=20)
    
    return outer

