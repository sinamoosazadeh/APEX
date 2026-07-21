# APEX Engineering Conventions

Distilled from the [Development Constitution](specs/03_constitution.md)
(Book III). The Constitution is binding; on conflict the priority order is
**Book III → Book I → Book II → AICE logic** (Constitution, mission section).

## Language & typing

- Python **3.13+** only; no deprecated features (3.3).
- Everything typed; no function without hints; `Any` only in genuinely
  exceptional cases (3.4). mypy runs in `strict` mode and must be clean.
- Data objects are **frozen dataclasses** (`frozen=True, slots=True`);
  only explicitly-named State objects may mutate (3.5, Book II 4.10/4.11).
- No string literals in business logic — use enums (3.6).
- No raw floats across module boundaries — use the concept types in
  `apex.core.types`.

## Configuration & dependencies

- **No magic numbers.** Every threshold/weight/window/timeout lives in
  `config/*.yaml` (3.7). Structural invariants live in `apex/core/constants.py`.
- **Everything is injected** — logger, config, clock, id provider included
  (3.8). No class constructs its own dependencies; use `ServiceContainer`.
- Dependencies point downward only; circular imports forbidden (2.11, 3.23).
- No wildcard imports (3.23).

## Determinism & time

- Same input → same output. Randomness only through a seeded provider (3.24).
- Never call `datetime.now()` / `time.time()` — inject a `Clock` (3.25).
  The only sanctioned OS-clock call site is `apex/core/time/clock.py`.
- All timestamps are UTC epoch-milliseconds (Book II 4.16).
- **No repainting / no future leakage**: decision code consumes confirmed bars
  only — enforce with `Bar.require_closed()` (Master Prompt 3.2).

## Numerical stability (3.26)

- NaN, infinity, division-by-zero are contract violations, rejected centrally
  (`apex.core.validation`, `apex.core.serialization`).
- Market magnitudes (price/volume/quantity/money) use `Decimal`, parsed from
  exact representations — `parse()` rejects float.

## Errors, results, logging

- Never raise bare `Exception` — use the `ApexError` hierarchy with `ABC-123`
  codes and machine-readable details (Book II 4.25/4.26).
- Never return bare booleans for outcomes — return `Result[T]` (Book II 4.30).
- Health is a 4-state enum, never a boolean (Book II 4.28).
- Logging is structured from day one: event name + typed fields, no free-form
  strings (3.13, Book II 5.24). Log every important operation, decision and
  failure.

## Code shape

- Naming: `PascalCase` classes, `snake_case` functions/variables,
  `UPPER_CASE` constants, `_leading` private (3.21).
- Files ≤ 800 lines (target 400); functions ≤ 50 lines (target 20);
  one responsibility per class (3.20/3.22, Book II 3.29-3.31).
- Every class documents purpose, inputs, outputs, dependencies, constraints
  (3.19). Every package carries a README and tests (Book II 3.32).
- All network/database/websocket I/O is async; no blocking calls inside async
  code (3.14).

## Contracts (Book II ch. 5)

- Contract first: interfaces and schemas before implementations (5.2, 29.6).
- Modules communicate **only** through versioned contracts and official
  interfaces; internals are never reached across module boundaries (5.38).
- Every interface declares a stability level (`@stability(...)`, 5.36);
  contracts are versioned and evolve backward-compatibly (5.26).
- Events: journal before publish, deterministic ordering, replayable
  (5.30-5.32); event types come from catalogs, never inline strings.

## Absolute prohibitions (Master Prompt §3, Constitution 2.5)

- No pseudo-code, no placeholders, no TODOs, no "assume implementation",
  no simulation-only logic in committed code.
- No repainting, no forward-looking references, no hidden future bias.
- No unexplainable decisions: every signal must expose why it triggered,
  what passed, what failed, and its probability breakdown.

## Workflow (Constitution §4)

- Phased development (Phase 0-15); a phase is done only when tests pass,
  docs are updated and quality gates are green (4.15). The project must
  remain runnable at the end of every phase (4.6).
- Branches: `main` (protected), `develop`, `feature/*`, `research/*`,
  `optimizer/*`, `hotfix/*`, `release/*` (4.14). No direct work on `main`.
- One purpose per commit; tests must pass before commit (4.13).

## Quality gates

```bash
.venv/bin/ruff check apex tests   # style, imports, naming, complexity
.venv/bin/mypy                    # strict typing
.venv/bin/pytest                  # unit + integration
.venv/bin/python -m apex --check  # boot gate
```

All four must pass before any merge.
