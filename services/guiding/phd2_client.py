"""
NIGHTWATCH PHD2 Guiding Client
Socket Server Integration

POS Panel v2.0 - Day 11 Recommendations (Craig Stark):
- Use PHD2's socket server for automation integration
- JSON-RPC protocol over TCP (port 4400)
- Auto-select guide star after GOTO
- Monitor RMS and alert on degradation
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, List, Any

logger = logging.getLogger("NIGHTWATCH.Guiding")


class GuideState(Enum):
    """PHD2 guiding states."""
    STOPPED = "Stopped"
    SELECTED = "Selected"
    CALIBRATING = "Calibrating"
    GUIDING = "Guiding"
    LOST_LOCK = "LostLock"
    PAUSED = "Paused"
    LOOPING = "Looping"


@dataclass
class GuideStats:
    """Current guiding statistics."""
    timestamp: datetime
    state: GuideState
    rms_total: float          # Total RMS in arcsec
    rms_ra: float             # RA RMS in arcsec
    rms_dec: float            # DEC RMS in arcsec
    peak_ra: float            # Peak RA error
    peak_dec: float           # Peak DEC error
    snr: float                # Signal-to-noise ratio
    star_mass: float          # Guide star brightness
    frame_number: int         # Current frame


@dataclass
class CalibrationData:
    """PHD2 calibration data."""
    timestamp: datetime
    ra_rate: float            # RA rate in arcsec/sec
    dec_rate: float           # DEC rate in arcsec/sec
    ra_angle: float           # RA axis angle in degrees
    dec_angle: float          # DEC axis angle in degrees
    orthogonality: float      # Axis orthogonality error
    valid: bool = True


@dataclass
class GuideStar:
    """Selected guide star."""
    x: float                  # X position in pixels
    y: float                  # Y position in pixels
    snr: float                # Signal-to-noise ratio


class PHD2Client:
    """
    PHD2 Socket Server Client for NIGHTWATCH.

    Implements JSON-RPC protocol for guiding control and monitoring.
    Based on PHD2 server interface specification.

    Usage:
        client = PHD2Client()
        await client.connect()
        await client.start_guiding()
        stats = await client.get_guide_stats()
        await client.stop_guiding()
    """

    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 4400

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        """
        Initialize PHD2 client.

        Args:
            host: PHD2 server hostname
            port: PHD2 server port (default 4400)
        """
        self.host = host
        self.port = port
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._request_id = 0
        self._callbacks: List[Callable] = []
        self._state = GuideState.STOPPED
        self._last_stats: Optional[GuideStats] = None
        self._calibration: Optional[CalibrationData] = None
        self._event_task: Optional[asyncio.Task] = None

        # Step 194, 195: Dither and settling tracking
        self._dither_in_progress: bool = False
        self._settling: bool = False
        self._settle_start_time: Optional[datetime] = None
        self._dither_settle_event = asyncio.Event()

        # Step 196: Guide star loss recovery
        self._star_lost: bool = False
        self._star_lost_time: Optional[datetime] = None
        self._star_lost_count: int = 0
        self._auto_recover_enabled: bool = True
        self._recovery_attempts: int = 0
        self._max_recovery_attempts: int = 3
        self._recovery_delay_sec: float = 2.0
        self._star_lost_callback: Optional[Callable] = None
        self._recovery_task: Optional[asyncio.Task] = None

        # Step 197: RMS trending and alerts
        self._rms_history: List[tuple] = []  # (timestamp, rms_total)
        self._rms_history_max_size: int = 1000
        self._rms_alert_threshold: float = 2.0  # arcsec
        self._rms_alert_callback: Optional[Callable] = None

    @property
    def connected(self) -> bool:
        """Check if connected to PHD2."""
        return self._connected

    @property
    def state(self) -> GuideState:
        """Current guiding state."""
        return self._state

    @property
    def last_stats(self) -> Optional[GuideStats]:
        """Most recent guiding statistics."""
        return self._last_stats

    async def connect(self) -> bool:
        """
        Connect to PHD2 socket server.

        Returns:
            True if connected successfully
        """
        try:
            self._reader, self._writer = await asyncio.open_connection(
                self.host, self.port
            )
            self._connected = True
            logger.info(f"Connected to PHD2 at {self.host}:{self.port}")

            # Start event listener
            self._event_task = asyncio.create_task(self._listen_events())

            return True

        except ConnectionRefusedError:
            logger.error(f"PHD2 not running at {self.host}:{self.port}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to PHD2: {e}")
            return False

    async def disconnect(self):
        """Disconnect from PHD2."""
        if self._event_task:
            self._event_task.cancel()
            try:
                await self._event_task
            except asyncio.CancelledError:
                pass

        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

        self._connected = False
        logger.info("Disconnected from PHD2")

    async def _send_request(self, method: str, params: Optional[dict] = None) -> Any:
        """
        Send JSON-RPC request to PHD2.

        Args:
            method: RPC method name
            params: Optional parameters

        Returns:
            Response result
        """
        if not self._connected or not self._writer:
            raise ConnectionError("Not connected to PHD2")

        self._request_id += 1
        request = {
            "method": method,
            "id": self._request_id
        }
        if params:
            request["params"] = params

        message = json.dumps(request) + "\r\n"
        self._writer.write(message.encode())
        await self._writer.drain()

        # Read response
        response_line = await self._reader.readline()
        response = json.loads(response_line.decode())

        if "error" in response:
            raise RuntimeError(f"PHD2 error: {response['error']}")

        return response.get("result")

    async def _listen_events(self):
        """Listen for PHD2 events."""
        try:
            while self._connected:
                line = await self._reader.readline()
                if not line:
                    break

                try:
                    event = json.loads(line.decode())
                    await self._handle_event(event)
                except json.JSONDecodeError:
                    continue

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Event listener error: {e}")

    async def _handle_event(self, event: dict):
        """Handle PHD2 event."""
        event_type = event.get("Event")

        if event_type == "GuideStep":
            # Calculate RMS
            ra_dist = event.get("RADistanceRaw", 0)
            dec_dist = event.get("DECDistanceRaw", 0)
            rms_total = (ra_dist ** 2 + dec_dist ** 2) ** 0.5

            # Update guide stats
            self._last_stats = GuideStats(
                timestamp=datetime.now(),
                state=self._state,
                rms_total=rms_total,
                rms_ra=abs(ra_dist),
                rms_dec=abs(dec_dist),
                peak_ra=0,  # Would calculate from history
                peak_dec=0,
                snr=event.get("SNR", 0),
                star_mass=event.get("StarMass", 0),
                frame_number=event.get("Frame", 0)
            )

            # Step 197: Track RMS history
            self._rms_history.append((datetime.now(), rms_total))
            if len(self._rms_history) > self._rms_history_max_size:
                self._rms_history = self._rms_history[-self._rms_history_max_size:]

            # Step 197: Check RMS alert threshold
            if rms_total > self._rms_alert_threshold and self._rms_alert_callback:
                try:
                    self._rms_alert_callback(rms_total, self._rms_alert_threshold)
                except Exception as e:
                    logger.error(f"RMS alert callback error: {e}")

        elif event_type == "AppState":
            state_str = event.get("State", "Stopped")
            try:
                self._state = GuideState(state_str)
            except ValueError:
                self._state = GuideState.STOPPED

        elif event_type == "GuidingDithered":
            # Step 194: Dither complete
            logger.debug("Dither complete, waiting for settle")
            self._dither_in_progress = False

        elif event_type == "Settling":
            # Step 195: Settling started
            self._settling = True
            self._settle_start_time = datetime.now()
            logger.debug("Guiding settling...")

        elif event_type == "SettleDone":
            # Step 195: Settling complete
            self._settling = False
            settle_status = event.get("Status", 0)
            if settle_status == 0:
                logger.debug("Settle complete - guiding stable")
                self._dither_settle_event.set()
            else:
                logger.warning(f"Settle failed with status {settle_status}")
            self._settle_start_time = None

        elif event_type == "StarLost":
            logger.warning("Guide star lost!")
            self._state = GuideState.LOST_LOCK
            self._star_lost = True
            self._star_lost_time = datetime.now()
            self._star_lost_count += 1

            # Notify callback
            if self._star_lost_callback:
                try:
                    self._star_lost_callback(self._star_lost_count)
                except Exception as e:
                    logger.error(f"Star lost callback error: {e}")

            # Trigger auto-recovery if enabled
            if self._auto_recover_enabled and not self._recovery_task:
                self._recovery_task = asyncio.create_task(self._auto_recover_star())

        elif event_type == "StarSelected":
            # Star was reselected (manually or via recovery)
            logger.info("Guide star selected")
            self._star_lost = False
            self._recovery_attempts = 0
            if self._recovery_task:
                self._recovery_task.cancel()
                self._recovery_task = None

        # Notify callbacks
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def register_callback(self, callback: Callable):
        """Register callback for PHD2 events."""
        self._callbacks.append(callback)

    # =========================================================================
    # GUIDING CONTROL
    # =========================================================================

    async def start_guiding(self, settle_pixels: float = 1.0,
                           settle_time: float = 10.0,
                           settle_timeout: float = 60.0) -> bool:
        """
        Start autoguiding.

        Args:
            settle_pixels: Maximum settle distance in pixels
            settle_time: Time to remain settled (seconds)
            settle_timeout: Maximum time to wait for settle (seconds)

        Returns:
            True if guiding started successfully
        """
        try:
            result = await self._send_request("guide", {
                "settle": {
                    "pixels": settle_pixels,
                    "time": settle_time,
                    "timeout": settle_timeout
                },
                "recalibrate": False
            })
            logger.info("Autoguiding started")
            return result == 0
        except Exception as e:
            logger.error(f"Failed to start guiding: {e}")
            return False

    async def stop_guiding(self) -> bool:
        """
        Stop autoguiding.

        Returns:
            True if stopped successfully
        """
        try:
            await self._send_request("stop_capture")
            logger.info("Autoguiding stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop guiding: {e}")
            return False

    async def pause_guiding(self) -> bool:
        """Pause guiding (keep looping but don't send corrections)."""
        try:
            await self._send_request("set_paused", {"paused": True})
            return True
        except Exception as e:
            logger.error(f"Failed to pause guiding: {e}")
            return False

    async def resume_guiding(self) -> bool:
        """Resume guiding after pause."""
        try:
            await self._send_request("set_paused", {"paused": False})
            return True
        except Exception as e:
            logger.error(f"Failed to resume guiding: {e}")
            return False

    async def dither(self, pixels: float = 5.0, ra_only: bool = False,
                     settle_pixels: float = 1.0, settle_time: float = 10.0,
                     settle_timeout: float = 60.0) -> bool:
        """
        Dither the guide position (Step 194).

        Args:
            pixels: Dither amount in pixels
            ra_only: Only dither in RA direction
            settle_pixels: Settle threshold
            settle_time: Settle duration
            settle_timeout: Maximum settle wait time

        Returns:
            True if dither initiated successfully
        """
        try:
            self._dither_in_progress = True
            await self._send_request("dither", {
                "amount": pixels,
                "raOnly": ra_only,
                "settle": {
                    "pixels": settle_pixels,
                    "time": settle_time,
                    "timeout": settle_timeout
                }
            })
            logger.debug(f"Dithered {pixels} pixels")
            return True
        except Exception as e:
            self._dither_in_progress = False
            logger.error(f"Failed to dither: {e}")
            return False

    async def dither_and_wait(self, pixels: float = 5.0, ra_only: bool = False,
                              settle_pixels: float = 1.0, settle_time: float = 10.0,
                              settle_timeout: float = 60.0) -> bool:
        """
        Dither and wait for guiding to settle (Step 194).

        This is the recommended method for imaging workflows as it
        blocks until guiding is stable after the dither.

        Args:
            pixels: Dither amount in pixels
            ra_only: Only dither in RA direction
            settle_pixels: Settle threshold
            settle_time: Settle duration
            settle_timeout: Maximum settle wait time

        Returns:
            True if dither and settle completed successfully
        """
        # Clear the settle event
        self._dither_settle_event.clear()

        # Initiate dither
        if not await self.dither(pixels, ra_only, settle_pixels, settle_time, settle_timeout):
            return False

        # Wait for settle
        try:
            await asyncio.wait_for(
                self._dither_settle_event.wait(),
                timeout=settle_timeout
            )
            logger.info(f"Dither of {pixels} pixels complete and settled")
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Dither settle timeout after {settle_timeout}s")
            return False

    # =========================================================================
    # STAR SELECTION
    # =========================================================================

    async def auto_select_star(self) -> Optional[GuideStar]:
        """
        Automatically select best guide star.

        Returns:
            Selected guide star info
        """
        try:
            result = await self._send_request("find_star")
            if result:
                return GuideStar(
                    x=result.get("x", 0),
                    y=result.get("y", 0),
                    snr=0  # Not provided by find_star
                )
            return None
        except Exception as e:
            logger.error(f"Failed to auto-select star: {e}")
            return None

    async def set_guide_star(self, x: float, y: float) -> bool:
        """
        Manually set guide star position.

        Args:
            x: X position in pixels
            y: Y position in pixels

        Returns:
            True if star set successfully
        """
        try:
            await self._send_request("set_lock_position", {
                "x": x,
                "y": y,
                "exact": True
            })
            return True
        except Exception as e:
            logger.error(f"Failed to set guide star: {e}")
            return False

    # =========================================================================
    # CALIBRATION
    # =========================================================================

    async def calibrate(self) -> bool:
        """
        Run calibration.

        Returns:
            True if calibration started
        """
        try:
            await self._send_request("guide", {
                "recalibrate": True,
                "settle": {
                    "pixels": 1.0,
                    "time": 10.0,
                    "timeout": 120.0
                }
            })
            return True
        except Exception as e:
            logger.error(f"Failed to start calibration: {e}")
            return False

    async def clear_calibration(self) -> bool:
        """Clear current calibration."""
        try:
            await self._send_request("clear_calibration", {"which": "both"})
            return True
        except Exception as e:
            logger.error(f"Failed to clear calibration: {e}")
            return False

    async def get_calibration_data(self) -> Optional[CalibrationData]:
        """
        Get current calibration data.

        Returns:
            Calibration data if available
        """
        try:
            result = await self._send_request("get_calibration_data", {"which": "AO"})
            if result:
                return CalibrationData(
                    timestamp=datetime.now(),
                    ra_rate=result.get("xRate", 0),
                    dec_rate=result.get("yRate", 0),
                    ra_angle=result.get("xAngle", 0),
                    dec_angle=result.get("yAngle", 0),
                    orthogonality=abs(result.get("xAngle", 0) - result.get("yAngle", 0) - 90)
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get calibration: {e}")
            return None

    # =========================================================================
    # STATUS AND STATS
    # =========================================================================

    async def get_guide_stats(self) -> Optional[GuideStats]:
        """
        Get current guiding statistics.

        Returns:
            Current guide stats
        """
        # Return cached stats from event stream
        return self._last_stats

    async def get_app_state(self) -> GuideState:
        """Get PHD2 application state."""
        try:
            result = await self._send_request("get_app_state")
            return GuideState(result)
        except Exception:
            return GuideState.STOPPED

    async def get_pixel_scale(self) -> float:
        """Get guider pixel scale in arcsec/pixel."""
        try:
            result = await self._send_request("get_pixel_scale")
            return float(result)
        except Exception:
            return 0.0

    # =========================================================================
    # SETTLING DETECTION (Step 195)
    # =========================================================================

    @property
    def is_settling(self) -> bool:
        """Check if guiding is currently settling."""
        return self._settling

    async def wait_for_settle(self, timeout: float = 60.0) -> bool:
        """
        Wait for guiding to settle (Step 195).

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if settled, False if timeout
        """
        if not self._settling:
            return True  # Already settled

        self._dither_settle_event.clear()

        try:
            await asyncio.wait_for(
                self._dither_settle_event.wait(),
                timeout=timeout
            )
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Settle timeout after {timeout}s")
            return False

    def get_settle_status(self) -> dict:
        """
        Get current settle status (Step 195).

        Returns:
            Dict with settling information
        """
        elapsed = None
        if self._settle_start_time:
            elapsed = (datetime.now() - self._settle_start_time).total_seconds()

        return {
            "settling": self._settling,
            "settle_elapsed_sec": elapsed,
            "dither_in_progress": self._dither_in_progress,
        }

    # =========================================================================
    # RMS TRENDING AND ALERTS (Step 197)
    # =========================================================================

    def set_rms_alert_threshold(self, threshold_arcsec: float) -> None:
        """
        Set RMS alert threshold (Step 197).

        Args:
            threshold_arcsec: RMS threshold in arcseconds
        """
        self._rms_alert_threshold = threshold_arcsec
        logger.info(f"RMS alert threshold set to {threshold_arcsec} arcsec")

    def set_rms_alert_callback(self, callback: Optional[Callable]) -> None:
        """
        Set callback for RMS alerts (Step 197).

        Args:
            callback: Function(rms_value, threshold) called when RMS exceeds threshold
        """
        self._rms_alert_callback = callback

    def get_rms_history(self, limit: int = 100) -> List[tuple]:
        """
        Get recent RMS history (Step 197).

        Args:
            limit: Maximum number of samples to return

        Returns:
            List of (timestamp, rms_total) tuples, most recent last
        """
        return self._rms_history[-limit:]

    def get_rms_stats(self) -> dict:
        """
        Get RMS statistics (Step 197).

        Returns:
            Dict with RMS statistics
        """
        if not self._rms_history:
            return {
                "sample_count": 0,
                "avg_rms": None,
                "min_rms": None,
                "max_rms": None,
                "current_rms": None,
                "alert_threshold": self._rms_alert_threshold,
            }

        rms_values = [rms for _, rms in self._rms_history]
        return {
            "sample_count": len(rms_values),
            "avg_rms": sum(rms_values) / len(rms_values),
            "min_rms": min(rms_values),
            "max_rms": max(rms_values),
            "current_rms": rms_values[-1] if rms_values else None,
            "alert_threshold": self._rms_alert_threshold,
            "above_threshold_count": sum(1 for r in rms_values if r > self._rms_alert_threshold),
        }

    def get_rms_trend(self, window_size: int = 10) -> str:
        """
        Get RMS trend direction (Step 197).

        Args:
            window_size: Number of samples for trend calculation

        Returns:
            "improving", "degrading", or "stable"
        """
        if len(self._rms_history) < window_size * 2:
            return "unknown"

        # Compare average of first half vs second half
        recent = self._rms_history[-window_size:]
        older = self._rms_history[-window_size*2:-window_size]

        recent_avg = sum(r for _, r in recent) / len(recent)
        older_avg = sum(r for _, r in older) / len(older)

        # 10% threshold for trend detection
        if recent_avg < older_avg * 0.9:
            return "improving"
        elif recent_avg > older_avg * 1.1:
            return "degrading"
        else:
            return "stable"

    def clear_rms_history(self) -> int:
        """
        Clear RMS history (Step 197).

        Returns:
            Number of samples cleared
        """
        count = len(self._rms_history)
        self._rms_history.clear()
        return count

    # =========================================================================
    # GUIDE STAR LOSS RECOVERY (Step 196)
    # =========================================================================

    @property
    def star_lost(self) -> bool:
        """Check if guide star is currently lost."""
        return self._star_lost

    def enable_auto_recovery(self, enabled: bool = True) -> None:
        """
        Enable or disable automatic guide star recovery (Step 196).

        Args:
            enabled: Whether to automatically attempt recovery
        """
        self._auto_recover_enabled = enabled
        logger.info(f"Auto guide star recovery {'enabled' if enabled else 'disabled'}")

    def set_recovery_params(self, max_attempts: int = 3, delay_sec: float = 2.0) -> None:
        """
        Configure recovery parameters (Step 196).

        Args:
            max_attempts: Maximum recovery attempts before giving up
            delay_sec: Delay between recovery attempts
        """
        self._max_recovery_attempts = max_attempts
        self._recovery_delay_sec = delay_sec
        logger.info(f"Recovery params: max_attempts={max_attempts}, delay={delay_sec}s")

    def set_star_lost_callback(self, callback: Optional[Callable]) -> None:
        """
        Set callback for star lost events (Step 196).

        Args:
            callback: Function(loss_count) called when star is lost
        """
        self._star_lost_callback = callback

    async def _auto_recover_star(self) -> None:
        """
        Automatic guide star recovery routine (Step 196).

        Attempts to find and select a new guide star after star loss.
        """
        logger.info("Starting automatic guide star recovery...")

        while self._star_lost and self._recovery_attempts < self._max_recovery_attempts:
            self._recovery_attempts += 1
            logger.info(f"Recovery attempt {self._recovery_attempts}/{self._max_recovery_attempts}")

            # Wait before attempting recovery
            await asyncio.sleep(self._recovery_delay_sec)

            # Try to find a new star
            try:
                star = await self.auto_select_star()
                if star:
                    logger.info(f"Recovery: Found star at ({star.x:.1f}, {star.y:.1f})")

                    # Try to resume guiding
                    success = await self.start_guiding()
                    if success:
                        logger.info("Recovery successful - guiding resumed")
                        self._star_lost = False
                        break
                    else:
                        logger.warning("Recovery: Failed to restart guiding")
                else:
                    logger.warning("Recovery: No suitable guide star found")

            except asyncio.CancelledError:
                logger.info("Recovery cancelled")
                break
            except Exception as e:
                logger.error(f"Recovery error: {e}")

        if self._star_lost:
            logger.error(f"Guide star recovery failed after {self._recovery_attempts} attempts")

        self._recovery_task = None

    async def manual_recover_star(self) -> bool:
        """
        Manually trigger guide star recovery (Step 196).

        Returns:
            True if recovery successful
        """
        logger.info("Manual guide star recovery requested")

        # Cancel any existing auto-recovery
        if self._recovery_task:
            self._recovery_task.cancel()
            self._recovery_task = None

        self._recovery_attempts = 0

        # Try to find a new star
        star = await self.auto_select_star()
        if not star:
            logger.warning("Manual recovery: No guide star found")
            return False

        logger.info(f"Manual recovery: Found star at ({star.x:.1f}, {star.y:.1f})")

        # Resume guiding
        success = await self.start_guiding()
        if success:
            self._star_lost = False
            logger.info("Manual recovery successful")
        else:
            logger.warning("Manual recovery: Failed to start guiding")

        return success

    def get_star_loss_status(self) -> dict:
        """
        Get guide star loss status (Step 196).

        Returns:
            Dict with star loss information
        """
        lost_duration = None
        if self._star_lost_time and self._star_lost:
            lost_duration = (datetime.now() - self._star_lost_time).total_seconds()

        return {
            "star_lost": self._star_lost,
            "lost_duration_sec": lost_duration,
            "total_lost_count": self._star_lost_count,
            "recovery_attempts": self._recovery_attempts,
            "max_recovery_attempts": self._max_recovery_attempts,
            "auto_recover_enabled": self._auto_recover_enabled,
            "recovery_in_progress": self._recovery_task is not None,
        }

    def reset_star_loss_stats(self) -> None:
        """Reset star loss statistics (Step 196)."""
        self._star_lost_count = 0
        self._recovery_attempts = 0
        logger.info("Star loss stats reset")

    # =========================================================================
    # GUIDE LOG PARSING (Step 198)
    # =========================================================================

    @staticmethod
    def parse_guide_log(log_path: str) -> dict:
        """
        Parse a PHD2 guide log file (Step 198).

        PHD2 guide logs are CSV-like files with guiding data.
        Format: Frame, Time, mount, dx, dy, RARawDistance, DECRawDistance,
                RAGuideDistance, DECGuideDistance, RADuration, DECDuration,
                RADirection, DECDirection, XStep, YStep, StarMass, SNR, ErrorCode

        Args:
            log_path: Path to PHD2 guide log file

        Returns:
            Dict with parsed log data and statistics
        """
        from pathlib import Path
        import csv

        log_file = Path(log_path)
        if not log_file.exists():
            raise FileNotFoundError(f"Guide log not found: {log_path}")

        result = {
            "file": str(log_file),
            "header": {},
            "frames": [],
            "statistics": {},
        }

        frames = []
        header_section = True

        with open(log_file, 'r') as f:
            for line in f:
                line = line.strip()

                # Skip empty lines
                if not line:
                    continue

                # Parse header section (PHD2 metadata)
                if header_section:
                    if line.startswith("Frame,"):
                        # End of header, start of data
                        header_section = False
                        columns = line.split(",")
                        result["columns"] = columns
                        continue

                    # Parse header key-value pairs
                    if ":" in line or "=" in line:
                        sep = ":" if ":" in line else "="
                        parts = line.split(sep, 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip()
                            result["header"][key] = value
                    continue

                # Parse data rows
                try:
                    values = line.split(",")
                    if len(values) >= 7:
                        frame_data = {
                            "frame": int(values[0]) if values[0] else 0,
                            "time": float(values[1]) if values[1] else 0.0,
                            "ra_raw": float(values[5]) if len(values) > 5 and values[5] else 0.0,
                            "dec_raw": float(values[6]) if len(values) > 6 and values[6] else 0.0,
                            "snr": float(values[16]) if len(values) > 16 and values[16] else 0.0,
                            "star_mass": float(values[15]) if len(values) > 15 and values[15] else 0.0,
                        }
                        frames.append(frame_data)
                except (ValueError, IndexError):
                    continue

        result["frames"] = frames
        result["frame_count"] = len(frames)

        # Calculate statistics
        if frames:
            ra_values = [f["ra_raw"] for f in frames if f["ra_raw"] != 0]
            dec_values = [f["dec_raw"] for f in frames if f["dec_raw"] != 0]
            snr_values = [f["snr"] for f in frames if f["snr"] != 0]

            if ra_values:
                result["statistics"]["ra_rms"] = (sum(v**2 for v in ra_values) / len(ra_values)) ** 0.5
                result["statistics"]["ra_peak"] = max(abs(v) for v in ra_values)
                result["statistics"]["ra_mean"] = sum(ra_values) / len(ra_values)

            if dec_values:
                result["statistics"]["dec_rms"] = (sum(v**2 for v in dec_values) / len(dec_values)) ** 0.5
                result["statistics"]["dec_peak"] = max(abs(v) for v in dec_values)
                result["statistics"]["dec_mean"] = sum(dec_values) / len(dec_values)

            if ra_values and dec_values:
                # Total RMS
                total_sq = [ra**2 + dec**2 for ra, dec in zip(ra_values, dec_values)]
                result["statistics"]["total_rms"] = (sum(total_sq) / len(total_sq)) ** 0.5

            if snr_values:
                result["statistics"]["snr_mean"] = sum(snr_values) / len(snr_values)
                result["statistics"]["snr_min"] = min(snr_values)

            # Duration
            if len(frames) > 1:
                result["statistics"]["duration_sec"] = frames[-1]["time"] - frames[0]["time"]

        return result

    @staticmethod
    def analyze_guide_session(log_path: str) -> dict:
        """
        Analyze a complete guiding session from log (Step 198).

        Provides session-level analysis including:
        - Overall guiding quality assessment
        - Trend analysis (improving/degrading)
        - Problem detection (star loss events, high RMS periods)

        Args:
            log_path: Path to PHD2 guide log file

        Returns:
            Dict with session analysis
        """
        parsed = PHD2Client.parse_guide_log(log_path)

        analysis = {
            "file": parsed["file"],
            "frame_count": parsed["frame_count"],
            "statistics": parsed.get("statistics", {}),
            "quality": "unknown",
            "issues": [],
            "recommendations": [],
        }

        stats = parsed.get("statistics", {})

        # Quality assessment based on RMS
        total_rms = stats.get("total_rms", 0)
        if total_rms > 0:
            if total_rms < 0.5:
                analysis["quality"] = "excellent"
            elif total_rms < 1.0:
                analysis["quality"] = "good"
            elif total_rms < 2.0:
                analysis["quality"] = "acceptable"
            else:
                analysis["quality"] = "poor"
                analysis["issues"].append(f"High RMS: {total_rms:.2f} arcsec")
                analysis["recommendations"].append("Check polar alignment or balance")

        # Check for SNR issues
        snr_min = stats.get("snr_min", 0)
        if snr_min > 0 and snr_min < 5:
            analysis["issues"].append(f"Low SNR minimum: {snr_min:.1f}")
            analysis["recommendations"].append("Consider brighter guide star or longer exposure")

        # Analyze trend (first half vs second half)
        frames = parsed.get("frames", [])
        if len(frames) >= 20:
            mid = len(frames) // 2
            first_half = frames[:mid]
            second_half = frames[mid:]

            first_rms = sum(f["ra_raw"]**2 + f["dec_raw"]**2 for f in first_half) / len(first_half)
            second_rms = sum(f["ra_raw"]**2 + f["dec_raw"]**2 for f in second_half) / len(second_half)

            if second_rms > first_rms * 1.5:
                analysis["trend"] = "degrading"
                analysis["issues"].append("Guiding quality degraded during session")
            elif second_rms < first_rms * 0.7:
                analysis["trend"] = "improving"
            else:
                analysis["trend"] = "stable"

        return analysis

    async def get_guide_log_path(self) -> Optional[str]:
        """
        Get path to current guide log file (Step 198).

        Returns:
            Path to guide log or None if not available
        """
        try:
            result = await self._send_request("get_guide_output_filename")
            return result if result else None
        except Exception as e:
            logger.error(f"Failed to get guide log path: {e}")
            return None


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    async def test():
        print("NIGHTWATCH PHD2 Client Test\n")

        client = PHD2Client()

        print(f"Connecting to PHD2 at {client.host}:{client.port}...")
        if await client.connect():
            print("Connected!")

            state = await client.get_app_state()
            print(f"PHD2 State: {state.value}")

            pixel_scale = await client.get_pixel_scale()
            print(f"Pixel scale: {pixel_scale} arcsec/pixel")

            await client.disconnect()
        else:
            print("Failed to connect (is PHD2 running?)")

    asyncio.run(test())
