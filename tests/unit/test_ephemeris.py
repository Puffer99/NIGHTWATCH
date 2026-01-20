"""
NIGHTWATCH Ephemeris Service Tests

Tests for astronomical calculations including moon avoidance (Step 116).
"""

import math
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_skyfield():
    """Mock Skyfield to avoid needing actual ephemeris data."""
    with patch.dict('sys.modules', {
        'skyfield': MagicMock(),
        'skyfield.api': MagicMock(),
        'skyfield.almanac': MagicMock(),
    }):
        yield


@pytest.fixture
def ephemeris_service(mock_skyfield):
    """Create an EphemerisService with mocked Skyfield."""
    # Import after mocking
    from services.ephemeris.skyfield_service import (
        EphemerisService,
        ObserverLocation,
        SKYFIELD_AVAILABLE,
    )

    # Create service with mocked internals
    service = EphemerisService(ObserverLocation.nevada_site())

    # Mock the internal state
    service._initialized = True
    service._ts = MagicMock()
    service._eph = MagicMock()
    service._earth = MagicMock()
    service._observer = MagicMock()

    return service


# =============================================================================
# Moon Avoidance Tests (Step 116)
# =============================================================================


class TestMoonSeparation:
    """Tests for moon separation calculations."""

    def test_get_moon_separation_returns_degrees(self, ephemeris_service):
        """Test that moon separation returns a value in degrees."""
        # Mock the separation calculation
        mock_separation = MagicMock()
        mock_separation.degrees = 45.0

        mock_apparent = MagicMock()
        mock_apparent.separation_from.return_value = mock_separation
        mock_apparent.radec.return_value = (MagicMock(hours=12.0), MagicMock(degrees=30.0), MagicMock())

        mock_astrometric = MagicMock()
        mock_astrometric.apparent.return_value = mock_apparent

        ephemeris_service._observer.at.return_value.observe.return_value = mock_astrometric
        ephemeris_service._eph.__getitem__ = MagicMock(return_value=MagicMock())

        # Test
        separation = ephemeris_service.get_moon_separation(12.0, 30.0)
        assert separation == 45.0

    def test_get_moon_separation_from_body(self, ephemeris_service):
        """Test moon separation from another solar system body."""
        from services.ephemeris.skyfield_service import CelestialBody

        # Mock
        mock_separation = MagicMock()
        mock_separation.degrees = 90.0

        mock_apparent = MagicMock()
        mock_apparent.separation_from.return_value = mock_separation

        mock_astrometric = MagicMock()
        mock_astrometric.apparent.return_value = mock_apparent

        ephemeris_service._observer.at.return_value.observe.return_value = mock_astrometric
        ephemeris_service._eph.__getitem__ = MagicMock(return_value=MagicMock())

        # Test
        separation = ephemeris_service.get_moon_separation_from_body(CelestialBody.MARS)
        assert separation == 90.0


class TestMoonSafety:
    """Tests for moon safety evaluation."""

    def test_is_moon_safe_when_below_horizon(self, ephemeris_service):
        """Target is safe when moon is below horizon."""
        # Mock moon below horizon
        with patch.object(ephemeris_service, 'get_body_altaz') as mock_altaz:
            mock_pos = MagicMock()
            mock_pos.is_visible = False
            mock_pos.altitude_degrees = -10.0
            mock_altaz.return_value = mock_pos

            result = ephemeris_service.is_moon_safe(12.0, 30.0)
            assert result is True

    def test_is_moon_safe_when_thin_crescent(self, ephemeris_service):
        """Target is safe when moon is a thin crescent."""
        with patch.object(ephemeris_service, 'get_body_altaz') as mock_altaz:
            mock_pos = MagicMock()
            mock_pos.is_visible = True
            mock_altaz.return_value = mock_pos

            with patch.object(ephemeris_service, 'get_moon_phase') as mock_phase:
                mock_phase.return_value = 0.05  # 5% illuminated

                result = ephemeris_service.is_moon_safe(12.0, 30.0)
                assert result is True

    def test_is_moon_safe_when_far_enough(self, ephemeris_service):
        """Target is safe when separated by at least min distance."""
        with patch.object(ephemeris_service, 'get_body_altaz') as mock_altaz:
            mock_pos = MagicMock()
            mock_pos.is_visible = True
            mock_altaz.return_value = mock_pos

            with patch.object(ephemeris_service, 'get_moon_phase') as mock_phase:
                mock_phase.return_value = 0.80  # 80% illuminated

                with patch.object(ephemeris_service, 'get_moon_separation') as mock_sep:
                    mock_sep.return_value = 45.0  # 45° separation

                    result = ephemeris_service.is_moon_safe(12.0, 30.0, min_separation_deg=30.0)
                    assert result is True

    def test_is_moon_unsafe_when_close_and_bright(self, ephemeris_service):
        """Target is unsafe when close to bright moon."""
        with patch.object(ephemeris_service, 'get_body_altaz') as mock_altaz:
            mock_pos = MagicMock()
            mock_pos.is_visible = True
            mock_altaz.return_value = mock_pos

            with patch.object(ephemeris_service, 'get_moon_phase') as mock_phase:
                mock_phase.return_value = 0.95  # 95% illuminated

                with patch.object(ephemeris_service, 'get_moon_separation') as mock_sep:
                    mock_sep.return_value = 15.0  # Only 15° separation

                    result = ephemeris_service.is_moon_safe(12.0, 30.0, min_separation_deg=30.0)
                    assert result is False


class TestMoonPenalty:
    """Tests for moon penalty scoring."""

    def test_penalty_zero_when_moon_below_horizon(self, ephemeris_service):
        """Penalty is 0 when moon is not visible."""
        with patch.object(ephemeris_service, 'get_body_altaz') as mock_altaz:
            mock_pos = MagicMock()
            mock_pos.is_visible = False
            mock_altaz.return_value = mock_pos

            penalty = ephemeris_service.get_moon_penalty(12.0, 30.0)
            assert penalty == 0.0

    def test_penalty_low_for_new_moon(self, ephemeris_service):
        """Penalty is low during new moon."""
        with patch.object(ephemeris_service, 'get_body_altaz') as mock_altaz:
            mock_pos = MagicMock()
            mock_pos.is_visible = True
            mock_pos.altitude_degrees = 45.0
            mock_altaz.return_value = mock_pos

            with patch.object(ephemeris_service, 'get_moon_phase') as mock_phase:
                mock_phase.return_value = 0.05  # 5% illuminated

                with patch.object(ephemeris_service, 'get_moon_separation') as mock_sep:
                    mock_sep.return_value = 30.0

                    penalty = ephemeris_service.get_moon_penalty(12.0, 30.0)
                    # Low phase = low penalty even at moderate separation
                    assert penalty < 0.1

    def test_penalty_high_for_full_moon_close(self, ephemeris_service):
        """Penalty is high when close to full moon."""
        with patch.object(ephemeris_service, 'get_body_altaz') as mock_altaz:
            mock_pos = MagicMock()
            mock_pos.is_visible = True
            mock_pos.altitude_degrees = 60.0
            mock_altaz.return_value = mock_pos

            with patch.object(ephemeris_service, 'get_moon_phase') as mock_phase:
                mock_phase.return_value = 1.0  # Full moon

                with patch.object(ephemeris_service, 'get_moon_separation') as mock_sep:
                    mock_sep.return_value = 10.0  # Close

                    penalty = ephemeris_service.get_moon_penalty(12.0, 30.0)
                    # Full moon close by = high penalty
                    assert penalty > 0.5

    def test_penalty_decreases_with_distance(self, ephemeris_service):
        """Penalty decreases as separation increases."""
        with patch.object(ephemeris_service, 'get_body_altaz') as mock_altaz:
            mock_pos = MagicMock()
            mock_pos.is_visible = True
            mock_pos.altitude_degrees = 45.0
            mock_altaz.return_value = mock_pos

            with patch.object(ephemeris_service, 'get_moon_phase') as mock_phase:
                mock_phase.return_value = 0.75  # 75% illuminated

                with patch.object(ephemeris_service, 'get_moon_separation') as mock_sep:
                    # Test at different separations
                    mock_sep.return_value = 10.0
                    penalty_close = ephemeris_service.get_moon_penalty(12.0, 30.0)

                    mock_sep.return_value = 60.0
                    penalty_far = ephemeris_service.get_moon_penalty(12.0, 30.0)

                    assert penalty_close > penalty_far

    def test_penalty_clamped_to_unit_range(self, ephemeris_service):
        """Penalty is always between 0 and 1."""
        with patch.object(ephemeris_service, 'get_body_altaz') as mock_altaz:
            mock_pos = MagicMock()
            mock_pos.is_visible = True
            mock_pos.altitude_degrees = 90.0  # Zenith
            mock_altaz.return_value = mock_pos

            with patch.object(ephemeris_service, 'get_moon_phase') as mock_phase:
                mock_phase.return_value = 1.0  # Full moon

                with patch.object(ephemeris_service, 'get_moon_separation') as mock_sep:
                    mock_sep.return_value = 0.0  # Directly at moon

                    penalty = ephemeris_service.get_moon_penalty(12.0, 30.0)
                    assert 0.0 <= penalty <= 1.0


class TestMoonAvoidanceInfo:
    """Tests for moon avoidance info dictionary."""

    def test_info_contains_required_keys(self, ephemeris_service):
        """Info dict contains all required keys."""
        with patch.object(ephemeris_service, 'get_body_altaz') as mock_altaz:
            mock_pos = MagicMock()
            mock_pos.is_visible = True
            mock_pos.altitude_degrees = 45.0
            mock_pos.azimuth_degrees = 180.0
            mock_altaz.return_value = mock_pos

            with patch.object(ephemeris_service, 'get_moon_phase') as mock_phase:
                mock_phase.return_value = 0.50

                with patch.object(ephemeris_service, 'get_moon_separation') as mock_sep:
                    mock_sep.return_value = 40.0

                    with patch.object(ephemeris_service, 'get_moon_penalty') as mock_penalty:
                        mock_penalty.return_value = 0.3

                        with patch.object(ephemeris_service, 'is_moon_safe') as mock_safe:
                            mock_safe.return_value = True

                            info = ephemeris_service.get_moon_avoidance_info(12.0, 30.0)

                            required_keys = [
                                "moon_visible",
                                "moon_altitude_deg",
                                "moon_azimuth_deg",
                                "moon_phase_percent",
                                "separation_deg",
                                "penalty_score",
                                "is_safe",
                                "status",
                                "recommendation",
                            ]
                            for key in required_keys:
                                assert key in info

    def test_info_excellent_when_moon_below_horizon(self, ephemeris_service):
        """Recommendation is excellent when moon is below horizon."""
        with patch.object(ephemeris_service, 'get_body_altaz') as mock_altaz:
            mock_pos = MagicMock()
            mock_pos.is_visible = False
            mock_pos.altitude_degrees = -15.0
            mock_pos.azimuth_degrees = 90.0
            mock_altaz.return_value = mock_pos

            with patch.object(ephemeris_service, 'get_moon_phase') as mock_phase:
                mock_phase.return_value = 0.50

                with patch.object(ephemeris_service, 'get_moon_separation') as mock_sep:
                    mock_sep.return_value = 30.0

                    with patch.object(ephemeris_service, 'get_moon_penalty') as mock_penalty:
                        mock_penalty.return_value = 0.0

                        with patch.object(ephemeris_service, 'is_moon_safe') as mock_safe:
                            mock_safe.return_value = True

                            info = ephemeris_service.get_moon_avoidance_info(12.0, 30.0)
                            assert info["status"] == "below_horizon"
                            assert info["recommendation"] == "excellent"


class TestMoonAvoidanceFormatting:
    """Tests for moon avoidance voice output formatting."""

    def test_format_below_horizon(self, ephemeris_service):
        """Format message when moon below horizon."""
        with patch.object(ephemeris_service, 'get_moon_avoidance_info') as mock_info:
            mock_info.return_value = {
                "moon_visible": False,
                "moon_altitude_deg": -10.0,
                "moon_azimuth_deg": 90.0,
                "moon_phase_percent": 50.0,
                "separation_deg": 45.0,
                "penalty_score": 0.0,
                "is_safe": True,
                "status": "below_horizon",
                "recommendation": "excellent",
            }

            msg = ephemeris_service.format_moon_avoidance_info(12.0, 30.0)
            assert "below the horizon" in msg
            assert "Excellent" in msg

    def test_format_close_to_target_warning(self, ephemeris_service):
        """Format warning when moon is close to target."""
        with patch.object(ephemeris_service, 'get_moon_avoidance_info') as mock_info:
            mock_info.return_value = {
                "moon_visible": True,
                "moon_altitude_deg": 50.0,
                "moon_azimuth_deg": 180.0,
                "moon_phase_percent": 90.0,
                "separation_deg": 15.0,
                "penalty_score": 0.8,
                "is_safe": False,
                "status": "close_to_target",
                "recommendation": "avoid",
            }

            msg = ephemeris_service.format_moon_avoidance_info(12.0, 30.0)
            assert "Warning" in msg
            assert "bright" in msg.lower()


# =============================================================================
# Observer Location Tests
# =============================================================================


class TestObserverLocation:
    """Tests for observer location handling."""

    def test_nevada_site_defaults(self):
        """Test default Nevada site coordinates."""
        from services.ephemeris.skyfield_service import ObserverLocation

        location = ObserverLocation.nevada_site()
        assert location.latitude == 39.0
        assert location.longitude == -117.0
        assert location.elevation_m == 1800
        assert "Nevada" in location.name


# =============================================================================
# Data Classes Tests
# =============================================================================


class TestPosition:
    """Tests for Position dataclass."""

    def test_ra_hms_format(self):
        """Test RA formatting in HH:MM:SS."""
        from services.ephemeris.skyfield_service import Position

        pos = Position(ra_hours=12.5, dec_degrees=45.0, distance_au=1.0)
        hms = pos.ra_hms
        assert hms.startswith("12:")

    def test_dec_dms_format_positive(self):
        """Test Dec formatting in +DD:MM:SS."""
        from services.ephemeris.skyfield_service import Position

        pos = Position(ra_hours=12.0, dec_degrees=45.5, distance_au=1.0)
        dms = pos.dec_dms
        assert dms.startswith("+45:")

    def test_dec_dms_format_negative(self):
        """Test Dec formatting in -DD:MM:SS."""
        from services.ephemeris.skyfield_service import Position

        pos = Position(ra_hours=12.0, dec_degrees=-30.25, distance_au=1.0)
        dms = pos.dec_dms
        assert dms.startswith("-30:")


class TestHorizontalPosition:
    """Tests for HorizontalPosition dataclass."""

    def test_is_visible_above_horizon(self):
        """Test visibility check when above horizon."""
        from services.ephemeris.skyfield_service import HorizontalPosition

        pos = HorizontalPosition(altitude_degrees=30.0, azimuth_degrees=180.0)
        assert pos.is_visible is True

    def test_is_visible_below_horizon(self):
        """Test visibility check when below horizon."""
        from services.ephemeris.skyfield_service import HorizontalPosition

        pos = HorizontalPosition(altitude_degrees=-10.0, azimuth_degrees=180.0)
        assert pos.is_visible is False

    def test_compass_direction_north(self):
        """Test compass direction for North."""
        from services.ephemeris.skyfield_service import HorizontalPosition

        pos = HorizontalPosition(altitude_degrees=30.0, azimuth_degrees=0.0)
        assert pos.compass_direction == "N"

    def test_compass_direction_south(self):
        """Test compass direction for South."""
        from services.ephemeris.skyfield_service import HorizontalPosition

        pos = HorizontalPosition(altitude_degrees=30.0, azimuth_degrees=180.0)
        assert pos.compass_direction == "S"

    def test_compass_direction_east(self):
        """Test compass direction for East."""
        from services.ephemeris.skyfield_service import HorizontalPosition

        pos = HorizontalPosition(altitude_degrees=30.0, azimuth_degrees=90.0)
        assert pos.compass_direction == "E"
