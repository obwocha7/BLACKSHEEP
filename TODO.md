# BLACKSHEEP Telegram Session Hardening TODO

- [x] Add session preflight restore/fail-fast guard in `run_bot.bat`
- [x] Harden auth bootstrap observability and explicit unauthorized failure
- [x] Update listener authorize flow to use robust interactive start/post-check
- [x] Add OTP fallback logic in listener (`send_code_request` + `force_sms=True` retry)
- [x] Complete interactive auth and verify `AUTHORIZED=True`
- [x] Verify scheduler non-interactive startup with persisted session
- [x] Run API verification (`/health`, `/state/summary`) after scheduler start
- [x] Run soak/PID stability checks and confirm listener stays up
- [ ] Validate missing-session simulation and recovery end-to-end (attempted; blocked by Windows file lock/truncated terminal capture)
