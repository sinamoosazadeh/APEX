"""Research platform (Phase 11): the scientific lifecycle.

Attribution, the AICE learning fold, calibration measurement, drift
detection, the experiment registry and the Book V part 7 optimization
orchestrator (Book II ch. 14/23; Book I ch. 11/12) - the only official
path by which the system evolves.
"""

from apex.research.analysis import (
    CalibrationReport,
    DriftReport,
    ExecutionQualityReport,
    detect_drift,
    measure_calibration,
    measure_execution_quality,
)
from apex.research.attribution import AttributionResult, TradeOutcome, join_outcomes
from apex.research.experiments import (
    ComparisonResult,
    WalkForwardReport,
    bootstrap_comparison,
    walk_forward_reoptimize,
)
from apex.research.service import (
    OrchestrationSummary,
    ResearchService,
    ResearchSummary,
    SeriesStudy,
)
from apex.research.store import (
    ExperimentRecord,
    ResearchJob,
    SqliteResearchRepository,
)

__all__ = [
    "AttributionResult",
    "CalibrationReport",
    "ComparisonResult",
    "DriftReport",
    "ExecutionQualityReport",
    "ExperimentRecord",
    "OrchestrationSummary",
    "ResearchJob",
    "ResearchService",
    "ResearchSummary",
    "SeriesStudy",
    "SqliteResearchRepository",
    "TradeOutcome",
    "WalkForwardReport",
    "bootstrap_comparison",
    "detect_drift",
    "join_outcomes",
    "measure_calibration",
    "measure_execution_quality",
    "walk_forward_reoptimize",
]
