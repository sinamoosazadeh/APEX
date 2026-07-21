"""Registry declarations for the volume & normalization family."""

from apex.core.versioning import SemanticVersion
from apex.features.registry import FeatureDefinition
from apex.features.volume.engine import FAMILY, VolumeParams

_VERSION = SemanticVersion(1, 0, 0)

_DESCRIPTIONS: dict[str, str] = {
    "volume.rvol": "Relative volume: bar volume over its rolling mean",
    "volume.volume_available": "Exchange reported nonzero volume for this bar",
    "volume.atr_percentile": "Percent rank of ATR over the rank window",
    "volume.volatility_width": "ATR over its own rolling mean (regime width)",
    "volume.volatility_factor": "Discrete volatility multiplier: wide 1.3 / narrow 0.75",
    "volume.forecast_ratio": "EWMA volatility of log returns over historical deviation",
    "volume.adaptive_atr_ratio": "Adaptive ATR risk multiple from forecast and rank",
    "volume.vwap_deviation_atr": "Close distance from the UTC-day VWAP in ATR units",
    "volume.vwap_deviation_z": "Winsorized z-score of the VWAP deviation",
    "volume.expansion": "Bar range above 1.5x its rolling mean",
    "volume.compression": "Bar range below 0.6x its rolling mean",
    "volume.aggression": "Net delta approximation over mean volume (buy minus sell)",
    "volume.rolling_delta_bias": "Rolling sum of the net delta approximation",
    "volume.cumulative_delta_bias": "Cumulative delta minus its EMA baseline",
    "volume.absorption_buy": "High RVOL, dominant lower wick, strong close, narrow bar",
    "volume.absorption_sell": "High RVOL, dominant upper wick, weak close, narrow bar",
    "volume.spike": "Volume above twice its rolling mean",
    "volume.selling_climax": "Volume spike with dominant lower wick and positive delta",
    "volume.buying_climax": "Volume spike with dominant upper wick and negative delta",
    "volume.poc_distance_atr": "Distance from the rolling volume-profile POC in ATR",
    "volume.poc_acceptance": "Close-bin volume share of the POC bin (acceptance)",
    "volume.above_poc": "Close trades above the rolling volume-profile POC",
    "volume.momentum_bull": "Zero-lag fast above slow with rising slope (local bull)",
    "volume.momentum_bear": "Zero-lag fast below slow with falling slope (local bear)",
    "volume.momentum_slope": "Squashed winsorized z-score of the zero-lag slope",
}


def volume_definitions(params: VolumeParams) -> tuple[FeatureDefinition, ...]:
    """Build the registry declarations for the volume family."""
    defaults = {
        "atr_length": params.atr_length,
        "volume_sma_length": params.volume_sma_length,
        "range_sma_length": params.range_sma_length,
        "normalization_window": params.normalization_window,
        "rank_window": params.rank_window,
        "forecast_length": params.forecast_length,
        "winsor_z": params.winsor_z,
        "zpf_fast_length": params.zpf_fast_length,
        "zpf_slow_length": params.zpf_slow_length,
        "profile_length": params.profile_length,
        "profile_bins": params.profile_bins,
        "delta_roll_length": params.delta_roll_length,
        "delta_bias_ema_length": params.delta_bias_ema_length,
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
