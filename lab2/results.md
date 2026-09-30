# lab2 sweep results

Generated 2026-09-29T04:48:32Z | 307 trials evaluated (registry incl. intermediates) | 305 kept variants | cost 5bps/side | long-only, no leverage

Splits: train 2023-09-29..2025-06-30 | validation 2025-07-01..2026-09-28. Signals use data through t-1; execution at t close.

## Top 25 by validation Sharpe

`DSR pass @95% (N=307)`: deflated Sharpe >= 0.95 with the true trial-count registry (expected-max-Sharpe correction on the validation/selection split).

| # | id | family | params | train SR | val SR | val CAGR | val maxDD | val win | avg exp | trades/yr | val turn/yr | DSR pass @95% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | V228 | meanrev-volscaled | n=1,kvol=2.0,y=10.0,sel=3 | 0.83 | 2.80 | 61.2% | -9.2% | 55% | 74% | 29.8 | 1932% | fail (0.86) |
| 2 | V306 | killswitch | base=V228,base_family=meanrev_vol,trigger_pct=-10.0,cash_sessions=20 | 0.57 | 2.80 | 61.2% | -9.2% | 55% | 74% | 29.8 | 1932% | fail (0.86) |
| 3 | V236 | meanrev-volscaled | n=3,kvol=1.5,y=10.0,sel=3 | 1.77 | 2.76 | 70.2% | -11.4% | 61% | 86% | 27.4 | 1852% | fail (0.84) |
| 4 | V211 | meanrev | n=5,x=2.5,y=10.0,sel=1 | 0.03 | 2.69 | 138.3% | -14.7% | 55% | 99% | 9.7 | 1932% | fail (0.81) |
| 5 | V226 | meanrev-volscaled | n=1,kvol=2.0,y=5.0,sel=3 | 0.87 | 2.64 | 51.1% | -6.4% | 54% | 66% | 39.5 | 2550% | fail (0.81) |
| 6 | V239 | meanrev-volscaled | n=3,kvol=2.0,y=10.0,sel=1 | 1.70 | 2.62 | 99.4% | -18.6% | 45% | 74% | 8.9 | 1852% | fail (0.75) |
| 7 | V041 | xsmom | n=10,k=1,abs=0,cad=daily | 0.69 | 2.61 | 223.9% | -30.7% | 56% | 100% | 73.3 | 14653% | fail (0.80) |
| 8 | V044 | xsmom | n=10,k=1,abs=1,cad=daily | 0.58 | 2.61 | 223.9% | -30.7% | 56% | 100% | 73.3 | 14653% | fail (0.80) |
| 9 | V234 | meanrev-volscaled | n=3,kvol=1.5,y=5.0,sel=3 | 1.36 | 2.36 | 57.3% | -13.2% | 61% | 81% | 39.5 | 2576% | fail (0.68) |
| 10 | V243 | meanrev-volscaled | n=3,kvol=2.5,y=10.0,sel=1 | -0.10 | 2.33 | 58.9% | -9.0% | 28% | 51% | 7.2 | 1449% | fail (0.69) |
| 11 | V233 | meanrev-volscaled | n=3,kvol=1.5,y=5.0,sel=1 | 0.48 | 2.25 | 80.1% | -15.2% | 50% | 89% | 14.5 | 2818% | fail (0.65) |
| 12 | V204 | meanrev | n=3,x=5.0,y=10.0,sel=3 | 0.68 | 2.20 | 58.1% | -16.2% | 55% | 90% | 33.8 | 2281% | fail (0.63) |
| 13 | V222 | meanrev-volscaled | n=1,kvol=1.5,y=5.0,sel=3 | 1.42 | 2.20 | 53.7% | -15.1% | 58% | 87% | 46.7 | 3086% | fail (0.62) |
| 14 | V246 | meanrev-volscaled | n=5,kvol=1.5,y=5.0,sel=3 | 0.87 | 2.20 | 46.0% | -9.5% | 57% | 68% | 36.2 | 2469% | fail (0.63) |
| 15 | V276 | donchian | len=126,p=2.0,s=5.0,norm=active | 0.94 | 2.18 | 47.4% | -10.2% | 56% | 100% | 10.5 | 394% | fail (0.62) |
| 16 | V210 | meanrev | n=5,x=2.5,y=5.0,sel=3 | 1.17 | 2.15 | 65.4% | -9.7% | 59% | 94% | 53.9 | 3596% | fail (0.60) |
| 17 | V216 | meanrev | n=5,x=5.0,y=10.0,sel=3 | 1.04 | 2.14 | 55.5% | -13.0% | 57% | 94% | 27.4 | 1825% | fail (0.60) |
| 18 | V278 | donchian | len=126,p=2.0,s=8.0,norm=active | 0.68 | 2.12 | 45.1% | -11.6% | 56% | 100% | 7.2 | 232% | fail (0.59) |
| 19 | V248 | meanrev-volscaled | n=5,kvol=1.5,y=10.0,sel=3 | 1.34 | 2.11 | 50.4% | -12.2% | 55% | 86% | 25.8 | 1744% | fail (0.59) |
| 20 | V202 | meanrev | n=3,x=5.0,y=5.0,sel=3 | 0.64 | 2.09 | 58.3% | -19.1% | 56% | 76% | 53.9 | 3650% | fail (0.58) |
| 21 | V269 | donchian | len=63,p=5.0,s=8.0,norm=fixed | 1.31 | 2.06 | 42.5% | -12.2% | 58% | 100% | 0.0 | 0% | fail (0.56) |
| 22 | V270 | donchian | len=63,p=5.0,s=8.0,norm=active | 1.32 | 2.06 | 42.5% | -12.2% | 58% | 100% | 0.0 | 0% | fail (0.56) |
| 23 | V273 | donchian | len=63,p=10.0,s=8.0,norm=fixed | 1.36 | 2.06 | 42.5% | -12.2% | 58% | 100% | 0.0 | 0% | fail (0.56) |
| 24 | V274 | donchian | len=63,p=10.0,s=8.0,norm=active | 1.32 | 2.06 | 42.5% | -12.2% | 58% | 100% | 0.0 | 0% | fail (0.56) |
| 25 | V265 | donchian | len=63,p=2.0,s=8.0,norm=fixed | 1.35 | 2.05 | 42.3% | -12.2% | 58% | 100% | 0.8 | 7% | fail (0.56) |

## Deflated Sharpe / multiple testing

- trials_evaluated N = 307 (every config actually evaluated, including the two two_sleeve intermediate diagnostics and both kill-switch overlays).
- expected-max Sharpe under N independent trials: SR0 = 1.92 (annualized; cross-trial SR variance 0.435).
- DSR survivors @95%: **0** of 305 kept variants; in the top-25 table above: 0.
- PBO (CSCV, 8 blocks, 70 combinations): 44% — mean OOS percentile of the train-best trial 0.55.
- Caveat: with ~311 validation days the Sharpe standard error is ~0.8; DSR pass is a necessary, not sufficient, condition.

## Sensitivity notes

| family | n | median val SR | max val SR | min val SR |
|---|---|---|---|---|
| baseline | 4 | 1.41 | 1.58 | 0.00 |
| donchian | 24 | 2.00 | 2.18 | 1.71 |
| dualmom | 6 | 0.91 | 1.63 | 0.13 |
| killswitch | 2 | 1.98 | 2.80 | 1.15 |
| meanrev | 36 | 1.11 | 2.69 | 0.02 |
| meanrev-volscaled | 36 | 1.55 | 2.80 | -0.00 |
| random-control | 10 | 1.23 | 1.86 | 0.41 |
| sma | 6 | 1.53 | 1.87 | 0.97 |
| two_sleeve | 1 | 1.15 | 1.15 | 1.15 |
| volmom | 72 | 0.63 | 1.75 | -0.44 |
| xsmom | 108 | 1.16 | 2.61 | -0.38 |

- xsmom cadence: median val SR daily 1.10 / weekly 1.46 / monthly 1.01; mean annual turnover 11486% / 4720% / 1460% (weekly cuts cost, keeps SR).
- xsmom absolute-momentum filter (daily cadence): median val SR off 1.10 vs on 1.02.
- xsmom lookback n (k=3, no abs, daily): 3d:0.72 5d:0.07 10d:1.11 21d:1.11 63d:1.77 126d:1.10.
- mean-reversion entry type (sel=1): fixed-% median val SR 0.85 vs vol-scaled 1.20.
- volmom SPY-vol regime gate: median val SR off 1.22 vs on 0.51.
- volmom vol window: 20d 0.61 vs 60d 0.68.
- random control (5 seeds x 2 cadences): val SR [0.41, 1.86] vs matched momentum (n=21,k=3) [1.11, 2.03].
- two_sleeve val annual turnover 2371% (target < 200%), avg exposure 45%.

## Benchmark block (survivorship honesty)

Universe = today's mega-cap winners -> absolute returns overstate skill.
Spreads vs SPY/QQQ on validation; `exposure-matched CAGR` = variant CAGR /
avg exposure (rf=0 approximation) vs benchmark buy-hold CAGR.

| variant | family | val CAGR | vs SPY | vs QQQ | val SR | SPY SR | QQQ SR | exp-match CAGR | SPY | QQQ |
|---|---|---|---|---|---|---|---|---|---|---|
| V228 | meanrev-volscaled | 61.2% | +42.3% | +34.9% | 2.80 | 1.47 | 1.35 | 82.1% | 18.8% | 26.2% |
| V306 | killswitch | 61.2% | +42.3% | +34.9% | 2.80 | 1.47 | 1.35 | 82.1% | 18.8% | 26.2% |
| V236 | meanrev-volscaled | 70.2% | +51.4% | +44.0% | 2.76 | 1.47 | 1.35 | 81.9% | 18.8% | 26.2% |
| V211 | meanrev | 138.3% | +119.4% | +112.1% | 2.69 | 1.47 | 1.35 | 139.2% | 18.8% | 26.2% |
| V226 | meanrev-volscaled | 51.1% | +32.3% | +24.9% | 2.64 | 1.47 | 1.35 | 77.7% | 18.8% | 26.2% |
| V239 | meanrev-volscaled | 99.4% | +80.6% | +73.2% | 2.62 | 1.47 | 1.35 | 133.6% | 18.8% | 26.2% |
| V041 | xsmom | 223.9% | +205.1% | +197.7% | 2.61 | 1.47 | 1.35 | 223.9% | 18.8% | 26.2% |
| V044 | xsmom | 223.9% | +205.1% | +197.7% | 2.61 | 1.47 | 1.35 | 223.9% | 18.8% | 26.2% |
| V234 | meanrev-volscaled | 57.3% | +38.5% | +31.1% | 2.36 | 1.47 | 1.35 | 70.9% | 18.8% | 26.2% |
| V243 | meanrev-volscaled | 58.9% | +40.0% | +32.7% | 2.33 | 1.47 | 1.35 | 115.2% | 18.8% | 26.2% |

SPY val CAGR 18.8%, QQQ val CAGR 26.2%.
