from __future__ import annotations

import argparse
import asyncio
import logging
import threading
import time

import uvicorn

from config import settings
from logging_setup import setup_logging
from storage.state_store import StateStore
from execution.mt5_client import MT5Client
from execution.manager import TradeManager
from execution.reconciler import Reconciler
from telegram.listener import TelegramSignalListener
from dashboard.api import create_app


logger = logging.getLogger(__name__)


def run_dashboard(store: StateStore, mt5c: MT5Client) -> None:
    app = create_app(store, mt5c)
    uvicorn.run(app, host=settings.dashboard_host, port=settings.dashboard_port, log_level="info")


def run_reconciler_loop(reconciler: Reconciler, interval: int) -> None:
    while True:
        try:
            reconciler.reconcile()
        except Exception as exc:
            logger.exception("Reconciler error: %s", exc)
        time.sleep(interval)


def diagnose(mt5c: MT5Client) -> int:
    print("=== DIAGNOSE START ===")
    try:
        settings.validate_required()
        print("Config validation: OK")
    except Exception as e:
        print(f"Config validation failed: {e}")
        return 1

    if not mt5c.connect():
        print("MT5 connect: FAILED")
        return 2
    print("MT5 connect: OK")

    sym = mt5c.discover_xau_symbol(settings.mt5_symbol)
    if not sym:
        print("MT5 symbol discovery: FAILED")
        return 3
    print(f"MT5 symbol discovery: OK ({sym.name})")

    tick = mt5c.get_tick(sym.name)
    if tick is None:
        print("MT5 tick read: FAILED")
        return 4
    print(f"MT5 tick read: OK (bid={tick.bid}, ask={tick.ask})")
    print("=== DIAGNOSE END ===")
    return 0


async def run_system(listener: TelegramSignalListener, store: StateStore, mt5c: MT5Client, reconciler: Reconciler) -> None:
    await listener.authorize()

    t_dash = threading.Thread(target=run_dashboard, args=(store, mt5c), daemon=True)
    t_dash.start()

    t_rec = threading.Thread(
        target=run_reconciler_loop,
        args=(reconciler, settings.reconcile_interval_seconds),
        daemon=True,
    )
    t_rec.start()

    await listener.start()


def main() -> None:
    parser = argparse.ArgumentParser(description="Telegram MT5 Copier")
    parser.add_argument("--diagnose", action="store_true", help="Run diagnostics and exit")
    args = parser.parse_args()

    setup_logging(settings.log_level)

    store = StateStore(settings.db_url)
    mt5c = MT5Client(
        login=settings.mt5_login,
        password=settings.mt5_password,
        server=settings.mt5_server,
        path=settings.mt5_path,
        magic=settings.mt5_magic,
        deviation_points=settings.slippage_deviation_points,
        dry_run=settings.dry_run,
    )

    if args.diagnose:
        code = diagnose(mt5c)
        mt5c.shutdown()
        raise SystemExit(code)

    settings.validate_required()

    if not mt5c.connect():
        raise RuntimeError("Failed to connect to MT5 terminal.")

    symbol = mt5c.discover_xau_symbol(settings.mt5_symbol)
    if not symbol:
        raise RuntimeError("Could not discover tradable XAU symbol.")

    manager = TradeManager(settings, store, mt5c)
    reconciler = Reconciler(store, mt5c)

    listener = TelegramSignalListener(settings, manager)
    try:
        asyncio.run(run_system(listener, store, mt5c, reconciler))
    finally:
        mt5c.shutdown()


if __name__ == "__main__":
    main()
