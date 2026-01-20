"""
NIGHTWATCH AAG CloudWatcher Integration (Steps 201-202, 206)

Provides cloud sensing data from AAG CloudWatcher Solo for observatory safety.

The CloudWatcher measures:
- Sky temperature (infrared) for cloud detection
- Ambient temperature
- Rain sensor (capacitive)
- Light sensor (day/night detection)
- Wind sensor (optional external)

Protocol: Serial/TCP with simple command/response format
Commands: A (ambient), C (cloud/sky), E (rain), D (daylight), K (switch), Q (all)
"""

import asyncio
import logging
import socket
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Callable, List

logger = logging.getLogger("NIGHTWATCH.CloudWatcher")


class CloudCondition(Enum):
    """Cloud condition assessment based on sky-ambient temperature difference."""
    CLEAR = "clear"           # Sky temp < ambient - 30°C
    MOSTLY_CLEAR = "mostly_clear"  # Sky temp < ambient - 20°C
    PARTLY_CLOUDY = "partly_cloudy"  # Sky temp < ambient - 10°C
    CLOUDY = "cloudy"         # Sky temp >= ambient - 10°C
    OVERCAST = "overcast"     # Sky temp close to ambient
    UNKNOWN = "unknown"


class RainCondition(Enum):
    """Rain sensor condition."""
    DRY = "dry"
    WET = "wet"
    RAIN = "rain"
    UNKNOWN = "unknown"


class DaylightCondition(Enum):
    """Daylight/darkness condition."""
    DARK = "dark"           # Nighttime
    TWILIGHT = "twilight"   # Dawn/dusk
    DAYLIGHT = "daylight"   # Daytime


@dataclass
class CloudWatcherData:
    """Current conditions from CloudWatcher sensor."""
    timestamp: datetime

    # Temperature readings
    sky_temp_c: float              # Infrared sky temperature
    ambient_temp_c: float          # Ambient air temperature
    sky_ambient_diff_c: float      # Difference (key metric for clouds)

    # Rain sensor
    rain_frequency: int            # Capacitive sensor frequency
    rain_condition: RainCondition

    # Light sensor
    brightness: int                # Light level
    daylight_condition: DaylightCondition

    # Switch status (safe/unsafe output)
    switch_safe: bool

    # Heater
    heater_pwm: int                # Heater power (0-100%)

    # Derived conditions
    cloud_condition: CloudCondition
    safe_to_observe: bool


@dataclass
class CloudThresholds:
    """
    Cloud detection thresholds (Step 206).

    These thresholds determine cloud condition based on the difference
    between sky (infrared) temperature and ambient temperature.
    Clear skies radiate heat to space and appear much colder than ambient.
    """
    clear_threshold_c: float = -30.0       # Sky-ambient diff for "clear"
    mostly_clear_threshold_c: float = -20.0
    partly_cloudy_threshold_c: float = -10.0
    cloudy_threshold_c: float = -5.0       # Above this = overcast

    # Rain sensor thresholds
    dry_frequency: int = 2200              # Typical dry reading
    wet_frequency: int = 1800              # Getting wet
    rain_frequency: int = 1500             # Active rain

    # Brightness thresholds
    dark_threshold: int = 50               # Nighttime
    twilight_threshold: int = 5000         # Dawn/dusk

    def classify_clouds(self, sky_ambient_diff: float) -> CloudCondition:
        """Classify cloud condition from sky-ambient temperature difference."""
        if sky_ambient_diff < self.clear_threshold_c:
            return CloudCondition.CLEAR
        elif sky_ambient_diff < self.mostly_clear_threshold_c:
            return CloudCondition.MOSTLY_CLEAR
        elif sky_ambient_diff < self.partly_cloudy_threshold_c:
            return CloudCondition.PARTLY_CLOUDY
        elif sky_ambient_diff < self.cloudy_threshold_c:
            return CloudCondition.CLOUDY
        else:
            return CloudCondition.OVERCAST

    def classify_rain(self, frequency: int) -> RainCondition:
        """Classify rain condition from sensor frequency."""
        if frequency >= self.dry_frequency:
            return RainCondition.DRY
        elif frequency >= self.wet_frequency:
            return RainCondition.WET
        else:
            return RainCondition.RAIN

    def classify_daylight(self, brightness: int) -> DaylightCondition:
        """Classify daylight condition from brightness sensor."""
        if brightness < self.dark_threshold:
            return DaylightCondition.DARK
        elif brightness < self.twilight_threshold:
            return DaylightCondition.TWILIGHT
        else:
            return DaylightCondition.DAYLIGHT


class CloudWatcherClient:
    """
    Client for AAG CloudWatcher Solo sensor (Steps 201-202).

    Communicates via serial or TCP connection using simple
    command/response protocol.

    Usage:
        client = CloudWatcherClient(host="192.168.1.100", port=8081)
        await client.connect()
        data = await client.get_conditions()
        print(f"Sky temp: {data.sky_temp_c}°C, Clouds: {data.cloud_condition.value}")
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8081,
        timeout: float = 5.0,
        thresholds: Optional[CloudThresholds] = None
    ):
        """
        Initialize CloudWatcher client.

        Args:
            host: CloudWatcher host (serial-to-TCP bridge)
            port: TCP port (default 8081)
            timeout: Connection timeout in seconds
            thresholds: Cloud detection thresholds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.thresholds = thresholds or CloudThresholds()

        self._socket: Optional[socket.socket] = None
        self._connected = False
        self._last_data: Optional[CloudWatcherData] = None
        self._callbacks: List[Callable] = []

    @property
    def connected(self) -> bool:
        """Check if connected to CloudWatcher."""
        return self._connected

    @property
    def last_data(self) -> Optional[CloudWatcherData]:
        """Get most recent sensor data."""
        return self._last_data

    async def connect(self) -> bool:
        """
        Connect to CloudWatcher sensor.

        Returns:
            True if connected successfully
        """
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            self._socket.connect((self.host, self.port))
            self._connected = True
            logger.info(f"Connected to CloudWatcher at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to CloudWatcher: {e}")
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from CloudWatcher."""
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        self._connected = False
        logger.info("Disconnected from CloudWatcher")

    def _send_command(self, cmd: str) -> Optional[str]:
        """Send command and receive response (Step 202)."""
        if not self._socket:
            return None
        try:
            self._socket.sendall(cmd.encode())
            response = self._socket.recv(256).decode().strip()
            return response
        except Exception as e:
            logger.error(f"CloudWatcher communication error: {e}")
            return None

    def _parse_response(self, response: str) -> tuple:
        """
        Parse CloudWatcher response format (Step 202).

        Format: !CODE value1 value2 ... checksum
        """
        if not response or not response.startswith("!"):
            return None, []
        parts = response[1:].split()
        if len(parts) < 2:
            return None, []
        code = parts[0]
        values = parts[1:-1]  # Exclude checksum
        return code, values

    async def get_ambient_temp(self) -> Optional[float]:
        """Get ambient temperature (command A)."""
        response = self._send_command("A")
        code, values = self._parse_response(response)
        if code == "A" and values:
            return int(values[0]) / 10.0
        return None

    async def get_sky_temp(self) -> Optional[float]:
        """Get sky/cloud temperature (command C)."""
        response = self._send_command("C")
        code, values = self._parse_response(response)
        if code == "C" and values:
            return int(values[0]) / 10.0
        return None

    async def get_rain_frequency(self) -> Optional[int]:
        """Get rain sensor frequency (command E)."""
        response = self._send_command("E")
        code, values = self._parse_response(response)
        if code == "E" and values:
            return int(values[0])
        return None

    async def get_brightness(self) -> Optional[int]:
        """Get brightness/daylight sensor (command D)."""
        response = self._send_command("D")
        code, values = self._parse_response(response)
        if code == "D" and values:
            return int(values[0])
        return None

    async def get_switch_status(self) -> Optional[bool]:
        """Get switch status (command K)."""
        response = self._send_command("K")
        code, values = self._parse_response(response)
        if code == "K" and values:
            return int(values[0]) == 1
        return None

    async def get_conditions(self) -> Optional[CloudWatcherData]:
        """
        Get all sensor conditions (command Q).

        Returns complete CloudWatcherData with all readings.
        """
        if not self._connected:
            # Try to reconnect
            if not await self.connect():
                return None

        response = self._send_command("Q")
        code, values = self._parse_response(response)

        if code != "Q" or len(values) < 5:
            # Fall back to individual queries
            return await self._get_conditions_individual()

        try:
            sky_temp = int(values[0]) / 10.0
            ambient_temp = int(values[1]) / 10.0
            rain_freq = int(values[2])
            heater_pwm = int(values[3])
            brightness = int(values[4])
            switch_safe = int(values[5]) == 1 if len(values) > 5 else True

            sky_ambient_diff = sky_temp - ambient_temp

            data = CloudWatcherData(
                timestamp=datetime.now(),
                sky_temp_c=sky_temp,
                ambient_temp_c=ambient_temp,
                sky_ambient_diff_c=sky_ambient_diff,
                rain_frequency=rain_freq,
                rain_condition=self.thresholds.classify_rain(rain_freq),
                brightness=brightness,
                daylight_condition=self.thresholds.classify_daylight(brightness),
                switch_safe=switch_safe,
                heater_pwm=heater_pwm,
                cloud_condition=self.thresholds.classify_clouds(sky_ambient_diff),
                safe_to_observe=self._is_safe(sky_ambient_diff, rain_freq, switch_safe)
            )

            self._last_data = data
            await self._notify_callbacks(data)
            return data

        except (ValueError, IndexError) as e:
            logger.error(f"Failed to parse CloudWatcher response: {e}")
            return None

    async def _get_conditions_individual(self) -> Optional[CloudWatcherData]:
        """Get conditions using individual commands (fallback)."""
        try:
            sky_temp = await self.get_sky_temp() or 0.0
            ambient_temp = await self.get_ambient_temp() or 0.0
            rain_freq = await self.get_rain_frequency() or 2300
            brightness = await self.get_brightness() or 0
            switch_safe = await self.get_switch_status()
            if switch_safe is None:
                switch_safe = True

            sky_ambient_diff = sky_temp - ambient_temp

            data = CloudWatcherData(
                timestamp=datetime.now(),
                sky_temp_c=sky_temp,
                ambient_temp_c=ambient_temp,
                sky_ambient_diff_c=sky_ambient_diff,
                rain_frequency=rain_freq,
                rain_condition=self.thresholds.classify_rain(rain_freq),
                brightness=brightness,
                daylight_condition=self.thresholds.classify_daylight(brightness),
                switch_safe=switch_safe,
                heater_pwm=0,
                cloud_condition=self.thresholds.classify_clouds(sky_ambient_diff),
                safe_to_observe=self._is_safe(sky_ambient_diff, rain_freq, switch_safe)
            )

            self._last_data = data
            return data

        except Exception as e:
            logger.error(f"Failed to get individual conditions: {e}")
            return None

    def _is_safe(self, sky_ambient_diff: float, rain_freq: int, switch_safe: bool) -> bool:
        """Determine if conditions are safe for observing."""
        # Must pass hardware safety switch
        if not switch_safe:
            return False

        # Check for rain
        rain_condition = self.thresholds.classify_rain(rain_freq)
        if rain_condition in [RainCondition.WET, RainCondition.RAIN]:
            return False

        # Check for heavy clouds
        cloud_condition = self.thresholds.classify_clouds(sky_ambient_diff)
        if cloud_condition == CloudCondition.OVERCAST:
            return False

        return True

    def register_callback(self, callback: Callable):
        """Register callback for data updates."""
        self._callbacks.append(callback)

    async def _notify_callbacks(self, data: CloudWatcherData):
        """Notify registered callbacks."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    # =========================================================================
    # CALIBRATION (Step 206)
    # =========================================================================

    def calibrate_clear_sky(self, measured_diff: float):
        """
        Calibrate clear sky threshold from current measurement (Step 206).

        Call this on a confirmed clear night to set the baseline.

        Args:
            measured_diff: Current sky-ambient temperature difference
        """
        # Set clear threshold slightly above current reading
        self.thresholds.clear_threshold_c = measured_diff + 5.0
        self.thresholds.mostly_clear_threshold_c = measured_diff + 15.0
        self.thresholds.partly_cloudy_threshold_c = measured_diff + 25.0
        self.thresholds.cloudy_threshold_c = measured_diff + 30.0

        logger.info(f"Calibrated clear sky threshold: {self.thresholds.clear_threshold_c}°C")

    def calibrate_rain_sensor(self, dry_reading: int):
        """
        Calibrate rain sensor from current dry reading (Step 206).

        Call this when sensor is confirmed dry.

        Args:
            dry_reading: Current rain sensor frequency when dry
        """
        self.thresholds.dry_frequency = dry_reading
        self.thresholds.wet_frequency = int(dry_reading * 0.8)
        self.thresholds.rain_frequency = int(dry_reading * 0.6)

        logger.info(f"Calibrated rain sensor: dry={dry_reading}")

    def get_calibration(self) -> dict:
        """Get current calibration values."""
        return {
            "clear_threshold_c": self.thresholds.clear_threshold_c,
            "mostly_clear_threshold_c": self.thresholds.mostly_clear_threshold_c,
            "partly_cloudy_threshold_c": self.thresholds.partly_cloudy_threshold_c,
            "cloudy_threshold_c": self.thresholds.cloudy_threshold_c,
            "dry_frequency": self.thresholds.dry_frequency,
            "wet_frequency": self.thresholds.wet_frequency,
            "rain_frequency": self.thresholds.rain_frequency,
        }

    def set_calibration(self, calibration: dict):
        """Set calibration values from dict."""
        if "clear_threshold_c" in calibration:
            self.thresholds.clear_threshold_c = calibration["clear_threshold_c"]
        if "mostly_clear_threshold_c" in calibration:
            self.thresholds.mostly_clear_threshold_c = calibration["mostly_clear_threshold_c"]
        if "partly_cloudy_threshold_c" in calibration:
            self.thresholds.partly_cloudy_threshold_c = calibration["partly_cloudy_threshold_c"]
        if "cloudy_threshold_c" in calibration:
            self.thresholds.cloudy_threshold_c = calibration["cloudy_threshold_c"]
        if "dry_frequency" in calibration:
            self.thresholds.dry_frequency = calibration["dry_frequency"]
        if "wet_frequency" in calibration:
            self.thresholds.wet_frequency = calibration["wet_frequency"]
        if "rain_frequency" in calibration:
            self.thresholds.rain_frequency = calibration["rain_frequency"]

        logger.info("Loaded calibration values")
