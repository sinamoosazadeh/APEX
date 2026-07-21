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
| 4 | Feature Platform | ⬜ pending | Book II ch. 7/17; AICE feature migration (Book VI reference, Book II ch. 2 migration matrix) |
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

## Current quality-gate results (Phase 3 acceptance)

- `ruff check apex tests` — clean
- `mypy` (strict, 122 files) — clean
- `pytest` — **214 passed**
- `python -m apex --check` — boots healthy (2 plugins, 3 modules), exits 0
- Live smoke: `sync` stored 400 bars across 4 series (0 gaps) and a 25s
  `stream` session captured 320 WS messages / 225 deduped ticks from Toobit

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

## Next up (Phase 4: Feature Platform)

The AICE migration begins (Book II ch. 2 migration matrix, ch. 7/17; Book VI
reference source), on top of the confirmed-bar store:

1. Feature contract plumbing: registry, store, pipeline, validation, cache
   (Book II 29.10 build order).
2. First feature families from the AICE Pine source: market structure
   (swings/BOS/CHoCH), then liquidity, then volume/normalization.
3. Every feature is a plugin (Book II 3.23) computing from confirmed bars
   only, emitting the universal Feature contract (5.8).
