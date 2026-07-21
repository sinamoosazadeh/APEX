"""Base object model.

Book II 4.6-4.10 and 4.20-4.23: every domain object is immutable,
carries a global UUID, a lineage with explicit versions (change means a
new version, never an overwrite), metadata, a stable content hash and
semantic equality. Subclasses implement ``_validate`` to make invalid
state unrepresentable.
"""

import uuid
from dataclasses import dataclass, field, fields, replace
from typing import Any, Self

from apex.core.exceptions import ValidationError
from apex.core.identity import new_entropy_id
from apex.core.metadata import ObjectMetadata
from apex.core.serialization import JsonValue, content_hash, to_canonical
from apex.core.time.timestamp import Timestamp

# Fields that define an object's identity envelope rather than its
# semantic content; excluded from content hashing and semantic equality.
IDENTITY_FIELDS: frozenset[str] = frozenset(
    {"object_id", "lineage_id", "object_version", "created_at", "metadata"}
)


@dataclass(frozen=True, slots=True, kw_only=True)
class BaseObject:
    """Immutable, identifiable, versioned, hashable platform object.

    Attributes:
        object_id: unique id of this concrete instance (this version).
        lineage_id: stable id shared by all versions of the object.
        object_version: 1-based version within the lineage (4.8).
        created_at: instant this version was created (from a Clock).
        metadata: traceability envelope (4.9).
    """

    created_at: Timestamp
    object_id: uuid.UUID = field(default_factory=new_entropy_id)
    lineage_id: uuid.UUID | None = None
    object_version: int = 1
    metadata: ObjectMetadata = field(default_factory=ObjectMetadata)

    def __post_init__(self) -> None:
        if self.lineage_id is None:
            object.__setattr__(self, "lineage_id", self.object_id)
        if self.object_version < 1:
            raise ValidationError(
                "object_version must be >= 1",
                code="VAL-050",
                details={"object_version": self.object_version},
            )
        self._validate()

    def _validate(self) -> None:
        """Subclass hook; raise :class:`ValidationError` on invalid state."""

    # --- Versioning (4.8) ----------------------------------------------------

    def evolve(self, *, created_at: Timestamp, **changes: Any) -> Self:
        """Return the next version of this object with ``changes`` applied.

        The lineage id is preserved, the version increments and the new
        instance receives a fresh object id. Identity fields cannot be
        overridden.
        """
        illegal = IDENTITY_FIELDS.intersection(changes)
        if illegal:
            raise ValidationError(
                "identity fields cannot be evolved directly",
                code="VAL-051",
                details={"fields": ", ".join(sorted(illegal))},
            )
        return replace(
            self,
            object_id=new_entropy_id(),
            object_version=self.object_version + 1,
            created_at=created_at,
            **changes,
        )

    def clone(self, *, created_at: Timestamp) -> Self:
        """Return a copy that starts a brand-new lineage (4.23)."""
        new_id = new_entropy_id()
        return replace(
            self,
            object_id=new_id,
            lineage_id=new_id,
            object_version=1,
            created_at=created_at,
        )

    # --- Serialization, hashing, equality (4.20-4.22) -------------------------

    def semantic_content(self) -> dict[str, JsonValue]:
        """Canonical content excluding the identity envelope."""
        return {
            f.name: to_canonical(getattr(self, f.name))
            for f in fields(self)
            if f.name not in IDENTITY_FIELDS
        }

    def to_dict(self) -> dict[str, JsonValue]:
        """Full canonical form including the identity envelope."""
        result = {f.name: to_canonical(getattr(self, f.name)) for f in fields(self)}
        result["object_type"] = type(self).__name__
        return result

    def content_hash(self) -> str:
        """Stable hash of semantic content (audit, replay, caching)."""
        return content_hash(self.semantic_content())

    def semantically_equals(self, other: "BaseObject") -> bool:
        """Semantic equality: same type and same content (4.22)."""
        if type(other) is not type(self):
            return False
        return self.semantic_content() == other.semantic_content()
