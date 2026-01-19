"""
NIGHTWATCH Service Health Check Framework

Provides a unified health check system for validating service availability
and readiness during startup and runtime monitoring.

Usage:
    from nightwatch.health import HealthChecker, HealthStatus

    checker = HealthChecker(config)
    results = await checker.check_all()

    if results.all_healthy:
        print("All services ready")
    else:
        for name, status in results.items():
            if not status.healthy:
                print(f"{name}: {status.message}")
"""

from __future__ import annotations

import asyncio
import socket
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Callable, Awaitable

from nightwatch.logging_config import get_logger

if TYPE_CHECKING:
    from nightwatch.config import NightwatchConfig

__all__ = [
    "HealthStatus",
    "ServiceHealth",
    "HealthCheckResult",
    "HealthChecker",
    "check_tcp_connection",
    "check_http_endpoint",
]

logger = get_logger(__name__)


# =============================================================================
# Health Status Types
# =============================================================================


class HealthStatus(Enum):
    """Health check status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"  # Working but with issues
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    DISABLED = "disabled"  # Service intentionally disabled


@dataclass
class ServiceHealth:
    """Health status for a single service."""

    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    details: dict = field(default_factory=dict)

    @property
    def healthy(self) -> bool:
        """Check if service is healthy or disabled."""
        return self.status in (HealthStatus.HEALTHY, HealthStatus.DISABLED)

    @property
    def available(self) -> bool:
        """Check if service is available for use."""
        return self.status == HealthStatus.HEALTHY


@dataclass
class HealthCheckResult:
    """Aggregated health check results for all services."""

    services: dict[str, ServiceHealth] = field(default_factory=dict)
    checked_at: float = field(default_factory=time.time)

    @property
    def all_healthy(self) -> bool:
        """Check if all services are healthy."""
        return all(s.healthy for s in self.services.values())

    @property
    def all_required_healthy(self) -> bool:
        """Check if all required (non-disabled) services are healthy."""
        return all(
            s.healthy
            for s in self.services.values()
            if s.status != HealthStatus.DISABLED
        )

    @property
    def summary(self) -> str:
        """Get a summary of health check results."""
        total = len(self.services)
        healthy = sum(1 for s in self.services.values() if s.healthy)
        return f"{healthy}/{total} services healthy"

    def __iter__(self):
        """Iterate over service health items."""
        return iter(self.services.items())


# =============================================================================
# Health Check Utilities
# =============================================================================


async def check_tcp_connection(
    host: str,
    port: int,
    timeout: float = 5.0,
) -> tuple[bool, float, str]:
    """Check if a TCP connection can be established.

    Args:
        host: Hostname or IP address
        port: Port number
        timeout: Connection timeout in seconds

    Returns:
        Tuple of (success, latency_ms, message)
    """
    start = time.monotonic()
    try:
        # Use asyncio for non-blocking connection
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
        latency = (time.monotonic() - start) * 1000
        writer.close()
        await writer.wait_closed()
        return True, latency, f"Connected to {host}:{port}"
    except asyncio.TimeoutError:
        latency = (time.monotonic() - start) * 1000
        return False, latency, f"Connection timeout to {host}:{port}"
    except OSError as e:
        latency = (time.monotonic() - start) * 1000
        return False, latency, f"Connection failed to {host}:{port}: {e}"


async def check_http_endpoint(
    url: str,
    timeout: float = 5.0,
    expected_status: int = 200,
) -> tuple[bool, float, str]:
    """Check if an HTTP endpoint is responding.

    Args:
        url: Full URL to check
        timeout: Request timeout in seconds
        expected_status: Expected HTTP status code

    Returns:
        Tuple of (success, latency_ms, message)
    """
    try:
        import aiohttp

        start = time.monotonic()
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                latency = (time.monotonic() - start) * 1000
                if resp.status == expected_status:
                    return True, latency, f"HTTP {resp.status} from {url}"
                else:
                    return False, latency, f"HTTP {resp.status} (expected {expected_status})"
    except ImportError:
        return False, 0.0, "aiohttp not installed"
    except asyncio.TimeoutError:
        return False, timeout * 1000, f"HTTP timeout to {url}"
    except Exception as e:
        return False, 0.0, f"HTTP error: {e}"


def check_socket_sync(host: str, port: int, timeout: float = 5.0) -> tuple[bool, str]:
    """Synchronous TCP connection check (for use in sync contexts).

    Args:
        host: Hostname or IP address
        port: Port number
        timeout: Connection timeout in seconds

    Returns:
        Tuple of (success, message)
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True, f"Connected to {host}:{port}"
    except socket.timeout:
        return False, f"Connection timeout to {host}:{port}"
    except OSError as e:
        return False, f"Connection failed: {e}"


# =============================================================================
# Service-Specific Health Checks (Steps 47-49)
# =============================================================================


async def check_mount_health(config: "NightwatchConfig") -> ServiceHealth:
    """Check mount controller connectivity (Step 47).

    Args:
        config: Application configuration

    Returns:
        ServiceHealth for mount service
    """
    mount_config = config.mount

    if mount_config.type == "simulator":
        return ServiceHealth(
            name="mount",
            status=HealthStatus.HEALTHY,
            message="Simulator mode",
            details={"type": "simulator"},
        )

    # Check TCP connection to mount controller
    success, latency, message = await check_tcp_connection(
        mount_config.host,
        mount_config.port,
        mount_config.timeout,
    )

    if success:
        return ServiceHealth(
            name="mount",
            status=HealthStatus.HEALTHY,
            message=message,
            latency_ms=latency,
            details={
                "host": mount_config.host,
                "port": mount_config.port,
                "type": mount_config.type,
            },
        )
    else:
        return ServiceHealth(
            name="mount",
            status=HealthStatus.UNHEALTHY,
            message=message,
            latency_ms=latency,
            details={
                "host": mount_config.host,
                "port": mount_config.port,
            },
        )


async def check_weather_health(config: "NightwatchConfig") -> ServiceHealth:
    """Check weather station connectivity (Step 48).

    Args:
        config: Application configuration

    Returns:
        ServiceHealth for weather service
    """
    weather_config = config.weather

    if not weather_config.enabled:
        return ServiceHealth(
            name="weather",
            status=HealthStatus.DISABLED,
            message="Weather monitoring disabled",
        )

    if weather_config.type == "simulator":
        return ServiceHealth(
            name="weather",
            status=HealthStatus.HEALTHY,
            message="Simulator mode",
            details={"type": "simulator"},
        )

    if weather_config.type == "none":
        return ServiceHealth(
            name="weather",
            status=HealthStatus.DISABLED,
            message="No weather station configured",
        )

    # Check HTTP endpoint for Ecowitt
    if weather_config.type == "ecowitt":
        url = f"http://{weather_config.host}:{weather_config.port}/"
        success, latency, message = await check_http_endpoint(url)

        if success:
            return ServiceHealth(
                name="weather",
                status=HealthStatus.HEALTHY,
                message=message,
                latency_ms=latency,
                details={
                    "host": weather_config.host,
                    "type": weather_config.type,
                },
            )
        else:
            return ServiceHealth(
                name="weather",
                status=HealthStatus.UNHEALTHY,
                message=message,
                latency_ms=latency,
            )

    # For other types, check TCP connection
    success, latency, message = await check_tcp_connection(
        weather_config.host,
        weather_config.port,
        timeout=5.0,
    )

    status = HealthStatus.HEALTHY if success else HealthStatus.UNHEALTHY
    return ServiceHealth(
        name="weather",
        status=status,
        message=message,
        latency_ms=latency,
    )


async def check_voice_health(config: "NightwatchConfig") -> ServiceHealth:
    """Check voice pipeline readiness (Step 49).

    Args:
        config: Application configuration

    Returns:
        ServiceHealth for voice pipeline
    """
    voice_config = config.voice
    tts_config = config.tts

    if not voice_config.enabled and not tts_config.enabled:
        return ServiceHealth(
            name="voice",
            status=HealthStatus.DISABLED,
            message="Voice pipeline disabled",
        )

    # Check if required packages are available
    issues = []
    details = {}

    # Check STT (faster-whisper)
    if voice_config.enabled:
        try:
            import faster_whisper  # noqa: F401
            details["stt"] = "faster-whisper available"
        except ImportError:
            issues.append("faster-whisper not installed")
            details["stt"] = "not available"

    # Check TTS (piper)
    if tts_config.enabled:
        try:
            import piper  # noqa: F401
            details["tts"] = "piper available"
        except ImportError:
            # Piper might be installed differently
            details["tts"] = "piper check skipped"

    # Check CUDA availability for GPU acceleration
    if voice_config.device in ("cuda", "auto") or tts_config.use_cuda:
        try:
            import torch
            if torch.cuda.is_available():
                details["cuda"] = f"available ({torch.cuda.get_device_name(0)})"
            else:
                details["cuda"] = "not available (CPU fallback)"
                if voice_config.device == "cuda":
                    issues.append("CUDA requested but not available")
        except ImportError:
            details["cuda"] = "torch not installed"

    if issues:
        return ServiceHealth(
            name="voice",
            status=HealthStatus.DEGRADED if len(issues) < 2 else HealthStatus.UNHEALTHY,
            message="; ".join(issues),
            details=details,
        )

    return ServiceHealth(
        name="voice",
        status=HealthStatus.HEALTHY,
        message="Voice pipeline ready",
        details=details,
    )


async def check_guider_health(config: "NightwatchConfig") -> ServiceHealth:
    """Check PHD2 guider connectivity.

    Args:
        config: Application configuration

    Returns:
        ServiceHealth for guider service
    """
    guider_config = config.guider

    if not guider_config.enabled:
        return ServiceHealth(
            name="guider",
            status=HealthStatus.DISABLED,
            message="Autoguiding disabled",
        )

    success, latency, message = await check_tcp_connection(
        guider_config.phd2_host,
        guider_config.phd2_port,
        timeout=5.0,
    )

    status = HealthStatus.HEALTHY if success else HealthStatus.UNHEALTHY
    return ServiceHealth(
        name="guider",
        status=status,
        message=message,
        latency_ms=latency,
    )


async def check_power_health(config: "NightwatchConfig") -> ServiceHealth:
    """Check NUT UPS monitoring connectivity.

    Args:
        config: Application configuration

    Returns:
        ServiceHealth for power service
    """
    power_config = config.power

    if not power_config.enabled:
        return ServiceHealth(
            name="power",
            status=HealthStatus.DISABLED,
            message="Power monitoring disabled",
        )

    success, latency, message = await check_tcp_connection(
        power_config.ups_host,
        power_config.ups_port,
        timeout=5.0,
    )

    status = HealthStatus.HEALTHY if success else HealthStatus.UNHEALTHY
    return ServiceHealth(
        name="power",
        status=status,
        message=message,
        latency_ms=latency,
    )


# =============================================================================
# Health Checker (Step 46)
# =============================================================================


class HealthChecker:
    """Unified health check manager for all services (Step 46).

    Coordinates health checks across all configured services with
    configurable timeouts and parallel execution.
    """

    def __init__(self, config: "NightwatchConfig") -> None:
        """Initialize health checker.

        Args:
            config: Application configuration
        """
        self.config = config
        self._checks: dict[str, Callable[["NightwatchConfig"], Awaitable[ServiceHealth]]] = {
            "mount": check_mount_health,
            "weather": check_weather_health,
            "voice": check_voice_health,
            "guider": check_guider_health,
            "power": check_power_health,
        }

    def register_check(
        self,
        name: str,
        check_fn: Callable[["NightwatchConfig"], Awaitable[ServiceHealth]],
    ) -> None:
        """Register a custom health check.

        Args:
            name: Service name
            check_fn: Async function that returns ServiceHealth
        """
        self._checks[name] = check_fn

    async def check_service(self, name: str) -> ServiceHealth:
        """Run health check for a single service.

        Args:
            name: Service name

        Returns:
            ServiceHealth result
        """
        if name not in self._checks:
            return ServiceHealth(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"No health check registered for '{name}'",
            )

        try:
            return await self._checks[name](self.config)
        except Exception as e:
            logger.exception(f"Health check failed for {name}: {e}")
            return ServiceHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check error: {e}",
            )

    async def check_all(
        self,
        timeout: float = 30.0,
        services: list[str] | None = None,
    ) -> HealthCheckResult:
        """Run health checks for all services in parallel.

        Args:
            timeout: Overall timeout for all checks
            services: Optional list of specific services to check

        Returns:
            Aggregated HealthCheckResult
        """
        check_names = services or list(self._checks.keys())

        logger.info(f"Running health checks for: {', '.join(check_names)}")

        # Run all checks in parallel
        tasks = [self.check_service(name) for name in check_names]

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.error("Health checks timed out")
            results = [
                ServiceHealth(
                    name=name,
                    status=HealthStatus.UNKNOWN,
                    message="Health check timed out",
                )
                for name in check_names
            ]

        # Build result
        health_result = HealthCheckResult()
        for i, result in enumerate(results):
            name = check_names[i]
            if isinstance(result, Exception):
                health_result.services[name] = ServiceHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(result),
                )
            else:
                health_result.services[name] = result

        # Log summary
        for name, health in health_result.services.items():
            level = "info" if health.healthy else "warning"
            getattr(logger, level)(
                f"  {name}: {health.status.value} - {health.message}"
            )

        logger.info(f"Health check complete: {health_result.summary}")
        return health_result

    async def wait_for_healthy(
        self,
        services: list[str],
        timeout: float = 60.0,
        interval: float = 2.0,
    ) -> bool:
        """Wait for specified services to become healthy.

        Args:
            services: List of service names to wait for
            timeout: Maximum time to wait
            interval: Time between checks

        Returns:
            True if all services became healthy, False on timeout
        """
        start = time.monotonic()
        while (time.monotonic() - start) < timeout:
            result = await self.check_all(services=services)
            if result.all_required_healthy:
                return True
            await asyncio.sleep(interval)

        return False


# =============================================================================
# Startup Sequence (Step 50)
# =============================================================================


class StartupSequence:
    """Manages ordered service startup with health checks (Step 50).

    Services are started in dependency order:
    1. Core infrastructure (config, logging) - already done
    2. External connections (mount, weather, power)
    3. Optional services (guider, voice)
    """

    # Service startup order and dependencies
    STARTUP_ORDER = [
        # (service_name, required, dependencies)
        ("power", False, []),  # Check UPS first
        ("mount", True, []),  # Mount is required
        ("weather", False, []),  # Weather is optional
        ("guider", False, ["mount"]),  # Guider needs mount
        ("voice", False, []),  # Voice is optional
    ]

    def __init__(self, config: "NightwatchConfig") -> None:
        """Initialize startup sequence.

        Args:
            config: Application configuration
        """
        self.config = config
        self.health_checker = HealthChecker(config)
        self._started_services: set[str] = set()

    async def run(
        self,
        skip_optional: bool = False,
        timeout_per_service: float = 30.0,
    ) -> tuple[bool, HealthCheckResult]:
        """Run the startup sequence.

        Args:
            skip_optional: If True, skip non-required services
            timeout_per_service: Timeout for each service check

        Returns:
            Tuple of (success, final_health_result)
        """
        logger.info("Starting NIGHTWATCH startup sequence...")
        all_healthy = True

        for service_name, required, dependencies in self.STARTUP_ORDER:
            # Skip optional services if requested
            if skip_optional and not required:
                logger.info(f"Skipping optional service: {service_name}")
                continue

            # Check dependencies
            for dep in dependencies:
                if dep not in self._started_services:
                    logger.warning(
                        f"Skipping {service_name}: dependency '{dep}' not started"
                    )
                    continue

            # Check service health
            logger.info(f"Checking {service_name}...")
            health = await self.health_checker.check_service(service_name)

            if health.healthy:
                self._started_services.add(service_name)
                logger.info(f"  ✓ {service_name}: {health.message}")
            elif health.status == HealthStatus.DISABLED:
                logger.info(f"  - {service_name}: disabled")
            elif required:
                logger.error(f"  ✗ {service_name}: {health.message}")
                all_healthy = False
                # Don't continue if required service fails
                break
            else:
                logger.warning(f"  ! {service_name}: {health.message} (optional)")

        # Final health check
        final_result = await self.health_checker.check_all()

        if all_healthy and final_result.all_required_healthy:
            logger.info("Startup sequence completed successfully")
        else:
            logger.error("Startup sequence completed with errors")

        return all_healthy, final_result
