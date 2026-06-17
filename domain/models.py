from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
from datetime import datetime, timezone
import uuid


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    BUY_LIMIT = "BUY_LIMIT"
    SELL_LIMIT = "SELL_LIMIT"


class ActionType(str, Enum):
    NEW_SIGNAL = "NEW_SIGNAL"
    BUY_NOW = "BUY_NOW"
    SELL_NOW = "SELL_NOW"
    RE_ENTRY = "RE_ENTRY"
    MOVE_SL = "MOVE_SL"
    TP1_HIT = "TP1_HIT"
    TP2_HIT = "TP2_HIT"
    SOFT_PARTIAL = "SOFT_PARTIAL"
    CLOSE_PERCENT = "CLOSE_PERCENT"
    CLOSE_ALL = "CLOSE_ALL"
    DELETE_LIMITS = "DELETE_LIMITS"
    NOISE = "NOISE"


@dataclass
class Signal:
    source_message_id: int
    chat_id: str
    raw_text: str
    action_type: ActionType
    symbol_hint: str = "XAUUSD"
    side: Optional[Side] = None
    order_type: Optional[OrderType] = None
    entry_low: Optional[float] = None
    entry_high: Optional[float] = None
    sl: Optional[float] = None
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    close_percent: Optional[float] = None
    move_sl_to: Optional[float] = None
    signal_group_id: Optional[str] = None
    entry_role: str = "primary"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def ensure_group_id(self) -> str:
        if self.signal_group_id:
            return self.signal_group_id
        self.signal_group_id = f"{self.chat_id}:{uuid.uuid4().hex[:12]}"
        return self.signal_group_id


@dataclass
class TicketLink:
    signal_id: int
    mt5_ticket: int
    side: Side
    volume: float
    open_price: float
    status: str
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Decision:
    accepted: bool
    reason: str
    notes: List[str] = field(default_factory=list)
