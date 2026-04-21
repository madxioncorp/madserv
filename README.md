# PyLaragon

A local development environment manager for Windows, macOS, and Linux — inspired by [Laragon](https://laragon.org/).

Built with Python and tkinter (no external GUI dependencies required for the core app).

---

## Features

- **Apache** – Start/stop Apache httpd with auto-generated `httpd.conf`
- **MySQL / MariaDB** – Start/stop MySQL server with auto-generated `my.ini`
- **PHP** – Run PHP's built-in web server; detect multiple installed PHP versions
- **Virtual Hosts** – Auto-detect folders in `www/` and generate Apache vhost configs
- **PHP Extensions** – Enable/disable extensions by editing `php.ini` through a GUI
- **System Tray** – Minimise to tray (requires `pystray` + `Pillow`)
- **Activity Log** – Live log output from each service

---

## Requirements

- Python 3.8+
- Apache httpd, MySQL/MariaDB, and/or PHP installed separately (or via XAMPP / Laragon)

### Optional Python packages

```
pip install -r requirements.txt
```

| Package   | Purpose                        |
|-----------|--------------------------------|
| pystray   | System tray icon               |
| Pillow    | Tray icon image rendering      |
| psutil    | Enhanced process detection     |

---

## Quick Start

```bash
# Clone / download the project
cd pylaragon

# (Optional) install extras
pip install -r requirements.txt

# Run
python main.py
```

---

## Project Structure

```
pylaragon/
├── main.py                     # Entry point
├── config.json                 # Auto-created; stores your settings
├── app/
│   ├── config.py               # Paths, ports, executable detection
│   ├── services/
│   │   ├── base_service.py     # Abstract service base class
│   │   ├── apache.py           # Apache httpd manager
│   │   ├── mysql.py            # MySQL/MariaDB manager
│   │   └── php.py              # PHP built-in server manager
│   ├── managers/
│   │   ├── vhost_manager.py    # Virtual host scanning & config generation
│   │   └── php_ext_manager.py  # php.ini extension enable/disable
│   └── gui/
│       ├── main_window.py      # Root window, menu, toolbar, tray
│       ├── services_tab.py     # Services table with start/stop/restart
│       ├── vhost_tab.py        # Virtual hosts list
│       └── php_ext_tab.py      # PHP extensions checklist
├── config/
│   ├── apache/
│   │   ├── httpd.conf.template # Apache config template
│   │   └── vhost.conf.template # Per-vhost config template
│   └── mysql/
│       └── my.ini.template     # MySQL config template
├── www/
│   └── default/
│       └── index.php           # Default welcome page
├── logs/                       # Service log files
└── requirements.txt
```

---

## Configuration

On first run, PyLaragon auto-detects executables in common locations:

| Service | Checked locations |
|---------|-------------------|
| Apache  | XAMPP, Apache24, Laragon, system PATH |
| MySQL   | XAMPP, MySQL 8/5.7, Laragon, system PATH |
| PHP     | XAMPP, C:\php, Laragon, system PATH |

To override, open **File → Settings** and set the paths manually.  
Settings are saved to `config.json` in the project root.

---

## Virtual Hosts

1. Create a folder inside `www/` (e.g. `www/myapp`)
2. Click **↺ Refresh** in the Virtual Hosts tab
3. Click **⚙ Generate Configs** to write Apache vhost `.conf` files
4. Copy the hosts file entries shown and add them to your system hosts file:
   - Windows: `C:\Windows\System32\drivers\etc\hosts` (run as Administrator)
   - Linux/macOS: `/etc/hosts` (requires `sudo`)
5. Reload Apache

The domain format is `<foldername>.test` by default (configurable in Settings).

---

## PHP Extensions

1. Make sure `php.ini` path is set in **File → Settings**
2. Open the **PHP Extensions** tab
3. Check/uncheck extensions
4. Click **✔ Apply Changes**
5. Restart PHP (or Apache if using mod_php)

A backup of `php.ini` is created as `php.ini.bak` before any modification.

---

## Ports

| Service | Default Port |
|---------|-------------|
| Apache  | 80          |
| MySQL   | 3306        |
| PHP     | 8000        |

Change ports in **File → Settings**.

---

## Troubleshooting

**Service shows "Not Found"**  
→ The executable wasn't auto-detected. Set the path manually in Settings.

**Apache fails to start**  
→ Check the Activity Log. Common causes: port 80 already in use, missing modules, bad config.  
→ Use **Tools → Regenerate Apache Config** to recreate `httpd.conf`.

**PHP extensions tab is empty**  
→ Set the `php.ini` path in Settings.

**Hosts file changes don't work**  
→ You must edit the hosts file with administrator/root privileges.

---

## License

MIT
