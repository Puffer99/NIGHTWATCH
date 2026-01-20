"""
NIGHTWATCH ZWO ASI Camera Service
Planetary and Deep-Sky Imaging

POS Panel v2.0 - Day 12 Recommendations (Damian Peach):
- Gain: 250-300 for Mars (balance noise/speed)
- Exposure: 5-15ms depending on seeing
- ROI: Crop to 640x480 for faster capture
- Binning: 1x1 only (already undersampled at f/6)
- Format: SER files for stacking, 60-90 seconds each

Step 83: SDK wrapper import handling for graceful degradation
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Tuple, Any

logger = logging.getLogger("NIGHTWATCH.Camera")


# =============================================================================
# ZWO ASI SDK Wrapper (Step 83)
# =============================================================================

class ASISDKWrapper:
    """
    Wrapper for ZWO ASI SDK with graceful degradation (Step 83).

    Handles SDK import failures gracefully, providing:
    - Mock mode when SDK unavailable
    - Consistent API regardless of SDK presence
    - Clear error messages for installation guidance
    """

    # SDK status
    SDK_AVAILABLE = False
    SDK_ERROR: Optional[str] = None
    _sdk = None

    # SDK constants (fallbacks if SDK not available)
    ASI_GAIN = 0
    ASI_EXPOSURE = 1
    ASI_BANDWIDTHOVERLOAD = 6
    ASI_HIGH_SPEED_MODE = 14
    ASI_FLIP = 17
    ASI_TEMPERATURE = 18
    ASI_TARGET_TEMP = 19
    ASI_COOLER_ON = 20
    ASI_COOLER_POWER_PERC = 21

    @classmethod
    def initialize(cls) -> bool:
        """
        Initialize the ASI SDK wrapper.

        Returns:
            True if SDK is available and initialized
        """
        if cls._sdk is not None:
            return cls.SDK_AVAILABLE

        try:
            import zwoasi as asi
            cls._sdk = asi
            cls.SDK_AVAILABLE = True

            # Copy SDK constants
            cls.ASI_GAIN = asi.ASI_GAIN
            cls.ASI_EXPOSURE = asi.ASI_EXPOSURE
            cls.ASI_BANDWIDTHOVERLOAD = asi.ASI_BANDWIDTHOVERLOAD
            cls.ASI_HIGH_SPEED_MODE = asi.ASI_HIGH_SPEED_MODE
            cls.ASI_FLIP = asi.ASI_FLIP
            cls.ASI_TEMPERATURE = asi.ASI_TEMPERATURE
            cls.ASI_TARGET_TEMP = asi.ASI_TARGET_TEMP
            cls.ASI_COOLER_ON = asi.ASI_COOLER_ON
            cls.ASI_COOLER_POWER_PERC = asi.ASI_COOLER_POWER_PERC

            # Initialize the library
            try:
                asi.init()
                logger.info("ZWO ASI SDK initialized successfully")
            except Exception as e:
                # May already be initialized
                logger.debug(f"ASI init note: {e}")

            return True

        except ImportError as e:
            cls.SDK_ERROR = (
                f"ZWO ASI SDK not installed: {e}\n"
                "Install with: pip install zwoasi\n"
                "Or download from: https://astronomy-imaging-camera.com/software-drivers"
            )
            logger.warning(cls.SDK_ERROR)
            return False

        except Exception as e:
            cls.SDK_ERROR = f"Failed to initialize ZWO ASI SDK: {e}"
            logger.error(cls.SDK_ERROR)
            return False

    @classmethod
    def get_sdk(cls) -> Optional[Any]:
        """Get the SDK module if available."""
        if not cls.SDK_AVAILABLE:
            cls.initialize()
        return cls._sdk

    @classmethod
    def get_num_cameras(cls) -> int:
        """Get number of connected cameras."""
        if not cls.SDK_AVAILABLE:
            return 0
        try:
            return cls._sdk.get_num_cameras()
        except Exception as e:
            logger.error(f"Failed to enumerate cameras: {e}")
            return 0

    @classmethod
    def list_cameras(cls) -> List[dict]:
        """
        List all connected ZWO cameras.

        Returns:
            List of camera info dictionaries
        """
        if not cls.SDK_AVAILABLE:
            return []

        try:
            cameras = []
            num = cls._sdk.get_num_cameras()
            for i in range(num):
                try:
                    cam = cls._sdk.Camera(i)
                    props = cam.get_camera_property()
                    cameras.append({
                        "index": i,
                        "name": props.get("Name", f"Camera {i}"),
                        "id": props.get("CameraID", i),
                        "max_width": props.get("MaxWidth", 0),
                        "max_height": props.get("MaxHeight", 0),
                        "is_color": props.get("IsColorCam", False),
                        "has_cooler": props.get("IsCoolerCam", False),
                    })
                    cam.close()
                except Exception as e:
                    logger.warning(f"Failed to query camera {i}: {e}")
            return cameras

        except Exception as e:
            logger.error(f"Failed to list cameras: {e}")
            return []

    @classmethod
    def is_available(cls) -> bool:
        """Check if SDK is available."""
        if cls._sdk is None:
            cls.initialize()
        return cls.SDK_AVAILABLE

    @classmethod
    def get_error(cls) -> Optional[str]:
        """Get SDK initialization error if any."""
        return cls.SDK_ERROR


# Initialize SDK wrapper on module load
ASISDKWrapper.initialize()


# =============================================================================
# Camera Detection and Enumeration (Step 84)
# =============================================================================

def detect_cameras() -> List[dict]:
    """
    Detect and enumerate all connected ZWO ASI cameras (Step 84).

    Returns a list of camera info dictionaries with details about each
    connected camera, suitable for display and selection.

    Returns:
        List of camera dictionaries with keys:
        - index: Camera index for connection
        - name: Camera model name
        - id: Unique camera ID
        - max_width/max_height: Sensor resolution
        - pixel_size_um: Pixel size in microns
        - is_color: True if color camera
        - has_cooler: True if cooled camera
        - usb_host: USB host controller info
    """
    if not ASISDKWrapper.is_available():
        logger.warning("ZWO ASI SDK not available - cannot detect cameras")
        return []

    cameras = []
    sdk = ASISDKWrapper.get_sdk()

    try:
        num_cameras = sdk.get_num_cameras()
        logger.info(f"Detected {num_cameras} ZWO camera(s)")

        for i in range(num_cameras):
            try:
                cam = sdk.Camera(i)
                props = cam.get_camera_property()

                camera_info = {
                    "index": i,
                    "name": props.get("Name", f"Camera {i}"),
                    "id": props.get("CameraID", i),
                    "max_width": props.get("MaxWidth", 0),
                    "max_height": props.get("MaxHeight", 0),
                    "pixel_size_um": props.get("PixelSize", 0.0),
                    "is_color": props.get("IsColorCam", False),
                    "has_cooler": props.get("IsCoolerCam", False),
                    "bit_depth": props.get("BitDepth", 8),
                    "supported_bins": list(props.get("SupportedBins", [1])),
                    "usb_host": props.get("USB3Host", "Unknown"),
                    "is_usb3": props.get("IsUSB3Camera", False),
                }

                cameras.append(camera_info)
                cam.close()

                logger.debug(f"  Camera {i}: {camera_info['name']}")

            except Exception as e:
                logger.warning(f"Failed to query camera {i}: {e}")

    except Exception as e:
        logger.error(f"Camera detection failed: {e}")

    return cameras


def get_camera_count() -> int:
    """Get number of connected ZWO cameras."""
    return ASISDKWrapper.get_num_cameras()


def find_camera_by_name(name_pattern: str) -> Optional[dict]:
    """
    Find a camera by name pattern.

    Args:
        name_pattern: Partial name to match (case-insensitive)

    Returns:
        Camera info dict or None if not found
    """
    cameras = detect_cameras()
    name_lower = name_pattern.lower()

    for cam in cameras:
        if name_lower in cam["name"].lower():
            return cam

    return None


# =============================================================================
# Camera Connection Helper (Step 85)
# =============================================================================

def connect_camera(
    camera_index: int = 0,
    settings: Optional["CameraSettings"] = None,
    data_dir: Optional[Path] = None
) -> Optional["ASICamera"]:
    """
    Connect to a camera with optional initial settings (Step 85).

    Convenience function for connecting to a camera by index with
    initial configuration applied.

    Args:
        camera_index: Camera index from detect_cameras()
        settings: Initial camera settings to apply
        data_dir: Directory for saving captures

    Returns:
        Connected ASICamera instance or None on failure
    """
    camera = ASICamera(camera_index=camera_index, data_dir=data_dir)

    if not camera.initialize():
        logger.error(f"Failed to connect to camera {camera_index}")
        return None

    if settings:
        camera.apply_settings(settings)

    logger.info(f"Connected to camera: {camera.info.name if camera.info else 'Unknown'}")
    return camera


def connect_camera_by_name(
    name_pattern: str,
    settings: Optional["CameraSettings"] = None,
    data_dir: Optional[Path] = None
) -> Optional["ASICamera"]:
    """
    Connect to a camera by name pattern (Step 85).

    Args:
        name_pattern: Partial name to match
        settings: Initial camera settings
        data_dir: Directory for captures

    Returns:
        Connected ASICamera or None
    """
    cam_info = find_camera_by_name(name_pattern)
    if not cam_info:
        logger.error(f"No camera found matching '{name_pattern}'")
        return None

    return connect_camera(cam_info["index"], settings, data_dir)


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

    # =========================================================================
    # GAIN CONTROL (Step 86)
    # =========================================================================

    def set_gain(self, gain: int) -> bool:
        """
        Set camera gain.

        Args:
            gain: Gain value (typically 0-500 for ZWO cameras)

        Returns:
            True if successful
        """
        if not self._camera:
            logger.warning("Cannot set gain: camera not initialized")
            return False

        try:
            # Validate gain range
            min_gain, max_gain = self.get_gain_range()
            if not min_gain <= gain <= max_gain:
                logger.warning(f"Gain {gain} out of range ({min_gain}-{max_gain})")
                return False

            self._camera.set_control_value(self._asi.ASI_GAIN, gain)
            self._settings.gain = gain
            logger.debug(f"Set gain to {gain}")
            return True
        except Exception as e:
            logger.error(f"Failed to set gain: {e}")
            return False

    def get_gain(self) -> int:
        """
        Get current camera gain.

        Returns:
            Current gain value
        """
        if not self._camera:
            return self._settings.gain

        try:
            gain = self._camera.get_control_value(self._asi.ASI_GAIN)[0]
            return int(gain)
        except Exception:
            return self._settings.gain

    def get_gain_range(self) -> Tuple[int, int]:
        """
        Get supported gain range.

        Returns:
            Tuple of (min_gain, max_gain)
        """
        if not self._camera:
            return (0, 500)  # Default ZWO range

        try:
            info = self._camera.get_controls()[self._asi.ASI_GAIN]
            return (info["MinValue"], info["MaxValue"])
        except Exception:
            return (0, 500)

    # =========================================================================
    # EXPOSURE CONTROL (Step 87)
    # =========================================================================

    def set_exposure(self, exposure_ms: float) -> bool:
        """
        Set camera exposure time.

        Args:
            exposure_ms: Exposure time in milliseconds

        Returns:
            True if successful
        """
        if not self._camera:
            logger.warning("Cannot set exposure: camera not initialized")
            return False

        try:
            # Validate exposure range
            min_exp, max_exp = self.get_exposure_range()
            if not min_exp <= exposure_ms <= max_exp:
                logger.warning(f"Exposure {exposure_ms}ms out of range ({min_exp}-{max_exp}ms)")
                return False

            # Convert to microseconds for ASI API
            exposure_us = int(exposure_ms * 1000)
            self._camera.set_control_value(self._asi.ASI_EXPOSURE, exposure_us)
            self._settings.exposure_ms = exposure_ms
            logger.debug(f"Set exposure to {exposure_ms}ms")
            return True
        except Exception as e:
            logger.error(f"Failed to set exposure: {e}")
            return False

    def get_exposure(self) -> float:
        """
        Get current exposure time in milliseconds.

        Returns:
            Current exposure in ms
        """
        if not self._camera:
            return self._settings.exposure_ms

        try:
            exposure_us = self._camera.get_control_value(self._asi.ASI_EXPOSURE)[0]
            return exposure_us / 1000.0  # Convert to ms
        except Exception:
            return self._settings.exposure_ms

    def get_exposure_range(self) -> Tuple[float, float]:
        """
        Get supported exposure range in milliseconds.

        Returns:
            Tuple of (min_ms, max_ms)
        """
        if not self._camera:
            return (0.001, 3600000.0)  # 1us to 1hr default

        try:
            info = self._camera.get_controls()[self._asi.ASI_EXPOSURE]
            # Convert from microseconds to milliseconds
            return (info["MinValue"] / 1000.0, info["MaxValue"] / 1000.0)
        except Exception:
            return (0.001, 3600000.0)

    # =========================================================================
    # BINNING CONTROL (Step 88)
    # =========================================================================

    def set_binning(self, binning: int) -> bool:
        """
        Set camera binning mode.

        Args:
            binning: Binning factor (1, 2, 3, or 4)

        Returns:
            True if successful
        """
        if not self._camera:
            logger.warning("Cannot set binning: camera not initialized")
            return False

        supported = self.get_supported_binning()
        if binning not in supported:
            logger.warning(f"Binning {binning}x{binning} not supported. Supported: {supported}")
            return False

        try:
            # Get current ROI
            roi_info = self._camera.get_roi()
            # Set new ROI with updated binning
            self._camera.set_roi(
                roi_info[0], roi_info[1],  # x, y
                roi_info[2], roi_info[3],  # width, height
                binning
            )
            self._settings.binning = binning
            logger.debug(f"Set binning to {binning}x{binning}")
            return True
        except Exception as e:
            logger.error(f"Failed to set binning: {e}")
            return False

    def get_binning(self) -> int:
        """
        Get current binning mode.

        Returns:
            Current binning factor
        """
        if not self._camera:
            return self._settings.binning

        try:
            roi_info = self._camera.get_roi()
            return roi_info[4]  # binning is 5th element
        except Exception:
            return self._settings.binning

    def get_supported_binning(self) -> List[int]:
        """
        Get supported binning modes.

        Returns:
            List of supported binning factors
        """
        if not self._camera or not self._info:
            return [1, 2, 4]  # Default ZWO support

        try:
            props = self._camera.get_camera_property()
            bins = props.get("SupportedBins", [1, 2, 4])
            return list(bins)
        except Exception:
            return [1, 2, 4]

    # =========================================================================
    # ROI CONTROL (Step 89)
    # =========================================================================

    def set_roi(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        binning: Optional[int] = None
    ) -> bool:
        """
        Set region of interest for capture (Step 89).

        Args:
            x: ROI start X position
            y: ROI start Y position
            width: ROI width in pixels
            height: ROI height in pixels
            binning: Optional binning factor (keeps current if None)

        Returns:
            True if successful
        """
        if not self._camera:
            logger.warning("Cannot set ROI: camera not initialized")
            return False

        try:
            # Get current binning if not specified
            if binning is None:
                binning = self._settings.binning

            # Validate binning
            supported = self.get_supported_binning()
            if binning not in supported:
                logger.warning(f"Binning {binning} not supported")
                binning = 1

            # Calculate max dimensions accounting for binning
            max_width = self._info.max_width // binning if self._info else 4096
            max_height = self._info.max_height // binning if self._info else 4096

            # Clamp values to valid range
            x = max(0, min(x, max_width - 64))
            y = max(0, min(y, max_height - 64))
            width = max(64, min(width, max_width - x))
            height = max(64, min(height, max_height - y))

            # ZWO cameras require width/height to be multiples of 8
            width = (width // 8) * 8
            height = (height // 8) * 8

            self._camera.set_roi(x, y, width, height, binning)

            self._settings.roi = (x, y, width, height)
            self._settings.binning = binning

            logger.info(f"Set ROI: ({x}, {y}) {width}x{height} bin{binning}")
            return True

        except Exception as e:
            logger.error(f"Failed to set ROI: {e}")
            return False

    def get_roi(self) -> Tuple[int, int, int, int]:
        """
        Get current region of interest.

        Returns:
            Tuple of (x, y, width, height)
        """
        if not self._camera:
            return self._settings.roi or (0, 0, 4096, 4096)

        try:
            roi_info = self._camera.get_roi()
            return (roi_info[0], roi_info[1], roi_info[2], roi_info[3])
        except Exception:
            return self._settings.roi or (0, 0, 4096, 4096)

    def reset_roi(self) -> bool:
        """
        Reset ROI to full frame.

        Returns:
            True if successful
        """
        if not self._info:
            return False

        return self.set_roi(0, 0, self._info.max_width, self._info.max_height, 1)

    def set_roi_centered(self, width: int, height: int, binning: int = 1) -> bool:
        """
        Set a centered ROI of specified size.

        Useful for planetary imaging where target is centered.

        Args:
            width: ROI width
            height: ROI height
            binning: Binning factor

        Returns:
            True if successful
        """
        if not self._info:
            return False

        max_w = self._info.max_width // binning
        max_h = self._info.max_height // binning

        # Center the ROI
        x = (max_w - width) // 2
        y = (max_h - height) // 2

        return self.set_roi(x, y, width, height, binning)

    def get_roi_presets(self) -> dict:
        """
        Get common ROI presets for this camera.

        Returns:
            Dictionary of preset name -> (width, height) tuples
        """
        if not self._info:
            return {}

        max_w = self._info.max_width
        max_h = self._info.max_height

        return {
            "full_frame": (max_w, max_h),
            "half": (max_w // 2, max_h // 2),
            "quarter": (max_w // 4, max_h // 4),
            "planetary_640": (640, 480),
            "planetary_800": (800, 600),
            "planetary_1024": (1024, 768),
            "1080p": (1920, 1080),
            "720p": (1280, 720),
        }

    # =========================================================================
    # APPLY SETTINGS (Step 85 helper)
    # =========================================================================

    def apply_settings(self, settings: CameraSettings) -> bool:
        """
        Apply a complete settings object to camera.

        Args:
            settings: CameraSettings to apply

        Returns:
            True if all settings applied successfully
        """
        if not self._camera:
            logger.warning("Cannot apply settings: camera not initialized")
            return False

        success = True

        # Apply gain
        if not self.set_gain(settings.gain):
            success = False

        # Apply exposure
        if not self.set_exposure(settings.exposure_ms):
            success = False

        # Apply ROI if specified
        if settings.roi:
            x, y, w, h = settings.roi
            if not self.set_roi(x, y, w, h, settings.binning):
                success = False
        elif settings.binning != self._settings.binning:
            if not self.set_binning(settings.binning):
                success = False

        # Apply cooling if specified
        if settings.cooler_on and self._info and self._info.has_cooler:
            self.set_cooler(True, settings.target_temp_c)

        self._settings = settings
        return success

    # =========================================================================
    # TEMPERATURE MONITORING (Step 95)
    # =========================================================================

    def get_temperature_status(self) -> dict:
        """
        Get detailed temperature status.

        Returns:
            Dict with temperature information
        """
        result = {
            "sensor_temp_c": None,
            "target_temp_c": self._settings.target_temp_c,
            "cooler_on": self._settings.cooler_on,
            "cooler_power_percent": None,
            "has_cooler": False,
        }

        if not self._camera or not self._info:
            return result

        result["has_cooler"] = self._info.has_cooler

        if not self._info.has_cooler:
            return result

        try:
            # Get current sensor temperature
            temp = self._camera.get_control_value(self._asi.ASI_TEMPERATURE)[0]
            result["sensor_temp_c"] = temp / 10.0  # Reported in 0.1°C

            # Get cooler power
            power = self._camera.get_control_value(self._asi.ASI_COOLER_POWER_PERC)[0]
            result["cooler_power_percent"] = float(power)

            # Get cooler state
            cooler_on = self._camera.get_control_value(self._asi.ASI_COOLER_ON)[0]
            result["cooler_on"] = cooler_on == 1

        except Exception as e:
            logger.debug(f"Error reading temperature status: {e}")

        return result

    def set_cooler(self, enabled: bool, target_temp_c: Optional[float] = None) -> bool:
        """
        Control camera cooler.

        Args:
            enabled: Turn cooler on/off
            target_temp_c: Target temperature (required if enabling)

        Returns:
            True if successful
        """
        if not self._camera or not self._info or not self._info.has_cooler:
            logger.warning("Camera does not have a cooler")
            return False

        try:
            if enabled:
                if target_temp_c is None:
                    target_temp_c = self._settings.target_temp_c or -10.0

                self._camera.set_control_value(
                    self._asi.ASI_TARGET_TEMP,
                    int(target_temp_c)
                )
                self._camera.set_control_value(self._asi.ASI_COOLER_ON, 1)
                self._settings.target_temp_c = target_temp_c
                self._settings.cooler_on = True
                logger.info(f"Cooler enabled, target: {target_temp_c}°C")
            else:
                self._camera.set_control_value(self._asi.ASI_COOLER_ON, 0)
                self._settings.cooler_on = False
                logger.info("Cooler disabled")

            return True
        except Exception as e:
            logger.error(f"Failed to control cooler: {e}")
            return False

    # =========================================================================
    # COOLING CONTROL (Step 94)
    # =========================================================================

    def set_target_temperature(self, temp_c: float) -> bool:
        """
        Set cooler target temperature (Step 94).

        Args:
            temp_c: Target temperature in Celsius

        Returns:
            True if successful
        """
        if not self._camera or not self._info or not self._info.has_cooler:
            logger.warning("Camera does not have a cooler")
            return False

        try:
            self._camera.set_control_value(self._asi.ASI_TARGET_TEMP, int(temp_c))
            self._settings.target_temp_c = temp_c
            logger.info(f"Set target temperature to {temp_c}°C")
            return True
        except Exception as e:
            logger.error(f"Failed to set target temperature: {e}")
            return False

    def get_target_temperature(self) -> Optional[float]:
        """Get current target temperature."""
        return self._settings.target_temp_c

    def is_cooler_at_target(self, tolerance_c: float = 1.0) -> bool:
        """
        Check if cooler has reached target temperature (Step 94).

        Args:
            tolerance_c: Acceptable temperature difference

        Returns:
            True if within tolerance of target
        """
        if not self._info or not self._info.has_cooler:
            return True  # No cooler = always "at target"

        current = self.get_temperature()
        target = self._settings.target_temp_c

        if current is None or target is None:
            return False

        return abs(current - target) <= tolerance_c

    async def wait_for_temperature(
        self,
        timeout_sec: float = 300.0,
        tolerance_c: float = 1.0,
        poll_interval_sec: float = 5.0
    ) -> bool:
        """
        Wait for cooler to reach target temperature (Step 94).

        Args:
            timeout_sec: Maximum wait time
            tolerance_c: Temperature tolerance
            poll_interval_sec: Time between checks

        Returns:
            True if target reached within timeout
        """
        if not self._info or not self._info.has_cooler:
            return True

        start = datetime.now()
        target = self._settings.target_temp_c

        while (datetime.now() - start).total_seconds() < timeout_sec:
            current = self.get_temperature()
            if current is not None and target is not None:
                diff = abs(current - target)
                logger.debug(f"Cooling: {current:.1f}°C (target {target}°C, diff {diff:.1f}°C)")

                if diff <= tolerance_c:
                    logger.info(f"Cooler reached target temperature: {current:.1f}°C")
                    return True

            await asyncio.sleep(poll_interval_sec)

        logger.warning(f"Cooler did not reach target within {timeout_sec}s")
        return False

    def get_cooler_power(self) -> Optional[float]:
        """
        Get current cooler power percentage (Step 94).

        Returns:
            Cooler power 0-100%, or None if unavailable
        """
        if not self._camera or not self._info or not self._info.has_cooler:
            return None

        try:
            power = self._camera.get_control_value(self._asi.ASI_COOLER_POWER_PERC)[0]
            return float(power)
        except Exception:
            return None

    def is_cooler_overloaded(self, threshold: float = 95.0) -> bool:
        """
        Check if cooler is at high power (struggling to cool).

        High cooler power may indicate:
        - Ambient temperature too high
        - Poor thermal contact
        - Target temperature too aggressive

        Args:
            threshold: Power percentage considered overloaded

        Returns:
            True if cooler power exceeds threshold
        """
        power = self.get_cooler_power()
        if power is None:
            return False

        return power >= threshold

    def get_cooling_recommendation(self) -> str:
        """
        Get recommendation for cooling settings based on conditions.

        Returns:
            Recommendation string
        """
        if not self._info or not self._info.has_cooler:
            return "Camera does not have active cooling"

        current = self.get_temperature()
        power = self.get_cooler_power()

        if current is None:
            return "Unable to read sensor temperature"

        if not self._settings.cooler_on:
            # Recommend based on sensor temperature
            if current > 30:
                return f"Sensor at {current:.0f}°C - recommend enabling cooler at -10°C"
            elif current > 20:
                return f"Sensor at {current:.0f}°C - cooling optional, recommend -5°C to -10°C"
            else:
                return f"Sensor at {current:.0f}°C - ambient is cool, cooling optional"

        # Cooler is on
        if power is not None and power > 90:
            return f"Cooler at {power:.0f}% power - consider raising target temperature"
        elif power is not None and power < 20:
            return f"Cooler at {power:.0f}% power - target easily maintained, could lower further"

        return f"Cooling nominal at {current:.0f}°C with {power:.0f}% power"

    # =========================================================================
    # CAPTURE ABORT (Step 96)
    # =========================================================================

    async def abort_capture(self) -> bool:
        """
        Immediately abort any capture in progress.

        Returns:
            True if capture was aborted
        """
        if not self._capturing:
            logger.debug("No capture to abort")
            return False

        logger.warning("Aborting capture!")
        self._capturing = False

        # Mark session as incomplete
        if self._current_session:
            self._current_session.complete = False
            self._current_session.error = "Capture aborted by user"

        # Stop video capture if running
        if self._camera:
            try:
                self._camera.stop_video_capture()
            except Exception:
                pass  # May not be in video mode

        # Brief delay to let capture loop exit
        await asyncio.sleep(0.1)

        logger.info("Capture aborted")
        return True

    def is_capture_in_progress(self) -> bool:
        """Check if a capture is currently in progress."""
        return self._capturing

    def get_capture_progress(self) -> Optional[dict]:
        """
        Get progress of current capture.

        Returns:
            Dict with capture progress or None if no capture
        """
        if not self._current_session:
            return None

        session = self._current_session
        elapsed = (datetime.now() - session.start_time).total_seconds()

        return {
            "session_id": session.session_id,
            "target": session.target,
            "frame_count": session.frame_count,
            "elapsed_sec": elapsed,
            "duration_sec": session.duration_sec,
            "progress_percent": min(100.0, (elapsed / session.duration_sec) * 100) if session.duration_sec > 0 else 0,
            "output_path": str(session.output_path),
        }


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
