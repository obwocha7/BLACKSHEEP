from types import SimpleNamespace

from execution.reconciler import Reconciler


class FakeStore:
    def __init__(self):
        self.closed = []
        self.added = []

    def get_latest_open_signal(self, symbol):
        return SimpleNamespace(id=1)

    def get_open_tickets_for_signal(self, signal_id):
        return [
            SimpleNamespace(mt5_ticket=100, side="BUY", volume=0.02, open_price=4300.0),
            SimpleNamespace(mt5_ticket=101, side="BUY", volume=0.02, open_price=4301.0),
        ]

    def update_ticket_status(self, tid, status, volume=0.0):
        self.closed.append((tid, status, volume))

    def add_ticket(self, signal_id, mt5_ticket, side, volume, open_price, status):
        self.added.append((signal_id, mt5_ticket, side, volume, open_price, status))


class FakeMT5:
    def __init__(self):
        self.symbol = SimpleNamespace(name="XAUUSD")

    def get_positions(self):
        return [
            SimpleNamespace(ticket=101, type=0, volume=0.02, price_open=4301.0),
            SimpleNamespace(ticket=202, type=1, volume=0.01, price_open=4310.0),
        ]

    def get_orders(self):
        return []


def test_reconciler_marks_missing_and_imports_orphan():
    store = FakeStore()
    mt5 = FakeMT5()
    r = Reconciler(store, mt5)

    report = r.reconcile()

    assert report["open_positions"] == 2
    assert report["db_open_tickets_checked"] == 2
    assert report["db_marked_closed"] == 1
    assert report["orphan_imported"] == 1

    assert any(x[0] == 100 and x[1] == "CLOSED" for x in store.closed)
    assert any(x[1] == 202 for x in store.added)
