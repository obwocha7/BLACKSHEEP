from __future__ import annotations

import logging
from telethon import TelegramClient, events

from config import Settings
from parser.signal_parser import parse_message
from execution.manager import TradeManager


logger = logging.getLogger(__name__)


class TelegramSignalListener:
    def __init__(self, settings: Settings, manager: TradeManager):
        self.settings = settings
        self.manager = manager
        self.client = TelegramClient(settings.tg_session_name, settings.tg_api_id, settings.tg_api_hash)

    def _allowed(self, event) -> bool:
        allowed = str(self.settings.tg_allowed_chat).strip().lower()
        chat = str(getattr(event.chat, "username", "") or "").strip().lower()
        chat_id = str(getattr(event, "chat_id", ""))
        return (allowed == chat) or (allowed == chat_id)

    async def start(self) -> None:
        @self.client.on(events.NewMessage)
        async def handler(event):
            try:
                if not self._allowed(event):
                    return

                text = event.raw_text or ""
                if not text.strip():
                    return

                chat_id = str(event.chat_id)
                msg_id = int(event.id)

                signal = parse_message(chat_id=chat_id, message_id=msg_id, text=text)
                self.manager.process(signal)
            except Exception as exc:
                logger.exception("Listener handler error: %s", exc)

        await self.client.start()
        logger.info("Telegram listener started.")
        await self.client.run_until_disconnected()
