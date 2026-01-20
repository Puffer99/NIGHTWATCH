"""
NIGHTWATCH Camera Simulator (Step 528)

Simulates a ZWO ASI camera for testing without hardware.
Provides realistic behavior for development and integration testing.

Features:
- Simulated camera detection and enumeration
- Configurable camera properties (resolution, color, cooler)
- Simulated image capture with noise patterns
- Temperature and cooler simulation
- Capture progress callbacks
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("NIGHTWATCH.CameraSimulator")


class SimulatedCameraModel(Enum):
    """Simulated camera models."""
    ASI294MC_PRO = "ZWO ASI294MC Pro"
    ASI533MC_PRO = "ZWO ASI533MC Pro"
    ASI183MM_PRO = "ZWO ASI183MM Pro"
    ASI120MM_S = "ZWO ASI120MM-S"
    ASI462MC = "ZWO ASI462MC"


@dataclass
class SimulatedCameraProps:
    """Properties for a simulated camera model."""
    name: str
    max_width: int
    max_height: int
    pixel_size_um: float
    is_color: bool
    has_cooler: bool
    bit_depth: int
    supported_bins: List[int]
    max_gain: int
    min_exposure_us: int
    max_exposure_us: int


# Camera model specifications
CAMERA_SPECS: Dict[SimulatedCameraModel, SimulatedCameraProps] = {
    SimulatedCameraModel.ASI294MC_PRO: SimulatedCameraProps(
        name="ZWO ASI294MC Pro",
        max_width=4144,
        max_height=2822,
        pixel_size_um=4.63,
        is_color=True,
        has_cooler=True,
        bit_depth=14,
        supported_bins=[1, 2, 4],
        max_gain=570,
        min_exposure_us=32,
        max_exposure_us=2000000000,
    ),
    SimulatedCameraModel.ASI533MC_PRO: SimulatedCameraProps(
        name="ZWO ASI533MC Pro",
        max_width=3008,
        max_height=3008,
        pixel_size_um=3.76,
        is_color=True,
        has_cooler=True,
        bit_depth=14,
        supported_bins=[1, 2, 4],
        max_gain=500,
        min_exposure_us=32,
        max_exposure_us=2000000000,
    ),
    SimulatedCameraModel.ASI183MM_PRO: SimulatedCameraProps(
        name="ZWO ASI183MM Pro",
        max_width=5496,
        max_height=3672,
        pixel_size_um=2.4,
        is_color=False,
        has_cooler=True,
        bit_depth=12,
        supported_bins=[1, 2, 4],
        max_gain=300,
        min_exposure_us=32,
        max_exposure_us=3600000000,
    ),
    SimulatedCameraModel.ASI120MM_S: SimulatedCameraProps(
        name="ZWO ASI120MM-S",
        max_width=1280,
        max_height=960,
        pixel_size_um=3.75,
        is_color=False,
        has_cooler=False,
        bit_depth=12,
        supported_bins=[1, 2],
        max_gain=100,
        min_exposure_us=32,
        max_exposure_us=1000000000,
    ),
    SimulatedCameraModel.ASI462MC: SimulatedCameraProps(
        name="ZWO ASI462MC",
        max_width=1936,
        max_height=1096,
        pixel_size_um=2.9,
        is_color=True,
        has_cooler=False,
        bit_depth=10,
        supported_bins=[1, 2],
        max_gain=500,
        min_exposure_us=32,
        max_exposure_us=2000000000,
    ),
}


class CameraSimulator:
    """
    Simulates ZWO ASI camera for testing (Step 528).

    Provides a realistic camera interface for development and testing
    without requiring actual hardware.

    Usage:
        sim = CameraSimulator(model=SimulatedCameraModel.ASI294MC_PRO)
        sim.initialize()

        # Set exposure
        sim.set_exposure_us(10000)  # 10ms
        sim.set_gain(250)

        # Capture
        image_data = sim.capture_frame()
    """

    def __init__(
        self,
        model: SimulatedCameraModel = SimulatedCameraModel.ASI294MC_PRO,
        camera_index: int = 0,
        data_dir: Optional[Path] = None,
    ):
        """
        Initialize camera simulator.

        Args:
            model: Camera model to simulate
            camera_index: Simulated camera index
            data_dir: Directory for saving captures
        """
        self.model = model
        self.camera_index = camera_index
        self.data_dir = data_dir or Path("/tmp/camera_sim")
        self.props = CAMERA_SPECS[model]

        # State
        self._initialized = False
        self._capturing = False

        # Settings
        self._gain = 100
        self._exposure_us = 10000  # 10ms default
        self._roi = (0, 0, self.props.max_width, self.props.max_height)
        self._binning = 1
        self._flip = 0
        self._usb_bandwidth = 80
        self._high_speed_mode = True

        # Cooler simulation
        self._cooler_on = False
        self._target_temp_c = -10.0
        self._sensor_temp_c = 25.0  # Starts at ambient
        self._cooler_power = 0.0

        # Capture state
        self._frame_count = 0
        self._last_capture_time: Optional[datetime] = None
        self._callbacks: List[Callable] = []

        logger.info(f"CameraSimulator created: {self.props.name}")

    def initialize(self) -> bool:
        """Initialize the simulated camera."""
        logger.info(f"Initializing camera simulator: {self.props.name}")
        self._initialized = True
        self._sensor_temp_c = 25.0 + random.uniform(-2, 2)  # Ambient with variation
        return True

    def close(self):
        """Close the simulated camera."""
        self._initialized = False
        self._capturing = False
        logger.info("Camera simulator closed")

    @property
    def initialized(self) -> bool:
        """Check if simulator is initialized."""
        return self._initialized

    @property
    def capturing(self) -> bool:
        """Check if capture is in progress."""
        return self._capturing

    # =========================================================================
    # Camera Property Queries
    # =========================================================================

    def get_camera_property(self) -> dict:
        """Get camera properties (mimics ASI SDK)."""
        return {
            "Name": self.props.name,
            "CameraID": self.camera_index,
            "MaxWidth": self.props.max_width,
            "MaxHeight": self.props.max_height,
            "PixelSize": self.props.pixel_size_um,
            "IsColorCam": self.props.is_color,
            "IsCoolerCam": self.props.has_cooler,
            "BitDepth": self.props.bit_depth,
            "SupportedBins": self.props.supported_bins,
            "USB3Host": "Simulated",
        }

    def get_controls(self) -> dict:
        """Get camera control ranges (mimics ASI SDK)."""
        return {
            0: {  # ASI_GAIN
                "MinValue": 0,
                "MaxValue": self.props.max_gain,
                "DefaultValue": 100,
            },
            1: {  # ASI_EXPOSURE
                "MinValue": self.props.min_exposure_us,
                "MaxValue": self.props.max_exposure_us,
                "DefaultValue": 10000,
            },
        }

    def get_roi(self) -> Tuple[int, int, int, int, int]:
        """Get current ROI and binning."""
        return (*self._roi, self._binning)

    # =========================================================================
    # Camera Settings
    # =========================================================================

    def set_control_value(self, control_type: int, value: int):
        """Set a camera control value (mimics ASI SDK)."""
        if control_type == 0:  # ASI_GAIN
            self._gain = max(0, min(self.props.max_gain, value))
        elif control_type == 1:  # ASI_EXPOSURE
            self._exposure_us = max(
                self.props.min_exposure_us,
                min(self.props.max_exposure_us, value)
            )
        elif control_type == 6:  # ASI_BANDWIDTHOVERLOAD
            self._usb_bandwidth = max(40, min(100, value))
        elif control_type == 14:  # ASI_HIGH_SPEED_MODE
            self._high_speed_mode = value == 1
        elif control_type == 17:  # ASI_FLIP
            self._flip = value
        elif control_type == 18:  # ASI_TEMPERATURE (read-only, but store for testing)
            pass
        elif control_type == 19:  # ASI_TARGET_TEMP
            self._target_temp_c = value
        elif control_type == 20:  # ASI_COOLER_ON
            self._cooler_on = value == 1
            if self._cooler_on:
                logger.info(f"Cooler enabled, target: {self._target_temp_c}°C")
            else:
                logger.info("Cooler disabled")

    def get_control_value(self, control_type: int) -> Tuple[int, bool]:
        """Get a camera control value (mimics ASI SDK)."""
        if control_type == 0:  # ASI_GAIN
            return (self._gain, False)
        elif control_type == 1:  # ASI_EXPOSURE
            return (self._exposure_us, False)
        elif control_type == 18:  # ASI_TEMPERATURE
            # Returns temperature in 0.1°C units
            return (int(self._sensor_temp_c * 10), False)
        elif control_type == 19:  # ASI_TARGET_TEMP
            return (int(self._target_temp_c), False)
        elif control_type == 20:  # ASI_COOLER_ON
            return (1 if self._cooler_on else 0, False)
        elif control_type == 21:  # ASI_COOLER_POWER_PERC
            return (int(self._cooler_power), False)
        return (0, False)

    def set_roi(self, x: int, y: int, width: int, height: int, binning: int = 1):
        """Set region of interest."""
        # Validate binning
        if binning not in self.props.supported_bins:
            binning = 1

        # Validate ROI
        max_w = self.props.max_width // binning
        max_h = self.props.max_height // binning

        width = min(width, max_w - x)
        height = min(height, max_h - y)

        self._roi = (x, y, width, height)
        self._binning = binning
        logger.debug(f"ROI set: {self._roi}, binning: {self._binning}")

    # =========================================================================
    # Capture Simulation
    # =========================================================================

    def capture_frame(self) -> bytes:
        """
        Capture a simulated frame.

        Returns:
            Simulated image data as bytes
        """
        if not self._initialized:
            raise RuntimeError("Camera not initialized")

        x, y, width, height = self._roi

        # Calculate image size
        bytes_per_pixel = 2 if self.props.bit_depth > 8 else 1
        if self.props.is_color and bytes_per_pixel == 1:
            # Bayer pattern (same size as mono for raw)
            pass

        image_size = width * height * bytes_per_pixel

        # Simulate exposure delay
        exposure_sec = self._exposure_us / 1_000_000
        if exposure_sec > 0.1:
            time.sleep(min(exposure_sec, 0.1))  # Cap at 100ms for simulation

        # Generate simulated noise image
        # Higher gain = more noise
        noise_level = int(20 + self._gain * 0.1)
        base_level = int(50 + self._gain * 0.5)

        # Create simple noise pattern
        image_data = bytearray(image_size)
        for i in range(0, image_size, bytes_per_pixel):
            value = base_level + random.randint(-noise_level, noise_level)
            value = max(0, min(255 if bytes_per_pixel == 1 else 65535, value))

            if bytes_per_pixel == 1:
                image_data[i] = value
            else:
                image_data[i] = value & 0xFF
                image_data[i + 1] = (value >> 8) & 0xFF

        self._frame_count += 1
        self._last_capture_time = datetime.now()

        logger.debug(f"Captured frame {self._frame_count}: {width}x{height}")

        return bytes(image_data)

    async def capture_video(
        self,
        duration_sec: float,
        callback: Optional[Callable[[int, bytes], None]] = None
    ) -> int:
        """
        Simulate video capture.

        Args:
            duration_sec: Duration of capture
            callback: Called for each frame with (frame_num, data)

        Returns:
            Total frames captured
        """
        if not self._initialized:
            raise RuntimeError("Camera not initialized")

        self._capturing = True
        frame_count = 0
        start_time = time.time()

        # Calculate expected FPS based on exposure
        frame_time_sec = self._exposure_us / 1_000_000
        min_frame_time = 0.001  # 1000 FPS max

        try:
            while self._capturing and (time.time() - start_time) < duration_sec:
                frame_data = self.capture_frame()
                frame_count += 1

                if callback:
                    callback(frame_count, frame_data)

                # Simulate frame interval
                await asyncio.sleep(max(frame_time_sec, min_frame_time))

        finally:
            self._capturing = False

        logger.info(f"Video capture complete: {frame_count} frames in {duration_sec}s")
        return frame_count

    def stop_video_capture(self):
        """Stop video capture."""
        self._capturing = False

    # =========================================================================
    # Video/Streaming Capture Mode (Step 91)
    # =========================================================================

    async def start_video_streaming(
        self,
        roi: Optional[Tuple[int, int, int, int]] = None,
        target_fps: float = 30.0,
        frame_callback: Optional[Callable[[int, bytes, dict], None]] = None
    ) -> bool:
        """
        Start continuous video streaming mode (Step 91).

        Optimized for planetary imaging with:
        - ROI (Region of Interest) support for faster frame rates
        - Target FPS control
        - Frame metadata (timestamp, frame number)

        Args:
            roi: Optional (x, y, width, height) for region of interest
            target_fps: Target frames per second (limited by exposure)
            frame_callback: Called for each frame with (frame_num, data, metadata)

        Returns:
            True if streaming started successfully
        """
        if not self._initialized:
            raise RuntimeError("Camera not initialized")

        if self._capturing:
            logger.warning("Already capturing, stop first")
            return False

        self._capturing = True
        self._streaming = True
        self._stream_roi = roi
        self._stream_target_fps = target_fps
        self._stream_callback = frame_callback
        self._stream_frame_count = 0
        self._stream_start_time = time.time()
        self._stream_dropped_frames = 0

        # Calculate effective ROI
        if roi:
            x, y, w, h = roi
            self._stream_width = min(w, self.props.max_width - x)
            self._stream_height = min(h, self.props.max_height - y)
        else:
            self._stream_width = self.props.max_width // self._binning
            self._stream_height = self.props.max_height // self._binning

        logger.info(f"Video streaming started: {self._stream_width}x{self._stream_height} "
                   f"@ target {target_fps} FPS")

        # Start streaming task
        self._stream_task = asyncio.create_task(self._streaming_loop())

        return True

    async def _streaming_loop(self):
        """Internal streaming loop for video capture (Step 91)."""
        target_frame_time = 1.0 / self._stream_target_fps
        exposure_time = self._exposure_us / 1_000_000

        # Effective frame time is max of exposure and target interval
        effective_frame_time = max(target_frame_time, exposure_time)
        effective_fps = 1.0 / effective_frame_time

        if effective_fps < self._stream_target_fps:
            logger.info(f"FPS limited by exposure to {effective_fps:.1f}")

        try:
            while self._streaming and self._capturing:
                frame_start = time.time()

                # Generate frame (use ROI if set)
                frame_data = self._generate_stream_frame()
                self._stream_frame_count += 1

                # Build metadata
                metadata = {
                    "frame_number": self._stream_frame_count,
                    "timestamp": datetime.now().isoformat(),
                    "timestamp_unix": time.time(),
                    "exposure_us": self._exposure_us,
                    "gain": self._gain,
                    "width": self._stream_width,
                    "height": self._stream_height,
                    "effective_fps": effective_fps,
                }

                # Call callback if set
                if self._stream_callback:
                    try:
                        self._stream_callback(
                            self._stream_frame_count,
                            frame_data,
                            metadata
                        )
                    except Exception as e:
                        logger.error(f"Stream callback error: {e}")

                # Calculate sleep time to maintain frame rate
                elapsed = time.time() - frame_start
                sleep_time = effective_frame_time - elapsed

                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    # Dropped frame (processing took too long)
                    self._stream_dropped_frames += 1

        except asyncio.CancelledError:
            logger.debug("Streaming loop cancelled")
        except Exception as e:
            logger.error(f"Streaming error: {e}")
        finally:
            self._streaming = False
            logger.info(f"Streaming stopped: {self._stream_frame_count} frames, "
                       f"{self._stream_dropped_frames} dropped")

    def _generate_stream_frame(self) -> bytes:
        """Generate a single streaming frame with ROI support (Step 91)."""
        width = self._stream_width
        height = self._stream_height

        # Generate simplified frame for speed (no complex star simulation)
        # In real implementation, this would read from camera buffer

        if self.props.is_color:
            # RGB24 format for color
            channels = 3
            image_data = bytearray(width * height * channels)

            # Simple gradient + noise for visual feedback
            for y in range(height):
                for x in range(width):
                    idx = (y * width + x) * channels
                    # Add some variation
                    noise = random.randint(-10, 10)
                    r = min(255, max(0, 30 + noise))
                    g = min(255, max(0, 30 + noise))
                    b = min(255, max(0, 40 + noise))
                    image_data[idx] = r
                    image_data[idx + 1] = g
                    image_data[idx + 2] = b
        else:
            # Mono 8-bit
            image_data = bytearray(width * height)
            for i in range(len(image_data)):
                image_data[i] = random.randint(20, 50)

        return bytes(image_data)

    async def stop_video_streaming(self) -> dict:
        """
        Stop video streaming and return capture statistics (Step 91).

        Returns:
            Dict with capture statistics
        """
        self._streaming = False
        self._capturing = False

        # Wait for task to complete
        if hasattr(self, '_stream_task') and self._stream_task:
            try:
                self._stream_task.cancel()
                await asyncio.sleep(0.1)
            except Exception:
                pass

        duration = time.time() - self._stream_start_time if hasattr(self, '_stream_start_time') else 0
        actual_fps = self._stream_frame_count / duration if duration > 0 else 0

        stats = {
            "total_frames": self._stream_frame_count,
            "dropped_frames": self._stream_dropped_frames,
            "duration_sec": duration,
            "actual_fps": actual_fps,
            "target_fps": self._stream_target_fps if hasattr(self, '_stream_target_fps') else 0,
            "width": self._stream_width if hasattr(self, '_stream_width') else 0,
            "height": self._stream_height if hasattr(self, '_stream_height') else 0,
        }

        logger.info(f"Streaming stats: {stats['total_frames']} frames @ {actual_fps:.1f} FPS")

        return stats

    def get_streaming_status(self) -> dict:
        """Get current streaming status (Step 91)."""
        if not hasattr(self, '_streaming') or not self._streaming:
            return {"streaming": False}

        duration = time.time() - self._stream_start_time
        current_fps = self._stream_frame_count / duration if duration > 0 else 0

        return {
            "streaming": True,
            "frame_count": self._stream_frame_count,
            "dropped_frames": self._stream_dropped_frames,
            "duration_sec": duration,
            "current_fps": current_fps,
            "target_fps": self._stream_target_fps,
            "roi": self._stream_roi,
        }

    async def capture_planetary_sequence(
        self,
        duration_sec: float,
        output_callback: Optional[Callable[[int, bytes, dict], None]] = None,
        roi: Optional[Tuple[int, int, int, int]] = None,
        lucky_imaging: bool = False
    ) -> dict:
        """
        Capture planetary imaging sequence (Step 91).

        Optimized for planetary imaging with:
        - High frame rate capture
        - Optional ROI for faster readout
        - Lucky imaging mode (marks best frames)

        Args:
            duration_sec: Total capture duration
            output_callback: Called for each frame
            roi: Region of interest (x, y, width, height)
            lucky_imaging: Enable lucky imaging analysis

        Returns:
            Dict with capture statistics and quality metrics
        """
        logger.info(f"Starting planetary capture: {duration_sec}s, lucky={lucky_imaging}")

        # Set up for high-speed capture
        original_exposure = self._exposure_us
        if self._exposure_us > 50000:  # > 50ms is too slow for planetary
            self._exposure_us = 10000  # Default to 10ms
            logger.info(f"Reduced exposure to {self._exposure_us}us for planetary")

        frame_data_list = []
        quality_scores = []

        def collect_frame(frame_num: int, data: bytes, meta: dict):
            frame_info = {"frame_num": frame_num, "timestamp": meta["timestamp"]}

            if lucky_imaging:
                # Simple quality metric (would use actual sharpness in real impl)
                quality = random.uniform(0.5, 1.0)  # Simulated
                quality_scores.append(quality)
                frame_info["quality"] = quality

            if output_callback:
                meta["quality"] = quality_scores[-1] if quality_scores else None
                output_callback(frame_num, data, meta)

            frame_data_list.append(frame_info)

        # Start streaming
        await self.start_video_streaming(
            roi=roi,
            target_fps=100,  # High FPS for planetary
            frame_callback=collect_frame
        )

        # Run for specified duration
        await asyncio.sleep(duration_sec)

        # Stop and get stats
        stats = await self.stop_video_streaming()

        # Restore original exposure
        self._exposure_us = original_exposure

        # Add quality analysis
        if lucky_imaging and quality_scores:
            stats["quality_analysis"] = {
                "mean_quality": sum(quality_scores) / len(quality_scores),
                "max_quality": max(quality_scores),
                "min_quality": min(quality_scores),
                "frames_above_90pct": sum(1 for q in quality_scores if q > 0.9),
                "best_frame_indices": [
                    i for i, q in enumerate(quality_scores)
                    if q > sum(quality_scores) / len(quality_scores) * 1.2
                ][:10]  # Top 10 frames
            }

        logger.info(f"Planetary capture complete: {stats['total_frames']} frames")

        return stats

    # =========================================================================
    # Cooler Simulation
    # =========================================================================

    async def update_cooler_simulation(self, dt_sec: float = 1.0):
        """
        Update cooler simulation state.

        Should be called periodically to simulate temperature changes.

        Args:
            dt_sec: Time step in seconds
        """
        if not self.props.has_cooler:
            return

        ambient_temp = 25.0

        if self._cooler_on:
            # Simulate cooling toward target
            temp_diff = self._sensor_temp_c - self._target_temp_c

            if temp_diff > 0.5:
                # Cooling
                cooling_rate = min(2.0, temp_diff * 0.3)  # °C per second
                self._sensor_temp_c -= cooling_rate * dt_sec

                # Calculate power needed (roughly)
                self._cooler_power = min(100.0, temp_diff * 3.0)
            else:
                # At target, maintain
                self._cooler_power = max(20.0, (ambient_temp - self._target_temp_c) * 2.0)
        else:
            # Warming back to ambient
            if self._sensor_temp_c < ambient_temp - 0.5:
                warming_rate = 1.0  # °C per second
                self._sensor_temp_c += warming_rate * dt_sec
            self._cooler_power = 0.0

        # Add some noise
        self._sensor_temp_c += random.uniform(-0.1, 0.1)

    def get_temperature_status(self) -> dict:
        """Get temperature status."""
        return {
            "sensor_temp_c": self._sensor_temp_c,
            "target_temp_c": self._target_temp_c,
            "cooler_on": self._cooler_on,
            "cooler_power_percent": self._cooler_power,
            "has_cooler": self.props.has_cooler,
        }

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def register_callback(self, callback: Callable):
        """Register a capture callback."""
        self._callbacks.append(callback)

    def get_stats(self) -> dict:
        """Get simulator statistics."""
        return {
            "model": self.props.name,
            "initialized": self._initialized,
            "capturing": self._capturing,
            "frame_count": self._frame_count,
            "gain": self._gain,
            "exposure_us": self._exposure_us,
            "roi": self._roi,
            "binning": self._binning,
            "sensor_temp_c": self._sensor_temp_c if self.props.has_cooler else None,
        }


# =============================================================================
# Global simulator registry (for multi-camera simulation)
# =============================================================================

_simulators: List[CameraSimulator] = []


def get_num_cameras() -> int:
    """Get number of simulated cameras."""
    return len(_simulators)


def add_simulated_camera(model: SimulatedCameraModel = SimulatedCameraModel.ASI294MC_PRO) -> int:
    """
    Add a simulated camera.

    Returns:
        Camera index
    """
    index = len(_simulators)
    sim = CameraSimulator(model=model, camera_index=index)
    _simulators.append(sim)
    logger.info(f"Added simulated camera {index}: {sim.props.name}")
    return index


def get_simulated_camera(index: int) -> Optional[CameraSimulator]:
    """Get a simulated camera by index."""
    if 0 <= index < len(_simulators):
        return _simulators[index]
    return None


def reset_simulators():
    """Reset all simulators."""
    for sim in _simulators:
        sim.close()
    _simulators.clear()
    logger.info("Camera simulators reset")


# =============================================================================
# Main for testing
# =============================================================================

if __name__ == "__main__":
    async def test():
        print("NIGHTWATCH Camera Simulator Test\n")

        # Create simulator
        sim = CameraSimulator(model=SimulatedCameraModel.ASI294MC_PRO)
        sim.initialize()

        print(f"Camera: {sim.props.name}")
        print(f"Resolution: {sim.props.max_width}x{sim.props.max_height}")
        print(f"Pixel size: {sim.props.pixel_size_um}μm")
        print(f"Color: {sim.props.is_color}")
        print(f"Cooler: {sim.props.has_cooler}")

        # Set settings
        sim.set_control_value(0, 250)  # Gain
        sim.set_control_value(1, 10000)  # Exposure 10ms

        # Capture frame
        print("\nCapturing frame...")
        frame = sim.capture_frame()
        print(f"Frame size: {len(frame)} bytes")

        # Test cooler
        if sim.props.has_cooler:
            print("\nTesting cooler simulation...")
            sim.set_control_value(19, -10)  # Target -10°C
            sim.set_control_value(20, 1)     # Cooler on

            for i in range(5):
                await sim.update_cooler_simulation(1.0)
                status = sim.get_temperature_status()
                print(f"  Temp: {status['sensor_temp_c']:.1f}°C, "
                      f"Power: {status['cooler_power_percent']:.0f}%")
                await asyncio.sleep(0.2)

        # Stats
        print("\nSimulator stats:")
        for key, value in sim.get_stats().items():
            print(f"  {key}: {value}")

        sim.close()

    asyncio.run(test())
