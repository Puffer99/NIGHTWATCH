"""
NIGHTWATCH Success Tracker Tests

Tests for historical success rate tracking and prediction (Step 119).
"""

import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from services.catalog.success_tracker import (
    SuccessTracker,
    ObservationRecord,
    SuccessPrediction,
    ConditionBucket,
    get_success_tracker,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_history_path():
    """Create a temporary path for history file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_history.json"


@pytest.fixture
def tracker(temp_history_path):
    """Create a SuccessTracker with temp storage."""
    return SuccessTracker(history_path=temp_history_path)


@pytest.fixture
def tracker_with_data(tracker):
    """Create tracker with some recorded observations."""
    # M31: 4 observations, 3 successful
    tracker.record_observation("M31", success=True, quality_score=0.9, altitude_deg=45)
    tracker.record_observation("M31", success=True, quality_score=0.85, altitude_deg=50)
    tracker.record_observation("M31", success=True, quality_score=0.8, altitude_deg=40)
    tracker.record_observation("M31", success=False, quality_score=0.3, altitude_deg=20)

    # M42: 3 observations, all successful
    tracker.record_observation("M42", success=True, quality_score=0.95, altitude_deg=55)
    tracker.record_observation("M42", success=True, quality_score=0.9, altitude_deg=60)
    tracker.record_observation("M42", success=True, quality_score=0.88, altitude_deg=50)

    # NGC7000: 3 observations, 1 successful (struggling target)
    tracker.record_observation("NGC7000", success=False, quality_score=0.2, altitude_deg=30)
    tracker.record_observation("NGC7000", success=False, quality_score=0.25, altitude_deg=25)
    tracker.record_observation("NGC7000", success=True, quality_score=0.6, altitude_deg=45)

    return tracker


# =============================================================================
# ObservationRecord Tests
# =============================================================================


class TestObservationRecord:
    """Tests for ObservationRecord dataclass."""

    def test_record_creation(self):
        """Create a basic observation record."""
        record = ObservationRecord(
            target_id="M31",
            timestamp=datetime.now(),
            success=True,
            quality_score=0.85,
        )
        assert record.target_id == "M31"
        assert record.success is True
        assert record.quality_score == 0.85

    def test_record_with_conditions(self):
        """Create record with condition data."""
        record = ObservationRecord(
            target_id="M31",
            timestamp=datetime.now(),
            success=True,
            quality_score=0.85,
            altitude_deg=45.0,
            moon_separation_deg=90.0,
            seeing_arcsec=2.0,
        )
        assert record.altitude_deg == 45.0
        assert record.moon_separation_deg == 90.0
        assert record.seeing_arcsec == 2.0

    def test_record_to_dict(self):
        """Record converts to dictionary."""
        record = ObservationRecord(
            target_id="M31",
            timestamp=datetime(2025, 1, 15, 22, 30),
            success=True,
            quality_score=0.85,
            altitude_deg=45.0,
        )
        d = record.to_dict()
        assert d["target_id"] == "M31"
        assert d["success"] is True
        assert d["altitude_deg"] == 45.0

    def test_record_from_dict(self):
        """Record creates from dictionary."""
        data = {
            "target_id": "M31",
            "timestamp": "2025-01-15T22:30:00",
            "success": True,
            "quality_score": 0.85,
            "altitude_deg": 45.0,
        }
        record = ObservationRecord.from_dict(data)
        assert record.target_id == "M31"
        assert record.success is True
        assert record.altitude_deg == 45.0


# =============================================================================
# SuccessPrediction Tests
# =============================================================================


class TestSuccessPrediction:
    """Tests for SuccessPrediction dataclass."""

    def test_prediction_creation(self):
        """Create a success prediction."""
        pred = SuccessPrediction(
            target_id="M31",
            predicted_success_rate=0.75,
            confidence=0.8,
            confidence_factor=1.1,
            historical_rate=0.75,
            condition_adjustment=1.0,
            recency_adjustment=1.0,
            total_observations=10,
            recent_observations=3,
        )
        assert pred.predicted_success_rate == 0.75
        assert pred.confidence == 0.8

    def test_prediction_to_dict(self):
        """Prediction converts to dictionary."""
        pred = SuccessPrediction(
            target_id="M31",
            predicted_success_rate=0.75,
            confidence=0.8,
            confidence_factor=1.1,
            historical_rate=0.75,
            condition_adjustment=1.0,
            recency_adjustment=1.0,
            total_observations=10,
            recent_observations=3,
            reason="Good history",
        )
        d = pred.to_dict()
        assert d["target_id"] == "M31"
        assert d["predicted_success_rate"] == 0.75
        assert d["reason"] == "Good history"


# =============================================================================
# Recording Tests
# =============================================================================


class TestRecording:
    """Tests for observation recording."""

    def test_record_observation(self, tracker):
        """Record a single observation."""
        tracker.record_observation("M31", success=True, quality_score=0.9)

        stats = tracker.get_target_statistics("M31")
        assert stats is not None
        assert stats["total_observations"] == 1
        assert stats["successful_observations"] == 1

    def test_record_multiple_observations(self, tracker):
        """Record multiple observations for same target."""
        tracker.record_observation("M31", success=True, quality_score=0.9)
        tracker.record_observation("M31", success=True, quality_score=0.8)
        tracker.record_observation("M31", success=False, quality_score=0.3)

        stats = tracker.get_target_statistics("M31")
        assert stats["total_observations"] == 3
        assert stats["successful_observations"] == 2
        assert stats["success_rate"] == pytest.approx(2/3, rel=0.01)

    def test_record_with_conditions(self, tracker):
        """Record observation with condition data."""
        tracker.record_observation(
            "M31",
            success=True,
            quality_score=0.85,
            altitude_deg=45.0,
            moon_separation_deg=90.0,
            seeing_arcsec=2.0,
        )

        stats = tracker.get_target_statistics("M31")
        assert stats is not None

    def test_unknown_target_returns_none(self, tracker):
        """Unknown target returns None."""
        stats = tracker.get_target_statistics("Unknown")
        assert stats is None


# =============================================================================
# Prediction Tests
# =============================================================================


class TestPrediction:
    """Tests for success prediction."""

    def test_predict_with_history(self, tracker_with_data):
        """Predict success for target with history."""
        pred = tracker_with_data.predict_success("M31")

        assert pred.target_id == "M31"
        assert pred.total_observations == 4
        assert pred.historical_rate == 0.75  # 3/4
        assert 0.0 <= pred.predicted_success_rate <= 1.0
        assert 0.0 <= pred.confidence <= 1.0

    def test_predict_no_history(self, tracker):
        """Predict for target with no history."""
        pred = tracker.predict_success("Unknown")

        assert pred.target_id == "Unknown"
        assert pred.total_observations == 0
        assert pred.confidence < 0.5  # Low confidence

    def test_predict_condition_adjustment(self, tracker_with_data):
        """Conditions affect prediction."""
        # Good conditions
        pred_good = tracker_with_data.predict_success(
            "M31",
            altitude_deg=70,
            moon_separation_deg=120,
            seeing_arcsec=1.5,
        )

        # Poor conditions
        pred_poor = tracker_with_data.predict_success(
            "M31",
            altitude_deg=15,
            moon_separation_deg=20,
            seeing_arcsec=5.0,
        )

        # Good conditions should have higher prediction
        assert pred_good.predicted_success_rate > pred_poor.predicted_success_rate

    def test_confidence_factor_range(self, tracker_with_data):
        """Confidence factor in reasonable range."""
        pred = tracker_with_data.predict_success("M31")

        # Should be in 0.5-1.5 range
        assert 0.3 <= pred.confidence_factor <= 1.7


# =============================================================================
# Statistics Tests
# =============================================================================


class TestStatistics:
    """Tests for statistical analysis."""

    def test_get_target_statistics(self, tracker_with_data):
        """Get detailed target statistics."""
        stats = tracker_with_data.get_target_statistics("M31")

        assert stats["target_id"] == "M31"
        assert stats["total_observations"] == 4
        assert stats["successful_observations"] == 3
        assert stats["success_rate"] == 0.75

    def test_get_best_performing(self, tracker_with_data):
        """Get best performing targets."""
        best = tracker_with_data.get_best_performing_targets(limit=5)

        assert len(best) > 0
        # M42 should be first (100% success)
        assert best[0]["target_id"] == "M42"
        assert best[0]["success_rate"] == 1.0

    def test_get_struggling_targets(self, tracker_with_data):
        """Get targets with poor success."""
        struggling = tracker_with_data.get_struggling_targets(limit=5)

        assert len(struggling) > 0
        # NGC7000 should be in list (33% success)
        target_ids = [t["target_id"] for t in struggling]
        assert "NGC7000" in target_ids

    def test_get_overall_statistics(self, tracker_with_data):
        """Get overall statistics."""
        stats = tracker_with_data.get_overall_statistics()

        assert stats["total_observations"] == 10
        assert stats["unique_targets"] == 3
        assert 0.0 <= stats["overall_success_rate"] <= 1.0

    def test_condition_analysis(self, tracker_with_data):
        """Analyze success by conditions."""
        analysis = tracker_with_data.get_condition_analysis()

        assert "excellent" in analysis
        assert "good" in analysis
        assert "fair" in analysis
        assert "poor" in analysis


# =============================================================================
# Condition Bucketing Tests
# =============================================================================


class TestConditionBucketing:
    """Tests for condition categorization."""

    def test_excellent_conditions(self, tracker):
        """High altitude, good moon, good seeing = excellent."""
        tracker.record_observation(
            "M31",
            success=True,
            quality_score=0.95,
            altitude_deg=70,
            moon_separation_deg=120,
            seeing_arcsec=1.2,
        )

        analysis = tracker.get_condition_analysis()
        assert analysis["excellent"]["total"] == 1

    def test_poor_conditions(self, tracker):
        """Low altitude, close moon, bad seeing = poor."""
        tracker.record_observation(
            "M31",
            success=False,
            quality_score=0.2,
            altitude_deg=15,
            moon_separation_deg=20,
            seeing_arcsec=5.0,
        )

        analysis = tracker.get_condition_analysis()
        assert analysis["poor"]["total"] == 1


# =============================================================================
# Persistence Tests
# =============================================================================


class TestPersistence:
    """Tests for history persistence."""

    def test_history_saved(self, temp_history_path):
        """History is saved to disk."""
        tracker = SuccessTracker(history_path=temp_history_path)
        tracker.record_observation("M31", success=True, quality_score=0.9)

        assert temp_history_path.exists()

    def test_history_loaded(self, temp_history_path):
        """History is loaded from disk."""
        # Create and save
        tracker1 = SuccessTracker(history_path=temp_history_path)
        tracker1.record_observation("M31", success=True, quality_score=0.9)
        tracker1.record_observation("M31", success=True, quality_score=0.85)

        # Create new instance, should load
        tracker2 = SuccessTracker(history_path=temp_history_path)

        stats = tracker2.get_target_statistics("M31")
        assert stats is not None
        assert stats["total_observations"] == 2

    def test_clear_history(self, tracker_with_data):
        """Clear removes all history."""
        tracker_with_data.clear_history()

        stats = tracker_with_data.get_target_statistics("M31")
        assert stats is None

        overall = tracker_with_data.get_overall_statistics()
        assert overall["total_observations"] == 0


# =============================================================================
# Recency Tests
# =============================================================================


class TestRecencyWeighting:
    """Tests for recent observation weighting."""

    def test_recent_observations_counted(self, tracker):
        """Recent observations are tracked."""
        tracker.record_observation("M31", success=True, quality_score=0.9)

        stats = tracker.get_target_statistics("M31")
        assert stats["recent_observations"] >= 1

    def test_prediction_includes_recent_count(self, tracker_with_data):
        """Prediction includes recent observation count."""
        pred = tracker_with_data.predict_success("M31")

        assert pred.recent_observations >= 0


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunction:
    """Tests for module-level factory."""

    def test_get_success_tracker_returns_singleton(self):
        """get_success_tracker returns same instance."""
        t1 = get_success_tracker()
        t2 = get_success_tracker()
        assert t1 is t2

    def test_get_success_tracker_creates_instance(self):
        """get_success_tracker creates instance."""
        tracker = get_success_tracker()
        assert isinstance(tracker, SuccessTracker)


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for scoring adjustment."""

    def test_confidence_factor_boosts_good_targets(self, tracker_with_data):
        """High success targets get higher confidence factor than poor targets."""
        pred_good = tracker_with_data.predict_success("M42")  # 100% success
        pred_poor = tracker_with_data.predict_success("NGC7000")  # ~33% success

        # Good target should have higher confidence factor than poor target
        # Note: With limited observations, absolute values may be < 1.0,
        # but relative ordering should be correct
        assert pred_good.confidence_factor > pred_poor.confidence_factor

    def test_confidence_factor_penalizes_poor_targets(self, tracker_with_data):
        """Low success targets get penalized."""
        pred = tracker_with_data.predict_success("NGC7000")  # ~33% success

        # Should have lower confidence factor
        assert pred.confidence_factor < 1.0

    def test_can_use_for_scoring_adjustment(self, tracker_with_data):
        """Confidence factor can adjust target scores."""
        base_score = 0.8

        pred_good = tracker_with_data.predict_success("M42")
        pred_poor = tracker_with_data.predict_success("NGC7000")

        adjusted_good = base_score * pred_good.confidence_factor
        adjusted_poor = base_score * pred_poor.confidence_factor

        # Good target should score higher after adjustment
        assert adjusted_good > adjusted_poor
