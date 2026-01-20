"""
NIGHTWATCH Unified Weather Interface (Step 208)

Provides a single interface for all weather and atmospheric data,
abstracting the Ecowitt WS90 weather station and AAG CloudWatcher sensor.

The unified interface:
- Combines ground weather (Ecowitt) with sky conditions (CloudWatcher)
- Provides comprehensive safety assessment using all available data
- Handles graceful degradation when one sensor is unavailable
- Supports callbacks for weather events

Usage:
    service = UnifiedWeatherService(
        ecowitt_ip="192.168.1.50",
        cloudwatcher_host="192.168.1.100"
    )
    await service.connect()
    conditions = await service.get_conditions()
    print(f"Safe: {conditions.safe_to_observe}, Clouds: {conditions.cloud_condition}")
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Callable, List, Dict, Any

from .ecowitt import EcowittClient, WeatherData, WeatherCondition, WindCondition
from .cloudwatcher import (
    CloudWatcherClient,
    CloudWatcherData,
    CloudCondition,
    RainCondition,
    DaylightCondition,
    CloudThresholds
)

logger = logging.getLogger("NIGHTWATCH.UnifiedWeather")


class SafetyLevel(Enum):
    """Overall observatory safety level."""
    SAFE = "safe"               # All systems go
    MARGINAL = "marginal"       # Proceed with caution
    UNSAFE = "unsafe"           # Close roof, park telescope
    EMERGENCY = "emergency"     # Immediate emergency closure


@dataclass
class UnifiedConditions:
    """
    Combined weather and sky conditions from all sensors.

    This is the primary data structure returned by the unified interface,
    containing data from both Ecowitt and CloudWatcher sensors.
    """
    timestamp: datetime

    # Data availability
    ecowitt_available: bool = False
    cloudwatcher_available: bool = False

    # Ground weather (from Ecowitt)
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    dew_point_c: Optional[float] = None
    wind_speed_mph: Optional[float] = None
    wind_gust_mph: Optional[float] = None
    wind_direction: Optional[str] = None
    pressure_inhg: Optional[float] = None

    # Rain detection (combined from both sensors)
    is_raining: bool = False
    rain_rate_in_hr: float = 0.0
    ecowitt_rain: bool = False
    cloudwatcher_rain: RainCondition = RainCondition.UNKNOWN

    # Sky conditions (from CloudWatcher)
    sky_temp_c: Optional[float] = None
    sky_ambient_diff_c: Optional[float] = None
    cloud_condition: CloudCondition = CloudCondition.UNKNOWN
    daylight_condition: DaylightCondition = DaylightCondition.DARK

    # Solar/UV (from Ecowitt)
    solar_radiation_wm2: Optional[float] = None
    uv_index: Optional[float] = None

    # Overall conditions
    wind_condition: WindCondition = WindCondition.CALM
    weather_condition: WeatherCondition = WeatherCondition.GOOD

    # Safety assessment
    safe_to_observe: bool = False
    safety_level: SafetyLevel = SafetyLevel.UNSAFE
    safety_reasons: List[str] = field(default_factory=list)

    # Raw data references
    ecowitt_data: Optional[WeatherData] = None
    cloudwatcher_data: Optional[CloudWatcherData] = None


class UnifiedWeatherService:
    """
    Unified weather service combining Ecowitt and CloudWatcher (Step 208).

    Provides a single point of access for all weather and atmospheric
    conditions relevant to observatory operation.

    Example:
        service = UnifiedWeatherService()
        await service.connect()

        # Get combined conditions
        conditions = await service.get_conditions()

        if conditions.safe_to_observe:
            print("Conditions are safe for observing")
        else:
            print(f"Unsafe: {', '.join(conditions.safety_reasons)}")
    """

    # Safety thresholds
    WIND_LIMIT_MPH = 25.0
    GUST_LIMIT_MPH = 35.0
    HUMIDITY_LIMIT = 85.0
    TEMP_MIN_C = -7.0  # ~20°F
    TEMP_MAX_C = 40.0  # ~104°F
    DEW_POINT_MARGIN_C = 2.0  # Close if temp within this of dew point

    def __init__(
        self,
        ecowitt_ip: Optional[str] = None,
        ecowitt_port: int = 80,
        cloudwatcher_host: Optional[str] = None,
        cloudwatcher_port: int = 8081,
        cloud_thresholds: Optional[CloudThresholds] = None,
        poll_interval: float = 30.0
    ):
        """
        Initialize unified weather service.

        Args:
            ecowitt_ip: IP address of Ecowitt gateway (None to disable)
            ecowitt_port: Ecowitt gateway port
            cloudwatcher_host: CloudWatcher host (None to disable)
            cloudwatcher_port: CloudWatcher port
            cloud_thresholds: Custom cloud detection thresholds
            poll_interval: Seconds between automatic polls
        """
        self._ecowitt: Optional[EcowittClient] = None
        self._cloudwatcher: Optional[CloudWatcherClient] = None
        self._poll_interval = poll_interval
        self._callbacks: List[Callable] = []
        self._latest: Optional[UnifiedConditions] = None
        self._polling_task: Optional[asyncio.Task] = None

        # Initialize Ecowitt client if configured
        if ecowitt_ip:
            self._ecowitt = EcowittClient(
                gateway_ip=ecowitt_ip,
                gateway_port=ecowitt_port,
                poll_interval=poll_interval
            )
            logger.info(f"Ecowitt client configured: {ecowitt_ip}:{ecowitt_port}")

        # Initialize CloudWatcher client if configured
        if cloudwatcher_host:
            self._cloudwatcher = CloudWatcherClient(
                host=cloudwatcher_host,
                port=cloudwatcher_port,
                thresholds=cloud_thresholds
            )
            logger.info(f"CloudWatcher client configured: {cloudwatcher_host}:{cloudwatcher_port}")

    @property
    def ecowitt_enabled(self) -> bool:
        """Check if Ecowitt integration is enabled."""
        return self._ecowitt is not None

    @property
    def cloudwatcher_enabled(self) -> bool:
        """Check if CloudWatcher integration is enabled."""
        return self._cloudwatcher is not None

    @property
    def latest(self) -> Optional[UnifiedConditions]:
        """Get most recent unified conditions."""
        return self._latest

    async def connect(self) -> bool:
        """
        Connect to all configured weather sensors.

        Returns:
            True if at least one sensor connected successfully
        """
        ecowitt_ok = False
        cloudwatcher_ok = False

        # Connect to CloudWatcher (Ecowitt uses HTTP, no persistent connection)
        if self._cloudwatcher:
            cloudwatcher_ok = await self._cloudwatcher.connect()
            if cloudwatcher_ok:
                logger.info("CloudWatcher connected")
            else:
                logger.warning("CloudWatcher connection failed")

        # Test Ecowitt connectivity with a fetch
        if self._ecowitt:
            data = await self._ecowitt.fetch_data()
            ecowitt_ok = data is not None
            if ecowitt_ok:
                logger.info("Ecowitt connectivity verified")
            else:
                logger.warning("Ecowitt connectivity check failed")

        return ecowitt_ok or cloudwatcher_ok

    async def disconnect(self):
        """Disconnect from all sensors."""
        if self._polling_task:
            self._polling_task.cancel()
            self._polling_task = None

        if self._cloudwatcher:
            await self._cloudwatcher.disconnect()

        logger.info("Unified weather service disconnected")

    async def get_conditions(self) -> UnifiedConditions:
        """
        Get current unified weather and sky conditions.

        Fetches data from all available sensors and combines them
        into a unified conditions object with safety assessment.

        Returns:
            UnifiedConditions with combined data from all sensors
        """
        ecowitt_data: Optional[WeatherData] = None
        cloudwatcher_data: Optional[CloudWatcherData] = None

        # Fetch from both sources in parallel
        tasks = []
        if self._ecowitt:
            tasks.append(("ecowitt", self._ecowitt.fetch_data()))
        if self._cloudwatcher:
            tasks.append(("cloudwatcher", self._cloudwatcher.get_conditions()))

        if tasks:
            results = await asyncio.gather(
                *[t[1] for t in tasks],
                return_exceptions=True
            )

            for i, (name, _) in enumerate(tasks):
                result = results[i]
                if isinstance(result, Exception):
                    logger.error(f"Error fetching {name} data: {result}")
                elif name == "ecowitt":
                    ecowitt_data = result
                elif name == "cloudwatcher":
                    cloudwatcher_data = result

        # Combine into unified conditions
        conditions = self._combine_conditions(ecowitt_data, cloudwatcher_data)

        # Store and notify
        self._latest = conditions
        await self._notify_callbacks(conditions)

        return conditions

    def _combine_conditions(
        self,
        ecowitt: Optional[WeatherData],
        cloudwatcher: Optional[CloudWatcherData]
    ) -> UnifiedConditions:
        """Combine data from both sensors into unified conditions."""
        conditions = UnifiedConditions(
            timestamp=datetime.now(),
            ecowitt_available=ecowitt is not None,
            cloudwatcher_available=cloudwatcher is not None,
            ecowitt_data=ecowitt,
            cloudwatcher_data=cloudwatcher
        )

        # Populate from Ecowitt data
        if ecowitt:
            conditions.temperature_c = ecowitt.temperature_c
            conditions.humidity_percent = ecowitt.humidity_percent
            conditions.dew_point_c = (ecowitt.dew_point_f - 32) * 5 / 9
            conditions.wind_speed_mph = ecowitt.wind_speed_mph
            conditions.wind_gust_mph = ecowitt.wind_gust_mph
            conditions.wind_direction = ecowitt.wind_direction_str
            conditions.pressure_inhg = ecowitt.pressure_inhg
            conditions.ecowitt_rain = ecowitt.is_raining
            conditions.rain_rate_in_hr = ecowitt.rain_rate_in_hr
            conditions.solar_radiation_wm2 = ecowitt.solar_radiation_wm2
            conditions.uv_index = ecowitt.uv_index
            conditions.wind_condition = ecowitt.wind_condition
            conditions.weather_condition = ecowitt.condition

        # Populate from CloudWatcher data
        if cloudwatcher:
            conditions.sky_temp_c = cloudwatcher.sky_temp_c
            conditions.sky_ambient_diff_c = cloudwatcher.sky_ambient_diff_c
            conditions.cloud_condition = cloudwatcher.cloud_condition
            conditions.cloudwatcher_rain = cloudwatcher.rain_condition
            conditions.daylight_condition = cloudwatcher.daylight_condition

            # Use CloudWatcher ambient if Ecowitt not available
            if conditions.temperature_c is None:
                conditions.temperature_c = cloudwatcher.ambient_temp_c

        # Combined rain detection (either sensor)
        conditions.is_raining = (
            conditions.ecowitt_rain or
            conditions.cloudwatcher_rain in [RainCondition.WET, RainCondition.RAIN]
        )

        # Perform safety assessment
        self._assess_safety(conditions)

        return conditions

    def _assess_safety(self, conditions: UnifiedConditions):
        """
        Assess overall safety based on all available data.

        Updates the safety_level, safe_to_observe, and safety_reasons
        fields of the conditions object.
        """
        reasons = []
        level = SafetyLevel.SAFE

        # Rain check (highest priority)
        if conditions.is_raining:
            reasons.append("Rain detected")
            level = SafetyLevel.EMERGENCY

        # Wind checks
        if conditions.wind_gust_mph and conditions.wind_gust_mph > self.GUST_LIMIT_MPH:
            reasons.append(f"Wind gusts too high ({conditions.wind_gust_mph:.1f} mph)")
            level = max(level, SafetyLevel.EMERGENCY, key=lambda x: x.value)
        elif conditions.wind_speed_mph and conditions.wind_speed_mph > self.WIND_LIMIT_MPH:
            reasons.append(f"Wind speed too high ({conditions.wind_speed_mph:.1f} mph)")
            level = max(level, SafetyLevel.UNSAFE, key=lambda x: x.value)

        # Humidity check
        if conditions.humidity_percent and conditions.humidity_percent > self.HUMIDITY_LIMIT:
            reasons.append(f"Humidity too high ({conditions.humidity_percent:.1f}%)")
            level = max(level, SafetyLevel.UNSAFE, key=lambda x: x.value)

        # Dew point check
        if conditions.temperature_c is not None and conditions.dew_point_c is not None:
            dew_margin = conditions.temperature_c - conditions.dew_point_c
            if dew_margin < self.DEW_POINT_MARGIN_C:
                reasons.append(f"Dew risk (margin: {dew_margin:.1f}°C)")
                level = max(level, SafetyLevel.UNSAFE, key=lambda x: x.value)

        # Temperature checks
        if conditions.temperature_c is not None:
            if conditions.temperature_c < self.TEMP_MIN_C:
                reasons.append(f"Temperature too low ({conditions.temperature_c:.1f}°C)")
                level = max(level, SafetyLevel.MARGINAL, key=lambda x: x.value)
            elif conditions.temperature_c > self.TEMP_MAX_C:
                reasons.append(f"Temperature too high ({conditions.temperature_c:.1f}°C)")
                level = max(level, SafetyLevel.MARGINAL, key=lambda x: x.value)

        # Cloud check
        if conditions.cloud_condition == CloudCondition.OVERCAST:
            reasons.append("Sky overcast")
            level = max(level, SafetyLevel.UNSAFE, key=lambda x: x.value)
        elif conditions.cloud_condition == CloudCondition.CLOUDY:
            reasons.append("Cloudy conditions")
            if level == SafetyLevel.SAFE:
                level = SafetyLevel.MARGINAL

        # Daylight check (warning only)
        if conditions.daylight_condition == DaylightCondition.DAYLIGHT:
            reasons.append("Daytime (not dark)")
            if level == SafetyLevel.SAFE:
                level = SafetyLevel.MARGINAL

        # No data warning
        if not conditions.ecowitt_available and not conditions.cloudwatcher_available:
            reasons.append("No sensor data available")
            level = SafetyLevel.UNSAFE

        # Update conditions
        conditions.safety_level = level
        conditions.safe_to_observe = level in [SafetyLevel.SAFE, SafetyLevel.MARGINAL]
        conditions.safety_reasons = reasons

    def register_callback(self, callback: Callable):
        """Register callback for condition updates."""
        self._callbacks.append(callback)

    async def _notify_callbacks(self, conditions: UnifiedConditions):
        """Notify registered callbacks."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(conditions)
                else:
                    callback(conditions)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    async def start_polling(self):
        """Start background polling of weather conditions."""
        async def poll_loop():
            while True:
                try:
                    await self.get_conditions()
                except Exception as e:
                    logger.error(f"Polling error: {e}")
                await asyncio.sleep(self._poll_interval)

        self._polling_task = asyncio.create_task(poll_loop())
        logger.info(f"Started polling with {self._poll_interval}s interval")

    def stop_polling(self):
        """Stop background polling."""
        if self._polling_task:
            self._polling_task.cancel()
            self._polling_task = None
            logger.info("Stopped polling")

    def get_status(self) -> Dict[str, Any]:
        """Get current service status."""
        status = {
            "ecowitt_enabled": self.ecowitt_enabled,
            "cloudwatcher_enabled": self.cloudwatcher_enabled,
            "polling_active": self._polling_task is not None,
            "poll_interval": self._poll_interval
        }

        if self._latest:
            status["last_update"] = self._latest.timestamp.isoformat()
            status["ecowitt_available"] = self._latest.ecowitt_available
            status["cloudwatcher_available"] = self._latest.cloudwatcher_available
            status["safety_level"] = self._latest.safety_level.value
            status["safe_to_observe"] = self._latest.safe_to_observe

        return status

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    async def is_safe(self) -> bool:
        """Quick check if conditions are safe for observing."""
        conditions = await self.get_conditions()
        return conditions.safe_to_observe

    async def get_safety_summary(self) -> str:
        """Get human-readable safety summary."""
        conditions = await self.get_conditions()

        if conditions.safe_to_observe:
            if conditions.safety_level == SafetyLevel.SAFE:
                return "Conditions are safe for observing."
            else:
                return f"Conditions are marginal: {', '.join(conditions.safety_reasons)}"
        else:
            return f"UNSAFE: {', '.join(conditions.safety_reasons)}"

    async def get_cloud_status(self) -> str:
        """Get current cloud status as string."""
        conditions = await self.get_conditions()
        if conditions.cloudwatcher_available:
            diff = conditions.sky_ambient_diff_c
            return f"{conditions.cloud_condition.value} (sky-ambient: {diff:.1f}°C)"
        return "Cloud sensor unavailable"

    def get_ecowitt_client(self) -> Optional[EcowittClient]:
        """Get underlying Ecowitt client for direct access."""
        return self._ecowitt

    def get_cloudwatcher_client(self) -> Optional[CloudWatcherClient]:
        """Get underlying CloudWatcher client for direct access."""
        return self._cloudwatcher


# Factory function for common configurations
def create_weather_service(
    config: Optional[Dict[str, Any]] = None
) -> UnifiedWeatherService:
    """
    Create a UnifiedWeatherService from configuration dict.

    Args:
        config: Configuration dict with keys:
            - ecowitt_ip: Ecowitt gateway IP
            - ecowitt_port: Ecowitt gateway port (default 80)
            - cloudwatcher_host: CloudWatcher host
            - cloudwatcher_port: CloudWatcher port (default 8081)
            - poll_interval: Polling interval in seconds

    Returns:
        Configured UnifiedWeatherService instance
    """
    config = config or {}

    return UnifiedWeatherService(
        ecowitt_ip=config.get("ecowitt_ip"),
        ecowitt_port=config.get("ecowitt_port", 80),
        cloudwatcher_host=config.get("cloudwatcher_host"),
        cloudwatcher_port=config.get("cloudwatcher_port", 8081),
        poll_interval=config.get("poll_interval", 30.0)
    )
