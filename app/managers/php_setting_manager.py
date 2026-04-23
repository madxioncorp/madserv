"""
PHP settings manager.
Reads and modifies general settings in php.ini.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class PHPSettingManager:
    """
    Reads and modifies general key=value settings in php.ini.
    """

    def __init__(self, config):
        self.config = config
        self._lines: List[str] = []
        self._loaded = False

    def _get_ini_path(self) -> Optional[Path]:
        if self.config.php_ini:
            p = Path(self.config.php_ini)
            if p.exists():
                return p
        return None

    def load(self) -> bool:
        """Parse php.ini. Returns True on success."""
        ini_path = self._get_ini_path()
        if ini_path is None:
            return False

        try:
            content = ini_path.read_text(encoding="utf-8", errors="replace")
            self._lines = content.splitlines(keepends=True)
            self._loaded = True
            return True
        except OSError:
            return False

    def get_setting(self, key: str) -> Optional[str]:
        """Get the value of a setting from php.ini."""
        if not self._loaded:
            if not self.load():
                return None

        # Regex to match key = value (optionally commented out)
        # We want the active one, or the last one if multiple exist.
        pattern = re.compile(r"^\s*" + re.escape(key) + r"\s*=\s*(?P<value>[^\s;]+)", re.IGNORECASE)
        
        last_val = None
        for line in self._lines:
            m = pattern.match(line)
            if m:
                last_val = m.group("value").strip().strip('"')
        
        return last_val

    def set_settings(self, settings: Dict[str, str]) -> Tuple[int, List[str]]:
        """
        Update multiple settings in php.ini.
        Returns (count_changed, errors).
        """
        if not self._loaded:
            if not self.load():
                return 0, ["php.ini not found."]

        ini_path = self._get_ini_path()
        if ini_path is None:
            return 0, ["php.ini not found."]

        changed = 0
        errors = []

        for key, value in settings.items():
            found = False
            # Try to find and update existing active line
            pattern = re.compile(r"^\s*" + re.escape(key) + r"\s*=", re.IGNORECASE)
            
            for i, line in enumerate(self._lines):
                if pattern.match(line):
                    # Check if it's already the same value
                    current_val = line.split("=", 1)[1].split(";")[0].strip().strip('"')
                    if current_val == value:
                        found = True
                        break
                    
                    # Update line
                    self._lines[i] = f"{key} = {value}\n"
                    changed += 1
                    found = True
                    break
            
            if not found:
                # If not found, try to find a commented out version to replace
                comment_pattern = re.compile(r"^\s*;\s*" + re.escape(key) + r"\s*=", re.IGNORECASE)
                for i, line in enumerate(self._lines):
                    if comment_pattern.match(line):
                        self._lines[i] = f"{key} = {value}\n"
                        changed += 1
                        found = True
                        break
            
            if not found:
                # Still not found, append to the end
                self._lines.append(f"\n{key} = {value}\n")
                changed += 1

        if changed > 0:
            if not self._write(ini_path):
                return 0, ["Failed to write php.ini."]
        
        return changed, errors

    def _write(self, path: Path) -> bool:
        try:
            path.write_text("".join(self._lines), encoding="utf-8")
            return True
        except OSError:
            return False
