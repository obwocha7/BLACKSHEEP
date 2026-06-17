from types import SimpleNamespace

from domain.models import Signal, ActionType, Side, OrderType
from execution.manager import TradeManager


class FakeSettings:
    risk_mode = "fixed"
    fixed_lot = 0.02
    auto_close_opposite = True
    tp1_close_percent = 50.0
    tp2_close_percent = 100.0
    be_after_tp1 = True
    be_buffer_points = 0
    be_profit_lock_points = 0
    enable_sl_buffer = False
    sl_buffer_pips = 5.0
    zone_second_entry_enabled = True
    zone_best_plus_pips_close_worst = 30.0
    trailing_enabled = True
    trailing_trigger_to_tp2_percent = 80.0
    trailing_step_points = 20
    default_soft_partial_percent = 25.0
    risk_percent = 1.0


class FakeStore:
    def __init__(self):
        self.processed = set()
        self.signal_id = 1
        self.lifecycle = "OPEN"
        self.tickets = [SimpleNamespace(mt5_ticket=101, side="BUY", volume=0.02, open_price=4300.0)]

    def add_message_event(self, *args, **kwargs):
        pass

    def is_message_processed(self, chat_id, message_id):
        return (chat_id, message_id) in self.processed

    def mark_message_processed(self, chat_id, message_id):
        self.processed.add((chat_id, message_id))

    def create_signal_state(self, **kwargs):
        return self.signal_id

    def add_ticket(self, *args, **kwargs):
        pass

    def update_signal_lifecycle(self, signal_id, lifecycle):
        self.lifecycle = lifecycle

    def get_latest_open_signal(self, symbol):
        return SimpleNamespace(id=1)

    def get_open_tickets_for_signal(self, signal_id):
        return self.tickets

    def update_ticket_status(self, mt5_ticket, status, volume=None):
        for t in self.tickets:
            if int(t.mt5_ticket) == int(mt5_ticket):
                t.volume = volume if volume is not None else t.volume


class FakeMT5:
    def __init__(self):
        self.symbol = SimpleNamespace(
            name="XAUUSD",
            point=0.1,
            trade_tick_value=1.0,
            trade_tick_size=0.1,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
        )
        self.calls = []

    def close_all_side(self, side):
        self.calls.append(("close_all_side", side))

    def place_market(self, side, volume, sl=None, tp=None):
        self.calls.append(("place_market", side, volume, sl, tp))
        return SimpleNamespace(order=1001)

    def place_limit(self, side, volume, price, sl=None, tp=None):
        self.calls.append(("place_limit", side, volume, price, sl, tp))
        return SimpleNamespace(order=1002)

    def close_position_partial(self, ticket, side, volume_to_close):
        self.calls.append(("close_partial", ticket, side, volume_to_close))
        return SimpleNamespace(retcode=10009)

    def modify_position_sl(self, ticket, sl):
        self.calls.append(("modify_sl", ticket, sl))
        return True

    def delete_all_limits(self):
        self.calls.append(("delete_all_limits",))


def test_manager_new_signal_market_and_opposite_close():
    m = TradeManager(FakeSettings(), FakeStore(), FakeMT5())
    s = Signal(
        source_message_id=1,
        chat_id="c1",
        raw_text="new",
        action_type=ActionType.NEW_SIGNAL,
        side=Side.BUY,
        order_type=OrderType.MARKET,
        entry_low=4300,
        entry_high=4304,
        sl=4295,
        tp1=4311,
        tp2=4325,
    )
    m.process(s)
    assert any(c[0] == "close_all_side" and c[1] == "SELL" for c in m.mt5.calls)
    assert any(c[0] == "place_market" for c in m.mt5.calls)


def test_manager_tp1_partial_and_be():
    store = FakeStore()
    mt5 = FakeMT5()
    m = TradeManager(FakeSettings(), store, mt5)
    s = Signal(source_message_id=2, chat_id="c1", raw_text="tp1", action_type=ActionType.TP1_HIT)
    m.process(s)
    assert any(c[0] == "close_partial" for c in mt5.calls)
    assert any(c[0] == "modify_sl" for c in mt5.calls)
    assert store.lifecycle == "PARTIAL_CLOSED"


def test_manager_tp2_close_remaining():
    store = FakeStore()
    mt5 = FakeMT5()
    m = TradeManager(FakeSettings(), store, mt5)
    s = Signal(source_message_id=3, chat_id="c1", raw_text="tp2", action_type=ActionType.TP2_HIT)
    m.process(s)
    assert any(c[0] == "close_partial" for c in mt5.calls)
    assert store.lifecycle == "CLOSED"


def test_manager_soft_partial_25pct():
    store = FakeStore()
    mt5 = FakeMT5()
    m = TradeManager(FakeSettings(), store, mt5)
    s = Signal(source_message_id=4, chat_id="c1", raw_text="take some", action_type=ActionType.SOFT_PARTIAL)
    m.process(s)
    partials = [c for c in mt5.calls if c[0] == "close_partial"]
    assert len(partials) == 1
    assert abs(partials[0][3] - 0.005) < 1e-6


def test_manager_close_percent_override():
    store = FakeStore()
    mt5 = FakeMT5()
    m = TradeManager(FakeSettings(), store, mt5)
    s = Signal(source_message_id=5, chat_id="c1", raw_text="close 70%", action_type=ActionType.CLOSE_PERCENT, close_percent=70)
    m.process(s)
    partials = [c for c in mt5.calls if c[0] == "close_partial"]
    assert len(partials) == 1
    assert abs(partials[0][3] - 0.014) < 1e-6


def test_manager_close_all():
    store = FakeStore()
    mt5 = FakeMT5()
    m = TradeManager(FakeSettings(), store, mt5)
    s = Signal(source_message_id=6, chat_id="c1", raw_text="close all", action_type=ActionType.CLOSE_ALL)
    m.process(s)
    assert any(c[0] == "close_partial" for c in mt5.calls)
    assert store.lifecycle == "CLOSED"
