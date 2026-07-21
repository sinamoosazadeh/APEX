"""Identity system.

Book II 4.7: every object carries a globally unique UUID, never a local
id. Constitution 3.24: no unseeded randomness - the provider supports a
deterministic mode (seeded) for replay and testing, and an entropy mode
for live operation. The provider is injected (Constitution 3.8), never
reached through globals by business logic.
"""

import uuid
from random import Random
from typing import Final

# UUID namespace for deriving stable, content-addressed identifiers.
APEX_NAMESPACE: Final[uuid.UUID] = uuid.uuid5(uuid.NAMESPACE_DNS, "apex.platform")


class IdProvider:
    """Source of unique identifiers.

    In entropy mode (default) ids come from ``uuid4``. In deterministic
    mode ids are derived from a seeded PRNG so a replayed run produces
    the identical id sequence (Constitution 3.27 reproducibility).
    """

    def __init__(self, *, seed: int | None = None) -> None:
        self._seed: Final[int | None] = seed
        self._rng: Random | None = Random(seed) if seed is not None else None

    @property
    def is_deterministic(self) -> bool:
        """Whether this provider produces a reproducible id sequence."""
        return self._rng is not None

    def new_id(self) -> uuid.UUID:
        """Return the next unique identifier."""
        if self._rng is not None:
            return uuid.UUID(int=self._rng.getrandbits(128), version=4)
        return uuid.uuid4()

    def derive_id(self, name: str) -> uuid.UUID:
        """Return a stable id derived from ``name`` (content addressing)."""
        return uuid.uuid5(APEX_NAMESPACE, name)


def new_entropy_id() -> uuid.UUID:
    """Module-level convenience for default object identity.

    Domain object factories accept an :class:`IdProvider` for
    deterministic runs; this helper backs the non-deterministic default.
    """
    return uuid.uuid4()
