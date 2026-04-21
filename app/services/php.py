"""
PHP service manager.
Supports PHP built-in web server and PHP-CGI mode.
"""

import subprocess
import sys
import re
import shutil
from pathlib import Path
from typing import List, Optional

from .base_service import BaseService, ServiceStatus


# Common locations to search for PHP installations
PHP_SEARCH_PATHS_WIN = [
    r"C:\xampp\php",
    r"C:\php",
    r"C:\laragon\bin\php",
    r"C:\Program Files\PHP",
    r"C:\Program Files (x86)\PHP",
]

PHP_SEARCH_PATHS_UNIX = [
    "/usr/bin",
    "/usr/local/bin",
    "/opt/homebrew/bin",
    "/opt/homebrew/opt/php/bin",
]


class PHPService(BaseService):
    """
    Manages a PHP built-in web server instance.
    The built-in server is used for development convenience when Apache
    is not available or not configured with mod_php / PHP-CGI.
    """

    def __init__(self, config):
        super().__init__(config)
        self._version_cache: Optional[str] = None
        self._available_versions: Optional[List[dict]] = None

    # ------------------------------------------------------------------
    # BaseService interface
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "PHP"

    @property
    def version(self) -> str:
        if self._version_cache is not None:
            return self._version_cache
        exe = self.config.php_exe
        if not exe:
            return "Not Found"
        ver = self._get_version(exe)
        self._version_cache = ver
        return ver

    def _build_start_command(self) -> List[str]:
        exe = self.config.php_exe
        if not exe:
            return []

        # Always use php.exe (not php-cgi.exe) for the built-in server.
        # php-cgi.exe does not support the -S flag.
        exe_path = Path(exe)
        if exe_path.name.lower() == "php-cgi.exe":
            php_main = exe_path.parent / "php.exe"
            if php_main.exists():
                exe = str(php_main)
            else:
                self._log("php.exe not found next to php-cgi.exe – cannot start built-in server.")
                return []

        host = "127.0.0.1"
        port = self.config.php_port
        docroot = str(self.config.www_dir / "default")

        return [
            exe,
            "-S", f"{host}:{port}",
            "-t", docroot,
        ]

    # ------------------------------------------------------------------
    # Version detection
    # ------------------------------------------------------------------

    def _get_version(self, exe: str) -> str:
        try:
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            result = subprocess.run(
                [exe, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                **kwargs,
            )
            output = result.stdout + result.stderr
            match = re.search(r"PHP (\d+\.\d+\.\d+)", output)
            if match:
                return match.group(1)
        except (OSError, subprocess.TimeoutExpired):
            pass
        return "Unknown"

    # ------------------------------------------------------------------
    # Multi-version discovery
    # ------------------------------------------------------------------

    def discover_versions(self) -> List[dict]:
        """
        Scan common directories for PHP executables.
        Returns a list of dicts: {exe, version, path}.
        """
        if self._available_versions is not None:
            return self._available_versions

        found = {}

        # Check PATH first
        for name in ("php", "php8", "php7", "php5"):
            exe = shutil.which(name)
            if exe and exe not in found:
                found[exe] = self._get_version(exe)

        # Check known directories
        search_paths = (
            PHP_SEARCH_PATHS_WIN if sys.platform == "win32" else PHP_SEARCH_PATHS_UNIX
        )
        for base in search_paths:
            base_path = Path(base)
            if not base_path.exists():
                continue
            # Direct php.exe / php in this dir
            for exe_name in ("php.exe", "php"):
                candidate = base_path / exe_name
                if candidate.exists() and str(candidate) not in found:
                    found[str(candidate)] = self._get_version(str(candidate))
            # Sub-directories (e.g. C:\laragon\bin\php\php-8.1\php.exe)
            for sub in base_path.iterdir():
                if sub.is_dir():
                    for exe_name in ("php.exe", "php"):
                        candidate = sub / exe_name
                        if candidate.exists() and str(candidate) not in found:
                            found[str(candidate)] = self._get_version(str(candidate))

        self._available_versions = [
            {"exe": exe, "version": ver, "path": str(Path(exe).parent)}
            for exe, ver in found.items()
        ]
        return self._available_versions

    def set_version(self, exe: str):
        """Switch to a different PHP executable."""
        self.config.php_exe = exe
        self._version_cache = None  # Reset cache
        # Update php.ini path
        php_dir = Path(exe).parent
        for candidate in [php_dir / "php.ini", php_dir / "php.ini-development"]:
            if candidate.exists():
                self.config.php_ini = str(candidate)
                break
        self.config.save()

    # ------------------------------------------------------------------
    # PHP-CGI helper
    # ------------------------------------------------------------------

    def get_cgi_exe(self) -> Optional[str]:
        """Return path to php-cgi if available alongside the main php exe."""
        exe = self.config.php_exe
        if not exe:
            return None
        php_dir = Path(exe).parent
        for name in ("php-cgi.exe", "php-cgi"):
            candidate = php_dir / name
            if candidate.exists():
                return str(candidate)
        return None

    def get_log_path(self) -> Optional[Path]:
        return self.config.logs_dir / "php_error.log"
