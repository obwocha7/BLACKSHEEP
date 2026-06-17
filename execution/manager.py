from __future__ import annotations

import logging
from typing import Optional, List, Any

from domain.models import Signal, ActionType, Side
from storage.state_store import StateStore, SignalState
from execution.mt5_client import MT5Client
from execution.risk import compute_lot_by_risk, SymbolSpec
from config import Settings


logger = logging.getLogger(__name__)


class TradeManager:
    def __init__(self, settings: Settings, store: StateStore, mt5c: MT5Client):
        self.settings = settings
        self.store = store
        self.mt5 = mt5c

    def _pip_in_price(self) -> float:
        if not self.mt5.symbol:
            return 0.1
        if self.mt5.symbol.digits in (2, 3):
            return 0.1
        return self.mt5.symbol.point * 10.0

    def _sl_with_buffer(self, side: str, sl: Optional[float]) -> Optional[float]:
        if sl is None:
            return None
        if not self.settings.enable_sl_buffer:
            return sl
        buf = self.settings.sl_buffer_pips * self._pip_in_price()
        return float(sl - buf) if side.upper() == "BUY" else float(sl + buf)

    def _choose_entry_price(self, signal: Signal, phase: str = "first") -> Optional[float]:
        if signal.entry_low is not None and signal.entry_high is not None:
            if phase == "first":
                if signal.side == Side.BUY:
                    return signal.entry_high
                if signal.side == Side.SELL:
                    return signal.entry_low
            if phase == "second":
                if signal.side == Side.BUY:
                    return signal.entry_low
                if signal.side == Side.SELL:
                    return signal.entry_high
            return (signal.entry_low + signal.entry_high) / 2.0
        return signal.entry_low or signal.entry_high

    def _compute_volume(self, signal: Signal, entry_override: Optional[float] = None, sl_override: Optional[float] = None) -> float:
        if self.settings.risk_mode.lower() == "fixed":
            return self.settings.fixed_lot

        if not self.mt5.symbol:
            raise ValueError("MT5 symbol info missing for risk calc.")
        entry = entry_override if entry_override is not None else self._choose_entry_price(signal)
        sl_price = sl_override if sl_override is not None else signal.sl
        if entry is None or sl_price is None:
            raise ValueError("Risk mode requires entry and SL.")

        account = __import__("MetaTrader5").account_info()
        if account is None:
            raise ValueError("Cannot read MT5 account info.")

        spec = SymbolSpec(
            point=self.mt5.symbol.point,
            tick_value=self.mt5.symbol.trade_tick_value,
            tick_size=self.mt5.symbol.trade_tick_size,
            volume_min=self.mt5.symbol.volume_min,
            volume_max=self.mt5.symbol.volume_max,
            volume_step=self.mt5.symbol.volume_step,
        )
        return compute_lot_by_risk(
            equity=float(account.equity),
            risk_percent=self.settings.risk_percent,
            entry_price=float(entry),
            stop_loss_price=float(sl_price),
            spec=spec,
        )

    def _select_zone_entry(self, signal: Signal, side: str, preferred_price: Optional[float]) -> tuple[str, Optional[float]]:
        if not getattr(self.settings, "zone_entry_policy_enabled", False):
            return ("market", preferred_price)
        if signal.entry_low is None or signal.entry_high is None:
            return ("market", preferred_price)

        ba = self.mt5.current_bid_ask()
        if not ba:
            return ("market", preferred_price)
        bid, ask = ba
        px = ask if side == "BUY" else bid
        lo, hi = float(signal.entry_low), float(signal.entry_high)

        if lo <= px <= hi:
            return ("market", px)

        if side == "BUY":
            if px > hi:
                return ("limit", hi)
            if getattr(self.settings, "zone_entry_wait_outside_enabled", False):
                return ("wait", None)
            chase = getattr(self.settings, "zone_entry_chase_buffer_pips", 0.0) * self._pip_in_price()
            return ("market", lo + chase if chase > 0 else lo)

        if side == "SELL":
            if px < lo:
                return ("limit", lo)
            if getattr(self.settings, "zone_entry_wait_outside_enabled", False):
                return ("wait", None)
            chase = getattr(self.settings, "zone_entry_chase_buffer_pips", 0.0) * self._pip_in_price()
            return ("market", hi - chase if chase > 0 else hi)

        return ("market", preferred_price)

    def _resolve_reentry_role(self, signal: Signal, side: str) -> str:
        mode = (getattr(self.settings, "reentry_mode", "auto") or "auto").lower()
        if mode == "continuation":
            return "continuation"
        if mode == "post_sl_only":
            return "reentry"

        latest = self._latest_basket()
        if latest and latest.side and latest.side.upper() == side.upper():
            return "continuation"
        return "reentry"

    def _open_new_signal(self, signal: Signal, is_reentry: bool = False) -> None:
        side = signal.side.value if signal.side else None
        if side is None:
            logger.warning("Missing side in NEW_SIGNAL message_id=%s", signal.source_message_id)
            return

        entry_role = "primary"
        if is_reentry:
            entry_role = self._resolve_reentry_role(signal, side)

        if self.settings.auto_close_opposite and (not is_reentry or entry_role == "reentry"):
            opposite = "SELL" if side == "BUY" else "BUY"
            self.mt5.close_all_side(opposite)

        first_entry = self._choose_entry_price(signal, phase="first")
        second_entry = self._choose_entry_price(signal, phase="second")
        buffered_sl = self._sl_with_buffer(side, signal.sl)
        volume = self._compute_volume(signal, entry_override=first_entry, sl_override=buffered_sl)
        signal_group_id = signal.ensure_group_id()
        signal_id = self.store.create_signal_state(
            chat_id=signal.chat_id,
            source_message_id=signal.source_message_id,
            symbol=self.mt5.symbol.name if self.mt5.symbol else "XAUUSD",
            side=side,
            lifecycle="VALIDATED",
            sl=signal.sl,
            tp1=signal.tp1,
            tp2=signal.tp2,
            signal_group_id=signal_group_id,
            entry_role=entry_role,
        )

        if is_reentry and entry_role == "continuation":
            self.store.increment_continuation_add_count(signal_id)

        if signal.order_type and signal.order_type.value.endswith("LIMIT"):
            entry_price = first_entry
            if entry_price is None:
                logger.warning("Limit signal missing entry range.")
                return
            result = self.mt5.place_limit(side=side, volume=volume, price=entry_price, sl=buffered_sl, tp=signal.tp1)
            if result:
                ticket = int(getattr(result, "order", -1) if hasattr(result, "order") else -1)
                self.store.add_ticket(signal_id, ticket, side, volume, entry_price, status="PENDING")
                self.store.update_signal_lifecycle(signal_id, "PENDING")
            return

        entry_mode, entry_price = self._select_zone_entry(signal, side, first_entry)
        if entry_mode == "wait":
            logger.info("Zone-entry wait policy active; skipping immediate execution for signal=%s", signal.source_message_id)
            self.store.update_signal_lifecycle(signal_id, "VALIDATED")
            return

        if entry_mode == "limit":
            if entry_price is None:
                return
            result = self.mt5.place_limit(side=side, volume=volume, price=float(entry_price), sl=buffered_sl, tp=signal.tp1)
            if result:
                ticket = int(getattr(result, "order", -1) if hasattr(result, "order") else -1)
                self.store.add_ticket(signal_id, ticket, side, volume, float(entry_price), status="PENDING")
                self.store.update_signal_lifecycle(signal_id, "PENDING")
        else:
            result = self.mt5.place_market(side=side, volume=volume, sl=buffered_sl, tp=signal.tp1)
            if result:
                ticket = int(getattr(result, "order", -1) if hasattr(result, "order") else -1)
                deal_price = entry_price if entry_price is not None else (first_entry or 0.0)
                self.store.add_ticket(signal_id, ticket, side, volume, float(deal_price), status="OPEN")
                self.store.update_signal_lifecycle(signal_id, "OPEN")

        if self.settings.zone_second_entry_enabled and (signal.entry_low is not None and signal.entry_high is not None) and second_entry is not None and second_entry != first_entry:
            result2 = self.mt5.place_limit(side=side, volume=volume, price=float(second_entry), sl=buffered_sl, tp=signal.tp1)
            if result2:
                ticket2 = int(getattr(result2, "order", -1) if hasattr(result2, "order") else -1)
                self.store.add_ticket(signal_id, ticket2, side, volume, float(second_entry), status="PENDING")

    def _latest_basket(self) -> Optional[SignalState]:
        return self.store.get_latest_open_signal(symbol=self.mt5.symbol.name if self.mt5.symbol else "XAUUSD")

    def _close_percent_on_basket(self, signal_id: int, percent: float) -> None:
        tickets = self.store.get_open_tickets_for_signal(signal_id)
        for t in tickets:
            close_vol = max(0.0, float(t.volume) * (percent / 100.0))
            if close_vol <= 0:
                continue
            result = self.mt5.close_position_partial(ticket=int(t.mt5_ticket), side=t.side, volume_to_close=close_vol)
            if result:
                remaining = max(0.0, float(t.volume) - close_vol)
                new_status = "CLOSED" if remaining <= 0.0000001 else "PARTIAL_CLOSED"
                self.store.update_ticket_status(int(t.mt5_ticket), new_status, volume=remaining)

    def _move_sl_to_be(self, signal_id: int) -> None:
        tickets = self.store.get_open_tickets_for_signal(signal_id)
        buffer_price = 0.0
        if self.mt5.symbol:
            buffer_price = self.settings.be_buffer_points * self.mt5.symbol.point

        for t in tickets:
            entry = float(t.open_price)
            profit_lock = self.settings.be_profit_lock_points * (self.mt5.symbol.point if self.mt5.symbol else 0.0)
            if t.side.upper() == "BUY":
                be = entry + buffer_price + profit_lock
            else:
                be = entry - buffer_price - profit_lock
            self.mt5.modify_position_sl(ticket=int(t.mt5_ticket), sl=be)

    def _handle_tp1(self) -> None:
        basket = self._latest_basket()
        if not basket:
            return
        self._close_percent_on_basket(int(basket.id), self.settings.tp1_close_percent)
        if self.settings.be_after_tp1:
            self._move_sl_to_be(int(basket.id))
        self.store.update_signal_lifecycle(int(basket.id), "PARTIAL_CLOSED")

    def _handle_tp2(self) -> None:
        basket = self._latest_basket()
        if not basket:
            return
        self._close_percent_on_basket(int(basket.id), self.settings.tp2_close_percent)
        self.store.update_signal_lifecycle(int(basket.id), "CLOSED")

    def _handle_soft_partial(self) -> None:
        basket = self._latest_basket()
        if not basket:
            return
        self._close_percent_on_basket(int(basket.id), self.settings.default_soft_partial_percent)
        self.store.update_signal_lifecycle(int(basket.id), "PARTIAL_CLOSED")

    def _handle_close_percent(self, percent: float) -> None:
        basket = self._latest_basket()
        if not basket:
            return
        self._close_percent_on_basket(int(basket.id), percent)
        self.store.update_signal_lifecycle(int(basket.id), "PARTIAL_CLOSED")

    def _handle_move_sl(self, price: float) -> None:
        basket = self._latest_basket()
        if not basket:
            return
        tickets = self.store.get_open_tickets_for_signal(int(basket.id))
        for t in tickets:
            self.mt5.modify_position_sl(ticket=int(t.mt5_ticket), sl=price)

    def _trail_as_near_tp2(self, signal_id: int) -> None:
        if not self.settings.trailing_enabled:
            return
        basket = self._latest_basket()
        if not basket or basket.tp2 is None:
            return
        tickets = self.store.get_open_tickets_for_signal(signal_id)
        ba = self.mt5.current_bid_ask()
        if not ba:
            return
        bid, ask = ba
        for t in tickets:
            side = t.side.upper()
            cur = ask if side == "BUY" else bid
            entry = float(t.open_price)
            tp2 = float(basket.tp2)
            total = abs(tp2 - entry)
            if total <= 0:
                continue
            progressed = abs(cur - entry) / total * 100.0
            if progressed < self.settings.trailing_trigger_to_tp2_percent:
                continue
            step = self.settings.trailing_step_points * (self.mt5.symbol.point if self.mt5.symbol else 0.0)
            if side == "BUY":
                new_sl = cur - step
            else:
                new_sl = cur + step
            self.mt5.modify_position_sl(ticket=int(t.mt5_ticket), sl=float(new_sl))

    def _handle_close_all(self) -> None:
        basket = self._latest_basket()
        if not basket:
            return
        self._close_percent_on_basket(int(basket.id), 100.0)
        self.store.update_signal_lifecycle(int(basket.id), "CLOSED")

    def process(self, signal: Signal) -> None:
        self.store.add_message_event(signal.chat_id, signal.source_message_id, signal.action_type.value, signal.raw_text)

        if self.store.is_message_processed(signal.chat_id, signal.source_message_id):
            logger.info("Skipping duplicate message_id=%s", signal.source_message_id)
            return

        action = signal.action_type

        if action == ActionType.NOISE:
            self.store.mark_message_processed(signal.chat_id, signal.source_message_id)
            return

        if action in [ActionType.NEW_SIGNAL, ActionType.BUY_NOW, ActionType.SELL_NOW]:
            self._open_new_signal(signal, is_reentry=False)
        elif action == ActionType.RE_ENTRY:
            self._open_new_signal(signal, is_reentry=True)
        elif action == ActionType.TP1_HIT:
            self._handle_tp1()
        elif action == ActionType.TP2_HIT:
            self._handle_tp2()
        elif action == ActionType.SOFT_PARTIAL:
            self._handle_soft_partial()
        elif action == ActionType.CLOSE_PERCENT:
            self._handle_close_percent(float(signal.close_percent or self.settings.default_soft_partial_percent))
        elif action == ActionType.MOVE_SL:
            if signal.move_sl_to is not None:
                self._handle_move_sl(float(signal.move_sl_to))
        elif action == ActionType.CLOSE_ALL:
            self._handle_close_all()
        elif action == ActionType.DELETE_LIMITS:
            self.mt5.delete_all_limits()

        self.store.mark_message_processed(signal.chat_id, signal.source_message_id)
