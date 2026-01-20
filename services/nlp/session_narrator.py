"""
NIGHTWATCH Session Narrator

Voice-friendly narration of observing sessions integrating scheduler and descriptions.

This module bridges:
- ObservingScheduler: Structured scheduling with scoring
- SkyDescriber: Natural language descriptions

Provides:
- Tonight's observing plan narration
- Target transition announcements
- Progress updates during sessions
- Session summary generation
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


# =============================================================================
# Enums and Constants
# =============================================================================


class NarrationStyle(Enum):
    """Style of session narration."""

    BRIEF = "brief"          # Quick announcements
    STANDARD = "standard"    # Normal detail level
    VERBOSE = "verbose"      # Full explanations


class SessionPhase(Enum):
    """Current phase of observing session."""

    PLANNING = "planning"        # Before session starts
    STARTING = "starting"        # Session initialization
    OBSERVING = "observing"      # Active observation
    TRANSITIONING = "transitioning"  # Moving between targets
    PAUSED = "paused"           # Temporary pause
    ENDING = "ending"           # Session wrap-up
    COMPLETE = "complete"       # Session finished


# Narration templates
PLAN_INTROS = {
    NarrationStyle.BRIEF: [
        "Tonight's plan: {target_count} targets over {duration}.",
        "{target_count} targets scheduled for {duration}.",
    ],
    NarrationStyle.STANDARD: [
        "I've prepared tonight's observing plan. We have {target_count} targets lined up for approximately {duration} of observation.",
        "Tonight's schedule includes {target_count} targets. Total planned observation time is about {duration}.",
        "Your observing session is ready. {target_count} targets are scheduled for {duration}.",
    ],
    NarrationStyle.VERBOSE: [
        "I've analyzed tonight's conditions and prepared an optimized observing plan for you. We'll be observing {target_count} targets over approximately {duration}. The schedule takes into account current sky conditions, moon position, and your observing preferences.",
        "Based on tonight's sky conditions, I've scheduled {target_count} targets for observation. The total session duration is approximately {duration}. Each target has been chosen for optimal viewing during its scheduled window.",
    ],
}

TARGET_INTROS = {
    NarrationStyle.BRIEF: [
        "First up: {name}.",
        "Starting with {name}.",
        "First target: {name}.",
    ],
    NarrationStyle.STANDARD: [
        "We'll begin with {name}, {quality_phrase}.",
        "First on the list is {name}. {reason_phrase}",
        "Starting with {name}, which {quality_phrase}.",
    ],
    NarrationStyle.VERBOSE: [
        "Our first target tonight is {name}. At {altitude} degrees altitude, it's {quality_phrase}. {reason_phrase} Scheduled observation time is {duration}.",
        "We're beginning with {name}. Currently at {altitude} degrees altitude, {quality_phrase}. {detailed_reason} I've allocated {duration} for this target.",
    ],
}

TRANSITION_PHRASES = {
    NarrationStyle.BRIEF: [
        "Next: {name}.",
        "Moving to {name}.",
        "Now: {name}.",
    ],
    NarrationStyle.STANDARD: [
        "Next up is {name}, {quality_phrase}.",
        "Moving to our next target: {name}. {reason_phrase}",
        "Transitioning to {name}, which {quality_phrase}.",
    ],
    NarrationStyle.VERBOSE: [
        "Our next target is {name}. Now at {altitude} degrees altitude, it's {quality_phrase}. {reason_phrase} We have {duration} scheduled for observation.",
        "Transitioning to {name}. It's currently positioned at {altitude} degrees above the horizon, {quality_phrase}. {detailed_reason} Observation window is {duration}.",
    ],
}

QUALITY_PHRASES = {
    "excellent": [
        "conditions are excellent",
        "ideally positioned for observation",
        "at peak observability",
        "in optimal viewing position",
    ],
    "good": [
        "conditions are good",
        "well placed for viewing",
        "nicely positioned",
        "favorable for observation",
    ],
    "fair": [
        "conditions are fair",
        "reasonably positioned",
        "acceptable for viewing",
        "viewable with some limitations",
    ],
    "marginal": [
        "conditions are marginal",
        "positioned lower than ideal",
        "observable but challenging",
        "borderline viewing conditions",
    ],
    "poor": [
        "conditions are poor",
        "not ideally positioned",
        "challenging to observe",
        "difficult viewing conditions",
    ],
}

REASON_PHRASES = {
    "optimal_altitude": [
        "It's at an excellent altitude right now.",
        "Currently high in the sky for best viewing.",
        "At peak altitude for minimal atmospheric distortion.",
    ],
    "moon_avoidance": [
        "Well separated from the moon.",
        "Good distance from lunar glare.",
        "Moon interference is minimal.",
    ],
    "weather_window": [
        "Weather conditions are favorable.",
        "Clear skies for this window.",
        "Good atmospheric conditions.",
    ],
    "historical_success": [
        "You've had success with this target before.",
        "Based on your past observations.",
        "A historically successful target for you.",
    ],
    "user_preference": [
        "One of your preferred targets.",
        "Matching your observing preferences.",
        "Selected based on your interests.",
    ],
    "time_constraint": [
        "Best available in this time window.",
        "Optimal for current timing.",
        "Scheduled for best availability.",
    ],
    "meridian_transit": [
        "Approaching meridian transit.",
        "Near its highest point tonight.",
        "Crossing the meridian soon.",
    ],
}

SESSION_SUMMARIES = {
    NarrationStyle.BRIEF: [
        "Session complete. {targets_observed} targets, {duration}.",
        "Done. Observed {targets_observed} targets in {duration}.",
    ],
    NarrationStyle.STANDARD: [
        "Your observing session is complete. We observed {targets_observed} targets over {duration}. {quality_summary}",
        "Session finished. {targets_observed} targets observed in {duration}. {quality_summary}",
        "That wraps up tonight's session. {targets_observed} targets were observed over {duration}. {quality_summary}",
    ],
    NarrationStyle.VERBOSE: [
        "Your observing session is now complete. Over the past {duration}, we successfully observed {targets_observed} targets. {quality_summary} {conditions_summary} {recommendation}",
        "Tonight's session has concluded after {duration} of observation. We covered {targets_observed} targets in total. {quality_summary} {conditions_summary} {recommendation}",
    ],
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class NarratedTarget:
    """A target with narration context."""

    target_id: str
    target_name: Optional[str]
    scheduled_start: datetime
    scheduled_end: datetime
    altitude_deg: float
    quality: str
    score: float
    reasons: list[str] = field(default_factory=list)
    is_current: bool = False
    is_completed: bool = False
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    notes: Optional[str] = None

    @property
    def display_name(self) -> str:
        """Get name for narration."""
        return self.target_name or self.target_id

    @property
    def scheduled_duration_minutes(self) -> float:
        """Get scheduled duration."""
        delta = self.scheduled_end - self.scheduled_start
        return delta.total_seconds() / 60

    @property
    def actual_duration_minutes(self) -> Optional[float]:
        """Get actual observation duration if completed."""
        if self.actual_start and self.actual_end:
            delta = self.actual_end - self.actual_start
            return delta.total_seconds() / 60
        return None


@dataclass
class SessionNarration:
    """A narration output."""

    text: str
    style: NarrationStyle
    phase: SessionPhase
    timestamp: datetime = field(default_factory=datetime.now)
    target_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class SessionState:
    """Current state of observing session."""

    phase: SessionPhase = SessionPhase.PLANNING
    targets: list[NarratedTarget] = field(default_factory=list)
    current_target_index: int = -1
    session_start: Optional[datetime] = None
    session_end: Optional[datetime] = None
    weather_notes: Optional[str] = None
    observer_notes: Optional[str] = None

    @property
    def current_target(self) -> Optional[NarratedTarget]:
        """Get currently active target."""
        if 0 <= self.current_target_index < len(self.targets):
            return self.targets[self.current_target_index]
        return None

    @property
    def targets_completed(self) -> int:
        """Count completed targets."""
        return sum(1 for t in self.targets if t.is_completed)

    @property
    def targets_remaining(self) -> int:
        """Count remaining targets."""
        return len(self.targets) - self.targets_completed

    @property
    def total_scheduled_minutes(self) -> float:
        """Total scheduled observation time."""
        return sum(t.scheduled_duration_minutes for t in self.targets)

    @property
    def elapsed_minutes(self) -> float:
        """Elapsed session time."""
        if self.session_start:
            delta = datetime.now() - self.session_start
            return delta.total_seconds() / 60
        return 0.0


# =============================================================================
# Session Narrator
# =============================================================================


class SessionNarrator:
    """
    Voice-friendly narrator for observing sessions.

    Integrates scheduling results with natural language generation
    to provide spoken narration of observing plans and progress.
    """

    def __init__(
        self,
        default_style: NarrationStyle = NarrationStyle.STANDARD,
    ):
        """
        Initialize narrator.

        Args:
            default_style: Default narration style
        """
        self.default_style = default_style
        self._state = SessionState()
        self._narration_history: list[SessionNarration] = []

    @property
    def state(self) -> SessionState:
        """Get current session state."""
        return self._state

    def load_schedule(
        self,
        schedule_result: dict,
    ) -> None:
        """
        Load a schedule result from the scheduler.

        Args:
            schedule_result: ScheduleResult.to_dict() output
        """
        self._state = SessionState(phase=SessionPhase.PLANNING)

        for target_dict in schedule_result.get("targets", []):
            target = NarratedTarget(
                target_id=target_dict["target_id"],
                target_name=target_dict.get("target_name"),
                scheduled_start=datetime.fromisoformat(target_dict["scheduled_start"]),
                scheduled_end=datetime.fromisoformat(target_dict["scheduled_end"]),
                altitude_deg=target_dict.get("expected_altitude_deg", 0),
                quality=target_dict.get("quality", "fair"),
                score=target_dict.get("score", 0.5),
                reasons=target_dict.get("reasons", []),
            )
            self._state.targets.append(target)

    def narrate_plan(
        self,
        style: Optional[NarrationStyle] = None,
    ) -> SessionNarration:
        """
        Generate narration for the observing plan.

        Args:
            style: Narration style

        Returns:
            SessionNarration with plan overview
        """
        import random

        style = style or self.default_style
        targets = self._state.targets

        if not targets:
            return SessionNarration(
                text="No targets are currently scheduled for observation.",
                style=style,
                phase=SessionPhase.PLANNING,
            )

        # Calculate totals
        target_count = len(targets)
        total_minutes = sum(t.scheduled_duration_minutes for t in targets)
        duration = self._format_duration(total_minutes)

        # Select template
        templates = PLAN_INTROS[style]
        intro = random.choice(templates).format(
            target_count=target_count,
            duration=duration,
        )

        # Add target list for standard and verbose
        parts = [intro]

        if style != NarrationStyle.BRIEF and targets:
            target_names = [t.display_name for t in targets[:5]]
            if len(targets) > 5:
                target_list = ", ".join(target_names) + f", and {len(targets) - 5} more"
            else:
                target_list = ", ".join(target_names[:-1])
                if len(target_names) > 1:
                    target_list += f" and {target_names[-1]}"
                else:
                    target_list = target_names[0]

            parts.append(f"Targets include {target_list}.")

        # Add first target preview for verbose
        if style == NarrationStyle.VERBOSE and targets:
            first = targets[0]
            quality_phrase = random.choice(QUALITY_PHRASES.get(first.quality, QUALITY_PHRASES["fair"]))
            parts.append(f"We'll start with {first.display_name}, where {quality_phrase}.")

        text = " ".join(parts)

        narration = SessionNarration(
            text=text,
            style=style,
            phase=SessionPhase.PLANNING,
            metadata={"target_count": target_count, "total_minutes": total_minutes},
        )

        self._narration_history.append(narration)
        return narration

    def narrate_target_start(
        self,
        target_index: int = 0,
        style: Optional[NarrationStyle] = None,
    ) -> SessionNarration:
        """
        Generate narration for starting a target.

        Args:
            target_index: Index of target in schedule
            style: Narration style

        Returns:
            SessionNarration for target start
        """
        import random

        style = style or self.default_style

        if target_index < 0 or target_index >= len(self._state.targets):
            return SessionNarration(
                text="No target available at that position.",
                style=style,
                phase=self._state.phase,
            )

        target = self._state.targets[target_index]

        # Update state
        self._state.current_target_index = target_index
        target.is_current = True
        target.actual_start = datetime.now()

        if target_index == 0:
            self._state.phase = SessionPhase.STARTING
            self._state.session_start = datetime.now()
            templates = TARGET_INTROS[style]
        else:
            self._state.phase = SessionPhase.TRANSITIONING
            templates = TRANSITION_PHRASES[style]

        # Build narration
        quality_phrase = random.choice(
            QUALITY_PHRASES.get(target.quality, QUALITY_PHRASES["fair"])
        )

        # Get reason phrase
        reason_phrase = ""
        if target.reasons:
            primary_reason = target.reasons[0]
            reason_phrases = REASON_PHRASES.get(primary_reason, [])
            if reason_phrases:
                reason_phrase = random.choice(reason_phrases)

        # Detailed reason for verbose
        detailed_reason = ""
        if style == NarrationStyle.VERBOSE and len(target.reasons) > 1:
            secondary_reasons = []
            for reason in target.reasons[1:3]:
                phrases = REASON_PHRASES.get(reason, [])
                if phrases:
                    secondary_reasons.append(random.choice(phrases).lower())
            if secondary_reasons:
                detailed_reason = "Additionally, " + " and ".join(secondary_reasons) + "."

        duration = self._format_duration(target.scheduled_duration_minutes)

        template = random.choice(templates)
        text = template.format(
            name=target.display_name,
            altitude=f"{target.altitude_deg:.0f}",
            quality_phrase=quality_phrase,
            reason_phrase=reason_phrase,
            detailed_reason=detailed_reason,
            duration=duration,
        )

        # Clean up any double spaces
        text = " ".join(text.split())

        narration = SessionNarration(
            text=text,
            style=style,
            phase=self._state.phase,
            target_id=target.target_id,
            metadata={
                "target_index": target_index,
                "altitude": target.altitude_deg,
                "quality": target.quality,
            },
        )

        self._state.phase = SessionPhase.OBSERVING
        self._narration_history.append(narration)
        return narration

    def narrate_target_complete(
        self,
        style: Optional[NarrationStyle] = None,
        notes: Optional[str] = None,
    ) -> SessionNarration:
        """
        Generate narration for completing current target.

        Args:
            style: Narration style
            notes: Optional notes about the observation

        Returns:
            SessionNarration for target completion
        """
        style = style or self.default_style
        target = self._state.current_target

        if not target:
            return SessionNarration(
                text="No target currently active.",
                style=style,
                phase=self._state.phase,
            )

        # Update state
        target.is_completed = True
        target.is_current = False
        target.actual_end = datetime.now()
        if notes:
            target.notes = notes

        # Calculate observation time
        actual_minutes = target.actual_duration_minutes or 0

        # Build narration
        remaining = self._state.targets_remaining
        if style == NarrationStyle.BRIEF:
            if remaining > 0:
                text = f"{target.display_name} complete. {remaining} targets remaining."
            else:
                text = f"{target.display_name} complete. Session finished."
        elif style == NarrationStyle.STANDARD:
            duration = self._format_duration(actual_minutes)
            if remaining > 0:
                text = f"Observation of {target.display_name} is complete after {duration}. {remaining} targets remaining in tonight's schedule."
            else:
                text = f"Observation of {target.display_name} is complete after {duration}. That was our last target."
        else:  # VERBOSE
            duration = self._format_duration(actual_minutes)
            text = f"We've completed our observation of {target.display_name}. Total observation time was {duration}."
            if notes:
                text += f" Notes: {notes}"
            if remaining > 0:
                next_target = self._state.targets[self._state.current_target_index + 1]
                text += f" {remaining} targets remain. Next up will be {next_target.display_name}."
            else:
                text += " That concludes our scheduled targets for tonight."

        narration = SessionNarration(
            text=text,
            style=style,
            phase=SessionPhase.OBSERVING,
            target_id=target.target_id,
            metadata={
                "actual_minutes": actual_minutes,
                "remaining": remaining,
            },
        )

        self._narration_history.append(narration)
        return narration

    def narrate_progress(
        self,
        style: Optional[NarrationStyle] = None,
    ) -> SessionNarration:
        """
        Generate narration of current session progress.

        Args:
            style: Narration style

        Returns:
            SessionNarration with progress update
        """
        style = style or self.default_style

        completed = self._state.targets_completed
        total = len(self._state.targets)
        elapsed = self._state.elapsed_minutes

        if total == 0:
            return SessionNarration(
                text="No observing session is currently active.",
                style=style,
                phase=self._state.phase,
            )

        elapsed_str = self._format_duration(elapsed)
        progress_pct = (completed / total * 100) if total > 0 else 0

        if style == NarrationStyle.BRIEF:
            text = f"{completed} of {total} targets. {elapsed_str} elapsed."
        elif style == NarrationStyle.STANDARD:
            text = f"Session progress: {completed} of {total} targets observed ({progress_pct:.0f}% complete). Time elapsed: {elapsed_str}."
            if self._state.current_target:
                text += f" Currently observing {self._state.current_target.display_name}."
        else:  # VERBOSE
            text = f"Your observing session has been running for {elapsed_str}. So far, you've completed {completed} of {total} scheduled targets, which is {progress_pct:.0f}% of tonight's plan."
            if self._state.current_target:
                target = self._state.current_target
                text += f" You're currently observing {target.display_name} at {target.altitude_deg:.0f} degrees altitude."
            remaining = total - completed
            if remaining > 0:
                remaining_minutes = sum(
                    t.scheduled_duration_minutes
                    for t in self._state.targets
                    if not t.is_completed
                )
                text += f" Approximately {self._format_duration(remaining_minutes)} of scheduled observation time remains."

        narration = SessionNarration(
            text=text,
            style=style,
            phase=self._state.phase,
            metadata={
                "completed": completed,
                "total": total,
                "progress_pct": progress_pct,
                "elapsed_minutes": elapsed,
            },
        )

        self._narration_history.append(narration)
        return narration

    def narrate_session_end(
        self,
        style: Optional[NarrationStyle] = None,
    ) -> SessionNarration:
        """
        Generate session summary narration.

        Args:
            style: Narration style

        Returns:
            SessionNarration with session summary
        """
        import random

        style = style or self.default_style

        self._state.phase = SessionPhase.COMPLETE
        self._state.session_end = datetime.now()

        completed = self._state.targets_completed
        elapsed = self._state.elapsed_minutes
        duration = self._format_duration(elapsed)

        # Calculate quality summary
        if completed > 0:
            qualities = [t.quality for t in self._state.targets if t.is_completed]
            excellent = sum(1 for q in qualities if q == "excellent")
            good = sum(1 for q in qualities if q == "good")

            if excellent > completed / 2:
                quality_summary = "Conditions were excellent throughout."
            elif excellent + good > completed / 2:
                quality_summary = "Overall conditions were good."
            else:
                quality_summary = "Conditions were mixed but manageable."
        else:
            quality_summary = ""

        # Conditions summary for verbose
        conditions_summary = ""
        if style == NarrationStyle.VERBOSE:
            if self._state.weather_notes:
                conditions_summary = f"Weather: {self._state.weather_notes}"

        # Recommendation for verbose
        recommendation = ""
        if style == NarrationStyle.VERBOSE and completed > 0:
            recommendation = "Your observation data has been logged for future reference."

        templates = SESSION_SUMMARIES[style]
        template = random.choice(templates)

        text = template.format(
            targets_observed=completed,
            duration=duration,
            quality_summary=quality_summary,
            conditions_summary=conditions_summary,
            recommendation=recommendation,
        )

        # Clean up
        text = " ".join(text.split())

        narration = SessionNarration(
            text=text,
            style=style,
            phase=SessionPhase.COMPLETE,
            metadata={
                "targets_observed": completed,
                "duration_minutes": elapsed,
            },
        )

        self._narration_history.append(narration)
        return narration

    def get_history(
        self,
        limit: int = 10,
    ) -> list[SessionNarration]:
        """Get recent narration history."""
        return self._narration_history[-limit:]

    def reset(self) -> None:
        """Reset narrator state for new session."""
        self._state = SessionState()
        self._narration_history = []

    def _format_duration(self, minutes: float) -> str:
        """Format duration in human-readable form."""
        if minutes < 1:
            return "less than a minute"
        elif minutes < 60:
            mins = int(minutes)
            return f"{mins} minute{'s' if mins != 1 else ''}"
        else:
            hours = int(minutes // 60)
            mins = int(minutes % 60)
            if mins == 0:
                return f"{hours} hour{'s' if hours != 1 else ''}"
            else:
                return f"{hours} hour{'s' if hours != 1 else ''} and {mins} minute{'s' if mins != 1 else ''}"


# =============================================================================
# Module-level singleton
# =============================================================================

_narrator: Optional[SessionNarrator] = None


def get_narrator(
    default_style: NarrationStyle = NarrationStyle.STANDARD,
) -> SessionNarrator:
    """Get the global session narrator instance."""
    global _narrator
    if _narrator is None:
        _narrator = SessionNarrator(default_style)
    return _narrator
