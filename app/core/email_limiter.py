"""
A persistent, time-based rate limiter for sending notification emails.
This prevents flooding mailboxes during repeated failure events and survives
application restarts.
"""

import json
import time
from pathlib import Path
from threading import Lock

STATE_FILE = Path(__file__).resolve().parent / ".email_limiter_state.json"


class EmailRateLimiter:
    """
    Limits email sending with a circuit-breaker pattern.

    - Allows 1 email every 10 minutes.
    - Stops all emails after a 1-hour alert window.
    - Resets after 24 hours of inactivity.
    """

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.min_interval = 600  # 10 minutes
        self.alert_window_duration = 3600  # 1 hour
        self.reset_duration = 86400  # 24 hours
        self._lock = Lock()
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """Loads the limiter state from a file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, "r") as f:
                    return json.load(f)
        except (IOError, json.JSONDecodeError):
            pass  # Ignore errors and start fresh
        return {"first_error_timestamp": 0, "last_sent_timestamp": 0}

    def _save_state(self) -> None:
        """Saves the current state to a file."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.state, f)
        except IOError:
            # If we can't save, we can't enforce limits across restarts,
            # but the in-memory part will still work for the current process.
            pass

    def can_send(self) -> bool:
        """Checks if an email can be sent based on the rate limit."""
        with self._lock:
            now = time.time()
            self.state = self._load_state()  # Always get the latest state

            first_error_ts = self.state.get("first_error_timestamp", 0)
            last_sent_ts = self.state.get("last_sent_timestamp", 0)

            # Reset if the last error was more than 24 hours ago
            if now - first_error_ts > self.reset_duration:
                self.state = {"first_error_timestamp": 0, "last_sent_timestamp": 0}
                first_error_ts = 0

            # If this is the first error in a while, start the alert window
            if first_error_ts == 0:
                self.state["first_error_timestamp"] = now

            # Stop sending if we are outside the 1-hour alert window
            if now - self.state["first_error_timestamp"] > self.alert_window_duration:
                return False

            # Allow sending only if it's been more than 10 minutes
            if now - last_sent_ts > self.min_interval:
                self.state["last_sent_timestamp"] = now
                self._save_state()
                return True

            return False

# Global instance of the limiter.
error_email_limiter = EmailRateLimiter(state_file=STATE_FILE)