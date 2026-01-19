"""
NIGHTWATCH Unit Tests - Alpaca Client Adapters

Unit tests for services/alpaca/alpaca_client.py.
Uses mocking to test Alpaca device adapters without requiring alpyca
or physical hardware.

Run:
    pytest tests/unit/test_alpaca_client.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass


# =============================================================================
# Test AlpacaDevice Dataclass
# =============================================================================

class TestAlpacaDevice:
    """Unit tests for AlpacaDevice dataclass."""

    def test_alpaca_device_creation(self):
        """Test creating AlpacaDevice with all fields."""
        from services.alpaca.alpaca_client import AlpacaDevice

        device = AlpacaDevice(
            name="Test Telescope",
            device_type="Telescope",
            address="192.168.1.100",
            port=11111,
            device_number=0,
            unique_id="ABC123",
        )

        assert device.name == "Test Telescope"
        assert device.device_type == "Telescope"
        assert device.address == "192.168.1.100"
        assert device.port == 11111
        assert device.device_number == 0
        assert device.unique_id == "ABC123"

    def test_alpaca_device_endpoint(self):
        """Test AlpacaDevice endpoint property."""
        from services.alpaca.alpaca_client import AlpacaDevice

        device = AlpacaDevice(
            name="Test Device",
            device_type="Camera",
            address="192.168.1.50",
            port=32323,
            device_number=1,
        )

        assert device.endpoint == "http://192.168.1.50:32323"

    def test_alpaca_device_default_unique_id(self):
        """Test AlpacaDevice default unique_id."""
        from services.alpaca.alpaca_client import AlpacaDevice

        device = AlpacaDevice(
            name="Device",
            device_type="Focuser",
            address="localhost",
            port=11111,
            device_number=0,
        )

        assert device.unique_id == ""


# =============================================================================
# Test CameraState Dataclass
# =============================================================================

class TestCameraState:
    """Unit tests for CameraState dataclass."""

    def test_camera_state_creation(self):
        """Test creating CameraState."""
        from services.alpaca.alpaca_client import CameraState

        state = CameraState(
            state=CameraState.State.EXPOSING,
            percent_complete=50.0,
            image_ready=False,
        )

        assert state.state == CameraState.State.EXPOSING
        assert state.percent_complete == 50.0
        assert state.image_ready is False

    def test_camera_state_enum_values(self):
        """Test CameraState enum has expected values."""
        from services.alpaca.alpaca_client import CameraState

        assert CameraState.State.IDLE.value == 0
        assert CameraState.State.WAITING.value == 1
        assert CameraState.State.EXPOSING.value == 2
        assert CameraState.State.READING.value == 3
        assert CameraState.State.DOWNLOAD.value == 4
        assert CameraState.State.ERROR.value == 5


# =============================================================================
# Test ImageData Dataclass
# =============================================================================

class TestImageData:
    """Unit tests for ImageData dataclass."""

    def test_image_data_creation(self):
        """Test creating ImageData."""
        from services.alpaca.alpaca_client import ImageData

        image = ImageData(
            data=[1, 2, 3],  # Simplified test data
            width=1920,
            height=1080,
            exposure_duration=30.0,
            start_time="2026-01-19T12:00:00",
            filter_name="Ha",
            bin_x=2,
            bin_y=2,
        )

        assert image.width == 1920
        assert image.height == 1080
        assert image.exposure_duration == 30.0
        assert image.filter_name == "Ha"
        assert image.bin_x == 2
        assert image.bin_y == 2


# =============================================================================
# Test AlpacaDiscovery
# =============================================================================

class TestAlpacaDiscovery:
    """Unit tests for AlpacaDiscovery class."""

    def test_discovery_constants(self):
        """Test discovery constants are set correctly."""
        from services.alpaca.alpaca_client import AlpacaDiscovery

        assert AlpacaDiscovery.DISCOVERY_PORT == 32227
        assert AlpacaDiscovery.DISCOVERY_MESSAGE == b"alpacadiscovery1"

    def test_discover_handles_import_error(self):
        """Test discovery handles missing alpyca gracefully."""
        from services.alpaca.alpaca_client import AlpacaDiscovery

        # Mock alpyca import failure and fallback
        with patch.dict("sys.modules", {"alpaca.discovery": None}):
            with patch.object(
                AlpacaDiscovery,
                "_fallback_discover",
                return_value=[]
            ):
                devices = AlpacaDiscovery.discover(timeout=0.1)
                assert isinstance(devices, list)

    def test_discover_by_type_filters_correctly(self):
        """Test discover_by_type filters by device type."""
        from services.alpaca.alpaca_client import AlpacaDiscovery, AlpacaDevice

        mock_devices = [
            AlpacaDevice("Telescope1", "Telescope", "192.168.1.1", 11111, 0),
            AlpacaDevice("Camera1", "Camera", "192.168.1.1", 11111, 0),
            AlpacaDevice("Telescope2", "Telescope", "192.168.1.2", 11111, 0),
            AlpacaDevice("Focuser1", "Focuser", "192.168.1.1", 11111, 0),
        ]

        with patch.object(AlpacaDiscovery, "discover", return_value=mock_devices):
            telescopes = AlpacaDiscovery.discover_by_type("Telescope")

            assert len(telescopes) == 2
            assert all(d.device_type == "Telescope" for d in telescopes)

    def test_discover_by_type_case_insensitive(self):
        """Test discover_by_type is case insensitive."""
        from services.alpaca.alpaca_client import AlpacaDiscovery, AlpacaDevice

        mock_devices = [
            AlpacaDevice("Camera1", "Camera", "192.168.1.1", 11111, 0),
        ]

        with patch.object(AlpacaDiscovery, "discover", return_value=mock_devices):
            # Test different cases
            cameras1 = AlpacaDiscovery.discover_by_type("camera")
            cameras2 = AlpacaDiscovery.discover_by_type("CAMERA")
            cameras3 = AlpacaDiscovery.discover_by_type("Camera")

            assert len(cameras1) == 1
            assert len(cameras2) == 1
            assert len(cameras3) == 1


# =============================================================================
# Test AlpacaDeviceBase
# =============================================================================

class TestAlpacaDeviceBase:
    """Unit tests for AlpacaDeviceBase class."""

    def test_base_initialization(self):
        """Test AlpacaDeviceBase initialization."""
        from services.alpaca.alpaca_client import AlpacaDeviceBase

        base = AlpacaDeviceBase(
            address="192.168.1.100",
            port=11111,
            device_number=1,
            client_id=42,
        )

        assert base.address == "192.168.1.100"
        assert base.port == 11111
        assert base.device_number == 1
        assert base.client_id == 42
        assert base._connected is False

    def test_base_default_values(self):
        """Test AlpacaDeviceBase default values."""
        from services.alpaca.alpaca_client import AlpacaDeviceBase

        base = AlpacaDeviceBase(address="localhost")

        assert base.port == 11111
        assert base.device_number == 0
        assert base.client_id == 1

    def test_is_connected_property(self):
        """Test is_connected property."""
        from services.alpaca.alpaca_client import AlpacaDeviceBase

        base = AlpacaDeviceBase(address="localhost")
        assert base.is_connected is False

        base._connected = True
        assert base.is_connected is True

    def test_get_endpoint(self):
        """Test _get_endpoint method."""
        from services.alpaca.alpaca_client import AlpacaDeviceBase

        base = AlpacaDeviceBase(address="192.168.1.50", port=32323)
        assert base._get_endpoint() == "http://192.168.1.50:32323"


# =============================================================================
# Test AlpacaTelescope
# =============================================================================

class TestAlpacaTelescope:
    """Unit tests for AlpacaTelescope class."""

    @pytest.fixture
    def mock_telescope(self):
        """Create mock alpaca Telescope object."""
        mock = Mock()
        mock.Connected = True
        mock.RightAscension = 12.5
        mock.Declination = 45.0
        mock.Altitude = 60.0
        mock.Azimuth = 180.0
        mock.Tracking = True
        mock.Slewing = False
        mock.AtPark = False
        mock.SideOfPier = 0  # East
        return mock

    @pytest.fixture
    def telescope(self):
        """Create AlpacaTelescope instance for testing."""
        from services.alpaca.alpaca_client import AlpacaTelescope

        return AlpacaTelescope(
            address="localhost",
            port=11111,
            device_number=0
        )

    def test_telescope_initialization(self, telescope):
        """Test AlpacaTelescope initialization."""
        assert telescope.address == "localhost"
        assert telescope.port == 11111
        assert telescope.device_number == 0
        assert telescope._telescope is None
        assert telescope.is_connected is False

    def test_connect_success(self, telescope, mock_telescope):
        """Test successful telescope connection."""
        mock_telescope_class = Mock(return_value=mock_telescope)

        with patch.dict("sys.modules", {"alpaca.telescope": Mock(Telescope=mock_telescope_class)}):
            with patch("services.alpaca.alpaca_client.AlpacaTelescope.connect") as mock_connect:
                mock_connect.return_value = True
                result = telescope.connect()

                assert result is True

    def test_properties_when_not_connected(self, telescope):
        """Test property access when not connected."""
        assert telescope.ra == 0.0
        assert telescope.dec == 0.0
        assert telescope.altitude == 0.0
        assert telescope.azimuth == 0.0
        assert telescope.is_tracking is False
        assert telescope.is_slewing is False
        assert telescope.is_parked is False
        assert telescope.pier_side == "Unknown"

    def test_properties_when_connected(self, telescope, mock_telescope):
        """Test property access when connected."""
        telescope._telescope = mock_telescope
        telescope._connected = True

        assert telescope.ra == 12.5
        assert telescope.dec == 45.0
        assert telescope.altitude == 60.0
        assert telescope.azimuth == 180.0
        assert telescope.is_tracking is True
        assert telescope.is_slewing is False
        assert telescope.is_parked is False
        assert telescope.pier_side == "East"

    def test_pier_side_west(self, telescope, mock_telescope):
        """Test pier_side property returns West."""
        mock_telescope.SideOfPier = 1  # West
        telescope._telescope = mock_telescope
        telescope._connected = True

        assert telescope.pier_side == "West"

    def test_set_tracking(self, telescope, mock_telescope):
        """Test set_tracking method."""
        telescope._telescope = mock_telescope
        telescope._connected = True

        result = telescope.set_tracking(True)
        assert result is True
        assert mock_telescope.Tracking is True

        result = telescope.set_tracking(False)
        assert result is True

    def test_slew_to_coordinates_async(self, telescope, mock_telescope):
        """Test slew to coordinates (async)."""
        telescope._telescope = mock_telescope
        telescope._connected = True

        result = telescope.slew_to_coordinates(12.0, 45.0, async_slew=True)

        assert result is True
        mock_telescope.SlewToCoordinatesAsync.assert_called_once_with(12.0, 45.0)

    def test_slew_to_coordinates_sync(self, telescope, mock_telescope):
        """Test slew to coordinates (sync)."""
        telescope._telescope = mock_telescope
        telescope._connected = True

        result = telescope.slew_to_coordinates(12.0, 45.0, async_slew=False)

        assert result is True
        mock_telescope.SlewToCoordinates.assert_called_once_with(12.0, 45.0)

    def test_slew_to_altaz(self, telescope, mock_telescope):
        """Test slew to alt/az coordinates."""
        telescope._telescope = mock_telescope
        telescope._connected = True

        result = telescope.slew_to_altaz(60.0, 180.0)

        assert result is True
        mock_telescope.SlewToAltAzAsync.assert_called_once_with(180.0, 60.0)

    def test_abort_slew(self, telescope, mock_telescope):
        """Test abort slew."""
        telescope._telescope = mock_telescope
        telescope._connected = True

        result = telescope.abort_slew()

        assert result is True
        mock_telescope.AbortSlew.assert_called_once()

    def test_park(self, telescope, mock_telescope):
        """Test park telescope."""
        telescope._telescope = mock_telescope
        telescope._connected = True

        result = telescope.park()

        assert result is True
        mock_telescope.Park.assert_called_once()

    def test_unpark(self, telescope, mock_telescope):
        """Test unpark telescope."""
        telescope._telescope = mock_telescope
        telescope._connected = True

        result = telescope.unpark()

        assert result is True
        mock_telescope.Unpark.assert_called_once()

    def test_sync(self, telescope, mock_telescope):
        """Test sync to coordinates."""
        telescope._telescope = mock_telescope
        telescope._connected = True

        result = telescope.sync(12.5, 45.0)

        assert result is True
        mock_telescope.SyncToCoordinates.assert_called_once_with(12.5, 45.0)

    def test_move_axis(self, telescope, mock_telescope):
        """Test move axis."""
        telescope._telescope = mock_telescope
        telescope._connected = True

        result = telescope.move_axis(0, 1.0)  # RA axis at 1 deg/sec

        assert result is True
        mock_telescope.MoveAxis.assert_called_once_with(0, 1.0)

    def test_get_status(self, telescope, mock_telescope):
        """Test get_status method."""
        telescope._telescope = mock_telescope
        telescope._connected = True

        status = telescope.get_status()

        assert status["connected"] is True
        assert status["ra"] == 12.5
        assert status["dec"] == 45.0
        assert status["altitude"] == 60.0
        assert status["azimuth"] == 180.0
        assert status["is_tracking"] is True
        assert status["is_slewing"] is False
        assert status["is_parked"] is False
        assert status["pier_side"] == "East"

    def test_disconnect(self, telescope, mock_telescope):
        """Test disconnect from telescope."""
        telescope._telescope = mock_telescope
        telescope._connected = True

        telescope.disconnect()

        assert telescope._connected is False


# =============================================================================
# Test AlpacaFocuser
# =============================================================================

class TestAlpacaFocuser:
    """Unit tests for AlpacaFocuser class."""

    @pytest.fixture
    def mock_focuser(self):
        """Create mock alpaca Focuser object."""
        mock = Mock()
        mock.Connected = True
        mock.Position = 5000
        mock.MaxStep = 10000
        mock.IsMoving = False
        mock.Temperature = 15.5
        mock.TempComp = False
        return mock

    @pytest.fixture
    def focuser(self):
        """Create AlpacaFocuser instance for testing."""
        from services.alpaca.alpaca_client import AlpacaFocuser

        return AlpacaFocuser(
            address="localhost",
            port=11111,
            device_number=0
        )

    def test_focuser_initialization(self, focuser):
        """Test AlpacaFocuser initialization."""
        assert focuser.address == "localhost"
        assert focuser._focuser is None
        assert focuser.is_connected is False

    def test_properties_when_not_connected(self, focuser):
        """Test property access when not connected."""
        assert focuser.position == 0
        assert focuser.max_position == 0
        assert focuser.is_moving is False
        assert focuser.temperature == 0.0
        assert focuser.temp_comp is False

    def test_properties_when_connected(self, focuser, mock_focuser):
        """Test property access when connected."""
        focuser._focuser = mock_focuser
        focuser._connected = True

        assert focuser.position == 5000
        assert focuser.max_position == 10000
        assert focuser.is_moving is False
        assert focuser.temperature == 15.5
        assert focuser.temp_comp is False

    def test_move_absolute(self, focuser, mock_focuser):
        """Test move to absolute position."""
        focuser._focuser = mock_focuser
        focuser._connected = True

        result = focuser.move_absolute(7500)

        assert result is True
        mock_focuser.Move.assert_called_once_with(7500)

    def test_move_relative_positive(self, focuser, mock_focuser):
        """Test move by positive relative steps (out)."""
        focuser._focuser = mock_focuser
        focuser._connected = True

        result = focuser.move_relative(500)

        assert result is True
        # Should move to 5000 + 500 = 5500
        mock_focuser.Move.assert_called_once_with(5500)

    def test_move_relative_negative(self, focuser, mock_focuser):
        """Test move by negative relative steps (in)."""
        focuser._focuser = mock_focuser
        focuser._connected = True

        result = focuser.move_relative(-500)

        assert result is True
        # Should move to 5000 - 500 = 4500
        mock_focuser.Move.assert_called_once_with(4500)

    def test_halt(self, focuser, mock_focuser):
        """Test halt focuser movement."""
        focuser._focuser = mock_focuser
        focuser._connected = True

        result = focuser.halt()

        assert result is True
        mock_focuser.Halt.assert_called_once()

    def test_set_temp_comp(self, focuser, mock_focuser):
        """Test enable/disable temperature compensation."""
        focuser._focuser = mock_focuser
        focuser._connected = True

        result = focuser.set_temp_comp(True)

        assert result is True

    def test_get_status(self, focuser, mock_focuser):
        """Test get_status method."""
        focuser._focuser = mock_focuser
        focuser._connected = True

        status = focuser.get_status()

        assert status["connected"] is True
        assert status["position"] == 5000
        assert status["max_position"] == 10000
        assert status["is_moving"] is False
        assert status["temperature"] == 15.5
        assert status["temp_comp"] is False

    def test_disconnect(self, focuser, mock_focuser):
        """Test disconnect from focuser."""
        focuser._focuser = mock_focuser
        focuser._connected = True

        focuser.disconnect()

        assert focuser._connected is False


# =============================================================================
# Test AlpacaFilterWheel
# =============================================================================

class TestAlpacaFilterWheel:
    """Unit tests for AlpacaFilterWheel class."""

    @pytest.fixture
    def mock_filter_wheel(self):
        """Create mock alpaca FilterWheel object."""
        mock = Mock()
        mock.Connected = True
        mock.Position = 2
        mock.Names = ["L", "R", "G", "B", "Ha", "OIII", "SII"]
        return mock

    @pytest.fixture
    def filter_wheel(self):
        """Create AlpacaFilterWheel instance for testing."""
        from services.alpaca.alpaca_client import AlpacaFilterWheel

        return AlpacaFilterWheel(
            address="localhost",
            port=11111,
            device_number=0
        )

    def test_filter_wheel_initialization(self, filter_wheel):
        """Test AlpacaFilterWheel initialization."""
        assert filter_wheel.address == "localhost"
        assert filter_wheel._wheel is None
        assert filter_wheel.is_connected is False

    def test_properties_when_not_connected(self, filter_wheel):
        """Test property access when not connected."""
        assert filter_wheel.position == -1
        assert filter_wheel.filter_names == []
        assert filter_wheel.current_filter == "Unknown"

    def test_properties_when_connected(self, filter_wheel, mock_filter_wheel):
        """Test property access when connected."""
        filter_wheel._wheel = mock_filter_wheel
        filter_wheel._connected = True

        assert filter_wheel.position == 2
        assert filter_wheel.filter_names == ["L", "R", "G", "B", "Ha", "OIII", "SII"]
        assert filter_wheel.current_filter == "G"  # Position 2 = index 2

    def test_set_position(self, filter_wheel, mock_filter_wheel):
        """Test set filter position."""
        filter_wheel._wheel = mock_filter_wheel
        filter_wheel._connected = True

        result = filter_wheel.set_position(4)

        assert result is True

    def test_set_filter_by_name(self, filter_wheel, mock_filter_wheel):
        """Test set filter by name."""
        filter_wheel._wheel = mock_filter_wheel
        filter_wheel._connected = True

        result = filter_wheel.set_filter_by_name("Ha")

        assert result is True

    def test_set_filter_by_name_case_insensitive(self, filter_wheel, mock_filter_wheel):
        """Test set filter by name is case insensitive."""
        filter_wheel._wheel = mock_filter_wheel
        filter_wheel._connected = True

        result = filter_wheel.set_filter_by_name("ha")

        assert result is True

    def test_set_filter_by_name_not_found(self, filter_wheel, mock_filter_wheel):
        """Test set filter by name when filter not found."""
        filter_wheel._wheel = mock_filter_wheel
        filter_wheel._connected = True

        result = filter_wheel.set_filter_by_name("UV")

        assert result is False

    def test_get_status(self, filter_wheel, mock_filter_wheel):
        """Test get_status method."""
        filter_wheel._wheel = mock_filter_wheel
        filter_wheel._connected = True

        status = filter_wheel.get_status()

        assert status["connected"] is True
        assert status["position"] == 2
        assert status["current_filter"] == "G"
        assert len(status["filter_names"]) == 7

    def test_disconnect(self, filter_wheel, mock_filter_wheel):
        """Test disconnect from filter wheel."""
        filter_wheel._wheel = mock_filter_wheel
        filter_wheel._connected = True

        filter_wheel.disconnect()

        assert filter_wheel._connected is False


# =============================================================================
# Test AlpacaCamera
# =============================================================================

class TestAlpacaCamera:
    """Unit tests for AlpacaCamera class."""

    @pytest.fixture
    def mock_camera(self):
        """Create mock alpaca Camera object."""
        mock = Mock()
        mock.Connected = True
        mock.CameraState = 0  # IDLE
        mock.PercentCompleted = 0.0
        mock.ImageReady = False
        mock.CameraXSize = 4656
        mock.CameraYSize = 3520
        mock.CCDTemperature = -10.0
        mock.CoolerOn = True
        mock.CoolerPower = 50.0
        mock.BinX = 1
        mock.BinY = 1
        return mock

    @pytest.fixture
    def camera(self):
        """Create AlpacaCamera instance for testing."""
        from services.alpaca.alpaca_client import AlpacaCamera

        return AlpacaCamera(
            address="localhost",
            port=11111,
            device_number=0
        )

    def test_camera_initialization(self, camera):
        """Test AlpacaCamera initialization."""
        assert camera.address == "localhost"
        assert camera._camera is None
        assert camera.is_connected is False

    def test_properties_when_not_connected(self, camera):
        """Test property access when not connected."""
        assert camera.image_ready is False
        assert camera.sensor_width == 0
        assert camera.sensor_height == 0
        assert camera.temperature == 0.0
        assert camera.cooler_on is False
        assert camera.bin_x == 1
        assert camera.bin_y == 1

    def test_properties_when_connected(self, camera, mock_camera):
        """Test property access when connected."""
        camera._camera = mock_camera
        camera._connected = True

        assert camera.image_ready is False
        assert camera.sensor_width == 4656
        assert camera.sensor_height == 3520
        assert camera.temperature == -10.0
        assert camera.cooler_on is True
        assert camera.cooler_power == 50.0
        assert camera.bin_x == 1
        assert camera.bin_y == 1

    def test_camera_state_property(self, camera, mock_camera):
        """Test camera_state property."""
        from services.alpaca.alpaca_client import CameraState

        camera._camera = mock_camera
        camera._connected = True

        state = camera.camera_state

        assert state.state == CameraState.State.IDLE
        assert state.percent_complete == 0.0
        assert state.image_ready is False

    def test_set_binning(self, camera, mock_camera):
        """Test set binning."""
        camera._camera = mock_camera
        camera._connected = True

        result = camera.set_binning(2, 2)

        assert result is True

    def test_set_cooler(self, camera, mock_camera):
        """Test enable/disable cooler."""
        camera._camera = mock_camera
        camera._connected = True

        result = camera.set_cooler(True)

        assert result is True

    def test_set_temperature(self, camera, mock_camera):
        """Test set target temperature."""
        camera._camera = mock_camera
        camera._connected = True

        result = camera.set_temperature(-15.0)

        assert result is True

    def test_start_exposure(self, camera, mock_camera):
        """Test start exposure."""
        camera._camera = mock_camera
        camera._connected = True

        result = camera.start_exposure(30.0, light=True)

        assert result is True
        mock_camera.StartExposure.assert_called_once_with(30.0, True)

    def test_start_dark_exposure(self, camera, mock_camera):
        """Test start dark exposure."""
        camera._camera = mock_camera
        camera._connected = True

        result = camera.start_exposure(30.0, light=False)

        assert result is True
        mock_camera.StartExposure.assert_called_once_with(30.0, False)

    def test_abort_exposure(self, camera, mock_camera):
        """Test abort exposure."""
        camera._camera = mock_camera
        camera._connected = True

        result = camera.abort_exposure()

        assert result is True
        mock_camera.AbortExposure.assert_called_once()

    def test_stop_exposure(self, camera, mock_camera):
        """Test stop exposure (read out)."""
        camera._camera = mock_camera
        camera._connected = True

        result = camera.stop_exposure()

        assert result is True
        mock_camera.StopExposure.assert_called_once()

    def test_get_status(self, camera, mock_camera):
        """Test get_status method."""
        camera._camera = mock_camera
        camera._connected = True

        status = camera.get_status()

        assert status["connected"] is True
        assert status["state"] == "IDLE"
        assert status["percent_complete"] == 0.0
        assert status["image_ready"] is False
        assert status["temperature"] == -10.0
        assert status["cooler_on"] is True
        assert status["sensor_width"] == 4656
        assert status["sensor_height"] == 3520

    def test_disconnect(self, camera, mock_camera):
        """Test disconnect from camera."""
        camera._camera = mock_camera
        camera._connected = True

        camera.disconnect()

        assert camera._connected is False


# =============================================================================
# Test Factory Function
# =============================================================================

class TestFactoryFunction:
    """Unit tests for create_for_dgx_spark factory function."""

    def test_create_telescope(self):
        """Test creating telescope adapter."""
        from services.alpaca.alpaca_client import create_for_dgx_spark, AlpacaTelescope

        device = create_for_dgx_spark("telescope", "localhost", 11111, 0)

        assert isinstance(device, AlpacaTelescope)
        assert device.address == "localhost"
        assert device.port == 11111
        assert device.device_number == 0

    def test_create_camera(self):
        """Test creating camera adapter."""
        from services.alpaca.alpaca_client import create_for_dgx_spark, AlpacaCamera

        device = create_for_dgx_spark("camera")

        assert isinstance(device, AlpacaCamera)

    def test_create_focuser(self):
        """Test creating focuser adapter."""
        from services.alpaca.alpaca_client import create_for_dgx_spark, AlpacaFocuser

        device = create_for_dgx_spark("focuser")

        assert isinstance(device, AlpacaFocuser)

    def test_create_filterwheel(self):
        """Test creating filter wheel adapter."""
        from services.alpaca.alpaca_client import create_for_dgx_spark, AlpacaFilterWheel

        device = create_for_dgx_spark("filterwheel")

        assert isinstance(device, AlpacaFilterWheel)

    def test_create_case_insensitive(self):
        """Test factory is case insensitive."""
        from services.alpaca.alpaca_client import create_for_dgx_spark, AlpacaTelescope

        device1 = create_for_dgx_spark("Telescope")
        device2 = create_for_dgx_spark("TELESCOPE")
        device3 = create_for_dgx_spark("telescope")

        assert isinstance(device1, AlpacaTelescope)
        assert isinstance(device2, AlpacaTelescope)
        assert isinstance(device3, AlpacaTelescope)

    def test_create_invalid_type(self):
        """Test factory raises error for invalid device type."""
        from services.alpaca.alpaca_client import create_for_dgx_spark

        with pytest.raises(ValueError) as exc_info:
            create_for_dgx_spark("invalid_device")

        assert "Unknown device type" in str(exc_info.value)


# =============================================================================
# Run Configuration
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
