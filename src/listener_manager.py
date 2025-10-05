"""
Discord Listener Process Manager

Manages the discord_listener.py process from Streamlit
"""

import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ListenerManager:
    """Manages the Discord listener process"""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        # Use absolute path for reliability
        self.listener_script = (
            Path(__file__).parent.parent / "discord_listener.py"
        ).resolve()
        self.pid_file = (Path(__file__).parent.parent / "listener.pid").resolve()

    def _load_pid(self) -> Optional[int]:
        """Load PID from file"""
        if self.pid_file.exists():
            try:
                with open(self.pid_file, "r") as f:
                    pid_str = f.read().strip()
                    if pid_str:
                        pid = int(pid_str)
                        logger.debug(f"Loaded PID {pid} from file")
                        return pid
            except Exception as e:
                logger.error(f"Failed to load PID from file: {e}")
                return None
        return None

    def _save_pid(self, pid: int):
        """Save PID to file"""
        try:
            with open(self.pid_file, "w") as f:
                f.write(str(pid))
        except Exception as e:
            logger.error(f"Failed to save PID: {e}")

    def _remove_pid(self):
        """Remove PID file"""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except Exception as e:
            logger.error(f"Failed to remove PID file: {e}")

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with given PID is running"""
        # First try checking /proc filesystem (Linux/Unix)
        proc_path = Path(f"/proc/{pid}")
        if proc_path.exists():
            return True

        # Fallback to os.kill method
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except (OSError, PermissionError):
            # If we get permission error, process exists but we can't signal it
            # This shouldn't happen for our own process, so assume it's not ours
            return False

    def is_running(self) -> bool:
        """Check if the listener process is running"""
        # First check if we have a process object
        if self.process is not None:
            poll = self.process.poll()
            if poll is None:
                return True
            else:
                self.process = None

        # If no process object, check PID file
        pid = self._load_pid()
        if pid is not None:
            if self._is_process_running(pid):
                logger.debug(f"Process {pid} is running (verified from PID file)")
                return True
            else:
                # Process not running, clean up PID file
                logger.info(f"Process {pid} is not running, cleaning up PID file")
                self._remove_pid()

        return False

    def start(self) -> bool:
        """Start the Discord listener process"""
        if self.is_running():
            logger.warning("Listener is already running")
            return False

        if not self.listener_script.exists():
            logger.error(f"Listener script not found: {self.listener_script}")
            return False

        try:
            # Start the listener as a subprocess
            logger.info(f"Starting Discord listener: {self.listener_script}")

            # Use the same Python interpreter
            python_executable = sys.executable

            # Start process in background
            self.process = subprocess.Popen(
                [python_executable, str(self.listener_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                cwd=str(self.listener_script.parent),
                # On Unix, create new process group
                preexec_fn=os.setsid if os.name != "nt" else None,
            )

            # Wait a bit to see if it starts successfully
            time.sleep(1)

            if self.is_running():
                pid = self.process.pid
                self._save_pid(pid)
                logger.info(f"Discord listener started successfully (PID: {pid})")
                return True
            else:
                logger.error("Discord listener failed to start")
                return False

        except Exception as e:
            logger.error(f"Error starting Discord listener: {e}")
            self.process = None
            return False

    def stop(self) -> bool:
        """Stop the Discord listener process"""
        if not self.is_running():
            logger.warning("Listener is not running")
            return False

        try:
            # Get PID from process or file
            pid = None
            if self.process is not None:
                pid = self.process.pid
            else:
                pid = self._load_pid()

            if pid is None:
                logger.error("Cannot find process PID")
                return False

            logger.info(f"Stopping Discord listener (PID: {pid})")

            # Send SIGTERM to gracefully shutdown
            if os.name != "nt":
                # On Unix, kill the entire process group
                try:
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                except ProcessLookupError:
                    logger.warning("Process already terminated")
                    self._remove_pid()
                    self.process = None
                    return True
            else:
                # On Windows, just terminate the process
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    logger.warning("Process already terminated")
                    self._remove_pid()
                    self.process = None
                    return True

            # Wait for process to exit (max 5 seconds)
            for _ in range(50):
                if not self._is_process_running(pid):
                    logger.info("Discord listener stopped successfully")
                    self._remove_pid()
                    self.process = None
                    return True
                time.sleep(0.1)

            # Force kill if still running
            logger.warning("Listener did not stop gracefully, forcing kill")
            if os.name != "nt":
                try:
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

            self._remove_pid()
            self.process = None
            return True

        except Exception as e:
            logger.error(f"Error stopping Discord listener: {e}")
            self._remove_pid()
            self.process = None
            return False

    def restart(self) -> bool:
        """Restart the Discord listener process"""
        logger.info("Restarting Discord listener")
        self.stop()
        time.sleep(1)
        return self.start()

    def get_status(self) -> dict:
        """Get the current status of the listener"""
        is_running = self.is_running()

        # Get PID from process or file
        pid = None
        if is_running:
            if self.process is not None:
                pid = self.process.pid
            else:
                pid = self._load_pid()

        status = {
            "is_running": is_running,
            "pid": pid,
        }

        return status

    def get_logs(self, lines: int = 100) -> str:
        """Get recent logs from the listener (if available)"""
        log_file = Path(__file__).parent.parent / "discord_listener.log"

        if not log_file.exists():
            return "No logs available"

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
                # Get last N lines and reverse them (newest first)
                recent_lines = all_lines[-lines:]
                recent_lines.reverse()
                return "".join(recent_lines)
        except Exception as e:
            logger.error(f"Error reading logs: {e}")
            return f"Error reading logs: {e}"
