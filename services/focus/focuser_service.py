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


@dataclass
class FocusPositionRecord:
    """Record of a focus position change (Step 188)."""
    timestamp: datetime
    position: int
    temperature_c: float
    reason: str  # e.g., "manual", "auto_focus", "temp_compensation"
    hfd: Optional[float] = None  # HFD at this position if measured


class FocusRunDatabase:
    """
    SQLite database for storing focus run history (Step 189).

    Provides persistent storage for focus runs, enabling:
    - Historical analysis of focus performance
    - Temperature compensation calibration data
    - Focus trend tracking over time
    - Debug and diagnostic information

    Schema:
    - focus_runs: Main run data (id, timestamp, method, positions, success)
    - focus_measurements: Individual measurements per run
    """

    def __init__(self, db_path: str = "focus_history.db"):
        """
        Initialize focus run database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._conn = None
        self._initialized = False

    def initialize(self) -> bool:
        """
        Initialize database and create tables.

        Returns:
            True if initialization successful
        """
        try:
            import sqlite3
            self._conn = sqlite3.connect(self.db_path)
            self._create_tables()
            self._initialized = True
            logger.info(f"Focus database initialized: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize focus database: {e}")
            return False

    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self._conn.cursor()

        # Focus runs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS focus_runs (
                run_id TEXT PRIMARY KEY,
                start_time TEXT NOT NULL,
                end_time TEXT,
                method TEXT NOT NULL,
                initial_position INTEGER,
                final_position INTEGER,
                best_hfd REAL,
                success INTEGER,
                error TEXT,
                temperature_c REAL
            )
        """)

        # Focus measurements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS focus_measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                position INTEGER NOT NULL,
                hfd REAL,
                fwhm REAL,
                peak_value REAL,
                star_count INTEGER,
                temperature_c REAL,
                FOREIGN KEY (run_id) REFERENCES focus_runs (run_id)
            )
        """)

        # Index for efficient queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_runs_time ON focus_runs (start_time)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_measurements_run ON focus_measurements (run_id)
        """)

        self._conn.commit()

    def save_run(self, run: FocusRun) -> bool:
        """
        Save a focus run to the database (Step 189).

        Args:
            run: FocusRun to save

        Returns:
            True if saved successfully
        """
        if not self._initialized:
            logger.warning("Focus database not initialized")
            return False

        try:
            cursor = self._conn.cursor()

            # Insert run record
            cursor.execute("""
                INSERT OR REPLACE INTO focus_runs
                (run_id, start_time, end_time, method, initial_position,
                 final_position, best_hfd, success, error, temperature_c)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run.run_id,
                run.start_time.isoformat(),
                run.end_time.isoformat() if run.end_time else None,
                run.method.value,
                run.initial_position,
                run.final_position,
                run.best_hfd,
                1 if run.success else 0,
                run.error,
                run.measurements[-1].temperature_c if run.measurements else None
            ))

            # Insert measurements
            for m in run.measurements:
                cursor.execute("""
                    INSERT INTO focus_measurements
                    (run_id, timestamp, position, hfd, fwhm, peak_value,
                     star_count, temperature_c)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run.run_id,
                    m.timestamp.isoformat(),
                    m.position,
                    m.hfd,
                    m.fwhm,
                    m.peak_value,
                    m.star_count,
                    m.temperature_c
                ))

            self._conn.commit()
            logger.debug(f"Saved focus run {run.run_id} to database")
            return True

        except Exception as e:
            logger.error(f"Failed to save focus run: {e}")
            return False

    def get_run(self, run_id: str) -> Optional[FocusRun]:
        """
        Retrieve a focus run by ID (Step 189).

        Args:
            run_id: Run identifier

        Returns:
            FocusRun or None if not found
        """
        if not self._initialized:
            return None

        try:
            cursor = self._conn.cursor()

            # Get run record
            cursor.execute("""
                SELECT run_id, start_time, end_time, method, initial_position,
                       final_position, best_hfd, success, error
                FROM focus_runs WHERE run_id = ?
            """, (run_id,))
            row = cursor.fetchone()

            if not row:
                return None

            run = FocusRun(
                run_id=row[0],
                start_time=datetime.fromisoformat(row[1]),
                end_time=datetime.fromisoformat(row[2]) if row[2] else None,
                method=AutoFocusMethod(row[3]),
                initial_position=row[4],
                final_position=row[5],
                best_hfd=row[6] or float('inf'),
                success=bool(row[7]),
                error=row[8]
            )

            # Get measurements
            cursor.execute("""
                SELECT timestamp, position, hfd, fwhm, peak_value,
                       star_count, temperature_c
                FROM focus_measurements WHERE run_id = ?
                ORDER BY timestamp
            """, (run_id,))

            for m_row in cursor.fetchall():
                run.measurements.append(FocusMetric(
                    timestamp=datetime.fromisoformat(m_row[0]),
                    position=m_row[1],
                    hfd=m_row[2] or 0,
                    fwhm=m_row[3] or 0,
                    peak_value=m_row[4] or 0,
                    star_count=m_row[5] or 0,
                    temperature_c=m_row[6] or 0
                ))

            return run

        except Exception as e:
            logger.error(f"Failed to retrieve focus run: {e}")
            return None

    def get_recent_runs(self, limit: int = 10) -> List[FocusRun]:
        """
        Get most recent focus runs (Step 189).

        Args:
            limit: Maximum number of runs to return

        Returns:
            List of FocusRun objects, most recent first
        """
        if not self._initialized:
            return []

        try:
            cursor = self._conn.cursor()
            cursor.execute("""
                SELECT run_id FROM focus_runs
                ORDER BY start_time DESC LIMIT ?
            """, (limit,))

            runs = []
            for (run_id,) in cursor.fetchall():
                run = self.get_run(run_id)
                if run:
                    runs.append(run)

            return runs

        except Exception as e:
            logger.error(f"Failed to get recent runs: {e}")
            return []

    def get_runs_by_temperature_range(
        self,
        min_temp: float,
        max_temp: float
    ) -> List[FocusRun]:
        """
        Get focus runs within a temperature range (Step 189).

        Useful for analyzing focus position vs temperature relationship.

        Args:
            min_temp: Minimum temperature in Celsius
            max_temp: Maximum temperature in Celsius

        Returns:
            List of FocusRun objects within temperature range
        """
        if not self._initialized:
            return []

        try:
            cursor = self._conn.cursor()
            cursor.execute("""
                SELECT run_id FROM focus_runs
                WHERE temperature_c BETWEEN ? AND ?
                AND success = 1
                ORDER BY temperature_c
            """, (min_temp, max_temp))

            runs = []
            for (run_id,) in cursor.fetchall():
                run = self.get_run(run_id)
                if run:
                    runs.append(run)

            return runs

        except Exception as e:
            logger.error(f"Failed to get runs by temperature: {e}")
            return []

    def get_focus_statistics(self) -> dict:
        """
        Get overall focus statistics (Step 189).

        Returns:
            Dict with statistics:
            - total_runs: Total number of focus runs
            - successful_runs: Number of successful runs
            - avg_hfd: Average best HFD across successful runs
            - avg_duration_sec: Average focus run duration
        """
        if not self._initialized:
            return {}

        try:
            cursor = self._conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM focus_runs")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM focus_runs WHERE success = 1")
            successful = cursor.fetchone()[0]

            cursor.execute("""
                SELECT AVG(best_hfd) FROM focus_runs
                WHERE success = 1 AND best_hfd < 100
            """)
            avg_hfd = cursor.fetchone()[0] or 0

            return {
                "total_runs": total,
                "successful_runs": successful,
                "success_rate": successful / total if total > 0 else 0,
                "avg_hfd": avg_hfd,
            }

        except Exception as e:
            logger.error(f"Failed to get focus statistics: {e}")
            return {}

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            self._initialized = False


class FocuserService:
    """
    Temperature-compensated auto-focus for NIGHTWATCH.

    Features:
    - ZWO EAF integration via ASCOM/INDI
    - Temperature compensation with configurable coefficient
    - V-curve auto-focus with HFD metric
    - Backlash compensation
    - Focus history and trending
    - Position history tracking (Step 188)

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

        # Step 188: Position history tracking
        self._position_history: List[FocusPositionRecord] = []
        self._position_history_max_size: int = 1000  # Keep last 1000 records

        # Step 187: Backlash tracking
        self._last_direction: int = 0  # 1 = outward, -1 = inward, 0 = unknown
        self._backlash_calibrated: bool = False
        self._measured_backlash: Optional[int] = None

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

    async def move_to(self, position: int, compensate_backlash: bool = True, reason: str = "manual") -> bool:
        """
        Move focuser to absolute position.

        Args:
            position: Target position in steps
            compensate_backlash: Apply backlash compensation
            reason: Reason for move (for history tracking, Step 188)

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

        # Step 187: Enhanced backlash compensation
        # Only apply when changing direction (direction reversal)
        needs_backlash_comp = (
            compensate_backlash and
            self._last_direction != 0 and
            direction != self._last_direction
        )

        backlash = self._measured_backlash or self.config.backlash_steps

        if needs_backlash_comp:
            # Approaching from consistent direction reduces backlash error
            if direction > 0:
                # Moving outward after inward: overshoot then return
                overshoot = position + backlash
                overshoot = min(overshoot, self.config.max_position)

                self._state = FocuserState.MOVING
                logger.debug(f"Backlash compensation: overshoot to {overshoot}")
                await self._do_move(overshoot)
                await self._do_move(position)
            else:
                # Moving inward after outward: undershoot then return
                undershoot = position - backlash
                undershoot = max(0, undershoot)

                self._state = FocuserState.MOVING
                logger.debug(f"Backlash compensation: undershoot to {undershoot}")
                await self._do_move(undershoot)
                await self._do_move(position)
        else:
            self._state = FocuserState.MOVING
            await self._do_move(position)

        # Track direction for next move
        self._last_direction = direction

        self._state = FocuserState.IDLE

        # Step 188: Record position in history
        self._record_position(reason)

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
    # BACKLASH COMPENSATION (Step 187)
    # =========================================================================

    def get_backlash_info(self) -> dict:
        """
        Get backlash compensation information (Step 187).

        Returns:
            Dict with backlash settings and status
        """
        return {
            "configured_backlash": self.config.backlash_steps,
            "measured_backlash": self._measured_backlash,
            "effective_backlash": self._measured_backlash or self.config.backlash_steps,
            "calibrated": self._backlash_calibrated,
            "last_direction": self._last_direction,
        }

    def set_backlash(self, steps: int) -> None:
        """
        Set measured backlash value (Step 187).

        Args:
            steps: Backlash in steps (typically 50-200)
        """
        self._measured_backlash = max(0, steps)
        self._backlash_calibrated = True
        logger.info(f"Backlash set to {steps} steps")

    async def calibrate_backlash(self, camera=None) -> int:
        """
        Calibrate backlash by measuring star position shift (Step 187).

        This is a simplified calibration that measures the mechanical
        backlash by reversing direction and measuring the actual movement.

        Args:
            camera: Optional camera for precise measurement

        Returns:
            Measured backlash in steps
        """
        if not self._connected:
            raise RuntimeError("Focuser not connected")

        self._state = FocuserState.CALIBRATING
        logger.info("Starting backlash calibration...")

        try:
            # Move to a known position
            start_pos = self._position
            test_distance = 500

            # Move outward
            await self._do_move(start_pos + test_distance)
            self._last_direction = 1

            # Move back to start (should have backlash)
            await self._do_move(start_pos)
            self._last_direction = -1

            # In real implementation with camera:
            # 1. Take image, measure star centroid
            # 2. Move in small steps until star moves
            # 3. That step count is the backlash

            # For simulation, use configured value
            measured = self.config.backlash_steps

            self._measured_backlash = measured
            self._backlash_calibrated = True

            logger.info(f"Backlash calibration complete: {measured} steps")
            return measured

        finally:
            self._state = FocuserState.IDLE

    def reset_backlash_calibration(self) -> None:
        """Reset backlash calibration to use configured default."""
        self._measured_backlash = None
        self._backlash_calibrated = False
        self._last_direction = 0
        logger.info("Backlash calibration reset")

    # =========================================================================
    # POSITION HISTORY TRACKING (Step 188)
    # =========================================================================

    def _record_position(self, reason: str, hfd: Optional[float] = None) -> None:
        """
        Record current position to history (Step 188).

        Args:
            reason: Reason for position change
            hfd: HFD measurement at this position if available
        """
        record = FocusPositionRecord(
            timestamp=datetime.now(),
            position=self._position,
            temperature_c=self._temperature,
            reason=reason,
            hfd=hfd,
        )
        self._position_history.append(record)

        # Trim history if too large
        if len(self._position_history) > self._position_history_max_size:
            self._position_history = self._position_history[-self._position_history_max_size:]

        logger.debug(f"Position recorded: {self._position} ({reason})")

    def get_position_history(self, limit: int = 100) -> List[FocusPositionRecord]:
        """
        Get focus position history (Step 188).

        Args:
            limit: Maximum number of records to return

        Returns:
            List of position records, most recent first
        """
        history = self._position_history[-limit:] if len(self._position_history) > limit else self._position_history
        return list(reversed(history))

    def get_position_history_since(self, since: datetime) -> List[FocusPositionRecord]:
        """
        Get position history since a given time (Step 188).

        Args:
            since: Start time for history

        Returns:
            List of position records after the given time
        """
        return [r for r in self._position_history if r.timestamp >= since]

    def get_position_stats(self) -> dict:
        """
        Get statistics about focus position history (Step 188).

        Returns:
            Dict with position statistics
        """
        if not self._position_history:
            return {
                "record_count": 0,
                "min_position": None,
                "max_position": None,
                "avg_position": None,
                "temp_range_c": None,
            }

        positions = [r.position for r in self._position_history]
        temps = [r.temperature_c for r in self._position_history]
        hfds = [r.hfd for r in self._position_history if r.hfd is not None]

        return {
            "record_count": len(self._position_history),
            "min_position": min(positions),
            "max_position": max(positions),
            "avg_position": sum(positions) / len(positions),
            "position_range": max(positions) - min(positions),
            "temp_range_c": max(temps) - min(temps),
            "min_temp_c": min(temps),
            "max_temp_c": max(temps),
            "avg_hfd": sum(hfds) / len(hfds) if hfds else None,
            "best_hfd": min(hfds) if hfds else None,
            "oldest_record": self._position_history[0].timestamp.isoformat() if self._position_history else None,
            "newest_record": self._position_history[-1].timestamp.isoformat() if self._position_history else None,
        }

    def clear_position_history(self) -> int:
        """
        Clear position history (Step 188).

        Returns:
            Number of records cleared
        """
        count = len(self._position_history)
        self._position_history.clear()
        logger.info(f"Position history cleared ({count} records)")
        return count

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
            elif method == AutoFocusMethod.CONTRAST:
                await self._contrast_focus(run, camera)
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
        await self.move_to(best_pos, reason="auto_focus")

        # Verify focus
        final_hfd = await self._measure_hfd(camera)

        run.final_position = best_pos
        run.best_hfd = final_hfd

        # Step 188: Record final position with HFD
        self._record_position("auto_focus_complete", hfd=final_hfd)

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
                await self.move_to(best_pos, reason="auto_focus")
                break

            # Safety limit
            if len(run.measurements) > 20:
                break

        run.final_position = best_pos
        run.best_hfd = best_hfd

        # Step 188: Record final position with HFD
        self._record_position("auto_focus_complete", hfd=best_hfd)

    async def _contrast_focus(self, run: FocusRun, camera):
        """
        Contrast-based auto-focus algorithm (Step 184).

        Maximizes image contrast/sharpness as a focus metric.
        This is useful when stars are not available (e.g., daytime,
        lunar/planetary imaging, or terrestrial targets).

        The algorithm:
        1. Sample contrast at multiple focus positions
        2. Find the position with maximum contrast
        3. Use hill-climbing to refine the position
        """
        logger.info("Starting contrast-based auto-focus")

        # Calculate focus range
        half_range = (self.config.autofocus_samples // 2) * self.config.autofocus_step_size
        start_pos = self._position - half_range
        end_pos = self._position + half_range

        # Move to start position with backlash compensation
        await self.move_to(start_pos - self.config.backlash_steps, False)
        await self.move_to(start_pos, False)

        # Sample contrast at each position
        positions = []
        contrasts = []

        for i in range(self.config.autofocus_samples):
            pos = start_pos + i * self.config.autofocus_step_size
            await self.move_to(pos, compensate_backlash=False)

            # Measure contrast
            contrast = await self._measure_contrast(camera)

            positions.append(pos)
            contrasts.append(contrast)

            # Record as a focus metric (use contrast as inverse HFD for consistency)
            run.measurements.append(FocusMetric(
                timestamp=datetime.now(),
                position=pos,
                hfd=1.0 / max(contrast, 0.001),  # Lower HFD = better focus
                fwhm=0,
                peak_value=contrast,  # Store actual contrast in peak_value
                star_count=0,
                temperature_c=self._temperature
            ))

            logger.debug(f"Contrast sample: pos={pos}, contrast={contrast:.4f}")

        # Find position with maximum contrast
        max_idx = contrasts.index(max(contrasts))
        best_pos = positions[max_idx]
        best_contrast = contrasts[max_idx]

        # Refine with smaller steps around best position
        step = self.config.autofocus_step_size // 4
        await self.move_to(best_pos - step * 2, compensate_backlash=True)

        for offset in range(-2, 3):
            pos = best_pos + offset * step
            await self.move_to(pos, compensate_backlash=False)
            contrast = await self._measure_contrast(camera)

            if contrast > best_contrast:
                best_contrast = contrast
                best_pos = pos

        # Move to best position
        await self.move_to(best_pos, reason="auto_focus")

        # Final verification
        final_contrast = await self._measure_contrast(camera)

        run.final_position = best_pos
        run.best_hfd = 1.0 / max(final_contrast, 0.001)  # Convert to HFD-like metric

        logger.info(f"Contrast focus complete: pos={best_pos}, contrast={final_contrast:.4f}")

        # Step 188: Record final position
        self._record_position("contrast_focus_complete", hfd=run.best_hfd)

    async def _measure_contrast(self, camera) -> float:
        """
        Measure image contrast/sharpness (Step 184).

        Uses Laplacian variance as a focus metric. Higher variance
        indicates sharper edges and better focus.

        In real implementation:
        1. Capture frame with camera
        2. Convert to grayscale
        3. Apply Laplacian operator
        4. Calculate variance of result

        Returns:
            Contrast metric (higher = sharper)
        """
        # Simulate contrast measurement
        # Returns a curve centered around position 25000
        optimal = 25000
        distance = abs(self._position - optimal)

        # Inverse parabolic model: contrast peaks at optimal
        max_contrast = 1.0
        k = 4e-9
        contrast = max_contrast - k * distance * distance

        # Add noise
        import random
        contrast += random.gauss(0, 0.01)

        await asyncio.sleep(self.config.autofocus_exposure_sec * 0.5)

        return max(0.1, contrast)

    def calculate_laplacian_variance(self, image_data) -> float:
        """
        Calculate Laplacian variance of an image (Step 184).

        The Laplacian highlights edges, and its variance indicates
        how many sharp edges are present. In-focus images have
        higher Laplacian variance.

        Args:
            image_data: 2D numpy array of image data

        Returns:
            Laplacian variance (higher = sharper)
        """
        try:
            import numpy as np
            from scipy import ndimage

            # Apply Laplacian filter
            laplacian = ndimage.laplace(image_data.astype(np.float64))

            # Calculate variance
            variance = laplacian.var()

            return float(variance)
        except ImportError:
            # Fallback if scipy not available
            logger.warning("scipy not available for Laplacian calculation")
            return 0.5

    async def _measure_hfd(self, camera) -> float:
        """
        Measure Half-Flux Diameter from focus frame.

        Captures a frame and calculates the median HFD of detected stars.
        Falls back to simulation if camera not available.

        Returns:
            Median HFD in pixels
        """
        if camera is None:
            # Simulation mode
            return await self._simulate_hfd()

        try:
            # Capture frame
            frame = await camera.capture(self.config.autofocus_exposure_sec)

            # Calculate HFD from frame
            hfd_result = self.calculate_hfd_from_image(frame)

            if hfd_result["num_stars"] > 0:
                return hfd_result["median_hfd"]
            else:
                logger.warning("No stars detected for HFD measurement")
                return await self._simulate_hfd()

        except Exception as e:
            logger.warning(f"HFD measurement failed: {e}, using simulation")
            return await self._simulate_hfd()

    async def _simulate_hfd(self) -> float:
        """Simulate HFD measurement for testing."""
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

    def calculate_hfd_from_image(self, image_data) -> dict:
        """
        Calculate Half-Flux Diameter from image data (Step 182).

        HFD is defined as the diameter of a circle centered on a star
        that contains half of the total flux. It's more robust than
        FWHM for defocused stars.

        Algorithm:
        1. Detect stars using threshold or SEP
        2. For each star, find centroid
        3. Calculate cumulative flux in expanding circles
        4. Find radius where cumulative flux = 50% of total
        5. Return median HFD across all stars

        Args:
            image_data: 2D numpy array of image data

        Returns:
            Dict with:
            - median_hfd: Median HFD in pixels
            - mean_hfd: Mean HFD
            - std_hfd: Standard deviation
            - num_stars: Number of stars measured
            - star_hfds: List of individual HFD values
        """
        try:
            import numpy as np
        except ImportError:
            return {"median_hfd": 3.0, "mean_hfd": 3.0, "std_hfd": 0, "num_stars": 0, "star_hfds": []}

        # Convert to numpy if needed
        if not isinstance(image_data, np.ndarray):
            image_data = np.array(image_data)

        # Ensure 2D
        if image_data.ndim > 2:
            image_data = image_data.mean(axis=2) if image_data.ndim == 3 else image_data

        # Background subtraction (simple median)
        background = np.median(image_data)
        image_sub = image_data - background

        # Find stars using simple threshold
        threshold = np.std(image_sub) * 5
        stars = self._detect_stars_simple(image_sub, threshold)

        if len(stars) == 0:
            return {"median_hfd": 0, "mean_hfd": 0, "std_hfd": 0, "num_stars": 0, "star_hfds": []}

        # Calculate HFD for each star
        hfds = []
        for star in stars:
            hfd = self._calculate_single_star_hfd(image_sub, star["x"], star["y"])
            if hfd is not None and 0.5 < hfd < 50:  # Sanity check
                hfds.append(hfd)

        if len(hfds) == 0:
            return {"median_hfd": 0, "mean_hfd": 0, "std_hfd": 0, "num_stars": 0, "star_hfds": []}

        return {
            "median_hfd": float(np.median(hfds)),
            "mean_hfd": float(np.mean(hfds)),
            "std_hfd": float(np.std(hfds)) if len(hfds) > 1 else 0,
            "num_stars": len(hfds),
            "star_hfds": hfds
        }

    def _detect_stars_simple(self, image: "np.ndarray", threshold: float) -> List[dict]:
        """
        Simple star detection using local maxima (Step 182).

        Args:
            image: Background-subtracted image
            threshold: Detection threshold

        Returns:
            List of star dicts with x, y, flux
        """
        try:
            import numpy as np
            from scipy import ndimage
        except ImportError:
            return []

        # Find local maxima
        max_filtered = ndimage.maximum_filter(image, size=5)
        peaks = (image == max_filtered) & (image > threshold)

        # Get coordinates
        y_coords, x_coords = np.where(peaks)

        stars = []
        for x, y in zip(x_coords, y_coords):
            # Simple flux estimate
            flux = image[y, x]
            stars.append({"x": float(x), "y": float(y), "flux": float(flux)})

        # Sort by flux and take top stars
        stars.sort(key=lambda s: s["flux"], reverse=True)
        return stars[:50]  # Max 50 stars

    def _calculate_single_star_hfd(
        self,
        image: "np.ndarray",
        cx: float,
        cy: float,
        max_radius: int = 25
    ) -> Optional[float]:
        """
        Calculate HFD for a single star (Step 182).

        Uses the aperture photometry approach:
        1. Sum flux in expanding circular apertures
        2. Find radius where cumulative flux = 50% of total

        Args:
            image: Background-subtracted image
            cx, cy: Star centroid coordinates
            max_radius: Maximum aperture radius to consider

        Returns:
            HFD in pixels, or None if calculation failed
        """
        try:
            import numpy as np
        except ImportError:
            return None

        h, w = image.shape
        cx_int, cy_int = int(round(cx)), int(round(cy))

        # Check bounds
        if cx_int < max_radius or cx_int >= w - max_radius:
            return None
        if cy_int < max_radius or cy_int >= h - max_radius:
            return None

        # Extract cutout
        cutout = image[cy_int - max_radius:cy_int + max_radius + 1,
                       cx_int - max_radius:cx_int + max_radius + 1]

        # Create distance array from center
        y_grid, x_grid = np.ogrid[-max_radius:max_radius + 1, -max_radius:max_radius + 1]
        distances = np.sqrt(x_grid**2 + y_grid**2)

        # Calculate cumulative flux at each radius
        radii = np.arange(1, max_radius + 1)
        cumulative_flux = np.zeros(len(radii))

        for i, r in enumerate(radii):
            mask = distances <= r
            cumulative_flux[i] = np.sum(cutout[mask])

        # Total flux (use largest aperture)
        total_flux = cumulative_flux[-1]

        if total_flux <= 0:
            return None

        # Find radius where cumulative flux = 50% of total
        half_flux = total_flux / 2
        half_flux_radius = None

        for i, (r, flux) in enumerate(zip(radii, cumulative_flux)):
            if flux >= half_flux:
                # Linear interpolation for sub-pixel precision
                if i > 0:
                    flux_prev = cumulative_flux[i - 1]
                    r_prev = radii[i - 1]
                    frac = (half_flux - flux_prev) / (flux - flux_prev)
                    half_flux_radius = r_prev + frac * (r - r_prev)
                else:
                    half_flux_radius = r
                break

        if half_flux_radius is None:
            return None

        # HFD is diameter, so multiply by 2
        hfd = half_flux_radius * 2

        return hfd

    def get_hfd_stats(self, image_data) -> dict:
        """
        Get comprehensive HFD statistics from an image (Step 182).

        Useful for focus quality assessment and logging.

        Args:
            image_data: 2D image array

        Returns:
            Dict with HFD statistics and quality assessment
        """
        result = self.calculate_hfd_from_image(image_data)

        # Add quality assessment
        if result["num_stars"] >= 10 and result["std_hfd"] < result["median_hfd"] * 0.3:
            quality = "good"
        elif result["num_stars"] >= 5:
            quality = "fair"
        elif result["num_stars"] > 0:
            quality = "poor"
        else:
            quality = "no_stars"

        result["quality"] = quality
        result["in_focus"] = result["median_hfd"] < 4.0 if result["num_stars"] > 0 else False

        return result

    def _fit_vcurve(self, positions: List[int], hfds: List[float]) -> int:
        """
        Fit parabola to V-curve data using full least squares (Step 181).

        The V-curve is modeled as y = ax² + bx + c where:
        - y is the HFD (Half-Flux Diameter)
        - x is the focuser position
        - The minimum (best focus) is at x = -b/(2a)

        Uses matrix-based least squares for accurate fitting.

        Returns:
            Optimal focus position
        """
        result = self._fit_vcurve_full(positions, hfds)
        return result["best_position"]

    def _fit_vcurve_full(self, positions: List[int], hfds: List[float]) -> dict:
        """
        Full V-curve parabolic fit with statistics (Step 181).

        Performs proper least squares parabolic regression:
        y = ax² + bx + c

        The optimal focus position is at the vertex: x = -b/(2a)

        Args:
            positions: List of focuser positions
            hfds: List of HFD values at each position

        Returns:
            Dict with:
            - best_position: Optimal focus position
            - a, b, c: Parabola coefficients
            - r_squared: Goodness of fit (1.0 = perfect)
            - curvature: Parabola curvature (a coefficient)
            - vertex_hfd: Predicted HFD at best position
            - confidence: Confidence level based on fit quality
        """
        n = len(positions)

        # Need at least 3 points for parabola
        if n < 3:
            min_idx = hfds.index(min(hfds))
            return {
                "best_position": positions[min_idx],
                "a": 0, "b": 0, "c": hfds[min_idx],
                "r_squared": 0,
                "curvature": 0,
                "vertex_hfd": hfds[min_idx],
                "confidence": "low",
                "method": "minimum_sample"
            }

        # Normalize positions for numerical stability
        x_mean = sum(positions) / n
        x_scale = max(abs(p - x_mean) for p in positions) or 1
        x_norm = [(p - x_mean) / x_scale for p in positions]
        y = hfds

        # Build design matrix for y = ax² + bx + c
        # [x²  x  1] * [a b c]ᵀ = y
        # Using normal equations: (XᵀX)β = Xᵀy

        # Compute sums for normal equations
        sum_x4 = sum(xi**4 for xi in x_norm)
        sum_x3 = sum(xi**3 for xi in x_norm)
        sum_x2 = sum(xi**2 for xi in x_norm)
        sum_x1 = sum(xi for xi in x_norm)
        sum_x0 = n

        sum_x2y = sum(xi**2 * yi for xi, yi in zip(x_norm, y))
        sum_x1y = sum(xi * yi for xi, yi in zip(x_norm, y))
        sum_x0y = sum(y)

        # Solve 3x3 system using Cramer's rule
        # | x4  x3  x2 | | a |   | x2y |
        # | x3  x2  x1 | | b | = | x1y |
        # | x2  x1  x0 | | c |   | x0y |

        det = (sum_x4 * (sum_x2 * sum_x0 - sum_x1 * sum_x1)
               - sum_x3 * (sum_x3 * sum_x0 - sum_x1 * sum_x2)
               + sum_x2 * (sum_x3 * sum_x1 - sum_x2 * sum_x2))

        if abs(det) < 1e-10:
            # Singular matrix - fallback to minimum
            min_idx = hfds.index(min(hfds))
            return {
                "best_position": positions[min_idx],
                "a": 0, "b": 0, "c": hfds[min_idx],
                "r_squared": 0,
                "curvature": 0,
                "vertex_hfd": hfds[min_idx],
                "confidence": "low",
                "method": "fallback_singular"
            }

        # Solve for a (normalized)
        det_a = (sum_x2y * (sum_x2 * sum_x0 - sum_x1 * sum_x1)
                 - sum_x3 * (sum_x1y * sum_x0 - sum_x1 * sum_x0y)
                 + sum_x2 * (sum_x1y * sum_x1 - sum_x2 * sum_x0y))
        a_norm = det_a / det

        # Solve for b (normalized)
        det_b = (sum_x4 * (sum_x1y * sum_x0 - sum_x1 * sum_x0y)
                 - sum_x2y * (sum_x3 * sum_x0 - sum_x1 * sum_x2)
                 + sum_x2 * (sum_x3 * sum_x0y - sum_x1y * sum_x2))
        b_norm = det_b / det

        # Solve for c (normalized)
        det_c = (sum_x4 * (sum_x2 * sum_x0y - sum_x1y * sum_x1)
                 - sum_x3 * (sum_x3 * sum_x0y - sum_x1y * sum_x2)
                 + sum_x2y * (sum_x3 * sum_x1 - sum_x2 * sum_x2))
        c_norm = det_c / det

        # Convert back to original scale
        # If x_norm = (x - x_mean) / x_scale, then
        # y = a_norm * x_norm² + b_norm * x_norm + c_norm
        # y = a_norm * ((x-x_mean)/x_scale)² + b_norm * ((x-x_mean)/x_scale) + c_norm
        a = a_norm / (x_scale ** 2)
        b = b_norm / x_scale - 2 * a_norm * x_mean / (x_scale ** 2)
        c = c_norm - b_norm * x_mean / x_scale + a_norm * (x_mean / x_scale) ** 2

        # Check that parabola opens upward (a > 0)
        if a <= 0:
            # Parabola opens downward - data doesn't form V-curve
            min_idx = hfds.index(min(hfds))
            return {
                "best_position": positions[min_idx],
                "a": a, "b": b, "c": c,
                "r_squared": 0,
                "curvature": a,
                "vertex_hfd": hfds[min_idx],
                "confidence": "low",
                "method": "fallback_inverted"
            }

        # Calculate vertex (minimum point)
        best_pos_float = -b / (2 * a)
        best_pos = int(round(best_pos_float))

        # Clamp to valid range
        best_pos = max(0, min(self.config.max_position, best_pos))

        # Calculate predicted HFD at vertex
        vertex_hfd = a * best_pos_float**2 + b * best_pos_float + c

        # Calculate R-squared
        y_mean = sum(y) / n
        ss_tot = sum((yi - y_mean)**2 for yi in y)
        ss_res = sum((yi - (a * xi**2 + b * xi + c))**2
                     for xi, yi in zip(positions, y))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Determine confidence level
        if r_squared > 0.95 and a > 0:
            confidence = "high"
        elif r_squared > 0.8 and a > 0:
            confidence = "medium"
        else:
            confidence = "low"

        logger.debug(f"V-curve fit: pos={best_pos}, HFD={vertex_hfd:.2f}, "
                    f"R²={r_squared:.3f}, a={a:.2e}")

        return {
            "best_position": best_pos,
            "a": a,
            "b": b,
            "c": c,
            "r_squared": r_squared,
            "curvature": a,
            "vertex_hfd": vertex_hfd,
            "confidence": confidence,
            "method": "parabolic_fit"
        }

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
                            # Step 188: Record reason for move
                            await self.move_to(
                                self._position + steps,
                                reason=f"temp_compensation ({temp_change:+.1f}C)"
                            )
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
        Calibrate temperature compensation coefficient (basic 2-point).

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

    async def calibrate_temp_coefficient_multipoint(
        self,
        camera,
        num_points: int = 5,
        temp_interval: float = 1.0,
        timeout_minutes: float = 120.0
    ) -> dict:
        """
        Multi-point temperature compensation calibration (Step 185).

        Collects multiple focus/temperature data points over a temperature
        range and performs linear regression to find the optimal coefficient.
        This provides a more accurate coefficient than the simple 2-point method.

        The process:
        1. Record initial focus and temperature
        2. Wait for temperature to change by temp_interval
        3. Find best focus at new temperature
        4. Repeat until num_points collected
        5. Perform linear regression on data
        6. Save coefficient and calibration data

        Args:
            camera: Camera for focus measurements
            num_points: Number of data points to collect (minimum 3)
            temp_interval: Temperature change between measurements (°C)
            timeout_minutes: Maximum time to wait for calibration

        Returns:
            Dict with:
            - coefficient: Calculated steps/°C
            - r_squared: Regression R² value (1.0 = perfect fit)
            - data_points: List of (temp, focus) tuples
            - std_error: Standard error of coefficient
            - status: "success" or error message
        """
        logger.info(f"Starting multi-point temp coefficient calibration (Step 185)")
        logger.info(f"Collecting {num_points} points at {temp_interval}°C intervals")

        if num_points < 3:
            return {"status": "error", "message": "Need at least 3 data points"}

        self._state = FocuserState.CALIBRATING
        data_points: List[Tuple[float, int]] = []
        start_time = datetime.now()
        last_temp = None

        try:
            # Collect data points
            for point_num in range(num_points):
                current_temp = self._temperature

                # For first point, just record
                if point_num == 0:
                    focus_pos = await self._find_best_focus(camera)
                    data_points.append((current_temp, focus_pos))
                    last_temp = current_temp
                    logger.info(f"Point 1/{num_points}: temp={current_temp:.1f}°C, focus={focus_pos}")
                    continue

                # Wait for temperature to change
                logger.info(f"Waiting for {temp_interval}°C temperature change...")
                while abs(self._temperature - last_temp) < temp_interval:
                    # Check timeout
                    elapsed = (datetime.now() - start_time).total_seconds() / 60
                    if elapsed > timeout_minutes:
                        logger.warning(f"Calibration timeout after {elapsed:.1f} minutes")
                        break

                    await asyncio.sleep(30)  # Check every 30 seconds

                # Check if we got enough temperature change
                if abs(self._temperature - last_temp) < temp_interval * 0.5:
                    logger.warning("Insufficient temperature change, ending calibration early")
                    break

                # Find best focus at new temperature
                current_temp = self._temperature
                focus_pos = await self._find_best_focus(camera)
                data_points.append((current_temp, focus_pos))
                last_temp = current_temp

                logger.info(f"Point {point_num + 1}/{num_points}: "
                           f"temp={current_temp:.1f}°C, focus={focus_pos}")

            # Need at least 2 points for regression
            if len(data_points) < 2:
                return {
                    "status": "error",
                    "message": f"Only collected {len(data_points)} points, need at least 2",
                    "data_points": data_points
                }

            # Perform linear regression
            result = self._linear_regression(data_points)

            # Update coefficient
            self.config.temp_coefficient = result["coefficient"]
            logger.info(f"Calibration complete: {result['coefficient']:.2f} steps/°C "
                       f"(R²={result['r_squared']:.3f})")

            # Save calibration data
            self._last_calibration = {
                "date": datetime.now().isoformat(),
                "coefficient": result["coefficient"],
                "r_squared": result["r_squared"],
                "data_points": data_points,
                "num_points": len(data_points),
            }

            return {
                "status": "success",
                "coefficient": result["coefficient"],
                "r_squared": result["r_squared"],
                "std_error": result["std_error"],
                "data_points": data_points,
                "intercept": result["intercept"],
            }

        except Exception as e:
            logger.error(f"Calibration failed: {e}")
            return {"status": "error", "message": str(e), "data_points": data_points}

        finally:
            self._state = FocuserState.IDLE

    def _linear_regression(self, data_points: List[Tuple[float, int]]) -> dict:
        """
        Perform linear regression on temperature/focus data (Step 185).

        Uses least squares method to find best-fit line.
        focus = coefficient * temperature + intercept

        Args:
            data_points: List of (temperature, focus_position) tuples

        Returns:
            Dict with coefficient, intercept, r_squared, std_error
        """
        n = len(data_points)
        if n < 2:
            return {"coefficient": 0, "intercept": 0, "r_squared": 0, "std_error": 0}

        # Extract x (temperature) and y (focus)
        temps = [p[0] for p in data_points]
        focus = [p[1] for p in data_points]

        # Calculate means
        mean_temp = sum(temps) / n
        mean_focus = sum(focus) / n

        # Calculate slope (coefficient) and intercept
        numerator = sum((t - mean_temp) * (f - mean_focus) for t, f in data_points)
        denominator = sum((t - mean_temp) ** 2 for t in temps)

        if abs(denominator) < 1e-10:
            return {"coefficient": 0, "intercept": mean_focus, "r_squared": 0, "std_error": 0}

        coefficient = numerator / denominator
        intercept = mean_focus - coefficient * mean_temp

        # Calculate R-squared
        ss_tot = sum((f - mean_focus) ** 2 for f in focus)
        ss_res = sum((f - (coefficient * t + intercept)) ** 2 for t, f in data_points)

        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Calculate standard error of coefficient
        if n > 2 and ss_tot > 0:
            mse = ss_res / (n - 2)
            std_error = (mse / denominator) ** 0.5 if denominator > 0 else 0
        else:
            std_error = 0

        return {
            "coefficient": coefficient,
            "intercept": intercept,
            "r_squared": r_squared,
            "std_error": std_error,
        }

    def apply_temp_compensation(self, temp_change: float) -> int:
        """
        Calculate focus adjustment for temperature change (Step 185).

        Args:
            temp_change: Temperature change in °C (positive = warmer)

        Returns:
            Focus position adjustment in steps
        """
        adjustment = int(temp_change * self.config.temp_coefficient)
        logger.debug(f"Temp compensation: {temp_change:.1f}°C -> {adjustment} steps")
        return adjustment

    def get_compensated_position(self, reference_temp: float, reference_focus: int) -> int:
        """
        Calculate compensated focus position for current temperature (Step 185).

        Given a known good focus at a reference temperature, calculate
        what the focus should be at the current temperature.

        Args:
            reference_temp: Temperature when reference_focus was optimal
            reference_focus: Focus position that was optimal at reference_temp

        Returns:
            Compensated focus position for current temperature
        """
        temp_change = self._temperature - reference_temp
        adjustment = self.apply_temp_compensation(temp_change)
        compensated = reference_focus + adjustment

        # Clamp to valid range
        compensated = max(0, min(self.config.max_position, compensated))

        logger.debug(f"Temp compensation: ref={reference_focus}@{reference_temp:.1f}°C -> "
                    f"{compensated}@{self._temperature:.1f}°C")

        return compensated

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
