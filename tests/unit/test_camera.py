"""
Unit tests for NIGHTWATCH ASI camera service.

Tests camera settings, capture modes, presets, and data structures.
"""

import pytest
from pathlib import Path
from datetime import datetime
from services.camera.asi_camera import (
    ASICamera,
    CameraSettings,
    CameraInfo,
    CaptureSession,
    ImageFormat,
    CaptureMode,
)


class TestImageFormat:
    """Tests for ImageFormat enum."""

    def test_raw8_format(self):
        """Test RAW8 format value."""
        assert ImageFormat.RAW8.value == "RAW8"

    def test_raw16_format(self):
        """Test RAW16 format value."""
        assert ImageFormat.RAW16.value == "RAW16"

    def test_ser_format(self):
        """Test SER format value."""
        assert ImageFormat.SER.value == "SER"

    def test_fits_format(self):
        """Test FITS format value."""
        assert ImageFormat.FITS.value == "FITS"

    def test_png_format(self):
        """Test PNG format value."""
        assert ImageFormat.PNG.value == "PNG"


class TestCaptureMode:
    """Tests for CaptureMode enum."""

    def test_planetary_mode(self):
        """Test planetary capture mode."""
        assert CaptureMode.PLANETARY.value == "planetary"

    def test_lunar_mode(self):
        """Test lunar capture mode."""
        assert CaptureMode.LUNAR.value == "lunar"

    def test_deep_sky_mode(self):
        """Test deep sky capture mode."""
        assert CaptureMode.DEEP_SKY.value == "deep_sky"

    def test_preview_mode(self):
        """Test preview capture mode."""
        assert CaptureMode.PREVIEW.value == "preview"


class TestCameraSettings:
    """Tests for CameraSettings dataclass."""

    def test_default_settings(self):
        """Test default camera settings."""
        settings = CameraSettings()

        assert settings.gain == 250
        assert settings.exposure_ms == 10.0
        assert settings.roi is None
        assert settings.binning == 1
        assert settings.format == ImageFormat.SER
        assert settings.usb_bandwidth == 80
        assert settings.high_speed_mode is True
        assert settings.flip_horizontal is False
        assert settings.flip_vertical is False
        assert settings.target_temp_c is None
        assert settings.cooler_on is False

    def test_custom_settings(self):
        """Test custom camera settings."""
        settings = CameraSettings(
            gain=300,
            exposure_ms=15.0,
            roi=(0, 0, 640, 480),
            binning=2,
            format=ImageFormat.FITS,
            high_speed_mode=False,
            flip_horizontal=True,
            target_temp_c=-10.0,
            cooler_on=True,
        )

        assert settings.gain == 300
        assert settings.exposure_ms == 15.0
        assert settings.roi == (0, 0, 640, 480)
        assert settings.binning == 2
        assert settings.format == ImageFormat.FITS
        assert settings.high_speed_mode is False
        assert settings.flip_horizontal is True
        assert settings.target_temp_c == -10.0
        assert settings.cooler_on is True

    def test_roi_tuple_structure(self):
        """Test ROI tuple structure (x, y, width, height)."""
        settings = CameraSettings(roi=(100, 50, 800, 600))

        x, y, width, height = settings.roi
        assert x == 100
        assert y == 50
        assert width == 800
        assert height == 600


class TestCameraInfo:
    """Tests for CameraInfo dataclass."""

    def test_camera_info_creation(self):
        """Test creating camera info."""
        info = CameraInfo(
            name="ZWO ASI290MC",
            camera_id=1,
            max_width=1936,
            max_height=1096,
            pixel_size_um=2.9,
            is_color=True,
            has_cooler=False,
            bit_depth=12,
            usb_host="USB3.0"
        )

        assert info.name == "ZWO ASI290MC"
        assert info.camera_id == 1
        assert info.max_width == 1936
        assert info.max_height == 1096
        assert info.pixel_size_um == 2.9
        assert info.is_color is True
        assert info.has_cooler is False
        assert info.bit_depth == 12
        assert info.usb_host == "USB3.0"

    def test_cooled_camera_info(self):
        """Test camera info for cooled camera."""
        info = CameraInfo(
            name="ZWO ASI294MC Pro",
            camera_id=2,
            max_width=4144,
            max_height=2822,
            pixel_size_um=4.63,
            is_color=True,
            has_cooler=True,
            bit_depth=14,
            usb_host="USB3.0"
        )

        assert info.has_cooler is True


class TestCaptureSession:
    """Tests for CaptureSession dataclass."""

    def test_capture_session_creation(self):
        """Test creating capture session."""
        settings = CameraSettings(gain=280, exposure_ms=8.0)
        session = CaptureSession(
            session_id="mars_20240115_220000",
            target="mars",
            start_time=datetime.now(),
            settings=settings,
            output_path=Path("/data/captures/2024-01-15/mars_20240115_220000.ser")
        )

        assert session.session_id == "mars_20240115_220000"
        assert session.target == "mars"
        assert session.settings.gain == 280
        assert session.frame_count == 0
        assert session.duration_sec == 0.0
        assert session.complete is False
        assert session.error is None

    def test_capture_session_with_frames(self):
        """Test capture session with accumulated frames."""
        settings = CameraSettings()
        session = CaptureSession(
            session_id="test_123",
            target="jupiter",
            start_time=datetime.now(),
            settings=settings,
            output_path=Path("/data/test.ser"),
            frame_count=1500,
            duration_sec=60.0,
            complete=True
        )

        assert session.frame_count == 1500
        assert session.duration_sec == 60.0
        assert session.complete is True

    def test_capture_session_with_error(self):
        """Test capture session with error."""
        settings = CameraSettings()
        session = CaptureSession(
            session_id="test_err",
            target="saturn",
            start_time=datetime.now(),
            settings=settings,
            output_path=Path("/data/test.ser"),
            complete=False,
            error="USB connection lost"
        )

        assert session.error == "USB connection lost"
        assert session.complete is False


class TestASICameraPresets:
    """Tests for ASI camera presets."""

    def test_presets_exist(self):
        """Test that all standard presets exist."""
        presets = ASICamera.PRESETS

        assert "mars" in presets
        assert "jupiter" in presets
        assert "saturn" in presets
        assert "moon" in presets
        assert "sun" in presets
        assert "deep_sky" in presets

    def test_mars_preset(self):
        """Test Mars preset values (Damian Peach recommendations)."""
        preset = ASICamera.PRESETS["mars"]

        assert preset.gain == 280
        assert preset.exposure_ms == 8.0
        assert preset.roi == (0, 0, 640, 480)

    def test_jupiter_preset(self):
        """Test Jupiter preset values."""
        preset = ASICamera.PRESETS["jupiter"]

        assert preset.gain == 250
        assert preset.exposure_ms == 12.0
        assert preset.roi == (0, 0, 800, 600)

    def test_saturn_preset(self):
        """Test Saturn preset values."""
        preset = ASICamera.PRESETS["saturn"]

        assert preset.gain == 300
        assert preset.exposure_ms == 15.0

    def test_moon_preset(self):
        """Test Moon preset values."""
        preset = ASICamera.PRESETS["moon"]

        assert preset.gain == 100
        assert preset.exposure_ms == 3.0

    def test_sun_preset(self):
        """Test Sun preset values (requires solar filter!)."""
        preset = ASICamera.PRESETS["sun"]

        assert preset.gain == 50
        assert preset.exposure_ms == 1.0

    def test_deep_sky_preset(self):
        """Test deep sky preset values."""
        preset = ASICamera.PRESETS["deep_sky"]

        assert preset.gain == 200
        assert preset.exposure_ms == 30000.0  # 30 second exposure
        assert preset.format == ImageFormat.FITS


class TestASICameraInitialization:
    """Tests for ASI camera initialization."""

    def test_camera_creation(self):
        """Test camera instance creation."""
        camera = ASICamera(camera_index=0)

        assert camera.camera_index == 0
        assert camera.data_dir == Path("/data/captures")
        assert camera.initialized is False
        assert camera.capturing is False
        assert camera.info is None

    def test_camera_custom_data_dir(self):
        """Test camera with custom data directory."""
        custom_dir = Path("/custom/data/path")
        camera = ASICamera(camera_index=1, data_dir=custom_dir)

        assert camera.camera_index == 1
        assert camera.data_dir == custom_dir

    def test_get_preset_valid(self):
        """Test getting valid preset."""
        camera = ASICamera()

        preset = camera.get_preset("mars")
        assert preset.gain == 280

    def test_get_preset_invalid(self):
        """Test getting invalid preset returns default."""
        camera = ASICamera()

        preset = camera.get_preset("invalid_target")
        # Should return default CameraSettings
        assert preset.gain == 250  # Default gain

    def test_get_preset_case_insensitive(self):
        """Test preset lookup is case insensitive."""
        camera = ASICamera()

        preset1 = camera.get_preset("Mars")
        preset2 = camera.get_preset("MARS")
        preset3 = camera.get_preset("mars")

        assert preset1.gain == preset2.gain == preset3.gain


class TestCameraSettingsValidation:
    """Tests for camera settings boundary conditions."""

    def test_gain_bounds(self):
        """Test gain at boundary values."""
        # Minimum gain
        settings_low = CameraSettings(gain=0)
        assert settings_low.gain == 0

        # High gain
        settings_high = CameraSettings(gain=500)
        assert settings_high.gain == 500

    def test_exposure_bounds(self):
        """Test exposure at boundary values."""
        # Very short exposure (planetary)
        settings_short = CameraSettings(exposure_ms=0.1)
        assert settings_short.exposure_ms == 0.1

        # Very long exposure (deep sky)
        settings_long = CameraSettings(exposure_ms=300000.0)  # 5 minutes
        assert settings_long.exposure_ms == 300000.0

    def test_binning_options(self):
        """Test various binning options."""
        for binning in [1, 2, 3, 4]:
            settings = CameraSettings(binning=binning)
            assert settings.binning == binning

    def test_usb_bandwidth_range(self):
        """Test USB bandwidth range."""
        settings_low = CameraSettings(usb_bandwidth=40)
        assert settings_low.usb_bandwidth == 40

        settings_high = CameraSettings(usb_bandwidth=100)
        assert settings_high.usb_bandwidth == 100

    def test_cooling_temperature_range(self):
        """Test cooling temperature range."""
        # Typical cooling temps
        settings_cold = CameraSettings(target_temp_c=-20.0, cooler_on=True)
        assert settings_cold.target_temp_c == -20.0

        # Ambient temp
        settings_ambient = CameraSettings(target_temp_c=10.0, cooler_on=True)
        assert settings_ambient.target_temp_c == 10.0
