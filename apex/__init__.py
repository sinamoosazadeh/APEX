"""APEX - Autonomous Probabilistic Execution eXchange.

Institutional-grade, deterministic, non-repainting crypto trading
intelligence platform. Re-engineered from the AICE Pine Script v6
reference per the APEX specification books (Books I-III).

Layer map (dependencies point downward only, see docs/ARCHITECTURE.md):

    dashboard -> api -> services -> engines -> features -> domain -> core

This package root exposes only the project version.
"""

from typing import Final

__version__: Final[str] = "0.11.0"

__all__ = ["__version__"]
