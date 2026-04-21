"""
Application configuration management.
Handles paths, ports, executable locations, and persistent settings.
"""

import json
import os
import sys
import shutil
from pathlib import Path
from typing import Optional, Dict, Any


def _get_base_dir() -> Path:
    """
    Return the application base directory.

    - When running from source:  the folder containing main.py
    - When bundled (PyInstaller): the folder containing the .exe
      (sys.executable), NOT sys._MEIPASS which is the temp _internal dir.
    """
    if getattr(sys, "frozen", False):
        # PyInstaller / Nuitka bundle – use the directory of the executable
        return Path(sys.executable).parent.resolve()
    else:
        # Running from source – go up from app/config.py → app/ → project root
        return Path(__file__).parent.parent.resolve()


class AppConfig:
    """Central configuration for MadServ."""

    CONFIG_FILE = "config.json"

    def __init__(self):
        # Base directory – works both in source and bundled mode
        self.base_dir = _get_base_dir()

        # Core directories
        self.www_dir = self.base_dir / "www"
        self.logs_dir = self.base_dir / "logs"
        self.config_dir = self.base_dir / "config"
        self.bin_dir = self.base_dir / "bin"

        # Apache config directories
        self.apache_conf_dir = self.config_dir / "apache"
        self.apache_vhosts_dir = self.apache_conf_dir / "vhosts"

        # MySQL config directory
        self.mysql_conf_dir = self.config_dir / "mysql"

        # Template paths
        self.httpd_conf_template = self.apache_conf_dir / "httpd.conf.template"
        self.vhost_conf_template = self.apache_conf_dir / "vhost.conf.template"
        self.mysql_conf_template = self.mysql_conf_dir / "my.ini.template"

        # Generated config paths
        self.httpd_conf = self.apache_conf_dir / "httpd.conf"
        self.mysql_conf = self.mysql_conf_dir / "my.ini"

        # Default ports
        self.apache_port: int = 80
        self.mysql_port: int = 3306
        self.php_port: int = 8000  # for PHP built-in server

        # Executable paths (auto-detected or user-configured)
        self.apache_exe: Optional[str] = None
        self.mysql_exe: Optional[str] = None
        self.mysqld_exe: Optional[str] = None
        self.php_exe: Optional[str] = None

        # PHP ini path
        self.php_ini: Optional[str] = None

        # Domain suffix for virtual hosts
        self.vhost_suffix: str = "test"

        # Auto-detect executables
        self._auto_detect()

        # Load saved config (overrides auto-detected values if present)
        self._load()

    # ------------------------------------------------------------------
    # Directory management
    # ------------------------------------------------------------------

    def ensure_directories(self):
        """Create required directories if they don't exist."""
        dirs = [
            self.www_dir,
            self.www_dir / "default",
            self.logs_dir,
            self.config_dir,
            self.apache_conf_dir,
            self.apache_vhosts_dir,
            self.mysql_conf_dir,
            self.bin_dir,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # Create default index.php if missing
        default_index = self.www_dir / "default" / "index.php"
        if not default_index.exists():
            self._write_default_index(default_index)

    def _write_default_index(self, path: Path):
        content = """<?php
/**
 * MadServ - Default Welcome Page
 */
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to MadServ</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }
        .container {
            text-align: center;
            padding: 40px;
            background: #16213e;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
            max-width: 600px;
            width: 90%;
        }
        h1 { font-size: 2.5rem; color: #0f3460; margin-bottom: 8px;
             background: linear-gradient(135deg, #667eea, #764ba2);
             -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .subtitle { color: #888; margin-bottom: 30px; }
        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 24px; }
        .info-card {
            background: #0f3460;
            border-radius: 8px;
            padding: 16px;
            text-align: left;
        }
        .info-card h3 { color: #667eea; font-size: 0.85rem; text-transform: uppercase;
                        letter-spacing: 1px; margin-bottom: 8px; }
        .info-card p { font-size: 0.95rem; word-break: break-all; }
        .badge {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>MadServ</h1>
        <p class="subtitle">Your local development environment is running.</p>
        <div class="info-grid">
            <div class="info-card">
                <h3>PHP Version</h3>
                <p><?= phpversion() ?></p>
            </div>
            <div class="info-card">
                <h3>Server Software</h3>
                <p><?= $_SERVER['SERVER_SOFTWARE'] ?? 'PHP Built-in' ?></p>
            </div>
            <div class="info-card">
                <h3>Document Root</h3>
                <p><?= $_SERVER['DOCUMENT_ROOT'] ?></p>
            </div>
            <div class="info-card">
                <h3>Server Time</h3>
                <p><?= date('Y-m-d H:i:s') ?></p>
            </div>
        </div>
        <span class="badge">MadServ v1.0</span>
        <p style="margin-top:20px; color:#555; font-size:0.8rem;">
            Place your projects in the <strong>www/</strong> folder.
        </p>
    </div>
</body>
</html>
"""
        path.write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # Auto-detection
    # ------------------------------------------------------------------

    def _auto_detect(self):
        """Try to find executables in common locations."""
        self.apache_exe = self._find_exe(
            "httpd",
            [
                r"C:\xampp\apache\bin\httpd.exe",
                r"C:\Apache24\bin\httpd.exe",
                r"C:\Apache2\bin\httpd.exe",
                r"C:\laragon\bin\apache\apache2.4\bin\httpd.exe",
                "/usr/sbin/apache2",
                "/usr/sbin/httpd",
                "/usr/local/sbin/httpd",
                "/opt/homebrew/sbin/httpd",
            ],
        )

        self.mysqld_exe = self._find_exe(
            "mysqld",
            [
                r"C:\xampp\mysql\bin\mysqld.exe",
                r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe",
                r"C:\Program Files\MySQL\MySQL Server 5.7\bin\mysqld.exe",
                r"C:\laragon\bin\mysql\mysql-8.0\bin\mysqld.exe",
                r"C:\laragon\bin\mysql\mysql-5.7\bin\mysqld.exe",
                "/usr/sbin/mysqld",
                "/usr/local/sbin/mysqld",
                "/opt/homebrew/bin/mysqld",
            ],
        )

        self.mysql_exe = self._find_exe(
            "mysql",
            [
                r"C:\xampp\mysql\bin\mysql.exe",
                r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
                r"C:\laragon\bin\mysql\mysql-8.0\bin\mysql.exe",
                "/usr/bin/mysql",
                "/usr/local/bin/mysql",
                "/opt/homebrew/bin/mysql",
            ],
        )

        self.php_exe = self._find_exe(
            "php",
            [
                r"C:\xampp\php\php.exe",
                r"C:\php\php.exe",
                r"C:\laragon\bin\php\php-8.1\php.exe",
                r"C:\laragon\bin\php\php-8.0\php.exe",
                r"C:\laragon\bin\php\php-7.4\php.exe",
                "/usr/bin/php",
                "/usr/local/bin/php",
                "/opt/homebrew/bin/php",
            ],
        )

        # Detect php.ini
        if self.php_exe:
            php_dir = Path(self.php_exe).parent
            for candidate in [php_dir / "php.ini", php_dir / "php.ini-development"]:
                if candidate.exists():
                    self.php_ini = str(candidate)
                    break

    def _find_exe(self, name: str, candidates: list) -> Optional[str]:
        """Find an executable: check PATH first, then known locations."""
        # Check PATH
        found = shutil.which(name)
        if found:
            return found
        # On Windows also try with .exe
        if sys.platform == "win32":
            found = shutil.which(name + ".exe")
            if found:
                return found
        # Check known locations
        for path in candidates:
            if Path(path).exists():
                return str(path)
        return None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @property
    def config_file(self) -> Path:
        return self.base_dir / self.CONFIG_FILE

    def _load(self):
        """Load configuration from JSON file."""
        if not self.config_file.exists():
            return
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)

            self.apache_port = data.get("apache_port", self.apache_port)
            self.mysql_port = data.get("mysql_port", self.mysql_port)
            self.php_port = data.get("php_port", self.php_port)
            self.vhost_suffix = data.get("vhost_suffix", self.vhost_suffix)

            # Only override exe paths if the saved path still exists
            for attr in ("apache_exe", "mysqld_exe", "mysql_exe", "php_exe", "php_ini"):
                val = data.get(attr)
                if val and Path(val).exists():
                    setattr(self, attr, val)

        except (json.JSONDecodeError, OSError):
            pass  # Silently ignore corrupt config

    def save(self):
        """Persist current configuration to JSON file."""
        data = {
            "apache_port": self.apache_port,
            "mysql_port": self.mysql_port,
            "php_port": self.php_port,
            "vhost_suffix": self.vhost_suffix,
            "apache_exe": self.apache_exe,
            "mysqld_exe": self.mysqld_exe,
            "mysql_exe": self.mysql_exe,
            "php_exe": self.php_exe,
            "php_ini": self.php_ini,
        }
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            print(f"[Config] Failed to save config: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Return config as a plain dict (for display/editing)."""
        return {
            "apache_port": self.apache_port,
            "mysql_port": self.mysql_port,
            "php_port": self.php_port,
            "vhost_suffix": self.vhost_suffix,
            "apache_exe": self.apache_exe or "",
            "mysqld_exe": self.mysqld_exe or "",
            "mysql_exe": self.mysql_exe or "",
            "php_exe": self.php_exe or "",
            "php_ini": self.php_ini or "",
            "www_dir": str(self.www_dir),
            "logs_dir": str(self.logs_dir),
        }

    def update_from_dict(self, data: Dict[str, Any]):
        """Update config from a dict (e.g. from settings dialog)."""
        int_fields = ("apache_port", "mysql_port", "php_port")
        str_fields = ("vhost_suffix", "apache_exe", "mysqld_exe", "mysql_exe", "php_exe", "php_ini")

        for field in int_fields:
            if field in data:
                try:
                    setattr(self, field, int(data[field]))
                except (ValueError, TypeError):
                    pass

        for field in str_fields:
            if field in data:
                val = str(data[field]).strip() or None
                setattr(self, field, val)

        self.save()
