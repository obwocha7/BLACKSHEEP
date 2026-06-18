from parser.signal_parser import parse_message
from domain.models import ActionType, Side, OrderType


def test_parse_new_signal_buy_limit():
    text = """
🔔 NEW SIGNAL: GOLD/XAUUSD
🔷 BUY-Limit: 4160 - 4165
🔴 SL: 4155
✔️ TP1: 4172
✔️ TP2: 4188
"""
    s = parse_message("chat1", 1, text)
    assert s.action_type == ActionType.NEW_SIGNAL
    assert s.side == Side.BUY
    assert s.order_type == OrderType.BUY_LIMIT
    assert s.entry_low == 4160
    assert s.entry_high == 4165
    assert s.sl == 4155
    assert s.tp1 == 4172
    assert s.tp2 == 4188


def test_parse_tp1():
    s = parse_message("chat1", 2, "GOLD - TP1 HIT ✔️")
    assert s.action_type == ActionType.TP1_HIT


def test_parse_tp2():
    s = parse_message("chat1", 3, "Gold - tp2 reached ✔️")
    assert s.action_type == ActionType.TP2_HIT


def test_parse_move_sl():
    s = parse_message("chat1", 4, "Move SL to 4321.")
    assert s.action_type == ActionType.MOVE_SL
    assert s.move_sl_to == 4321


def test_parse_close_percent():
    s = parse_message("chat1", 5, "Close 70% of the trade")
    assert s.action_type == ActionType.CLOSE_PERCENT
    assert s.close_percent == 70


def test_parse_soft_partial():
    s = parse_message("chat1", 6, "Take some profits")
    assert s.action_type == ActionType.SOFT_PARTIAL


def test_parse_close_all():
    s = parse_message("chat1", 7, "Close GOLD completely at 4322.")
    assert s.action_type == ActionType.CLOSE_ALL


def test_parse_reentry():
    s = parse_message("chat1", 8, "For GOLD re-entry: 4329-4331 with SL at 4335")
    assert s.action_type == ActionType.RE_ENTRY
    assert s.entry_low == 4329
    assert s.entry_high == 4331
    assert s.sl == 4335


def test_parse_now():
    s = parse_message("chat1", 9, "gold buy now 4353.5")
    assert s.action_type == ActionType.BUY_NOW
    assert s.side == Side.BUY
    assert s.entry_low == 4353.5


def test_parse_noise():
    s = parse_message("chat1", 10, "✨ 38,000+ students already started earning with me ✨")
    assert s.action_type == ActionType.NOISE


def test_parse_close_gold_buy_then_sell_now_block_prefers_close_all():
    s = parse_message(
        "chat1",
        11,
        "Close GOLD BUY 4324\nGOLD SELL NOW\nScalp Setup\n4322-4325 If the market is unable to break this range",
    )
    assert s.action_type == ActionType.CLOSE_ALL


def test_parse_stop_loss_hit_maps_to_close_all():
    s = parse_message("chat1", 12, "Stop loss hit ! ❌\n-45 pips!")
    assert s.action_type == ActionType.CLOSE_ALL


def test_parse_sell_now_without_explicit_now_price_uses_range():
    s = parse_message("chat1", 13, "GOLD SELL NOW\n4322-4325")
    assert s.action_type == ActionType.SELL_NOW
    assert s.side == Side.SELL
    assert s.entry_low == 4322
    assert s.entry_high == 4322
