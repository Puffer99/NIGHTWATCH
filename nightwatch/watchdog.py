"""
NIGHTWATCH Watchdog Module.

Monitors service health and communication timeouts to detect failures
and trigger appropriate recovery actions for autonomous operation.

Key Features:
- Service heartbeat monitoring with configurable intervals
- Per-service communication timeout detection
- Automatic restart with attempt limits
- Safe state transition on persistent failure
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Callable, Any

logger = logging.getLogger("NIGHTWATCH.Watchdog")


class ServiceState(Enum):
    """Service health states."""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    RESTARTING = "restarting"
    STOPPED = "stopped"


class ServiceType(Enum):
    """Types of monitored services."""
    MOUNT = "mount"
    WEATHER = "weather"
    CAMERA = "camera"
    GUIDER = "guider"
    FOCUSER = "focuser"
    ENCLOSURE = "enclosure"
    POWER = "power"
    LLM = "llm"
    STT = "stt"
    TTS = "tts"


@dataclass
class ServiceConfig:
    """Configuration for a monitored service."""
    service_type: ServiceType
    name: str
    heartbeat_interval_sec: float = 30.0
    timeout_sec: float = 60.0
    max_restart_attempts: int = 3
    restart_cooldown_sec: float = 60.0
    critical: bool = False  # If true, failure triggers safe state

    def __post_init__(self):
        """Validate configuration."""
        if self.timeout_sec < self.heartbeat_interval_sec:
            self.timeout_sec = self.heartbeat_interval_sec * 2


@dataclass
class ServiceStatus:
    """Current status of a monitored service."""
    service_type: ServiceType
    name: str
    state: ServiceState = ServiceState.UNKNOWN
    last_heartbeat: Optional[datetime] = None
    last_error: Optional[str] = None
    restart_count: int = 0
    last_restart: Optional[datetime] = None
    consecutive_failures: int = 0

    @property
    def is_healthy(self) -> bool:
        """Check if service is healthy."""
        return self.state == ServiceState.HEALTHY

    @property
    def is_failed(self) -> bool:
        """Check if service has failed."""
        return self.state == ServiceState.FAILED

    @property
    def seconds_since_heartbeat(self) -> Optional[float]:
        """Get seconds since last heartbeat."""
        if self.last_heartbeat is None:
            return None
        return (datetime.now() - self.last_heartbeat).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "service_type": self.service_type.value,
            "name": self.name,
            "state": self.state.value,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "last_error": self.last_error,
            "restart_count": self.restart_count,
            "consecutive_failures": self.consecutive_failures,
        }


# =============================================================================
# Default Service Configurations
# =============================================================================

DEFAULT_CONFIGS = {
    ServiceType.MOUNT: ServiceConfig(
        service_type=ServiceType.MOUNT,
        name="Mount Controller",
        heartbeat_interval_sec=10.0,
        timeout_sec=30.0,
        max_restart_attempts=3,
        critical=True,  # Mount failure is critical
    ),
    ServiceType.WEATHER: ServiceConfig(
        service_type=ServiceType.WEATHER,
        name="Weather Service",
        heartbeat_interval_sec=60.0,
        timeout_sec=120.0,
        max_restart_attempts=5,
        critical=True,  # Weather data is safety-critical
    ),
    ServiceType.CAMERA: ServiceConfig(
        service_type=ServiceType.CAMERA,
        name="Camera Controller",
        heartbeat_interval_sec=30.0,
        timeout_sec=90.0,
        max_restart_attempts=3,
        critical=False,
    ),
    ServiceType.GUIDER: ServiceConfig(
        service_type=ServiceType.GUIDER,
        name="Guiding Service",
        heartbeat_interval_sec=5.0,
        timeout_sec=15.0,
        max_restart_attempts=3,
        critical=False,
    ),
    ServiceType.FOCUSER: ServiceConfig(
        service_type=ServiceType.FOCUSER,
        name="Focus Controller",
        heartbeat_interval_sec=30.0,
        timeout_sec=60.0,
        max_restart_attempts=3,
        critical=False,
    ),
    ServiceType.ENCLOSURE: ServiceConfig(
        service_type=ServiceType.ENCLOSURE,
        name="Enclosure Controller",
        heartbeat_interval_sec=30.0,
        timeout_sec=60.0,
        max_restart_attempts=2,
        critical=True,  # Enclosure control is safety-critical
    ),
    ServiceType.POWER: ServiceConfig(
        service_type=ServiceType.POWER,
        name="Power Monitor",
        heartbeat_interval_sec=30.0,
        timeout_sec=60.0,
        max_restart_attempts=3,
        critical=True,  # Power monitoring is safety-critical
    ),
}


# =============================================================================
# Service Watchdog
# =============================================================================

class ServiceWatchdog:
    """
    Monitors a single service's health (Steps 494-496).

    Tracks heartbeats and detects communication timeouts.
    """

    def __init__(self, config: ServiceConfig):
        """
        Initialize service watchdog.

        Args:
            config: Service configuration
        """
        self.config = config
        self.status = ServiceStatus(
            service_type=config.service_type,
            name=config.name,
        )
        self._restart_callback: Optional[Callable] = None
        self._failure_callback: Optional[Callable] = None

    def record_heartbeat(self):
        """Record a successful heartbeat from the service."""
        self.status.last_heartbeat = datetime.now()
        self.status.consecutive_failures = 0

        if self.status.state in {ServiceState.UNKNOWN, ServiceState.DEGRADED, ServiceState.RESTARTING}:
            self.status.state = ServiceState.HEALTHY
            logger.info(f"{self.config.name} is now healthy")

    def record_error(self, error: str):
        """
        Record an error from the service.

        Args:
            error: Error message
        """
        self.status.last_error = error
        self.status.consecutive_failures += 1
        logger.warning(f"{self.config.name} error: {error}")

        # Determine new state based on consecutive failures
        if self.status.consecutive_failures >= 3:
            self.status.state = ServiceState.FAILED
        else:
            self.status.state = ServiceState.DEGRADED

    def check_timeout(self) -> bool:
        """
        Check if service has timed out.

        Returns:
            True if timed out
        """
        if self.status.last_heartbeat is None:
            return False  # Never received heartbeat, don't timeout yet

        elapsed = self.status.seconds_since_heartbeat
        if elapsed is not None and elapsed > self.config.timeout_sec:
            if self.status.state != ServiceState.FAILED:
                self.status.state = ServiceState.FAILED
                self.status.last_error = f"Communication timeout after {elapsed:.1f}s"
                logger.error(f"{self.config.name} timed out after {elapsed:.1f}s")
            return True

        return False

    def can_restart(self) -> bool:
        """
        Check if service can be restarted (Step 498).

        Respects restart attempt limit and cooldown.

        Returns:
            True if restart is allowed
        """
        # Check restart limit
        if self.status.restart_count >= self.config.max_restart_attempts:
            return False

        # Check cooldown
        if self.status.last_restart is not None:
            elapsed = (datetime.now() - self.status.last_restart).total_seconds()
            if elapsed < self.config.restart_cooldown_sec:
                return False

        return True

    def record_restart_attempt(self):
        """Record a restart attempt."""
        self.status.restart_count += 1
        self.status.last_restart = datetime.now()
        self.status.state = ServiceState.RESTARTING
        logger.info(f"{self.config.name} restart attempt {self.status.restart_count}/{self.config.max_restart_attempts}")

    def reset_restart_count(self):
        """Reset restart counter (call after successful recovery)."""
        self.status.restart_count = 0

    def set_restart_callback(self, callback: Callable):
        """Set callback for restart requests."""
        self._restart_callback = callback

    def set_failure_callback(self, callback: Callable):
        """Set callback for persistent failures."""
        self._failure_callback = callback


# =============================================================================
# Watchdog Manager
# =============================================================================

class WatchdogManager:
    """
    Manages all service watchdogs (Steps 492-493).

    Coordinates health monitoring across all services and
    triggers appropriate actions on failures.
    """

    def __init__(self):
        """Initialize watchdog manager."""
        self._watchdogs: Dict[ServiceType, ServiceWatchdog] = {}
        self._running = False
        self._check_task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable] = []
        self._safe_state_callback: Optional[Callable] = None

        # Initialize default watchdogs
        for service_type, config in DEFAULT_CONFIGS.items():
            self._watchdogs[service_type] = ServiceWatchdog(config)

        logger.info(f"Watchdog manager initialized with {len(self._watchdogs)} services")

    def register_service(self, config: ServiceConfig):
        """
        Register a service for monitoring.

        Args:
            config: Service configuration
        """
        self._watchdogs[config.service_type] = ServiceWatchdog(config)
        logger.info(f"Registered watchdog for {config.name}")

    def get_watchdog(self, service_type: ServiceType) -> Optional[ServiceWatchdog]:
        """Get watchdog for a service type."""
        return self._watchdogs.get(service_type)

    def heartbeat(self, service_type: ServiceType):
        """
        Record heartbeat for a service (Step 493).

        Args:
            service_type: Service that sent heartbeat
        """
        watchdog = self._watchdogs.get(service_type)
        if watchdog:
            watchdog.record_heartbeat()
        else:
            logger.warning(f"Heartbeat from unregistered service: {service_type.value}")

    def report_error(self, service_type: ServiceType, error: str):
        """
        Report error from a service.

        Args:
            service_type: Service reporting error
            error: Error message
        """
        watchdog = self._watchdogs.get(service_type)
        if watchdog:
            watchdog.record_error(error)

    def get_status(self, service_type: ServiceType) -> Optional[ServiceStatus]:
        """Get status of a service."""
        watchdog = self._watchdogs.get(service_type)
        return watchdog.status if watchdog else None

    def get_all_status(self) -> Dict[str, ServiceStatus]:
        """Get status of all services."""
        return {
            st.value: wd.status
            for st, wd in self._watchdogs.items()
        }

    def is_all_healthy(self) -> bool:
        """Check if all services are healthy."""
        return all(wd.status.is_healthy for wd in self._watchdogs.values())

    def get_failed_services(self) -> List[ServiceType]:
        """Get list of failed services."""
        return [
            st for st, wd in self._watchdogs.items()
            if wd.status.is_failed
        ]

    def get_critical_failures(self) -> List[ServiceType]:
        """Get list of failed critical services."""
        return [
            st for st, wd in self._watchdogs.items()
            if wd.status.is_failed and wd.config.critical
        ]

    async def _check_services(self):
        """Periodic check of all services."""
        while self._running:
            try:
                failed_critical = []

                for service_type, watchdog in self._watchdogs.items():
                    # Check for timeout
                    if watchdog.check_timeout():
                        if watchdog.config.critical:
                            failed_critical.append(service_type)

                        # Attempt restart if allowed
                        if watchdog.can_restart():
                            watchdog.record_restart_attempt()
                            if watchdog._restart_callback:
                                try:
                                    await self._call_async(watchdog._restart_callback, service_type)
                                except Exception as e:
                                    logger.error(f"Restart callback failed: {e}")
                        elif watchdog.status.restart_count >= watchdog.config.max_restart_attempts:
                            # Max restarts exceeded
                            if watchdog._failure_callback:
                                try:
                                    await self._call_async(watchdog._failure_callback, service_type)
                                except Exception as e:
                                    logger.error(f"Failure callback failed: {e}")

                # Trigger safe state if critical services failed
                if failed_critical and self._safe_state_callback:
                    logger.critical(f"Critical services failed: {[s.value for s in failed_critical]}")
                    try:
                        await self._call_async(self._safe_state_callback, failed_critical)
                    except Exception as e:
                        logger.error(f"Safe state callback failed: {e}")

                # Notify callbacks
                for callback in self._callbacks:
                    try:
                        await self._call_async(callback, self.get_all_status())
                    except Exception as e:
                        logger.error(f"Status callback failed: {e}")

            except Exception as e:
                logger.error(f"Watchdog check error: {e}")

            await asyncio.sleep(5.0)  # Check every 5 seconds

    async def _call_async(self, callback: Callable, *args):
        """Call a callback that may be sync or async."""
        if asyncio.iscoroutinefunction(callback):
            await callback(*args)
        else:
            callback(*args)

    async def start(self):
        """Start watchdog monitoring."""
        if self._running:
            return

        self._running = True
        self._check_task = asyncio.create_task(self._check_services())
        logger.info("Watchdog manager started")

    async def stop(self):
        """Stop watchdog monitoring."""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        logger.info("Watchdog manager stopped")

    def register_status_callback(self, callback: Callable):
        """Register callback for status updates."""
        self._callbacks.append(callback)

    def set_safe_state_callback(self, callback: Callable):
        """Set callback for triggering safe state."""
        self._safe_state_callback = callback


# =============================================================================
# Mount Watchdog (Step 494)
# =============================================================================

class MountWatchdog(ServiceWatchdog):
    """
    Specialized watchdog for mount communication.

    Monitors mount connection and tracking status.
    """

    def __init__(self, config: Optional[ServiceConfig] = None):
        """Initialize mount watchdog."""
        if config is None:
            config = DEFAULT_CONFIGS[ServiceType.MOUNT]
        super().__init__(config)
        self._tracking_lost_count = 0

    def record_tracking_status(self, is_tracking: bool):
        """Record mount tracking status."""
        if is_tracking:
            self._tracking_lost_count = 0
        else:
            self._tracking_lost_count += 1
            if self._tracking_lost_count >= 3:
                self.record_error("Tracking lost")

    def record_position(self, ra: float, dec: float):
        """Record mount position as heartbeat."""
        self.record_heartbeat()


# =============================================================================
# Weather Watchdog (Step 495)
# =============================================================================

class WeatherWatchdog(ServiceWatchdog):
    """
    Specialized watchdog for weather service communication.

    Monitors weather data freshness.
    """

    def __init__(self, config: Optional[ServiceConfig] = None):
        """Initialize weather watchdog."""
        if config is None:
            config = DEFAULT_CONFIGS[ServiceType.WEATHER]
        super().__init__(config)
        self._stale_data_count = 0

    def record_weather_data(self, timestamp: datetime):
        """
        Record weather data update.

        Args:
            timestamp: Timestamp of weather data
        """
        # Check if data is stale
        data_age = (datetime.now() - timestamp).total_seconds()
        if data_age > 120:  # Data older than 2 minutes
            self._stale_data_count += 1
            if self._stale_data_count >= 3:
                self.record_error(f"Weather data stale ({data_age:.0f}s old)")
        else:
            self._stale_data_count = 0
            self.record_heartbeat()


# =============================================================================
# Camera Watchdog (Step 496)
# =============================================================================

class CameraWatchdog(ServiceWatchdog):
    """
    Specialized watchdog for camera communication.

    Monitors camera connection and exposure status.
    """

    def __init__(self, config: Optional[ServiceConfig] = None):
        """Initialize camera watchdog."""
        if config is None:
            config = DEFAULT_CONFIGS[ServiceType.CAMERA]
        super().__init__(config)
        self._exposure_timeout_count = 0

    def record_exposure_complete(self):
        """Record successful exposure completion."""
        self._exposure_timeout_count = 0
        self.record_heartbeat()

    def record_exposure_timeout(self):
        """Record exposure timeout."""
        self._exposure_timeout_count += 1
        if self._exposure_timeout_count >= 3:
            self.record_error("Multiple exposure timeouts")


# =============================================================================
# Safe State Handler (Step 499)
# =============================================================================

class SafeStateHandler:
    """
    Handles transition to safe state on persistent service failure (Step 499).

    When critical services fail and cannot be recovered, this handler
    ensures the observatory is secured by:
    1. Parking the telescope
    2. Closing the enclosure
    3. Sending alerts to the operator
    """

    def __init__(
        self,
        mount_client=None,
        roof_controller=None,
        alert_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize safe state handler.

        Args:
            mount_client: LX200Client for telescope control
            roof_controller: RoofController for enclosure
            alert_callback: Callback for sending alerts
        """
        self._mount = mount_client
        self._roof = roof_controller
        self._alert_callback = alert_callback
        self._in_safe_state = False
        self._safe_state_time: Optional[datetime] = None

    @property
    def in_safe_state(self) -> bool:
        """Check if system is in safe state."""
        return self._in_safe_state

    async def enter_safe_state(self, failed_services: List[ServiceType]) -> bool:
        """
        Enter safe state due to persistent service failure.

        This is the callback for WatchdogManager.set_safe_state_callback().

        Args:
            failed_services: List of services that failed

        Returns:
            True if safe state achieved, False otherwise
        """
        if self._in_safe_state:
            logger.warning("Already in safe state")
            return True

        logger.critical(f"ENTERING SAFE STATE - Failed services: {[s.value for s in failed_services]}")

        # Send alert
        alert_msg = f"CRITICAL: Entering safe state. Failed services: {', '.join(s.value for s in failed_services)}"
        if self._alert_callback:
            try:
                if asyncio.iscoroutinefunction(self._alert_callback):
                    await self._alert_callback(alert_msg)
                else:
                    self._alert_callback(alert_msg)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

        success = True

        # Step 1: Park telescope
        if self._mount:
            try:
                logger.info("Safe state: Parking telescope")
                self._mount.stop()
                await asyncio.sleep(0.5)
                park_result = self._mount.park()
                if park_result:
                    # Wait for park with timeout
                    for _ in range(30):  # 30 seconds timeout
                        await asyncio.sleep(1.0)
                        status = self._mount.get_status()
                        if status and status.is_parked:
                            logger.info("Safe state: Telescope parked")
                            break
                    else:
                        logger.error("Safe state: Park timeout")
                        success = False
                else:
                    logger.error("Safe state: Park command failed")
                    success = False
            except Exception as e:
                logger.error(f"Safe state: Park error - {e}")
                success = False

        # Step 2: Close enclosure
        if self._roof:
            try:
                logger.info("Safe state: Closing enclosure")
                close_result = await self._roof.close()
                if close_result:
                    # Wait for close with timeout
                    for _ in range(45):  # 45 seconds timeout
                        await asyncio.sleep(1.0)
                        state = self._roof.get_state()
                        state_str = state.value if hasattr(state, 'value') else str(state)
                        if state_str == "closed":
                            logger.info("Safe state: Enclosure closed")
                            break
                    else:
                        logger.error("Safe state: Close timeout")
                        success = False
                else:
                    logger.error("Safe state: Close command failed")
                    success = False
            except Exception as e:
                logger.error(f"Safe state: Close error - {e}")
                success = False

        self._in_safe_state = True
        self._safe_state_time = datetime.now()

        # Final alert
        if success:
            final_msg = "Safe state achieved - telescope parked, enclosure closed"
            logger.info(final_msg)
        else:
            final_msg = "ALERT: Safe state incomplete - manual intervention required"
            logger.error(final_msg)

        if self._alert_callback:
            try:
                if asyncio.iscoroutinefunction(self._alert_callback):
                    await self._alert_callback(final_msg)
                else:
                    self._alert_callback(final_msg)
            except Exception:
                pass

        return success

    def reset_safe_state(self) -> None:
        """Reset safe state flag (after manual intervention)."""
        if self._in_safe_state:
            logger.info("Safe state reset by operator")
            self._in_safe_state = False
            self._safe_state_time = None


# =============================================================================
# Factory Function
# =============================================================================

def create_watchdog_manager() -> WatchdogManager:
    """
    Create a watchdog manager with default configuration.

    Returns:
        Configured WatchdogManager instance
    """
    return WatchdogManager()


def create_safe_state_handler(
    mount_client=None,
    roof_controller=None,
    alert_callback: Optional[Callable[[str], None]] = None,
) -> SafeStateHandler:
    """
    Create a safe state handler.

    Args:
        mount_client: LX200Client instance
        roof_controller: RoofController instance
        alert_callback: Callback for alerts

    Returns:
        Configured SafeStateHandler instance
    """
    return SafeStateHandler(
        mount_client=mount_client,
        roof_controller=roof_controller,
        alert_callback=alert_callback,
    )
