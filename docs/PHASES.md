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
| 4 | Feature Platform | ✅ **complete** | Feature registry (declare-before-compute, versioned definitions), SQLite feature store (bar-anchored, idempotent, vector + series queries), computation pipeline (pure engines, registry-validated emission, catalog events), `apex features` CLI, a shared chart-structure fold (BOS/CHoCH state machine + dealing range, single source per Constitution 2.12), and all seven migrated AICE families — **market structure** (19 features: swings via strict pivots, BOS/CHoCH, break quality with decay, displacement, dealing range/premium/discount/OTE, sweeps, equal highs/lows), **liquidity** (16 features: decayed confidence pools bumped by equal extremes at three pivot scales, resting-liquidity composites, external-extreme proximity, sweep efficiency, stop hunts, inducement) **order blocks/FVG** (22 features: creation scans on structure breaks with the nine-term OB quality, decay/retest/mitigation lifecycle, breaker flags, three-bar FVG detection with six-term quality, fill tracking, IFVG inversions, BPR; FVG ``trendQ`` fully wired via the zero-lag momentum filter, HTF terms pinned to AICE neutrals until the MTF family lands) and **volume & normalization** (25 features: RVOL, ATR percentile rank/width/regime factor, EWMA volatility forecast + adaptive ATR ratio, UTC-day VWAP deviation in ATR and winsorized z, expansion/compression, delta approximation — aggression, rolling/cumulative delta bias, absorption, spikes, climaxes — rolling volume-profile POC distance/acceptance, zero-lag momentum) — plus the first multi-series families on the new ``IContextFeatureEngine`` contract (pipeline fetches declared auxiliary series; strictly causal closed-bar mapping replaces Pine's ``request.security`` per the Constitution's no-repaint rule): **HTF context** (8 features: two macro struct-pack biases, alignment, bull/bear context, confidence, macro discount/premium) and **SMT divergence** (7 features: age-gated opposing-swing conditions against the correlated reference, rolling return correlation with AICE's dynamic quality, decayed per-side confidence pools). OB/FVG ``mtfQ``/``htfQ``/``locQ`` HTF terms fully rewired (defs 1.0.2) — every AICE context term in the family is now live. Finally the **statistical** family closes the ch. 2 migration matrix (32 features: regime detection — ADX/DMI, Kaufman efficiency, variance-ratio Hurst proxy, return entropy, slope quality, volatility clustering, five-term trend evidence with trending/ranging split, market entropy — candle DNA with persistence/body rank/impulse/rejections and the weighted composites, engulfing/pin/hammer/star/doji patterns, sequence bias, and the kinetic oscillators: WaveTrend, Schaff trend cycle, CCI with regime-scaled thresholds composed into kin_long/short). **All seven AICE families migrated and validated against live Toobit data.** |
| 5 | Probability Platform | ✅ **complete** | The AICE confluence core behind the evolved `IProbabilityEngine` (bar-anchored, windowed, pure): thirteen evidence channels computed from stored 133-feature vectors (structure with the struct-momentum fold, liquidity gated on sweeps/springs, OB/FVG passthrough, zone, candle DNA, kinetic, delta with sos/sow compositions, sequences, trend, MTF alignment over internal/external/chart/macro biases, SMT, volume profile), trend-blended adaptive weights normalized to one (regime-composed SMT weight), the nine cross-channel interaction bonuses, the opposing-context penalty stack, and sigmoid calibration `squash((raw - 0.45) x (5.4 + tc x 1.2))` clamped [0.01, 0.99]. Assessments persist per (bar, side) with channels payload in the SQLite assessment store; `probability.assessed/failed` catalog events; `apex probability` CLI. Confidence intervals are APEX semantics (entropy-scaled width) until the research platform measures calibration. Deferred per AICE gates/later phases: IC + meta-learning weight factors and the meta calibrator (Phase 11), Kalman terms, crypto dominance context, probability smoothing (off in AICE). Four features added for exact evidence: structure internal/external bias, volume narrow-range, statistical direction (registry 133) |
| 6 | Decision Platform | ✅ **complete** | The Central Decision Kernel behind the new `IDecisionEngine` contract (bar-anchored, windowed, pure), consuming persisted assessments + feature vectors: the AICE contributor counts (13 per-channel thresholds), the uncertainty composite (ambiguity/entropy/transition/thin-evidence/clustering), expectancy (target room vs macro extremes, rr quality, `expected_R = p*rr - (1-p) - fees`), regime-adjusted probability/uncertainty gates, RVOL + ATR-band + HTF permission + entropy standby (catalyst override) + failure-risk oracle + bar quality + expectancy + L/S edge gates, cooldown and the 13-channel cosine similarity cooldown, all three AICE execution timings (Immediate, Trigger Candle, Retest + Micro BOS with the pending arm/confirm/expire state machine), the 12-setup classification taxonomy, and signal construction (entry at close, ATR / Structure-Hybrid stop, three R-multiple targets with the macro-extreme liquidity resolver) emitting `Signal` domain objects (5.5). Every outcome is audited: signal / **pending** (armed awaiting confirmation) / veto (with failed gates) / stand-aside, persisted in the SQLite decision store; `decision.signal.fired/completed/failed` events; `apex decide` CLI. Deferred along AICE gates/later phases: position flatness (portfolio), virtual equity guard (needs trade history), crypto context, Kalman |
| 7 | Signal Optimizer | ✅ **complete** | The Book V ten-stage pipeline behind the evolved `IOptimizer` contract (space discovered from the engine, pure, one seed determines every trial): random exploration → Latin hypercube → Bayesian (Optuna TPE, seeded) → local grid refinement → sensitivity analysis (per-parameter perturbation ranking) → stability analysis (top-candidate dispersion) → walk-forward → rolling-window (+ expanding per the validation protocol) → seeded Monte Carlo bootstrap → final ranking with the full acceptance gate (all validations + no OOS collapse + trade-count floor). The decision kernel publishes its 16-parameter search space (bounds from the AICE input declarations); every trial re-folds the CDK over stored snapshots and simulates fired signals to R outcomes (stop/target/horizon, pessimistic same-bar collisions — signal quality only, per part 5's separation from risk/execution). Multi-objective score: expectancy/net-R/profit-factor/Sharpe/Sortino/Calmar/win-rate/consistency minus drawdown/streak/variance/low-trade penalties. Runs persist in the SQLite run store; accepted winners publish the per-symbol-per-timeframe `{SYMBOL}_{TF}_signal.json` artifact with SHA256 (strict series isolation); `apex optimize-signal` CLI; per-fold re-optimization defers to the research orchestrator (Book V part 7) |
| 8 | Risk Optimizer | ⬜ pending | Book V part 6; Book II ch. 10 |
| 9 | Portfolio Engine | ⬜ pending | Book II ch. 13/21; Book I ch. 8 |
| 10 | Execution Engine | ⬜ pending | Book II ch. 12/20 |
| 11 | Research Platform | ⬜ pending | Book II ch. 14/23; Book I ch. 11/12; optimization orchestrator (Book V part 7) |
| 12 | Monitoring Platform | ⬜ pending | Book II ch. 26; Book I ch. 10; Telegram console (Book IV) |
| 13 | Security Platform | ⬜ pending | Book II ch. 25; Book I ch. 13 |
| 14 | Deployment | ⬜ pending | Book II 29.20/29.25 |
| 15 | Production Validation | ⬜ pending | Book II 29.26 acceptance criteria |

## Current quality-gate results (Phase 7 closed)

- `ruff check apex tests` — clean
- `mypy` (strict, 188 files) — clean
- `pytest` — **340 passed**
- `python -m apex --check` — boots healthy (6 plugins, 7 modules)
- Real-data validation: `apex optimize-signal` ran the full ten-stage
  pipeline (136 trials) over 317 live snapshots and correctly REJECTED the
  run — every candidate produced too few confirmed trades on 13 days of
  history, tripping the Book V low-trade acceptance gate; no artifact was
  published. The acceptance path (all validations green, SHA256 artifact)
  is proven on richer synthetic data in the test suite (8 trades,
  confidence 1.0, deterministic across seeds). Live acceptance awaits the
  deeper backfills the research platform orchestrates (Phase 11).
  Mid-session live catch: with_overrides used a string type comparison
  that missed real type objects — integer parameters arrived as floats;
  fixed with a regression test

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

## Next up (Phase 8)

The Risk Optimizer (Book V part 6; Book II ch. 10): per-symbol,
per-timeframe optimization of the risk layer — stop models, target
structure, exposure shaping — strictly isolated from signal logic,
reusing the optimization platform's stages, stores and artifacts.
