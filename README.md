# ai-trading

Self-hosted paper-trading experiment: deterministic momentum book + forward
out-of-sample tracker + buy-and-hold control group, all state in git.

Off-boarded from the ai4trade platform on **2026-09-30** (owner decision):
no external trading platform, no social/challenge integration, no LLM in the
daily loop. The paper book was carried over and continues here.

## Architecture

```
                     GitHub repo (state-in-git)
 ┌──────────────────────────────────────────────────────────────────┐
 │                                                                  │
 │  marketdata.py ──► trade.py ──► daily_run.py ──► broker.py       │
 │  (Yahoo quotes)   (decision:   (two-layer    (local paper        │
 │                    exits then   entry gate +  fills, 5bps/side,   │
 │                    entries)     max 2/day)    state/book.json)    │
 │                       ▲               │                          │
 │                       │               ▼                          │
 │              dd_screen.py      state/log.txt                     │
 │              (TA deep-dive,    state/dd_verdicts.json            │
 │               veto-only —             ▲                         │
 │               workspace-side)          │                         │
 │                                        │                         │
 │  forward/forward.py   control.py       │  scoreboard             │
 │  (OOS variants,       (buy-and-hold    │  comparison             │
 │   daily replay)        control clone)──┘                         │
 │                                                                  │
 │  .github/workflows: daily / scoreboard / (ddgate) / (panel) / ci │
 └──────────────────────────────────────────────────────────────────┘
        runs on: gokore-runner (ARC, kubernetes-mode) × python:3.12-slim
```

## Schedule table (all UTC — GitHub Actions cron is UTC)

| Workflow      | Schedule            | Runs                                   | State written                              |
| ------------- | ------------------- | -------------------------------------- | ------------------------------------------ |
| daily         | `0 14 * * 1-5`      | `daily_run.py`                         | `state/` (book.json, log.txt)              |
| scoreboard    | `30 21 * * 1-5`     | `forward/forward.py` then `control.py` | `state/`, `control_state.json`, `forward/` |
| ddgate        | dispatch-only       | `dd_screen.py` (stubbed, see below)    | `state/dd_verdicts.json`                   |
| panel         | dispatch-only       | stub note                              | —                                          |
| ci            | on PR               | compile + import + broker math checks  | —                                          |

Every job commits its state back to the branch it ran on (default branch for
scheduled runs) as `ai-trading-bot` using the workflow `GITHUB_TOKEN`.

## State-in-git model

The repo IS the database: `state/book.json` (cash, positions, fills),
`state/log.txt` (DAILY/TRADED/SKIP_BUY/DD_VETO lines), `state/last_trade_decision.json`,
`control_state.json`, `forward/forward_state.json` + `forward/data/*.csv`.
No external store; history is the git log. Fills are capped to the last 500
in the book.

## Runner requirements

- Self-hosted runner `gokore-runner` (ARC, kubernetes-mode — **no docker**;
  jobs use `container: python:3.12-slim` instead of container jobs).
- Outbound HTTPS to `query1.finance.yahoo.com` and `news.google.com` (market
  data + headline screens). Nothing else — no platform API remains.
- `permissions: contents: write` so the `GITHUB_TOKEN` can push state commits.

## Secrets

| Secret                   | Required | Used by                                   |
| ------------------------ | -------- | ----------------------------------------- |
| `OPENAI_API_KEY`         | no       | dd_screen.py (TradingAgents) — only when the DD gate is enabled |
| `OPENAI_API_BASE`        | no       | optional LLM endpoint override for the same |
| `FINANCIAL_DATASETS_API_KEY` | no   | future AIHF panel                          |

No tokens are stored in the repo or the book.

## Enabling the DD gate

`dd_screen.py` (copied from the workspace) runs a TradingAgents deep-dive on
`trade.py` buy candidates with veto-only authority. It needs the TA venv
(`integration/vendor/TradingAgents` — not vendored here) and an
`OPENAI_API_KEY` secret. Until then:

- the `ddgate` workflow is `workflow_dispatch`-only (schedule lines commented,
  ready to uncomment),
- the DD gate runs workspace-side and pushes `state/dd_verdicts.json`,
- `daily_run.py` treats a missing/stale verdict file as "no vetoes" — the
  absence never blocks trades (abstain semantics).

To enable: vendor the venv (or a TA container image), add the secret,
uncomment the schedule in `.github/workflows/ddgate.yml` and the run/commit
steps inside it.

## What was dropped with the platform

ai4trade platform API calls (account, positions, trade execution at
`/signals/realtime`, strategy/discussion posting, challenges), `poll.py`
(platform-only context poller), and `credentials.json`. Trade execution is
now `broker.py` with local fills at 5 bps/side; `trade.py` reads cash and
positions from `state/book.json` instead of the platform account.

## History

- 2026-09-28..29 — stack built and run in the workspace against the ai4trade
  paper platform (see `orchestrator/progress-*.txt`, `research/`,
  `lab/`, `lab2/` results; 307-trial lab sweep found nothing passing
  multiple-testing correction, motivating the forward tracker).
- 2026-09-29 — sleeve deployed/trimmed/rebalanced; CRWD + PANW bought.
- 2026-09-30 — **platform off-boarded**; book seeded into `state/book.json`
  (cash 25,666.20, positions with entry prices from the last platform
  snapshot — not approximated) and the experiment continues self-hosted.
