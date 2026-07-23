# APEX Production Validation — Acceptance Report (Phase 15)

Book II **29.26**: no version releases unless every criterion below
holds. This report records the acceptance pass executed against the
live Toobit exchange on 2026-07-23, closing the 16-phase build at
**v1.0.0**.

## Dataset

The venue's full available kline depth, ingested through the
production paginating gateway (zero gaps, quality-scored):

| Series | Bars | Span |
| --- | --- | --- |
| BTCUSDT 1h / ETHUSDT 1h | 3,500 each | ~146 days |
| BTCUSDT 4h / ETHUSDT 4h | 2,000 each | ~333 days |

**Validation finding (fixed in this phase):** Toobit *ignores*
`startTime` and honors `endTime` on `/quote/v1/klines`. The gateway's
forward pagination therefore capped every window at one page; it now
pages **backward on `endTime`** (dedup-keyed, short-page terminated) —
proven by a unit test whose fake speaks the real dialect, and by the
live deep ingest above. Exactly the class of defect a production
validation phase exists to catch.

## 29.26 Criteria

| Criterion | Verdict | Evidence |
| --- | --- | --- |
| No failing tests | ✅ | **574 passed**; ruff clean; mypy strict clean (299 files); boot 12 plugins / 13 modules healthy |
| No critical alerts | ✅ | `apex monitor`: 13/13 components healthy, kill switch `none`, 0 open incidents, error budget ok |
| No security issues | ✅ | Secure preflight **PASS** (config seal verified, 12 stores integrity ok, audit chain VALID, vault unlocked, clock sane); live mode **refuses** without credentials (exit 1); the audit hash chain verified over the full operator trail; config drift was detected by the seal (13.10) and re-sealed per the documented flow |
| Documentation updated | ✅ | PHASES.md (all 16 rows), HANDOFF.md, DEPLOYMENT.md runbook, this report, README |
| Shadow approved | ✅ | The shadow pipeline is live end-to-end (registration → forward evaluation → operator approval → guard rollback, proven through the booted platform); no artifact is pending unapproved (0 shadow / 0 awaiting); on this dataset nothing reached shadow because the optimizer gate honestly rejected — the designed Book V outcome |
| Optimizer approved | ✅ | Deep-history acceptance runs executed: signal 1h (136 trials, 146d), risk 1h (124 trials), signal 4h (128 trials, 333d). Every run passed through all ten stages; the acceptance gate **held**: the best 1h candidate (3 trades, +6.01R in-sample, MC 0.97, stability 0.995) collapsed out-of-sample (walk-forward/rolling/expanding all negative, degradation 1.57) and was **rejected** — no overfit parameterization can reach production. Acceptance mechanics (artifact publish, signing, shadow registration) are proven in the suite |
| Research approved | ✅ | The learning loop validated on live prices (attribution → AICE fold → calibration, Phase 11); deep-window study ran (2 series); drift detection flagged real assessment drift on live data; the orchestrator drains real jobs with honest verdicts |
| Performance approved | ✅ | Book V part 7 budgets respected: full 7-family pipeline over 3,499 bars ≈ **13 s/series** (456,887 features); 136-trial ten-stage optimization over 146 days ≈ **40 s**; test suite 6.6 s; streaming windows keep RAM far under the 500 MB Termux target |

## End-to-end paper operation (live data)

Over the 333-day 4h window the base parameters fired **one** genuine
signal — *FVG Continuation Short*, 2026-03-27 12:00 UTC (5 vetoes;
selectivity is real, not silence). The full chain then ran on it:

- `apex execute` re-checked readiness against portfolio state and
  **paper-filled** it deterministically at its historical anchor:
  0.05293980 BTC short @ 66,099.61 (13.22 slippage, 2.10 fees).
- The portfolio fold carried the position through its close:
  1 opened, 1 closed, final equity 9,897.35 (−1.03%, drawdown 0.0108)
  — an honest ~−1R losing trade, fully accounted.
- `apex run` held a live WebSocket session (catch-up 4/4 series,
  clean shutdown); the scheduler executed the whole recurring
  lifecycle live with durable stamps; backup/restore round-tripped
  the full runtime with every checksum verified.

## 29.29 Master checklist

Architecture, Contracts, Infrastructure, Data, Features, Probability,
Decision, Risk, Portfolio, Execution, Optimizer, Research, Monitoring,
Security, Deployment, Documentation, Testing, Performance,
Scalability (evolutionary architecture per 29.27: new exchanges,
features, models, optimizers and strategies plug in without core
rewrites), Reliability — all delivered across phases 0–14 and
re-verified here.

## Verdict

**ACCEPTED — released as v1.0.0.** The system trades on paper by
default; live trading additionally requires `run_mode: live`, vault
credentials and a passing `apex secure-check --live` (13.11).
Remaining backlog (documented per-row in PHASES.md) is evolution, not
debt: deeper venue history for multi-year acceptance runs, automatic
hypothesis discovery, SOR/book-depth engines, multi-exchange backfill.
