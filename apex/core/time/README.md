# apex.core.time — Time System

Book II 4.14-4.16. `Timestamp` (UTC epoch-milliseconds, exact integer math),
`Clock` protocol, `SystemClock` (the single sanctioned OS-clock call site in
the entire codebase) and `ManualClock` (deterministic; never moves backwards)
for tests, replay and simulation.

Tests: `tests/unit/core/test_time.py`.
