"""Canonical serialization and hashing.

Book II 4.20/4.21: every object serializes to a canonical form and has
a stable content hash used for audit, replay, caching and versioning.
Canonical JSON here means: sorted keys, no whitespace variance, no NaN
or infinity, Decimal as exact strings, enums as values, timestamps as
epoch milliseconds, UUIDs as strings.
"""

import hashlib
import json
import uuid
from dataclasses import fields, is_dataclass
from decimal import Decimal
from enum import Enum
from typing import Any

from apex.core.exceptions import SerializationError
from apex.core.time.timestamp import Timestamp

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


def to_canonical(value: object) -> JsonValue:
    """Convert a value into canonical JSON-compatible data.

    Supports the core object model: dataclasses (via their fields or a
    ``to_dict`` override), wrapper value types, enums, Decimal, UUID,
    Timestamp, mappings and sequences.
    """
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return _canonical_float(value)
    if isinstance(value, (Decimal, uuid.UUID)):
        return str(value)
    if isinstance(value, Timestamp):
        return value.epoch_ms
    if isinstance(value, Enum):
        return to_canonical(value.value)
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_canonical(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {_canonical_key(k): to_canonical(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, frozenset, set)):
        return _canonical_sequence(value)
    raise SerializationError(
        "unsupported type for canonical serialization",
        code="SER-001",
        details={"type": type(value).__name__},
    )


def _canonical_sequence(
    value: list[object] | tuple[object, ...] | frozenset[object] | set[object],
) -> list[JsonValue]:
    items = list(value)
    if isinstance(value, (set, frozenset)):
        items = sorted(items, key=repr)
    return [to_canonical(item) for item in items]


def _canonical_float(value: float) -> float:
    if value != value or value in (float("inf"), float("-inf")):
        raise SerializationError(
            "NaN and infinity are not serializable",
            code="SER-002",
            details={"value": repr(value)},
        )
    return value


def _canonical_key(key: object) -> str:
    if isinstance(key, str):
        return key
    if isinstance(key, Enum):
        raw = key.value
        if isinstance(raw, str):
            return raw
        return str(raw)
    raise SerializationError(
        "mapping keys must be strings or string-valued enums",
        code="SER-003",
        details={"key_type": type(key).__name__},
    )


def canonical_json(value: object) -> str:
    """Serialize to canonical JSON text (stable across runs)."""
    try:
        return json.dumps(
            to_canonical(value),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            ensure_ascii=False,
        )
    except (TypeError, ValueError) as exc:
        raise SerializationError(
            "canonical JSON encoding failed",
            code="SER-004",
            details={"reason": str(exc)},
        ) from exc


def content_hash(value: object) -> str:
    """SHA-256 hex digest of the canonical JSON form (Book II 4.21)."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def from_json(text: str) -> Any:
    """Parse JSON text, mapping failures onto the exception contract."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SerializationError(
            "JSON decoding failed",
            code="SER-005",
            details={"reason": str(exc), "position": exc.pos},
        ) from exc
