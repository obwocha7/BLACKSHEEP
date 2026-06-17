import re
from typing import Optional
from domain.models import Signal, ActionType, Side, OrderType


NOISE_PATTERNS = [
    r"free course",
    r"students already",
    r"special offer",
    r"click here",
    r"no experience needed",
]


def _has_noise(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in NOISE_PATTERNS)


def _extract_float(pattern: str, text: str) -> Optional[float]:
    m = re.search(pattern, text, flags=re.IGNORECASE)
    if not m:
        return None
    return float(m.group(1))


def parse_message(chat_id: str, message_id: int, text: str) -> Signal:
    raw = text.strip()

    if _has_noise(raw):
        return Signal(
            source_message_id=message_id,
            chat_id=chat_id,
            raw_text=raw,
            action_type=ActionType.NOISE,
        )

    low = _extract_float(
        r"(?:buy|sell)(?:[-\s]*limit)?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*[-–]\s*[0-9]+(?:\.[0-9]+)?",
        raw,
    )
    high = _extract_float(
        r"(?:buy|sell)(?:[-\s]*limit)?\s*[:\-]?\s*[0-9]+(?:\.[0-9]+)?\s*[-–]\s*([0-9]+(?:\.[0-9]+)?)",
        raw,
    )
    if low is None or high is None:
        low = _extract_float(r"([0-9]+(?:\.[0-9]+)?)\s*[-–]\s*[0-9]+(?:\.[0-9]+)?", raw)
        high = _extract_float(r"[0-9]+(?:\.[0-9]+)?\s*[-–]\s*([0-9]+(?:\.[0-9]+)?)", raw)

    sl = _extract_float(r"(?:sl|stop\s*loss)\s*(?:at)?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)", raw)
    tp1 = _extract_float(r"(?:tp1|take\s*profit\s*1)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)", raw)
    tp2 = _extract_float(r"(?:tp2|take\s*profit\s*2)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)", raw)
    move_sl_to = _extract_float(r"move\s*sl\s*to\s*([0-9]+(?:\.[0-9]+)?)", raw)

    side = None
    if re.search(r"\bbuy\b", raw, re.IGNORECASE):
        side = Side.BUY
    elif re.search(r"\bsell\b", raw, re.IGNORECASE):
        side = Side.SELL

    if re.search(r"new signal", raw, re.IGNORECASE):
        order_type = OrderType.MARKET
        if re.search(r"buy[-\s]*limit", raw, re.IGNORECASE):
            order_type = OrderType.BUY_LIMIT
        elif re.search(r"sell[-\s]*limit", raw, re.IGNORECASE):
            order_type = OrderType.SELL_LIMIT

        return Signal(
            source_message_id=message_id,
            chat_id=chat_id,
            raw_text=raw,
            action_type=ActionType.NEW_SIGNAL,
            side=side,
            order_type=order_type,
            entry_low=low,
            entry_high=high,
            sl=sl,
            tp1=tp1,
            tp2=tp2,
        )

    if re.search(r"\b(tp1 hit|tp1 reached)\b", raw, re.IGNORECASE):
        return Signal(message_id, chat_id, raw, ActionType.TP1_HIT)

    if re.search(r"\b(tp2 hit|tp2 reached)\b", raw, re.IGNORECASE):
        return Signal(message_id, chat_id, raw, ActionType.TP2_HIT)

    if move_sl_to is not None:
        return Signal(message_id, chat_id, raw, ActionType.MOVE_SL, move_sl_to=move_sl_to)

    close_pct = _extract_float(r"close\s*([0-9]+(?:\.[0-9]+)?)\s*%", raw)
    if close_pct is not None:
        return Signal(message_id, chat_id, raw, ActionType.CLOSE_PERCENT, close_percent=close_pct)

    if re.search(r"close.*completely|close gold completely", raw, re.IGNORECASE):
        return Signal(message_id, chat_id, raw, ActionType.CLOSE_ALL)

    # Handle mixed instruction blocks where close + now may appear together.
    # Prioritize explicit CLOSE_ALL semantics before handling buy/sell-now.
    if re.search(r"\bclose\s+gold\b", raw, re.IGNORECASE):
        return Signal(message_id, chat_id, raw, ActionType.CLOSE_ALL)

    if re.search(r"take some profits|secure some profits|book some profits|consider booking", raw, re.IGNORECASE):
        return Signal(message_id, chat_id, raw, ActionType.SOFT_PARTIAL)

    if re.search(r"stop\s*loss\s*hit", raw, re.IGNORECASE):
        return Signal(message_id, chat_id, raw, ActionType.CLOSE_ALL)

    if re.search(r"re-entry", raw, re.IGNORECASE):
        return Signal(
            source_message_id=message_id,
            chat_id=chat_id,
            raw_text=raw,
            action_type=ActionType.RE_ENTRY,
            side=side,
            entry_low=low,
            entry_high=high,
            sl=sl,
            tp1=tp1,
            tp2=tp2,
        )

    now_price = _extract_float(r"(?:buy|sell)\s*now(?:\s*at)?\s*([0-9]+(?:\.[0-9]+)?)", raw)
    if side is not None and re.search(r"(?:buy|sell)\s*now", raw, re.IGNORECASE):
        if now_price is None:
            now_price = low if low is not None else high
        return Signal(
            source_message_id=message_id,
            chat_id=chat_id,
            raw_text=raw,
            action_type=ActionType.BUY_NOW if side == Side.BUY else ActionType.SELL_NOW,
            side=side,
            order_type=OrderType.MARKET,
            entry_low=now_price,
            entry_high=now_price,
        )

    if re.search(r"delete all limit orders", raw, re.IGNORECASE):
        return Signal(message_id, chat_id, raw, ActionType.DELETE_LIMITS)

    return Signal(message_id, chat_id, raw, ActionType.NOISE)
