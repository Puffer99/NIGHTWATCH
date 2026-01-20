"""
NIGHTWATCH Service Restart Tests (Step 229)

Tests for automatic service restart functionality including:
- Restart policies
- Exponential backoff
- Restart count tracking
- Manual restart
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock, patch

from nightwatch.orchestrator import (
    Orchestrator,
    ServiceRegistry,
    ServiceStatus,
    RestartPolicy,
    RestartConfig,
    EventType,
)
from nightwatch.config import NightwatchConfig


# =============================================================================
# Mock Services
# =============================================================================


class MockService:
    """Basic mock service for testing."""

    def __init__(self, fail_on_start: bool = False, fail_count: int = 0):
        self._is_running = False
        self._fail_on_start = fail_on_start
        self._fail_count = fail_count  # Number of times to fail before succeeding
        self._start_attempts = 0

    @property
    def is_running(self) -> bool:
        return self._is_running

    async def start(self):
        self._start_attempts += 1
        if self._fail_on_start and self._start_attempts <= self._fail_count:
            raise Exception(f"Service start failed (attempt {self._start_attempts})")
        self._is_running = True

    async def stop(self):
        self._is_running = False


class MockFailingService:
    """Service that always fails to start."""

    def __init__(self):
        self._is_running = False
        self.start_attempts = 0

    @property
    def is_running(self) -> bool:
        return self._is_running

    async def start(self):
        self.start_attempts += 1
        raise Exception("Service always fails")

    async def stop(self):
        self._is_running = False


class MockRecoverableService:
    """Service that fails N times then succeeds."""

    def __init__(self, failures_before_success: int = 2):
        self._is_running = False
        self.start_attempts = 0
        self.failures_before_success = failures_before_success

    @property
    def is_running(self) -> bool:
        return self._is_running

    async def start(self):
        self.start_attempts += 1
        if self.start_attempts <= self.failures_before_success:
            raise Exception(f"Temporary failure {self.start_attempts}")
        self._is_running = True

    async def stop(self):
        self._is_running = False


# =============================================================================
# Restart Policy Tests
# =============================================================================


class TestRestartPolicy:
    """Tests for restart policy enum."""

    def test_policy_values(self):
        """Test restart policy values."""
        assert RestartPolicy.NEVER.value == "never"
        assert RestartPolicy.ON_FAILURE.value == "on_failure"
        assert RestartPolicy.ALWAYS.value == "always"

    def test_all_policies_defined(self):
        """Test all policies are defined."""
        policies = list(RestartPolicy)
        assert len(policies) == 3


class TestRestartConfig:
    """Tests for restart configuration."""

    def test_default_config(self):
        """Test default restart configuration values."""
        config = RestartConfig()

        assert config.policy == RestartPolicy.ON_FAILURE
        assert config.max_restarts == 3
        assert config.restart_delay_sec == 5.0
        assert config.backoff_multiplier == 2.0
        assert config.max_delay_sec == 60.0
        assert config.reset_after_sec == 300.0

    def test_custom_config(self):
        """Test custom restart configuration."""
        config = RestartConfig(
            policy=RestartPolicy.ALWAYS,
            max_restarts=5,
            restart_delay_sec=2.0,
            backoff_multiplier=1.5,
            max_delay_sec=30.0,
            reset_after_sec=120.0,
        )

        assert config.policy == RestartPolicy.ALWAYS
        assert config.max_restarts == 5
        assert config.restart_delay_sec == 2.0


# =============================================================================
# Service Registry Restart Tests
# =============================================================================


class TestServiceRegistryRestart:
    """Tests for ServiceRegistry restart functionality."""

    @pytest.fixture
    def registry(self):
        return ServiceRegistry()

    @pytest.fixture
    def mock_service(self):
        return MockService()

    def test_register_with_restart_config(self, registry, mock_service):
        """Test registering service with restart config."""
        config = RestartConfig(
            policy=RestartPolicy.ALWAYS,
            max_restarts=5,
        )

        registry.register("test", mock_service, restart_config=config)

        info = registry._services.get("test")
        assert info is not None
        assert info.restart_config.policy == RestartPolicy.ALWAYS
        assert info.restart_config.max_restarts == 5

    def test_set_restart_config(self, registry, mock_service):
        """Test setting restart config after registration."""
        registry.register("test", mock_service)

        config = RestartConfig(policy=RestartPolicy.NEVER)
        result = registry.set_restart_config("test", config)

        assert result is True
        assert registry.get_restart_config("test").policy == RestartPolicy.NEVER

    def test_set_restart_config_unknown_service(self, registry):
        """Test setting config for unknown service."""
        config = RestartConfig()
        result = registry.set_restart_config("unknown", config)
        assert result is False

    def test_record_restart_attempt(self, registry, mock_service):
        """Test recording restart attempts."""
        registry.register("test", mock_service)

        registry.record_restart_attempt("test")
        info = registry._services["test"]

        assert info.restart_count == 1
        assert info.last_restart_attempt is not None

    def test_record_successful_start(self, registry, mock_service):
        """Test recording successful start."""
        registry.register("test", mock_service)

        registry.record_successful_start("test")
        info = registry._services["test"]

        assert info.last_successful_start is not None
        assert info.manually_stopped is False

    def test_reset_restart_count(self, registry, mock_service):
        """Test resetting restart count."""
        registry.register("test", mock_service)
        registry.record_restart_attempt("test")
        registry.record_restart_attempt("test")

        assert registry._services["test"].restart_count == 2

        registry.reset_restart_count("test")

        assert registry._services["test"].restart_count == 0

    def test_mark_manually_stopped(self, registry, mock_service):
        """Test marking service as manually stopped."""
        registry.register("test", mock_service)

        registry.mark_manually_stopped("test")

        assert registry._services["test"].manually_stopped is True


class TestShouldRestart:
    """Tests for should_restart logic."""

    @pytest.fixture
    def registry(self):
        return ServiceRegistry()

    @pytest.fixture
    def mock_service(self):
        return MockService()

    def test_should_not_restart_never_policy(self, registry, mock_service):
        """Test NEVER policy prevents restart."""
        config = RestartConfig(policy=RestartPolicy.NEVER)
        registry.register("test", mock_service, restart_config=config)
        registry.set_status("test", ServiceStatus.ERROR)

        assert registry.should_restart("test") is False

    def test_should_not_restart_manually_stopped(self, registry, mock_service):
        """Test manually stopped service is not restarted."""
        config = RestartConfig(policy=RestartPolicy.ALWAYS)
        registry.register("test", mock_service, restart_config=config)
        registry.set_status("test", ServiceStatus.STOPPED)
        registry.mark_manually_stopped("test")

        assert registry.should_restart("test") is False

    def test_should_not_restart_max_exceeded(self, registry, mock_service):
        """Test max restarts prevents further attempts."""
        config = RestartConfig(policy=RestartPolicy.ON_FAILURE, max_restarts=2)
        registry.register("test", mock_service, restart_config=config)
        registry.set_status("test", ServiceStatus.ERROR)

        # Exceed max restarts
        registry.record_restart_attempt("test")
        registry.record_restart_attempt("test")

        assert registry.should_restart("test") is False

    def test_should_restart_on_failure(self, registry, mock_service):
        """Test ON_FAILURE policy restarts on error."""
        config = RestartConfig(policy=RestartPolicy.ON_FAILURE)
        registry.register("test", mock_service, restart_config=config)
        registry.set_status("test", ServiceStatus.ERROR)

        assert registry.should_restart("test") is True

    def test_should_not_restart_on_failure_when_stopped(self, registry, mock_service):
        """Test ON_FAILURE policy does not restart stopped services."""
        config = RestartConfig(policy=RestartPolicy.ON_FAILURE)
        registry.register("test", mock_service, restart_config=config)
        registry.set_status("test", ServiceStatus.STOPPED)

        assert registry.should_restart("test") is False

    def test_should_restart_always_on_error(self, registry, mock_service):
        """Test ALWAYS policy restarts on error."""
        config = RestartConfig(policy=RestartPolicy.ALWAYS)
        registry.register("test", mock_service, restart_config=config)
        registry.set_status("test", ServiceStatus.ERROR)

        assert registry.should_restart("test") is True

    def test_should_restart_always_on_stopped(self, registry, mock_service):
        """Test ALWAYS policy restarts stopped services."""
        config = RestartConfig(policy=RestartPolicy.ALWAYS)
        registry.register("test", mock_service, restart_config=config)
        registry.set_status("test", ServiceStatus.STOPPED)

        assert registry.should_restart("test") is True

    def test_should_not_restart_running(self, registry, mock_service):
        """Test running service is not restarted."""
        config = RestartConfig(policy=RestartPolicy.ALWAYS)
        registry.register("test", mock_service, restart_config=config)
        registry.set_status("test", ServiceStatus.RUNNING)

        assert registry.should_restart("test") is False


class TestRestartDelay:
    """Tests for restart delay calculation."""

    @pytest.fixture
    def registry(self):
        return ServiceRegistry()

    @pytest.fixture
    def mock_service(self):
        return MockService()

    def test_initial_delay(self, registry, mock_service):
        """Test initial restart delay."""
        config = RestartConfig(restart_delay_sec=5.0, backoff_multiplier=2.0)
        registry.register("test", mock_service, restart_config=config)

        delay = registry.get_restart_delay("test")
        assert delay == 5.0

    def test_exponential_backoff(self, registry, mock_service):
        """Test exponential backoff increases delay."""
        config = RestartConfig(restart_delay_sec=5.0, backoff_multiplier=2.0)
        registry.register("test", mock_service, restart_config=config)

        # First attempt
        assert registry.get_restart_delay("test") == 5.0

        registry.record_restart_attempt("test")
        assert registry.get_restart_delay("test") == 10.0

        registry.record_restart_attempt("test")
        assert registry.get_restart_delay("test") == 20.0

    def test_max_delay_cap(self, registry, mock_service):
        """Test delay is capped at max_delay."""
        config = RestartConfig(
            restart_delay_sec=10.0,
            backoff_multiplier=2.0,
            max_delay_sec=30.0,
        )
        registry.register("test", mock_service, restart_config=config)

        # Multiple attempts should cap at max
        for _ in range(5):
            registry.record_restart_attempt("test")

        delay = registry.get_restart_delay("test")
        assert delay == 30.0


class TestRestartStats:
    """Tests for restart statistics."""

    @pytest.fixture
    def registry(self):
        return ServiceRegistry()

    @pytest.fixture
    def mock_service(self):
        return MockService()

    def test_get_restart_stats(self, registry, mock_service):
        """Test getting restart statistics."""
        config = RestartConfig(policy=RestartPolicy.ALWAYS, max_restarts=5)
        registry.register("test", mock_service, restart_config=config)
        registry.record_restart_attempt("test")
        registry.record_successful_start("test")

        stats = registry.get_restart_stats("test")

        assert stats["restart_count"] == 1
        assert stats["max_restarts"] == 5
        assert stats["policy"] == "always"
        assert stats["last_restart_attempt"] is not None
        assert stats["last_successful_start"] is not None
        assert stats["manually_stopped"] is False

    def test_get_services_needing_restart(self, registry, mock_service):
        """Test getting list of services needing restart."""
        registry.register("good", MockService())
        registry.register("bad", mock_service)

        registry.set_status("good", ServiceStatus.RUNNING)
        registry.set_status("bad", ServiceStatus.ERROR)

        needing_restart = registry.get_services_needing_restart()

        assert "bad" in needing_restart
        assert "good" not in needing_restart


# =============================================================================
# Orchestrator Restart Tests
# =============================================================================


class TestOrchestratorRestart:
    """Tests for Orchestrator restart functionality."""

    @pytest.fixture
    def config(self):
        return NightwatchConfig()

    @pytest.fixture
    def orchestrator(self, config):
        return Orchestrator(config)

    @pytest.mark.asyncio
    async def test_restart_service_manual(self, orchestrator):
        """Test manual service restart."""
        service = MockRecoverableService(failures_before_success=0)
        orchestrator.register_mount(service, required=False)

        await orchestrator.start()

        # Simulate failure
        service._is_running = False
        orchestrator.registry.set_status("mount", ServiceStatus.ERROR)

        # Manual restart
        result = await orchestrator.restart_service("mount", force=True)

        assert result is True
        assert service.is_running is True

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_restart_service_not_found(self, orchestrator):
        """Test restart of unknown service."""
        result = await orchestrator.restart_service("unknown")
        assert result is False

    @pytest.mark.asyncio
    async def test_set_service_restart_policy(self, orchestrator):
        """Test setting restart policy via orchestrator."""
        service = MockService()
        orchestrator.register_mount(service, required=False)

        result = orchestrator.set_service_restart_policy(
            "mount",
            RestartPolicy.ALWAYS,
            max_restarts=10,
            restart_delay=2.0,
        )

        assert result is True
        config = orchestrator.registry.get_restart_config("mount")
        assert config.policy == RestartPolicy.ALWAYS
        assert config.max_restarts == 10

    @pytest.mark.asyncio
    async def test_get_restart_statistics(self, orchestrator):
        """Test getting restart statistics."""
        service1 = MockService()
        service2 = MockService()

        orchestrator.register_mount(service1, required=False)
        orchestrator.register_camera(service2, required=False)

        stats = orchestrator.get_restart_statistics()

        assert "mount" in stats
        assert "camera" in stats
        assert "restart_count" in stats["mount"]
        assert "policy" in stats["mount"]

    @pytest.mark.asyncio
    async def test_restart_records_successful_start(self, orchestrator):
        """Test that successful restart records start time."""
        service = MockService()
        orchestrator.register_mount(service, required=False)

        await orchestrator.start()

        # Check start was recorded
        info = orchestrator.registry._services.get("mount")
        assert info.last_successful_start is not None

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_service_start_emits_event(self, orchestrator):
        """Test that service start emits event."""
        events_received = []

        def listener(event):
            events_received.append(event)

        orchestrator.subscribe(EventType.SERVICE_STARTED, listener)

        service = MockService()
        orchestrator.register_mount(service, required=False)

        await orchestrator.start()

        # Should have received service started event
        assert len(events_received) >= 1
        assert any(e.source == "mount" for e in events_received)

        await orchestrator.shutdown()


class TestAutoRestart:
    """Tests for automatic restart in health loop."""

    @pytest.fixture
    def config(self):
        return NightwatchConfig()

    @pytest.fixture
    def orchestrator(self, config):
        return Orchestrator(config)

    @pytest.mark.asyncio
    async def test_check_and_restart_services(self, orchestrator):
        """Test _check_and_restart_services method."""
        # Create a service that will need restart
        service = MockRecoverableService(failures_before_success=0)
        orchestrator.register_mount(service, required=False)

        await orchestrator.start()

        # Simulate failure
        service._is_running = False
        orchestrator.registry.set_status("mount", ServiceStatus.ERROR)

        # Trigger restart check
        await orchestrator._check_and_restart_services()

        # Service should be restarted
        assert service.is_running is True

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_restart_respects_max_attempts(self, orchestrator):
        """Test that restart respects max attempts."""
        # Create a service that always fails
        service = MockFailingService()
        config = RestartConfig(
            policy=RestartPolicy.ON_FAILURE,
            max_restarts=2,
            restart_delay_sec=0.01,  # Fast for testing
        )
        orchestrator.registry.register("test", service, restart_config=config)
        orchestrator.registry.set_status("test", ServiceStatus.ERROR)

        # First restart attempt
        orchestrator.registry.record_restart_attempt("test")
        assert orchestrator.registry.should_restart("test") is True

        # Second restart attempt
        orchestrator.registry.record_restart_attempt("test")
        assert orchestrator.registry.should_restart("test") is False

    @pytest.mark.asyncio
    async def test_restart_service_internal(self, orchestrator):
        """Test _restart_service internal method."""
        service = MockRecoverableService(failures_before_success=0)
        orchestrator.registry.register("test", service, restart_config=RestartConfig(
            restart_delay_sec=0.01,
        ))
        orchestrator.registry.set_status("test", ServiceStatus.ERROR)

        result = await orchestrator._restart_service("test")

        assert result is True
        assert service.is_running is True
        assert orchestrator.registry.get_status("test") == ServiceStatus.RUNNING

    @pytest.mark.asyncio
    async def test_restart_service_failure(self, orchestrator):
        """Test _restart_service when service fails."""
        service = MockFailingService()
        orchestrator.registry.register("test", service, restart_config=RestartConfig(
            restart_delay_sec=0.01,
        ))
        orchestrator.registry.set_status("test", ServiceStatus.ERROR)

        result = await orchestrator._restart_service("test")

        assert result is False
        assert orchestrator.registry.get_status("test") == ServiceStatus.ERROR


class TestRestartStatus:
    """Tests for ServiceStatus.RESTARTING."""

    def test_restarting_status_exists(self):
        """Test RESTARTING status is defined."""
        assert ServiceStatus.RESTARTING.value == "restarting"

    @pytest.fixture
    def orchestrator(self):
        return Orchestrator(NightwatchConfig())

    @pytest.mark.asyncio
    async def test_status_set_to_restarting(self, orchestrator):
        """Test status is set to RESTARTING during restart."""
        service = MockRecoverableService(failures_before_success=0)
        orchestrator.registry.register("test", service, restart_config=RestartConfig(
            restart_delay_sec=0.1,  # Enough to check status
        ))
        orchestrator.registry.set_status("test", ServiceStatus.ERROR)

        # Start restart in background
        task = asyncio.create_task(orchestrator._restart_service("test"))

        # Give it time to set status
        await asyncio.sleep(0.05)

        # Status should be RESTARTING
        assert orchestrator.registry.get_status("test") == ServiceStatus.RESTARTING

        # Wait for completion
        await task


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
