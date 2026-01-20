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
    "ObservationLogEntry",
    "EventType",
    "OrchestratorEvent",
    "OrchestratorMetrics",
    "CommandPriority",
]


# =============================================================================
# Command Priority System (Step 235)
# =============================================================================


class CommandPriority(Enum):
    """
    Command priority levels (Step 235).

    Higher priority commands are processed first and can interrupt
    lower priority commands in progress.

    Priority order (highest to lowest):
    1. EMERGENCY - Safety-critical commands (park, close, stop)
    2. SAFETY - Safety-related commands (weather alerts)
    3. HIGH - User-initiated immediate commands
    4. NORMAL - Standard commands (slew, capture)
    5. LOW - Background tasks (calibration, status)
    6. BACKGROUND - Deferred tasks (cleanup, logging)
    """
    EMERGENCY = 100  # Highest - immediate execution, interrupts all
    SAFETY = 80      # Safety-related commands
    HIGH = 60        # User-initiated urgent commands
    NORMAL = 40      # Standard user commands
    LOW = 20         # Non-urgent commands
    BACKGROUND = 0   # Lowest - background tasks

    @classmethod
    def from_command(cls, command: str) -> "CommandPriority":
        """
        Determine priority from command string.

        Args:
            command: The command string

        Returns:
            Appropriate CommandPriority level
        """
        command_lower = command.lower()

        # Emergency commands
        if any(kw in command_lower for kw in [
            "emergency", "stop", "abort", "halt"
        ]):
            return cls.EMERGENCY

        # Safety commands
        if any(kw in command_lower for kw in [
            "park", "close roof", "unsafe", "weather alert"
        ]):
            return cls.SAFETY

        # High priority commands
        if any(kw in command_lower for kw in [
            "slew", "goto", "move", "track"
        ]):
            return cls.HIGH

        # Normal commands
        if any(kw in command_lower for kw in [
            "capture", "expose", "focus", "guide"
        ]):
            return cls.NORMAL

        # Low priority
        if any(kw in command_lower for kw in [
            "status", "what", "where", "report"
        ]):
            return cls.LOW

        # Default to normal
        return cls.NORMAL


# =============================================================================
# Event System (Steps 243-246)
# =============================================================================


class EventType(Enum):
    """Types of orchestrator events."""
    # Mount events (Step 243)
    MOUNT_POSITION_CHANGED = "mount_position_changed"
    MOUNT_SLEW_STARTED = "mount_slew_started"
    MOUNT_SLEW_COMPLETE = "mount_slew_complete"
    MOUNT_PARKED = "mount_parked"
    MOUNT_UNPARKED = "mount_unparked"

    # Weather events (Step 244)
    WEATHER_CHANGED = "weather_changed"
    WEATHER_SAFE = "weather_safe"
    WEATHER_UNSAFE = "weather_unsafe"

    # Safety events (Step 245)
    SAFETY_STATE_CHANGED = "safety_state_changed"
    SAFETY_ALERT = "safety_alert"
    SAFETY_VETO = "safety_veto"

    # Guiding events (Step 246)
    GUIDING_STATE_CHANGED = "guiding_state_changed"
    GUIDING_STARTED = "guiding_started"
    GUIDING_STOPPED = "guiding_stopped"
    GUIDING_LOST = "guiding_lost"
    GUIDING_SETTLED = "guiding_settled"
    GUIDING_DITHER = "guiding_dither"

    # Session events
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    IMAGE_CAPTURED = "image_captured"

    # System events
    SERVICE_STARTED = "service_started"
    SERVICE_STOPPED = "service_stopped"
    SERVICE_ERROR = "service_error"
    SHUTDOWN_INITIATED = "shutdown_initiated"


@dataclass
class OrchestratorEvent:
    """Event emitted by the orchestrator."""
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


# =============================================================================
# Metrics (Steps 247-250)
# =============================================================================


@dataclass
class OrchestratorMetrics:
    """
    Orchestrator performance metrics.

    Tracks command latency, service uptime, and error rates.
    """
    # Timing metrics (Step 248)
    commands_executed: int = 0
    total_command_time_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0

    # Service metrics (Step 249)
    service_start_time: Dict[str, datetime] = field(default_factory=dict)

    # Error metrics (Step 250)
    error_count: int = 0
    errors_by_service: Dict[str, int] = field(default_factory=dict)

    @property
    def avg_latency_ms(self) -> float:
        """Average command latency in milliseconds."""
        if self.commands_executed == 0:
            return 0.0
        return self.total_command_time_ms / self.commands_executed

    def record_command(self, latency_ms: float):
        """Record a command execution."""
        self.commands_executed += 1
        self.total_command_time_ms += latency_ms
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)

    def record_error(self, service: str):
        """Record a service error."""
        self.error_count += 1
        self.errors_by_service[service] = self.errors_by_service.get(service, 0) + 1

    def get_service_uptime(self, service: str) -> float:
        """Get service uptime in seconds."""
        start = self.service_start_time.get(service)
        if start:
            return (datetime.now() - start).total_seconds()
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "commands_executed": self.commands_executed,
            "avg_latency_ms": self.avg_latency_ms,
            "min_latency_ms": self.min_latency_ms if self.min_latency_ms != float('inf') else 0,
            "max_latency_ms": self.max_latency_ms,
            "error_count": self.error_count,
            "errors_by_service": self.errors_by_service.copy(),
        }


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
class ObservationLogEntry:
    """Single entry in the observation log (Step 233)."""
    timestamp: datetime
    event_type: str  # "target_acquired", "image_captured", "slew", "focus", "error", etc.
    message: str
    data: Dict[str, Any] = field(default_factory=dict)


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

    # Observation log (Step 233)
    observation_log: List[ObservationLogEntry] = field(default_factory=list)
    targets_observed: List[str] = field(default_factory=list)


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

        # Metrics tracking (Steps 248-250)
        self.metrics = OrchestratorMetrics()

        # Event system (Steps 243-246)
        self._event_listeners: Dict[EventType, List[Callable]] = {}

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

    async def shutdown(self, safe: bool = True):
        """
        Shutdown the orchestrator and all services.

        Args:
            safe: If True, perform safe shutdown (park mount, close enclosure)
        """
        if not self._running:
            return

        logger.info("Shutting down orchestrator...")

        # Emit shutdown event
        await self.emit_event(
            EventType.SHUTDOWN_INITIATED,
            source="orchestrator",
            message="Shutdown initiated"
        )

        # Cancel health monitoring
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass

        # Safe shutdown steps (Steps 252-254)
        if safe:
            await self._safe_shutdown()

        # Stop all services in reverse order
        for name in reversed(self.registry.list_services()):
            service = self.registry.get(name)
            if service and hasattr(service, 'stop'):
                try:
                    await service.stop()
                    self.registry.set_status(name, ServiceStatus.STOPPED)
                    await self.emit_event(
                        EventType.SERVICE_STOPPED,
                        source=name,
                        message=f"Service {name} stopped"
                    )
                    logger.info(f"Service stopped: {name}")
                except Exception as e:
                    logger.error(f"Error stopping service {name}: {e}")

        self._running = False
        logger.info("Orchestrator shutdown complete")

    async def _safe_shutdown(self):
        """
        Perform safe shutdown sequence (Steps 252-254).

        - Step 252: Park the telescope mount
        - Step 253: Close the enclosure/roof
        - Step 254: Save session log
        """
        logger.info("Performing safe shutdown sequence...")

        # Step 252: Park the telescope mount
        if self.mount:
            try:
                if hasattr(self.mount, 'is_parked') and not self.mount.is_parked:
                    logger.info("Parking telescope mount...")
                    await self.mount.park()
                    await self.emit_event(
                        EventType.MOUNT_PARKED,
                        source="mount",
                        message="Mount parked during safe shutdown"
                    )
                    logger.info("Mount parked successfully")
            except Exception as e:
                logger.error(f"Failed to park mount during shutdown: {e}")
                self.record_service_error("mount")

        # Step 253: Close the enclosure/roof
        if self.enclosure:
            try:
                if hasattr(self.enclosure, 'close'):
                    logger.info("Closing enclosure...")
                    await self.enclosure.close()
                    logger.info("Enclosure closed successfully")
            except Exception as e:
                logger.error(f"Failed to close enclosure during shutdown: {e}")
                self.record_service_error("enclosure")

        # Step 254: Save session log
        if self.session.is_observing:
            await self._save_session_log()
            await self.end_session()

    async def _save_session_log(self):
        """
        Save session log to file (Step 254).

        Records session summary including targets observed,
        images captured, and any errors.
        """
        import json
        from pathlib import Path

        log_dir = Path(self.config.data_dir if hasattr(self.config, 'data_dir') else "logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"session_{self.session.session_id}.json"

        session_log = {
            "session_id": self.session.session_id,
            "started_at": self.session.started_at.isoformat() if self.session.started_at else None,
            "ended_at": datetime.now().isoformat(),
            "images_captured": self.session.images_captured,
            "total_exposure_sec": self.session.total_exposure_sec,
            "current_target": self.session.current_target.name if self.session.current_target else None,
            "error_count": self.session.error_count,
            "last_error": self.session.last_error,
            "metrics": self.metrics.to_dict(),
        }

        try:
            with open(log_file, "w") as f:
                json.dump(session_log, f, indent=2)
            logger.info(f"Session log saved to {log_file}")
        except Exception as e:
            logger.error(f"Failed to save session log: {e}")

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

    async def end_session(self, park: bool = True, close: bool = True) -> bool:
        """
        End the current observing session (Step 232).

        Performs safe shutdown of observing equipment:
        - Stop any active guiding
        - Park the telescope mount
        - Close the enclosure/roof
        - Save session log

        Args:
            park: Whether to park the mount (default True)
            close: Whether to close the enclosure (default True)

        Returns:
            True if session ended successfully
        """
        if not self.session.is_observing:
            logger.info("No active session to end")
            return True

        logger.info(f"Ending observing session: {self.session.session_id}")
        success = True

        # Stop guiding if active
        if self.guiding:
            try:
                if hasattr(self.guiding, 'is_guiding') and self.guiding.is_guiding:
                    logger.info("Stopping autoguiding...")
                    await self.guiding.stop_guiding()
            except Exception as e:
                logger.error(f"Error stopping guiding: {e}")
                success = False

        # Park the mount (Step 232)
        if park and self.mount:
            try:
                if hasattr(self.mount, 'is_parked') and not self.mount.is_parked:
                    logger.info("Parking telescope mount...")
                    await self.mount.park()
                    await self.emit_event(
                        EventType.MOUNT_PARKED,
                        source="mount",
                        message="Mount parked at end of session"
                    )
                    logger.info("Mount parked successfully")
            except Exception as e:
                logger.error(f"Failed to park mount: {e}")
                self.record_service_error("mount")
                success = False

        # Close enclosure (Step 232)
        if close and self.enclosure:
            try:
                if hasattr(self.enclosure, 'is_open') and self.enclosure.is_open:
                    logger.info("Closing enclosure...")
                    await self.enclosure.close()
                    logger.info("Enclosure closed successfully")
            except Exception as e:
                logger.error(f"Failed to close enclosure: {e}")
                self.record_service_error("enclosure")
                success = False

        # Save session log
        await self._save_session_log()

        # Update session state
        self.session.is_observing = False
        self.session.is_imaging = False

        # Emit session ended event
        await self.emit_event(
            EventType.SESSION_ENDED,
            source="orchestrator",
            data={
                "session_id": self.session.session_id,
                "images_captured": self.session.images_captured,
                "total_exposure_sec": self.session.total_exposure_sec,
            },
            message=f"Session {self.session.session_id} ended"
        )

        logger.info(f"Observing session ended: {self.session.session_id}")
        logger.info(f"  Images captured: {self.session.images_captured}")
        logger.info(f"  Total exposure: {self.session.total_exposure_sec:.1f}s")

        return success

    # =========================================================================
    # Observation Log Recording (Step 233)
    # =========================================================================

    def log_observation(
        self,
        event_type: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record an entry in the observation log (Step 233).

        Args:
            event_type: Type of event (target_acquired, image_captured, slew, etc.)
            message: Human-readable description
            data: Additional event data
        """
        entry = ObservationLogEntry(
            timestamp=datetime.now(),
            event_type=event_type,
            message=message,
            data=data or {},
        )
        self.session.observation_log.append(entry)
        logger.debug(f"Observation log: [{event_type}] {message}")

    def log_target_acquired(self, target_name: str, ra: float, dec: float) -> None:
        """Log target acquisition (Step 233)."""
        self.log_observation(
            event_type="target_acquired",
            message=f"Acquired target: {target_name}",
            data={"target": target_name, "ra": ra, "dec": dec}
        )
        if target_name not in self.session.targets_observed:
            self.session.targets_observed.append(target_name)

    def log_image_captured(
        self,
        filename: str,
        exposure_sec: float,
        filter_name: Optional[str] = None
    ) -> None:
        """Log image capture (Step 233)."""
        self.session.images_captured += 1
        self.session.total_exposure_sec += exposure_sec
        self.log_observation(
            event_type="image_captured",
            message=f"Captured {exposure_sec}s exposure: {filename}",
            data={
                "filename": filename,
                "exposure_sec": exposure_sec,
                "filter": filter_name,
                "image_number": self.session.images_captured,
            }
        )

    def log_slew(self, target: str, ra: float, dec: float) -> None:
        """Log telescope slew (Step 233)."""
        self.log_observation(
            event_type="slew",
            message=f"Slewing to {target}",
            data={"target": target, "ra": ra, "dec": dec}
        )

    def log_focus_run(self, position: int, hfd: Optional[float] = None) -> None:
        """Log autofocus run (Step 233)."""
        self.log_observation(
            event_type="focus",
            message=f"Autofocus complete at position {position}",
            data={"position": position, "hfd": hfd}
        )

    def log_error(self, error_message: str, error_type: str = "error") -> None:
        """Log an error (Step 233)."""
        self.session.error_count += 1
        self.session.last_error = error_message
        self.log_observation(
            event_type=error_type,
            message=error_message,
            data={"error_count": self.session.error_count}
        )

    def get_observation_log(self) -> List[Dict[str, Any]]:
        """
        Get the observation log as a list of dicts (Step 233).

        Returns:
            List of observation log entries
        """
        return [
            {
                "timestamp": entry.timestamp.isoformat(),
                "event_type": entry.event_type,
                "message": entry.message,
                "data": entry.data,
            }
            for entry in self.session.observation_log
        ]

    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current session (Step 233).

        Returns:
            Dict with session summary
        """
        duration = None
        if self.session.started_at:
            duration = (datetime.now() - self.session.started_at).total_seconds()

        return {
            "session_id": self.session.session_id,
            "started_at": self.session.started_at.isoformat() if self.session.started_at else None,
            "duration_sec": duration,
            "is_observing": self.session.is_observing,
            "targets_observed": self.session.targets_observed,
            "images_captured": self.session.images_captured,
            "total_exposure_sec": self.session.total_exposure_sec,
            "current_target": self.session.current_target.name if self.session.current_target else None,
            "error_count": self.session.error_count,
            "log_entry_count": len(self.session.observation_log),
        }

    # =========================================================================
    # Command Cancellation (Step 237)
    # =========================================================================

    def __init_command_tracking(self):
        """Initialize command tracking for cancellation support."""
        if not hasattr(self, '_active_commands'):
            self._active_commands: Dict[str, asyncio.Task] = {}
            self._command_counter = 0

    def _get_next_command_id(self) -> str:
        """Generate unique command ID."""
        self.__init_command_tracking()
        self._command_counter += 1
        return f"cmd_{self._command_counter:06d}"

    async def execute_cancellable(
        self,
        coro,
        command_id: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        """
        Execute a coroutine with cancellation support (Step 237).

        Args:
            coro: Coroutine to execute
            command_id: Optional command identifier (auto-generated if not provided)
            timeout: Optional timeout in seconds

        Returns:
            Result of the coroutine

        Raises:
            asyncio.CancelledError: If command was cancelled
            asyncio.TimeoutError: If command timed out
        """
        self.__init_command_tracking()

        if command_id is None:
            command_id = self._get_next_command_id()

        # Create task
        task = asyncio.create_task(coro)
        self._active_commands[command_id] = task

        try:
            if timeout:
                result = await asyncio.wait_for(task, timeout=timeout)
            else:
                result = await task
            return result
        except asyncio.CancelledError:
            logger.info(f"Command {command_id} was cancelled")
            raise
        except asyncio.TimeoutError:
            logger.warning(f"Command {command_id} timed out after {timeout}s")
            raise
        finally:
            # Clean up tracking
            self._active_commands.pop(command_id, None)

    async def cancel_command(self, command_id: str) -> bool:
        """
        Cancel an active command (Step 237).

        Args:
            command_id: ID of the command to cancel

        Returns:
            True if command was cancelled, False if not found
        """
        self.__init_command_tracking()

        task = self._active_commands.get(command_id)
        if task is None:
            logger.warning(f"Command {command_id} not found or already completed")
            return False

        if task.done():
            logger.info(f"Command {command_id} already completed")
            return False

        logger.info(f"Cancelling command {command_id}...")
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        return True

    async def cancel_all_commands(self) -> int:
        """
        Cancel all active commands (Step 237).

        Returns:
            Number of commands cancelled
        """
        self.__init_command_tracking()

        cancelled = 0
        for command_id in list(self._active_commands.keys()):
            if await self.cancel_command(command_id):
                cancelled += 1

        logger.info(f"Cancelled {cancelled} active commands")
        return cancelled

    def get_active_commands(self) -> List[str]:
        """
        Get list of active command IDs (Step 237).

        Returns:
            List of active command identifiers
        """
        self.__init_command_tracking()
        return [
            cmd_id for cmd_id, task in self._active_commands.items()
            if not task.done()
        ]

    # =========================================================================
    # Command Timeout Handling (Step 236)
    # =========================================================================

    # Default timeouts for different command types
    DEFAULT_TIMEOUTS = {
        "slew": 120.0,      # 2 minutes for slew
        "capture": 600.0,   # 10 minutes for long exposures
        "focus": 180.0,     # 3 minutes for autofocus
        "park": 60.0,       # 1 minute for park
        "calibrate": 300.0, # 5 minutes for calibration
        "dither": 60.0,     # 1 minute for dither
        "default": 30.0,    # 30 seconds default
    }

    def get_command_timeout(self, command_type: str) -> float:
        """
        Get the timeout for a specific command type (Step 236).

        Args:
            command_type: Type of command (slew, capture, focus, etc.)

        Returns:
            Timeout in seconds
        """
        return self.DEFAULT_TIMEOUTS.get(command_type, self.DEFAULT_TIMEOUTS["default"])

    def set_command_timeout(self, command_type: str, timeout_sec: float) -> None:
        """
        Set a custom timeout for a command type (Step 236).

        Args:
            command_type: Type of command
            timeout_sec: Timeout in seconds
        """
        self.DEFAULT_TIMEOUTS[command_type] = timeout_sec
        logger.info(f"Set timeout for '{command_type}' to {timeout_sec}s")

    async def execute_with_timeout(
        self,
        coro,
        command_type: str = "default",
        custom_timeout: Optional[float] = None,
        on_timeout: Optional[Callable] = None,
    ):
        """
        Execute a coroutine with automatic timeout handling (Step 236).

        Args:
            coro: Coroutine to execute
            command_type: Type of command for timeout lookup
            custom_timeout: Override default timeout
            on_timeout: Optional callback to execute on timeout

        Returns:
            Result of the coroutine

        Raises:
            asyncio.TimeoutError: If command times out
        """
        timeout = custom_timeout or self.get_command_timeout(command_type)
        start_time = datetime.now()

        try:
            result = await asyncio.wait_for(coro, timeout=timeout)
            return result

        except asyncio.TimeoutError:
            elapsed = (datetime.now() - start_time).total_seconds()
            error_msg = f"Command '{command_type}' timed out after {elapsed:.1f}s (limit: {timeout}s)"
            logger.warning(error_msg)

            # Log the timeout
            self.log_error(error_msg, error_type="timeout")
            self.record_service_error("timeout")

            # Execute timeout callback if provided
            if on_timeout:
                try:
                    if asyncio.iscoroutinefunction(on_timeout):
                        await on_timeout()
                    else:
                        on_timeout()
                except Exception as e:
                    logger.error(f"Timeout callback error: {e}")

            raise

    async def execute_slew_with_timeout(
        self,
        slew_coro,
        target_name: str = "unknown"
    ):
        """
        Execute a slew operation with proper timeout (Step 236).

        Args:
            slew_coro: Slew coroutine
            target_name: Name of target for logging

        Returns:
            Result of slew operation
        """
        async def on_slew_timeout():
            logger.warning(f"Slew to {target_name} timed out - stopping mount")
            if self.mount and hasattr(self.mount, 'abort_slew'):
                try:
                    await self.mount.abort_slew()
                except Exception as e:
                    logger.error(f"Failed to abort slew: {e}")

        return await self.execute_with_timeout(
            slew_coro,
            command_type="slew",
            on_timeout=on_slew_timeout,
        )

    async def execute_capture_with_timeout(
        self,
        capture_coro,
        exposure_sec: float
    ):
        """
        Execute a capture operation with appropriate timeout (Step 236).

        Args:
            capture_coro: Capture coroutine
            exposure_sec: Exposure duration in seconds

        Returns:
            Result of capture operation
        """
        # Timeout should be at least 2x exposure + 30s for download
        timeout = max(exposure_sec * 2 + 30, self.get_command_timeout("capture"))

        async def on_capture_timeout():
            logger.warning("Capture timed out - aborting exposure")
            if self.camera and hasattr(self.camera, 'abort_exposure'):
                try:
                    await self.camera.abort_exposure()
                except Exception as e:
                    logger.error(f"Failed to abort exposure: {e}")

        return await self.execute_with_timeout(
            capture_coro,
            command_type="capture",
            custom_timeout=timeout,
            on_timeout=on_capture_timeout,
        )

    # =========================================================================
    # Graceful Shutdown (Step 251)
    # =========================================================================

    async def graceful_shutdown(self, timeout: float = 30.0) -> bool:
        """
        Perform graceful shutdown sequence (Step 251).

        This method ensures all operations complete safely:
        1. Cancel all non-essential commands
        2. Wait for essential operations to complete
        3. End the observing session (park, close)
        4. Stop all services
        5. Save state

        Args:
            timeout: Maximum time to wait for operations to complete

        Returns:
            True if shutdown completed successfully
        """
        logger.info("Initiating graceful shutdown sequence...")

        success = True

        # Step 1: Cancel non-essential commands
        try:
            cancelled = await self.cancel_all_commands()
            if cancelled > 0:
                logger.info(f"Cancelled {cancelled} active commands")
        except Exception as e:
            logger.error(f"Error cancelling commands: {e}")

        # Step 2: End observing session (includes park and close)
        try:
            if self.session.is_observing:
                logger.info("Ending observing session...")
                session_success = await asyncio.wait_for(
                    self.end_session(park=True, close=True),
                    timeout=timeout
                )
                if not session_success:
                    success = False
        except asyncio.TimeoutError:
            logger.error(f"Session end timed out after {timeout}s")
            success = False
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            success = False

        # Step 3: Emit shutdown event
        await self.emit_event(
            EventType.SHUTDOWN_INITIATED,
            source="orchestrator",
            data={"graceful": True},
            message="Graceful shutdown initiated"
        )

        # Step 4: Send alert if alerts service is available
        if self.alerts:
            try:
                await self.alerts.send_alert(
                    level="info",
                    message="NIGHTWATCH graceful shutdown completed"
                )
            except Exception as e:
                logger.warning(f"Could not send shutdown alert: {e}")

        # Step 5: Full shutdown
        await self.shutdown(safe=False)  # Safe ops already done above

        logger.info("Graceful shutdown sequence complete")
        return success

    async def emergency_shutdown(self) -> bool:
        """
        Perform emergency shutdown (Step 251).

        Immediately stops all operations and safely parks/closes
        without waiting for commands to complete.

        Returns:
            True if emergency shutdown completed
        """
        logger.warning("EMERGENCY SHUTDOWN INITIATED")

        # Immediately cancel all commands
        try:
            for cmd_id, task in list(getattr(self, '_active_commands', {}).items()):
                task.cancel()
        except Exception as e:
            logger.error(f"Error cancelling commands: {e}")

        # Stop guiding immediately
        if self.guiding:
            try:
                await self.guiding.stop_guiding()
            except Exception:
                pass

        # Park mount (critical safety)
        if self.mount:
            try:
                await self.mount.park()
                logger.info("Mount parked (emergency)")
            except Exception as e:
                logger.error(f"EMERGENCY: Failed to park mount: {e}")

        # Close enclosure (critical safety)
        if self.enclosure:
            try:
                await self.enclosure.close()
                logger.info("Enclosure closed (emergency)")
            except Exception as e:
                logger.error(f"EMERGENCY: Failed to close enclosure: {e}")

        # Send emergency alert
        if self.alerts:
            try:
                await self.alerts.send_alert(
                    level="critical",
                    message="NIGHTWATCH EMERGENCY SHUTDOWN"
                )
            except Exception:
                pass

        self._running = False
        logger.warning("Emergency shutdown complete")
        return True

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
    # Event Callbacks (legacy)
    # =========================================================================

    def register_callback(self, callback: Callable):
        """Register callback for orchestrator events (legacy)."""
        self._callbacks.append(callback)

    async def _notify_callbacks(self, event: str, data: Any = None):
        """Notify registered callbacks (legacy)."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event, data)
                else:
                    callback(event, data)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    # =========================================================================
    # Event System (Steps 243-246)
    # =========================================================================

    def subscribe(self, event_type: EventType, listener: Callable[[OrchestratorEvent], None]):
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to listen for
            listener: Callback function to invoke when event occurs
        """
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        self._event_listeners[event_type].append(listener)
        logger.debug(f"Subscribed listener to {event_type.value}")

    def unsubscribe(self, event_type: EventType, listener: Callable[[OrchestratorEvent], None]):
        """
        Unsubscribe from an event type.

        Args:
            event_type: Type of event to unsubscribe from
            listener: Callback function to remove
        """
        if event_type in self._event_listeners:
            try:
                self._event_listeners[event_type].remove(listener)
            except ValueError:
                pass

    async def emit_event(
        self,
        event_type: EventType,
        source: str = "",
        data: Optional[Dict[str, Any]] = None,
        message: str = ""
    ):
        """
        Emit an event to all subscribed listeners.

        Args:
            event_type: Type of event to emit
            source: Source of the event (e.g., service name)
            data: Event data
            message: Human-readable message
        """
        event = OrchestratorEvent(
            event_type=event_type,
            source=source,
            data=data or {},
            message=message,
        )

        listeners = self._event_listeners.get(event_type, [])
        for listener in listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event)
                else:
                    listener(event)
            except Exception as e:
                logger.error(f"Event listener error for {event_type.value}: {e}")

        # Also notify legacy callbacks
        await self._notify_callbacks(event_type.value, event)

    # =========================================================================
    # Metrics (Steps 248-250)
    # =========================================================================

    def get_metrics(self) -> Dict[str, Any]:
        """Get current orchestrator metrics."""
        return self.metrics.to_dict()

    async def record_command_execution(self, latency_ms: float):
        """
        Record a command execution for metrics.

        Args:
            latency_ms: Command execution time in milliseconds
        """
        self.metrics.record_command(latency_ms)

    def record_service_error(self, service: str):
        """
        Record a service error for metrics.

        Args:
            service: Name of the service that had an error
        """
        self.metrics.record_error(service)


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
