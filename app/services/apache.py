"""
Apache httpd service manager.
"""

import subprocess
import sys
import re
from pathlib import Path
from typing import List, Optional

from .base_service import BaseService, ServiceStatus


class ApacheService(BaseService):
    """Manages the Apache httpd process."""

    def __init__(self, config):
        super().__init__(config)
        self._version_cache: Optional[str] = None

    # ------------------------------------------------------------------
    # BaseService interface
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "Apache"

    @property
    def version(self) -> str:
        if self._version_cache is not None:
            return self._version_cache
        exe = self.config.apache_exe
        if not exe:
            return "Not Found"
        try:
            result = subprocess.run(
                [exe, "-v"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            output = result.stdout + result.stderr
            match = re.search(r"Apache/(\S+)", output)
            if match:
                self._version_cache = match.group(1)
                return self._version_cache
        except (OSError, subprocess.TimeoutExpired):
            pass
        return "Unknown"

    def _build_start_command(self) -> List[str]:
        exe = self.config.apache_exe
        if not exe:
            return []

        # Ensure php.ini has correct extension_dir before starting
        self._fix_php_extension_dir()

        # Generate httpd.conf and all vhost configs before starting
        self._generate_httpd_conf()
        self._regenerate_vhosts()

        conf_path = self.config.httpd_conf
        if conf_path.exists():
            return [exe, "-f", str(conf_path), "-D", "FOREGROUND"]
        else:
            return [exe, "-D", "FOREGROUND"]

    # ------------------------------------------------------------------
    # Config generation
    # ------------------------------------------------------------------

    def _generate_httpd_conf(self):
        """Generate httpd.conf from template, substituting paths."""
        template_path = self.config.httpd_conf_template
        if not template_path.exists():
            self._log(f"httpd.conf.template not found at: {template_path}")
            self._log("Skipping config generation – Apache will use its own default config.")
            return

        try:
            template = template_path.read_text(encoding="utf-8")
        except OSError as e:
            self._log(f"Cannot read template: {e}")
            return

        exe = self.config.apache_exe or ""
        # ServerRoot = Apache installation root (parent of bin/)
        # e.g. .../Apache24/bin/httpd.exe  →  .../Apache24
        if exe:
            exe_path = Path(exe)
            # If exe is inside a "bin" subfolder, go up two levels; otherwise one
            if exe_path.parent.name.lower() == "bin":
                server_root = str(exe_path.parent.parent)
            else:
                server_root = str(exe_path.parent)
        else:
            server_root = str(self.config.base_dir)

        www_default = str(self.config.www_dir / "default")
        vhosts_dir  = str(self.config.apache_vhosts_dir)
        logs_dir    = str(self.config.logs_dir)
        port        = str(self.config.apache_port)

        # php directory (for mod_php LoadFile / LoadModule / PHPIniDir)
        php_exe = self.config.php_exe or ""
        php_dir = str(Path(php_exe).parent) if php_exe else ""

        # Normalise to forward slashes (Apache on Windows prefers them)
        def fwd(p: str) -> str:
            return p.replace("\\", "/")

        conf = template.format(
            server_root=fwd(server_root),
            www_default=fwd(www_default),
            vhosts_dir=fwd(vhosts_dir),
            logs_dir=fwd(logs_dir),
            port=port,
            php_dir=fwd(php_dir),
        )

        try:
            self.config.httpd_conf.write_text(conf, encoding="utf-8")
            self._log(f"Generated httpd.conf at {self.config.httpd_conf}")
        except OSError as e:
            self._log(f"Cannot write httpd.conf: {e}")

    def _fix_php_extension_dir(self):
        """Set extension_dir in php.ini to absolute path before Apache loads mod_php."""
        try:
            from app.managers.php_ext_manager import PHPExtManager
            mgr = PHPExtManager(self.config)
            if mgr.ensure_extension_dir():
                self._log("php.ini extension_dir verified/updated.")
        except Exception as e:
            self._log(f"Could not fix extension_dir: {e}")

    def _regenerate_vhosts(self):
        """Regenerate all vhost .conf files before Apache starts."""
        try:
            from app.managers.vhost_manager import VHostManager
            mgr = VHostManager(self.config)
            files = mgr.generate_vhost_configs()
            if files:
                self._log(f"Generated {len(files)} vhost config(s).")
        except Exception as e:
            self._log(f"Vhost generation error: {e}")

    def reload_config(self) -> bool:
        """Send a graceful reload signal to Apache."""
        if not self.is_running():
            self._log("Not running – cannot reload.")
            return False

        exe = self.config.apache_exe
        if not exe:
            return False

        try:
            if sys.platform == "win32":
                subprocess.run(
                    [exe, "-k", "restart"],
                    check=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                subprocess.run([exe, "-k", "graceful"], check=True)
            self._log("Config reloaded.")
            return True
        except subprocess.CalledProcessError as e:
            self._log(f"Reload failed: {e}")
            return False

    def test_config(self) -> tuple:
        """
        Test the Apache configuration.
        Returns (success: bool, output: str).
        """
        exe = self.config.apache_exe
        if not exe:
            return False, "Apache executable not found."

        conf_path = self.config.httpd_conf
        cmd = [exe, "-t"]
        if conf_path.exists():
            cmd += ["-f", str(conf_path)]

        try:
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                **kwargs,
            )
            output = (result.stdout + result.stderr).strip()
            return result.returncode == 0, output
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, str(e)

    def get_log_path(self) -> Optional[Path]:
        log = self.config.logs_dir / "apache_error.log"
        return log if log.exists() else self.config.logs_dir / "apache_error.log"
