# MadServ v1.2.0

<img width="900" height="729" alt="image" src="https://github.com/user-attachments/assets/1a02cb1e-eabc-4591-9dc7-e6036f7bc3c7" />

---

A local development environment manager for Windows — inspired by [Laragon](https://laragon.org/).

Built with Python and tkinter. No external GUI framework required for the core app.

---

## Features

- **Apache** — Start/stop Apache httpd with auto-generated `httpd.conf`. PHP executed via `mod_php` (no FastCGI daemon needed).
- **MySQL / MariaDB** — Start/stop MySQL with auto-generated `my.ini`. Auto-initializes data directory on first run.
- **PHP (built-in server)** — Run PHP's built-in web server as a standalone service.
- **Virtual Hosts** — Auto-detect folders in `www/` and generate Apache vhost configs. Domain format: `<folder>.test`.
- **PHP Extensions** — Enable/disable extensions via GUI. Edits `php.ini` directly with automatic backup. Sets `extension_dir` to absolute path automatically.
- **mod_rewrite** — Enabled by default. `.htaccess` rewrite rules work out of the box.
- **System Tray** — Minimize to tray or exit on window close (requires `pystray` + `Pillow`).
- **Colored service buttons** — Green/red/blue buttons reflect real-time service state.
- **Activity Log** — Live log output from each service in the Services tab.
- **MySQL data persistence** — Data stored in `data/mysql/` at app root, survives MySQL version upgrades.
- **Node.js & Go Support** — Run Node.js and Go (Golang) applications as standalone services.
- **Redis Support** — Run Redis server as a standalone service with automatic configuration.
- **Project Isolation** — Prepend specific binary paths (Node/Go/PHP/Redis) to the environment `PATH` for each service.
- **System PATH Management** — Easily add or remove configured binary paths to your Windows User PATH via Settings.
- **Multi-Version Manager** — Easily switch between multiple versions of PHP, Node.js, Go, and Redis via dropdown selectors.
- **Custom App Paths** — Configure custom project folders for Node.js and Go applications.
- **Improved Settings Dialog** — Organized 2-column layout for better visibility of all configurations.
- **Self-Healing Templates** — Embedded default configurations allow the app to run even if `config/` files are missing.

---

## Requirements

- Python 3.8+
- Apache httpd, MySQL/MariaDB, and/or PHP installed separately

### Optional Python packages

```bash
pip install -r requirements.txt
```

| Package  | Purpose                                    |
|----------|--------------------------------------------|
| pystray  | System tray icon                           |
| Pillow   | Tray icon + window icon rendering          |
| psutil   | Clean process tree termination             |

---

## Quick Start

```bash
# Install optional dependencies
pip install -r requirements.txt

# Run
python main.py
```

On first launch MadServ will:
- Auto-detect Apache, MySQL, and PHP from common installation paths
- Create `www/`, `logs/`, `config/`, and `data/` directories
- Generate `httpd.conf` and `my.ini` from templates
- Initialize the MySQL data directory if it doesn't exist

---

## Project Structure

```
MadServ/
├── main.py                      # Entry point
├── config.json                  # Auto-created; stores your settings
├── data/
│   └── mysql/                   # MySQL data directory (persists across upgrades)
├── www/                         # Web root — create project folders here
│   └── default/
│       └── index.php            # Default welcome page
├── logs/                        # Apache, MySQL, PHP log files
├── config/
│   ├── apache/
│   │   ├── httpd.conf           # Auto-generated Apache config
│   │   ├── httpd.conf.template  # Template for httpd.conf
│   │   ├── vhost.conf.template  # Template for per-project vhosts
│   │   └── vhosts/              # Generated vhost .conf files
│   └── mysql/
│       ├── my.ini               # Auto-generated MySQL config
│       └── my.ini.template      # Template for my.ini
└── app/
    ├── config.py                # Paths, ports, executable detection
    ├── services/
    │   ├── base_service.py      # Abstract service base (process tree kill, DLL fix, PATH injection)
    │   ├── apache.py            # Apache httpd manager
    │   ├── mysql.py             # MySQL/MariaDB manager + auto-init
    │   ├── php.py               # PHP built-in server manager
    │   ├── node.py              # Node.js service manager
    │   ├── go.py                # Go (Golang) service manager
    │   └── redis.py             # Redis server manager
    ├── managers/
    │   ├── vhost_manager.py     # Virtual host scanning & config generation
    │   ├── php_ext_manager.py   # php.ini extension enable/disable + extension_dir fix
    │   ├── php_setting_manager.py # php.ini general settings manager
    │   └── env_manager.py       # Windows System PATH management
    └── gui/
        ├── main_window.py       # Root window, menu, toolbar, tray, settings dialog
        ├── services_tab.py      # Services table with colored start/stop/restart buttons
        ├── vhost_tab.py         # Virtual hosts list
        ├── php_ext_tab.py       # PHP extensions checklist
        └── imagekit.py          # Embedded base64 app icon
```

---

## Configuration

MadServ auto-detects executables on startup from these locations:

| Service | Checked locations |
|---------|-------------------|
| Apache  | `bin/Apache24/`, XAMPP, Apache24, system PATH |
| MySQL   | `bin/mysql-*/`, XAMPP, MySQL 8/5.7, system PATH |
| PHP     | `bin/php-*/`, XAMPP, `C:\php`, system PATH |
| Node.js | `bin/node-*/`, `C:\Program Files\nodejs\`, system PATH |
| Go      | `bin/go/`, `C:\Program Files\Go\`, system PATH |
| Redis   | `bin/redis-*/`, `C:\Program Files\Redis\`, system PATH |

To override or switch versions, open **File → Settings**. Use the **Binary Version Selection** dropdowns to pick from detected versions or use the **…** browse button to set paths manually.  
The Settings dialog is organized into two columns for easier navigation.

### System PATH Management

You can globally add or remove the configured binary directories (PHP, MySQL, Node, etc.) from your Windows User PATH:
1. Open **File → Settings**.
2. Click **Add to PATH** to include all current service directories in your environment variables.
3. Click **Remove from PATH** to clean up and remove them.
*Note: You may need to restart your terminal or applications for these changes to take effect.*

Settings are saved to `config.json` at the app root.

---

## Virtual Hosts

1. Create a folder inside `www/` — e.g. `www/myapp`
2. Click **↺ Refresh** in the Virtual Hosts tab
3. Apache vhost configs are auto-generated when Apache starts
4. Add the shown entries to your system hosts file:
   - **Windows:** `C:\Windows\System32\drivers\etc\hosts` *(run Notepad as Administrator)*
   - **Linux/macOS:** `/etc/hosts` *(requires `sudo`)*
5. Access your site at `http://myapp.test`

The domain suffix is `.test` by default — change it in **File → Settings → VHost Suffix**.

---

## PHP Extensions

1. Open the **PHP Extensions** tab
2. Check/uncheck extensions — grouped by category with a search filter
3. Click **✔ Apply Changes** — `php.ini` is updated automatically
4. A backup is saved as `php.ini.bak` before any change
5. Click **↺ Reload PHP** or restart Apache for changes to take effect

> `extension_dir` is automatically set to an absolute path when Apache starts,
> so extensions load correctly regardless of Apache's working directory.

---

## MySQL

- Data is stored in `data/mysql/` at the app root — **not** inside the MySQL binary folder
- Upgrading or replacing MySQL does not affect your databases
- On first start, MadServ runs `mysqld --initialize-insecure` automatically
- Default root password is **empty** — set one via a MySQL client after first start

---

## Redis

- Runs `redis-server` with an auto-generated `redis.conf`.
- Configuration includes custom port, log file, and data directory.
- Supports MSYS2-based Redis builds on Windows by using relative paths for configuration.

---

## Ports

| Service      | Default |
|--------------|---------|
| Apache       | 80      |
| MySQL        | 3306    |
| PHP (built-in) | 8000  |
| Node.js      | 3000    |
| Go           | 8080    |

Change in **File → Settings**.

---

## Closing the App

When you click **×** on the window:

- If the system tray is available, a dialog asks: **Minimize to Tray** / **Exit** / **Cancel**
- **Minimize to Tray** — window hides, services keep running, tray icon stays active
- **Exit** — all services are stopped and the process terminates completely

---

## Troubleshooting

**Service shows "Not Found"**  
→ Executable not auto-detected. Set the path manually in **File → Settings**.

**Apache fails to start (exit code 1)**  
→ Check the Activity Log for the exact error.  
→ Common causes: port 80 in use, wrong `ServerRoot`, missing modules.  
→ Use **Tools → Regenerate Apache Config** to recreate `httpd.conf`.

**PHP shows plain source code instead of rendered output**  
→ Apache is not executing PHP. Ensure `php8apache2_4.dll` exists in the PHP folder.  
→ Restart Apache after any PHP path change in Settings.

**PHP extension not loading despite being enabled**  
→ Restart Apache — `extension_dir` is fixed automatically on each Apache start.  
→ Check `logs/apache_error.log` for DLL load errors.

**MySQL fails to start**  
→ Check `logs/mysql_error.log` and `logs/mysql_init.log`.  
→ If the data directory is corrupt, rename `data/mysql/` and restart to re-initialize.

**App stays in background after closing**  
→ Use **File → Exit** or the tray **Exit** option to ensure a clean shutdown.

---

## License

MIT
