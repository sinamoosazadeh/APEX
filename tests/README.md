# tests

`unit/` mirrors the package layout (core, domain, kernel); `integration/`
boots the real kernel against the real config set and exercises the CLI.
Async paths are tested with `asyncio.run` inside synchronous tests; time uses
`ManualClock` — no test depends on the wall clock.

Run: `.venv/bin/pytest`
