"""
Unit tests for LX200Client - NIGHTWATCH Mount Control Service

Tests the base LX200 protocol client for OnStepX mount control.
Validates Phase 2 (Enhanced Mount Control) foundation.

Co-authored-by: Claude <noreply@anthropic.com>
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import socket
import serial

from services.mount_control.lx200 import (
    LX200Client,
    ConnectionType,
    PierSide,
    TrackingRate,
    MountStatus,
    ra_to_hours,
    dec_to_degrees,
    hours_to_ra,
    degrees_to_dec,
)


class TestConnectionType:
    """Test ConnectionType enum."""

    def test_serial_value(self):
        assert ConnectionType.SERIAL.value == "serial"

    def test_tcp_value(self):
        assert ConnectionType.TCP.value == "tcp"


class TestPierSide:
    """Test PierSide enum."""

    def test_east_value(self):
        assert PierSide.EAST.value == "E"

    def test_west_value(self):
        assert PierSide.WEST.value == "W"

    def test_unknown_value(self):
        assert PierSide.UNKNOWN.value == "?"


class TestTrackingRate:
    """Test TrackingRate enum."""

    def test_sidereal_value(self):
        assert TrackingRate.SIDEREAL.value == "TQ"

    def test_lunar_value(self):
        assert TrackingRate.LUNAR.value == "TL"

    def test_solar_value(self):
        assert TrackingRate.SOLAR.value == "TS"

    def test_king_value(self):
        assert TrackingRate.KING.value == "TK"


class TestMountStatus:
    """Test MountStatus dataclass."""

    def test_create_status(self):
        status = MountStatus(
            ra_hours=12.0,
            ra_minutes=30.0,
            ra_seconds=45.0,
            dec_degrees=45.0,
            dec_minutes=15.0,
            dec_seconds=30.0,
            is_tracking=True,
            is_slewing=False,
            is_parked=False,
            pier_side=PierSide.EAST,
        )
        assert status.ra_hours == 12.0
        assert status.ra_minutes == 30.0
        assert status.ra_seconds == 45.0
        assert status.dec_degrees == 45.0
        assert status.dec_minutes == 15.0
        assert status.dec_seconds == 30.0
        assert status.is_tracking is True
        assert status.is_slewing is False
        assert status.is_parked is False
        assert status.pier_side == PierSide.EAST

    def test_optional_altitude_azimuth(self):
        status = MountStatus(
            ra_hours=0.0,
            ra_minutes=0.0,
            ra_seconds=0.0,
            dec_degrees=0.0,
            dec_minutes=0.0,
            dec_seconds=0.0,
            is_tracking=False,
            is_slewing=False,
            is_parked=True,
            pier_side=PierSide.UNKNOWN,
            altitude=45.5,
            azimuth=180.0,
        )
        assert status.altitude == 45.5
        assert status.azimuth == 180.0

    def test_defaults_none_for_altitude_azimuth(self):
        status = MountStatus(
            ra_hours=0.0,
            ra_minutes=0.0,
            ra_seconds=0.0,
            dec_degrees=0.0,
            dec_minutes=0.0,
            dec_seconds=0.0,
            is_tracking=False,
            is_slewing=False,
            is_parked=False,
            pier_side=PierSide.UNKNOWN,
        )
        assert status.altitude is None
        assert status.azimuth is None


class TestLX200ClientInit:
    """Test LX200Client initialization."""

    def test_default_tcp_connection(self):
        client = LX200Client()
        assert client.connection_type == ConnectionType.TCP
        assert client.host == "192.168.1.100"
        assert client.port == 9999
        assert client._connected is False

    def test_serial_connection_params(self):
        client = LX200Client(
            connection_type=ConnectionType.SERIAL,
            serial_port="/dev/ttyUSB1",
            baudrate=115200,
        )
        assert client.connection_type == ConnectionType.SERIAL
        assert client.serial_port == "/dev/ttyUSB1"
        assert client.baudrate == 115200

    def test_tcp_connection_params(self):
        client = LX200Client(
            connection_type=ConnectionType.TCP,
            host="10.0.0.50",
            port=8080,
        )
        assert client.connection_type == ConnectionType.TCP
        assert client.host == "10.0.0.50"
        assert client.port == 8080

    def test_encoder_bridge_optional(self):
        client = LX200Client()
        assert client.encoder is None

    def test_encoder_bridge_integration(self):
        mock_encoder = MagicMock()
        client = LX200Client(encoder_bridge=mock_encoder)
        assert client.encoder is mock_encoder

    def test_encoder_offset_initialized(self):
        client = LX200Client()
        assert client._encoder_offset == (0.0, 0.0)


class TestLX200ClientTCPConnection:
    """Test TCP connection handling."""

    @patch("socket.socket")
    def test_connect_tcp_success(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        client = LX200Client(
            connection_type=ConnectionType.TCP,
            host="192.168.1.100",
            port=9999,
        )
        result = client.connect()

        assert result is True
        assert client._connected is True
        mock_socket.settimeout.assert_called_once_with(5.0)
        mock_socket.connect.assert_called_once_with(("192.168.1.100", 9999))

    @patch("socket.socket")
    def test_connect_tcp_failure(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = socket.error("Connection refused")
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        result = client.connect()

        assert result is False
        assert client._connected is False

    @patch("socket.socket")
    def test_disconnect_tcp(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        client.disconnect()

        assert client._connected is False
        mock_socket.close.assert_called_once()


class TestLX200ClientSerialConnection:
    """Test serial connection handling."""

    @patch("serial.Serial")
    def test_connect_serial_success(self, mock_serial_class):
        mock_serial = MagicMock()
        mock_serial_class.return_value = mock_serial

        client = LX200Client(
            connection_type=ConnectionType.SERIAL,
            serial_port="/dev/ttyUSB0",
            baudrate=9600,
        )
        result = client.connect()

        assert result is True
        assert client._connected is True
        mock_serial_class.assert_called_once_with(
            port="/dev/ttyUSB0",
            baudrate=9600,
            timeout=5.0,
        )

    @patch("serial.Serial")
    def test_connect_serial_failure(self, mock_serial_class):
        mock_serial_class.side_effect = serial.SerialException("Device not found")

        client = LX200Client(connection_type=ConnectionType.SERIAL)
        result = client.connect()

        assert result is False
        assert client._connected is False

    @patch("serial.Serial")
    def test_disconnect_serial(self, mock_serial_class):
        mock_serial = MagicMock()
        mock_serial_class.return_value = mock_serial

        client = LX200Client(connection_type=ConnectionType.SERIAL)
        client.connect()
        client.disconnect()

        assert client._connected is False
        mock_serial.close.assert_called_once()


class TestLX200ClientCommands:
    """Test LX200 command sending."""

    @patch("socket.socket")
    def test_send_command_tcp(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"12:30:45#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client._send_command("GR")

        mock_socket.sendall.assert_called_with(b":GR#")
        assert result == "12:30:45"

    @patch("serial.Serial")
    def test_send_command_serial(self, mock_serial_class):
        mock_serial = MagicMock()
        mock_serial.read_until.return_value = b"+45*30:00#"
        mock_serial_class.return_value = mock_serial

        client = LX200Client(connection_type=ConnectionType.SERIAL)
        client.connect()
        result = client._send_command("GD")

        mock_serial.write.assert_called_with(b":GD#")
        assert result == "+45*30:00"

    def test_send_command_not_connected(self):
        client = LX200Client()
        result = client._send_command("GR")
        assert result is None


class TestLX200ClientPositionQueries:
    """Test position query commands."""

    @patch("socket.socket")
    def test_get_ra(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"12:30:45#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        ra = client.get_ra()

        assert ra == "12:30:45"

    @patch("socket.socket")
    def test_get_dec(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"+45*30:15#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        dec = client.get_dec()

        assert dec == "+45*30:15"

    @patch("socket.socket")
    def test_get_altitude(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"+60*15'30#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        alt = client.get_altitude()

        assert alt == "+60*15'30"

    @patch("socket.socket")
    def test_get_azimuth(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"180*30'45#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        az = client.get_azimuth()

        assert az == "180*30'45"

    @patch("socket.socket")
    def test_get_pier_side_east(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"E#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        pier = client.get_pier_side()

        assert pier == PierSide.EAST

    @patch("socket.socket")
    def test_get_pier_side_west(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"W#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        pier = client.get_pier_side()

        assert pier == PierSide.WEST

    @patch("socket.socket")
    def test_get_pier_side_unknown(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"X#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        pier = client.get_pier_side()

        assert pier == PierSide.UNKNOWN


class TestLX200ClientGetStatus:
    """Test get_status comprehensive query."""

    @patch.object(LX200Client, "get_ra")
    @patch.object(LX200Client, "get_dec")
    @patch.object(LX200Client, "is_tracking")
    @patch.object(LX200Client, "is_slewing")
    @patch.object(LX200Client, "is_parked")
    @patch.object(LX200Client, "get_pier_side")
    def test_get_status_success(
        self,
        mock_pier,
        mock_parked,
        mock_slewing,
        mock_tracking,
        mock_dec,
        mock_ra,
    ):
        mock_ra.return_value = "12:30:45"
        mock_dec.return_value = "+45*15:30"
        mock_tracking.return_value = True
        mock_slewing.return_value = False
        mock_parked.return_value = False
        mock_pier.return_value = PierSide.EAST

        client = LX200Client()
        client._connected = True
        status = client.get_status()

        assert status is not None
        assert status.ra_hours == 12.0
        assert status.ra_minutes == 30.0
        assert status.ra_seconds == 45.0
        assert status.dec_degrees == 45.0
        assert status.dec_minutes == 15.0
        assert status.dec_seconds == 30.0
        assert status.is_tracking is True
        assert status.is_slewing is False
        assert status.is_parked is False
        assert status.pier_side == PierSide.EAST

    @patch.object(LX200Client, "get_ra")
    @patch.object(LX200Client, "get_dec")
    def test_get_status_no_ra(self, mock_dec, mock_ra):
        mock_ra.return_value = None
        mock_dec.return_value = "+45*15:30"

        client = LX200Client()
        status = client.get_status()

        assert status is None

    @patch.object(LX200Client, "get_ra")
    @patch.object(LX200Client, "get_dec")
    def test_get_status_no_dec(self, mock_dec, mock_ra):
        mock_ra.return_value = "12:30:45"
        mock_dec.return_value = None

        client = LX200Client()
        status = client.get_status()

        assert status is None

    @patch.object(LX200Client, "get_ra")
    @patch.object(LX200Client, "get_dec")
    def test_get_status_invalid_ra_format(self, mock_dec, mock_ra):
        mock_ra.return_value = "invalid"
        mock_dec.return_value = "+45*15:30"

        client = LX200Client()
        status = client.get_status()

        assert status is None

    @patch.object(LX200Client, "get_ra")
    @patch.object(LX200Client, "get_dec")
    def test_get_status_invalid_dec_format(self, mock_dec, mock_ra):
        mock_ra.return_value = "12:30:45"
        mock_dec.return_value = "invalid"

        client = LX200Client()
        status = client.get_status()

        assert status is None

    @patch.object(LX200Client, "get_ra")
    @patch.object(LX200Client, "get_dec")
    @patch.object(LX200Client, "is_tracking")
    @patch.object(LX200Client, "is_slewing")
    @patch.object(LX200Client, "is_parked")
    @patch.object(LX200Client, "get_pier_side")
    def test_get_status_negative_dec(
        self,
        mock_pier,
        mock_parked,
        mock_slewing,
        mock_tracking,
        mock_dec,
        mock_ra,
    ):
        mock_ra.return_value = "06:00:00"
        mock_dec.return_value = "-30*45:15"
        mock_tracking.return_value = False
        mock_slewing.return_value = True
        mock_parked.return_value = False
        mock_pier.return_value = PierSide.WEST

        client = LX200Client()
        client._connected = True
        status = client.get_status()

        assert status is not None
        assert status.dec_degrees == -30.0
        assert status.dec_minutes == 45.0
        assert status.dec_seconds == 15.0


class TestLX200ClientMotionControl:
    """Test motion control commands."""

    @patch("socket.socket")
    def test_goto_ra_dec_success(self, mock_socket_class):
        mock_socket = MagicMock()
        responses = [b"1#", b"1#", b"0#"]
        mock_socket.recv.side_effect = responses
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.goto_ra_dec("12:30:45", "+45*30:00")

        assert result is True

    @patch("socket.socket")
    def test_goto_ra_dec_ra_fail(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"0#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.goto_ra_dec("invalid", "+45*30:00")

        assert result is False

    @patch("socket.socket")
    def test_goto_ra_dec_dec_fail(self, mock_socket_class):
        mock_socket = MagicMock()
        responses = [b"1#", b"0#"]
        mock_socket.recv.side_effect = responses
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.goto_ra_dec("12:30:45", "invalid")

        assert result is False

    @patch("socket.socket")
    def test_goto_alt_az(self, mock_socket_class):
        mock_socket = MagicMock()
        responses = [b"1#", b"1#", b"0#"]
        mock_socket.recv.side_effect = responses
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.goto_alt_az("+45*30", "180*00")

        assert result is True

    @patch("socket.socket")
    def test_sync(self, mock_socket_class):
        mock_socket = MagicMock()
        responses = [b"1#", b"1#", b"M31#"]
        mock_socket.recv.side_effect = responses
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.sync("00:42:44", "+41*16:09")

        assert result is True

    @patch("socket.socket")
    def test_stop(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        client.stop()

        mock_socket.sendall.assert_called_with(b":Q#")

    @patch("socket.socket")
    def test_stop_axis_north(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        client.stop_axis("n")

        mock_socket.sendall.assert_called_with(b":Qn#")


class TestLX200ClientTrackingControl:
    """Test tracking control commands."""

    @patch("socket.socket")
    def test_start_tracking(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"1#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.start_tracking()

        assert result is True
        mock_socket.sendall.assert_called_with(b":Te#")

    @patch("socket.socket")
    def test_stop_tracking(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"1#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.stop_tracking()

        assert result is True
        mock_socket.sendall.assert_called_with(b":Td#")

    @patch("socket.socket")
    def test_set_tracking_rate_sidereal(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"1#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.set_tracking_rate(TrackingRate.SIDEREAL)

        assert result is True
        mock_socket.sendall.assert_called_with(b":TQ#")

    @patch("socket.socket")
    def test_set_tracking_rate_lunar(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"1#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.set_tracking_rate(TrackingRate.LUNAR)

        assert result is True
        mock_socket.sendall.assert_called_with(b":TL#")

    @patch("socket.socket")
    def test_is_tracking_true(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"TS#"  # T=Tracking, S=stationary
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.is_tracking()

        assert result is True

    @patch("socket.socket")
    def test_is_tracking_false(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"NS#"  # N=Not tracking
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.is_tracking()

        assert result is False

    @patch("socket.socket")
    def test_is_slewing_true(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"TS#"  # S=Slewing
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.is_slewing()

        assert result is True

    @patch("socket.socket")
    def test_is_slewing_false(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"TN#"  # N=Not slewing
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.is_slewing()

        assert result is False


class TestLX200ClientParkControl:
    """Test park control commands."""

    @patch("socket.socket")
    def test_park_success(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"1#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.park()

        assert result is True
        mock_socket.sendall.assert_called_with(b":hP#")

    @patch("socket.socket")
    def test_park_failure(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"0#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.park()

        assert result is False

    @patch("socket.socket")
    def test_unpark_success(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"1#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.unpark()

        assert result is True
        mock_socket.sendall.assert_called_with(b":hR#")

    @patch("socket.socket")
    def test_is_parked_true(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"P#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.is_parked()

        assert result is True

    @patch("socket.socket")
    def test_is_parked_false(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"N#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.is_parked()

        assert result is False

    @patch("socket.socket")
    def test_set_park_position(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"1#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.set_park_position()

        assert result is True
        mock_socket.sendall.assert_called_with(b":hQ#")


class TestLX200ClientHoming:
    """Test homing commands."""

    @patch("socket.socket")
    def test_home(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"1#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.home()

        assert result is True
        mock_socket.sendall.assert_called_with(b":hC#")

    @patch("socket.socket")
    def test_home_reset(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"1#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.home_reset()

        assert result is True
        mock_socket.sendall.assert_called_with(b":hF#")


class TestLX200ClientSiteInfo:
    """Test site information commands."""

    @patch("socket.socket")
    def test_get_latitude(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"+34*03#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        lat = client.get_latitude()

        assert lat == "+34*03"

    @patch("socket.socket")
    def test_get_longitude(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"-118*15#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        lon = client.get_longitude()

        assert lon == "-118*15"

    @patch("socket.socket")
    def test_set_latitude(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"1#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.set_latitude("+34*03")

        assert result is True

    @patch("socket.socket")
    def test_set_longitude(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"1#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client.set_longitude("-118*15")

        assert result is True

    @patch("socket.socket")
    def test_get_local_time(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"21:30:45#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        time_str = client.get_local_time()

        assert time_str == "21:30:45"

    @patch("socket.socket")
    def test_get_sidereal_time(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"05:42:30#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        lst = client.get_sidereal_time()

        assert lst == "05:42:30"


class TestLX200ClientFirmware:
    """Test firmware information commands."""

    @patch("socket.socket")
    def test_get_firmware_info(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"OnStepX#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        info = client.get_firmware_info()

        assert info == "OnStepX"

    @patch("socket.socket")
    def test_get_firmware_version(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"10.20#"
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        version = client.get_firmware_version()

        assert version == "10.20"


class TestLX200ClientEncoderIntegration:
    """Test encoder integration methods."""

    def test_mount_ra_to_degrees(self):
        client = LX200Client()
        status = MountStatus(
            ra_hours=12.0,
            ra_minutes=30.0,
            ra_seconds=0.0,
            dec_degrees=0.0,
            dec_minutes=0.0,
            dec_seconds=0.0,
            is_tracking=False,
            is_slewing=False,
            is_parked=False,
            pier_side=PierSide.UNKNOWN,
        )
        degrees = client._mount_ra_to_degrees(status)
        # 12h 30m = 12.5 hours * 15 = 187.5 degrees
        assert degrees == 187.5

    def test_mount_dec_to_degrees_positive(self):
        client = LX200Client()
        status = MountStatus(
            ra_hours=0.0,
            ra_minutes=0.0,
            ra_seconds=0.0,
            dec_degrees=45.0,
            dec_minutes=30.0,
            dec_seconds=0.0,
            is_tracking=False,
            is_slewing=False,
            is_parked=False,
            pier_side=PierSide.UNKNOWN,
        )
        degrees = client._mount_dec_to_degrees(status)
        assert degrees == 45.5

    def test_mount_dec_to_degrees_negative(self):
        client = LX200Client()
        status = MountStatus(
            ra_hours=0.0,
            ra_minutes=0.0,
            ra_seconds=0.0,
            dec_degrees=-30.0,
            dec_minutes=15.0,
            dec_seconds=0.0,
            is_tracking=False,
            is_slewing=False,
            is_parked=False,
            pier_side=PierSide.UNKNOWN,
        )
        degrees = client._mount_dec_to_degrees(status)
        assert degrees == -30.25

    def test_degrees_to_ra_components(self):
        client = LX200Client()
        h, m, s = client._degrees_to_ra_components(180.0)
        assert h == 12.0
        assert m == 0.0
        assert s == 0.0

    def test_degrees_to_ra_components_with_minutes(self):
        client = LX200Client()
        h, m, s = client._degrees_to_ra_components(187.5)
        assert h == 12.0
        assert m == 30.0
        assert abs(s) < 0.001

    def test_degrees_to_ra_components_normalizes_negative(self):
        client = LX200Client()
        h, m, s = client._degrees_to_ra_components(-15.0)  # -1 hour = 23 hours
        assert h == 23.0

    def test_degrees_to_ra_components_normalizes_over_360(self):
        client = LX200Client()
        h, m, s = client._degrees_to_ra_components(375.0)  # 25 hours = 1 hour
        assert h == 1.0

    def test_degrees_to_dec_components_positive(self):
        client = LX200Client()
        d, m, s = client._degrees_to_dec_components(45.5)
        assert d == 45.0
        assert m == 30.0
        assert abs(s) < 0.001

    def test_degrees_to_dec_components_negative(self):
        client = LX200Client()
        d, m, s = client._degrees_to_dec_components(-30.25)
        assert d == -30.0
        assert m == 15.0
        assert abs(s) < 0.001

    def test_calibrate_encoder_offset(self):
        client = LX200Client()
        client.calibrate_encoder_offset(0.5, -0.3)
        assert client._encoder_offset == (0.5, -0.3)

    @pytest.mark.asyncio
    async def test_get_corrected_position_no_encoder(self):
        client = LX200Client()
        with patch.object(client, "get_status") as mock_status:
            mock_status.return_value = MountStatus(
                ra_hours=12.0,
                ra_minutes=0.0,
                ra_seconds=0.0,
                dec_degrees=45.0,
                dec_minutes=0.0,
                dec_seconds=0.0,
                is_tracking=True,
                is_slewing=False,
                is_parked=False,
                pier_side=PierSide.EAST,
            )
            result = await client.get_corrected_position()
            assert result is not None
            assert result.ra_hours == 12.0

    @pytest.mark.asyncio
    async def test_get_pointing_error_no_encoder(self):
        client = LX200Client()
        result = await client.get_pointing_error()
        assert result is None


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_ra_to_hours_basic(self):
        hours = ra_to_hours("12:30:45")
        expected = 12 + 30 / 60 + 45 / 3600
        assert abs(hours - expected) < 0.0001

    def test_ra_to_hours_with_decimal_seconds(self):
        hours = ra_to_hours("06:15:30.5")
        expected = 6 + 15 / 60 + 30.5 / 3600
        assert abs(hours - expected) < 0.0001

    def test_ra_to_hours_invalid(self):
        hours = ra_to_hours("invalid")
        assert hours == 0.0

    def test_dec_to_degrees_positive(self):
        degrees = dec_to_degrees("+45*30:15")
        expected = 45 + 30 / 60 + 15 / 3600
        assert abs(degrees - expected) < 0.0001

    def test_dec_to_degrees_negative(self):
        degrees = dec_to_degrees("-30*15:45")
        expected = -(30 + 15 / 60 + 45 / 3600)
        assert abs(degrees - expected) < 0.0001

    def test_dec_to_degrees_with_degree_symbol(self):
        degrees = dec_to_degrees("+45°30'15")
        expected = 45 + 30 / 60 + 15 / 3600
        assert abs(degrees - expected) < 0.0001

    def test_dec_to_degrees_invalid(self):
        degrees = dec_to_degrees("invalid")
        assert degrees == 0.0

    def test_hours_to_ra_basic(self):
        ra = hours_to_ra(12.5)
        assert ra == "12:30:00.00"

    def test_hours_to_ra_with_seconds(self):
        ra = hours_to_ra(6.2625)  # 6h 15m 45s
        assert ra.startswith("06:15:45")

    def test_degrees_to_dec_positive(self):
        dec = degrees_to_dec(45.5)
        assert dec == "+45*30:00.00"

    def test_degrees_to_dec_negative(self):
        dec = degrees_to_dec(-30.25)
        assert dec == "-30*15:00.00"

    def test_degrees_to_dec_zero(self):
        dec = degrees_to_dec(0.0)
        assert dec.startswith("+00*00:00")


class TestLX200ClientEdgeCases:
    """Test edge cases and error handling."""

    def test_disconnect_when_not_connected(self):
        client = LX200Client()
        # Should not raise exception
        client.disconnect()
        assert client._connected is False

    @patch("socket.socket")
    def test_command_exception_handling(self, mock_socket_class):
        mock_socket = MagicMock()
        mock_socket.sendall.side_effect = Exception("Network error")
        mock_socket_class.return_value = mock_socket

        client = LX200Client(connection_type=ConnectionType.TCP)
        client.connect()
        result = client._send_command("GR")

        assert result is None

    def test_thread_safety_lock(self):
        client = LX200Client()
        assert hasattr(client, "_lock")
        # Verify lock is a threading lock
        import threading
        assert isinstance(client._lock, type(threading.Lock()))
