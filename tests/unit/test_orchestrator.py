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
