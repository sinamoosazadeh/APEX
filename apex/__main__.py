"""APEX entrypoint: ``python -m apex``.

Commands:
- (default)          boot, report status, shut down cleanly
- ``--check``        boot and exit; the CI/deployment configuration gate
- ``ingest``         pull history for one series into the bar store
- ``sync``           catch up every configured series to the present
- ``stream``         sync, then consume the live WebSocket feed for a
                     bounded duration (bars close, ticks persist)
- ``run``            the live operational loop: streamed bars ->
                     features -> assessment -> decision -> execution ->
                     portfolio -> research, monitored end to end
- ``monitor``        the unified operations status (alerts, health,
                     kill switch, error budget; ``--snapshot`` stores one)
- ``telegram``       the Telegram console (long-polls the Bot API)
- ``execute``        execute the latest fired signal (paper unless
                     ``--live`` with run_mode live + credentials)
- ``research``       run a research study: attribution, learning fold,
                     calibration measurement, drift detection
- ``orchestrate``    enqueue/drain optimization jobs (Book V part 7)
- ``portfolio``      rebuild the governed portfolio from stored
                     decisions across one or more symbols
- ``optimize-risk``  run the ten-stage Book V risk optimizer
- ``optimize-signal`` run the ten-stage Book V signal optimizer
- ``decide``         run the Central Decision Kernel over stored
  assessments (signals, vetoes, stand-asides)
- ``probability``    assess stored feature vectors into calibrated
  per-side probabilities
- ``features``       compute registered feature families over stored
                     confirmed bars into the feature store

The project stays runnable at the end of every phase (Constitution 4.6).
"""

import argparse
import asyncio
import signal as os_signal
import sys
from collections.abc import Callable
from pathlib import Path

from apex import __version__
from apex.core.config import AppConfig
from apex.core.contracts.interfaces import IClock
from apex.core.enums import Timeframe
from apex.core.exceptions import (
    ApexError,
    SecurityError,
    TelegramError,
    ValidationError,
)
from apex.data.catchup import CatchUpReport, CatchUpService
from apex.data.pipeline import BarIngestionPipeline, IngestionSummary
from apex.data.streaming import MarketStreamService, StreamStats
from apex.decision.service import DecisionService, DecisionSummary
from apex.deployment.cli import run_backup, run_package, run_restore, run_schedule
from apex.execution.service import ExecutionService, ExecutionSummary
from apex.features.pipeline import FeatureComputationPipeline, FeatureComputationSummary
from apex.kernel.kernel import Kernel, KernelStatus
from apex.monitoring.loop import LoopStats, OperationsLoopService
from apex.monitoring.records import AlertRecord, KillSwitchLevel, OperationsStatus
from apex.monitoring.service import MonitoringService
from apex.optimization.risk.service import RiskOptimizationService
from apex.optimization.signal.service import OptimizationSummary, SignalOptimizationService
from apex.portfolio.service import PortfolioService, PortfolioSummary
from apex.probability.service import ProbabilityService, ProbabilitySummary
from apex.research.service import OrchestrationSummary, ResearchService, ResearchSummary
from apex.security.cli import (
    build_preflight,
    run_audit,
    run_secrets,
    run_secure_check,
)
from apex.telegram.service import ConsoleStats, TelegramConsoleService

DEFAULT_CONFIG_DIR = Path("config")

EXIT_OK = 0
EXIT_FAILURE = 1


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="apex",
        description="APEX - Autonomous Probabilistic Execution eXchange",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=DEFAULT_CONFIG_DIR,
        help="directory containing the APEX YAML configuration set",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="boot, validate and exit (configuration/boot gate)",
    )
    parser.add_argument("--version", action="version", version=f"apex {__version__}")
    subcommands = parser.add_subparsers(dest="command")
    ingest = subcommands.add_parser(
        "ingest",
        help="fetch market history into the bar store",
    )
    ingest.add_argument("--symbol", required=True, help="instrument symbol, e.g. BTCUSDT")
    ingest.add_argument(
        "--timeframe",
        required=True,
        choices=sorted(tf.value for tf in Timeframe),
        help="bar timeframe",
    )
    ingest.add_argument(
        "--bars",
        type=int,
        default=0,
        help="number of most-recent bars to fetch (default: market.history_bars)",
    )
    subcommands.add_parser(
        "sync",
        help="catch up every configured series to the present",
    )
    stream = subcommands.add_parser(
        "stream",
        help="sync, then consume the live feed for a bounded duration",
    )
    stream.add_argument(
        "--seconds",
        type=int,
        default=60,
        help="how long to stream before shutting down cleanly",
    )
    run_loop_parser = subcommands.add_parser(
        "run",
        help="the monitored live operational loop over streamed bars",
    )
    run_loop_parser.add_argument(
        "--symbol",
        action="append",
        dest="symbols",
        default=None,
        help="instrument symbol (repeatable; default: configured set)",
    )
    run_loop_parser.add_argument(
        "--timeframe",
        action="append",
        dest="timeframes",
        choices=sorted(tf.value for tf in Timeframe),
        default=None,
        help="bar timeframe (repeatable; default: configured set)",
    )
    run_loop_parser.add_argument(
        "--seconds",
        type=int,
        default=0,
        help="bounded session length; 0 runs until SIGINT/SIGTERM",
    )
    run_loop_parser.add_argument(
        "--live",
        action="store_true",
        help="execute signals at the venue (run_mode live + credentials)",
    )
    run_loop_parser.add_argument(
        "--orchestrate",
        action="store_true",
        help="drain one queued optimization job between bars",
    )
    run_loop_parser.add_argument(
        "--telegram",
        action="store_true",
        help="run the Telegram console beside the loop",
    )
    monitor = subcommands.add_parser(
        "monitor",
        help="render the unified operations status",
    )
    monitor.add_argument(
        "--snapshot",
        action="store_true",
        help="store a state snapshot before rendering",
    )
    monitor.add_argument(
        "--alerts",
        type=int,
        default=5,
        help="how many recent alerts to list",
    )
    telegram = subcommands.add_parser(
        "telegram",
        help="run the Telegram console (long-polls the Bot API)",
    )
    telegram.add_argument(
        "--seconds",
        type=int,
        default=0,
        help="bounded session length; 0 runs until SIGINT/SIGTERM",
    )
    subcommands.add_parser(
        "package",
        help="build the signed, checksummed release package (29.25)",
    )
    subcommands.add_parser(
        "backup",
        help="back up the durable state consistently (13.19)",
    )
    restore = subcommands.add_parser(
        "restore",
        help="verified restore of a backup archive (13.20)",
    )
    restore.add_argument("--archive", required=True, help="backup archive path")
    restore.add_argument(
        "--force", action="store_true", help="overwrite existing state"
    )
    restore.add_argument(
        "--into", default=None, help="alternate target directory"
    )
    schedule = subcommands.add_parser(
        "schedule",
        help="resource-aware recurring jobs (Book V part 7)",
    )
    schedule.add_argument(
        "--run",
        action="store_true",
        help="execute due jobs (default: status only)",
    )
    secure_check = subcommands.add_parser(
        "secure-check",
        help="run the secure-boot preflight (Book I 13.11)",
    )
    secure_check.add_argument(
        "--live",
        action="store_true",
        help="apply live-trading requirements (seal, credentials)",
    )
    secrets = subcommands.add_parser(
        "secrets",
        help="manage the encrypted vault (values only via --from-env)",
    )
    secrets.add_argument(
        "action",
        choices=("list", "set", "delete", "rotate", "seal"),
        help="vault operation",
    )
    secrets.add_argument("--name", default=None, help="secret name (set/delete)")
    secrets.add_argument(
        "--from-env",
        dest="from_env",
        default=None,
        help="environment variable carrying the value (set/rotate)",
    )
    audit = subcommands.add_parser(
        "audit",
        help="verify and tail the immutable audit ledger (25.16)",
    )
    audit.add_argument(
        "--tail", type=int, default=10, help="newest entries to list"
    )
    kill = subcommands.add_parser(
        "kill",
        help="operate the kill switch (10.25/25.29)",
    )
    kill.add_argument(
        "--engage",
        choices=sorted(
            level.value
            for level in KillSwitchLevel
            if level is not KillSwitchLevel.NONE
        ),
        default=None,
        help="engage a restrictive level (flattened closes positions)",
    )
    kill.add_argument(
        "--release", action="store_true", help="return to normal trading"
    )
    kill.add_argument(
        "--reason", default="operator request", help="transition reason"
    )
    features = subcommands.add_parser(
        "features",
        help="compute feature families over stored confirmed bars",
    )
    features.add_argument("--symbol", required=True, help="instrument symbol")
    features.add_argument(
        "--timeframe",
        required=True,
        choices=sorted(tf.value for tf in Timeframe),
        help="bar timeframe",
    )
    features.add_argument(
        "--bars",
        type=int,
        default=0,
        help="window of most-recent bars (default: market.history_bars)",
    )
    probability = subcommands.add_parser(
        "probability",
        help="assess stored feature vectors into calibrated probabilities",
    )
    probability.add_argument("--symbol", required=True, help="instrument symbol")
    probability.add_argument(
        "--timeframe",
        required=True,
        choices=sorted(tf.value for tf in Timeframe),
        help="bar timeframe",
    )
    probability.add_argument(
        "--bars",
        type=int,
        default=0,
        help="window of most-recent bars (default: market.history_bars)",
    )
    decide = subcommands.add_parser(
        "decide",
        help="run the Central Decision Kernel over stored assessments",
    )
    decide.add_argument("--symbol", required=True, help="instrument symbol")
    decide.add_argument(
        "--timeframe",
        required=True,
        choices=sorted(tf.value for tf in Timeframe),
        help="bar timeframe",
    )
    decide.add_argument(
        "--bars",
        type=int,
        default=0,
        help="window of most-recent bars (default: market.history_bars)",
    )
    optimize = subcommands.add_parser(
        "optimize-signal",
        help="run the ten-stage signal optimizer over one series",
    )
    optimize.add_argument("--symbol", required=True, help="instrument symbol")
    optimize.add_argument(
        "--timeframe",
        required=True,
        choices=sorted(tf.value for tf in Timeframe),
        help="bar timeframe",
    )
    optimize.add_argument(
        "--bars",
        type=int,
        default=0,
        help="window of most-recent bars (default: market.history_bars)",
    )
    optimize.add_argument(
        "--seed", type=int, default=7, help="deterministic optimization seed"
    )
    optimize_risk = subcommands.add_parser(
        "optimize-risk",
        help="run the ten-stage risk optimizer over the fixed decisions",
    )
    optimize_risk.add_argument("--symbol", required=True, help="instrument symbol")
    optimize_risk.add_argument(
        "--timeframe",
        required=True,
        choices=sorted(tf.value for tf in Timeframe),
        help="bar timeframe",
    )
    optimize_risk.add_argument(
        "--bars",
        type=int,
        default=0,
        help="window of most-recent bars (default: market.history_bars)",
    )
    optimize_risk.add_argument(
        "--seed", type=int, default=7, help="deterministic optimization seed"
    )
    portfolio = subcommands.add_parser(
        "portfolio",
        help="rebuild the governed portfolio from stored decisions",
    )
    portfolio.add_argument(
        "--symbol",
        required=True,
        action="append",
        dest="symbols",
        help="instrument symbol (repeatable for a multi-series portfolio)",
    )
    portfolio.add_argument(
        "--timeframe",
        required=True,
        choices=sorted(tf.value for tf in Timeframe),
        help="bar timeframe",
    )
    portfolio.add_argument(
        "--bars",
        type=int,
        default=0,
        help="window of most-recent bars (default: market.history_bars)",
    )
    execute = subcommands.add_parser(
        "execute",
        help="execute the latest fired signal (paper unless --live)",
    )
    execute.add_argument("--symbol", required=True, help="instrument symbol")
    execute.add_argument(
        "--timeframe",
        required=True,
        choices=sorted(tf.value for tf in Timeframe),
        help="bar timeframe",
    )
    execute.add_argument(
        "--bars",
        type=int,
        default=0,
        help="signal search window in bars (default: market.history_bars)",
    )
    execute.add_argument(
        "--live",
        action="store_true",
        help="execute at the venue (requires run_mode live + credentials)",
    )
    research = subcommands.add_parser(
        "research",
        help="run a research study: attribution, learning, calibration, drift",
    )
    research.add_argument(
        "--symbol",
        required=True,
        action="append",
        dest="symbols",
        help="instrument symbol (repeatable)",
    )
    research.add_argument(
        "--timeframe",
        required=True,
        choices=sorted(tf.value for tf in Timeframe),
        help="bar timeframe",
    )
    research.add_argument(
        "--bars",
        type=int,
        default=0,
        help="study window in bars (default: market.history_bars)",
    )
    orchestrate = subcommands.add_parser(
        "orchestrate",
        help="drain queued optimization jobs (Book V part 7)",
    )
    orchestrate.add_argument(
        "--limit", type=int, default=2, help="jobs to drain this run"
    )
    orchestrate.add_argument(
        "--enqueue",
        action="store_true",
        help="queue a signal+risk cycle for the configured symbols first",
    )
    orchestrate.add_argument(
        "--timeframe",
        default="1h",
        choices=sorted(tf.value for tf in Timeframe),
        help="cycle timeframe when enqueueing",
    )
    orchestrate.add_argument(
        "--bars",
        type=int,
        default=0,
        help="job window in bars (default: research orchestrator setting)",
    )
    return parser


def render_status(status: KernelStatus) -> str:
    """Human-readable boot report."""
    lines = [
        f"APEX {__version__} ready",
        f"  session      : {status.session_id}",
        f"  app          : {status.app_name}",
        f"  environment  : {status.environment}",
        f"  run mode     : {status.run_mode}",
        f"  config hash  : {status.config_hash[:16]}...",
        f"  health       : {status.health.value}",
        f"  plugins      : {', '.join(status.plugins_loaded) or '(none)'}",
        f"  modules      : {', '.join(status.modules_started) or '(none registered)'}",
        f"  services     : {len(status.services_registered)} registered",
        f"  events       : {status.events_journaled} journaled",
    ]
    return "\n".join(lines)


def render_summary(summary: IngestionSummary) -> str:
    """Human-readable ingestion report."""
    first = str(summary.first_open) if summary.first_open else "-"
    last = str(summary.last_open) if summary.last_open else "-"
    lines = [
        f"ingestion complete: {summary.exchange} {summary.symbol} {summary.timeframe.value}",
        f"  fetched      : {summary.fetched}",
        f"  stored       : {summary.stored}",
        f"  closed bars  : {summary.closed_bars}",
        f"  forming bars : {summary.forming_bars}",
        f"  gaps         : {summary.gap_count} ({summary.missing_bars} missing bars)",
        f"  range        : {first} .. {last}",
    ]
    return "\n".join(lines)


async def run_status(config_dir: Path) -> KernelStatus:
    """Boot the kernel, capture status, shut down cleanly."""
    kernel = Kernel(config_dir=config_dir)
    status = await kernel.boot()
    try:
        return status
    finally:
        await kernel.shutdown()


def render_catchup(report: CatchUpReport) -> str:
    """Human-readable catch-up report."""
    lines = [f"sync complete: {report.succeeded} ok, {report.failed} failed"]
    for symbol, timeframe, result in report.results:
        if result.ok:
            summary = result.unwrap()
            lines.append(
                f"  {symbol} {timeframe.value}: +{summary.stored} bars "
                f"({summary.gap_count} gaps)"
            )
        else:
            assert result.error is not None
            lines.append(f"  {symbol} {timeframe.value}: FAILED {result.error}")
    return "\n".join(lines)


def render_stream(stats: StreamStats) -> str:
    """Human-readable streaming report."""
    return "\n".join(
        [
            "stream session complete",
            f"  messages     : {stats.messages}",
            f"  bar updates  : {stats.bars_updated}",
            f"  bars closed  : {stats.bars_closed}",
            f"  ticks stored : {stats.ticks_stored}",
            f"  reconnects   : {stats.reconnects}",
        ]
    )


async def run_sync(config_dir: Path) -> CatchUpReport:
    """Boot, run one catch-up pass, shut down."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        return await kernel.container.resolve(CatchUpService).run_once()
    finally:
        await kernel.shutdown()


async def run_stream(config_dir: Path, seconds: int) -> tuple[CatchUpReport, StreamStats]:
    """Boot, catch up, then stream live for ``seconds``."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        report = await kernel.container.resolve(CatchUpService).run_once()
        stats = await kernel.container.resolve(MarketStreamService).run(
            duration_ms=seconds * 1000
        )
        return report, stats
    finally:
        await kernel.shutdown()


def render_optimization(summary: OptimizationSummary) -> str:
    """Human-readable optimization report."""
    return "\n".join(
        [
            f"signal optimization: {summary.symbol} {summary.timeframe.value}",
            f"  trials       : {summary.trials}",
            f"  best score   : {summary.best_score:.4f}",
            f"  confidence   : {summary.confidence:.2f}",
            f"  accepted     : {'yes' if summary.accepted else 'no'}",
            f"  artifact     : {summary.artifact_path or '(none - rejected)'}",
        ]
    )


async def run_optimize_risk(
    config_dir: Path,
    symbol: str,
    timeframe: Timeframe,
    bars: int,
    seed: int,
) -> OptimizationSummary:
    """Boot, risk-optimize one series, shut down."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        config = kernel.container.resolve(AppConfig)
        clock = kernel.container.resolve(IClock)  # type: ignore[type-abstract]
        service = kernel.container.resolve(RiskOptimizationService)
        count = bars if bars > 0 else config.market.history_bars
        now = clock.now()
        aligned_end = now.floor(timeframe.duration_ms).add_ms(timeframe.duration_ms)
        start = aligned_end.add_ms(-count * timeframe.duration_ms)
        result = await service.optimize(
            symbol, timeframe, start=start, end=aligned_end, seed=seed
        )
        return result.unwrap()
    finally:
        await kernel.shutdown()


async def run_optimize_signal(
    config_dir: Path,
    symbol: str,
    timeframe: Timeframe,
    bars: int,
    seed: int,
) -> OptimizationSummary:
    """Boot, optimize one series, shut down."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        config = kernel.container.resolve(AppConfig)
        clock = kernel.container.resolve(IClock)  # type: ignore[type-abstract]
        service = kernel.container.resolve(SignalOptimizationService)
        count = bars if bars > 0 else config.market.history_bars
        now = clock.now()
        aligned_end = now.floor(timeframe.duration_ms).add_ms(timeframe.duration_ms)
        start = aligned_end.add_ms(-count * timeframe.duration_ms)
        result = await service.optimize(
            symbol, timeframe, start=start, end=aligned_end, seed=seed
        )
        return result.unwrap()
    finally:
        await kernel.shutdown()


def render_decision(summary: DecisionSummary) -> str:
    """Human-readable decision run report."""
    return "\n".join(
        [
            f"decisions computed: {summary.exchange} {summary.symbol} "
            f"{summary.timeframe.value}",
            f"  bars loaded  : {summary.bars_loaded}",
            f"  bars decided : {summary.bars_decided}",
            f"  signals      : {summary.signals_fired} fired",
            f"  pendings     : {summary.pendings} armed",
            f"  vetoes       : {summary.vetoes}",
            f"  records      : {summary.records_stored} stored",
        ]
    )


async def run_decide(
    config_dir: Path,
    symbol: str,
    timeframe: Timeframe,
    bars: int,
) -> DecisionSummary:
    """Boot, decide over stored assessments, shut down.

    The runtime injector (Book V part 7): when research holds an
    active accepted signal artifact and/or a learning state for this
    series, the kernel runs with them.
    """
    from apex.decision.kernel import CentralDecisionKernel
    from apex.decision.plugin import decision_params_from_config

    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        config = kernel.container.resolve(AppConfig)
        clock = kernel.container.resolve(IClock)  # type: ignore[type-abstract]
        service = kernel.container.resolve(DecisionService)
        research = kernel.container.resolve(ResearchService)
        overrides = await research.active_overrides(symbol, timeframe)
        learning = await research.learning_state(symbol, timeframe)
        kernel_override = None
        if overrides or learning is not None:
            base = decision_params_from_config(config.market.decision)
            params = base.with_overrides(overrides) if overrides else base
            kernel_override = CentralDecisionKernel(
                params=params, clock=clock, learning=learning
            )
        count = bars if bars > 0 else config.market.history_bars
        now = clock.now()
        aligned_end = now.floor(timeframe.duration_ms).add_ms(timeframe.duration_ms)
        start = aligned_end.add_ms(-count * timeframe.duration_ms)
        result = await service.compute(
            symbol, timeframe, start=start, end=aligned_end,
            kernel_override=kernel_override,
        )
        return result.unwrap()
    finally:
        await kernel.shutdown()


def render_probability(summary: ProbabilitySummary) -> str:
    """Human-readable probability computation report."""
    return "\n".join(
        [
            f"probabilities assessed: {summary.exchange} {summary.symbol} "
            f"{summary.timeframe.value}",
            f"  bars loaded  : {summary.bars_loaded}",
            f"  bars assessed: {summary.bars_assessed}",
            f"  records      : {summary.records_stored} stored",
        ]
    )


async def run_probability(
    config_dir: Path,
    symbol: str,
    timeframe: Timeframe,
    bars: int,
) -> ProbabilitySummary:
    """Boot, assess stored feature vectors, shut down.

    The runtime injector (Book V part 7): with a learning state for
    this series, the engine runs with its channel factors.
    """
    from apex.probability.engine import ConfluenceProbabilityEngine
    from apex.probability.plugin import probability_params_from_config

    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        config = kernel.container.resolve(AppConfig)
        clock = kernel.container.resolve(IClock)  # type: ignore[type-abstract]
        service = kernel.container.resolve(ProbabilityService)
        research = kernel.container.resolve(ResearchService)
        learning = await research.learning_state(symbol, timeframe)
        engine_override = None
        if learning is not None:
            engine_override = ConfluenceProbabilityEngine(
                params=probability_params_from_config(config.market.probability),
                clock=clock,
                learning=learning,
            )
        count = bars if bars > 0 else config.market.history_bars
        now = clock.now()
        aligned_end = now.floor(timeframe.duration_ms).add_ms(timeframe.duration_ms)
        start = aligned_end.add_ms(-count * timeframe.duration_ms)
        result = await service.compute(
            symbol, timeframe, start=start, end=aligned_end,
            engine_override=engine_override,
        )
        return result.unwrap()
    finally:
        await kernel.shutdown()


def render_research(summary: ResearchSummary) -> str:
    """Human-readable research study report."""
    lines = [f"research study complete ({summary.timeframe.value})"]
    for study in summary.studies:
        drifting = [report.name for report in study.drifts if report.drifting]
        lines.extend(
            [
                f"  {study.symbol}:",
                f"    closed trades : {study.attribution.closed_trades} "
                f"({len(study.attribution.outcomes)} attributed)",
                f"    learning      : v{study.learning_version} "
                f"({study.attribution.closed_trades} outcomes folded)",
                f"    brier score   : {study.calibration.brier_score:.4f}",
                f"    drifting      : {', '.join(drifting) or 'none'}",
            ]
        )
    quality = summary.execution_quality
    lines.append(
        f"  executions   : {quality.executions} "
        f"(fill rate {quality.fill_rate:.2f}, avg slippage {quality.average_slippage})"
    )
    return "\n".join(lines)


async def run_research(
    config_dir: Path,
    symbols: tuple[str, ...],
    timeframe: Timeframe,
    bars: int,
) -> ResearchSummary:
    """Boot, run one research study, shut down."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        config = kernel.container.resolve(AppConfig)
        clock = kernel.container.resolve(IClock)  # type: ignore[type-abstract]
        service = kernel.container.resolve(ResearchService)
        count = bars if bars > 0 else config.market.history_bars
        now = clock.now()
        aligned_end = now.floor(timeframe.duration_ms).add_ms(timeframe.duration_ms)
        start = aligned_end.add_ms(-count * timeframe.duration_ms)
        result = await service.study(symbols, timeframe, start=start, end=aligned_end)
        return result.unwrap()
    finally:
        await kernel.shutdown()


def render_orchestration(summary: OrchestrationSummary) -> str:
    """Human-readable queue drain report."""
    lines = [
        "orchestration complete",
        f"  drained      : {summary.drained}",
        f"  completed    : {summary.completed}",
        f"  failed       : {summary.failed}",
        f"  activated    : {len(summary.activated)} artifact(s)",
    ]
    lines.extend(f"    - {path}" for path in summary.activated)
    lines.append(f"  shadowed     : {len(summary.shadowed)} artifact(s)")
    lines.extend(f"    - {path}" for path in summary.shadowed)
    return "\n".join(lines)


def _install_stop_handlers(*stoppers: Callable[[], None]) -> None:
    """SIGINT/SIGTERM ask every long-running service to stop."""

    def stop_all() -> None:
        for stopper in stoppers:
            stopper()

    try:
        loop = asyncio.get_running_loop()
        for signum in (os_signal.SIGINT, os_signal.SIGTERM):
            loop.add_signal_handler(signum, stop_all)
    except (NotImplementedError, RuntimeError, ValueError):
        sys.stderr.write("warning: signal-driven shutdown unavailable\n")


def render_loop(stats: LoopStats) -> str:
    """Human-readable operational-loop report."""
    return "\n".join(
        [
            "operational loop complete",
            f"  bars         : {stats.bars_processed} processed",
            f"  signals      : {stats.signals_fired} fired",
            f"  executions   : {stats.executions_filled} filled / "
            f"{stats.executions_attempted} attempted",
            f"  alerts       : {stats.alerts_raised} raised",
            f"  jobs         : {stats.jobs_drained} drained",
            f"  promotions   : {stats.promotions_evaluated} evaluated",
            f"  rollbacks    : {stats.rollbacks}",
            f"  snapshots    : {stats.snapshots_taken} taken",
            f"  reconnects   : {stats.stream_reconnects}",
        ]
    )


def render_console(stats: ConsoleStats) -> str:
    """Human-readable Telegram console report."""
    return "\n".join(
        [
            "telegram console session complete",
            f"  updates      : {stats.updates}",
            f"  commands     : {stats.commands}",
            f"  callbacks    : {stats.callbacks}",
            f"  notifications: {stats.notifications}",
            f"  denied       : {stats.denied}",
        ]
    )


def render_ops(status: OperationsStatus, alerts: list[AlertRecord]) -> str:
    """Human-readable operations center report (Book II 26.29)."""
    healthy = sum(
        1 for component in status.components if component.state.value == "healthy"
    )
    budget = status.error_budget
    lines = [
        "operations status",
        f"  health       : {status.overall_health.value} "
        f"({healthy}/{len(status.components)} components healthy)",
        f"  kill switch  : {status.kill_switch.value}"
        + (f" ({status.kill_switch_reason})" if status.kill_switch_reason else ""),
        f"  incidents    : {status.incidents_open} open",
        f"  equity       : {status.equity} (cash {status.cash})",
        f"  drawdown     : {status.drawdown:.4f}",
        f"  positions    : {status.open_positions} open",
        f"  trades       : {status.closed_trades} closed "
        f"(win rate {status.win_rate:.2f}, net R {status.r_sum:.2f})",
        f"  research     : {status.jobs_pending} pending / {status.jobs_running} "
        f"running jobs; {status.promotions_shadow} shadow / "
        f"{status.promotions_pending_approval} awaiting approval",
        f"  error budget : {budget.errors}/{budget.operations} "
        f"({budget.error_rate:.4f} vs {budget.budget:.4f}, "
        f"{'EXHAUSTED' if budget.exhausted else 'ok'})",
        f"  snapshots    : {status.snapshots_stored} stored",
    ]
    if status.heartbeats:
        beats = ", ".join(
            f"{beat.component}={beat.age_ms // 1000}s"
            + ("!" if beat.stale else "")
            for beat in status.heartbeats
        )
        lines.append(f"  heartbeats   : {beats}")
    if alerts:
        lines.append("  alerts:")
        lines.extend(
            f"    [{alert.severity.value}] {alert.message} (x{alert.count})"
            for alert in alerts
        )
    return "\n".join(lines)


async def run_loop(
    config_dir: Path,
    *,
    symbols: tuple[str, ...],
    timeframes: tuple[Timeframe, ...],
    seconds: int,
    live: bool,
    orchestrate: bool,
    telegram: bool,
) -> tuple[LoopStats, ConsoleStats | None]:
    """Boot, run the operational loop (and console), shut down."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        if live:
            preflight = await build_preflight(kernel).run(live=True)
            if not preflight.passed:
                raise SecurityError(
                    "secure preflight failed; live trading refused (13.11)",
                    code="SEC-040",
                    details={
                        "failures": ", ".join(
                            check.name
                            for check in preflight.checks
                            if not check.passed and not check.skipped
                        )
                    },
                )
        loop_service = kernel.container.resolve(OperationsLoopService)
        console: TelegramConsoleService | None = None
        if telegram:
            console = kernel.container.resolve(TelegramConsoleService)
            if not console.available:
                raise TelegramError(
                    "telegram console unavailable: set TELEGRAM_BOT_TOKEN and "
                    "TELEGRAM_ADMIN_CHAT_IDS and enable telegram.console",
                    code="TGM-004",
                )
        stoppers: list[Callable[[], None]] = [loop_service.request_stop]
        if console is not None:
            stoppers.append(console.request_stop)
        _install_stop_handlers(*stoppers)
        if console is None:
            stats = await loop_service.run(
                seconds=seconds,
                live=live,
                orchestrate=orchestrate,
                symbols=symbols,
                timeframes=timeframes,
            )
            return stats, None
        loop_run = loop_service.run(
            seconds=seconds,
            live=live,
            orchestrate=orchestrate,
            symbols=symbols,
            timeframes=timeframes,
        )
        console_run = console.run(seconds=seconds)
        loop_stats, console_stats = await asyncio.gather(loop_run, console_run)
        return loop_stats, console_stats
    finally:
        await kernel.shutdown()


async def run_monitor(
    config_dir: Path, *, snapshot: bool, alerts: int
) -> tuple[OperationsStatus, list[AlertRecord]]:
    """Boot, read the operations status, shut down."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        service = kernel.container.resolve(MonitoringService)
        if snapshot:
            await service.capture_snapshot()
        status = await service.ops_status()
        recent = await service.recent_alerts(limit=alerts)
        return status, recent
    finally:
        await kernel.shutdown()


async def run_telegram(config_dir: Path, *, seconds: int) -> ConsoleStats:
    """Boot, run the Telegram console, shut down."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        console = kernel.container.resolve(TelegramConsoleService)
        _install_stop_handlers(console.request_stop)
        return await console.run(seconds=seconds)
    finally:
        await kernel.shutdown()


async def run_orchestrate(
    config_dir: Path,
    *,
    limit: int,
    enqueue: bool,
    timeframe: Timeframe,
    bars: int,
) -> OrchestrationSummary:
    """Boot, optionally enqueue a cycle, drain jobs, shut down."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        config = kernel.container.resolve(AppConfig)
        service = kernel.container.resolve(ResearchService)
        if enqueue:
            await service.enqueue_cycle(
                config.market.symbols, (timeframe,), window_bars=bars
            )
        research_section = config.section("research").get("orchestrator", {})
        default_bars = 480
        if isinstance(research_section, dict):
            raw = research_section.get("default_window_bars", 480)
            if isinstance(raw, int) and not isinstance(raw, bool):
                default_bars = raw
        result = await service.orchestrate(
            limit=limit, default_window_bars=bars if bars > 0 else default_bars
        )
        return result.unwrap()
    finally:
        await kernel.shutdown()


def _run_research_command(args: argparse.Namespace) -> int:
    """Dispatch the research study command."""
    if args.bars < 0:
        raise ValidationError("--bars must be non-negative", code="VAL-130")
    summary = asyncio.run(
        run_research(
            args.config_dir, tuple(args.symbols), Timeframe(args.timeframe), args.bars
        )
    )
    sys.stdout.write(render_research(summary) + "\n")
    return EXIT_OK


def _run_orchestrate_command(args: argparse.Namespace) -> int:
    """Dispatch the orchestrator drain command."""
    if args.limit < 1:
        raise ValidationError("--limit must be >= 1", code="VAL-132")
    summary = asyncio.run(
        run_orchestrate(
            args.config_dir,
            limit=args.limit,
            enqueue=args.enqueue,
            timeframe=Timeframe(args.timeframe),
            bars=args.bars,
        )
    )
    sys.stdout.write(render_orchestration(summary) + "\n")
    return EXIT_OK


def render_portfolio(summary: PortfolioSummary) -> str:
    """Human-readable portfolio rebuild report."""
    return "\n".join(
        [
            f"portfolio rebuilt: {summary.portfolio_id} "
            f"({', '.join(summary.symbols)} {summary.timeframe.value})",
            f"  bars loaded  : {summary.bars_loaded}",
            f"  signals      : {summary.signals_seen} seen",
            f"  opened       : {summary.positions_opened} positions",
            f"  closed       : {summary.positions_closed} positions",
            f"  rejected     : {summary.signals_rejected} signals",
            f"  open now     : {summary.open_positions} positions",
            f"  snapshots    : {summary.snapshots_stored} stored",
            f"  final equity : {summary.final_equity}",
            f"  drawdown     : {summary.final_drawdown:.4f}",
        ]
    )


async def run_portfolio(
    config_dir: Path,
    symbols: tuple[str, ...],
    timeframe: Timeframe,
    bars: int,
) -> PortfolioSummary:
    """Boot, rebuild the portfolio from stored decisions, shut down."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        config = kernel.container.resolve(AppConfig)
        clock = kernel.container.resolve(IClock)  # type: ignore[type-abstract]
        service = kernel.container.resolve(PortfolioService)
        count = bars if bars > 0 else config.market.history_bars
        now = clock.now()
        aligned_end = now.floor(timeframe.duration_ms).add_ms(timeframe.duration_ms)
        start = aligned_end.add_ms(-count * timeframe.duration_ms)
        result = await service.rebuild(
            symbols, timeframe, start=start, end=aligned_end
        )
        return result.unwrap()
    finally:
        await kernel.shutdown()


def render_features(summary: FeatureComputationSummary) -> str:
    """Human-readable feature computation report."""
    return "\n".join(
        [
            f"features computed: {summary.exchange} {summary.symbol} "
            f"{summary.timeframe.value}",
            f"  bars loaded  : {summary.bars_loaded}",
            f"  engines run  : {summary.engines_run}",
            f"  families     : {', '.join(summary.families)}",
            f"  features     : {summary.features_stored} stored",
        ]
    )


async def run_features(
    config_dir: Path,
    symbol: str,
    timeframe: Timeframe,
    bars: int,
) -> FeatureComputationSummary:
    """Boot, compute features over stored bars, shut down."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        config = kernel.container.resolve(AppConfig)
        clock = kernel.container.resolve(IClock)  # type: ignore[type-abstract]
        pipeline = kernel.container.resolve(FeatureComputationPipeline)
        count = bars if bars > 0 else config.market.history_bars
        now = clock.now()
        aligned_end = now.floor(timeframe.duration_ms).add_ms(timeframe.duration_ms)
        start = aligned_end.add_ms(-count * timeframe.duration_ms)
        result = await pipeline.compute(symbol, timeframe, start=start, end=aligned_end)
        return result.unwrap()
    finally:
        await kernel.shutdown()


async def run_ingest(
    config_dir: Path,
    symbol: str,
    timeframe: Timeframe,
    bars: int,
) -> IngestionSummary:
    """Boot, ingest one series through the pipeline, shut down."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        config = kernel.container.resolve(AppConfig)
        clock = kernel.container.resolve(IClock)  # type: ignore[type-abstract]
        pipeline = kernel.container.resolve(BarIngestionPipeline)
        count = bars if bars > 0 else config.market.history_bars
        now = clock.now()
        aligned_end = now.floor(timeframe.duration_ms).add_ms(timeframe.duration_ms)
        start = aligned_end.add_ms(-count * timeframe.duration_ms)
        result = await pipeline.ingest(symbol, timeframe, start=start, end=aligned_end)
        return result.unwrap()
    finally:
        await kernel.shutdown()


def _run_windowed_command(args: argparse.Namespace) -> int:
    """Dispatch the bar-windowed compute commands (features, probability)."""
    if args.bars < 0:
        raise ValidationError("--bars must be non-negative", code="VAL-130")
    if args.command == "features":
        feature_summary = asyncio.run(
            run_features(
                args.config_dir, args.symbol, Timeframe(args.timeframe), args.bars
            )
        )
        sys.stdout.write(render_features(feature_summary) + "\n")
        return EXIT_OK
    if args.command == "decide":
        decision_summary = asyncio.run(
            run_decide(
                args.config_dir, args.symbol, Timeframe(args.timeframe), args.bars
            )
        )
        sys.stdout.write(render_decision(decision_summary) + "\n")
        return EXIT_OK
    probability_summary = asyncio.run(
        run_probability(
            args.config_dir, args.symbol, Timeframe(args.timeframe), args.bars
        )
    )
    sys.stdout.write(render_probability(probability_summary) + "\n")
    return EXIT_OK


def render_execution(summary: ExecutionSummary) -> str:
    """Human-readable execution report."""
    lines = [
        f"execution {summary.status}: {summary.symbol} {summary.timeframe.value} "
        f"({summary.mode})",
        f"  execution id : {summary.execution_id}",
        f"  direction    : {summary.direction}",
        f"  order type   : {summary.order_type}",
        f"  quantity     : {summary.filled_quantity} / {summary.requested_quantity}",
        f"  decision px  : {summary.decision_price}",
        f"  fill px      : {summary.fill_price or '-'}",
        f"  slippage     : {summary.slippage or '-'}",
        f"  fees         : {summary.fees}",
        f"  position     : {'opened' if summary.position_opened else 'not opened'}",
    ]
    if summary.reasons:
        lines.append(f"  reasons      : {', '.join(summary.reasons)}")
    return "\n".join(lines)


async def run_execute(
    config_dir: Path,
    symbol: str,
    timeframe: Timeframe,
    bars: int,
    live: bool,
) -> ExecutionSummary:
    """Boot, execute the latest fired signal, shut down."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        config = kernel.container.resolve(AppConfig)
        clock = kernel.container.resolve(IClock)  # type: ignore[type-abstract]
        service = kernel.container.resolve(ExecutionService)
        count = bars if bars > 0 else config.market.history_bars
        now = clock.now()
        aligned_end = now.floor(timeframe.duration_ms).add_ms(timeframe.duration_ms)
        start = aligned_end.add_ms(-count * timeframe.duration_ms)
        result = await service.execute_latest_signal(
            symbol, timeframe, start=start, end=aligned_end, live=live
        )
        return result.unwrap()
    finally:
        await kernel.shutdown()


def _run_execute_command(args: argparse.Namespace) -> int:
    """Dispatch the execution command."""
    if args.bars < 0:
        raise ValidationError("--bars must be non-negative", code="VAL-130")
    summary = asyncio.run(
        run_execute(
            args.config_dir,
            args.symbol,
            Timeframe(args.timeframe),
            args.bars,
            args.live,
        )
    )
    sys.stdout.write(render_execution(summary) + "\n")
    return EXIT_OK


def _run_portfolio_command(args: argparse.Namespace) -> int:
    """Dispatch the portfolio rebuild command."""
    if args.bars < 0:
        raise ValidationError("--bars must be non-negative", code="VAL-130")
    summary = asyncio.run(
        run_portfolio(
            args.config_dir,
            tuple(args.symbols),
            Timeframe(args.timeframe),
            args.bars,
        )
    )
    sys.stdout.write(render_portfolio(summary) + "\n")
    return EXIT_OK


def _run_loop_command(args: argparse.Namespace) -> int:
    """Dispatch the operational loop command."""
    if args.seconds < 0:
        raise ValidationError("--seconds must be non-negative", code="VAL-133")
    symbols = tuple(args.symbols) if args.symbols else ()
    timeframes = (
        tuple(Timeframe(raw) for raw in args.timeframes) if args.timeframes else ()
    )
    loop_stats, console_stats = asyncio.run(
        run_loop(
            args.config_dir,
            symbols=symbols,
            timeframes=timeframes,
            seconds=args.seconds,
            live=args.live,
            orchestrate=args.orchestrate,
            telegram=args.telegram,
        )
    )
    sys.stdout.write(render_loop(loop_stats) + "\n")
    if console_stats is not None:
        sys.stdout.write(render_console(console_stats) + "\n")
    return EXIT_OK


def _run_monitor_command(args: argparse.Namespace) -> int:
    """Dispatch the operations status command."""
    if args.alerts < 0:
        raise ValidationError("--alerts must be non-negative", code="VAL-134")
    status, recent = asyncio.run(
        run_monitor(args.config_dir, snapshot=args.snapshot, alerts=args.alerts)
    )
    sys.stdout.write(render_ops(status, recent) + "\n")
    return EXIT_OK


def _run_telegram_command(args: argparse.Namespace) -> int:
    """Dispatch the Telegram console command."""
    if args.seconds < 0:
        raise ValidationError("--seconds must be non-negative", code="VAL-133")
    stats = asyncio.run(run_telegram(args.config_dir, seconds=args.seconds))
    sys.stdout.write(render_console(stats) + "\n")
    return EXIT_OK


def _run_package_command(args: argparse.Namespace) -> int:
    """Dispatch release packaging."""
    lines = asyncio.run(run_package(args.config_dir, root=Path.cwd()))
    sys.stdout.write("\n".join(lines) + "\n")
    return EXIT_OK


def _run_backup_command(args: argparse.Namespace) -> int:
    """Dispatch the durable-state backup."""
    lines = asyncio.run(run_backup(args.config_dir))
    sys.stdout.write("\n".join(lines) + "\n")
    return EXIT_OK


def _run_restore_command(args: argparse.Namespace) -> int:
    """Dispatch the verified restore."""
    lines = asyncio.run(
        run_restore(
            args.config_dir,
            archive=Path(args.archive),
            force=args.force,
            into=Path(args.into) if args.into else None,
        )
    )
    sys.stdout.write("\n".join(lines) + "\n")
    return EXIT_OK


def _run_schedule_command(args: argparse.Namespace) -> int:
    """Dispatch the recurring-job planner."""
    lines = asyncio.run(run_schedule(args.config_dir, execute=args.run))
    sys.stdout.write("\n".join(lines) + "\n")
    return EXIT_OK


async def run_kill(
    config_dir: Path, *, engage: str | None, release: bool, reason: str
) -> list[str]:
    """Boot, operate (or read) the kill switch, shut down."""
    if engage is not None and release:
        raise ValidationError(
            "choose one of --engage / --release", code="VAL-144"
        )
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        engine = kernel.container.resolve(MonitoringService).kill_switch
        if engage is not None:
            record = await engine.engage(
                KillSwitchLevel(engage), reason=reason, actor="operator"
            )
            return [f"kill switch engaged: {record.level.value} ({reason})"]
        if release:
            await engine.release(reason=reason, actor="operator")
            return [f"kill switch released ({reason})"]
        return [f"kill switch: {(await engine.level()).value}"]
    finally:
        await kernel.shutdown()


def _run_secure_check_command(args: argparse.Namespace) -> int:
    """Dispatch the secure-boot preflight."""
    report = asyncio.run(run_secure_check(args.config_dir, live=args.live))
    sys.stdout.write("\n".join(report.lines()) + "\n")
    return EXIT_OK if report.passed else EXIT_FAILURE


def _run_secrets_command(args: argparse.Namespace) -> int:
    """Dispatch vault operations."""
    lines = asyncio.run(
        run_secrets(
            args.config_dir,
            action=args.action,
            name=args.name,
            from_env=args.from_env,
        )
    )
    sys.stdout.write("\n".join(lines) + "\n")
    return EXIT_OK


def _run_audit_command(args: argparse.Namespace) -> int:
    """Dispatch the audit ledger review."""
    if args.tail < 0:
        raise ValidationError("--tail must be non-negative", code="VAL-145")
    lines = asyncio.run(run_audit(args.config_dir, tail=args.tail))
    sys.stdout.write("\n".join(lines) + "\n")
    return EXIT_OK


def _run_kill_command(args: argparse.Namespace) -> int:
    """Dispatch kill-switch operations."""
    lines = asyncio.run(
        run_kill(
            args.config_dir,
            engage=args.engage,
            release=args.release,
            reason=args.reason,
        )
    )
    sys.stdout.write("\n".join(lines) + "\n")
    return EXIT_OK


def _run_optimizer_command(args: argparse.Namespace) -> int:
    """Dispatch the seeded optimizer commands."""
    runner = (
        run_optimize_signal if args.command == "optimize-signal" else run_optimize_risk
    )
    summary = asyncio.run(
        runner(
            args.config_dir, args.symbol, Timeframe(args.timeframe),
            args.bars, args.seed,
        )
    )
    label = "signal" if args.command == "optimize-signal" else "risk"
    sys.stdout.write(
        render_optimization(summary).replace("signal optimization", f"{label} optimization")
        + "\n"
    )
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args(argv)
    try:
        if args.command == "ingest":
            if args.bars < 0:
                raise ValidationError("--bars must be non-negative", code="VAL-130")
            summary = asyncio.run(
                run_ingest(
                    args.config_dir,
                    args.symbol,
                    Timeframe(args.timeframe),
                    args.bars,
                )
            )
            sys.stdout.write(render_summary(summary) + "\n")
            return EXIT_OK
        if args.command == "sync":
            report = asyncio.run(run_sync(args.config_dir))
            sys.stdout.write(render_catchup(report) + "\n")
            return EXIT_OK if report.failed == 0 else EXIT_FAILURE
        if args.command == "stream":
            if args.seconds < 1:
                raise ValidationError("--seconds must be >= 1", code="VAL-131")
            report, stats = asyncio.run(run_stream(args.config_dir, args.seconds))
            sys.stdout.write(render_catchup(report) + "\n")
            sys.stdout.write(render_stream(stats) + "\n")
            return EXIT_OK
        dispatchers = {
            "features": _run_windowed_command,
            "probability": _run_windowed_command,
            "decide": _run_windowed_command,
            "optimize-signal": _run_optimizer_command,
            "optimize-risk": _run_optimizer_command,
            "portfolio": _run_portfolio_command,
            "execute": _run_execute_command,
            "research": _run_research_command,
            "orchestrate": _run_orchestrate_command,
            "run": _run_loop_command,
            "monitor": _run_monitor_command,
            "telegram": _run_telegram_command,
            "secure-check": _run_secure_check_command,
            "secrets": _run_secrets_command,
            "audit": _run_audit_command,
            "kill": _run_kill_command,
            "package": _run_package_command,
            "backup": _run_backup_command,
            "restore": _run_restore_command,
            "schedule": _run_schedule_command,
        }
        handler = dispatchers.get(args.command or "")
        if handler is not None:
            return handler(args)
        status = asyncio.run(run_status(args.config_dir))
    except ApexError as error:
        stage = args.command if args.command else "boot"
        sys.stderr.write(f"{stage} failed: {error}\n")
        return EXIT_FAILURE
    sys.stdout.write(render_status(status) + "\n")
    if args.check:
        sys.stdout.write("check passed\n")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
