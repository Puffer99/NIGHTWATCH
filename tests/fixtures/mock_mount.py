"""
Mock Mount Controller for Testing.

Simulates mount behavior for unit and integration testing.
Provides realistic slew times, tracking states, and error simulation.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, List, Tuple

logger = logging.getLogger("NIGHTWATCH.fixtures.MockMount")


class MockMountState(Enum):
    """Mount operational states."""
    DISCONNECTED = "disconnected"
    PARKED = "parked"
    IDLE = "idle"
    SLEWING = "slewing"
    TRACKING = "tracking"
    HOMING = "homing"
    ERROR = "error"


class TrackingRate(Enum):
    """Tracking rate modes."""
    SIDEREAL = "sidereal"
    LUNAR = "lunar"
    SOLAR = "solar"
    CUSTOM = "custom"


@dataclass
class MountPosition:
    """Current mount position."""
    ra_hours: float = 0.0  # Right ascension in hours (0-24)
    dec_degrees: float = 0.0  # Declination in degrees (-90 to +90)
    alt_degrees: float = 0.0  # Altitude in degrees
    az_degrees: float = 0.0  # Azimuth in degrees
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SlewTarget:
    """Slew target coordinates."""
    ra_hours: float
    dec_degrees: float
    name: Optional[str] = None


class MockMount:
    """
    Mock mount controller for testing.

    Simulates a realistic telescope mount with:
    - Connection/disconnection
    - Slewing with configurable speed
    - Tracking in multiple modes
    - Park/unpark functionality
    - Position queries
    - Error injection for testing failure scenarios

    Example:
        mount = MockMount()
        await mount.connect()
        await mount.slew_to_coordinates(12.5, 45.0)
        await mount.start_tracking()
        position = mount.get_position()
    """

    # Default configuration
    DEFAULT_SLEW_RATE_DEG_SEC = 3.0  # Degrees per second
    DEFAULT_PARK_POSITION = MountPosition(ra_hours=0.0, dec_degrees=90.0)

    def __init__(
        self,
        slew_rate: float = DEFAULT_SLEW_RATE_DEG_SEC,
        park_position: Optional[MountPosition] = None,
        simulate_delays: bool = True,
    ):
        """
        Initialize mock mount.

        Args:
            slew_rate: Slew speed in degrees per second
            park_position: Position for parking (default: north pole)
            simulate_delays: Whether to simulate realistic delays
        """
        self.slew_rate = slew_rate
        self.park_position = park_position or self.DEFAULT_PARK_POSITION
        self.simulate_delays = simulate_delays

        # State
        self._state = MockMountState.DISCONNECTED
        self._position = MountPosition()
        self._target: Optional[SlewTarget] = None
        self._tracking_rate = TrackingRate.SIDEREAL
        self._is_tracking = False

        # Error injection
        self._inject_connect_error = False
        self._inject_slew_error = False
        self._inject_timeout = False

        # Callbacks
        self._slew_complete_callbacks: List[Callable] = []
        self._position_callbacks: List[Callable] = []

        # Internal
        self._slew_task: Optional[asyncio.Task] = None

    @property
    def state(self) -> MockMountState:
        """Get current mount state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if mount is connected."""
        return self._state != MockMountState.DISCONNECTED

    @property
    def is_parked(self) -> bool:
        """Check if mount is parked."""
        return self._state == MockMountState.PARKED

    @property
    def is_slewing(self) -> bool:
        """Check if mount is currently slewing."""
        return self._state == MockMountState.SLEWING

    @property
    def is_tracking(self) -> bool:
        """Check if mount is tracking."""
        return self._is_tracking and self._state == MockMountState.TRACKING

    @property
    def tracking_rate(self) -> TrackingRate:
        """Get current tracking rate."""
        return self._tracking_rate

    async def connect(self, host: str = "localhost", port: int = 9999) -> bool:
        """
        Connect to the mount.

        Args:
            host: Mount host (ignored in mock)
            port: Mount port (ignored in mock)

        Returns:
            True if connected successfully

        Raises:
            ConnectionError: If error injection enabled
        """
        if self._inject_connect_error:
            raise ConnectionError("Mock: Simulated connection failure")

        if self.simulate_delays:
            await asyncio.sleep(0.1)

        self._state = MockMountState.PARKED
        logger.info(f"MockMount connected (host={host}, port={port})")
        return True

    async def disconnect(self):
        """Disconnect from the mount."""
        if self._slew_task and not self._slew_task.done():
            self._slew_task.cancel()
            try:
                await self._slew_task
            except asyncio.CancelledError:
                pass

        self._state = MockMountState.DISCONNECTED
        self._is_tracking = False
        logger.info("MockMount disconnected")

    def get_position(self) -> MountPosition:
        """Get current mount position."""
        self._position.timestamp = datetime.now()
        return self._position

    def get_ra_dec(self) -> Tuple[float, float]:
        """Get current RA/Dec coordinates."""
        return (self._position.ra_hours, self._position.dec_degrees)

    def get_alt_az(self) -> Tuple[float, float]:
        """Get current Alt/Az coordinates."""
        return (self._position.alt_degrees, self._position.az_degrees)

    async def slew_to_coordinates(
        self,
        ra_hours: float,
        dec_degrees: float,
        name: Optional[str] = None,
    ) -> bool:
        """
        Slew to target coordinates.

        Args:
            ra_hours: Target RA in hours (0-24)
            dec_degrees: Target Dec in degrees (-90 to +90)
            name: Optional target name

        Returns:
            True if slew started successfully

        Raises:
            RuntimeError: If mount not connected or in error state
            TimeoutError: If timeout injection enabled
        """
        if not self.is_connected:
            raise RuntimeError("Mount not connected")

        if self._state == MockMountState.ERROR:
            raise RuntimeError("Mount in error state")

        if self._inject_slew_error:
            raise RuntimeError("Mock: Simulated slew failure")

        if self._inject_timeout:
            raise TimeoutError("Mock: Simulated slew timeout")

        # Validate coordinates
        if not (0 <= ra_hours < 24):
            raise ValueError(f"RA must be 0-24 hours, got {ra_hours}")
        if not (-90 <= dec_degrees <= 90):
            raise ValueError(f"Dec must be -90 to +90 degrees, got {dec_degrees}")

        # Stop tracking during slew
        self._is_tracking = False

        # Set target and state
        self._target = SlewTarget(ra_hours=ra_hours, dec_degrees=dec_degrees, name=name)
        self._state = MockMountState.SLEWING

        logger.info(f"MockMount slewing to RA={ra_hours:.4f}h, Dec={dec_degrees:.2f}°")

        # Start simulated slew
        self._slew_task = asyncio.create_task(self._simulate_slew())
        return True

    async def _simulate_slew(self):
        """Simulate slew movement over time."""
        if not self._target:
            return

        start_ra = self._position.ra_hours
        start_dec = self._position.dec_degrees
        target_ra = self._target.ra_hours
        target_dec = self._target.dec_degrees

        # Calculate slew distance (simplified)
        ra_diff = abs(target_ra - start_ra)
        if ra_diff > 12:
            ra_diff = 24 - ra_diff  # Shorter path
        dec_diff = abs(target_dec - start_dec)

        # Convert to degrees for time calculation
        total_distance = (ra_diff * 15) + dec_diff  # Rough approximation
        slew_time = total_distance / self.slew_rate

        if self.simulate_delays and slew_time > 0:
            # Simulate gradual movement
            steps = max(1, int(slew_time * 10))  # 10 updates per second
            for i in range(steps):
                if self._state != MockMountState.SLEWING:
                    return  # Slew was aborted

                progress = (i + 1) / steps
                self._position.ra_hours = start_ra + (target_ra - start_ra) * progress
                self._position.dec_degrees = start_dec + (target_dec - start_dec) * progress

                # Notify position callbacks
                for callback in self._position_callbacks:
                    try:
                        callback(self._position)
                    except Exception as e:
                        logger.error(f"Position callback error: {e}")

                await asyncio.sleep(slew_time / steps)
        else:
            # Instant move for testing
            self._position.ra_hours = target_ra
            self._position.dec_degrees = target_dec

        # Slew complete
        self._state = MockMountState.IDLE
        logger.info(f"MockMount slew complete at RA={target_ra:.4f}h, Dec={target_dec:.2f}°")

        # Notify callbacks
        for callback in self._slew_complete_callbacks:
            try:
                callback(self._target)
            except Exception as e:
                logger.error(f"Slew complete callback error: {e}")

    async def abort_slew(self):
        """Abort current slew operation."""
        if self._slew_task and not self._slew_task.done():
            self._slew_task.cancel()
            try:
                await self._slew_task
            except asyncio.CancelledError:
                pass

        if self._state == MockMountState.SLEWING:
            self._state = MockMountState.IDLE
            logger.info("MockMount slew aborted")

    async def start_tracking(self, rate: TrackingRate = TrackingRate.SIDEREAL) -> bool:
        """
        Start tracking at specified rate.

        Args:
            rate: Tracking rate mode

        Returns:
            True if tracking started
        """
        if not self.is_connected:
            raise RuntimeError("Mount not connected")

        if self._state in {MockMountState.PARKED, MockMountState.SLEWING}:
            raise RuntimeError(f"Cannot start tracking in {self._state.value} state")

        self._tracking_rate = rate
        self._is_tracking = True
        self._state = MockMountState.TRACKING

        logger.info(f"MockMount tracking started at {rate.value} rate")
        return True

    async def stop_tracking(self):
        """Stop tracking."""
        self._is_tracking = False
        if self._state == MockMountState.TRACKING:
            self._state = MockMountState.IDLE
        logger.info("MockMount tracking stopped")

    async def park(self) -> bool:
        """
        Park the mount.

        Returns:
            True if park successful
        """
        if not self.is_connected:
            raise RuntimeError("Mount not connected")

        # Stop any active slew
        await self.abort_slew()
        self._is_tracking = False

        # Slew to park position
        self._state = MockMountState.SLEWING
        self._position.ra_hours = self.park_position.ra_hours
        self._position.dec_degrees = self.park_position.dec_degrees

        if self.simulate_delays:
            await asyncio.sleep(0.5)

        self._state = MockMountState.PARKED
        logger.info("MockMount parked")
        return True

    async def unpark(self) -> bool:
        """
        Unpark the mount.

        Returns:
            True if unpark successful
        """
        if not self.is_connected:
            raise RuntimeError("Mount not connected")

        if self._state != MockMountState.PARKED:
            logger.warning("Mount not parked")
            return False

        if self.simulate_delays:
            await asyncio.sleep(0.2)

        self._state = MockMountState.IDLE
        logger.info("MockMount unparked")
        return True

    async def home(self) -> bool:
        """
        Home the mount (find reference position).

        Returns:
            True if homing successful
        """
        if not self.is_connected:
            raise RuntimeError("Mount not connected")

        await self.abort_slew()
        self._is_tracking = False
        self._state = MockMountState.HOMING

        if self.simulate_delays:
            await asyncio.sleep(1.0)

        self._position.ra_hours = 0.0
        self._position.dec_degrees = 0.0
        self._state = MockMountState.IDLE

        logger.info("MockMount homed")
        return True

    async def sync(self, ra_hours: float, dec_degrees: float) -> bool:
        """
        Sync mount to specified coordinates.

        Args:
            ra_hours: Actual RA position
            dec_degrees: Actual Dec position

        Returns:
            True if sync successful
        """
        if not self.is_connected:
            raise RuntimeError("Mount not connected")

        self._position.ra_hours = ra_hours
        self._position.dec_degrees = dec_degrees

        logger.info(f"MockMount synced to RA={ra_hours:.4f}h, Dec={dec_degrees:.2f}°")
        return True

    def set_position_callback(self, callback: Callable):
        """Register callback for position updates during slew."""
        self._position_callbacks.append(callback)

    def set_slew_complete_callback(self, callback: Callable):
        """Register callback for slew completion."""
        self._slew_complete_callbacks.append(callback)

    # Error injection methods for testing
    def inject_connect_error(self, enable: bool = True):
        """Enable/disable connection error injection."""
        self._inject_connect_error = enable

    def inject_slew_error(self, enable: bool = True):
        """Enable/disable slew error injection."""
        self._inject_slew_error = enable

    def inject_timeout(self, enable: bool = True):
        """Enable/disable timeout injection."""
        self._inject_timeout = enable

    def set_error_state(self):
        """Put mount in error state."""
        self._state = MockMountState.ERROR
        self._is_tracking = False

    def clear_error_state(self):
        """Clear error state."""
        if self._state == MockMountState.ERROR:
            self._state = MockMountState.IDLE

    def reset(self):
        """Reset mock to initial state."""
        self._state = MockMountState.DISCONNECTED
        self._position = MountPosition()
        self._target = None
        self._is_tracking = False
        self._inject_connect_error = False
        self._inject_slew_error = False
        self._inject_timeout = False
