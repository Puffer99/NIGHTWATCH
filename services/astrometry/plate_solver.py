"""
NIGHTWATCH Plate Solving Service
Astrometric Position Determination

POS Panel v3.0 - Day 22 Recommendations (Dustin Lang + ASTAP Team):
- Local astrometry.net solve-field for offline operation
- Index files for your FOV (2MASS for wide, UCAC4 for narrow)
- ASTAP as fast fallback solver
- Blind solve timeout: 30 seconds, hint solve: 5 seconds
- Sync mount after successful solve for pointing correction
"""

import asyncio
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
import json
import math

logger = logging.getLogger("NIGHTWATCH.Astrometry")


class SolverBackend(Enum):
    """Plate solving backends."""
    ASTROMETRY_NET = "astrometry.net"  # Local solve-field
    ASTAP = "astap"                     # ASTAP solver
    PLATESOLVE2 = "platesolve2"         # PlateSolve2 (Windows)
    NOVA = "nova"                        # nova.astrometry.net API


class SolveStatus(Enum):
    """Solve result status."""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    NO_STARS = "no_stars"
    CANCELLED = "cancelled"


@dataclass
class SolverConfig:
    """Plate solver configuration."""
    # Backend selection
    primary_solver: SolverBackend = SolverBackend.ASTROMETRY_NET
    fallback_solver: Optional[SolverBackend] = SolverBackend.ASTAP

    # Paths
    solve_field_path: str = "/usr/bin/solve-field"
    astap_path: str = "/opt/astap/astap"
    index_path: str = "/usr/share/astrometry"

    # Timeouts
    blind_timeout_sec: float = 30.0     # Timeout for blind solve
    hint_timeout_sec: float = 5.0       # Timeout with position hint
    download_timeout_sec: float = 10.0  # Timeout for star detection

    # Image parameters (for MN78 at 1050mm f/6)
    pixel_scale_low: float = 0.5        # arcsec/pixel lower bound
    pixel_scale_high: float = 2.0       # arcsec/pixel upper bound
    field_width_deg: float = 0.5        # Approximate field width

    # Solve parameters
    downsample: int = 2                 # Downsample factor for speed
    depth: str = "20,30,40,50"          # Search depth
    use_sextractor: bool = True         # Use SExtractor for star detection


@dataclass
class SolveResult:
    """Plate solve result."""
    status: SolveStatus
    timestamp: datetime = field(default_factory=datetime.now)

    # Solved position (J2000)
    ra_deg: Optional[float] = None      # Right Ascension in degrees
    dec_deg: Optional[float] = None     # Declination in degrees

    # Image orientation
    rotation_deg: Optional[float] = None  # Field rotation in degrees
    pixel_scale: Optional[float] = None   # arcsec/pixel

    # Field dimensions
    field_width_deg: Optional[float] = None
    field_height_deg: Optional[float] = None

    # Solve metadata
    solve_time_sec: float = 0.0
    backend_used: Optional[SolverBackend] = None
    num_stars_matched: int = 0
    num_index_stars: int = 0

    # WCS info (for image annotation)
    wcs_header: Optional[Dict[str, Any]] = None

    # Error info
    error_message: Optional[str] = None

    @property
    def ra_hms(self) -> str:
        """RA in HMS format."""
        if self.ra_deg is None:
            return ""
        h = self.ra_deg / 15.0
        hours = int(h)
        m = (h - hours) * 60
        minutes = int(m)
        seconds = (m - minutes) * 60
        return f"{hours:02d}h {minutes:02d}m {seconds:05.2f}s"

    @property
    def dec_dms(self) -> str:
        """Dec in DMS format."""
        if self.dec_deg is None:
            return ""
        sign = "+" if self.dec_deg >= 0 else "-"
        d = abs(self.dec_deg)
        degrees = int(d)
        m = (d - degrees) * 60
        minutes = int(m)
        seconds = (m - minutes) * 60
        return f"{sign}{degrees:02d}° {minutes:02d}' {seconds:05.2f}\""


@dataclass
class PlateSolveHint:
    """Position hint for faster solving."""
    ra_deg: float           # Approximate RA
    dec_deg: float          # Approximate Dec
    radius_deg: float = 5.0 # Search radius


class PlateSolver:
    """
    Astrometric plate solving for NIGHTWATCH.

    Features:
    - Local astrometry.net (solve-field) integration
    - ASTAP fallback solver
    - Position hints for fast solving
    - Mount sync integration
    - WCS header generation

    Usage:
        solver = PlateSolver()
        result = await solver.solve("/path/to/image.fits")
        if result.status == SolveStatus.SUCCESS:
            print(f"Position: {result.ra_hms} {result.dec_dms}")
    """

    def __init__(self, config: Optional[SolverConfig] = None):
        """
        Initialize plate solver.

        Args:
            config: Solver configuration
        """
        self.config = config or SolverConfig()
        self._solve_history: List[SolveResult] = []
        self._current_process: Optional[asyncio.subprocess.Process] = None

    async def solve(self,
                   image_path: str,
                   hint: Optional[PlateSolveHint] = None,
                   timeout: Optional[float] = None) -> SolveResult:
        """
        Solve image astrometry.

        Args:
            image_path: Path to FITS image
            hint: Optional position hint for faster solving
            timeout: Override default timeout

        Returns:
            SolveResult with position or error
        """
        image_path = Path(image_path)
        if not image_path.exists():
            return SolveResult(
                status=SolveStatus.FAILED,
                error_message=f"Image not found: {image_path}"
            )

        # Determine timeout
        if timeout is None:
            timeout = (self.config.hint_timeout_sec if hint
                      else self.config.blind_timeout_sec)

        start_time = datetime.now()

        # Try primary solver
        result = await self._solve_with_backend(
            self.config.primary_solver, image_path, hint, timeout
        )

        # Try fallback if primary failed
        if (result.status != SolveStatus.SUCCESS and
            self.config.fallback_solver is not None):

            logger.info(f"Primary solver failed, trying {self.config.fallback_solver.value}")
            result = await self._solve_with_backend(
                self.config.fallback_solver, image_path, hint, timeout
            )

        # Record solve time
        result.solve_time_sec = (datetime.now() - start_time).total_seconds()

        # Store in history
        self._solve_history.append(result)

        if result.status == SolveStatus.SUCCESS:
            logger.info(f"Plate solve success: {result.ra_hms} {result.dec_dms} "
                       f"({result.solve_time_sec:.1f}s)")
        else:
            logger.warning(f"Plate solve failed: {result.error_message}")

        return result

    async def _solve_with_backend(self,
                                  backend: SolverBackend,
                                  image_path: Path,
                                  hint: Optional[PlateSolveHint],
                                  timeout: float) -> SolveResult:
        """Solve using specific backend."""
        if backend == SolverBackend.ASTROMETRY_NET:
            return await self._solve_astrometry_net(image_path, hint, timeout)
        elif backend == SolverBackend.ASTAP:
            return await self._solve_astap(image_path, hint, timeout)
        else:
            return SolveResult(
                status=SolveStatus.FAILED,
                error_message=f"Unsupported backend: {backend}"
            )

    async def _solve_astrometry_net(self,
                                    image_path: Path,
                                    hint: Optional[PlateSolveHint],
                                    timeout: float) -> SolveResult:
        """Solve using local astrometry.net solve-field."""
        # Build command
        cmd = [
            self.config.solve_field_path,
            "--overwrite",
            "--no-plots",
            "--downsample", str(self.config.downsample),
            "--scale-units", "arcsecperpix",
            "--scale-low", str(self.config.pixel_scale_low),
            "--scale-high", str(self.config.pixel_scale_high),
            "--depth", self.config.depth,
            "--cpulimit", str(int(timeout)),
        ]

        # Add position hint
        if hint:
            cmd.extend([
                "--ra", str(hint.ra_deg),
                "--dec", str(hint.dec_deg),
                "--radius", str(hint.radius_deg),
            ])

        # Add index path
        cmd.extend(["--index-dir", self.config.index_path])

        # Output files
        output_base = image_path.with_suffix("")
        cmd.extend([
            "--new-fits", "none",
            "--solved", str(output_base) + ".solved",
            "--wcs", str(output_base) + ".wcs",
            str(image_path)
        ])

        logger.debug(f"Running: {' '.join(cmd)}")

        try:
            # Run solve-field
            self._current_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    self._current_process.communicate(),
                    timeout=timeout + 5
                )
            except asyncio.TimeoutError:
                self._current_process.kill()
                return SolveResult(
                    status=SolveStatus.TIMEOUT,
                    backend_used=SolverBackend.ASTROMETRY_NET,
                    error_message=f"Solve timed out after {timeout}s"
                )

            # Check for success
            solved_file = Path(str(output_base) + ".solved")
            wcs_file = Path(str(output_base) + ".wcs")

            if solved_file.exists():
                # Parse WCS solution
                return await self._parse_wcs(wcs_file, SolverBackend.ASTROMETRY_NET)
            else:
                return SolveResult(
                    status=SolveStatus.FAILED,
                    backend_used=SolverBackend.ASTROMETRY_NET,
                    error_message="No solution found"
                )

        except FileNotFoundError:
            return SolveResult(
                status=SolveStatus.FAILED,
                backend_used=SolverBackend.ASTROMETRY_NET,
                error_message=f"solve-field not found at {self.config.solve_field_path}"
            )
        except Exception as e:
            return SolveResult(
                status=SolveStatus.FAILED,
                backend_used=SolverBackend.ASTROMETRY_NET,
                error_message=str(e)
            )

    async def _solve_astap(self,
                          image_path: Path,
                          hint: Optional[PlateSolveHint],
                          timeout: float) -> SolveResult:
        """Solve using ASTAP."""
        # Build command
        cmd = [
            self.config.astap_path,
            "-f", str(image_path),
            "-r", str(int(self.config.field_width_deg * 60)),  # Search radius in arcmin
            "-z", str(self.config.downsample),
        ]

        # Add position hint
        if hint:
            cmd.extend([
                "-ra", str(hint.ra_deg / 15.0),  # ASTAP uses hours
                "-spd", str(hint.dec_deg + 90),  # South Pole Distance
            ])

        logger.debug(f"Running: {' '.join(cmd)}")

        try:
            self._current_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    self._current_process.communicate(),
                    timeout=timeout + 5
                )
            except asyncio.TimeoutError:
                self._current_process.kill()
                return SolveResult(
                    status=SolveStatus.TIMEOUT,
                    backend_used=SolverBackend.ASTAP,
                    error_message=f"ASTAP timed out after {timeout}s"
                )

            # ASTAP creates .wcs file with same base name
            wcs_file = image_path.with_suffix(".wcs")
            ini_file = image_path.with_suffix(".ini")

            if wcs_file.exists():
                return await self._parse_wcs(wcs_file, SolverBackend.ASTAP)
            elif ini_file.exists():
                return await self._parse_astap_ini(ini_file)
            else:
                return SolveResult(
                    status=SolveStatus.FAILED,
                    backend_used=SolverBackend.ASTAP,
                    error_message="ASTAP: No solution found"
                )

        except FileNotFoundError:
            return SolveResult(
                status=SolveStatus.FAILED,
                backend_used=SolverBackend.ASTAP,
                error_message=f"ASTAP not found at {self.config.astap_path}"
            )
        except Exception as e:
            return SolveResult(
                status=SolveStatus.FAILED,
                backend_used=SolverBackend.ASTAP,
                error_message=str(e)
            )

    async def _parse_wcs(self, wcs_file: Path, backend: SolverBackend) -> SolveResult:
        """Parse WCS FITS header for solution."""
        try:
            # Try to import astropy for WCS parsing
            try:
                from astropy.io import fits
                from astropy.wcs import WCS

                with fits.open(wcs_file) as hdul:
                    header = hdul[0].header
                    wcs = WCS(header)

                    # Get center position
                    naxis1 = header.get("NAXIS1", header.get("IMAGEW", 1000))
                    naxis2 = header.get("NAXIS2", header.get("IMAGEH", 1000))
                    ra, dec = wcs.wcs_pix2world(naxis1/2, naxis2/2, 1)

                    # Get pixel scale and rotation
                    cd11 = header.get("CD1_1", 0)
                    cd12 = header.get("CD1_2", 0)
                    cd21 = header.get("CD2_1", 0)
                    cd22 = header.get("CD2_2", 0)

                    pixel_scale = math.sqrt(cd11**2 + cd21**2) * 3600  # deg to arcsec
                    rotation = math.degrees(math.atan2(cd21, cd11))

                    return SolveResult(
                        status=SolveStatus.SUCCESS,
                        ra_deg=float(ra),
                        dec_deg=float(dec),
                        rotation_deg=rotation,
                        pixel_scale=pixel_scale,
                        field_width_deg=naxis1 * pixel_scale / 3600,
                        field_height_deg=naxis2 * pixel_scale / 3600,
                        backend_used=backend,
                        wcs_header=dict(header)
                    )

            except ImportError:
                # Fallback: parse header manually
                return await self._parse_wcs_manual(wcs_file, backend)

        except Exception as e:
            return SolveResult(
                status=SolveStatus.FAILED,
                backend_used=backend,
                error_message=f"WCS parse error: {e}"
            )

    async def _parse_wcs_manual(self, wcs_file: Path, backend: SolverBackend) -> SolveResult:
        """Manually parse WCS header without astropy."""
        # Simple keyword extraction
        header = {}

        with open(wcs_file, 'rb') as f:
            while True:
                line = f.read(80)
                if not line or line.startswith(b'END'):
                    break
                try:
                    line_str = line.decode('ascii').strip()
                    if '=' in line_str:
                        key, value = line_str.split('=', 1)
                        key = key.strip()
                        value = value.split('/')[0].strip().strip("'")
                        try:
                            value = float(value)
                        except ValueError:
                            pass
                        header[key] = value
                except Exception:
                    continue

        ra = header.get('CRVAL1')
        dec = header.get('CRVAL2')

        if ra is not None and dec is not None:
            return SolveResult(
                status=SolveStatus.SUCCESS,
                ra_deg=float(ra),
                dec_deg=float(dec),
                backend_used=backend
            )
        else:
            return SolveResult(
                status=SolveStatus.FAILED,
                backend_used=backend,
                error_message="Could not extract RA/Dec from WCS"
            )

    async def _parse_astap_ini(self, ini_file: Path) -> SolveResult:
        """Parse ASTAP .ini result file."""
        data = {}
        with open(ini_file) as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    data[key] = value

        if data.get('PLTSOLVD') == 'T':
            return SolveResult(
                status=SolveStatus.SUCCESS,
                ra_deg=float(data.get('CRVAL1', 0)),
                dec_deg=float(data.get('CRVAL2', 0)),
                rotation_deg=float(data.get('CROTA2', 0)),
                pixel_scale=float(data.get('CDELT2', 0)) * 3600,
                backend_used=SolverBackend.ASTAP
            )
        else:
            return SolveResult(
                status=SolveStatus.FAILED,
                backend_used=SolverBackend.ASTAP,
                error_message="ASTAP: Plate solve failed"
            )

    async def cancel(self):
        """Cancel current solve operation."""
        if self._current_process:
            self._current_process.kill()
            logger.info("Plate solve cancelled")

    # =========================================================================
    # MOUNT SYNC
    # =========================================================================

    async def solve_and_sync(self,
                            image_path: str,
                            mount,
                            hint: Optional[PlateSolveHint] = None) -> SolveResult:
        """
        Solve image and sync mount to solved position.

        Args:
            image_path: Path to image
            mount: Mount controller with sync_to_coordinates method
            hint: Optional position hint

        Returns:
            SolveResult
        """
        result = await self.solve(image_path, hint)

        if result.status == SolveStatus.SUCCESS:
            try:
                # Sync mount to solved position
                await mount.sync_to_coordinates(result.ra_deg, result.dec_deg)
                logger.info(f"Mount synced to {result.ra_hms} {result.dec_dms}")
            except Exception as e:
                logger.error(f"Failed to sync mount: {e}")

        return result

    # =========================================================================
    # PIXEL SCALE ESTIMATION (Step 115)
    # =========================================================================

    def estimate_pixel_scale_from_image(self, image_path: str) -> Optional[float]:
        """
        Estimate pixel scale from image metadata (Step 115).

        Tries to determine pixel scale from FITS header information:
        - FOCALLEN (focal length in mm)
        - XPIXSZ/PIXSIZE1 (pixel size in microns)
        - SCALE (direct scale if available)

        Args:
            image_path: Path to FITS image

        Returns:
            Estimated pixel scale in arcsec/pixel, or None if cannot determine
        """
        try:
            from astropy.io import fits

            with fits.open(image_path) as hdul:
                header = hdul[0].header

                # Check for direct scale keyword
                if 'SCALE' in header:
                    return float(header['SCALE'])

                # Try to calculate from focal length and pixel size
                focal_length_mm = header.get('FOCALLEN', header.get('FOCAL', None))
                pixel_size_um = header.get('XPIXSZ', header.get('PIXSIZE1', header.get('PIXSIZE', None)))

                if focal_length_mm and pixel_size_um:
                    # Scale = 206.265 * pixel_size_um / focal_length_mm
                    scale = 206.265 * float(pixel_size_um) / float(focal_length_mm)
                    logger.debug(f"Estimated pixel scale from header: {scale:.3f} arcsec/px")
                    return scale

                # Check for CDELT keywords from existing WCS
                cdelt1 = header.get('CDELT1', header.get('CD1_1', None))
                cdelt2 = header.get('CDELT2', header.get('CD2_2', None))

                if cdelt1 or cdelt2:
                    scale = abs(float(cdelt1 or cdelt2)) * 3600  # Convert deg to arcsec
                    return scale

                logger.debug("Could not determine pixel scale from FITS header")
                return None

        except ImportError:
            return self._estimate_pixel_scale_manual(image_path)
        except Exception as e:
            logger.debug(f"Pixel scale estimation failed: {e}")
            return None

    def _estimate_pixel_scale_manual(self, image_path: str) -> Optional[float]:
        """
        Manually estimate pixel scale without astropy (Step 115).

        Simple FITS header parser for basic keywords.
        """
        try:
            with open(image_path, 'rb') as f:
                header_bytes = f.read(2880 * 10)  # Read first 10 blocks

            header_str = header_bytes.decode('ascii', errors='ignore')
            keywords = {}

            for line in [header_str[i:i+80] for i in range(0, len(header_str), 80)]:
                if '=' in line:
                    key = line[:8].strip()
                    value_part = line[10:].split('/')[0].strip()
                    try:
                        value = float(value_part)
                        keywords[key] = value
                    except ValueError:
                        pass

            # Try focal length + pixel size calculation
            focal_length = keywords.get('FOCALLEN', keywords.get('FOCAL'))
            pixel_size = keywords.get('XPIXSZ', keywords.get('PIXSIZE1', keywords.get('PIXSIZE')))

            if focal_length and pixel_size:
                return 206.265 * pixel_size / focal_length

            return None

        except Exception as e:
            logger.debug(f"Manual pixel scale estimation failed: {e}")
            return None

    def auto_configure_scale(self, image_path: str) -> Tuple[float, float]:
        """
        Auto-configure pixel scale range from image (Step 115).

        Estimates pixel scale and returns appropriate search range.

        Args:
            image_path: Path to FITS image

        Returns:
            (scale_low, scale_high) in arcsec/pixel
        """
        estimated = self.estimate_pixel_scale_from_image(image_path)

        if estimated:
            # Use +/- 50% range around estimated value
            scale_low = estimated * 0.5
            scale_high = estimated * 1.5
            logger.info(f"Auto-configured scale: {scale_low:.2f}-{scale_high:.2f} arcsec/px "
                       f"(estimated {estimated:.2f})")
            return (scale_low, scale_high)
        else:
            # Fall back to config defaults
            return (self.config.pixel_scale_low, self.config.pixel_scale_high)

    def calculate_pointing_error(self,
                                expected_ra: float,
                                expected_dec: float,
                                result: SolveResult) -> Tuple[float, float, float]:
        """
        Calculate pointing error from solve result.

        Args:
            expected_ra: Expected RA in degrees
            expected_dec: Expected Dec in degrees
            result: Solve result

        Returns:
            (ra_error_arcsec, dec_error_arcsec, total_error_arcsec)
        """
        if result.status != SolveStatus.SUCCESS:
            return (0, 0, 0)

        # Calculate errors
        ra_error = (result.ra_deg - expected_ra) * 3600 * math.cos(math.radians(expected_dec))
        dec_error = (result.dec_deg - expected_dec) * 3600

        total = math.sqrt(ra_error**2 + dec_error**2)

        return (ra_error, dec_error, total)

    # =========================================================================
    # HISTORY AND STATISTICS
    # =========================================================================

    def get_solve_statistics(self) -> Dict[str, Any]:
        """Get plate solving statistics."""
        if not self._solve_history:
            return {"total_solves": 0}

        successes = [r for r in self._solve_history if r.status == SolveStatus.SUCCESS]
        failures = [r for r in self._solve_history if r.status != SolveStatus.SUCCESS]

        success_times = [r.solve_time_sec for r in successes]

        return {
            "total_solves": len(self._solve_history),
            "success_count": len(successes),
            "failure_count": len(failures),
            "success_rate": len(successes) / len(self._solve_history) * 100,
            "avg_solve_time": sum(success_times) / len(success_times) if success_times else 0,
            "min_solve_time": min(success_times) if success_times else 0,
            "max_solve_time": max(success_times) if success_times else 0,
        }


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    async def test():
        print("NIGHTWATCH Plate Solver Test\n")

        solver = PlateSolver()

        print(f"Primary solver: {solver.config.primary_solver.value}")
        print(f"Fallback solver: {solver.config.fallback_solver.value}")
        print(f"Pixel scale range: {solver.config.pixel_scale_low}-{solver.config.pixel_scale_high} arcsec/px")

        # Test with hint
        hint = PlateSolveHint(ra_deg=180.0, dec_deg=45.0, radius_deg=5.0)
        print(f"\nTest hint: RA={hint.ra_deg}°, Dec={hint.dec_deg}°")

        # Note: Actual solve would require a real image file
        print("\nNote: Actual solving requires a FITS image file")
        print("Example usage:")
        print("  result = await solver.solve('image.fits')")
        print("  result = await solver.solve('image.fits', hint=hint)")

        # Show result format
        result = SolveResult(
            status=SolveStatus.SUCCESS,
            ra_deg=180.123,
            dec_deg=45.456,
            rotation_deg=12.5,
            pixel_scale=0.95,
            solve_time_sec=3.2,
            backend_used=SolverBackend.ASTROMETRY_NET
        )
        print(f"\nExample result:")
        print(f"  Status: {result.status.value}")
        print(f"  Position: {result.ra_hms} {result.dec_dms}")
        print(f"  Rotation: {result.rotation_deg}°")
        print(f"  Scale: {result.pixel_scale} arcsec/px")
        print(f"  Solve time: {result.solve_time_sec}s")

    asyncio.run(test())
