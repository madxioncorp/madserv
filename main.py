"""
MadServ - Local Development Environment Manager
Entry point for the application.
"""

import os
import sys
import tkinter as tk
from pathlib import Path

# Ensure the project root is on the path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def _fix_dll_search_path():
    """
    When bundled by PyInstaller, clear the extra DLL search directories
    that PyInstaller registers via SetDllDirectory / AddDllDirectory.
    This prevents child processes (PHP, Apache, MySQL) from loading the
    wrong VCRUNTIME140.dll or other CRT DLLs that PyInstaller bundles.
    """
    if not getattr(sys, "frozen", False):
        return
    if sys.platform != "win32":
        return
    try:
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        # SetDllDirectory("") clears any directory set by SetDllDirectory
        # and removes the application directory from the search order.
        kernel32.SetDllDirectoryW("")
    except Exception:
        pass


_fix_dll_search_path()

from app.config import AppConfig
from app.gui.main_window import MainWindow


def main():
    """Main entry point."""
    config = AppConfig()
    config.ensure_directories()

    root = tk.Tk()
    app = MainWindow(root, config)
    root.mainloop()
    # If mainloop returns normally (window destroyed without os._exit),
    # force-exit to clean up any lingering threads or handles.
    os._exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        os._exit(0)
