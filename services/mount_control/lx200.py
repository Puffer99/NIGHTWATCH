"""
NIGHTWATCH Mount Control Service
LX200 Protocol Client for OnStepX

This module implements the Meade LX200 serial protocol for communication
with the OnStepX telescope controller running on Teensy 4.1.

Reference: LX200 Command Set (Meade Telescope Serial Command Protocol)
"""

import socket
import serial
import threading
import time
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class ConnectionType(Enum):
    SERIAL = "serial"
    TCP = "tcp"


class PierSide(Enum):
    EAST = "E"
    WEST = "W"
    UNKNOWN = "?"


class TrackingRate(Enum):
    SIDEREAL = "TQ"
    LUNAR = "TL"
    SOLAR = "TS"
    KING = "TK"


@dataclass
class MountStatus:
    """Current mount status."""
    ra_hours: float
    ra_minutes: float
    ra_seconds: float
    dec_degrees: float
    dec_minutes: float
    dec_seconds: float
    is_tracking: bool
    is_slewing: bool
    is_parked: bool
    pier_side: PierSide
    altitude: Optional[float] = None
    azimuth: Optional[float] = None


class LX200Client:
    """
    LX200 Protocol client for OnStepX mount control.

    Supports both serial (USB) and TCP/IP connections to the controller.
    """

    TERMINATOR = "#"
    COMMAND_TIMEOUT = 5.0

    def __init__(
        self,
        connection_type: ConnectionType = ConnectionType.TCP,
        host: str = "192.168.1.100",
        port: int = 9999,
        serial_port: str = "/dev/ttyUSB0",
        baudrate: int = 9600
    ):
        self.connection_type = connection_type
        self.host = host
        self.port = port
        self.serial_port = serial_port
        self.baudrate = baudrate

        self._connection = None
        self._lock = threading.Lock()
        self._connected = False

    def connect(self) -> bool:
        """Establish connection to mount controller."""
        with self._lock:
            try:
                if self.connection_type == ConnectionType.TCP:
                    self._connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self._connection.settimeout(self.COMMAND_TIMEOUT)
                    self._connection.connect((self.host, self.port))
                else:
                    self._connection = serial.Serial(
                        port=self.serial_port,
                        baudrate=self.baudrate,
                        timeout=self.COMMAND_TIMEOUT
                    )

                self._connected = True
                return True
            except Exception as e:
                print(f"Connection failed: {e}")
                self._connected = False
                return False

    def disconnect(self):
        """Close connection to mount controller."""
        with self._lock:
            if self._connection:
                self._connection.close()
                self._connection = None
            self._connected = False

    def _send_command(self, command: str) -> Optional[str]:
        """Send command and receive response."""
        if not self._connected:
            return None

        with self._lock:
            try:
                # Format command with colon prefix
                full_cmd = f":{command}{self.TERMINATOR}"

                if self.connection_type == ConnectionType.TCP:
                    self._connection.sendall(full_cmd.encode('ascii'))
                    response = self._receive_tcp()
                else:
                    self._connection.write(full_cmd.encode('ascii'))
                    response = self._receive_serial()

                return response
            except Exception as e:
                print(f"Command failed: {e}")
                return None

    def _receive_tcp(self) -> str:
        """Receive response over TCP."""
        data = b""
        while True:
            chunk = self._connection.recv(1024)
            if not chunk:
                break
            data += chunk
            if b"#" in chunk:
                break
        return data.decode('ascii').rstrip('#')

    def _receive_serial(self) -> str:
        """Receive response over serial."""
        response = self._connection.read_until(b'#')
        return response.decode('ascii').rstrip('#')

    # =========================================================================
    # POSITION QUERIES
    # =========================================================================

    def get_ra(self) -> Optional[str]:
        """Get current Right Ascension (HH:MM:SS format)."""
        return self._send_command("GR")

    def get_dec(self) -> Optional[str]:
        """Get current Declination (sDD*MM:SS format)."""
        return self._send_command("GD")

    def get_altitude(self) -> Optional[str]:
        """Get current Altitude (sDD*MM'SS format)."""
        return self._send_command("GA")

    def get_azimuth(self) -> Optional[str]:
        """Get current Azimuth (DDD*MM'SS format)."""
        return self._send_command("GZ")

    def get_pier_side(self) -> PierSide:
        """Get current pier side (E/W)."""
        response = self._send_command("Gm")
        if response == "E":
            return PierSide.EAST
        elif response == "W":
            return PierSide.WEST
        return PierSide.UNKNOWN

    def get_status(self) -> Optional[MountStatus]:
        """Get comprehensive mount status."""
        ra = self.get_ra()
        dec = self.get_dec()

        if not ra or not dec:
            return None

        # Parse RA (HH:MM:SS)
        ra_match = re.match(r"(\d{2}):(\d{2}):(\d{2})", ra)
        if ra_match:
            ra_h, ra_m, ra_s = map(float, ra_match.groups())
        else:
            return None

        # Parse DEC (sDD*MM:SS or sDD*MM'SS)
        dec_match = re.match(r"([+-]?\d{2})[*°](\d{2})[:'′](\d{2})", dec)
        if dec_match:
            dec_d = float(dec_match.group(1))
            dec_m = float(dec_match.group(2))
            dec_s = float(dec_match.group(3))
        else:
            return None

        return MountStatus(
            ra_hours=ra_h,
            ra_minutes=ra_m,
            ra_seconds=ra_s,
            dec_degrees=dec_d,
            dec_minutes=dec_m,
            dec_seconds=dec_s,
            is_tracking=self.is_tracking(),
            is_slewing=self.is_slewing(),
            is_parked=self.is_parked(),
            pier_side=self.get_pier_side()
        )

    # =========================================================================
    # MOTION CONTROL
    # =========================================================================

    def goto_ra_dec(self, ra: str, dec: str) -> bool:
        """
        Slew to RA/DEC coordinates.

        Args:
            ra: Right Ascension in HH:MM:SS format
            dec: Declination in sDD*MM:SS format

        Returns:
            True if slew initiated successfully
        """
        # Set target RA
        ra_result = self._send_command(f"Sr{ra}")
        if ra_result != "1":
            return False

        # Set target DEC
        dec_result = self._send_command(f"Sd{dec}")
        if dec_result != "1":
            return False

        # Initiate slew
        slew_result = self._send_command("MS")
        return slew_result == "0"

    def goto_alt_az(self, alt: str, az: str) -> bool:
        """
        Slew to Altitude/Azimuth coordinates.

        Args:
            alt: Altitude in sDD*MM format
            az: Azimuth in DDD*MM format

        Returns:
            True if slew initiated successfully
        """
        # Set target altitude
        self._send_command(f"Sa{alt}")

        # Set target azimuth
        self._send_command(f"Sz{az}")

        # Initiate slew
        slew_result = self._send_command("MA")
        return slew_result == "0"

    def sync(self, ra: str, dec: str) -> bool:
        """Sync mount to specified coordinates."""
        # Set target coordinates
        self._send_command(f"Sr{ra}")
        self._send_command(f"Sd{dec}")

        # Sync
        result = self._send_command("CM")
        return result is not None

    def stop(self):
        """Stop all mount motion."""
        self._send_command("Q")

    def stop_axis(self, axis: str):
        """
        Stop motion on specific axis.

        Args:
            axis: 'e' (east), 'w' (west), 'n' (north), 's' (south)
        """
        self._send_command(f"Q{axis}")

    # =========================================================================
    # TRACKING CONTROL
    # =========================================================================

    def start_tracking(self) -> bool:
        """Enable sidereal tracking."""
        result = self._send_command("Te")
        return result == "1"

    def stop_tracking(self) -> bool:
        """Disable tracking."""
        result = self._send_command("Td")
        return result == "1"

    def set_tracking_rate(self, rate: TrackingRate) -> bool:
        """Set tracking rate (sidereal, lunar, solar, King)."""
        result = self._send_command(rate.value)
        return result is not None

    def is_tracking(self) -> bool:
        """Check if mount is currently tracking."""
        result = self._send_command("GW")
        if result and len(result) >= 1:
            return result[0] == "T"
        return False

    def is_slewing(self) -> bool:
        """Check if mount is currently slewing."""
        result = self._send_command("GW")
        if result and len(result) >= 2:
            return result[1] == "S"
        return False

    # =========================================================================
    # PARK CONTROL
    # =========================================================================

    def park(self) -> bool:
        """Park the mount at home position."""
        result = self._send_command("hP")
        return result == "1"

    def unpark(self) -> bool:
        """Unpark the mount."""
        result = self._send_command("hR")
        return result == "1"

    def is_parked(self) -> bool:
        """Check if mount is parked."""
        result = self._send_command("GU")
        if result:
            return "P" in result
        return False

    def set_park_position(self) -> bool:
        """Set current position as park position."""
        result = self._send_command("hQ")
        return result == "1"

    # =========================================================================
    # HOMING
    # =========================================================================

    def home(self) -> bool:
        """Return mount to home position."""
        result = self._send_command("hC")
        return result == "1"

    def home_reset(self) -> bool:
        """Reset home position."""
        result = self._send_command("hF")
        return result == "1"

    # =========================================================================
    # SITE INFORMATION
    # =========================================================================

    def get_latitude(self) -> Optional[str]:
        """Get site latitude."""
        return self._send_command("Gt")

    def get_longitude(self) -> Optional[str]:
        """Get site longitude."""
        return self._send_command("Gg")

    def set_latitude(self, lat: str) -> bool:
        """Set site latitude (sDD*MM format)."""
        result = self._send_command(f"St{lat}")
        return result == "1"

    def set_longitude(self, lon: str) -> bool:
        """Set site longitude (sDDD*MM format)."""
        result = self._send_command(f"Sg{lon}")
        return result == "1"

    def get_local_time(self) -> Optional[str]:
        """Get local time from mount."""
        return self._send_command("GL")

    def get_sidereal_time(self) -> Optional[str]:
        """Get local sidereal time."""
        return self._send_command("GS")

    # =========================================================================
    # UTILITY
    # =========================================================================

    def get_firmware_info(self) -> Optional[str]:
        """Get OnStepX firmware information."""
        return self._send_command("GVP")

    def get_firmware_version(self) -> Optional[str]:
        """Get firmware version number."""
        return self._send_command("GVN")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def ra_to_hours(ra_str: str) -> float:
    """Convert RA string (HH:MM:SS) to decimal hours."""
    match = re.match(r"(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)", ra_str)
    if match:
        h, m, s = map(float, match.groups())
        return h + m/60 + s/3600
    return 0.0


def dec_to_degrees(dec_str: str) -> float:
    """Convert DEC string (sDD*MM:SS) to decimal degrees."""
    match = re.match(r"([+-]?\d{2})[*°](\d{2})[:'′](\d{2}(?:\.\d+)?)", dec_str)
    if match:
        d = float(match.group(1))
        m = float(match.group(2))
        s = float(match.group(3))
        sign = -1 if d < 0 else 1
        return sign * (abs(d) + m/60 + s/3600)
    return 0.0


def hours_to_ra(hours: float) -> str:
    """Convert decimal hours to RA string (HH:MM:SS)."""
    h = int(hours)
    m = int((hours - h) * 60)
    s = ((hours - h) * 60 - m) * 60
    return f"{h:02d}:{m:02d}:{s:05.2f}"


def degrees_to_dec(degrees: float) -> str:
    """Convert decimal degrees to DEC string (sDD*MM:SS)."""
    sign = "+" if degrees >= 0 else "-"
    degrees = abs(degrees)
    d = int(degrees)
    m = int((degrees - d) * 60)
    s = ((degrees - d) * 60 - m) * 60
    return f"{sign}{d:02d}*{m:02d}:{s:05.2f}"


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    # Example usage
    mount = LX200Client(
        connection_type=ConnectionType.TCP,
        host="192.168.1.100",
        port=9999
    )

    if mount.connect():
        print(f"Firmware: {mount.get_firmware_info()}")
        print(f"Version: {mount.get_firmware_version()}")

        status = mount.get_status()
        if status:
            print(f"RA: {status.ra_hours}h {status.ra_minutes}m {status.ra_seconds}s")
            print(f"DEC: {status.dec_degrees}° {status.dec_minutes}' {status.dec_seconds}\"")
            print(f"Tracking: {status.is_tracking}")
            print(f"Parked: {status.is_parked}")

        mount.disconnect()
    else:
        print("Failed to connect to mount")
