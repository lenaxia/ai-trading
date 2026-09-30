#!/usr/bin/env python3
"""Daily runner for the self-hosted ai-trading experiment — no platform, no LLM.

Pipeline per run:
  1) marketdata.py snapshot (subprocess, stdout JSON)
  2) trade.py decision (subprocess, stdout JSON — exits before entries; it
     never trades itself; cash/positions come from state/book.json)
  3) execute exits first, then two-layer-gated entries through broker.py:
       layer 1  DD gate — state/dd_verdicts.json dated today with verdict
                "veto" for the symbol -> skip the buy (DD_VETO). Missing or
                stale file = no vetoes (abstain never blocks).
       layer 2  headline screen on the entry's own headlines — skip on
                material political / regulatory / earnings risk, and on
                unavailable headlines (SKIP_BUY)
       max 2 executed trades per UTC day (book "trades_YYYYMMDD" counter)
  4) append state/log.txt (DAILY / TRADED / SKIP_BUY / DD_VETO lines,
     workspace log format) and save the book.

The GHA workflow commits the changed state files afterwards. The only
network use is the marketdata/news fetching inside the subprocesses.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state")
sys.path.insert(0, HERE)
import broker  # noqa: E402

MAX_TRADES_PER_DAY = 2

RISK_PAT = re.compile(
    r"(lawsuit|indict\w*|fraud|probe|investigat\w*|\bsec\b|\bdoj\b|sanction\w*|"
    r"recall\w*|bankrupt\w*|resign\w*|downgrade\w*|halted|guidance (?:cut|lower\w*)|"
    r"miss(?:es|ed)? (?:earnings|estimates|revenue)|layoff\w*|delist\w*|ceo exit)", re.I)


def log(tag, line):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(os.path.join(STATE, "log.txt"), "a") as fh:
        fh.write("%s %s %s\n" % (ts, tag, line))


def dd_vetoes(today):
    """Veto-only DD gate: {symbol: verdict-row} for TODAY's file only."""
    try:
        with open(os.path.join(STATE, "dd_verdicts.json")) as fh:
            v = json.load(fh)
    except Exception:
        return {}
    if v.get("date") != today:
        return {}
    return {r.get("symbol"): r for r in v.get("verdicts", []) if r.get("verdict") == "veto"}


def headline_risk(headlines):
    if not headlines or any(not h.strip() or h.startswith("_news_fetch_error") for h in headlines):
        return "headline screen unavailable"
    for h in headlines:
        if RISK_PAT.search(h):
            return "risk headline: %s" % h[:120]
    return None


def main():
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    os.makedirs(STATE, exist_ok=True)
    book = broker.load_book()
    tkey = "trades_" + today
    trades_today = int(book.get(tkey) or 0)

    snap = json.loads(subprocess.run(
        [sys.executable, os.path.join(HERE, "marketdata.py")],
        capture_output=True, text=True, timeout=240).stdout)
    prices = {s["sym"]: s.get("price") for s in snap.get("stocks", [])
              if isinstance(s, dict) and "error" not in s}
    log("DAILY", "data_snapshot %s" % ",".join(prices))

    decision = json.loads(subprocess.run(
        [sys.executable, os.path.join(HERE, "trade.py")],
        capture_output=True, text=True, timeout=300).stdout)
    if not decision.get("ok"):
        print(json.dumps({"ok": False, "error": "trade decision failed",
                          "detail": str(decision.get("error"))[:200]}))
        sys.exit(1)

    vetoes = dd_vetoes(today)
    executed = []

    def fill(action, sym, qty, note):
        px = prices.get(sym)
        if not px:
            log("SKIP_BUY" if action == "buy" else "SKIP_SELL",
                "%s no market price" % sym)
            return False
        try:
            broker.execute(book, action, sym, qty, px, note)
        except ValueError as e:
            log("SKIP_BUY" if action == "buy" else "SKIP_SELL", "%s %s" % (sym, e))
            return False
        log("TRADED", "%s %s x%s @%.2f %s" % (action, sym, qty, px, note))
        return True

    for e in decision.get("exits", []):
        if trades_today >= MAX_TRADES_PER_DAY:
            break
        if fill("sell", e["symbol"], e["quantity"], e["reason"]):
            executed.append(e["symbol"])
            trades_today += 1

    for ent in decision.get("entries", []):
        sym = ent.get("symbol")
        if trades_today >= MAX_TRADES_PER_DAY:
            log("SKIP_BUY", "%s max %d trades/day reached" % (sym, MAX_TRADES_PER_DAY))
            break
        if not decision.get("market_open"):
            log("SKIP_BUY", "%s market closed (execute only 13:30-20:00 UTC weekdays)" % sym)
            continue
        if sym in vetoes:
            log("DD_VETO", "%s %s" % (sym, (vetoes[sym].get("thesis_excerpt") or "")[:120]))
            continue
        risk = headline_risk(ent.get("headlines") or [])
        if risk:
            log("SKIP_BUY", "%s %s" % (sym, risk))
            continue
        if fill("buy", sym, ent.get("quantity", 0), ent.get("reason", "momentum entry")):
            executed.append(sym)
            trades_today += 1

    book[tkey] = trades_today
    book["last_daily_run"] = today
    broker.save_book(book)

    print(json.dumps({"ok": True, "date": today, "trades": executed,
                      "trades_today": trades_today,
                      "cash": book["cash"],
                      "equity": round(book["cash"] + broker.position_value(book, prices), 2),
                      "vetoes": sorted(vetoes)}, sort_keys=True))


if __name__ == "__main__":
    main()
