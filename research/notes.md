# Literature Scan — US Large-Cap Daily Trading Lab
Worker: research | Scan date: 2026-09-29 (UTC) | Window: 2024–2026, prefer <=18mo
Method: webfetch via DuckDuckGo HTML + arXiv/SSRN landing pages. arXiv API returned persistent HTTP 429 — dropped after 3 attempts; paper metadata gathered via search instead. No trading-platform APIs touched.
Lab context assumed: 12 mega-caps + SPY/QQQ, daily rebalance, 3y history, long-only, no leverage.

Legend — CONFIDENCE: high = peer-reviewed / major institution + concrete evidence; med = serious practitioner or preprint with methodology; low = promotional / thin evidence.

---

## (a) Equity momentum / factor efficacy in the current regime

1. CLAIM: The momentum factor has had a "continued very strong run" through 2025–2026, but the winner cohort keeps rotating (hyperscalers in 2024 → memory-chip makers YTD 2026), so momentum profits now concentrate in AI-adjacent names.
   SOURCE: J.P. Morgan AM "Factor Views 3Q 2026" — https://am.jpmorgan.com/us/en/asset-management/adv/insights/portfolio-insights/asset-class-views/factor/ | 2026-08-07 | CONFIDENCE: high
   IMPLICATION: Our 12-mega-cap momentum ranks will be dominated by AI-complex beta, not idiosyncratic momentum. Benchmark any momentum sleeve against SPY/QQQ buy-and-hold before crediting the signal; cap per-name weight so "momentum" ≠ "NVDA-tilt".

2. CLAIM: Momentum led Q4-2024 factor returns as yields and inflation expectations rose, i.e., momentum worked *in* the higher-rate regime, while size/value lagged.
   SOURCE: LSEG/FTSE Russell "Equity Factor Insights Q4 2024" — https://www.lseg.com/content/dam/ftse-russell/en_us/documents/market-insights/equity-factor/equity-factor-insights-q4-2024.pdf | 2025-01 | CONFIDENCE: high
   IMPLICATION: Don't handicraft the backtest start-date: our 3y window (2023–2026) is essentially one momentum-friendly regime. Treat in-sample momentum efficacy as regime-conditional, not structural.

3. CLAIM: Momentum underperformance episodes line up with volatility spikes, and long/short momentum suffers far more than long-only in those episodes.
   SOURCE: Alpha Architect (via IBKR Quant) "Why Momentum Investing Has Been Struggling — And What Volatility Has to Do With It" — https://www.interactivebrokers.com/campus/ibkr-quant-news/why-momentum-investing-has-been-struggling-and-what-volatility-has-to-do-with-it/ | 2026-05-27 | CONFIDENCE: med-high
   IMPLICATION: Add a realized-vol regime gate (e.g., 20d vol percentile) that de-risks or flattens the momentum sleeve in high-vol states; long-only constraint already softens this but a vol overlay is cheap insurance.

4. CLAIM: Risk-managed momentum (vol-scaling, dynamic position sizing) mitigates momentum crash risk and improves risk-efficiency of the factor.
   SOURCE: Alpha Architect "Momentum factor investing has its weak spots!" — https://alphaarchitect.com/momentum-factor-investing/ | 2025-11-24 | CONFIDENCE: med-high
   IMPLICATION: Implement momentum as vol-targeted (e.g., target 15–20% annualized sleeve vol, scale by inverse realized vol) rather than fixed weights — directly translatable parameter.

5. CLAIM: Momentum has paid a 7–8%/yr premium in US equities since 1927 but is crash-prone exactly at regime changes (rate turns, bubbles bursting).
   SOURCE: Quant Decoded factor explainer citing AQR/KCMI — https://quantdecoded.com/en/the-momentum-factor-why-winners-keep-winning | 2026-01-23 | CONFIDENCE: med (secondary source, but consistent with canon)
   IMPLICATION: With only 3y of data we cannot estimate momentum crash exposure. Hard-code a structural guardrail instead: max sleeve drawdown kill-switch (e.g., −15% → flatten to SPY).

---

## (b) Short-horizon mean reversion in liquid large caps — still alive?

6. CLAIM: Short-term (days-scale) mean reversion in US large caps remains statistically robust post-2024, with high win rates and favorable risk/reward in range-bound conditions.
   SOURCE: Weekly Catalysts (Substack) "Quantitative Analysis: Mean Reversion in U.S. Large Caps" — https://weeklycatalysts.substack.com/p/quantitative-analysis-mean-reversion | 2025-09-11 | CONFIDENCE: med (methodology shown, independent author)
   IMPLICATION: A 3–5 day reversal sleeve (buy 12-name-universe laggards vs SPY) is a viable second strategy family; validate its decay half-life on our own data before sizing.

7. CLAIM: Cross-sectional short-term reversal has a real *gross* edge but it is "eaten alive by turnover costs" at daily rebalance frequency.
   SOURCE: Quant Memo, build guide for 5-day cross-sectional reversal — https://quantmemo.com/guides/build-mean-reversion | 2025–2026 (undated page) | CONFIDENCE: med-high
   IMPLICATION: For our lab: model 2–5 bps/side costs minimum, add a trade-only-if-signal-exceeds-threshold band (hysteresis) to cut turnover, and report net-of-cost Sharpe only. Daily *rebalance-eligible* ≠ daily *trading*.

8. CLAIM: Practitioner live systems (live since 2024) exploit short-term reversion via option-implied-vol-conditioned dip buying rather than raw price z-scores — timing the dip with IV improves entries.
   SOURCE: Cracking Markets "Deep Dip" — https://www.crackingmarkets.com/deep-dip-innovative-short-term-mean-reversion/ | 2025-04-08 | CONFIDENCE: med (live-tracked, but single author)
   IMPLICATION: Enhance reversal entries with a condition like "down-move > k·realized-vol σ" instead of fixed % pullback; parameter k is a clean, testable knob.

9. CLAIM: A 2000–2026 contrarian/mean-reversion backtest on S&P 500 names shows reversion works as a *hedge sleeve* in bear markets and as a side-strategy, not a standalone alpha engine.
   SOURCE: RavenQuant contrarian study — https://ravenquant.com/sp-500-contrarian-strategy/ | 2026-07-28 | CONFIDENCE: low-med
   IMPLICATION: Size reversal as a diversifier vs the momentum sleeve (they are naturally negatively correlated signal-wise), not as the core.

---

## (c) ML/RL for daily equity trading — replicates vs hype

10. CLAIM: The FinRL community itself identifies non-stationarity, low signal-to-noise, and market frictions as the reasons RL trading results fail to transfer; contests 2023–2025 were designed specifically around these failure modes.
    SOURCE: "FinRL Contests: Benchmarking Data-driven Financial Reinforcement Learning" arXiv:2504.02281 — https://arxiv.org/pdf/2504.02281v3 | 2025-04 | CONFIDENCE: high
    IMPLICATION: Do not spend lab time training PPO/DQN on 756 daily observations — the SNR math is hopeless. If ML at all, use it for regime classification (low variance target), not return prediction.

11. CLAIM: The three canonical failure sources for financial RL benchmarks are low SNR, survivorship bias of historical data, and backtest overfitting — i.e., headline RL results are upper bounds.
    SOURCE: FinRL-Meta (OpenReview/Columbia OpenFIN) — https://openreview.net/pdf?id=LkAFwrqdRY6 | 2022 (context; re-affirmed in 2025 contest paper) | CONFIDENCE: high
    IMPLICATION: Our 12 mega-cap universe is *survivorship-biased by construction* (today's winners). Never interpret absolute returns as skill; only vs SPY/QQQ relative, and even then discount.

12. CLAIM: Most deep-RL trading models "fail precipitously in live markets", driven by extreme sensitivity to random initialization seeds, overfitting to historical anomalies, and unrealistic transaction costs.
    SOURCE: Mental Momentum Research, evaluation of DRL for trading — https://research.mental-momentum.ai/r/evaluation-deep-reinforcement-learning-y8je8b | 2026-06-14 | CONFIDENCE: med
    IMPLICATION: Any stochastic component in our lab must be seed-averaged (report mean±std over >=10 seeds) and results shown net of costs before promotion.

13. CLAIM: A 2023–2026 survey of 34 LLM+RL financial studies finds the literature fragmented, with no systematic comparison — i.e., no replicated evidence of durable RL/LLM alpha at daily horizon.
    SOURCE: Springer survey, LLM-enhanced RL in financial markets — https://link.springer.com/article/10.1007/s44163-026-02018-0 | 2026-08-28 | CONFIDENCE: high
    IMPLICATION: Deprioritize end-to-end learned policies; the evidence base supports rules + light ML overlays. What replicates: simple factors + risk overlays. What doesn't: end-to-end RL/LLM alpha.

---

## (d) LLM-agents in trading/markets — papers, benchmarks, failure modes

14. CLAIM: FinMem (layered-memory LLM agent, ICLR/AAAI-SS'24) reports leading trading performance vs baselines — but on single-name, cherry-picked windows with no cost/regime controls (the template the later critique papers attacked).
    SOURCE: arXiv:2311.13743 — https://arxiv.org/abs/2311.13743 | 2023-11 (v2 2023-12; AAAI-SS 2024) | CONFIDENCE: high that it claims this; low that it generalizes
    IMPLICATION: Treat all "LLM-agent beats market" results as unvalidated until leakage-controlled (see 16–18).

15. CLAIM: In a realistic simulated market (order book, partial fills, dividends), LLM agents execute strategies and produce realistic market dynamics but "adhere to instructions rather than optimizing profit" — they are good *simulacra* of trader behavior, not profit-seeking edge.
    SOURCE: Lopez-Lira et al., "Can Large Language Models Trade?" arXiv:2504.10789 / SSRN 5217340 — https://arxiv.org/abs/2504.10789 | 2025-04 | CONFIDENCE: high
    IMPLICATION: Use LLMs in our lab for *analysis/simulation* (scenario narratives, parameter sanity-checks), never as the return-generating decision core.

16. CLAIM: Most LLM-agent backtest profits are a "profit mirage" — dazzling backtested returns driven by information leakage into prompts/memory (news embeddings, future index levels) rather than skill.
    SOURCE: "Profit Mirage: Revisiting Information Leakage in LLM-based Financial Agents" — https://www.researchgate.net/publication/396373592_Profit_Mirage_Revisiting_Information_Leakage_in_LLM-based_Financial_Agents | 2025-10-09 | CONFIDENCE: high (systematic study)
    IMPLICATION: If we ever prompt an LLM with market context, feed only point-in-time, precomputed numeric features — never raw text/news whose timestamps we can't verify — and hold out a post-training-cutoff window as the only trusted test.

17. CLAIM: Look-Ahead-Bench (built on the 45k-star "AI Hedge Fund" agent repo) is a standardized benchmark measuring look-ahead bias in agentic LLM trading end-to-end; leakage materially inflates reported returns.
    SOURCE: arXiv:2601.13770 + code https://github.com/benstaf/lookaheadbench | 2026-01-20 | CONFIDENCE: high
    IMPLICATION: Adopt their pattern: evaluate any agent on a "memory-controlled" variant (agent cannot recall post-decision data). For us: strict as-of joins in the feature builder, asserted in code.

18. CLAIM: A statistical "Lookahead Propensity" test (detecting whether an LLM memorized the outcome via its training corpus) shows materially positive lookahead contamination in-sample that collapses out-of-sample — LLM forecasts can be contaminated even when the prompt looks clean.
    SOURCE: "Detecting Lookahead Bias in LLM Forecasts" (NBER working paper) arXiv:2512.23847 — https://arxiv.org/abs/2512.23847 | 2025-12-29 | CONFIDENCE: high
    IMPLICATION: Any LLM-assisted signal must be evaluated only on dates after the model's knowledge cutoff (for us: 2025–2026 live/paper window), never on 2023–2024 history the model memorized.

---

## (e) Ensemble & regime-switching strategy design

19. CLAIM: A 3-state Gaussian HMM on daily ETF data (2004–2025) combined with regime-conditional allocation (equities/bonds/gold) improves risk-adjusted returns vs static allocation; the regime detector itself is the alpha, the allocator is simple.
    SOURCE: "Regime-Based Portfolio Allocation Using HMMs" SSRN 5785443 / arXiv:2605.27848 — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5785443 | 2025-12-24 | CONFIDENCE: med-high
    IMPLICATION: Build a 2–3 state HMM (or simpler: vol percentile + trend sign) on SPY/QQQ as the top-level switch: risk-on → momentum sleeve, range/high-vol → reversal sleeve or cash-tilt. Keep the switch slow (weekly state changes) to avoid whipsaw costs.

20. CLAIM: Combining bagging/boosting tree ensembles with HMM state estimates for bull/bear/neutral detection improves regime-shift detection vs HMM alone.
    SOURCE: AIMS "multi-model ensemble-HMM voting framework" — https://www.aimspress.com/aimspress-data/dsfe/2025/4/PDF/DSFE-05-04-019.pdf | 2025 | CONFIDENCE: med
    IMPLICATION: If we ML anything, this is the spot: a small random-forest voting on top of HMM posterior + trend/vol features for regime classification (classification, not return prediction).

21. CLAIM: Bayesian fitting of Gaussian HMMs on daily returns with a simple forward-filter/backward-smoother preserves regime structure and stabilizes detection in high-vol episodes; smoothing (using only info up to t) avoids the classic HMM lag pitfall.
    SOURCE: Wiley "Data Driven Investment Strategies Using Bayesian Inference in Regime Switching" — https://onlinelibrary.wiley.com/doi/full/10.1002/asmb.70058 | 2025-11-23 | CONFIDENCE: med-high
    IMPLICATION: Use filtered (real-time) probabilities in backtests, never smoothed full-sample Viterbi paths — a classic look-ahead bug in HMM backtests. Parameter: minimum regime dwell time (e.g., 5 days) before acting.

22. CLAIM: Practitioner guides converge on HMM regime detection + walk-forward (not in-sample) backtesting as the minimum standard for regime-adaptive strategies.
    SOURCE: QuantInsti regime-adaptive trading guide — https://blog.quantinsti.com/regime-adaptive-trading-python/ | 2025-08-07 | CONFIDENCE: med
    IMPLICATION: All our comparisons must be walk-forward (expanding window, refit monthly); with 3y history that gives ~30 folds — enough for stable regime-parameter estimates, not for deep nets.

---

## (f) Backtest overfitting — multiple testing, DSR, MinTRL guardrails

23. CLAIM: The Deflated Sharpe Ratio corrects observed Sharpe for (i) selection bias under multiple testing and (ii) non-normal returns; without it, the best of N tried configs is a statistical fluke with high probability.
    SOURCE: Bailey & López de Prado, "The Deflated Sharpe Ratio", J. Portfolio Management 40(5) — https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf | 2014 (foundational; still the standard) | CONFIDENCE: high
    IMPLICATION: Log EVERY configuration we try (even aborted ones) and compute DSR with the true trial count N before promoting any strategy. N includes parameter grids, not just "final" candidates.

24. CLAIM: A dependency-light reference implementation assembles PSR, expected-max-Sharpe under N trials, DSR, and MinTRL and shows they are computable in a few dozen lines — the friction is bookkeeping, not math.
    SOURCE: "The Deflated Sharpe Ratio in Practice" (working paper + code) — https://dmitridefreitas.com/papers/Deflated-Sharpe-Ratio-Working-Paper.pdf | recent (2025±) | CONFIDENCE: med-high
    IMPLICATION: Vendor nothing — implement PSR/DSR/MinTRL as a ~100-line module in the lab and gate every promotion on DSR > 0 at 95%.

25. CLAIM: A ready-made "statistical gate" exists combining DSR + PBO (probability of backtest overfitting via CSCV) + multiple-testing Sharpe haircut + MinTRL with a PASS/FAIL verdict; released as an open skill (Jul 2026).
    SOURCE: quantskills/skill-backtest-overfit — https://github.com/quantskills/skill-backtest-overfit | 2026-07-03 | CONFIDENCE: med (tooling, methodology sound)
    IMPLICATION: Copy this gate design for our promotion checklist; PBO via combinatorial CV is feasible even on 3y daily data (756 obs) if strategy count stays small.

26. CLAIM (the math we must internalize): with ~756 daily obs (3y), the standard error of an annualized Sharpe is roughly sqrt((1+SR²/2)/756)*sqrt(252) ≈ 0.6 — i.e., a 3y backtest cannot statistically distinguish SR 1.0 from SR 0.4. MinTRL for SR≈0.5 at 95% confidence is ~5+ years.
    SOURCE: derived from Bailey & López de Prado PSR/MinTRL formulas (source #23/#25) | 2026-09-29 | CONFIDENCE: high (arithmetic)
    IMPLICATION: HARD CONSTRAINT for the lab: 3y backtests are directional screens only. Decisions must rest on (a) DSR-pass, (b) economic prior (why should this edge exist in mega-caps?), (c) live/paper forward test. Never promote on backtest Sharpe alone; report CIs on every Sharpe.

---

# TOP-10 ACTIONABLE (ranked) — US mega-cap daily lab, 12 names + SPY/QQQ, 3y, long-only

1. **DSR/PBO/MinTRL promotion gate (build first).** Implement PSR/DSR + trial-count registry + PBO(CSCV). Nothing ships without DSR>0 @95% with the *true* N of configs tried. [from #23–26]
2. **Treat 3y as a screen, forward-test as the evidence.** MinTRL math says SR estimates on 756 obs have ~±0.6 error bands; run paper-trading (shadow.py) for >=3 months before any capital decision. [#26]
3. **Two-sleeve architecture: momentum (risk-on) + 3–5d reversal (range-bound).** Negatively-correlated signal families; simple rules, slow top-level HMM/vol-percentile switch with 5-day dwell minimum, filtered (not smoothed) probabilities. [#6,#19,#21]
4. **Vol-target the momentum sleeve** (target ~15–20% sleeve vol; flatten or halve when 20d SPY vol > 80th percentile) — directly mitigates momentum crash risk. [#3,#4]
5. **Per-name weight cap (e.g., 20%) + sector/AI-complex concentration check** so momentum doesn't collapse into an AI-beta bet; always report vs QQQ-relative, not absolute. [#1,#11]
6. **Net-of-cost only, with hysteresis bands.** Model >=2–5 bps/side; trade only when signal crosses a band, target turnover < 200%/yr; reversal sleeve especially dies on costs. [#7]
7. **Survivorship honesty.** The 12-name universe is today's winners — never claim absolute alpha; evaluate everything relative to SPY and QQQ with matching exposure. [#11]
8. **Reversal entries conditioned on vol-scaled moves** (down > k·σ20) instead of fixed % dips; test k ∈ {1.5, 2, 2.5}. [#8]
9. **No end-to-end RL/LLM decision cores.** ML only for regime classification (RF-on-HMM ensemble); if any LLM touches the pipeline, point-in-time features only + evaluation restricted to post-cutoff dates. [#10,#13,#15,#16,#18]
10. **Drawdown kill-switch as structural constant** (sleeve −15% → flatten to SPY; portfolio −10% → all cash 20 days) — substitutes for the crash history our 3y window can't provide. [#5]

## Noted dead-ends / gaps
- arXiv export API: persistent 429 from this environment; used search-index metadata instead. Direct SSRN abstract fetches not attempted beyond one (reachable via search snippets).
- Two Sigma / Man Group blogs: not surfaced in this pass (DDG ranking); JPM AM + LSEG + Alpha Architect carried the practitioner weight instead.
- Paper-specific depth (full PDFs) not read for all entries; claims above rest on abstracts + consistent multi-source triangulation where possible.
