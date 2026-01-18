"""
NIGHTWATCH Ephemeris Service

Provides astronomical calculations using Skyfield library.
"""

from .skyfield_service import (
    EphemerisService,
    CelestialBody,
    TwilightPhase,
    Position,
    HorizontalPosition,
    RiseTransitSet,
    ObserverLocation,
    get_service,
    planet_position,
    is_dark,
    sun_altitude,
)

__all__ = [
    "EphemerisService",
    "CelestialBody",
    "TwilightPhase",
    "Position",
    "HorizontalPosition",
    "RiseTransitSet",
    "ObserverLocation",
    "get_service",
    "planet_position",
    "is_dark",
    "sun_altitude",
]
