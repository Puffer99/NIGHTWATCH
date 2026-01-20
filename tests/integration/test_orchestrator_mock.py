"""
NIGHTWATCH Orchestrator Integration Test with Mock Services (Step 256)

Tests the orchestrator's ability to coordinate multiple mock services
in realistic scenarios including startup, shutdown, and error handling.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock, patch

from nightwatch.orchestrator import (
    Orchestrator,
    ServiceRegistry,
    ServiceStatus,
    SessionState,
    EventType,
    OrchestratorEvent,
)
from nightwatch.config import NightwatchConfig


class MockMountService:
    """Mock mount service for testing."""

    def __init__(self):
        self.is_running = False
        self.is_parked = True
        self.is_tracking = False
        self.is_slewing = False
        self.ra = 0.0
        self.dec = 0.0
        self._start_called = False
        self._stop_called = False

    async def start(self):
        self._start_called = True
        self.is_running = True

    async def stop(self):
        self._stop_called = True
        self.is_running = False

    async def park(self):
        self.is_parked = True
        self.is_tracking = False
        return True

    async def unpark(self):
        self.is_parked = False
        return True

    async def slew_to(self, ra: float, dec: float):
        self.is_slewing = True
        await asyncio.sleep(0.01)  # Simulate slew time
        self.ra = ra
        self.dec = dec
        self.is_slewing = False
        self.is_tracking = True
        return True

    def get_position(self):
        return {"ra": self.ra, "dec": self.dec}


class MockWeatherService:
    """Mock weather service for testing."""

    def __init__(self):
        self.is_running = False
        self.is_safe = True
        self.temperature = 15.0
        self.humidity = 50.0
        self.wind_speed = 5.0

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    def get_conditions(self):
        return {
            "temperature": self.temperature,
            "humidity": self.humidity,
            "wind_speed": self.wind_speed,
            "is_safe": self.is_safe,
        }


class MockCameraService:
    """Mock camera service for testing."""

    def __init__(self):
        self.is_running = False
        self.is_exposing = False
        self.exposure_count = 0

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    async def capture(self, exposure_sec: float):
        self.is_exposing = True
        await asyncio.sleep(0.01)  # Simulate exposure
        self.is_exposing = False
        self.exposure_count += 1
        return {"path": f"/images/test_{self.exposure_count}.fits"}


class MockSafetyService:
    """Mock safety service for testing."""

    def __init__(self):
        self.is_running = False
        self.is_safe = True
        self.vetoes = []

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    def check_safety(self):
        return self.is_safe

    def get_vetoes(self):
        return self.vetoes


class MockEnclosureService:
    """Mock enclosure service for testing."""

    def __init__(self):
        self.is_running = False
        self.is_open = False

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    async def open(self):
        self.is_open = True
        return True

    async def close(self):
        self.is_open = False
        return True


class TestOrchestratorWithMockServices:
    """Integration tests for orchestrator with mock services."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return NightwatchConfig()

    @pytest.fixture
    def mock_services(self):
        """Create mock services."""
        return {
            "mount": MockMountService(),
            "weather": MockWeatherService(),
            "camera": MockCameraService(),
            "safety": MockSafetyService(),
            "enclosure": MockEnclosureService(),
        }

    @pytest.fixture
    def orchestrator(self, config, mock_services):
        """Create orchestrator with mock services."""
        orch = Orchestrator(config)
        orch.register_mount(mock_services["mount"], required=False)
        orch.register_weather(mock_services["weather"], required=False)
        orch.register_camera(mock_services["camera"], required=False)
        orch.register_safety(mock_services["safety"], required=False)
        orch.register_enclosure(mock_services["enclosure"], required=False)
        return orch

    @pytest.mark.asyncio
    async def test_startup_all_services(self, orchestrator, mock_services):
        """Test orchestrator starts all registered services."""
        result = await orchestrator.start()
        assert result is True
        assert orchestrator.is_running is True

        # All services should be running
        assert mock_services["mount"].is_running is True
        assert mock_services["weather"].is_running is True
        assert mock_services["camera"].is_running is True
        assert mock_services["safety"].is_running is True
        assert mock_services["enclosure"].is_running is True

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_all_services(self, orchestrator, mock_services):
        """Test orchestrator stops all services on shutdown."""
        await orchestrator.start()
        await orchestrator.shutdown()

        assert orchestrator.is_running is False
        assert mock_services["mount"].is_running is False
        assert mock_services["weather"].is_running is False
        assert mock_services["camera"].is_running is False

    @pytest.mark.asyncio
    async def test_safe_shutdown_parks_mount(self, orchestrator, mock_services):
        """Test safe shutdown parks mount first."""
        await orchestrator.start()

        # Unpark mount
        await mock_services["mount"].unpark()
        assert mock_services["mount"].is_parked is False

        # Safe shutdown should park
        await orchestrator.shutdown(safe=True)
        assert mock_services["mount"].is_parked is True

    @pytest.mark.asyncio
    async def test_safe_shutdown_closes_enclosure(self, orchestrator, mock_services):
        """Test safe shutdown closes enclosure."""
        await orchestrator.start()

        # Open enclosure
        await mock_services["enclosure"].open()
        assert mock_services["enclosure"].is_open is True

        # Safe shutdown should close
        await orchestrator.shutdown(safe=True)
        assert mock_services["enclosure"].is_open is False

    @pytest.mark.asyncio
    async def test_session_lifecycle(self, orchestrator):
        """Test starting and ending observing session."""
        await orchestrator.start()

        # Start session
        result = await orchestrator.start_session("test_session_001")
        assert result is True
        assert orchestrator.session.session_id == "test_session_001"
        assert orchestrator.session.is_observing is True
        assert orchestrator.session.started_at is not None

        # End session
        await orchestrator.end_session()
        assert orchestrator.session.is_observing is False

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_service_status_tracking(self, orchestrator, mock_services):
        """Test service status is tracked correctly."""
        await orchestrator.start()

        # Check statuses are set to running
        status = orchestrator.get_service_status()
        assert status["mount"]["status"] == "running"
        assert status["weather"]["status"] == "running"

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_event_emission_on_startup(self, orchestrator):
        """Test events are emitted on startup."""
        events_received = []

        def listener(event):
            events_received.append(event)

        orchestrator.subscribe(EventType.SERVICE_STARTED, listener)

        await orchestrator.start()

        # Should have received service_started events
        assert len(events_received) > 0

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_event_emission_on_shutdown(self, orchestrator):
        """Test shutdown event is emitted."""
        shutdown_received = []

        def listener(event):
            shutdown_received.append(event)

        orchestrator.subscribe(EventType.SHUTDOWN_INITIATED, listener)

        await orchestrator.start()
        await orchestrator.shutdown()

        assert len(shutdown_received) == 1

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, orchestrator):
        """Test metrics are tracked during operation."""
        await orchestrator.start()

        # Record some metrics
        await orchestrator.record_command_execution(100.0)
        await orchestrator.record_command_execution(150.0)
        orchestrator.record_service_error("mount")

        metrics = orchestrator.get_metrics()
        assert metrics["commands_executed"] == 2
        assert metrics["avg_latency_ms"] == 125.0
        assert metrics["error_count"] == 1

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_callback_notification(self, orchestrator):
        """Test callbacks are notified of events."""
        callback_data = []

        def callback(event, data):
            callback_data.append((event, data))

        orchestrator.register_callback(callback)

        await orchestrator.start()
        await orchestrator._notify_callbacks("test_event", {"key": "value"})

        assert len(callback_data) == 1
        assert callback_data[0][0] == "test_event"
        assert callback_data[0][1]["key"] == "value"

        await orchestrator.shutdown()


class TestOrchestratorErrorHandling:
    """Tests for orchestrator error handling."""

    @pytest.fixture
    def config(self):
        return NightwatchConfig()

    @pytest.mark.asyncio
    async def test_service_start_failure_non_required(self, config):
        """Test handling of non-required service failure."""
        orch = Orchestrator(config)

        # Create failing service
        failing_service = AsyncMock()
        failing_service.start = AsyncMock(side_effect=Exception("Start failed"))
        failing_service.is_running = False

        orch.register_camera(failing_service, required=False)

        # Should succeed despite camera failure
        result = await orch.start()
        assert result is True
        assert orch.is_running is True

        await orch.shutdown()

    @pytest.mark.asyncio
    async def test_service_start_failure_required(self, config):
        """Test handling of required service failure."""
        orch = Orchestrator(config)

        # Create failing required service
        failing_service = AsyncMock()
        failing_service.start = AsyncMock(side_effect=Exception("Start failed"))
        failing_service.is_running = False

        orch.register_mount(failing_service, required=True)

        # Should fail because required service failed
        result = await orch.start()
        assert result is False

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, config):
        """Test orchestrator continues with partial services."""
        orch = Orchestrator(config)

        # Good service
        good_service = MockMountService()
        orch.register_mount(good_service, required=False)

        # Failing service
        bad_service = AsyncMock()
        bad_service.start = AsyncMock(side_effect=Exception("Failed"))
        bad_service.is_running = False
        orch.register_camera(bad_service, required=False)

        result = await orch.start()
        assert result is True
        assert good_service.is_running is True

        await orch.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_handles_service_errors(self, config):
        """Test shutdown continues even if service stop fails."""
        orch = Orchestrator(config)

        # Service that fails on stop
        bad_service = AsyncMock()
        bad_service.start = AsyncMock()
        bad_service.stop = AsyncMock(side_effect=Exception("Stop failed"))
        bad_service.is_running = True

        orch.register_mount(bad_service, required=False)

        await orch.start()
        # Should not raise
        await orch.shutdown()
        assert orch.is_running is False


class TestOrchestratorConcurrency:
    """Tests for concurrent operation handling."""

    @pytest.fixture
    def config(self):
        return NightwatchConfig()

    @pytest.mark.asyncio
    async def test_concurrent_callbacks(self, config):
        """Test concurrent callback handling."""
        orch = Orchestrator(config)

        results = []

        async def async_callback(event, data):
            await asyncio.sleep(0.01)
            results.append(f"async_{event}")

        def sync_callback(event, data):
            results.append(f"sync_{event}")

        orch.register_callback(async_callback)
        orch.register_callback(sync_callback)

        await orch._notify_callbacks("test", {})

        # Both callbacks should have run
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_multiple_event_listeners(self, config):
        """Test multiple listeners for same event."""
        orch = Orchestrator(config)

        listener_calls = []

        def listener1(event):
            listener_calls.append("L1")

        def listener2(event):
            listener_calls.append("L2")

        def listener3(event):
            listener_calls.append("L3")

        orch.subscribe(EventType.WEATHER_CHANGED, listener1)
        orch.subscribe(EventType.WEATHER_CHANGED, listener2)
        orch.subscribe(EventType.WEATHER_CHANGED, listener3)

        await orch.emit_event(EventType.WEATHER_CHANGED, source="test")

        assert len(listener_calls) == 3


class TestOrchestratorServiceRegistry:
    """Tests for service registry integration."""

    @pytest.fixture
    def config(self):
        return NightwatchConfig()

    def test_list_all_services(self, config):
        """Test listing all registered services."""
        orch = Orchestrator(config)

        orch.register_mount(MockMountService())
        orch.register_weather(MockWeatherService())
        orch.register_camera(MockCameraService())

        services = orch.registry.list_services()
        assert len(services) == 3
        assert "mount" in services
        assert "weather" in services
        assert "camera" in services

    def test_get_required_services(self, config):
        """Test getting required services list."""
        orch = Orchestrator(config)

        orch.register_mount(MockMountService(), required=True)
        orch.register_weather(MockWeatherService(), required=False)
        orch.register_safety(MockSafetyService(), required=True)

        required = orch.registry.get_required_services()
        assert "mount" in required
        assert "safety" in required
        assert "weather" not in required

    def test_service_info_tracking(self, config):
        """Test service info is tracked correctly."""
        orch = Orchestrator(config)

        orch.register_mount(MockMountService())
        orch.registry.set_status("mount", ServiceStatus.RUNNING)

        info = orch.registry.get_all_info()
        assert "mount" in info
        assert info["mount"].status == ServiceStatus.RUNNING


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
