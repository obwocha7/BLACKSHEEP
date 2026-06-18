# TODO

- [ ] Add explicit `TG_SESSION_FILE` support in config and propagate to Telegram client initialization.
- [ ] Harden Telegram authorize flow with clear session-path/authorization logging and optional 2FA handling.
- [ ] Update `run_bot.bat` to set `TG_SESSION_FILE`, validate session directory/file access, and improve diagnostics.
- [ ] Add `auth_bootstrap.py` utility for one-time interactive session generation/refresh.
- [ ] Run full validation: scheduler run, log inspection, and API checks (`/health`, `/state/summary`), then mark complete.
