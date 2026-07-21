"""Registry declarations for the order block / FVG family."""

from apex.core.versioning import SemanticVersion
from apex.features.orderblocks.engine import FAMILY, OrderBlockParams
from apex.features.registry import FeatureDefinition

_VERSION = SemanticVersion(1, 0, 0)

_DESCRIPTIONS: dict[str, str] = {
    "orderblocks.ob_long_confidence": (
        "Best bull order block by effective score: decayed confidence x proximity x retest"
    ),
    "orderblocks.ob_short_confidence": (
        "Best bear order block by effective score: decayed confidence x proximity x retest"
    ),
    "orderblocks.ob_long_freshness": "Age share remaining for the best bull order block",
    "orderblocks.ob_short_freshness": "Age share remaining for the best bear order block",
    "orderblocks.in_bull_ob": "Bar range overlaps the best bull order block",
    "orderblocks.in_bear_ob": "Bar range overlaps the best bear order block",
    "orderblocks.bull_ob_count": "Live bull order blocks (capped at max_live_objects)",
    "orderblocks.bear_ob_count": "Live bear order blocks (capped at max_live_objects)",
    "orderblocks.bull_breaker": "Bull order block mitigated this bar (breaker block)",
    "orderblocks.bear_breaker": "Bear order block mitigated this bar (breaker block)",
    "orderblocks.new_bull_fvg": "Qualified bullish fair value gap created this bar",
    "orderblocks.new_bear_fvg": "Qualified bearish fair value gap created this bar",
    "orderblocks.fvg_long_confidence": (
        "Best bull FVG by score: decayed confidence x proximity, discounted by fill"
    ),
    "orderblocks.fvg_short_confidence": (
        "Best bear FVG by score: decayed confidence x proximity, discounted by fill"
    ),
    "orderblocks.in_bull_fvg": "Bar range overlaps the best bull fair value gap",
    "orderblocks.in_bear_fvg": "Bar range overlaps the best bear fair value gap",
    "orderblocks.bull_fvg_count": "Live bull fair value gaps (capped at max_live_objects)",
    "orderblocks.bear_fvg_count": "Live bear fair value gaps (capped at max_live_objects)",
    "orderblocks.ifvg_bull": "Bear FVG inverted this bar (close through its top)",
    "orderblocks.ifvg_bear": "Bull FVG inverted this bar (close through its bottom)",
    "orderblocks.bpr_bull": "Balanced price range: new bull FVG after a bear FVG last bar",
    "orderblocks.bpr_bear": "Balanced price range: new bear FVG after a bull FVG last bar",
}


def orderblock_definitions(params: OrderBlockParams) -> tuple[FeatureDefinition, ...]:
    """Build the registry declarations for the OB/FVG family."""
    defaults = {
        "pivot_lookback": params.pivot_lookback,
        "atr_length": params.atr_length,
        "displacement_body_atr": params.displacement_body_atr,
        "break_decay": params.break_decay,
        "scan_lookback": params.scan_lookback,
        "scan_cap": params.scan_cap,
        "ob_decay": params.ob_decay,
        "fvg_decay": params.fvg_decay,
        "max_live_objects": params.max_live_objects,
        "max_object_age": params.max_object_age,
        "min_fvg_size_atr": params.min_fvg_size_atr,
        "volume_sma_length": params.volume_sma_length,
        "range_sma_length": params.range_sma_length,
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
