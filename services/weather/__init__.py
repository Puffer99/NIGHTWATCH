"""
NIGHTWATCH Weather Service

Provides weather data integration from multiple sources:
- Ecowitt WS90 weather station (ground weather)
- AAG CloudWatcher Solo (cloud/sky conditions)
- Unified interface combining both sources
"""

from .ecowitt import (
    EcowittClient,
    WeatherData,
    WeatherCondition,
    WindCondition,
)
from .cloudwatcher import (
    CloudWatcherClient,
    CloudWatcherData,
    CloudCondition,
    RainCondition,
    DaylightCondition,
    CloudThresholds,
)
from .unified import (
    UnifiedWeatherService,
    UnifiedConditions,
    SafetyLevel,
    create_weather_service,
)

__all__ = [
    # Ecowitt
    "EcowittClient",
    "WeatherData",
    "WeatherCondition",
    "WindCondition",
    # CloudWatcher
    "CloudWatcherClient",
    "CloudWatcherData",
    "CloudCondition",
    "RainCondition",
    "DaylightCondition",
    "CloudThresholds",
    # Unified
    "UnifiedWeatherService",
    "UnifiedConditions",
    "SafetyLevel",
    "create_weather_service",
]
