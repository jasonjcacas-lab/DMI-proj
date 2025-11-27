"""
Browser and Chrome utility functions for MVR Runner.
Handles Chrome detection, port checking, and executable finding.
"""

import os
import socket
import sys

# Optional dependencies
try:
    import psutil
except Exception:
    psutil = None


def _is_port_open(host: str, port: int, timeout: float = 0.25) -> bool:
    """Check if a port is open on the given host."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        return s.connect_ex((host, port)) == 0
    finally:
        try:
            s.close()
        except Exception:
            pass


def _is_chrome_running() -> bool:
    """Quick check if any Chrome process is running."""
    if not psutil:
        return False
    try:
        for p in psutil.process_iter(attrs=["name"]):
            name = (p.info.get("name") or "").lower()
            if "chrome" in name or "chrome.exe" in name:
                return True
    except Exception:
        pass
    return False


def _find_chrome_executable():
    """Find Chrome executable path on Windows."""
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get('LOCALAPPDATA', ''), r'Google\Chrome\Application\chrome.exe'),
        os.path.join(os.environ.get('PROGRAMFILES', ''), r'Google\Chrome\Application\chrome.exe'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), r'Google\Chrome\Application\chrome.exe'),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


def _get_chrome_user_data_dir():
    """Get the Chrome user data directory for the current user."""
    if os.name == 'nt':  # Windows
        user_data_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'User Data')
    else:  # macOS/Linux
        if os.name == 'posix':
            home = os.environ.get('HOME', '')
            if sys.platform == 'darwin':  # macOS
                user_data_dir = os.path.join(home, 'Library', 'Application Support', 'Google', 'Chrome')
            else:  # Linux
                user_data_dir = os.path.join(home, '.config', 'google-chrome')
        else:
            user_data_dir = None
    return user_data_dir if user_data_dir and os.path.exists(user_data_dir) else None

