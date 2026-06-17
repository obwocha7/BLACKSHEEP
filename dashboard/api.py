from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from typing import Dict, Any

from storage.state_store import StateStore
from execution.mt5_client import MT5Client


def create_app(store: StateStore, mt5c: MT5Client) -> FastAPI:
    app = FastAPI(title="Telegram MT5 Copier Dashboard")

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/state/summary")
    def state_summary():
        positions = mt5c.get_positions()
        orders = mt5c.get_orders()

        unrealized = sum(float(getattr(p, "profit", 0.0)) for p in positions) if positions else 0.0
        return {
            "open_positions": len(positions),
            "open_orders": len(orders),
            "unrealized_pnl": unrealized,
            "paused": store.get_flag("paused", "false") == "true",
        }

    @app.get("/positions")
    def positions():
        out = []
        for p in mt5c.get_positions():
            out.append(
                {
                    "ticket": int(p.ticket),
                    "symbol": p.symbol,
                    "type": int(p.type),
                    "volume": float(p.volume),
                    "price_open": float(p.price_open),
                    "sl": float(p.sl),
                    "tp": float(p.tp),
                    "profit": float(p.profit),
                }
            )
        return out

    @app.get("/orders")
    def orders():
        out = []
        for o in mt5c.get_orders():
            out.append(
                {
                    "ticket": int(o.ticket),
                    "symbol": o.symbol,
                    "type": int(o.type),
                    "volume_initial": float(o.volume_initial),
                    "price_open": float(o.price_open),
                    "sl": float(o.sl),
                    "tp": float(o.tp),
                }
            )
        return out

    @app.post("/controls/pause")
    def pause():
        store.set_flag("paused", "true")
        return {"ok": True, "paused": True}

    @app.post("/controls/resume")
    def resume():
        store.set_flag("paused", "false")
        return {"ok": True, "paused": False}

    @app.post("/controls/close-all")
    def close_all():
        mt5c.close_all_side("BUY")
        mt5c.close_all_side("SELL")
        return {"ok": True}

    @app.get("/", response_class=HTMLResponse)
    def home():
        return """
        <html>
          <head><title>Telegram MT5 Copier</title></head>
          <body style="font-family:Arial;max-width:900px;margin:40px auto;">
            <h1>Telegram MT5 Copier Dashboard</h1>
            <p>Use API endpoints:</p>
            <ul>
              <li><a href="/health">/health</a></li>
              <li><a href="/state/summary">/state/summary</a></li>
              <li><a href="/positions">/positions</a></li>
              <li><a href="/orders">/orders</a></li>
            </ul>
          </body>
        </html>
        """

    return app
