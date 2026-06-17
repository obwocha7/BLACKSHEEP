from dataclasses import dataclass


@dataclass
class SymbolSpec:
    point: float
    tick_value: float
    tick_size: float
    volume_min: float
    volume_max: float
    volume_step: float


def _round_to_step(value: float, step: float) -> float:
    n = round(value / step)
    return round(n * step, 8)


def compute_lot_by_risk(
    equity: float,
    risk_percent: float,
    entry_price: float,
    stop_loss_price: float,
    spec: SymbolSpec,
) -> float:
    risk_amount = equity * (risk_percent / 100.0)
    distance = abs(entry_price - stop_loss_price)
    if distance <= 0:
        raise ValueError("Invalid SL distance for risk calculation.")

    value_per_price_unit_per_lot = spec.tick_value / spec.tick_size
    loss_per_lot = distance * value_per_price_unit_per_lot

    if loss_per_lot <= 0:
        raise ValueError("Invalid symbol tick settings for risk calculation.")

    raw_lot = risk_amount / loss_per_lot
    stepped = _round_to_step(raw_lot, spec.volume_step)
    stepped = max(spec.volume_min, min(spec.volume_max, stepped))
    return stepped
