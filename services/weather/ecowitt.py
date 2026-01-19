"""
NIGHTWATCH Weather Service
Ecowitt WS90 Weather Station Integration

This module provides weather data from the Ecowitt WS90 weather station
for use in observatory automation and safety decisions.

The WS90 features:
- Ultrasonic wind sensor (no moving parts)
- Integrated rain gauge
- Temperature/humidity sensor
- Solar radiation sensor
- WiFi connectivity with local API
"""

import aiohttp
import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
import json


class WeatherCondition(Enum):
    """Overall weather condition assessment."""
    EXCELLENT = "excellent"      # Clear, calm, low humidity
    GOOD = "good"                # Suitable for observing
    MARGINAL = "marginal"        # Proceed with caution
    POOR = "poor"                # Not recommended
    DANGEROUS = "dangerous"      # Close immediately


class WindCondition(Enum):
    """Wind condition for telescope operation."""
    CALM = "calm"           # < 5 mph
    LIGHT = "light"         # 5-15 mph
    MODERATE = "moderate"   # 15-25 mph
    STRONG = "strong"       # > 25 mph (unsafe)


@dataclass
class WeatherData:
    """Current weather conditions from WS90 station."""
    timestamp: datetime

    # Temperature (Step 205)
    temperature_f: float
    temperature_c: float
    feels_like_f: float
    dew_point_f: float
    ambient_temperature_c: float = 0.0  # Raw ambient sensor

    # Humidity
    humidity_percent: float

    # Wind
    wind_speed_mph: float
    wind_gust_mph: float
    wind_direction_deg: int
    wind_direction_str: str

    # Rain (Step 204)
    rain_rate_in_hr: float
    rain_daily_in: float
    rain_event_in: float
    is_raining: bool
    rain_sensor_status: str = "ok"  # Sensor health status

    # Solar
    solar_radiation_wm2: float
    uv_index: float

    # Pressure
    pressure_inhg: float
    pressure_trend: str

    # Sky Quality (Step 203)
    sky_quality_mpsas: Optional[float] = None  # Mag per square arcsec
    sky_brightness: Optional[str] = None  # "excellent", "good", "fair", "poor"

    # Derived
    condition: WeatherCondition
    wind_condition: WindCondition
    safe_to_observe: bool


class EcowittClient:
    """
    Client for Ecowitt weather station local API.

    The Ecowitt gateway provides a local HTTP API for accessing
    real-time weather data without cloud dependency.
    """

    # Safety thresholds for observatory operation
    WIND_LIMIT_MPH = 25.0       # Park telescope above this
    GUST_LIMIT_MPH = 35.0       # Emergency close
    HUMIDITY_LIMIT = 85.0       # Dew risk
    TEMP_MIN_F = 20.0           # Cold operation limit
    RAIN_THRESHOLD = 0.0        # Any rain is unsafe

    def __init__(
        self,
        gateway_ip: str = "192.168.1.50",
        gateway_port: int = 80,
        poll_interval: float = 30.0
    ):
        """
        Initialize Ecowitt client.

        Args:
            gateway_ip: IP address of Ecowitt gateway/console
            gateway_port: HTTP port (usually 80)
            poll_interval: Seconds between automatic polls
        """
        self.gateway_ip = gateway_ip
        self.gateway_port = gateway_port
        self.poll_interval = poll_interval
        self._base_url = f"http://{gateway_ip}:{gateway_port}"
        self._latest_data: Optional[WeatherData] = None
        self._callbacks = []

    async def fetch_data(self) -> Optional[WeatherData]:
        """
        Fetch current weather data from gateway.

        Returns:
            WeatherData object or None if fetch fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Ecowitt local API endpoint
                url = f"{self._base_url}/get_livedata_info"

                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_response(data)
                    else:
                        print(f"Weather API error: {response.status}")
                        return None
        except Exception as e:
            print(f"Weather fetch failed: {e}")
            return None

    def _parse_response(self, data: dict) -> WeatherData:
        """Parse Ecowitt API response into WeatherData."""
        # Extract common fields (structure varies by firmware version)
        common = data.get("common_list", [])
        rain = data.get("rain", {})
        wind = data.get("wh80batt", {}) or data.get("wind", {})

        # Helper to find value in common list
        def get_common(key: str, default=0.0):
            for item in common:
                if item.get("id") == key:
                    return float(item.get("val", default))
            return default

        # Parse temperature
        temp_f = get_common("0x02", 70.0)
        temp_c = (temp_f - 32) * 5 / 9

        # Parse humidity
        humidity = get_common("0x07", 50.0)

        # Calculate dew point
        dew_point_f = self._calculate_dew_point(temp_f, humidity)

        # Calculate feels like
        feels_like_f = self._calculate_feels_like(
            temp_f,
            get_common("0x0B", 0.0),  # wind speed
            humidity
        )

        # Parse wind
        wind_speed = get_common("0x0B", 0.0)
        wind_gust = get_common("0x0C", 0.0)
        wind_dir = int(get_common("0x0A", 0))
        wind_dir_str = self._wind_direction_to_string(wind_dir)

        # Parse rain
        rain_rate = float(rain.get("rain_rate", {}).get("val", 0))
        rain_daily = float(rain.get("daily", {}).get("val", 0))
        rain_event = float(rain.get("event", {}).get("val", 0))
        is_raining = rain_rate > 0

        # Parse solar/UV
        solar = get_common("0x15", 0.0)
        uv_index = get_common("0x17", 0.0)

        # Parse pressure
        pressure = get_common("0x03", 29.92)

        # Assess conditions
        wind_condition = self._assess_wind(wind_speed, wind_gust)
        condition = self._assess_overall(
            temp_f, humidity, wind_speed, wind_gust, rain_rate
        )
        safe = self._is_safe_to_observe(
            temp_f, humidity, wind_speed, wind_gust, rain_rate
        )

        weather = WeatherData(
            timestamp=datetime.now(),
            temperature_f=temp_f,
            temperature_c=temp_c,
            feels_like_f=feels_like_f,
            dew_point_f=dew_point_f,
            humidity_percent=humidity,
            wind_speed_mph=wind_speed,
            wind_gust_mph=wind_gust,
            wind_direction_deg=wind_dir,
            wind_direction_str=wind_dir_str,
            rain_rate_in_hr=rain_rate,
            rain_daily_in=rain_daily,
            rain_event_in=rain_event,
            is_raining=is_raining,
            solar_radiation_wm2=solar,
            uv_index=uv_index,
            pressure_inhg=pressure,
            pressure_trend="steady",  # Would need historical data
            condition=condition,
            wind_condition=wind_condition,
            safe_to_observe=safe
        )

        self._latest_data = weather
        return weather

    def _calculate_dew_point(self, temp_f: float, humidity: float) -> float:
        """Calculate dew point using Magnus formula."""
        temp_c = (temp_f - 32) * 5 / 9
        a = 17.27
        b = 237.7
        alpha = ((a * temp_c) / (b + temp_c)) + (humidity / 100.0)
        dew_c = (b * alpha) / (a - alpha)
        return dew_c * 9 / 5 + 32

    def _calculate_feels_like(
        self,
        temp_f: float,
        wind_mph: float,
        humidity: float
    ) -> float:
        """Calculate feels-like temperature (wind chill or heat index)."""
        if temp_f <= 50 and wind_mph >= 3:
            # Wind chill formula
            return (
                35.74 + 0.6215 * temp_f
                - 35.75 * (wind_mph ** 0.16)
                + 0.4275 * temp_f * (wind_mph ** 0.16)
            )
        elif temp_f >= 80:
            # Heat index (simplified)
            return temp_f + 0.5 * (humidity - 40) * 0.1
        return temp_f

    def _wind_direction_to_string(self, degrees: int) -> str:
        """Convert wind direction degrees to compass string."""
        directions = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
        ]
        index = round(degrees / 22.5) % 16
        return directions[index]

    def _assess_wind(
        self,
        speed: float,
        gust: float
    ) -> WindCondition:
        """Assess wind condition for telescope operation."""
        max_wind = max(speed, gust)
        if max_wind < 5:
            return WindCondition.CALM
        elif max_wind < 15:
            return WindCondition.LIGHT
        elif max_wind < 25:
            return WindCondition.MODERATE
        else:
            return WindCondition.STRONG

    def _assess_overall(
        self,
        temp_f: float,
        humidity: float,
        wind_speed: float,
        wind_gust: float,
        rain_rate: float
    ) -> WeatherCondition:
        """Assess overall weather condition."""
        if rain_rate > 0:
            return WeatherCondition.DANGEROUS

        if wind_gust > self.GUST_LIMIT_MPH:
            return WeatherCondition.DANGEROUS

        if wind_speed > self.WIND_LIMIT_MPH:
            return WeatherCondition.POOR

        if humidity > self.HUMIDITY_LIMIT:
            return WeatherCondition.MARGINAL

        if temp_f < self.TEMP_MIN_F:
            return WeatherCondition.MARGINAL

        if wind_speed < 10 and humidity < 70 and temp_f > 40:
            return WeatherCondition.EXCELLENT

        return WeatherCondition.GOOD

    def _is_safe_to_observe(
        self,
        temp_f: float,
        humidity: float,
        wind_speed: float,
        wind_gust: float,
        rain_rate: float
    ) -> bool:
        """Determine if conditions are safe for observation."""
        if rain_rate > self.RAIN_THRESHOLD:
            return False
        if wind_speed > self.WIND_LIMIT_MPH:
            return False
        if wind_gust > self.GUST_LIMIT_MPH:
            return False
        if humidity > self.HUMIDITY_LIMIT:
            return False
        if temp_f < self.TEMP_MIN_F:
            return False
        return True

    @property
    def latest(self) -> Optional[WeatherData]:
        """Get most recently fetched weather data."""
        return self._latest_data

    def register_callback(self, callback):
        """Register callback for weather updates."""
        self._callbacks.append(callback)

    # =========================================================================
    # Individual Sensor Readings (Steps 203-205)
    # =========================================================================

    def get_sky_quality(self) -> Optional[float]:
        """
        Get sky quality meter reading (Step 203).

        Returns:
            Sky quality in magnitudes per square arcsecond (MPSAS),
            or None if not available.

        Note:
            Ecowitt stations don't include SQM sensors. This method
            returns None unless an external SQM is integrated.
            Typical dark sky values:
            - 21.5+ MPSAS: Excellent (Bortle 1-2)
            - 20.5-21.5: Good (Bortle 3-4)
            - 19.5-20.5: Fair (Bortle 5-6)
            - <19.5: Poor (Bortle 7+)
        """
        if self._latest_data:
            return self._latest_data.sky_quality_mpsas
        return None

    def get_sky_brightness_category(self) -> Optional[str]:
        """
        Get sky brightness category based on SQM reading (Step 203).

        Returns:
            Category string: "excellent", "good", "fair", "poor", or None
        """
        sqm = self.get_sky_quality()
        if sqm is None:
            return None
        if sqm >= 21.5:
            return "excellent"
        elif sqm >= 20.5:
            return "good"
        elif sqm >= 19.5:
            return "fair"
        else:
            return "poor"

    def get_rain_sensor_reading(self) -> dict:
        """
        Get detailed rain sensor data (Step 204).

        Returns:
            Dict with rain_rate, daily_total, event_total, is_raining, sensor_status
        """
        if not self._latest_data:
            return {
                "rain_rate_in_hr": 0.0,
                "rain_daily_in": 0.0,
                "rain_event_in": 0.0,
                "is_raining": False,
                "sensor_status": "no_data",
            }

        return {
            "rain_rate_in_hr": self._latest_data.rain_rate_in_hr,
            "rain_daily_in": self._latest_data.rain_daily_in,
            "rain_event_in": self._latest_data.rain_event_in,
            "is_raining": self._latest_data.is_raining,
            "sensor_status": self._latest_data.rain_sensor_status,
        }

    def is_rain_detected(self) -> bool:
        """
        Check if rain is currently detected (Step 204).

        Returns:
            True if rain rate > 0 or recent rain event detected
        """
        if not self._latest_data:
            return False
        return self._latest_data.is_raining

    def get_ambient_temperature(self) -> Optional[float]:
        """
        Get ambient temperature reading in Celsius (Step 205).

        Returns:
            Temperature in Celsius, or None if unavailable
        """
        if self._latest_data:
            return self._latest_data.temperature_c
        return None

    def get_ambient_temperature_f(self) -> Optional[float]:
        """
        Get ambient temperature reading in Fahrenheit (Step 205).

        Returns:
            Temperature in Fahrenheit, or None if unavailable
        """
        if self._latest_data:
            return self._latest_data.temperature_f
        return None

    def get_temperature_trend(self) -> Optional[str]:
        """
        Get temperature trend (Step 205).

        Returns:
            "rising", "falling", "stable", or None

        Note:
            Requires historical data; currently returns None.
            Future: compare with data from 30 minutes ago.
        """
        # TODO: Implement temperature history tracking
        return None

    def is_dew_risk(self) -> bool:
        """
        Check if there's risk of dew formation (Step 205).

        Returns:
            True if temperature is within 3°F of dew point
        """
        if not self._latest_data:
            return False
        temp = self._latest_data.temperature_f
        dew = self._latest_data.dew_point_f
        return (temp - dew) < 3.0

    async def start_polling(self):
        """Start background polling of weather data."""
        while True:
            data = await self.fetch_data()
            if data:
                for callback in self._callbacks:
                    try:
                        await callback(data)
                    except Exception as e:
                        print(f"Weather callback error: {e}")
            await asyncio.sleep(self.poll_interval)


# =============================================================================
# MAIN (for testing)
# =============================================================================

async def main():
    """Test weather service."""
    client = EcowittClient(gateway_ip="192.168.1.50")

    # Single fetch
    data = await client.fetch_data()
    if data:
        print(f"Temperature: {data.temperature_f:.1f}°F")
        print(f"Humidity: {data.humidity_percent:.1f}%")
        print(f"Wind: {data.wind_speed_mph:.1f} mph from {data.wind_direction_str}")
        print(f"Condition: {data.condition.value}")
        print(f"Safe to observe: {data.safe_to_observe}")
    else:
        print("Failed to fetch weather data")


if __name__ == "__main__":
    asyncio.run(main())
