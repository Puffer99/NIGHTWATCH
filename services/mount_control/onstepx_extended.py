"""
OnStepX Extended Command Interface

This module provides extended OnStepX commands beyond the standard LX200 protocol,
including Periodic Error Correction (PEC), driver diagnostics, and tracking rate
fine-tuning.

These extended commands are specific to OnStepX firmware and enable advanced
mount control features for high-precision tracking.

Reference: https://github.com/hjd1964/OnStepX-Plugins
"""

import logging
from dataclasses import dataclass
from typing import Optional

from .lx200 import LX200Client, ConnectionType

logger = logging.getLogger(__name__)


@dataclass
class PECStatus:
    """Periodic Error Correction status."""

    recording: bool  # Currently recording PEC data
    playing: bool  # PEC playback active
    ready: bool  # PEC data available and ready
    index_detected: bool  # Worm gear index sensor detected
    record_progress: float  # Recording progress (0.0-1.0)


@dataclass
class DriverStatus:
    """TMC stepper driver status (TMC5160/TMC2130)."""

    axis: int  # Axis number (1=RA, 2=DEC)
    standstill: bool  # Motor at standstill
    open_load_a: bool  # Open load on coil A
    open_load_b: bool  # Open load on coil B
    short_to_ground_a: bool  # Short to ground on coil A
    short_to_ground_b: bool  # Short to ground on coil B
    overtemperature: bool  # Driver overtemperature warning
    overtemperature_pre: bool  # Driver overtemperature pre-warning
    stallguard: bool  # StallGuard triggered (stall detected)
    current_ma: Optional[int]  # Motor current in mA


class OnStepXExtended(LX200Client):
    """
    Extended OnStepX commands beyond standard LX200.

    Provides access to OnStepX-specific features including:
    - Periodic Error Correction (PEC) recording and playback
    - TMC stepper driver diagnostics
    - Tracking rate fine-tuning
    - Extended status information

    Example:
        >>> mount = OnStepXExtended(host="192.168.1.100")
        >>> mount.connect()
        >>> status = await mount.pec_status()
        >>> if status.ready:
        ...     await mount.pec_start_playback()
    """

    # PEC Commands
    CMD_PEC_STATUS = "$QZ"
    CMD_PEC_PLAY = "$QZ+"
    CMD_PEC_STOP = "$QZ-"
    CMD_PEC_RECORD = "$QZR"
    CMD_PEC_CLEAR = "$QZC"
    CMD_PEC_WRITE_EEPROM = "$QZW"
    CMD_PEC_READ_EEPROM = "$QZR"

    # Extended Status Commands
    CMD_GET_DRIVER_STATUS = "GXU"
    CMD_GET_EXTENDED_STATUS = "GX"

    # Tracking Rate Commands
    CMD_SET_TRACKING_OFFSET = "ST"

    def __init__(
        self,
        connection_type: ConnectionType = ConnectionType.TCP,
        host: str = "192.168.1.100",
        port: int = 9999,
        serial_port: str = "/dev/ttyUSB0",
        baudrate: int = 9600,
    ):
        """
        Initialize OnStepX Extended client.

        Args:
            connection_type: TCP or Serial connection
            host: IP address for TCP connection
            port: Port number for TCP connection
            serial_port: Serial port path
            baudrate: Serial baud rate
        """
        super().__init__(
            connection_type=connection_type,
            host=host,
            port=port,
            serial_port=serial_port,
            baudrate=baudrate,
        )

    # =========================================================================
    # PERIODIC ERROR CORRECTION (PEC)
    # =========================================================================

    async def pec_status(self) -> PECStatus:
        """
        Get PEC recording/playback status.

        Returns:
            PECStatus with current PEC state
        """
        response = self._send_command(self.CMD_PEC_STATUS)

        # Parse PEC status response
        # OnStepX returns: I = Index detected, R = Recording, P = Playing, r = Ready
        recording = False
        playing = False
        ready = False
        index_detected = False
        record_progress = 0.0

        if response:
            recording = "R" in response
            playing = "P" in response
            ready = "r" in response.lower() or "R" not in response and "P" not in response
            index_detected = "I" in response

            # Get recording progress if recording
            if recording:
                progress_response = self._send_command("$QZ?")
                if progress_response:
                    try:
                        record_progress = float(progress_response) / 100.0
                    except ValueError:
                        pass

        logger.debug(
            f"PEC status: recording={recording}, playing={playing}, "
            f"ready={ready}, index={index_detected}"
        )

        return PECStatus(
            recording=recording,
            playing=playing,
            ready=ready,
            index_detected=index_detected,
            record_progress=record_progress,
        )

    async def pec_start_playback(self) -> bool:
        """
        Start PEC playback.

        PEC must be trained (ready) before playback can start.

        Returns:
            True if playback started successfully
        """
        response = self._send_command(self.CMD_PEC_PLAY)
        success = response == "1"

        if success:
            logger.info("PEC playback started")
        else:
            logger.warning(f"Failed to start PEC playback: {response}")

        return success

    async def pec_stop(self) -> bool:
        """
        Stop PEC recording or playback.

        Returns:
            True if stopped successfully
        """
        response = self._send_command(self.CMD_PEC_STOP)
        success = response == "1"

        if success:
            logger.info("PEC stopped")
        else:
            logger.warning(f"Failed to stop PEC: {response}")

        return success

    async def pec_record(self) -> bool:
        """
        Start PEC recording for one worm period.

        Recording captures the periodic error of the worm gear over
        one complete rotation. The mount should be tracking a star
        with autoguiding providing corrections during recording.

        Returns:
            True if recording started successfully
        """
        response = self._send_command(self.CMD_PEC_RECORD)
        success = response == "1"

        if success:
            logger.info("PEC recording started")
        else:
            logger.warning(f"Failed to start PEC recording: {response}")

        return success

    async def pec_clear(self) -> bool:
        """
        Clear PEC data from memory.

        Returns:
            True if cleared successfully
        """
        response = self._send_command(self.CMD_PEC_CLEAR)
        success = response == "1"

        if success:
            logger.info("PEC data cleared")

        return success

    async def pec_save_to_eeprom(self) -> bool:
        """
        Save PEC data to EEPROM for persistence across power cycles.

        Returns:
            True if saved successfully
        """
        response = self._send_command(self.CMD_PEC_WRITE_EEPROM)
        success = response == "1"

        if success:
            logger.info("PEC data saved to EEPROM")
        else:
            logger.warning("Failed to save PEC data to EEPROM")

        return success

    # =========================================================================
    # DRIVER DIAGNOSTICS
    # =========================================================================

    async def get_driver_status(self, axis: int = 1) -> DriverStatus:
        """
        Get TMC stepper driver status.

        Reads diagnostic information from the TMC5160/TMC2130 driver
        including fault conditions and current settings.

        Args:
            axis: Axis number (1=RA/Az, 2=DEC/Alt)

        Returns:
            DriverStatus with driver diagnostic information
        """
        # OnStepX extended command for driver diagnostics
        response = self._send_command(f"{self.CMD_GET_DRIVER_STATUS}{axis}")

        # Default values
        status_flags = 0
        current_ma = None

        if response:
            try:
                # Response is hex status flags
                status_flags = int(response, 16)
            except ValueError:
                logger.warning(f"Failed to parse driver status: {response}")

        # Parse TMC5160 status flags (DRV_STATUS register)
        # Reference: TMC5160 datasheet
        return DriverStatus(
            axis=axis,
            standstill=bool(status_flags & 0x80000000),  # Bit 31
            open_load_a=bool(status_flags & 0x40000000),  # Bit 30
            open_load_b=bool(status_flags & 0x20000000),  # Bit 29
            short_to_ground_a=bool(status_flags & 0x10000000),  # Bit 28
            short_to_ground_b=bool(status_flags & 0x08000000),  # Bit 27
            overtemperature=bool(status_flags & 0x04000000),  # Bit 26
            overtemperature_pre=bool(status_flags & 0x02000000),  # Bit 25
            stallguard=bool(status_flags & 0x01000000),  # Bit 24
            current_ma=current_ma,
        )

    async def get_all_driver_status(self) -> dict:
        """
        Get driver status for both axes.

        Returns:
            Dictionary with axis1 and axis2 DriverStatus
        """
        axis1 = await self.get_driver_status(1)
        axis2 = await self.get_driver_status(2)

        return {
            "axis1_ra": axis1,
            "axis2_dec": axis2,
        }

    # =========================================================================
    # TRACKING RATE FINE-TUNING
    # =========================================================================

    async def set_tracking_offset(self, offset_ppm: float) -> bool:
        """
        Fine-tune tracking rate in parts-per-million.

        This allows for refraction correction or compensation for
        non-sidereal tracking rates.

        Args:
            offset_ppm: Tracking rate offset in parts per million
                       Positive = faster, Negative = slower

        Returns:
            True if offset applied successfully
        """
        # Format offset with sign and 4 decimal places
        cmd = f"{self.CMD_SET_TRACKING_OFFSET}{offset_ppm:+.4f}"
        response = self._send_command(cmd)
        success = response == "1"

        if success:
            logger.info(f"Tracking offset set to {offset_ppm:+.4f} ppm")
        else:
            logger.warning(f"Failed to set tracking offset: {response}")

        return success

    async def get_tracking_offset(self) -> Optional[float]:
        """
        Get current tracking rate offset.

        Returns:
            Current offset in ppm, or None if unavailable
        """
        response = self._send_command("GT")
        if response:
            try:
                return float(response)
            except ValueError:
                pass
        return None

    # =========================================================================
    # EXTENDED STATUS
    # =========================================================================

    async def get_mount_errors(self) -> dict:
        """
        Get mount error counts and status.

        Returns:
            Dictionary with error information
        """
        errors = {
            "slew_aborts": 0,
            "limit_errors": 0,
            "tracking_errors": 0,
            "driver_faults": 0,
        }

        # Query extended error status
        response = self._send_command("GXE")
        if response:
            # Parse error response (format varies by OnStepX version)
            try:
                parts = response.split(",")
                if len(parts) >= 4:
                    errors["slew_aborts"] = int(parts[0])
                    errors["limit_errors"] = int(parts[1])
                    errors["tracking_errors"] = int(parts[2])
                    errors["driver_faults"] = int(parts[3])
            except (ValueError, IndexError):
                pass

        return errors

    async def get_motor_temperature(self, axis: int = 1) -> Optional[float]:
        """
        Get motor temperature if sensor available.

        Args:
            axis: Axis number (1 or 2)

        Returns:
            Temperature in Celsius, or None if unavailable
        """
        response = self._send_command(f"GXT{axis}")
        if response:
            try:
                return float(response)
            except ValueError:
                pass
        return None

    # =========================================================================
    # RETICLE CONTROL
    # =========================================================================

    async def set_reticle_brightness(self, level: int) -> bool:
        """
        Set reticle LED brightness for visual observation.

        Args:
            level: Brightness level 0-255 (0=off, 255=max)

        Returns:
            True if set successfully
        """
        level = max(0, min(255, level))
        response = self._send_command(f"rc{level:03d}")
        return response == "1"

    async def toggle_reticle(self) -> bool:
        """
        Toggle reticle on/off.

        Returns:
            True if toggled successfully
        """
        response = self._send_command("rC")
        return response == "1"


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================


def create_onstepx_extended(
    host: str = "192.168.1.100",
    port: int = 9999,
    use_tcp: bool = True,
    serial_port: str = "/dev/ttyUSB0",
) -> OnStepXExtended:
    """
    Create OnStepXExtended client with convenient defaults.

    Args:
        host: IP address for TCP connection
        port: Port number for TCP connection
        use_tcp: Use TCP if True, serial if False
        serial_port: Serial port path (if use_tcp=False)

    Returns:
        Configured OnStepXExtended instance
    """
    connection_type = ConnectionType.TCP if use_tcp else ConnectionType.SERIAL

    return OnStepXExtended(
        connection_type=connection_type,
        host=host,
        port=port,
        serial_port=serial_port,
    )


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    import asyncio

    async def test_onstepx():
        print("OnStepX Extended Command Test\n")

        mount = create_onstepx_extended(host="192.168.1.100")

        if mount.connect():
            print(f"Firmware: {mount.get_firmware_info()}")
            print(f"Version: {mount.get_firmware_version()}")
            print()

            # Test PEC status
            print("PEC Status:")
            pec = await mount.pec_status()
            print(f"  Recording: {pec.recording}")
            print(f"  Playing: {pec.playing}")
            print(f"  Ready: {pec.ready}")
            print(f"  Index detected: {pec.index_detected}")
            print()

            # Test driver status
            print("Driver Status (Axis 1 - RA):")
            driver = await mount.get_driver_status(1)
            print(f"  Standstill: {driver.standstill}")
            print(f"  Open load A: {driver.open_load_a}")
            print(f"  Open load B: {driver.open_load_b}")
            print(f"  Overtemperature: {driver.overtemperature}")
            print(f"  StallGuard: {driver.stallguard}")
            print()

            # Get tracking offset
            offset = await mount.get_tracking_offset()
            print(f"Tracking offset: {offset} ppm")

            mount.disconnect()
        else:
            print("Failed to connect to mount")

    asyncio.run(test_onstepx())
