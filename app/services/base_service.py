"""
Abstract base class for all managed services (Apache, MySQL, PHP).
"""

import subprocess
import threading
import time
import os
import signal
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Callable, IO


class ServiceStatus:
    STOPPED = "Stopped"
    RUNNING = "Running"
    STARTING = "Starting"
    INITIALIZING = "Initializing"
    STOPPING = "Stopping"
    ERROR = "Error"
    NOT_FOUND = "Not Found"


class BaseService(ABC):
    """
    Abstract base for a managed background service.
    """

    def __init__(self, config):
        self.config = config
        self._process: Optional[subprocess.Popen] = None
        self._log_file: Optional[IO] = None          # kept so we can close it
        self._status: str = ServiceStatus.STOPPED
        self._lock = threading.Lock()
        self._status_callbacks: List[Callable[[str], None]] = []
        self._log_callbacks: List[Callable[[str], None]] = []

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable service name."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Detected version string, or 'Unknown'."""

    @abstractmethod
    def _build_start_command(self) -> List[str]:
        """Return the command list to start the service."""

    # ------------------------------------------------------------------
    # Status management
    # ------------------------------------------------------------------

    @property
    def status(self) -> str:
        return self._status

    def _set_status(self, status: str):
        self._status = status
        for cb in self._status_callbacks:
            try:
                cb(status)
            except Exception:
                pass

    def add_status_callback(self, cb: Callable[[str], None]):
        self._status_callbacks.append(cb)

    def add_log_callback(self, cb: Callable[[str], None]):
        self._log_callbacks.append(cb)

    def _log(self, message: str):
        formatted = f"[{self.name}] {message}"
        print(formatted)

        # Also write to the log file if it's open
        if self._log_file is not None:
            try:
                # Add timestamp for internal messages
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                self._log_file.write(f"[{timestamp}] {formatted}\n".encode("utf-8", errors="replace"))
                self._log_file.flush()
            except OSError:
                pass

        for cb in self._log_callbacks:
            try:
                cb(message)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def is_running(self) -> bool:
        """Return True if the managed process is alive."""
        with self._lock:
            if self._process is None:
                return False
            ret = self._process.poll()
            return ret is None

    def start(self) -> bool:
        """Start the service. Returns True on success."""
        if self.is_running():
            self._log("Already running.")
            return True

        self._set_status(ServiceStatus.STARTING)

        cmd = self._build_start_command()
        if not cmd:
            self._set_status(ServiceStatus.NOT_FOUND)
            self._log("Executable not found – cannot start.")
            return False

        # Open log file early so _log can write to it
        log_path = self.get_log_path()
        if log_path:
            try:
                log_path.parent.mkdir(parents=True, exist_ok=True)
                self._log_file = open(log_path, "ab")
            except OSError:
                self._log_file = None

        self._log(f"Starting: {' '.join(str(c) for c in cmd)}")

        try:
            kwargs = self._popen_kwargs()

            # Set cwd to the executable's own directory.
            # This ensures the child process finds its own DLLs first,
            # not the ones bundled by PyInstaller in the app directory.
            exe_dir = Path(cmd[0]).parent
            if exe_dir.exists():
                kwargs["cwd"] = str(exe_dir)

            with self._lock:
                self._process = subprocess.Popen(cmd, **kwargs)

            # Start the output reader thread
            threading.Thread(target=self._read_output, daemon=True).start()

            # Give the process a moment to fail fast
            time.sleep(0.8)
            if self._process.poll() is not None:
                rc = self._process.returncode
                self._set_status(ServiceStatus.ERROR)
                self._log(f"Process exited immediately with code {rc}.")
                return False

            self._set_status(ServiceStatus.RUNNING)
            self._log("Started successfully.")
            # Start a watcher thread
            threading.Thread(target=self._watch, daemon=True).start()
            return True

        except FileNotFoundError:
            self._set_status(ServiceStatus.NOT_FOUND)
            self._log(f"Executable not found: {cmd[0]}")
            return False
        except OSError as e:
            self._set_status(ServiceStatus.ERROR)
            self._log(f"Failed to start: {e}")
            return False

    def stop(self) -> bool:
        """Stop the service. Returns True on success."""
        if not self.is_running():
            self._set_status(ServiceStatus.STOPPED)
            self._close_log_file()
            return True

        self._set_status(ServiceStatus.STOPPING)
        self._log("Stopping…")

        with self._lock:
            proc = self._process

        if proc is None:
            self._set_status(ServiceStatus.STOPPED)
            self._close_log_file()
            return True

        try:
            if sys.platform == "win32":
                # Kill the entire process tree (parent + all children).
                # MySQL 8.0 spawns a child worker process that survives
                # a simple terminate() on the parent.
                self._kill_process_tree_win(proc.pid)
            else:
                # On Unix send SIGTERM to the process group so children die too
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                except (OSError, AttributeError):
                    proc.send_signal(signal.SIGTERM)

            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._log("Graceful stop timed out – killing process.")
                if sys.platform == "win32":
                    self._kill_process_tree_win(proc.pid)
                else:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except (OSError, AttributeError):
                        proc.kill()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass

            self._set_status(ServiceStatus.STOPPED)
            self._log("Stopped.")
            with self._lock:
                self._process = None
            self._close_log_file()
            return True

        except OSError as e:
            self._set_status(ServiceStatus.ERROR)
            self._log(f"Error stopping: {e}")
            self._close_log_file()
            return False

    @staticmethod
    def _kill_process_tree_win(pid: int):
        """
        Terminate a process and all its descendants on Windows.
        Uses taskkill /F /T which forcefully kills the entire tree.
        Falls back to psutil if available for a cleaner shutdown.
        """
        # Try psutil first — sends SIGTERM-equivalent to each child gracefully
        try:
            import psutil
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            # Terminate children first, then parent
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            parent.terminate()
            # Wait up to 5s, then force-kill anything still alive
            gone, alive = psutil.wait_procs(children + [parent], timeout=5)
            for p in alive:
                try:
                    p.kill()
                except psutil.NoSuchProcess:
                    pass
            return
        except ImportError:
            pass
        except Exception:
            pass

        # Fallback: taskkill /F /T kills the whole tree forcefully
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
        except Exception:
            pass

    def restart(self) -> bool:
        """Stop then start the service."""
        self._log("Restarting…")
        self.stop()
        time.sleep(1)
        return self.start()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _popen_kwargs(self) -> dict:
        """Build kwargs for subprocess.Popen."""
        # Use PIPEs so we can read output in real-time and show it in GUI.
        # We merge stderr into stdout for easier reading.
        kwargs: dict = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": False,  # Read bytes to avoid encoding issues
            "bufsize": 1,   # Line buffered (if text=True), but we'll read by line
        }

        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        # Sanitised environment — strips PyInstaller dirs from PATH
        kwargs["env"] = self._clean_env()

        return kwargs

    def _read_output(self):
        """Read process output and log it in real-time."""
        proc = self._process
        if not proc or not proc.stdout:
            return

        # Read line by line until EOF
        for line_bytes in iter(proc.stdout.readline, b""):
            try:
                # Decode for GUI display
                msg = line_bytes.decode("utf-8", errors="replace").rstrip()

                # Write raw bytes to the log file if open
                if self._log_file is not None:
                    try:
                        self._log_file.write(line_bytes)
                        self._log_file.flush()
                    except OSError:
                        pass

                # Forward to GUI callbacks
                for cb in self._log_callbacks:
                    try:
                        cb(msg)
                    except Exception:
                        pass

                # Also print to console for debug
                print(f"[{self.name} output] {msg}")

            except Exception as e:
                print(f"Error reading output from {self.name}: {e}")

    @staticmethod
    def _clean_env() -> dict:
        """
        Return os.environ with PyInstaller's internal directories removed
        from PATH and without PYTHONPATH / PYTHONHOME.
        """
        env = os.environ.copy()

        strip_dirs = set()
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            meipass = getattr(sys, "_MEIPASS", None)

            # Strip the exe directory and all its immediate subdirectories
            # (PyInstaller onedir puts DLLs in _internal/, app/, etc.)
            strip_dirs.add(os.path.normcase(exe_dir))
            try:
                for sub in os.listdir(exe_dir):
                    full = os.path.join(exe_dir, sub)
                    if os.path.isdir(full):
                        strip_dirs.add(os.path.normcase(full))
            except OSError:
                pass

            if meipass:
                strip_dirs.add(os.path.normcase(meipass))
                try:
                    for sub in os.listdir(meipass):
                        full = os.path.join(meipass, sub)
                        if os.path.isdir(full):
                            strip_dirs.add(os.path.normcase(full))
                except OSError:
                    pass

        if strip_dirs:
            original_path = env.get("PATH", "")
            cleaned = [
                p for p in original_path.split(os.pathsep)
                if os.path.normcase(p) not in strip_dirs
            ]
            env["PATH"] = os.pathsep.join(cleaned)

        for var in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"):
            env.pop(var, None)

        return env

    def _close_log_file(self):
        """Close the log file handle opened for this service's process."""
        if self._log_file is not None:
            try:
                self._log_file.close()
            except OSError:
                pass
            self._log_file = None

    def _watch(self):
        """Background thread: watch the process and update status when it exits."""
        proc = self._process
        if proc is None:
            return
        proc.wait()
        if self._status not in (ServiceStatus.STOPPING, ServiceStatus.STOPPED):
            self._set_status(ServiceStatus.STOPPED)
            self._log(f"Process exited with code {proc.returncode}.")

    def get_log_path(self) -> Optional[Path]:
        """Return the path to this service's log file, if any."""
        return None
