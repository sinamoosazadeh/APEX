"""Optimization platform plugin (Book V; Book II 3.23).

Wires the Phase 7 slice: the signal optimizer engine settings from
optimizer.yaml (``signal`` section), the run store and the service.
"""

from collections.abc import Sequence
from pathlib import Path

from apex.core.config import AppConfig, ConfigSection
from apex.core.contracts.interfaces import IClock, IEventBus, IModule
from apex.core.enums import HealthState, PluginKind, StabilityLevel
from apex.core.logging import LoggerFactory, StructuredLogger
from apex.core.versioning import SemanticVersion
from apex.decision.plugin import _decision_params
from apex.decision.service import DecisionService
from apex.kernel.container import ServiceContainer
from apex.optimization.objective import ObjectiveWeights
from apex.optimization.risk.service import RiskOptimizationService
from apex.optimization.signal.engine import OptimizerSettings
from apex.optimization.signal.service import SignalOptimizationService
from apex.optimization.signal.store import SignalOptimizationStore
from apex.plugins.contract import PluginManifest
from apex.storage.bars import SqliteBarRepository

OPTIMIZATION_DATABASE_FILENAME = "optimization.sqlite"
ARTIFACT_DIRECTORY = "optimizer"


class OptimizationPlatformModule:
    """Kernel module owning the optimization store lifecycle."""

    MODULE_NAME = "optimization_platform"

    def __init__(
        self,
        *,
        store: SignalOptimizationStore,
        logger: StructuredLogger,
    ) -> None:
        self._store = store
        self._logger = logger
        self._running = False

    @property
    def name(self) -> str:
        """Unique module name."""
        return self.MODULE_NAME

    @property
    def dependencies(self) -> tuple[str, ...]:
        """Optimizes the decision layer; starts after it."""
        return ("decision_platform",)

    async def start(self) -> None:
        """Open the optimization store."""
        await self._store.open()
        self._running = True
        self._logger.info("optimization_platform_started")

    async def stop(self) -> None:
        """Close the optimization store."""
        self._running = False
        await self._store.close()
        self._logger.info("optimization_platform_stopped")

    def health(self) -> HealthState:
        """Healthy while the store is open."""
        return HealthState.HEALTHY if self._running else HealthState.OFFLINE


def _numbers(section: ConfigSection) -> dict[str, float]:
    numbers: dict[str, float] = {}
    if isinstance(section, dict):
        for key, value in section.items():
            if not isinstance(value, bool) and isinstance(value, (int, float)):
                numbers[key] = float(value)
    return numbers


def _settings(optimizer_config: ConfigSection, key: str) -> OptimizerSettings:
    """Optimizer stage settings: config overrides on Book V defaults."""
    raw = optimizer_config.get(key, {})
    numbers = _numbers(raw if isinstance(raw, dict) else {})
    defaults = OptimizerSettings()
    return OptimizerSettings(
        random_trials=int(numbers.get("random_trials", defaults.random_trials)),
        latin_trials=int(numbers.get("latin_trials", defaults.latin_trials)),
        bayesian_trials=int(numbers.get("bayesian_trials", defaults.bayesian_trials)),
        refinement_rounds=int(
            numbers.get("refinement_rounds", defaults.refinement_rounds)
        ),
        validation_folds=int(numbers.get("validation_folds", defaults.validation_folds)),
        test_share=numbers.get("test_share", defaults.test_share),
        monte_carlo_resamples=int(
            numbers.get("monte_carlo_resamples", defaults.monte_carlo_resamples)
        ),
        monte_carlo_minimum=numbers.get(
            "monte_carlo_minimum", defaults.monte_carlo_minimum
        ),
        validation_minimum_score=numbers.get(
            "validation_minimum_score", defaults.validation_minimum_score
        ),
        degradation_maximum=numbers.get(
            "degradation_maximum", defaults.degradation_maximum
        ),
        stability_minimum=numbers.get("stability_minimum", defaults.stability_minimum),
        horizon_bars=int(numbers.get("horizon_bars", defaults.horizon_bars)),
        top_candidates=int(numbers.get("top_candidates", defaults.top_candidates)),
    )


class OptimizationPlatformPlugin:
    """Builds the optimization platform as a kernel plugin."""

    @property
    def manifest(self) -> PluginManifest:
        """Plugin self-description."""
        return PluginManifest(
            name="optimization_platform",
            version=SemanticVersion(0, 1, 0),
            kind=PluginKind.SERVICE,
            api_version=SemanticVersion(1, 0, 0),
            description="Signal and risk optimizers: ten-stage search, stores, artifacts",
            stability=StabilityLevel.BETA,
            requires=("decision_platform",),
        )

    def build_modules(self, container: ServiceContainer) -> Sequence[IModule]:
        """Construct the optimization platform from injected services."""
        config = container.resolve(AppConfig)
        loggers = container.resolve(LoggerFactory)
        clock = container.resolve(IClock)  # type: ignore[type-abstract]
        bus = container.resolve(IEventBus)  # type: ignore[type-abstract]
        optimizer_config = config.sections["optimizer"]
        data_dir = Path(config.system.data_dir)
        store = SignalOptimizationStore(
            database_path=data_dir / OPTIMIZATION_DATABASE_FILENAME,
            artifact_dir=data_dir / ARTIFACT_DIRECTORY,
        )
        base_params = _decision_params(config.market.decision)
        service = SignalOptimizationService(
            exchange_id="toobit",
            base_params=base_params,
            settings=_settings(optimizer_config, "signal"),
            weights=ObjectiveWeights(),
            decision_service=container.resolve(DecisionService),
            bar_repository=container.resolve(SqliteBarRepository),
            store=store,
            bus=bus,
            clock=clock,
            logger=loggers.get("optimization.signal"),
        )
        risk_numbers = _numbers(
            optimizer_config.get("risk", {})  # type: ignore[arg-type]
        )
        risk_service = RiskOptimizationService(
            slippage_r=risk_numbers.get("slippage_r", 0.01),
            exchange_id="toobit",
            base_params=base_params,
            settings=_settings(optimizer_config, "risk"),
            weights=ObjectiveWeights(),
            decision_service=container.resolve(DecisionService),
            bar_repository=container.resolve(SqliteBarRepository),
            store=store,
            bus=bus,
            clock=clock,
            logger=loggers.get("optimization.risk"),
        )
        container.register_instance(SignalOptimizationStore, store)
        container.register_instance(SignalOptimizationService, service)
        container.register_instance(RiskOptimizationService, risk_service)
        return [
            OptimizationPlatformModule(
                store=store,
                logger=loggers.get("optimization.module"),
            )
        ]


APEX_PLUGIN = OptimizationPlatformPlugin()
