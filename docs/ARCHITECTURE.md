# APEX Architecture (as built)

This document describes the architecture **as implemented so far** (Phases 0-1
plus the Shared Kernel / Contracts / Event Platform stages of the Master
Repository Blueprint). The authoritative full design lives in
[docs/specs/](specs/) — Book I (architecture), Book II (migration &
implementation), Book III (constitution).

## Layer map

```
dashboard → api → services → engines → features → domain → core
```

Dependencies point **downward only** (Book II 3.25). Circular dependencies and
wildcard imports are forbidden and enforced by review + ruff.

| Package | Status | Contents |
| --- | --- | --- |
| `apex/core` | ✅ built | Foundation: constants, enums, exceptions (coded), identity, time, metadata, validation, serialization, types, result, base object, context, versioning, logging, config, infra contracts, event platform |
| `apex/domain` | ✅ built | Shared kernel: Money, Bar, Tick, Signal, Order, Trade, Feature, ProbabilityAssessment, RiskAssessment, Position, PortfolioSnapshot, StateSnapshot |
| `apex/contracts` | ✅ built | Engine interfaces: IExchange, IFeatureEngine, IProbabilityEngine, IRiskEngine, IExecutionEngine, IOptimizer |
| `apex/kernel` | ✅ built | ServiceContainer (DI), ModuleRegistry (topological start order), HealthMonitor, Kernel (boot/shutdown) |
| everything else | 📋 scaffolded | Owned by Phases 2-15; docstring-only packages, no fake logic |

### Mapping decision: spec tree → repository

Book II 3.3 lists the layers directly under `APEX/`. In this repository the
**code layers** live under the importable package `apex/` (so imports read
`from apex.core.types import Price`), while **project directories** (`config/`,
`tests/`, `docs/`, `tools/`, `scripts/`, `resources/`) stay at the repo root.
This preserves the spec's layer structure and gives standard Python packaging.

### Placement decision: engine contracts

Book II 3.4 puts "Interfaces/Contracts" in Core, but engine interfaces are
typed against Domain objects, and Core must never import Domain. Resolution:

- **Infrastructure contracts** (IClock, ILogger, IEventBus, IStorage,
  IRepository, IModule, IHealthCheck) → `apex/core/contracts` (core-only types)
- **Engine contracts** (IExchange, IFeatureEngine, ...) → `apex/contracts`
  (sits between domain and engines)

## The object model (Book II ch. 4)

- **Concept types, not raw floats** — `Price`, `Volume`, `Quantity` (Decimal,
  exact) and `Probability`, `Confidence`, `Weight`, `Entropy`, ... (bounded
  floats). Cross-concept arithmetic raises `VAL-033`. NaN/∞ can never enter.
- **BaseObject** — every entity carries `object_id` (UUID), `lineage_id`,
  `object_version`, `created_at`, `metadata` (trace/correlation/causation/
  session/execution ids). `evolve()` produces version N+1 in the same lineage
  (no overwrites, ever); `clone()` starts a new lineage; equality is semantic;
  `content_hash()` is a stable SHA-256 of canonical content.
- **Result[T]** — operations return data/error/warnings/duration, never a bare
  boolean. **HealthState** is a 4-state enum, never `healthy=True`.
- **Coded errors** — every exception is an `ApexError` subclass with a
  `ABC-123` code and machine-readable details.
- **Time** — `Timestamp` is UTC epoch-milliseconds. The only OS-clock call in
  the codebase is inside `SystemClock`; everything else receives an injected
  `Clock` (replay/simulation ready). `ManualClock` never moves backwards.

## Event platform (Book II ch. 5, 29.7)

- `Event` envelope: id, dotted `event_type`, category (10), priority (5),
  source/destination, payload (canonical-JSON-safe, checked at construction),
  trace/correlation/causation ids, schema version, bus-assigned `sequence`.
- `EventJournal` — bounded, append-only; **journals before delivery** (5.32);
  monotonic sequencing = deterministic total order (5.30); replayable (5.31).
- `InProcessEventBus` — delivers sequentially in subscription order
  (determinism over throughput); handler failures are isolated, logged and
  surfaced as `system.bus.handler_failed` events; optional `fail_fast` mode.
- `catalog.py` — event types are declared, never invented at call sites.

## Kernel lifecycle (Book II 29.21/29.22)

```
boot:      Configuration → Logger → DI container → Event Bus → Modules (topological) → Health → Ready
shutdown:  Modules (reverse order) → journal flush → bus close → stopped
```

- Boot **fails** on any config violation (missing file, wrong `schema_version`,
  bad enum value, deterministic ids without seed): Book II 5.18.
- Engine platforms join as `IModule` implementations registered on
  `kernel.modules`; the orchestrator does not change as phases land.
- `python -m apex --check` boots and exits — the CI/deployment gate.

## Configuration (Constitution 3.7)

Twelve YAML files in `config/`, each schema-gated. `system.yaml` and
`logging.yaml` are deep-validated now; the ten phase-owned files are
shape+version-gated until their phases ship their deep schemas. Scalar
overrides: `APEX__<FILE>__<KEY>[__<NESTED>]` environment variables. The full
config set is content-hashed into every session (`SessionContext.config_hash`)
for reproducibility.

## Determinism inventory

| Source of nondeterminism | Control |
| --- | --- |
| Wall clock | Injected `Clock`; `ManualClock` for replay/tests |
| Randomness | `IdProvider(seed=...)` (Constitution 3.24); no other RNG exists yet |
| Event ordering | Journal sequence + sequential dispatch |
| Dict/iteration order | Canonical JSON sorts keys; module start order sorts ties alphabetically |
| Float drift | Decimal for market magnitudes; NaN/∞ rejected everywhere |
