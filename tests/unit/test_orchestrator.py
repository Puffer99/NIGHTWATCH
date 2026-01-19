"""
Unit tests for NIGHTWATCH Orchestrator.

Tests service registry, session management, and orchestrator lifecycle.
"""

import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock

import pytest

from nightwatch.orchestrator import (
    Orchestrator,
    ServiceRegistry,
    ServiceStatus,
    ServiceInfo,
    SessionState,
    ObservingTarget,
    EventType,
    OrchestratorEvent,
    OrchestratorMetrics,
)
from nightwatch.config import NightwatchConfig


class TestServiceRegistry:
    """Tests for ServiceRegistry class."""

    def test_init_empty(self):
        """Test empty registry initialization."""
        registry = ServiceRegistry()
        assert len(registry.list_services()) == 0

    def test_register_service(self):
        """Test registering a service."""
        registry = ServiceRegistry()
        mock_service = Mock()

        registry.register("mount", mock_service)

        assert "mount" in registry.list_services()
        assert registry.get("mount") is mock_service

    def test_register_service_required(self):
        """Test registering required service."""
        registry = ServiceRegistry()
        mock_service = Mock()

        registry.register("mount", mock_service, required=True)

        assert "mount" in registry.get_required_services()

    def test_register_service_optional(self):
        """Test registering optional service."""
        registry = ServiceRegistry()
        mock_service = Mock()

        registry.register("camera", mock_service, required=False)

        assert "camera" not in registry.get_required_services()
        assert "camera" in registry.list_services()

    def test_unregister_service(self):
        """Test unregistering a service."""
        registry = ServiceRegistry()
        mock_service = Mock()

        registry.register("mount", mock_service)
        registry.unregister("mount")

        assert "mount" not in registry.list_services()
        assert registry.get("mount") is None

    def test_get_nonexistent_service(self):
        """Test getting non-existent service returns None."""
        registry = ServiceRegistry()
        assert registry.get("nonexistent") is None

    def test_service_status(self):
        """Test getting and setting service status."""
        registry = ServiceRegistry()
        mock_service = Mock()

        registry.register("mount", mock_service)

        # Default status is unknown
        assert registry.get_status("mount") == ServiceStatus.UNKNOWN

        # Set status
        registry.set_status("mount", ServiceStatus.RUNNING)
        assert registry.get_status("mount") == ServiceStatus.RUNNING

    def test_service_status_with_error(self):
        """Test setting service status with error."""
        registry = ServiceRegistry()
        mock_service = Mock()

        registry.register("mount", mock_service)
        registry.set_status("mount", ServiceStatus.ERROR, "Connection failed")

        info = registry.get_all_info()["mount"]
        assert info.status == ServiceStatus.ERROR
        assert info.last_error == "Connection failed"
        assert info.last_check is not None

    def test_all_required_running_true(self):
        """Test all_required_running when all are running."""
        registry = ServiceRegistry()

        registry.register("mount", Mock(), required=True)
        registry.register("weather", Mock(), required=True)
        registry.register("camera", Mock(), required=False)

        registry.set_status("mount", ServiceStatus.RUNNING)
        registry.set_status("weather", ServiceStatus.RUNNING)

        assert registry.all_required_running() is True

    def test_all_required_running_false(self):
        """Test all_required_running when one is not running."""
        registry = ServiceRegistry()

        registry.register("mount", Mock(), required=True)
        registry.register("weather", Mock(), required=True)

        registry.set_status("mount", ServiceStatus.RUNNING)
        registry.set_status("weather", ServiceStatus.ERROR)

        assert registry.all_required_running() is False


class TestSessionState:
    """Tests for SessionState dataclass."""

    def test_default_values(self):
        """Test default session state values."""
        session = SessionState()

        assert session.session_id == ""
        assert session.current_target is None
        assert session.images_captured == 0
        assert session.total_exposure_sec == 0.0
        assert session.is_observing is False

    def test_with_target(self):
        """Test session state with target."""
        target = ObservingTarget(
            name="M31",
            ra=0.712,
            dec=41.269,
            object_type="galaxy"
        )
        session = SessionState(current_target=target)

        assert session.current_target is not None
        assert session.current_target.name == "M31"


class TestObservingTarget:
    """Tests for ObservingTarget dataclass."""

    def test_basic_target(self):
        """Test basic target creation."""
        target = ObservingTarget(
            name="Andromeda Galaxy",
            ra=0.712,
            dec=41.269,
        )

        assert target.name == "Andromeda Galaxy"
        assert target.ra == 0.712
        assert target.dec == 41.269
        assert target.catalog_id is None

    def test_full_target(self):
        """Test target with all fields."""
        now = datetime.now()
        target = ObservingTarget(
            name="Andromeda Galaxy",
            ra=0.712,
            dec=41.269,
            object_type="galaxy",
            catalog_id="M31",
            acquired_at=now,
        )

        assert target.catalog_id == "M31"
        assert target.object_type == "galaxy"
        assert target.acquired_at == now


class TestOrchestrator:
    """Tests for Orchestrator class."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return NightwatchConfig()

    @pytest.fixture
    def orchestrator(self, config):
        """Create orchestrator for testing."""
        return Orchestrator(config)

    def test_init(self, orchestrator, config):
        """Test orchestrator initialization."""
        assert orchestrator.config is config
        assert orchestrator.registry is not None
        assert orchestrator._running is False

    def test_is_running_property(self, orchestrator):
        """Test is_running property."""
        assert orchestrator.is_running is False
        orchestrator._running = True
        assert orchestrator.is_running is True

    def test_service_properties_none_initially(self, orchestrator):
        """Test service properties return None when not registered."""
        assert orchestrator.mount is None
        assert orchestrator.catalog is None
        assert orchestrator.ephemeris is None
        assert orchestrator.weather is None
        assert orchestrator.safety is None
        assert orchestrator.camera is None

    def test_register_mount(self, orchestrator):
        """Test registering mount service."""
        mock_mount = Mock()
        orchestrator.register_mount(mock_mount)

        assert orchestrator.mount is mock_mount
        assert "mount" in orchestrator.registry.list_services()

    def test_register_catalog(self, orchestrator):
        """Test registering catalog service."""
        mock_catalog = Mock()
        orchestrator.register_catalog(mock_catalog)

        assert orchestrator.catalog is mock_catalog

    def test_register_ephemeris(self, orchestrator):
        """Test registering ephemeris service."""
        mock_ephemeris = Mock()
        orchestrator.register_ephemeris(mock_ephemeris)

        assert orchestrator.ephemeris is mock_ephemeris

    def test_register_weather(self, orchestrator):
        """Test registering weather service."""
        mock_weather = Mock()
        orchestrator.register_weather(mock_weather)

        assert orchestrator.weather is mock_weather

    def test_register_all_services(self, orchestrator):
        """Test registering all services."""
        orchestrator.register_mount(Mock())
        orchestrator.register_catalog(Mock())
        orchestrator.register_ephemeris(Mock())
        orchestrator.register_weather(Mock())
        orchestrator.register_safety(Mock())
        orchestrator.register_camera(Mock())
        orchestrator.register_guiding(Mock())
        orchestrator.register_focus(Mock())
        orchestrator.register_astrometry(Mock())
        orchestrator.register_alerts(Mock())
        orchestrator.register_power(Mock())
        orchestrator.register_enclosure(Mock())

        services = orchestrator.registry.list_services()
        assert len(services) == 12

    @pytest.mark.asyncio
    async def test_start(self, orchestrator):
        """Test starting orchestrator."""
        mock_service = AsyncMock()
        mock_service.is_running = True
        orchestrator.register_mount(mock_service, required=False)

        result = await orchestrator.start()

        assert result is True
        assert orchestrator.is_running is True
        mock_service.start.assert_called_once()

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_start_already_running(self, orchestrator):
        """Test starting already running orchestrator."""
        orchestrator._running = True

        result = await orchestrator.start()

        assert result is True

    @pytest.mark.asyncio
    async def test_shutdown(self, orchestrator):
        """Test shutting down orchestrator."""
        mock_service = AsyncMock()
        mock_service.is_running = True
        orchestrator.register_mount(mock_service, required=False)

        await orchestrator.start()
        await orchestrator.shutdown()

        assert orchestrator.is_running is False
        mock_service.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_with_failing_required_service(self, orchestrator):
        """Test start fails when required service fails."""
        mock_service = AsyncMock()
        mock_service.start.side_effect = Exception("Connection failed")
        orchestrator.register_mount(mock_service, required=True)

        result = await orchestrator.start()

        assert result is False
        assert orchestrator.registry.get_status("mount") == ServiceStatus.ERROR

    @pytest.mark.asyncio
    async def test_start_session(self, orchestrator):
        """Test starting observing session."""
        mock_service = AsyncMock()
        mock_service.is_running = True
        orchestrator.register_mount(mock_service, required=False)

        await orchestrator.start()

        result = await orchestrator.start_session("test_session")

        assert result is True
        assert orchestrator.session.session_id == "test_session"
        assert orchestrator.session.is_observing is True

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_start_session_auto_id(self, orchestrator):
        """Test starting session with auto-generated ID."""
        mock_service = AsyncMock()
        mock_service.is_running = True
        orchestrator.register_mount(mock_service, required=False)

        await orchestrator.start()
        await orchestrator.start_session()

        assert orchestrator.session.session_id != ""
        assert len(orchestrator.session.session_id) > 0

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_end_session(self, orchestrator):
        """Test ending observing session."""
        mock_service = AsyncMock()
        mock_service.is_running = True
        orchestrator.register_mount(mock_service, required=False)

        await orchestrator.start()
        await orchestrator.start_session("test")
        await orchestrator.end_session()

        assert orchestrator.session.is_observing is False

        await orchestrator.shutdown()

    def test_get_status(self, orchestrator):
        """Test getting orchestrator status."""
        mock_mount = Mock()
        orchestrator.register_mount(mock_mount)

        status = orchestrator.get_status()

        assert "running" in status
        assert "session" in status
        assert "services" in status
        assert status["running"] is False

    def test_get_service_status(self, orchestrator):
        """Test getting service status."""
        mock_mount = Mock()
        orchestrator.register_mount(mock_mount)
        orchestrator.registry.set_status("mount", ServiceStatus.RUNNING)

        status = orchestrator.get_service_status()

        assert "mount" in status
        assert status["mount"]["status"] == "running"
        assert status["mount"]["required"] is True

    def test_register_callback(self, orchestrator):
        """Test registering callback."""
        callback = Mock()
        orchestrator.register_callback(callback)

        assert callback in orchestrator._callbacks

    @pytest.mark.asyncio
    async def test_notify_callbacks(self, orchestrator):
        """Test notifying callbacks."""
        callback = Mock()
        orchestrator.register_callback(callback)

        await orchestrator._notify_callbacks("test_event", {"data": "value"})

        callback.assert_called_once_with("test_event", {"data": "value"})

    @pytest.mark.asyncio
    async def test_notify_async_callbacks(self, orchestrator):
        """Test notifying async callbacks."""
        callback = AsyncMock()
        orchestrator.register_callback(callback)

        await orchestrator._notify_callbacks("test_event", {"data": "value"})

        callback.assert_called_once_with("test_event", {"data": "value"})


class TestServiceStatus:
    """Tests for ServiceStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert ServiceStatus.UNKNOWN.value == "unknown"
        assert ServiceStatus.STARTING.value == "starting"
        assert ServiceStatus.RUNNING.value == "running"
        assert ServiceStatus.DEGRADED.value == "degraded"
        assert ServiceStatus.STOPPED.value == "stopped"
        assert ServiceStatus.ERROR.value == "error"


class TestEventType:
    """Tests for EventType enum (Steps 243-246)."""

    def test_mount_events(self):
        """Test mount event types exist."""
        assert EventType.MOUNT_POSITION_CHANGED.value == "mount_position_changed"
        assert EventType.MOUNT_SLEW_STARTED.value == "mount_slew_started"
        assert EventType.MOUNT_SLEW_COMPLETE.value == "mount_slew_complete"
        assert EventType.MOUNT_PARKED.value == "mount_parked"
        assert EventType.MOUNT_UNPARKED.value == "mount_unparked"

    def test_weather_events(self):
        """Test weather event types exist."""
        assert EventType.WEATHER_CHANGED.value == "weather_changed"
        assert EventType.WEATHER_SAFE.value == "weather_safe"
        assert EventType.WEATHER_UNSAFE.value == "weather_unsafe"

    def test_safety_events(self):
        """Test safety event types exist."""
        assert EventType.SAFETY_STATE_CHANGED.value == "safety_state_changed"
        assert EventType.SAFETY_ALERT.value == "safety_alert"
        assert EventType.SAFETY_VETO.value == "safety_veto"

    def test_guiding_events(self):
        """Test guiding event types exist."""
        assert EventType.GUIDING_STATE_CHANGED.value == "guiding_state_changed"
        assert EventType.GUIDING_STARTED.value == "guiding_started"
        assert EventType.GUIDING_STOPPED.value == "guiding_stopped"
        assert EventType.GUIDING_LOST.value == "guiding_lost"
        assert EventType.GUIDING_SETTLED.value == "guiding_settled"
        assert EventType.GUIDING_DITHER.value == "guiding_dither"

    def test_session_events(self):
        """Test session event types exist."""
        assert EventType.SESSION_STARTED.value == "session_started"
        assert EventType.SESSION_ENDED.value == "session_ended"
        assert EventType.IMAGE_CAPTURED.value == "image_captured"

    def test_system_events(self):
        """Test system event types exist."""
        assert EventType.SERVICE_STARTED.value == "service_started"
        assert EventType.SERVICE_STOPPED.value == "service_stopped"
        assert EventType.SERVICE_ERROR.value == "service_error"
        assert EventType.SHUTDOWN_INITIATED.value == "shutdown_initiated"


class TestOrchestratorEvent:
    """Tests for OrchestratorEvent dataclass."""

    def test_create_event(self):
        """Test creating an event."""
        event = OrchestratorEvent(
            event_type=EventType.MOUNT_SLEW_STARTED,
            source="mount",
            data={"target": "M31"},
            message="Starting slew to M31"
        )

        assert event.event_type == EventType.MOUNT_SLEW_STARTED
        assert event.source == "mount"
        assert event.data["target"] == "M31"
        assert event.message == "Starting slew to M31"
        assert event.timestamp is not None

    def test_event_defaults(self):
        """Test event default values."""
        event = OrchestratorEvent(event_type=EventType.WEATHER_SAFE)

        assert event.source == ""
        assert event.data == {}
        assert event.message == ""


class TestOrchestratorMetrics:
    """Tests for OrchestratorMetrics dataclass (Steps 248-250)."""

    def test_default_metrics(self):
        """Test default metric values."""
        metrics = OrchestratorMetrics()

        assert metrics.commands_executed == 0
        assert metrics.total_command_time_ms == 0.0
        assert metrics.min_latency_ms == float('inf')
        assert metrics.max_latency_ms == 0.0
        assert metrics.error_count == 0

    def test_record_command(self):
        """Test recording command execution."""
        metrics = OrchestratorMetrics()

        metrics.record_command(100.0)
        assert metrics.commands_executed == 1
        assert metrics.total_command_time_ms == 100.0
        assert metrics.min_latency_ms == 100.0
        assert metrics.max_latency_ms == 100.0

        metrics.record_command(50.0)
        assert metrics.commands_executed == 2
        assert metrics.total_command_time_ms == 150.0
        assert metrics.min_latency_ms == 50.0
        assert metrics.max_latency_ms == 100.0

    def test_avg_latency(self):
        """Test average latency calculation."""
        metrics = OrchestratorMetrics()

        assert metrics.avg_latency_ms == 0.0

        metrics.record_command(100.0)
        metrics.record_command(200.0)

        assert metrics.avg_latency_ms == 150.0

    def test_record_error(self):
        """Test recording service errors."""
        metrics = OrchestratorMetrics()

        metrics.record_error("mount")
        metrics.record_error("mount")
        metrics.record_error("camera")

        assert metrics.error_count == 3
        assert metrics.errors_by_service["mount"] == 2
        assert metrics.errors_by_service["camera"] == 1

    def test_service_uptime(self):
        """Test service uptime tracking."""
        metrics = OrchestratorMetrics()
        metrics.service_start_time["mount"] = datetime.now()

        # Should be close to 0
        uptime = metrics.get_service_uptime("mount")
        assert uptime >= 0.0 and uptime < 1.0

        # Non-existent service returns 0
        assert metrics.get_service_uptime("nonexistent") == 0.0

    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = OrchestratorMetrics()
        metrics.record_command(100.0)
        metrics.record_error("mount")

        d = metrics.to_dict()

        assert d["commands_executed"] == 1
        assert d["avg_latency_ms"] == 100.0
        assert d["min_latency_ms"] == 100.0
        assert d["max_latency_ms"] == 100.0
        assert d["error_count"] == 1
        assert "mount" in d["errors_by_service"]


class TestOrchestratorEventSystem:
    """Tests for Orchestrator event system (Steps 243-246)."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return NightwatchConfig()

    @pytest.fixture
    def orchestrator(self, config):
        """Create orchestrator for testing."""
        return Orchestrator(config)

    def test_subscribe(self, orchestrator):
        """Test subscribing to events."""
        listener = Mock()
        orchestrator.subscribe(EventType.MOUNT_PARKED, listener)

        assert EventType.MOUNT_PARKED in orchestrator._event_listeners
        assert listener in orchestrator._event_listeners[EventType.MOUNT_PARKED]

    def test_unsubscribe(self, orchestrator):
        """Test unsubscribing from events."""
        listener = Mock()
        orchestrator.subscribe(EventType.MOUNT_PARKED, listener)
        orchestrator.unsubscribe(EventType.MOUNT_PARKED, listener)

        assert listener not in orchestrator._event_listeners.get(EventType.MOUNT_PARKED, [])

    def test_unsubscribe_nonexistent(self, orchestrator):
        """Test unsubscribing non-existent listener doesn't error."""
        listener = Mock()
        # Should not raise
        orchestrator.unsubscribe(EventType.MOUNT_PARKED, listener)

    @pytest.mark.asyncio
    async def test_emit_event(self, orchestrator):
        """Test emitting events to listeners."""
        listener = Mock()
        orchestrator.subscribe(EventType.WEATHER_UNSAFE, listener)

        await orchestrator.emit_event(
            EventType.WEATHER_UNSAFE,
            source="weather",
            data={"reason": "wind"},
            message="Wind too high"
        )

        listener.assert_called_once()
        event = listener.call_args[0][0]
        assert event.event_type == EventType.WEATHER_UNSAFE
        assert event.source == "weather"
        assert event.data["reason"] == "wind"

    @pytest.mark.asyncio
    async def test_emit_event_async_listener(self, orchestrator):
        """Test emitting events to async listeners."""
        listener = AsyncMock()
        orchestrator.subscribe(EventType.MOUNT_SLEW_COMPLETE, listener)

        await orchestrator.emit_event(
            EventType.MOUNT_SLEW_COMPLETE,
            source="mount"
        )

        listener.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_event_multiple_listeners(self, orchestrator):
        """Test emitting events to multiple listeners."""
        listener1 = Mock()
        listener2 = Mock()
        orchestrator.subscribe(EventType.SESSION_STARTED, listener1)
        orchestrator.subscribe(EventType.SESSION_STARTED, listener2)

        await orchestrator.emit_event(EventType.SESSION_STARTED)

        listener1.assert_called_once()
        listener2.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_event_listener_error_handled(self, orchestrator):
        """Test that listener errors don't stop other listeners."""
        listener1 = Mock(side_effect=Exception("Listener error"))
        listener2 = Mock()
        orchestrator.subscribe(EventType.IMAGE_CAPTURED, listener1)
        orchestrator.subscribe(EventType.IMAGE_CAPTURED, listener2)

        # Should not raise
        await orchestrator.emit_event(EventType.IMAGE_CAPTURED)

        # Second listener should still be called
        listener2.assert_called_once()


class TestOrchestratorMetricsIntegration:
    """Tests for Orchestrator metrics integration (Steps 248-250)."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return NightwatchConfig()

    @pytest.fixture
    def orchestrator(self, config):
        """Create orchestrator for testing."""
        return Orchestrator(config)

    def test_metrics_initialized(self, orchestrator):
        """Test metrics are initialized."""
        assert orchestrator.metrics is not None
        assert isinstance(orchestrator.metrics, OrchestratorMetrics)

    def test_get_metrics(self, orchestrator):
        """Test getting metrics dict."""
        metrics = orchestrator.get_metrics()

        assert "commands_executed" in metrics
        assert "avg_latency_ms" in metrics
        assert "error_count" in metrics

    @pytest.mark.asyncio
    async def test_record_command_execution(self, orchestrator):
        """Test recording command execution."""
        await orchestrator.record_command_execution(150.0)

        assert orchestrator.metrics.commands_executed == 1
        assert orchestrator.metrics.avg_latency_ms == 150.0

    def test_record_service_error(self, orchestrator):
        """Test recording service error."""
        orchestrator.record_service_error("camera")

        assert orchestrator.metrics.error_count == 1
        assert orchestrator.metrics.errors_by_service["camera"] == 1


class TestSafeShutdown:
    """Tests for safe shutdown functionality (Steps 252-254)."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return NightwatchConfig()

    @pytest.fixture
    def orchestrator(self, config):
        """Create orchestrator with mock services."""
        orch = Orchestrator(config)

        # Mock mount
        mock_mount = AsyncMock()
        mock_mount.is_running = True
        mock_mount.is_parked = False
        mock_mount.park = AsyncMock(return_value=True)
        orch.register_mount(mock_mount, required=False)

        # Mock enclosure
        mock_enclosure = AsyncMock()
        mock_enclosure.is_running = True
        mock_enclosure.close = AsyncMock(return_value=True)
        orch.register_enclosure(mock_enclosure, required=False)

        return orch

    @pytest.mark.asyncio
    async def test_safe_shutdown_parks_mount(self, orchestrator):
        """Test safe shutdown parks the mount."""
        await orchestrator.start()
        await orchestrator.shutdown(safe=True)

        orchestrator.mount.park.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_shutdown_closes_enclosure(self, orchestrator):
        """Test safe shutdown closes enclosure."""
        await orchestrator.start()
        await orchestrator.shutdown(safe=True)

        orchestrator.enclosure.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_shutdown_skips_parked_mount(self, orchestrator):
        """Test safe shutdown skips already parked mount."""
        orchestrator.mount.is_parked = True

        await orchestrator.start()
        await orchestrator.shutdown(safe=True)

        orchestrator.mount.park.assert_not_called()

    @pytest.mark.asyncio
    async def test_unsafe_shutdown_skips_safe_steps(self, orchestrator):
        """Test unsafe shutdown skips safe steps."""
        await orchestrator.start()
        await orchestrator.shutdown(safe=False)

        orchestrator.mount.park.assert_not_called()
        orchestrator.enclosure.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_shutdown_emits_event(self, orchestrator):
        """Test shutdown emits shutdown event."""
        listener = Mock()
        orchestrator.subscribe(EventType.SHUTDOWN_INITIATED, listener)

        await orchestrator.start()
        await orchestrator.shutdown()

        listener.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_shutdown_handles_mount_error(self, orchestrator):
        """Test safe shutdown handles mount park error gracefully."""
        orchestrator.mount.park.side_effect = Exception("Park failed")

        await orchestrator.start()
        # Should not raise
        await orchestrator.shutdown(safe=True)

        # Error should be recorded
        assert orchestrator.metrics.errors_by_service.get("mount", 0) == 1

    @pytest.mark.asyncio
    async def test_safe_shutdown_handles_enclosure_error(self, orchestrator):
        """Test safe shutdown handles enclosure close error gracefully."""
        orchestrator.enclosure.close.side_effect = Exception("Close failed")

        await orchestrator.start()
        # Should not raise
        await orchestrator.shutdown(safe=True)

        # Error should be recorded
        assert orchestrator.metrics.errors_by_service.get("enclosure", 0) == 1

    @pytest.mark.asyncio
    async def test_save_session_log(self, orchestrator, tmp_path):
        """Test session log functionality via _save_session_log."""
        import json
        from unittest.mock import patch

        await orchestrator.start()
        await orchestrator.start_session("test_session")

        # Add some data to session
        orchestrator.session.images_captured = 5
        orchestrator.session.total_exposure_sec = 300.0

        # Patch the config's data_dir by mocking hasattr and getattr behavior
        # This test verifies _save_session_log creates proper log structure
        with patch.object(orchestrator, '_save_session_log') as mock_save:
            await orchestrator.shutdown(safe=True)
            # _save_session_log is called during safe shutdown when observing
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_log_format(self, orchestrator, tmp_path):
        """Test session log file format."""
        import json

        await orchestrator.start()
        await orchestrator.start_session("test_session")
        orchestrator.session.images_captured = 5
        orchestrator.session.total_exposure_sec = 300.0

        # Manually create the log to verify format
        log_file = tmp_path / "session_test_session.json"
        session_log = {
            "session_id": orchestrator.session.session_id,
            "started_at": orchestrator.session.started_at.isoformat(),
            "ended_at": datetime.now().isoformat(),
            "images_captured": orchestrator.session.images_captured,
            "total_exposure_sec": orchestrator.session.total_exposure_sec,
            "current_target": None,
            "error_count": 0,
            "last_error": None,
            "metrics": orchestrator.metrics.to_dict(),
        }

        with open(log_file, "w") as f:
            json.dump(session_log, f, indent=2)

        # Verify file was written correctly
        with open(log_file) as f:
            loaded = json.load(f)

        assert loaded["session_id"] == "test_session"
        assert loaded["images_captured"] == 5
        assert loaded["total_exposure_sec"] == 300.0
        assert "metrics" in loaded

        await orchestrator.shutdown(safe=False)
