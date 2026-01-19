"""
Unit tests for NIGHTWATCH plate solving service.

Tests solver configuration, result handling, and coordinate formatting.
"""

import pytest
from datetime import datetime
from services.astrometry.plate_solver import (
    PlateSolver,
    SolverConfig,
    SolverBackend,
    SolveStatus,
    SolveResult,
    PlateSolveHint,
)


class TestSolverBackend:
    """Tests for SolverBackend enum."""

    def test_astrometry_net_backend(self):
        """Test astrometry.net backend value."""
        assert SolverBackend.ASTROMETRY_NET.value == "astrometry.net"

    def test_astap_backend(self):
        """Test ASTAP backend value."""
        assert SolverBackend.ASTAP.value == "astap"

    def test_platesolve2_backend(self):
        """Test PlateSolve2 backend value."""
        assert SolverBackend.PLATESOLVE2.value == "platesolve2"

    def test_nova_backend(self):
        """Test nova.astrometry.net API backend value."""
        assert SolverBackend.NOVA.value == "nova"


class TestSolveStatus:
    """Tests for SolveStatus enum."""

    def test_success_status(self):
        """Test success status value."""
        assert SolveStatus.SUCCESS.value == "success"

    def test_failed_status(self):
        """Test failed status value."""
        assert SolveStatus.FAILED.value == "failed"

    def test_timeout_status(self):
        """Test timeout status value."""
        assert SolveStatus.TIMEOUT.value == "timeout"

    def test_no_stars_status(self):
        """Test no stars status value."""
        assert SolveStatus.NO_STARS.value == "no_stars"

    def test_cancelled_status(self):
        """Test cancelled status value."""
        assert SolveStatus.CANCELLED.value == "cancelled"


class TestSolverConfig:
    """Tests for SolverConfig dataclass."""

    def test_default_config(self):
        """Test default solver configuration."""
        config = SolverConfig()

        assert config.primary_solver == SolverBackend.ASTROMETRY_NET
        assert config.fallback_solver == SolverBackend.ASTAP
        assert config.solve_field_path == "/usr/bin/solve-field"
        assert config.astap_path == "/opt/astap/astap"
        assert config.index_path == "/usr/share/astrometry"
        assert config.blind_timeout_sec == 30.0
        assert config.hint_timeout_sec == 5.0
        assert config.download_timeout_sec == 10.0
        assert config.pixel_scale_low == 0.5
        assert config.pixel_scale_high == 2.0
        assert config.field_width_deg == 0.5
        assert config.downsample == 2
        assert config.use_sextractor is True

    def test_custom_config(self):
        """Test custom solver configuration."""
        config = SolverConfig(
            primary_solver=SolverBackend.ASTAP,
            fallback_solver=None,
            blind_timeout_sec=60.0,
            hint_timeout_sec=10.0,
            pixel_scale_low=0.8,
            pixel_scale_high=1.5,
            downsample=4,
        )

        assert config.primary_solver == SolverBackend.ASTAP
        assert config.fallback_solver is None
        assert config.blind_timeout_sec == 60.0
        assert config.hint_timeout_sec == 10.0
        assert config.pixel_scale_low == 0.8
        assert config.pixel_scale_high == 1.5
        assert config.downsample == 4

    def test_depth_string_format(self):
        """Test depth string format."""
        config = SolverConfig()
        assert "," in config.depth  # Comma-separated values
        assert "20" in config.depth


class TestSolveResult:
    """Tests for SolveResult dataclass."""

    def test_success_result(self):
        """Test successful solve result."""
        result = SolveResult(
            status=SolveStatus.SUCCESS,
            ra_deg=10.684,  # ~0h 42m 44s
            dec_deg=41.269,  # +41° 16' 9"
            rotation_deg=45.5,
            pixel_scale=1.2,
            field_width_deg=0.5,
            field_height_deg=0.35,
            solve_time_sec=2.5,
            backend_used=SolverBackend.ASTROMETRY_NET,
            num_stars_matched=85,
            num_index_stars=120,
        )

        assert result.status == SolveStatus.SUCCESS
        assert result.ra_deg == 10.684
        assert result.dec_deg == 41.269
        assert result.rotation_deg == 45.5
        assert result.pixel_scale == 1.2
        assert result.solve_time_sec == 2.5
        assert result.backend_used == SolverBackend.ASTROMETRY_NET
        assert result.error_message is None

    def test_failed_result(self):
        """Test failed solve result."""
        result = SolveResult(
            status=SolveStatus.FAILED,
            error_message="No matching stars found",
            solve_time_sec=30.0,
        )

        assert result.status == SolveStatus.FAILED
        assert result.error_message == "No matching stars found"
        assert result.ra_deg is None
        assert result.dec_deg is None

    def test_timeout_result(self):
        """Test timeout solve result."""
        result = SolveResult(
            status=SolveStatus.TIMEOUT,
            error_message="Solve exceeded 30 second timeout",
            solve_time_sec=30.0,
        )

        assert result.status == SolveStatus.TIMEOUT
        assert "timeout" in result.error_message.lower()

    def test_ra_hms_formatting(self):
        """Test RA hours-minutes-seconds formatting."""
        result = SolveResult(
            status=SolveStatus.SUCCESS,
            ra_deg=83.6333,  # Approximately 5h 34m 32s (Orion Nebula)
            dec_deg=-5.391,
        )

        ra_hms = result.ra_hms
        assert "h" in ra_hms
        assert "m" in ra_hms
        assert "s" in ra_hms

    def test_ra_hms_empty_when_none(self):
        """Test RA HMS returns empty when RA is None."""
        result = SolveResult(status=SolveStatus.FAILED)
        assert result.ra_hms == ""

    def test_dec_dms_formatting_positive(self):
        """Test Dec degrees-minutes-seconds formatting for positive declination."""
        result = SolveResult(
            status=SolveStatus.SUCCESS,
            ra_deg=83.0,
            dec_deg=41.269,  # +41° 16' 9"
        )

        dec_dms = result.dec_dms
        assert "+" in dec_dms
        assert "41" in dec_dms
        assert "°" in dec_dms

    def test_dec_dms_formatting_negative(self):
        """Test Dec degrees-minutes-seconds formatting for negative declination."""
        result = SolveResult(
            status=SolveStatus.SUCCESS,
            ra_deg=83.0,
            dec_deg=-5.391,  # Negative declination
        )

        dec_dms = result.dec_dms
        assert "-" in dec_dms

    def test_dec_dms_empty_when_none(self):
        """Test Dec DMS returns empty when Dec is None."""
        result = SolveResult(status=SolveStatus.FAILED)
        assert result.dec_dms == ""


class TestPlateSolveHint:
    """Tests for PlateSolveHint dataclass."""

    def test_hint_creation(self):
        """Test creating position hint."""
        hint = PlateSolveHint(
            ra_deg=83.6333,
            dec_deg=-5.391,
            radius_deg=2.0,
        )

        assert hint.ra_deg == 83.6333
        assert hint.dec_deg == -5.391
        assert hint.radius_deg == 2.0

    def test_hint_default_radius(self):
        """Test hint default radius."""
        hint = PlateSolveHint(ra_deg=0.0, dec_deg=0.0)
        assert hint.radius_deg == 5.0  # Default 5 degree radius

    def test_hint_narrow_radius(self):
        """Test hint with narrow search radius."""
        hint = PlateSolveHint(
            ra_deg=100.0,
            dec_deg=50.0,
            radius_deg=0.5,
        )
        assert hint.radius_deg == 0.5


class TestPlateSolverInitialization:
    """Tests for PlateSolver initialization."""

    def test_default_initialization(self):
        """Test default solver initialization."""
        solver = PlateSolver()

        assert solver.config.primary_solver == SolverBackend.ASTROMETRY_NET
        assert solver.config.fallback_solver == SolverBackend.ASTAP

    def test_custom_config_initialization(self):
        """Test solver initialization with custom config."""
        config = SolverConfig(
            primary_solver=SolverBackend.ASTAP,
            blind_timeout_sec=45.0,
        )
        solver = PlateSolver(config=config)

        assert solver.config.primary_solver == SolverBackend.ASTAP
        assert solver.config.blind_timeout_sec == 45.0


class TestSolveResultCoordinateFormatting:
    """Tests for coordinate formatting edge cases."""

    def test_ra_at_zero_hours(self):
        """Test RA formatting at 0 hours."""
        result = SolveResult(
            status=SolveStatus.SUCCESS,
            ra_deg=0.0,
            dec_deg=0.0,
        )

        ra_hms = result.ra_hms
        assert "00h" in ra_hms

    def test_ra_near_24_hours(self):
        """Test RA formatting near 24 hours (wraps to ~0)."""
        result = SolveResult(
            status=SolveStatus.SUCCESS,
            ra_deg=359.9,  # Very close to 24h
            dec_deg=0.0,
        )

        ra_hms = result.ra_hms
        assert "23h" in ra_hms  # Should be 23h 59m...

    def test_dec_at_north_pole(self):
        """Test Dec formatting at north pole."""
        result = SolveResult(
            status=SolveStatus.SUCCESS,
            ra_deg=0.0,
            dec_deg=90.0,
        )

        dec_dms = result.dec_dms
        assert "+90" in dec_dms

    def test_dec_at_south_pole(self):
        """Test Dec formatting at south pole."""
        result = SolveResult(
            status=SolveStatus.SUCCESS,
            ra_deg=0.0,
            dec_deg=-90.0,
        )

        dec_dms = result.dec_dms
        assert "-90" in dec_dms

    def test_dec_at_equator(self):
        """Test Dec formatting at celestial equator."""
        result = SolveResult(
            status=SolveStatus.SUCCESS,
            ra_deg=0.0,
            dec_deg=0.0,
        )

        dec_dms = result.dec_dms
        assert "00" in dec_dms


class TestSolverConfigValidation:
    """Tests for solver configuration boundary conditions."""

    def test_timeout_bounds(self):
        """Test timeout at boundary values."""
        # Very short timeout
        config_short = SolverConfig(blind_timeout_sec=1.0, hint_timeout_sec=0.5)
        assert config_short.blind_timeout_sec == 1.0
        assert config_short.hint_timeout_sec == 0.5

        # Long timeout for difficult fields
        config_long = SolverConfig(blind_timeout_sec=120.0)
        assert config_long.blind_timeout_sec == 120.0

    def test_pixel_scale_range(self):
        """Test pixel scale range configuration."""
        # Narrow scale (high focal length)
        config_narrow = SolverConfig(pixel_scale_low=0.1, pixel_scale_high=0.5)
        assert config_narrow.pixel_scale_low == 0.1

        # Wide scale (short focal length)
        config_wide = SolverConfig(pixel_scale_low=2.0, pixel_scale_high=10.0)
        assert config_wide.pixel_scale_high == 10.0

    def test_downsample_options(self):
        """Test downsample factor options."""
        for ds in [1, 2, 4, 8]:
            config = SolverConfig(downsample=ds)
            assert config.downsample == ds


class TestSolveResultMetadata:
    """Tests for solve result metadata fields."""

    def test_star_matching_stats(self):
        """Test star matching statistics."""
        result = SolveResult(
            status=SolveStatus.SUCCESS,
            ra_deg=100.0,
            dec_deg=50.0,
            num_stars_matched=150,
            num_index_stars=200,
        )

        assert result.num_stars_matched == 150
        assert result.num_index_stars == 200

    def test_wcs_header_storage(self):
        """Test WCS header storage."""
        wcs = {
            "CRPIX1": 960.0,
            "CRPIX2": 540.0,
            "CRVAL1": 100.0,
            "CRVAL2": 50.0,
            "CD1_1": -0.0003,
            "CD1_2": 0.0,
            "CD2_1": 0.0,
            "CD2_2": 0.0003,
        }

        result = SolveResult(
            status=SolveStatus.SUCCESS,
            ra_deg=100.0,
            dec_deg=50.0,
            wcs_header=wcs,
        )

        assert result.wcs_header is not None
        assert result.wcs_header["CRVAL1"] == 100.0
        assert result.wcs_header["CRVAL2"] == 50.0

    def test_field_dimensions(self):
        """Test field dimension storage."""
        result = SolveResult(
            status=SolveStatus.SUCCESS,
            ra_deg=100.0,
            dec_deg=50.0,
            field_width_deg=0.5,
            field_height_deg=0.35,
        )

        assert result.field_width_deg == 0.5
        assert result.field_height_deg == 0.35

    def test_timestamp_auto_created(self):
        """Test timestamp is automatically created."""
        result = SolveResult(status=SolveStatus.SUCCESS)

        assert result.timestamp is not None
        assert isinstance(result.timestamp, datetime)
