"""
NIGHTWATCH Session Narrator Tests

Tests for voice-friendly session narration service.
"""

import pytest
from datetime import datetime, timedelta

from services.nlp.session_narrator import (
    SessionNarrator,
    NarrationStyle,
    SessionPhase,
    NarratedTarget,
    SessionNarration,
    SessionState,
    get_narrator,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def narrator():
    """Create a SessionNarrator."""
    return SessionNarrator()


@pytest.fixture
def sample_schedule():
    """Create a sample schedule result dict."""
    now = datetime.now()
    return {
        "targets": [
            {
                "target_id": "M31",
                "target_name": "Andromeda Galaxy",
                "scheduled_start": now.isoformat(),
                "scheduled_end": (now + timedelta(hours=1)).isoformat(),
                "expected_altitude_deg": 55.0,
                "quality": "excellent",
                "score": 0.9,
                "reasons": ["optimal_altitude", "moon_avoidance"],
            },
            {
                "target_id": "M42",
                "target_name": "Orion Nebula",
                "scheduled_start": (now + timedelta(hours=1, minutes=5)).isoformat(),
                "scheduled_end": (now + timedelta(hours=2, minutes=5)).isoformat(),
                "expected_altitude_deg": 45.0,
                "quality": "good",
                "score": 0.8,
                "reasons": ["weather_window"],
            },
            {
                "target_id": "M45",
                "target_name": "Pleiades",
                "scheduled_start": (now + timedelta(hours=2, minutes=10)).isoformat(),
                "scheduled_end": (now + timedelta(hours=3)).isoformat(),
                "expected_altitude_deg": 60.0,
                "quality": "excellent",
                "score": 0.85,
                "reasons": ["optimal_altitude", "user_preference"],
            },
        ],
        "total_observation_minutes": 170.0,
    }


@pytest.fixture
def loaded_narrator(narrator, sample_schedule):
    """Create narrator with loaded schedule."""
    narrator.load_schedule(sample_schedule)
    return narrator


# =============================================================================
# NarrationStyle Tests
# =============================================================================


class TestNarrationStyle:
    """Tests for NarrationStyle enum."""

    def test_style_values(self):
        """All styles have correct values."""
        assert NarrationStyle.BRIEF.value == "brief"
        assert NarrationStyle.STANDARD.value == "standard"
        assert NarrationStyle.VERBOSE.value == "verbose"


# =============================================================================
# SessionPhase Tests
# =============================================================================


class TestSessionPhase:
    """Tests for SessionPhase enum."""

    def test_phase_values(self):
        """All phases have correct values."""
        assert SessionPhase.PLANNING.value == "planning"
        assert SessionPhase.STARTING.value == "starting"
        assert SessionPhase.OBSERVING.value == "observing"
        assert SessionPhase.TRANSITIONING.value == "transitioning"
        assert SessionPhase.PAUSED.value == "paused"
        assert SessionPhase.ENDING.value == "ending"
        assert SessionPhase.COMPLETE.value == "complete"


# =============================================================================
# NarratedTarget Tests
# =============================================================================


class TestNarratedTarget:
    """Tests for NarratedTarget dataclass."""

    def test_target_creation(self):
        """Create a narrated target."""
        now = datetime.now()
        target = NarratedTarget(
            target_id="M31",
            target_name="Andromeda Galaxy",
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=1),
            altitude_deg=55.0,
            quality="excellent",
            score=0.9,
        )

        assert target.target_id == "M31"
        assert target.target_name == "Andromeda Galaxy"
        assert target.quality == "excellent"

    def test_display_name_with_name(self):
        """Display name uses target_name when available."""
        now = datetime.now()
        target = NarratedTarget(
            target_id="M31",
            target_name="Andromeda Galaxy",
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=1),
            altitude_deg=55.0,
            quality="good",
            score=0.8,
        )

        assert target.display_name == "Andromeda Galaxy"

    def test_display_name_without_name(self):
        """Display name falls back to target_id."""
        now = datetime.now()
        target = NarratedTarget(
            target_id="NGC1234",
            target_name=None,
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=1),
            altitude_deg=40.0,
            quality="fair",
            score=0.6,
        )

        assert target.display_name == "NGC1234"

    def test_scheduled_duration(self):
        """Scheduled duration calculated correctly."""
        now = datetime.now()
        target = NarratedTarget(
            target_id="M31",
            target_name=None,
            scheduled_start=now,
            scheduled_end=now + timedelta(minutes=45),
            altitude_deg=50.0,
            quality="good",
            score=0.75,
        )

        assert target.scheduled_duration_minutes == 45.0

    def test_actual_duration_when_completed(self):
        """Actual duration available when completed."""
        now = datetime.now()
        target = NarratedTarget(
            target_id="M31",
            target_name=None,
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=1),
            altitude_deg=50.0,
            quality="good",
            score=0.75,
            actual_start=now,
            actual_end=now + timedelta(minutes=50),
        )

        assert target.actual_duration_minutes == 50.0

    def test_actual_duration_none_when_incomplete(self):
        """Actual duration is None when not completed."""
        now = datetime.now()
        target = NarratedTarget(
            target_id="M31",
            target_name=None,
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=1),
            altitude_deg=50.0,
            quality="good",
            score=0.75,
        )

        assert target.actual_duration_minutes is None


# =============================================================================
# SessionState Tests
# =============================================================================


class TestSessionState:
    """Tests for SessionState dataclass."""

    def test_default_state(self):
        """Default state is planning phase."""
        state = SessionState()

        assert state.phase == SessionPhase.PLANNING
        assert state.targets == []
        assert state.current_target_index == -1

    def test_current_target_with_valid_index(self):
        """Current target returned when index is valid."""
        now = datetime.now()
        targets = [
            NarratedTarget(
                target_id="M31",
                target_name=None,
                scheduled_start=now,
                scheduled_end=now + timedelta(hours=1),
                altitude_deg=50.0,
                quality="good",
                score=0.8,
            )
        ]

        state = SessionState(targets=targets, current_target_index=0)
        assert state.current_target.target_id == "M31"

    def test_current_target_none_with_invalid_index(self):
        """Current target is None when index invalid."""
        state = SessionState(current_target_index=-1)
        assert state.current_target is None

    def test_targets_completed_count(self):
        """Count completed targets correctly."""
        now = datetime.now()
        targets = [
            NarratedTarget(
                target_id="M31",
                target_name=None,
                scheduled_start=now,
                scheduled_end=now + timedelta(hours=1),
                altitude_deg=50.0,
                quality="good",
                score=0.8,
                is_completed=True,
            ),
            NarratedTarget(
                target_id="M42",
                target_name=None,
                scheduled_start=now,
                scheduled_end=now + timedelta(hours=1),
                altitude_deg=45.0,
                quality="good",
                score=0.7,
                is_completed=False,
            ),
        ]

        state = SessionState(targets=targets)
        assert state.targets_completed == 1
        assert state.targets_remaining == 1


# =============================================================================
# Load Schedule Tests
# =============================================================================


class TestLoadSchedule:
    """Tests for loading schedules."""

    def test_load_schedule(self, narrator, sample_schedule):
        """Load schedule from dict."""
        narrator.load_schedule(sample_schedule)

        assert len(narrator.state.targets) == 3
        assert narrator.state.phase == SessionPhase.PLANNING

    def test_loaded_targets_have_data(self, loaded_narrator):
        """Loaded targets have correct data."""
        targets = loaded_narrator.state.targets

        assert targets[0].target_id == "M31"
        assert targets[0].target_name == "Andromeda Galaxy"
        assert targets[0].quality == "excellent"
        assert targets[0].altitude_deg == 55.0

    def test_loaded_targets_have_reasons(self, loaded_narrator):
        """Loaded targets preserve reasons."""
        target = loaded_narrator.state.targets[0]

        assert "optimal_altitude" in target.reasons
        assert "moon_avoidance" in target.reasons


# =============================================================================
# Plan Narration Tests
# =============================================================================


class TestNarratePlan:
    """Tests for plan narration."""

    def test_narrate_empty_plan(self, narrator):
        """Narrate handles empty schedule."""
        narration = narrator.narrate_plan()

        assert "No targets" in narration.text
        assert narration.phase == SessionPhase.PLANNING

    def test_narrate_plan_brief(self, loaded_narrator):
        """Brief plan narration includes count and duration."""
        narration = loaded_narrator.narrate_plan(NarrationStyle.BRIEF)

        assert "3" in narration.text  # target count
        assert narration.style == NarrationStyle.BRIEF

    def test_narrate_plan_standard(self, loaded_narrator):
        """Standard plan narration includes target names."""
        narration = loaded_narrator.narrate_plan(NarrationStyle.STANDARD)

        assert "3" in narration.text
        assert narration.style == NarrationStyle.STANDARD

    def test_narrate_plan_verbose(self, loaded_narrator):
        """Verbose plan narration includes first target preview."""
        narration = loaded_narrator.narrate_plan(NarrationStyle.VERBOSE)

        assert "Andromeda" in narration.text or "M31" in narration.text
        assert narration.style == NarrationStyle.VERBOSE

    def test_narration_recorded_in_history(self, loaded_narrator):
        """Narration added to history."""
        loaded_narrator.narrate_plan()

        history = loaded_narrator.get_history()
        assert len(history) == 1


# =============================================================================
# Target Start Narration Tests
# =============================================================================


class TestNarrateTargetStart:
    """Tests for target start narration."""

    def test_narrate_first_target(self, loaded_narrator):
        """Narrate starting first target."""
        narration = loaded_narrator.narrate_target_start(0)

        assert "Andromeda" in narration.text or "M31" in narration.text
        assert narration.target_id == "M31"

    def test_first_target_updates_state(self, loaded_narrator):
        """Starting first target updates session state."""
        loaded_narrator.narrate_target_start(0)

        assert loaded_narrator.state.current_target_index == 0
        assert loaded_narrator.state.session_start is not None
        assert loaded_narrator.state.current_target.is_current

    def test_narrate_subsequent_target(self, loaded_narrator):
        """Narrate transitioning to next target."""
        loaded_narrator.narrate_target_start(0)
        loaded_narrator.state.targets[0].is_completed = True

        narration = loaded_narrator.narrate_target_start(1)

        assert "Orion" in narration.text or "M42" in narration.text
        assert loaded_narrator.state.phase == SessionPhase.OBSERVING

    def test_narrate_invalid_index(self, loaded_narrator):
        """Handle invalid target index."""
        narration = loaded_narrator.narrate_target_start(99)

        assert "No target" in narration.text

    def test_brief_style_concise(self, loaded_narrator):
        """Brief style produces short narration."""
        narration = loaded_narrator.narrate_target_start(0, NarrationStyle.BRIEF)

        assert len(narration.text) < 50

    def test_verbose_includes_details(self, loaded_narrator):
        """Verbose style includes altitude and duration."""
        narration = loaded_narrator.narrate_target_start(0, NarrationStyle.VERBOSE)

        # Should include altitude or duration info
        assert "55" in narration.text or "altitude" in narration.text.lower() or "hour" in narration.text


# =============================================================================
# Target Complete Narration Tests
# =============================================================================


class TestNarrateTargetComplete:
    """Tests for target completion narration."""

    def test_complete_without_active_target(self, loaded_narrator):
        """Handle completion when no target active."""
        narration = loaded_narrator.narrate_target_complete()

        assert "No target" in narration.text

    def test_complete_first_target(self, loaded_narrator):
        """Complete first target narration."""
        loaded_narrator.narrate_target_start(0)
        narration = loaded_narrator.narrate_target_complete()

        assert "complete" in narration.text.lower()
        assert "2" in narration.text  # remaining targets

    def test_completion_updates_state(self, loaded_narrator):
        """Completing target updates state."""
        loaded_narrator.narrate_target_start(0)
        loaded_narrator.narrate_target_complete()

        target = loaded_narrator.state.targets[0]
        assert target.is_completed
        assert not target.is_current
        assert target.actual_end is not None

    def test_complete_last_target(self, loaded_narrator):
        """Complete last target mentions session end."""
        # Complete all targets
        for i in range(3):
            loaded_narrator.narrate_target_start(i)
            loaded_narrator.narrate_target_complete()

        # Get last completion narration
        history = loaded_narrator.get_history()
        last_complete = [n for n in history if "complete" in n.text.lower()][-1]

        assert "last" in last_complete.text.lower() or "finish" in last_complete.text.lower() or "0" in last_complete.text

    def test_complete_with_notes(self, loaded_narrator):
        """Completion can include observer notes."""
        loaded_narrator.narrate_target_start(0)
        narration = loaded_narrator.narrate_target_complete(
            style=NarrationStyle.VERBOSE,
            notes="Excellent seeing conditions"
        )

        assert "Excellent seeing" in narration.text


# =============================================================================
# Progress Narration Tests
# =============================================================================


class TestNarrateProgress:
    """Tests for progress narration."""

    def test_progress_no_session(self, narrator):
        """Progress with no active session."""
        narration = narrator.narrate_progress()

        assert "No observing session" in narration.text

    def test_progress_during_session(self, loaded_narrator):
        """Progress update during active session."""
        loaded_narrator.narrate_target_start(0)
        loaded_narrator.narrate_target_complete()
        loaded_narrator.narrate_target_start(1)

        narration = loaded_narrator.narrate_progress()

        assert "1" in narration.text  # completed count
        assert "3" in narration.text  # total count

    def test_progress_includes_percentage(self, loaded_narrator):
        """Standard progress includes percentage."""
        loaded_narrator.narrate_target_start(0)
        loaded_narrator.narrate_target_complete()

        narration = loaded_narrator.narrate_progress(NarrationStyle.STANDARD)

        assert "%" in narration.text or "33" in narration.text

    def test_progress_verbose_includes_current(self, loaded_narrator):
        """Verbose progress mentions current target."""
        loaded_narrator.narrate_target_start(0)

        narration = loaded_narrator.narrate_progress(NarrationStyle.VERBOSE)

        assert "Andromeda" in narration.text or "currently" in narration.text.lower()


# =============================================================================
# Session End Narration Tests
# =============================================================================


class TestNarrateSessionEnd:
    """Tests for session end narration."""

    def test_session_end_narration(self, loaded_narrator):
        """Generate session end summary."""
        loaded_narrator.narrate_target_start(0)
        loaded_narrator.narrate_target_complete()

        narration = loaded_narrator.narrate_session_end()

        assert "complete" in narration.text.lower() or "finished" in narration.text.lower()
        assert narration.phase == SessionPhase.COMPLETE

    def test_session_end_updates_state(self, loaded_narrator):
        """Session end updates state correctly."""
        loaded_narrator.narrate_target_start(0)
        loaded_narrator.narrate_session_end()

        assert loaded_narrator.state.phase == SessionPhase.COMPLETE
        assert loaded_narrator.state.session_end is not None

    def test_session_end_counts_completed(self, loaded_narrator):
        """Session end includes completed count."""
        loaded_narrator.narrate_target_start(0)
        loaded_narrator.narrate_target_complete()
        loaded_narrator.narrate_target_start(1)
        loaded_narrator.narrate_target_complete()

        narration = loaded_narrator.narrate_session_end()

        assert "2" in narration.text


# =============================================================================
# History Tests
# =============================================================================


class TestHistory:
    """Tests for narration history."""

    def test_empty_history(self, narrator):
        """Empty history initially."""
        history = narrator.get_history()
        assert history == []

    def test_history_accumulates(self, loaded_narrator):
        """History accumulates narrations."""
        loaded_narrator.narrate_plan()
        loaded_narrator.narrate_target_start(0)
        loaded_narrator.narrate_target_complete()

        history = loaded_narrator.get_history()
        assert len(history) == 3

    def test_history_limit(self, loaded_narrator):
        """History respects limit."""
        for i in range(3):
            loaded_narrator.narrate_target_start(i)
            loaded_narrator.narrate_target_complete()

        history = loaded_narrator.get_history(limit=2)
        assert len(history) == 2


# =============================================================================
# Reset Tests
# =============================================================================


class TestReset:
    """Tests for narrator reset."""

    def test_reset_clears_state(self, loaded_narrator):
        """Reset clears session state."""
        loaded_narrator.narrate_target_start(0)
        loaded_narrator.reset()

        assert len(loaded_narrator.state.targets) == 0
        assert loaded_narrator.state.phase == SessionPhase.PLANNING

    def test_reset_clears_history(self, loaded_narrator):
        """Reset clears narration history."""
        loaded_narrator.narrate_plan()
        loaded_narrator.reset()

        history = loaded_narrator.get_history()
        assert len(history) == 0


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunction:
    """Tests for module-level factory."""

    def test_get_narrator_returns_instance(self):
        """get_narrator returns SessionNarrator."""
        narrator = get_narrator()
        assert isinstance(narrator, SessionNarrator)

    def test_get_narrator_singleton(self):
        """get_narrator returns same instance."""
        n1 = get_narrator()
        n2 = get_narrator()
        assert n1 is n2


# =============================================================================
# Duration Formatting Tests
# =============================================================================


class TestDurationFormatting:
    """Tests for duration formatting."""

    def test_format_minutes(self, narrator):
        """Format duration in minutes."""
        result = narrator._format_duration(45)
        assert "45" in result
        assert "minute" in result

    def test_format_single_minute(self, narrator):
        """Format single minute correctly."""
        result = narrator._format_duration(1)
        assert "1 minute" in result
        assert "minutes" not in result

    def test_format_hours(self, narrator):
        """Format duration in hours."""
        result = narrator._format_duration(120)
        assert "2" in result
        assert "hour" in result

    def test_format_hours_and_minutes(self, narrator):
        """Format mixed hours and minutes."""
        result = narrator._format_duration(90)
        assert "hour" in result
        assert "30" in result

    def test_format_less_than_minute(self, narrator):
        """Format very short duration."""
        result = narrator._format_duration(0.5)
        assert "less than a minute" in result


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests with scheduler output."""

    def test_full_session_workflow(self, loaded_narrator):
        """Test complete session narration workflow."""
        # Plan
        plan = loaded_narrator.narrate_plan()
        assert plan.phase == SessionPhase.PLANNING

        # Start first target
        start1 = loaded_narrator.narrate_target_start(0)
        assert start1.target_id == "M31"

        # Check progress
        progress1 = loaded_narrator.narrate_progress()
        assert "0" in progress1.text or "33" not in progress1.text  # 0 completed

        # Complete first target
        complete1 = loaded_narrator.narrate_target_complete()
        assert "complete" in complete1.text.lower()

        # Start second target
        start2 = loaded_narrator.narrate_target_start(1)
        assert start2.target_id == "M42"

        # Check progress again
        progress2 = loaded_narrator.narrate_progress()
        assert loaded_narrator.state.targets_completed == 1

        # End session
        end = loaded_narrator.narrate_session_end()
        assert end.phase == SessionPhase.COMPLETE

    def test_narration_metadata(self, loaded_narrator):
        """Narrations include useful metadata."""
        loaded_narrator.narrate_plan()
        narration = loaded_narrator.narrate_target_start(0)

        assert "altitude" in narration.metadata
        assert "quality" in narration.metadata
        assert narration.metadata["quality"] == "excellent"
