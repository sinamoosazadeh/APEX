"""Validation splits and resampling (Book V part 5).

Deterministic window builders (walk-forward, rolling, expanding) and
the seeded Monte Carlo bootstrap over a simulated R series. Every
split is expressed as index ranges over the snapshot window so the
same evaluation core scores each side.
"""

import random
from dataclasses import dataclass

from apex.core.exceptions import ValidationError


@dataclass(frozen=True, slots=True, kw_only=True)
class Split:
    """A train/test pair of half-open index ranges."""

    train_start: int
    train_end: int
    test_start: int
    test_end: int


def walk_forward_splits(total: int, folds: int, test_share: float) -> list[Split]:
    """Anchored-train walk-forward folds marching through the window."""
    _validate(total, folds, test_share)
    test_size = max(int(total * test_share), 1)
    stride = max((total - test_size) // folds, 1)
    splits: list[Split] = []
    for fold in range(folds):
        test_start = min(stride * (fold + 1), total - test_size)
        splits.append(
            Split(
                train_start=0,
                train_end=test_start,
                test_start=test_start,
                test_end=min(test_start + test_size, total),
            )
        )
    return splits


def rolling_splits(total: int, folds: int, test_share: float) -> list[Split]:
    """Fixed-width rolling train windows with adjacent test windows."""
    _validate(total, folds, test_share)
    test_size = max(int(total * test_share), 1)
    train_size = max(total - folds * test_size, test_size)
    splits: list[Split] = []
    for fold in range(folds):
        test_start = min(train_size + fold * test_size, total - test_size)
        splits.append(
            Split(
                train_start=max(test_start - train_size, 0),
                train_end=test_start,
                test_start=test_start,
                test_end=min(test_start + test_size, total),
            )
        )
    return splits


def expanding_splits(total: int, folds: int, test_share: float) -> list[Split]:
    """Expanding train windows (anchored) - alias shape of walk-forward
    with growing trains, kept explicit per the Book V protocol."""
    return walk_forward_splits(total, folds, test_share)


def monte_carlo_positive_share(
    r_series: list[float], *, resamples: int, seed: int
) -> float:
    """Share of seeded bootstrap resamples with positive total R."""
    if not r_series:
        return 0.0
    rng = random.Random(seed)
    positive = 0
    for _ in range(resamples):
        total = sum(rng.choice(r_series) for _ in r_series)
        if total > 0:
            positive += 1
    return positive / resamples


def _validate(total: int, folds: int, test_share: float) -> None:
    if total < 4:
        raise ValidationError(
            "validation window too small", code="OPT-010", details={"total": total}
        )
    if folds < 1:
        raise ValidationError("folds must be positive", code="OPT-011", details={})
    if not 0.0 < test_share < 1.0:
        raise ValidationError(
            "test share must be in (0, 1)", code="OPT-012", details={}
        )
