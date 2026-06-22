# TODO

- [x] Add explicit `TG_SESSION_FILE` support in config and propagate to Telegram client initialization.
- [x] Harden Telegram authorize flow with clear session-path/authorization logging and optional 2FA handling.
- [x] Update `run_bot.bat` to set `TG_SESSION_FILE`, validate session directory/file access, and improve diagnostics.
- [x] Add `auth_bootstrap.py` utility for one-time interactive session generation/refresh.
- [x] Add single-instance/port-ownership guard in `run_bot.bat` to avoid 8080 bind collisions.
- [x] Re-run scheduler recovery tests and API validation after guard change.
- [x] Mitigate Windows log rotation lock contention (`WinError 32`) and verify via rerun logs.
- [x] Run extended soak validation after logging fix.
- [x] Run reboot auto-start validation and capture final evidence.
