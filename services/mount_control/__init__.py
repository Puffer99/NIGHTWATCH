"""
NIGHTWATCH Mount Control Service

Provides LX200 protocol communication with OnStepX controller.
"""

from .lx200 import (
    LX200Client,
    ConnectionType,
    PierSide,
    TrackingRate,
    MountStatus,
    ra_to_hours,
    dec_to_degrees,
    hours_to_ra,
    degrees_to_dec,
)

__all__ = [
    "LX200Client",
    "ConnectionType",
    "PierSide",
    "TrackingRate",
    "MountStatus",
    "ra_to_hours",
    "dec_to_degrees",
    "hours_to_ra",
    "degrees_to_dec",
]
