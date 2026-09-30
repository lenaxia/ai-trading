# METHODOLOGY — /workspace/ai4trade/lab

## Data

- 14 symbols (SPY, QQQ + 12 mega-cap stocks), daily OHLCV, 751 rows each,
  2023-09-29 .. 2026-09-28, identical trading calendars (asserted at load).
- Tradeable universe = the 12 stocks (NVDA AAPL MSFT TSLA AMZN META GOOGL AMD
  JPM XOM LLY AVGO). SPY is the benchmark; QQQ is a second benchmark held out
  of trading (both ETFs excluded from the stock cross-section).
- Source: local CSVs in `data/` via `data/load.py`. No network, no trading
  platform APIs, nothing outside the lab directory touched.

## No-lookahead rule (enforced)

- A signal for execution day `t` is computed by `strategy.target(t-1)` from
  closes with index <= t-1 (data through yesterday). The trade fills at the
  close of day t. Holdings established at close t earn day t+1's return.
- Structural test: corrupting all closes after day 700 leaves every return
  through day 700 bit-identical across all families (probe in repo history,
  11 representative variants). An independent re-derivation of the momentum
  ranking matched engine holdings on 40/40 sampled days.
- Determinism: the full grid is run twice per invocation and the serialized
  results must match byte-for-byte or the run aborts. Randomness exists only
  in the seeded random-control family (seeds 42-46).

## Execution & costs

- Daily close-to-close mark-to-market. Weight drift between trades is tracked,
  so turnover (and cost) is charged on the true difference between drifted and
  target weights: `turnover = sum_s |target_s - drifted_s|`, cost =
  5 basis points per side (0.05%) applied on the trade day.
- Positions: long-only, whole positions, equal weight within selected names,
  no leverage (gross <= 100%), no shorts, no derivatives.
- SMA/Donchian families run as 12 fixed 1/12 capital sleeves (each sleeve
  whole-position in its name or cash). Mean-reversion families hold one name
  at 100% of equity. Cross-sectional families equal-weight their picks.
- First possible execution is the close after each strategy's warmup
  (e.g. 126d lookback momentum first trades ~6 months in). Buy-and-hold
  baselines buy at the close of day 2 (index 1) — hence the ~1-5bps gap vs a
  raw day-0 price return.

## Splits

- TRAIN 2023-09-29 .. 2025-06-30 (~438 days, ~1.7y)
- VALIDATION 2025-07-01 .. 2026-09-28 (~313 days, ~1.2y) — the ranking split
- Strategies run continuously across the boundary; positions may carry over.
  Split metrics are computed from the daily-return series sliced by date;
  round trips are attributed to the split of their exit date.

## Metrics

- total return, CAGR (252 trading days/year), max drawdown (on the split's
  equity curve), Sharpe = mean/std(daily returns) * sqrt(252) (sample std),
  win rate (share of round trips closed at a profit, per exit date),
  avg exposure (mean daily gross weight), trades/year (entries per year).

## Variant grid (137 variants = true trial count)

- Baselines (3): SPY buy-hold; EW-12 buy-hold; 100% cash.
- Cross-sectional momentum (90): n in {5,10,21,63,126} x k in {1,3,5} x
  abs filter {off,on} x rebalance cadence in {1d,5d,21d}. The cadence axis
  extends the spec's grid so the total clears 100 materially different
  variants and prices the turnover/cost dimension explicitly.
- Mean reversion, fixed trigger (12): n in {1,5} x x in {2.5,5,10} x y in
  {5,10}, z = 5.
- Mean reversion, vol-scaled trigger (12, research steer): entry when n-day
  return <= -k * sigma20 * sqrt(n), k in {1.5,2,2.5}; exits as above.
- SMA crossover (3): (10,50), (20,100), (50,200) per-asset sleeves.
- Donchian breakout (6): p in {2,5,10} x stop in {5,8}, 63-day closing high.
- Dual momentum (4): k in {1,3} x cadence {5,21} (63d return, cash if <= 0).
- Vol-target momentum (1): top-3 by 21d return, weights ~ 1/sigma20,
  gross <= 100%, weekly.
- Two-sleeve combo (1, research steer): 50/50 vol-targeted momentum (top-3
  63d, 1/vol20, 15% name cap, flattened when SPY 20d vol ranks above the 80th
  percentile of its trailing 60 vol20 obs) + vol-gated 3-5d reversal (worst 3d
  performer while SPY vol rank <= 60d median with +/-1 percentile hysteresis;
  exit +4%/-5%/5 sessions). Weekly A cadence; B event-driven.
- Random controls (5): 3 random names weekly, seeds 42-46.

Interpretation conventions: "within p% of 63d high" uses the max of closes
over the trailing 63 days including the decision day; vol percentile ranks are
inclusive of the current observation; the DSR trial count includes every
distinct configuration evaluated (137; 0 discarded during development — no
config was backtested and then dropped from the grid).

## Statistical honesty

- 3y Sharpe standard error ~ +/-0.6 (MinTRL): rankings are screens.
- DSR (Bailey & Lopez de Prado 2014) computed per top-10 variant on
  validation daily returns with N = 137 trials and the cross-trial variance of
  daily Sharpes. As of the current run, no variant clears DSR >= 0.95.
- Benchmark spreads vs SPY and QQQ are exposure-matched: the benchmark is
  held only on the variant's daily gross-exposure fraction, rest cash.
- Random controls (mean val Sharpe 1.45, max 1.90) sit inside the top decile
  of the grid — a direct read on how much of the ranking is luck.

## Known biases and limitations (the honest list)

1. **Survivorship, by construction**: the universe was chosen today
   (2026-09) from mega-cap winners; backfilling 2023-2026 embeds hindsight.
   Absolute returns are inflated; only exposure-matched spreads vs SPY/QQQ
   are meaningful, and even those are suspect (the 12 names ARE the
   benchmark's recent winners).
2. **One regime**: the window is a single AI-led bull tape with shallow
   drawdowns. No bear-market data → trend/vol overlays are untested where
   they matter most.
3. **3y sample, 1.2y validation**: MinTRL logic says Sharpe error ~ +/-0.6;
   adjacent ranks are noise. DSR fails everything at 95%.
4. **Costs are optimistic**: 5 bps/side, no spread beyond that, no market
   impact, no borrow/financing, fills guaranteed at the close. Daily-rebalance
   variants (cadence=1) are the most cost-sensitive to this optimism.
5. **Close-execution assumption**: signals fire on t-1 data and fill at t's
   close auction; real slippage at that auction is not modeled.
6. **23/137 variants have validation metrics identical to another variant**
   (rel/abs momentum twins where the filter never bound; dual_k3_c5 is by
   construction identical to mom_n63_k3_abs_c5). Distinct configs, coincident
   outcomes in this window.
7. **No dividends/corporate actions**: price series only; total-return
   effects (buybacks, dividends) are ignored — modest tilt vs mega-cap
   benchmarks which include them.

## Forward picks protocol

Top 5 by validation Sharpe among variants passing: val Sharpe in top quartile
AND train Sharpe >= 0.7x val Sharpe AND val maxDD <= 25%. Random-control
family excluded (yardstick, not candidate). Current run: 4 of 5 slots filled;
the 5th is left empty rather than relaxing a gate. A forward shadow tracker
should consume `forward_variants.json` and judge on data after 2026-09-28
only.

## Reproduce

```
cd /workspace/ai4trade/lab && python3 backtest.py
```
Writes results.json, results.md, forward_variants.json (plus the in-run
determinism double-run check).
