"""
Virtual Hosts tab – lists www/ folders as virtual hosts.
"""

import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import List

from app.managers.vhost_manager import VirtualHost, VHostManager


class VHostTab:
    """
    Displays virtual hosts derived from www/ subdirectories.
    """

    def __init__(self, parent: ttk.Frame, config, vhost_manager: VHostManager):
        self.parent = parent
        self.config = config
        self.vhost_manager = vhost_manager
        self._vhosts: List[VirtualHost] = []

        self._build(parent)
        self.refresh()

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build(self, parent: ttk.Frame):
        # Top toolbar
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=8, pady=(8, 4))

        ttk.Label(toolbar, text="Virtual Hosts", font=("TkDefaultFont", 12, "bold")).pack(
            side=tk.LEFT
        )

        ttk.Button(toolbar, text="↺ Refresh", command=self.refresh).pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(toolbar, text="📁 Open www", command=self._open_www).pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(toolbar, text="+ New Project", command=self._new_project).pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(toolbar, text="⚙ Generate Configs", command=self._gen_configs).pack(
            side=tk.RIGHT, padx=4
        )

        # Treeview
        tree_frame = ttk.LabelFrame(parent, text="Detected Virtual Hosts")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        columns = ("domain", "docroot", "port")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("domain", text="Domain")
        self.tree.heading("docroot", text="Document Root")
        self.tree.heading("port", text="Port")

        self.tree.column("domain", width=200, anchor=tk.W)
        self.tree.column("docroot", width=380, anchor=tk.W)
        self.tree.column("port", width=60, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Double-click to open in browser
        self.tree.bind("<Double-1>", self._on_double_click)

        # Action buttons below tree
        action_bar = ttk.Frame(parent)
        action_bar.pack(fill=tk.X, padx=8, pady=4)

        ttk.Button(action_bar, text="🌐 Open in Browser", command=self._open_browser).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(action_bar, text="📋 Copy Domain", command=self._copy_domain).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(action_bar, text="🗑 Remove Config", command=self._remove_config).pack(
            side=tk.LEFT, padx=4
        )

        # Hosts file section
        hosts_frame = ttk.LabelFrame(parent, text="Hosts File Entries  (add these manually)")
        hosts_frame.pack(fill=tk.BOTH, padx=8, pady=(4, 8))

        hosts_toolbar = ttk.Frame(hosts_frame)
        hosts_toolbar.pack(fill=tk.X, padx=4, pady=2)

        ttk.Button(hosts_toolbar, text="📋 Copy All", command=self._copy_hosts).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(hosts_toolbar, text="✏ Edit hosts file", command=self._edit_hosts).pack(
            side=tk.LEFT, padx=4
        )

        self.hosts_text = tk.Text(
            hosts_frame,
            height=5,
            state=tk.DISABLED,
            font=("Courier", 9),
            background="#f5f5f5",
            relief=tk.FLAT,
        )
        self.hosts_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def refresh(self):
        """Rescan www/ and update the UI."""
        self._vhosts = self.vhost_manager.scan()

        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        for vhost in self._vhosts:
            self.tree.insert(
                "",
                tk.END,
                iid=vhost.folder_name,
                values=(vhost.domain, str(vhost.doc_root), vhost.port),
            )

        # Update hosts text
        entries = self.vhost_manager.get_hosts_entries()
        self.hosts_text.config(state=tk.NORMAL)
        self.hosts_text.delete("1.0", tk.END)
        self.hosts_text.insert(tk.END, entries)
        self.hosts_text.config(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _selected_vhost(self):
        sel = self.tree.selection()
        if not sel:
            return None
        folder = sel[0]
        return next((v for v in self._vhosts if v.folder_name == folder), None)

    def _on_double_click(self, event):
        self._open_browser()

    def _open_browser(self):
        vhost = self._selected_vhost()
        if vhost is None:
            messagebox.showinfo("No Selection", "Select a virtual host first.")
            return
        port = vhost.port
        url = (
            f"http://{vhost.domain}"
            if port == 80
            else f"http://{vhost.domain}:{port}"
        )
        webbrowser.open(url)

    def _copy_domain(self):
        vhost = self._selected_vhost()
        if vhost is None:
            return
        self.parent.clipboard_clear()
        self.parent.clipboard_append(vhost.domain)

    def _remove_config(self):
        vhost = self._selected_vhost()
        if vhost is None:
            messagebox.showinfo("No Selection", "Select a virtual host first.")
            return
        if messagebox.askyesno(
            "Remove Config",
            f"Remove the Apache config file for '{vhost.domain}'?\n"
            "(The www folder will NOT be deleted.)",
        ):
            self.vhost_manager.remove_vhost_config(vhost.folder_name)
            messagebox.showinfo("Done", f"Config for '{vhost.domain}' removed.")

    def _copy_hosts(self):
        entries = self.vhost_manager.get_hosts_entries()
        self.parent.clipboard_clear()
        self.parent.clipboard_append(entries)
        messagebox.showinfo("Copied", "Hosts file entries copied to clipboard.")

    def _edit_hosts(self):
        self.vhost_manager.open_hosts_file()

    def _open_www(self):
        self.vhost_manager.open_www_folder()

    def _gen_configs(self):
        files = self.vhost_manager.generate_vhost_configs()
        messagebox.showinfo(
            "Done",
            f"Generated {len(files)} vhost config file(s).\n\n"
            "Reload Apache for changes to take effect.",
        )

    def _new_project(self):
        name = simpledialog.askstring(
            "New Project",
            "Enter project folder name:",
            parent=self.parent,
        )
        if not name:
            return
        path = self.vhost_manager.create_project(name)
        if path:
            messagebox.showinfo(
                "Created",
                f"Project created at:\n{path}\n\n"
                f"Domain: {name}.{self.config.vhost_suffix}",
            )
            self.refresh()
        else:
            messagebox.showerror("Error", f"Could not create project '{name}'.")
