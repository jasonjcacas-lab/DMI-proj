# -*- coding: utf-8 -*-
"""
Gemma AI Tool - Secure local AI chat using Gemma 2 7B GGUF
"""
import os
import sys
import threading
import queue
import json
from typing import Optional, List, Dict

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# Try to import llama-cpp-python
_LLAMA_AVAILABLE = False
_Llama = None
try:
    from llama_cpp import Llama
    _Llama = Llama
    _LLAMA_AVAILABLE = True
except ImportError:
    _LLAMA_AVAILABLE = False

# ------------------ Paths ------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
_MODELS_DIR = os.path.join(_PROJECT_ROOT, "models")
_DEFAULT_MODEL_PATH = os.path.join(_MODELS_DIR, "gemma-2-7b-it-Q5_K_M.gguf")
_SETTINGS_PATH = os.path.join(_PROJECT_ROOT, "gemma_ai_settings.json")

# Default settings
_DEFAULT_SETTINGS = {
    "model_path": _DEFAULT_MODEL_PATH,
    "n_ctx": 4096,  # Context window size
    "n_threads": None,  # None = auto-detect (will use ~80% of available cores)
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 512,
    "repeat_penalty": 1.1,
}

# Model state
_model_instance = None
_model_lock = threading.Lock()
_inference_queue = queue.Queue()
_response_queue = queue.Queue()


def _ensure_dir(path):
    """Ensure directory exists"""
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


def _load_settings():
    """Load settings from file"""
    try:
        if os.path.isfile(_SETTINGS_PATH):
            with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    settings = dict(_DEFAULT_SETTINGS)
                    settings.update(data)
                    return settings
    except Exception:
        pass
    return dict(_DEFAULT_SETTINGS)


def _save_settings(settings):
    """Save settings to file"""
    try:
        _ensure_dir(os.path.dirname(_SETTINGS_PATH))
        with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _get_thread_count():
    """Get optimal thread count (80% of available CPUs)"""
    try:
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        # Use 80% of cores, minimum 2, maximum 32
        threads = max(2, min(32, int(cpu_count * 0.8)))
        return threads
    except Exception:
        return 4  # Fallback


def _load_model(settings, status_callback=None):
    """Load the Gemma model"""
    global _model_instance
    
    model_path = settings.get("model_path", _DEFAULT_MODEL_PATH)
    
    if not _LLAMA_AVAILABLE:
        raise RuntimeError(
            "llama-cpp-python is not installed.\n\n"
            "Please install it with:\n"
            "pip install llama-cpp-python"
        )
    
    if not os.path.isfile(model_path):
        raise FileNotFoundError(
            f"Model file not found: {model_path}\n\n"
            "Please download the Gemma 2 7B GGUF model (Q5_K_M recommended)\n"
            "from Hugging Face and place it in the models directory."
        )
    
    if status_callback:
        status_callback("Loading model...")
    
    try:
        n_threads = settings.get("n_threads")
        if n_threads is None:
            n_threads = _get_thread_count()
        
        _model_instance = _Llama(
            model_path=model_path,
            n_ctx=settings.get("n_ctx", 4096),
            n_threads=n_threads,
            n_gpu_layers=0,  # CPU-only
            verbose=False,
            use_mmap=True,  # Faster loading
        )
        
        if status_callback:
            status_callback("Model loaded successfully")
        
        return True
    except Exception as e:
        _model_instance = None
        raise RuntimeError(f"Failed to load model: {str(e)}")


def _unload_model():
    """Unload the model to free memory"""
    global _model_instance
    with _model_lock:
        _model_instance = None


def _run_inference(prompt: str, settings: Dict, conversation_history: List[Dict]) -> str:
    """Run inference in the current thread (call from worker thread)"""
    global _model_instance
    
    if not _model_instance:
        raise RuntimeError("Model not loaded")
    
    # Build context from conversation history
    context = ""
    for msg in conversation_history[-10:]:  # Keep last 10 messages
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            context += f"User: {content}\n\n"
        elif role == "assistant":
            context += f"Assistant: {content}\n\n"
    
    # Add current prompt
    full_prompt = f"{context}User: {prompt}\n\nAssistant:"
    
    try:
        with _model_lock:
            response = _model_instance(
                full_prompt,
                max_tokens=settings.get("max_tokens", 512),
                temperature=settings.get("temperature", 0.7),
                top_p=settings.get("top_p", 0.9),
                repeat_penalty=settings.get("repeat_penalty", 1.1),
                stop=["User:", "\n\nUser:"],  # Stop at next user message
                echo=False,
            )
        
        # Extract text from response
        if isinstance(response, dict):
            if "choices" in response and len(response["choices"]) > 0:
                text = response["choices"][0].get("text", "").strip()
                return text
            elif "text" in response:
                return response["text"].strip()
        
        return str(response).strip()
    
    except Exception as e:
        raise RuntimeError(f"Inference error: {str(e)}")


def _inference_worker(settings, conversation_history, prompt, callback):
    """Worker thread for running inference"""
    try:
        response = _run_inference(prompt, settings, conversation_history)
        callback(True, response)
    except Exception as e:
        callback(False, str(e))


def build_tab(parent):
    """
    Create the Gemma AI Tool tab.
    """
    outer = ttk.Frame(parent)
    
    settings = _load_settings()
    
    # Check if llama-cpp-python is available
    if not _LLAMA_AVAILABLE:
        error_frame = ttk.Frame(outer)
        error_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ttk.Label(
            error_frame,
            text="Gemma AI Tool",
            font=("Segoe UI", 12, "bold")
        ).pack(pady=(0, 10))
        
        error_text = (
            "llama-cpp-python is not installed.\n\n"
            "Please install it with:\n"
            "pip install llama-cpp-python\n\n"
            "Then restart the application."
        )
        ttk.Label(
            error_frame,
            text=error_text,
            font=("Segoe UI", 10),
            foreground="red"
        ).pack()
        
        return outer
    
    # Title
    title_frame = ttk.Frame(outer)
    title_frame.pack(fill="x", padx=16, pady=(10, 5))
    
    ttk.Label(
        title_frame,
        text="Gemma AI Tool",
        font=("Segoe UI", 12, "bold")
    ).pack(side="left")
    
    # Status label
    status_var = tk.StringVar(value="Initializing...")
    status_label = ttk.Label(
        title_frame,
        textvariable=status_var,
        font=("Segoe UI", 9)
    )
    status_label.pack(side="right")
    
    # Main content area with PanedWindow for resizable panels
    paned = ttk.PanedWindow(outer, orient="vertical")
    paned.pack(fill="both", expand=True, padx=16, pady=5)
    
    # Chat display area
    chat_frame = ttk.Frame(paned)
    paned.add(chat_frame, weight=3)
    
    ttk.Label(
        chat_frame,
        text="Conversation",
        font=("Segoe UI", 10, "bold")
    ).pack(anchor="w", padx=5, pady=(5, 2))
    
    chat_display = scrolledtext.ScrolledText(
        chat_frame,
        wrap=tk.WORD,
        font=("Segoe UI", 10),
        state="disabled",
        relief="solid",
        borderwidth=1,
        bg="white",
        fg="black"
    )
    chat_display.pack(fill="both", expand=True, padx=5, pady=(0, 5))
    
    # Configure tags for styling messages
    chat_display.tag_config("user", foreground="blue", font=("Segoe UI", 10, "bold"))
    chat_display.tag_config("assistant", foreground="green")
    chat_display.tag_config("system", foreground="gray", font=("Segoe UI", 9, "italic"))
    
    # Input area
    input_frame = ttk.Frame(paned)
    paned.add(input_frame, weight=1)
    
    ttk.Label(
        input_frame,
        text="Your message",
        font=("Segoe UI", 10, "bold")
    ).pack(anchor="w", padx=5, pady=(5, 2))
    
    input_text = scrolledtext.ScrolledText(
        input_frame,
        height=4,
        wrap=tk.WORD,
        font=("Segoe UI", 10),
        relief="solid",
        borderwidth=1
    )
    input_text.pack(fill="both", expand=True, padx=5, pady=(0, 5))
    
    # Button frame
    button_frame = ttk.Frame(input_frame)
    button_frame.pack(fill="x", padx=5, pady=(0, 5))
    
    # Conversation history
    conversation_history: List[Dict] = []
    
    # Model loading state
    model_loaded = False
    inference_thread = None
    
    def update_status(text):
        """Update status label"""
        try:
            status_var.set(text)
            status_label.update_idletasks()
        except Exception:
            pass
    
    def append_to_chat(role: str, content: str):
        """Append message to chat display"""
        try:
            chat_display.config(state="normal")
            
            if role == "user":
                chat_display.insert("end", "You: ", "user")
                chat_display.insert("end", content + "\n\n")
            elif role == "assistant":
                chat_display.insert("end", "Gemma: ", "assistant")
                chat_display.insert("end", content + "\n\n")
            elif role == "system":
                chat_display.insert("end", content + "\n", "system")
            
            chat_display.see("end")
            chat_display.config(state="disabled")
        except Exception:
            pass
    
    def inference_callback(success: bool, result: str):
        """Callback for inference completion"""
        nonlocal inference_thread
        
        if success:
            append_to_chat("assistant", result)
            conversation_history.append({"role": "assistant", "content": result})
            update_status("Ready")
        else:
            error_msg = f"Error: {result}"
            append_to_chat("system", error_msg)
            update_status(f"Error: {result[:50]}")
            messagebox.showerror("Inference Error", result)
        
        inference_thread = None
    
    def send_message():
        """Send message to AI"""
        nonlocal model_loaded, inference_thread
        
        # Get input text
        user_input = input_text.get("1.0", "end-1c").strip()
        if not user_input:
            return
        
        # Check if model is loaded
        if not model_loaded:
            messagebox.showwarning(
                "Model Not Loaded",
                "Model is still loading. Please wait."
            )
            return
        
        # Check if already processing
        if inference_thread and inference_thread.is_alive():
            messagebox.showwarning(
                "Already Processing",
                "Please wait for the current response to complete."
            )
            return
        
        # Clear input
        input_text.delete("1.0", "end")
        
        # Add to conversation
        append_to_chat("user", user_input)
        conversation_history.append({"role": "user", "content": user_input})
        
        # Update status
        update_status("Thinking...")
        
        # Run inference in background thread
        inference_thread = threading.Thread(
            target=_inference_worker,
            args=(settings, conversation_history, user_input, inference_callback),
            daemon=True
        )
        inference_thread.start()
    
    def clear_conversation():
        """Clear conversation history"""
        nonlocal conversation_history
        
        conversation_history.clear()
        chat_display.config(state="normal")
        chat_display.delete("1.0", "end")
        append_to_chat("system", "Conversation cleared.")
        chat_display.config(state="disabled")
    
    def load_model():
        """Load the model"""
        nonlocal model_loaded
        
        if model_loaded:
            return
        
        try:
            update_status("Loading model (this may take 10-15 seconds)...")
            _load_model(settings, update_status)
            model_loaded = True
            update_status("Model ready")
            append_to_chat("system", "Model loaded successfully. You can start chatting!")
        except Exception as e:
            update_status("Model load failed")
            error_msg = f"Failed to load model: {str(e)}"
            append_to_chat("system", error_msg)
            messagebox.showerror("Model Load Error", error_msg)
    
    # Buttons
    send_btn = ttk.Button(
        button_frame,
        text="Send (Enter)",
        command=send_message
    )
    send_btn.pack(side="left", padx=(0, 5))
    
    clear_btn = ttk.Button(
        button_frame,
        text="Clear Conversation",
        command=clear_conversation
    )
    clear_btn.pack(side="left", padx=5)
    
    # Settings button
    def show_settings():
        """Show settings dialog"""
        settings_window = tk.Toplevel(outer.winfo_toplevel())
        settings_window.title("Gemma AI Settings")
        settings_window.geometry("500x400")
        settings_window.transient(outer.winfo_toplevel())
        settings_window.grab_set()
        
        settings_frame = ttk.Frame(settings_window, padding=20)
        settings_frame.pack(fill="both", expand=True)
        
        # Model path
        ttk.Label(settings_frame, text="Model Path:", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w", pady=5
        )
        model_path_var = tk.StringVar(value=settings.get("model_path", ""))
        model_path_entry = ttk.Entry(settings_frame, textvariable=model_path_var, width=50)
        model_path_entry.grid(row=0, column=1, columnspan=2, sticky="ew", pady=5, padx=5)
        
        def browse_model():
            path = tk.filedialog.askopenfilename(
                title="Select Gemma GGUF Model",
                filetypes=[("GGUF files", "*.gguf"), ("All files", "*.*")]
            )
            if path:
                model_path_var.set(path)
        
        ttk.Button(settings_frame, text="Browse...", command=browse_model).grid(
            row=0, column=3, padx=5
        )
        
        # Threads
        ttk.Label(settings_frame, text="Threads (auto):", font=("Segoe UI", 9, "bold")).grid(
            row=1, column=0, sticky="w", pady=5
        )
        n_threads = settings.get("n_threads") or _get_thread_count()
        threads_var = tk.StringVar(value=str(n_threads) if settings.get("n_threads") else "Auto")
        threads_entry = ttk.Entry(settings_frame, textvariable=threads_var, width=20)
        threads_entry.grid(row=1, column=1, sticky="w", pady=5, padx=5)
        ttk.Label(settings_frame, text="(Leave empty for auto)", font=("Segoe UI", 8)).grid(
            row=1, column=2, sticky="w"
        )
        
        # Temperature
        ttk.Label(settings_frame, text="Temperature:", font=("Segoe UI", 9, "bold")).grid(
            row=2, column=0, sticky="w", pady=5
        )
        temp_var = tk.DoubleVar(value=settings.get("temperature", 0.7))
        temp_scale = ttk.Scale(
            settings_frame,
            from_=0.1,
            to=2.0,
            variable=temp_var,
            orient="horizontal"
        )
        temp_scale.grid(row=2, column=1, columnspan=2, sticky="ew", pady=5, padx=5)
        temp_label = ttk.Label(settings_frame, text=f"{temp_var.get():.2f}")
        temp_label.grid(row=2, column=3, padx=5)
        
        def update_temp_label(*args):
            temp_label.config(text=f"{temp_var.get():.2f}")
        
        temp_var.trace("w", update_temp_label)
        
        # Max tokens
        ttk.Label(settings_frame, text="Max Tokens:", font=("Segoe UI", 9, "bold")).grid(
            row=3, column=0, sticky="w", pady=5
        )
        max_tokens_var = tk.IntVar(value=settings.get("max_tokens", 512))
        max_tokens_entry = ttk.Entry(settings_frame, textvariable=max_tokens_var, width=20)
        max_tokens_entry.grid(row=3, column=1, sticky="w", pady=5, padx=5)
        
        # Context window
        ttk.Label(settings_frame, text="Context Window:", font=("Segoe UI", 9, "bold")).grid(
            row=4, column=0, sticky="w", pady=5
        )
        ctx_var = tk.IntVar(value=settings.get("n_ctx", 4096))
        ctx_entry = ttk.Entry(settings_frame, textvariable=ctx_var, width=20)
        ctx_entry.grid(row=4, column=1, sticky="w", pady=5, padx=5)
        
        # Buttons
        button_frame2 = ttk.Frame(settings_frame)
        button_frame2.grid(row=5, column=0, columnspan=4, pady=20)
        
        def save_settings_and_close():
            new_settings = dict(settings)
            new_settings["model_path"] = model_path_var.get()
            
            threads_val = threads_var.get().strip()
            if threads_val.lower() == "auto" or not threads_val:
                new_settings["n_threads"] = None
            else:
                try:
                    new_settings["n_threads"] = int(threads_val)
                except ValueError:
                    messagebox.showerror("Invalid Value", "Threads must be a number or 'Auto'")
                    return
            
            new_settings["temperature"] = temp_var.get()
            new_settings["max_tokens"] = max_tokens_var.get()
            new_settings["n_ctx"] = ctx_var.get()
            
            _save_settings(new_settings)
            settings.update(new_settings)
            
            # Reload model if it's already loaded
            nonlocal model_loaded
            if model_loaded:
                update_status("Reloading model with new settings...")
                _unload_model()
                model_loaded = False
                load_model()
            
            settings_window.destroy()
        
        ttk.Button(button_frame2, text="Save", command=save_settings_and_close).pack(
            side="left", padx=5
        )
        ttk.Button(button_frame2, text="Cancel", command=settings_window.destroy).pack(
            side="left", padx=5
        )
        
        settings_frame.columnconfigure(1, weight=1)
    
    ttk.Button(
        button_frame,
        text="Settings...",
        command=show_settings
    ).pack(side="right", padx=5)
    
    # Bind Enter key to send (Ctrl+Enter for newline)
    def on_input_key(event):
        if event.state & 0x4 and event.keysym == "Return":  # Ctrl+Enter
            send_message()
            return "break"
        elif event.keysym == "Return":  # Enter alone
            # Allow Enter to add newline, use Ctrl+Enter to send
            pass
    
    input_text.bind("<KeyPress>", on_input_key)
    
    # Alternative: Shift+Enter for newline, Enter to send
    def on_input_key_alt(event):
        if event.keysym == "Return":
            if event.state & 0x1:  # Shift+Enter = newline
                return None
            else:  # Enter = send
                send_message()
                return "break"
    
    # Uncomment to use Enter-to-send instead:
    # input_text.bind("<KeyPress>", on_input_key_alt)
    
    # Load model when tab is first accessed (lazy loading)
    def on_tab_selected(event=None):
        if not model_loaded and _LLAMA_AVAILABLE:
            # Load in background to avoid blocking
            load_thread = threading.Thread(target=load_model, daemon=True)
            load_thread.start()
    
    # Try to bind to tab selection (may not work with all notebook implementations)
    try:
        notebook = parent.master  # Assuming parent is in a Notebook
        if notebook:
            notebook.bind("<<NotebookTabChanged>>", lambda e: on_tab_selected() if notebook.index("current") == notebook.index(parent) else None)
    except Exception:
        pass
    
    # Load model immediately (or use on_tab_selected for lazy loading)
    # For now, load immediately
    if _LLAMA_AVAILABLE:
        load_thread = threading.Thread(target=load_model, daemon=True)
        load_thread.start()
    else:
        update_status("llama-cpp-python not installed")
    
    return outer
