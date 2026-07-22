"""Decision platform plugin (Book II ch. 11/19, Book I ch. 9).

Wires the Phase 6 slice: the Central Decision Kernel -> decision store
-> computation service -> kernel module. Kernel parameters come from
the ``decision`` section of market.yaml, falling back to the AICE
input defaults (Constitution 3.7: tunables are data).
"""

from collections.abc import Sequence
from pathlib import Path

from apex.core.config import AppConfig, ConfigSection
from apex.core.contracts.interfaces import IClock, IEventBus, IModule
from apex.core.enums import HealthState, PluginKind, StabilityLevel, Timeframe
from apex.core.exceptions import ConfigurationError
from apex.core.logging import LoggerFactory, StructuredLogger
from apex.core.versioning import SemanticVersion
from apex.decision.kernel import CentralDecisionKernel, DecisionParams
from apex.decision.service import DecisionService
from apex.decision.store import SqliteDecisionRepository
from apex.kernel.container import ServiceContainer
from apex.plugins.contract import PluginManifest
from apex.probability.store import SqliteProbabilityRepository
from apex.storage.bars import SqliteBarRepository
from apex.storage.features import SqliteFeatureRepository

DECISION_DATABASE_FILENAME = "decisions.sqlite"


class DecisionPlatformModule:
    """Kernel module owning the decision store lifecycle."""

    MODULE_NAME = "decision_platform"

    def __init__(
        self,
        *,
        repository: SqliteDecisionRepository,
        logger: StructuredLogger,
    ) -> None:
        self._repository = repository
        self._logger = logger
        self._running = False

    @property
    def name(self) -> str:
        """Unique module name."""
        return self.MODULE_NAME

    @property
    def dependencies(self) -> tuple[str, ...]:
        """Consumes assessments; starts after the probability platform."""
        return ("probability_platform",)

    async def start(self) -> None:
        """Open the decision store."""
        await self._repository.open()
        self._running = True
        self._logger.info("decision_platform_started")

    async def stop(self) -> None:
        """Close the decision store."""
        self._running = False
        await self._repository.close()
        self._logger.info("decision_platform_stopped")

    def health(self) -> HealthState:
        """Healthy while the store is open."""
        return HealthState.HEALTHY if self._running else HealthState.OFFLINE


def _numbers(section: ConfigSection, code: str) -> dict[str, float]:
    if not isinstance(section, dict):
        raise ConfigurationError(
            "market.decision must be a mapping", code=code, details={}
        )
    numbers: dict[str, float] = {}
    for key, value in section.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        numbers[key] = float(value)
    return numbers


def _flags(section: ConfigSection, code: str) -> dict[str, bool]:
    if not isinstance(section, dict):
        raise ConfigurationError(
            "market.decision must be a mapping", code=code, details={}
        )
    return {
        key: value for key, value in section.items() if isinstance(value, bool)
    }


def _decision_params(section: ConfigSection) -> DecisionParams:
    """Kernel params: numeric/flag config overrides on AICE defaults."""
    numbers = _numbers(section, "CFG-029")
    flags = _flags(section, "CFG-029")
    defaults = DecisionParams()
    return DecisionParams(
        probability_threshold=numbers.get(
            "probability_threshold", defaults.probability_threshold
        ),
        probability_edge=numbers.get("probability_edge", defaults.probability_edge),
        uncertainty_maximum=numbers.get(
            "uncertainty_maximum", defaults.uncertainty_maximum
        ),
        minimum_contributors=int(
            numbers.get("minimum_contributors", defaults.minimum_contributors)
        ),
        cooldown_bars=int(numbers.get("cooldown_bars", defaults.cooldown_bars)),
        rvol_cutoff=numbers.get("rvol_cutoff", defaults.rvol_cutoff),
        minimum_atr_percent=numbers.get(
            "minimum_atr_percent", defaults.minimum_atr_percent
        ),
        maximum_atr_percent=numbers.get(
            "maximum_atr_percent", defaults.maximum_atr_percent
        ),
        entropy_maximum=numbers.get("entropy_maximum", defaults.entropy_maximum),
        oracle_failure_maximum=numbers.get(
            "oracle_failure_maximum", defaults.oracle_failure_maximum
        ),
        minimum_expected_r=numbers.get(
            "minimum_expected_r", defaults.minimum_expected_r
        ),
        minimum_expected_edge_r=numbers.get(
            "minimum_expected_edge_r", defaults.minimum_expected_edge_r
        ),
        fee_slippage_r=numbers.get("fee_slippage_r", defaults.fee_slippage_r),
        stop_atr_multiple=numbers.get("stop_atr_multiple", defaults.stop_atr_multiple),
        target_atr_multiple=numbers.get(
            "target_atr_multiple", defaults.target_atr_multiple
        ),
        similarity_threshold=numbers.get(
            "similarity_threshold", defaults.similarity_threshold
        ),
        similarity_cooldown_bars=int(
            numbers.get("similarity_cooldown_bars", defaults.similarity_cooldown_bars)
        ),
        pending_maximum_bars=int(
            numbers.get("pending_maximum_bars", defaults.pending_maximum_bars)
        ),
        micro_bos_length=int(numbers.get("micro_bos_length", defaults.micro_bos_length)),
        trigger_close_location=numbers.get(
            "trigger_close_location", defaults.trigger_close_location
        ),
        atr_length=int(numbers.get("atr_length", defaults.atr_length)),
        ema_length=int(numbers.get("ema_length", defaults.ema_length)),
        flatness_gate_enabled=flags.get(
            "flatness_gate_enabled", defaults.flatness_gate_enabled
        ),
        conservative_resolver=flags.get(
            "conservative_resolver", defaults.conservative_resolver
        ),
        equity_guard_enabled=flags.get(
            "equity_guard_enabled", defaults.equity_guard_enabled
        ),
        equity_guard_minimum_trades=int(
            numbers.get(
                "equity_guard_minimum_trades", defaults.equity_guard_minimum_trades
            )
        ),
        equity_guard_ema_length=int(
            numbers.get("equity_guard_ema_length", defaults.equity_guard_ema_length)
        ),
    )


class DecisionPlatformPlugin:
    """Builds the decision platform as a kernel plugin."""

    @property
    def manifest(self) -> PluginManifest:
        """Plugin self-description."""
        return PluginManifest(
            name="decision_platform",
            version=SemanticVersion(0, 1, 0),
            kind=PluginKind.SERVICE,
            api_version=SemanticVersion(1, 0, 0),
            description="Central Decision Kernel, decision store and service",
            stability=StabilityLevel.BETA,
            requires=("probability_platform",),
        )

    def build_modules(self, container: ServiceContainer) -> Sequence[IModule]:
        """Construct the decision platform from injected services."""
        config = container.resolve(AppConfig)
        loggers = container.resolve(LoggerFactory)
        clock = container.resolve(IClock)  # type: ignore[type-abstract]
        bus = container.resolve(IEventBus)  # type: ignore[type-abstract]
        params = _decision_params(config.market.decision)
        kernel = CentralDecisionKernel(params=params, clock=clock)
        repository = SqliteDecisionRepository(
            database_path=Path(config.system.data_dir) / DECISION_DATABASE_FILENAME,
        )
        service = DecisionService(
            exchange_id="toobit",
            kernel=kernel,
            macro_timeframe=Timeframe.H4,
            macro_pivot_lookback=int(
                _numbers(config.market.decision, "CFG-029").get(
                    "macro_pivot_lookback", 8
                )
            ),
            bar_repository=container.resolve(SqliteBarRepository),
            feature_repository=container.resolve(SqliteFeatureRepository),
            probability_repository=container.resolve(SqliteProbabilityRepository),
            decision_repository=repository,
            bus=bus,
            clock=clock,
            logger=loggers.get("decision.service"),
        )
        container.register_instance(CentralDecisionKernel, kernel)
        container.register_instance(SqliteDecisionRepository, repository)
        container.register_instance(DecisionService, service)
        return [
            DecisionPlatformModule(
                repository=repository,
                logger=loggers.get("decision.module"),
            )
        ]


APEX_PLUGIN = DecisionPlatformPlugin()
