"""
Environment variable manager for Windows.
Handles adding application paths to the User PATH.
"""

import os
import sys
import winreg
import ctypes
from pathlib import Path
from typing import List, Set


class EnvManager:
    """Manages Windows environment variables."""

    def __init__(self, config):
        self.config = config

    def get_required_paths(self) -> List[str]:
        """Get a list of directories that should be in PATH."""
        paths: Set[str] = set()
        
        # Collect directories from configured executables
        exe_attrs = [
            "apache_exe", "mysqld_exe", "mysql_exe", 
            "php_exe", "node_exe", "go_exe", "redis_exe"
        ]
        
        for attr in exe_attrs:
            val = getattr(self.config, attr, None)
            if val:
                p = Path(val)
                if p.exists():
                    # If it's a file, get its parent directory
                    if p.is_file():
                        paths.add(str(p.parent.resolve()))
                    else:
                        paths.add(str(p.resolve()))
        
        return sorted(list(paths))

    def add_to_user_path(self) -> tuple:
        """
        Add required paths to the current user's PATH environment variable.
        Returns (success: bool, message: str).
        """
        if sys.platform != "win32":
            return False, "This feature is only supported on Windows."

        required_paths = self.get_required_paths()
        if not required_paths:
            return False, "No valid paths found to add."

        try:
            # Open the User Environment key
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, 
                "Environment", 
                0, 
                winreg.KEY_ALL_ACCESS
            )
            
            try:
                # Read current PATH
                current_path_str, data_type = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                current_path_str = ""
                data_type = winreg.REG_EXPAND_SZ

            # Split current path and clean up
            current_paths = [p.strip() for p in current_path_str.split(";") if p.strip()]
            
            # Add missing paths
            added_count = 0
            for p in required_paths:
                if p not in current_paths:
                    current_paths.append(p)
                    added_count += 1
            
            if added_count == 0:
                winreg.CloseKey(key)
                return True, "All paths are already in your PATH."

            # Write back to registry
            new_path_str = ";".join(current_paths)
            winreg.SetValueEx(key, "Path", 0, data_type, new_path_str)
            winreg.CloseKey(key)

            # Notify system about the change
            self._broadcast_change()
            
            return True, f"Successfully added {added_count} paths to your User PATH. You may need to restart your terminal or computer for changes to take effect."

        except Exception as e:
            return False, f"Error modifying PATH: {str(e)}"

    def remove_from_user_path(self) -> tuple:
        """
        Remove required paths from the current user's PATH environment variable.
        Returns (success: bool, message: str).
        """
        if sys.platform != "win32":
            return False, "This feature is only supported on Windows."

        required_paths = self.get_required_paths()
        if not required_paths:
            return False, "No valid paths found to remove."

        try:
            # Open the User Environment key
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, 
                "Environment", 
                0, 
                winreg.KEY_ALL_ACCESS
            )
            
            try:
                # Read current PATH
                current_path_str, data_type = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                winreg.CloseKey(key)
                return True, "PATH variable not found. Nothing to remove."

            # Split current path and clean up
            current_paths = [p.strip() for p in current_path_str.split(";") if p.strip()]
            
            # Remove paths
            removed_count = 0
            new_paths = []
            for p in current_paths:
                if p in required_paths:
                    removed_count += 1
                else:
                    new_paths.append(p)
            
            if removed_count == 0:
                winreg.CloseKey(key)
                return True, "None of the configured paths were found in your PATH."

            # Write back to registry
            new_path_str = ";".join(new_paths)
            winreg.SetValueEx(key, "Path", 0, data_type, new_path_str)
            winreg.CloseKey(key)

            # Notify system about the change
            self._broadcast_change()
            
            return True, f"Successfully removed {removed_count} paths from your User PATH."

        except Exception as e:
            return False, f"Error modifying PATH: {str(e)}"

    def _broadcast_change(self):
        """Broadcast WM_SETTINGCHANGE to notify other applications."""
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002
        
        lp_param = ctypes.c_wchar_p("Environment")
        
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, 
            WM_SETTINGCHANGE, 
            0, 
            lp_param, 
            SMTO_ABORTIFHUNG, 
            5000, 
            ctypes.byref(ctypes.c_size_t())
        )
