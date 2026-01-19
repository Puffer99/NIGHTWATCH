"""
NIGHTWATCH Orchestrator
Central control loop for observatory automation.

The Orchestrator is responsible for:
- Service lifecycle management (startup, shutdown, health monitoring)
- Session state management (observing session context)
- Voice pipeline coordination (STT -> LLM -> Tool -> TTS)
- Error recovery and graceful degradation
- Event routing between services

Architecture:
    +-----------------+
    |  Voice Input    |
    +-------+---------+
            |
    +-------v---------+
    |   Orchestrator  |<---> Session State
    +-------+---------+
            |
    +-------v---------+
    | Service Registry|
    +-------+---------+
            |
    +-------v---------+
    |    Services     |
    | (Mount, Camera, |
    |  Weather, etc.) |
    +-----------------+

Usage:
    from nightwatch.config import load_config
    from nightwatch.orchestrator import Orchestrator

    config = load_config()
    orchestrator = Orchestrator(config)

    # Register services
    orchestrator.register_mount(mount_service)
    orchestrator.register_camera(camera_service)

    # Start the orchestrator
    await orchestrator.start()

    # Process voice command
    response = await orchestrator.process_command("slew to M31")

    # Shutdown
    await orchestrator.shutdown()
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, TypeVar

from nightwatch.config import NightwatchConfig
from nightwatch.exceptions import NightwatchError

logger = logging.getLogger("NIGHTWATCH.Orchestrator")


__all__ = [
    "Orchestrator",
    "ServiceRegistry",
    "ServiceStatus",
    "SessionState",
    "ObservingTarget",
]


# =============================================================================
# Service Protocol Definitions
# =============================================================================


class ServiceProtocol(Protocol):
    """Protocol defining the interface all services must implement."""

    async def start(self) -> None:
        """Start the service."""
        ...

    async def stop(self) -> None:
        """Stop the service."""
        ...

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        ...


class MountServiceProtocol(ServiceProtocol, Protocol):
    """Protocol for mount control service."""

    async def slew_to_coordinates(self, ra: float, dec: float) -> bool:
        """Slew to RA/Dec coordinates."""
        ...

    async def park(self) -> bool:
        """Park the mount."""
        ...

    async def unpark(self) -> bool:
        """Unpark the mount."""
        ...

    @property
    def is_parked(self) -> bool:
        """Check if mount is parked."""
        ...

    @property
    def is_tracking(self) -> bool:
        """Check if mount is tracking."""
        ...


class CatalogServiceProtocol(ServiceProtocol, Protocol):
    """Protocol for catalog lookup service."""

    def lookup(self, name: str) -> Optional[Any]:
        """Look up an object by name."""
        ...

    def resolve_object(self, name: str) -> Optional[tuple]:
        """Resolve object to RA/Dec coordinates."""
        ...


class EphemerisServiceProtocol(ServiceProtocol, Protocol):
    """Protocol for ephemeris/planetary service."""

    def get_planet_position(self, planet: str) -> Optional[tuple]:
        """Get current planet position."""
        ...

    def get_sun_altitude(self) -> float:
        """Get current sun altitude."""
        ...

    def get_twilight_times(self) -> Dict[str, datetime]:
        """Get twilight times for today."""
        ...


class WeatherServiceProtocol(ServiceProtocol, Protocol):
    """Protocol for weather monitoring service."""

    @property
    def is_safe(self) -> bool:
        """Check if weather is safe for observing."""
        ...

    @property
    def current_conditions(self) -> Dict[str, Any]:
        """Get current weather conditions."""
        ...


class SafetyServiceProtocol(ServiceProtocol, Protocol):
    """Protocol for safety monitoring service."""

    @property
    def is_safe(self) -> bool:
        """Check overall safety status."""
        ...

    def get_unsafe_reasons(self) -> List[str]:
        """Get list of reasons if unsafe."""
        ...


class CameraServiceProtocol(ServiceProtocol, Protocol):
    """Protocol for camera service."""

    async def capture(self, exposure: float, gain: int = 0) -> Any:
        """Capture an image."""
        ...

    @property
    def is_exposing(self) -> bool:
        """Check if currently exposing."""
        ...


class GuidingServiceProtocol(ServiceProtocol, Protocol):
    """Protocol for guiding service."""

    async def start_guiding(self) -> bool:
        """Start autoguiding."""
        ...

    async def stop_guiding(self) -> bool:
        """Stop autoguiding."""
        ...

    @property
    def is_guiding(self) -> bool:
        """Check if currently guiding."""
        ...


class FocusServiceProtocol(ServiceProtocol, Protocol):
    """Protocol for focus service."""

    async def autofocus(self) -> bool:
        """Run autofocus routine."""
        ...

    async def move_to(self, position: int) -> bool:
        """Move to absolute position."""
        ...


class AstrometryServiceProtocol(ServiceProtocol, Protocol):
    """Protocol for plate solving service."""

    async def solve(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Solve an image."""
        ...


class AlertServiceProtocol(ServiceProtocol, Protocol):
    """Protocol for alert notification service."""

    async def send_alert(self, level: str, message: str) -> bool:
        """Send an alert notification."""
        ...


class PowerServiceProtocol(ServiceProtocol, Protocol):
    """Protocol for power management service."""

    @property
    def on_battery(self) -> bool:
        """Check if running on battery."""
        ...

    @property
    def battery_percent(self) -> int:
        """Get battery percentage."""
        ...


class EnclosureServiceProtocol(ServiceProtocol, Protocol):
    """Protocol for enclosure/roof service."""

    async def open(self) -> bool:
        """Open the roof."""
        ...

    async def close(self) -> bool:
        """Close the roof."""
        ...

    @property
    def is_open(self) -> bool:
        """Check if roof is open."""
        ...


# =============================================================================
# Service Status and Registry
# =============================================================================


class ServiceStatus(Enum):
    """Service health status."""
    UNKNOWN = "unknown"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ServiceInfo:
    """Information about a registered service."""
    name: str
    service: Any
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_error: Optional[str] = None
    last_check: Optional[datetime] = None
    required: bool = True  # If True, orchestrator won't start without it


class ServiceRegistry:
    """
    Registry for all observatory services.

    Provides dependency injection and service discovery.
    Services are registered by type and can be retrieved by name.
    """

    def __init__(self):
        """Initialize empty service registry."""
        self._services: Dict[str, ServiceInfo] = {}
        self._callbacks: List[Callable] = []

    def register(self, name: str, service: Any, required: bool = True) -> None:
        """
        Register a service.

        Args:
            name: Service identifier (e.g., "mount", "camera")
            service: The service instance
            required: If True, orchestrator requires this service to start
        """
        self._services[name] = ServiceInfo(
            name=name,
            service=service,
            status=ServiceStatus.UNKNOWN,
            required=required,
        )
        logger.info(f"Registered service: {name} (required={required})")

    def unregister(self, name: str) -> None:
        """Unregister a service."""
        if name in self._services:
            del self._services[name]
            logger.info(f"Unregistered service: {name}")

    def get(self, name: str) -> Optional[Any]:
        """
        Get a service by name.

        Args:
            name: Service identifier

        Returns:
            Service instance or None if not found
        """
        info = self._services.get(name)
        return info.service if info else None

    def get_status(self, name: str) -> ServiceStatus:
        """Get service status."""
        info = self._services.get(name)
        return info.status if info else ServiceStatus.UNKNOWN

    def set_status(self, name: str, status: ServiceStatus, error: Optional[str] = None):
        """Update service status."""
        if name in self._services:
            self._services[name].status = status
            self._services[name].last_check = datetime.now()
            if error:
                self._services[name].last_error = error

    def list_services(self) -> List[str]:
        """List all registered service names."""
        return list(self._services.keys())

    def get_required_services(self) -> List[str]:
        """List required services."""
        return [name for name, info in self._services.items() if info.required]

    def get_all_info(self) -> Dict[str, ServiceInfo]:
        """Get info for all services."""
        return self._services.copy()

    def all_required_running(self) -> bool:
        """Check if all required services are running."""
        for name, info in self._services.items():
            if info.required and info.status != ServiceStatus.RUNNING:
                return False
        return True


# =============================================================================
# Session State
# =============================================================================


@dataclass
class ObservingTarget:
    """Current observing target information."""
    name: str
    ra: float  # Hours
    dec: float  # Degrees
    object_type: Optional[str] = None
    catalog_id: Optional[str] = None
    acquired_at: Optional[datetime] = None


@dataclass
class SessionState:
    """
    Current observing session state.

    Tracks the current target, imaging progress, and session metadata.
    """
    # Session info
    started_at: datetime = field(default_factory=datetime.now)
    session_id: str = ""

    # Current target
    current_target: Optional[ObservingTarget] = None

    # Imaging state
    images_captured: int = 0
    total_exposure_sec: float = 0.0
    current_filter: Optional[str] = None

    # Status flags
    is_observing: bool = False
    is_imaging: bool = False
    is_slewing: bool = False

    # Error tracking
    last_error: Optional[str] = None
    error_count: int = 0


# =============================================================================
# Orchestrator
# =============================================================================


class Orchestrator:
    """
    Central orchestrator for NIGHTWATCH observatory.

    Coordinates all services, manages session state, and provides
    the main interface for voice commands and automation.
    """

    def __init__(self, config: NightwatchConfig):
        """
        Initialize orchestrator with configuration.

        Args:
            config: NIGHTWATCH configuration object
        """
        self.config = config
        self.registry = ServiceRegistry()
        self.session = SessionState()
        self._running = False
        self._health_task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable] = []

        logger.info("Orchestrator initialized")

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def is_running(self) -> bool:
        """Check if orchestrator is running."""
        return self._running

    @property
    def mount(self) -> Optional[MountServiceProtocol]:
        """Get mount service."""
        return self.registry.get("mount")

    @property
    def catalog(self) -> Optional[CatalogServiceProtocol]:
        """Get catalog service."""
        return self.registry.get("catalog")

    @property
    def ephemeris(self) -> Optional[EphemerisServiceProtocol]:
        """Get ephemeris service."""
        return self.registry.get("ephemeris")

    @property
    def weather(self) -> Optional[WeatherServiceProtocol]:
        """Get weather service."""
        return self.registry.get("weather")

    @property
    def safety(self) -> Optional[SafetyServiceProtocol]:
        """Get safety monitor service."""
        return self.registry.get("safety")

    @property
    def camera(self) -> Optional[CameraServiceProtocol]:
        """Get camera service."""
        return self.registry.get("camera")

    @property
    def guiding(self) -> Optional[GuidingServiceProtocol]:
        """Get guiding service."""
        return self.registry.get("guiding")

    @property
    def focus(self) -> Optional[FocusServiceProtocol]:
        """Get focus service."""
        return self.registry.get("focus")

    @property
    def astrometry(self) -> Optional[AstrometryServiceProtocol]:
        """Get astrometry service."""
        return self.registry.get("astrometry")

    @property
    def alerts(self) -> Optional[AlertServiceProtocol]:
        """Get alert service."""
        return self.registry.get("alerts")

    @property
    def power(self) -> Optional[PowerServiceProtocol]:
        """Get power service."""
        return self.registry.get("power")

    @property
    def enclosure(self) -> Optional[EnclosureServiceProtocol]:
        """Get enclosure service."""
        return self.registry.get("enclosure")

    # =========================================================================
    # Service Registration (Steps 215-226)
    # =========================================================================

    def register_mount(self, service: MountServiceProtocol, required: bool = True):
        """Register mount control service (Step 215)."""
        self.registry.register("mount", service, required)

    def register_catalog(self, service: CatalogServiceProtocol, required: bool = False):
        """Register catalog lookup service (Step 216)."""
        self.registry.register("catalog", service, required)

    def register_ephemeris(self, service: EphemerisServiceProtocol, required: bool = False):
        """Register ephemeris service (Step 217)."""
        self.registry.register("ephemeris", service, required)

    def register_weather(self, service: WeatherServiceProtocol, required: bool = True):
        """Register weather monitoring service (Step 218)."""
        self.registry.register("weather", service, required)

    def register_safety(self, service: SafetyServiceProtocol, required: bool = True):
        """Register safety monitor service (Step 219)."""
        self.registry.register("safety", service, required)

    def register_camera(self, service: CameraServiceProtocol, required: bool = False):
        """Register camera service (Step 220)."""
        self.registry.register("camera", service, required)

    def register_guiding(self, service: GuidingServiceProtocol, required: bool = False):
        """Register guiding service (Step 221)."""
        self.registry.register("guiding", service, required)

    def register_focus(self, service: FocusServiceProtocol, required: bool = False):
        """Register focus service (Step 222)."""
        self.registry.register("focus", service, required)

    def register_astrometry(self, service: AstrometryServiceProtocol, required: bool = False):
        """Register astrometry service (Step 223)."""
        self.registry.register("astrometry", service, required)

    def register_alerts(self, service: AlertServiceProtocol, required: bool = False):
        """Register alert notification service (Step 224)."""
        self.registry.register("alerts", service, required)

    def register_power(self, service: PowerServiceProtocol, required: bool = False):
        """Register power management service (Step 225)."""
        self.registry.register("power", service, required)

    def register_enclosure(self, service: EnclosureServiceProtocol, required: bool = False):
        """Register enclosure/roof service (Step 226)."""
        self.registry.register("enclosure", service, required)

    # =========================================================================
    # Lifecycle Management
    # =========================================================================

    async def start(self) -> bool:
        """
        Start the orchestrator and all registered services.

        Returns:
            True if started successfully
        """
        if self._running:
            logger.warning("Orchestrator already running")
            return True

        logger.info("Starting orchestrator...")

        # Check required services
        required = self.registry.get_required_services()
        if not required:
            logger.warning("No required services registered")

        # Start all services
        for name in self.registry.list_services():
            service = self.registry.get(name)
            if service and hasattr(service, 'start'):
                try:
                    self.registry.set_status(name, ServiceStatus.STARTING)
                    await service.start()
                    self.registry.set_status(name, ServiceStatus.RUNNING)
                    logger.info(f"Service started: {name}")
                except Exception as e:
                    self.registry.set_status(name, ServiceStatus.ERROR, str(e))
                    logger.error(f"Failed to start service {name}: {e}")
                    if self.registry.get_status(name) == ServiceStatus.ERROR:
                        info = self.registry._services.get(name)
                        if info and info.required:
                            logger.error(f"Required service {name} failed to start")
                            return False

        # Start health monitoring
        self._health_task = asyncio.create_task(self._health_loop())

        self._running = True
        self.session = SessionState()
        logger.info("Orchestrator started")
        return True

    async def shutdown(self):
        """Shutdown the orchestrator and all services."""
        if not self._running:
            return

        logger.info("Shutting down orchestrator...")

        # Cancel health monitoring
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass

        # Stop all services in reverse order
        for name in reversed(self.registry.list_services()):
            service = self.registry.get(name)
            if service and hasattr(service, 'stop'):
                try:
                    await service.stop()
                    self.registry.set_status(name, ServiceStatus.STOPPED)
                    logger.info(f"Service stopped: {name}")
                except Exception as e:
                    logger.error(f"Error stopping service {name}: {e}")

        self._running = False
        logger.info("Orchestrator shutdown complete")

    async def _health_loop(self):
        """Background health monitoring loop."""
        while self._running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                for name in self.registry.list_services():
                    service = self.registry.get(name)
                    if service and hasattr(service, 'is_running'):
                        try:
                            if service.is_running:
                                self.registry.set_status(name, ServiceStatus.RUNNING)
                            else:
                                self.registry.set_status(name, ServiceStatus.STOPPED)
                        except Exception as e:
                            self.registry.set_status(name, ServiceStatus.ERROR, str(e))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    # =========================================================================
    # Session Management (Step 231)
    # =========================================================================

    async def start_session(self, session_id: Optional[str] = None) -> bool:
        """
        Start a new observing session.

        Args:
            session_id: Optional session identifier

        Returns:
            True if session started successfully
        """
        if not self._running:
            raise NightwatchError("Orchestrator not running")

        # Generate session ID if not provided
        if not session_id:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.session = SessionState(
            session_id=session_id,
            started_at=datetime.now(),
            is_observing=True,
        )

        logger.info(f"Observing session started: {session_id}")
        return True

    async def end_session(self):
        """End the current observing session."""
        if self.session.is_observing:
            self.session.is_observing = False
            logger.info(f"Observing session ended: {self.session.session_id}")
            logger.info(f"  Images captured: {self.session.images_captured}")
            logger.info(f"  Total exposure: {self.session.total_exposure_sec:.1f}s")

    # =========================================================================
    # Status and Information
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get overall orchestrator status."""
        return {
            "running": self._running,
            "session": {
                "id": self.session.session_id,
                "started": self.session.started_at.isoformat() if self.session.started_at else None,
                "is_observing": self.session.is_observing,
                "current_target": self.session.current_target.name if self.session.current_target else None,
                "images_captured": self.session.images_captured,
            },
            "services": {
                name: info.status.value
                for name, info in self.registry.get_all_info().items()
            },
        }

    def get_service_status(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed status for all services."""
        result = {}
        for name, info in self.registry.get_all_info().items():
            result[name] = {
                "status": info.status.value,
                "required": info.required,
                "last_error": info.last_error,
                "last_check": info.last_check.isoformat() if info.last_check else None,
            }
        return result

    # =========================================================================
    # Event Callbacks
    # =========================================================================

    def register_callback(self, callback: Callable):
        """Register callback for orchestrator events."""
        self._callbacks.append(callback)

    async def _notify_callbacks(self, event: str, data: Any = None):
        """Notify registered callbacks."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event, data)
                else:
                    callback(event, data)
            except Exception as e:
                logger.error(f"Callback error: {e}")


# =============================================================================
# Factory Function
# =============================================================================


def create_orchestrator(config_path: Optional[str] = None) -> Orchestrator:
    """
    Create an orchestrator instance with configuration.

    Args:
        config_path: Optional path to config file

    Returns:
        Configured Orchestrator instance
    """
    from nightwatch.config import load_config

    config = load_config(config_path)
    return Orchestrator(config)
