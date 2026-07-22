"""Signal search space: the decision kernel's optimizable parameters.

Book V part 5 (dynamic discovery): the space is published next to the
engine it tunes, with bounds taken from the AICE input declarations
(Book VI), never hardcoded inside the optimizer. Fee/slippage is a
cost, not a tunable; timing/stop model enums are configuration
choices, not search dimensions.
"""

from apex.optimization.parameters import OptimizableParameter

SIGNAL_SEARCH_SPACE: tuple[OptimizableParameter, ...] = (
    OptimizableParameter(name="probability_threshold", minimum=0.50, maximum=0.95, step=0.01),
    OptimizableParameter(name="probability_edge", minimum=0.0, maximum=0.30, step=0.01),
    OptimizableParameter(name="uncertainty_maximum", minimum=0.10, maximum=0.90, step=0.05),
    OptimizableParameter(
        name="minimum_contributors", minimum=1, maximum=13, step=1, integer=True
    ),
    OptimizableParameter(name="cooldown_bars", minimum=0, maximum=96, step=4, integer=True),
    OptimizableParameter(name="rvol_cutoff", minimum=1.0, maximum=3.0, step=0.1),
    OptimizableParameter(name="entropy_maximum", minimum=0.40, maximum=0.98, step=0.01),
    OptimizableParameter(name="oracle_failure_maximum", minimum=0.40, maximum=0.95, step=0.01),
    OptimizableParameter(name="minimum_expected_r", minimum=-0.50, maximum=1.50, step=0.05),
    OptimizableParameter(name="stop_atr_multiple", minimum=0.5, maximum=5.0, step=0.1),
    OptimizableParameter(name="target_atr_multiple", minimum=0.5, maximum=8.0, step=0.1),
    OptimizableParameter(name="similarity_threshold", minimum=0.50, maximum=0.99, step=0.01),
    OptimizableParameter(
        name="similarity_cooldown_bars", minimum=1, maximum=200, step=1, integer=True
    ),
    OptimizableParameter(
        name="pending_maximum_bars", minimum=1, maximum=48, step=1, integer=True
    ),
    OptimizableParameter(name="micro_bos_length", minimum=2, maximum=20, step=1, integer=True),
    OptimizableParameter(name="trigger_close_location", minimum=0.50, maximum=0.95, step=0.01),
)
