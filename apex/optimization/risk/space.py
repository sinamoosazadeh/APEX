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

# Sizing models (part 6): fixed / probability-adjusted / confidence-adjusted.
SIZING_FIXED = 0
SIZING_PROBABILITY = 1
SIZING_CONFIDENCE = 2
# Stop models: pure ATR or the signal's structure-hybrid stop.
STOP_MODEL_ATR = 0
STOP_MODEL_SIGNAL = 1

RISK_SEARCH_SPACE: tuple[OptimizableParameter, ...] = (
    OptimizableParameter(name="stop_model", minimum=0, maximum=1, step=1, integer=True),
    OptimizableParameter(name="stop_atr_multiple", minimum=0.5, maximum=5.0, step=0.1),
    OptimizableParameter(name="tp1_r", minimum=0.4, maximum=1.5, step=0.1),
    OptimizableParameter(name="tp2_step_r", minimum=0.3, maximum=2.0, step=0.1),
    OptimizableParameter(name="tp3_step_r", minimum=0.3, maximum=3.0, step=0.1),
    OptimizableParameter(name="tp1_allocation", minimum=0.10, maximum=0.45, step=0.05),
    OptimizableParameter(name="tp2_allocation", minimum=0.10, maximum=0.45, step=0.05),
    OptimizableParameter(name="breakeven_trigger_r", minimum=0.3, maximum=2.0, step=0.1),
    OptimizableParameter(name="trailing_enabled", minimum=0, maximum=1, step=1, integer=True),
    OptimizableParameter(name="trailing_distance_r", minimum=0.5, maximum=3.0, step=0.25),
    OptimizableParameter(name="sizing_model", minimum=0, maximum=2, step=1, integer=True),
    OptimizableParameter(name="risk_fraction", minimum=0.25, maximum=2.0, step=0.25),
)
