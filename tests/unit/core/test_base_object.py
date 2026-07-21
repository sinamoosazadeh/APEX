"""BaseObject: identity, versioning, lineage, semantic equality."""

from dataclasses import dataclass

import pytest
from apex.core.base import BaseObject
from apex.core.exceptions import ValidationError
from apex.core.time.timestamp import Timestamp
from apex.core.validation import ensure_not_empty

T0 = Timestamp(epoch_ms=1_750_000_000_000)
T1 = T0.add_ms(60_000)


@dataclass(frozen=True, slots=True, kw_only=True)
class Note(BaseObject):
    """Minimal concrete object for exercising the base model."""

    text: str

    def _validate(self) -> None:
        ensure_not_empty(self.text, "text")


class TestBaseObject:
    def test_lineage_defaults_to_object_id(self) -> None:
        note = Note(created_at=T0, text="hello")
        assert note.lineage_id == note.object_id
        assert note.object_version == 1

    def test_validation_hook_runs(self) -> None:
        with pytest.raises(ValidationError):
            Note(created_at=T0, text="")

    def test_evolve_increments_version_and_keeps_lineage(self) -> None:
        v1 = Note(created_at=T0, text="hello")
        v2 = v1.evolve(created_at=T1, text="hello world")
        assert v2.object_version == 2
        assert v2.lineage_id == v1.lineage_id
        assert v2.object_id != v1.object_id
        assert v1.text == "hello"  # v1 untouched: no overwrite, ever

    def test_evolve_rejects_identity_tampering(self) -> None:
        v1 = Note(created_at=T0, text="hello")
        with pytest.raises(ValidationError):
            v1.evolve(created_at=T1, object_version=99)

    def test_evolved_object_is_revalidated(self) -> None:
        v1 = Note(created_at=T0, text="hello")
        with pytest.raises(ValidationError):
            v1.evolve(created_at=T1, text="")

    def test_clone_starts_new_lineage(self) -> None:
        original = Note(created_at=T0, text="hello")
        copy = original.clone(created_at=T1)
        assert copy.lineage_id != original.lineage_id
        assert copy.object_version == 1
        assert copy.semantically_equals(original)

    def test_semantic_equality_ignores_identity(self) -> None:
        left = Note(created_at=T0, text="same")
        right = Note(created_at=T1, text="same")
        assert left.semantically_equals(right)
        assert left != right  # dataclass equality still identity-aware

    def test_content_hash_tracks_content_only(self) -> None:
        left = Note(created_at=T0, text="same")
        right = Note(created_at=T1, text="same")
        other = Note(created_at=T0, text="different")
        assert left.content_hash() == right.content_hash()
        assert left.content_hash() != other.content_hash()

    def test_to_dict_includes_type_and_envelope(self) -> None:
        note = Note(created_at=T0, text="hello")
        data = note.to_dict()
        assert data["object_type"] == "Note"
        assert data["object_version"] == 1
        assert data["text"] == "hello"

    def test_version_floor(self) -> None:
        with pytest.raises(ValidationError):
            Note(created_at=T0, text="x", object_version=0)
