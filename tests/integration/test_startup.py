"""
Integration tests for NIGHTWATCH startup sequence.

Tests the full startup flow including configuration loading,
health checks, and graceful shutdown.
"""

import asyncio
import os
import signal
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from nightwatch.config import NightwatchConfig, load_config
from nightwatch.health import (
    HealthChecker,
    HealthCheckResult,
    HealthStatus,
    ServiceHealth,
    StartupSequence,
)
from nightwatch.main import (
    GracefulShutdown,
    async_main,
    create_parser,
    get_shutdown_handler,
)


class TestArgumentParser:
    """Tests for command-line argument parsing."""

    def test_parser_defaults(self) -> None:
        """Test parser with no arguments uses defaults."""
        parser = create_parser()
        args = parser.parse_args([])

        assert args.config is None
        assert args.log_level is None
        assert args.dry_run is False
        assert args.check_health is False
        assert args.no_voice is False
        assert args.simulator is False

    def test_parser_config_option(self) -> None:
        """Test --config option."""
        parser = create_parser()
        args = parser.parse_args(["--config", "/path/to/config.yaml"])
        assert args.config == "/path/to/config.yaml"

        args = parser.parse_args(["-c", "/another/path.yaml"])
        assert args.config == "/another/path.yaml"

    def test_parser_log_level_option(self) -> None:
        """Test --log-level option."""
        parser = create_parser()

        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            args = parser.parse_args(["--log-level", level])
            assert args.log_level == level

    def test_parser_dry_run_option(self) -> None:
        """Test --dry-run option."""
        parser = create_parser()
        args = parser.parse_args(["--dry-run"])
        assert args.dry_run is True

    def test_parser_check_health_option(self) -> None:
        """Test --check-health option."""
        parser = create_parser()
        args = parser.parse_args(["--check-health"])
        assert args.check_health is True

    def test_parser_no_voice_option(self) -> None:
        """Test --no-voice option."""
        parser = create_parser()
        args = parser.parse_args(["--no-voice"])
        assert args.no_voice is True

    def test_parser_simulator_option(self) -> None:
        """Test --simulator option."""
        parser = create_parser()
        args = parser.parse_args(["--simulator"])
        assert args.simulator is True

    def test_parser_combined_options(self) -> None:
        """Test multiple options combined."""
        parser = create_parser()
        args = parser.parse_args([
            "--config", "/path/config.yaml",
            "--log-level", "DEBUG",
            "--simulator",
            "--no-voice",
        ])

        assert args.config == "/path/config.yaml"
        assert args.log_level == "DEBUG"
        assert args.simulator is True
        assert args.no_voice is True


class TestGracefulShutdown:
    """Tests for graceful shutdown handling."""

    def test_initial_state(self) -> None:
        """Test shutdown handler initial state."""
        handler = GracefulShutdown()
        assert handler.shutdown_requested is False

    def test_install_restore_handlers(self) -> None:
        """Test signal handler installation and restoration."""
        handler = GracefulShutdown()

        # Install handlers
        handler.install_handlers()

        # Verify handlers are installed (they should be our handler)
        assert signal.getsignal(signal.SIGINT) == handler._handle_signal
        assert signal.getsignal(signal.SIGTERM) == handler._handle_signal

        # Restore handlers
        handler.restore_handlers()

    def test_shutdown_event(self) -> None:
        """Test shutdown event creation."""
        handler = GracefulShutdown()
        event = handler.get_shutdown_event()

        assert isinstance(event, asyncio.Event)
        assert not event.is_set()

    def test_signal_sets_shutdown(self) -> None:
        """Test that receiving signal sets shutdown flag."""
        handler = GracefulShutdown()
        handler.install_handlers()

        try:
            # Manually call handler (simulating signal)
            handler._handle_signal(signal.SIGINT, None)

            assert handler.shutdown_requested is True
        finally:
            handler.restore_handlers()


class TestHealthChecker:
    """Tests for health check framework."""

    @pytest.fixture
    def config(self) -> NightwatchConfig:
        """Create test configuration."""
        return NightwatchConfig(
            mount={"type": "simulator"},
            weather={"enabled": False},
            voice={"enabled": False},
            tts={"enabled": False},
            guider={"enabled": False},
            power={"enabled": False},
        )

    @pytest.mark.asyncio
    async def test_check_all_with_simulators(self, config: NightwatchConfig) -> None:
        """Test health checks with simulator mode."""
        checker = HealthChecker(config)
        result = await checker.check_all()

        assert isinstance(result, HealthCheckResult)
        assert "mount" in result.services

        # Mount in simulator mode should be healthy
        assert result.services["mount"].status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_disabled_services(self, config: NightwatchConfig) -> None:
        """Test health checks for disabled services."""
        checker = HealthChecker(config)
        result = await checker.check_all()

        # Disabled services should have DISABLED status
        assert result.services["weather"].status == HealthStatus.DISABLED
        assert result.services["voice"].status == HealthStatus.DISABLED

    @pytest.mark.asyncio
    async def test_check_single_service(self, config: NightwatchConfig) -> None:
        """Test checking a single service."""
        checker = HealthChecker(config)
        health = await checker.check_service("mount")

        assert isinstance(health, ServiceHealth)
        assert health.name == "mount"

    @pytest.mark.asyncio
    async def test_check_unknown_service(self, config: NightwatchConfig) -> None:
        """Test checking an unregistered service."""
        checker = HealthChecker(config)
        health = await checker.check_service("nonexistent")

        assert health.status == HealthStatus.UNKNOWN
        assert "No health check registered" in health.message

    @pytest.mark.asyncio
    async def test_register_custom_check(self, config: NightwatchConfig) -> None:
        """Test registering a custom health check."""
        checker = HealthChecker(config)

        async def custom_check(cfg: NightwatchConfig) -> ServiceHealth:
            return ServiceHealth(
                name="custom",
                status=HealthStatus.HEALTHY,
                message="Custom check passed",
            )

        checker.register_check("custom", custom_check)
        health = await checker.check_service("custom")

        assert health.status == HealthStatus.HEALTHY
        assert health.message == "Custom check passed"


class TestStartupSequence:
    """Tests for startup sequence."""

    @pytest.fixture
    def config(self) -> NightwatchConfig:
        """Create test configuration with simulators."""
        return NightwatchConfig(
            mount={"type": "simulator"},
            weather={"type": "simulator"},
            voice={"enabled": False},
            tts={"enabled": False},
            guider={"enabled": False},
            power={"enabled": False},
        )

    @pytest.mark.asyncio
    async def test_startup_with_simulators(self, config: NightwatchConfig) -> None:
        """Test startup sequence with simulator backends."""
        sequence = StartupSequence(config)
        success, result = await sequence.run()

        # Should succeed with simulators
        assert success is True
        assert result.all_required_healthy is True

    @pytest.mark.asyncio
    async def test_startup_skip_optional(self, config: NightwatchConfig) -> None:
        """Test startup sequence skipping optional services."""
        sequence = StartupSequence(config)
        success, result = await sequence.run(skip_optional=True)

        assert success is True

    @pytest.mark.asyncio
    async def test_startup_tracks_started_services(self, config: NightwatchConfig) -> None:
        """Test that startup sequence tracks started services."""
        sequence = StartupSequence(config)
        await sequence.run()

        # Mount should be tracked as started (it's required and in simulator mode)
        assert "mount" in sequence._started_services


class TestHealthCheckResult:
    """Tests for HealthCheckResult aggregation."""

    def test_all_healthy(self) -> None:
        """Test all_healthy property."""
        result = HealthCheckResult(
            services={
                "service1": ServiceHealth("service1", HealthStatus.HEALTHY, "OK"),
                "service2": ServiceHealth("service2", HealthStatus.HEALTHY, "OK"),
            }
        )
        assert result.all_healthy is True

    def test_all_healthy_with_disabled(self) -> None:
        """Test all_healthy includes disabled services as healthy."""
        result = HealthCheckResult(
            services={
                "service1": ServiceHealth("service1", HealthStatus.HEALTHY, "OK"),
                "service2": ServiceHealth("service2", HealthStatus.DISABLED, "Disabled"),
            }
        )
        assert result.all_healthy is True

    def test_not_all_healthy(self) -> None:
        """Test all_healthy with unhealthy service."""
        result = HealthCheckResult(
            services={
                "service1": ServiceHealth("service1", HealthStatus.HEALTHY, "OK"),
                "service2": ServiceHealth("service2", HealthStatus.UNHEALTHY, "Failed"),
            }
        )
        assert result.all_healthy is False

    def test_summary(self) -> None:
        """Test summary generation."""
        result = HealthCheckResult(
            services={
                "service1": ServiceHealth("service1", HealthStatus.HEALTHY, "OK"),
                "service2": ServiceHealth("service2", HealthStatus.UNHEALTHY, "Failed"),
                "service3": ServiceHealth("service3", HealthStatus.DISABLED, "Off"),
            }
        )
        assert result.summary == "2/3 services healthy"


class TestConfigIntegration:
    """Tests for configuration loading integration."""

    def test_load_config_with_simulator_mode(self) -> None:
        """Test loading config and applying simulator mode."""
        config = load_config()

        # Apply simulator mode (as main.py does with --simulator)
        config.mount.type = "simulator"
        config.weather.type = "simulator"
        config.camera.type = "simulator"

        assert config.mount.type == "simulator"
        assert config.weather.type == "simulator"

    def test_load_config_with_voice_disabled(self) -> None:
        """Test loading config and disabling voice."""
        config = load_config()

        # Disable voice (as main.py does with --no-voice)
        config.voice.enabled = False
        config.tts.enabled = False

        assert config.voice.enabled is False
        assert config.tts.enabled is False

    def test_load_custom_config_file(self) -> None:
        """Test loading configuration from custom file."""
        config_data = {
            "site": {"name": "Test Observatory"},
            "mount": {"host": "test.local", "type": "simulator"},
            "log_level": "DEBUG",
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            config = load_config(temp_path)
            assert config.site.name == "Test Observatory"
            assert config.mount.host == "test.local"
            assert config.log_level == "DEBUG"
        finally:
            os.unlink(temp_path)


class TestAsyncMain:
    """Tests for async main function."""

    @pytest.fixture
    def config(self) -> NightwatchConfig:
        """Create test configuration."""
        return NightwatchConfig(
            mount={"type": "simulator"},
            weather={"enabled": False},
            voice={"enabled": False},
            tts={"enabled": False},
        )

    @pytest.mark.asyncio
    async def test_check_health_mode(self, config: NightwatchConfig) -> None:
        """Test --check-health mode exits after health checks."""
        parser = create_parser()
        args = parser.parse_args(["--check-health"])

        # Should return 0 after health checks
        exit_code = await async_main(args, config)
        assert exit_code == 0
