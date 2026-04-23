"""
Services tab – shows Apache, MySQL, PHP with start/stop/restart controls.
"""

import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
from pathlib import Path
from typing import Dict, List

from app.services.base_service import BaseService, ServiceStatus


# ── Status colours ──────────────────────────────────────────────────────────
STATUS_DOT_COLOR: Dict[str, str] = {
    ServiceStatus.RUNNING:   "#27ae60",   # green
    ServiceStatus.STOPPED:   "#e74c3c",   # red
    ServiceStatus.STARTING:  "#f39c12",   # orange
    ServiceStatus.INITIALIZING: "#f39c12", # orange
    ServiceStatus.STOPPING:  "#f39c12",   # orange
    ServiceStatus.ERROR:     "#c0392b",   # dark red
    ServiceStatus.NOT_FOUND: "#95a5a6",   # grey
}

STATUS_LABEL_COLOR: Dict[str, str] = {
    ServiceStatus.RUNNING:   "#27ae60",
    ServiceStatus.STOPPED:   "#e74c3c",
    ServiceStatus.STARTING:  "#e67e22",
    ServiceStatus.INITIALIZING: "#e67e22",
    ServiceStatus.STOPPING:  "#e67e22",
    ServiceStatus.ERROR:     "#c0392b",
    ServiceStatus.NOT_FOUND: "#7f8c8d",
}

# ── Button colour profiles  (bg, fg, active_bg) ─────────────────────────────
_BTN = {
    "start":   {"bg": "#27ae60", "fg": "white", "active": "#219a52"},
    "stop":    {"bg": "#e74c3c", "fg": "white", "active": "#c0392b"},
    "restart": {"bg": "#2980b9", "fg": "white", "active": "#2471a3"},
    "logs":    {"bg": "#7f8c8d", "fg": "white", "active": "#6c7a7d"},
}


def _colored_btn(parent, label: str, key: str, command) -> tk.Button:
    """Create a flat coloured tk.Button (not ttk, so bg/fg work on Windows)."""
    c = _BTN[key]
    btn = tk.Button(
        parent,
        text=label,
        command=command,
        bg=c["bg"],
        fg=c["fg"],
        activebackground=c["active"],
        activeforeground="white",
        relief=tk.FLAT,
        bd=0,
        padx=10,
        pady=3,
        cursor="hand2",
        font=("TkDefaultFont", 9),
    )
    return btn


# ── ServiceRow ───────────────────────────────────────────────────────────────

class ServiceRow:
    """One row in the services table."""

    def __init__(self, parent_frame: ttk.Frame, service: BaseService,
                 row: int, config):
        self.service = service
        self.config  = config
        pad = {"padx": 6, "pady": 6}

        # ── Status dot ──────────────────────────────────────────────────
        self.dot = tk.Label(
            parent_frame, text="●",
            font=("TkDefaultFont", 16),
            fg=STATUS_DOT_COLOR.get(service.status, "#95a5a6"),
        )
        self.dot.grid(row=row, column=0, **pad)

        # ── Service name ────────────────────────────────────────────────
        ttk.Label(
            parent_frame, text=service.name,
            font=("TkDefaultFont", 10, "bold"),
        ).grid(row=row, column=1, sticky=tk.W, **pad)

        # ── Status label ────────────────────────────────────────────────
        self.status_var = tk.StringVar(value=service.status)
        self.status_lbl = tk.Label(
            parent_frame,
            textvariable=self.status_var,
            width=12,
            font=("TkDefaultFont", 9, "bold"),
            fg=STATUS_LABEL_COLOR.get(service.status, "#7f8c8d"),
            anchor=tk.W,
        )
        self.status_lbl.grid(row=row, column=2, sticky=tk.W, **pad)

        # ── Port ────────────────────────────────────────────────────────
        self.port_var = tk.StringVar(value=self._get_port())
        ttk.Label(parent_frame, textvariable=self.port_var, width=8).grid(
            row=row, column=3, **pad
        )

        # ── Version ─────────────────────────────────────────────────────
        self.version_var = tk.StringVar(value="…")
        ttk.Label(parent_frame, textvariable=self.version_var, width=16).grid(
            row=row, column=4, **pad
        )

        # ── Action buttons ───────────────────────────────────────────────
        btn_frame = tk.Frame(parent_frame)
        btn_frame.grid(row=row, column=5, **pad)

        self.start_btn   = _colored_btn(btn_frame, "▶ Start",   "start",   self._start)
        self.stop_btn    = _colored_btn(btn_frame, "■ Stop",    "stop",    self._stop)
        self.restart_btn = _colored_btn(btn_frame, "↺ Restart", "restart", self._restart)
        self.log_btn     = _colored_btn(btn_frame, "📋 Logs",   "logs",    self._show_logs)

        for btn in (self.start_btn, self.stop_btn, self.restart_btn, self.log_btn):
            btn.pack(side=tk.LEFT, padx=3)

        # Register callback so service thread can trigger GUI refresh
        service.add_status_callback(self._on_status_change)

        # Initial paint
        self.refresh(fetch_version=True)

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _get_port(self) -> str:
        name = self.service.name
        if name == "Apache":  return str(self.config.apache_port)
        if name == "MySQL":   return str(self.config.mysql_port)
        if name == "PHP":     return str(self.config.php_port)
        if name == "Redis":   return str(self.config.redis_port)
        if name == "Node.js": return "3000"
        if name == "Go":      return "8080"
        return "—"

    # ── Refresh ──────────────────────────────────────────────────────────────

    def refresh(self, fetch_version: bool = False):
        """Repaint all widgets to reflect current service state."""
        status  = self.service.status
        running = self.service.is_running()

        # Dot colour
        dot_color = STATUS_DOT_COLOR.get(status, "#95a5a6")
        self.dot.config(fg=dot_color)

        # Status label text + colour
        self.status_var.set(status)
        lbl_color = STATUS_LABEL_COLOR.get(status, "#7f8c8d")
        self.status_lbl.config(fg=lbl_color)

        # Port (may change if settings were updated)
        self.port_var.set(self._get_port())

        # Version (background fetch, once)
        if fetch_version:
            threading.Thread(target=self._fetch_version, daemon=True).start()

        # ── Button state + colour ────────────────────────────────────────
        transitioning = status in (ServiceStatus.STARTING, ServiceStatus.INITIALIZING, ServiceStatus.STOPPING)

        if running:
            # Running → Start disabled (greyed), Stop & Restart enabled
            self._set_btn(self.start_btn,   enabled=False, key="start")
            self._set_btn(self.stop_btn,    enabled=True,  key="stop")
            self._set_btn(self.restart_btn, enabled=True,  key="restart")
        elif transitioning:
            # Mid-transition → all action buttons disabled
            self._set_btn(self.start_btn,   enabled=False, key="start")
            self._set_btn(self.stop_btn,    enabled=False, key="stop")
            self._set_btn(self.restart_btn, enabled=False, key="restart")
        else:
            # Stopped / Error / Not Found → Start enabled, Stop & Restart disabled
            not_found = status == ServiceStatus.NOT_FOUND
            self._set_btn(self.start_btn,   enabled=not not_found, key="start")
            self._set_btn(self.stop_btn,    enabled=False,         key="stop")
            self._set_btn(self.restart_btn, enabled=False,         key="restart")

    @staticmethod
    def _set_btn(btn: tk.Button, enabled: bool, key: str):
        """Enable/disable a coloured button, adjusting colours accordingly."""
        c = _BTN[key]
        if enabled:
            btn.config(
                state=tk.NORMAL,
                bg=c["bg"],
                fg=c["fg"],
                activebackground=c["active"],
                cursor="hand2",
            )
        else:
            btn.config(
                state=tk.DISABLED,
                bg="#bdc3c7",       # flat grey when disabled
                fg="#7f8c8d",
                activebackground="#bdc3c7",
                cursor="",
            )

    def _fetch_version(self):
        ver = self.service.version
        try:
            self.dot.after(0, lambda: self.version_var.set(ver))
        except tk.TclError:
            pass

    def _on_status_change(self, status: str):
        """Called from service thread → schedule refresh on main thread."""
        try:
            self.dot.after(0, self.refresh)
        except tk.TclError:
            pass

    # ── Button handlers ──────────────────────────────────────────────────────

    def _start(self):
        threading.Thread(target=self.service.start, daemon=True).start()

    def _stop(self):
        threading.Thread(target=self.service.stop, daemon=True).start()

    def _restart(self):
        threading.Thread(target=self.service.restart, daemon=True).start()

    def _show_logs(self):
        LogViewer(self.dot.winfo_toplevel(), self.service.name,
                  self.service.get_log_path())


# ── ServicesTab ──────────────────────────────────────────────────────────────

class ServicesTab:
    REFRESH_MS = 2000

    def __init__(self, parent: ttk.Frame, config, apache, mysql, php, node, go, redis):
        self.parent   = parent
        self.config   = config
        self.services = [apache, mysql, php, redis, node, go]
        self._rows: List[ServiceRow] = []
        self._build(parent)
        self._schedule_refresh()

    def _build(self, parent: ttk.Frame):
        # Header
        hdr = ttk.Frame(parent)
        hdr.pack(fill=tk.X, padx=8, pady=(8, 0))
        ttk.Label(hdr, text="Services",
                  font=("TkDefaultFont", 12, "bold")).pack(side=tk.LEFT)

        # Table
        outer = ttk.LabelFrame(parent, text="")
        outer.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        table = ttk.Frame(outer)
        table.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        headers   = ["",   "Service", "Status", "Port", "Version", "Actions"]
        col_widths = [30,   90,        110,      60,     130,       340]
        for col, (h, w) in enumerate(zip(headers, col_widths)):
            ttk.Label(table, text=h,
                      font=("TkDefaultFont", 9, "bold"),
                      foreground="#555").grid(
                row=0, column=col, padx=6, pady=2, sticky=tk.W)
            table.columnconfigure(col, minsize=w)

        ttk.Separator(table, orient=tk.HORIZONTAL).grid(
            row=1, column=0, columnspan=len(headers), sticky=tk.EW, pady=2)

        for i, svc in enumerate(self.services):
            self._rows.append(ServiceRow(table, svc, i + 2, self.config))

        # Bottom bar
        bar = ttk.Frame(parent)
        bar.pack(fill=tk.X, padx=8, pady=(0, 8))

        for label, cmd in [
            ("▶  Start All",   self._start_all),
            ("■  Stop All",    self._stop_all),
            ("↺  Restart All", self._restart_all),
        ]:
            ttk.Button(bar, text=label, command=cmd, width=14).pack(
                side=tk.LEFT, padx=4)

        # Activity log
        log_frame = ttk.LabelFrame(parent, text="Activity Log")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=6, state=tk.DISABLED,
            font=("Courier", 9),
            background="#1e1e1e", foreground="#d4d4d4",
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        for svc in self.services:
            svc.add_log_callback(self._append_log)

    # ── Log ──────────────────────────────────────────────────────────────────

    def _append_log(self, message: str):
        def _do():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        try:
            self.log_text.after(0, _do)
        except tk.TclError:
            pass

    # ── Refresh loop ─────────────────────────────────────────────────────────

    def _refresh_all(self):
        for row in self._rows:
            row.refresh()

    def _schedule_refresh(self):
        self._refresh_all()
        self.parent.after(self.REFRESH_MS, self._schedule_refresh)

    # ── Bulk actions ─────────────────────────────────────────────────────────

    def _start_all(self):
        def _run():
            for svc in self.services:
                if not svc.is_running():
                    svc.start()
        threading.Thread(target=_run, daemon=True).start()

    def _stop_all(self):
        def _run():
            for svc in self.services:
                if svc.is_running():
                    svc.stop()
        threading.Thread(target=_run, daemon=True).start()

    def _restart_all(self):
        def _run():
            for svc in self.services:
                svc.restart()
        threading.Thread(target=_run, daemon=True).start()


# ── LogViewer ────────────────────────────────────────────────────────────────

class LogViewer(tk.Toplevel):
    def __init__(self, parent, service_name: str, log_path):
        super().__init__(parent)
        self.title(f"{service_name} – Log")
        self.geometry("800x500")
        self.log_path = log_path
        self._build()
        self._load()

    def _build(self):
        bar = ttk.Frame(self)
        bar.pack(fill=tk.X, padx=4, pady=4)
        ttk.Button(bar, text="Refresh",    command=self._load).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="Clear View", command=self._clear).pack(side=tk.LEFT, padx=4)
        if self.log_path:
            ttk.Label(bar, text=str(self.log_path),
                      foreground="#888").pack(side=tk.LEFT, padx=8)

        self.text = scrolledtext.ScrolledText(
            self, font=("Courier", 9),
            background="#1e1e1e", foreground="#d4d4d4",
            state=tk.DISABLED,
        )
        self.text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def _load(self):
        self.text.config(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        if self.log_path is None:
            self.text.insert(tk.END, "No log file configured for this service.\n")
        else:
            p = Path(self.log_path)
            if p.exists():
                try:
                    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
                    self.text.insert(tk.END, "\n".join(lines[-500:]))
                    self.text.see(tk.END)
                except OSError as e:
                    self.text.insert(tk.END, f"Cannot read log: {e}\n")
            else:
                self.text.insert(tk.END, f"Log file not found:\n{p}\n")
        self.text.config(state=tk.DISABLED)

    def _clear(self):
        self.text.config(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.config(state=tk.DISABLED)
