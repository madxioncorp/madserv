# PyLaragon Usage Guide

Complete guide to using PyLaragon for local web development.

---

## Installation

### 1. Prerequisites

**Required:**
- Python 3.8 or higher
- At least one of: Apache httpd, MySQL/MariaDB, or PHP

**Optional (for full functionality):**
- Apache httpd 2.4+ (for web server)
- MySQL 5.7+ or MariaDB (for database)
- PHP 7.4+ (for PHP applications)

### 2. Install PyLaragon

```bash
# Clone or download the project
cd pylaragon

# Install optional dependencies (system tray, process management)
pip install -r requirements.txt
```

### 3. First Run

```bash
python main.py
```

On first launch, PyLaragon will:
- Auto-detect Apache, MySQL, and PHP installations
- Create necessary directories (`www/`, `logs/`, `config/`)
- Generate a default welcome page in `www/default/`
- Create `config.json` with detected settings

---

## Main Window Overview

### Toolbar
- **▶ Start All** – Start all services at once
- **■ Stop All** – Stop all services
- **⚙ Settings** – Configure paths and ports
- **📁 www** – Open the www folder in file explorer

### Status Bar (bottom)
Shows real-time status of each service:
- **● Green** – Running
- **● Red** – Stopped
- **● Orange** – Starting/Stopping
- **● Gray** – Not Found

### Tabs
1. **Services** – Control Apache, MySQL, PHP
2. **Virtual Hosts** – Manage project domains
3. **PHP Extensions** – Enable/disable PHP extensions

---

## Services Tab

### Service Controls

Each service row shows:
- **Status** – Current state (Running/Stopped/etc.)
- **Port** – Listening port
- **Version** – Detected version
- **Actions** – Start, Stop, Restart, Logs

### Starting Services

**Individual service:**
1. Click **Start** button for the service
2. Wait for status to change to "Running"
3. Check Activity Log for any errors

**All services:**
- Click **▶ Start All** in toolbar or bottom of tab

### Viewing Logs

Click **Logs** button to open a log viewer window showing:
- Apache: `logs/apache_error.log`
- MySQL: `logs/mysql_error.log`
- PHP: `logs/php_error.log`

### Activity Log

The bottom panel shows real-time service messages:
```
[Apache] Starting: E:\apache\bin\httpd.exe -f ...
[Apache] Started successfully.
[MySQL] Starting: E:\mysql\bin\mysqld.exe ...
[MySQL] Started successfully.
```

---

## Virtual Hosts Tab

### Creating a New Project

**Method 1: Using the GUI**
1. Click **+ New Project**
2. Enter project name (e.g., `myapp`)
3. Project folder created at `www/myapp/`
4. Domain will be `myapp.test`

**Method 2: Manual**
1. Create folder in `www/` (e.g., `www/blog/`)
2. Add an `index.php` or `index.html`
3. Click **↺ Refresh** in Virtual Hosts tab

### Configuring Virtual Hosts

1. **Generate Apache configs:**
   - Click **⚙ Generate Configs**
   - Creates `.conf` files in `config/apache/vhosts/`

2. **Update hosts file:**
   - Copy entries from the "Hosts File Entries" section
   - Click **✏ Edit hosts file** (opens in editor)
   - Add the entries:
     ```
     127.0.0.1    myapp.test
     127.0.0.1    blog.test
     ```
   - Save (requires admin/root privileges)

3. **Reload Apache:**
   - Go to Services tab
   - Click **Restart** for Apache

### Accessing Projects

**From the GUI:**
- Select a virtual host
- Click **🌐 Open in Browser**

**Manually:**
- Open browser to `http://myapp.test`
- Or `http://myapp.test:80` if using non-standard port

### Virtual Host Actions

- **🌐 Open in Browser** – Launch default browser
- **📋 Copy Domain** – Copy domain to clipboard
- **🗑 Remove Config** – Delete Apache vhost config (folder remains)
- **📁 Open www** – Open www folder in file explorer

---

## PHP Extensions Tab

### Viewing Extensions

Extensions are grouped by category:
- **Database** – mysqli, pdo_mysql, pdo_pgsql, etc.
- **Caching** – opcache, apcu, redis, memcached
- **Image** – gd, imagick, exif
- **Crypto / Security** – openssl, sodium
- **String / Encoding** – mbstring, iconv, intl
- **Network** – curl, soap, ftp
- **Compression** – zip, zlib, bz2
- **Development** – xdebug, pcov
- **Misc** – Other extensions

### Enabling/Disabling Extensions

1. **Check/uncheck** extensions you want to enable/disable
2. Click **✔ Apply Changes**
3. Review the changes in the confirmation dialog
4. Click **Yes** to modify `php.ini`
5. Click **↺ Reload PHP** to restart PHP service

### Filtering Extensions

Use the **🔍 Filter** box to search:
- Type `mysql` to show only MySQL-related extensions
- Type `cache` to show caching extensions

### Bulk Actions

- **Enable All Visible** – Enable all extensions matching current filter
- **Disable All Visible** – Disable all extensions matching current filter
- **Reset Changes** – Undo unsaved changes

### Safety Features

- **Automatic backup** – `php.ini.bak` created before any changes
- **Change indicator** – Shows "⚠ X unsaved change(s)" when modified
- **Confirmation dialog** – Lists all changes before applying

---

## Settings

Access via **File → Settings** or **⚙ Settings** button.

### Configurable Options

| Setting | Description | Example |
|---------|-------------|---------|
| Apache Port | HTTP port for Apache | 80 |
| MySQL Port | Database port | 3306 |
| PHP Port | PHP built-in server port | 8000 |
| VHost Suffix | Domain suffix for projects | test |
| Apache Executable | Path to httpd.exe | C:\Apache24\bin\httpd.exe |
| mysqld Executable | Path to mysqld.exe | C:\mysql\bin\mysqld.exe |
| mysql Client | Path to mysql.exe | C:\mysql\bin\mysql.exe |
| PHP Executable | Path to php.exe | C:\php\php.exe |
| php.ini Path | Path to php.ini | C:\php\php.ini |

### Auto-Detection

PyLaragon checks these locations automatically:

**Apache:**
- `C:\xampp\apache\bin\httpd.exe`
- `C:\Apache24\bin\httpd.exe`
- `C:\laragon\bin\apache\...\httpd.exe`
- System PATH

**MySQL:**
- `C:\xampp\mysql\bin\mysqld.exe`
- `C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe`
- `C:\laragon\bin\mysql\...\mysqld.exe`
- System PATH

**PHP:**
- `C:\xampp\php\php.exe`
- `C:\php\php.exe`
- `C:\laragon\bin\php\...\php.exe`
- System PATH

---

## Menu Bar

### File Menu
- **Settings…** – Open settings dialog
- **Open www Folder** – Open www directory
- **Open Logs Folder** – Open logs directory
- **Exit** – Stop all services and quit

### Tools Menu
- **Start All Services** – Start Apache, MySQL, PHP
- **Stop All Services** – Stop all services
- **Regenerate Apache Config** – Recreate `httpd.conf` from template
- **Regenerate VHost Configs** – Recreate all vhost `.conf` files
- **Edit hosts file** – Open system hosts file in editor

### Help Menu
- **About PyLaragon** – Version and info

---

## System Tray (Optional)

If `pystray` and `Pillow` are installed:

- **Minimize to tray** – Click window close button
- **Show window** – Double-click tray icon or select "Show"
- **Quick actions** – Right-click tray icon for Start All / Stop All
- **Exit** – Right-click → Exit

---

## Common Workflows

### Starting a New PHP Project

1. **Create project:**
   ```bash
   # Manual method
   mkdir www/myproject
   echo "<?php phpinfo();" > www/myproject/index.php
   ```
   Or use **+ New Project** button

2. **Generate vhost:**
   - Go to Virtual Hosts tab
   - Click **⚙ Generate Configs**

3. **Update hosts file:**
   - Copy entry: `127.0.0.1    myproject.test`
   - Edit hosts file (admin required)
   - Add the line

4. **Start services:**
   - Go to Services tab
   - Click **▶ Start All**

5. **Access project:**
   - Open browser to `http://myproject.test`

### Switching PHP Versions

1. **Stop PHP service** (if running)
2. **File → Settings**
3. Change **PHP Executable** path to different version
4. Change **php.ini Path** to match
5. Click **Save**
6. **Start PHP service**
7. Verify version in Services tab

### Enabling Xdebug

1. **PHP Extensions tab**
2. **Filter:** type `xdebug`
3. **Check** the xdebug extension
4. Click **✔ Apply Changes**
5. Click **↺ Reload PHP**
6. Verify in browser: `<?php phpinfo(); ?>` should show Xdebug section

### Troubleshooting Port Conflicts

If Apache fails to start with "port already in use":

1. **Find conflicting process:**
   ```bash
   # Windows
   netstat -ano | findstr :80
   
   # Linux/Mac
   lsof -i :80
   ```

2. **Option A: Stop conflicting service**
   - Stop IIS, Skype, or other service using port 80

3. **Option B: Change Apache port**
   - **File → Settings**
   - Change **Apache Port** to 8080
   - Click **Save**
   - **Tools → Regenerate Apache Config**
   - Restart Apache
   - Access projects at `http://myproject.test:8080`

---

## Advanced Configuration

### Custom Apache Modules

Edit `config/apache/httpd.conf.template`:

```apache
# Add your custom modules
LoadModule ssl_module modules/mod_ssl.so
LoadModule http2_module modules/mod_http2.so

# Add custom directives
Protocols h2 http/1.1
```

Then: **Tools → Regenerate Apache Config**

### Custom VHost Template

Edit `config/apache/vhost.conf.template`:

```apache
<VirtualHost *:{port}>
    ServerName {domain}
    DocumentRoot "{docroot}"
    
    # Add custom directives
    SetEnv APP_ENV development
    
    <Directory "{docroot}">
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
</VirtualHost>
```

Then: **Tools → Regenerate VHost Configs**

### MySQL Configuration

Edit `config/mysql/my.ini.template` to customize:
- Buffer sizes
- Connection limits
- Character sets
- Logging options

Then restart MySQL service.

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Settings | Alt+F, S |
| Start All | (none – use toolbar) |
| Stop All | (none – use toolbar) |
| Refresh VHosts | (none – use button) |

---

## Tips & Best Practices

### Performance
- **Disable unused extensions** – Reduces PHP memory usage
- **Enable opcache** – Dramatically improves PHP performance
- **Adjust MySQL buffer pool** – Edit `my.ini.template`

### Security
- **Never expose to internet** – PyLaragon is for local development only
- **Use strong MySQL passwords** – Set via MySQL client
- **Keep software updated** – Update Apache, MySQL, PHP regularly

### Organization
- **One project per folder** – Keep `www/` organized
- **Use descriptive names** – `www/client-website` not `www/proj1`
- **Version control** – Initialize git in each project folder

### Backup
- **Database dumps** – Regular mysqldump backups
- **Project files** – Use git or file sync
- **Configuration** – Backup `config.json` and templates

---

## Troubleshooting

### Service Won't Start

**Check logs:**
1. Click **Logs** button for the service
2. Look for error messages

**Common issues:**
- Port already in use → Change port in Settings
- Executable not found → Set correct path in Settings
- Missing dependencies → Install required libraries
- Permission denied → Run as administrator (Windows) or with sudo (Linux)

### Virtual Host Not Working

**Checklist:**
- [ ] Folder exists in `www/`
- [ ] Vhost config generated (click **⚙ Generate Configs**)
- [ ] Hosts file entry added (requires admin)
- [ ] Apache restarted after config changes
- [ ] Correct domain format: `foldername.test`

**Test:**
```bash
# Windows
ping myproject.test

# Should return 127.0.0.1
```

### PHP Extensions Not Showing

**Verify php.ini path:**
1. **File → Settings**
2. Check **php.ini Path** is correct
3. File should exist and be readable

**Find php.ini:**
```bash
php --ini
```

### Changes Not Taking Effect

**Restart services:**
- Apache changes → Restart Apache
- MySQL changes → Restart MySQL
- PHP changes → Restart PHP (or Apache if using mod_php)
- Hosts file → No restart needed, but may need to flush DNS

**Flush DNS cache:**
```bash
# Windows
ipconfig /flushdns

# Linux
sudo systemd-resolve --flush-caches

# macOS
sudo dscacheutil -flushcache
```

---

## Getting Help

### Log Files

Check these locations:
- `logs/apache_error.log` – Apache errors
- `logs/apache_access.log` – HTTP requests
- `logs/mysql_error.log` – MySQL errors
- `logs/php_error.log` – PHP errors

### Diagnostic Info

When reporting issues, include:
- Operating system and version
- Python version: `python --version`
- Apache version: `httpd -v`
- MySQL version: `mysqld --version`
- PHP version: `php -v`
- Contents of `config.json`
- Relevant log excerpts

---

## Uninstallation

1. **Stop all services** – Click **■ Stop All**
2. **Close PyLaragon**
3. **Delete project folder** – Remove `pylaragon/` directory
4. **Clean hosts file** – Remove added entries
5. **Optional:** Uninstall Apache, MySQL, PHP if no longer needed

---

## License

MIT License – See LICENSE file for details.
