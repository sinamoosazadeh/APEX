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
from apex.domain.market import Bar, Tick
from apex.domain.order import Order
from apex.domain.portfolio import PortfolioSnapshot
from apex.domain.probability import ProbabilityAssessment
from apex.domain.risk import RiskAssessment
from apex.domain.signal import Signal
from apex.domain.trade import Trade


@runtime_checkable
@stability(StabilityLevel.EXPERIMENTAL)
class IExchange(Protocol):
    """Market gateway contract (anti-corruption layer, Book II 5.37).

    Implementations translate exchange-specific APIs (Toobit first,
    per Book VII) into domain contracts; no exchange concept leaks in.
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
        """Fetch confirmed historical bars in [start, end)."""
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
@stability(StabilityLevel.EXPERIMENTAL)
class IFeatureEngine(Protocol):
    """Feature platform contract (Phase 4)."""

    @property
    def families(self) -> tuple[str, ...]:
        """Feature families this engine produces."""
        ...

    async def compute(
        self,
        bars: Sequence[Bar],
        context: MarketContext,
    ) -> Result[Mapping[str, float]]:
        """Compute features from confirmed bars only (non-repainting)."""
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
