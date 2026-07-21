"""Bar quality inspection (Book II ch. 6/16).

Detects gaps in a bar series (missing intervals between consecutive
bars) and assigns quality scores: bars adjacent to a gap and forming
bars are down-scored so downstream engines can weigh or reject them.
All scoring parameters come from configuration (Constitution 3.7).
"""

from dataclasses import dataclass, field, replace
from itertools import pairwise

from apex.core.enums import Timeframe
from apex.core.time.timestamp import Timestamp
from apex.core.types import QualityScore
from apex.core.validation import ensure_in_range
from apex.domain.market import Bar


@dataclass(frozen=True, slots=True, kw_only=True)
class GapReport:
    """Missing intervals detected in one bar series."""

    symbol: str
    timeframe: Timeframe
    gaps: tuple[tuple[Timestamp, Timestamp], ...] = field(default=())

    @property
    def gap_count(self) -> int:
        """Number of contiguous holes in the series."""
        return len(self.gaps)

    @property
    def missing_bars(self) -> int:
        """Total number of missing bar intervals across all holes."""
        step = self.timeframe.duration_ms
        return sum((end.epoch_ms - start.epoch_ms) // step for start, end in self.gaps)


class BarQualityInspector:
    """Scores bar series and reports gaps."""

    def __init__(self, *, gap_penalty: float, forming_bar_quality: float) -> None:
        ensure_in_range(gap_penalty, 0.0, 1.0, "gap_penalty")
        ensure_in_range(forming_bar_quality, 0.0, 1.0, "forming_bar_quality")
        self._gap_penalty = gap_penalty
        self._forming_quality = forming_bar_quality

    def inspect(self, bars: list[Bar]) -> tuple[list[Bar], GapReport | None]:
        """Return re-scored bars plus a gap report (None for empty input).

        Input must be a single (symbol, timeframe) series sorted by
        open time - the ingestion pipeline guarantees this.
        """
        if not bars:
            return [], None
        step = bars[0].timeframe.duration_ms
        gaps: list[tuple[Timestamp, Timestamp]] = []
        scored: list[Bar] = [self._score(bars[0], follows_gap=False)]
        for previous, current in pairwise(bars):
            expected_ms = previous.open_time.epoch_ms + step
            follows_gap = current.open_time.epoch_ms > expected_ms
            if follows_gap:
                gaps.append(
                    (Timestamp(epoch_ms=expected_ms), current.open_time)
                )
            scored.append(self._score(current, follows_gap=follows_gap))
        report = GapReport(
            symbol=bars[0].symbol,
            timeframe=bars[0].timeframe,
            gaps=tuple(gaps),
        )
        return scored, report

    def _score(self, bar: Bar, *, follows_gap: bool) -> Bar:
        quality = 1.0
        if not bar.is_closed:
            quality = self._forming_quality
        if follows_gap:
            quality = max(0.0, quality - self._gap_penalty)
        if quality == bar.quality.value:
            return bar
        return replace(bar, quality=QualityScore(quality))
