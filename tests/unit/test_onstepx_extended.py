"""
NIGHTWATCH Unit Tests - OnStepXExtended Service

Unit tests for services/mount_control/onstepx_extended.py.
Uses mocking to test OnStepX extended commands without requiring network
or serial connections to physical hardware.

These tests validate Phase 2.3 of the Integration Plan:
- Periodic Error Correction (PEC) commands
- TMC stepper driver diagnostics
- Tracking rate fine-tuning
- Extended status queries
- Reticle control

Run:
    pytest tests/unit/test_onstepx_extended.py -v
"""

import asyncio
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from dataclasses import dataclass


# =============================================================================
# Test PECStatus Dataclass
# =============================================================================

class TestPECStatus:
    """Unit tests for PECStatus dataclass."""

    def test_pec_status_creation(self):
        """Test creating PECStatus with all fields."""
        from services.mount_control.onstepx_extended import PECStatus

        status = PECStatus(
            recording=True,
            playing=False,
            ready=True,
            index_detected=True,
            record_progress=0.75,
        )

        assert status.recording is True
        assert status.playing is False
        assert status.ready is True
        assert status.index_detected is True
        assert status.record_progress == 0.75

    def test_pec_status_default_values(self):
        """Test PECStatus with all false/zero values."""
        from services.mount_control.onstepx_extended import PECStatus

        status = PECStatus(
            recording=False,
            playing=False,
            ready=False,
            index_detected=False,
            record_progress=0.0,
        )

        assert status.recording is False
        assert status.playing is False
        assert status.ready is False
        assert status.index_detected is False
        assert status.record_progress == 0.0

    def test_pec_status_equality(self):
        """Test PECStatus equality comparison."""
        from services.mount_control.onstepx_extended import PECStatus

        status1 = PECStatus(True, False, True, True, 0.5)
        status2 = PECStatus(True, False, True, True, 0.5)
        status3 = PECStatus(False, False, True, True, 0.5)

        assert status1 == status2
        assert status1 != status3


# =============================================================================
# Test DriverStatus Dataclass
# =============================================================================

class TestDriverStatus:
    """Unit tests for DriverStatus dataclass."""

    def test_driver_status_creation(self):
        """Test creating DriverStatus with all fields."""
        from services.mount_control.onstepx_extended import DriverStatus

        status = DriverStatus(
            axis=1,
            standstill=True,
            open_load_a=False,
            open_load_b=False,
            short_to_ground_a=False,
            short_to_ground_b=False,
            overtemperature=False,
            overtemperature_pre=False,
            stallguard=False,
            current_ma=800,
        )

        assert status.axis == 1
        assert status.standstill is True
        assert status.open_load_a is False
        assert status.open_load_b is False
        assert status.short_to_ground_a is False
        assert status.short_to_ground_b is False
        assert status.overtemperature is False
        assert status.overtemperature_pre is False
        assert status.stallguard is False
        assert status.current_ma == 800

    def test_driver_status_with_faults(self):
        """Test DriverStatus with fault conditions."""
        from services.mount_control.onstepx_extended import DriverStatus

        status = DriverStatus(
            axis=2,
            standstill=False,
            open_load_a=True,
            open_load_b=False,
            short_to_ground_a=False,
            short_to_ground_b=True,
            overtemperature=True,
            overtemperature_pre=True,
            stallguard=True,
            current_ma=1200,
        )

        assert status.axis == 2
        assert status.open_load_a is True
        assert status.short_to_ground_b is True
        assert status.overtemperature is True
        assert status.overtemperature_pre is True
        assert status.stallguard is True
        assert status.current_ma == 1200

    def test_driver_status_none_current(self):
        """Test DriverStatus with None current (unavailable)."""
        from services.mount_control.onstepx_extended import DriverStatus

        status = DriverStatus(
            axis=1,
            standstill=True,
            open_load_a=False,
            open_load_b=False,
            short_to_ground_a=False,
            short_to_ground_b=False,
            overtemperature=False,
            overtemperature_pre=False,
            stallguard=False,
            current_ma=None,
        )

        assert status.current_ma is None

    def test_driver_status_equality(self):
        """Test DriverStatus equality comparison."""
        from services.mount_control.onstepx_extended import DriverStatus

        status1 = DriverStatus(1, True, False, False, False, False, False, False, False, 800)
        status2 = DriverStatus(1, True, False, False, False, False, False, False, False, 800)
        status3 = DriverStatus(2, True, False, False, False, False, False, False, False, 800)

        assert status1 == status2
        assert status1 != status3


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_socket():
    """Create a mock socket for TCP testing."""
    socket_mock = Mock()
    socket_mock.sendall = Mock()
    socket_mock.recv = Mock(return_value=b"1#")
    socket_mock.settimeout = Mock()
    socket_mock.connect = Mock()
    socket_mock.close = Mock()
    return socket_mock


@pytest.fixture
def onstepx_client():
    """Create OnStepXExtended instance for testing."""
    from services.mount_control.onstepx_extended import OnStepXExtended
    from services.mount_control.lx200 import ConnectionType

    client = OnStepXExtended(
        connection_type=ConnectionType.TCP,
        host="192.168.1.100",
        port=9999,
    )
    return client


@pytest.fixture
def connected_client(onstepx_client, mock_socket):
    """Create a connected OnStepXExtended client with mocked socket."""
    onstepx_client._connection = mock_socket
    onstepx_client._connected = True
    return onstepx_client


# =============================================================================
# OnStepXExtended Initialization Tests
# =============================================================================

class TestOnStepXExtendedInit:
    """Unit tests for OnStepXExtended initialization."""

    def test_default_tcp_initialization(self):
        """Test OnStepXExtended with TCP connection (default)."""
        from services.mount_control.onstepx_extended import OnStepXExtended
        from services.mount_control.lx200 import ConnectionType

        client = OnStepXExtended()

        assert client.connection_type == ConnectionType.TCP
        assert client.host == "192.168.1.100"
        assert client.port == 9999
        assert client._connected is False

    def test_custom_tcp_initialization(self):
        """Test OnStepXExtended with custom TCP parameters."""
        from services.mount_control.onstepx_extended import OnStepXExtended
        from services.mount_control.lx200 import ConnectionType

        client = OnStepXExtended(
            connection_type=ConnectionType.TCP,
            host="10.0.0.50",
            port=9876,
        )

        assert client.host == "10.0.0.50"
        assert client.port == 9876

    def test_serial_initialization(self):
        """Test OnStepXExtended with serial connection."""
        from services.mount_control.onstepx_extended import OnStepXExtended
        from services.mount_control.lx200 import ConnectionType

        client = OnStepXExtended(
            connection_type=ConnectionType.SERIAL,
            serial_port="/dev/ttyACM0",
            baudrate=115200,
        )

        assert client.connection_type == ConnectionType.SERIAL
        assert client.serial_port == "/dev/ttyACM0"
        assert client.baudrate == 115200

    def test_command_constants(self):
        """Test that command constants are defined correctly."""
        from services.mount_control.onstepx_extended import OnStepXExtended

        assert OnStepXExtended.CMD_PEC_STATUS == "$QZ"
        assert OnStepXExtended.CMD_PEC_PLAY == "$QZ+"
        assert OnStepXExtended.CMD_PEC_STOP == "$QZ-"
        assert OnStepXExtended.CMD_PEC_RECORD == "$QZR"
        assert OnStepXExtended.CMD_PEC_CLEAR == "$QZC"
        assert OnStepXExtended.CMD_SET_TRACKING_OFFSET == "ST"
        assert OnStepXExtended.CMD_GET_DRIVER_STATUS == "GXU"


# =============================================================================
# PEC Status Tests
# =============================================================================

class TestPECStatus:
    """Unit tests for PEC status command."""

    @pytest.mark.asyncio
    async def test_pec_status_playing(self, connected_client, mock_socket):
        """Test PEC status when playback is active."""
        # Mock response indicating PEC is playing
        mock_socket.recv = Mock(return_value=b"P#")

        status = await connected_client.pec_status()

        assert status.playing is True
        assert status.recording is False
        assert status.ready is True  # Ready when not recording

    @pytest.mark.asyncio
    async def test_pec_status_recording(self, connected_client, mock_socket):
        """Test PEC status when recording is active."""
        # First call returns recording status, second returns progress
        responses = [b"R#", b"50#"]
        mock_socket.recv = Mock(side_effect=responses)

        status = await connected_client.pec_status()

        assert status.recording is True
        assert status.playing is False
        assert status.record_progress == 0.5

    @pytest.mark.asyncio
    async def test_pec_status_ready(self, connected_client, mock_socket):
        """Test PEC status when trained and ready."""
        mock_socket.recv = Mock(return_value=b"r#")

        status = await connected_client.pec_status()

        assert status.ready is True
        assert status.recording is False
        assert status.playing is False

    @pytest.mark.asyncio
    async def test_pec_status_index_detected(self, connected_client, mock_socket):
        """Test PEC status with index sensor detected."""
        mock_socket.recv = Mock(return_value=b"IP#")

        status = await connected_client.pec_status()

        assert status.index_detected is True
        assert status.playing is True

    @pytest.mark.asyncio
    async def test_pec_status_no_response(self, connected_client, mock_socket):
        """Test PEC status with no response from mount."""
        mock_socket.recv = Mock(return_value=b"#")

        status = await connected_client.pec_status()

        # Default values when no valid response
        assert status.recording is False
        assert status.playing is False
        assert status.record_progress == 0.0


# =============================================================================
# PEC Playback Control Tests
# =============================================================================

class TestPECPlayback:
    """Unit tests for PEC playback control."""

    @pytest.mark.asyncio
    async def test_pec_start_playback_success(self, connected_client, mock_socket):
        """Test starting PEC playback successfully."""
        mock_socket.recv = Mock(return_value=b"1#")

        result = await connected_client.pec_start_playback()

        assert result is True
        # Verify correct command was sent
        call_args = mock_socket.sendall.call_args[0][0]
        assert b"$QZ+" in call_args

    @pytest.mark.asyncio
    async def test_pec_start_playback_failure(self, connected_client, mock_socket):
        """Test failed PEC playback start."""
        mock_socket.recv = Mock(return_value=b"0#")

        result = await connected_client.pec_start_playback()

        assert result is False

    @pytest.mark.asyncio
    async def test_pec_stop_success(self, connected_client, mock_socket):
        """Test stopping PEC successfully."""
        mock_socket.recv = Mock(return_value=b"1#")

        result = await connected_client.pec_stop()

        assert result is True
        call_args = mock_socket.sendall.call_args[0][0]
        assert b"$QZ-" in call_args

    @pytest.mark.asyncio
    async def test_pec_stop_failure(self, connected_client, mock_socket):
        """Test failed PEC stop."""
        mock_socket.recv = Mock(return_value=b"0#")

        result = await connected_client.pec_stop()

        assert result is False


# =============================================================================
# PEC Recording Tests
# =============================================================================

class TestPECRecording:
    """Unit tests for PEC recording control."""

    @pytest.mark.asyncio
    async def test_pec_record_success(self, connected_client, mock_socket):
        """Test starting PEC recording successfully."""
        mock_socket.recv = Mock(return_value=b"1#")

        result = await connected_client.pec_record()

        assert result is True
        call_args = mock_socket.sendall.call_args[0][0]
        assert b"$QZR" in call_args

    @pytest.mark.asyncio
    async def test_pec_record_failure(self, connected_client, mock_socket):
        """Test failed PEC recording start."""
        mock_socket.recv = Mock(return_value=b"0#")

        result = await connected_client.pec_record()

        assert result is False

    @pytest.mark.asyncio
    async def test_pec_clear_success(self, connected_client, mock_socket):
        """Test clearing PEC data successfully."""
        mock_socket.recv = Mock(return_value=b"1#")

        result = await connected_client.pec_clear()

        assert result is True
        call_args = mock_socket.sendall.call_args[0][0]
        assert b"$QZC" in call_args

    @pytest.mark.asyncio
    async def test_pec_clear_failure(self, connected_client, mock_socket):
        """Test failed PEC clear."""
        mock_socket.recv = Mock(return_value=b"0#")

        result = await connected_client.pec_clear()

        assert result is False

    @pytest.mark.asyncio
    async def test_pec_save_to_eeprom_success(self, connected_client, mock_socket):
        """Test saving PEC data to EEPROM."""
        mock_socket.recv = Mock(return_value=b"1#")

        result = await connected_client.pec_save_to_eeprom()

        assert result is True
        call_args = mock_socket.sendall.call_args[0][0]
        assert b"$QZW" in call_args

    @pytest.mark.asyncio
    async def test_pec_save_to_eeprom_failure(self, connected_client, mock_socket):
        """Test failed EEPROM save."""
        mock_socket.recv = Mock(return_value=b"0#")

        result = await connected_client.pec_save_to_eeprom()

        assert result is False


# =============================================================================
# Driver Status Tests
# =============================================================================

class TestDriverStatusCommands:
    """Unit tests for TMC driver status commands."""

    @pytest.mark.asyncio
    async def test_get_driver_status_normal(self, connected_client, mock_socket):
        """Test driver status with normal operation (standstill)."""
        # Hex value with standstill bit set (bit 31)
        mock_socket.recv = Mock(return_value=b"80000000#")

        status = await connected_client.get_driver_status(axis=1)

        assert status.axis == 1
        assert status.standstill is True
        assert status.open_load_a is False
        assert status.open_load_b is False
        assert status.short_to_ground_a is False
        assert status.short_to_ground_b is False
        assert status.overtemperature is False
        assert status.stallguard is False

    @pytest.mark.asyncio
    async def test_get_driver_status_open_load(self, connected_client, mock_socket):
        """Test driver status with open load condition."""
        # Hex value with open_load_a bit set (bit 30)
        mock_socket.recv = Mock(return_value=b"40000000#")

        status = await connected_client.get_driver_status(axis=1)

        assert status.open_load_a is True
        assert status.standstill is False

    @pytest.mark.asyncio
    async def test_get_driver_status_overtemperature(self, connected_client, mock_socket):
        """Test driver status with overtemperature warning."""
        # Hex value with overtemperature bit set (bit 26)
        mock_socket.recv = Mock(return_value=b"04000000#")

        status = await connected_client.get_driver_status(axis=1)

        assert status.overtemperature is True

    @pytest.mark.asyncio
    async def test_get_driver_status_stallguard(self, connected_client, mock_socket):
        """Test driver status with stallguard triggered."""
        # Hex value with stallguard bit set (bit 24)
        mock_socket.recv = Mock(return_value=b"01000000#")

        status = await connected_client.get_driver_status(axis=2)

        assert status.axis == 2
        assert status.stallguard is True

    @pytest.mark.asyncio
    async def test_get_driver_status_multiple_faults(self, connected_client, mock_socket):
        """Test driver status with multiple fault conditions."""
        # Hex value with standstill, open_load_b, and overtemperature_pre
        # Bits: 31 (standstill) + 29 (open_load_b) + 25 (overtemp_pre)
        mock_socket.recv = Mock(return_value=b"A2000000#")

        status = await connected_client.get_driver_status(axis=1)

        assert status.standstill is True
        assert status.open_load_b is True
        assert status.overtemperature_pre is True

    @pytest.mark.asyncio
    async def test_get_driver_status_empty_response(self, connected_client, mock_socket):
        """Test driver status with empty response."""
        mock_socket.recv = Mock(return_value=b"#")

        status = await connected_client.get_driver_status(axis=1)

        # All flags should be False with empty response
        assert status.standstill is False
        assert status.open_load_a is False
        assert status.overtemperature is False

    @pytest.mark.asyncio
    async def test_get_driver_status_invalid_hex(self, connected_client, mock_socket):
        """Test driver status with invalid hex response."""
        mock_socket.recv = Mock(return_value=b"INVALID#")

        status = await connected_client.get_driver_status(axis=1)

        # All flags should be False with invalid response
        assert status.standstill is False

    @pytest.mark.asyncio
    async def test_get_all_driver_status(self, connected_client, mock_socket):
        """Test getting driver status for both axes."""
        # Return different values for each axis
        responses = [b"80000000#", b"01000000#"]
        mock_socket.recv = Mock(side_effect=responses)

        result = await connected_client.get_all_driver_status()

        assert "axis1_ra" in result
        assert "axis2_dec" in result
        assert result["axis1_ra"].standstill is True
        assert result["axis2_dec"].stallguard is True


# =============================================================================
# Tracking Rate Offset Tests
# =============================================================================

class TestTrackingOffset:
    """Unit tests for tracking rate fine-tuning."""

    @pytest.mark.asyncio
    async def test_set_tracking_offset_positive(self, connected_client, mock_socket):
        """Test setting positive tracking offset."""
        mock_socket.recv = Mock(return_value=b"1#")

        result = await connected_client.set_tracking_offset(15.5)

        assert result is True
        call_args = mock_socket.sendall.call_args[0][0]
        assert b"ST+15.5000" in call_args

    @pytest.mark.asyncio
    async def test_set_tracking_offset_negative(self, connected_client, mock_socket):
        """Test setting negative tracking offset."""
        mock_socket.recv = Mock(return_value=b"1#")

        result = await connected_client.set_tracking_offset(-10.25)

        assert result is True
        call_args = mock_socket.sendall.call_args[0][0]
        assert b"ST-10.2500" in call_args

    @pytest.mark.asyncio
    async def test_set_tracking_offset_zero(self, connected_client, mock_socket):
        """Test setting zero tracking offset."""
        mock_socket.recv = Mock(return_value=b"1#")

        result = await connected_client.set_tracking_offset(0.0)

        assert result is True
        call_args = mock_socket.sendall.call_args[0][0]
        assert b"ST+0.0000" in call_args

    @pytest.mark.asyncio
    async def test_set_tracking_offset_failure(self, connected_client, mock_socket):
        """Test failed tracking offset setting."""
        mock_socket.recv = Mock(return_value=b"0#")

        result = await connected_client.set_tracking_offset(5.0)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_tracking_offset_success(self, connected_client, mock_socket):
        """Test getting current tracking offset."""
        mock_socket.recv = Mock(return_value=b"12.5#")

        result = await connected_client.get_tracking_offset()

        assert result == 12.5
        call_args = mock_socket.sendall.call_args[0][0]
        assert b"GT" in call_args

    @pytest.mark.asyncio
    async def test_get_tracking_offset_negative(self, connected_client, mock_socket):
        """Test getting negative tracking offset."""
        mock_socket.recv = Mock(return_value=b"-7.25#")

        result = await connected_client.get_tracking_offset()

        assert result == -7.25

    @pytest.mark.asyncio
    async def test_get_tracking_offset_empty(self, connected_client, mock_socket):
        """Test getting tracking offset with empty response."""
        mock_socket.recv = Mock(return_value=b"#")

        result = await connected_client.get_tracking_offset()

        assert result is None

    @pytest.mark.asyncio
    async def test_get_tracking_offset_invalid(self, connected_client, mock_socket):
        """Test getting tracking offset with invalid response."""
        mock_socket.recv = Mock(return_value=b"invalid#")

        result = await connected_client.get_tracking_offset()

        assert result is None


# =============================================================================
# Extended Status Tests
# =============================================================================

class TestExtendedStatus:
    """Unit tests for extended status commands."""

    @pytest.mark.asyncio
    async def test_get_mount_errors_success(self, connected_client, mock_socket):
        """Test getting mount error counts."""
        mock_socket.recv = Mock(return_value=b"5,2,1,0#")

        errors = await connected_client.get_mount_errors()

        assert errors["slew_aborts"] == 5
        assert errors["limit_errors"] == 2
        assert errors["tracking_errors"] == 1
        assert errors["driver_faults"] == 0

    @pytest.mark.asyncio
    async def test_get_mount_errors_empty(self, connected_client, mock_socket):
        """Test getting mount errors with empty response."""
        mock_socket.recv = Mock(return_value=b"#")

        errors = await connected_client.get_mount_errors()

        # Should return default zeros
        assert errors["slew_aborts"] == 0
        assert errors["limit_errors"] == 0
        assert errors["tracking_errors"] == 0
        assert errors["driver_faults"] == 0

    @pytest.mark.asyncio
    async def test_get_mount_errors_partial(self, connected_client, mock_socket):
        """Test getting mount errors with partial response."""
        mock_socket.recv = Mock(return_value=b"3,1#")

        errors = await connected_client.get_mount_errors()

        # Should return defaults when parsing fails
        assert errors["slew_aborts"] == 0

    @pytest.mark.asyncio
    async def test_get_motor_temperature_success(self, connected_client, mock_socket):
        """Test getting motor temperature."""
        mock_socket.recv = Mock(return_value=b"42.5#")

        temp = await connected_client.get_motor_temperature(axis=1)

        assert temp == 42.5
        call_args = mock_socket.sendall.call_args[0][0]
        assert b"GXT1" in call_args

    @pytest.mark.asyncio
    async def test_get_motor_temperature_axis2(self, connected_client, mock_socket):
        """Test getting motor temperature for axis 2."""
        mock_socket.recv = Mock(return_value=b"38.0#")

        temp = await connected_client.get_motor_temperature(axis=2)

        assert temp == 38.0
        call_args = mock_socket.sendall.call_args[0][0]
        assert b"GXT2" in call_args

    @pytest.mark.asyncio
    async def test_get_motor_temperature_unavailable(self, connected_client, mock_socket):
        """Test getting motor temperature when sensor unavailable."""
        mock_socket.recv = Mock(return_value=b"#")

        temp = await connected_client.get_motor_temperature(axis=1)

        assert temp is None

    @pytest.mark.asyncio
    async def test_get_motor_temperature_invalid(self, connected_client, mock_socket):
        """Test getting motor temperature with invalid response."""
        mock_socket.recv = Mock(return_value=b"N/A#")

        temp = await connected_client.get_motor_temperature(axis=1)

        assert temp is None


# =============================================================================
# Reticle Control Tests
# =============================================================================

class TestReticleControl:
    """Unit tests for reticle brightness control."""

    @pytest.mark.asyncio
    async def test_set_reticle_brightness_min(self, connected_client, mock_socket):
        """Test setting reticle brightness to minimum (off)."""
        mock_socket.recv = Mock(return_value=b"1#")

        result = await connected_client.set_reticle_brightness(0)

        assert result is True
        call_args = mock_socket.sendall.call_args[0][0]
        assert b"rc000" in call_args

    @pytest.mark.asyncio
    async def test_set_reticle_brightness_max(self, connected_client, mock_socket):
        """Test setting reticle brightness to maximum."""
        mock_socket.recv = Mock(return_value=b"1#")

        result = await connected_client.set_reticle_brightness(255)

        assert result is True
        call_args = mock_socket.sendall.call_args[0][0]
        assert b"rc255" in call_args

    @pytest.mark.asyncio
    async def test_set_reticle_brightness_mid(self, connected_client, mock_socket):
        """Test setting reticle brightness to mid-level."""
        mock_socket.recv = Mock(return_value=b"1#")

        result = await connected_client.set_reticle_brightness(128)

        assert result is True
        call_args = mock_socket.sendall.call_args[0][0]
        assert b"rc128" in call_args

    @pytest.mark.asyncio
    async def test_set_reticle_brightness_clamp_high(self, connected_client, mock_socket):
        """Test that brightness is clamped to 255."""
        mock_socket.recv = Mock(return_value=b"1#")

        result = await connected_client.set_reticle_brightness(300)

        assert result is True
        call_args = mock_socket.sendall.call_args[0][0]
        assert b"rc255" in call_args

    @pytest.mark.asyncio
    async def test_set_reticle_brightness_clamp_low(self, connected_client, mock_socket):
        """Test that brightness is clamped to 0."""
        mock_socket.recv = Mock(return_value=b"1#")

        result = await connected_client.set_reticle_brightness(-50)

        assert result is True
        call_args = mock_socket.sendall.call_args[0][0]
        assert b"rc000" in call_args

    @pytest.mark.asyncio
    async def test_toggle_reticle_success(self, connected_client, mock_socket):
        """Test toggling reticle on/off."""
        mock_socket.recv = Mock(return_value=b"1#")

        result = await connected_client.toggle_reticle()

        assert result is True
        call_args = mock_socket.sendall.call_args[0][0]
        assert b"rC" in call_args

    @pytest.mark.asyncio
    async def test_toggle_reticle_failure(self, connected_client, mock_socket):
        """Test failed reticle toggle."""
        mock_socket.recv = Mock(return_value=b"0#")

        result = await connected_client.toggle_reticle()

        assert result is False


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactoryFunctions:
    """Unit tests for convenience factory functions."""

    def test_create_onstepx_extended_tcp_default(self):
        """Test factory function with TCP defaults."""
        from services.mount_control.onstepx_extended import create_onstepx_extended
        from services.mount_control.lx200 import ConnectionType

        client = create_onstepx_extended()

        assert client.connection_type == ConnectionType.TCP
        assert client.host == "192.168.1.100"
        assert client.port == 9999

    def test_create_onstepx_extended_tcp_custom(self):
        """Test factory function with custom TCP settings."""
        from services.mount_control.onstepx_extended import create_onstepx_extended
        from services.mount_control.lx200 import ConnectionType

        client = create_onstepx_extended(
            host="10.0.0.100",
            port=8888,
            use_tcp=True,
        )

        assert client.connection_type == ConnectionType.TCP
        assert client.host == "10.0.0.100"
        assert client.port == 8888

    def test_create_onstepx_extended_serial(self):
        """Test factory function with serial connection."""
        from services.mount_control.onstepx_extended import create_onstepx_extended
        from services.mount_control.lx200 import ConnectionType

        client = create_onstepx_extended(
            use_tcp=False,
            serial_port="/dev/ttyACM0",
        )

        assert client.connection_type == ConnectionType.SERIAL
        assert client.serial_port == "/dev/ttyACM0"


# =============================================================================
# Inheritance Tests
# =============================================================================

class TestInheritance:
    """Unit tests verifying proper inheritance from LX200Client."""

    def test_inherits_from_lx200client(self):
        """Test that OnStepXExtended inherits from LX200Client."""
        from services.mount_control.onstepx_extended import OnStepXExtended
        from services.mount_control.lx200 import LX200Client

        assert issubclass(OnStepXExtended, LX200Client)

    def test_has_lx200_methods(self, onstepx_client):
        """Test that OnStepXExtended has LX200Client methods."""
        # Core LX200 methods should be available
        assert hasattr(onstepx_client, "get_ra")
        assert hasattr(onstepx_client, "get_dec")
        assert hasattr(onstepx_client, "goto_ra_dec")
        assert hasattr(onstepx_client, "park")
        assert hasattr(onstepx_client, "unpark")
        assert hasattr(onstepx_client, "start_tracking")
        assert hasattr(onstepx_client, "stop_tracking")

    def test_has_extended_methods(self, onstepx_client):
        """Test that OnStepXExtended has extended methods."""
        # Extended OnStepX methods
        assert hasattr(onstepx_client, "pec_status")
        assert hasattr(onstepx_client, "pec_start_playback")
        assert hasattr(onstepx_client, "pec_stop")
        assert hasattr(onstepx_client, "pec_record")
        assert hasattr(onstepx_client, "get_driver_status")
        assert hasattr(onstepx_client, "set_tracking_offset")
        assert hasattr(onstepx_client, "set_reticle_brightness")


# =============================================================================
# Connection State Tests
# =============================================================================

class TestConnectionState:
    """Unit tests for connection state handling."""

    @pytest.mark.asyncio
    async def test_pec_status_not_connected(self, onstepx_client):
        """Test PEC status when not connected returns default values."""
        # Client is not connected by default
        status = await onstepx_client.pec_status()

        assert status.recording is False
        assert status.playing is False
        assert status.ready is True  # Defaults to ready when no response

    @pytest.mark.asyncio
    async def test_get_driver_status_not_connected(self, onstepx_client):
        """Test driver status when not connected returns default values."""
        status = await onstepx_client.get_driver_status(axis=1)

        assert status.standstill is False
        assert status.overtemperature is False

    @pytest.mark.asyncio
    async def test_set_tracking_offset_not_connected(self, onstepx_client):
        """Test tracking offset setting when not connected."""
        result = await onstepx_client.set_tracking_offset(10.0)

        assert result is False


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Unit tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_pec_status_malformed_progress(self, connected_client, mock_socket):
        """Test PEC status with malformed progress response."""
        responses = [b"R#", b"abc#"]  # Invalid progress value
        mock_socket.recv = Mock(side_effect=responses)

        status = await connected_client.pec_status()

        assert status.recording is True
        assert status.record_progress == 0.0  # Should default to 0

    @pytest.mark.asyncio
    async def test_driver_status_with_lowercase_hex(self, connected_client, mock_socket):
        """Test driver status with lowercase hex response."""
        mock_socket.recv = Mock(return_value=b"8a000000#")

        status = await connected_client.get_driver_status(axis=1)

        # Should parse lowercase hex correctly
        assert status.standstill is True

    @pytest.mark.asyncio
    async def test_large_tracking_offset(self, connected_client, mock_socket):
        """Test setting very large tracking offset."""
        mock_socket.recv = Mock(return_value=b"1#")

        result = await connected_client.set_tracking_offset(999999.9999)

        assert result is True

    @pytest.mark.asyncio
    async def test_pec_status_combined_flags(self, connected_client, mock_socket):
        """Test PEC status with multiple flags in response."""
        mock_socket.recv = Mock(return_value=b"IrP#")  # Index, ready, Playing

        status = await connected_client.pec_status()

        assert status.index_detected is True
        assert status.ready is True
        assert status.playing is True

    @pytest.mark.asyncio
    async def test_motor_temp_negative(self, connected_client, mock_socket):
        """Test motor temperature below zero (cold environment)."""
        mock_socket.recv = Mock(return_value=b"-15.5#")

        temp = await connected_client.get_motor_temperature(axis=1)

        assert temp == -15.5

    @pytest.mark.asyncio
    async def test_get_driver_status_zero(self, connected_client, mock_socket):
        """Test driver status when all flags are zero."""
        mock_socket.recv = Mock(return_value=b"00000000#")

        status = await connected_client.get_driver_status(axis=1)

        assert status.standstill is False
        assert status.open_load_a is False
        assert status.open_load_b is False
        assert status.short_to_ground_a is False
        assert status.short_to_ground_b is False
        assert status.overtemperature is False
        assert status.overtemperature_pre is False
        assert status.stallguard is False


# =============================================================================
# Complete Workflow Tests
# =============================================================================

class TestWorkflows:
    """Integration-style tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_pec_training_workflow(self, connected_client, mock_socket):
        """Test complete PEC training workflow."""
        # Simulate workflow responses
        responses = [
            b"1#",  # Clear
            b"1#",  # Record
            b"R#",  # Status (recording)
            b"100#",  # Progress (100%)
            b"1#",  # Stop
            b"r#",  # Status (ready)
            b"1#",  # Save to EEPROM
            b"1#",  # Start playback
            b"P#",  # Status (playing)
        ]
        mock_socket.recv = Mock(side_effect=responses)

        # Clear existing PEC data
        assert await connected_client.pec_clear() is True

        # Start recording
        assert await connected_client.pec_record() is True

        # Check status while recording
        status = await connected_client.pec_status()
        assert status.recording is True
        assert status.record_progress == 1.0

        # Stop recording
        assert await connected_client.pec_stop() is True

        # Check status after recording
        status = await connected_client.pec_status()
        assert status.ready is True

        # Save to EEPROM
        assert await connected_client.pec_save_to_eeprom() is True

        # Start playback
        assert await connected_client.pec_start_playback() is True

        # Verify playback active
        status = await connected_client.pec_status()
        assert status.playing is True

    @pytest.mark.asyncio
    async def test_driver_diagnostics_workflow(self, connected_client, mock_socket):
        """Test complete driver diagnostics workflow."""
        responses = [
            b"80000000#",  # Axis 1 status (standstill)
            b"00000000#",  # Axis 2 status (all clear)
            b"35.5#",  # Axis 1 temperature
            b"33.0#",  # Axis 2 temperature
        ]
        mock_socket.recv = Mock(side_effect=responses)

        # Get all driver status
        all_status = await connected_client.get_all_driver_status()
        assert all_status["axis1_ra"].standstill is True
        assert all_status["axis2_dec"].standstill is False

        # Get motor temperatures
        temp1 = await connected_client.get_motor_temperature(1)
        temp2 = await connected_client.get_motor_temperature(2)
        assert temp1 == 35.5
        assert temp2 == 33.0
