from execution.risk import compute_lot_by_risk, SymbolSpec


def test_compute_lot_by_risk_basic():
    spec = SymbolSpec(
        point=0.1,
        tick_value=1.0,
        tick_size=0.1,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01,
    )
    lot = compute_lot_by_risk(
        equity=10000,
        risk_percent=1.0,
        entry_price=4300.0,
        stop_loss_price=4295.0,
        spec=spec,
    )
    assert lot >= 0.01
    assert lot <= 100.0


def test_compute_lot_clamped_to_min():
    spec = SymbolSpec(
        point=0.1,
        tick_value=1.0,
        tick_size=0.1,
        volume_min=0.05,
        volume_max=1.0,
        volume_step=0.01,
    )
    lot = compute_lot_by_risk(
        equity=1000,
        risk_percent=0.1,
        entry_price=4300,
        stop_loss_price=4299.9,
        spec=spec,
    )
    assert lot >= 0.05
