"""
Mock Enclosure Controller for Testing.

Simulates roll-off roof or dome enclosure for unit and integration testing.
Provides state machine with safety interlocks and error injection.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, List

logger = logging.getLogger("NIGHTWATCH.fixtures.MockEnclosure")


class MockEnclosureState(Enum):
    """Enclosure operational states."""
    DISCONNECTED = "disconnected"
    UNKNOWN = "unknown"
    CLOSED = "closed"
    OPENING = "opening"
    OPEN = "open"
    CLOSING = "closing"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class EnclosureStatus:
    """Current enclosure status."""
    state: MockEnclosureState = MockEnclosureState.DISCONNECTED
    position_percent: float = 0.0  # 0 = closed, 100 = open
    is_rain_sensor_wet: bool = False
    open_limit_switch: bool = False
    closed_limit_switch: bool = True
    motor_running: bool = False
    last_movement_time: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "state": self.state.value,
            "position_percent": self.position_percent,
            "is_rain_sensor_wet": self.is_rain_sensor_wet,
            "open_limit_switch": self.open_limit_switch,
            "closed_limit_switch": self.closed_limit_switch,
            "motor_running": self.motor_running,
        }


class MockEnclosure:
    """
    Mock enclosure controller for testing.

    Simulates a roll-off roof observatory enclosure with:
    - Open/close operations with position tracking
    - Rain sensor simulation
    - Limit switch simulation
    - Safety interlocks (mount parked, weather safe)
    - Emergency stop functionality

    Example:
        enclosure = MockEnclosure()
        await enclosure.connect()
        await enclosure.open()
        status = enclosure.get_status()
        await enclosure.close()
    """

    # Default timing
    DEFAULT_OPEN_TIME_SEC = 30.0
    DEFAULT_CLOSE_TIME_SEC = 30.0

    def __init__(
        self,
        open_time_sec: float = DEFAULT_OPEN_TIME_SEC,
        close_time_sec: float = DEFAULT_CLOSE_TIME_SEC,
        simulate_delays: bool = True,
    ):
        """
        Initialize mock enclosure.

        Args:
            open_time_sec: Time to fully open
            close_time_sec: Time to fully close
            simulate_delays: Whether to simulate realistic delays
        """
        self.open_time_sec = open_time_sec
        self.close_time_sec = close_time_sec
        self.simulate_delays = simulate_delays

        # Status
        self.status = EnclosureStatus()

        # Safety interlocks
        self._mount_parked = True
        self._weather_safe = True

        # Internal
        self._movement_task: Optional[asyncio.Task] = None

        # Error injection
        self._inject_connect_error = False
        self._inject_open_error = False
        self._inject_close_error = False
        self._inject_motor_stall = False

        # Callbacks
        self._state_callbacks: List[Callable] = []
        self._position_callbacks: List[Callable] = []

    @property
    def is_connected(self) -> bool:
        """Check if enclosure is connected."""
        return self.status.state != MockEnclosureState.DISCONNECTED

    @property
    def is_open(self) -> bool:
        """Check if enclosure is fully open."""
        return self.status.state == MockEnclosureState.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if enclosure is fully closed."""
        return self.status.state == MockEnclosureState.CLOSED

    @property
    def is_moving(self) -> bool:
        """Check if enclosure is currently moving."""
        return self.status.state in {
            MockEnclosureState.OPENING,
            MockEnclosureState.CLOSING,
        }

    async def connect(self) -> bool:
        """
        Connect to enclosure controller.

        Returns:
            True if connected successfully
        """
        if self._inject_connect_error:
            raise ConnectionError("Mock: Simulated connection failure")

        if self.simulate_delays:
            await asyncio.sleep(0.1)

        # Determine initial state from limit switches
        if self.status.closed_limit_switch:
            self.status.state = MockEnclosureState.CLOSED
            self.status.position_percent = 0.0
        elif self.status.open_limit_switch:
            self.status.state = MockEnclosureState.OPEN
            self.status.position_percent = 100.0
        else:
            self.status.state = MockEnclosureState.UNKNOWN

        logger.info("MockEnclosure connected")
        return True

    async def disconnect(self):
        """Disconnect from enclosure controller."""
        await self.stop()
        self.status.state = MockEnclosureState.DISCONNECTED
        logger.info("MockEnclosure disconnected")

    def get_status(self) -> EnclosureStatus:
        """Get current enclosure status."""
        return self.status

    async def open(self) -> bool:
        """
        Open the enclosure.

        Returns:
            True if open command accepted

        Raises:
            RuntimeError: If safety conditions not met
        """
        if not self.is_connected:
            raise RuntimeError("Enclosure not connected")

        if self.is_moving:
            raise RuntimeError("Enclosure already moving")

        if self._inject_open_error:
            raise RuntimeError("Mock: Simulated open failure")

        # Safety checks
        if not self._mount_parked:
            raise RuntimeError("Cannot open: mount not parked")

        if not self._weather_safe:
            raise RuntimeError("Cannot open: weather unsafe")

        if self.status.is_rain_sensor_wet:
            raise RuntimeError("Cannot open: rain detected")

        if self.is_open:
            logger.info("Enclosure already open")
            return True

        self._set_state(MockEnclosureState.OPENING)
        self.status.motor_running = True

        logger.info("MockEnclosure opening")

        # Start movement simulation
        self._movement_task = asyncio.create_task(self._simulate_open())
        return True

    async def _simulate_open(self):
        """Simulate opening movement."""
        start_position = self.status.position_percent
        target_position = 100.0

        if self.simulate_delays:
            # Calculate remaining time based on position
            remaining_travel = target_position - start_position
            movement_time = (remaining_travel / 100.0) * self.open_time_sec
            update_interval = 0.2
            elapsed = 0.0

            while elapsed < movement_time:
                if self.status.state != MockEnclosureState.OPENING:
                    return  # Movement was stopped

                if self._inject_motor_stall:
                    self._set_state(MockEnclosureState.ERROR)
                    self.status.motor_running = False
                    logger.error("MockEnclosure: Motor stall detected")
                    return

                await asyncio.sleep(update_interval)
                elapsed += update_interval

                # Update position
                progress = min(1.0, elapsed / movement_time)
                self.status.position_percent = start_position + (remaining_travel * progress)

                # Update limit switches
                self.status.closed_limit_switch = self.status.position_percent < 5.0
                self.status.open_limit_switch = self.status.position_percent > 95.0

                # Notify callbacks
                self._notify_position()
        else:
            self.status.position_percent = target_position

        # Movement complete
        self.status.position_percent = 100.0
        self.status.open_limit_switch = True
        self.status.closed_limit_switch = False
        self.status.motor_running = False
        self.status.last_movement_time = datetime.now()
        self._set_state(MockEnclosureState.OPEN)

        logger.info("MockEnclosure fully open")

    async def close(self) -> bool:
        """
        Close the enclosure.

        Returns:
            True if close command accepted
        """
        if not self.is_connected:
            raise RuntimeError("Enclosure not connected")

        if self.is_moving:
            raise RuntimeError("Enclosure already moving")

        if self._inject_close_error:
            raise RuntimeError("Mock: Simulated close failure")

        if self.is_closed:
            logger.info("Enclosure already closed")
            return True

        self._set_state(MockEnclosureState.CLOSING)
        self.status.motor_running = True

        logger.info("MockEnclosure closing")

        # Start movement simulation
        self._movement_task = asyncio.create_task(self._simulate_close())
        return True

    async def _simulate_close(self):
        """Simulate closing movement."""
        start_position = self.status.position_percent
        target_position = 0.0

        if self.simulate_delays:
            # Calculate remaining time based on position
            remaining_travel = start_position - target_position
            movement_time = (remaining_travel / 100.0) * self.close_time_sec
            update_interval = 0.2
            elapsed = 0.0

            while elapsed < movement_time:
                if self.status.state != MockEnclosureState.CLOSING:
                    return  # Movement was stopped

                if self._inject_motor_stall:
                    self._set_state(MockEnclosureState.ERROR)
                    self.status.motor_running = False
                    logger.error("MockEnclosure: Motor stall detected")
                    return

                await asyncio.sleep(update_interval)
                elapsed += update_interval

                # Update position
                progress = min(1.0, elapsed / movement_time)
                self.status.position_percent = start_position - (remaining_travel * progress)

                # Update limit switches
                self.status.closed_limit_switch = self.status.position_percent < 5.0
                self.status.open_limit_switch = self.status.position_percent > 95.0

                # Notify callbacks
                self._notify_position()
        else:
            self.status.position_percent = target_position

        # Movement complete
        self.status.position_percent = 0.0
        self.status.open_limit_switch = False
        self.status.closed_limit_switch = True
        self.status.motor_running = False
        self.status.last_movement_time = datetime.now()
        self._set_state(MockEnclosureState.CLOSED)

        logger.info("MockEnclosure fully closed")

    async def stop(self):
        """Stop enclosure movement."""
        if self._movement_task and not self._movement_task.done():
            self._movement_task.cancel()
            try:
                await self._movement_task
            except asyncio.CancelledError:
                pass

        if self.is_moving:
            self.status.motor_running = False
            # Determine state based on position
            if self.status.position_percent < 5.0:
                self._set_state(MockEnclosureState.CLOSED)
            elif self.status.position_percent > 95.0:
                self._set_state(MockEnclosureState.OPEN)
            else:
                self._set_state(MockEnclosureState.UNKNOWN)

            logger.info(f"MockEnclosure stopped at {self.status.position_percent:.1f}%")

    async def emergency_close(self) -> bool:
        """
        Emergency close - bypasses safety checks.

        Returns:
            True if emergency close started
        """
        # Stop any current movement
        await self.stop()

        # Force close regardless of safety state
        self._set_state(MockEnclosureState.CLOSING)
        self.status.motor_running = True

        logger.warning("MockEnclosure EMERGENCY CLOSE initiated")

        self._movement_task = asyncio.create_task(self._simulate_close())
        return True

    def _set_state(self, state: MockEnclosureState):
        """Set state and notify callbacks."""
        old_state = self.status.state
        self.status.state = state

        if old_state != state:
            for callback in self._state_callbacks:
                try:
                    callback(state)
                except Exception as e:
                    logger.error(f"State callback error: {e}")

    def _notify_position(self):
        """Notify position callbacks."""
        for callback in self._position_callbacks:
            try:
                callback(self.status.position_percent)
            except Exception as e:
                logger.error(f"Position callback error: {e}")

    # Safety interlock setters (for testing)
    def set_mount_parked(self, parked: bool):
        """Set mount parked state for safety interlock."""
        self._mount_parked = parked

    def set_weather_safe(self, safe: bool):
        """Set weather safe state for safety interlock."""
        self._weather_safe = safe

    def set_rain_sensor(self, wet: bool):
        """Set rain sensor state."""
        self.status.is_rain_sensor_wet = wet
        if wet and self.is_open:
            logger.warning("MockEnclosure: Rain detected while open!")

    # Callbacks
    def set_state_callback(self, callback: Callable):
        """Register callback for state changes."""
        self._state_callbacks.append(callback)

    def set_position_callback(self, callback: Callable):
        """Register callback for position updates."""
        self._position_callbacks.append(callback)

    # Error injection
    def inject_connect_error(self, enable: bool = True):
        """Enable/disable connection error injection."""
        self._inject_connect_error = enable

    def inject_open_error(self, enable: bool = True):
        """Enable/disable open error injection."""
        self._inject_open_error = enable

    def inject_close_error(self, enable: bool = True):
        """Enable/disable close error injection."""
        self._inject_close_error = enable

    def inject_motor_stall(self, enable: bool = True):
        """Enable/disable motor stall injection."""
        self._inject_motor_stall = enable

    def reset(self):
        """Reset mock to initial state."""
        self.status = EnclosureStatus()
        self._mount_parked = True
        self._weather_safe = True
        self._inject_connect_error = False
        self._inject_open_error = False
        self._inject_close_error = False
        self._inject_motor_stall = False
