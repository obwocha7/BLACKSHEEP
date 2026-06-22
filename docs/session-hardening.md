# Telegram Session Hardening & Scheduler Reliability

## Summary

This document describes the reliability hardening implemented for Telegram authorization/session reuse in scheduled runs, including startup-order fixes, deterministic session pathing, bootstrap auth flow, and verification evidence.

## Problem Statement

Scheduled task runs intermittently prompted for interactive Telegram login:

- `Please enter your phone (or bot token):`
- `Please enter the code you received:`

This blocked unattended execution and could cascade into unstable startup behavior.

## Root Causes Identified

1. Session reuse across run contexts was not explicit enough.
2. Scheduler and interactive runs could diverge in runtime context.
3. Startup ordering needed strict gating (auth first, then runtime services).
4. Potential port conflict (`127.0.0.1:8080`) occurred during overlapping reruns.

## Implemented Changes

### 1) Config: explicit Telegram session file env support

**File:** `config.py`

Added new setting:
- `tg_session_file` sourced from `TG_SESSION_FILE` (optional; trims whitespace)

Behavior:
- If `TG_SESSION_FILE` is set, it is used as canonical Telethon session target.
- Otherwise existing `TG_SESSION_NAME` behavior remains.

---

### 2) Telegram listener: deterministic session target + safer auth flow

**File:** `telegram/listener.py`

Changes:
- Added support for explicit session selection:
  - `session_value = tg_session_file or tg_session_name`
- Logs effective resolved session file target at auth time.
- Keeps explicit `authorize()` flow before listener starts.
- Added explicit code request + fallback logic:
  - `send_code_request(phone)` for in-app code,
  - if no code entered, retries with `send_code_request(phone, force_sms=True)`.
- Added 2FA fallback branch during sign-in (if Telegram password is required).
- Verifies authorization persistence after sign-in and raises on failure.

Operational effect:
- Improved visibility of exact session file in use.
- Better resilience when in-app OTP is delayed/unavailable.
- Better resilience for accounts with Telegram 2FA enabled.

---

### 3) Scheduler runner hardening

**File:** `run_bot.bat`

Changes:
- Sets deterministic env:
  - `TG_SESSION_FILE=C:\Users\Administrator\Desktop\BLACKSHEEP\tg_mt5_session`
- Logs these values into `logs\runner.env.log`:
  - `TG_SESSION_FILE`
  - `TG_SESSION_DB` (`.session` derivative)
  - `SESSION_FILE_EXISTS` preflight check
- Preserves existing run/error/env logging and exit code capture.

Operational effect:
- Scheduled runs are pinned to the same intended session artifact path.
- Easier diagnostics of session continuity per scheduled invocation.

---

### 4) One-time bootstrap script for session creation/repair

**File:** `auth_bootstrap.py`

Purpose:
- Perform controlled interactive authorization once and persist session.
- Disconnect cleanly after auth.
- Log resulting session file and existence status.

Usage:
```bat
cd C:\Users\Administrator\Desktop\BLACKSHEEP
set TG_SESSION_FILE=C:\Users\Administrator\Desktop\BLACKSHEEP\tg_mt5_session
.venv\Scripts\python.exe auth_bootstrap.py
```

When prompted:
1. Enter phone number / bot token
2. Enter OTP code
3. Enter Telegram 2FA password if prompted

---

## Existing Startup-Order Reliability (already integrated)

### `app.py` single-loop lifecycle

The service uses one asyncio loop for authorization and listener lifecycle, avoiding Telethon loop-switch errors:

- Authorize Telegram first
- Start dashboard/reconciler only after successful auth
- Start Telegram listener on the same loop

This prevents:
- `RuntimeError: The asyncio event loop must not change after connection`

---

## Verification Evidence

### 2026-06-22 latest validation snapshot

- Interactive bootstrap completed successfully with correct phone/code.
- Explicit auth probe returned `AUTHORIZED=True`.
- Scheduler run showed:
  - `Telegram session already authorized.`
  - `Telegram listener started.`
- API checks passed on active scheduler run:
  - `GET /health` -> 200
  - `GET /state/summary` -> 200
- Soak/PID stability metrics:
  - `SOAK_OK=6`
  - `SOAK_FAIL=0`
  - `LISTENER_PID_UNIQUE_COUNT=1`
  - `LISTENER_PIDS=4360`

## A) API and endpoint checks

Verified via curl:

- `GET /` -> 200 (dashboard HTML)
- `GET /health` -> 200 `{"ok":true}`
- `GET /state/summary` -> 200 valid JSON
- `GET /positions` -> 200 `[]`
- `GET /orders` -> 200 `[]`
- `GET /nonexistent` -> 404
- `POST /health` -> 405

## B) Scheduler/session validation

From scheduled-run logs:
- runtime user context captured (`USERNAME=trader`)
- session target logged:
  - `Telegram session target=C:\Users\Administrator\Desktop\BLACKSHEEP\tg_mt5_session.session`
- authorization reuse confirmed:
  - `Telegram session already authorized.`
- listener startup confirmed:
  - `Telegram listener started.`

## C) Restart and port conflict handling

Observed one overlapping-run bind failure:
- `[Errno 10048] ... bind on ('127.0.0.1', 8080)`

After forced cleanup + rerun:
- Uvicorn successfully running on `127.0.0.1:8080`
- `/health` and `/state/summary` returned 200

---

## Recommended Operational Runbook

1. **Initial setup / repair (interactive once):**
   - Run `auth_bootstrap.py` with `TG_SESSION_FILE` set.
2. **Scheduled unattended operation:**
   - Use `run_bot.bat` through Task Scheduler.
3. **If login prompts recur:**
   - Confirm `TG_SESSION_FILE` path
   - Confirm session file exists and is readable
   - Re-run bootstrap script once
4. **If API fails to bind 8080:**
   - stop prior listener process on 8080
   - rerun scheduled task

---

## Security & Repo Hygiene Notes

Do **not** commit sensitive/runtime artifacts:
- `.env`
- `*.session`
- `state.db`
- `logs/*`
- `__pycache__/`
- `*.pyc`

Only commit source/config/docs/scripts required for deterministic behavior.
