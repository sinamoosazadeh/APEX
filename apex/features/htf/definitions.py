"""Registry declarations for the HTF context family."""

from apex.core.versioning import SemanticVersion
from apex.features.htf.engine import FAMILY, HtfParams
from apex.features.registry import FeatureDefinition

_VERSION = SemanticVersion(1, 0, 0)

_DESCRIPTIONS: dict[str, str] = {
    "htf.macro1_bias": "Structure bias of the first macro timeframe (pivot break or EMA side)",
    "htf.macro2_bias": "Structure bias of the second macro timeframe (pivot break or EMA side)",
    "htf.alignment": "Sum of both macro biases: -2 (bearish) to +2 (bullish)",
    "htf.bull_context": "Macro alignment is net bullish",
    "htf.bear_context": "Macro alignment is net bearish",
    "htf.confidence": "Absolute macro alignment over two (agreement strength)",
    "htf.in_discount": "Close below the macro-1 pivot midpoint",
    "htf.in_premium": "Close above the macro-1 pivot midpoint",
}


def htf_definitions(params: HtfParams) -> tuple[FeatureDefinition, ...]:
    """Build the registry declarations for the HTF family."""
    defaults = {
        "pivot_lookback": params.pivot_lookback,
        "ema_length": params.ema_length,
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
