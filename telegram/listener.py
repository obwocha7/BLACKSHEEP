from __future__ import annotations

import logging
from pathlib import Path
from telethon import TelegramClient, events

from config import Settings
from parser.signal_parser import parse_message
from execution.manager import TradeManager


logger = logging.getLogger(__name__)


class TelegramSignalListener:
    def __init__(self, settings: Settings, manager: TradeManager):
        self.settings = settings
        self.manager = manager

        session_value = (settings.tg_session_file or "").strip() or settings.tg_session_name
        self.session_value = session_value
        self.client = TelegramClient(session_value, settings.tg_api_id, settings.tg_api_hash)

        session_db = f"{session_value}.session" if not str(session_value).endswith(".session") else str(session_value)
        self.session_db_path = Path(session_db).resolve()

    def _allowed(self, event) -> bool:
        allowed = str(self.settings.tg_allowed_chat).strip().lower()
        chat = str(getattr(event.chat, "username", "") or "").strip().lower()
        chat_id = str(getattr(event, "chat_id", ""))
        return (allowed == chat) or (allowed == chat_id)

    async def authorize(self) -> None:
        logger.info("Telegram session target=%s", self.session_db_path)
        await self.client.connect()
        if await self.client.is_user_authorized():
            logger.info("Telegram session already authorized.")
            return

        logger.info("Telegram session not authorized. Starting interactive sign-in.")
        phone = input("Please enter your phone (international format, e.g. +2547...): ").strip()
        sent = await self.client.send_code_request(phone)
        logger.info(
            "Telegram code requested via app channel. type=%s timeout=%s",
            type(getattr(sent, "type", None)).__name__,
            getattr(sent, "timeout", None),
        )
        code = input("Enter Telegram code (or press Enter if not received): ").strip()

        if not code:
            logger.warning("No code entered. Retrying code request with force_sms=True.")
            sent_sms = await self.client.send_code_request(phone, force_sms=True)
            logger.info(
                "Telegram SMS code requested. type=%s timeout=%s",
                type(getattr(sent_sms, "type", None)).__name__,
                getattr(sent_sms, "timeout", None),
            )
            code = input("Enter Telegram SMS code: ").strip()

        try:
            await self.client.sign_in(phone=phone, code=code)
        except Exception as exc:
            if "password" in str(exc).lower():
                pwd = input("Please enter your Telegram 2FA password: ").strip()
                await self.client.sign_in(password=pwd)
            else:
                raise

        if not await self.client.is_user_authorized():
            raise RuntimeError("Telegram authorization failed: session remains unauthorized after sign-in flow.")
        logger.info("Telegram authorization completed and persisted.")

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

        logger.info("Telegram listener started.")
        await self.client.run_until_disconnected()
