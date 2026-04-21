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

    def __init__(self, parent: ttk.Frame, config, ext_manager: PHPExtManager, php_service):
        self.parent = parent
        self.config = config
        self.ext_manager = ext_manager
        self.php_service = php_service

        # {ext_name: BooleanVar}
        self._check_vars: Dict[str, tk.BooleanVar] = {}
        # {ext_name: original_enabled}
        self._original_states: Dict[str, bool] = {}

        self._build(parent)
        self._load_extensions()

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
        ttk.Button(top, text="↺ Refresh List", command=self._load_extensions).pack(
            side=tk.RIGHT, padx=4
        )

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

    def _load_extensions(self):
        """Load extensions from php.ini in a background thread."""
        self.ini_var.set(self.config.php_ini or "php.ini not found")

        def _do():
            self.ext_manager.reload()
            grouped = self.ext_manager.get_extensions_by_category()
            # Schedule GUI update on main thread via parent widget
            self.parent.after(0, lambda: self._populate(grouped))

        threading.Thread(target=_do, daemon=True).start()

    def _populate(self, grouped: Dict[str, List[PHPExtension]]):
        """Populate the scrollable list with extension checkboxes."""
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

    def _update_change_indicator(self):
        changes = self._get_pending_changes()
        if changes:
            self.change_var.set(f"⚠ {len(changes)} unsaved change(s)")
        else:
            self.change_var.set("")

    def _get_pending_changes(self) -> Dict[str, bool]:
        """Return {name: new_state} for extensions whose state has changed."""
        changes = {}
        for name, var in self._check_vars.items():
            new_val = var.get()
            if new_val != self._original_states.get(name, new_val):
                changes[name] = new_val
        return changes

    def _apply_changes(self):
        changes = self._get_pending_changes()
        if not changes:
            messagebox.showinfo("No Changes", "No changes to apply.")
            return

        ini_path = self.config.php_ini
        if not ini_path:
            messagebox.showerror(
                "Error",
                "php.ini path is not configured.\n"
                "Set it in File → Settings.",
            )
            return

        summary = "\n".join(
            f"  {'Enable' if v else 'Disable'}: {k}" for k, v in changes.items()
        )
        if not messagebox.askyesno(
            "Apply Changes",
            f"Apply the following changes to php.ini?\n\n{summary}",
        ):
            return

        def _do():
            count, errors = self.ext_manager.apply_changes(changes)
            def _update():
                if errors:
                    messagebox.showerror(
                        "Errors",
                        f"Applied {count} change(s) with errors:\n" + "\n".join(errors),
                    )
                else:
                    messagebox.showinfo(
                        "Done",
                        f"Applied {count} change(s) to php.ini.\n"
                        "Restart PHP for changes to take effect.",
                    )
                # Update original states
                for name, val in changes.items():
                    self._original_states[name] = val
                self._update_change_indicator()
            self.parent.after(0, _update)

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
        for name, var in self._check_vars.items():
            var.set(self._original_states.get(name, False))
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
