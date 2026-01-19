"""
Mock Guider Service for Testing.

Simulates PHD2 guiding behavior for unit and integration testing.
Provides configurable guiding states and RMS simulation.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, List
import random

logger = logging.getLogger("NIGHTWATCH.fixtures.MockGuider")


class MockGuiderState(Enum):
    """Guider operational states."""
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    CALIBRATING = "calibrating"
    LOOPING = "looping"
    GUIDING = "guiding"
    SETTLING = "settling"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class GuideStats:
    """Current guiding statistics."""
    rms_total_arcsec: float = 0.0
    rms_ra_arcsec: float = 0.0
    rms_dec_arcsec: float = 0.0
    peak_ra_arcsec: float = 0.0
    peak_dec_arcsec: float = 0.0
    snr: float = 0.0
    star_mass: float = 0.0
    frame_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "rms_total": self.rms_total_arcsec,
            "rms_ra": self.rms_ra_arcsec,
            "rms_dec": self.rms_dec_arcsec,
            "peak_ra": self.peak_ra_arcsec,
            "peak_dec": self.peak_dec_arcsec,
            "snr": self.snr,
            "star_mass": self.star_mass,
            "frame_count": self.frame_count,
        }


@dataclass
class GuideStar:
    """Selected guide star information."""
    x: float = 0.0
    y: float = 0.0
    snr: float = 0.0
    mass: float = 0.0
    is_locked: bool = False


class MockGuider:
    """
    Mock guider service for testing.

    Simulates PHD2 guiding behavior with:
    - Connection management
    - Guide star selection
    - Calibration simulation
    - Guiding with RMS simulation
    - Dithering support
    - Settling detection

    Example:
        guider = MockGuider()
        await guider.connect()
        await guider.start_looping()
        await guider.select_star(100, 100)
        await guider.start_guiding()
        stats = guider.get_stats()
    """

    # Default guiding performance
    DEFAULT_RMS_ARCSEC = 0.8
    DEFAULT_SNR = 30.0

    def __init__(
        self,
        simulate_delays: bool = True,
        base_rms: float = DEFAULT_RMS_ARCSEC,
    ):
        """
        Initialize mock guider.

        Args:
            simulate_delays: Whether to simulate realistic delays
            base_rms: Base RMS value for guiding simulation
        """
        self.simulate_delays = simulate_delays
        self.base_rms = base_rms

        # State
        self._state = MockGuiderState.DISCONNECTED
        self._stats = GuideStats()
        self._guide_star: Optional[GuideStar] = None
        self._is_calibrated = False

        # Dithering
        self._dither_pixels = 0.0
        self._is_settling = False
        self._settle_timeout_sec = 60.0

        # Background tasks
        self._guide_task: Optional[asyncio.Task] = None

        # Error injection
        self._inject_connect_error = False
        self._inject_calibrate_error = False
        self._inject_guide_error = False
        self._inject_star_lost = False

        # Callbacks
        self._guide_callbacks: List[Callable] = []
        self._settle_callbacks: List[Callable] = []

    @property
    def state(self) -> MockGuiderState:
        """Get current guider state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if guider is connected."""
        return self._state != MockGuiderState.DISCONNECTED

    @property
    def is_guiding(self) -> bool:
        """Check if actively guiding."""
        return self._state == MockGuiderState.GUIDING

    @property
    def is_calibrated(self) -> bool:
        """Check if guider is calibrated."""
        return self._is_calibrated

    @property
    def is_settling(self) -> bool:
        """Check if guider is settling after dither."""
        return self._is_settling

    async def connect(self, host: str = "localhost", port: int = 4400) -> bool:
        """
        Connect to guider service.

        Args:
            host: PHD2 host (ignored in mock)
            port: PHD2 port (ignored in mock)

        Returns:
            True if connected successfully
        """
        if self._inject_connect_error:
            raise ConnectionError("Mock: Simulated connection failure")

        if self.simulate_delays:
            await asyncio.sleep(0.1)

        self._state = MockGuiderState.CONNECTED
        logger.info(f"MockGuider connected (host={host}, port={port})")
        return True

    async def disconnect(self):
        """Disconnect from guider service."""
        await self.stop_guiding()
        self._state = MockGuiderState.DISCONNECTED
        logger.info("MockGuider disconnected")

    async def start_looping(self) -> bool:
        """
        Start camera looping (exposure loop without guiding).

        Returns:
            True if looping started
        """
        if not self.is_connected:
            raise RuntimeError("Guider not connected")

        if self.simulate_delays:
            await asyncio.sleep(0.2)

        self._state = MockGuiderState.LOOPING
        logger.info("MockGuider looping started")
        return True

    async def stop_looping(self):
        """Stop camera looping."""
        if self._state == MockGuiderState.LOOPING:
            self._state = MockGuiderState.CONNECTED
            logger.info("MockGuider looping stopped")

    async def select_star(self, x: float, y: float) -> bool:
        """
        Select a guide star at given position.

        Args:
            x: Star x position
            y: Star y position

        Returns:
            True if star selected successfully
        """
        if not self.is_connected:
            raise RuntimeError("Guider not connected")

        # Simulate star detection
        self._guide_star = GuideStar(
            x=x,
            y=y,
            snr=self.DEFAULT_SNR + random.uniform(-5, 10),
            mass=1000 + random.uniform(-200, 500),
            is_locked=True,
        )

        logger.info(f"MockGuider selected star at ({x}, {y}), SNR={self._guide_star.snr:.1f}")
        return True

    async def auto_select_star(self) -> bool:
        """
        Automatically select the best guide star.

        Returns:
            True if star selected successfully
        """
        if not self.is_connected:
            raise RuntimeError("Guider not connected")

        if self.simulate_delays:
            await asyncio.sleep(0.3)

        # Simulate auto selection
        x = random.uniform(100, 900)
        y = random.uniform(100, 700)

        return await self.select_star(x, y)

    async def calibrate(self) -> bool:
        """
        Run guider calibration.

        Returns:
            True if calibration successful
        """
        if not self.is_connected:
            raise RuntimeError("Guider not connected")

        if self._inject_calibrate_error:
            raise RuntimeError("Mock: Simulated calibration failure")

        self._state = MockGuiderState.CALIBRATING
        logger.info("MockGuider calibration started")

        if self.simulate_delays:
            # Calibration takes ~60 seconds typically
            await asyncio.sleep(2.0)

        self._is_calibrated = True
        self._state = MockGuiderState.CONNECTED
        logger.info("MockGuider calibration complete")
        return True

    async def start_guiding(self) -> bool:
        """
        Start guiding.

        Returns:
            True if guiding started
        """
        if not self.is_connected:
            raise RuntimeError("Guider not connected")

        if not self._is_calibrated:
            raise RuntimeError("Guider not calibrated")

        if not self._guide_star:
            raise RuntimeError("No guide star selected")

        if self._inject_guide_error:
            raise RuntimeError("Mock: Simulated guiding failure")

        self._state = MockGuiderState.GUIDING
        self._stats = GuideStats()

        # Start background guiding simulation
        self._guide_task = asyncio.create_task(self._simulate_guiding())

        logger.info("MockGuider guiding started")
        return True

    async def stop_guiding(self):
        """Stop guiding."""
        if self._guide_task and not self._guide_task.done():
            self._guide_task.cancel()
            try:
                await self._guide_task
            except asyncio.CancelledError:
                pass

        if self._state in {MockGuiderState.GUIDING, MockGuiderState.SETTLING}:
            self._state = MockGuiderState.STOPPED
            logger.info("MockGuider guiding stopped")

    async def _simulate_guiding(self):
        """Simulate guiding in background."""
        frame_interval = 2.0  # 2-second exposure typical

        while self._state == MockGuiderState.GUIDING:
            try:
                if self.simulate_delays:
                    await asyncio.sleep(frame_interval)

                # Check for star lost injection
                if self._inject_star_lost:
                    if self._guide_star:
                        self._guide_star.is_locked = False
                    self._state = MockGuiderState.ERROR
                    logger.error("MockGuider: Guide star lost")
                    break

                # Generate simulated guide stats
                self._update_guide_stats()

                # Notify callbacks
                for callback in self._guide_callbacks:
                    try:
                        callback(self._stats)
                    except Exception as e:
                        logger.error(f"Guide callback error: {e}")

            except asyncio.CancelledError:
                break

    def _update_guide_stats(self):
        """Update guiding statistics with simulated values."""
        # Add some randomness to RMS
        rms_variation = random.uniform(-0.2, 0.2)
        base = self.base_rms + rms_variation

        # RA typically has more error than Dec
        self._stats.rms_ra_arcsec = base * random.uniform(0.8, 1.2)
        self._stats.rms_dec_arcsec = base * random.uniform(0.6, 1.0)
        self._stats.rms_total_arcsec = (
            (self._stats.rms_ra_arcsec ** 2 + self._stats.rms_dec_arcsec ** 2) ** 0.5
        )

        # Peak values
        self._stats.peak_ra_arcsec = self._stats.rms_ra_arcsec * random.uniform(2.0, 3.5)
        self._stats.peak_dec_arcsec = self._stats.rms_dec_arcsec * random.uniform(2.0, 3.5)

        # SNR and star mass
        if self._guide_star:
            self._stats.snr = self._guide_star.snr + random.uniform(-2, 2)
            self._stats.star_mass = self._guide_star.mass + random.uniform(-50, 50)

        self._stats.frame_count += 1
        self._stats.timestamp = datetime.now()

    def get_stats(self) -> GuideStats:
        """Get current guiding statistics."""
        return self._stats

    def get_guide_star(self) -> Optional[GuideStar]:
        """Get selected guide star info."""
        return self._guide_star

    async def dither(self, pixels: float = 5.0, settle_timeout: float = 60.0) -> bool:
        """
        Dither the guide star position.

        Args:
            pixels: Dither amount in pixels
            settle_timeout: Maximum time to wait for settling

        Returns:
            True if dither and settle completed
        """
        if not self.is_guiding:
            raise RuntimeError("Not currently guiding")

        self._dither_pixels = pixels
        self._is_settling = True
        self._state = MockGuiderState.SETTLING

        logger.info(f"MockGuider dithering {pixels} pixels")

        if self.simulate_delays:
            # Simulate settling time (5-15 seconds typical)
            settle_time = random.uniform(3.0, 10.0)
            await asyncio.sleep(min(settle_time, settle_timeout))

        self._is_settling = False
        self._state = MockGuiderState.GUIDING

        # Notify settle callbacks
        for callback in self._settle_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Settle callback error: {e}")

        logger.info("MockGuider dither settled")
        return True

    async def pause(self):
        """Pause guiding."""
        if self._state == MockGuiderState.GUIDING:
            self._state = MockGuiderState.STOPPED
            logger.info("MockGuider paused")

    async def resume(self):
        """Resume guiding."""
        if self._state == MockGuiderState.STOPPED and self._is_calibrated:
            self._state = MockGuiderState.GUIDING
            logger.info("MockGuider resumed")

    def set_guide_callback(self, callback: Callable):
        """Register callback for guide frame updates."""
        self._guide_callbacks.append(callback)

    def set_settle_callback(self, callback: Callable):
        """Register callback for dither settle completion."""
        self._settle_callbacks.append(callback)

    # Error injection
    def inject_connect_error(self, enable: bool = True):
        """Enable/disable connection error injection."""
        self._inject_connect_error = enable

    def inject_calibrate_error(self, enable: bool = True):
        """Enable/disable calibration error injection."""
        self._inject_calibrate_error = enable

    def inject_guide_error(self, enable: bool = True):
        """Enable/disable guiding error injection."""
        self._inject_guide_error = enable

    def inject_star_lost(self, enable: bool = True):
        """Enable/disable star lost injection."""
        self._inject_star_lost = enable

    def set_rms(self, rms_arcsec: float):
        """Set base RMS for simulation."""
        self.base_rms = rms_arcsec

    def reset(self):
        """Reset mock to initial state."""
        self._state = MockGuiderState.DISCONNECTED
        self._stats = GuideStats()
        self._guide_star = None
        self._is_calibrated = False
        self._is_settling = False
        self._inject_connect_error = False
        self._inject_calibrate_error = False
        self._inject_guide_error = False
        self._inject_star_lost = False
