# APEX Phase Tracker & Roadmap

Phase structure per Constitution 4.4; build order per Book II ch. 29
(Master Repository Blueprint). A phase is complete only when tests pass,
docs are updated and quality gates are green (Constitution 4.15). The
project stays runnable at the end of every phase (4.6).

## Status

| Phase | Name | Status | Delivered |
| --- | --- | --- | --- |
| 0 | Project Initialization | ✅ **complete** | Repo structure, tooling (uv/ruff/mypy strict/pytest), 12-file schema-gated config set, git (main/develop), docs, spec library |
| 1 | Foundation Layer | ✅ **complete** | `apex/core`: types, enums, coded exceptions, identity, time system, metadata, validation, serialization+hashing, Result, BaseObject (lineage/versioning), contexts, versioning/stability, structured logging, config platform |
| 2 | Core Infrastructure | ✅ **complete** | Shared kernel (`apex/domain`), infra + engine contracts, event platform (journal + deterministic bus), DI container, module registry, health monitor, kernel boot/shutdown with plugin stage, storage platform (SQLite key/value behind `IStorage`, durable event archive with journal catch-up), plugin system (manifest contract, config-driven loader with API-version/dependency validation) |
| 3 | Data Platform | ✅ **complete** | REST: Toobit client, anti-corruption translator (5.37), paginating gateway behind `IMarketDataGateway`, gap detection + quality scoring, ingestion pipeline. Live: WebSocket streaming (`wss` client with keepalive + injected connector, closed-bar transition detection publishing `market.bar.closed`, throttled forming-bar persistence), tick storage (idempotent on exchange trade ids), catch-up synchronization resuming from the latest stored bar. Replay serves bars *and* ticks. CLI: `ingest`, `sync`, `stream`. Live-validated: 400 bars synced + 225 ticks streamed in 25s from Toobit. Deferred to later phases: funding/OI enrichment (Phase 4 features), multi-exchange backfill (plugin per Book II 29.9) |
| 4 | Feature Platform | 🟡 **partial** | Delivered: feature registry (declare-before-compute, versioned definitions), SQLite feature store (bar-anchored, idempotent, vector + series queries), computation pipeline (pure engines, registry-validated emission, catalog events), `apex features` CLI, a shared chart-structure fold (BOS/CHoCH state machine + dealing range, single source per Constitution 2.12), and three migrated AICE families — **market structure** (19 features: swings via strict pivots, BOS/CHoCH, break quality with decay, displacement, dealing range/premium/discount/OTE, sweeps, equal highs/lows), **liquidity** (16 features: decayed confidence pools bumped by equal extremes at three pivot scales, resting-liquidity composites, external-extreme proximity, sweep efficiency, stop hunts, inducement) **order blocks/FVG** (22 features: creation scans on structure breaks with the nine-term OB quality, decay/retest/mitigation lifecycle, breaker flags, three-bar FVG detection with six-term quality, fill tracking, IFVG inversions, BPR; FVG ``trendQ`` fully wired via the zero-lag momentum filter, HTF terms pinned to AICE neutrals until the MTF family lands) and **volume & normalization** (25 features: RVOL, ATR percentile rank/width/regime factor, EWMA volatility forecast + adaptive ATR ratio, UTC-day VWAP deviation in ATR and winsorized z, expansion/compression, delta approximation — aggression, rolling/cumulative delta bias, absorption, spikes, climaxes — rolling volume-profile POC distance/acceptance, zero-lag momentum) — plus the first multi-series families on the new ``IContextFeatureEngine`` contract (pipeline fetches declared auxiliary series; strictly causal closed-bar mapping replaces Pine's ``request.security`` per the Constitution's no-repaint rule): **HTF context** (8 features: two macro struct-pack biases, alignment, bull/bear context, confidence, macro discount/premium) and **SMT divergence** (7 features: age-gated opposing-swing conditions against the correlated reference, rolling return correlation with AICE's dynamic quality, decayed per-side confidence pools). OB/FVG ``mtfQ``/``htfQ``/``locQ`` HTF terms fully rewired (defs 1.0.2) — every AICE context term in the family is now live. All validated against real Toobit bars. Remaining per the ch. 2 matrix: statistical family |
| 5 | Probability Platform | ⬜ pending | Book II ch. 8/18 |
| 6 | Decision Platform | ⬜ pending | Book II ch. 11/19; Central Decision Kernel (Book I ch. 9) |
| 7 | Signal Optimizer | ⬜ pending | Book V part 5; Book II ch. 9 |
| 8 | Risk Optimizer | ⬜ pending | Book V part 6; Book II ch. 10 |
| 9 | Portfolio Engine | ⬜ pending | Book II ch. 13/21; Book I ch. 8 |
| 10 | Execution Engine | ⬜ pending | Book II ch. 12/20 |
| 11 | Research Platform | ⬜ pending | Book II ch. 14/23; Book I ch. 11/12; optimization orchestrator (Book V part 7) |
| 12 | Monitoring Platform | ⬜ pending | Book II ch. 26; Book I ch. 10; Telegram console (Book IV) |
| 13 | Security Platform | ⬜ pending | Book II ch. 25; Book I ch. 13 |
| 14 | Deployment | ⬜ pending | Book II 29.20/29.25 |
| 15 | Production Validation | ⬜ pending | Book II 29.26 acceptance criteria |

## Current quality-gate results (Phase 4 fifth slice)

- `ruff check apex tests` — clean
- `mypy` (strict, 152 files) — clean
- `pytest` — **278 passed**
- `python -m apex --check` — boots healthy (3 plugins, 4 modules, 6 engines)
- Real-data validation: six families over 518 confirmed live Toobit 1h bars
  per symbol with live 4h macro series; `apex features` stores 43,683
  registry-validated features per run (structure 501x19 + liquidity 468x16 +
  orderblocks 498x22 + volume 318x25 + htf 518x8 + smt 518x7 — exact).
  Context readings coherent: HTF alignment +2 (bullish) on both symbols in
  premium, BTC/ETH return correlation 0.89 (quality 0.73), bull SMT
  confidence 0.50 vs bear 0.15. Fixed a latent core bug found by this slice:
  the stability/contract-version decorators mutated classes, which polluted
  runtime-checkable Protocol members and broke isinstance dispatch — moved to
  external registries

## Spec library

| File | Book | Content |
| --- | --- | --- |
| `specs/01_architecture.md` | Book I | APEX architecture (13 chapters) |
| `specs/02_aice_reverse.md` | Book II | AICE reverse-engineering & implementation spec (29 chapters) |
| `specs/03_constitution.md` | Book III | Development Constitution |
| `specs/04_telegram_bot.md` | Book IV | Telegram subsystem blueprint |
| `specs/05_optimization.md` | Book V | Signal/Risk/Execution optimizers + orchestrator |
| `specs/06_aice_pine.md` | Book VI | AICE Pine Script v6 source (reference logic) |
| `specs/07_toobit_api.md` | Book VII | Toobit exchange API documentation |
| `specs/08_master_prompt.md` | — | Master project prompt (execution constraints) |

Note: books 1, 2, 3, 7 and 8 were delivered as DOCX and converted to text;
book 8 is truncated at its source ("Dependency Rule" section) — its missing
content is fully covered by Books I-III. Priority on conflict:
**Constitution → Book I → Book II → AICE logic**.

## Next up (Phase 4 continuation)

Migrate the remaining AICE families onto the delivered plumbing (Book II
ch. 2 migration matrix; Book VI source):

1. Statistical family (regime: ADX/efficiency ratio/hurst proxy/entropy,
   candle DNA, kinetic oscillators) — closes Phase 4.
2. Then Phase 5: the Probability Platform consuming stored feature vectors.
