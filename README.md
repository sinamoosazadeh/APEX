# APEX — Autonomous Probabilistic Execution eXchange

Institutional-grade, deterministic, non-repainting crypto trading intelligence
platform. APEX is a ground-up re-engineering of the **AICE** (Adaptive
Institutional Confluence Engine) Pine Script v6 indicator into a modular,
event-driven Python system, built strictly to the APEX specification books.

> Market understanding first, future-state estimation second, signals last.
> A buy/sell signal is a *product* of the system — never its core.

## Status

**Phases 0-3 complete.** The kernel boots with a plugin system, durable
storage and event archiving. The data platform is fully operational:
REST catch-up, live WebSocket streaming with closed-bar events, tick
capture (deduped on exchange trade ids), quality scoring, gap detection
and deterministic replay — all validated against the live Toobit
exchange. Next: Phase 4, the AICE feature migration.
See [docs/PHASES.md](docs/PHASES.md).

## Requirements

- Python **3.13+** (Constitution 3.3)

## Quick start

```bash
# create environment and install (uv shown; pip works equally)
uv venv --python 3.13 .venv
uv pip install -p .venv/bin/python -e . --group dev

# boot the platform: config -> logger -> DI -> event bus -> modules -> health -> ready
.venv/bin/python -m apex

# boot as a validation gate (CI / deployment)
.venv/bin/python -m apex --check

# catch every configured series up to the present (REST)
.venv/bin/python -m apex sync

# sync, then consume the live WebSocket feed for a minute
.venv/bin/python -m apex stream --seconds 60

# ingest history for one series
.venv/bin/python -m apex ingest --symbol BTCUSDT --timeframe 1h --bars 200

# quality gates
.venv/bin/ruff check apex tests
.venv/bin/mypy
.venv/bin/pytest
```

## Layout

| Path | Layer |
| --- | --- |
| `apex/core/` | Foundation: types, enums, errors, time, identity, validation, serialization, logging, config, contracts, events |
| `apex/domain/` | Shared kernel: Bar, Tick, Signal, Order, Trade, Position, Portfolio, Probability, Risk, Money |
| `apex/contracts/` | Engine interface contracts (exchange, features, probability, risk, execution, optimizer) |
| `apex/kernel/` | DI container, module registry, health monitor, boot/shutdown orchestrator |
| `apex/storage/` | Storage platform: SQLite key/value (IStorage), bar repository, event archive |
| `apex/plugins/` | Plugin system: manifest contract + config-driven loader |
| `apex/data/` | Data platform: Toobit gateway, quality inspection, ingestion pipeline, replay |
| `apex/<layer>/` | Engine layers owned by Phases 4-15 (see each package docstring) |
| `config/` | The 12-file YAML configuration set (schema-gated at boot) |
| `docs/` | Architecture, conventions, phase tracker, and the source specification books |
| `tests/` | Unit + integration suites |

Dependencies point **downward only**:
`dashboard → api → services → engines → features → domain → core`.

## The rules this codebase lives by

The [Development Constitution](docs/specs/03_constitution.md) is binding. The
short version:

- **No repainting, no future leakage** — decisions consume confirmed bars only.
- **Determinism** — same input, same output; randomness only through seeds.
- **Everything is data** — no magic numbers; every tunable lives in `config/`.
- **No raw floats across boundaries** — concept types (`Price`, `Probability`,
  `Confidence`, ...) make cross-concept arithmetic a type error.
- **Immutability** — domain objects never mutate; change produces a new
  version in the same lineage.
- **Full traceability** — every object carries trace/correlation identity;
  every event is journaled before delivery and replayable.
- **No placeholders** — a layer either exists for real, with tests, or it
  does not exist yet.

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — layers, dependency rules, kernel lifecycle
- [docs/CONVENTIONS.md](docs/CONVENTIONS.md) — the distilled engineering constitution
- [docs/PHASES.md](docs/PHASES.md) — phase tracker and roadmap to Phase 15
- [docs/specs/](docs/specs/) — the eight authoritative specification books
