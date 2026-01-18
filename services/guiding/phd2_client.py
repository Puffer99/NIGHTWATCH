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
            # Update guide stats
            self._last_stats = GuideStats(
                timestamp=datetime.now(),
                state=self._state,
                rms_total=event.get("RADistanceRaw", 0) ** 2 + event.get("DECDistanceRaw", 0) ** 2,
                rms_ra=abs(event.get("RADistanceRaw", 0)),
                rms_dec=abs(event.get("DECDistanceRaw", 0)),
                peak_ra=0,  # Would calculate from history
                peak_dec=0,
                snr=event.get("SNR", 0),
                star_mass=event.get("StarMass", 0),
                frame_number=event.get("Frame", 0)
            )

        elif event_type == "AppState":
            state_str = event.get("State", "Stopped")
            try:
                self._state = GuideState(state_str)
            except ValueError:
                self._state = GuideState.STOPPED

        elif event_type == "GuidingDithered":
            logger.debug("Dither complete")

        elif event_type == "StarLost":
            logger.warning("Guide star lost!")
            self._state = GuideState.LOST_LOCK

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
                     settle_pixels: float = 1.0, settle_time: float = 10.0) -> bool:
        """
        Dither the guide position.

        Args:
            pixels: Dither amount in pixels
            ra_only: Only dither in RA direction
            settle_pixels: Settle threshold
            settle_time: Settle duration

        Returns:
            True if dither initiated successfully
        """
        try:
            await self._send_request("dither", {
                "amount": pixels,
                "raOnly": ra_only,
                "settle": {
                    "pixels": settle_pixels,
                    "time": settle_time,
                    "timeout": 60.0
                }
            })
            logger.debug(f"Dithered {pixels} pixels")
            return True
        except Exception as e:
            logger.error(f"Failed to dither: {e}")
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
