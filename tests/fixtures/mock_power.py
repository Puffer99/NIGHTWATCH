"""
Mock Power Monitor for Testing.

Simulates UPS and PDU power monitoring for unit and integration testing.
Provides battery state simulation and power outlet control.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, List, Dict

logger = logging.getLogger("NIGHTWATCH.fixtures.MockPower")


class PowerState(Enum):
    """Overall power state."""
    DISCONNECTED = "disconnected"
    ON_MAINS = "on_mains"
    ON_BATTERY = "on_battery"
    LOW_BATTERY = "low_battery"
    CRITICAL_BATTERY = "critical_battery"
    CHARGING = "charging"
    ERROR = "error"


class OutletState(Enum):
    """PDU outlet state."""
    ON = "on"
    OFF = "off"
    UNKNOWN = "unknown"


@dataclass
class BatteryStatus:
    """Battery/UPS status."""
    charge_percent: float = 100.0
    voltage: float = 13.8
    runtime_minutes: float = 120.0
    is_charging: bool = False
    temperature_c: float = 25.0


@dataclass
class PowerStatus:
    """Complete power system status."""
    state: PowerState = PowerState.DISCONNECTED
    battery: BatteryStatus = field(default_factory=BatteryStatus)
    mains_voltage: float = 120.0
    mains_present: bool = True
    load_watts: float = 150.0
    load_percent: float = 25.0
    outlets: Dict[str, OutletState] = field(default_factory=dict)
    last_update: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "state": self.state.value,
            "battery_percent": self.battery.charge_percent,
            "battery_voltage": self.battery.voltage,
            "runtime_minutes": self.battery.runtime_minutes,
            "mains_present": self.mains_present,
            "load_watts": self.load_watts,
            "outlets": {k: v.value for k, v in self.outlets.items()},
        }


class MockPower:
    """
    Mock power monitor for testing.

    Simulates a UPS and optional PDU with:
    - Battery charge monitoring
    - Mains power detection
    - Runtime estimation
    - PDU outlet control
    - Power loss scenarios

    Example:
        power = MockPower()
        await power.connect()
        status = await power.get_status()
        is_safe = power.is_safe_for_operation()

        # Simulate power loss
        power.set_mains_present(False)
    """

    # Safety thresholds
    LOW_BATTERY_THRESHOLD = 50.0
    CRITICAL_BATTERY_THRESHOLD = 25.0
    EMERGENCY_BATTERY_THRESHOLD = 15.0

    # Default outlets for PDU
    DEFAULT_OUTLETS = [
        "mount",
        "camera",
        "focuser",
        "computer",
        "aux1",
        "aux2",
    ]

    def __init__(
        self,
        has_pdu: bool = False,
        outlets: Optional[List[str]] = None,
        simulate_delays: bool = True,
    ):
        """
        Initialize mock power monitor.

        Args:
            has_pdu: Whether PDU control is available
            outlets: List of outlet names (uses default if None)
            simulate_delays: Whether to simulate realistic delays
        """
        self.has_pdu = has_pdu
        self.simulate_delays = simulate_delays

        # Status
        self.status = PowerStatus()

        # Initialize outlets if PDU available
        if has_pdu:
            outlet_names = outlets or self.DEFAULT_OUTLETS
            self.status.outlets = {name: OutletState.ON for name in outlet_names}

        # Error injection
        self._inject_connect_error = False
        self._inject_read_error = False

        # Callbacks
        self._state_callbacks: List[Callable] = []
        self._battery_callbacks: List[Callable] = []

        # Background drain simulation
        self._drain_task: Optional[asyncio.Task] = None

    @property
    def is_connected(self) -> bool:
        """Check if power monitor is connected."""
        return self.status.state != PowerState.DISCONNECTED

    @property
    def is_on_battery(self) -> bool:
        """Check if running on battery power."""
        return self.status.state in {
            PowerState.ON_BATTERY,
            PowerState.LOW_BATTERY,
            PowerState.CRITICAL_BATTERY,
        }

    @property
    def battery_percent(self) -> float:
        """Get current battery percentage."""
        return self.status.battery.charge_percent

    async def connect(self, host: str = "localhost", port: int = 3493) -> bool:
        """
        Connect to power monitor (NUT server).

        Args:
            host: NUT server host (ignored in mock)
            port: NUT server port (ignored in mock)

        Returns:
            True if connected successfully
        """
        if self._inject_connect_error:
            raise ConnectionError("Mock: Simulated connection failure")

        if self.simulate_delays:
            await asyncio.sleep(0.1)

        self._update_state()
        logger.info(f"MockPower connected (host={host}, port={port})")
        return True

    async def disconnect(self):
        """Disconnect from power monitor."""
        if self._drain_task and not self._drain_task.done():
            self._drain_task.cancel()
            try:
                await self._drain_task
            except asyncio.CancelledError:
                pass

        self.status.state = PowerState.DISCONNECTED
        logger.info("MockPower disconnected")

    async def get_status(self) -> PowerStatus:
        """
        Get current power status.

        Returns:
            Current power status
        """
        if not self.is_connected:
            raise RuntimeError("Power monitor not connected")

        if self._inject_read_error:
            raise RuntimeError("Mock: Simulated read failure")

        self.status.last_update = datetime.now()
        return self.status

    def is_safe_for_operation(self) -> bool:
        """
        Check if power conditions are safe for observatory operation.

        Returns:
            True if safe to operate
        """
        # Not safe if critical battery
        if self.status.battery.charge_percent < self.CRITICAL_BATTERY_THRESHOLD:
            return False

        # Not safe if on battery and low
        if self.is_on_battery and self.status.battery.charge_percent < self.LOW_BATTERY_THRESHOLD:
            return False

        return True

    def get_runtime_minutes(self) -> float:
        """Get estimated battery runtime in minutes."""
        return self.status.battery.runtime_minutes

    def _update_state(self):
        """Update power state based on conditions."""
        old_state = self.status.state

        if self.status.mains_present:
            if self.status.battery.charge_percent < 100.0:
                self.status.state = PowerState.CHARGING
                self.status.battery.is_charging = True
            else:
                self.status.state = PowerState.ON_MAINS
                self.status.battery.is_charging = False
        else:
            self.status.battery.is_charging = False
            if self.status.battery.charge_percent < self.EMERGENCY_BATTERY_THRESHOLD:
                self.status.state = PowerState.CRITICAL_BATTERY
            elif self.status.battery.charge_percent < self.LOW_BATTERY_THRESHOLD:
                self.status.state = PowerState.LOW_BATTERY
            else:
                self.status.state = PowerState.ON_BATTERY

        # Notify if state changed
        if old_state != self.status.state:
            self._notify_state_change()

    def _notify_state_change(self):
        """Notify callbacks of state change."""
        for callback in self._state_callbacks:
            try:
                callback(self.status.state)
            except Exception as e:
                logger.error(f"State callback error: {e}")

    def _notify_battery_change(self):
        """Notify callbacks of battery change."""
        for callback in self._battery_callbacks:
            try:
                callback(self.status.battery)
            except Exception as e:
                logger.error(f"Battery callback error: {e}")

    # Simulation controls
    def set_mains_present(self, present: bool):
        """
        Set mains power state (simulate power loss/restore).

        Args:
            present: Whether mains power is available
        """
        self.status.mains_present = present

        if not present:
            logger.warning("MockPower: Mains power lost!")
            # Start battery drain if not already running
            if self._drain_task is None or self._drain_task.done():
                self._drain_task = asyncio.create_task(self._simulate_drain())
        else:
            logger.info("MockPower: Mains power restored")
            # Stop drain and start charging
            if self._drain_task and not self._drain_task.done():
                self._drain_task.cancel()

        self._update_state()

    def set_battery_percent(self, percent: float):
        """
        Set battery charge percentage.

        Args:
            percent: Battery charge (0-100)
        """
        self.status.battery.charge_percent = max(0.0, min(100.0, percent))

        # Update runtime estimate (rough: 2 min per percent at current load)
        self.status.battery.runtime_minutes = self.status.battery.charge_percent * 2.0

        # Update voltage (roughly 10.5-13.8V range)
        self.status.battery.voltage = 10.5 + (self.status.battery.charge_percent / 100.0) * 3.3

        self._update_state()
        self._notify_battery_change()

    def set_load(self, watts: float, max_watts: float = 600.0):
        """
        Set current load.

        Args:
            watts: Current power draw in watts
            max_watts: Maximum UPS capacity
        """
        self.status.load_watts = watts
        self.status.load_percent = (watts / max_watts) * 100.0

    async def _simulate_drain(self):
        """Simulate battery drain while on battery power."""
        drain_rate = 0.5  # Percent per 10 seconds

        while self.is_on_battery and self.status.battery.charge_percent > 0:
            await asyncio.sleep(10.0)
            self.set_battery_percent(self.status.battery.charge_percent - drain_rate)

    # PDU outlet control
    async def set_outlet(self, outlet: str, state: OutletState) -> bool:
        """
        Set PDU outlet state.

        Args:
            outlet: Outlet name
            state: Desired state (ON/OFF)

        Returns:
            True if successful
        """
        if not self.has_pdu:
            raise RuntimeError("PDU not available")

        if outlet not in self.status.outlets:
            raise ValueError(f"Unknown outlet: {outlet}")

        if self.simulate_delays:
            await asyncio.sleep(0.2)

        self.status.outlets[outlet] = state
        logger.info(f"MockPower: Outlet '{outlet}' set to {state.value}")
        return True

    async def get_outlet_state(self, outlet: str) -> OutletState:
        """
        Get PDU outlet state.

        Args:
            outlet: Outlet name

        Returns:
            Outlet state
        """
        if not self.has_pdu:
            raise RuntimeError("PDU not available")

        if outlet not in self.status.outlets:
            raise ValueError(f"Unknown outlet: {outlet}")

        return self.status.outlets[outlet]

    async def power_cycle_outlet(self, outlet: str, delay_sec: float = 5.0) -> bool:
        """
        Power cycle an outlet.

        Args:
            outlet: Outlet name
            delay_sec: Time to wait before turning back on

        Returns:
            True if successful
        """
        await self.set_outlet(outlet, OutletState.OFF)

        if self.simulate_delays:
            await asyncio.sleep(delay_sec)

        await self.set_outlet(outlet, OutletState.ON)
        logger.info(f"MockPower: Outlet '{outlet}' power cycled")
        return True

    # Callbacks
    def set_state_callback(self, callback: Callable):
        """Register callback for state changes."""
        self._state_callbacks.append(callback)

    def set_battery_callback(self, callback: Callable):
        """Register callback for battery changes."""
        self._battery_callbacks.append(callback)

    # Error injection
    def inject_connect_error(self, enable: bool = True):
        """Enable/disable connection error injection."""
        self._inject_connect_error = enable

    def inject_read_error(self, enable: bool = True):
        """Enable/disable read error injection."""
        self._inject_read_error = enable

    def reset(self):
        """Reset mock to initial state."""
        self.status = PowerStatus()
        if self.has_pdu:
            self.status.outlets = {name: OutletState.ON for name in self.DEFAULT_OUTLETS}
        self._inject_connect_error = False
        self._inject_read_error = False
