from __future__ import annotations

import asyncio
import logging

from config import settings
from logging_setup import setup_logging
from telegram.listener import TelegramSignalListener


class _NoopManager:
    def process(self, signal) -> None:
        return None


async def _run() -> None:
    setup_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    listener = TelegramSignalListener(settings, _NoopManager())  # type: ignore[arg-type]

    logger.info("Bootstrap start. session_target=%s", listener.session_db_path)
    await listener.authorize()

    authorized = await listener.client.is_user_authorized()
    await listener.client.disconnect()

    session_file = listener.session_db_path
    exists = session_file.exists()
    logger.info("Bootstrap complete. session_file=%s exists=%s authorized=%s", session_file, exists, authorized)

    if not authorized:
        raise SystemExit(2)


if __name__ == "__main__":
    asyncio.run(_run())
