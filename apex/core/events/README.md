# apex.core.events — Event Platform

Book II ch. 5 / 29.7. `Event` (immutable envelope with trace, correlation,
causation, category, priority, schema version), `EventJournal` (append-only,
sequence-assigning, replayable; journal-before-publish), `InProcessEventBus`
(deterministic sequential dispatch, handler failure isolation, optional
fail-fast), `catalog` (declared system event types).

Tests: `tests/unit/core/test_events.py`.
