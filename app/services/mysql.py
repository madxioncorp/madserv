"""
MySQL / MariaDB service manager.
"""

import subprocess
import sys
import re
from pathlib import Path
from typing import List, Optional

from .base_service import BaseService, ServiceStatus


class MySQLService(BaseService):
    """Manages the MySQL/MariaDB server process."""

    def __init__(self, config):
        super().__init__(config)
        self._version_cache: Optional[str] = None

    # ------------------------------------------------------------------
    # BaseService interface
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "MySQL"

    @property
    def version(self) -> str:
        if self._version_cache is not None:
            return self._version_cache

        exe = self.config.mysqld_exe or self.config.mysql_exe
        if not exe:
            return "Not Found"

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
            # Look for "Ver X.Y.Z" or "version X.Y.Z" to avoid matching version strings in the path
            match = re.search(r"(?:Ver|version)\s+(\d+\.\d+\.\d+[\w.-]*)", output, re.IGNORECASE)
            if not match:
                # Fallback to generic version match if keywords not found
                match = re.search(r"(\d+\.\d+\.\d+[\w.-]*)", output)
            
            if match:
                self._version_cache = match.group(1)
                return self._version_cache
        except (OSError, subprocess.TimeoutExpired):
            pass
        return "Unknown"

    def _build_start_command(self) -> List[str]:
        exe = self.config.mysqld_exe
        if not exe:
            return []

        # Generate my.ini from template
        self._generate_my_ini()

        # Initialize data directory if it doesn't exist
        if not self._initialize_if_needed():
            return []

        cmd = [exe]
        conf = self.config.mysql_conf
        if conf.exists():
            cmd += [f"--defaults-file={conf}"]

        cmd += [
            f"--port={self.config.mysql_port}",
            f"--log-error={self.config.logs_dir / 'mysql_error.log'}",
        ]
        return cmd

    # ------------------------------------------------------------------
    # Data directory initialization
    # ------------------------------------------------------------------

    def _get_data_dir(self) -> Path:
        """
        Return the MySQL data directory path.
        Always stored in <app_base>/data/mysql so it persists
        across MySQL version upgrades.
        """
        return self.config.base_dir / "data" / "mysql"

    def _initialize_if_needed(self) -> bool:
        """
        Run --initialize-insecure if the data directory doesn't exist.
        Returns True if ready to start, False on failure.
        """
        data_dir = self._get_data_dir()
        # Check for mysql system schema as sign of successful init
        if (data_dir / "mysql").exists():
            return True

        self._log(f"Data directory not found at: {data_dir}")
        self._log("Initializing MySQL data directory (first run)...")
        self._set_status(ServiceStatus.INITIALIZING)

        exe = self.config.mysqld_exe
        data_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            exe,
            "--initialize-insecure",
            f"--datadir={data_dir}",
            f"--log-error={self.config.logs_dir / 'mysql_init.log'}",
        ]

        try:
            env = self._clean_env()
            kwargs = {"env": env, "cwd": str(Path(exe).parent)}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            self._log(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=120,
                **kwargs,
            )

            if result.returncode == 0 and (data_dir / "mysql").exists():
                self._log("MySQL initialized successfully. Root password is empty.")
                return True
            else:
                init_log = self.config.logs_dir / "mysql_init.log"
                if init_log.exists():
                    lines = init_log.read_text(encoding="utf-8", errors="replace").splitlines()
                    for line in lines[-15:]:
                        if line.strip():
                            self._log(f"  {line.strip()}")
                self._log(f"MySQL initialization failed (code {result.returncode}).")
                return False

        except subprocess.TimeoutExpired:
            self._log("MySQL initialization timed out.")
            return False
        except OSError as e:
            self._log(f"MySQL initialization error: {e}")
            return False

    # ------------------------------------------------------------------
    # Config generation
    # ------------------------------------------------------------------

    def _generate_my_ini(self):
        """Generate my.ini from template."""
        template_path = self.config.mysql_conf_template
        if not template_path.exists():
            self._log("my.ini.template not found – skipping config generation.")
            return

        try:
            template = template_path.read_text(encoding="utf-8")
        except OSError as e:
            self._log(f"Cannot read template: {e}")
            return

        exe = self.config.mysqld_exe or ""
        mysql_base = str(Path(exe).parent.parent) if exe else ""
        # Data dir is always in <app_base>/data/mysql — persists across upgrades
        data_dir = str(self._get_data_dir())
        logs_dir = str(self.config.logs_dir)
        port = str(self.config.mysql_port)

        def fwd(p: str) -> str:
            return p.replace("\\", "/")

        conf = template.format(
            mysql_base=fwd(mysql_base),
            data_dir=fwd(data_dir),
            logs_dir=fwd(logs_dir),
            port=port,
        )

        try:
            self.config.mysql_conf.write_text(conf, encoding="utf-8")
            self._log(f"Generated my.ini at {self.config.mysql_conf}")
        except OSError as e:
            self._log(f"Cannot write my.ini: {e}")

    # ------------------------------------------------------------------
    # Extra helpers
    # ------------------------------------------------------------------

    def get_log_path(self) -> Optional[Path]:
        return self.config.logs_dir / "mysql_error.log"

    def run_query(self, query: str, database: str = "") -> tuple:
        """
        Run a SQL query via the mysql CLI client.
        Returns (success: bool, output: str).
        """
        exe = self.config.mysql_exe
        if not exe:
            return False, "mysql client not found."

        cmd = [
            exe,
            f"--port={self.config.mysql_port}",
            "--user=root",
            "--execute", query,
        ]
        if database:
            cmd.append(database)

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
