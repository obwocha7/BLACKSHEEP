import logging
from logging.handlers import RotatingFileHandler
import os


def setup_logging(level: str = "INFO") -> None:
    os.makedirs("logs", exist_ok=True)

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    if root.handlers:
        return

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    file_handler = RotatingFileHandler("logs/app.log", maxBytes=2_000_000, backupCount=3)
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)
