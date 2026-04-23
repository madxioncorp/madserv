"""
Main application window for MadServ.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
from typing import Optional

from app.services.apache import ApacheService
from app.services.mysql import MySQLService
from app.services.php import PHPService
from app.services.base_service import ServiceStatus
from app.managers.vhost_manager import VHostManager
from app.managers.php_ext_manager import PHPExtManager
from app.managers.php_setting_manager import PHPSettingManager
from app.gui.services_tab import ServicesTab
from app.gui.vhost_tab import VHostTab
from app.gui.php_ext_tab import PHPExtTab


class MainWindow:
    """
    Root application window.
    Hosts a Notebook with Services, Virtual Hosts, and PHP Extensions tabs.
    """

    APP_TITLE = "MadServ v1.1.0"
    APP_VERSION = "1.1.0"
    REFRESH_INTERVAL_MS = 2000  # Status bar refresh

    def __init__(self, root: tk.Tk, config):
        self.root = root
        self.config = config

        # Instantiate services
        self.apache = ApacheService(config)
        self.mysql = MySQLService(config)
        self.php = PHPService(config)

        # Managers
        self.vhost_manager = VHostManager(config)
        self.php_ext_manager = PHPExtManager(config)
        self.php_setting_manager = PHPSettingManager(config)

        # Tray icon reference (optional)
        self._tray_icon = None

        self._setup_window()
        self._build_menu()
        self._build_toolbar()
        self._build_notebook()
        self._build_statusbar()

        # Start periodic status refresh
        self._schedule_status_refresh()

        # Attempt to set up system tray
        self._setup_tray()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _setup_window(self):
        self.root.title(self.APP_TITLE)
        self.root.geometry("900x620")
        self.root.minsize(700, 480)

        # Set window icon from embedded base64 image
        try:
            from app.gui.imagekit import Image as AppImage
            import base64
            from io import BytesIO
            from tkinter import PhotoImage

            icon_data = base64.b64decode(AppImage.icon)
            # Try to use PIL for .ico / PNG support
            try:
                from PIL import Image as PILImage, ImageTk
                img = PILImage.open(BytesIO(icon_data))
                photo = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, photo)
                # Keep reference so it's not garbage-collected
                self._icon_photo = photo
            except ImportError:
                # Fallback: try as raw PNG via tkinter PhotoImage
                photo = PhotoImage(data=AppImage.icon)
                self.root.iconphoto(True, photo)
                self._icon_photo = photo
        except Exception:
            pass

        # Style
        style = ttk.Style()
        available = style.theme_names()
        for preferred in ("clam", "alt", "default"):
            if preferred in available:
                style.theme_use(preferred)
                break

        style.configure("TNotebook.Tab", padding=[12, 6])
        style.configure("Running.TLabel", foreground="#27ae60")
        style.configure("Stopped.TLabel", foreground="#e74c3c")
        style.configure("Starting.TLabel", foreground="#f39c12")
        style.configure("NotFound.TLabel", foreground="#95a5a6")

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Settings…", command=self._open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Open www Folder", command=self._open_www)
        file_menu.add_command(label="Open Logs Folder", command=self._open_logs)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=False)
        tools_menu.add_command(label="Start All Services", command=self._start_all)
        tools_menu.add_command(label="Stop All Services", command=self._stop_all)
        tools_menu.add_separator()
        tools_menu.add_command(label="Regenerate Apache Config", command=self._regen_apache_conf)
        tools_menu.add_command(label="Regenerate VHost Configs", command=self._regen_vhosts)
        tools_menu.add_separator()
        tools_menu.add_command(label="Edit hosts file", command=self._edit_hosts)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="About MadServ", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------

    def _build_toolbar(self):
        toolbar = ttk.Frame(self.root, relief=tk.FLAT)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=4, pady=2)

        ttk.Button(
            toolbar, text="▶  Start All", command=self._start_all, width=12
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar, text="■  Stop All", command=self._stop_all, width=12
        ).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        ttk.Button(
            toolbar, text="⚙  Settings", command=self._open_settings, width=12
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar, text="📁  www", command=self._open_www, width=10
        ).pack(side=tk.LEFT, padx=2)

    # ------------------------------------------------------------------
    # Notebook / tabs
    # ------------------------------------------------------------------

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # Services tab
        services_frame = ttk.Frame(self.notebook)
        self.notebook.add(services_frame, text="  Services  ")
        self.services_tab = ServicesTab(
            services_frame,
            config=self.config,
            apache=self.apache,
            mysql=self.mysql,
            php=self.php,
        )

        # Virtual Hosts tab
        vhost_frame = ttk.Frame(self.notebook)
        self.notebook.add(vhost_frame, text="  Virtual Hosts  ")
        self.vhost_tab = VHostTab(
            vhost_frame,
            config=self.config,
            vhost_manager=self.vhost_manager,
        )

        # PHP Extensions tab
        php_ext_frame = ttk.Frame(self.notebook)
        self.notebook.add(php_ext_frame, text="  PHP Extensions  ")
        self.php_ext_tab = PHPExtTab(
            php_ext_frame,
            config=self.config,
            ext_manager=self.php_ext_manager,
            setting_manager=self.php_setting_manager,
            php_service=self.php,
        )

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_statusbar(self):
        bar = ttk.Frame(self.root, relief=tk.SUNKEN)
        bar.pack(side=tk.BOTTOM, fill=tk.X)

        self._status_labels = {}
        services = [
            ("Apache", self.apache),
            ("MySQL", self.mysql),
            ("PHP", self.php),
        ]

        for i, (label, svc) in enumerate(services):
            if i > 0:
                ttk.Separator(bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
            dot = tk.Label(bar, text="●", font=("TkDefaultFont", 10))
            dot.pack(side=tk.LEFT, padx=(6, 0))
            lbl = ttk.Label(bar, text=f"{label}: {svc.status}")
            lbl.pack(side=tk.LEFT, padx=(2, 6))
            self._status_labels[label] = (dot, lbl, svc)

        # Right side: version info
        self._version_var = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self._version_var).pack(side=tk.RIGHT, padx=8)

    def _update_statusbar(self):
        """Refresh status bar indicators."""
        color_map = {
            ServiceStatus.RUNNING: "#27ae60",
            ServiceStatus.STOPPED: "#e74c3c",
            ServiceStatus.STARTING: "#f39c12",
            ServiceStatus.STOPPING: "#f39c12",
            ServiceStatus.ERROR: "#c0392b",
            ServiceStatus.NOT_FOUND: "#95a5a6",
        }
        for label, (dot, lbl, svc) in self._status_labels.items():
            status = svc.status
            color = color_map.get(status, "#95a5a6")
            dot.config(fg=color)
            lbl.config(text=f"{label}: {status}")

    def _schedule_status_refresh(self):
        """Schedule periodic status bar refresh."""
        self._update_statusbar()
        self.root.after(self.REFRESH_INTERVAL_MS, self._schedule_status_refresh)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _start_all(self):
        threading.Thread(target=self._start_all_sync, daemon=True).start()

    def _stop_all(self):
        threading.Thread(target=self._stop_all_sync, daemon=True).start()

    def _open_www(self):
        self.vhost_manager.open_www_folder()

    def _open_logs(self):
        import subprocess
        logs = self.config.logs_dir
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", str(logs)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(logs)])
            else:
                subprocess.Popen(["xdg-open", str(logs)])
        except OSError:
            pass

    def _regen_apache_conf(self):
        self.apache._generate_httpd_conf()
        messagebox.showinfo("Done", "Apache httpd.conf regenerated.")

    def _regen_vhosts(self):
        files = self.vhost_manager.generate_vhost_configs()
        messagebox.showinfo("Done", f"Generated {len(files)} vhost config(s).")

    def _edit_hosts(self):
        self.vhost_manager.open_hosts_file()

    def _open_settings(self):
        SettingsDialog(self.root, self.config)

    def _show_about(self):
        messagebox.showinfo(
            "About MadServ",
            f"MadServ v{self.APP_VERSION}\n\n"
            "A local development environment manager\n"
            "inspired by Laragon.\n\n"
            "Built with Python + tkinter.",
        )

    # ------------------------------------------------------------------
    # Window close / tray
    # ------------------------------------------------------------------

    def _on_close(self):
        """Handle window close button — ask user: minimize to tray or exit."""
        if self._tray_icon is not None:
            # Offer choice: minimize to tray or exit
            answer = _ask_close_action(self.root)
            if answer == "tray":
                self.root.withdraw()
                return
            elif answer == "exit":
                self._quit_no_confirm()
            # else: cancelled, do nothing
        else:
            self._quit()

    def _quit_no_confirm(self):
        """Exit without asking for confirmation (used after close dialog)."""
        for svc in (self.apache, self.mysql, self.php):
            try:
                svc.stop()
            except Exception:
                pass
        if self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
            self._tray_icon = None
        try:
            self.root.destroy()
        except Exception:
            pass
        os._exit(0)

    def _quit(self):
        """Stop all services, close all resources, and exit the process."""
        if not messagebox.askyesno("Exit", "Stop all services and exit?"):
            return
        self._quit_no_confirm()

    # ------------------------------------------------------------------
    # System tray (optional – requires pystray + Pillow)
    # ------------------------------------------------------------------

    def _setup_tray(self):
        try:
            import pystray
            from PIL import Image as PILImage
            import base64
            from io import BytesIO
            from app.gui.imagekit import Image as AppImage

            icon_data = base64.b64decode(AppImage.icon)
            img = PILImage.open(BytesIO(icon_data)).convert("RGBA")

            menu = pystray.Menu(
                pystray.MenuItem("Show", self._tray_show, default=True),
                pystray.MenuItem("Hide", lambda icon, item: self.root.after(0, self.root.withdraw)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Start All", lambda icon, item: threading.Thread(target=self._start_all_sync, daemon=True).start()),
                pystray.MenuItem("Stop All",  lambda icon, item: threading.Thread(target=self._stop_all_sync,  daemon=True).start()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", lambda icon, item: self.root.after(0, self._quit)),
            )

            self._tray_icon = pystray.Icon("madserv", img, "MadServ v1.0.0", menu)
            threading.Thread(target=self._tray_icon.run, daemon=True).start()

        except ImportError:
            pass  # pystray not installed

    def _start_all_sync(self):
        for svc in (self.apache, self.mysql, self.php):
            if not svc.is_running():
                svc.start()

    def _stop_all_sync(self):
        for svc in (self.apache, self.mysql, self.php):
            if svc.is_running():
                svc.stop()

    def _tray_show(self):
        self.root.after(0, self.root.deiconify)
        self.root.after(0, self.root.lift)


# ---------------------------------------------------------------------------
# Close action dialog
# ---------------------------------------------------------------------------

def _ask_close_action(parent) -> str:
    """
    Show a dialog asking whether to minimize to tray or exit.
    Returns: 'tray', 'exit', or 'cancel'
    """
    result = {"value": "cancel"}

    dlg = tk.Toplevel(parent)
    dlg.title("Close MadServ")
    dlg.resizable(False, False)
    dlg.grab_set()
    dlg.transient(parent)

    # Centre on parent
    parent.update_idletasks()
    px, py = parent.winfo_x(), parent.winfo_y()
    pw, ph = parent.winfo_width(), parent.winfo_height()
    dlg.geometry(f"320x140+{px + pw//2 - 160}+{py + ph//2 - 70}")

    ttk.Label(dlg, text="What would you like to do?",
              font=("TkDefaultFont", 10, "bold")).pack(pady=(18, 8))

    btn_frame = ttk.Frame(dlg)
    btn_frame.pack(pady=4)

    def _tray():
        result["value"] = "tray"
        dlg.destroy()

    def _exit():
        result["value"] = "exit"
        dlg.destroy()

    def _cancel():
        result["value"] = "cancel"
        dlg.destroy()

    ttk.Button(btn_frame, text="Minimize to Tray", width=18, command=_tray).pack(side=tk.LEFT, padx=6)
    ttk.Button(btn_frame, text="Exit",             width=10, command=_exit).pack(side=tk.LEFT, padx=6)
    ttk.Button(btn_frame, text="Cancel",           width=10, command=_cancel).pack(side=tk.LEFT, padx=6)

    dlg.protocol("WM_DELETE_WINDOW", _cancel)
    dlg.wait_window()
    return result["value"]


# ---------------------------------------------------------------------------
# Settings dialog
# ---------------------------------------------------------------------------

class SettingsDialog(tk.Toplevel):
    """Settings editor dialog with browse buttons for file paths."""

    # Fields that are file paths and need a Browse button
    _FILE_FIELDS = {"apache_exe", "mysqld_exe", "mysql_exe", "php_exe", "php_ini"}

    # filedialog filter per field key
    _FILE_FILTERS = {
        "apache_exe":  [("Executable", "*.exe *.EXE httpd httpd2"), ("All files", "*.*")],
        "mysqld_exe":  [("Executable", "*.exe *.EXE mysqld"),        ("All files", "*.*")],
        "mysql_exe":   [("Executable", "*.exe *.EXE mysql"),         ("All files", "*.*")],
        "php_exe":     [("Executable", "*.exe *.EXE php"),           ("All files", "*.*")],
        "php_ini":     [("INI file",   "*.ini"),                     ("All files", "*.*")],
    }

    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        self.title("Settings")
        self.resizable(True, False)
        self.grab_set()

        self._vars: dict = {}
        self._build()
        self.transient(parent)
        self.wait_window()

    def _build(self):
        from tkinter import filedialog

        pad = {"padx": 8, "pady": 4}
        data = self.config.to_dict()

        # Two sections: plain settings and file paths
        plain_fields = [
            ("Apache Port",              "apache_port"),
            ("MySQL Port",               "mysql_port"),
            ("PHP Port (built-in server)", "php_port"),
            ("VHost Suffix",             "vhost_suffix"),
        ]
        file_fields = [
            ("Apache Executable", "apache_exe"),
            ("mysqld Executable", "mysqld_exe"),
            ("mysql Client",      "mysql_exe"),
            ("PHP Executable",    "php_exe"),
            ("php.ini Path",      "php_ini"),
        ]

        # ── Plain settings ──────────────────────────────────────────────
        plain_lf = ttk.LabelFrame(self, text="General")
        plain_lf.pack(fill=tk.X, padx=12, pady=(10, 4))

        for row, (label, key) in enumerate(plain_fields):
            ttk.Label(plain_lf, text=label + ":").grid(
                row=row, column=0, sticky=tk.W, **pad)
            var = tk.StringVar(value=str(data.get(key, "")))
            self._vars[key] = var
            ttk.Entry(plain_lf, textvariable=var, width=20).grid(
                row=row, column=1, sticky=tk.EW, **pad)

        plain_lf.columnconfigure(1, weight=1)

        # ── File path settings ──────────────────────────────────────────
        file_lf = ttk.LabelFrame(self, text="Executable / File Paths")
        file_lf.pack(fill=tk.X, padx=12, pady=(4, 4))

        for row, (label, key) in enumerate(file_fields):
            ttk.Label(file_lf, text=label + ":").grid(
                row=row, column=0, sticky=tk.W, **pad)

            var = tk.StringVar(value=str(data.get(key, "")))
            self._vars[key] = var

            entry = ttk.Entry(file_lf, textvariable=var, width=52)
            entry.grid(row=row, column=1, sticky=tk.EW, **pad)

            # Browse button — capture key in default arg to avoid closure issue
            browse_btn = ttk.Button(
                file_lf, text="…", width=3,
                command=lambda k=key, v=var: self._browse(k, v),
            )
            browse_btn.grid(row=row, column=2, padx=(0, 8), pady=4)

        file_lf.columnconfigure(1, weight=1)

        # ── Buttons ─────────────────────────────────────────────────────
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=12, pady=10)
        ttk.Button(btn_frame, text="Save",   command=self._save).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT)

    def _browse(self, key: str, var: tk.StringVar):
        """Open a file dialog and put the chosen path into var."""
        from tkinter import filedialog
        from pathlib import Path

        filetypes = self._FILE_FILTERS.get(key, [("All files", "*.*")])

        # Start in the directory of the current value if it exists
        current = var.get().strip()
        initial_dir = str(Path(current).parent) if current and Path(current).exists() else "/"

        path = filedialog.askopenfilename(
            parent=self,
            title=f"Select {key}",
            initialdir=initial_dir,
            filetypes=filetypes,
        )
        if path:
            var.set(path)

    def _save(self):
        data = {key: var.get() for key, var in self._vars.items()}
        self.config.update_from_dict(data)
        messagebox.showinfo(
            "Saved",
            "Settings saved.\nRestart services for changes to take effect.",
            parent=self,
        )
        self.destroy()
