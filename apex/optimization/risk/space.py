"""Risk search space (Book V part 6: dynamic discovery).

The risk layer's optimizable parameters: stop model and multiples,
the three-level take-profit ladder (monotonic by construction: TP2/TP3
are positive steps above the previous level), volume allocations
(TP3 receives the remainder, floored by the allocation bounds),
breakeven and trailing management, and exposure shaping (sizing model
and risk fraction). Stop/TP models needing engines that arrive later
(liquidity/ICT/session stops, order-block targets) extend this space
with those phases - the space is discovered, never hardcoded.
"""

from apex.optimization.parameters import OptimizableParameter

# Sizing models (part 6 + Book V 4.10, portfolio state from Phase 9):
# fixed / probability / confidence shape on the signal alone;
# Kelly / drawdown / budget shape on the fold's own trailing trade
# history and equity curve.
SIZING_FIXED = 0
SIZING_PROBABILITY = 1
SIZING_CONFIDENCE = 2
SIZING_KELLY = 3
SIZING_DRAWDOWN = 4
SIZING_BUDGET = 5
# Stop models (Book V catalog over the honestly available levels,
# Phase 10): pure ATR, the signal's structure-hybrid stop, beyond the
# best order-block boundary (ICT, zone features), beyond the external
# liquidity extreme (the AICE macro targets), beyond the UTC-day
# extreme (session), or the volatility-regime-scaled ATR multiple.
# Each level model falls back to ATR when its level is absent (the
# AICE na-branch).
STOP_MODEL_ATR = 0
STOP_MODEL_SIGNAL = 1
STOP_MODEL_ICT_OB = 2
STOP_MODEL_LIQUIDITY = 3
STOP_MODEL_SESSION = 4
STOP_MODEL_VOLATILITY = 5
# Entry models (execution, Phase 10): market crosses the spread and
# pays the slippage share; a limit waits at an offset and stands the
# trade aside when never filled within its patience.
ENTRY_MARKET = 0
ENTRY_LIMIT = 1

RISK_SEARCH_SPACE: tuple[OptimizableParameter, ...] = (
    OptimizableParameter(name="stop_model", minimum=0, maximum=5, step=1, integer=True),
    OptimizableParameter(name="stop_atr_multiple", minimum=0.5, maximum=5.0, step=0.1),
    OptimizableParameter(name="tp1_r", minimum=0.4, maximum=1.5, step=0.1),
    OptimizableParameter(name="tp2_step_r", minimum=0.3, maximum=2.0, step=0.1),
    OptimizableParameter(name="tp3_step_r", minimum=0.3, maximum=3.0, step=0.1),
    OptimizableParameter(name="tp1_allocation", minimum=0.10, maximum=0.45, step=0.05),
    OptimizableParameter(name="tp2_allocation", minimum=0.10, maximum=0.45, step=0.05),
    OptimizableParameter(name="breakeven_trigger_r", minimum=0.3, maximum=2.0, step=0.1),
    OptimizableParameter(name="trailing_enabled", minimum=0, maximum=1, step=1, integer=True),
    OptimizableParameter(name="trailing_distance_r", minimum=0.5, maximum=3.0, step=0.25),
    OptimizableParameter(name="sizing_model", minimum=0, maximum=5, step=1, integer=True),
    OptimizableParameter(name="risk_fraction", minimum=0.25, maximum=2.0, step=0.25),
    OptimizableParameter(name="entry_model", minimum=0, maximum=1, step=1, integer=True),
    OptimizableParameter(name="limit_offset_atr", minimum=0.0, maximum=0.5, step=0.05),
    OptimizableParameter(name="limit_patience_bars", minimum=1, maximum=6, step=1, integer=True),
)
