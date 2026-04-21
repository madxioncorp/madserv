"""
Virtual host manager.
Scans www/ for project folders and generates Apache vhost configs.
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional


class VirtualHost:
    """Represents a single virtual host entry."""

    def __init__(self, folder_name: str, doc_root: Path, suffix: str, port: int = 80):
        self.folder_name = folder_name
        self.doc_root = doc_root
        self.domain = f"{folder_name}.{suffix}"
        self.port = port

    def __repr__(self):
        return f"<VirtualHost {self.domain} -> {self.doc_root}>"

    def to_dict(self) -> Dict:
        return {
            "folder": self.folder_name,
            "domain": self.domain,
            "doc_root": str(self.doc_root),
            "port": self.port,
        }


class VHostManager:
    """
    Scans the www/ directory and manages Apache virtual host configuration files.
    """

    def __init__(self, config):
        self.config = config

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def scan(self) -> List[VirtualHost]:
        """
        Scan www/ directory and return a list of VirtualHost objects,
        one per subdirectory found.
        """
        www = self.config.www_dir
        if not www.exists():
            return []

        vhosts = []
        for entry in sorted(www.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                vhost = VirtualHost(
                    folder_name=entry.name,
                    doc_root=entry,
                    suffix=self.config.vhost_suffix,
                    port=self.config.apache_port,
                )
                vhosts.append(vhost)
        return vhosts

    # ------------------------------------------------------------------
    # Config generation
    # ------------------------------------------------------------------

    def generate_vhost_configs(self) -> List[str]:
        """
        Generate an Apache .conf file for each virtual host.
        Returns a list of generated file paths.
        """
        template_path = self.config.vhost_conf_template
        if not template_path.exists():
            print("[VHostManager] vhost.conf.template not found.")
            return []

        try:
            template = template_path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"[VHostManager] Cannot read template: {e}")
            return []

        vhosts_dir = self.config.apache_vhosts_dir
        vhosts_dir.mkdir(parents=True, exist_ok=True)

        generated = []
        logs_dir = str(self.config.logs_dir).replace("\\", "/")

        for vhost in self.scan():
            conf_content = template.format(
                domain=vhost.domain,
                docroot=str(vhost.doc_root).replace("\\", "/"),
                port=vhost.port,
                logs_dir=logs_dir,
            )
            conf_file = vhosts_dir / f"{vhost.folder_name}.conf"
            try:
                conf_file.write_text(conf_content, encoding="utf-8")
                generated.append(str(conf_file))
            except OSError as e:
                print(f"[VHostManager] Cannot write {conf_file}: {e}")

        return generated

    def remove_vhost_config(self, folder_name: str) -> bool:
        """Remove the vhost config file for a given folder."""
        conf_file = self.config.apache_vhosts_dir / f"{folder_name}.conf"
        if conf_file.exists():
            try:
                conf_file.unlink()
                return True
            except OSError:
                return False
        return False

    # ------------------------------------------------------------------
    # Hosts file helpers
    # ------------------------------------------------------------------

    def get_hosts_entries(self) -> str:
        """
        Return the /etc/hosts (or C:\\Windows\\System32\\drivers\\etc\\hosts)
        entries the user needs to add manually.
        """
        lines = ["# Add these lines to your hosts file:", "# (requires administrator/root privileges)", ""]
        for vhost in self.scan():
            lines.append(f"127.0.0.1    {vhost.domain}")
        return "\n".join(lines)

    @staticmethod
    def get_hosts_file_path() -> Path:
        """Return the OS-appropriate hosts file path."""
        import sys
        if sys.platform == "win32":
            return Path(r"C:\Windows\System32\drivers\etc\hosts")
        return Path("/etc/hosts")

    def open_hosts_file(self) -> bool:
        """
        Attempt to open the hosts file in the default text editor.
        Returns True if the open command was issued.
        """
        import subprocess, sys
        hosts = self.get_hosts_file_path()
        try:
            if sys.platform == "win32":
                # notepad needs elevation to save; open it anyway
                subprocess.Popen(["notepad.exe", str(hosts)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-t", str(hosts)])
            else:
                editor = os.environ.get("EDITOR", "xdg-open")
                subprocess.Popen([editor, str(hosts)])
            return True
        except OSError:
            return False

    # ------------------------------------------------------------------
    # www folder helpers
    # ------------------------------------------------------------------

    def open_www_folder(self) -> bool:
        """Open the www/ directory in the system file manager."""
        import subprocess, sys
        www = self.config.www_dir
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", str(www)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(www)])
            else:
                subprocess.Popen(["xdg-open", str(www)])
            return True
        except OSError:
            return False

    def create_project(self, name: str) -> Optional[Path]:
        """
        Create a new project folder in www/ with a starter index.php.
        Returns the created path, or None on failure.
        """
        # Sanitise name
        safe_name = "".join(c for c in name if c.isalnum() or c in "-_").lower()
        if not safe_name:
            return None

        project_dir = self.config.www_dir / safe_name
        if project_dir.exists():
            return project_dir  # Already exists

        try:
            project_dir.mkdir(parents=True)
            index = project_dir / "index.php"
            index.write_text(
                f"<?php\necho '<h1>Welcome to {safe_name}</h1>';\n",
                encoding="utf-8",
            )
            return project_dir
        except OSError as e:
            print(f"[VHostManager] Cannot create project: {e}")
            return None
