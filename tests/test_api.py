from types import SimpleNamespace

from fastapi.testclient import TestClient

from dashboard.api import create_app


class FakeStore:
    def __init__(self):
        self.flags = {}

    def get_flag(self, key, default=""):
        return self.flags.get(key, default)

    def set_flag(self, key, value):
        self.flags[key] = value


class FakeMT5:
    def __init__(self):
        self.calls = []

    def get_positions(self):
        return [
            SimpleNamespace(ticket=1, symbol="XAUUSD", type=0, volume=0.02, price_open=4300.0, sl=4295.0, tp=4311.0, profit=12.3)
        ]

    def get_orders(self):
        return []

    def close_all_side(self, side):
        self.calls.append(("close_all_side", side))
        return True


def test_api_health_and_summary_and_controls():
    store = FakeStore()
    mt5 = FakeMT5()
    app = create_app(store, mt5)
    c = TestClient(app)

    r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    r = c.get("/state/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["open_positions"] == 1
    assert body["open_orders"] == 0
    assert "unrealized_pnl" in body
    assert body["paused"] is False

    r = c.post("/controls/pause")
    assert r.status_code == 200
    assert r.json()["paused"] is True

    r = c.post("/controls/pause")
    assert r.status_code == 200
    assert r.json()["paused"] is True

    r = c.get("/state/summary")
    assert r.status_code == 200
    assert r.json()["paused"] is True

    r = c.post("/controls/resume")
    assert r.status_code == 200
    assert r.json()["paused"] is False

    r = c.post("/controls/resume")
    assert r.status_code == 200
    assert r.json()["paused"] is False

    r = c.post("/controls/close-all")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert ("close_all_side", "BUY") in mt5.calls
    assert ("close_all_side", "SELL") in mt5.calls


def test_api_positions_orders_and_home_routes():
    store = FakeStore()
    mt5 = FakeMT5()
    app = create_app(store, mt5)
    c = TestClient(app)

    r = c.get("/positions")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["ticket"] == 1
    assert body[0]["symbol"] == "XAUUSD"

    r = c.get("/orders")
    assert r.status_code == 200
    assert r.json() == []

    r = c.get("/")
    assert r.status_code == 200
    assert "Telegram MT5 Copier Dashboard" in r.text
