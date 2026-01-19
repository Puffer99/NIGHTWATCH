"""
Mock Weather Service for Testing.

Simulates weather station behavior for unit and integration testing.
Provides configurable weather conditions and scenario injection.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, List

logger = logging.getLogger("NIGHTWATCH.fixtures.MockWeather")


class WeatherCondition(Enum):
    """Overall weather condition categories."""
    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    RAIN = "rain"
    STORM = "storm"
    UNKNOWN = "unknown"


@dataclass
class MockWeatherConditions:
    """
    Current weather conditions.

    Based on Ecowitt WS90 and AAG CloudWatcher parameters.
    """
    # Temperature
    temperature_c: float = 15.0
    dew_point_c: float = 8.0
    humidity_percent: float = 60.0

    # Wind
    wind_speed_ms: float = 2.0
    wind_gust_ms: float = 3.5
    wind_direction_deg: float = 180.0

    # Pressure
    pressure_hpa: float = 1013.25

    # Sky conditions
    cloud_cover_percent: float = 10.0
    sky_temperature_c: float = -20.0  # Clear sky is cold
    ambient_temperature_c: float = 15.0

    # Rain
    rain_rate_mmh: float = 0.0
    rain_detected: bool = False

    # Light
    light_level_lux: float = 0.0  # Night
    sqm_mag_arcsec2: float = 21.5  # Dark sky quality

    # Safety
    is_safe: bool = True
    condition: WeatherCondition = WeatherCondition.CLEAR

    # Timestamps
    timestamp: datetime = field(default_factory=datetime.now)
    last_rain_time: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "temperature_c": self.temperature_c,
            "dew_point_c": self.dew_point_c,
            "humidity_percent": self.humidity_percent,
            "wind_speed_ms": self.wind_speed_ms,
            "wind_gust_ms": self.wind_gust_ms,
            "wind_direction_deg": self.wind_direction_deg,
            "pressure_hpa": self.pressure_hpa,
            "cloud_cover_percent": self.cloud_cover_percent,
            "sky_temperature_c": self.sky_temperature_c,
            "rain_rate_mmh": self.rain_rate_mmh,
            "rain_detected": self.rain_detected,
            "is_safe": self.is_safe,
            "condition": self.condition.value,
            "timestamp": self.timestamp.isoformat(),
        }


class MockWeather:
    """
    Mock weather service for testing.

    Simulates a weather station with:
    - Configurable weather conditions
    - Preset scenarios (clear, cloudy, rainy, etc.)
    - Gradual condition changes
    - Safety state evaluation
    - Error injection for testing

    Example:
        weather = MockWeather()
        await weather.connect()
        conditions = await weather.get_conditions()
        is_safe = await weather.is_safe_for_observing()

        # Set rain scenario
        weather.set_scenario("rain")
    """

    # Safety thresholds (matching SafetyMonitor)
    WIND_LIMIT_MS = 15.0
    HUMIDITY_LIMIT = 85.0
    RAIN_RATE_LIMIT = 0.1
    CLOUD_COVER_LIMIT = 70.0

    # Preset scenarios
    SCENARIOS = {
        "clear": MockWeatherConditions(
            temperature_c=12.0,
            humidity_percent=55.0,
            wind_speed_ms=2.0,
            cloud_cover_percent=5.0,
            sky_temperature_c=-25.0,
            is_safe=True,
            condition=WeatherCondition.CLEAR,
        ),
        "partly_cloudy": MockWeatherConditions(
            temperature_c=14.0,
            humidity_percent=65.0,
            wind_speed_ms=4.0,
            cloud_cover_percent=40.0,
            sky_temperature_c=-10.0,
            is_safe=True,
            condition=WeatherCondition.PARTLY_CLOUDY,
        ),
        "cloudy": MockWeatherConditions(
            temperature_c=15.0,
            humidity_percent=75.0,
            wind_speed_ms=5.0,
            cloud_cover_percent=85.0,
            sky_temperature_c=5.0,
            is_safe=False,
            condition=WeatherCondition.CLOUDY,
        ),
        "high_wind": MockWeatherConditions(
            temperature_c=10.0,
            humidity_percent=50.0,
            wind_speed_ms=18.0,
            wind_gust_ms=25.0,
            cloud_cover_percent=20.0,
            is_safe=False,
            condition=WeatherCondition.CLEAR,
        ),
        "humid": MockWeatherConditions(
            temperature_c=18.0,
            humidity_percent=92.0,
            dew_point_c=16.5,
            wind_speed_ms=1.0,
            cloud_cover_percent=30.0,
            is_safe=False,
            condition=WeatherCondition.PARTLY_CLOUDY,
        ),
        "rain": MockWeatherConditions(
            temperature_c=16.0,
            humidity_percent=95.0,
            wind_speed_ms=6.0,
            cloud_cover_percent=100.0,
            rain_rate_mmh=5.0,
            rain_detected=True,
            is_safe=False,
            condition=WeatherCondition.RAIN,
        ),
        "storm": MockWeatherConditions(
            temperature_c=20.0,
            humidity_percent=98.0,
            wind_speed_ms=25.0,
            wind_gust_ms=35.0,
            cloud_cover_percent=100.0,
            rain_rate_mmh=20.0,
            rain_detected=True,
            is_safe=False,
            condition=WeatherCondition.STORM,
        ),
    }

    def __init__(
        self,
        initial_scenario: str = "clear",
        poll_interval_sec: float = 10.0,
    ):
        """
        Initialize mock weather service.

        Args:
            initial_scenario: Starting weather scenario
            poll_interval_sec: Simulated poll interval
        """
        self.poll_interval = poll_interval_sec
        self._connected = False
        self._conditions = self._get_scenario(initial_scenario)

        # Error injection
        self._inject_connect_error = False
        self._inject_timeout = False

        # Callbacks
        self._condition_callbacks: List[Callable] = []

        # Background polling task
        self._poll_task: Optional[asyncio.Task] = None

    def _get_scenario(self, name: str) -> MockWeatherConditions:
        """Get a copy of scenario conditions."""
        if name in self.SCENARIOS:
            scenario = self.SCENARIOS[name]
            return MockWeatherConditions(
                temperature_c=scenario.temperature_c,
                dew_point_c=scenario.dew_point_c,
                humidity_percent=scenario.humidity_percent,
                wind_speed_ms=scenario.wind_speed_ms,
                wind_gust_ms=scenario.wind_gust_ms,
                wind_direction_deg=scenario.wind_direction_deg,
                pressure_hpa=scenario.pressure_hpa,
                cloud_cover_percent=scenario.cloud_cover_percent,
                sky_temperature_c=scenario.sky_temperature_c,
                rain_rate_mmh=scenario.rain_rate_mmh,
                rain_detected=scenario.rain_detected,
                light_level_lux=scenario.light_level_lux,
                sqm_mag_arcsec2=scenario.sqm_mag_arcsec2,
                is_safe=scenario.is_safe,
                condition=scenario.condition,
            )
        else:
            logger.warning(f"Unknown scenario '{name}', using clear")
            return self._get_scenario("clear")

    @property
    def is_connected(self) -> bool:
        """Check if weather service is connected."""
        return self._connected

    async def connect(self, host: str = "localhost", port: int = 80) -> bool:
        """
        Connect to weather service.

        Args:
            host: Service host (ignored in mock)
            port: Service port (ignored in mock)

        Returns:
            True if connected successfully
        """
        if self._inject_connect_error:
            raise ConnectionError("Mock: Simulated connection failure")

        await asyncio.sleep(0.1)
        self._connected = True
        logger.info(f"MockWeather connected (host={host}, port={port})")
        return True

    async def disconnect(self):
        """Disconnect from weather service."""
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

        self._connected = False
        logger.info("MockWeather disconnected")

    async def get_conditions(self) -> MockWeatherConditions:
        """
        Get current weather conditions.

        Returns:
            Current weather conditions

        Raises:
            RuntimeError: If not connected
            TimeoutError: If timeout injection enabled
        """
        if not self._connected:
            raise RuntimeError("Weather service not connected")

        if self._inject_timeout:
            raise TimeoutError("Mock: Simulated weather timeout")

        # Update timestamp
        self._conditions.timestamp = datetime.now()
        return self._conditions

    async def is_safe_for_observing(self) -> bool:
        """
        Check if conditions are safe for observing.

        Returns:
            True if conditions are safe
        """
        conditions = await self.get_conditions()
        return conditions.is_safe

    def get_temperature(self) -> float:
        """Get current temperature in Celsius."""
        return self._conditions.temperature_c

    def get_humidity(self) -> float:
        """Get current humidity percentage."""
        return self._conditions.humidity_percent

    def get_wind_speed(self) -> float:
        """Get current wind speed in m/s."""
        return self._conditions.wind_speed_ms

    def get_cloud_cover(self) -> float:
        """Get current cloud cover percentage."""
        return self._conditions.cloud_cover_percent

    def is_raining(self) -> bool:
        """Check if rain is detected."""
        return self._conditions.rain_detected

    def set_scenario(self, name: str):
        """
        Set weather conditions from a preset scenario.

        Args:
            name: Scenario name (clear, cloudy, rain, storm, etc.)
        """
        self._conditions = self._get_scenario(name)
        self._update_safety()
        logger.info(f"MockWeather scenario set to '{name}'")

        # Notify callbacks
        self._notify_callbacks()

    def set_conditions(
        self,
        temperature_c: Optional[float] = None,
        humidity_percent: Optional[float] = None,
        wind_speed_ms: Optional[float] = None,
        wind_gust_ms: Optional[float] = None,
        cloud_cover_percent: Optional[float] = None,
        rain_rate_mmh: Optional[float] = None,
        rain_detected: Optional[bool] = None,
    ):
        """
        Set individual weather conditions.

        Args:
            temperature_c: Temperature in Celsius
            humidity_percent: Humidity percentage
            wind_speed_ms: Wind speed in m/s
            wind_gust_ms: Wind gust speed in m/s
            cloud_cover_percent: Cloud cover percentage
            rain_rate_mmh: Rain rate in mm/hour
            rain_detected: Whether rain is detected
        """
        if temperature_c is not None:
            self._conditions.temperature_c = temperature_c
        if humidity_percent is not None:
            self._conditions.humidity_percent = humidity_percent
        if wind_speed_ms is not None:
            self._conditions.wind_speed_ms = wind_speed_ms
        if wind_gust_ms is not None:
            self._conditions.wind_gust_ms = wind_gust_ms
        if cloud_cover_percent is not None:
            self._conditions.cloud_cover_percent = cloud_cover_percent
        if rain_rate_mmh is not None:
            self._conditions.rain_rate_mmh = rain_rate_mmh
        if rain_detected is not None:
            self._conditions.rain_detected = rain_detected
            if rain_detected:
                self._conditions.last_rain_time = datetime.now()

        self._update_safety()
        self._notify_callbacks()

    def _update_safety(self):
        """Update safety state based on current conditions."""
        c = self._conditions

        # Check each safety threshold
        unsafe_reasons = []

        if c.wind_speed_ms > self.WIND_LIMIT_MS:
            unsafe_reasons.append("high_wind")
        if c.humidity_percent > self.HUMIDITY_LIMIT:
            unsafe_reasons.append("high_humidity")
        if c.rain_rate_mmh > self.RAIN_RATE_LIMIT or c.rain_detected:
            unsafe_reasons.append("rain")
        if c.cloud_cover_percent > self.CLOUD_COVER_LIMIT:
            unsafe_reasons.append("clouds")

        c.is_safe = len(unsafe_reasons) == 0

        # Update overall condition
        if c.rain_detected:
            if c.wind_speed_ms > 20:
                c.condition = WeatherCondition.STORM
            else:
                c.condition = WeatherCondition.RAIN
        elif c.cloud_cover_percent > 80:
            c.condition = WeatherCondition.CLOUDY
        elif c.cloud_cover_percent > 30:
            c.condition = WeatherCondition.PARTLY_CLOUDY
        else:
            c.condition = WeatherCondition.CLEAR

    def _notify_callbacks(self):
        """Notify registered callbacks of condition change."""
        for callback in self._condition_callbacks:
            try:
                callback(self._conditions)
            except Exception as e:
                logger.error(f"Condition callback error: {e}")

    def set_condition_callback(self, callback: Callable):
        """Register callback for condition updates."""
        self._condition_callbacks.append(callback)

    # Error injection methods
    def inject_connect_error(self, enable: bool = True):
        """Enable/disable connection error injection."""
        self._inject_connect_error = enable

    def inject_timeout(self, enable: bool = True):
        """Enable/disable timeout injection."""
        self._inject_timeout = enable

    def reset(self):
        """Reset mock to initial state."""
        self._connected = False
        self._conditions = self._get_scenario("clear")
        self._inject_connect_error = False
        self._inject_timeout = False
