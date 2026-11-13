# lab4 — Universe selection for V228 (mean-rev vol)

## Pre-registration (written 2026-11-13, before any variant run in this lab)

Trigger: owner asked for a wider universe ("match the other alpaca book"),
then asked whether universe selection should be rule-based ("stocks that
pass a DD") instead of relying on the lab-selected EW-12. This lab freezes
the candidate universes BEFORE running them, per the V236 pre-registration
convention. All variants share the EXACT V228 rules and accounting:

- rules: `forward/forward.py meanrev_vol_rows` — n=1, kvol=2.0, sel=3,
  TP +10% / stop -5% vs entry fill close, worst-first, 1/3 sizing
- accounting: v2 chain, 5 bps/side, weights decided at close t-1, fills at
  close t
- window: 2024-03-27 -> 2026-11-13 (662 sessions; lower bound set by GEV's
  2024 listing in the intersection calendar)
- splits: H1 = 2024-03-28..2025-07-24, H2 = 2025-07-25..2026-11-13,
  forward = 2026-09-29..end (overlaps the live fwd tracker)
- data: Yahoo daily closes, 5y fetch, intersection-aligned; BK excluded
  (fetch failed). Survivorship bias present in ALL universes (today's
  lists); EW-12 additionally carries in-sample universe selection.

### Frozen candidate universes

1. **EW-12** (incumbent): NVDA AAPL MSFT TSLA AMZN META GOOGL AMD JPM XOM
   LLY AVGO.
2. **WIDE-114**: the pilot watchlist (marketdata.universe(), universe.txt).
3. **MEGA100**: top 100 names of WIDE-114 by market cap at freeze time
   (mechanical, approximates index membership without cherry-picking).
4. **TRENDGATE**: WIDE-114 with a per-name entry gate — a name qualifies
   only if its close on the signal day (t-1) is above its own 200d SMA.
   Exits/TP/stops unchanged (gate suppresses entries only).
5. **DD-SCREEN**: WIDE-114 filtered by mechanical due-diligence screen,
   frozen as: trailing P/E > 0, market cap >= $10B, 3-month average volume
   >= 2M shares (Yahoo quote fields). If the fundamentals endpoint is
   unavailable at run time, this variant is reported as SKIPPED (no
   substitution, per the no-silent-fallback convention).

### Decision rule (frozen)

Preference order: (1) H2 Sharpe, (2) forward-window return, (3) full-window
maxDD. H2 is primary because it covers the regime the live book will trade
through next (post-correction chop), and because H1 rewards long-uptrend
universes mechanically. No variant may be promoted on full-window return
alone.

## Results (executed 2026-11-13, after freeze)

Full = 2024-03-27..2026-11-13 (662 sessions). [tot%, Sharpe, maxDD%]

| Universe | n | Full | H1 (→25-07) | H2 (25-07→) | Fwd (9/29→) | Expo | Entries |
|---|---|---|---|---|---|---|---|
| **EW12** (incumbent) | 12 | +171.2%, **2.87***, -21.2% | +33.3%, 0.94 | **+103.5%, 2.87**, -9.2% | **+17.7%, 4.13** | 0.71 | 87 |
| WIDE114 | 113 | +17.5%, 0.42, -28.9% | +24.2%, 1.01 | -5.4%, **-0.12**, -23.7% | +4.2%, 1.17 | 0.95 | 80 |
| TRENDGATE | 113 | +26.0%, 0.62, **-17.8%** | +11.7%, 0.68 | +12.7%, 0.59, -16.8% | +0.7%, 0.33 | 0.67 | 59 |
| MEGA100 | — | **SKIPPED** | | | | | |
| DD-SCREEN | — | **SKIPPED** | | | | | |

*EW-12 Sharpe remains flattered by in-sample universe selection and the AI
bull; the frozen decision rule nevertheless decides only among these runs.

**SKIPPED**: Yahoo's fundamentals endpoint (v7 quote: marketCap / trailingPE
/ ADV3M) returned HTTP 401 (crumb-gated) for all batches after retries.
Per the freeze, no substitution was made. Backlog: add a fundamentals
source (crumb auth, FMP/EOD key, or SEC companyfacts) to run MEGA100 and
DD-SCREEN as specified.

## Decision (frozen rule: H2 Sharpe → forward return → full maxDD)

1. H2 Sharpe: EW12 2.87 > TRENDGATE 0.59 > WIDE114 -0.12 → **EW12 wins**.
2. Forward return: EW12 +17.7% > WIDE114 +4.2% > TRENDGATE +0.7% (confirms).
3. Full maxDD: TRENDGATE best (-17.8%) — tertiary, does not overturn.

**Outcome**: live v228 retains the EW-12 universe (decide/execute 0.4.2;
the wide build 0.4.1 never reached the cluster, so the live book has always
been EW-12 — nothing to unwind). TRENDGATE is the best non-incumbent and
the natural next forward-tracker candidate (register as a tracker variant
if pursued). Mechanism, recorded for posterity: worst-first dip-buying
derives its edge from 2σ dips in *uptrending* quality names; widening the
candidate pool converts entries into falling knives in names with no drift
(ABT/CVS/T-type), which is why breadth degraded every risk metric.

