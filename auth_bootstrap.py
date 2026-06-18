from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from config import settings
from logging_setup import setup_logging
from telegram.listener import TelegramSignalListener


class _NoopManager:
    def process(self, signal) -> None:
        return None


async def _run() -> None:
    setup_logging(settings.log_level)
    listener = TelegramSignalListener(settings, _NoopManager())  # type: ignore[arg-type]
    await listener.authorize()
    await listener.client.disconnect()

    session_file = listener.session_db_path
    exists = session_file.exists()
    logging.getLogger(__name__).info("Bootstrap complete. session_file=%s exists=%s", session_file, exists)


if __name__ == "__main__":
    asyncio.run(_run())
