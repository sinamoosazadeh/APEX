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
| 2 | Core Infrastructure | 🟡 **partial** | Delivered now: shared kernel (`apex/domain`), infra + engine contracts, event platform (journal + deterministic bus), DI container, module registry, health monitor, kernel boot/shutdown, `python -m apex`. Remaining: durable storage-backed journal, plugin loader, scheduler service |
| 3 | Data Platform | ⬜ pending | Book II ch. 6/16/24; Toobit gateway (Book VII) behind `IExchange`, storage repositories, replay |
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

## Current quality-gate results (Phase 0/1 acceptance)

- `ruff check apex tests` — clean
- `mypy` (strict, 89 files) — clean
- `pytest` — **148 passed**
- `python -m apex --check` — boots healthy, exits 0

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

## Next up (Phase 2 completion → Phase 3)

1. Durable event journal + repository implementations over SQLite/Parquet
   (`IStorage`/`IRepository`, Book II ch. 24).
2. Plugin loader with signature/version/dependency checks (Book II 29.24).
3. Toobit market gateway behind `IExchange` with the anti-corruption layer
   (Book II 5.37, Book VII) — first as market-data-only (Phase 3 read path).
4. Bar ingestion pipeline with quality scoring and gap detection
   (Book II ch. 6/16).
