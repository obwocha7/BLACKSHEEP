# TODO - Telegram → MT5 Copier Enhancements

## Approved implementation scope
- [ ] Zone-smart entry policy (inside zone market, outside zone next-best limit/wait rules, slippage/TTL guards)
- [ ] Proactive partial ladder (pre-TP1), with channel-command overrides
- [ ] BE improvements (+buffer) and optional step trailing controls
- [ ] Re-entry vs continuation tracking with signal lineage
- [ ] Configurable `REENTRY_MODE` logic: auto/continuation/post_sl_only
- [ ] Same-direction safety: never close originals on continuation
- [ ] SL-hit detection hardening and closed-reason persistence
- [ ] Reconciler + state sync updates for group lifecycle
- [ ] Tests for manager/reconciler/parser updates
- [x] Config/docs updates (`config.py` enhanced with new knobs)

## Execution steps
1. Add new config flags and validation
2. Extend domain/state models for signal grouping and entry roles
3. Implement zone-smart entry decision in manager
4. Implement proactive partial ladder + BE/trailing hooks
5. Implement re-entry resolver and continuation safety
6. Add closed-reason detection hooks in reconciler/state store
7. Update/extend tests
8. Run full pytest suite
9. Summarize runtime validation checklist for RDP-side final pass
