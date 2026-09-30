# Strategy Lab — Results

Generated 2026-09-29T04:43:30Z · 137 variants in grid · **true trial count = 137** (all configs evaluated, incl. 0 discarded during development)

Engine: daily close-to-close, signals from data through t-1, execution at t close, 5 bps/side. Splits: train 2023-09-29..2025-06-30, validation 2025-07-01..2026-09-28 (ranking split). Long-only, whole positions, no leverage, no shorts.

## Honest screen caveat (read before believing any number below)

- With 313 trading days (~1.2y) of validation and 751 days (~3.0y) total, the standard error of a 3y-sample Sharpe is roughly **+/-0.6** (MinTRL logic): treat rankings as **screens**, not proof. A variant one or two Sharpe ranks from another is statistically indistinguishable.
- **137 configurations were evaluated**; the best-of-N maximum is upward-biased. DSR verdicts below apply the Bailey–López de Prado deflation with N=137.
- The universe is today's mega-cap winners (survivorship by construction), so absolute returns overstate skill; check the benchmark-spread table.
- Material-difference audit: 23 of 137 variants produced validation metrics identical to another variant (mostly rel/abs momentum twins whose absolute filter never bound in this window). Distinct configs, coincident outcomes — another reason to read ranks as screens.

## Baselines

| baseline | train Sharpe | train CAGR | val Sharpe | val CAGR | val maxDD |
|---|---|---|---|---|---|
| base_ew12 | 1.42 | 41.7% | 1.59 | 38.1% | -15.5% |
| base_spy | 1.32 | 23.6% | 1.47 | 18.8% | -9.1% |
| base_cash | 0.00 | 0.0% | 0.00 | 0.0% | 0.0% |

## Top 20 by validation Sharpe

| # | id | family | val Sharpe | val CAGR | val maxDD | val total ret | train Sharpe | val win rate | val expo | val trades/yr |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | mom_n10_k1_rel_c1 | xs-momentum | 2.61 | 223.8% | -30.7% | 330.3% | 0.69 | 54.9% | 100.0% | 73.3 |
| 2 | mom_n10_k1_abs_c1 | xs-momentum | 2.61 | 223.8% | -30.7% | 330.3% | 0.58 | 54.9% | 100.0% | 73.3 |
| 3 | two_sleeve | two-sleeve-combo | 2.29 | 51.6% | -12.0% | 67.6% | 0.20 | 50.0% | 56.5% | 45.9 |
| 4 | don_p2_s5 | donchian | 1.97 | 41.1% | -11.6% | 53.3% | 1.22 | 0.0% | 96.8% | 2.4 |
| 5 | don_p5_s8 | donchian | 1.94 | 46.8% | -12.8% | 61.2% | 1.25 | - | 100.0% | 0.0 |
| 6 | don_p10_s8 | donchian | 1.94 | 47.6% | -12.9% | 62.2% | 1.39 | - | 100.0% | 0.0 |
| 7 | don_p5_s5 | donchian | 1.93 | 39.9% | -11.6% | 51.7% | 1.21 | 0.0% | 97.5% | 2.4 |
| 8 | don_p2_s8 | donchian | 1.93 | 45.4% | -12.6% | 59.2% | 1.24 | - | 99.9% | 0.8 |
| 9 | rand_k3_seed42 | random-control | 1.90 | 53.1% | -9.1% | 69.7% | 1.52 | 57.3% | 100.0% | 105.5 |
| 10 | don_p10_s5 | donchian | 1.89 | 39.4% | -12.1% | 51.0% | 1.24 | 0.0% | 97.7% | 1.6 |
| 11 | mom_n63_k3_rel_c5 | xs-momentum | 1.85 | 66.7% | -13.1% | 88.6% | 0.85 | 52.8% | 100.0% | 29.0 |
| 12 | mrev_n5_x2p5_y5_z5 | mean-reversion | 1.83 | 71.1% | -11.7% | 94.9% | -0.29 | 77.3% | 91.4% | 17.7 |
| 13 | mom_n5_k5_rel_c21 | xs-momentum | 1.82 | 50.4% | -17.9% | 66.0% | 1.27 | 58.7% | 100.0% | 37.0 |
| 14 | mom_n5_k5_abs_c21 | xs-momentum | 1.80 | 47.7% | -16.3% | 62.3% | 1.32 | 62.8% | 93.5% | 34.6 |
| 15 | mom_n63_k3_abs_c5 | xs-momentum | 1.79 | 63.7% | -13.1% | 84.4% | 0.69 | 52.9% | 97.3% | 27.4 |
| 16 | dual_k3_c5 | dual-momentum | 1.79 | 63.7% | -13.1% | 84.4% | 0.69 | 52.9% | 97.3% | 27.4 |
| 17 | mom_n63_k3_abs_c1 | xs-momentum | 1.78 | 62.5% | -14.2% | 82.8% | 0.62 | 44.6% | 97.0% | 59.6 |
| 18 | mom_n63_k3_rel_c1 | xs-momentum | 1.74 | 61.5% | -14.2% | 81.4% | 0.85 | 44.4% | 100.0% | 58.0 |
| 19 | rand_k3_seed43 | random-control | 1.72 | 47.2% | -12.6% | 61.7% | 1.34 | 61.6% | 100.0% | 117.5 |
| 20 | rand_k3_seed44 | random-control | 1.68 | 50.7% | -12.9% | 66.4% | 1.10 | 58.8% | 100.0% | 109.5 |

## DSR gate — top 10 vs the 137-trial selection pool

Deflated Sharpe > 0 at 95% confidence (DSR probability >= 0.95) after multiple-testing deflation:

- `mom_n10_k1_rel_c1` — val Sharpe 2.61, DSR = 0.91 -> fail
- `mom_n10_k1_abs_c1` — val Sharpe 2.61, DSR = 0.91 -> fail
- `two_sleeve` — val Sharpe 2.29, DSR = 0.82 -> fail
- `don_p2_s5` — val Sharpe 1.97, DSR = 0.69 -> fail
- `don_p5_s8` — val Sharpe 1.94, DSR = 0.68 -> fail
- `don_p10_s8` — val Sharpe 1.94, DSR = 0.68 -> fail
- `don_p5_s5` — val Sharpe 1.93, DSR = 0.67 -> fail
- `don_p2_s8` — val Sharpe 1.93, DSR = 0.67 -> fail
- `rand_k3_seed42` — val Sharpe 1.90, DSR = 0.66 -> fail
- `don_p10_s5` — val Sharpe 1.89, DSR = 0.66 -> fail

## Benchmark spreads — top 10 (validation, exposure-matched)

Spread = variant CAGR minus CAGR of the benchmark held *only on the variant's daily gross-exposure fraction* (rest in cash) — i.e., matched average market participation, which partially deflates the survivorship tilt of a today's-winners universe.

| # | id | val CAGR | avg expo | spread vs SPY (matched) | spread vs QQQ (matched) |
|---|---|---|---|---|---|
| 1 | mom_n10_k1_rel_c1 | 223.8% | 100.0% | 204.9% | 197.6% |
| 2 | mom_n10_k1_abs_c1 | 223.8% | 100.0% | 204.9% | 197.6% |
| 3 | two_sleeve | 51.6% | 56.5% | 43.9% | 40.4% |
| 4 | don_p2_s5 | 41.1% | 96.8% | 22.9% | 15.7% |
| 5 | don_p5_s8 | 46.8% | 100.0% | 28.0% | 20.6% |
| 6 | don_p10_s8 | 47.6% | 100.0% | 28.7% | 21.4% |
| 7 | don_p5_s5 | 39.9% | 97.5% | 21.4% | 13.7% |
| 8 | don_p2_s8 | 45.4% | 99.9% | 26.6% | 19.2% |
| 9 | rand_k3_seed42 | 53.1% | 100.0% | 34.2% | 26.9% |
| 10 | don_p10_s5 | 39.4% | 97.7% | 20.8% | 13.2% |

## One-factor sensitivity (mean validation Sharpe by parameter level)

- momentum lookback n: 5: 0.76, 10: 1.17, 21: 1.16, 63: 1.33, 126: 1.06
- momentum top-k: 1: 0.89, 3: 1.18, 5: 1.21
- momentum cadence (d): 1: 1.09, 5: 1.13, 21: 1.07
- momentum absolute filter: no filter: 1.11, abs filter: 1.08
- momentum abs-filter binding: rel/abs twins differ in 26/45 matched pairs (macro-level means nearly identical); binding shows up in short lookbacks and k>1, and not at all for top-1 in this bull window
- mean-reversion fixed -x% trigger: 2.5: 0.84, 5.0: 0.74, 10.0: 0.57
- mean-reversion take-profit +y%: 5.0: 0.70, 10.0: 0.73
- mean-reversion lookback n: 1: 0.56, 5: 0.87
- vol-scaled reversion k: k=1.5: 0.73, k=2.0: 0.52, k=2.5: 0.39
- donchian proximity p%: 2: 1.95, 5: 1.94, 10: 1.91
- donchian stop s%: 5: 1.93, 8: 1.94
- sma pairs: 10/50: 1.11, 20/100: 1.67, 50/200: 1.59
- random control (5 seeds): mean val Sharpe 1.45 (spread 0.81..1.90) — the 'did the screen find noise' bar

## Forward picks (robustness-screened)

Rule: val Sharpe in top quartile AND train Sharpe >= 0.7x val Sharpe AND val maxDD <= 25%; top 5 by val Sharpe. Random-control family excluded (noise yardstick, not a candidate). Details in `forward_variants.json`.

**Only 4 of 5 slots filled** — no other variant passed all three gates; the 5th slot is left empty rather than relaxing the rule.

- `don_p10_s8` — val Sharpe 1.94 (train 1.39), val CAGR 47.6%, val maxDD -12.9%
- `mom_n5_k5_abs_c21` — val Sharpe 1.80 (train 1.32), val CAGR 47.7%, val maxDD -16.3%
- `base_ew12` — val Sharpe 1.59 (train 1.42), val CAGR 38.1%, val maxDD -15.5%
- `mom_n21_k5_abs_c1` — val Sharpe 1.54 (train 1.30), val CAGR 37.6%, val maxDD -13.9%

## Files

- `results.json` — every variant, both splits, machine-readable
- `forward_variants.json` — exact params of the robust picks
- `METHODOLOGY.md` — assumptions, costs, splits, biases
