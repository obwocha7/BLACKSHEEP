import logging
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

    file_handler = logging.FileHandler("logs/app.log", mode="a", encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)
