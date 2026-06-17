from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, List, Tuple, Any

import MetaTrader5 as mt5


logger = logging.getLogger(__name__)


@dataclass
class Mt5SymbolInfo:
    name: str
    digits: int
    point: float
    trade_tick_size: float
    trade_tick_value: float
    volume_min: float
    volume_max: float
    volume_step: float
    stops_level: int


class MT5Client:
    def __init__(
        self,
        login: int,
        password: str,
        server: str,
        path: str = "",
        magic: int = 260617,
        deviation_points: int = 50,
        dry_run: bool = True,
    ):
        self.login = login
        self.password = password
        self.server = server
        self.path = path
        self.magic = magic
        self.deviation_points = deviation_points
        self.dry_run = dry_run
        self.symbol: Optional[Mt5SymbolInfo] = None

    def connect(self) -> bool:
        kwargs = {"login": self.login, "password": self.password, "server": self.server}
        if self.path:
            ok = mt5.initialize(path=self.path, **kwargs)
        else:
            ok = mt5.initialize(**kwargs)

        if not ok:
            logger.error("MT5 initialize failed: %s", mt5.last_error())
            return False

        account = mt5.account_info()
        if account is None:
            logger.error("MT5 account_info unavailable: %s", mt5.last_error())
            return False

        logger.info("MT5 connected account=%s server=%s", account.login, account.server)
        return True

    def shutdown(self) -> None:
        mt5.shutdown()

    def discover_xau_symbol(self, preferred: str = "auto") -> Optional[Mt5SymbolInfo]:
        if preferred and preferred.lower() != "auto":
            info = mt5.symbol_info(preferred)
            if info and info.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED:
                if not info.visible:
                    mt5.symbol_select(preferred, True)
                self.symbol = self._to_symbol_info(info)
                return self.symbol

        all_symbols = mt5.symbols_get()
        if not all_symbols:
            logger.error("No symbols available in MT5 terminal.")
            return None

        candidates = []
        for s in all_symbols:
            nm = (s.name or "").upper()
            if "XAUUSD" in nm and s.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED:
                candidates.append(s)

        if not candidates:
            logger.error("No tradable XAUUSD-like symbol found.")
            return None

        candidates.sort(key=lambda x: (0 if x.visible else 1, len(x.name)))
        chosen = candidates[0]
        if not chosen.visible:
            mt5.symbol_select(chosen.name, True)

        self.symbol = self._to_symbol_info(chosen)
        logger.info("Selected MT5 symbol: %s", self.symbol.name)
        return self.symbol

    def _to_symbol_info(self, info: Any) -> Mt5SymbolInfo:
        return Mt5SymbolInfo(
            name=info.name,
            digits=info.digits,
            point=info.point,
            trade_tick_size=info.trade_tick_size,
            trade_tick_value=info.trade_tick_value,
            volume_min=info.volume_min,
            volume_max=info.volume_max,
            volume_step=info.volume_step,
            stops_level=info.trade_stops_level,
        )

    def get_tick(self, symbol: Optional[str] = None):
        sym = symbol or (self.symbol.name if self.symbol else None)
        if not sym:
            return None
        return mt5.symbol_info_tick(sym)

    def current_bid_ask(self, symbol: Optional[str] = None) -> Optional[Tuple[float, float]]:
        t = self.get_tick(symbol)
        if t is None:
            return None
        return float(t.bid), float(t.ask)

    def _order_send(self, request: dict):
        if self.dry_run:
            logger.info("DRY_RUN order_send: %s", request)
            return {"retcode": 0, "order": -1, "deal": -1, "comment": "dry-run"}
        result = mt5.order_send(request)
        if result is None:
            logger.error("order_send None result: %s", mt5.last_error())
            return None
        return result

    def place_market(self, side: str, volume: float, sl: Optional[float], tp: Optional[float]) -> Optional[Any]:
        if not self.symbol:
            logger.error("Symbol not initialized.")
            return None

        tick = self.get_tick(self.symbol.name)
        if not tick:
            logger.error("No tick for symbol %s", self.symbol.name)
            return None

        is_buy = side.upper() == "BUY"
        order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
        price = float(tick.ask if is_buy else tick.bid)

        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol.name,
            "volume": float(volume),
            "type": order_type,
            "price": price,
            "sl": float(sl) if sl else 0.0,
            "tp": float(tp) if tp else 0.0,
            "deviation": self.deviation_points,
            "magic": self.magic,
            "comment": "tg_copier_market",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        return self._order_send(req)

    def place_limit(self, side: str, volume: float, price: float, sl: Optional[float], tp: Optional[float]) -> Optional[Any]:
        if not self.symbol:
            logger.error("Symbol not initialized.")
            return None

        is_buy = side.upper() == "BUY"
        order_type = mt5.ORDER_TYPE_BUY_LIMIT if is_buy else mt5.ORDER_TYPE_SELL_LIMIT

        req = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": self.symbol.name,
            "volume": float(volume),
            "type": order_type,
            "price": float(price),
            "sl": float(sl) if sl else 0.0,
            "tp": float(tp) if tp else 0.0,
            "deviation": self.deviation_points,
            "magic": self.magic,
            "comment": "tg_copier_limit",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }
        return self._order_send(req)

    def modify_position_sl(self, ticket: int, sl: float, tp: Optional[float] = None) -> Optional[Any]:
        if not self.symbol:
            return None

        req = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": self.symbol.name,
            "position": int(ticket),
            "sl": float(sl),
            "tp": float(tp) if tp else 0.0,
            "magic": self.magic,
            "comment": "tg_copier_move_sl",
        }
        return self._order_send(req)

    def close_position_partial(self, ticket: int, side: str, volume_to_close: float) -> Optional[Any]:
        if not self.symbol:
            return None

        tick = self.get_tick(self.symbol.name)
        if not tick:
            return None

        is_buy_position = side.upper() == "BUY"
        close_type = mt5.ORDER_TYPE_SELL if is_buy_position else mt5.ORDER_TYPE_BUY
        price = float(tick.bid if is_buy_position else tick.ask)

        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol.name,
            "position": int(ticket),
            "volume": float(volume_to_close),
            "type": close_type,
            "price": price,
            "deviation": self.deviation_points,
            "magic": self.magic,
            "comment": "tg_copier_partial_close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        return self._order_send(req)

    def get_positions(self) -> List[Any]:
        if not self.symbol:
            return []
        rows = mt5.positions_get(symbol=self.symbol.name)
        return list(rows) if rows else []

    def get_orders(self) -> List[Any]:
        if not self.symbol:
            return []
        rows = mt5.orders_get(symbol=self.symbol.name)
        return list(rows) if rows else []

    def close_all_side(self, side: str) -> List[Any]:
        results = []
        positions = self.get_positions()
        for p in positions:
            pside = "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL"
            if pside == side.upper():
                results.append(self.close_position_partial(p.ticket, pside, p.volume))
        return results

    def delete_all_limits(self) -> List[Any]:
        results = []
        for o in self.get_orders():
            if o.type in (mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_SELL_LIMIT):
                req = {
                    "action": mt5.TRADE_ACTION_REMOVE,
                    "order": int(o.ticket),
                    "symbol": o.symbol,
                    "magic": self.magic,
                    "comment": "tg_copier_delete_limit",
                }
                results.append(self._order_send(req))
        return results
