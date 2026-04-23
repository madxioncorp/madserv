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
        self.redis_port: int = 6379

        # Executable paths (auto-detected or user-configured)
        self.apache_exe: Optional[str] = None
        self.mysqld_exe: Optional[str] = None
        self.mysql_exe: Optional[str] = None
        self.php_exe: Optional[str] = None
        self.node_exe: Optional[str] = None
        self.go_exe: Optional[str] = None
        self.redis_exe: Optional[str] = None

        # PHP ini path
        self.php_ini: Optional[str] = None

        # Domain suffix for virtual hosts
        self.vhost_suffix: str = "test"

        # Node and Go app paths
        self.node_app_path: str = str(self.www_dir / "node_app")
        self.go_app_path: str = str(self.www_dir / "go_app")

        # Auto-detect executables
        self._auto_detect()

        # Load saved config (overrides auto-detected values if present)
        self._load()

    # ------------------------------------------------------------------
    # Directory management
    # ------------------------------------------------------------------

    def ensure_directories(self):
        """Create required directories and default files if they don't exist."""
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

        # Create default templates if missing
        self._ensure_templates()

    def _ensure_templates(self):
        """Write default templates if they are missing from the config directory."""
        templates = {
            self.httpd_conf_template: self._DEFAULT_HTTPD_CONF_TEMPLATE,
            self.vhost_conf_template: self._DEFAULT_VHOST_CONF_TEMPLATE,
            self.mysql_conf_template: self._DEFAULT_MY_INI_TEMPLATE,
        }
        for path, content in templates.items():
            if not path.exists():
                try:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content.strip(), encoding="utf-8")
                    print(f"[Config] Created default template: {path.name}")
                except OSError as e:
                    print(f"[Config] Failed to create template {path.name}: {e}")

    _DEFAULT_HTTPD_CONF_TEMPLATE = """
# MadServ - Apache httpd configuration
# Auto-generated from httpd.conf.template – do not edit manually.

ServerRoot "{server_root}"

Listen {port}

# ── Modules ────────────────────────────────────────────────────────────────
LoadModule access_compat_module modules/mod_access_compat.so
LoadModule actions_module modules/mod_actions.so
LoadModule alias_module modules/mod_alias.so
LoadModule allowmethods_module modules/mod_allowmethods.so
LoadModule auth_basic_module modules/mod_auth_basic.so
LoadModule authn_core_module modules/mod_authn_core.so
LoadModule authn_file_module modules/mod_authn_file.so
LoadModule authz_core_module modules/mod_authz_core.so
LoadModule authz_groupfile_module modules/mod_authz_groupfile.so
LoadModule authz_host_module modules/mod_authz_host.so
LoadModule authz_user_module modules/mod_authz_user.so
LoadModule autoindex_module modules/mod_autoindex.so
LoadModule dir_module modules/mod_dir.so
LoadModule env_module modules/mod_env.so
LoadModule filter_module modules/mod_filter.so
LoadModule headers_module modules/mod_headers.so
LoadModule isapi_module modules/mod_isapi.so
LoadModule log_config_module modules/mod_log_config.so
LoadModule mime_module modules/mod_mime.so
LoadModule negotiation_module modules/mod_negotiation.so
LoadModule rewrite_module modules/mod_rewrite.so
LoadModule reqtimeout_module modules/mod_reqtimeout.so
LoadModule setenvif_module modules/mod_setenvif.so
LoadModule version_module modules/mod_version.so

# ── PHP via mod_php ────────────────────────────────────────────────────────
LoadFile "{php_dir}/php8ts.dll"
LoadModule php_module "{php_dir}/php8apache2_4.dll"
PHPIniDir "{php_dir}"
AddType application/x-httpd-php .php .phtml .php3 .php4 .php5 .php7
AddType application/x-httpd-php-source .phps

# ── Rewrite engine (enabled globally, .htaccess can use RewriteRule) ───────
RewriteEngine On

# ── Server identity ────────────────────────────────────────────────────────
ServerAdmin admin@localhost
ServerName localhost:{port}

# ── Default document root ──────────────────────────────────────────────────
DocumentRoot "{www_default}"

<Directory />
    AllowOverride none
    Require all denied
</Directory>

<Directory "{www_default}">
    Options Indexes FollowSymLinks
    AllowOverride All
    Require all granted
    DirectoryIndex index.php index.html index.htm
</Directory>

<Files ".ht*">
    Require all denied
</Files>

# ── MIME types ─────────────────────────────────────────────────────────────
TypesConfig "{server_root}/conf/mime.types"
AddType application/x-compress .Z
AddType application/x-gzip .gz .tgz
AddDefaultCharset UTF-8

# ── Logging ────────────────────────────────────────────────────────────────
ErrorLog "{logs_dir}/apache_error.log"
LogLevel warn

LogFormat "%h %l %u %t \\"%r\\" %>s %b \\"%{{Referer}}i\\" \\"%{{User-Agent}}i\\"" combined
LogFormat "%h %l %u %t \\"%r\\" %>s %b" common
CustomLog "{logs_dir}/apache_access.log" combined

# ── Virtual hosts ──────────────────────────────────────────────────────────
IncludeOptional "{vhosts_dir}/*.conf"
"""

    _DEFAULT_VHOST_CONF_TEMPLATE = """
# MadServ Virtual Host – auto-generated
# Domain: {domain}

<VirtualHost *:{port}>
    ServerName {domain}
    DocumentRoot "{docroot}"

    <Directory "{docroot}">
        Options Indexes FollowSymLinks MultiViews
        AllowOverride All
        Require all granted
        DirectoryIndex index.php index.html index.htm
    </Directory>

    ErrorLog "{logs_dir}/{domain}_error.log"
    CustomLog "{logs_dir}/{domain}_access.log" combined
</VirtualHost>
"""

    _DEFAULT_MY_INI_TEMPLATE = """
# MadServ - MySQL / MariaDB configuration
# Auto-generated from my.ini.template – do not edit manually.

[client]
port            = {port}
socket          = /tmp/mysql.sock

[mysqld]
# Basic settings
port            = {port}
basedir         = {mysql_base}
datadir         = {data_dir}
socket          = /tmp/mysql.sock
pid-file        = {data_dir}/mysql.pid

# Networking
bind-address    = 127.0.0.1
max_connections = 100

# Logging
log-error       = {logs_dir}/mysql_error.log
general_log     = 0
general_log_file = {logs_dir}/mysql_general.log
slow_query_log  = 0
slow_query_log_file = {logs_dir}/mysql_slow.log
long_query_time = 2

# InnoDB settings
default_storage_engine  = InnoDB
innodb_buffer_pool_size = 128M
innodb_log_file_size    = 48M
innodb_flush_log_at_trx_commit = 1
innodb_lock_wait_timeout = 50

# Character set
character-set-server    = utf8mb4
collation-server        = utf8mb4_unicode_ci

# SQL mode (permissive for development)
sql_mode = ""

[mysqldump]
quick
max_allowed_packet = 64M

[mysql]
no-auto-rehash
default-character-set = utf8mb4
"""

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
        <span class="badge">MadServ v1.2.0</span>
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
        """Try to find executables in common locations, prioritizing local bin/."""
        # 1. Apache
        apache_local = self.bin_dir / "Apache24" / "bin" / "httpd.exe"
        self.apache_exe = self._find_exe(
            "httpd",
            [
                str(apache_local),
                r"C:\xampp\apache\bin\httpd.exe",
                r"C:\Apache24\bin\httpd.exe",
                r"C:\Apache2\bin\httpd.exe",
                r"C:\laragon\bin\apache\apache2.4\bin\httpd.exe",
            ],
            prioritize_local=True
        )

        # 2. MySQL / MariaDB
        # Search in bin/ for any directory starting with 'mysql' or 'mariadb'
        mysql_local_bin = None
        mysqld_local_bin = None
        if self.bin_dir.exists():
            for sub in self.bin_dir.iterdir():
                if sub.is_dir() and (sub.name.lower().startswith("mysql") or sub.name.lower().startswith("mariadb")):
                    mysqld_candidate = sub / "bin" / "mysqld.exe"
                    mysql_candidate = sub / "bin" / "mysql.exe"
                    if mysqld_candidate.exists():
                        mysqld_local_bin = str(mysqld_candidate)
                    if mysql_candidate.exists():
                        mysql_local_bin = str(mysql_candidate)
                    break

        self.mysqld_exe = self._find_exe(
            "mysqld",
            [
                mysqld_local_bin,
                r"C:\xampp\mysql\bin\mysqld.exe",
                r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe",
                r"C:\Program Files\MySQL\MySQL Server 5.7\bin\mysqld.exe",
                r"C:\laragon\bin\mysql\mysql-8.0\bin\mysqld.exe",
            ],
            prioritize_local=True
        )

        self.mysql_exe = self._find_exe(
            "mysql",
            [
                mysql_local_bin,
                r"C:\xampp\mysql\bin\mysql.exe",
                r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
                r"C:\laragon\bin\mysql\mysql-8.0\bin\mysql.exe",
            ],
            prioritize_local=True
        )

        # 3. PHP
        php_local = None
        if self.bin_dir.exists():
            for sub in self.bin_dir.iterdir():
                if sub.is_dir() and sub.name.lower().startswith("php"):
                    php_candidate = sub / "php.exe"
                    if php_candidate.exists():
                        php_local = str(php_candidate)
                        break

        self.php_exe = self._find_exe(
            "php",
            [
                php_local,
                r"C:\xampp\php\php.exe",
                r"C:\php\php.exe",
                r"C:\laragon\bin\php\php-8.1\php.exe",
                r"C:\laragon\bin\php\php-8.0\php.exe",
                r"C:\laragon\bin\php\php-7.4\php.exe",
            ],
            prioritize_local=True
        )

        # 4. Node.js
        node_local = None
        if self.bin_dir.exists():
            for sub in self.bin_dir.iterdir():
                if sub.is_dir() and sub.name.lower().startswith("node"):
                    node_candidate = sub / "node.exe"
                    if node_candidate.exists():
                        node_local = str(node_candidate)
                        break
        
        self.node_exe = self._find_exe(
            "node",
            [
                node_local,
                r"C:\Program Files\nodejs\node.exe",
            ],
            prioritize_local=True
        )

        # 5. Go
        go_local = None
        if self.bin_dir.exists():
            for sub in self.bin_dir.iterdir():
                if sub.is_dir() and sub.name.lower() == "go":
                    go_candidate = sub / "bin" / "go.exe"
                    if go_candidate.exists():
                        go_local = str(go_candidate)
                        break
        
        self.go_exe = self._find_exe(
            "go",
            [
                go_local,
                r"C:\Program Files\Go\bin\go.exe",
            ],
            prioritize_local=True
        )

        # 6. Redis
        redis_local = None
        if self.bin_dir.exists():
            for sub in self.bin_dir.iterdir():
                if sub.is_dir() and sub.name.lower().startswith("redis"):
                    redis_candidate = sub / "redis-server.exe"
                    if redis_candidate.exists():
                        redis_local = str(redis_candidate)
                        break

        self.redis_exe = self._find_exe(
            "redis-server",
            [
                redis_local,
                r"C:\Program Files\Redis\redis-server.exe",
                r"C:\Redis\redis-server.exe",
            ],
            prioritize_local=True
        )

        # Detect php.ini
        if self.php_exe:
            php_dir = Path(self.php_exe).parent
            for candidate in [php_dir / "php.ini", php_dir / "php.ini-development"]:
                if candidate.exists():
                    self.php_ini = str(candidate)
                    break

    def _find_exe(self, name: str, candidates: list, prioritize_local: bool = False) -> Optional[str]:
        """
        Find an executable.
        If prioritize_local is True, it checks the provided candidates list first
        (which should contain local paths) before checking the system PATH.
        """
        # Filter out None from candidates
        candidates = [c for c in candidates if c]

        if prioritize_local:
            # Check known locations first (local paths are at the top of the list)
            for path in candidates:
                if Path(path).exists():
                    return str(path)

        # Check PATH
        found = shutil.which(name)
        if found:
            return found
        # On Windows also try with .exe
        if sys.platform == "win32":
            found = shutil.which(name + ".exe")
            if found:
                return found

        if not prioritize_local:
            # Check known locations after PATH
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

            self.apache_port = int(data.get("apache_port", self.apache_port))
            self.mysql_port = int(data.get("mysql_port", self.mysql_port))
            self.php_port = int(data.get("php_port", self.php_port))
            self.redis_port = int(data.get("redis_port", self.redis_port))
            self.vhost_suffix = data.get("vhost_suffix", self.vhost_suffix)
            self.node_app_path = data.get("node_app_path", self.node_app_path)
            self.go_app_path = data.get("go_app_path", self.go_app_path)

            # Only override exe paths if the saved path still exists
            for attr in ("apache_exe", "mysqld_exe", "mysql_exe", "php_exe", "node_exe", "go_exe", "php_ini"):
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
            "redis_port": self.redis_port,
            "vhost_suffix": self.vhost_suffix,
            "node_app_path": self.node_app_path,
            "go_app_path": self.go_app_path,
            "apache_exe": self.apache_exe,
            "mysqld_exe": self.mysqld_exe,
            "mysql_exe": self.mysql_exe,
            "php_exe": self.php_exe,
            "node_exe": self.node_exe,
            "go_exe": self.go_exe,
            "redis_exe": self.redis_exe,
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
            "redis_port": self.redis_port,
            "vhost_suffix": self.vhost_suffix,
            "node_app_path": self.node_app_path,
            "go_app_path": self.go_app_path,
            "apache_exe": self.apache_exe or "",
            "mysqld_exe": self.mysqld_exe or "",
            "mysql_exe": self.mysql_exe or "",
            "php_exe": self.php_exe or "",
            "node_exe": self.node_exe or "",
            "go_exe": self.go_exe or "",
            "redis_exe": self.redis_exe or "",
            "php_ini": self.php_ini or "",
            "www_dir": str(self.www_dir),
            "logs_dir": str(self.logs_dir),
        }

    def update_from_dict(self, data: Dict[str, Any]):
        """Update config from a dict (e.g. from settings dialog)."""
        int_fields = ("apache_port", "mysql_port", "php_port", "redis_port")
        str_fields = ("vhost_suffix", "node_app_path", "go_app_path", "apache_exe", "mysqld_exe", "mysql_exe", "php_exe", "node_exe", "go_exe", "redis_exe", "php_ini")

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
