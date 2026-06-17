from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Any, List

from storage.state_store import StateStore
from execution.mt5_client import MT5Client


logger = logging.getLogger(__name__)


class Reconciler:
    def __init__(self, store: StateStore, mt5c: MT5Client):
        self.store = store
        self.mt5 = mt5c

    def reconcile(self) -> Dict[str, int]:
        report = {
            "open_positions": 0,
            "open_orders": 0,
            "db_open_tickets_checked": 0,
            "db_marked_closed": 0,
            "orphan_imported": 0,
        }

        positions = self.mt5.get_positions()
        orders = self.mt5.get_orders()
        report["open_positions"] = len(positions)
        report["open_orders"] = len(orders)

        latest = self.store.get_latest_open_signal(symbol=self.mt5.symbol.name if self.mt5.symbol else "XAUUSD")
        if latest:
            tickets = self.store.get_open_tickets_for_signal(int(latest.id))
            report["db_open_tickets_checked"] = len(tickets)

            mt5_pos_tickets = {int(p.ticket) for p in positions}
            mt5_ord_tickets = {int(o.ticket) for o in orders}

            for t in tickets:
                tid = int(t.mt5_ticket)
                if tid not in mt5_pos_tickets and tid not in mt5_ord_tickets:
                    self.store.update_ticket_status(tid, "CLOSED", volume=0.0)
                    report["db_marked_closed"] += 1

            db_tickets = {int(t.mt5_ticket) for t in tickets}
            for p in positions:
                if int(p.ticket) not in db_tickets:
                    side = "BUY" if int(p.type) == 0 else "SELL"
                    self.store.add_ticket(
                        signal_id=int(latest.id),
                        mt5_ticket=int(p.ticket),
                        side=side,
                        volume=float(p.volume),
                        open_price=float(p.price_open),
                        status="OPEN",
                    )
                    report["orphan_imported"] += 1

        logger.info("reconcile_report=%s", report)
        return report
