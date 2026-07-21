"""Event journal.

Book II 5.32: every event is recorded before it is published, and the
record is replayable (5.31). This is the in-process, bounded journal
used by the foundation; durable journaling arrives with the Storage
platform (Phase 3) behind the same append/replay semantics.
"""

from collections import deque
from collections.abc import Iterator

from apex.core.events.event import Event
from apex.core.exceptions import EventError


class EventJournal:
    """Bounded, append-only, sequenced event record."""

    def __init__(self, *, capacity: int) -> None:
        if capacity < 1:
            raise EventError(
                "journal capacity must be >= 1",
                code="EVT-010",
                details={"capacity": capacity},
            )
        self._capacity = capacity
        self._entries: deque[Event] = deque(maxlen=capacity)
        self._next_sequence = 0
        self._total_appended = 0

    @property
    def capacity(self) -> int:
        """Maximum retained entries (oldest evicted first)."""
        return self._capacity

    @property
    def total_appended(self) -> int:
        """Number of events ever appended (monotonic)."""
        return self._total_appended

    @property
    def next_sequence(self) -> int:
        """Sequence number the next appended event will receive."""
        return self._next_sequence

    def append(self, event: Event) -> Event:
        """Sequence and record an event; returns the sequenced event."""
        sequenced = event.with_sequence(self._next_sequence)
        self._entries.append(sequenced)
        self._next_sequence += 1
        self._total_appended += 1
        return sequenced

    def replay(self, *, from_sequence: int = 0) -> Iterator[Event]:
        """Iterate retained events with sequence >= ``from_sequence``."""
        for entry in self._entries:
            assert entry.sequence is not None
            if entry.sequence >= from_sequence:
                yield entry

    def latest(self) -> Event | None:
        """Most recently journaled event, if any is retained."""
        return self._entries[-1] if self._entries else None

    def __len__(self) -> int:
        return len(self._entries)
