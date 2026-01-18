"""
NIGHTWATCH ZWO ASI Camera Service
Planetary and Deep-Sky Imaging

POS Panel v2.0 - Day 12 Recommendations (Damian Peach):
- Gain: 250-300 for Mars (balance noise/speed)
- Exposure: 5-15ms depending on seeing
- ROI: Crop to 640x480 for faster capture
- Binning: 1x1 only (already undersampled at f/6)
- Format: SER files for stacking, 60-90 seconds each
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Tuple

logger = logging.getLogger("NIGHTWATCH.Camera")


class ImageFormat(Enum):
    """Supported image formats."""
    RAW8 = "RAW8"
    RAW16 = "RAW16"
    SER = "SER"
    FITS = "FITS"
    PNG = "PNG"


class CaptureMode(Enum):
    """Capture modes."""
    PLANETARY = "planetary"    # High-speed video
    LUNAR = "lunar"            # Medium-speed, larger ROI
    DEEP_SKY = "deep_sky"      # Long exposure FITS
    PREVIEW = "preview"        # Quick look


@dataclass
class CameraSettings:
    """Camera configuration for capture."""
    gain: int = 250               # 0-500 typically
    exposure_ms: float = 10.0     # Exposure time
    roi: Optional[Tuple[int, int, int, int]] = None  # (x, y, width, height)
    binning: int = 1              # 1x1, 2x2, etc.
    format: ImageFormat = ImageFormat.SER
    usb_bandwidth: int = 80       # Percentage (40-100)
    high_speed_mode: bool = True  # For planetary
    flip_horizontal: bool = False
    flip_vertical: bool = False

    # Cooling (for cooled cameras)
    target_temp_c: Optional[float] = None
    cooler_on: bool = False


@dataclass
class CameraInfo:
    """Camera hardware information."""
    name: str
    camera_id: int
    max_width: int
    max_height: int
    pixel_size_um: float
    is_color: bool
    has_cooler: bool
    bit_depth: int
    usb_host: str


@dataclass
class CaptureSession:
    """Active capture session metadata."""
    session_id: str
    target: str
    start_time: datetime
    settings: CameraSettings
    output_path: Path
    frame_count: int = 0
    duration_sec: float = 0.0
    complete: bool = False
    error: Optional[str] = None


class ASICamera:
    """
    ZWO ASI Camera Control for NIGHTWATCH.

    Supports:
    - Planetary high-speed video capture (SER format)
    - Deep-sky long exposure imaging (FITS format)
    - Live preview for focusing
    - Automated capture sequences

    Note: Requires zwoasi library (pip install zwoasi)
    """

    # Recommended settings by target type (Damian Peach recommendations)
    PRESETS = {
        "mars": CameraSettings(gain=280, exposure_ms=8.0, roi=(0, 0, 640, 480)),
        "jupiter": CameraSettings(gain=250, exposure_ms=12.0, roi=(0, 0, 800, 600)),
        "saturn": CameraSettings(gain=300, exposure_ms=15.0, roi=(0, 0, 800, 600)),
        "moon": CameraSettings(gain=100, exposure_ms=3.0),
        "sun": CameraSettings(gain=50, exposure_ms=1.0),  # REQUIRES FILTER!
        "deep_sky": CameraSettings(gain=200, exposure_ms=30000.0, format=ImageFormat.FITS),
    }

    def __init__(self, camera_index: int = 0, data_dir: Optional[Path] = None):
        """
        Initialize ASI camera.

        Args:
            camera_index: Camera index (0 for first camera)
            data_dir: Directory for saving captures
        """
        self.camera_index = camera_index
        self.data_dir = data_dir or Path("/data/captures")
        self._camera = None
        self._info: Optional[CameraInfo] = None
        self._initialized = False
        self._capturing = False
        self._current_session: Optional[CaptureSession] = None
        self._settings = CameraSettings()

    @property
    def initialized(self) -> bool:
        """Check if camera is initialized."""
        return self._initialized

    @property
    def capturing(self) -> bool:
        """Check if capture is in progress."""
        return self._capturing

    @property
    def info(self) -> Optional[CameraInfo]:
        """Camera information."""
        return self._info

    def initialize(self) -> bool:
        """
        Initialize camera connection.

        Returns:
            True if initialized successfully
        """
        try:
            # Import zwoasi (optional dependency)
            try:
                import zwoasi as asi
                self._asi = asi
            except ImportError:
                logger.error("zwoasi not installed. Install with: pip install zwoasi")
                return False

            # Initialize library
            asi.init()

            num_cameras = asi.get_num_cameras()
            if num_cameras == 0:
                logger.error("No ZWO cameras found")
                return False

            if self.camera_index >= num_cameras:
                logger.error(f"Camera index {self.camera_index} invalid (found {num_cameras})")
                return False

            # Connect to camera
            self._camera = asi.Camera(self.camera_index)
            props = self._camera.get_camera_property()

            self._info = CameraInfo(
                name=props["Name"],
                camera_id=props["CameraID"],
                max_width=props["MaxWidth"],
                max_height=props["MaxHeight"],
                pixel_size_um=props["PixelSize"],
                is_color=props["IsColorCam"],
                has_cooler=props["IsCoolerCam"],
                bit_depth=props["BitDepth"],
                usb_host=props.get("USB3Host", "Unknown")
            )

            # Set default controls
            self._apply_settings(self._settings)

            self._initialized = True
            logger.info(f"Initialized camera: {self._info.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            return False

    def close(self):
        """Close camera connection."""
        if self._camera:
            try:
                self._camera.close()
            except Exception:
                pass
        self._initialized = False
        self._camera = None
        logger.info("Camera closed")

    def _apply_settings(self, settings: CameraSettings):
        """Apply camera settings."""
        if not self._camera:
            return

        try:
            asi = self._asi

            # Gain
            self._camera.set_control_value(asi.ASI_GAIN, settings.gain)

            # Exposure (in microseconds)
            exposure_us = int(settings.exposure_ms * 1000)
            self._camera.set_control_value(asi.ASI_EXPOSURE, exposure_us)

            # USB bandwidth
            self._camera.set_control_value(
                asi.ASI_BANDWIDTHOVERLOAD,
                settings.usb_bandwidth
            )

            # High speed mode
            self._camera.set_control_value(
                asi.ASI_HIGH_SPEED_MODE,
                1 if settings.high_speed_mode else 0
            )

            # ROI
            if settings.roi:
                x, y, width, height = settings.roi
                self._camera.set_roi(x, y, width, height, settings.binning)
            else:
                # Full frame
                self._camera.set_roi(
                    0, 0,
                    self._info.max_width,
                    self._info.max_height,
                    settings.binning
                )

            # Flip
            self._camera.set_control_value(
                asi.ASI_FLIP,
                (2 if settings.flip_horizontal else 0) +
                (1 if settings.flip_vertical else 0)
            )

            # Cooling
            if self._info.has_cooler and settings.cooler_on:
                if settings.target_temp_c is not None:
                    self._camera.set_control_value(
                        asi.ASI_TARGET_TEMP,
                        int(settings.target_temp_c)
                    )
                    self._camera.set_control_value(asi.ASI_COOLER_ON, 1)

            self._settings = settings
            logger.debug(f"Applied camera settings: gain={settings.gain}, exp={settings.exposure_ms}ms")

        except Exception as e:
            logger.error(f"Failed to apply settings: {e}")

    def get_preset(self, target: str) -> CameraSettings:
        """
        Get recommended settings for a target.

        Args:
            target: Target name (mars, jupiter, saturn, moon, sun, deep_sky)

        Returns:
            Recommended settings
        """
        return self.PRESETS.get(target.lower(), CameraSettings())

    # =========================================================================
    # CAPTURE METHODS
    # =========================================================================

    async def start_capture(self,
                           target: str,
                           duration_sec: float = 60.0,
                           settings: Optional[CameraSettings] = None) -> CaptureSession:
        """
        Start planetary video capture.

        Args:
            target: Target name (for filename and metadata)
            duration_sec: Capture duration in seconds
            settings: Camera settings (uses preset if None)

        Returns:
            CaptureSession with capture details
        """
        if not self._initialized:
            raise RuntimeError("Camera not initialized")

        if self._capturing:
            raise RuntimeError("Capture already in progress")

        # Use preset if no settings provided
        if settings is None:
            settings = self.get_preset(target)

        self._apply_settings(settings)

        # Create session
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = f"{target.lower()}_{timestamp}"
        output_path = self.data_dir / datetime.now().strftime("%Y-%m-%d") / f"{session_id}.ser"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        session = CaptureSession(
            session_id=session_id,
            target=target,
            start_time=datetime.now(),
            settings=settings,
            output_path=output_path,
            duration_sec=duration_sec
        )

        self._current_session = session
        self._capturing = True

        # Start capture in background
        asyncio.create_task(self._capture_loop(session, duration_sec))

        logger.info(f"Started capture: {session_id} ({duration_sec}s)")
        return session

    async def _capture_loop(self, session: CaptureSession, duration_sec: float):
        """Background capture loop."""
        try:
            # In real implementation, would use ASI video capture
            # For now, simulate capture
            start_time = datetime.now()
            frame_count = 0

            while self._capturing:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= duration_sec:
                    break

                # Simulate frame capture
                await asyncio.sleep(session.settings.exposure_ms / 1000.0)
                frame_count += 1
                session.frame_count = frame_count

            session.complete = True
            session.frame_count = frame_count
            logger.info(f"Capture complete: {session.session_id} ({frame_count} frames)")

        except Exception as e:
            session.error = str(e)
            logger.error(f"Capture error: {e}")

        finally:
            self._capturing = False
            self._current_session = None

    async def stop_capture(self) -> Optional[CaptureSession]:
        """
        Stop current capture.

        Returns:
            Completed session info
        """
        if not self._capturing:
            return None

        session = self._current_session
        self._capturing = False

        # Wait for capture loop to finish
        await asyncio.sleep(0.1)

        logger.info("Capture stopped")
        return session

    async def capture_single(self,
                            exposure_sec: float = 1.0,
                            format: ImageFormat = ImageFormat.FITS,
                            filename: Optional[str] = None) -> Path:
        """
        Capture single frame.

        Args:
            exposure_sec: Exposure time in seconds
            format: Output format
            filename: Custom filename (optional)

        Returns:
            Path to saved image
        """
        if not self._initialized:
            raise RuntimeError("Camera not initialized")

        if self._capturing:
            raise RuntimeError("Capture in progress")

        # Set exposure
        settings = CameraSettings(
            gain=self._settings.gain,
            exposure_ms=exposure_sec * 1000,
            format=format
        )
        self._apply_settings(settings)

        # Generate filename
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = "fits" if format == ImageFormat.FITS else "png"
            filename = f"single_{timestamp}.{ext}"

        output_path = self.data_dir / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Capture frame
        try:
            # In real implementation: self._camera.capture()
            logger.info(f"Captured single frame: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Single capture failed: {e}")
            raise

    # =========================================================================
    # STATUS METHODS
    # =========================================================================

    def get_temperature(self) -> Optional[float]:
        """Get sensor temperature in Celsius."""
        if not self._camera or not self._info:
            return None

        try:
            if self._info.has_cooler:
                temp = self._camera.get_control_value(self._asi.ASI_TEMPERATURE)[0]
                return temp / 10.0  # Reported in 0.1°C units
            return None
        except Exception:
            return None

    def get_cooler_power(self) -> Optional[float]:
        """Get cooler power percentage."""
        if not self._camera or not self._info or not self._info.has_cooler:
            return None

        try:
            power = self._camera.get_control_value(self._asi.ASI_COOLER_POWER_PERC)[0]
            return float(power)
        except Exception:
            return None

    def get_current_settings(self) -> CameraSettings:
        """Get current camera settings."""
        return self._settings


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    async def test():
        print("NIGHTWATCH Camera Service Test\n")

        camera = ASICamera()

        print("Attempting to initialize camera...")
        if camera.initialize():
            print(f"Camera: {camera.info.name}")
            print(f"Resolution: {camera.info.max_width}x{camera.info.max_height}")
            print(f"Pixel size: {camera.info.pixel_size_um}μm")
            print(f"Color: {camera.info.is_color}")
            print(f"Cooler: {camera.info.has_cooler}")

            # Show presets
            print("\nPlanetary presets:")
            for name, preset in ASICamera.PRESETS.items():
                print(f"  {name}: gain={preset.gain}, exp={preset.exposure_ms}ms")

            camera.close()
        else:
            print("No camera found or initialization failed")
            print("(This is expected if no ZWO camera is connected)")

    asyncio.run(test())
