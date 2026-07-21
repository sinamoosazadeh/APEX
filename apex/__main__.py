"""APEX entrypoint: ``python -m apex``.

Commands:
- (default)          boot, report status, shut down cleanly
- ``--check``        boot and exit; the CI/deployment configuration gate
- ``ingest``         pull market history through the Toobit gateway into
                     the bar store and report the ingestion summary

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
from apex.data.pipeline import BarIngestionPipeline, IngestionSummary
from apex.kernel.kernel import Kernel, KernelStatus

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
        status = asyncio.run(run_status(args.config_dir))
    except ApexError as error:
        stage = "ingest" if args.command == "ingest" else "boot"
        sys.stderr.write(f"{stage} failed: {error}\n")
        return EXIT_FAILURE
    sys.stdout.write(render_status(status) + "\n")
    if args.check:
        sys.stdout.write("check passed\n")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
