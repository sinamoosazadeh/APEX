"""Learning state contract (Book I ch. 11; AICE online learning).

The knowledge the system accumulates from its own closed trades - the
AICE online-learning arrays (Book VI lines 860-975) as one immutable,
versioned artifact:

- **Channel memory**: per-channel Beta posteriors and R attribution
  (``f_update_feature``); read as the adaptive weight factor
  (``f_feature_factor``).
- **Setup memory**: per-setup wins/trades/R (``f_record_setup``); read
  as the probability meta factor (``f_setup_factor``).
- **Calibration memory**: ten probability bins (``f_update_cal``);
  read as the Laplace-blended calibrator (``f_calibrate``).

The research platform folds outcomes into this state; the probability
engine and the decision kernel only read it. Every formula lives here
once (Constitution 2.12) - producers and consumers share this module.
A missing state is the fresh chart: every factor 1.0, no calibration.
"""

import json
from dataclasses import dataclass, field, replace

from apex.core.exceptions import ValidationError


def _bounded(value: float, lower: float, upper: float) -> float:
    """Clamp (domain-local: the domain layer sits below features)."""
    return max(lower, min(upper, value))


# Canonical channel order (AICE w0..w12).
CHANNEL_NAMES: tuple[str, ...] = (
    "structure", "liquidity", "orderblock", "fvg", "zone", "dna",
    "kinetic", "delta", "sequence", "trend", "mtf", "smt", "profile",
)
CHANNEL_COUNT = len(CHANNEL_NAMES)
CALIBRATION_BINS = 10

# f_feature_factor shape (Book VI lines 889-902).
_PERF_SHARE, _R_SHARE = 0.70, 0.30
_FACTOR_FLOOR, _FACTOR_CEIL = 0.45, 1.75
_MINIMUM_SCORE = 0.20
# f_setup_factor shape (lines 965-975).
_SETUP_SAMPLE = 30.0
_SETUP_WR_SHARE, _SETUP_R_SHARE = 0.50, 0.20
_SETUP_FLOOR, _SETUP_CEIL = 0.80, 1.25
# f_calibrate bounds (lines 920-929).
_PROBABILITY_FLOOR, _PROBABILITY_CEIL = 0.01, 0.99


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningParams:
    """AICE learning inputs (Book VI lines 34-45)."""

    feature_prior: float = 6.0
    adapt_strength: float = 0.65
    feature_minimum_sample: float = 25.0
    calibration_minimum_sample: float = 25.0
    calibration_maximum_blend: float = 0.65

    def __post_init__(self) -> None:
        if not 1.0 <= self.feature_prior <= 50.0:
            raise ValidationError("feature_prior out of range", code="VAL-140")
        if not 0.0 <= self.adapt_strength <= 2.0:
            raise ValidationError("adapt_strength out of range", code="VAL-141")
        if self.feature_minimum_sample < 1.0:
            raise ValidationError("feature_minimum_sample too small", code="VAL-142")
        if self.calibration_minimum_sample < 1.0:
            raise ValidationError("calibration_minimum_sample too small", code="VAL-143")
        if not 0.0 <= self.calibration_maximum_blend <= 1.0:
            raise ValidationError("calibration_maximum_blend out of range", code="VAL-144")


@dataclass(frozen=True, slots=True, kw_only=True)
class SetupStats:
    """One setup's closed-trade record."""

    trades: float = 0.0
    wins: float = 0.0
    r_sum: float = 0.0


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningState:
    """The accumulated learning artifact (immutable snapshot)."""

    alpha: tuple[float, ...] = field(default=())
    beta: tuple[float, ...] = field(default=())
    r_sum: tuple[float, ...] = field(default=())
    trades: tuple[float, ...] = field(default=())
    calibration_wins: tuple[float, ...] = field(default=())
    calibration_trades: tuple[float, ...] = field(default=())
    setups: tuple[tuple[str, SetupStats], ...] = field(default=())
    outcomes_folded: int = 0

    def _validate_lengths(self) -> None:
        for name in ("alpha", "beta", "r_sum", "trades"):
            if len(getattr(self, name)) != CHANNEL_COUNT:
                raise ValidationError(
                    f"learning state {name} must carry {CHANNEL_COUNT} channels",
                    code="VAL-145",
                )
        for name in ("calibration_wins", "calibration_trades"):
            if len(getattr(self, name)) != CALIBRATION_BINS:
                raise ValidationError(
                    f"learning state {name} must carry {CALIBRATION_BINS} bins",
                    code="VAL-146",
                )

    def __post_init__(self) -> None:
        if self.alpha:
            self._validate_lengths()

    @classmethod
    def fresh(cls, params: LearningParams) -> "LearningState":
        """The AICE first-bar initialization (lines 877-887)."""
        prior = params.feature_prior
        return cls(
            alpha=(prior,) * CHANNEL_COUNT,
            beta=(prior,) * CHANNEL_COUNT,
            r_sum=(0.0,) * CHANNEL_COUNT,
            trades=(0.0,) * CHANNEL_COUNT,
            calibration_wins=(0.0,) * CALIBRATION_BINS,
            calibration_trades=(0.0,) * CALIBRATION_BINS,
        )

    # --- Folding (research side) ---------------------------------------------

    def fold_outcome(
        self,
        *,
        setup: str,
        win: bool,
        realized_r: float,
        probability: float,
        channel_scores: tuple[float, ...],
    ) -> "LearningState":
        """One closed trade folded in (AICE lines 3255-3271)."""
        if len(channel_scores) != CHANNEL_COUNT:
            raise ValidationError(
                "channel_scores must carry one score per channel",
                code="VAL-147",
                details={"got": len(channel_scores)},
            )
        alpha = list(self.alpha)
        beta = list(self.beta)
        r_sum = list(self.r_sum)
        trades = list(self.trades)
        for index, raw in enumerate(channel_scores):
            score = _bounded(raw, 0.0, 1.0)
            if score < _MINIMUM_SCORE:
                continue
            if win:
                alpha[index] += score
            else:
                beta[index] += score
            r_sum[index] += realized_r * score
            trades[index] += score
        wins = list(self.calibration_wins)
        counts = list(self.calibration_trades)
        bin_index = calibration_bin(probability)
        counts[bin_index] += 1.0
        wins[bin_index] += 1.0 if win else 0.0
        name = setup or "Confluence"
        stats = dict(self.setups)
        current = stats.get(name, SetupStats())
        stats[name] = SetupStats(
            trades=current.trades + 1.0,
            wins=current.wins + (1.0 if win else 0.0),
            r_sum=current.r_sum + realized_r,
        )
        return replace(
            self,
            alpha=tuple(alpha),
            beta=tuple(beta),
            r_sum=tuple(r_sum),
            trades=tuple(trades),
            calibration_wins=tuple(wins),
            calibration_trades=tuple(counts),
            setups=tuple(sorted(stats.items())),
            outcomes_folded=self.outcomes_folded + 1,
        )

    # --- Reading (engine side) --------------------------------------------------

    def channel_factor(self, index: int, params: LearningParams) -> float:
        """AICE ``f_feature_factor`` (lines 889-902)."""
        if not self.alpha:
            return 1.0
        a = self.alpha[index]
        b = self.beta[index]
        tr = self.trades[index]
        rs = self.r_sum[index]
        posterior = a / max(a + b, 0.0001)
        expected_r = rs / tr if tr > 0 else 0.0
        sample = _bounded(tr / params.feature_minimum_sample, 0.0, 1.0)
        performance_edge = (posterior - 0.5) * 2.0
        r_edge = _bounded(expected_r, -1.0, 1.0)
        return _bounded(
            1.0
            + params.adapt_strength
            * sample
            * (performance_edge * _PERF_SHARE + r_edge * _R_SHARE),
            _FACTOR_FLOOR,
            _FACTOR_CEIL,
        )

    def setup_factor(self, name: str) -> float:
        """AICE ``f_setup_factor`` (lines 965-975)."""
        stats = dict(self.setups).get(name or "Confluence")
        if stats is None or stats.trades <= 0:
            return 1.0
        win_rate = (stats.wins + 1.0) / (stats.trades + 2.0)
        expected_r = stats.r_sum / stats.trades
        sample = _bounded(stats.trades / _SETUP_SAMPLE, 0.0, 1.0)
        return _bounded(
            1.0
            + sample
            * (
                (win_rate - 0.5) * _SETUP_WR_SHARE
                + _bounded(expected_r, -1.0, 1.0) * _SETUP_R_SHARE
            ),
            _SETUP_FLOOR,
            _SETUP_CEIL,
        )

    def calibrate(self, probability: float, params: LearningParams) -> float:
        """AICE ``f_calibrate`` (lines 920-929): Laplace bin blend."""
        adjusted = _bounded(probability, _PROBABILITY_FLOOR, _PROBABILITY_CEIL)
        if not self.calibration_wins:
            return adjusted
        bin_index = calibration_bin(adjusted)
        wins = self.calibration_wins[bin_index]
        count = self.calibration_trades[bin_index]
        win_rate = (wins + 1.0) / (count + 2.0)
        blend = _bounded(
            count / params.calibration_minimum_sample,
            0.0,
            params.calibration_maximum_blend,
        )
        return _bounded(
            adjusted * (1.0 - blend) + win_rate * blend,
            _PROBABILITY_FLOOR,
            _PROBABILITY_CEIL,
        )

    # --- Serialization ------------------------------------------------------------

    def to_json(self) -> str:
        """Canonical artifact payload."""
        return json.dumps(
            {
                "alpha": list(self.alpha),
                "beta": list(self.beta),
                "r_sum": list(self.r_sum),
                "trades": list(self.trades),
                "calibration_wins": list(self.calibration_wins),
                "calibration_trades": list(self.calibration_trades),
                "setups": {
                    name: {"trades": s.trades, "wins": s.wins, "r_sum": s.r_sum}
                    for name, s in self.setups
                },
                "outcomes_folded": self.outcomes_folded,
            },
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, payload: str) -> "LearningState":
        """Parse an artifact payload (raises on malformed content)."""
        try:
            data = json.loads(payload)
        except ValueError as error:
            raise ValidationError(
                "learning artifact is not valid JSON", code="VAL-148"
            ) from error
        if not isinstance(data, dict):
            raise ValidationError(
                "learning artifact must be a mapping", code="VAL-148"
            )
        setups = data.get("setups", {})
        return cls(
            alpha=tuple(float(x) for x in data.get("alpha", ())),
            beta=tuple(float(x) for x in data.get("beta", ())),
            r_sum=tuple(float(x) for x in data.get("r_sum", ())),
            trades=tuple(float(x) for x in data.get("trades", ())),
            calibration_wins=tuple(
                float(x) for x in data.get("calibration_wins", ())
            ),
            calibration_trades=tuple(
                float(x) for x in data.get("calibration_trades", ())
            ),
            setups=tuple(
                sorted(
                    (
                        str(name),
                        SetupStats(
                            trades=float(s.get("trades", 0.0)),
                            wins=float(s.get("wins", 0.0)),
                            r_sum=float(s.get("r_sum", 0.0)),
                        ),
                    )
                    for name, s in setups.items()
                    if isinstance(s, dict)
                )
            ),
            outcomes_folded=int(data.get("outcomes_folded", 0)),
        )


def calibration_bin(probability: float) -> int:
    """AICE ``f_cal_bin`` (line 917)."""
    return int(_bounded(probability, 0.0, 0.9999) * 10.0)
