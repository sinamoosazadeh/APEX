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
| 4 | Feature Platform | 🟡 **partial** | Delivered: feature registry (declare-before-compute, versioned definitions), SQLite feature store (bar-anchored, idempotent, vector + series queries), computation pipeline (pure engines, registry-validated emission, catalog events), `apex features` CLI, a shared chart-structure fold (BOS/CHoCH state machine + dealing range, single source per Constitution 2.12), and three migrated AICE families — **market structure** (19 features: swings via strict pivots, BOS/CHoCH, break quality with decay, displacement, dealing range/premium/discount/OTE, sweeps, equal highs/lows), **liquidity** (16 features: decayed confidence pools bumped by equal extremes at three pivot scales, resting-liquidity composites, external-extreme proximity, sweep efficiency, stop hunts, inducement) **order blocks/FVG** (22 features: creation scans on structure breaks with the nine-term OB quality, decay/retest/mitigation lifecycle, breaker flags, three-bar FVG detection with six-term quality, fill tracking, IFVG inversions, BPR; FVG ``trendQ`` fully wired via the zero-lag momentum filter, HTF terms pinned to AICE neutrals until the MTF family lands) and **volume & normalization** (25 features: RVOL, ATR percentile rank/width/regime factor, EWMA volatility forecast + adaptive ATR ratio, UTC-day VWAP deviation in ATR and winsorized z, expansion/compression, delta approximation — aggression, rolling/cumulative delta bias, absorption, spikes, climaxes — rolling volume-profile POC distance/acceptance, zero-lag momentum) — all validated against real Toobit bars. Remaining families per the ch. 2 migration matrix: SMT divergence + HTF/MTF context, statistical |
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

## Current quality-gate results (Phase 4 fourth slice)

- `ruff check apex tests` — clean
- `mypy` (strict, 145 files) — clean
- `pytest` — **268 passed**
- `python -m apex --check` — boots healthy (3 plugins, 4 modules), exits 0
- Real-data validation: four families over 518 confirmed live Toobit bars per
  symbol; `apex features` stores 35,913 registry-validated features per run
  (structure 501x19 + liquidity 468x16 + orderblocks 498x22 + volume 318x25 —
  per-family warmup gating verified, volume honoring its 200-bar AICE warmup).
  Volume readings coherent with the observed tape: BTC above its day-VWAP and
  ~5.6 ATR above the 96h POC with thin acceptance, momentum-bull bars
  dominating (150 vs 117), sparse absorption/climax events

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

1. SMT divergence (multi-symbol context) and the HTF/MTF context family
   (rewires the remaining ``mtfQ``/``htfQ`` neutral values in OB/FVG
   quality and the FVG ``locQ`` HTF branch).
2. Statistical family (regime: ADX/efficiency ratio/hurst proxy/entropy,
   candle DNA, kinetic oscillators) — closes Phase 4.
3. Then Phase 5: the Probability Platform consuming stored feature vectors.
