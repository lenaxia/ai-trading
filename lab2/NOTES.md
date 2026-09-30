# lab2 — v2 sweep framework notes

Worker: framework | Completed 2026-09-29 (UTC) | LOCAL backtesting only; no
trading-platform APIs touched at any point.

## Install / versions

- venv: `/workspace/ai4trade/lab2/.venv` (python 3.12.13, pip 26.2.1)
- Installed first attempt (no fallback needed): numpy 2.5.3, pandas 3.0.6,
  vectorbt 1.1.1, yfinance 1.7.0, quantstats 0.0.86 (scipy 1.18.1, numba
  0.67.0 pulled in transitively). Full freeze in `requirements.txt`.
- vectorbt 1.1.1 imports and runs cleanly against pandas 3.0.6 / numpy 2.5.3
  in this environment; used as a **verification layer** (`vbt_check.py`), not
  as the sweep engine. yfinance/quantstats were installed per spec but are
  unused (data comes from the lab CSVs; custom metric set).

## Engine notes

- Custom weight-matrix engine (`engine.py` + `families.py`): every variant
  produces a T×14 target-weight frame W; daily returns are
  `strat_ret[t+1] = Σ W[t]·ret[t+1] − 5bps·Σ|W[t]−W[t−1]|`.
- **No-lookahead discipline**: W decided at close t uses only information
  through close t−1 — every decision frame is `indicator.shift(1)`. Path-
  dependent loops (mean-reversion, Donchian, two_sleeve exits) check
  `close[t−1]` vs entry and execute at close t. Warmup days (NaN indicators)
  are honestly flat (cash), which slightly penalizes long lookbacks (126d)
  inside the train split.
- Determinism: the only stochastic family is random-control (numpy
  `default_rng`, seeds 42–46 fixed; picks drawn on the matched momentum
  variant's trade dates).
- Splits: train 2023-09-29..2025-06-30 (438 d), validation 2025-07-01..
  2026-09-28 (313 d). Metrics per split: total return, CAGR, max DD, daily
  Sharpe (√252, ddof=1), win rate (fraction of positive days over ALL split
  days incl. flat days), avg exposure (mean Σw), trades/yr (weight 0→>0
  transitions per name), annual one-way turnover %.
- Kill-switch overlay state (−10% → 20-session cash) resets at each split
  start because metrics are per split.
- Two-sleeve spec details: A freezes weights between weekly refreshes with a
  rank stay-band (top-3, stay while rank ≤ 5), per-name cap 15%, flatten when
  SPY vol20 > rolling-60d p80 (re-enter ≤ p79); B buys the single worst 3d
  performer only on a genuine decline (rr3 < 0) while SPY vol20 ≤ p60d median
  (enter ≤ p49, exit > p51), exits +4%/−5%/5 sessions, 5-session cooldown +
  10-session per-name lockout.
- **Turnover target miss, reported honestly**: the orchestrator steer set a
  < 200%/yr turnover target for two_sleeve. Measured: 2371%/yr (sleeve A
  alone 841%, sleeve B alone 1530%). A 3–5-session reversal sleeve at a 50%
  budget cannot run below ~200%/yr one-way turnover without disabling the
  signal: ~2 round trips/yr is not a functioning reversal strategy. All
  anti-churn devices above are in place; the residual is structural.
  results.json carries the number (`two_sleeve_turnover`).
- Trial registry (`trials_evaluated` = 307): every config actually evaluated —
  305 kept variants + 2 two_sleeve intermediate diagnostics (sleeve A-only /
  B-only, flagged `status: intermediate`, excluded from top-25). Kill-switch
  overlays count as trials. vbt_check verification runs are engine checks,
  not strategy trials, and are not counted.

## Deflated Sharpe / multiple testing

- `deflated_sharpe.py`: PSR (skew/kurtosis-corrected), expected-max Sharpe
  under N independent trials from the cross-trial SR variance, DSR = PSR at
  SR0, plus CSCV PBO (8 blocks, 70 combinations). N = the true registry count
  (307). DSR is evaluated on the **validation** split because that is where
  the top-25 selection happens (val doubles as the selection set — an
  inherent limitation of reporting "best by validation Sharpe").
- Result: **0 of 305 variants survive DSR @95%** (SR0 ≈ 1.92 annualized;
  best val SR 2.80 → DSR 0.86). PBO 44%. Read: after testing 307 configs on
  313 validation days, no variant's Sharpe is statistically distinguishable
  from the best of 307 random draws. Any promotion requires an economic
  prior + forward test, per the research notes' MinTRL math (3y SR standard
  error ≈ 0.6–0.8).

## Biases and caveats

- **Survivorship bias, by construction**: the 12 tradeable names are today's
  mega-cap winners (selected 2026). Absolute returns/CAGRs are inflated; only
  spreads vs SPY/QQQ at matched exposure (benchmark block in results.md) are
  even arguably meaningful, and even those are discounted. Corroborating
  tell: the random-control family (purely seeded 3-name picks) reaches val
  SR 1.86 / 57% CAGR — random selection inside a winners-only universe looks
  brilliant.
- **3-year window ≈ one regime**: 2023-09..2026-09 is essentially a single
  AI-led bull regime; momentum efficacy is regime-conditional, and no crash
  episode informs the mean-reversion or kill-switch numbers.
- **14 large caps only**: cross-sectional ranks over 12 names are noisy and
  concentrated (top-1 momentum ≈ NVDA-tilt risk); per-name caps in the
  two_sleeve mitigate but do not remove concentration.
- **Costs 5bps/side, flat**: no spread/slippage/impact modeling; fills at
  close assumed frictionless beyond the bps. High-turnover variants (xsmom
  daily k=1 at ~14,600%/yr) would degrade materially with realistic
  microstructure; weekly/monthly cadence rows quantify that sensitivity.
- **vectorbt-specific caveats** (why it is verification, not the engine):
  first-call numba JIT warmup makes timing unreliable on short runs (fine
  here since vectorbt is only used on 3 cases); from_signals default fill
  semantics and per-order fee rounding differ in the 4th decimal from
  weight-matrix accounting (measured ≤0.07% on total return, ≤0.002 SR);
  pandas 3.x copy-on-write means some older vectorbt recipes mutate
  read-only frames — vbt_check builds fresh frames instead.
- **Win-rate convention**: fraction of positive days over all split days
  (flat/cash days count as non-wins); a cash-heavy variant shows a deflated
  win rate by construction.
- **Lookahead audit**: `close[t−1]`-based exit checks vs entry fills;
  expanding/rolling windows only; vol-target scaling uses the sleeve's own
  past returns (≤ t−1). The one deliberate judgment call: EW-12 buy-hold
  drifts from the sample start (position is inherited into validation, as a
  real 2023 purchase would be).

## Cross-validation summary

- vs **vectorbt** (`vbt_check.md`): 3 representative variants, both splits —
  agreement ≤0.07% on total return, ≤0.002 on Sharpe.
- vs **lab v1** (`crosscheck.md`, 133 matched configs): every
  identical-convention comparison (daily-cadence cross-sectional momentum)
  agrees to <1% on returns and Sharpe — engine parity. Remaining DIFFs are
  traced to documented convention differences (v1 cadence = every-N-sessions
  vs lab2 calendar dates; v1 mean-reversion re-enters one close later than
  lab2; v1 vol-target momentum is unscaled; SMA 50/200 train-start warmup).

## File map

- `sweep.py` — orchestrator; writes results.json + results.md
- `families.py` / `engine.py` / `common.py` — strategy grid + backtest
- `deflated_sharpe.py` — PSR/DSR/expected-max + CSCV PBO (registry-driven)
- `crosscheck.py` / `crosscheck.md` — v1 comparison (rerunnable)
- `vbt_check.py` / `vbt_check.md` — vectorbt verification
- `results.json` (307-trial registry + all metrics), `results.md` (top-25,
  DSR column, sensitivity, benchmark block)
- `logs/` — pip install logs
