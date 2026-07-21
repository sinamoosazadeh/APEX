"""Engine interface contracts.

Contract-first (Book II 5.2): these are the official boundaries of the
platforms delivered in Phases 3-10. Implementations arrive with their
phases; the contracts exist now so every layer builds against stable
interfaces from day one. All are EXPERIMENTAL until their platform
lands (Book II 5.36).
"""

import uuid
from collections.abc import Mapping, Sequence
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
@stability(StabilityLevel.EXPERIMENTAL)
class IProbabilityEngine(Protocol):
    """Probability platform contract (Phase 5)."""

    async def assess(
        self,
        subject: str,
        feature_vector_id: uuid.UUID,
        context: MarketContext,
    ) -> Result[ProbabilityAssessment]:
        """Produce a full probabilistic judgement for ``subject``."""
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
@stability(StabilityLevel.EXPERIMENTAL)
class IOptimizer(Protocol):
    """Optimizer contract (Book II 5.20, Phases 7-8)."""

    @property
    def optimizer_version(self) -> str:
        """Version tag stamped onto optimized outputs."""
        ...

    async def optimize(
        self,
        search_space: Mapping[str, tuple[float, float]],
        *,
        seed: int,
    ) -> Result[Mapping[str, float]]:
        """Search the space deterministically (seeded) for best parameters."""
        ...
