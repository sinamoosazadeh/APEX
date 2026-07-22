"""Configuration platform: loading, schema gates, env overrides."""

from pathlib import Path

import pytest
from apex.core.config import load_config
from apex.core.enums import Environment, RunMode, Timeframe
from apex.core.exceptions import ConfigurationError
from apex.core.logging import LogFormat, LogLevel


class TestLoadConfig:
    def test_repository_config_set_is_valid(self, config_dir: Path) -> None:
        config = load_config(config_dir)
        assert config.system.app_name == "apex"
        assert config.system.environment is Environment.DEVELOPMENT
        assert config.system.run_mode is RunMode.BACKTEST
        assert config.logging.level is LogLevel.INFO
        assert config.logging.output_format is LogFormat.CONSOLE
        assert config.system.event_journal_capacity == 10000
        assert len(config.config_hash) == 64

    def test_all_phase_sections_present(self, config_dir: Path) -> None:
        config = load_config(config_dir)
        for name in (
            "signal",
            "risk",
            "optimizer",
            "portfolio",
            "research",
            "telemetry",
            "scheduler",
            "device",
        ):
            assert isinstance(config.section(name), dict)
        with pytest.raises(ConfigurationError):
            config.section("nonexistent")

    def test_market_config_parsed(self, config_dir: Path) -> None:
        config = load_config(config_dir)
        assert "BTCUSDT" in config.market.symbols
        assert Timeframe.H1 in config.market.timeframes
        assert config.market.history_bars >= 1
        assert 0.0 <= config.market.gap_penalty <= 1.0
        assert config.system.plugin_modules == (
            "apex.storage.plugin",
            "apex.data.toobit.plugin",
            "apex.features.plugin",
            "apex.probability.plugin",
            "apex.decision.plugin",
        )

    def test_exchange_config_parsed(self, config_dir: Path) -> None:
        config = load_config(config_dir)
        assert config.toobit.base_url.startswith("https://")
        assert config.toobit.kline_page_limit == 1000

    def test_bad_market_symbol_refuses_boot(self, config_dir: Path) -> None:
        text = (config_dir / "market.yaml").read_text(encoding="utf-8")
        (config_dir / "market.yaml").write_text(
            text.replace("- BTCUSDT", "- btc/usdt"), encoding="utf-8"
        )
        with pytest.raises(ConfigurationError):
            load_config(config_dir)

    def test_bad_timeframe_refuses_boot(self, config_dir: Path) -> None:
        text = (config_dir / "market.yaml").read_text(encoding="utf-8")
        (config_dir / "market.yaml").write_text(
            text.replace("- 1h", "- 7h"), encoding="utf-8"
        )
        with pytest.raises(ConfigurationError) as excinfo:
            load_config(config_dir)
        assert excinfo.value.code == "CFG-020"

    def test_http_exchange_url_refuses_boot(self, config_dir: Path) -> None:
        text = (config_dir / "exchange.yaml").read_text(encoding="utf-8")
        (config_dir / "exchange.yaml").write_text(
            text.replace("https://api.toobit.com", "http://api.toobit.com"),
            encoding="utf-8",
        )
        with pytest.raises(ConfigurationError) as excinfo:
            load_config(config_dir)
        assert excinfo.value.code == "CFG-021"

    def test_missing_file_refuses_boot(self, config_dir: Path) -> None:
        (config_dir / "risk.yaml").unlink()
        with pytest.raises(ConfigurationError) as excinfo:
            load_config(config_dir)
        assert excinfo.value.code == "CFG-002"

    def test_wrong_schema_version_refuses_boot(self, config_dir: Path) -> None:
        path = config_dir / "market.yaml"
        path.write_text("schema_version: 999\nsymbols: []\n", encoding="utf-8")
        with pytest.raises(ConfigurationError) as excinfo:
            load_config(config_dir)
        assert excinfo.value.code == "CFG-007"

    def test_malformed_yaml_refuses_boot(self, config_dir: Path) -> None:
        (config_dir / "signal.yaml").write_text("::: not yaml :::", encoding="utf-8")
        with pytest.raises(ConfigurationError):
            load_config(config_dir)

    def test_missing_required_key_refuses_boot(self, config_dir: Path) -> None:
        (config_dir / "system.yaml").write_text("schema_version: 1\n", encoding="utf-8")
        with pytest.raises(ConfigurationError) as excinfo:
            load_config(config_dir)
        assert excinfo.value.code == "CFG-008"

    def test_unsupported_enum_value_refuses_boot(self, config_dir: Path) -> None:
        text = (config_dir / "system.yaml").read_text(encoding="utf-8")
        (config_dir / "system.yaml").write_text(
            text.replace("run_mode: backtest", "run_mode: warp_speed"), encoding="utf-8"
        )
        with pytest.raises(ConfigurationError) as excinfo:
            load_config(config_dir)
        assert excinfo.value.code == "CFG-013"

    def test_deterministic_ids_require_seed(self, config_dir: Path) -> None:
        text = (config_dir / "system.yaml").read_text(encoding="utf-8")
        (config_dir / "system.yaml").write_text(
            text.replace("deterministic_ids: false", "deterministic_ids: true"),
            encoding="utf-8",
        )
        with pytest.raises(ConfigurationError) as excinfo:
            load_config(config_dir)
        assert excinfo.value.code == "CFG-016"

    def test_env_override_scalar(self, config_dir: Path) -> None:
        config = load_config(config_dir, env={"APEX__LOGGING__LEVEL": "debug"})
        assert config.logging.level is LogLevel.DEBUG

    def test_env_override_nested(self, config_dir: Path) -> None:
        config = load_config(
            config_dir, env={"APEX__SYSTEM__EVENTS__JOURNAL_CAPACITY": "500"}
        )
        assert config.system.event_journal_capacity == 500

    def test_env_override_bad_path_rejected(self, config_dir: Path) -> None:
        with pytest.raises(ConfigurationError) as excinfo:
            load_config(config_dir, env={"APEX__SYSTEM__NOPE__DEEP": "1"})
        assert excinfo.value.code == "CFG-005"

    def test_config_hash_changes_with_content(self, config_dir: Path) -> None:
        baseline = load_config(config_dir).config_hash
        overridden = load_config(config_dir, env={"APEX__LOGGING__LEVEL": "debug"})
        assert overridden.config_hash != baseline

    def test_missing_directory(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigurationError) as excinfo:
            load_config(tmp_path / "nope")
        assert excinfo.value.code == "CFG-001"
