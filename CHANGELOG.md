# Changelog

All notable changes to MadServ are documented here.

---

## [1.2.0] — 2026-04-24

### Core
- **Node.js & Go Support** — New services added for Node.js and Go (Golang) with automatic binary detection and project management.
- **Redis Support** — Added Redis as a standalone service with automatic configuration and binary detection.
- **Custom App Paths** — Ability to customize project folders for Node.js and Go via Settings.
- **Binary Version Selection** — Easily switch between different installed versions of PHP, Node.js, and Go using dropdowns in the Settings dialog.
- **Isolated Environment PATH** — Services now automatically prepend their specific binary directory to the environment `PATH` when running, ensuring the correct versions of tools (like `npm` or `go`) are used.
- **Smart Binary Detection** — Enhanced auto-detection logic to find and prioritize executables in the local `bin/` folder.
- **Improved Tray & Close Logic** — Fixed an issue where the close dialog was missing. Updated tray menu and "Start/Stop All" to include Node.js and Go.

### Services
- **Redis** — Added Redis as a standalone service with automatic configuration and binary detection.



### PHP
- **PHP Settings Manager** — Change common `php.ini` parameters directly from the GUI (e.g., `upload_max_filesize`, `post_max_size`).
- **Enhanced Configuration** — Centralized PHP settings and extensions management in a single tab.

---

## [1.1.0] — 2026-04-23

### Core
- **Real-time Logging** — Captured process `stdout`/`stderr` is now displayed live in the Activity Log and written to log files with timestamps.
- **Improved Process Management** — Output reading via dedicated threads ensures non-blocking GUI while services are running.
- **Self-Healing Templates** — Embedded default configuration templates to ensure the app can recover even if `config/` folder is missing.
- **Improved MySQL Initialization** — Added "Initializing" status indicator and better process locking during first-time database setup.

### Bug Fixes
- **MySQL Version Detection** — Fixed an issue where the app version was incorrectly detected as the MySQL version on some systems.

---

## [1.0.0] — 2026-04-21

Initial release.

### Core

- Python + tkinter GUI, no external GUI framework required
- Auto-detects Apache, MySQL, and PHP executables from 20+ common locations (XAMPP, Laragon, system PATH)
- Settings persisted to `config.json` at app root
- Settings dialog with **…** browse buttons for all executable/file paths
- `os._exit(0)` hard-exit on close ensures no lingering background process

### Services

- **Apache** — start/stop with auto-generated `httpd.conf` from template
  - PHP executed via `mod_php` (`php8apache2_4.dll`) — no FastCGI daemon needed
  - `mod_rewrite` enabled globally by default
  - `RewriteEngine On` set in `httpd.conf`; `.htaccess` rules work out of the box
  - `TypesConfig` uses absolute path to avoid relative-path failures
  - Vhost configs auto-regenerated on every Apache start
- **MySQL** — start/stop with auto-generated `my.ini` from template
  - Auto-initializes data directory with `--initialize-insecure` on first run
  - Data stored in `data/mysql/` at app root — survives MySQL binary upgrades
  - Process tree kill on stop (parent + child worker) via `psutil` or `taskkill /F /T`
- **PHP** — PHP built-in server (`php -S`) as standalone service
  - Auto-detects and uses `php.exe`, not `php-cgi.exe` (which does not support `-S`)

### Virtual Hosts

- Scans `www/` directory; one vhost per subfolder
- Domain format: `<folder>.test` (suffix configurable)
- Generates Apache `.conf` files with correct absolute log paths
- Shows hosts file entries for manual addition
- "Edit hosts file" opens system hosts file in Notepad
- New project creation from GUI

### PHP Extensions

- Parses `php.ini` for `extension=` lines (enabled and commented)
- Scans `ext/` directory for available `.dll`/`.so` files
- Grouped by category with search/filter
- Apply Changes writes `php.ini` with automatic `.ini.bak` backup
- `extension_dir` automatically set to absolute path on every Apache start — fixes "could not find driver" errors when PHP runs as `mod_php`

### GUI

- Notebook layout: Services / Virtual Hosts / PHP Extensions tabs
- **Services tab** — colored action buttons reflecting real-time state:
  - Green **▶ Start** — enabled only when stopped
  - Red **■ Stop** — enabled only when running
  - Blue **↺ Restart** — enabled only when running
  - Grey when disabled; all buttons disabled during transitions (Starting/Stopping)
  - Status label colored per state (green/red/orange/grey)
- Status bar with colored dots (green/red/orange) refreshed every 2 seconds
- Activity log (dark theme) with live output from all services
- System tray support via `pystray` + `Pillow` (graceful fallback if not installed)
- Close dialog: **Minimize to Tray** / **Exit** / **Cancel** when tray is available
- Window and tray icon loaded from embedded base64 image (`imagekit.py`)
- Settings dialog split into General (ports, suffix) and Executable/File Paths sections

### Stability & Compatibility

- All GUI updates from background threads routed through `widget.after(0, ...)` — no `RuntimeError: main thread is not in main loop`
- Service output redirected to log files (not pipes) — prevents PHP built-in server from detecting no-TTY and exiting immediately
- PyInstaller bundle compatibility:
  - `_get_base_dir()` uses `sys.executable` parent when frozen, not `__file__`
  - `SetDllDirectoryW("")` called at startup to clear PyInstaller's DLL search path
  - Child processes spawned with sanitized `PATH` (PyInstaller `_internal/` and subdirs stripped) and `cwd` set to executable's own directory — fixes VCRUNTIME140.dll version conflict with PHP 8.5+
- MySQL stop kills entire process tree, not just parent PID
