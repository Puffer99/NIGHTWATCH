"""
NIGHTWATCH Safety Monitor Service
Observatory Automation and Safety Controller

This module implements the safety logic for autonomous observatory operation.
It integrates data from weather sensors, cloud sensor, and mount status to
make automated decisions about telescope operation.

Safety Priority Order:
1. Rain detection -> Immediate park
2. High wind -> Park and wait
3. Cloud cover -> Park and wait
4. Daylight -> Park for day
5. All clear -> Safe to observe
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Callable, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NIGHTWATCH.Safety")


class SafetyAction(Enum):
    """Actions the safety monitor can command."""
    SAFE_TO_OBSERVE = "safe_to_observe"
    PARK_AND_WAIT = "park_and_wait"
    PARK_FOR_DAYLIGHT = "park_for_daylight"
    EMERGENCY_CLOSE = "emergency_close"
    DEW_WARNING = "dew_warning"
    COLD_WARNING = "cold_warning"


class ObservatoryState(Enum):
    """Current observatory operational state."""
    UNKNOWN = "unknown"
    CLOSED = "closed"
    OPENING = "opening"
    OPEN_IDLE = "open_idle"
    OBSERVING = "observing"
    PARKING = "parking"
    PARKED = "parked"
    EMERGENCY = "emergency"


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class SafetyStatus:
    """Current safety assessment."""
    timestamp: datetime
    action: SafetyAction
    is_safe: bool
    reasons: List[str]
    alert_level: AlertLevel

    # Individual sensor status
    weather_ok: bool = True
    clouds_ok: bool = True
    daylight_ok: bool = True
    mount_ok: bool = True

    # Environmental readings
    temperature_f: Optional[float] = None
    humidity_percent: Optional[float] = None
    wind_speed_mph: Optional[float] = None
    cloud_cover_percent: Optional[float] = None
    sun_altitude_deg: Optional[float] = None


@dataclass
class SafetyThresholds:
    """
    Configurable safety thresholds.

    POS Panel Recommendations (v1.0):
    - Antonio García: Calibrated cloud thresholds for Nevada altitude
    - Bob Denny: Added sensor timeout and hysteresis for ASCOM compatibility
    - Sierra Remote: Adjusted timing for autonomous operation
    """
    # Wind limits (POS: calibrated for 6000ft elevation)
    wind_limit_mph: float = 25.0
    wind_gust_limit_mph: float = 35.0
    wind_hysteresis_mph: float = 5.0      # POS: Must drop 5mph below limit to clear

    # Humidity/temperature (POS: adjusted for Nevada desert)
    humidity_limit: float = 85.0
    humidity_hysteresis: float = 5.0      # POS: Must drop to 80% to clear
    temp_min_f: float = 20.0
    dew_point_margin_f: float = 5.0       # POS: Park if within 5°F of dew point

    # Cloud sensor (sky-ambient differential in Celsius)
    # POS Antonio García: Calibrated for Nevada altitude (thinner atmosphere)
    clear_sky_threshold: float = -25.0    # < -25°C = clear
    cloudy_threshold: float = -15.0       # > -15°C = cloudy
    cloud_hysteresis: float = 3.0         # POS: 3°C hysteresis band

    # Sun altitude for astronomical twilight
    twilight_altitude: float = -12.0      # degrees
    twilight_hysteresis: float = 2.0      # POS: 2° hysteresis

    # Timing (POS Bob Denny: ASCOM-compatible timeouts)
    unsafe_duration_to_park: float = 60.0  # seconds before parking
    safe_duration_to_resume: float = 300.0 # seconds (5 min) to confirm safe

    # POS: Sensor health timeouts (treat stale data as unsafe)
    weather_sensor_timeout: float = 120.0  # seconds - Ecowitt update interval ~60s
    cloud_sensor_timeout: float = 180.0    # seconds - CloudWatcher slower updates
    ephemeris_timeout: float = 600.0       # seconds - ephemeris changes slowly


@dataclass
class SensorInput:
    """Input from a single sensor."""
    name: str
    value: Any
    timestamp: datetime
    is_valid: bool = True
    error: Optional[str] = None


class SafetyMonitor:
    """
    Main safety monitor for NIGHTWATCH observatory.

    Integrates multiple sensor inputs and makes automated decisions
    about telescope operation to protect equipment.
    """

    def __init__(
        self,
        thresholds: Optional[SafetyThresholds] = None,
        mount_controller=None,
        weather_client=None,
        cloud_sensor=None
    ):
        self.thresholds = thresholds or SafetyThresholds()
        self.mount = mount_controller
        self.weather = weather_client
        self.cloud_sensor = cloud_sensor

        self._state = ObservatoryState.UNKNOWN
        self._last_status: Optional[SafetyStatus] = None
        self._unsafe_since: Optional[datetime] = None
        self._safe_since: Optional[datetime] = None
        self._callbacks: List[Callable] = []
        self._running = False

        # Sensor data cache
        self._weather_data: Optional[SensorInput] = None
        self._cloud_data: Optional[SensorInput] = None
        self._sun_altitude: Optional[float] = None
        self._sun_altitude_time: Optional[datetime] = None

        # POS: Hysteresis state tracking
        # Tracks whether each condition is currently in "triggered" state
        self._wind_triggered: bool = False
        self._humidity_triggered: bool = False
        self._cloud_triggered: bool = False
        self._daylight_triggered: bool = False

    @property
    def state(self) -> ObservatoryState:
        """Current observatory state."""
        return self._state

    @property
    def last_status(self) -> Optional[SafetyStatus]:
        """Most recent safety assessment."""
        return self._last_status

    def register_callback(self, callback: Callable[[SafetyStatus], None]):
        """Register callback for safety status changes."""
        self._callbacks.append(callback)

    async def update_weather(self, data):
        """Update weather sensor data."""
        self._weather_data = SensorInput(
            name="Ecowitt WS90",
            value=data,
            timestamp=datetime.now()
        )

    async def update_cloud_sensor(self, sky_temp_diff: float):
        """Update cloud sensor data (sky-ambient temperature difference)."""
        self._cloud_data = SensorInput(
            name="CloudWatcher",
            value=sky_temp_diff,
            timestamp=datetime.now()
        )

    async def update_sun_altitude(self, altitude: float):
        """Update sun altitude (from ephemeris service)."""
        self._sun_altitude = altitude
        self._sun_altitude_time = datetime.now()

    def _is_sensor_stale(self, sensor: Optional[SensorInput], timeout: float) -> bool:
        """
        Check if sensor data is stale (POS recommendation).

        Args:
            sensor: Sensor input to check
            timeout: Maximum age in seconds

        Returns:
            True if sensor is stale or missing
        """
        if not sensor:
            return True
        age = (datetime.now() - sensor.timestamp).total_seconds()
        return age > timeout

    def _evaluate_weather(self) -> tuple[bool, List[str]]:
        """
        Evaluate weather conditions with hysteresis (POS recommendation).

        Hysteresis prevents rapid oscillation between safe/unsafe states
        when conditions are near threshold values.
        """
        reasons = []

        # POS: Check for stale sensor data
        if self._is_sensor_stale(self._weather_data, self.thresholds.weather_sensor_timeout):
            return False, ["Weather data stale or unavailable - treating as unsafe"]

        if not self._weather_data or not self._weather_data.is_valid:
            return False, ["Weather data unavailable"]

        data = self._weather_data.value
        if not data:
            return False, ["Weather data unavailable"]

        # Check rain (no hysteresis - immediate response)
        if hasattr(data, 'is_raining') and data.is_raining:
            return False, ["Rain detected - EMERGENCY"]

        if hasattr(data, 'rain_rate_in_hr') and data.rain_rate_in_hr > 0:
            return False, [f"Rain rate: {data.rain_rate_in_hr} in/hr - EMERGENCY"]

        # Check wind with hysteresis (POS recommendation)
        if hasattr(data, 'wind_gust_mph'):
            if data.wind_gust_mph > self.thresholds.wind_gust_limit_mph:
                self._wind_triggered = True
                return False, [f"Wind gust {data.wind_gust_mph:.1f} mph exceeds limit"]

        if hasattr(data, 'wind_speed_mph'):
            wind = data.wind_speed_mph
            if self._wind_triggered:
                # POS: Must drop below limit minus hysteresis to clear
                clear_threshold = self.thresholds.wind_limit_mph - self.thresholds.wind_hysteresis_mph
                if wind < clear_threshold:
                    self._wind_triggered = False
                else:
                    reasons.append(f"Wind {wind:.1f} mph - waiting for drop below {clear_threshold:.0f} mph")
            else:
                if wind > self.thresholds.wind_limit_mph:
                    self._wind_triggered = True
                    reasons.append(f"Wind {wind:.1f} mph exceeds limit")

        # Check humidity with hysteresis (POS recommendation)
        if hasattr(data, 'humidity_percent'):
            humidity = data.humidity_percent
            if self._humidity_triggered:
                clear_threshold = self.thresholds.humidity_limit - self.thresholds.humidity_hysteresis
                if humidity < clear_threshold:
                    self._humidity_triggered = False
                else:
                    reasons.append(f"Humidity {humidity:.1f}% - waiting for drop below {clear_threshold:.0f}%")
            else:
                if humidity > self.thresholds.humidity_limit:
                    self._humidity_triggered = True
                    reasons.append(f"Humidity {humidity:.1f}% exceeds limit")

        # Check temperature
        if hasattr(data, 'temperature_f'):
            if data.temperature_f < self.thresholds.temp_min_f:
                reasons.append(f"Temperature {data.temperature_f:.1f}°F below minimum")

        # POS: Check dew point proximity
        if hasattr(data, 'temperature_f') and hasattr(data, 'dew_point_f'):
            margin = data.temperature_f - data.dew_point_f
            if margin < self.thresholds.dew_point_margin_f:
                reasons.append(f"Temperature within {margin:.1f}°F of dew point - condensation risk")

        is_ok = len(reasons) == 0
        return is_ok, reasons

    def _evaluate_clouds(self) -> tuple[bool, List[str]]:
        """
        Evaluate cloud cover from IR sensor with hysteresis (POS recommendation).

        Antonio García's CloudWatcher calibration notes:
        - Sky-ambient differential indicates cloud cover
        - Nevada's thinner atmosphere at 6000ft affects readings
        - Hysteresis prevents oscillation during partly cloudy conditions
        """
        # POS: Check for stale sensor data
        if self._is_sensor_stale(self._cloud_data, self.thresholds.cloud_sensor_timeout):
            # Cloud sensor timeout - log warning but don't block
            # (weather sensor is primary safety)
            logger.warning("Cloud sensor data stale")
            return True, ["Cloud sensor data stale - relying on weather sensor"]

        if not self._cloud_data or not self._cloud_data.is_valid:
            # If no cloud sensor, assume OK (but log warning)
            return True, []

        sky_diff = self._cloud_data.value

        # POS: Apply hysteresis to prevent oscillation
        if self._cloud_triggered:
            # Currently cloudy - need clear reading plus hysteresis to clear
            clear_threshold = self.thresholds.clear_sky_threshold - self.thresholds.cloud_hysteresis
            if sky_diff < clear_threshold:
                self._cloud_triggered = False
                return True, [f"Clouds clearing: sky-ambient diff {sky_diff:.1f}°C"]
            else:
                return False, [f"Cloudy: sky-ambient diff {sky_diff:.1f}°C (waiting for < {clear_threshold:.0f}°C)"]
        else:
            # Currently clear - trigger if above cloudy threshold
            if sky_diff > self.thresholds.cloudy_threshold:
                self._cloud_triggered = True
                return False, [f"Cloudy: sky-ambient diff {sky_diff:.1f}°C"]

            if sky_diff > self.thresholds.clear_sky_threshold:
                return True, [f"Partly cloudy: sky-ambient diff {sky_diff:.1f}°C"]

        return True, []

    def _evaluate_daylight(self) -> tuple[bool, List[str]]:
        """
        Evaluate if it's astronomical night with hysteresis (POS recommendation).

        Hysteresis prevents rapid state changes during twilight transitions.
        """
        # POS: Check ephemeris staleness
        if self._sun_altitude_time:
            age = (datetime.now() - self._sun_altitude_time).total_seconds()
            if age > self.thresholds.ephemeris_timeout:
                logger.warning("Ephemeris data stale")
                # Don't fail on stale ephemeris - it changes slowly
                # But log for monitoring

        if self._sun_altitude is None:
            # If no ephemeris data, assume OK
            return True, []

        # POS: Apply hysteresis for twilight transitions
        if self._daylight_triggered:
            # Currently in daylight mode - need sun well below horizon to clear
            clear_threshold = self.thresholds.twilight_altitude - self.thresholds.twilight_hysteresis
            if self._sun_altitude < clear_threshold:
                self._daylight_triggered = False
                return True, [f"Astronomical night beginning (sun at {self._sun_altitude:.1f}°)"]
            else:
                return False, [f"Sun altitude {self._sun_altitude:.1f}° - waiting for < {clear_threshold:.0f}°"]
        else:
            # Currently night - trigger if sun rises above threshold
            if self._sun_altitude > self.thresholds.twilight_altitude:
                self._daylight_triggered = True
                return False, [f"Sun altitude {self._sun_altitude:.1f}° - not astronomical night"]

        return True, []

    def evaluate(self) -> SafetyStatus:
        """
        Perform comprehensive safety evaluation.

        Returns:
            SafetyStatus with current assessment
        """
        reasons = []

        # Evaluate each subsystem
        weather_ok, weather_reasons = self._evaluate_weather()
        clouds_ok, cloud_reasons = self._evaluate_clouds()
        daylight_ok, daylight_reasons = self._evaluate_daylight()

        reasons.extend(weather_reasons)
        reasons.extend(cloud_reasons)
        reasons.extend(daylight_reasons)

        # Determine overall safety and action
        is_safe = weather_ok and clouds_ok and daylight_ok

        # Check for emergency conditions (rain)
        is_emergency = False
        if self._weather_data and self._weather_data.is_valid:
            data = self._weather_data.value
            if hasattr(data, 'is_raining') and data.is_raining:
                is_emergency = True
            elif hasattr(data, 'rain_rate_in_hr') and data.rain_rate_in_hr > 0:
                is_emergency = True

        # Determine action
        if is_emergency:
            action = SafetyAction.EMERGENCY_CLOSE
            alert_level = AlertLevel.EMERGENCY
        elif not daylight_ok:
            action = SafetyAction.PARK_FOR_DAYLIGHT
            alert_level = AlertLevel.INFO
        elif not weather_ok or not clouds_ok:
            action = SafetyAction.PARK_AND_WAIT
            alert_level = AlertLevel.WARNING
        else:
            action = SafetyAction.SAFE_TO_OBSERVE
            alert_level = AlertLevel.INFO

        # Extract readings for status
        temp = None
        humidity = None
        wind = None
        if self._weather_data and self._weather_data.is_valid:
            data = self._weather_data.value
            temp = getattr(data, 'temperature_f', None)
            humidity = getattr(data, 'humidity_percent', None)
            wind = getattr(data, 'wind_speed_mph', None)

        cloud_cover = None
        if self._cloud_data and self._cloud_data.is_valid:
            # Convert sky diff to approximate cloud percentage
            sky_diff = self._cloud_data.value
            if sky_diff < -25:
                cloud_cover = 0
            elif sky_diff > -5:
                cloud_cover = 100
            else:
                cloud_cover = ((sky_diff + 25) / 20) * 100

        status = SafetyStatus(
            timestamp=datetime.now(),
            action=action,
            is_safe=is_safe,
            reasons=reasons if reasons else ["All systems nominal"],
            alert_level=alert_level,
            weather_ok=weather_ok,
            clouds_ok=clouds_ok,
            daylight_ok=daylight_ok,
            mount_ok=True,  # Would check mount status here
            temperature_f=temp,
            humidity_percent=humidity,
            wind_speed_mph=wind,
            cloud_cover_percent=cloud_cover,
            sun_altitude_deg=self._sun_altitude
        )

        self._last_status = status
        return status

    async def execute_action(self, action: SafetyAction):
        """Execute a safety action on the mount."""
        if not self.mount:
            logger.warning("No mount controller configured")
            return

        try:
            if action == SafetyAction.EMERGENCY_CLOSE:
                logger.critical("EMERGENCY CLOSE - Parking immediately!")
                self._state = ObservatoryState.EMERGENCY
                self.mount.stop()
                self.mount.park()

            elif action == SafetyAction.PARK_AND_WAIT:
                logger.warning("Unsafe conditions - Parking telescope")
                self._state = ObservatoryState.PARKING
                self.mount.stop()
                self.mount.park()

            elif action == SafetyAction.PARK_FOR_DAYLIGHT:
                logger.info("Daylight approaching - Parking for day")
                self._state = ObservatoryState.PARKING
                self.mount.park()

            elif action == SafetyAction.SAFE_TO_OBSERVE:
                if self._state in [ObservatoryState.PARKED, ObservatoryState.CLOSED]:
                    logger.info("Conditions safe - Ready to observe")
                    self._state = ObservatoryState.OPEN_IDLE

        except Exception as e:
            logger.error(f"Failed to execute safety action: {e}")

    async def _notify_callbacks(self, status: SafetyStatus):
        """Notify registered callbacks of status change."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(status)
                else:
                    callback(status)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    async def run(self, poll_interval: float = 10.0):
        """
        Main monitoring loop.

        Args:
            poll_interval: Seconds between safety evaluations
        """
        logger.info("Safety monitor started")
        self._running = True

        last_action = None

        while self._running:
            try:
                # Evaluate current conditions
                status = self.evaluate()

                # Track unsafe duration
                if not status.is_safe:
                    if self._unsafe_since is None:
                        self._unsafe_since = datetime.now()
                    self._safe_since = None
                else:
                    if self._safe_since is None:
                        self._safe_since = datetime.now()
                    self._unsafe_since = None

                # Execute action if conditions warrant
                if status.action != SafetyAction.SAFE_TO_OBSERVE:
                    # Check if unsafe long enough to act
                    if self._unsafe_since:
                        unsafe_duration = (datetime.now() - self._unsafe_since).total_seconds()
                        if unsafe_duration > self.thresholds.unsafe_duration_to_park:
                            await self.execute_action(status.action)

                elif status.action == SafetyAction.SAFE_TO_OBSERVE and last_action != SafetyAction.SAFE_TO_OBSERVE:
                    # Check if safe long enough to resume
                    if self._safe_since:
                        safe_duration = (datetime.now() - self._safe_since).total_seconds()
                        if safe_duration > self.thresholds.safe_duration_to_resume:
                            await self.execute_action(status.action)

                # Notify callbacks if action changed
                if status.action != last_action:
                    await self._notify_callbacks(status)
                    last_action = status.action

                # Log status periodically
                if status.alert_level in [AlertLevel.WARNING, AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
                    logger.warning(f"Safety: {status.action.value} - {'; '.join(status.reasons)}")

            except Exception as e:
                logger.error(f"Safety monitor error: {e}")

            await asyncio.sleep(poll_interval)

    def stop(self):
        """Stop the monitoring loop."""
        self._running = False
        logger.info("Safety monitor stopped")


# =============================================================================
# CONVENIENCE CLASS
# =============================================================================

class NightwatchSafetySystem:
    """
    High-level safety system for NIGHTWATCH observatory.

    Combines all safety components into a single interface.
    """

    def __init__(self):
        self.thresholds = SafetyThresholds()
        self.monitor = SafetyMonitor(thresholds=self.thresholds)
        self._tasks = []

    async def start(self):
        """Start all safety monitoring."""
        # Would start weather polling, cloud sensor polling, etc.
        monitor_task = asyncio.create_task(self.monitor.run())
        self._tasks.append(monitor_task)

    async def stop(self):
        """Stop all safety monitoring."""
        self.monitor.stop()
        for task in self._tasks:
            task.cancel()

    def is_safe(self) -> bool:
        """Quick check if observing is currently safe."""
        if self.monitor.last_status:
            return self.monitor.last_status.is_safe
        return False


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    async def test():
        monitor = SafetyMonitor()

        # Simulate weather data
        class MockWeather:
            is_raining = False
            rain_rate_in_hr = 0.0
            wind_speed_mph = 5.0
            wind_gust_mph = 8.0
            humidity_percent = 45.0
            temperature_f = 55.0

        await monitor.update_weather(MockWeather())
        await monitor.update_sun_altitude(-18.0)  # Night

        status = monitor.evaluate()
        print(f"Safe: {status.is_safe}")
        print(f"Action: {status.action.value}")
        print(f"Reasons: {status.reasons}")

    asyncio.run(test())
