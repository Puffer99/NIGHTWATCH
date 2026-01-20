"""
NIGHTWATCH Weather Simulator

Simulates weather station data with configurable scenarios.
Supports Ecowitt-style API responses.

Step 527: Configurable weather scenarios (clear, cloudy, rain, etc.)
"""

import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

from . import BaseSimulator, SimulatorConfig


class WeatherScenario(Enum):
    """Pre-defined weather scenarios (Step 527)."""
    CLEAR = "clear"              # Perfect observing conditions
    PARTLY_CLOUDY = "partly_cloudy"  # Some clouds
    CLOUDY = "cloudy"            # Overcast
    RAIN = "rain"                # Raining
    STORM = "storm"              # Thunderstorm
    WINDY = "windy"              # High winds
    HUMID = "humid"              # High humidity
    COLD = "cold"                # Very cold
    HOT = "hot"                  # Very hot
    CUSTOM = "custom"            # User-defined values


@dataclass
class WeatherConditions:
    """Current weather conditions."""
    temperature_c: float = 15.0
    humidity_percent: float = 50.0
    pressure_hpa: float = 1013.25
    wind_speed_kph: float = 5.0
    wind_gust_kph: float = 8.0
    wind_direction_deg: float = 180.0
    rain_mm: float = 0.0
    rain_rate_mmh: float = 0.0
    cloud_cover_percent: float = 0.0
    dew_point_c: float = 5.0
    sky_quality: float = 21.0  # mag/arcsec^2 (darker is better)
    seeing_arcsec: float = 2.0


@dataclass
class WeatherSimulatorConfig(SimulatorConfig):
    """Configuration for weather simulator."""
    # Initial scenario
    scenario: WeatherScenario = WeatherScenario.CLEAR

    # Variation settings
    add_noise: bool = True
    noise_amplitude: float = 0.1  # Fraction of value

    # Update interval
    update_interval_sec: float = 60.0

    # Safety thresholds (for testing safety logic)
    safe_humidity_max: float = 85.0
    safe_wind_max_kph: float = 40.0
    safe_rain_max_mmh: float = 0.0


class WeatherSimulator(BaseSimulator):
    """
    Simulated weather station (Step 527).

    Features:
    - Pre-defined weather scenarios
    - Configurable conditions
    - Realistic variation
    - Safety threshold support
    """

    # Scenario definitions (Step 527)
    SCENARIO_PRESETS: Dict[WeatherScenario, Dict[str, Any]] = {
        WeatherScenario.CLEAR: {
            "temperature_c": 15.0,
            "humidity_percent": 45.0,
            "wind_speed_kph": 5.0,
            "cloud_cover_percent": 0.0,
            "rain_rate_mmh": 0.0,
            "sky_quality": 21.5,
            "seeing_arcsec": 1.5,
        },
        WeatherScenario.PARTLY_CLOUDY: {
            "temperature_c": 14.0,
            "humidity_percent": 55.0,
            "wind_speed_kph": 10.0,
            "cloud_cover_percent": 40.0,
            "rain_rate_mmh": 0.0,
            "sky_quality": 19.5,
            "seeing_arcsec": 2.5,
        },
        WeatherScenario.CLOUDY: {
            "temperature_c": 12.0,
            "humidity_percent": 70.0,
            "wind_speed_kph": 15.0,
            "cloud_cover_percent": 90.0,
            "rain_rate_mmh": 0.0,
            "sky_quality": 17.0,
            "seeing_arcsec": 4.0,
        },
        WeatherScenario.RAIN: {
            "temperature_c": 10.0,
            "humidity_percent": 95.0,
            "wind_speed_kph": 20.0,
            "cloud_cover_percent": 100.0,
            "rain_rate_mmh": 5.0,
            "sky_quality": 15.0,
            "seeing_arcsec": 10.0,
        },
        WeatherScenario.STORM: {
            "temperature_c": 8.0,
            "humidity_percent": 98.0,
            "wind_speed_kph": 50.0,
            "cloud_cover_percent": 100.0,
            "rain_rate_mmh": 25.0,
            "sky_quality": 12.0,
            "seeing_arcsec": 20.0,
        },
        WeatherScenario.WINDY: {
            "temperature_c": 12.0,
            "humidity_percent": 40.0,
            "wind_speed_kph": 45.0,
            "cloud_cover_percent": 20.0,
            "rain_rate_mmh": 0.0,
            "sky_quality": 20.0,
            "seeing_arcsec": 4.0,
        },
        WeatherScenario.HUMID: {
            "temperature_c": 20.0,
            "humidity_percent": 90.0,
            "wind_speed_kph": 5.0,
            "cloud_cover_percent": 30.0,
            "rain_rate_mmh": 0.0,
            "sky_quality": 19.0,
            "seeing_arcsec": 3.0,
        },
        WeatherScenario.COLD: {
            "temperature_c": -10.0,
            "humidity_percent": 30.0,
            "wind_speed_kph": 10.0,
            "cloud_cover_percent": 10.0,
            "rain_rate_mmh": 0.0,
            "sky_quality": 22.0,
            "seeing_arcsec": 1.0,
        },
        WeatherScenario.HOT: {
            "temperature_c": 35.0,
            "humidity_percent": 25.0,
            "wind_speed_kph": 5.0,
            "cloud_cover_percent": 5.0,
            "rain_rate_mmh": 0.0,
            "sky_quality": 20.5,
            "seeing_arcsec": 3.0,
        },
    }

    def __init__(self, config: Optional[WeatherSimulatorConfig] = None):
        super().__init__(config or WeatherSimulatorConfig(name="weather_simulator"))
        self.weather_config = config or WeatherSimulatorConfig(name="weather_simulator")

        self._conditions = WeatherConditions()
        self._scenario = self.weather_config.scenario
        self._last_update = datetime.now()

        # Apply initial scenario
        self.set_scenario(self._scenario)

    @property
    def scenario(self) -> WeatherScenario:
        """Get current weather scenario."""
        return self._scenario

    @property
    def conditions(self) -> WeatherConditions:
        """Get current weather conditions."""
        return self._conditions

    def set_scenario(self, scenario: WeatherScenario) -> None:
        """
        Set weather scenario (Step 527).

        Args:
            scenario: Weather scenario to apply
        """
        self._scenario = scenario

        if scenario == WeatherScenario.CUSTOM:
            return  # Keep current values

        preset = self.SCENARIO_PRESETS.get(scenario, {})

        # Apply preset values
        self._conditions.temperature_c = preset.get("temperature_c", 15.0)
        self._conditions.humidity_percent = preset.get("humidity_percent", 50.0)
        self._conditions.wind_speed_kph = preset.get("wind_speed_kph", 5.0)
        self._conditions.cloud_cover_percent = preset.get("cloud_cover_percent", 0.0)
        self._conditions.rain_rate_mmh = preset.get("rain_rate_mmh", 0.0)
        self._conditions.sky_quality = preset.get("sky_quality", 21.0)
        self._conditions.seeing_arcsec = preset.get("seeing_arcsec", 2.0)

        # Calculate derived values
        self._update_derived_values()

    def set_conditions(self, **kwargs) -> None:
        """
        Set individual weather conditions.

        Args:
            **kwargs: Condition name-value pairs
        """
        for key, value in kwargs.items():
            if hasattr(self._conditions, key):
                setattr(self._conditions, key, value)

        self._scenario = WeatherScenario.CUSTOM
        self._update_derived_values()

    def _update_derived_values(self) -> None:
        """Update calculated weather values."""
        # Calculate dew point using Magnus formula
        T = self._conditions.temperature_c
        RH = self._conditions.humidity_percent

        if RH > 0:
            a, b = 17.27, 237.7
            alpha = ((a * T) / (b + T)) + (RH / 100.0)
            self._conditions.dew_point_c = (b * alpha) / (a - alpha)
        else:
            self._conditions.dew_point_c = T - 20

        # Set wind gust (typically 1.5x wind speed)
        self._conditions.wind_gust_kph = self._conditions.wind_speed_kph * 1.5

    def _add_variation(self) -> None:
        """Add realistic variation to readings."""
        if not self.weather_config.add_noise:
            return

        amp = self.weather_config.noise_amplitude

        self._conditions.temperature_c += random.gauss(0, amp * 2)
        self._conditions.humidity_percent += random.gauss(0, amp * 5)
        self._conditions.humidity_percent = max(0, min(100, self._conditions.humidity_percent))
        self._conditions.wind_speed_kph += random.gauss(0, amp * 3)
        self._conditions.wind_speed_kph = max(0, self._conditions.wind_speed_kph)

    def update(self) -> None:
        """Update weather readings with variation."""
        self._add_variation()
        self._update_derived_values()
        self._last_update = datetime.now()

    def is_safe(self) -> bool:
        """Check if conditions are safe for observing."""
        config = self.weather_config

        if self._conditions.humidity_percent > config.safe_humidity_max:
            return False
        if self._conditions.wind_speed_kph > config.safe_wind_max_kph:
            return False
        if self._conditions.rain_rate_mmh > config.safe_rain_max_mmh:
            return False

        return True

    def get_safety_status(self) -> Dict[str, Any]:
        """Get detailed safety status."""
        config = self.weather_config

        return {
            "is_safe": self.is_safe(),
            "humidity_safe": self._conditions.humidity_percent <= config.safe_humidity_max,
            "wind_safe": self._conditions.wind_speed_kph <= config.safe_wind_max_kph,
            "rain_safe": self._conditions.rain_rate_mmh <= config.safe_rain_max_mmh,
            "thresholds": {
                "humidity_max": config.safe_humidity_max,
                "wind_max_kph": config.safe_wind_max_kph,
                "rain_max_mmh": config.safe_rain_max_mmh,
            },
        }

    def get_conditions(self) -> Dict[str, Any]:
        """Get current weather conditions."""
        return {
            "scenario": self._scenario.value,
            "temperature_c": round(self._conditions.temperature_c, 1),
            "humidity_percent": round(self._conditions.humidity_percent, 1),
            "pressure_hpa": round(self._conditions.pressure_hpa, 1),
            "wind_speed_kph": round(self._conditions.wind_speed_kph, 1),
            "wind_gust_kph": round(self._conditions.wind_gust_kph, 1),
            "wind_direction_deg": round(self._conditions.wind_direction_deg, 0),
            "rain_mm": round(self._conditions.rain_mm, 1),
            "rain_rate_mmh": round(self._conditions.rain_rate_mmh, 1),
            "cloud_cover_percent": round(self._conditions.cloud_cover_percent, 0),
            "dew_point_c": round(self._conditions.dew_point_c, 1),
            "sky_quality": round(self._conditions.sky_quality, 2),
            "seeing_arcsec": round(self._conditions.seeing_arcsec, 1),
            "is_safe": self.is_safe(),
            "last_update": self._last_update.isoformat(),
        }

    def get_ecowitt_response(self) -> Dict[str, Any]:
        """Get Ecowitt-compatible API response."""
        return {
            "outdoor": {
                "temperature": {"value": self._conditions.temperature_c, "unit": "C"},
                "humidity": {"value": self._conditions.humidity_percent, "unit": "%"},
                "dew_point": {"value": self._conditions.dew_point_c, "unit": "C"},
            },
            "wind": {
                "wind_speed": {"value": self._conditions.wind_speed_kph, "unit": "km/h"},
                "wind_gust": {"value": self._conditions.wind_gust_kph, "unit": "km/h"},
                "wind_direction": {"value": self._conditions.wind_direction_deg, "unit": "deg"},
            },
            "rainfall": {
                "rain_rate": {"value": self._conditions.rain_rate_mmh, "unit": "mm/h"},
                "daily": {"value": self._conditions.rain_mm, "unit": "mm"},
            },
            "pressure": {
                "relative": {"value": self._conditions.pressure_hpa, "unit": "hPa"},
            },
        }
