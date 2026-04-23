"""
Node.js service manager.
Runs a Node.js application (e.g. server.js) in the www/node_app folder.
"""

import subprocess
import sys
import shutil
from pathlib import Path
from typing import List, Optional

from .base_service import BaseService, ServiceStatus


class NodeService(BaseService):
    """Manages a Node.js process."""

    def __init__(self, config):
        super().__init__(config)
        self._version_cache: Optional[str] = None
        self._available_versions: Optional[List[dict]] = None

    @property
    def name(self) -> str:
        return "Node.js"

    @property
    def version(self) -> str:
        if self._version_cache is not None:
            return self._version_cache
        exe = self.config.node_exe
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
            # Output is usually "v18.12.1"
            if output.strip().startswith("v"):
                return output.strip()[1:]
            return output.strip()
        except (OSError, subprocess.TimeoutExpired):
            pass
        return "Unknown"

    def discover_versions(self) -> List[dict]:
        """Scan common directories for Node executables."""
        if self._available_versions is not None:
            return self._available_versions

        found = {}

        # 1. Check PATH
        node_path = shutil.which("node")
        if node_path:
            found[node_path] = self._get_version(node_path)

        # 2. Check local bin/
        if self.config.bin_dir.exists():
            for sub in self.config.bin_dir.iterdir():
                if sub.is_dir() and sub.name.lower().startswith("node"):
                    exe = sub / "node.exe"
                    if exe.exists():
                        found[str(exe)] = self._get_version(str(exe))

        # 3. Check common Windows paths
        if sys.platform == "win32":
            common = [Path(r"C:\Program Files\nodejs\node.exe")]
            for p in common:
                if p.exists():
                    found[str(p)] = self._get_version(str(p))

        self._available_versions = [
            {"exe": exe, "version": ver, "path": str(Path(exe).parent)}
            for exe, ver in found.items()
        ]
        return self._available_versions

    def set_version(self, exe: str):
        """Switch to a different Node executable."""
        self.config.node_exe = exe
        self._version_cache = None
        self.config.save()

    def _build_start_command(self) -> List[str]:
        exe = self.config.node_exe
        if not exe:
            return []

        # Use configured path or fallback to default
        node_dir = Path(self.config.node_app_path)
        node_dir.mkdir(parents=True, exist_ok=True)
        
        entry_file = node_dir / "app.js"
        if not entry_file.exists():
            entry_file = node_dir / "server.js"
            
        if not entry_file.exists():
            # Create a default app.js if none exists
            self._create_default_app(entry_file)

        return [exe, str(entry_file)]

    def _create_default_app(self, path: Path):
        content = """
const http = require('http');

const hostname = '127.0.0.1';
const port = 3000;

const server = http.createServer((req, res) => {
  res.statusCode = 200;
  res.setHeader('Content-Type', 'text/plain');
  res.end('Hello from Node.js in MadServ!\\n');
});

server.listen(port, hostname, () => {
  console.log(`Server running at http://${hostname}:${port}/`);
});
"""
        try:
            path.write_text(content.strip(), encoding="utf-8")
        except OSError:
            pass

    def get_log_path(self) -> Optional[Path]:
        return self.config.logs_dir / "node_error.log"
