"""
NIGHTWATCH Mount Simulator

Simulates a telescope mount with LX200-style protocol.
Supports tracking, slewing, parking, and position reporting.

Steps 521-522: Tracking rate simulation and park/unpark state machine.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

from . import BaseSimulator, SimulatorConfig


class TrackingRate(Enum):
    """Telescope tracking rates (Step 521)."""
    SIDEREAL = "sidereal"      # 15.041 arcsec/sec
    LUNAR = "lunar"            # 14.685 arcsec/sec
    SOLAR = "solar"            # 15.0 arcsec/sec
    KING = "king"              # Sidereal + refraction correction
    CUSTOM = "custom"
    STOPPED = "stopped"


class MountState(Enum):
    """Mount state machine states (Step 522)."""
    PARKED = "parked"
    UNPARKING = "unparking"
    IDLE = "idle"
    SLEWING = "slewing"
    TRACKING = "tracking"
    PARKING = "parking"
    ERROR = "error"


@dataclass
class MountPosition:
    """Current mount position."""
    ra_hours: float = 0.0       # Right Ascension in hours (0-24)
    dec_degrees: float = 0.0    # Declination in degrees (-90 to +90)
    alt_degrees: float = 45.0   # Altitude in degrees
    az_degrees: float = 180.0   # Azimuth in degrees
    lst_hours: float = 0.0      # Local Sidereal Time


@dataclass
class MountSimulatorConfig(SimulatorConfig):
    """Configuration for mount simulator."""
    # Park position
    park_ra: float = 0.0
    park_dec: float = 90.0  # Parked at pole

    # Slew rates (degrees per second)
    slew_rate_fast: float = 3.0
    slew_rate_slow: float = 0.5

    # Tracking rates (arcsec/sec)
    sidereal_rate: float = 15.041

    # Timing
    park_time_sec: float = 10.0
    unpark_time_sec: float = 5.0

    # Location (default: Sedona, AZ)
    latitude: float = 34.8697
    longitude: float = -111.7610


class MountSimulator(BaseSimulator):
    """
    Simulated telescope mount (Steps 521-522).

    Features:
    - Sidereal/lunar/solar tracking rates
    - Park/unpark state machine
    - Realistic slew timing
    - Position simulation
    """

    def __init__(self, config: Optional[MountSimulatorConfig] = None):
        super().__init__(config or MountSimulatorConfig(name="mount_simulator"))
        self.mount_config = config or MountSimulatorConfig(name="mount_simulator")

        # State
        self._state = MountState.PARKED
        self._position = MountPosition()
        self._tracking_rate = TrackingRate.STOPPED
        self._custom_rate: float = 0.0

        # Targets
        self._target_ra: float = 0.0
        self._target_dec: float = 0.0

        # Tasks
        self._tracking_task: Optional[asyncio.Task] = None
        self._slew_task: Optional[asyncio.Task] = None

        # Initialize at park position
        self._position.ra_hours = self.mount_config.park_ra
        self._position.dec_degrees = self.mount_config.park_dec

    @property
    def state(self) -> MountState:
        """Get current mount state."""
        return self._state

    @property
    def is_parked(self) -> bool:
        """Check if mount is parked."""
        return self._state == MountState.PARKED

    @property
    def is_tracking(self) -> bool:
        """Check if mount is tracking."""
        return self._state == MountState.TRACKING

    @property
    def is_slewing(self) -> bool:
        """Check if mount is slewing."""
        return self._state == MountState.SLEWING

    async def start(self) -> bool:
        """Start the mount simulator."""
        await super().start()
        return True

    async def stop(self) -> bool:
        """Stop the mount simulator."""
        await self.stop_tracking()
        if self._slew_task:
            self._slew_task.cancel()
        await super().stop()
        return True

    # =========================================================================
    # Park/Unpark (Step 522)
    # =========================================================================

    async def park(self) -> bool:
        """
        Park the mount (Step 522).

        State transition: * -> PARKING -> PARKED
        """
        if self._state == MountState.PARKED:
            return True

        if self._state == MountState.PARKING:
            return False  # Already parking

        # Stop any current operations
        await self.stop_tracking()
        if self._slew_task:
            self._slew_task.cancel()
            self._slew_task = None

        self._state = MountState.PARKING

        # Simulate parking motion
        await asyncio.sleep(self.mount_config.park_time_sec)

        # Move to park position
        self._position.ra_hours = self.mount_config.park_ra
        self._position.dec_degrees = self.mount_config.park_dec
        self._tracking_rate = TrackingRate.STOPPED

        self._state = MountState.PARKED
        return True

    async def unpark(self) -> bool:
        """
        Unpark the mount (Step 522).

        State transition: PARKED -> UNPARKING -> IDLE
        """
        if self._state != MountState.PARKED:
            return self._state == MountState.IDLE or self._state == MountState.TRACKING

        self._state = MountState.UNPARKING

        # Simulate unpark sequence
        await asyncio.sleep(self.mount_config.unpark_time_sec)

        self._state = MountState.IDLE
        return True

    # =========================================================================
    # Tracking (Step 521)
    # =========================================================================

    async def start_tracking(self, rate: TrackingRate = TrackingRate.SIDEREAL) -> bool:
        """
        Start tracking at specified rate (Step 521).

        Args:
            rate: Tracking rate to use
        """
        if self._state == MountState.PARKED:
            return False

        if self._state == MountState.SLEWING:
            return False

        self._tracking_rate = rate
        self._state = MountState.TRACKING

        # Start tracking task
        if self._tracking_task:
            self._tracking_task.cancel()
        self._tracking_task = asyncio.create_task(self._tracking_loop())

        return True

    async def stop_tracking(self) -> bool:
        """Stop tracking."""
        if self._tracking_task:
            self._tracking_task.cancel()
            try:
                await self._tracking_task
            except asyncio.CancelledError:
                pass
            self._tracking_task = None

        self._tracking_rate = TrackingRate.STOPPED
        if self._state == MountState.TRACKING:
            self._state = MountState.IDLE

        return True

    def set_tracking_rate(self, rate: TrackingRate, custom_rate: float = 0.0) -> None:
        """
        Set tracking rate (Step 521).

        Args:
            rate: Tracking rate type
            custom_rate: Custom rate in arcsec/sec (if rate is CUSTOM)
        """
        self._tracking_rate = rate
        if rate == TrackingRate.CUSTOM:
            self._custom_rate = custom_rate

    def get_tracking_rate_value(self) -> float:
        """Get current tracking rate in arcsec/sec (Step 521)."""
        rates = {
            TrackingRate.SIDEREAL: 15.041,
            TrackingRate.LUNAR: 14.685,
            TrackingRate.SOLAR: 15.0,
            TrackingRate.KING: 15.041,  # Simplified
            TrackingRate.STOPPED: 0.0,
        }
        if self._tracking_rate == TrackingRate.CUSTOM:
            return self._custom_rate
        return rates.get(self._tracking_rate, 0.0)

    async def _tracking_loop(self) -> None:
        """Background tracking simulation (Step 521)."""
        update_interval = 1.0  # seconds

        while True:
            try:
                await asyncio.sleep(update_interval)

                if self._tracking_rate == TrackingRate.STOPPED:
                    continue

                # Update RA based on tracking rate
                # Earth rotates ~15 arcsec/sec, tracking compensates
                rate_arcsec = self.get_tracking_rate_value()
                ra_change_hours = (rate_arcsec * update_interval) / 3600 / 15  # 15 arcsec = 1 sec of RA

                # Tracking keeps object stationary, so we adjust RA
                # (In real mount, this counters Earth rotation)
                self._position.ra_hours += ra_change_hours

                # Keep RA in 0-24 range
                self._position.ra_hours = self._position.ra_hours % 24

            except asyncio.CancelledError:
                break

    # =========================================================================
    # Slewing
    # =========================================================================

    async def slew_to(self, ra_hours: float, dec_degrees: float) -> bool:
        """
        Slew to target coordinates.

        Args:
            ra_hours: Target RA in hours
            dec_degrees: Target Dec in degrees
        """
        if self._state == MountState.PARKED:
            return False

        # Stop current operations
        await self.stop_tracking()

        self._target_ra = ra_hours
        self._target_dec = dec_degrees
        self._state = MountState.SLEWING

        # Calculate slew time based on distance
        ra_diff = abs(ra_hours - self._position.ra_hours)
        dec_diff = abs(dec_degrees - self._position.dec_degrees)

        # Approximate slew time
        slew_time = max(ra_diff * 15, dec_diff) / self.mount_config.slew_rate_fast
        slew_time = max(slew_time, 1.0)  # Minimum 1 second

        # Simulate slew
        await asyncio.sleep(slew_time)

        # Update position
        self._position.ra_hours = ra_hours
        self._position.dec_degrees = dec_degrees

        self._state = MountState.IDLE
        return True

    async def abort_slew(self) -> bool:
        """Abort current slew."""
        if self._slew_task:
            self._slew_task.cancel()
            self._slew_task = None

        if self._state == MountState.SLEWING:
            self._state = MountState.IDLE

        return True

    # =========================================================================
    # Position
    # =========================================================================

    def get_position(self) -> Dict[str, float]:
        """Get current mount position."""
        return {
            "ra_hours": self._position.ra_hours,
            "dec_degrees": self._position.dec_degrees,
            "alt_degrees": self._position.alt_degrees,
            "az_degrees": self._position.az_degrees,
        }

    def get_status(self) -> Dict[str, Any]:
        """Get complete mount status."""
        return {
            "state": self._state.value,
            "is_parked": self.is_parked,
            "is_tracking": self.is_tracking,
            "is_slewing": self.is_slewing,
            "tracking_rate": self._tracking_rate.value,
            "tracking_rate_arcsec": self.get_tracking_rate_value(),
            "position": self.get_position(),
            "target": {
                "ra_hours": self._target_ra,
                "dec_degrees": self._target_dec,
            },
        }
