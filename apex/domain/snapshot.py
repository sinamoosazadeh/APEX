"""State snapshot contract (Book II 4.31).

Every mutable state in APEX can be captured as an immutable,
content-hashed snapshot for persistence, audit and restore.
"""

from dataclasses import dataclass

from apex.core.base import BaseObject
from apex.core.exceptions import ValidationError
from apex.core.serialization import JsonValue, content_hash
from apex.core.time.timestamp import Timestamp
from apex.core.validation import ensure_not_empty


@dataclass(frozen=True, slots=True, kw_only=True)
class StateSnapshot(BaseObject):
    """Immutable capture of one mutable state object."""

    state_type: str
    taken_at: Timestamp
    payload: dict[str, JsonValue]
    payload_hash: str = ""

    def _validate(self) -> None:
        ensure_not_empty(self.state_type, "state_type")
        expected = content_hash(self.payload)
        if not self.payload_hash:
            object.__setattr__(self, "payload_hash", expected)
        elif self.payload_hash != expected:
            raise ValidationError(
                "snapshot payload hash mismatch",
                code="VAL-110",
                details={"expected": expected, "found": self.payload_hash},
            )
