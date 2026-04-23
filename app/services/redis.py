"""
Redis service manager.
Runs redis-server with auto-generated configuration.
"""

import subprocess
import sys
import re
import os
import shutil
from pathlib import Path
from typing import List, Optional

from .base_service import BaseService, ServiceStatus


class RedisService(BaseService):
    """Manages a Redis server process."""

    def __init__(self, config):
        super().__init__(config)
        self._version_cache: Optional[str] = None
        self._available_versions: Optional[List[dict]] = None

    @property
    def name(self) -> str:
        return "Redis"

    @property
    def version(self) -> str:
        if self._version_cache is not None:
            return self._version_cache
        exe = self.config.redis_exe
        if not exe:
            return "Not Found"
        ver = self._get_version(exe)
        self._version_cache = ver
        return ver

    def _get_version(self, exe: str) -> str:
        try:
            result = subprocess.run(
                [exe, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            output = result.stdout + result.stderr
            # Output: Redis server v=3.0.504 sha=00000000:0 malloc=jemalloc-3.6.0 bits=64
            match = re.search(r"v=(\d+\.\d+\.\d+)", output)
            if match:
                return match.group(1)
        except (OSError, subprocess.TimeoutExpired):
            pass
        return "Unknown"

    def discover_versions(self) -> List[dict]:
        """Scan common directories for Redis executables."""
        if self._available_versions is not None:
            return self._available_versions

        found = {}

        # 1. Check PATH
        redis_path = shutil.which("redis-server")
        if redis_path:
            found[redis_path] = self._get_version(redis_path)

        # 2. Check local bin/
        if self.config.bin_dir.exists():
            for sub in self.config.bin_dir.iterdir():
                if sub.is_dir() and sub.name.lower().startswith("redis"):
                    exe = sub / "redis-server.exe"
                    if exe.exists():
                        found[str(exe)] = self._get_version(str(exe))

        # 3. Check common Windows paths
        if sys.platform == "win32":
            common = [
                Path(r"C:\Program Files\Redis\redis-server.exe"),
                Path(r"C:\Redis\redis-server.exe")
            ]
            for p in common:
                if p.exists():
                    found[str(p)] = self._get_version(str(p))

        self._available_versions = [
            {"exe": exe, "version": ver, "path": str(Path(exe).parent)}
            for exe, ver in found.items()
        ]
        return self._available_versions

    def set_version(self, exe: str):
        """Switch to a different Redis executable."""
        self.config.redis_exe = exe
        self._version_cache = None
        self.config.save()

    def _build_start_command(self) -> List[str]:
        exe = self.config.redis_exe
        if not exe:
            return []

        conf_path = self._ensure_config()
        
        # MSYS2-based Redis on Windows often struggles with absolute paths 
        # when passed as arguments (it may try to prepend its own root).
        # Using a relative path from the executable's directory is more reliable.
        try:
            exe_dir = Path(exe).parent
            rel_conf = os.path.relpath(conf_path, exe_dir)
            return [exe, rel_conf]
        except (ValueError, OSError):
            return [exe, str(conf_path)]

    def _ensure_config(self) -> Path:
        """Create a basic redis.conf if missing."""
        conf_dir = self.config.config_dir / "redis"
        conf_dir.mkdir(parents=True, exist_ok=True)
        conf_path = conf_dir / "redis.conf"

        # MSYS2-based Redis on Windows often struggles with absolute paths.
        # We use relative paths from the executable's directory.
        exe_dir = Path(self.config.redis_exe).parent if self.config.redis_exe else None

        if not conf_path.exists():
            if exe_dir:
                try:
                    log_path_str = os.path.relpath(self.get_log_path(), exe_dir).replace("\\", "/")
                    www_dir_str = os.path.relpath(self.config.www_dir, exe_dir).replace("\\", "/")
                except (ValueError, OSError):
                    log_path_str = str(self.get_log_path()).replace("\\", "/")
                    www_dir_str = str(self.config.www_dir).replace("\\", "/")
            else:
                log_path_str = str(self.get_log_path()).replace("\\", "/")
                www_dir_str = str(self.config.www_dir).replace("\\", "/")

            content = f"""
# MadServ - Redis configuration
port {self.config.redis_port}
bind 127.0.0.1
loglevel notice
logfile "{log_path_str}"
dir "{www_dir_str}"
"""
            try:
                conf_path.write_text(content.strip(), encoding="utf-8")
            except OSError:
                pass
        
        return conf_path

    def get_log_path(self) -> Optional[Path]:
        return self.config.logs_dir / "redis_error.log"
