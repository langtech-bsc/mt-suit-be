
import logging
import json
import requests
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread
from app.core.config import settings

class TamarinLogHandler(logging.Handler):
    def __init__(self, token, url):
        super().__init__()
        self.token = token
        self.url = url

    def _send_log(self, record: logging.LogRecord) -> None:
        """Sends the log record to the Tamarin API in a separate thread."""
        log_entry = self.format(record)
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        data = {
            "app_name": settings.tamarin_app_name,
            "level": record.levelname,
            "message": log_entry,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        try:
            # Use a timeout to prevent requests from hanging indefinitely
            response = requests.post(self.url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            # This print will go to stderr, which is fine for a background error
            print(f"Error al enviar log a Tamarin: {e}")

    def emit(self, record: logging.LogRecord) -> None:
        thread = Thread(target=self._send_log, args=(record,))
        thread.start()

class ColorFormatter(logging.Formatter):
    """A custom log formatter that adds color based on log level."""

    COLORS = {
        logging.DEBUG: '\033[94m',    # Blue
        logging.INFO: '\033[92m',     # Green
        logging.WARNING: '\033[93m',  # Yellow
        logging.ERROR: '\033[91m',    # Red
        logging.CRITICAL: '\033[1;91m', # Bold Red
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        """Applies color to the entire log message."""
        color = self.COLORS.get(record.levelno, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"

class TamarinFormatter(logging.Formatter):
    """
    A custom formatter for Tamarin that prioritizes a 'plain_message'
    from the log record's extra dictionary, falling back to the default message.
    """
    def format(self, record: logging.LogRecord) -> str:
        message = getattr(record, 'plain_message', record.getMessage())
        return message

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
        }
        return json.dumps(log_record)

def setup_logging():
    log_level = settings.log_level.upper()
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    if settings.log_json:
        formatter = JsonFormatter("%(asctime)s - %(levelname)s - %(message)s")
    elif settings.log_color:
        formatter = ColorFormatter("%(asctime)s - %(levelname)-8s - %(message)s")
    else:
        formatter = logging.Formatter("%(asctime)s - %(levelname)-8s - %(message)s")

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    if settings.log_to_file:
        file_handler = logging.FileHandler(log_dir / settings.log_filename)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Tamarin handler
    if settings.tamarin_logs_enabled and settings.tamarin_app_token:
        tamarin_handler = TamarinLogHandler(
            token=settings.tamarin_app_token, url=settings.tamarin_api_url
        )
        tamarin_handler.setLevel(log_level)
        # Use a custom formatter that extracts a plain message if available.
        tamarin_formatter = TamarinFormatter()
        tamarin_handler.setFormatter(tamarin_formatter)
        logger.addHandler(tamarin_handler)
