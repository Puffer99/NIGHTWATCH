"""
NIGHTWATCH Roll-Off Roof Controller
Enclosure Automation with Safety Interlocks

POS Panel v3.0 - Day 23 Recommendations (AAG CloudWatcher Team + DIY ROR Builders):
- Hardware interlocks: Rain sensor closes roof regardless of software
- Dual limit switches with NC contacts (fail-safe)
- Motor timeout: 60 seconds max run time
- Telescope parked verification before opening
- Weather hold-off: 30 min after last rain before opening
- Power loss: Motor brake engages, roof stays put
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Callable, Dict, Any

logger = logging.getLogger("NIGHTWATCH.Enclosure")


class RoofState(Enum):
    """Roof position states."""
    OPEN = "open"
    CLOSED = "closed"
    OPENING = "opening"
    CLOSING = "closing"
    UNKNOWN = "unknown"
    ERROR = "error"


class SafetyCondition(Enum):
    """Safety conditions that affect roof operation."""
    WEATHER_SAFE = "weather_safe"
    TELESCOPE_PARKED = "telescope_parked"
    RAIN_HOLDOFF = "rain_holdoff"
    POWER_OK = "power_ok"
    HARDWARE_INTERLOCK = "hardware_interlock"
    MOTOR_OK = "motor_ok"
    LIMITS_OK = "limits_ok"


@dataclass
class RoofConfig:
    """Roof controller configuration."""
    # Motor settings
    motor_timeout_sec: float = 60.0     # Maximum motor run time
    motor_current_limit_a: float = 5.0  # Over-current protection

    # Safety
    rain_holdoff_min: float = 30.0      # Wait after rain clears
    park_verify_timeout: float = 10.0   # Time to verify park position

    # Hardware
    use_hardware_interlock: bool = True # Enable rain sensor interlock
    invert_motor: bool = False          # Invert motor direction

    # Position (for partial open support)
    max_position: int = 100             # 100 = fully open
    open_position: int = 100
    closed_position: int = 0

    # Polling
    status_poll_interval: float = 1.0   # Status check interval


@dataclass
class RoofStatus:
    """Current roof status."""
    state: RoofState
    position_percent: int = 0           # 0=closed, 100=open
    timestamp: datetime = field(default_factory=datetime.now)

    # Limit switches
    open_limit: bool = False            # Open limit switch active
    closed_limit: bool = False          # Closed limit switch active

    # Safety
    safety_conditions: Dict[SafetyCondition, bool] = field(default_factory=dict)
    can_open: bool = False
    can_close: bool = True

    # Motor
    motor_running: bool = False
    motor_current_a: float = 0.0

    # Errors
    error_message: Optional[str] = None


class RoofController:
    """
    Roll-off roof automation for NIGHTWATCH.

    Safety-first design with multiple interlocks:
    - Hardware rain sensor interlock (closes roof directly)
    - Software weather monitoring
    - Telescope park verification
    - Motor current and timeout protection
    - Dual limit switch verification

    Usage:
        roof = RoofController()
        await roof.connect()

        # Check safety before opening
        if roof.status.can_open:
            await roof.open()

        # Emergency close (always works)
        await roof.close(emergency=True)
    """

    def __init__(self,
                 config: Optional[RoofConfig] = None,
                 weather_service=None,
                 mount_service=None):
        """
        Initialize roof controller.

        Args:
            config: Roof configuration
            weather_service: Weather monitoring service
            mount_service: Mount controller for park verification
        """
        self.config = config or RoofConfig()
        self._weather = weather_service
        self._mount = mount_service

        self._state = RoofState.UNKNOWN
        self._position = 0
        self._connected = False
        self._motor_running = False
        self._last_rain_time: Optional[datetime] = None
        self._status_task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable] = []

        # Safety tracking
        self._safety: Dict[SafetyCondition, bool] = {
            SafetyCondition.WEATHER_SAFE: False,
            SafetyCondition.TELESCOPE_PARKED: False,
            SafetyCondition.RAIN_HOLDOFF: True,
            SafetyCondition.POWER_OK: True,
            SafetyCondition.HARDWARE_INTERLOCK: True,
            SafetyCondition.MOTOR_OK: True,
            SafetyCondition.LIMITS_OK: True,
        }

        # Emergency stop tracking (Step 171)
        self._emergency_stop_active = False
        self._emergency_stop_callbacks: List[Callable] = []

        # Status callbacks for state transitions (Step 176)
        self._status_callbacks: Dict[str, List[Callable]] = {
            "opening": [],
            "open": [],
            "closing": [],
            "closed": [],
            "error": [],
            "emergency_stop": [],
        }

    @property
    def connected(self) -> bool:
        """Check if controller is connected."""
        return self._connected

    @property
    def state(self) -> RoofState:
        """Current roof state."""
        return self._state

    @property
    def is_open(self) -> bool:
        """Check if roof is fully open."""
        return self._state == RoofState.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if roof is fully closed."""
        return self._state == RoofState.CLOSED

    @property
    def status(self) -> RoofStatus:
        """Get current roof status."""
        return RoofStatus(
            state=self._state,
            position_percent=self._position,
            open_limit=(self._state == RoofState.OPEN),
            closed_limit=(self._state == RoofState.CLOSED),
            safety_conditions=self._safety.copy(),
            can_open=self._can_open(),
            can_close=True,  # Always allow close
            motor_running=self._motor_running,
        )

    def _can_open(self) -> bool:
        """Check if roof can be opened."""
        # Emergency stop must not be active
        if self._emergency_stop_active:
            return False

        # All safety conditions must be met
        return all([
            self._safety[SafetyCondition.WEATHER_SAFE],
            self._safety[SafetyCondition.TELESCOPE_PARKED],
            self._safety[SafetyCondition.RAIN_HOLDOFF],
            self._safety[SafetyCondition.POWER_OK],
            self._safety[SafetyCondition.HARDWARE_INTERLOCK],
            self._safety[SafetyCondition.MOTOR_OK],
            self._safety[SafetyCondition.LIMITS_OK],
        ])

    # =========================================================================
    # CONNECTION
    # =========================================================================

    async def connect(self, port: str = "/dev/ttyUSB0") -> bool:
        """
        Connect to roof controller.

        Args:
            port: Serial port or controller address

        Returns:
            True if connected successfully
        """
        try:
            logger.info(f"Connecting to roof controller on {port}")

            # In real implementation, would connect to Arduino/relay controller
            await asyncio.sleep(0.5)

            self._connected = True

            # Read initial state
            await self._read_limit_switches()

            # Start status monitoring
            self._status_task = asyncio.create_task(self._status_loop())

            logger.info(f"Roof controller connected. State: {self._state.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect roof controller: {e}")
            return False

    async def disconnect(self):
        """Disconnect from roof controller."""
        if self._status_task:
            self._status_task.cancel()
            try:
                await self._status_task
            except asyncio.CancelledError:
                pass

        self._connected = False
        logger.info("Roof controller disconnected")

    # =========================================================================
    # ROOF OPERATION
    # =========================================================================

    async def open(self, force: bool = False) -> bool:
        """
        Open the roof.

        Args:
            force: Bypass safety checks (USE WITH CAUTION)

        Returns:
            True if roof opened successfully
        """
        if not self._connected:
            raise RuntimeError("Roof controller not connected")

        if self._state == RoofState.OPEN:
            logger.info("Roof already open")
            return True

        if self._motor_running:
            raise RuntimeError("Motor already running")

        # Safety checks
        if not force:
            if not self._can_open():
                failed = [k.value for k, v in self._safety.items() if not v]
                raise RuntimeError(f"Cannot open: safety conditions not met: {failed}")

            # Verify telescope is parked
            if not await self._verify_telescope_parked():
                raise RuntimeError("Cannot open: telescope not parked")

        logger.info("Opening roof...")
        self._state = RoofState.OPENING
        await self._emit_status_event("opening")  # Step 176

        try:
            await self._run_motor(direction="open")

            # Verify open
            if await self._check_open_limit():
                self._state = RoofState.OPEN
                self._position = 100
                logger.info("Roof open")
                await self._notify_callbacks("opened")
                await self._emit_status_event("open")  # Step 176
                return True
            else:
                self._state = RoofState.ERROR
                logger.error("Roof failed to reach open limit")
                return False

        except Exception as e:
            self._state = RoofState.ERROR
            logger.error(f"Roof open failed: {e}")
            return False

    async def close(self, emergency: bool = False) -> bool:
        """
        Close the roof.

        Emergency close bypasses all checks and stops any motion first.

        Args:
            emergency: Emergency close mode

        Returns:
            True if roof closed successfully
        """
        if not self._connected:
            raise RuntimeError("Roof controller not connected")

        if self._state == RoofState.CLOSED:
            logger.info("Roof already closed")
            return True

        if emergency:
            logger.warning("EMERGENCY ROOF CLOSE")
            # Stop any current motion
            await self._stop_motor()

        if self._motor_running:
            raise RuntimeError("Motor already running")

        logger.info("Closing roof...")
        self._state = RoofState.CLOSING
        await self._emit_status_event("closing")  # Step 176

        try:
            await self._run_motor(direction="close")

            # Verify closed
            if await self._check_closed_limit():
                self._state = RoofState.CLOSED
                self._position = 0
                logger.info("Roof closed")
                await self._notify_callbacks("closed")
                await self._emit_status_event("closed")  # Step 176
                return True
            else:
                self._state = RoofState.ERROR
                logger.error("Roof failed to reach closed limit")
                return False

        except Exception as e:
            self._state = RoofState.ERROR
            logger.error(f"Roof close failed: {e}")
            return False

    async def stop(self):
        """Stop roof motion immediately."""
        await self._stop_motor()
        self._state = RoofState.UNKNOWN
        await self._read_limit_switches()
        logger.warning("Roof motion stopped")

    # =========================================================================
    # EMERGENCY STOP (Step 171)
    # =========================================================================

    async def emergency_stop(self) -> bool:
        """
        Emergency stop - immediately halt all roof motion (Step 171).

        This is the manual override that stops the motor regardless of
        software state. Should be wired to a physical emergency stop button.

        Returns:
            True if emergency stop was executed
        """
        logger.warning("EMERGENCY STOP ACTIVATED")
        self._emergency_stop_active = True

        # Immediately stop motor
        await self._stop_motor()

        # Update state
        self._state = RoofState.UNKNOWN
        await self._read_limit_switches()

        # Notify callbacks
        await self._emit_status_event("emergency_stop")

        # Call emergency stop callbacks
        for callback in self._emergency_stop_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Emergency stop callback error: {e}")

        return True

    def clear_emergency_stop(self) -> bool:
        """
        Clear emergency stop condition (Step 171).

        Must be called before roof can be operated again after
        an emergency stop.

        Returns:
            True if cleared successfully
        """
        if self._emergency_stop_active:
            logger.info("Emergency stop cleared")
            self._emergency_stop_active = False
            return True
        return False

    @property
    def is_emergency_stopped(self) -> bool:
        """Check if emergency stop is active (Step 171)."""
        return self._emergency_stop_active

    def register_emergency_stop_callback(self, callback: Callable):
        """
        Register callback for emergency stop events (Step 171).

        Args:
            callback: Function to call when emergency stop activates
        """
        self._emergency_stop_callbacks.append(callback)

    # =========================================================================
    # MOTOR CONTROL
    # =========================================================================

    async def _run_motor(self, direction: str):
        """
        Run roof motor with timeout and current monitoring.

        Args:
            direction: "open" or "close"
        """
        self._motor_running = True
        start_time = datetime.now()

        logger.debug(f"Starting motor: {direction}")

        try:
            # In real implementation, would send commands to motor controller
            # Simulate motor run
            while True:
                # Check timeout
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > self.config.motor_timeout_sec:
                    raise RuntimeError(f"Motor timeout after {elapsed:.0f}s")

                # Simulate position update
                if direction == "open":
                    self._position = min(100, self._position + 5)
                    if self._position >= 100:
                        break
                else:
                    self._position = max(0, self._position - 5)
                    if self._position <= 0:
                        break

                await asyncio.sleep(0.5)

        finally:
            self._motor_running = False
            logger.debug("Motor stopped")

    async def _stop_motor(self):
        """Stop motor immediately."""
        # In real implementation, would cut power to motor
        self._motor_running = False
        logger.debug("Motor force stop")

    # =========================================================================
    # LIMIT SWITCHES
    # =========================================================================

    async def _read_limit_switches(self):
        """Read limit switch states and update roof state."""
        # In real implementation, would read GPIO/serial
        open_limit = self._position >= 100
        closed_limit = self._position <= 0

        if closed_limit:
            self._state = RoofState.CLOSED
        elif open_limit:
            self._state = RoofState.OPEN
        else:
            self._state = RoofState.UNKNOWN

    async def _check_open_limit(self) -> bool:
        """Check if open limit switch is active."""
        await self._read_limit_switches()
        return self._state == RoofState.OPEN

    async def _check_closed_limit(self) -> bool:
        """Check if closed limit switch is active."""
        await self._read_limit_switches()
        return self._state == RoofState.CLOSED

    # =========================================================================
    # SAFETY CHECKS
    # =========================================================================

    async def _verify_telescope_parked(self) -> bool:
        """Verify telescope is in parked position."""
        if self._mount is None:
            logger.warning("No mount service - assuming parked")
            self._safety[SafetyCondition.TELESCOPE_PARKED] = True
            return True

        try:
            # Check mount park status
            is_parked = await self._mount.is_parked()
            self._safety[SafetyCondition.TELESCOPE_PARKED] = is_parked

            if not is_parked:
                logger.warning("Telescope not parked!")

            return is_parked

        except Exception as e:
            logger.error(f"Park verification failed: {e}")
            self._safety[SafetyCondition.TELESCOPE_PARKED] = False
            return False

    async def update_weather_status(self, is_safe: bool, rain_detected: bool = False):
        """
        Update weather safety status.

        Args:
            is_safe: Overall weather safety
            rain_detected: Rain currently detected
        """
        self._safety[SafetyCondition.WEATHER_SAFE] = is_safe

        if rain_detected:
            self._last_rain_time = datetime.now()
            self._safety[SafetyCondition.RAIN_HOLDOFF] = False

            # Emergency close if rain detected
            if self._state in [RoofState.OPEN, RoofState.OPENING]:
                logger.warning("Rain detected - emergency close!")
                asyncio.create_task(self.close(emergency=True))

        elif self._last_rain_time is not None:
            # Check rain holdoff
            elapsed = (datetime.now() - self._last_rain_time).total_seconds() / 60.0
            holdoff_complete = elapsed >= self.config.rain_holdoff_min
            self._safety[SafetyCondition.RAIN_HOLDOFF] = holdoff_complete

            if not holdoff_complete:
                remaining = self.config.rain_holdoff_min - elapsed
                logger.debug(f"Rain holdoff: {remaining:.1f} minutes remaining")

    def set_hardware_interlock(self, safe: bool):
        """
        Set hardware interlock status.

        This is typically called from hardware interrupt handler
        when rain sensor trips.

        Args:
            safe: True if interlock allows operation
        """
        self._safety[SafetyCondition.HARDWARE_INTERLOCK] = safe

        if not safe:
            logger.warning("Hardware interlock triggered!")
            # Hardware handles the close, but update state
            if self._state != RoofState.CLOSED:
                asyncio.create_task(self.close(emergency=True))

    # =========================================================================
    # STATUS MONITORING
    # =========================================================================

    async def _status_loop(self):
        """Background status monitoring loop."""
        try:
            while self._connected:
                await asyncio.sleep(self.config.status_poll_interval)

                # Read hardware status
                await self._read_limit_switches()

                # Check motor current (in real implementation)
                # await self._check_motor_current()

                # Update telescope park status
                await self._verify_telescope_parked()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Status loop error: {e}")

    # =========================================================================
    # CALLBACKS
    # =========================================================================

    def register_callback(self, callback: Callable):
        """Register callback for roof events."""
        self._callbacks.append(callback)

    async def _notify_callbacks(self, event: str):
        """Notify registered callbacks."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event, self.status)
                else:
                    callback(event, self.status)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    # =========================================================================
    # STATUS CALLBACKS (Step 176)
    # =========================================================================

    def register_status_callback(self, state: str, callback: Callable):
        """
        Register callback for specific roof state transitions (Step 176).

        Args:
            state: State to listen for ("opening", "open", "closing", "closed", "error", "emergency_stop")
            callback: Function to call when state is reached

        Example:
            roof.register_status_callback("open", lambda status: print("Roof opened!"))
            roof.register_status_callback("closed", on_roof_closed)
        """
        if state not in self._status_callbacks:
            raise ValueError(f"Invalid state: {state}. Valid states: {list(self._status_callbacks.keys())}")
        self._status_callbacks[state].append(callback)
        logger.debug(f"Registered status callback for '{state}'")

    def unregister_status_callback(self, state: str, callback: Callable) -> bool:
        """
        Unregister a status callback (Step 176).

        Args:
            state: State the callback was registered for
            callback: The callback to remove

        Returns:
            True if callback was found and removed
        """
        if state in self._status_callbacks:
            try:
                self._status_callbacks[state].remove(callback)
                return True
            except ValueError:
                return False
        return False

    async def _emit_status_event(self, state: str):
        """
        Emit status event to registered callbacks (Step 176).

        Args:
            state: The state that was reached
        """
        if state not in self._status_callbacks:
            return

        status = self.status
        logger.debug(f"Emitting status event: {state}")

        for callback in self._status_callbacks[state]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(status)
                else:
                    callback(status)
            except Exception as e:
                logger.error(f"Status callback error for '{state}': {e}")

    def get_registered_callbacks(self) -> Dict[str, int]:
        """
        Get count of registered callbacks per state (Step 176).

        Returns:
            Dict mapping state to callback count
        """
        return {state: len(callbacks) for state, callbacks in self._status_callbacks.items()}


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    async def test():
        print("NIGHTWATCH Roof Controller Test\n")

        roof = RoofController()

        print("Connecting to roof controller...")
        if await roof.connect():
            print(f"Connected! State: {roof.state.value}")

            status = roof.status
            print(f"\nRoof Status:")
            print(f"  State: {status.state.value}")
            print(f"  Position: {status.position_percent}%")
            print(f"  Can Open: {status.can_open}")
            print(f"  Can Close: {status.can_close}")

            print(f"\nSafety Conditions:")
            for cond, val in status.safety_conditions.items():
                symbol = "✓" if val else "✗"
                print(f"  [{symbol}] {cond.value}")

            # Simulate weather update
            print("\nUpdating weather status (safe, no rain)...")
            await roof.update_weather_status(is_safe=True, rain_detected=False)

            # Mark telescope as parked
            roof._safety[SafetyCondition.TELESCOPE_PARKED] = True

            status = roof.status
            print(f"Can Open: {status.can_open}")

            if status.can_open:
                print("\nOpening roof...")
                await roof.open()
                print(f"State: {roof.state.value}")

                print("\nClosing roof...")
                await roof.close()
                print(f"State: {roof.state.value}")

            await roof.disconnect()
        else:
            print("Failed to connect (expected if no hardware)")

    asyncio.run(test())
