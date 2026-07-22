"""Registry declarations for the statistical family."""

from apex.core.versioning import SemanticVersion
from apex.features.registry import FeatureDefinition
from apex.features.statistical.engine import FAMILY, StatisticalParams

# 1.1.0: candle direction added for the probability platform's
# effort-vs-result penalty (AICE lines 1633, 2750).
_VERSION = SemanticVersion(1, 1, 0)

_DESCRIPTIONS: dict[str, str] = {
    "statistical.adx": "Average directional index (Wilder DMI)",
    "statistical.efficiency_ratio": "Kaufman efficiency: net change over traveled path",
    "statistical.hurst_proxy": "Variance-ratio persistence proxy around 0.5",
    "statistical.return_entropy": "Entropy of the scaled normalized absolute return",
    "statistical.slope_quality": "Absolute correlation of price with time",
    "statistical.volatility_clustering": "Autocorrelation of absolute returns",
    "statistical.trend_confidence": "Five-term weighted regime evidence",
    "statistical.is_trending": "Trend confidence at or above the trending threshold",
    "statistical.is_ranging": "Trend confidence below the ranging threshold",
    "statistical.market_entropy": "Composite disorder: entropy, transition, compression",
    "statistical.direction": "Candle direction: up +1, down -1, flat 0",
    "statistical.persistence": "Share of the previous four bars agreeing in direction",
    "statistical.body_rank": "Percent rank of the candle body over the norm window",
    "statistical.impulse_efficiency": "Three-bar displacement over the traveled range",
    "statistical.dna_bull": "Weighted bullish candle anatomy composite",
    "statistical.dna_bear": "Weighted bearish candle anatomy composite",
    "statistical.sequence_bull_bias": "Positive share of the five-bar direction sum",
    "statistical.sequence_bear_bias": "Negative share of the five-bar direction sum",
    "statistical.direction_flip_bull": "Down-to-up flip on a high-rank body",
    "statistical.direction_flip_bear": "Up-to-down flip on a high-rank body",
    "statistical.doji": "Body within a tenth of the bar range",
    "statistical.bull_engulfing": "Up body engulfing the previous down body",
    "statistical.bear_engulfing": "Down body engulfing the previous up body",
    "statistical.pin_bull": "Lower wick over twice the body with a small upper wick",
    "statistical.pin_bear": "Upper wick over twice the body with a small lower wick",
    "statistical.hammer": "Dominant lower wick with a strong close location",
    "statistical.shooting_star": "Dominant upper wick with a weak close location",
    "statistical.wavetrend": "WaveTrend oscillator (deviation-normalized channel)",
    "statistical.wavetrend_bull": "WaveTrend above its signal average",
    "statistical.stc": "Schaff trend cycle (double-stochastic MACD), 0-100",
    "statistical.cci": "Commodity channel index of the typical price",
    "statistical.kinetic_long": "AICE kin_long: WT/STC/CCI cross-state composite",
    "statistical.kinetic_short": "AICE kin_short: WT/STC/CCI cross-state composite",
}


def statistical_definitions(params: StatisticalParams) -> tuple[FeatureDefinition, ...]:
    """Build the registry declarations for the statistical family."""
    defaults = {
        "atr_length": params.atr_length,
        "adx_length": params.adx_length,
        "adx_trend_threshold": params.adx_trend_threshold,
        "efficiency_length": params.efficiency_length,
        "entropy_window": params.entropy_window,
        "normalization_window": params.normalization_window,
        "rank_window": params.rank_window,
        "range_sma_length": params.range_sma_length,
        "wavetrend_channel": params.wavetrend_channel,
        "wavetrend_average": params.wavetrend_average,
        "stc_cycle": params.stc_cycle,
        "stc_fast": params.stc_fast,
        "stc_slow": params.stc_slow,
        "cci_length": params.cci_length,
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
