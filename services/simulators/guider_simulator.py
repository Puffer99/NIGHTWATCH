"""
NIGHTWATCH Guider Simulator

Simulates PHD2-style autoguiding with configurable RMS levels.
Supports JSON-RPC protocol for integration testing.

Step 535: Configurable RMS levels for quality simulation.
"""

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

from . import BaseSimulator, SimulatorConfig


class GuideState(Enum):
    """Guider states."""
    STOPPED = "stopped"
    CALIBRATING = "calibrating"
    LOOPING = "looping"
    GUIDING = "guiding"
    PAUSED = "paused"
    LOST = "lost"
    ERROR = "error"


class RMSQuality(Enum):
    """Pre-defined RMS quality levels (Step 535)."""
    EXCELLENT = "excellent"   # < 0.5 arcsec
    GOOD = "good"             # 0.5 - 1.0 arcsec
    ACCEPTABLE = "acceptable" # 1.0 - 2.0 arcsec
    POOR = "poor"             # 2.0 - 3.0 arcsec
    BAD = "bad"               # > 3.0 arcsec
    CUSTOM = "custom"


@dataclass
class GuideStats:
    """Guiding statistics."""
    rms_ra_arcsec: float = 0.0
    rms_dec_arcsec: float = 0.0
    rms_total_arcsec: float = 0.0
    peak_ra_arcsec: float = 0.0
    peak_dec_arcsec: float = 0.0
    snr: float = 20.0
    star_mass: float = 1000.0
    frame_count: int = 0


@dataclass
class GuideStar:
    """Selected guide star."""
    x: float = 512.0
    y: float = 512.0
    snr: float = 20.0
    star_mass: float = 1000.0


@dataclass
class GuiderSimulatorConfig(SimulatorConfig):
    """Configuration for guider simulator."""
    # Initial quality level
    rms_quality: RMSQuality = RMSQuality.GOOD

    # Custom RMS settings
    custom_rms_ra: float = 0.8
    custom_rms_dec: float = 0.6

    # Simulation settings
    guide_rate_hz: float = 2.0  # Guide frames per second
    settle_time_sec: float = 5.0
    calibration_time_sec: float = 30.0

    # Star simulation
    star_count: int = 10
    min_snr: float = 5.0
    max_snr: float = 50.0


class GuiderSimulator(BaseSimulator):
    """
    Simulated autoguider (Step 535).

    Features:
    - Configurable RMS quality levels
    - Realistic guide frame simulation
    - Dither support
    - Star loss simulation
    """

    # RMS quality presets (Step 535)
    RMS_PRESETS: Dict[RMSQuality, Dict[str, float]] = {
        RMSQuality.EXCELLENT: {"rms_ra": 0.3, "rms_dec": 0.25, "snr": 40.0},
        RMSQuality.GOOD: {"rms_ra": 0.7, "rms_dec": 0.5, "snr": 25.0},
        RMSQuality.ACCEPTABLE: {"rms_ra": 1.2, "rms_dec": 1.0, "snr": 15.0},
        RMSQuality.POOR: {"rms_ra": 2.0, "rms_dec": 1.8, "snr": 10.0},
        RMSQuality.BAD: {"rms_ra": 3.5, "rms_dec": 3.0, "snr": 6.0},
    }

    def __init__(self, config: Optional[GuiderSimulatorConfig] = None):
        super().__init__(config or GuiderSimulatorConfig(name="guider_simulator"))
        self.guider_config = config or GuiderSimulatorConfig(name="guider_simulator")

        # State
        self._state = GuideState.STOPPED
        self._guide_star: Optional[GuideStar] = None
        self._stats = GuideStats()
        self._rms_quality = self.guider_config.rms_quality

        # RMS settings
        self._target_rms_ra: float = 0.7
        self._target_rms_dec: float = 0.5

        # Dither state
        self._dithering = False
        self._settling = False

        # History
        self._guide_history: List[Dict[str, float]] = []

        # Tasks
        self._guide_task: Optional[asyncio.Task] = None

        # Apply initial quality
        self.set_rms_quality(self._rms_quality)

    @property
    def guide_state(self) -> GuideState:
        """Get current guide state."""
        return self._state

    @property
    def is_guiding(self) -> bool:
        """Check if actively guiding."""
        return self._state == GuideState.GUIDING

    @property
    def is_calibrated(self) -> bool:
        """Check if guider is calibrated."""
        return self._guide_star is not None

    # =========================================================================
    # RMS Quality Control (Step 535)
    # =========================================================================

    def set_rms_quality(self, quality: RMSQuality) -> None:
        """
        Set RMS quality level (Step 535).

        Args:
            quality: Desired RMS quality level
        """
        self._rms_quality = quality

        if quality == RMSQuality.CUSTOM:
            self._target_rms_ra = self.guider_config.custom_rms_ra
            self._target_rms_dec = self.guider_config.custom_rms_dec
        else:
            preset = self.RMS_PRESETS.get(quality, self.RMS_PRESETS[RMSQuality.GOOD])
            self._target_rms_ra = preset["rms_ra"]
            self._target_rms_dec = preset["rms_dec"]
            self._stats.snr = preset["snr"]

    def set_custom_rms(self, rms_ra: float, rms_dec: float) -> None:
        """
        Set custom RMS values (Step 535).

        Args:
            rms_ra: Target RA RMS in arcsec
            rms_dec: Target Dec RMS in arcsec
        """
        self._rms_quality = RMSQuality.CUSTOM
        self._target_rms_ra = rms_ra
        self._target_rms_dec = rms_dec

    def get_rms_quality(self) -> RMSQuality:
        """Get current RMS quality level."""
        return self._rms_quality

    def get_target_rms(self) -> Dict[str, float]:
        """Get target RMS values."""
        return {
            "ra_arcsec": self._target_rms_ra,
            "dec_arcsec": self._target_rms_dec,
            "total_arcsec": (self._target_rms_ra**2 + self._target_rms_dec**2) ** 0.5,
        }

    # =========================================================================
    # Guiding Control
    # =========================================================================

    async def start_guiding(self) -> bool:
        """Start autoguiding."""
        if self._state == GuideState.GUIDING:
            return True

        if not self._guide_star:
            # Auto-select star
            self._guide_star = GuideStar(
                x=random.uniform(200, 800),
                y=random.uniform(200, 800),
                snr=self._stats.snr,
                star_mass=random.uniform(500, 2000),
            )

        self._state = GuideState.GUIDING
        self._stats.frame_count = 0
        self._guide_history.clear()

        # Start guide loop
        if self._guide_task:
            self._guide_task.cancel()
        self._guide_task = asyncio.create_task(self._guide_loop())

        return True

    async def stop_guiding(self) -> bool:
        """Stop autoguiding."""
        if self._guide_task:
            self._guide_task.cancel()
            try:
                await self._guide_task
            except asyncio.CancelledError:
                pass
            self._guide_task = None

        self._state = GuideState.STOPPED
        return True

    async def calibrate(self) -> bool:
        """Run calibration."""
        self._state = GuideState.CALIBRATING

        # Simulate calibration
        await asyncio.sleep(self.guider_config.calibration_time_sec)

        # Select a star
        self._guide_star = GuideStar(
            x=random.uniform(200, 800),
            y=random.uniform(200, 800),
            snr=random.uniform(15, 40),
            star_mass=random.uniform(500, 2000),
        )

        self._state = GuideState.STOPPED
        return True

    async def auto_select_star(self) -> Optional[GuideStar]:
        """Automatically select best guide star."""
        # Simulate finding stars
        await asyncio.sleep(0.5)

        self._guide_star = GuideStar(
            x=random.uniform(200, 800),
            y=random.uniform(200, 800),
            snr=random.uniform(self.guider_config.min_snr, self.guider_config.max_snr),
            star_mass=random.uniform(500, 2000),
        )

        return self._guide_star

    # =========================================================================
    # Dithering
    # =========================================================================

    async def dither(self, pixels: float = 5.0) -> bool:
        """
        Execute a dither.

        Args:
            pixels: Dither amount in pixels
        """
        if self._state != GuideState.GUIDING:
            return False

        self._dithering = True
        self._settling = False

        # Simulate dither movement
        await asyncio.sleep(1.0)

        self._dithering = False
        self._settling = True

        # Simulate settling
        await asyncio.sleep(self.guider_config.settle_time_sec)

        self._settling = False
        return True

    # =========================================================================
    # Guide Loop
    # =========================================================================

    async def _guide_loop(self) -> None:
        """Background guiding simulation."""
        interval = 1.0 / self.guider_config.guide_rate_hz

        while True:
            try:
                await asyncio.sleep(interval)

                if self._state != GuideState.GUIDING:
                    break

                # Generate guide frame data
                frame = self._generate_guide_frame()
                self._guide_history.append(frame)

                # Keep limited history
                if len(self._guide_history) > 1000:
                    self._guide_history = self._guide_history[-1000:]

                # Update statistics
                self._update_stats()

                self._stats.frame_count += 1

            except asyncio.CancelledError:
                break

    def _generate_guide_frame(self) -> Dict[str, float]:
        """Generate a simulated guide frame."""
        # Add noise to target RMS
        noise_factor = 1.0 if not self._settling else 2.0

        ra_error = random.gauss(0, self._target_rms_ra * noise_factor)
        dec_error = random.gauss(0, self._target_rms_dec * noise_factor)

        return {
            "timestamp": datetime.now().timestamp(),
            "ra_error": ra_error,
            "dec_error": dec_error,
            "snr": self._stats.snr + random.gauss(0, 2),
        }

    def _update_stats(self) -> None:
        """Update guiding statistics from history."""
        if len(self._guide_history) < 10:
            return

        recent = self._guide_history[-100:]

        ra_errors = [f["ra_error"] for f in recent]
        dec_errors = [f["dec_error"] for f in recent]

        # Calculate RMS
        self._stats.rms_ra_arcsec = (sum(e**2 for e in ra_errors) / len(ra_errors)) ** 0.5
        self._stats.rms_dec_arcsec = (sum(e**2 for e in dec_errors) / len(dec_errors)) ** 0.5
        self._stats.rms_total_arcsec = (self._stats.rms_ra_arcsec**2 + self._stats.rms_dec_arcsec**2) ** 0.5

        # Peak values
        self._stats.peak_ra_arcsec = max(abs(e) for e in ra_errors)
        self._stats.peak_dec_arcsec = max(abs(e) for e in dec_errors)

    # =========================================================================
    # Status
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get guiding statistics."""
        return {
            "rms_ra_arcsec": round(self._stats.rms_ra_arcsec, 3),
            "rms_dec_arcsec": round(self._stats.rms_dec_arcsec, 3),
            "rms_total_arcsec": round(self._stats.rms_total_arcsec, 3),
            "peak_ra_arcsec": round(self._stats.peak_ra_arcsec, 3),
            "peak_dec_arcsec": round(self._stats.peak_dec_arcsec, 3),
            "snr": round(self._stats.snr, 1),
            "frame_count": self._stats.frame_count,
        }

    def get_status(self) -> Dict[str, Any]:
        """Get complete guider status."""
        return {
            "state": self._state.value,
            "is_guiding": self.is_guiding,
            "is_calibrated": self.is_calibrated,
            "rms_quality": self._rms_quality.value,
            "target_rms": self.get_target_rms(),
            "current_stats": self.get_stats(),
            "dithering": self._dithering,
            "settling": self._settling,
            "guide_star": {
                "x": self._guide_star.x if self._guide_star else None,
                "y": self._guide_star.y if self._guide_star else None,
                "snr": self._guide_star.snr if self._guide_star else None,
            } if self._guide_star else None,
        }
