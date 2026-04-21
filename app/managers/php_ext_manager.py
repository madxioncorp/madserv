"""
PHP extension manager.
Parses php.ini to enable/disable extensions by editing the file directly.
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple


# Rough categorisation of common PHP extensions
EXTENSION_CATEGORIES: Dict[str, List[str]] = {
    "Database": [
        "mysqli", "pdo", "pdo_mysql", "pdo_pgsql", "pdo_sqlite", "pdo_sqlsrv",
        "pgsql", "sqlite3", "sqlsrv", "oci8", "odbc",
    ],
    "Caching": [
        "apcu", "memcache", "memcached", "redis", "opcache", "wincache",
    ],
    "Image": [
        "gd", "imagick", "exif",
    ],
    "Crypto / Security": [
        "openssl", "sodium", "hash", "mcrypt",
    ],
    "String / Encoding": [
        "mbstring", "iconv", "intl", "gettext", "xml", "xmlrpc",
        "simplexml", "dom", "xsl", "json",
    ],
    "Network": [
        "curl", "ftp", "ldap", "soap", "sockets", "xmlrpc",
    ],
    "Math": [
        "bcmath", "gmp",
    ],
    "Compression": [
        "zip", "zlib", "bz2",
    ],
    "Development": [
        "xdebug", "pcov", "tidy", "tokenizer", "reflection",
    ],
    "Misc": [],  # Catch-all
}


def _categorise(ext_name: str) -> str:
    name_lower = ext_name.lower()
    for category, members in EXTENSION_CATEGORIES.items():
        if name_lower in members:
            return category
    return "Misc"


class PHPExtension:
    """Represents a single PHP extension entry."""

    def __init__(self, name: str, enabled: bool, line_index: int, raw_line: str):
        self.name = name
        self.enabled = enabled
        self.line_index = line_index  # Line number in php.ini (0-based)
        self.raw_line = raw_line
        self.category = _categorise(name)

    def __repr__(self):
        state = "ON" if self.enabled else "OFF"
        return f"<PHPExtension {self.name} [{state}]>"


class PHPExtManager:
    """
    Reads and modifies php.ini to enable/disable PHP extensions.
    """

    # Matches lines like:
    #   extension=curl
    #   extension=php_curl.dll
    #   ;extension=curl
    #   ; extension=curl
    _EXT_RE = re.compile(
        r"^(?P<comment>\s*;+\s*)?extension\s*=\s*(?P<name>[^\s;]+)",
        re.IGNORECASE,
    )
    # Also match zend_extension lines
    _ZEND_RE = re.compile(
        r"^(?P<comment>\s*;+\s*)?zend_extension\s*=\s*(?P<name>[^\s;]+)",
        re.IGNORECASE,
    )

    def __init__(self, config):
        self.config = config
        self._lines: List[str] = []
        self._extensions: List[PHPExtension] = []
        self._loaded = False

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _get_ini_path(self) -> Optional[Path]:
        if self.config.php_ini:
            p = Path(self.config.php_ini)
            if p.exists():
                return p
        return None

    def load(self) -> bool:
        """
        Parse php.ini and populate the extension list.
        Returns True on success.
        """
        ini_path = self._get_ini_path()
        if ini_path is None:
            return False

        try:
            content = ini_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False

        self._lines = content.splitlines(keepends=True)
        self._extensions = []
        seen: Dict[str, int] = {}  # name -> first occurrence index

        for i, line in enumerate(self._lines):
            for pattern in (self._EXT_RE, self._ZEND_RE):
                m = pattern.match(line)
                if m:
                    raw_name = m.group("name")
                    # Normalise: strip .dll / .so and php_ prefix
                    name = self._normalise_name(raw_name)
                    enabled = m.group("comment") is None or m.group("comment").strip() == ""
                    # Deduplicate: keep first occurrence
                    if name not in seen:
                        seen[name] = i
                        ext = PHPExtension(
                            name=name,
                            enabled=enabled,
                            line_index=i,
                            raw_line=line,
                        )
                        self._extensions.append(ext)
                    break  # Don't match both patterns on same line

        # Also scan the ext/ directory for available extensions not in php.ini
        self._add_available_from_ext_dir(seen)

        self._loaded = True
        return True

    def _normalise_name(self, raw: str) -> str:
        """Strip path, .dll/.so suffix, and php_ prefix."""
        name = Path(raw).stem  # removes extension
        if name.lower().startswith("php_"):
            name = name[4:]
        return name.lower()

    def _add_available_from_ext_dir(self, seen: Dict[str, int]):
        """
        Scan the PHP ext/ directory for .dll/.so files and add any
        extensions not already in php.ini as disabled entries.
        """
        php_exe = self.config.php_exe
        if not php_exe:
            return

        ext_dir = Path(php_exe).parent / "ext"
        if not ext_dir.exists():
            return

        suffix = ".dll" if sys.platform == "win32" else ".so"
        for f in sorted(ext_dir.iterdir()):
            if f.suffix.lower() == suffix:
                name = self._normalise_name(f.name)
                if name not in seen:
                    ext = PHPExtension(
                        name=name,
                        enabled=False,
                        line_index=-1,  # Not in php.ini yet
                        raw_line="",
                    )
                    self._extensions.append(ext)

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_extensions(self) -> List[PHPExtension]:
        if not self._loaded:
            self.load()
        return list(self._extensions)

    def get_extensions_by_category(self) -> Dict[str, List[PHPExtension]]:
        """Return extensions grouped by category."""
        result: Dict[str, List[PHPExtension]] = {}
        for ext in self.get_extensions():
            result.setdefault(ext.category, []).append(ext)
        # Sort categories, put Misc last
        ordered = {}
        for cat in sorted(result.keys(), key=lambda c: (c == "Misc", c)):
            ordered[cat] = sorted(result[cat], key=lambda e: e.name)
        return ordered

    # ------------------------------------------------------------------
    # Modification
    # ------------------------------------------------------------------

    def set_extension(self, name: str, enabled: bool) -> bool:
        """
        Enable or disable an extension by name.
        Returns True if php.ini was modified.
        """
        if not self._loaded:
            self.load()

        ini_path = self._get_ini_path()
        if ini_path is None:
            return False

        # Find the extension object
        ext = next((e for e in self._extensions if e.name == name), None)
        if ext is None:
            return False

        if ext.enabled == enabled:
            return True  # Nothing to do

        if ext.line_index == -1:
            # Extension not in php.ini yet – append it
            return self._append_extension(name, enabled, ini_path)

        # Modify existing line
        old_line = self._lines[ext.line_index]
        new_line = self._toggle_line(old_line, enabled)
        if new_line == old_line:
            return False

        self._lines[ext.line_index] = new_line
        ext.enabled = enabled
        ext.raw_line = new_line
        return self._write(ini_path)

    def apply_changes(self, changes: Dict[str, bool]) -> Tuple[int, List[str]]:
        """
        Apply a batch of enable/disable changes.
        changes: {extension_name: enabled_bool}
        Returns (count_changed, list_of_errors).
        """
        if not self._loaded:
            self.load()

        ini_path = self._get_ini_path()
        if ini_path is None:
            return 0, ["php.ini not found."]

        # Always ensure extension_dir is set to absolute path before writing
        self._ensure_extension_dir()

        errors = []
        changed = 0

        for name, enabled in changes.items():
            ext = next((e for e in self._extensions if e.name == name), None)
            if ext is None:
                errors.append(f"Extension '{name}' not found.")
                continue
            if ext.enabled == enabled:
                continue

            if ext.line_index == -1:
                if self._append_extension(name, enabled, ini_path):
                    changed += 1
                else:
                    errors.append(f"Failed to add '{name}' to php.ini.")
            else:
                old_line = self._lines[ext.line_index]
                new_line = self._toggle_line(old_line, enabled)
                if new_line != old_line:
                    self._lines[ext.line_index] = new_line
                    ext.enabled = enabled
                    ext.raw_line = new_line
                    changed += 1

        if changed > 0:
            if not self._write(ini_path):
                errors.append("Failed to write php.ini.")
                changed = 0

        return changed, errors

    def ensure_extension_dir(self) -> bool:
        """
        Public method: ensure extension_dir is set to the absolute path
        of the ext/ folder. Call this before starting Apache/PHP.
        Returns True if php.ini was modified or already correct.
        """
        if not self._loaded:
            self.load()
        return self._ensure_extension_dir()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_extension_dir(self) -> bool:
        """
        Make sure extension_dir in php.ini points to the absolute path
        of the ext/ directory next to php.exe.

        Without an absolute extension_dir, PHP loaded as mod_php inside
        Apache cannot find extension DLLs because its working directory
        is Apache's bin/ folder, not the PHP folder.
        """
        ini_path = self._get_ini_path()
        if ini_path is None:
            return False

        php_exe = self.config.php_exe
        if not php_exe:
            return False

        ext_dir = Path(php_exe).parent / "ext"
        if not ext_dir.exists():
            return False

        # Normalise to forward slashes for php.ini
        ext_dir_str = str(ext_dir).replace("\\", "/")
        target_line = f'extension_dir = "{ext_dir_str}"\n'

        if not self._loaded:
            self.load()

        # Look for existing extension_dir line (commented or not)
        ext_dir_re = re.compile(r"^\s*;*\s*extension_dir\s*=", re.IGNORECASE)
        found_idx = None
        for i, line in enumerate(self._lines):
            if ext_dir_re.match(line):
                found_idx = i
                break

        if found_idx is not None:
            # Check if it already has the correct absolute path
            if ext_dir_str in self._lines[found_idx] and not self._lines[found_idx].strip().startswith(";"):
                return True  # Already correct, nothing to do
            # Replace with correct absolute path
            self._lines[found_idx] = target_line
        else:
            # Append at end
            self._lines.append(f"\n; extension_dir set by MadServ\n")
            self._lines.append(target_line)

        return self._write(ini_path)

    def _toggle_line(self, line: str, enable: bool) -> str:
        """Comment or uncomment an extension line."""
        stripped = line.rstrip("\r\n")
        eol = line[len(stripped):]

        if enable:
            # Remove leading semicolons and whitespace
            new = re.sub(r"^\s*;+\s*", "", stripped)
        else:
            # Add a semicolon if not already commented
            if not re.match(r"^\s*;", stripped):
                new = ";" + stripped
            else:
                new = stripped  # Already commented

        return new + eol

    def _append_extension(self, name: str, enabled: bool, ini_path: Path) -> bool:
        """Append a new extension= line to php.ini."""
        prefix = "" if enabled else ";"
        if sys.platform == "win32":
            line = f"{prefix}extension=php_{name}.dll\n"
        else:
            line = f"{prefix}extension={name}.so\n"

        self._lines.append(line)
        ext = next((e for e in self._extensions if e.name == name), None)
        if ext:
            ext.line_index = len(self._lines) - 1
            ext.enabled = enabled
            ext.raw_line = line
        return self._write(ini_path)

    def _write(self, ini_path: Path) -> bool:
        """Write the modified lines back to php.ini."""
        # Create a backup first
        backup = ini_path.with_suffix(".ini.bak")
        try:
            import shutil
            shutil.copy2(ini_path, backup)
        except OSError:
            pass  # Backup failure is non-fatal

        try:
            ini_path.write_text("".join(self._lines), encoding="utf-8")
            return True
        except OSError as e:
            print(f"[PHPExtManager] Cannot write php.ini: {e}")
            return False

    def reload(self):
        """Reload from disk (discard in-memory state)."""
        self._lines = []
        self._extensions = []
        self._loaded = False
