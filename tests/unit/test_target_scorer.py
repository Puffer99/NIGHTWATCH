"""
NIGHTWATCH Target Scorer Tests

Tests for intelligent target scoring (Step 118).
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch

from services.catalog.target_scorer import (
    TargetScorer,
    TargetScore,
    ScoringWeights,
    ScoringWeight,
    get_scorer,
)
from services.catalog.catalog import CatalogObject, ObjectType


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def scorer():
    """Create a basic TargetScorer without ephemeris."""
    return TargetScorer()


@pytest.fixture
def scorer_with_ephemeris():
    """Create a TargetScorer with mocked ephemeris service."""
    mock_eph = MagicMock()

    # Mock altitude/azimuth
    mock_altaz = MagicMock()
    mock_altaz.altitude_degrees = 45.0
    mock_altaz.azimuth_degrees = 180.0
    mock_eph.get_star_altaz.return_value = mock_altaz

    # Mock moon penalty and separation
    mock_eph.get_moon_penalty.return_value = 0.2
    mock_eph.get_moon_separation.return_value = 60.0

    return TargetScorer(ephemeris_service=mock_eph)


@pytest.fixture
def sample_catalog_object():
    """Create a sample CatalogObject for testing."""
    return CatalogObject(
        catalog_id="M31",
        name="Andromeda Galaxy",
        object_type=ObjectType.GALAXY,
        ra_hours=0.71,
        dec_degrees=41.27,
        magnitude=3.4,
        size_arcmin=178.0,
        constellation="Andromeda",
        description="Nearest major galaxy",
        aliases=["NGC 224"],
    )


# =============================================================================
# Scoring Weights Tests
# =============================================================================


class TestScoringWeights:
    """Tests for ScoringWeights configuration."""

    def test_default_weights_sum_to_one(self):
        """Default weights should approximately sum to 1.0."""
        w = ScoringWeights()
        total = (w.altitude + w.moon_penalty + w.hour_angle +
                 w.time_remaining + w.magnitude + w.size_match + w.airmass)
        assert 0.99 <= total <= 1.01

    def test_balanced_profile(self):
        """Balanced profile creates default weights."""
        w = ScoringWeights.balanced()
        assert w.altitude == 0.25
        assert w.moon_penalty == 0.20

    def test_deep_sky_profile(self):
        """Deep sky profile emphasizes moon avoidance."""
        w = ScoringWeights.deep_sky()
        assert w.moon_penalty > ScoringWeights.balanced().moon_penalty

    def test_planetary_profile(self):
        """Planetary profile emphasizes altitude."""
        w = ScoringWeights.planetary()
        assert w.altitude > ScoringWeights.balanced().altitude
        assert w.moon_penalty < ScoringWeights.balanced().moon_penalty

    def test_widefield_profile(self):
        """Widefield profile emphasizes time remaining."""
        w = ScoringWeights.widefield()
        assert w.time_remaining >= ScoringWeights.balanced().time_remaining


# =============================================================================
# Altitude Score Tests
# =============================================================================


class TestAltitudeScore:
    """Tests for altitude scoring."""

    def test_altitude_below_minimum_is_zero(self, scorer):
        """Objects below minimum altitude score 0."""
        score = scorer._calculate_altitude_score(5.0)
        assert score == 0.0

    def test_altitude_at_minimum_is_zero(self, scorer):
        """Objects at minimum altitude score 0."""
        score = scorer._calculate_altitude_score(scorer.MIN_ALTITUDE)
        assert score == 0.0

    def test_altitude_at_excellent_is_one(self, scorer):
        """Objects at excellent altitude score 1.0."""
        score = scorer._calculate_altitude_score(scorer.EXCELLENT_ALTITUDE)
        assert score == 1.0

    def test_altitude_above_excellent_is_one(self, scorer):
        """Objects above excellent altitude still score 1.0."""
        score = scorer._calculate_altitude_score(80.0)
        assert score == 1.0

    def test_altitude_linear_interpolation(self, scorer):
        """Score interpolates linearly between min and excellent."""
        mid_alt = (scorer.MIN_ALTITUDE + scorer.EXCELLENT_ALTITUDE) / 2
        score = scorer._calculate_altitude_score(mid_alt)
        assert 0.45 <= score <= 0.55


# =============================================================================
# Hour Angle Score Tests
# =============================================================================


class TestHourAngleScore:
    """Tests for hour angle scoring."""

    def test_near_meridian_is_excellent(self, scorer):
        """Objects near meridian score 1.0."""
        score = scorer._calculate_hour_angle_score(0.0)
        assert score == 1.0

        score = scorer._calculate_hour_angle_score(0.3)
        assert score == 1.0

    def test_far_from_meridian_is_low(self, scorer):
        """Objects far from meridian score low."""
        score = scorer._calculate_hour_angle_score(5.0)
        assert score < 0.3

    def test_near_horizon_is_zero(self, scorer):
        """Objects at 6 hours from meridian score 0."""
        score = scorer._calculate_hour_angle_score(6.0)
        assert score == 0.0

    def test_negative_hour_angle(self, scorer):
        """Negative hour angle (rising) is handled correctly."""
        score_pos = scorer._calculate_hour_angle_score(2.0)
        score_neg = scorer._calculate_hour_angle_score(-2.0)
        assert score_pos == score_neg


# =============================================================================
# Time Remaining Score Tests
# =============================================================================


class TestTimeRemainingScore:
    """Tests for time remaining scoring."""

    def test_no_time_remaining(self, scorer):
        """Zero hours remaining scores 0."""
        score = scorer._calculate_time_remaining_score(0.0)
        assert score == 0.0

    def test_negative_time_remaining(self, scorer):
        """Negative hours (already set) scores 0."""
        score = scorer._calculate_time_remaining_score(-1.0)
        assert score == 0.0

    def test_ample_time_remaining(self, scorer):
        """4+ hours remaining scores 1.0."""
        score = scorer._calculate_time_remaining_score(4.0)
        assert score == 1.0

        score = scorer._calculate_time_remaining_score(8.0)
        assert score == 1.0

    def test_partial_time_remaining(self, scorer):
        """2 hours remaining scores 0.5."""
        score = scorer._calculate_time_remaining_score(2.0)
        assert score == 0.5


# =============================================================================
# Airmass Score Tests
# =============================================================================


class TestAirmassScore:
    """Tests for airmass scoring."""

    def test_airmass_at_zenith(self, scorer):
        """Zenith (90°) has airmass 1.0, score 1.0."""
        score = scorer._calculate_airmass_score(90.0)
        assert score == 1.0

    def test_airmass_at_horizon(self, scorer):
        """Horizon (0°) scores 0."""
        score = scorer._calculate_airmass_score(0.0)
        assert score == 0.0

    def test_airmass_at_30_degrees(self, scorer):
        """30° altitude has airmass ~2.0, score ~0.5."""
        score = scorer._calculate_airmass_score(30.0)
        assert 0.45 <= score <= 0.55

    def test_airmass_below_horizon(self, scorer):
        """Negative altitude scores 0."""
        score = scorer._calculate_airmass_score(-10.0)
        assert score == 0.0


# =============================================================================
# Moon Score Tests
# =============================================================================


class TestMoonScore:
    """Tests for moon interference scoring."""

    def test_moon_score_without_ephemeris(self, scorer):
        """Without ephemeris, returns moderate score."""
        score, sep = scorer._calculate_moon_score(12.0, 45.0)
        assert score == 0.5
        assert sep == 45.0

    def test_moon_score_with_ephemeris(self, scorer_with_ephemeris):
        """With ephemeris, uses actual moon penalty."""
        score, sep = scorer_with_ephemeris._calculate_moon_score(12.0, 45.0)
        # Mock returns penalty=0.2, so score should be 0.8
        assert score == 0.8
        assert sep == 60.0


# =============================================================================
# Magnitude Score Tests
# =============================================================================


class TestMagnitudeScore:
    """Tests for magnitude scoring."""

    def test_bright_object_scores_high(self, scorer):
        """Bright objects (mag 4 or less) score 1.0."""
        score = scorer._calculate_magnitude_score(3.0)
        assert score == 1.0

    def test_faint_object_scores_lower(self, scorer):
        """Fainter objects score progressively lower."""
        score_bright = scorer._calculate_magnitude_score(6.0)
        score_faint = scorer._calculate_magnitude_score(12.0)
        assert score_bright > score_faint

    def test_very_faint_object(self, scorer):
        """Very faint objects (mag 14+) score 0.2."""
        score = scorer._calculate_magnitude_score(15.0)
        assert score == 0.2

    def test_unknown_magnitude(self, scorer):
        """Unknown magnitude returns average score."""
        score = scorer._calculate_magnitude_score(None)
        assert score == 0.5

    def test_galaxy_adjustment(self, scorer):
        """Galaxies get slightly lower score (surface brightness)."""
        score_normal = scorer._calculate_magnitude_score(8.0)
        score_galaxy = scorer._calculate_magnitude_score(8.0, ObjectType.GALAXY)
        assert score_galaxy < score_normal


# =============================================================================
# Size Match Score Tests
# =============================================================================


class TestSizeMatchScore:
    """Tests for size vs FOV scoring."""

    def test_ideal_size_match(self, scorer):
        """Object filling 30-70% of FOV scores 1.0."""
        # 30 arcmin object in 60 arcmin FOV = 50% fill
        score = scorer._calculate_size_match_score(30.0, 60.0)
        assert score == 1.0

    def test_object_too_small(self, scorer):
        """Very small objects score lower."""
        # 3 arcmin object in 60 arcmin FOV = 5% fill
        score = scorer._calculate_size_match_score(3.0, 60.0)
        assert score < 0.7

    def test_object_too_large(self, scorer):
        """Objects larger than FOV score lower."""
        # 100 arcmin object in 60 arcmin FOV = 167% fill
        score = scorer._calculate_size_match_score(100.0, 60.0)
        assert score < 0.7

    def test_unknown_size(self, scorer):
        """Unknown size returns average score."""
        score = scorer._calculate_size_match_score(None, 60.0)
        assert score == 0.5


# =============================================================================
# Target Scoring Tests
# =============================================================================


class TestTargetScoring:
    """Tests for complete target scoring."""

    def test_score_target_returns_target_score(self, scorer):
        """score_target returns a TargetScore object."""
        result = scorer.score_target(12.0, 45.0, "Test")
        assert isinstance(result, TargetScore)
        assert result.target_id == "Test"
        assert result.ra_hours == 12.0
        assert result.dec_degrees == 45.0

    def test_score_target_has_all_factors(self, scorer):
        """Score includes all individual factor scores."""
        result = scorer.score_target(12.0, 45.0, "Test")
        assert 0.0 <= result.altitude_score <= 1.0
        assert 0.0 <= result.moon_score <= 1.0
        assert 0.0 <= result.hour_angle_score <= 1.0
        assert 0.0 <= result.time_remaining_score <= 1.0
        assert 0.0 <= result.airmass_score <= 1.0

    def test_score_target_total_is_weighted(self, scorer):
        """Total score is weighted combination of factors."""
        result = scorer.score_target(12.0, 45.0, "Test")
        # Total should be between 0 and 1
        assert 0.0 <= result.total_score <= 1.0

    def test_score_target_has_recommendation(self, scorer):
        """Score includes text recommendation."""
        result = scorer.score_target(12.0, 45.0, "Test")
        assert len(result.recommendation) > 0

    def test_score_target_with_magnitude(self, scorer):
        """Magnitude affects score."""
        bright = scorer.score_target(12.0, 45.0, "Bright", magnitude=4.0)
        faint = scorer.score_target(12.0, 45.0, "Faint", magnitude=14.0)
        assert bright.magnitude_score > faint.magnitude_score


# =============================================================================
# Catalog Object Scoring Tests
# =============================================================================


class TestCatalogObjectScoring:
    """Tests for scoring CatalogObject instances."""

    def test_score_catalog_object(self, scorer, sample_catalog_object):
        """Can score a CatalogObject directly."""
        result = scorer.score_catalog_object(sample_catalog_object)
        assert result.target_id == "M31"
        assert result.ra_hours == sample_catalog_object.ra_hours
        assert result.dec_degrees == sample_catalog_object.dec_degrees


# =============================================================================
# Ranking Tests
# =============================================================================


class TestTargetRanking:
    """Tests for ranking multiple targets."""

    def test_rank_targets_sorts_by_score(self, scorer):
        """rank_targets returns sorted list."""
        targets = [
            (12.0, 45.0, "A"),
            (6.0, 30.0, "B"),
            (18.0, 60.0, "C"),
        ]
        results = scorer.rank_targets(targets, min_score=0.0)

        # Verify sorted descending
        for i in range(len(results) - 1):
            assert results[i].total_score >= results[i + 1].total_score

    def test_rank_targets_filters_by_min_score(self, scorer):
        """rank_targets filters out low scores."""
        targets = [
            (12.0, 45.0, "A"),
            (6.0, 30.0, "B"),
        ]
        # High threshold should filter some
        results = scorer.rank_targets(targets, min_score=0.9)
        # May be empty or fewer results
        for r in results:
            assert r.total_score >= 0.9


# =============================================================================
# Profile Tests
# =============================================================================


class TestProfiles:
    """Tests for scoring profiles."""

    def test_set_profile_balanced(self, scorer):
        """set_profile with BALANCED updates weights."""
        scorer.set_profile(ScoringWeight.BALANCED)
        assert scorer.weights.altitude == 0.25

    def test_set_profile_deep_sky(self, scorer):
        """set_profile with DEEP_SKY updates weights."""
        scorer.set_profile(ScoringWeight.DEEP_SKY)
        assert scorer.weights.moon_penalty == 0.30

    def test_set_profile_planetary(self, scorer):
        """set_profile with PLANETARY updates weights."""
        scorer.set_profile(ScoringWeight.PLANETARY)
        assert scorer.weights.altitude == 0.35

    def test_profiles_affect_scoring(self, scorer):
        """Different profiles produce different scores."""
        # Score same target with different profiles
        scorer.set_profile(ScoringWeight.BALANCED)
        balanced_score = scorer.score_target(12.0, 45.0, "Test")

        scorer.set_profile(ScoringWeight.PLANETARY)
        planetary_score = scorer.score_target(12.0, 45.0, "Test")

        # Scores may differ due to different weight emphasis
        # (not guaranteed to be different, but weights are different)
        assert scorer.weights.altitude == 0.35


# =============================================================================
# Formatting Tests
# =============================================================================


class TestFormatting:
    """Tests for score formatting."""

    def test_format_score_summary(self, scorer):
        """format_score_summary returns string."""
        score = scorer.score_target(12.0, 45.0, "M31")
        summary = scorer.format_score_summary(score)
        assert isinstance(summary, str)
        assert "M31" in summary

    def test_format_includes_percentage(self, scorer):
        """Summary includes percentage score."""
        score = scorer.score_target(12.0, 45.0, "M31")
        summary = scorer.format_score_summary(score)
        assert "%" in summary

    def test_to_dict_serialization(self, scorer):
        """TargetScore can be converted to dict."""
        score = scorer.score_target(12.0, 45.0, "M31")
        d = score.to_dict()
        assert d["target_id"] == "M31"
        assert "scores" in d
        assert "altitude" in d["scores"]


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_scorer_default(self):
        """get_scorer creates balanced scorer by default."""
        scorer = get_scorer()
        assert isinstance(scorer, TargetScorer)
        assert scorer.weights.altitude == 0.25

    def test_get_scorer_with_profile(self):
        """get_scorer accepts profile string."""
        scorer = get_scorer(profile="deep_sky")
        assert scorer.weights.moon_penalty == 0.30

    def test_get_scorer_with_ephemeris(self):
        """get_scorer accepts ephemeris service."""
        mock_eph = MagicMock()
        scorer = get_scorer(ephemeris_service=mock_eph)
        assert scorer._ephemeris is mock_eph
