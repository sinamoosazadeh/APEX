"""Research analyses (Book II 14.16, 23.11-23.13; Book I 12.13).

Calibration measurement (the Phase 5 deferral: confidence intervals
carried APEX semantics until research could *measure* calibration),
drift detection across the platform's own stored series, and the
execution-quality aggregation (Book II 12.28 adaptive execution
learning) over the Phase 10 audit store. Every number is computed
from durable records - nothing is estimated from assumptions.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from math import sqrt

from apex.domain.learning import CALIBRATION_BINS
from apex.execution.store import ExecutionRecord
from apex.research.attribution import TradeOutcome


@dataclass(frozen=True, slots=True, kw_only=True)
class CalibrationBinReport:
    """One probability bin's observed vs predicted outcome."""

    lower: float
    upper: float
    trades: int
    predicted: float
    observed: float


@dataclass(frozen=True, slots=True, kw_only=True)
class CalibrationReport:
    """Reliability measurement over closed trades (23.13)."""

    trades: int
    brier_score: float
    bins: tuple[CalibrationBinReport, ...]


def measure_calibration(outcomes: Sequence[TradeOutcome]) -> CalibrationReport:
    """Reliability table and Brier score of decision probabilities."""
    sums = [0.0] * CALIBRATION_BINS
    wins = [0] * CALIBRATION_BINS
    counts = [0] * CALIBRATION_BINS
    brier = 0.0
    for outcome in outcomes:
        probability = min(max(outcome.probability, 0.0), 0.9999)
        bin_index = int(probability * CALIBRATION_BINS)
        counts[bin_index] += 1
        sums[bin_index] += probability
        wins[bin_index] += 1 if outcome.win else 0
        brier += (probability - (1.0 if outcome.win else 0.0)) ** 2
    bins = tuple(
        CalibrationBinReport(
            lower=index / CALIBRATION_BINS,
            upper=(index + 1) / CALIBRATION_BINS,
            trades=counts[index],
            predicted=sums[index] / counts[index] if counts[index] else 0.0,
            observed=wins[index] / counts[index] if counts[index] else 0.0,
        )
        for index in range(CALIBRATION_BINS)
    )
    total = len(outcomes)
    return CalibrationReport(
        trades=total,
        brier_score=brier / total if total else 0.0,
        bins=bins,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class DriftReport:
    """Reference-vs-recent shift of one measured series (14.16)."""

    name: str
    reference_mean: float
    recent_mean: float
    reference_std: float
    shift_z: float
    drifting: bool


def detect_drift(
    name: str,
    values: Sequence[float],
    *,
    recent_share: float = 0.25,
    threshold_z: float = 2.0,
) -> DriftReport:
    """Mean-shift drift: recent window vs the reference window.

    ``shift_z`` is the recent mean's distance from the reference mean
    in reference standard errors; |z| past the threshold flags drift.
    Degenerate windows (too few points, zero variance) never flag.
    """
    count = len(values)
    split = max(int(count * (1.0 - recent_share)), 1)
    reference = values[:split]
    recent = values[split:]
    if len(reference) < 10 or len(recent) < 5:
        return DriftReport(
            name=name, reference_mean=0.0, recent_mean=0.0,
            reference_std=0.0, shift_z=0.0, drifting=False,
        )
    ref_mean = sum(reference) / len(reference)
    rec_mean = sum(recent) / len(recent)
    variance = sum((v - ref_mean) ** 2 for v in reference) / len(reference)
    std = sqrt(variance)
    if std <= 0:
        return DriftReport(
            name=name, reference_mean=ref_mean, recent_mean=rec_mean,
            reference_std=0.0, shift_z=0.0, drifting=False,
        )
    standard_error = std / sqrt(len(recent))
    shift_z = (rec_mean - ref_mean) / standard_error
    return DriftReport(
        name=name,
        reference_mean=ref_mean,
        recent_mean=rec_mean,
        reference_std=std,
        shift_z=shift_z,
        drifting=abs(shift_z) >= threshold_z,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionQualityReport:
    """Aggregated execution telemetry (Book II 12.28)."""

    executions: int
    filled: int
    rejected: int
    unfilled: int
    fill_rate: float
    average_slippage: Decimal
    average_fees: Decimal


def measure_execution_quality(
    records: Sequence[ExecutionRecord],
) -> ExecutionQualityReport:
    """Fill/rejection rates and average costs from the audit store."""
    filled = [record for record in records if record.status == "filled"]
    rejected = sum(1 for record in records if record.status == "rejected")
    unfilled = sum(1 for record in records if record.status == "unfilled")
    slippages = [record.slippage for record in filled if record.slippage is not None]
    average_slippage = (
        sum(slippages, Decimal(0)) / len(slippages) if slippages else Decimal(0)
    )
    fees = [record.fees for record in filled]
    average_fees = sum(fees, Decimal(0)) / len(fees) if fees else Decimal(0)
    attempted = len(records) - rejected
    return ExecutionQualityReport(
        executions=len(records),
        filled=len(filled),
        rejected=rejected,
        unfilled=unfilled,
        fill_rate=len(filled) / attempted if attempted > 0 else 0.0,
        average_slippage=average_slippage,
        average_fees=average_fees,
    )
