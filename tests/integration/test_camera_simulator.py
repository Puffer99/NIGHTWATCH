"""
NIGHTWATCH Camera Simulator Integration Test (Step 101)

Tests end-to-end camera functionality using the camera simulator.
Verifies capture, format conversion, and callback mechanisms work together.
"""

import asyncio
import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

# Import simulator and camera service
from services.simulators.camera_simulator import (
    CameraSimulator,
    SimulatedCameraModel,
    add_simulated_camera,
    get_simulated_camera,
    reset_simulators,
)


class TestCameraSimulatorBasic:
    """Basic camera simulator functionality tests."""

    def setup_method(self):
        """Reset simulators before each test."""
        reset_simulators()

    def test_simulator_creation(self):
        """Test creating a camera simulator."""
        sim = CameraSimulator(model=SimulatedCameraModel.ASI294MC_PRO)
        assert sim.props.name == "ZWO ASI294MC Pro"
        assert sim.props.max_width == 4144
        assert sim.props.max_height == 2822
        assert sim.props.is_color is True
        assert sim.props.has_cooler is True

    def test_simulator_initialization(self):
        """Test initializing the simulator."""
        sim = CameraSimulator(model=SimulatedCameraModel.ASI294MC_PRO)
        assert sim.initialized is False

        result = sim.initialize()
        assert result is True
        assert sim.initialized is True

        sim.close()
        assert sim.initialized is False

    def test_get_camera_property(self):
        """Test getting camera properties."""
        sim = CameraSimulator(model=SimulatedCameraModel.ASI533MC_PRO)
        sim.initialize()

        props = sim.get_camera_property()
        assert props["Name"] == "ZWO ASI533MC Pro"
        assert props["MaxWidth"] == 3008
        assert props["MaxHeight"] == 3008
        assert props["IsColorCam"] is True
        assert props["IsCoolerCam"] is True

        sim.close()

    def test_multiple_camera_models(self):
        """Test different camera models."""
        models = [
            (SimulatedCameraModel.ASI294MC_PRO, True, True),
            (SimulatedCameraModel.ASI183MM_PRO, False, True),
            (SimulatedCameraModel.ASI120MM_S, False, False),
            (SimulatedCameraModel.ASI462MC, True, False),
        ]

        for model, is_color, has_cooler in models:
            sim = CameraSimulator(model=model)
            assert sim.props.is_color == is_color, f"{model.name} color mismatch"
            assert sim.props.has_cooler == has_cooler, f"{model.name} cooler mismatch"


class TestCameraSimulatorSettings:
    """Test camera settings and controls."""

    def setup_method(self):
        """Create and initialize simulator."""
        reset_simulators()
        self.sim = CameraSimulator(model=SimulatedCameraModel.ASI294MC_PRO)
        self.sim.initialize()

    def teardown_method(self):
        """Clean up simulator."""
        if self.sim:
            self.sim.close()

    def test_gain_control(self):
        """Test setting and getting gain."""
        self.sim.set_control_value(0, 250)  # ASI_GAIN
        value, _ = self.sim.get_control_value(0)
        assert value == 250

        # Test clamping
        self.sim.set_control_value(0, 1000)  # Above max
        value, _ = self.sim.get_control_value(0)
        assert value == self.sim.props.max_gain

    def test_exposure_control(self):
        """Test setting and getting exposure."""
        self.sim.set_control_value(1, 50000)  # ASI_EXPOSURE in us
        value, _ = self.sim.get_control_value(1)
        assert value == 50000

    def test_roi_setting(self):
        """Test setting region of interest."""
        self.sim.set_roi(100, 100, 800, 600, 1)
        roi = self.sim.get_roi()

        assert roi[0] == 100  # x
        assert roi[1] == 100  # y
        assert roi[2] == 800  # width
        assert roi[3] == 600  # height
        assert roi[4] == 1    # binning

    def test_binning_validation(self):
        """Test binning with invalid values."""
        # Set binning to invalid value - should fallback to 1
        self.sim.set_roi(0, 0, 1000, 1000, 8)
        roi = self.sim.get_roi()
        assert roi[4] == 1  # Should be 1, not 8


class TestCameraSimulatorCapture:
    """Test frame capture functionality."""

    def setup_method(self):
        """Create and initialize simulator."""
        reset_simulators()
        self.sim = CameraSimulator(model=SimulatedCameraModel.ASI294MC_PRO)
        self.sim.initialize()

    def teardown_method(self):
        """Clean up simulator."""
        if self.sim:
            self.sim.close()

    def test_single_frame_capture(self):
        """Test capturing a single frame."""
        self.sim.set_roi(0, 0, 640, 480, 1)
        self.sim.set_control_value(1, 10000)  # 10ms exposure

        frame = self.sim.capture_frame()
        assert frame is not None
        assert len(frame) > 0

        # Check expected size (640 * 480 * 2 bytes for 16-bit)
        expected_size = 640 * 480 * 2
        assert len(frame) == expected_size

    def test_capture_increments_frame_count(self):
        """Test that captures increment frame counter."""
        initial_count = self.sim._frame_count

        self.sim.capture_frame()
        assert self.sim._frame_count == initial_count + 1

        self.sim.capture_frame()
        assert self.sim._frame_count == initial_count + 2

    def test_capture_requires_initialization(self):
        """Test that capture requires initialization."""
        sim = CameraSimulator(model=SimulatedCameraModel.ASI294MC_PRO)
        # Don't initialize

        with pytest.raises(RuntimeError):
            sim.capture_frame()

    @pytest.mark.asyncio
    async def test_video_capture(self):
        """Test video capture mode."""
        self.sim.set_roi(0, 0, 320, 240, 1)
        self.sim.set_control_value(1, 1000)  # 1ms exposure

        frames_captured = []

        def callback(frame_num, data):
            frames_captured.append((frame_num, len(data)))

        # Capture for 0.1 seconds
        total = await self.sim.capture_video(0.1, callback=callback)

        assert total > 0
        assert len(frames_captured) > 0
        assert frames_captured[-1][0] == total

    @pytest.mark.asyncio
    async def test_video_capture_stop(self):
        """Test stopping video capture."""
        self.sim.set_control_value(1, 10000)  # 10ms exposure

        # Start capture in background
        capture_task = asyncio.create_task(
            self.sim.capture_video(10.0)  # Long duration
        )

        # Wait a bit then stop
        await asyncio.sleep(0.05)
        self.sim.stop_video_capture()

        # Should complete quickly
        total = await asyncio.wait_for(capture_task, timeout=1.0)
        assert total >= 0


class TestCameraSimulatorCooler:
    """Test cooler simulation."""

    def setup_method(self):
        """Create simulator with cooler."""
        reset_simulators()
        self.sim = CameraSimulator(model=SimulatedCameraModel.ASI294MC_PRO)
        self.sim.initialize()

    def teardown_method(self):
        """Clean up."""
        if self.sim:
            self.sim.close()

    def test_cooler_off_by_default(self):
        """Test cooler is off by default."""
        status = self.sim.get_temperature_status()
        assert status["cooler_on"] is False
        assert status["has_cooler"] is True

    def test_enable_cooler(self):
        """Test enabling cooler."""
        self.sim.set_control_value(19, -10)  # Target temp
        self.sim.set_control_value(20, 1)    # Cooler on

        status = self.sim.get_temperature_status()
        assert status["cooler_on"] is True
        assert status["target_temp_c"] == -10

    @pytest.mark.asyncio
    async def test_cooler_simulation(self):
        """Test cooler temperature simulation."""
        initial_temp = self.sim._sensor_temp_c

        # Enable cooler
        self.sim.set_control_value(19, -10)
        self.sim.set_control_value(20, 1)

        # Simulate cooling
        for _ in range(5):
            await self.sim.update_cooler_simulation(1.0)

        # Temperature should have dropped
        assert self.sim._sensor_temp_c < initial_temp

    def test_no_cooler_camera(self):
        """Test camera without cooler."""
        sim = CameraSimulator(model=SimulatedCameraModel.ASI120MM_S)
        sim.initialize()

        status = sim.get_temperature_status()
        assert status["has_cooler"] is False

        sim.close()


class TestCameraSimulatorRegistry:
    """Test camera registry functions."""

    def setup_method(self):
        """Reset registry before each test."""
        reset_simulators()

    def test_add_simulated_camera(self):
        """Test adding cameras to registry."""
        idx1 = add_simulated_camera(SimulatedCameraModel.ASI294MC_PRO)
        idx2 = add_simulated_camera(SimulatedCameraModel.ASI183MM_PRO)

        assert idx1 == 0
        assert idx2 == 1

    def test_get_simulated_camera(self):
        """Test retrieving cameras from registry."""
        add_simulated_camera(SimulatedCameraModel.ASI294MC_PRO)

        cam = get_simulated_camera(0)
        assert cam is not None
        assert cam.props.name == "ZWO ASI294MC Pro"

        # Invalid index
        cam = get_simulated_camera(99)
        assert cam is None

    def test_reset_simulators(self):
        """Test resetting simulator registry."""
        add_simulated_camera(SimulatedCameraModel.ASI294MC_PRO)
        add_simulated_camera(SimulatedCameraModel.ASI183MM_PRO)

        reset_simulators()

        assert get_simulated_camera(0) is None


class TestCameraSimulatorStats:
    """Test simulator statistics."""

    def test_get_stats(self):
        """Test getting simulator statistics."""
        sim = CameraSimulator(model=SimulatedCameraModel.ASI294MC_PRO)
        sim.initialize()

        sim.set_control_value(0, 200)
        sim.set_control_value(1, 5000)
        sim.set_roi(0, 0, 800, 600, 2)

        sim.capture_frame()
        sim.capture_frame()

        stats = sim.get_stats()

        assert stats["model"] == "ZWO ASI294MC Pro"
        assert stats["initialized"] is True
        assert stats["frame_count"] == 2
        assert stats["gain"] == 200
        assert stats["exposure_us"] == 5000
        assert stats["binning"] == 2

        sim.close()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
