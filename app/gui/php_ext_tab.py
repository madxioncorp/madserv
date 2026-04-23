"""
PHP Extensions tab – enable/disable PHP extensions via php.ini.
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List

from app.managers.php_ext_manager import PHPExtension, PHPExtManager


class PHPExtTab:
    """
    Displays all PHP extensions with checkboxes to enable/disable them.
    Changes are applied to php.ini when the user clicks "Apply Changes".
    """

    def __init__(self, parent: ttk.Frame, config, ext_manager: PHPExtManager, 
                 setting_manager, php_service):
        self.parent = parent
        self.config = config
        self.ext_manager = ext_manager
        self.setting_manager = setting_manager
        self.php_service = php_service

        # {ext_name: BooleanVar}
        self._check_vars: Dict[str, tk.BooleanVar] = {}
        # {ext_name: original_enabled}
        self._original_states: Dict[str, bool] = {}
        
        # {setting_key: StringVar}
        self._setting_vars: Dict[str, tk.StringVar] = {}
        # {setting_key: original_value}
        self._original_settings: Dict[str, str] = {}

        self._build(parent)
        self._load_all()

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build(self, parent: ttk.Frame):
        # Top bar
        top = ttk.Frame(parent)
        top.pack(fill=tk.X, padx=8, pady=(8, 4))

        ttk.Label(top, text="PHP Extensions", font=("TkDefaultFont", 12, "bold")).pack(
            side=tk.LEFT
        )

        # php.ini path label
        self.ini_var = tk.StringVar(value=self.config.php_ini or "php.ini not found")
        ttk.Label(top, textvariable=self.ini_var, foreground="#888",
                  font=("TkDefaultFont", 8)).pack(side=tk.LEFT, padx=12)

        # Reload PHP button
        ttk.Button(top, text="↺ Reload PHP", command=self._reload_php).pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(top, text="✔ Apply Changes", command=self._apply_changes).pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(top, text="↺ Refresh List", command=self._load_all).pack(
            side=tk.RIGHT, padx=4
        )

        # ── General PHP Settings ──────────────────────────────────────────
        settings_frame = ttk.LabelFrame(parent, text="General Settings")
        settings_frame.pack(fill=tk.X, padx=8, pady=4)

        pad = {"padx": 10, "pady": 5}
        
        # Row 1: upload_max_filesize and post_max_size
        ttk.Label(settings_frame, text="upload_max_filesize:").grid(row=0, column=0, sticky=tk.W, **pad)
        u_var = tk.StringVar()
        u_var.trace_add("write", lambda *args: self._on_setting_change())
        self._setting_vars["upload_max_filesize"] = u_var
        ttk.Entry(settings_frame, textvariable=u_var, width=10).grid(row=0, column=1, sticky=tk.W, **pad)
        ttk.Label(settings_frame, text="(e.g. 10M, 2G)", foreground="#888").grid(row=0, column=2, sticky=tk.W, **pad)

        ttk.Label(settings_frame, text="post_max_size:").grid(row=0, column=3, sticky=tk.W, **pad)
        p_var = tk.StringVar()
        p_var.trace_add("write", lambda *args: self._on_setting_change())
        self._setting_vars["post_max_size"] = p_var
        ttk.Entry(settings_frame, textvariable=p_var, width=10).grid(row=0, column=4, sticky=tk.W, **pad)
        ttk.Label(settings_frame, text="(e.g. 12M, 2G)", foreground="#888").grid(row=0, column=5, sticky=tk.W, **pad)

        # Search bar
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, padx=8, pady=4)

        ttk.Label(search_frame, text="🔍 Filter:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=6)

        ttk.Button(search_frame, text="✕", width=3,
                   command=lambda: self.search_var.set("")).pack(side=tk.LEFT)

        # Stats label
        self.stats_var = tk.StringVar(value="")
        ttk.Label(search_frame, textvariable=self.stats_var, foreground="#666").pack(
            side=tk.RIGHT, padx=8
        )

        # Scrollable extension list
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Canvas + scrollbar for the checkbox list
        self.canvas = tk.Canvas(list_frame, highlightthickness=0)
        vsb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.inner_frame = ttk.Frame(self.canvas)
        self._canvas_window = self.canvas.create_window(
            (0, 0), window=self.inner_frame, anchor=tk.NW
        )

        self.inner_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

        # Bottom action bar
        bottom = ttk.Frame(parent)
        bottom.pack(fill=tk.X, padx=8, pady=(0, 8))

        ttk.Button(bottom, text="Enable All Visible", command=self._enable_all_visible).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(bottom, text="Disable All Visible", command=self._disable_all_visible).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(bottom, text="Reset Changes", command=self._reset_changes).pack(
            side=tk.LEFT, padx=4
        )

        # Change indicator
        self.change_var = tk.StringVar(value="")
        ttk.Label(bottom, textvariable=self.change_var, foreground="#e67e22").pack(
            side=tk.RIGHT, padx=8
        )

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_all(self):
        """Load extensions and settings from php.ini."""
        self.ini_var.set(self.config.php_ini or "php.ini not found")

        def _do():
            # Load extensions
            self.ext_manager.reload()
            grouped = self.ext_manager.get_extensions_by_category()
            
            # Load settings
            self.setting_manager.load()
            settings = {
                key: self.setting_manager.get_setting(key) or ""
                for key in self._setting_vars.keys()
            }
            
            # Schedule GUI update on main thread
            self.parent.after(0, lambda: self._populate_all(grouped, settings))

        threading.Thread(target=_do, daemon=True).start()

    def _populate_all(self, grouped: Dict[str, List[PHPExtension]], settings: Dict[str, str]):
        """Populate the scrollable list and setting fields."""
        # 1. Update Settings
        self._original_settings.clear()
        for key, value in settings.items():
            self._setting_vars[key].set(value)
            self._original_settings[key] = value

        # 2. Update Extensions
        # Clear existing widgets
        for widget in self.inner_frame.winfo_children():
            widget.destroy()
        self._check_vars.clear()
        self._original_states.clear()

        if not grouped:
            ttk.Label(
                self.inner_frame,
                text="No extensions found.\nMake sure php.ini path is configured correctly.",
                foreground="#888",
            ).pack(padx=20, pady=20)
            self.stats_var.set("")
            return

        total = 0
        enabled_count = 0

        for category, extensions in grouped.items():
            # Category header
            cat_frame = ttk.Frame(self.inner_frame)
            cat_frame.pack(fill=tk.X, padx=4, pady=(8, 2))

            ttk.Label(
                cat_frame,
                text=f"  {category}",
                font=("TkDefaultFont", 9, "bold"),
                foreground="#555",
            ).pack(side=tk.LEFT)
            ttk.Separator(cat_frame, orient=tk.HORIZONTAL).pack(
                side=tk.LEFT, fill=tk.X, expand=True, padx=8
            )

            # Extension checkboxes in a grid
            grid_frame = ttk.Frame(self.inner_frame)
            grid_frame.pack(fill=tk.X, padx=16, pady=2)

            for col_idx, ext in enumerate(extensions):
                var = tk.BooleanVar(value=ext.enabled)
                self._check_vars[ext.name] = var
                self._original_states[ext.name] = ext.enabled

                cb = ttk.Checkbutton(
                    grid_frame,
                    text=ext.name,
                    variable=var,
                    command=self._on_check_change,
                )
                row_idx = col_idx // 3
                col_pos = col_idx % 3
                cb.grid(row=row_idx, column=col_pos, sticky=tk.W, padx=4, pady=1)

                total += 1
                if ext.enabled:
                    enabled_count += 1

        self.stats_var.set(f"{enabled_count} enabled / {total} total")
        self._update_change_indicator()

    # ------------------------------------------------------------------
    # Search / filter
    # ------------------------------------------------------------------

    def _on_search(self, *args):
        query = self.search_var.get().lower().strip()
        for widget in self.inner_frame.winfo_children():
            if isinstance(widget, ttk.Frame):
                # Check if this is a grid frame (contains checkbuttons)
                children = widget.winfo_children()
                if children and isinstance(children[0], ttk.Checkbutton):
                    visible = False
                    for cb in children:
                        if isinstance(cb, ttk.Checkbutton):
                            text = cb.cget("text").lower()
                            if not query or query in text:
                                cb.grid()
                                visible = True
                            else:
                                cb.grid_remove()
                    # Hide the category header if no extensions visible
                    # (header is the frame before this one)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_check_change(self):
        self._update_change_indicator()

    def _on_setting_change(self):
        self._update_change_indicator()

    def _update_change_indicator(self):
        ext_changes = self._get_pending_ext_changes()
        set_changes = self._get_pending_setting_changes()
        total = len(ext_changes) + len(set_changes)
        
        if total > 0:
            self.change_var.set(f"⚠ {total} unsaved change(s)")
        else:
            self.change_var.set("")

    def _get_pending_ext_changes(self) -> Dict[str, bool]:
        """Return {name: new_state} for extensions whose state has changed."""
        changes = {}
        for name, var in self._check_vars.items():
            new_val = var.get()
            if new_val != self._original_states.get(name, new_val):
                changes[name] = new_val
        return changes

    def _get_pending_setting_changes(self) -> Dict[str, str]:
        """Return {key: new_value} for settings that have changed."""
        changes = {}
        for key, var in self._setting_vars.items():
            new_val = var.get().strip()
            if new_val != self._original_settings.get(key, ""):
                changes[key] = new_val
        return changes

    def _apply_changes(self):
        ext_changes = self._get_pending_ext_changes()
        set_changes = self._get_pending_setting_changes()
        
        if not ext_changes and not set_changes:
            return

        def _do():
            errors = []
            changed_count = 0
            
            # Apply extension changes
            if ext_changes:
                count, errs = self.ext_manager.apply_changes(ext_changes)
                changed_count += count
                errors.extend(errs)
            
            # Apply setting changes
            if set_changes:
                count, errs = self.setting_manager.set_settings(set_changes)
                changed_count += count
                errors.extend(errs)

            def _done():
                if errors:
                    messagebox.showerror("Error", "\n".join(errors))
                
                if changed_count > 0:
                    self._load_all()  # Refresh everything
                    messagebox.showinfo(
                        "Success",
                        f"Applied {changed_count} change(s) to php.ini.\n"
                        "Restart Apache/PHP for changes to take effect.",
                    )
                else:
                    self._update_change_indicator()

            self.parent.after(0, _done)

        threading.Thread(target=_do, daemon=True).start()

    def _reload_php(self):
        """Restart the PHP service."""
        def _do():
            self.php_service.restart()
        threading.Thread(target=_do, daemon=True).start()
        messagebox.showinfo("PHP", "PHP service restart initiated.")

    def _enable_all_visible(self):
        for name, var in self._check_vars.items():
            var.set(True)
        self._update_change_indicator()

    def _disable_all_visible(self):
        for name, var in self._check_vars.items():
            var.set(False)
        self._update_change_indicator()

    def _reset_changes(self):
        # Reset extensions
        for name, var in self._check_vars.items():
            var.set(self._original_states.get(name, False))
        
        # Reset settings
        for key, var in self._setting_vars.items():
            var.set(self._original_settings.get(key, ""))
            
        self._update_change_indicator()

    # ------------------------------------------------------------------
    # Canvas scroll helpers
    # ------------------------------------------------------------------

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
