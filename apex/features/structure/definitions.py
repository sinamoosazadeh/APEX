"""Registry declarations for the structure family."""

from apex.core.versioning import SemanticVersion
from apex.features.registry import FeatureDefinition
from apex.features.structure.engine import FAMILY, StructureParams

# 1.1.0: internal/external struct-pack biases added for the
# probability platform's ev_mtf evidence channel (AICE lines 1084-1085).
_VERSION = SemanticVersion(1, 1, 0)

_DESCRIPTIONS: dict[str, str] = {
    "structure.trend_direction": "Structure trend state: -1 bearish, 0 undefined, 1 bullish",
    "structure.bos_up": "Break of structure above the last swing high (with-trend)",
    "structure.bos_down": "Break of structure below the last swing low (with-trend)",
    "structure.choch_up": "Change of character: counter-trend break above the last swing high",
    "structure.choch_down": "Change of character: counter-trend break below the last swing low",
    "structure.break_quality": "Latest break quality, decayed per bar since the break",
    "structure.displacement_body_atr": "Candle body measured in ATR units",
    "structure.is_displacement": "Body exceeds the displacement threshold",
    "structure.dealing_range_position": "Close position inside the swing dealing range [0, 1]",
    "structure.in_premium": "Close above dealing range equilibrium",
    "structure.in_discount": "Close below dealing range equilibrium",
    "structure.in_ote_long": "Close inside the long optimal trade entry window",
    "structure.in_ote_short": "Close inside the short optimal trade entry window",
    "structure.sweep_high": "Wick above the last swing high with close back below",
    "structure.sweep_low": "Wick below the last swing low with close back above",
    "structure.equal_highs": "New swing high within ATR tolerance of the previous one",
    "structure.equal_lows": "New swing low within ATR tolerance of the previous one",
    "structure.swing_high_distance": "Signed distance from close to the last swing high, in ATR",
    "structure.swing_low_distance": "Signed distance from close to the last swing low, in ATR",
    "structure.internal_bias": "Internal-scale struct-pack bias: pivot break or EMA side",
    "structure.external_bias": "External-scale struct-pack bias: pivot break or EMA side",
}


def structure_definitions(params: StructureParams) -> tuple[FeatureDefinition, ...]:
    """Build the registry declarations for the structure family."""
    defaults = {
        "pivot_lookback": params.pivot_lookback,
        "atr_length": params.atr_length,
        "displacement_body_atr": params.displacement_body_atr,
        "equal_tolerance_atr": params.equal_tolerance_atr,
        "break_decay": params.break_decay,
        "internal_lookback": params.internal_lookback,
        "external_lookback": params.external_lookback,
        "bias_ema_length": params.bias_ema_length,
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
