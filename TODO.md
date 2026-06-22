# TODO - Session Auth Hardening

- [x] Harden Telethon auth flow in `telegram/listener.py` (explicit sign-in path, OTP fallback, post-auth authorization checks)
- [x] Improve bootstrap observability/failure behavior in `auth_bootstrap.py`
- [x] Add scheduler/session preflight and fail-fast behavior in `run_bot.bat`
- [x] Validate scheduler startup and API endpoints (`/`, `/health`, `/state/summary`, `/positions`, `/orders`, 404/405)
- [x] Validate soak/PID stability
- [ ] Patch `run_bot.bat` to emit deterministic `SESSION_RESTORE_ACTION` + `SESSION_RESTORE_RESULT` markers for all branches
- [ ] Run deterministic missing-session restore cycle with file-based capture (`logs/restore_health.txt`, `logs/restore_markers.txt`)
- [ ] Update `docs/session-hardening.md` with exact captured restore proof
- [ ] Commit and push final thorough-fix updates to `blackboxai/session-auth-hardening`

## RDP thorough runtime + transition hardening
- [x] Backup old state.db and recreate schema-compatible DB
- [x] Launch app and verify API endpoints via curl
- [x] Validate reconciler/DRY_RUN runtime stability
- [ ] Add full transition documentation for future machine migration
- [ ] Commit all updates on blackboxai/setup-and-thorough-testing
