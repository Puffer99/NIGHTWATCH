"""
Mock Focuser Controller for Testing.

Simulates focus controller behavior for unit and integration testing.
Provides configurable movement simulation and temperature compensation.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, List

logger = logging.getLogger("NIGHTWATCH.fixtures.MockFocuser")


class MockFocuserState(Enum):
    """Focuser operational states."""
    DISCONNECTED = "disconnected"
    IDLE = "idle"
    MOVING = "moving"
    ERROR = "error"


@dataclass
class FocuserInfo:
    """Focuser hardware information."""
    name: str = "MockFocuser ZWO EAF"
    max_position: int = 100000
    min_position: int = 0
    step_size_um: float = 0.1
    has_temperature: bool = True
    is_absolute: bool = True


@dataclass
class FocuserStatus:
    """Current focuser status."""
    state: MockFocuserState = MockFocuserState.DISCONNECTED
    position: int = 50000
    target_position: int = 50000
    temperature_c: float = 15.0
    is_moving: bool = False
    last_move_time: Optional[datetime] = None


class MockFocuser:
    """
    Mock focuser controller for testing.

    Simulates a motorized focuser with:
    - Absolute and relative positioning
    - Movement simulation with configurable speed
    - Temperature reading
    - Temperature compensation
    - Backlash compensation

    Example:
        focuser = MockFocuser()
        await focuser.connect()
        await focuser.move_to(55000)
        position = focuser.get_position()
        temp = focuser.get_temperature()
    """

    # Default configuration
    DEFAULT_SPEED_STEPS_SEC = 1000
    DEFAULT_BACKLASH_STEPS = 50

    def __init__(
        self,
        speed: int = DEFAULT_SPEED_STEPS_SEC,
        backlash: int = DEFAULT_BACKLASH_STEPS,
        simulate_delays: bool = True,
    ):
        """
        Initialize mock focuser.

        Args:
            speed: Movement speed in steps per second
            backlash: Backlash compensation in steps
            simulate_delays: Whether to simulate realistic delays
        """
        self.speed = speed
        self.backlash = backlash
        self.simulate_delays = simulate_delays

        # Hardware info
        self.info = FocuserInfo()

        # Status
        self.status = FocuserStatus()

        # Temperature compensation
        self._temp_comp_enabled = False
        self._temp_comp_coefficient = 0.0  # steps per degree C
        self._last_temp_comp_temp: Optional[float] = None

        # Internal
        self._move_task: Optional[asyncio.Task] = None

        # Error injection
        self._inject_connect_error = False
        self._inject_move_error = False
        self._inject_stall = False

        # Callbacks
        self._position_callbacks: List[Callable] = []
        self._move_complete_callbacks: List[Callable] = []

    @property
    def is_connected(self) -> bool:
        """Check if focuser is connected."""
        return self.status.state != MockFocuserState.DISCONNECTED

    @property
    def is_moving(self) -> bool:
        """Check if focuser is currently moving."""
        return self.status.state == MockFocuserState.MOVING

    async def connect(self, port: str = "/dev/ttyUSB0") -> bool:
        """
        Connect to focuser.

        Args:
            port: Serial port (ignored in mock)

        Returns:
            True if connected successfully
        """
        if self._inject_connect_error:
            raise ConnectionError("Mock: Simulated connection failure")

        if self.simulate_delays:
            await asyncio.sleep(0.1)

        self.status.state = MockFocuserState.IDLE
        logger.info(f"MockFocuser connected: {self.info.name}")
        return True

    async def disconnect(self):
        """Disconnect from focuser."""
        await self.halt()
        self.status.state = MockFocuserState.DISCONNECTED
        logger.info("MockFocuser disconnected")

    def get_info(self) -> FocuserInfo:
        """Get focuser hardware information."""
        return self.info

    def get_status(self) -> FocuserStatus:
        """Get current focuser status."""
        return self.status

    def get_position(self) -> int:
        """Get current position in steps."""
        return self.status.position

    def get_temperature(self) -> Optional[float]:
        """Get focuser temperature in Celsius."""
        if self.info.has_temperature:
            return self.status.temperature_c
        return None

    async def move_to(self, position: int) -> bool:
        """
        Move to absolute position.

        Args:
            position: Target position in steps

        Returns:
            True if move started successfully
        """
        if not self.is_connected:
            raise RuntimeError("Focuser not connected")

        if self.is_moving:
            raise RuntimeError("Focuser already moving")

        if self._inject_move_error:
            raise RuntimeError("Mock: Simulated move failure")

        # Validate position
        if not (self.info.min_position <= position <= self.info.max_position):
            raise ValueError(
                f"Position must be {self.info.min_position}-{self.info.max_position}"
            )

        self.status.target_position = position
        self.status.state = MockFocuserState.MOVING
        self.status.is_moving = True

        logger.info(f"MockFocuser moving to {position}")

        # Start movement simulation
        self._move_task = asyncio.create_task(self._simulate_move(position))
        return True

    async def move_relative(self, steps: int) -> bool:
        """
        Move relative to current position.

        Args:
            steps: Number of steps to move (positive = out, negative = in)

        Returns:
            True if move started successfully
        """
        new_position = self.status.position + steps
        return await self.move_to(new_position)

    async def _simulate_move(self, target: int):
        """Simulate movement over time."""
        start_pos = self.status.position
        direction = 1 if target > start_pos else -1
        distance = abs(target - start_pos)

        # Apply backlash if changing direction
        # (simplified: just add extra steps)
        if self.backlash > 0:
            distance += self.backlash

        if self.simulate_delays and self.speed > 0:
            move_time = distance / self.speed
            update_interval = 0.1
            elapsed = 0.0

            while elapsed < move_time:
                if self.status.state != MockFocuserState.MOVING:
                    return  # Move was halted

                if self._inject_stall:
                    self.status.state = MockFocuserState.ERROR
                    logger.error("MockFocuser: Motor stall detected")
                    return

                await asyncio.sleep(update_interval)
                elapsed += update_interval

                # Update position
                progress = min(1.0, elapsed / move_time)
                self.status.position = int(start_pos + (target - start_pos) * progress)

                # Notify callbacks
                for callback in self._position_callbacks:
                    try:
                        callback(self.status.position)
                    except Exception as e:
                        logger.error(f"Position callback error: {e}")
        else:
            # Instant move for testing
            self.status.position = target

        # Move complete
        self.status.position = target
        self.status.state = MockFocuserState.IDLE
        self.status.is_moving = False
        self.status.last_move_time = datetime.now()

        logger.info(f"MockFocuser move complete at {target}")

        # Notify callbacks
        for callback in self._move_complete_callbacks:
            try:
                callback(target)
            except Exception as e:
                logger.error(f"Move complete callback error: {e}")

    async def halt(self):
        """Halt current movement."""
        if self._move_task and not self._move_task.done():
            self._move_task.cancel()
            try:
                await self._move_task
            except asyncio.CancelledError:
                pass

        if self.status.state == MockFocuserState.MOVING:
            self.status.state = MockFocuserState.IDLE
            self.status.is_moving = False
            logger.info(f"MockFocuser halted at {self.status.position}")

    async def sync_position(self, position: int):
        """
        Sync current position to given value.

        Args:
            position: Position to sync to
        """
        if not self.is_connected:
            raise RuntimeError("Focuser not connected")

        self.status.position = position
        self.status.target_position = position
        logger.info(f"MockFocuser synced to {position}")

    # Temperature compensation
    def set_temp_compensation(
        self,
        enabled: bool,
        coefficient: float = 0.0,
    ):
        """
        Configure temperature compensation.

        Args:
            enabled: Whether to enable compensation
            coefficient: Steps per degree C change
        """
        self._temp_comp_enabled = enabled
        self._temp_comp_coefficient = coefficient

        if enabled:
            self._last_temp_comp_temp = self.status.temperature_c
            logger.info(
                f"MockFocuser temp compensation enabled: {coefficient} steps/°C"
            )
        else:
            logger.info("MockFocuser temp compensation disabled")

    def apply_temp_compensation(self) -> int:
        """
        Apply temperature compensation.

        Returns:
            Number of steps compensated
        """
        if not self._temp_comp_enabled or self._last_temp_comp_temp is None:
            return 0

        temp_change = self.status.temperature_c - self._last_temp_comp_temp
        compensation = int(temp_change * self._temp_comp_coefficient)

        if abs(compensation) > 0:
            self.status.position += compensation
            self._last_temp_comp_temp = self.status.temperature_c
            logger.debug(f"MockFocuser temp compensation: {compensation} steps")

        return compensation

    # Temperature simulation
    def set_temperature(self, temperature_c: float):
        """Set simulated temperature."""
        self.status.temperature_c = temperature_c
        self.apply_temp_compensation()

    # Callbacks
    def set_position_callback(self, callback: Callable):
        """Register callback for position updates during move."""
        self._position_callbacks.append(callback)

    def set_move_complete_callback(self, callback: Callable):
        """Register callback for move completion."""
        self._move_complete_callbacks.append(callback)

    # Error injection
    def inject_connect_error(self, enable: bool = True):
        """Enable/disable connection error injection."""
        self._inject_connect_error = enable

    def inject_move_error(self, enable: bool = True):
        """Enable/disable move error injection."""
        self._inject_move_error = enable

    def inject_stall(self, enable: bool = True):
        """Enable/disable motor stall injection."""
        self._inject_stall = enable

    def set_error_state(self):
        """Put focuser in error state."""
        self.status.state = MockFocuserState.ERROR

    def clear_error_state(self):
        """Clear error state."""
        if self.status.state == MockFocuserState.ERROR:
            self.status.state = MockFocuserState.IDLE

    def reset(self):
        """Reset mock to initial state."""
        self.status = FocuserStatus()
        self._temp_comp_enabled = False
        self._temp_comp_coefficient = 0.0
        self._last_temp_comp_temp = None
        self._inject_connect_error = False
        self._inject_move_error = False
        self._inject_stall = False
