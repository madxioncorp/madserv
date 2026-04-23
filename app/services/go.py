"""
Go (Golang) service manager.
Runs a Go application (e.g. main.go) in the www/go_app folder.
"""

import subprocess
import sys
import re
import shutil
from pathlib import Path
from typing import List, Optional

from .base_service import BaseService, ServiceStatus


class GoService(BaseService):
    """Manages a Go process via 'go run'."""

    def __init__(self, config):
        super().__init__(config)
        self._version_cache: Optional[str] = None
        self._available_versions: Optional[List[dict]] = None

    @property
    def name(self) -> str:
        return "Go"

    @property
    def version(self) -> str:
        if self._version_cache is not None:
            return self._version_cache
        exe = self.config.go_exe
        if not exe:
            return "Not Found"
        ver = self._get_version(exe)
        self._version_cache = ver
        return ver

    def _get_version(self, exe: str) -> str:
        try:
            result = subprocess.run(
                [exe, "version"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            output = result.stdout + result.stderr
            # Output is usually "go version go1.19.3 windows/amd64"
            match = re.search(r"go(\d+\.\d+\.\d+)", output)
            if match:
                return match.group(1)
        except (OSError, subprocess.TimeoutExpired):
            pass
        return "Unknown"

    def discover_versions(self) -> List[dict]:
        """Scan common directories for Go executables."""
        if self._available_versions is not None:
            return self._available_versions

        found = {}

        # 1. Check PATH
        go_path = shutil.which("go")
        if go_path:
            found[go_path] = self._get_version(go_path)

        # 2. Check local bin/
        if self.config.bin_dir.exists():
            for sub in self.config.bin_dir.iterdir():
                if sub.is_dir() and sub.name.lower() == "go":
                    exe = sub / "bin" / "go.exe"
                    if exe.exists():
                        found[str(exe)] = self._get_version(str(exe))

        # 3. Check common Windows paths
        if sys.platform == "win32":
            common = [Path(r"C:\Program Files\Go\bin\go.exe")]
            for p in common:
                if p.exists():
                    found[str(p)] = self._get_version(str(p))

        self._available_versions = [
            {"exe": exe, "version": ver, "path": str(Path(exe).parent)}
            for exe, ver in found.items()
        ]
        return self._available_versions

    def set_version(self, exe: str):
        """Switch to a different Go executable."""
        self.config.go_exe = exe
        self._version_cache = None
        self.config.save()

    def _build_start_command(self) -> List[str]:
        exe = self.config.go_exe
        if not exe:
            return []

        # Use configured path or fallback to default
        go_dir = Path(self.config.go_app_path)
        go_dir.mkdir(parents=True, exist_ok=True)
        
        entry_file = go_dir / "main.go"
        if not entry_file.exists():
            # Create a default main.go if none exists
            self._create_default_app(entry_file)

        return [exe, "run", str(entry_file)]

    def _create_default_app(self, path: Path):
        content = """
package main

import (
	"fmt"
	"net/http"
)

func main() {
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, "Hello from Go in MadServ!")
	})

	fmt.Println("Server starting on http://localhost:8080")
	http.ListenAndServe(":8080", nil)
}
"""
        try:
            path.write_text(content.strip(), encoding="utf-8")
        except OSError:
            pass

    def get_log_path(self) -> Optional[Path]:
        return self.config.logs_dir / "go_error.log"
