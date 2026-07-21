"""Plugin system: manifest contract and loader validation."""

import io

import pytest
from apex.core.enums import PluginKind, StabilityLevel
from apex.core.exceptions import KernelError, ValidationError
from apex.core.logging import LogFormat, LoggerFactory, LogLevel, StructuredLogger
from apex.core.time.clock import ManualClock
from apex.core.versioning import SemanticVersion
from apex.kernel.container import ServiceContainer
from apex.kernel.modules import ModuleRegistry
from apex.plugins.contract import PluginManifest
from apex.plugins.loader import PluginLoader, safe_load

from tests.conftest import T0
from tests.unit.plugins.fixtures.good_plugin import MarkerService

FIXTURES = "tests.unit.plugins.fixtures"


def make_logger() -> StructuredLogger:
    factory = LoggerFactory(
        clock=ManualClock(T0),
        level=LogLevel.CRITICAL,
        log_format=LogFormat.JSON,
        stream=io.StringIO(),
    )
    return factory.get("test.plugins")


def make_loader() -> tuple[PluginLoader, ServiceContainer, ModuleRegistry]:
    container = ServiceContainer()
    registry = ModuleRegistry()
    loader = PluginLoader(container=container, registry=registry, logger=make_logger())
    return loader, container, registry


class TestManifest:
    def test_valid_manifest(self) -> None:
        manifest = PluginManifest(
            name="sample",
            version=SemanticVersion(1, 0, 0),
            kind=PluginKind.INDICATOR,
            api_version=SemanticVersion(1, 0, 0),
            description="sample plugin",
            stability=StabilityLevel.BETA,
        )
        assert manifest.name == "sample"

    def test_name_must_be_lowercase(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            PluginManifest(
                name="Sample",
                version=SemanticVersion(1, 0, 0),
                kind=PluginKind.INDICATOR,
                api_version=SemanticVersion(1, 0, 0),
                description="x",
            )
        assert excinfo.value.code == "VAL-120"

    def test_description_required(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            PluginManifest(
                name="sample",
                version=SemanticVersion(1, 0, 0),
                kind=PluginKind.INDICATOR,
                api_version=SemanticVersion(1, 0, 0),
                description="",
            )
        assert excinfo.value.code == "VAL-121"


class TestLoader:
    def test_loads_and_registers(self) -> None:
        loader, container, registry = make_loader()
        loaded = loader.load_all((f"{FIXTURES}.good_plugin",))
        assert [record.manifest.name for record in loaded] == ["good_plugin"]
        assert loaded[0].module_names == ("good_module",)
        assert registry.get("good_module").name == "good_module"
        assert container.resolve(MarkerService).label == "wired-by-plugin"

    def test_dependency_closure_satisfied(self) -> None:
        loader, _, _ = make_loader()
        loaded = loader.load_all(
            (f"{FIXTURES}.good_plugin", f"{FIXTURES}.needy_plugin")
        )
        assert len(loaded) == 2

    def test_missing_dependency_rejected(self) -> None:
        loader, _, _ = make_loader()
        with pytest.raises(KernelError) as excinfo:
            loader.load_all((f"{FIXTURES}.needy_plugin",))
        assert excinfo.value.code == "KRN-045"

    def test_incompatible_api_version_rejected(self) -> None:
        loader, _, _ = make_loader()
        with pytest.raises(KernelError) as excinfo:
            loader.load_all((f"{FIXTURES}.incompatible_plugin",))
        assert excinfo.value.code == "KRN-044"

    def test_module_without_plugin_attribute_rejected(self) -> None:
        loader, _, _ = make_loader()
        with pytest.raises(KernelError) as excinfo:
            loader.load_all((f"{FIXTURES}.not_a_plugin",))
        assert excinfo.value.code == "KRN-041"

    def test_unimportable_module_rejected(self) -> None:
        loader, _, _ = make_loader()
        with pytest.raises(KernelError) as excinfo:
            safe_load(loader, ("no.such.module.path",))
        assert excinfo.value.code == "KRN-040"

    def test_duplicate_plugin_rejected(self) -> None:
        loader, _, _ = make_loader()
        with pytest.raises(KernelError) as excinfo:
            loader.load_all((f"{FIXTURES}.good_plugin", f"{FIXTURES}.good_plugin"))
        assert excinfo.value.code in ("KRN-043", "KRN-010")
