# Telegram → MT5 Copier Transition Guide (RDP Handover)

This document explains **why the code is structured this way**, what behavior is implemented, and exactly how to move to RDP with minimal friction.

---

## 1) Goal of this implementation

Build a production-safe copier that:
- reads Telegram gold signals,
- converts noisy/free-form messages into deterministic trade actions,
- executes and manages positions on MT5 safely,
- preserves state across restarts,
- handles partials, BE, re-entry/continuation, opposite signals, and reconciling.

The key design principle is: **message ambiguity must not produce unsafe execution**.

---

## 2) What was changed and why

## 2.1 `config.py`
Added knobs for behavior that was previously hard-coded, so you can tune without editing logic:

- `zone_entry_policy_enabled`
- `zone_entry_wait_outside_enabled`
- `zone_entry_chase_buffer_pips`
- `proactive_partials_enabled`
- `proactive_partial_first_percent`
- `proactive_partial_second_percent`
- `proactive_partial_near_tp_pips`
- `proactive_partial_medium_tp_pips`
- `proactive_partial_be_trigger_pips`
- `reentry_mode`
- `continuation_max_adds`
- `same_direction_close_on_reentry`

Also changed:
- `trailing_enabled` default = `false` (safer default for signal-following strategy).

**Why:** avoid risky defaults and allow quick behavior adaptation in live/demo without code edits.

---

## 2.2 `domain/models.py`
`Signal` now supports lineage:
- `signal_group_id`
- `entry_role` (`primary`, `reentry`, `continuation`)
- helper `ensure_group_id()`

**Why:** re-entry and continuation need grouping to manage linked positions safely and deterministically.

---

## 2.3 `storage/state_store.py`
`SignalState` schema extended with:
- `signal_group_id`
- `entry_role`
- `closed_reason`
- `continuation_add_count`

New store methods:
- `get_latest_open_signal_by_group`
- `get_group_active_signals`
- `set_signal_closed_reason`
- `increment_continuation_add_count`

`create_signal_state(...)` expanded with optional lineage/closure params.

**Why:** runtime control and reconciler need durable metadata to avoid duplicate/unsafe actions after restarts.

---

## 2.4 `execution/manager.py`
Core execution logic enhanced with:
- zone-smart entry selection (`_select_zone_entry`)
- re-entry role resolution (`_resolve_reentry_role`)
- lineage-aware `_open_new_signal` behavior
- continuation add limits and same-direction safety
- robust fallback reading of settings via `getattr(...)` (for compatibility with test fakes).

**Why:** supports real-world signal flow:
- same direction add-ons,
- re-entry after stop/close,
- controlled continuation,
- reduced accidental over-stacking.

---

## 2.5 Reconciler/test compatibility
No dependency changes; improved behavior compatibility.
Tests were stabilized by safe settings fallback in manager.

---

## 3) Telegram message → action mapping

These are the effective behavior rules:

### 3.1 New signal block
Examples:
- `BUY: a - b, SL, TP1, TP2`
- `SELL-Limit: a - b, SL, TP1, TP2`
- variants of case/emoji/wording

Action:
- parse direction, type (market/limit), zone, SL, TP1, TP2.
- apply zone entry policy.
- create linked `SignalState` with lineage metadata.

---

### 3.2 “Buy now / Sell now”
Action:
- immediate market order in that direction.
- if opposite signal rule enabled, close opposite trades first.

---

### 3.3 TP and partials
- `TP1 hit` → partial close + BE logic (unless explicit hold-same-SL instruction)
- `TP2 hit` → close remaining
- `Close 70%` (or any %) → close exact percent
- `Take/secure/book some profits` → default partial percent (you chose 25%)

---

### 3.4 Stop updates
- `Move SL to X` → modify SL on relevant active positions.

---

### 3.5 Close instructions
- `Close GOLD completely` / equivalent → close all relevant open positions.

---

### 3.6 Re-entry / continuation
- `For GOLD re-entry: ...` handled via lineage:
  - grouped under `signal_group_id`
  - role marked as reentry/continuation based on mode and current group state
- continuation additions constrained by `continuation_max_adds`.

---

### 3.7 Noise/promotional messages
- ignored by parser/action filter.

---

## 4) Risk model and safety rails

Default:
- risk-per-trade = **1%** (configurable)
- lot size computed from SL distance and symbol properties.

Safety controls:
- settings-driven behavior (no hidden magic constants),
- group lineage state prevents uncontrolled adds,
- optional same-direction close-on-reentry,
- opposite-direction close-before-open sequence,
- manager compatibility fallback prevents crashes when optional settings absent.

---

## 5) Why this is stable for handover

1. **Stateful lineage**: re-entry and continuation are not guessed each time.
2. **Config-first behavior**: operations can be tuned on RDP without code edits.
3. **Tested critical logic**: parser/manager/reconciler/risk/api test suite passing.
4. **Compatibility guard**: manager `getattr` fallback avoids fake-settings/runtime breakages.

---

## 6) Current test status

Automated tests executed:
- `pytest -q` → **21 passed**

Fix included from testing:
- manager now uses safe `getattr(...)` fallbacks for newly introduced settings fields.

---

## 7) Remaining runtime checks to perform on RDP (recommended)

Because MT5 runtime checks must run in active terminal session:

1) API curl tests:
- `/health`
- `/state`
- `/positions`
- `/orders`
- `/pause`
- `/resume`
- `/close-all`

2) DRY_RUN replay with mixed real messages:
- verify parse → action → state transitions

3) Live MT5 edge checks:
- zone boundary behavior
- re-entry vs continuation behavior
- opposite-close sequencing
- stale quote/slippage response

4) Reconciler runtime checks:
- closure reason synchronization
- orphan handling consistency

---

## 8) RDP migration/run checklist

1. Pull branch:
```bash
git checkout blackboxai/telegram-mt5-enhancements
git pull
```

2. Create/verify env:
- copy `.env.example` → `.env`
- fill Telegram + MT5 + risk settings

3. Install deps:
```bash
pip install -r requirements.txt
```

4. Start in DRY_RUN first:
- confirm parser decisions and no live order sends

5. Validate API endpoints and logs.

6. Switch to live only after DRY_RUN passes.

---

## 9) Recommended initial config on RDP

- keep trailing disabled initially
- keep `reentry_mode` conservative
- keep 1% risk default
- keep default partial = 25%
- keep opposite-close behavior enabled (as requested)

After first stable session, tune gradually.

---

## 10) Troubleshooting quick matrix

- **No MT5 connection**:
  - verify terminal open, logged in, algo-trading enabled, symbol visible.

- **Orders rejected**:
  - check stops level, spread, deviation, symbol trade mode.

- **Unexpected duplicate behavior**:
  - inspect state DB and message-id idempotency flow.

- **Parser misses message variant**:
  - capture raw text in logs and add parser pattern test before changing logic.

- **Settings attribute errors**:
  - should be mitigated by manager `getattr` fallback; verify latest branch pulled.

---

## 11) What to ask before changing live behavior

If you change any of these, retest DRY_RUN replay:
- `reentry_mode`
- continuation limit
- zone entry policy
- partial/BE thresholds
- opposite signal handling

---

## 12) Final handover note

This implementation prioritizes **safety, deterministic behavior, and restart resilience** over aggressive execution.  
Use DRY_RUN for every new parser/rule tweak before live enablement.
