"""
NIGHTWATCH Mount Control Service

Provides LX200 protocol communication with OnStepX controller,
including extended OnStepX commands for PEC and driver diagnostics.
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

from .onstepx_extended import (
    OnStepXExtended,
    PECStatus,
    DriverStatus,
    create_onstepx_extended,
)

__all__ = [
    # LX200 base client
    "LX200Client",
    "ConnectionType",
    "PierSide",
    "TrackingRate",
    "MountStatus",
    "ra_to_hours",
    "dec_to_degrees",
    "hours_to_ra",
    "degrees_to_dec",
    # OnStepX extended
    "OnStepXExtended",
    "PECStatus",
    "DriverStatus",
    "create_onstepx_extended",
]
