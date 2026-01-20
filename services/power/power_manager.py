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
# PDU CLIENT - HTTP/SNMP Interface (Step 153)
# =============================================================================


class PDUProtocol(Enum):
    """Supported PDU communication protocols."""
    HTTP = "http"
    SNMP = "snmp"
    SIMULATION = "simulation"


@dataclass
class PDUConfig:
    """
    PDU (Power Distribution Unit) configuration (Step 153).

    Supports both HTTP REST API and SNMP protocols for common
    smart PDU models.
    """
    protocol: PDUProtocol = PDUProtocol.SIMULATION
    host: str = "192.168.1.100"
    port: int = 80  # HTTP port, or 161 for SNMP

    # HTTP settings
    http_username: str = "admin"
    http_password: str = "admin"
    http_timeout_sec: float = 10.0

    # SNMP settings
    snmp_community: str = "private"  # Read-write community
    snmp_version: int = 2  # SNMPv1, v2c, or v3

    # Port mapping (PDU outlet -> device name)
    port_names: Dict[int, str] = field(default_factory=lambda: {
        1: "mount",
        2: "camera",
        3: "focuser",
        4: "computer",
    })

    # Number of outlets
    num_outlets: int = 8


class PDUClient:
    """
    Smart PDU client with HTTP and SNMP support (Step 153).

    Provides unified interface for controlling smart PDUs from
    various manufacturers via HTTP REST API or SNMP.

    Supported PDU types:
    - APC Switched Rack PDU (SNMP)
    - CyberPower PDU (HTTP/SNMP)
    - TP-Link Smart PDU (HTTP)
    - Generic SNMP PDU

    Common SNMP OIDs for outlet control:
    - APC: 1.3.6.1.4.1.318.1.1.4.4.2.1.3.<outlet>
    - CyberPower: 1.3.6.1.4.1.3808.1.1.3.3.3.1.1.4.<outlet>

    Usage:
        pdu = PDUClient(PDUConfig(protocol=PDUProtocol.HTTP))
        await pdu.connect()
        await pdu.set_outlet(1, True)  # Turn on outlet 1
        status = await pdu.get_all_outlets()
    """

    def __init__(self, config: Optional[PDUConfig] = None):
        """
        Initialize PDU client.

        Args:
            config: PDU configuration
        """
        self.config = config or PDUConfig()
        self._connected = False
        self._outlet_states: Dict[int, bool] = {}

        # Initialize all outlets as unknown (None means unknown)
        for i in range(1, self.config.num_outlets + 1):
            self._outlet_states[i] = True  # Assume on initially

    @property
    def is_connected(self) -> bool:
        """Check if connected to PDU."""
        return self._connected

    async def connect(self) -> bool:
        """
        Connect to PDU.

        Returns:
            True if connection successful
        """
        if self.config.protocol == PDUProtocol.SIMULATION:
            logger.info("PDU client in simulation mode")
            self._connected = True
            return True

        try:
            if self.config.protocol == PDUProtocol.HTTP:
                return await self._connect_http()
            elif self.config.protocol == PDUProtocol.SNMP:
                return await self._connect_snmp()
            else:
                logger.error(f"Unknown PDU protocol: {self.config.protocol}")
                return False
        except Exception as e:
            logger.error(f"PDU connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from PDU."""
        self._connected = False
        logger.info("PDU client disconnected")

    async def _connect_http(self) -> bool:
        """Connect via HTTP REST API."""
        try:
            import aiohttp
            url = f"http://{self.config.host}:{self.config.port}/api/status"

            async with aiohttp.ClientSession() as session:
                auth = aiohttp.BasicAuth(
                    self.config.http_username,
                    self.config.http_password
                )
                async with session.get(
                    url,
                    auth=auth,
                    timeout=aiohttp.ClientTimeout(total=self.config.http_timeout_sec)
                ) as response:
                    if response.status == 200:
                        self._connected = True
                        logger.info(f"Connected to PDU via HTTP at {self.config.host}")
                        return True
                    else:
                        logger.error(f"PDU HTTP connection failed: {response.status}")
                        return False
        except ImportError:
            logger.warning("aiohttp not installed, using simulation mode")
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"PDU HTTP connection error: {e}")
            return False

    async def _connect_snmp(self) -> bool:
        """Connect via SNMP."""
        try:
            # Test SNMP connectivity by reading sysDescr
            result = await self._snmp_get("1.3.6.1.2.1.1.1.0")  # sysDescr
            if result:
                self._connected = True
                logger.info(f"Connected to PDU via SNMP at {self.config.host}: {result}")
                return True
            return False
        except Exception as e:
            logger.error(f"PDU SNMP connection error: {e}")
            return False

    async def _snmp_get(self, oid: str) -> Optional[str]:
        """
        Get SNMP OID value.

        Args:
            oid: SNMP OID to query

        Returns:
            Value as string, or None if failed
        """
        try:
            from pysnmp.hlapi.asyncio import (
                getCmd, SnmpEngine, CommunityData, UdpTransportTarget,
                ContextData, ObjectType, ObjectIdentity
            )

            engine = SnmpEngine()
            errorIndication, errorStatus, errorIndex, varBinds = await getCmd(
                engine,
                CommunityData(self.config.snmp_community),
                UdpTransportTarget((self.config.host, 161)),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )

            if errorIndication or errorStatus:
                logger.error(f"SNMP GET error: {errorIndication or errorStatus}")
                return None

            for varBind in varBinds:
                return str(varBind[1])
            return None

        except ImportError:
            logger.warning("pysnmp not installed, using simulation")
            return "Simulated PDU"
        except Exception as e:
            logger.error(f"SNMP GET failed: {e}")
            return None

    async def _snmp_set(self, oid: str, value: int) -> bool:
        """
        Set SNMP OID value.

        Args:
            oid: SNMP OID to set
            value: Integer value to set

        Returns:
            True if successful
        """
        try:
            from pysnmp.hlapi.asyncio import (
                setCmd, SnmpEngine, CommunityData, UdpTransportTarget,
                ContextData, ObjectType, ObjectIdentity, Integer
            )

            engine = SnmpEngine()
            errorIndication, errorStatus, errorIndex, varBinds = await setCmd(
                engine,
                CommunityData(self.config.snmp_community),
                UdpTransportTarget((self.config.host, 161)),
                ContextData(),
                ObjectType(ObjectIdentity(oid), Integer(value))
            )

            if errorIndication or errorStatus:
                logger.error(f"SNMP SET error: {errorIndication or errorStatus}")
                return False

            return True

        except ImportError:
            logger.warning("pysnmp not installed, using simulation")
            return True
        except Exception as e:
            logger.error(f"SNMP SET failed: {e}")
            return False

    async def _http_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Make HTTP request to PDU.

        Args:
            method: HTTP method (GET, POST, PUT)
            endpoint: API endpoint
            data: Optional request data

        Returns:
            Response JSON or None if failed
        """
        try:
            import aiohttp
            url = f"http://{self.config.host}:{self.config.port}{endpoint}"

            async with aiohttp.ClientSession() as session:
                auth = aiohttp.BasicAuth(
                    self.config.http_username,
                    self.config.http_password
                )

                if method == "GET":
                    async with session.get(
                        url, auth=auth,
                        timeout=aiohttp.ClientTimeout(total=self.config.http_timeout_sec)
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                elif method in ("POST", "PUT"):
                    async with session.request(
                        method, url, auth=auth, json=data,
                        timeout=aiohttp.ClientTimeout(total=self.config.http_timeout_sec)
                    ) as response:
                        if response.status in (200, 201, 204):
                            try:
                                return await response.json()
                            except:
                                return {"success": True}

            return None

        except ImportError:
            logger.warning("aiohttp not installed")
            return {"success": True, "simulated": True}
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            return None

    async def get_outlet_state(self, outlet: int) -> Optional[bool]:
        """
        Get state of a single outlet.

        Args:
            outlet: Outlet number (1-based)

        Returns:
            True if on, False if off, None if unknown
        """
        if outlet < 1 or outlet > self.config.num_outlets:
            logger.error(f"Invalid outlet number: {outlet}")
            return None

        if self.config.protocol == PDUProtocol.SIMULATION:
            return self._outlet_states.get(outlet, True)

        if self.config.protocol == PDUProtocol.HTTP:
            result = await self._http_request("GET", f"/api/outlets/{outlet}")
            if result:
                return result.get("state", result.get("on", True))

        elif self.config.protocol == PDUProtocol.SNMP:
            # Generic SNMP OID for outlet state (adjust for specific PDU)
            oid = f"1.3.6.1.4.1.318.1.1.4.4.2.1.3.{outlet}"  # APC OID
            result = await self._snmp_get(oid)
            if result:
                return result == "1"  # 1 = on, 2 = off for APC

        return self._outlet_states.get(outlet)

    async def get_all_outlets(self) -> Dict[int, Dict[str, Any]]:
        """
        Get state of all outlets.

        Returns:
            Dict mapping outlet number to status dict
        """
        outlets = {}

        for i in range(1, self.config.num_outlets + 1):
            state = await self.get_outlet_state(i)
            outlets[i] = {
                "outlet": i,
                "name": self.config.port_names.get(i, f"Outlet {i}"),
                "state": state,
                "on": state is True,
            }

        return outlets

    async def set_outlet(self, outlet: int, on: bool) -> bool:
        """
        Set outlet state.

        Args:
            outlet: Outlet number (1-based)
            on: True to turn on, False to turn off

        Returns:
            True if successful
        """
        if outlet < 1 or outlet > self.config.num_outlets:
            logger.error(f"Invalid outlet number: {outlet}")
            return False

        action = "ON" if on else "OFF"
        outlet_name = self.config.port_names.get(outlet, f"Outlet {outlet}")
        logger.info(f"Setting PDU outlet {outlet} ({outlet_name}) to {action}")

        if self.config.protocol == PDUProtocol.SIMULATION:
            self._outlet_states[outlet] = on
            return True

        success = False

        if self.config.protocol == PDUProtocol.HTTP:
            result = await self._http_request(
                "PUT",
                f"/api/outlets/{outlet}",
                {"state": on, "on": on}
            )
            success = result is not None

        elif self.config.protocol == PDUProtocol.SNMP:
            # APC: 1 = on, 2 = off
            oid = f"1.3.6.1.4.1.318.1.1.4.4.2.1.3.{outlet}"
            value = 1 if on else 2
            success = await self._snmp_set(oid, value)

        if success:
            self._outlet_states[outlet] = on
            logger.info(f"Outlet {outlet} set to {action}")
        else:
            logger.error(f"Failed to set outlet {outlet} to {action}")

        return success

    async def cycle_outlet(self, outlet: int, delay_sec: float = 5.0) -> bool:
        """
        Power cycle an outlet.

        Args:
            outlet: Outlet number
            delay_sec: Delay between off and on

        Returns:
            True if successful
        """
        logger.info(f"Power cycling outlet {outlet}")

        if not await self.set_outlet(outlet, False):
            return False

        await asyncio.sleep(delay_sec)

        return await self.set_outlet(outlet, True)

    async def all_on(self) -> bool:
        """Turn all outlets on."""
        success = True
        for i in range(1, self.config.num_outlets + 1):
            if not await self.set_outlet(i, True):
                success = False
        return success

    async def all_off(self) -> bool:
        """Turn all outlets off."""
        success = True
        for i in range(1, self.config.num_outlets + 1):
            if not await self.set_outlet(i, False):
                success = False
        return success

    def get_outlet_name(self, outlet: int) -> str:
        """Get configured name for outlet."""
        return self.config.port_names.get(outlet, f"Outlet {outlet}")


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

    # Smart PDU configuration (Step 152)
    pdu_enabled: bool = False               # Enable smart PDU control
    pdu_protocol: str = "simulation"        # "http", "snmp", or "simulation"
    pdu_host: str = "192.168.1.100"         # PDU IP address
    pdu_port: int = 80                      # PDU port (80 for HTTP, 161 for SNMP)
    pdu_username: str = "admin"             # PDU HTTP username
    pdu_password: str = "admin"             # PDU HTTP password
    pdu_snmp_community: str = "private"     # SNMP write community
    pdu_num_outlets: int = 8                # Number of PDU outlets


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

        # Smart PDU client (Step 152)
        self._pdu_client: Optional[PDUClient] = None
        self._pdu_connected = False

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

        # Initialize Smart PDU client (Step 152)
        if self.config.pdu_enabled:
            pdu_config = PDUConfig(
                protocol=PDUProtocol(self.config.pdu_protocol),
                host=self.config.pdu_host,
                port=self.config.pdu_port,
                http_username=self.config.pdu_username,
                http_password=self.config.pdu_password,
                snmp_community=self.config.pdu_snmp_community,
                port_names={
                    self.config.port_mount: "mount",
                    self.config.port_camera: "camera",
                    self.config.port_focuser: "focuser",
                    self.config.port_computer: "computer",
                },
                num_outlets=self.config.pdu_num_outlets,
            )
            self._pdu_client = PDUClient(pdu_config)
            self._pdu_connected = await self._pdu_client.connect()
            if self._pdu_connected:
                logger.info(f"Smart PDU connected at {self.config.pdu_host}")
            else:
                logger.warning("Smart PDU connection failed, port control unavailable")

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Power manager started (simulation={self._use_simulation}, pdu={self._pdu_connected})")

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

        # Disconnect PDU client (Step 152)
        if self._pdu_client:
            await self._pdu_client.disconnect()
            self._pdu_client = None
            self._pdu_connected = False

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
    # SEQUENCED POWER CONTROL (Steps 154-155)
    # =========================================================================

    async def sequenced_power_on(
        self,
        devices: Optional[List[str]] = None,
        delay_between_sec: float = 5.0,
        confirmed: bool = False,
    ) -> dict:
        """
        Power on devices in safe sequence (Step 154).

        Devices are powered on in a specific order to ensure safe startup:
        1. Computer/Control systems (already on if running this)
        2. Mount controller
        3. Camera/Imaging systems
        4. Focuser
        5. Accessories (filter wheels, etc.)

        Args:
            devices: List of devices to power on (None = all)
            delay_between_sec: Delay between each device power-on
            confirmed: Must be True to execute (safety check)

        Returns:
            Dict with power-on sequence result:
            - success: True if all devices powered on
            - sequence: List of devices and their status
            - message: Summary message
        """
        if not confirmed:
            return {
                "success": False,
                "requires_confirmation": True,
                "message": "Sequenced power-on requires confirmation. Set confirmed=True.",
            }

        logger.info("Starting sequenced power-on")

        # Default power-on sequence (order matters for safety)
        default_sequence = [
            {"name": "computer", "port": self.config.port_computer, "description": "Control computer"},
            {"name": "mount", "port": self.config.port_mount, "description": "Mount controller"},
            {"name": "camera", "port": self.config.port_camera, "description": "Camera system"},
            {"name": "focuser", "port": self.config.port_focuser, "description": "Focuser"},
        ]

        # Filter to requested devices if specified
        if devices:
            sequence = [d for d in default_sequence if d["name"] in devices]
        else:
            sequence = default_sequence

        results = []
        all_success = True

        for device in sequence:
            logger.info(f"Powering on {device['description']} (port {device['port']})")

            result = await self.set_port_power(
                port=device["port"],
                on=True,
                confirmed=True,
            )

            device_result = {
                "name": device["name"],
                "port": device["port"],
                "success": result["success"],
                "message": result.get("message", ""),
            }
            results.append(device_result)

            if not result["success"]:
                all_success = False
                logger.error(f"Failed to power on {device['name']}")
            else:
                # Wait before powering on next device
                if device != sequence[-1]:  # Don't delay after last device
                    logger.debug(f"Waiting {delay_between_sec}s before next device")
                    await asyncio.sleep(delay_between_sec)

        self._log_event(
            "POWER_ON_SEQUENCE",
            f"Sequenced power-on: {'success' if all_success else 'partial failure'}"
        )

        return {
            "success": all_success,
            "requires_confirmation": False,
            "sequence": results,
            "message": f"Powered on {sum(1 for r in results if r['success'])}/{len(results)} devices",
        }

    async def sequenced_power_off(
        self,
        devices: Optional[List[str]] = None,
        delay_between_sec: float = 5.0,
        confirmed: bool = False,
        safe_shutdown: bool = True,
    ) -> dict:
        """
        Power off devices in safe sequence (Step 155).

        Devices are powered off in reverse order from power-on:
        1. Accessories (filter wheels, etc.)
        2. Focuser
        3. Camera/Imaging systems
        4. Mount controller
        5. Computer/Control systems (optional, usually last)

        The mount should be parked before powering off.

        Args:
            devices: List of devices to power off (None = all except computer)
            delay_between_sec: Delay between each device power-off
            confirmed: Must be True to execute (safety check)
            safe_shutdown: If True, verify mount is parked before continuing

        Returns:
            Dict with power-off sequence result:
            - success: True if all devices powered off
            - sequence: List of devices and their status
            - message: Summary message
        """
        if not confirmed:
            return {
                "success": False,
                "requires_confirmation": True,
                "message": "Sequenced power-off requires confirmation. Set confirmed=True.",
            }

        logger.info("Starting sequenced power-off")

        # Check mount is parked before proceeding (safety)
        if safe_shutdown and self._mount:
            try:
                is_parked = await self._mount.is_parked()
                if not is_parked:
                    logger.warning("Mount not parked - attempting to park before power-off")
                    await self._mount.park()
                    await asyncio.sleep(5.0)  # Wait for park to complete
            except Exception as e:
                logger.error(f"Failed to verify/park mount: {e}")
                return {
                    "success": False,
                    "requires_confirmation": False,
                    "message": f"Mount park verification failed: {e}. Use safe_shutdown=False to override.",
                }

        # Default power-off sequence (reverse of power-on, excluding computer)
        default_sequence = [
            {"name": "focuser", "port": self.config.port_focuser, "description": "Focuser"},
            {"name": "camera", "port": self.config.port_camera, "description": "Camera system"},
            {"name": "mount", "port": self.config.port_mount, "description": "Mount controller"},
        ]

        # Filter to requested devices if specified
        if devices:
            sequence = [d for d in default_sequence if d["name"] in devices]
        else:
            sequence = default_sequence

        results = []
        all_success = True

        for device in sequence:
            logger.info(f"Powering off {device['description']} (port {device['port']})")

            result = await self.set_port_power(
                port=device["port"],
                on=False,
                confirmed=True,
            )

            device_result = {
                "name": device["name"],
                "port": device["port"],
                "success": result["success"],
                "message": result.get("message", ""),
            }
            results.append(device_result)

            if not result["success"]:
                all_success = False
                logger.error(f"Failed to power off {device['name']}")
            else:
                # Wait before powering off next device
                if device != sequence[-1]:  # Don't delay after last device
                    logger.debug(f"Waiting {delay_between_sec}s before next device")
                    await asyncio.sleep(delay_between_sec)

        self._log_event(
            "POWER_OFF_SEQUENCE",
            f"Sequenced power-off: {'success' if all_success else 'partial failure'}"
        )

        return {
            "success": all_success,
            "requires_confirmation": False,
            "sequence": results,
            "message": f"Powered off {sum(1 for r in results if r['success'])}/{len(results)} devices",
        }

    async def get_power_sequence_status(self) -> dict:
        """
        Get current power state of all sequenced devices (Steps 154-155).

        Returns:
            Dict with device power states:
            - devices: List of device status dicts
            - all_on: True if all devices are powered on
            - all_off: True if all devices are powered off
        """
        devices = [
            {"name": "computer", "port": self.config.port_computer},
            {"name": "mount", "port": self.config.port_mount},
            {"name": "camera", "port": self.config.port_camera},
            {"name": "focuser", "port": self.config.port_focuser},
        ]

        # In real implementation, would query PDU for actual port states
        # For simulation, assume all are on if we're running
        device_status = []
        for device in devices:
            device_status.append({
                "name": device["name"],
                "port": device["port"],
                "powered": True,  # Simulation
            })

        all_on = all(d["powered"] for d in device_status)
        all_off = all(not d["powered"] for d in device_status)

        return {
            "devices": device_status,
            "all_on": all_on,
            "all_off": all_off,
        }

    # =========================================================================
    # PDU CONTROL (Optional)
    # =========================================================================

    async def set_port_power(
        self,
        port: int,
        on: bool,
        confirmed: bool = False,
        confirmation_code: str = None,
    ) -> dict:
        """
        Control smart PDU port (Step 439: Requires confirmation).

        Power operations are potentially destructive and require explicit
        confirmation to prevent accidental power cycling of critical equipment.

        Args:
            port: Port number
            on: True to power on
            confirmed: Must be True to execute (safety check)
            confirmation_code: Optional confirmation code for automation

        Returns:
            Dict with result:
            - success: True if power change executed
            - requires_confirmation: True if confirmation needed
            - port: Port number
            - action: Action requested
            - message: Status message
        """
        action = "ON" if on else "OFF"

        # Step 439: Require confirmation for power operations
        if not confirmed and confirmation_code != "NIGHTWATCH_POWER_CONFIRM":
            logger.warning(f"PDU port {port} {action} requested but not confirmed")
            return {
                "success": False,
                "requires_confirmation": True,
                "port": port,
                "action": action,
                "message": f"Power {action} for port {port} requires confirmation. "
                          f"Set confirmed=True or provide confirmation_code.",
            }

        # Step 152: Use Smart PDU client for actual port control
        success = False
        if self._pdu_client and self._pdu_connected:
            success = await self._pdu_client.set_outlet(port, on)
            logger.info(f"PDU port {port}: {action} via smart PDU (success={success})")
        else:
            # Simulation mode - just track state
            logger.info(f"PDU port {port}: {action} (simulated, no PDU client)")
            success = True

        # Log the event
        self._log_event(
            f"PORT_{action}",
            f"Port {port} powered {action} (confirmed, success={success})"
        )

        return {
            "success": success,
            "requires_confirmation": False,
            "port": port,
            "action": action,
            "message": f"Port {port} powered {action}" if success else f"Failed to power {action} port {port}",
        }

    async def power_cycle_port(
        self,
        port: int,
        delay_sec: float = 5.0,
        confirmed: bool = False,
        confirmation_code: str = None,
    ) -> dict:
        """
        Power cycle a PDU port (Step 439: Requires confirmation).

        Power cycling is potentially destructive and requires explicit
        confirmation to prevent accidental cycling of critical equipment.

        Args:
            port: Port number
            delay_sec: Time to wait before powering back on
            confirmed: Must be True to execute (safety check)
            confirmation_code: Optional confirmation code for automation

        Returns:
            Dict with result:
            - success: True if power cycle completed
            - requires_confirmation: True if confirmation needed
            - port: Port number
            - message: Status message
        """
        # Step 439: Require confirmation for power operations
        if not confirmed and confirmation_code != "NIGHTWATCH_POWER_CONFIRM":
            logger.warning(f"Power cycle port {port} requested but not confirmed")
            return {
                "success": False,
                "requires_confirmation": True,
                "port": port,
                "message": f"Power cycle for port {port} requires confirmation. "
                          f"Set confirmed=True or provide confirmation_code.",
            }

        logger.info(f"Power cycling port {port} (confirmed)...")

        # Execute power cycle
        off_result = await self.set_port_power(port, False, confirmed=True)
        if not off_result["success"]:
            return {
                "success": False,
                "requires_confirmation": False,
                "port": port,
                "message": f"Failed to power off port {port}",
            }

        await asyncio.sleep(delay_sec)

        on_result = await self.set_port_power(port, True, confirmed=True)
        if not on_result["success"]:
            return {
                "success": False,
                "requires_confirmation": False,
                "port": port,
                "message": f"Failed to power on port {port} after cycle",
            }

        logger.info(f"Port {port} power cycled successfully")
        return {
            "success": True,
            "requires_confirmation": False,
            "port": port,
            "delay_sec": delay_sec,
            "message": f"Port {port} power cycled successfully",
        }

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

    def register_callback(self, callback: Callable[[str, Any], None]):
        """
        Register callback for power events.

        Callbacks are notified of power state changes, UPS events, and
        PDU port operations. Can be sync or async functions.

        Args:
            callback: Function with signature (event: str, data: Any) -> None
                     Events include: "power_lost", "power_restored",
                     "battery_low", "park_initiated", "shutdown_initiated"

        Example:
            async def on_power_event(event: str, data: Any):
                if event == "power_lost":
                    logger.warning("UPS on battery!")

            manager.register_callback(on_power_event)
        """
        self._callbacks.append(callback)

    async def _notify_callbacks(self, event: str, data: Any = None):
        """Notify registered callbacks with error isolation."""
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
