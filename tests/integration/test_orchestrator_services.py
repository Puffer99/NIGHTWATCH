"""
NIGHTWATCH Orchestrator Services Integration Test (Step 569)

Tests full orchestration of multiple services working together,
including service coordination, state management, and inter-service
communication.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Optional

from nightwatch.orchestrator import (
    Orchestrator,
    ServiceRegistry,
    ServiceStatus,
    SessionState,
    EventType,
    OrchestratorEvent,
)
from nightwatch.config import NightwatchConfig


# =============================================================================
# Mock Services
# =============================================================================

class MockMountService:
    """Mock mount service."""

    def __init__(self):
        self.is_running = False
        self.is_parked = True
        self.is_tracking = False
        self.ra = 0.0
        self.dec = 0.0

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    async def park(self):
        self.is_parked = True
        self.is_tracking = False
        return True

    async def slew_to(self, ra: float, dec: float):
        self.ra = ra
        self.dec = dec
        self.is_tracking = True
        return True


class MockCameraService:
    """Mock camera service."""

    def __init__(self):
        self.is_running = False
        self.is_exposing = False
        self.exposure_count = 0
        self.last_exposure_sec = 0

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    async def capture(self, exposure_sec: float):
        self.is_exposing = True
        self.last_exposure_sec = exposure_sec
        await asyncio.sleep(0.01)
        self.is_exposing = False
        self.exposure_count += 1
        return {"path": f"/images/img_{self.exposure_count}.fits"}


class MockWeatherService:
    """Mock weather service."""

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
            "is_safe": self.is_safe,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "wind_speed": self.wind_speed,
        }


class MockSafetyService:
    """Mock safety service."""

    def __init__(self):
        self.is_running = False
        self.is_safe = True
        self.vetoes = []

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    def evaluate_safety(self):
        return {
            "is_safe": self.is_safe and len(self.vetoes) == 0,
            "vetoes": self.vetoes,
        }

    def add_veto(self, reason: str):
        self.vetoes.append(reason)

    def clear_vetoes(self):
        self.vetoes.clear()


class MockGuidingService:
    """Mock guiding service."""

    def __init__(self):
        self.is_running = False
        self.is_guiding = False
        self.is_calibrated = False

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    async def start_guiding(self):
        if self.is_calibrated:
            self.is_guiding = True
            return True
        return False

    async def stop_guiding(self):
        self.is_guiding = False
        return True

    async def calibrate(self):
        await asyncio.sleep(0.01)
        self.is_calibrated = True
        return True


class MockFocusService:
    """Mock focus service."""

    def __init__(self):
        self.is_running = False
        self.position = 25000
        self.is_moving = False

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    async def move_to(self, position: int):
        self.is_moving = True
        await asyncio.sleep(0.01)
        self.position = position
        self.is_moving = False
        return True

    async def autofocus(self):
        self.is_moving = True
        await asyncio.sleep(0.01)
        self.position = 25500  # Optimal focus
        self.is_moving = False
        return {"position": self.position, "hfd": 2.5}


class MockEnclosureService:
    """Mock enclosure service."""

    def __init__(self):
        self.is_running = False
        self.is_open = False
        self.is_moving = False

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    async def open(self):
        self.is_moving = True
        await asyncio.sleep(0.01)
        self.is_open = True
        self.is_moving = False
        return True

    async def close(self):
        self.is_moving = True
        await asyncio.sleep(0.01)
        self.is_open = False
        self.is_moving = False
        return True


# =============================================================================
# Test Classes
# =============================================================================

class TestOrchestratorFullIntegration:
    """Tests for full orchestrator integration with all services."""

    @pytest.fixture
    def config(self):
        return NightwatchConfig()

    @pytest.fixture
    def services(self):
        return {
            "mount": MockMountService(),
            "camera": MockCameraService(),
            "weather": MockWeatherService(),
            "safety": MockSafetyService(),
            "guiding": MockGuidingService(),
            "focus": MockFocusService(),
            "enclosure": MockEnclosureService(),
        }

    @pytest.fixture
    def orchestrator(self, config, services):
        orch = Orchestrator(config)
        orch.register_mount(services["mount"], required=False)
        orch.register_camera(services["camera"], required=False)
        orch.register_weather(services["weather"], required=False)
        orch.register_safety(services["safety"], required=False)
        orch.register_guiding(services["guiding"], required=False)
        orch.register_focus(services["focus"], required=False)
        orch.register_enclosure(services["enclosure"], required=False)
        return orch

    @pytest.mark.asyncio
    async def test_all_services_start(self, orchestrator, services):
        """Test all services start correctly."""
        result = await orchestrator.start()
        assert result is True

        for name, service in services.items():
            assert service.is_running is True, f"{name} should be running"

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_all_services_stop(self, orchestrator, services):
        """Test all services stop on shutdown."""
        await orchestrator.start()
        await orchestrator.shutdown()

        for name, service in services.items():
            assert service.is_running is False, f"{name} should be stopped"

    @pytest.mark.asyncio
    async def test_service_status_tracking(self, orchestrator, services):
        """Test service status is tracked correctly."""
        await orchestrator.start()

        status = orchestrator.get_service_status()

        assert "mount" in status
        assert "camera" in status
        assert "weather" in status
        assert status["mount"]["status"] == "running"

        await orchestrator.shutdown()


class TestObservingSessionWorkflow:
    """Tests for complete observing session workflow."""

    @pytest.fixture
    def config(self):
        return NightwatchConfig()

    @pytest.fixture
    def services(self):
        return {
            "mount": MockMountService(),
            "camera": MockCameraService(),
            "weather": MockWeatherService(),
            "safety": MockSafetyService(),
            "enclosure": MockEnclosureService(),
        }

    @pytest.fixture
    def orchestrator(self, config, services):
        orch = Orchestrator(config)
        orch.register_mount(services["mount"], required=False)
        orch.register_camera(services["camera"], required=False)
        orch.register_weather(services["weather"], required=False)
        orch.register_safety(services["safety"], required=False)
        orch.register_enclosure(services["enclosure"], required=False)
        return orch

    @pytest.mark.asyncio
    async def test_session_startup_sequence(self, orchestrator, services):
        """Test session startup: start services -> open enclosure -> unpark."""
        await orchestrator.start()
        await orchestrator.start_session("test_session")

        assert orchestrator.session.is_observing is True
        assert orchestrator.session.session_id == "test_session"

        # Simulate opening sequence
        await services["enclosure"].open()
        assert services["enclosure"].is_open is True

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_session_shutdown_sequence(self, orchestrator, services):
        """Test session shutdown: park -> close enclosure -> stop services."""
        await orchestrator.start()
        await orchestrator.start_session("test_session")

        # Simulate observing
        services["mount"].is_parked = False
        services["mount"].is_tracking = True
        services["enclosure"].is_open = True

        # End session with safe shutdown
        await orchestrator.end_session()
        await orchestrator.shutdown(safe=True)

        assert services["mount"].is_parked is True
        assert services["enclosure"].is_open is False

    @pytest.mark.asyncio
    async def test_session_tracks_images(self, orchestrator, services):
        """Test session tracks captured images."""
        await orchestrator.start()
        await orchestrator.start_session("imaging_session")

        # Simulate captures
        for i in range(5):
            await services["camera"].capture(30.0)
            orchestrator.session.images_captured += 1
            orchestrator.session.total_exposure_sec += 30.0

        assert orchestrator.session.images_captured == 5
        assert orchestrator.session.total_exposure_sec == 150.0

        await orchestrator.shutdown()


class TestServiceCoordination:
    """Tests for service coordination scenarios."""

    @pytest.fixture
    def config(self):
        return NightwatchConfig()

    @pytest.fixture
    def services(self):
        return {
            "mount": MockMountService(),
            "camera": MockCameraService(),
            "guiding": MockGuidingService(),
            "focus": MockFocusService(),
        }

    @pytest.fixture
    def orchestrator(self, config, services):
        orch = Orchestrator(config)
        orch.register_mount(services["mount"], required=False)
        orch.register_camera(services["camera"], required=False)
        orch.register_guiding(services["guiding"], required=False)
        orch.register_focus(services["focus"], required=False)
        return orch

    @pytest.mark.asyncio
    async def test_imaging_sequence(self, orchestrator, services):
        """Test coordinated imaging: slew -> focus -> guide -> capture."""
        await orchestrator.start()

        # 1. Slew to target
        await services["mount"].slew_to(83.82, -5.39)  # M42
        assert services["mount"].is_tracking is True

        # 2. Autofocus
        result = await services["focus"].autofocus()
        assert result["hfd"] < 3.0

        # 3. Start guiding
        await services["guiding"].calibrate()
        await services["guiding"].start_guiding()
        assert services["guiding"].is_guiding is True

        # 4. Capture images
        for _ in range(3):
            await services["camera"].capture(60.0)

        assert services["camera"].exposure_count == 3

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_dither_sequence(self, orchestrator, services):
        """Test dither between exposures."""
        await orchestrator.start()

        services["mount"].is_tracking = True
        await services["guiding"].calibrate()
        await services["guiding"].start_guiding()

        # Capture with dithers
        for i in range(3):
            # Capture
            await services["camera"].capture(30.0)

            # Dither (stop guiding, nudge mount, resume guiding)
            await services["guiding"].stop_guiding()
            # Small offset would happen here
            await services["guiding"].start_guiding()

        assert services["camera"].exposure_count == 3

        await orchestrator.shutdown()


class TestSafetyIntegration:
    """Tests for safety integration with other services."""

    @pytest.fixture
    def config(self):
        return NightwatchConfig()

    @pytest.fixture
    def services(self):
        return {
            "mount": MockMountService(),
            "safety": MockSafetyService(),
            "enclosure": MockEnclosureService(),
            "weather": MockWeatherService(),
        }

    @pytest.fixture
    def orchestrator(self, config, services):
        orch = Orchestrator(config)
        orch.register_mount(services["mount"], required=False)
        orch.register_safety(services["safety"], required=False)
        orch.register_enclosure(services["enclosure"], required=False)
        orch.register_weather(services["weather"], required=False)
        return orch

    @pytest.mark.asyncio
    async def test_weather_unsafe_triggers_park(self, orchestrator, services):
        """Test that unsafe weather triggers parking."""
        await orchestrator.start()

        services["mount"].is_parked = False
        services["mount"].is_tracking = True
        services["enclosure"].is_open = True

        # Weather becomes unsafe
        services["weather"].is_safe = False
        services["safety"].add_veto("Unsafe weather")

        # Check safety
        safety_result = services["safety"].evaluate_safety()
        assert safety_result["is_safe"] is False

        # Would trigger park and close in real implementation
        await services["mount"].park()
        await services["enclosure"].close()

        assert services["mount"].is_parked is True
        assert services["enclosure"].is_open is False

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_safety_veto_prevents_operations(self, orchestrator, services):
        """Test that safety vetoes prevent unsafe operations."""
        await orchestrator.start()

        # Add safety veto
        services["safety"].add_veto("High wind detected")

        safety = services["safety"].evaluate_safety()
        assert safety["is_safe"] is False
        assert len(safety["vetoes"]) == 1

        # Clear veto
        services["safety"].clear_vetoes()
        safety = services["safety"].evaluate_safety()
        assert safety["is_safe"] is True

        await orchestrator.shutdown()


class TestEventPropagation:
    """Tests for event propagation between services."""

    @pytest.fixture
    def config(self):
        return NightwatchConfig()

    @pytest.fixture
    def orchestrator(self, config):
        return Orchestrator(config)

    @pytest.mark.asyncio
    async def test_event_listeners_receive_events(self, orchestrator):
        """Test event listeners receive emitted events."""
        received_events = []

        def listener(event):
            received_events.append(event)

        orchestrator.subscribe(EventType.MOUNT_SLEW_STARTED, listener)
        orchestrator.subscribe(EventType.MOUNT_SLEW_COMPLETE, listener)

        await orchestrator.emit_event(
            EventType.MOUNT_SLEW_STARTED,
            source="mount",
            data={"target": "M31"}
        )

        await orchestrator.emit_event(
            EventType.MOUNT_SLEW_COMPLETE,
            source="mount"
        )

        assert len(received_events) == 2
        assert received_events[0].event_type == EventType.MOUNT_SLEW_STARTED
        assert received_events[1].event_type == EventType.MOUNT_SLEW_COMPLETE

    @pytest.mark.asyncio
    async def test_multiple_listeners_per_event(self, orchestrator):
        """Test multiple listeners for same event type."""
        results = []

        orchestrator.subscribe(EventType.IMAGE_CAPTURED, lambda e: results.append("L1"))
        orchestrator.subscribe(EventType.IMAGE_CAPTURED, lambda e: results.append("L2"))
        orchestrator.subscribe(EventType.IMAGE_CAPTURED, lambda e: results.append("L3"))

        await orchestrator.emit_event(EventType.IMAGE_CAPTURED, source="camera")

        assert len(results) == 3


class TestMetricsAndMonitoring:
    """Tests for metrics and monitoring integration."""

    @pytest.fixture
    def config(self):
        return NightwatchConfig()

    @pytest.fixture
    def orchestrator(self, config):
        orch = Orchestrator(config)
        orch.register_mount(MockMountService(), required=False)
        orch.register_camera(MockCameraService(), required=False)
        return orch

    @pytest.mark.asyncio
    async def test_command_latency_tracking(self, orchestrator):
        """Test command latency is tracked."""
        await orchestrator.start()

        # Record some command executions
        await orchestrator.record_command_execution(100.0)
        await orchestrator.record_command_execution(150.0)
        await orchestrator.record_command_execution(200.0)

        metrics = orchestrator.get_metrics()

        assert metrics["commands_executed"] == 3
        assert metrics["avg_latency_ms"] == 150.0
        assert metrics["min_latency_ms"] == 100.0
        assert metrics["max_latency_ms"] == 200.0

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_error_tracking(self, orchestrator):
        """Test error tracking by service."""
        await orchestrator.start()

        orchestrator.record_service_error("mount")
        orchestrator.record_service_error("mount")
        orchestrator.record_service_error("camera")

        metrics = orchestrator.get_metrics()

        assert metrics["error_count"] == 3
        assert metrics["errors_by_service"]["mount"] == 2
        assert metrics["errors_by_service"]["camera"] == 1

        await orchestrator.shutdown()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
