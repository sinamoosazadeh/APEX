"""Shared test fixtures and factories."""

import shutil
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from apex.core.enums import Direction, Timeframe
from apex.core.time.clock import ManualClock
from apex.core.time.timestamp import Timestamp
from apex.core.types import Confidence, Price, Probability, QualityScore, Volume
from apex.domain.market import Bar
from apex.domain.signal import PriceZone, Signal

REPO_ROOT = Path(__file__).resolve().parent.parent
REPO_CONFIG_DIR = REPO_ROOT / "config"

T0 = Timestamp(epoch_ms=1_750_000_000_000)


@pytest.fixture
def clock() -> ManualClock:
    """Deterministic clock starting at T0."""
    return ManualClock(T0)


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """A private copy of the repository configuration set."""
    target = tmp_path / "config"
    shutil.copytree(REPO_CONFIG_DIR, target)
    return target


def price(raw: str) -> Price:
    """Shorthand exact price."""
    return Price(Decimal(raw))


def make_bar(
    *,
    open_: str = "100",
    high: str = "110",
    low: str = "95",
    close: str = "105",
    volume: str = "1000",
    is_closed: bool = True,
    open_time: Timestamp = T0,
) -> Bar:
    """A valid bar with overridable fields."""
    return Bar(
        exchange="toobit",
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        open_time=open_time,
        open=price(open_),
        high=price(high),
        low=price(low),
        close=price(close),
        volume=Volume(Decimal(volume)),
        is_closed=is_closed,
        quality=QualityScore(1.0),
    )


def make_signal(
    *,
    direction: Direction = Direction.LONG,
    entry: tuple[str, str] = ("100", "101"),
    stop: tuple[str, str] = ("95", "96"),
    targets: tuple[tuple[str, str], ...] = (("110", "112"),),
    created_at: Timestamp = T0,
    correlation_id: uuid.UUID | None = None,
) -> Signal:
    """A valid signal with overridable geometry."""
    from apex.core.metadata import ObjectMetadata

    return Signal(
        created_at=created_at,
        exchange="toobit",
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        direction=direction,
        probability=Probability(0.62),
        confidence=Confidence(0.8),
        entry_zone=PriceZone(lower=price(entry[0]), upper=price(entry[1])),
        stop_zone=PriceZone(lower=price(stop[0]), upper=price(stop[1])),
        target_zones=tuple(
            PriceZone(lower=price(lo), upper=price(hi)) for lo, hi in targets
        ),
        metadata=ObjectMetadata(module="tests", correlation_id=correlation_id),
    )
