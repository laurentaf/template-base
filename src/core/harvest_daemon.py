"""Auto-Harvest Daemon — Periodic background harvesting of learnings.

Runs as a lightweight daemon that periodically:
1. Discovers new projects
2. Harvests learnings from active projects
3. Optionally triggers analyze/apply if thresholds met

Usage:
  ltade evolve daemon          — Start daemon (foreground)
  ltade evolve daemon --bg     — Start daemon (background process)
  ltade evolve daemon --stop   — Stop background daemon

Configuration via .env:
  EVOLVE_DAEMON_INTERVAL=300          — Seconds between harvest cycles
  EVOLVE_DAEMON_AUTO_ANALYZE=true     — Run analyze after each harvest
  EVOLVE_DAEMON_AUTO_APPLY=false      — Auto-apply high-value learnings
"""

import json
import os
import signal
import subprocess
import sys
import time
from typing import Any

from src.core.config import settings
from src.core.evolve_engine import EVOLVE_DIR, EvolveEngine

DAEMON_PID_FILE = EVOLVE_DIR / "daemon.pid"
DAEMON_LOG_FILE = EVOLVE_DIR / "daemon.log"
DAEMON_STATE_FILE = EVOLVE_DIR / "daemon_state.json"

DEFAULT_INTERVAL = 300
DEFAULT_AUTO_ANALYZE = True
DEFAULT_AUTO_APPLY = False


class HarvestDaemon:
    def __init__(
        self,
        interval: int | None = None,
        auto_analyze: bool | None = None,
        auto_apply: bool | None = None,
        template_path: str | None = None,
    ):
        self.interval = interval or getattr(settings, "EVOLVE_DAEMON_INTERVAL", DEFAULT_INTERVAL)
        self.auto_analyze = (
            auto_analyze
            if auto_analyze is not None
            else getattr(settings, "EVOLVE_DAEMON_AUTO_ANALYZE", DEFAULT_AUTO_ANALYZE)
        )
        self.auto_apply = (
            auto_apply
            if auto_apply is not None
            else getattr(settings, "EVOLVE_DAEMON_AUTO_APPLY", DEFAULT_AUTO_APPLY)
        )
        self.engine = EvolveEngine(template_path=template_path)
        self._running = False
        self._cycle_count = 0

    def start(self):
        """Run the daemon loop (foreground, blocks until stopped)."""
        self._running = True
        signal.signal(signal.SIGINT, self._stop_signal)
        signal.signal(signal.SIGTERM, self._stop_signal)

        self._log(f"Harvest daemon started (interval={self.interval}s)")
        self._write_pid()

        try:
            while self._running:
                self._cycle()
                self._wait()
        except Exception as exc:
            self._log(f"Daemon error: {exc}")
        finally:
            self._remove_pid()
            self._log(f"Harvest daemon stopped after {self._cycle_count} cycles")

    def _stop_signal(self, signum, frame):
        self._log(f"Received signal {signum}, stopping...")
        self._running = False

    def _cycle(self):
        self._cycle_count += 1
        self._log(f"Cycle #{self._cycle_count} started")

        try:
            self.engine.discover_projects()
            results = self.engine.harvest_all()
            total = sum(len(v) for v in results.values())
            self._log(f"Harvested {total} learnings from {len(results)} projects")

            if total > 0 and self.auto_analyze:
                analysis = self.engine.analyze()
                self._log(
                    f"Analysis: {analysis['total']} total, {analysis['high_value']} high-value"
                )

                if self.auto_apply and analysis["high_value"] > 0:
                    changes = self.engine.apply()
                    self._log(f"Auto-applied {len(changes)} improvements")

            self._save_state(
                {
                    "last_cycle": self._cycle_count,
                    "last_harvest_count": total,
                    "last_projects": len(results),
                    "status": "running",
                }
            )

        except Exception as exc:
            self._log(f"Cycle error: {exc}")
            self._save_state(
                {
                    "last_cycle": self._cycle_count,
                    "status": "error",
                    "error": str(exc),
                }
            )

    def _wait(self):
        """Sleep in small increments so signal handling works promptly."""
        elapsed = 0
        while elapsed < self.interval and self._running:
            time.sleep(1)
            elapsed += 1

    def _log(self, message: str):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"
        DAEMON_PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DAEMON_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _write_pid(self):
        DAEMON_PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        DAEMON_PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

    def _remove_pid(self):
        if DAEMON_PID_FILE.exists():
            DAEMON_PID_FILE.unlink()

    def _save_state(self, state: dict[str, Any]):
        DAEMON_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        DAEMON_STATE_FILE.write_text(
            json.dumps(state, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def load_state() -> dict[str, Any]:
        if not DAEMON_STATE_FILE.exists():
            return {"status": "never_run"}
        try:
            return json.loads(DAEMON_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"status": "unknown"}

    @staticmethod
    def is_running() -> bool:
        if not DAEMON_PID_FILE.exists():
            return False
        try:
            pid = int(DAEMON_PID_FILE.read_text(encoding="utf-8").strip())
            os.kill(pid, 0)
            return True
        except (ValueError, ProcessLookupError, PermissionError):
            if DAEMON_PID_FILE.exists():
                DAEMON_PID_FILE.unlink()
            return False

    @staticmethod
    def stop() -> bool:
        if not DAEMON_PID_FILE.exists():
            return False
        try:
            pid = int(DAEMON_PID_FILE.read_text(encoding="utf-8").strip())
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
            return not HarvestDaemon.is_running()
        except (ValueError, ProcessLookupError, PermissionError):
            if DAEMON_PID_FILE.exists():
                DAEMON_PID_FILE.unlink()
            return False

    @staticmethod
    def start_background(
        interval: int | None = None,
        template_path: str | None = None,
    ) -> int:
        """Start daemon as a background process. Returns PID."""
        cmd = [sys.executable, "-m", "src.core.harvest_daemon"]
        if interval:
            cmd.extend(["--interval", str(interval)])
        if template_path:
            cmd.extend(["--template", template_path])

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=(subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
            if sys.platform == "win32"
            else 0,
        )
        return proc.pid


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LTADE Harvest Daemon")
    parser.add_argument("--interval", type=int, default=None)
    parser.add_argument("--template", type=str, default=None)
    args = parser.parse_args()

    daemon = HarvestDaemon(
        interval=args.interval,
        template_path=args.template,
    )
    daemon.start()
