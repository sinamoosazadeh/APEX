"""Engine interface contracts.

Contract-first (Book II 5.2): these are the official boundaries of the
platforms delivered in Phases 3-10. Implementations arrive with their
phases; the contracts exist now so every layer builds against stable
interfaces from day one. All are EXPERIMENTAL until their platform
lands (Book II 5.36).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from apex.core.context import ExecutionContext, MarketContext
from apex.core.enums import StabilityLevel, Timeframe
from apex.core.result import Result
from apex.core.time.timestamp import Timestamp
from apex.core.versioning import stability
from apex.domain.feature import Feature
from apex.domain.market import Bar, Tick
from apex.domain.order import Order
from apex.domain.portfolio import PortfolioSnapshot
from apex.domain.probability import ProbabilityAssessment
from apex.domain.risk import RiskAssessment
from apex.domain.signal import Signal
from apex.domain.trade import Trade


@runtime_checkable
@stability(StabilityLevel.BETA)
class IMarketDataGateway(Protocol):
    """Market data contract (anti-corruption layer, Book II 5.37).

    Contract evolution note (Book II 5.35): split out of ``IExchange``
    in Phase 3 so the data platform ships without any pretend trading
    surface. ``IExchange`` extends this with order methods and is
    implemented by the Execution Platform (Phase 10).
    """

    @property
    def exchange_id(self) -> str:
        """Lowercase exchange identifier (e.g. ``toobit``)."""
        ...

    async def fetch_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        *,
        start: Timestamp,
        end: Timestamp,
    ) -> Result[Sequence[Bar]]:
        """Fetch historical bars with open time in [start, end)."""
        ...

    async def fetch_ticks(
        self,
        symbol: str,
        *,
        start: Timestamp,
        limit: int,
    ) -> Result[Sequence[Tick]]:
        """Fetch executed trade prints from ``start``."""
        ...


@runtime_checkable
@stability(StabilityLevel.EXPERIMENTAL)
class IExchange(IMarketDataGateway, Protocol):
    """Full exchange contract: market data plus order lifecycle.

    Implemented by the Execution Platform (Phase 10); market data
    methods are inherited from :class:`IMarketDataGateway`.
    """

    async def submit_order(self, order: Order) -> Result[Order]:
        """Submit an order; returns the acknowledged order version."""
        ...

    async def cancel_order(self, order: Order) -> Result[Order]:
        """Cancel an order; returns the terminal order version."""
        ...

    async def fetch_open_orders(self, symbol: str) -> Result[Sequence[Order]]:
        """Fetch currently open orders for a symbol."""
        ...


@runtime_checkable
@stability(StabilityLevel.BETA)
class IFeatureEngine(Protocol):
    """Feature engine contract (Phase 4).

    Contract evolution (5.35): engines emit full :class:`Feature`
    domain objects - one per (bar, feature name) - computed from
    confirmed bars only. Computation is pure and synchronous: engines
    perform no I/O, which keeps every feature deterministic and
    replayable.
    """

    @property
    def family(self) -> str:
        """The feature family this engine produces."""
        ...

    @property
    def feature_names(self) -> tuple[str, ...]:
        """Every feature name this engine can emit."""
        ...

    def compute(
        self,
        bars: Sequence[Bar],
        context: MarketContext,
    ) -> Result[tuple[Feature, ...]]:
        """Compute features for every confirmed bar in the window."""
        ...


@runtime_checkable
@stability(StabilityLevel.BETA)
class IContextFeatureEngine(IFeatureEngine, Protocol):
    """Feature engine needing auxiliary bar series (Phase 4).

    Multi-series families (HTF/MTF context, SMT divergence) declare the
    extra series they need via :meth:`required_series`; the pipeline
    fetches those confirmed bars and passes them to
    :meth:`compute_with_context`. Engines must consume auxiliary series
    causally: for any chart bar, only auxiliary bars whose close time
    is at or before that bar's close time may influence its features
    (Constitution: no repainting - stricter than Pine's
    ``request.security`` semantics, which outranks AICE on conflict).

    ``compute`` (inherited) remains the auxiliary-free fallback: it
    must produce the family's documented neutral behavior so the
    engine stays usable when a required series is not stored.
    """

    def required_series(
        self,
        symbol: str,
        timeframe: Timeframe,
    ) -> tuple[tuple[str, Timeframe], ...]:
        """(symbol, timeframe) pairs this engine needs beyond the chart."""
        ...

    def compute_with_context(
        self,
        bars: Sequence[Bar],
        auxiliary: Mapping[tuple[str, Timeframe], Sequence[Bar]],
        context: MarketContext,
    ) -> Result[tuple[Feature, ...]]:
        """Compute features using the chart window plus auxiliary series."""
        ...


@dataclass(frozen=True, slots=True, kw_only=True)
class FeatureVectorSnapshot:
    """One bar's stored feature vector, keyed by feature name.

    ``close`` (Phase 11) feeds the rolling-IC learning fold; None
    keeps the fold neutral (fresh behavior).
    """

    bar_open_time: Timestamp
    values: Mapping[str, float]
    close: float | None = None


@runtime_checkable
@stability(StabilityLevel.BETA)
class IProbabilityEngine(Protocol):
    """Probability platform contract (Phase 5).

    Contract evolution (5.35): assessment is bar-anchored and windowed.
    The engine consumes an ascending series of stored feature vectors
    (momentum terms fold over the window, exactly like feature engines
    fold over bars) and returns one (long, short) assessment pair per
    snapshot, aligned with the input order. Computation is pure and
    synchronous - no I/O - so every assessment is deterministic and
    replayable.
    """

    def assess_series(
        self,
        snapshots: Sequence[FeatureVectorSnapshot],
        context: MarketContext,
    ) -> Result[tuple[tuple[ProbabilityAssessment, ProbabilityAssessment], ...]]:
        """(long, short) assessments per snapshot, in input order."""
        ...


@dataclass(frozen=True, slots=True, kw_only=True)
class DecisionSnapshot:
    """One bar's decision inputs: the bar, its vector and assessment.

    ``macro_high``/``macro_low`` are the last-closed macro-timeframe
    rolling extremes at this bar (the AICE ``htf1_hi/lo`` liquidity
    targets); None reads as the AICE na-branch.
    """

    bar: Bar
    vector: Mapping[str, float]
    probability_long: float
    probability_short: float
    channels: Mapping[str, float]
    macro_high: float | None = None
    macro_low: float | None = None
    # Zone levels (Phase 10): best live order-block boundaries from
    # the feature store (AICE ob_long_bot/ob_short_top); None is the
    # na-branch (no live zone).
    ob_long_bottom: float | None = None
    ob_short_top: float | None = None


@runtime_checkable
@stability(StabilityLevel.BETA)
class IDecisionEngine(Protocol):
    """Decision platform contract (Phase 6, Book I ch. 9).

    The Central Decision Kernel is the single decision authority: it
    consumes an ascending series of decision snapshots (bar + stored
    feature vector + persisted assessment) and returns one outcome per
    snapshot - a fired signal, a vetoed readiness (recorded with its
    failed gates for auditability) or a stand-aside. Computation is
    pure and synchronous; state (cooldowns, pending setups, similarity
    memory) folds over the window.
    """

    def decide_series(
        self,
        snapshots: Sequence["DecisionSnapshot"],
        context: MarketContext,
    ) -> Result[tuple[object, ...]]:
        """One decision outcome per snapshot, in input order."""
        ...


@runtime_checkable
@stability(StabilityLevel.EXPERIMENTAL)
class IRiskEngine(Protocol):
    """Risk platform contract (Phase 8)."""

    async def assess(
        self,
        signal: Signal,
        portfolio: PortfolioSnapshot,
    ) -> Result[RiskAssessment]:
        """Produce the risk verdict for a signal against the portfolio."""
        ...


@runtime_checkable
@stability(StabilityLevel.EXPERIMENTAL)
class IExecutionEngine(Protocol):
    """Execution platform contract (Phase 10)."""

    async def execute(
        self,
        order: Order,
        context: ExecutionContext,
    ) -> Result[Sequence[Trade]]:
        """Work an order to completion; returns resulting fills."""
        ...


@runtime_checkable
@stability(StabilityLevel.BETA)
class IOptimizer(Protocol):
    """Optimizer contract (Book II 5.20, Phases 7-8).

    Contract evolution (5.35): the search space is discovered from the
    optimized engine's published parameters (Book V part 5 - never
    passed in), and the search is pure and synchronous: one seed fully
    determines every trial, so runs are reproducible bit-for-bit.
    Returns the winning parameter overrides - empty when the candidate
    failed the Book V validation protocol and was rejected.
    """

    @property
    def optimizer_version(self) -> str:
        """Version tag stamped onto optimized outputs."""
        ...

    def optimize(self, *, seed: int) -> Result[Mapping[str, float]]:
        """Search deterministically; winning overrides or empty."""
        ...
