from parser.signal_parser import parse_message

msgs = [
    ("1", """🔔 NEW SIGNAL: GOLD/XAUUSD

🔹 BUY: 4322 - 4324
🔴 SL: 4317
✔️ TP1: 4331
✔️ TP2: 4345"""),
    ("2", """GOLD - 60+ pips profit running ✔️
Take some profits"""),
    ("3", """GOLD - TP1 hit !
Over 75 pips profit running ✔️
Move SL to 4330 ✔️"""),
    ("4", """Close GOLD BUY 4324
GOLD SELL NOW
Scalp Setup
4322-4325 If the market is unable to break this range, we might see 4310"""),
    ("5", """For GOLD re-entry:
4326.5–4328.5 with SL at 4322."""),
    ("6", """🔔 NEW SIGNAL: GOLD/XAUUSD

🔷 SELL: 4325 - 4327
🔴 SL: 4331.5
✔️ TP1: 4317
✔️ TP2: 4305"""),
    ("7", """Stop loss hit ! ❌
-45 pips!"""),
]

for mid, text in msgs:
    s = parse_message("testchat", int(mid), text)
    print(
        mid,
        s.action_type,
        s.side,
        s.order_type,
        s.entry_low,
        s.entry_high,
        s.sl,
        s.tp1,
        s.tp2,
        s.move_sl_to,
        s.close_percent,
    )
