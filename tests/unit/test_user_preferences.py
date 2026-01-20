"""
NIGHTWATCH User Preferences Tests

Tests for user preference learning and persistence (Step 131).
"""

import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from services.nlp.user_preferences import (
    UserPreferences,
    PreferenceCategory,
    ObservationStyle,
    CommunicationStyle,
    TargetPreference,
    ImagingPreference,
    get_user_preferences,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_prefs_path():
    """Create a temporary path for preferences file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_prefs.json"


@pytest.fixture
def prefs(temp_prefs_path):
    """Create a UserPreferences with temp storage."""
    return UserPreferences(prefs_path=temp_prefs_path)


@pytest.fixture
def prefs_with_data(prefs):
    """Create UserPreferences with some recorded data."""
    prefs.record_target_observation("M31", success=True, quality=0.9,
                                    object_type="galaxy", constellation="Andromeda")
    prefs.record_target_observation("M31", success=True, quality=0.85,
                                    object_type="galaxy")
    prefs.record_target_observation("M42", success=True, quality=0.8,
                                    object_type="nebula", constellation="Orion")
    prefs.record_target_observation("Jupiter", success=False, quality=0.3,
                                    object_type="planet")
    return prefs


# =============================================================================
# Enum Tests
# =============================================================================


class TestPreferenceCategory:
    """Tests for PreferenceCategory enum."""

    def test_all_categories_exist(self):
        """All expected categories are defined."""
        assert PreferenceCategory.TARGETS.value == "targets"
        assert PreferenceCategory.IMAGING.value == "imaging"
        assert PreferenceCategory.OBSERVATION_STYLE.value == "observation_style"
        assert PreferenceCategory.TIMING.value == "timing"
        assert PreferenceCategory.COMMUNICATION.value == "communication"


class TestObservationStyle:
    """Tests for ObservationStyle enum."""

    def test_all_styles_exist(self):
        """All expected styles are defined."""
        assert ObservationStyle.DEEP_SKY.value == "deep_sky"
        assert ObservationStyle.PLANETARY.value == "planetary"
        assert ObservationStyle.MIXED.value == "mixed"
        assert ObservationStyle.VISUAL.value == "visual"
        assert ObservationStyle.IMAGING.value == "imaging"
        assert ObservationStyle.UNKNOWN.value == "unknown"


class TestCommunicationStyle:
    """Tests for CommunicationStyle enum."""

    def test_all_styles_exist(self):
        """All expected styles are defined."""
        assert CommunicationStyle.CONCISE.value == "concise"
        assert CommunicationStyle.NORMAL.value == "normal"
        assert CommunicationStyle.VERBOSE.value == "verbose"
        assert CommunicationStyle.EXPERT.value == "expert"


# =============================================================================
# TargetPreference Tests
# =============================================================================


class TestTargetPreference:
    """Tests for TargetPreference dataclass."""

    def test_preference_creation(self):
        """Create a basic target preference."""
        pref = TargetPreference(target_id="M31")
        assert pref.target_id == "M31"
        assert pref.observation_count == 0

    def test_success_rate_calculation(self):
        """Success rate calculates correctly."""
        pref = TargetPreference(
            target_id="M31",
            observation_count=10,
            success_count=8,
        )
        assert pref.success_rate == 0.8

    def test_success_rate_zero_observations(self):
        """Success rate is 0 with no observations."""
        pref = TargetPreference(target_id="M31")
        assert pref.success_rate == 0.0

    def test_average_quality(self):
        """Average quality calculates correctly."""
        pref = TargetPreference(
            target_id="M31",
            success_count=4,
            total_quality=3.2,
        )
        assert pref.average_quality == 0.8

    def test_preference_score(self):
        """Preference score combines metrics."""
        pref = TargetPreference(
            target_id="M31",
            observation_count=5,
            success_count=4,
            total_quality=3.2,
        )
        score = pref.preference_score
        assert 0.0 <= score <= 1.0

    def test_to_dict(self):
        """Target preference converts to dict."""
        pref = TargetPreference(
            target_id="M31",
            observation_count=5,
            success_count=4,
        )
        d = pref.to_dict()
        assert d["target_id"] == "M31"
        assert d["observation_count"] == 5

    def test_from_dict(self):
        """Target preference creates from dict."""
        data = {
            "target_id": "M31",
            "observation_count": 5,
            "success_count": 4,
            "total_quality": 3.2,
            "last_observed": "2025-01-15T22:30:00",
            "total_exposure_time": 3600.0,
        }
        pref = TargetPreference.from_dict(data)
        assert pref.target_id == "M31"
        assert pref.observation_count == 5
        assert pref.last_observed is not None


# =============================================================================
# ImagingPreference Tests
# =============================================================================


class TestImagingPreference:
    """Tests for ImagingPreference dataclass."""

    def test_preference_creation(self):
        """Create imaging preference."""
        pref = ImagingPreference(object_type="galaxy")
        assert pref.object_type == "galaxy"

    def test_preferred_exposure(self):
        """Preferred exposure returns mode."""
        pref = ImagingPreference(
            object_type="galaxy",
            exposure_times=[60, 120, 120, 120, 180],
        )
        assert pref.preferred_exposure == 120

    def test_preferred_exposure_empty(self):
        """Preferred exposure returns None when empty."""
        pref = ImagingPreference(object_type="galaxy")
        assert pref.preferred_exposure is None

    def test_preferred_gain(self):
        """Preferred gain returns mode."""
        pref = ImagingPreference(
            object_type="galaxy",
            gain_values=[100, 200, 200, 300],
        )
        assert pref.preferred_gain == 200

    def test_preferred_binning(self):
        """Preferred binning returns mode."""
        pref = ImagingPreference(
            object_type="galaxy",
            binning_modes=["1x1", "1x1", "2x2"],
        )
        assert pref.preferred_binning == "1x1"

    def test_to_dict(self):
        """Imaging preference converts to dict."""
        pref = ImagingPreference(
            object_type="nebula",
            exposure_times=[60, 120],
        )
        d = pref.to_dict()
        assert d["object_type"] == "nebula"
        assert d["exposure_times"] == [60, 120]

    def test_from_dict(self):
        """Imaging preference creates from dict."""
        data = {
            "object_type": "nebula",
            "exposure_times": [60, 120, 180],
            "gain_values": [200],
            "binning_modes": ["1x1"],
            "filter_choices": ["L"],
        }
        pref = ImagingPreference.from_dict(data)
        assert pref.object_type == "nebula"
        assert len(pref.exposure_times) == 3


# =============================================================================
# Target Observation Tests
# =============================================================================


class TestTargetObservations:
    """Tests for target observation recording."""

    def test_record_observation(self, prefs):
        """Record a target observation."""
        prefs.record_target_observation("M31", success=True, quality=0.85)

        pref = prefs.get_target_preference("M31")
        assert pref is not None
        assert pref.observation_count == 1
        assert pref.success_count == 1

    def test_record_multiple_observations(self, prefs):
        """Multiple observations accumulate."""
        prefs.record_target_observation("M31", success=True, quality=0.9)
        prefs.record_target_observation("M31", success=True, quality=0.8)
        prefs.record_target_observation("M31", success=False, quality=0.3)

        pref = prefs.get_target_preference("M31")
        assert pref.observation_count == 3
        assert pref.success_count == 2

    def test_get_favorite_targets(self, prefs_with_data):
        """Get favorite targets by preference score."""
        favorites = prefs_with_data.get_favorite_targets(limit=5)

        # M31 should be first (2 successful obs)
        assert "M31" in favorites
        assert len(favorites) <= 5

    def test_favorite_object_types(self, prefs_with_data):
        """Get favorite object types."""
        types = prefs_with_data.get_favorite_object_types()

        # Galaxy should be most common
        assert len(types) > 0
        assert types[0][0] == "galaxy"

    def test_favorite_constellations(self, prefs_with_data):
        """Get favorite constellations."""
        constellations = prefs_with_data.get_favorite_constellations()

        assert len(constellations) > 0


# =============================================================================
# Imaging Preference Tests
# =============================================================================


class TestImagingPreferences:
    """Tests for imaging preference recording."""

    def test_record_exposure(self, prefs):
        """Record exposure setting."""
        prefs.record_exposure_setting(120, object_type="galaxy")
        prefs.record_exposure_setting(120, object_type="galaxy")
        prefs.record_exposure_setting(180, object_type="galaxy")

        exposure = prefs.get_preferred_exposure("galaxy")
        assert exposure == 120

    def test_record_gain(self, prefs):
        """Record gain setting."""
        prefs.record_gain_setting(200, object_type="nebula")
        prefs.record_gain_setting(200, object_type="nebula")

        gain = prefs.get_preferred_gain("nebula")
        assert gain == 200

    def test_record_binning(self, prefs):
        """Record binning setting."""
        prefs.record_binning_setting("1x1", object_type="planet")
        prefs.record_binning_setting("1x1", object_type="planet")

        binning = prefs.get_preferred_binning("planet")
        assert binning == "1x1"

    def test_record_filter(self, prefs):
        """Record filter choice."""
        prefs.record_filter_choice("Ha", object_type="nebula")

        imaging = prefs.get_imaging_preferences("nebula")
        assert "Ha" in imaging.filter_choices

    def test_fallback_to_default(self, prefs):
        """Preferences fall back to default type."""
        prefs.record_exposure_setting(60, object_type="default")

        # Query unknown type, should fall back
        exposure = prefs.get_preferred_exposure("unknown_type")
        assert exposure == 60


# =============================================================================
# Observation Style Tests
# =============================================================================


class TestObservationStyleLearning:
    """Tests for observation style learning."""

    def test_style_starts_unknown(self, prefs):
        """Style starts as unknown."""
        assert prefs.get_observation_style() == ObservationStyle.UNKNOWN

    def test_style_learned_deep_sky(self, prefs):
        """Style learns deep sky from observations."""
        for i in range(15):
            prefs.record_target_observation(f"NGC{i}", object_type="galaxy")

        style = prefs.get_observation_style()
        assert style == ObservationStyle.DEEP_SKY

    def test_style_learned_planetary(self, prefs):
        """Style learns planetary from observations."""
        for i in range(15):
            prefs.record_target_observation(f"Planet{i}", object_type="planet")

        style = prefs.get_observation_style()
        assert style == ObservationStyle.PLANETARY

    def test_style_mixed(self, prefs):
        """Style learns mixed from varied observations."""
        for i in range(10):
            prefs.record_target_observation(f"NGC{i}", object_type="galaxy")
        for i in range(8):
            prefs.record_target_observation(f"Planet{i}", object_type="planet")

        style = prefs.get_observation_style()
        assert style == ObservationStyle.MIXED

    def test_set_style_explicit(self, prefs):
        """Style can be set explicitly."""
        prefs.set_observation_style(ObservationStyle.IMAGING)
        assert prefs.get_observation_style() == ObservationStyle.IMAGING


# =============================================================================
# Communication Preference Tests
# =============================================================================


class TestCommunicationPreferences:
    """Tests for communication preferences."""

    def test_default_communication_style(self, prefs):
        """Default communication style is normal."""
        assert prefs.get_communication_style() == CommunicationStyle.NORMAL

    def test_set_communication_style(self, prefs):
        """Communication style can be set."""
        prefs.set_communication_style(CommunicationStyle.EXPERT)
        assert prefs.get_communication_style() == CommunicationStyle.EXPERT

    def test_default_confirmation_level(self, prefs):
        """Default confirmation level is 0.5."""
        assert prefs.get_confirmation_level() == 0.5

    def test_set_confirmation_level(self, prefs):
        """Confirmation level can be set."""
        prefs.set_confirmation_level(0.8)
        assert prefs.get_confirmation_level() == 0.8

    def test_confirmation_level_clamped(self, prefs):
        """Confirmation level is clamped to 0-1."""
        prefs.set_confirmation_level(1.5)
        assert prefs.get_confirmation_level() == 1.0

        prefs.set_confirmation_level(-0.5)
        assert prefs.get_confirmation_level() == 0.0

    def test_should_confirm_high_risk(self, prefs):
        """High risk actions always confirm."""
        assert prefs.should_confirm_action(action_risk=0.95) is True

    def test_should_confirm_low_risk(self, prefs):
        """Low risk actions respect preference."""
        prefs.set_confirmation_level(0.3)  # Low confirmation preference
        assert prefs.should_confirm_action(action_risk=0.2) is False


# =============================================================================
# Session Timing Tests
# =============================================================================


class TestSessionTiming:
    """Tests for session timing preferences."""

    def test_record_session_duration(self, prefs):
        """Record session duration."""
        prefs.record_session_duration(120)
        prefs.record_session_duration(180)
        prefs.record_session_duration(150)

        typical = prefs.get_typical_session_duration()
        assert typical == 150  # Average

    def test_record_start_time(self, prefs):
        """Record session start time."""
        prefs.record_session_start_time(21)  # 9 PM
        prefs.record_session_start_time(21)
        prefs.record_session_start_time(22)

        preferred = prefs.get_preferred_start_time()
        assert preferred == 21

    def test_no_timing_data(self, prefs):
        """No timing data returns None."""
        assert prefs.get_typical_session_duration() is None
        assert prefs.get_preferred_start_time() is None


# =============================================================================
# Persistence Tests
# =============================================================================


class TestPersistence:
    """Tests for preference persistence."""

    def test_preferences_saved(self, temp_prefs_path):
        """Preferences are saved to disk."""
        prefs = UserPreferences(prefs_path=temp_prefs_path)
        prefs.record_target_observation("M31", success=True, quality=0.9)

        # File should exist
        assert temp_prefs_path.exists()

    def test_preferences_loaded(self, temp_prefs_path):
        """Preferences are loaded from disk."""
        # Create and save
        prefs1 = UserPreferences(prefs_path=temp_prefs_path)
        prefs1.record_target_observation("M31", success=True, quality=0.9)
        prefs1.set_communication_style(CommunicationStyle.VERBOSE)

        # Create new instance, should load
        prefs2 = UserPreferences(prefs_path=temp_prefs_path)

        assert prefs2.get_target_preference("M31") is not None
        assert prefs2.get_communication_style() == CommunicationStyle.VERBOSE

    def test_reset_preferences(self, prefs):
        """Reset clears all preferences."""
        prefs.record_target_observation("M31", success=True, quality=0.9)
        prefs.set_communication_style(CommunicationStyle.EXPERT)

        prefs.reset()

        assert prefs.get_target_preference("M31") is None
        assert prefs.get_communication_style() == CommunicationStyle.NORMAL


# =============================================================================
# Summary and Export Tests
# =============================================================================


class TestSummaryExport:
    """Tests for summary and export functions."""

    def test_get_summary(self, prefs_with_data):
        """Get preference summary."""
        summary = prefs_with_data.get_summary()

        assert "total_observations" in summary
        assert "unique_targets" in summary
        assert "favorite_targets" in summary
        assert summary["total_observations"] == 4

    def test_to_dict(self, prefs_with_data):
        """Export preferences to dict."""
        d = prefs_with_data.to_dict()

        assert "target_prefs" in d
        assert "imaging_prefs" in d
        assert "observation_style" in d
        assert "M31" in d["target_prefs"]


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunction:
    """Tests for module-level factory."""

    def test_get_user_preferences_returns_singleton(self):
        """get_user_preferences returns same instance."""
        p1 = get_user_preferences()
        p2 = get_user_preferences()
        assert p1 is p2

    def test_get_user_preferences_creates_instance(self):
        """get_user_preferences creates instance."""
        prefs = get_user_preferences()
        assert isinstance(prefs, UserPreferences)
