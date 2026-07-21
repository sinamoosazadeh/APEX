# apex.kernel — Kernel

The platform's internal operating system (Book II 3.5). `ServiceContainer`
(explicit type-keyed DI with circular-resolution detection), `ModuleRegistry`
(deterministic topological start order, cycle rejection), `HealthMonitor`
(worst-state-wins aggregation), `Kernel` (boot sequence per 29.21, reverse
shutdown per 29.22, lifecycle events journaled).

Entrypoint: `python -m apex` / `python -m apex --check`.

Tests: `tests/unit/kernel/`, `tests/integration/test_boot.py`.
