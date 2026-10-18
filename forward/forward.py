#!/usr/bin/env python3
"""OUT-OF-SAMPLE FORWARD TRACKER (local simulation; virtual money only).

Tracks 9 variants live-out-of-sample from FORWARD_START (2026-09-29), each
starting with 100,000 virtual. Both backtest labs (137 + 307 variants) found
nothing passing multiple-testing correction on 3y history, so promotion
decisions require forward evidence. This machine collects it.

Daily job, in order:
  (a) refresh data: seed from lab/data once, then refetch from Yahoo with the
      same UA/retry behavior as lab/data/fetch.py, merged append-mostly into
      forward/data/ (history before the trailing revision tail is frozen so
      the warm-up replay is stable run-to-run);
  (b) replay every variant over the FULL available history under the
      no-lookahead convention (signals from closes <= t-1, execution at the
      close of day t), using pre-forward history only as warm-up state;
  (c) RECORD equity / positions / trades for dates >= FORWARD_START only,
      and overwrite forward_state.json wholesale (idempotent per UTC day:
      same data in -> same state out; re-running never double-appends);
  (d) print one comparison JSON to stdout: per-variant return-to-date,
      current positions, trade count, exposure, plus a SPY buy-and-hold
      benchmark series over the same window.

Conventions (see NOTES.md for the full statement):
  - v1 variants (donchian / xs-momentum / ew12 baseline) replay under the
    v1 engine semantics copied from lab/backtest.py: daily mult =
    (1 + r_day) * (1 - cost), cost = 5bps * |target - drifted| one-way
    turnover charged on the trade day; weights drift between targets.
  - v2 variants (V228 meanrev_vol, V306 killswitch) replay under the
    lab2/engine.py semantics: mult = (1 + r - cost) with r = W2[t-1] . ret[t]
    and cost = 5bps * |target_t - W2[t-1]| (the accounting used inside
    lab2 apply_killswitch). V306 segments are [history .. FORWARD_START-1]
    and [FORWARD_START ..] with killswitch equity/peak reset at the forward
    boundary, mirroring lab2's per-split reset (state carries across the
    boundary only through the effective weight row).
  - V236G (variants 8) replays V236's meanrev_vol rows under the same v2
    accounting with the lab3/regime G1G2G3 entry-suppression gate wired as
    a boolean mask by date (exits/TP/stops always run); gate inputs
    (^VIX, HYG, LQD raw closes) are fetched range=max as extra symbols and
    evaluated weekly on the prior session's closes.
  - COMPOSITE_50 (variant 9) blends 50% V236G + 50% mom_n5_k5_abs_c21 as
    sub-accounts: sleeve-internal costs live inside each sleeve's engine
    multipliers; capital fractions drift daily and are rebalanced back to
    50/50 at the first session close of each ISO week, charging 5 bps/side
    on that rebalance turnover (blend_sim convention: r_net = r_g - cost).
  - Costs 5 bps per side, long-only, no leverage, close marks only.
  - Deterministic: state is a pure function of the CSVs in forward/data/.

Universe (v1/lab conventions): 12 tradeable names; SPY benchmark, QQQ held
out. Stocks only; no trading-platform API is ever called - the only network
use is the public Yahoo daily-OHLC endpoint for research data refresh.
"""

import csv
import json
import math
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
STATE_PATH = os.path.join(HERE, "forward_state.json")
SRC_DATA = "/workspace/ai4trade/lab/data"        # read-only seed source

UNIVERSE = ["NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "META",
            "GOOGL", "AMD", "JPM", "XOM", "LLY", "AVGO"]
BENCH = "SPY"
ALL_SYMS = sorted(UNIVERSE + [BENCH, "QQQ"])

# macro/gate inputs (forward9): not traded, not part of the alignment
# calendar; fetched once with deep history so the G1G2G3 gate state
# (lab3/regime conventions) is operative over the whole warm-up.
# NOTE: Yahoo's range=max silently degrades ^VIX/HYG/LQD to MONTHLY bars
# (same quirk lab3/regime/fetch_macro.py works around), so deep history is
# fetched with period1 near each symbol's listing instead — daily bars from
# the first possible session (the max-range daily equivalent).
GATE_SYMS = ["^VIX", "HYG", "LQD"]
FETCH_SYMS = sorted(ALL_SYMS + GATE_SYMS)
GATE_FETCH_START = {"^VIX": "1990-01-01", "HYG": "2007-01-01",
                    "LQD": "2002-05-01"}

FORWARD_START = "2026-09-29"
START_EQUITY = 100000.0
COST = 0.0005                 # 5 bps per side
EPS = 1e-12
SLEEVE = 1.0 / len(UNIVERSE)  # v1 fixed 1/12 slot
DONCHIAN_WINDOW = 63

# v2 killswitch overlay parameters (lab2 V306)
KS_TRIGGER = -0.10
KS_SESSIONS = 20

# fetch behavior (mirrors lab/data/fetch.py)
BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
RANGE = "3y"
INTERVAL = "1d"
ATTEMPTS = 2
RETRY_SLEEP = 2.0
SYMBOL_PAUSE = 0.5
REVISION_TAIL = 5            # most recent N existing bars a refetch may revise

VARIANT_SPECS = [
    {"id": "don_p10_s8", "family": "donchian", "source": "v1 lab",
     "description": "Donchian: buy within 10% of 63d high, -8% stop (v1 conventions)",
     "params": {"p": 10, "stop": 8, "window": DONCHIAN_WINDOW}},
    {"id": "mom_n5_k5_abs_c21", "family": "xs-momentum", "source": "v1 lab",
     "description": ("XS momentum: top-5 by 5d return, abs filter "
                     "(cash when n-day return <= 0), rebalance every 21d"),
     "params": {"n": 5, "k": 5, "abs_filter": True, "cadence": 21}},
    {"id": "mom_n21_k5_abs_c1", "family": "xs-momentum", "source": "v1 lab",
     "description": ("XS momentum: top-5 by 21d return, abs filter "
                     "(cash when n-day return <= 0), rebalance every 1d"),
     "params": {"n": 21, "k": 5, "abs_filter": True, "cadence": 1}},
    {"id": "base_ew12", "family": "baseline", "source": "v1 lab",
     "description": "Equal-weight buy-and-hold of the 12 non-benchmark names",
     "params": {"assets": "EW-12"}},
    {"id": "V228_meanrev_vol_n1_k2_y10_sel3", "family": "meanrev_vol",
     "source": "v2 lab2 (V228)",
     "description": ("Vol-scaled mean reversion: buy worst 1d performers when "
                     "1d return <= -2.0 * sigma20 (per-name 20d stdev of daily "
                     "returns), up to 3 names at 1/3 each; exit +10% TP / -5% "
                     "stop vs entry fill close"),
     "params": {"n": 1, "kvol": 2.0, "y": 10.0, "sel": 3, "z_exit": 5.0}},
    {"id": "V236_meanrev_vol_n3_k1p5_y10_sel3", "family": "meanrev_vol",
     "source": "v2 lab2 (V236) — pre-registered 2026-10-17: only variant passing "
              "White Reality Check p=0.009 + DSR 0.975 in the gauntlet; forward "
              "clock starts now (first ~3 weeks overlap its selection data — caveat recorded)",
     "description": ("Vol-scaled mean reversion (V236): worst 3d performers when "
                     "3d return <= -1.5 * sigma20, up to 3 names; +10% TP / -5% stop"),
     "params": {"n": 3, "kvol": 1.5, "y": 10.0, "sel": 3, "z_exit": 5.0}},
    {"id": "V306_killswitch_V228", "family": "killswitch_overlay",
     "source": "v2 lab2 (V306)",
     "description": ("V228 with killswitch: portfolio equity <= -10% from its "
                     "running peak (forward-window peak) -> flatten to cash for "
                     "20 sessions, then resume base weights and reset the peak"),
     "params": {"base": "V228", "trigger_pct": -10.0, "cash_sessions": 20}},
    {"id": "V236G_meanrev_vol_n3_k1p5_y10_sel3_G1G2G3", "family": "meanrev_vol_gated",
     "source": "lab3/regime (V236 + G1G2G3 stack) — pre-registered 2026-10-18 "
               "(forward9): V236 is the gauntlet's only multiple-testing survivor; "
               "the regime lab's G1G2G3 stack is its agreed risk overlay",
     "description": ("V236 (worst 3d performers when 3d return <= -1.5*sigma20, "
                     "up to 3 names, +10% TP / -5% stop) with entry-suppression "
                     "gates G1G2G3 wired as one boolean mask by date: G1 VIX "
                     ">p80(252d) latched until <p70; G2 HYG/LQD price ratio "
                     "< mean60-2*sd60; G3 SPY < 200d SMA — all evaluated weekly "
                     "on the PRIOR session's closes; suppressed days block NEW "
                     "entries only (exits/TP/stops always run)"),
     "params": {"n": 3, "kvol": 1.5, "y": 10.0, "sel": 3, "z_exit": 5.0,
                "gates": "G1G2G3 (lab3/regime study.py; boolean entry mask)"}},
    {"id": "COMPOSITE_50_V236G_mom5", "family": "composite_5050",
     "source": "lab3/adaptive (blend family) — pre-registered 2026-10-18 "
               "(forward9): static equal-weight blend of the two sleeves the "
               "25y evidence ranks highest (adaptive_report.json table1)",
     "description": ("Equal-weight composite: 50% V236G (gated V236, v2 "
                     "accounting) + 50% mom_n5_k5_abs_c21 (v1 accounting) as "
                     "drifting sub-accounts, rebalanced to 50/50 at the first "
                     "session close of each ISO week; 5 bps/side charged on "
                     "the weekly rebalance turnover (sleeve-internal costs "
                     "already inside each sleeve's multipliers)"),
     "params": {"sleeve_a": "V236G_meanrev_vol_n3_k1p5_y10_sel3_G1G2G3",
                "sleeve_b": "mom_n5_k5_abs_c21",
                "w_a": 0.5, "w_b": 0.5,
                "rebalance": "weekly (first session of ISO week, at close)",
                "rebalance_cost_bps_per_side": 5}},
]


# --------------------------------------------------------------------------
# Data layer
# --------------------------------------------------------------------------

def seed_data():
    """One-time copy of the lab CSVs so the tracker owns its own data dir
    (lab/data is read-only for this worker)."""
    if os.path.isdir(DATA_DIR) and any(f.endswith(".csv") for f in os.listdir(DATA_DIR)):
        return False
    os.makedirs(DATA_DIR, exist_ok=True)
    for sym in ALL_SYMS:
        src = os.path.join(SRC_DATA, sym + ".csv")
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(DATA_DIR, sym + ".csv"))
    return True


def fetch_symbol(sym):
    """List of row dicts from Yahoo's public chart endpoint, or raise."""
    q = urllib.parse.quote(sym)
    start = GATE_FETCH_START.get(sym)
    if start is not None:                 # deep-history daily fetch (gate inputs)
        p1 = int(datetime.strptime(start, "%Y-%m-%d")
                 .replace(tzinfo=timezone.utc).timestamp())
        p2 = int(time.time()) + 86400
        url = (BASE_URL.format(sym=q)
               + "?interval={}&period1={}&period2={}".format(INTERVAL, p1, p2))
    else:
        url = BASE_URL.format(sym=q) + \
            "?interval={}&range={}".format(INTERVAL, RANGE)
    last_err = None
    for attempt in range(1, ATTEMPTS + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            result = payload["chart"]["result"][0]
            stamps = result["timestamp"]
            quote = result["indicators"]["quote"][0]
            rows = []
            for i, ts in enumerate(stamps):
                close = quote["close"][i]
                if close is None:
                    continue
                o = quote["open"][i]
                h = quote["high"][i]
                l = quote["low"][i]
                v = quote["volume"][i]
                rows.append({
                    "date": datetime.fromtimestamp(
                        ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                    "open": o if o is not None else close,
                    "high": h if h is not None else close,
                    "low": l if l is not None else close,
                    "close": close,
                    "volume": int(v) if v is not None else 0,
                })
            rows.sort(key=lambda r: r["date"])
            return rows
        except Exception as exc:  # noqa: BLE001 - retry, then give up per symbol
            last_err = exc
            sys.stderr.write("[{}] fetch attempt {}/{} failed: {}\n".format(
                sym, attempt, ATTEMPTS, exc))
            if attempt < ATTEMPTS:
                time.sleep(RETRY_SLEEP)
    raise RuntimeError("fetch failed: {}".format(last_err))


def _read_csv(path):
    rows = []
    with open(path, newline="") as fh:
        for rec in csv.DictReader(fh):
            rows.append({"date": rec["date"],
                         "open": float(rec["open"]),
                         "high": float(rec["high"]),
                         "low": float(rec["low"]),
                         "close": float(rec["close"]),
                         "volume": int(rec["volume"])})
    return rows


def _write_csv(path, rows):
    tmp = path + ".tmp"
    with open(tmp, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "open", "high", "low", "close", "volume"])
        for r in rows:
            w.writerow([r["date"],
                        "{:.6f}".format(r["open"]),
                        "{:.6f}".format(r["high"]),
                        "{:.6f}".format(r["low"]),
                        "{:.6f}".format(r["close"]),
                        r["volume"]])
    os.replace(tmp, path)


def merge_symbol(sym, fetched):
    """Append-mostly merge: new dates append; only the trailing REVISION_TAIL
    existing bars may be revised by the fetch (handles late fixes and
    same-session partial bars); deeper history is frozen so warm-up replay
    stays stable run-to-run."""
    path = os.path.join(DATA_DIR, sym + ".csv")
    existing = _read_csv(path) if os.path.isfile(path) else []
    if not existing:
        _write_csv(path, fetched)
        return {"appended": len(fetched), "revised": 0}
    have = {r["date"]: r for r in existing}
    dates = [r["date"] for r in existing]
    tail = set(dates[-REVISION_TAIL:])
    appended = revised = 0
    for r in fetched:
        d = r["date"]
        if d not in have:
            have[d] = r
            appended += 1
        elif d in tail:
            have[d] = r
            revised += 1
    merged = sorted(have.values(), key=lambda r: r["date"])
    _write_csv(path, merged)
    return {"appended": appended, "revised": revised}


def refresh_data():
    """Seed if needed, then refetch all symbols. Returns manifest dict."""
    seeded = seed_data()
    manifest = {"fetched_at_utc": datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"), "seeded_from_lab": seeded, "symbols": {}}
    for sym in FETCH_SYMS:
        info = {"status": "ok", "rows": 0, "first_date": None, "last_date": None,
                "appended": 0, "revised": 0}
        try:
            rows = fetch_symbol(sym)
            if not rows:
                raise RuntimeError("no non-null rows parsed")
            mg = merge_symbol(sym, rows)
            info.update(mg)
            final = _read_csv(os.path.join(DATA_DIR, sym + ".csv"))
            info["rows"] = len(final)
            info["first_date"] = final[0]["date"]
            info["last_date"] = final[-1]["date"]
        except Exception as exc:  # noqa: BLE001 - keep existing file, mark stale
            info["status"] = "stale ({})".format(exc)
            if os.path.isfile(os.path.join(DATA_DIR, sym + ".csv")):
                final = _read_csv(os.path.join(DATA_DIR, sym + ".csv"))
                info["rows"] = len(final)
                info["first_date"] = final[0]["date"]
                info["last_date"] = final[-1]["date"]
            else:
                info["status"] = "MISSING ({})".format(exc)
        manifest["symbols"][sym] = info
        time.sleep(SYMBOL_PAUSE)
    missing = [s for s, i in manifest["symbols"].items()
               if i["status"].startswith("MISSING")]
    if missing:
        raise RuntimeError("no usable data for: {}".format(", ".join(missing)))

    # Trailing-bar completeness: if any symbol lacks the newest session bar that
    # the majority already have (Yahoo finalizes end-of-day bars unevenly, and
    # cookie storms cause partial fetches), wait and refetch just those symbols.
    # This makes delayed/early runs self-heal instead of leaving stale rows.
    for attempt in range(2):
        last_dates = {s: i.get("last_date") for s, i in manifest["symbols"].items()
                      if i.get("last_date")}
        if not last_dates:
            break
        from collections import Counter
        mode_date, mode_n = Counter(last_dates.values()).most_common(1)[0]
        laggards = [s for s, d in last_dates.items() if d < mode_date]
        stale = [s for s, i in manifest["symbols"].items()
                 if i["status"].startswith("stale")]
        retry_syms = sorted(set(laggards) | set(stale))
        if not retry_syms:
            break
        sys.stderr.write("retry {}/2: refetching {} lagging symbols (mode last_date={})\n"
                         .format(attempt + 1, len(retry_syms), mode_date))
        time.sleep(180 if attempt == 0 else 300)
        for sym in retry_syms:
            try:
                rows = fetch_symbol(sym)
                if not rows:
                    continue
                mg = merge_symbol(sym, rows)
                manifest["symbols"][sym].update(mg)
                final = _read_csv(os.path.join(DATA_DIR, sym + ".csv"))
                manifest["symbols"][sym].update(
                    {"status": "ok", "rows": len(final),
                     "first_date": final[0]["date"], "last_date": final[-1]["date"]})
            except Exception:
                pass
            time.sleep(SYMBOL_PAUSE)
    return manifest


def load_aligned():
    """Load all CSVs, align on the intersection calendar, return
    (dates, px, dropped) with px[sym] -> list of closes."""
    per = {}
    for sym in ALL_SYMS:
        rows = _read_csv(os.path.join(DATA_DIR, sym + ".csv"))
        per[sym] = {r["date"]: r["close"] for r in rows}
    common = set.intersection(*(set(m) for m in per.values()))
    dropped = {s: len(per[s]) - len(common) for s in ALL_SYMS}
    dates = sorted(common)
    if len(dates) < 300:
        raise RuntimeError("aligned history too short: {} rows".format(len(dates)))
    px = {s: [per[s][d] for d in dates] for s in ALL_SYMS}
    for s in ALL_SYMS:
        if min(px[s]) <= 0:
            raise RuntimeError("{} non-positive close".format(s))
    return dates, px, dropped


# --------------------------------------------------------------------------
# v1 strategies - semantics copied verbatim from lab/strategies.py
# --------------------------------------------------------------------------

class Fixed:
    """Buy-and-hold a fixed weight vector, trade once at the first execution
    close, then never again. Empty weights = 100% cash."""

    warmup = 0

    def __init__(self, px, weights):
        self.px = px
        self.w = dict(weights)
        self.done = not self.w

    def target(self, j):
        if self.done:
            return None
        self.done = True
        return dict(self.w)

    def on_fill(self, i, w):
        pass


class XSMomentum:
    """Rank the universe by n-day return through decision day j; hold the
    top-k equal-weighted. With absf=True, names with return <= 0 are excluded
    (their slots go to cash). Rebalances every `cad` decision days."""

    def __init__(self, px, n, k, absf, cad):
        self.px = px
        self.n = n
        self.k = k
        self.absf = absf
        self.cad = cad
        self.warmup = n
        self.hold = None

    def target(self, j):
        if (j - self.n) % self.cad != 0:
            return None
        px = self.px
        scored = []
        for s in UNIVERSE:
            p1 = px[s][j]
            p0 = px[s][j - self.n]
            scored.append((p1 / p0 - 1.0, s))
        scored.sort(key=lambda t: (-t[0], t[1]))
        if self.absf:
            scored = [t for t in scored if t[0] > 0.0]
        self.hold = {s: 1.0 / self.k for _r, s in scored[: self.k]}
        return dict(self.hold)

    def on_fill(self, i, w):
        pass


class Donchian:
    """Sleeve enters when close is within p% of the trailing 63-day closing
    high; exits on a close s% below the entry fill price. Re-entries allowed."""

    def __init__(self, px, p, stop):
        self.px = px
        self.p = p / 100.0
        self.stop = stop / 100.0
        self.warmup = DONCHIAN_WINDOW - 1
        self.state = {s: None for s in UNIVERSE}
        self.pending = set()
        self.active = None

    def target(self, j):
        px = self.px
        act = set()
        changed = False
        for s in UNIVERSE:
            price = px[s][j]
            entry = self.state[s]
            if entry is None:
                hh = max(px[s][j - DONCHIAN_WINDOW + 1: j + 1])
                if price >= hh * (1.0 - self.p):
                    self.pending.add(s)
                    act.add(s)
                    changed = True
            else:
                if price <= entry * (1.0 - self.stop):
                    self.state[s] = None
                    self.pending.discard(s)
                    changed = True
                else:
                    act.add(s)
        if not changed and self.active is not None:
            return None
        self.active = act
        return {s: SLEEVE for s in act}

    def on_fill(self, i, w):
        for s in list(self.pending):
            if w.get(s, 0.0) > 0.0:
                self.state[s] = self.px[s][i]
            self.pending.discard(s)


# --------------------------------------------------------------------------
# v1 engine - semantics copied from lab/backtest.py run_variant, extended
# with absolute-equity / trade / recording bookkeeping for the forward window.
# --------------------------------------------------------------------------

def run_v1(strat, px, dates, fi, label):
    """fi: first forward index (dates[fi] >= FORWARD_START) or None."""
    n = len(dates)
    drifted = {}
    first_exec = strat.warmup + 1
    eq_abs = None                     # set to START_EQUITY at the boundary
    series, trades = [], []
    mults = [1.0] * n                 # unrounded daily multipliers (checks)
    fwd_eq = [None] * n               # unrounded absolute equity, forward only
    for i in range(1, n):
        # 1) day-i P&L from holdings set at close i-1 (weights drifted)
        r_day = 0.0
        if drifted:
            dayr = {}
            for s, w in drifted.items():
                rs = px[s][i] / px[s][i - 1] - 1.0
                r_day += w * rs
                dayr[s] = rs
            denom = 1.0 + r_day
            if denom > 0:
                drifted = {s: w * (1.0 + dayr[s]) / denom for s, w in drifted.items()}
            else:
                drifted = {}
        # absolute-equity bookkeeping from the forward boundary on
        if fi is not None and i == fi:
            eq_abs = START_EQUITY
        eq_pre = eq_abs * (1.0 + r_day) if eq_abs is not None else None
        # 2) trade at close i towards target computed from data <= i-1
        cost = 0.0
        tgt = strat.target(i - 1) if i >= first_exec else None
        if tgt is not None:
            syms = sorted(set(tgt) | set(drifted))   # canonical order: state
            turn = 0.0               # must be a pure function of the CSVs
            for s in syms:
                tw, dw = tgt.get(s, 0.0), drifted.get(s, 0.0)
                turn += abs(tw - dw)
                if eq_pre is not None and abs(tw - dw) > EPS:
                    qty = abs(tw - dw) * eq_pre / px[s][i]
                    action, reason = _v1_reason(label, tw, dw)
                    trades.append({"date": dates[i], "action": action,
                                   "symbol": s, "qty": round(qty, 4),
                                   "reason": reason,
                                   "price": round(px[s][i], 4)})
            cost = turn * COST
            drifted = {s: w for s, w in tgt.items() if w > EPS}
            strat.on_fill(i, drifted)
        mult = (1.0 + r_day) * (1.0 - cost)
        mults[i] = mult
        if eq_abs is not None:
            eq_abs *= mult
            fwd_eq[i] = eq_abs
            series.append({"date": dates[i], "equity": round(eq_abs, 2),
                           "exposure": round(sum(drifted.values()), 6)})
    last_w = dict(drifted)
    return series, trades, last_w, (eq_abs if eq_abs is not None else START_EQUITY), mults, fwd_eq


def _v1_reason(label, tw, dw):
    if dw <= EPS and tw > EPS:
        action, shape = "buy", "entry"
    elif dw > EPS and tw <= EPS:
        action, shape = "sell", "exit"
    elif tw > dw:
        action, shape = "buy", "increase"
    else:
        action, shape = "sell", "decrease"
    if label == "donchian":
        reason = {"entry": "donchian_entry", "exit": "donchian_stop_exit",
                  "increase": "donchian_rebalance",
                  "decrease": "donchian_rebalance"}[shape]
    elif label == "xs-momentum":
        reason = {"entry": "momo_buy", "exit": "momo_sell",
                  "increase": "momo_rebalance",
                  "decrease": "momo_rebalance"}[shape]
    else:
        reason = {"entry": "initial_buy", "exit": "final_exit",
                  "increase": "rebalance", "decrease": "rebalance"}[shape]
    return action, reason


# --------------------------------------------------------------------------
# v2 meanrev_vol - stdlib port of lab2/families.py meanrev_vol/_meanrev_loop
# --------------------------------------------------------------------------

def _sd20(px, s, j):
    """Sample stdev (ddof=1) of the last 20 daily returns through index j
    (pandas rolling(20).std() semantics)."""
    rs = [px[s][k] / px[s][k - 1] - 1.0 for k in range(j - 19, j + 1)]
    mu = sum(rs) / len(rs)
    return (sum((r - mu) ** 2 for r in rs) / (len(rs) - 1)) ** 0.5


def meanrev_vol_rows(px, n, kk, y, sel, z_exit):
    """Target-weight rows W[t] (dict sym->weight) decided at close t using
    only info through t-1, exactly lab2 _meanrev_loop: exits on close t-1 vs
    entry fill price (+y% TP / -z% stop), then worst-first entries among
    names whose n-day return (through t-1) <= -kk * sigma20 * sqrt(n), up to
    sel names at 1/sel each; entry fill price = close of day t."""
    T = len(px[UNIVERSE[0]])
    rows = []
    reasons = {}
    held = {}
    min_j = max(n, 20)            # rr needs j-n>=0; sigma20 needs j>=20
    for t in range(T):
        if t >= 1:
            for s in list(held):
                p = px[s][t - 1]
                if (p >= held[s] * (1.0 + y / 100.0)
                        or p <= held[s] * (1.0 - z_exit / 100.0)):
                    reasons[(t, s)] = ("v228_tp_exit" if p >= held[s] * (1.0 + y / 100.0)
                                       else "v228_stop_exit")
                    del held[s]
        j = t - 1
        if j >= min_j:
            cands = []
            for s in UNIVERSE:
                if s in held:
                    continue
                rr = px[s][j] / px[s][j - n] - 1.0
                thr = -kk * _sd20(px, s, j) * math.sqrt(n)
                if rr <= thr:
                    cands.append((rr, UNIVERSE.index(s), s))
            cands.sort()
            for _rr, _idx, s in cands:
                if len(held) >= sel:
                    break
                held[s] = px[s][t]
                reasons[(t, s)] = "v228_entry"
        rows.append({s: 1.0 / sel for s in held})
    return rows, reasons


# --------------------------------------------------------------------------
# G1G2G3 entry-suppression gate — stdlib port of lab3/regime/study.py
# build_gate_tracks (weekly eval, prior-close info, VIX 80/70 hysteresis,
# credit 60d z-score, SPY 200d SMA), wired as ONE boolean entry mask.
# State-reconstruction conventions follow lab3/adaptive.build_state (the
# same indicators feed its STRESS latch); here all three gates suppress
# NEW entries (per the forward9 pre-registration) instead of halving.
# --------------------------------------------------------------------------

def _isoweek(dstr):
    y, m, d = map(int, dstr.split("-"))
    return datetime(y, m, d).date().isocalendar()[:2]


def _pctl(vals, q):
    """Linear-interpolation percentile (numpy percentile default)."""
    s = sorted(vals)
    n = len(s)
    if n == 1:
        return s[0]
    rank = (q / 100.0) * (n - 1)
    lo = int(math.floor(rank))
    hi = min(lo + 1, n - 1)
    frac = rank - lo
    return s[lo] + frac * (s[hi] - s[lo])


def _asof_series(dates, m):
    """dict date->float -> list aligned to dates (last obs <= d, else None)."""
    out = []
    last = None
    cur = None
    it = iter(sorted(m.items()))
    cur = next(it, None)
    for d in dates:
        while cur is not None and cur[0] <= d:
            last = cur[1]
            cur = next(it, None)
        out.append(last)
    return out


def build_gate_mask(dates, px):
    """Boolean per-session entry-suppression mask (G1 OR G2 OR G3).

    Gate state is evaluated at the FIRST session of each ISO week from
    indicator values through the PRIOR session close (no lookahead, same
    convention as the entry signals), then held through the week:
      G1: VIX close > p80 of the trailing 252 sessions (>=126 valid) closes
          entries; reopens when VIX < p70 (Schmitt hysteresis, lab3/regime).
      G2: HYG/LQD raw-price ratio < mean60 - 2*sd60 (sample sd, needs 60
          valid pairs; inoperative before enough credit history).
      G3: SPY close < its 200-session SMA.
    Inputs: ^VIX/HYG/LQD CSVs in forward/data (raw closes, like every
    tracker series) as-of aligned onto the trading calendar; SPY from px.
    """
    T = len(dates)

    def _closes(sym):
        path = os.path.join(DATA_DIR, sym + ".csv")
        rows = _read_csv(path) if os.path.isfile(path) else []
        return {r["date"]: r["close"] for r in rows}

    vix = _asof_series(dates, _closes("^VIX"))
    hyg = _asof_series(dates, _closes("HYG"))
    lqd = _asof_series(dates, _closes("LQD"))
    spy = px[BENCH]
    sma200 = [None] * T
    run = 0.0
    for i in range(T):
        run += spy[i]
        if i >= 200:
            run -= spy[i - 200]
        if i >= 199:
            sma200[i] = run / 200.0

    mask = [False] * T
    diag = {"evals": 0, "g1_close_events": 0, "g1_open_events": 0,
            "g2_stress_weeks": 0, "g3_below_weeks": 0,
            "credit_inoperative_weeks": 0, "suppressed_sessions": 0}
    state_open = True
    evals = [i for i in range(1, T)
             if _isoweek(dates[i]) != _isoweek(dates[i - 1])]
    bounds = evals + [T]
    for k in range(len(evals)):
        i_e, i_end = evals[k], bounds[k + 1]
        j = i_e - 1                        # decision info through prior close
        # G1: VIX vs trailing-252d percentile, hysteresis 80/70
        if j - 251 >= 0 and vix[j] is not None:
            win = [v for v in vix[j - 251: j + 1] if v is not None]
            if len(win) >= 126:            # half-window minimum (lab3/regime)
                p80 = _pctl(win, 80.0)
                p70 = _pctl(win, 70.0)
                if state_open and vix[j] > p80:
                    state_open = False
                    diag["g1_close_events"] += 1
                elif not state_open and vix[j] < p70:
                    state_open = True
                    diag["g1_open_events"] += 1
        # G2: HYG/LQD price ratio < mean60 - 2*sd60
        stress = False
        if hyg[j] is not None and lqd[j] is not None and lqd[j] > 0:
            rj = hyg[j] / lqd[j]
            w60 = []
            for i in range(max(0, j - 59), j + 1):
                if hyg[i] is not None and lqd[i] is not None and lqd[i] > 0:
                    w60.append(hyg[i] / lqd[i])
            if len(w60) >= 60:
                m60 = sum(w60) / len(w60)
                sd60 = (sum((x - m60) ** 2 for x in w60)
                        / (len(w60) - 1)) ** 0.5
                stress = rj < m60 - 2.0 * sd60
            else:
                diag["credit_inoperative_weeks"] += 1
        else:
            diag["credit_inoperative_weeks"] += 1
        # G3: SPY below its 200d SMA
        below = sma200[j] is not None and spy[j] < sma200[j]
        diag["evals"] += 1
        if stress:
            diag["g2_stress_weeks"] += 1
        if below:
            diag["g3_below_weeks"] += 1
        blocked = (not state_open) or stress or below
        for t in range(i_e, i_end):
            mask[t] = blocked
    diag["suppressed_sessions"] = sum(mask)
    return mask, diag


def meanrev_vol_rows_gated(px, n, kk, y, sel, z_exit, mask):
    """meanrev_vol_rows + boolean entry mask: on mask[t] days the entry scan
    is skipped entirely (exits/TP/stops still processed first). Held weights
    stay 1/sel; the mask blocks NEW entries only."""
    T = len(px[UNIVERSE[0]])
    rows = []
    reasons = {}
    held = {}
    min_j = max(n, 20)
    blocked_days = blocked_candidates = 0
    entries = exits = 0
    for t in range(T):
        if t >= 1:
            for s in list(held):
                p = px[s][t - 1]
                if (p >= held[s] * (1.0 + y / 100.0)
                        or p <= held[s] * (1.0 - z_exit / 100.0)):
                    reasons[(t, s)] = ("v228_tp_exit" if p >= held[s] * (1.0 + y / 100.0)
                                       else "v228_stop_exit")
                    del held[s]
                    exits += 1
        j = t - 1
        if j >= min_j:
            cands = []
            if mask[t]:
                for s in UNIVERSE:
                    if s in held:
                        continue
                    rr = px[s][j] / px[s][j - n] - 1.0
                    thr = -kk * _sd20(px, s, j) * math.sqrt(n)
                    if rr <= thr:
                        cands.append((rr, UNIVERSE.index(s), s))
                if cands:
                    blocked_days += 1
                    blocked_candidates += len(cands)
            else:
                for s in UNIVERSE:
                    if s in held:
                        continue
                    rr = px[s][j] / px[s][j - n] - 1.0
                    thr = -kk * _sd20(px, s, j) * math.sqrt(n)
                    if rr <= thr:
                        cands.append((rr, UNIVERSE.index(s), s))
                cands.sort()
                for _rr, _idx, s in cands:
                    if len(held) >= sel:
                        break
                    held[s] = px[s][t]
                    reasons[(t, s)] = "v228_entry"
                    entries += 1
        rows.append({s: 1.0 / sel for s in held})
    stats = {"entries": entries, "exits": exits,
             "blocked_entry_days": blocked_days,
             "blocked_candidates": blocked_candidates}
    return rows, reasons, stats


# --------------------------------------------------------------------------
# v2 engine + killswitch - stdlib port of lab2/engine.py backtest() and
# apply_killswitch() (same-day cost accounting, as inside apply_killswitch)
# --------------------------------------------------------------------------

def run_v2(rows, reasons, px, dates, fi, killswitch):
    """v2 accounting chain: mult[t] = 1 + r - COST*to with r = W2[t-1].ret and
    to = |target_t - W2[t-1]| (lab2/engine.py killswitch accounting; without
    the overlay target_t == base row, so to is the plain one-way turnover).
    Killswitch (V306): two segments [1..fi-1] (warm-up; equity discarded) and
    [fi..] (forward; eq/peak reset to 1.0 at the boundary, effective weight
    row carried across) - mirroring lab2's per-split state reset. Trigger-day
    turnover follows v2 exactly: the cost of trading to the base target is
    charged even though the overlay then flattens to cash."""
    T = len(dates)
    W2 = [dict(r) for r in rows]
    fires = {"warmup": 0, "forward": 0}
    flatten_days, resume_days = set(), set()
    if killswitch:
        segments = [("warmup", 1, (fi - 1) if fi is not None else T - 1)]
        if fi is not None:
            segments.append(("forward", fi, T - 1))
        for name, s0, s1 in segments:
            eq = peak = 1.0
            resume_at = None
            for t in range(s0, s1 + 1):
                if resume_at is not None and t >= resume_at:
                    peak, resume_at = eq, None
                    resume_days.add(t)
                target = dict(rows[t]) if resume_at is None else {}
                prev = W2[t - 1]
                r = sum(w * (px[s][t] / px[s][t - 1] - 1.0)
                        for s, w in prev.items())
                to = sum(abs(target.get(s, 0.0) - prev.get(s, 0.0))
                         for s in set(target) | set(prev))
                eq *= (1.0 + r - COST * to)
                if resume_at is None:
                    if eq > peak:
                        peak = eq
                    if eq <= peak * (1.0 + KS_TRIGGER):
                        fires[name] += 1
                        W2[t] = {}
                        flatten_days.add(t)
                        resume_at = t + KS_SESSIONS
                    else:
                        W2[t] = dict(rows[t])
                else:
                    W2[t] = {}

    # forward-window recording pass over the stored effective rows
    series, trades = [], []
    eq_abs = None
    mults = [1.0] * T
    fwd_eq = [None] * T
    for t in range(1, T):
        if fi is not None and t == fi:
            eq_abs = START_EQUITY
        if eq_abs is None:
            continue
        prev, cur = W2[t - 1], W2[t]
        r = sum(w * (px[s][t] / px[s][t - 1] - 1.0) for s, w in prev.items())
        if killswitch:
            target = ({} if (t in flatten_days
                             or any(f < t < f + KS_SESSIONS for f in flatten_days))
                      else dict(rows[t]))
            to = sum(abs(target.get(s, 0.0) - prev.get(s, 0.0))
                     for s in set(target) | set(prev))
        else:
            to = sum(abs(cur.get(s, 0.0) - prev.get(s, 0.0))
                     for s in set(cur) | set(prev))
        eq_pre = eq_abs * (1.0 + r)
        for s in sorted(set(cur) | set(prev)):   # canonical order (see run_v1)
            delta = cur.get(s, 0.0) - prev.get(s, 0.0)
            if abs(delta) <= EPS:
                continue
            qty = abs(delta) * eq_pre / px[s][t]
            action = "buy" if delta > 0 else "sell"
            reason = reasons.get((t, s))
            if reason is None:
                if t in flatten_days:
                    reason = "killswitch_flatten"
                elif t in resume_days:
                    reason = "killswitch_resume"
                else:
                    reason = "v228_rebalance"
            trades.append({"date": dates[t], "action": action, "symbol": s,
                           "qty": round(qty, 4), "reason": reason,
                           "price": round(px[s][t], 4)})
        eq_abs *= (1.0 + r - COST * to)
        mults[t] = 1.0 + r - COST * to
        fwd_eq[t] = eq_abs
        series.append({"date": dates[t], "equity": round(eq_abs, 2),
                       "exposure": round(sum(cur.values()), 6)})
    last_w = dict(W2[-1]) if W2 else {}
    return series, trades, last_w, (eq_abs if eq_abs is not None else START_EQUITY), fires, mults, fwd_eq


# --------------------------------------------------------------------------
# COMPOSITE blend (forward9): two drifting sub-accounts rebalanced to a
# fixed mix weekly. Sleeve-internal costs are already inside each sleeve's
# engine multipliers; the blend charges 5 bps/side only on its own weekly
# rebalance turnover (r_net = r_g - COST*turn, lab3/adaptive blend_sim
# convention). Rebalance = first session close of each ISO week.
# --------------------------------------------------------------------------

def run_composite(mults_a, mults_b, exp_a, exp_b, dates, fi, w_a=0.5):
    """Blend two sleeve daily-multiplier tracks from the forward boundary.

    mults_a/mults_b: per-session net daily multipliers (1.0 where idle);
    exp_a/exp_b: per-session sleeve gross exposures (sum of effective
    weights). Returns (series, trades, last_state) where last_state is
    (cA, cB, eq) at the final session; trades are the weekly rebalance
    rows (symbol = sleeve tag, qty = capital fraction moved on that side,
    price = 1.0 unit, notional/cost explicit).
    """
    T = len(dates)
    series, trades = [], []
    eq = None
    cA = cB = None
    for t in range(fi, T):
        if eq is None:                     # forward boundary: fresh 50k/50k
            eq = START_EQUITY
            cA = cB = w_a
        ra, rb = mults_a[t] - 1.0, mults_b[t] - 1.0
        r_g = cA * ra + cB * rb
        eq_pre = eq * (1.0 + r_g)
        den = 1.0 + r_g
        cA_d = cA * (1.0 + ra) / den if den > 0 else 0.0
        cB_d = (1.0 - cA_d) if den > 0 else 0.0
        turn = 0.0
        if t > fi and _isoweek(dates[t]) != _isoweek(dates[t - 1]):
            turn = abs(cA_d - w_a) + abs(cB_d - (1.0 - w_a))
            if turn > EPS:
                f = abs(cA_d - w_a)
                sell, buy = (("SLEEVE:V236G", "SLEEVE:MOM5") if cA_d > w_a
                             else ("SLEEVE:MOM5", "SLEEVE:V236G"))
                for sym, action in ((sell, "sell"), (buy, "buy")):
                    trades.append({"date": dates[t], "action": action,
                                   "symbol": sym, "qty": round(f, 6),
                                   "reason": "composite_weekly_rebalance",
                                   "price": 1.0,
                                   "notional": round(f * eq_pre, 2),
                                   "cost": round(COST * f * eq_pre, 2)})
            cA, cB = w_a, 1.0 - w_a
        else:
            cA, cB = cA_d, cB_d
        eq = eq_pre - COST * turn * eq_pre
        series.append({"date": dates[t], "equity": round(eq, 2),
                       "exposure": round(cA * exp_a[t] + cB * exp_b[t], 6)})
    return series, trades, (cA, cB, eq)


# --------------------------------------------------------------------------
# Recording / state assembly
# --------------------------------------------------------------------------

def positions_from_weights(w, eq_abs, px, dates, trades):
    pos = {}
    last_i = len(dates) - 1
    for s, wt in sorted(w.items()):
        if wt <= EPS:
            continue
        price = px[s][last_i]
        qty = wt * eq_abs / price
        entry_date, entry_price = None, None
        for tr in reversed(trades):
            if tr["symbol"] == s and tr["action"] == "buy":
                entry_date, entry_price = tr["date"], price
                break
        pos[s] = {"qty": round(qty, 4), "weight": round(wt, 6),
                  "last_price": round(price, 4),
                  "value": round(wt * eq_abs, 2),
                  "entry_date": entry_date}
    return pos


def anchor(exposure):
    return {"date": FORWARD_START, "equity": round(START_EQUITY, 2),
            "exposure": round(exposure, 6),
            "note": ("window-start anchor (virtual cash; no forward session "
                     "close recorded yet - first session close replaces this "
                     "row on the next run with data)")}


def build_state(dates, px, fetch_manifest, dropped):
    fi = next((i for i, d in enumerate(dates) if d >= FORWARD_START), None)
    last_date = dates[-1]

    # SPY buy-and-hold benchmark over the same window (ref = last close
    # strictly before the window, so the benchmark earns day-1 like variants)
    if fi is not None:
        ref = px[BENCH][fi - 1]
        spy_series = [{"date": dates[i],
                       "equity": round(START_EQUITY * px[BENCH][i] / ref, 2)}
                      for i in range(fi, len(dates))]
        spy_ret = spy_series[-1]["equity"] / START_EQUITY - 1.0
    else:
        spy_series = [anchor(1.0)]
        spy_ret = 0.0

    variants_state = {}
    gate_ctx = None
    for spec in VARIANT_SPECS:
        vid, fam = spec["id"], spec["family"]
        gate_info = None
        if fam == "donchian":
            strat = Donchian(px, spec["params"]["p"], spec["params"]["stop"])
            series, trades, last_w, eq, _m, _e = run_v1(strat, px, dates, fi, "donchian")
        elif fam == "xs-momentum":
            p = spec["params"]
            strat = XSMomentum(px, p["n"], p["k"], p["abs_filter"], p["cadence"])
            series, trades, last_w, eq, _m, _e = run_v1(strat, px, dates, fi, "xs-momentum")
        elif fam == "baseline":
            strat = Fixed(px, {s: SLEEVE for s in UNIVERSE})
            series, trades, last_w, eq, _m, _e = run_v1(strat, px, dates, fi, "baseline")
        elif fam == "meanrev_vol_gated":
            if gate_ctx is None:
                gate_ctx = build_gate_mask(dates, px)
            mask, gdiag = gate_ctx
            p = spec["params"]
            rows, reasons, gstats = meanrev_vol_rows_gated(
                px, p["n"], p["kvol"], p["y"], p["sel"], p["z_exit"], mask)
            series, trades, last_w, eq, _f, _m, _e = run_v2(
                rows, reasons, px, dates, fi, killswitch=False)
            gate_info = {"gate_diag": gdiag, "entry_stats": gstats}
        elif fam == "composite_5050":
            p = spec["params"]
            spec_a = next(s for s in VARIANT_SPECS if s["id"] == p["sleeve_a"])
            spec_b = next(s for s in VARIANT_SPECS if s["id"] == p["sleeve_b"])
            if gate_ctx is None:
                gate_ctx = build_gate_mask(dates, px)
            mask, gdiag = gate_ctx
            pa = spec_a["params"]
            rows_a, reasons_a, gstats_a = meanrev_vol_rows_gated(
                px, pa["n"], pa["kvol"], pa["y"], pa["sel"], pa["z_exit"], mask)
            _s, trades_a, _w, _e, _f, mults_a, _fe = run_v2(
                rows_a, reasons_a, px, dates, fi, killswitch=False)
            pb = spec_b["params"]
            strat_b = XSMomentum(px, pb["n"], pb["k"], pb["abs_filter"], pb["cadence"])
            _s, trades_b, last_w_b, _e, mults_b, _fe = run_v1(
                strat_b, px, dates, fi, "xs-momentum")
            # per-session sleeve exposures over the forward window
            T = len(dates)
            exp_a = [sum(rows_a[t].values()) for t in range(T)]
            exp_b = [None] * T
            wdrift = {}
            for t in range(1, T):
                r_day = 0.0
                dayr = {}
                for s, w in wdrift.items():
                    rs = px[s][t] / px[s][t - 1] - 1.0
                    r_day += w * rs
                    dayr[s] = rs
                denom = 1.0 + r_day
                if denom > 0:
                    wdrift = {s: w * (1.0 + dayr[s]) / denom
                              for s, w in wdrift.items()}
                else:
                    wdrift = {}
                tgt = strat_b.target(t - 1) if t >= strat_b.warmup + 1 else None
                if tgt is not None:
                    wdrift = {s: w for s, w in tgt.items() if w > EPS}
                exp_b[t] = sum(wdrift.values())
            exp_b[0] = 0.0
            series, trades, (cA, cB, eq) = run_composite(
                mults_a, mults_b, exp_a, exp_b, dates,
                fi if fi is not None else 0, p["w_a"])
            # symbol-level combined positions from the two sleeves
            last_w = {}
            for s in UNIVERSE:
                w = cA * rows_a[-1].get(s, 0.0) + cB * last_w_b.get(s, 0.0)
                if w > EPS:
                    last_w[s] = w
            gate_info = {"sleeve_gate_diag": gdiag,
                         "sleeve_entry_stats": gstats_a,
                         "sleeve_capital": {"V236G": round(cA, 6),
                                            "mom5": round(cB, 6)}}
        else:
            # v2 lab2 families: each meanrev spec uses its OWN params;
            # V306's base is V228 (its own params carry only the overlay).
            if fam == "killswitch_overlay":
                p = VARIANT_SPECS[4]["params"]
            else:
                p = spec["params"]
            rows, reasons = meanrev_vol_rows(px, p["n"], p["kvol"], p["y"],
                                             p["sel"], p["z_exit"])
            series, trades, last_w, eq, fires, _m, _e = run_v2(
                rows, reasons, px, dates, fi, killswitch=(fam == "killswitch_overlay"))
        if fi is None:
            series = [anchor(sum(last_w.values()))]
            trades = []
            eq = START_EQUITY
        pos_trades = trades if fam != "composite_5050" else trades_a + trades_b
        exposures = [row["exposure"] for row in series
                     if "note" not in row] or [sum(last_w.values())]
        variants_state[vid] = {
            "family": fam,
            "source": spec["source"],
            "description": spec["description"],
            "params": spec["params"],
            "as_of_date": last_date,
            "equity_series": series,
            "current_positions": positions_from_weights(
                last_w, eq, px, dates, pos_trades),
            "trades": trades,
            "trade_count": len(trades),
            "return_to_date": round(eq / START_EQUITY - 1.0, 6),
            "current_equity": round(eq, 2),
            "current_exposure": round(sum(last_w.values()), 6),
            "avg_exposure": round(sum(exposures) / len(exposures), 6),
        }
        if fam == "killswitch_overlay":
            variants_state[vid]["killswitch_fires"] = fires
        if gate_info is not None:
            variants_state[vid].update(gate_info)

    state = {
        "meta": {
            "tracker": "forward OOS tracker (local simulation, virtual money)",
            "generated_utc": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"),
            "engine": ("no-lookahead: signals from closes <= t-1, execution at "
                       "t close; v1 variants (1-4) under lab/backtest.py "
                       "accounting ((1+r)*(1-cost), drift between targets); "
                       "v2 variants (5-7) under lab2/engine.py killswitch "
                       "accounting ((1+r-cost)); V236G (8) = V236 rows + "
                       "lab3/regime G1G2G3 boolean entry mask (v2 accounting); "
                       "COMPOSITE_50 (9) = 50/50 V236G+mom5 drifting "
                       "sub-accounts, weekly 50/50 rebalance at 5 bps/side "
                       "(r_g - cost on rebalance turnover)"),
            "cost_bps_per_side": 5,
            "forward_start": FORWARD_START,
            "start_equity": START_EQUITY,
            "forward_window_days": 0 if fi is None else len(dates) - fi,
            "warmup_range": [dates[0], dates[-1] if fi is None else dates[fi - 1]],
            "last_data_date": last_date,
            "universe_traded": UNIVERSE,
            "benchmark": BENCH,
            "gate_inputs": {"symbols": GATE_SYMS,
                            "note": ("^VIX/HYG/LQD deep daily history via "
                                     "period1-near-listing (range=max "
                                     "degrades to monthly), raw closes, "
                                     "as-of aligned; drive the V236G/"
                                     "composite G1G2G3 entry mask (weekly "
                                     "eval on prior close)")},
            "idempotency": ("state is fully recomputed from forward/data CSVs "
                            "on every run and written atomically; re-running "
                            "on the same UTC day overwrites, never appends"),
            "data": {"fetch_manifest": fetch_manifest,
                     "dropped_misaligned_rows": dropped},
        },
        "benchmark": {BENCH: {"series": spy_series,
                              "return_to_date": round(spy_ret, 6)}},
        "variants": variants_state,
    }
    return state, fi


def comparison_json(state, fi):
    comp = {
        "generated_utc": state["meta"]["generated_utc"],
        "forward_start": FORWARD_START,
        "last_data_date": state["meta"]["last_data_date"],
        "forward_window_days": state["meta"]["forward_window_days"],
        "benchmark": {
            "SPY": {"return_to_date": state["benchmark"]["SPY"]["return_to_date"],
                    "series": state["benchmark"]["SPY"]["series"]},
        },
        "variants": {},
    }
    for vid, v in state["variants"].items():
        comp["variants"][vid] = {
            "return_to_date": v["return_to_date"],
            "current_positions": {s: p["weight"] for s, p in
                                  v["current_positions"].items()},
            "trade_count": v["trade_count"],
            "current_exposure": v["current_exposure"],
            "avg_exposure": v["avg_exposure"],
            "current_equity": v["current_equity"],
            "as_of_date": v["as_of_date"],
        }
        if "killswitch_fires" in v:
            comp["variants"][vid]["killswitch_fires"] = v["killswitch_fires"]
    return comp


def write_state(state):
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(state, fh, indent=1, sort_keys=True)
    os.replace(tmp, STATE_PATH)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def replay(dates, px, fetch_manifest, dropped):
    return build_state(dates, px, fetch_manifest, dropped)[0]


def main():
    fetch_manifest = refresh_data()
    dates, px, dropped = load_aligned()
    state, fi = build_state(dates, px, fetch_manifest, dropped)

    # determinism guard: a second replay from the same data must be identical
    state2 = replay(dates, px, fetch_manifest, dropped)
    strip = lambda s: {k: v for k, v in s.items() if k != "meta"}  # noqa: E731
    if json.dumps(strip(state), sort_keys=True) != json.dumps(strip(state2), sort_keys=True):
        raise RuntimeError("non-deterministic replay")

    write_state(state)
    print(json.dumps(comparison_json(state, fi), indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
