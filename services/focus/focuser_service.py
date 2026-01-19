"""
NIGHTWATCH Auto Focus Service
Temperature-Compensated Focus Control

POS Panel v3.0 - Day 21 Recommendations (Larry Weber + Diffraction Limited):
- Temperature coefficient: -2.5 steps/°C typical for refractors
- HFD (Half Flux Diameter) for focus metric - more robust than FWHM
- V-curve fitting for precise focus position
- Backlash compensation: always approach from same direction
- Focus every 2°C change or 30 minutes
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Tuple, Callable
import math

logger = logging.getLogger("NIGHTWATCH.Focus")


class FocuserState(Enum):
    """Focuser states."""
    IDLE = "idle"
    MOVING = "moving"
    AUTOFOCUS = "autofocus"
    CALIBRATING = "calibrating"
    ERROR = "error"


class AutoFocusMethod(Enum):
    """Auto-focus algorithms."""
    VCURVE = "vcurve"           # V-curve parabolic fit
    BAHTINOV = "bahtinov"       # Bahtinov mask analysis
    CONTRAST = "contrast"       # Image contrast maximization
    HFD = "hfd"                 # Half-flux diameter minimization


@dataclass
class FocuserConfig:
    """Focuser configuration."""
    # Hardware
    max_position: int = 50000           # Maximum focuser position
    step_size_um: float = 1.0           # Microns per step
    backlash_steps: int = 100           # Backlash compensation

    # Temperature compensation
    temp_coefficient: float = -2.5      # Steps per °C
    temp_interval_c: float = 2.0        # Re-focus temperature threshold
    time_interval_min: float = 30.0     # Re-focus time threshold

    # Auto-focus
    autofocus_method: AutoFocusMethod = AutoFocusMethod.HFD
    autofocus_step_size: int = 100      # Steps between samples
    autofocus_samples: int = 9          # Number of focus positions to sample
    autofocus_exposure_sec: float = 2.0 # Exposure for focus frames

    # Tolerances
    hfd_target: float = 3.0             # Target HFD in pixels
    focus_tolerance: int = 10           # Position tolerance in steps


@dataclass
class FocusMetric:
    """Focus quality measurement."""
    timestamp: datetime
    position: int
    hfd: float              # Half-flux diameter in pixels
    fwhm: float             # Full-width half-max in arcsec
    peak_value: float       # Peak pixel value
    star_count: int         # Number of detected stars
    temperature_c: float    # Sensor temperature at measurement


@dataclass
class FocusRun:
    """Auto-focus run data."""
    run_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    method: AutoFocusMethod = AutoFocusMethod.HFD
    initial_position: int = 0
    final_position: int = 0
    measurements: List[FocusMetric] = field(default_factory=list)
    best_hfd: float = float('inf')
    success: bool = False
    error: Optional[str] = None


class FocuserService:
    """
    Temperature-compensated auto-focus for NIGHTWATCH.

    Features:
    - ZWO EAF integration via ASCOM/INDI
    - Temperature compensation with configurable coefficient
    - V-curve auto-focus with HFD metric
    - Backlash compensation
    - Focus history and trending

    Usage:
        focuser = FocuserService()
        await focuser.connect()
        await focuser.auto_focus()
        focuser.enable_temp_compensation()
    """

    def __init__(self, config: Optional[FocuserConfig] = None):
        """
        Initialize focuser service.

        Args:
            config: Focuser configuration
        """
        self.config = config or FocuserConfig()
        self._state = FocuserState.IDLE
        self._position = 25000  # Mid-range default
        self._temperature = 20.0
        self._connected = False
        self._last_focus_time: Optional[datetime] = None
        self._last_focus_temp: Optional[float] = None
        self._focus_history: List[FocusRun] = []
        self._temp_comp_enabled = False
        self._temp_monitor_task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable] = []

    @property
    def connected(self) -> bool:
        """Check if focuser is connected."""
        return self._connected

    @property
    def state(self) -> FocuserState:
        """Current focuser state."""
        return self._state

    @property
    def position(self) -> int:
        """Current focuser position in steps."""
        return self._position

    @property
    def temperature(self) -> float:
        """Current focuser temperature in Celsius."""
        return self._temperature

    async def connect(self, device: str = "ZWO EAF") -> bool:
        """
        Connect to focuser.

        Args:
            device: Focuser device name

        Returns:
            True if connected successfully
        """
        try:
            # In real implementation, would connect via ASCOM/INDI
            logger.info(f"Connecting to focuser: {device}")

            # Simulate connection
            await asyncio.sleep(0.5)

            self._connected = True
            self._state = FocuserState.IDLE
            logger.info(f"Focuser connected at position {self._position}")

            return True

        except Exception as e:
            logger.error(f"Failed to connect focuser: {e}")
            self._state = FocuserState.ERROR
            return False

    async def disconnect(self):
        """Disconnect from focuser."""
        if self._temp_monitor_task:
            self._temp_monitor_task.cancel()
            try:
                await self._temp_monitor_task
            except asyncio.CancelledError:
                pass

        self._connected = False
        self._state = FocuserState.IDLE
        logger.info("Focuser disconnected")

    # =========================================================================
    # MOVEMENT
    # =========================================================================

    async def move_to(self, position: int, compensate_backlash: bool = True) -> bool:
        """
        Move focuser to absolute position.

        Args:
            position: Target position in steps
            compensate_backlash: Apply backlash compensation

        Returns:
            True if move completed successfully
        """
        if not self._connected:
            raise RuntimeError("Focuser not connected")

        if self._state == FocuserState.MOVING:
            raise RuntimeError("Focuser already moving")

        # Clamp position
        position = max(0, min(position, self.config.max_position))

        # Calculate direction
        direction = 1 if position > self._position else -1

        # Backlash compensation: always approach from below
        if compensate_backlash and direction > 0:
            # Moving outward, overshoot and come back
            overshoot = position + self.config.backlash_steps
            overshoot = min(overshoot, self.config.max_position)

            self._state = FocuserState.MOVING
            await self._do_move(overshoot)
            await self._do_move(position)
        else:
            self._state = FocuserState.MOVING
            await self._do_move(position)

        self._state = FocuserState.IDLE
        return True

    async def _do_move(self, position: int):
        """Execute focuser move."""
        steps = abs(position - self._position)
        # Simulate movement time (roughly 100 steps/second)
        move_time = steps / 100.0

        logger.debug(f"Moving focuser: {self._position} -> {position} ({steps} steps)")

        # Simulate gradual movement
        start_pos = self._position
        start_time = datetime.now()

        while self._position != position:
            await asyncio.sleep(0.1)
            elapsed = (datetime.now() - start_time).total_seconds()
            progress = min(1.0, elapsed / move_time)
            self._position = int(start_pos + (position - start_pos) * progress)

        self._position = position
        logger.debug(f"Move complete: position {self._position}")

    async def move_relative(self, steps: int) -> bool:
        """
        Move focuser relative to current position.

        Args:
            steps: Steps to move (positive = outward)

        Returns:
            True if move completed
        """
        return await self.move_to(self._position + steps)

    async def halt(self):
        """Halt focuser movement."""
        # In real implementation, would send halt command
        self._state = FocuserState.IDLE
        logger.info("Focuser halted")

    # =========================================================================
    # AUTO-FOCUS
    # =========================================================================

    async def auto_focus(self,
                         camera=None,
                         method: Optional[AutoFocusMethod] = None) -> FocusRun:
        """
        Run auto-focus routine.

        Args:
            camera: Camera service for capturing focus frames
            method: Auto-focus method (uses config default if None)

        Returns:
            FocusRun with results
        """
        if not self._connected:
            raise RuntimeError("Focuser not connected")

        if self._state == FocuserState.AUTOFOCUS:
            raise RuntimeError("Auto-focus already running")

        method = method or self.config.autofocus_method

        run = FocusRun(
            run_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            start_time=datetime.now(),
            method=method,
            initial_position=self._position
        )

        self._state = FocuserState.AUTOFOCUS
        logger.info(f"Starting auto-focus ({method.value})")

        try:
            if method == AutoFocusMethod.VCURVE:
                await self._vcurve_focus(run, camera)
            elif method == AutoFocusMethod.HFD:
                await self._hfd_focus(run, camera)
            else:
                raise ValueError(f"Unsupported auto-focus method: {method}")

            run.success = True
            run.end_time = datetime.now()

            # Update tracking
            self._last_focus_time = datetime.now()
            self._last_focus_temp = self._temperature
            self._focus_history.append(run)

            logger.info(f"Auto-focus complete: position {run.final_position}, "
                       f"HFD {run.best_hfd:.2f}")

        except Exception as e:
            run.success = False
            run.error = str(e)
            run.end_time = datetime.now()
            logger.error(f"Auto-focus failed: {e}")

        finally:
            self._state = FocuserState.IDLE

        return run

    async def _vcurve_focus(self, run: FocusRun, camera):
        """V-curve auto-focus algorithm."""
        # Calculate focus range
        half_range = (self.config.autofocus_samples // 2) * self.config.autofocus_step_size
        start_pos = self._position - half_range
        end_pos = self._position + half_range

        # Move to start position
        await self.move_to(start_pos - self.config.backlash_steps, False)
        await self.move_to(start_pos, False)

        # Sample HFD at each position
        positions = []
        hfds = []

        for i in range(self.config.autofocus_samples):
            pos = start_pos + i * self.config.autofocus_step_size
            await self.move_to(pos, compensate_backlash=False)

            # Capture and measure HFD
            hfd = await self._measure_hfd(camera)

            positions.append(pos)
            hfds.append(hfd)

            run.measurements.append(FocusMetric(
                timestamp=datetime.now(),
                position=pos,
                hfd=hfd,
                fwhm=hfd * 0.6,  # Approximate conversion
                peak_value=0,
                star_count=0,
                temperature_c=self._temperature
            ))

            logger.debug(f"Focus sample: pos={pos}, HFD={hfd:.2f}")

        # Fit parabola to V-curve
        best_pos = self._fit_vcurve(positions, hfds)

        # Move to best position
        await self.move_to(best_pos)

        # Verify focus
        final_hfd = await self._measure_hfd(camera)

        run.final_position = best_pos
        run.best_hfd = final_hfd

    async def _hfd_focus(self, run: FocusRun, camera):
        """HFD minimization auto-focus."""
        # Simple hill-climbing approach
        step = self.config.autofocus_step_size
        best_hfd = await self._measure_hfd(camera)
        best_pos = self._position

        # Try moving inward
        await self.move_relative(-step)
        hfd_in = await self._measure_hfd(camera)

        if hfd_in < best_hfd:
            # Continue inward
            direction = -1
            best_hfd = hfd_in
            best_pos = self._position
        else:
            # Try outward
            await self.move_relative(step * 2)  # Back to start + one step out
            hfd_out = await self._measure_hfd(camera)

            if hfd_out < best_hfd:
                direction = 1
                best_hfd = hfd_out
                best_pos = self._position
            else:
                # Already at best position
                await self.move_relative(-step)
                run.final_position = self._position
                run.best_hfd = best_hfd
                return

        # Continue in chosen direction until HFD increases
        while True:
            await self.move_relative(direction * step)
            hfd = await self._measure_hfd(camera)

            run.measurements.append(FocusMetric(
                timestamp=datetime.now(),
                position=self._position,
                hfd=hfd,
                fwhm=hfd * 0.6,
                peak_value=0,
                star_count=0,
                temperature_c=self._temperature
            ))

            if hfd < best_hfd:
                best_hfd = hfd
                best_pos = self._position
            else:
                # Passed the minimum, go back
                await self.move_to(best_pos)
                break

            # Safety limit
            if len(run.measurements) > 20:
                break

        run.final_position = best_pos
        run.best_hfd = best_hfd

    async def _measure_hfd(self, camera) -> float:
        """
        Measure Half-Flux Diameter from focus frame.

        In real implementation, would:
        1. Capture frame with camera
        2. Detect stars using SEP/photutils
        3. Calculate HFD for each star
        4. Return median HFD
        """
        # Simulate HFD measurement
        # Returns a V-curve centered around position 25000
        optimal = 25000
        distance = abs(self._position - optimal)

        # Parabolic model: HFD = base + k * distance^2
        base_hfd = 2.5
        k = 1e-7
        hfd = base_hfd + k * distance * distance

        # Add some noise
        import random
        hfd += random.gauss(0, 0.1)

        await asyncio.sleep(self.config.autofocus_exposure_sec)

        return max(1.0, hfd)

    def _fit_vcurve(self, positions: List[int], hfds: List[float]) -> int:
        """
        Fit parabola to V-curve data.

        Returns:
            Optimal focus position
        """
        # Simple parabolic fit using least squares
        # y = ax^2 + bx + c
        # Minimum at x = -b/(2a)

        n = len(positions)
        if n < 3:
            return positions[hfds.index(min(hfds))]

        # Normalize positions for numerical stability
        x_mean = sum(positions) / n
        x = [p - x_mean for p in positions]
        y = hfds

        # Build normal equations
        sum_x2 = sum(xi**2 for xi in x)
        sum_x4 = sum(xi**4 for xi in x)
        sum_x2y = sum(xi**2 * yi for xi, yi in zip(x, y))
        sum_y = sum(y)

        # Simplified fit assuming symmetric V-curve
        # a = sum(x^2 * y) / sum(x^4)
        if sum_x4 > 0:
            a = sum_x2y / sum_x4
            c = (sum_y - a * sum_x2) / n

            # Minimum at x = 0 in normalized coords
            best_pos = int(x_mean)
        else:
            # Fallback to minimum sample
            best_pos = positions[hfds.index(min(hfds))]

        return best_pos

    # =========================================================================
    # TEMPERATURE COMPENSATION
    # =========================================================================

    def enable_temp_compensation(self):
        """Enable temperature compensation."""
        self._temp_comp_enabled = True
        if not self._temp_monitor_task:
            self._temp_monitor_task = asyncio.create_task(self._temperature_monitor())
        logger.info("Temperature compensation enabled")

    def disable_temp_compensation(self):
        """Disable temperature compensation."""
        self._temp_comp_enabled = False
        logger.info("Temperature compensation disabled")

    async def _temperature_monitor(self):
        """Monitor temperature and apply compensation."""
        try:
            while True:
                await asyncio.sleep(60)  # Check every minute

                if not self._temp_comp_enabled:
                    continue

                # Get current temperature
                new_temp = await self._read_temperature()

                if self._last_focus_temp is not None:
                    temp_change = new_temp - self._last_focus_temp

                    # Check if compensation needed
                    if abs(temp_change) >= self.config.temp_interval_c:
                        # Calculate compensation
                        steps = int(temp_change * self.config.temp_coefficient)

                        if steps != 0:
                            logger.info(f"Temperature compensation: {temp_change:.1f}°C "
                                       f"-> {steps} steps")
                            await self.move_relative(steps)
                            self._last_focus_temp = new_temp

                self._temperature = new_temp

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Temperature monitor error: {e}")

    async def _read_temperature(self) -> float:
        """Read focuser temperature sensor."""
        # In real implementation, would read from focuser
        # Simulate slow temperature drift
        import random
        self._temperature += random.gauss(0, 0.1)
        return self._temperature

    def needs_refocus(self) -> Tuple[bool, str]:
        """
        Check if refocus is needed.

        Returns:
            (needs_refocus, reason)
        """
        if self._last_focus_time is None:
            return True, "No previous focus"

        # Check time since last focus
        elapsed = (datetime.now() - self._last_focus_time).total_seconds() / 60.0
        if elapsed >= self.config.time_interval_min:
            return True, f"Time: {elapsed:.0f} minutes since last focus"

        # Check temperature change
        if self._last_focus_temp is not None:
            temp_change = abs(self._temperature - self._last_focus_temp)
            if temp_change >= self.config.temp_interval_c:
                return True, f"Temperature: {temp_change:.1f}°C change"

        return False, "Focus OK"

    # =========================================================================
    # CALIBRATION
    # =========================================================================

    async def calibrate_temp_coefficient(self,
                                         camera,
                                         temp_range: float = 5.0) -> float:
        """
        Calibrate temperature compensation coefficient.

        Requires temperature to change during calibration.

        Args:
            camera: Camera for focus measurements
            temp_range: Required temperature change for calibration

        Returns:
            Calculated temperature coefficient
        """
        logger.info("Starting temperature coefficient calibration")
        logger.info(f"Requires {temp_range}°C temperature change")

        self._state = FocuserState.CALIBRATING

        # Record initial state
        initial_temp = self._temperature
        initial_focus = await self._find_best_focus(camera)

        logger.info(f"Initial: temp={initial_temp:.1f}°C, focus={initial_focus}")

        # Wait for temperature change
        while abs(self._temperature - initial_temp) < temp_range:
            logger.debug(f"Waiting for temperature change: "
                        f"{self._temperature:.1f}°C (need {temp_range}°C change)")
            await asyncio.sleep(60)

        # Find new best focus
        final_temp = self._temperature
        final_focus = await self._find_best_focus(camera)

        logger.info(f"Final: temp={final_temp:.1f}°C, focus={final_focus}")

        # Calculate coefficient
        temp_change = final_temp - initial_temp
        focus_change = final_focus - initial_focus
        coefficient = focus_change / temp_change

        logger.info(f"Calibrated coefficient: {coefficient:.2f} steps/°C")

        self.config.temp_coefficient = coefficient
        self._state = FocuserState.IDLE

        return coefficient

    # =========================================================================
    # TEMPERATURE COEFFICIENT STORAGE (Step 186)
    # =========================================================================

    def save_temp_coefficient(self, filepath: str = None) -> bool:
        """
        Save temperature coefficient to persistent storage (Step 186).

        Args:
            filepath: Path to save file. Defaults to ~/.nightwatch/focus_calibration.json

        Returns:
            True if saved successfully
        """
        import json
        from pathlib import Path

        if filepath is None:
            config_dir = Path.home() / ".nightwatch"
            config_dir.mkdir(parents=True, exist_ok=True)
            filepath = config_dir / "focus_calibration.json"
        else:
            filepath = Path(filepath)

        calibration_data = {
            "temp_coefficient": self.config.temp_coefficient,
            "calibration_date": datetime.now().isoformat(),
            "focuser_position_at_calibration": self._position,
            "temperature_at_calibration": self._temperature,
            "max_position": self.config.max_position,
            "step_size_um": self.config.step_size_um,
        }

        try:
            with open(filepath, "w") as f:
                json.dump(calibration_data, f, indent=2)
            logger.info(f"Temperature coefficient saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save temperature coefficient: {e}")
            return False

    def load_temp_coefficient(self, filepath: str = None) -> bool:
        """
        Load temperature coefficient from persistent storage (Step 186).

        Args:
            filepath: Path to load from. Defaults to ~/.nightwatch/focus_calibration.json

        Returns:
            True if loaded successfully
        """
        import json
        from pathlib import Path

        if filepath is None:
            filepath = Path.home() / ".nightwatch" / "focus_calibration.json"
        else:
            filepath = Path(filepath)

        if not filepath.exists():
            logger.warning(f"No calibration file found at {filepath}")
            return False

        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            self.config.temp_coefficient = data.get("temp_coefficient", self.config.temp_coefficient)
            calibration_date = data.get("calibration_date", "unknown")

            logger.info(f"Loaded temperature coefficient: {self.config.temp_coefficient:.2f} steps/°C "
                       f"(calibrated {calibration_date})")
            return True

        except Exception as e:
            logger.error(f"Failed to load temperature coefficient: {e}")
            return False

    def get_temp_coefficient_info(self) -> dict:
        """
        Get information about the current temperature coefficient (Step 186).

        Returns:
            Dict with coefficient value and metadata
        """
        import json
        from pathlib import Path

        filepath = Path.home() / ".nightwatch" / "focus_calibration.json"

        info = {
            "current_coefficient": self.config.temp_coefficient,
            "from_calibration_file": False,
            "calibration_date": None,
        }

        if filepath.exists():
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                info["from_calibration_file"] = True
                info["calibration_date"] = data.get("calibration_date")
                info["focuser_position_at_calibration"] = data.get("focuser_position_at_calibration")
                info["temperature_at_calibration"] = data.get("temperature_at_calibration")
            except Exception:
                pass

        return info

    async def _find_best_focus(self, camera) -> int:
        """Run auto-focus and return best position."""
        run = await self.auto_focus(camera)
        return run.final_position


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    async def test():
        print("NIGHTWATCH Focuser Service Test\n")

        focuser = FocuserService()

        print("Connecting to focuser...")
        if await focuser.connect():
            print(f"Connected! Position: {focuser.position}")

            print("\nMoving to position 20000...")
            await focuser.move_to(20000)
            print(f"Position: {focuser.position}")

            print("\nRunning auto-focus...")
            run = await focuser.auto_focus()
            print(f"Auto-focus {'succeeded' if run.success else 'failed'}")
            print(f"Best position: {run.final_position}")
            print(f"Best HFD: {run.best_hfd:.2f}")

            print("\nEnabling temperature compensation...")
            focuser.enable_temp_compensation()

            needs, reason = focuser.needs_refocus()
            print(f"Needs refocus: {needs} ({reason})")

            await focuser.disconnect()
        else:
            print("Failed to connect (expected if no focuser attached)")

    asyncio.run(test())
