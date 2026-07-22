"""APEX entrypoint: ``python -m apex``.

Commands:
- (default)          boot, report status, shut down cleanly
- ``--check``        boot and exit; the CI/deployment configuration gate
- ``ingest``         pull history for one series into the bar store
- ``sync``           catch up every configured series to the present
- ``stream``         sync, then consume the live WebSocket feed for a
                     bounded duration (bars close, ticks persist)
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
import sys
from pathlib import Path

from apex import __version__
from apex.core.config import AppConfig
from apex.core.contracts.interfaces import IClock
from apex.core.enums import Timeframe
from apex.core.exceptions import ApexError, ValidationError
from apex.data.catchup import CatchUpReport, CatchUpService
from apex.data.pipeline import BarIngestionPipeline, IngestionSummary
from apex.data.streaming import MarketStreamService, StreamStats
from apex.decision.service import DecisionService, DecisionSummary
from apex.features.pipeline import FeatureComputationPipeline, FeatureComputationSummary
from apex.kernel.kernel import Kernel, KernelStatus
from apex.optimization.risk.service import RiskOptimizationService
from apex.optimization.signal.service import OptimizationSummary, SignalOptimizationService
from apex.probability.service import ProbabilityService, ProbabilitySummary

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
    """Boot, decide over stored assessments, shut down."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        config = kernel.container.resolve(AppConfig)
        clock = kernel.container.resolve(IClock)  # type: ignore[type-abstract]
        service = kernel.container.resolve(DecisionService)
        count = bars if bars > 0 else config.market.history_bars
        now = clock.now()
        aligned_end = now.floor(timeframe.duration_ms).add_ms(timeframe.duration_ms)
        start = aligned_end.add_ms(-count * timeframe.duration_ms)
        result = await service.compute(symbol, timeframe, start=start, end=aligned_end)
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
    """Boot, assess stored feature vectors, shut down."""
    kernel = Kernel(config_dir=config_dir)
    await kernel.boot()
    try:
        config = kernel.container.resolve(AppConfig)
        clock = kernel.container.resolve(IClock)  # type: ignore[type-abstract]
        service = kernel.container.resolve(ProbabilityService)
        count = bars if bars > 0 else config.market.history_bars
        now = clock.now()
        aligned_end = now.floor(timeframe.duration_ms).add_ms(timeframe.duration_ms)
        start = aligned_end.add_ms(-count * timeframe.duration_ms)
        result = await service.compute(symbol, timeframe, start=start, end=aligned_end)
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
        if args.command in ("features", "probability", "decide"):
            return _run_windowed_command(args)
        if args.command in ("optimize-signal", "optimize-risk"):
            return _run_optimizer_command(args)
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
