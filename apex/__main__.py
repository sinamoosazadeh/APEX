"""APEX entrypoint: ``python -m apex``.

Boots the kernel through the full startup sequence, reports status and
shuts down cleanly (Constitution 4.6: the project is runnable at the
end of every phase). ``--check`` boots and exits, which doubles as a
configuration validation gate for CI and deployments.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from apex import __version__
from apex.core.exceptions import ApexError
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
    parser.add_argument(
        "--version",
        action="version",
        version=f"apex {__version__}",
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
        f"  modules      : {', '.join(status.modules_started) or '(none registered)'}",
        f"  services     : {len(status.services_registered)} registered",
        f"  events       : {status.events_journaled} journaled",
    ]
    return "\n".join(lines)


async def run(config_dir: Path) -> KernelStatus:
    """Boot the kernel, capture status, shut down cleanly."""
    kernel = Kernel(config_dir=config_dir)
    status = await kernel.boot()
    try:
        return status
    finally:
        await kernel.shutdown()


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args(argv)
    try:
        status = asyncio.run(run(args.config_dir))
    except ApexError as error:
        sys.stderr.write(f"boot failed: {error}\n")
        return EXIT_FAILURE
    sys.stdout.write(render_status(status) + "\n")
    if args.check:
        sys.stdout.write("check passed\n")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
