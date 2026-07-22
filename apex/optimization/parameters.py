"""Optimizable parameter space (Book V part 5: dynamic discovery).

The optimizer never hardcodes its search space: each optimizable
engine publishes ``OptimizableParameter`` descriptors and the search
stages sample within them. Sampling is deterministic (seeded) and
step-quantized so trials are reproducible bit-for-bit.
"""

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from apex.core.exceptions import ValidationError


@dataclass(frozen=True, slots=True, kw_only=True)
class OptimizableParameter:
    """One searchable parameter with its bounds and quantization."""

    name: str
    minimum: float
    maximum: float
    step: float
    integer: bool = False

    def __post_init__(self) -> None:
        if self.minimum >= self.maximum:
            raise ValidationError(
                "parameter minimum must be below maximum",
                code="OPT-001",
                details={"name": self.name},
            )
        if self.step <= 0:
            raise ValidationError(
                "parameter step must be positive",
                code="OPT-002",
                details={"name": self.name},
            )

    def quantize(self, value: float) -> float:
        """Clamp into bounds and snap to the step grid."""
        clamped = max(self.minimum, min(self.maximum, value))
        steps = round((clamped - self.minimum) / self.step)
        snapped = self.minimum + steps * self.step
        snapped = max(self.minimum, min(self.maximum, snapped))
        return float(round(snapped)) if self.integer else round(snapped, 10)

    @property
    def grid_size(self) -> int:
        """Number of points on the step grid."""
        return round((self.maximum - self.minimum) / self.step) + 1


def sample_random(
    space: Sequence[OptimizableParameter], rng: random.Random
) -> dict[str, float]:
    """One uniform random point on the quantized grid."""
    return {
        parameter.name: parameter.quantize(
            rng.uniform(parameter.minimum, parameter.maximum)
        )
        for parameter in space
    }


def sample_latin_hypercube(
    space: Sequence[OptimizableParameter], count: int, rng: random.Random
) -> list[dict[str, float]]:
    """Latin hypercube: each dimension stratified into ``count`` bins."""
    columns: dict[str, list[float]] = {}
    for parameter in space:
        span = parameter.maximum - parameter.minimum
        points = [
            parameter.quantize(
                parameter.minimum + span * (slot + rng.random()) / count
            )
            for slot in range(count)
        ]
        rng.shuffle(points)
        columns[parameter.name] = points
    return [
        {name: columns[name][index] for name in columns} for index in range(count)
    ]


def neighbors(
    space: Sequence[OptimizableParameter],
    center: Mapping[str, float],
    *,
    steps: int = 1,
) -> list[dict[str, float]]:
    """One-parameter-at-a-time neighbors of ``center`` on the grid."""
    out: list[dict[str, float]] = []
    for parameter in space:
        for direction in (-1, 1):
            candidate = dict(center)
            candidate[parameter.name] = parameter.quantize(
                center[parameter.name] + direction * steps * parameter.step
            )
            if candidate != dict(center):
                out.append(candidate)
    return out
