"""
NIGHTWATCH Power Management Service
UPS Monitoring and Graceful Shutdown

POS Panel v3.0 - Day 25 Recommendations (Critical Power Systems):
- APC Smart-UPS or CyberPower for USB/serial monitoring
- NUT (Network UPS Tools) for Linux integration
- Battery threshold: 50% triggers park sequence
- Low battery (20%): Emergency close and hibernate
- Power restored: Wait 5 minutes before resuming
- Log all power events for forensics
"""

import asyncio
import logging
import socket
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Callable, Dict, Any

logger = logging.getLogger("NIGHTWATCH.Power")


# =============================================================================
# NUT CLIENT (Network UPS Tools Protocol)
# =============================================================================

class NUTClient:
    """
    Client for NUT (Network UPS Tools) protocol.

    NUT uses a simple text-based protocol over TCP:
    - Commands are sent as plain text terminated by newline
    - Responses are plain text, terminated by newline
    - Multi-line responses end with "END"
    - Errors are prefixed with "ERR"

    Common commands:
    - LIST UPS: List available UPS devices
    - LIST VAR <ups>: List all variables for a UPS
    - GET VAR <ups> <var>: Get a single variable
    - INSTCMD <ups> <cmd>: Execute instant command
    """

    def __init__(self, host: str = "localhost", port: int = 3493, timeout: float = 10.0):
        """
        Initialize NUT client.

        Args:
            host: NUT server hostname or IP
            port: NUT server port (default 3493)
            timeout: Socket timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self._socket: Optional[socket.socket] = None

    def connect(self) -> bool:
        """
        Connect to NUT server.

        Returns:
            True if connection successful
        """
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            self._socket.connect((self.host, self.port))
            logger.info(f"Connected to NUT server at {self.host}:{self.port}")
            return True
        except socket.error as e:
            logger.error(f"Failed to connect to NUT server: {e}")
            self._socket = None
            return False

    def disconnect(self):
        """Disconnect from NUT server."""
        if self._socket:
            try:
                self._send("LOGOUT")
            except Exception:
                pass
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
            logger.info("Disconnected from NUT server")

    def _send(self, command: str) -> str:
        """
        Send command and receive response.

        Args:
            command: NUT command to send

        Returns:
            Response string (may be multi-line)

        Raises:
            RuntimeError: If not connected or communication fails
        """
        if not self._socket:
            raise RuntimeError("Not connected to NUT server")

        try:
            # Send command with newline
            self._socket.sendall(f"{command}\n".encode())

            # Receive response
            response_lines = []
            buffer = b""

            while True:
                data = self._socket.recv(4096)
                if not data:
                    break
                buffer += data

                # Process complete lines
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line_str = line.decode().strip()

                    if line_str.startswith("ERR"):
                        raise RuntimeError(f"NUT error: {line_str}")

                    if line_str == "END":
                        return "\n".join(response_lines)

                    response_lines.append(line_str)

                    # For single-line responses, check if we're done
                    if not response_lines[0].startswith("BEGIN"):
                        return response_lines[0]

            return "\n".join(response_lines)

        except socket.timeout:
            raise RuntimeError("NUT server timeout")
        except socket.error as e:
            raise RuntimeError(f"NUT communication error: {e}")

    def list_ups(self) -> Dict[str, str]:
        """
        List available UPS devices.

        Returns:
            Dictionary of UPS name -> description
        """
        try:
            response = self._send("LIST UPS")
            ups_list = {}
            for line in response.split("\n"):
                if line.startswith("UPS "):
                    # Format: UPS <upsname> "<description>"
                    parts = line.split('"')
                    if len(parts) >= 2:
                        name = line.split()[1]
                        desc = parts[1]
                        ups_list[name] = desc
            return ups_list
        except Exception as e:
            logger.error(f"Failed to list UPS: {e}")
            return {}

    def get_var(self, ups_name: str, var_name: str) -> Optional[str]:
        """
        Get a single UPS variable.

        Args:
            ups_name: UPS device name
            var_name: Variable name (e.g., "battery.charge")

        Returns:
            Variable value as string, or None if not found
        """
        try:
            response = self._send(f"GET VAR {ups_name} {var_name}")
            # Format: VAR <ups> <var> "<value>"
            if response.startswith("VAR "):
                parts = response.split('"')
                if len(parts) >= 2:
                    return parts[1]
            return None
        except Exception as e:
            logger.debug(f"Failed to get {var_name}: {e}")
            return None

    def list_vars(self, ups_name: str) -> Dict[str, str]:
        """
        List all variables for a UPS.

        Args:
            ups_name: UPS device name

        Returns:
            Dictionary of variable name -> value
        """
        try:
            response = self._send(f"LIST VAR {ups_name}")
            variables = {}
            for line in response.split("\n"):
                if line.startswith("VAR "):
                    # Format: VAR <ups> <var> "<value>"
                    parts = line.split('"')
                    if len(parts) >= 2:
                        var_parts = line.split()
                        if len(var_parts) >= 3:
                            var_name = var_parts[2]
                            var_value = parts[1]
                            variables[var_name] = var_value
            return variables
        except Exception as e:
            logger.error(f"Failed to list vars: {e}")
            return {}

    def get_ups_status(self, ups_name: str) -> Dict[str, Any]:
        """
        Get comprehensive UPS status.

        Args:
            ups_name: UPS device name

        Returns:
            Dictionary with parsed UPS status values
        """
        vars_dict = self.list_vars(ups_name)
        if not vars_dict:
            return {}

        def get_float(key: str, default: float = 0.0) -> float:
            try:
                return float(vars_dict.get(key, default))
            except (ValueError, TypeError):
                return default

        def get_int(key: str, default: int = 0) -> int:
            try:
                return int(float(vars_dict.get(key, default)))
            except (ValueError, TypeError):
                return default

        # Parse UPS status flags
        status_str = vars_dict.get("ups.status", "")
        on_mains = "OL" in status_str  # Online
        on_battery = "OB" in status_str  # On Battery
        low_battery = "LB" in status_str  # Low Battery
        charging = "CHRG" in status_str  # Charging

        return {
            # Battery
            "battery_charge": get_int("battery.charge", 100),
            "battery_voltage": get_float("battery.voltage"),
            "battery_runtime": get_int("battery.runtime"),  # seconds
            "battery_temperature": get_float("battery.temperature"),

            # Input power
            "input_voltage": get_float("input.voltage"),
            "input_frequency": get_float("input.frequency"),

            # Output power
            "output_voltage": get_float("output.voltage"),
            "ups_load": get_int("ups.load"),
            "output_power": get_float("ups.realpower"),

            # Status flags
            "on_mains": on_mains,
            "on_battery": on_battery,
            "low_battery": low_battery,
            "charging": charging,
            "status": status_str,

            # Device info
            "ups_model": vars_dict.get("ups.model", ""),
            "ups_serial": vars_dict.get("ups.serial", ""),
        }

    def execute_command(self, ups_name: str, command: str) -> bool:
        """
        Execute an instant command on the UPS.

        Args:
            ups_name: UPS device name
            command: Command name (e.g., "test.battery.start")

        Returns:
            True if command accepted
        """
        try:
            response = self._send(f"INSTCMD {ups_name} {command}")
            return response == "OK"
        except Exception as e:
            logger.error(f"Failed to execute command {command}: {e}")
            return False

    def list_commands(self, ups_name: str) -> List[str]:
        """
        List available commands for a UPS.

        Args:
            ups_name: UPS device name

        Returns:
            List of available command names
        """
        try:
            response = self._send(f"LIST CMD {ups_name}")
            commands = []
            for line in response.split("\n"):
                if line.startswith("CMD "):
                    # Format: CMD <ups> <cmd>
                    parts = line.split()
                    if len(parts) >= 3:
                        commands.append(parts[2])
            return commands
        except Exception as e:
            logger.error(f"Failed to list commands: {e}")
            return []


class PowerState(Enum):
    """UPS power states."""
    ONLINE = "online"             # On mains power
    ON_BATTERY = "on_battery"     # Running on battery
    LOW_BATTERY = "low_battery"   # Battery critical
    CHARGING = "charging"         # Battery charging
    UNKNOWN = "unknown"           # State unknown


class ShutdownReason(Enum):
    """Reasons for system shutdown."""
    LOW_BATTERY = "low_battery"
    POWER_FAILURE = "power_failure"
    UPS_FAILURE = "ups_failure"
    USER_REQUEST = "user_request"
    SCHEDULED = "scheduled"


@dataclass
class PowerConfig:
    """Power management configuration."""
    # NUT configuration
    ups_name: str = "ups"                   # UPS name in NUT
    nut_host: str = "localhost"             # NUT server
    nut_port: int = 3493                    # NUT port

    # Battery thresholds
    park_threshold_pct: int = 50            # Start park sequence
    emergency_threshold_pct: int = 20       # Emergency shutdown
    resume_threshold_pct: int = 80          # Battery level to resume

    # Timing
    poll_interval_sec: float = 10.0         # Status poll interval
    power_restore_delay_sec: float = 300.0  # Wait after power restored
    shutdown_delay_sec: float = 60.0        # Time before shutdown

    # Power ports (for smart PDU)
    port_mount: int = 1
    port_camera: int = 2
    port_focuser: int = 3
    port_computer: int = 4


@dataclass
class UPSStatus:
    """UPS status information."""
    timestamp: datetime = field(default_factory=datetime.now)
    state: PowerState = PowerState.UNKNOWN

    # Battery
    battery_percent: int = 100
    battery_voltage: float = 0.0
    battery_runtime_sec: int = 0          # Estimated runtime

    # Input power
    input_voltage: float = 0.0
    input_frequency: float = 0.0

    # Load
    load_percent: int = 0
    output_watts: float = 0.0

    # Status flags
    on_mains: bool = True
    battery_low: bool = False
    ups_alarm: bool = False

    # Derived
    @property
    def runtime_minutes(self) -> float:
        """Runtime in minutes."""
        return self.battery_runtime_sec / 60.0


@dataclass
class PowerEvent:
    """Power event record."""
    timestamp: datetime
    event_type: str
    description: str
    battery_percent: int
    on_mains: bool


class PowerManager:
    """
    Power management for NIGHTWATCH observatory.

    Monitors UPS via NUT (Network UPS Tools) and manages
    graceful shutdown sequences on power failure.

    Features:
    - UPS status monitoring via NUT
    - Multi-threshold response (park, emergency)
    - Graceful shutdown with roof close
    - Power event logging
    - PDU port control (optional)

    Usage:
        power = PowerManager()
        await power.start()

        # Register for power events
        power.register_callback(my_handler)

        # Check status
        status = power.status
        if status.state == PowerState.ON_BATTERY:
            print("Running on battery!")
    """

    def __init__(self,
                 config: Optional[PowerConfig] = None,
                 roof_controller=None,
                 mount_controller=None,
                 alert_manager=None):
        """
        Initialize power manager.

        Args:
            config: Power configuration
            roof_controller: Roof for emergency close
            mount_controller: Mount for emergency park
            alert_manager: For power alerts
        """
        self.config = config or PowerConfig()
        self._roof = roof_controller
        self._mount = mount_controller
        self._alerts = alert_manager

        self._status = UPSStatus()
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable] = []
        self._event_log: List[PowerEvent] = []

        # NUT client
        self._nut_client: Optional[NUTClient] = None
        self._nut_connected = False
        self._use_simulation = False  # Set True for testing without NUT

        # State tracking
        self._was_on_mains = True
        self._power_lost_time: Optional[datetime] = None
        self._power_restored_time: Optional[datetime] = None
        self._park_initiated = False
        self._shutdown_initiated = False

    @property
    def status(self) -> UPSStatus:
        """Current UPS status."""
        return self._status

    @property
    def event_log(self) -> List[PowerEvent]:
        """Power event history."""
        return self._event_log.copy()

    # =========================================================================
    # LIFECYCLE
    # =========================================================================

    async def start(self):
        """Start power monitoring."""
        # Try to connect to NUT server
        if not self._use_simulation:
            self._nut_client = NUTClient(
                host=self.config.nut_host,
                port=self.config.nut_port,
                timeout=5.0
            )
            self._nut_connected = self._nut_client.connect()
            if not self._nut_connected:
                logger.warning("NUT server not available, using simulation mode")
                self._use_simulation = True

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Power manager started (simulation={self._use_simulation})")

    async def stop(self):
        """Stop power monitoring."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # Disconnect NUT client
        if self._nut_client:
            self._nut_client.disconnect()
            self._nut_client = None
            self._nut_connected = False

        logger.info("Power manager stopped")

    # =========================================================================
    # UPS MONITORING
    # =========================================================================

    async def _monitor_loop(self):
        """Main monitoring loop."""
        try:
            while self._running:
                # Read UPS status
                await self._read_ups_status()

                # Process state changes
                await self._process_status()

                await asyncio.sleep(self.config.poll_interval_sec)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Power monitor error: {e}")

    async def _read_ups_status(self):
        """Read UPS status from NUT."""
        try:
            # In real implementation, would use PyNUT or upsc command
            # For simulation, create mock status
            status = await self._query_nut()
            self._status = status

        except Exception as e:
            logger.error(f"Failed to read UPS status: {e}")
            self._status.state = PowerState.UNKNOWN

    async def _query_nut(self) -> UPSStatus:
        """
        Query NUT server for UPS status.

        Uses NUT client to communicate with NUT server and parse
        UPS variables into structured status.
        """
        if self._use_simulation or not self._nut_connected:
            # Simulation mode for testing
            return UPSStatus(
                timestamp=datetime.now(),
                state=PowerState.ONLINE if self._was_on_mains else PowerState.ON_BATTERY,
                battery_percent=100 if self._was_on_mains else 75,
                battery_voltage=54.2,
                battery_runtime_sec=1800,
                input_voltage=120.0 if self._was_on_mains else 0.0,
                input_frequency=60.0 if self._was_on_mains else 0.0,
                load_percent=25,
                output_watts=150.0,
                on_mains=self._was_on_mains,
                battery_low=False,
                ups_alarm=False,
            )

        # Query real NUT server
        try:
            nut_status = self._nut_client.get_ups_status(self.config.ups_name)
            if not nut_status:
                logger.warning("Empty response from NUT server")
                return self._status  # Return last known status

            # Determine power state
            if nut_status.get("low_battery"):
                state = PowerState.LOW_BATTERY
            elif nut_status.get("on_battery"):
                state = PowerState.ON_BATTERY
            elif nut_status.get("charging"):
                state = PowerState.CHARGING
            elif nut_status.get("on_mains"):
                state = PowerState.ONLINE
            else:
                state = PowerState.UNKNOWN

            return UPSStatus(
                timestamp=datetime.now(),
                state=state,
                battery_percent=nut_status.get("battery_charge", 100),
                battery_voltage=nut_status.get("battery_voltage", 0.0),
                battery_runtime_sec=nut_status.get("battery_runtime", 0),
                input_voltage=nut_status.get("input_voltage", 0.0),
                input_frequency=nut_status.get("input_frequency", 0.0),
                load_percent=nut_status.get("ups_load", 0),
                output_watts=nut_status.get("output_power", 0.0),
                on_mains=nut_status.get("on_mains", True),
                battery_low=nut_status.get("low_battery", False),
                ups_alarm=False,
            )

        except Exception as e:
            logger.error(f"Failed to query NUT: {e}")
            # Try to reconnect
            if self._nut_client:
                self._nut_client.disconnect()
                self._nut_connected = self._nut_client.connect()
            return self._status  # Return last known status

    async def _process_status(self):
        """Process UPS status and take action if needed."""
        status = self._status

        # Detect power transitions
        if self._was_on_mains and not status.on_mains:
            # Lost mains power
            await self._on_power_lost()

        elif not self._was_on_mains and status.on_mains:
            # Power restored
            await self._on_power_restored()

        # Check battery thresholds while on battery
        if status.state == PowerState.ON_BATTERY:
            if status.battery_percent <= self.config.emergency_threshold_pct:
                if not self._shutdown_initiated:
                    await self._emergency_shutdown()

            elif status.battery_percent <= self.config.park_threshold_pct:
                if not self._park_initiated:
                    await self._initiate_park()

        self._was_on_mains = status.on_mains

    async def _on_power_lost(self):
        """Handle mains power loss."""
        self._power_lost_time = datetime.now()
        self._status.state = PowerState.ON_BATTERY

        self._log_event("POWER_LOST", "Mains power lost - running on battery")
        logger.warning("POWER LOST - Running on UPS battery")

        # Send alert
        if self._alerts:
            from services.alerts.alert_manager import Alert, AlertLevel
            await self._alerts.raise_alert(Alert(
                level=AlertLevel.CRITICAL,
                source="power",
                message=f"Power failure - running on battery ({self._status.battery_percent}%)"
            ))

        await self._notify_callbacks("power_lost")

    async def _on_power_restored(self):
        """Handle power restoration."""
        self._power_restored_time = datetime.now()
        self._status.state = PowerState.CHARGING

        self._log_event("POWER_RESTORED", "Mains power restored")
        logger.info("Power restored - battery charging")

        # Reset flags
        self._park_initiated = False
        self._shutdown_initiated = False

        # Send alert
        if self._alerts:
            from services.alerts.alert_manager import Alert, AlertLevel
            await self._alerts.raise_alert(Alert(
                level=AlertLevel.INFO,
                source="power",
                message="Power restored - system recovering"
            ))

        await self._notify_callbacks("power_restored")

        # Wait before allowing resume
        logger.info(f"Waiting {self.config.power_restore_delay_sec}s before resume")
        await asyncio.sleep(self.config.power_restore_delay_sec)

        # Check battery level before resume
        if self._status.battery_percent >= self.config.resume_threshold_pct:
            self._status.state = PowerState.ONLINE
            await self._notify_callbacks("ready_to_resume")
        else:
            logger.info(f"Battery at {self._status.battery_percent}%, "
                       f"waiting for {self.config.resume_threshold_pct}%")

    # =========================================================================
    # EMERGENCY ACTIONS
    # =========================================================================

    async def _initiate_park(self):
        """Initiate telescope park on low battery."""
        self._park_initiated = True

        self._log_event("PARK_INITIATED",
                       f"Battery at {self._status.battery_percent}% - parking telescope")
        logger.warning(f"Low battery ({self._status.battery_percent}%) - parking telescope")

        # Send alert
        if self._alerts:
            from services.alerts.alert_manager import Alert, AlertLevel
            await self._alerts.raise_alert(Alert(
                level=AlertLevel.WARNING,
                source="power",
                message=f"Low battery ({self._status.battery_percent}%) - initiating park sequence"
            ))

        # Park telescope
        if self._mount:
            try:
                await self._mount.park()
                logger.info("Telescope parked")
            except Exception as e:
                logger.error(f"Failed to park telescope: {e}")

        await self._notify_callbacks("park_initiated")

    async def _emergency_shutdown(self):
        """Emergency shutdown on critical battery."""
        self._shutdown_initiated = True

        self._log_event("EMERGENCY_SHUTDOWN",
                       f"Critical battery ({self._status.battery_percent}%) - emergency shutdown")
        logger.critical(f"EMERGENCY SHUTDOWN - Battery at {self._status.battery_percent}%")

        # Send alert
        if self._alerts:
            from services.alerts.alert_manager import Alert, AlertLevel
            await self._alerts.raise_alert(Alert(
                level=AlertLevel.EMERGENCY,
                source="power",
                message=f"EMERGENCY: Battery critical ({self._status.battery_percent}%) - shutting down"
            ))

        # Close roof
        if self._roof:
            try:
                logger.info("Emergency closing roof...")
                await self._roof.close(emergency=True)
            except Exception as e:
                logger.error(f"Failed to close roof: {e}")

        # Park telescope if not already
        if self._mount and not self._park_initiated:
            try:
                await self._mount.park()
            except Exception as e:
                logger.error(f"Failed to park: {e}")

        await self._notify_callbacks("emergency_shutdown")

        # Wait before shutdown
        logger.warning(f"Shutting down in {self.config.shutdown_delay_sec} seconds...")
        await asyncio.sleep(self.config.shutdown_delay_sec)

        # Initiate system shutdown
        await self._system_shutdown(ShutdownReason.LOW_BATTERY)

    async def _system_shutdown(self, reason: ShutdownReason):
        """Initiate system shutdown."""
        self._log_event("SYSTEM_SHUTDOWN", f"System shutdown: {reason.value}")
        logger.critical(f"SYSTEM SHUTDOWN: {reason.value}")

        # In real implementation:
        # import subprocess
        # subprocess.run(["sudo", "shutdown", "-h", "now"])

        await self._notify_callbacks("system_shutdown", reason)

    # =========================================================================
    # MANUAL CONTROL
    # =========================================================================

    async def force_shutdown(self, reason: str = "manual"):
        """
        Force system shutdown.

        Args:
            reason: Reason for shutdown
        """
        self._log_event("FORCE_SHUTDOWN", f"Manual shutdown: {reason}")
        logger.warning(f"Manual shutdown requested: {reason}")

        # Safe shutdown sequence
        if self._roof:
            await self._roof.close(emergency=True)

        if self._mount:
            await self._mount.park()

        await self._system_shutdown(ShutdownReason.USER_REQUEST)

    async def simulate_power_failure(self, duration_sec: float = 30.0):
        """
        Simulate power failure for testing.

        Args:
            duration_sec: Duration of simulated failure
        """
        logger.warning(f"Simulating power failure for {duration_sec}s")
        self._was_on_mains = False
        await self._on_power_lost()

        await asyncio.sleep(duration_sec)

        self._was_on_mains = True
        await self._on_power_restored()

    # =========================================================================
    # PDU CONTROL (Optional)
    # =========================================================================

    async def set_port_power(self, port: int, on: bool) -> bool:
        """
        Control smart PDU port.

        Args:
            port: Port number
            on: True to power on

        Returns:
            True if successful
        """
        # In real implementation, would control PDU via SNMP or HTTP
        action = "ON" if on else "OFF"
        logger.info(f"PDU port {port}: {action}")
        return True

    async def power_cycle_port(self, port: int, delay_sec: float = 5.0):
        """
        Power cycle a PDU port.

        Args:
            port: Port number
            delay_sec: Time to wait before powering back on
        """
        logger.info(f"Power cycling port {port}...")
        await self.set_port_power(port, False)
        await asyncio.sleep(delay_sec)
        await self.set_port_power(port, True)
        logger.info(f"Port {port} power cycled")

    # =========================================================================
    # EVENT LOGGING
    # =========================================================================

    def _log_event(self, event_type: str, description: str):
        """Log power event."""
        event = PowerEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            description=description,
            battery_percent=self._status.battery_percent,
            on_mains=self._status.on_mains
        )
        self._event_log.append(event)

        # Keep last 1000 events
        if len(self._event_log) > 1000:
            self._event_log = self._event_log[-1000:]

    def get_events_since(self, since: datetime) -> List[PowerEvent]:
        """Get events since a given time."""
        return [e for e in self._event_log if e.timestamp > since]

    # =========================================================================
    # CALLBACKS
    # =========================================================================

    def register_callback(self, callback: Callable):
        """Register callback for power events."""
        self._callbacks.append(callback)

    async def _notify_callbacks(self, event: str, data: Any = None):
        """Notify registered callbacks."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event, data)
                else:
                    callback(event, data)
            except Exception as e:
                logger.error(f"Callback error: {e}")


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    async def test():
        print("NIGHTWATCH Power Manager Test\n")

        power = PowerManager()

        print("Starting power monitor...")
        await power.start()

        # Give it time to read status
        await asyncio.sleep(2)

        status = power.status
        print(f"\nUPS Status:")
        print(f"  State: {status.state.value}")
        print(f"  Battery: {status.battery_percent}%")
        print(f"  Runtime: {status.runtime_minutes:.1f} minutes")
        print(f"  On Mains: {status.on_mains}")
        print(f"  Load: {status.load_percent}%")
        print(f"  Output: {status.output_watts}W")

        print(f"\nConfiguration:")
        print(f"  Park threshold: {power.config.park_threshold_pct}%")
        print(f"  Emergency threshold: {power.config.emergency_threshold_pct}%")
        print(f"  Resume threshold: {power.config.resume_threshold_pct}%")

        # Test simulated failure (short)
        print("\nSimulating brief power failure...")
        # Commented out for safety:
        # await power.simulate_power_failure(5.0)

        print("\nEvent log:")
        for event in power.event_log[-5:]:
            print(f"  {event.timestamp}: {event.event_type} - {event.description}")

        await power.stop()
        print("\nPower manager stopped")

    asyncio.run(test())
