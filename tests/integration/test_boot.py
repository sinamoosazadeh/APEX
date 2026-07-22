"""Integration: full kernel boot, module lifecycle, CLI entrypoint."""

import asyncio
from pathlib import Path

import pytest
from apex.__main__ import main
from apex.contracts.engines import IMarketDataGateway
from apex.core.config import AppConfig
from apex.core.contracts.interfaces import IClock, IEventBus, ILogger, IStorage
from apex.core.enums import HealthState, ModuleState
from apex.core.events.catalog import SystemEvent
from apex.core.events.journal import EventJournal
from apex.core.exceptions import DataError, KernelError
from apex.data.pipeline import BarIngestionPipeline
from apex.features.pipeline import FeatureComputationPipeline
from apex.features.registry import FeatureRegistry
from apex.kernel.kernel import Kernel
from apex.storage.bars import SqliteBarRepository
from apex.storage.sqlite import SqliteKeyValueStorage

pytestmark = pytest.mark.integration


class RecordingModule:
    """A real module that records its lifecycle."""

    def __init__(self, name: str, dependencies: tuple[str, ...] = ()) -> None:
        self._name = name
        self._dependencies = dependencies
        self.events: list[str] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def dependencies(self) -> tuple[str, ...]:
        return self._dependencies

    async def start(self) -> None:
        self.events.append("start")

    async def stop(self) -> None:
        self.events.append("stop")

    def health(self) -> HealthState:
        return HealthState.HEALTHY


class FailingModule(RecordingModule):
    async def start(self) -> None:
        raise DataError("gateway unreachable", code="DAT-050")


class TestKernelBoot:
    def test_boot_and_shutdown_sequence(self, config_dir: Path) -> None:
        kernel = Kernel(config_dir=config_dir)
        first = RecordingModule("event_recorder")
        second = RecordingModule("consumer", dependencies=("event_recorder",))
        kernel.modules.register(second)
        kernel.modules.register(first)

        async def scenario() -> None:
            status = await kernel.boot()
            assert kernel.is_running
            assert status.health is HealthState.HEALTHY
            assert status.plugins_loaded == (
                "storage_core",
                "toobit_connector",
                "feature_platform",
                "probability_platform",
                "decision_platform",
                "optimization_platform",
                "portfolio_platform",
                "execution_platform",
            )
            # Deterministic topological order with alphabetical tie-breaks.
            assert status.modules_started == (
                "event_recorder",
                "storage_core",
                "consumer",
                "event_archive",
                "market_data",
                "feature_platform",
                "probability_platform",
                "decision_platform",
                "optimization_platform",
                "portfolio_platform",
                "execution_platform",
            )
            assert status.events_journaled >= 10  # booting, config, modules, started
            await kernel.shutdown()
            assert not kernel.is_running

        asyncio.run(scenario())
        assert first.events == ["start", "stop"]
        assert second.events == ["start", "stop"]
        # Shutdown order is the reverse of start order.
        assert kernel.modules.state_of("consumer") is ModuleState.STOPPED
        assert kernel.modules.state_of("market_data") is ModuleState.STOPPED

    def test_boot_registers_core_services(self, config_dir: Path) -> None:
        kernel = Kernel(config_dir=config_dir)

        async def scenario() -> None:
            await kernel.boot()
            assert kernel.container.resolve(AppConfig).system.app_name == "apex"
            assert kernel.container.contains(IEventBus)
            assert kernel.container.contains(IClock)
            assert kernel.container.contains(ILogger)
            assert kernel.container.contains(EventJournal)
            # Plugin-provided services.
            assert kernel.container.contains(IStorage)
            assert kernel.container.contains(IMarketDataGateway)
            assert kernel.container.contains(BarIngestionPipeline)
            assert kernel.container.contains(SqliteBarRepository)
            assert kernel.container.contains(FeatureComputationPipeline)
            assert kernel.container.contains(FeatureRegistry)
            await kernel.shutdown()

        asyncio.run(scenario())

    def test_event_archive_persists_boot_events(self, config_dir: Path) -> None:
        kernel = Kernel(config_dir=config_dir)

        async def scenario() -> None:
            await kernel.boot()
            storage = kernel.container.resolve(SqliteKeyValueStorage)
            # Sequence 0 is the kernel booting event, caught up from the journal.
            first = await storage.read("events", f"{0:020d}")
            assert first is not None and b"system.kernel.booting" in first
            await kernel.shutdown()

        asyncio.run(scenario())

    def test_kernel_lifecycle_events_are_journaled(self, config_dir: Path) -> None:
        kernel = Kernel(config_dir=config_dir)

        async def scenario() -> list[str]:
            await kernel.boot()
            journal = kernel.container.resolve(EventJournal)
            await kernel.shutdown()
            return [event.event_type for event in journal.replay()]

        event_types = asyncio.run(scenario())
        for expected in (
            SystemEvent.KERNEL_BOOTING,
            SystemEvent.CONFIG_LOADED,
            SystemEvent.KERNEL_STARTED,
            SystemEvent.KERNEL_STOPPING,
            SystemEvent.KERNEL_STOPPED,
        ):
            assert expected.value in event_types

    def test_module_failure_aborts_boot(self, config_dir: Path) -> None:
        kernel = Kernel(config_dir=config_dir)
        kernel.modules.register(FailingModule("broken_gateway"))

        async def scenario() -> None:
            await kernel.boot()

        with pytest.raises(KernelError) as excinfo:
            asyncio.run(scenario())
        assert excinfo.value.code == "KRN-031"
        assert kernel.modules.state_of("broken_gateway") is ModuleState.FAILED

    def test_double_boot_rejected(self, config_dir: Path) -> None:
        kernel = Kernel(config_dir=config_dir)

        async def scenario() -> None:
            await kernel.boot()
            try:
                with pytest.raises(KernelError):
                    await kernel.boot()
            finally:
                await kernel.shutdown()

        asyncio.run(scenario())

    def test_shutdown_is_idempotent(self, config_dir: Path) -> None:
        kernel = Kernel(config_dir=config_dir)

        async def scenario() -> None:
            await kernel.boot()
            await kernel.shutdown()
            await kernel.shutdown()  # second call is a no-op

        asyncio.run(scenario())


class TestCli:
    def test_cli_boot_check(
        self, config_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main(["--config-dir", str(config_dir), "--check"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "APEX" in captured.out and "ready" in captured.out
        assert "check passed" in captured.out

    def test_cli_fails_cleanly_on_bad_config(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main(["--config-dir", str(tmp_path / "missing"), "--check"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "boot failed" in captured.err
        assert "CFG-001" in captured.err
