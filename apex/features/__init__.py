"""APEX Feature Platform (Book II ch. 7/17) - Phase 4.

The AICE migration home. Registry (every feature is declared before it
is computed), SQLite feature store (anchored to confirmed bars),
computation pipeline (pure engines, validated emission, catalog
events) and the migrated feature families - starting with market
structure (swings, BOS, CHoCH, dealing range, sweeps) from the AICE
Pine v6 source.

Run it: ``python -m apex features --symbol BTCUSDT --timeframe 1h``
"""

from apex.features.pipeline import FeatureComputationPipeline, FeatureComputationSummary
from apex.features.registry import FeatureDefinition, FeatureRegistry

__all__ = [
    "FeatureComputationPipeline",
    "FeatureComputationSummary",
    "FeatureDefinition",
    "FeatureRegistry",
]
