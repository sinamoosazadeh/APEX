"""Registry declarations for the SMT divergence family."""

from apex.core.versioning import SemanticVersion
from apex.features.registry import FeatureDefinition
from apex.features.smt.engine import FAMILY, SmtParams

_VERSION = SemanticVersion(1, 0, 0)

_DESCRIPTIONS: dict[str, str] = {
    "smt.bull_divergence": "Fresh opposing swing lows against the correlated reference",
    "smt.bear_divergence": "Fresh opposing swing highs against the correlated reference",
    "smt.correlation": "Rolling correlation of log returns with the reference",
    "smt.correlation_quality": "AICE correlation quality: threshold-scaled and dynamics-damped",
    "smt.bull_confidence": "Decayed pool bumped to correlation quality on bull divergences",
    "smt.bear_confidence": "Decayed pool bumped to correlation quality on bear divergences",
    "smt.reference_available": "A closed reference bar was available for this chart bar",
}


def smt_definitions(params: SmtParams) -> tuple[FeatureDefinition, ...]:
    """Build the registry declarations for the SMT family."""
    defaults = {
        "pivot_lookback": params.pivot_lookback,
        "max_pivot_age": params.max_pivot_age,
        "correlation_length": params.correlation_length,
        "correlation_minimum": params.correlation_minimum,
        "correlation_slope_length": params.correlation_slope_length,
        "decay_rate": params.decay_rate,
        "min_score": params.min_score,
    }
    return tuple(
        FeatureDefinition(
            name=name,
            family=FAMILY,
            description=description,
            version=_VERSION,
            default_params=defaults,
        )
        for name, description in _DESCRIPTIONS.items()
    )
