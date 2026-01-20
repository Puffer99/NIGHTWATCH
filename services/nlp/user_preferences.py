"""
NIGHTWATCH User Preferences Learning (Step 131)

Tracks and learns user preferences from observation patterns and explicit
settings. Persists preferences to disk for session continuity.

Preference categories:
- Target preferences (favorite objects, object types, constellations)
- Imaging preferences (exposure times, gain settings, binning)
- Observation style (deep sky vs planetary, visual vs imaging)
- Time preferences (session duration, break intervals)
- Communication style (verbose vs concise, confirmation level)

Usage:
    from services.nlp.user_preferences import UserPreferences

    prefs = UserPreferences()
    prefs.record_target_observation("M31", success=True, quality=0.85)
    prefs.record_exposure_setting(120, object_type="galaxy")

    # Get learned preferences
    favorite_targets = prefs.get_favorite_targets()
    suggested_exposure = prefs.get_preferred_exposure("galaxy")
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("NIGHTWATCH.UserPreferences")


__all__ = [
    "UserPreferences",
    "PreferenceCategory",
    "ObservationStyle",
    "CommunicationStyle",
    "TargetPreference",
    "ImagingPreference",
    "get_user_preferences",
]


# =============================================================================
# Enums and Data Classes
# =============================================================================


class PreferenceCategory(Enum):
    """Categories of user preferences."""
    TARGETS = "targets"
    IMAGING = "imaging"
    OBSERVATION_STYLE = "observation_style"
    TIMING = "timing"
    COMMUNICATION = "communication"


class ObservationStyle(Enum):
    """User's preferred observation style."""
    DEEP_SKY = "deep_sky"        # Galaxies, nebulae, clusters
    PLANETARY = "planetary"      # Planets, moon, sun
    MIXED = "mixed"              # Both
    VISUAL = "visual"            # Visual observing
    IMAGING = "imaging"          # Astrophotography
    UNKNOWN = "unknown"


class CommunicationStyle(Enum):
    """User's preferred communication verbosity."""
    CONCISE = "concise"          # Brief responses
    NORMAL = "normal"            # Standard responses
    VERBOSE = "verbose"          # Detailed explanations
    EXPERT = "expert"            # Technical terminology


@dataclass
class TargetPreference:
    """Preference data for a specific target."""
    target_id: str
    observation_count: int = 0
    success_count: int = 0
    total_quality: float = 0.0
    last_observed: Optional[datetime] = None
    total_exposure_time: float = 0.0  # seconds

    @property
    def success_rate(self) -> float:
        """Calculate observation success rate."""
        if self.observation_count == 0:
            return 0.0
        return self.success_count / self.observation_count

    @property
    def average_quality(self) -> float:
        """Calculate average quality score."""
        if self.success_count == 0:
            return 0.0
        return self.total_quality / self.success_count

    @property
    def preference_score(self) -> float:
        """Calculate overall preference score."""
        # Weight: frequency (40%), success (30%), quality (30%)
        freq_score = min(1.0, self.observation_count / 10)
        return 0.4 * freq_score + 0.3 * self.success_rate + 0.3 * self.average_quality

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "target_id": self.target_id,
            "observation_count": self.observation_count,
            "success_count": self.success_count,
            "total_quality": self.total_quality,
            "last_observed": self.last_observed.isoformat() if self.last_observed else None,
            "total_exposure_time": self.total_exposure_time,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TargetPreference":
        """Create from dictionary."""
        last_obs = data.get("last_observed")
        if last_obs:
            last_obs = datetime.fromisoformat(last_obs)
        return cls(
            target_id=data["target_id"],
            observation_count=data.get("observation_count", 0),
            success_count=data.get("success_count", 0),
            total_quality=data.get("total_quality", 0.0),
            last_observed=last_obs,
            total_exposure_time=data.get("total_exposure_time", 0.0),
        )


@dataclass
class ImagingPreference:
    """Preference data for imaging settings by object type."""
    object_type: str
    exposure_times: List[float] = field(default_factory=list)  # seconds
    gain_values: List[int] = field(default_factory=list)
    binning_modes: List[str] = field(default_factory=list)
    filter_choices: List[str] = field(default_factory=list)

    @property
    def preferred_exposure(self) -> Optional[float]:
        """Get most commonly used exposure time."""
        if not self.exposure_times:
            return None
        # Return mode (most common value)
        return max(set(self.exposure_times), key=self.exposure_times.count)

    @property
    def preferred_gain(self) -> Optional[int]:
        """Get most commonly used gain."""
        if not self.gain_values:
            return None
        return max(set(self.gain_values), key=self.gain_values.count)

    @property
    def preferred_binning(self) -> Optional[str]:
        """Get most commonly used binning."""
        if not self.binning_modes:
            return None
        return max(set(self.binning_modes), key=self.binning_modes.count)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "object_type": self.object_type,
            "exposure_times": self.exposure_times[-50:],  # Keep last 50
            "gain_values": self.gain_values[-50:],
            "binning_modes": self.binning_modes[-50:],
            "filter_choices": self.filter_choices[-50:],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImagingPreference":
        """Create from dictionary."""
        return cls(
            object_type=data["object_type"],
            exposure_times=data.get("exposure_times", []),
            gain_values=data.get("gain_values", []),
            binning_modes=data.get("binning_modes", []),
            filter_choices=data.get("filter_choices", []),
        )


# =============================================================================
# User Preferences Manager
# =============================================================================


class UserPreferences:
    """
    Manages learning and persistence of user preferences.

    Tracks observation patterns, imaging settings, and communication
    preferences to personalize the NIGHTWATCH experience.
    """

    DEFAULT_PREFS_PATH = Path.home() / ".nightwatch" / "user_preferences.json"

    def __init__(self, prefs_path: Optional[Path] = None):
        """
        Initialize user preferences manager.

        Args:
            prefs_path: Path to preferences file (uses default if None)
        """
        self._prefs_path = prefs_path or self.DEFAULT_PREFS_PATH

        # Target preferences
        self._target_prefs: Dict[str, TargetPreference] = {}

        # Object type preferences (galaxy, nebula, etc.)
        self._type_counts: Dict[str, int] = {}

        # Constellation preferences
        self._constellation_counts: Dict[str, int] = {}

        # Imaging preferences by object type
        self._imaging_prefs: Dict[str, ImagingPreference] = {}

        # Observation style
        self._observation_style = ObservationStyle.UNKNOWN
        self._style_observations = {"deep_sky": 0, "planetary": 0}

        # Communication preferences
        self._communication_style = CommunicationStyle.NORMAL
        self._confirmation_level = 0.5  # 0=never confirm, 1=always confirm

        # Session timing preferences
        self._session_durations: List[float] = []  # minutes
        self._preferred_start_times: List[int] = []  # hour of day

        # Load existing preferences
        self._load()

        logger.debug(f"UserPreferences initialized from {self._prefs_path}")

    # =========================================================================
    # Target Preferences
    # =========================================================================

    def record_target_observation(
        self,
        target_id: str,
        success: bool = True,
        quality: float = 0.5,
        exposure_time: float = 0.0,
        object_type: Optional[str] = None,
        constellation: Optional[str] = None,
    ):
        """
        Record an observation of a target.

        Args:
            target_id: Target identifier (M31, NGC 7000, etc.)
            success: Whether observation was successful
            quality: Quality score 0.0-1.0
            exposure_time: Total exposure time in seconds
            object_type: Type of object (galaxy, nebula, etc.)
            constellation: Constellation containing target
        """
        # Update target preference
        if target_id not in self._target_prefs:
            self._target_prefs[target_id] = TargetPreference(target_id=target_id)

        pref = self._target_prefs[target_id]
        pref.observation_count += 1
        if success:
            pref.success_count += 1
            pref.total_quality += quality
        pref.last_observed = datetime.now()
        pref.total_exposure_time += exposure_time

        # Update object type counts
        if object_type:
            self._type_counts[object_type] = self._type_counts.get(object_type, 0) + 1
            self._update_observation_style(object_type)

        # Update constellation counts
        if constellation:
            self._constellation_counts[constellation] = \
                self._constellation_counts.get(constellation, 0) + 1

        self._save()
        logger.debug(f"Recorded observation: {target_id} (success={success}, quality={quality:.2f})")

    def get_favorite_targets(self, limit: int = 10) -> List[str]:
        """
        Get user's favorite targets by preference score.

        Args:
            limit: Maximum targets to return

        Returns:
            List of target IDs sorted by preference
        """
        sorted_prefs = sorted(
            self._target_prefs.values(),
            key=lambda p: p.preference_score,
            reverse=True,
        )
        return [p.target_id for p in sorted_prefs[:limit]]

    def get_target_preference(self, target_id: str) -> Optional[TargetPreference]:
        """Get preference data for a specific target."""
        return self._target_prefs.get(target_id)

    def get_favorite_object_types(self, limit: int = 5) -> List[Tuple[str, int]]:
        """Get most observed object types."""
        sorted_types = sorted(
            self._type_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return sorted_types[:limit]

    def get_favorite_constellations(self, limit: int = 5) -> List[Tuple[str, int]]:
        """Get most observed constellations."""
        sorted_const = sorted(
            self._constellation_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return sorted_const[:limit]

    # =========================================================================
    # Imaging Preferences
    # =========================================================================

    def record_exposure_setting(
        self,
        exposure_seconds: float,
        object_type: str = "default",
    ):
        """Record an exposure time setting."""
        if object_type not in self._imaging_prefs:
            self._imaging_prefs[object_type] = ImagingPreference(object_type=object_type)

        self._imaging_prefs[object_type].exposure_times.append(exposure_seconds)
        self._save()

    def record_gain_setting(self, gain: int, object_type: str = "default"):
        """Record a gain setting."""
        if object_type not in self._imaging_prefs:
            self._imaging_prefs[object_type] = ImagingPreference(object_type=object_type)

        self._imaging_prefs[object_type].gain_values.append(gain)
        self._save()

    def record_binning_setting(self, binning: str, object_type: str = "default"):
        """Record a binning setting."""
        if object_type not in self._imaging_prefs:
            self._imaging_prefs[object_type] = ImagingPreference(object_type=object_type)

        self._imaging_prefs[object_type].binning_modes.append(binning)
        self._save()

    def record_filter_choice(self, filter_name: str, object_type: str = "default"):
        """Record a filter choice."""
        if object_type not in self._imaging_prefs:
            self._imaging_prefs[object_type] = ImagingPreference(object_type=object_type)

        self._imaging_prefs[object_type].filter_choices.append(filter_name)
        self._save()

    def get_preferred_exposure(self, object_type: str = "default") -> Optional[float]:
        """Get preferred exposure for object type."""
        pref = self._imaging_prefs.get(object_type)
        if pref:
            return pref.preferred_exposure

        # Fall back to default
        default_pref = self._imaging_prefs.get("default")
        return default_pref.preferred_exposure if default_pref else None

    def get_preferred_gain(self, object_type: str = "default") -> Optional[int]:
        """Get preferred gain for object type."""
        pref = self._imaging_prefs.get(object_type)
        if pref:
            return pref.preferred_gain

        default_pref = self._imaging_prefs.get("default")
        return default_pref.preferred_gain if default_pref else None

    def get_preferred_binning(self, object_type: str = "default") -> Optional[str]:
        """Get preferred binning for object type."""
        pref = self._imaging_prefs.get(object_type)
        if pref:
            return pref.preferred_binning

        default_pref = self._imaging_prefs.get("default")
        return default_pref.preferred_binning if default_pref else None

    def get_imaging_preferences(self, object_type: str) -> Optional[ImagingPreference]:
        """Get all imaging preferences for an object type."""
        return self._imaging_prefs.get(object_type)

    # =========================================================================
    # Observation Style
    # =========================================================================

    def _update_observation_style(self, object_type: str):
        """Update observation style based on object type."""
        deep_sky_types = {"galaxy", "nebula", "cluster", "globular", "open_cluster",
                         "planetary_nebula", "supernova_remnant"}
        planetary_types = {"planet", "moon", "sun", "asteroid", "comet"}

        if object_type.lower() in deep_sky_types:
            self._style_observations["deep_sky"] += 1
        elif object_type.lower() in planetary_types:
            self._style_observations["planetary"] += 1

        # Determine dominant style
        deep = self._style_observations["deep_sky"]
        planetary = self._style_observations["planetary"]

        if deep > planetary * 2:
            self._observation_style = ObservationStyle.DEEP_SKY
        elif planetary > deep * 2:
            self._observation_style = ObservationStyle.PLANETARY
        elif deep + planetary > 10:
            self._observation_style = ObservationStyle.MIXED
        else:
            self._observation_style = ObservationStyle.UNKNOWN

    def get_observation_style(self) -> ObservationStyle:
        """Get user's determined observation style."""
        return self._observation_style

    def set_observation_style(self, style: ObservationStyle):
        """Explicitly set observation style."""
        self._observation_style = style
        self._save()

    # =========================================================================
    # Communication Preferences
    # =========================================================================

    def get_communication_style(self) -> CommunicationStyle:
        """Get user's communication preference."""
        return self._communication_style

    def set_communication_style(self, style: CommunicationStyle):
        """Set communication style preference."""
        self._communication_style = style
        self._save()

    def get_confirmation_level(self) -> float:
        """Get confirmation preference (0=never, 1=always)."""
        return self._confirmation_level

    def set_confirmation_level(self, level: float):
        """Set confirmation level preference."""
        self._confirmation_level = max(0.0, min(1.0, level))
        self._save()

    def should_confirm_action(self, action_risk: float = 0.5) -> bool:
        """
        Determine if action should require confirmation.

        Args:
            action_risk: Risk level of action (0=safe, 1=dangerous)

        Returns:
            True if confirmation should be requested
        """
        # High-risk actions always confirm
        if action_risk >= 0.9:
            return True

        # Check against user's confirmation preference
        return action_risk > (1.0 - self._confirmation_level)

    # =========================================================================
    # Session Timing
    # =========================================================================

    def record_session_duration(self, duration_minutes: float):
        """Record a session duration."""
        self._session_durations.append(duration_minutes)
        # Keep last 20 sessions
        self._session_durations = self._session_durations[-20:]
        self._save()

    def record_session_start_time(self, start_hour: int):
        """Record session start time (hour of day)."""
        self._preferred_start_times.append(start_hour)
        self._preferred_start_times = self._preferred_start_times[-20:]
        self._save()

    def get_typical_session_duration(self) -> Optional[float]:
        """Get typical session duration in minutes."""
        if not self._session_durations:
            return None
        return sum(self._session_durations) / len(self._session_durations)

    def get_preferred_start_time(self) -> Optional[int]:
        """Get most common session start hour."""
        if not self._preferred_start_times:
            return None
        return max(set(self._preferred_start_times),
                   key=self._preferred_start_times.count)

    # =========================================================================
    # Persistence
    # =========================================================================

    def _save(self):
        """Save preferences to disk."""
        try:
            self._prefs_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "version": 1,
                "saved_at": datetime.now().isoformat(),
                "target_prefs": {
                    tid: pref.to_dict()
                    for tid, pref in self._target_prefs.items()
                },
                "type_counts": self._type_counts,
                "constellation_counts": self._constellation_counts,
                "imaging_prefs": {
                    otype: pref.to_dict()
                    for otype, pref in self._imaging_prefs.items()
                },
                "observation_style": self._observation_style.value,
                "style_observations": self._style_observations,
                "communication_style": self._communication_style.value,
                "confirmation_level": self._confirmation_level,
                "session_durations": self._session_durations,
                "preferred_start_times": self._preferred_start_times,
            }

            with open(self._prefs_path, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to save preferences: {e}")

    def _load(self):
        """Load preferences from disk."""
        if not self._prefs_path.exists():
            return

        try:
            with open(self._prefs_path, "r") as f:
                data = json.load(f)

            # Load target preferences
            for tid, pdata in data.get("target_prefs", {}).items():
                self._target_prefs[tid] = TargetPreference.from_dict(pdata)

            # Load counts
            self._type_counts = data.get("type_counts", {})
            self._constellation_counts = data.get("constellation_counts", {})

            # Load imaging preferences
            for otype, pdata in data.get("imaging_prefs", {}).items():
                self._imaging_prefs[otype] = ImagingPreference.from_dict(pdata)

            # Load style
            style_val = data.get("observation_style", "unknown")
            self._observation_style = ObservationStyle(style_val)
            self._style_observations = data.get("style_observations",
                                                {"deep_sky": 0, "planetary": 0})

            # Load communication
            comm_val = data.get("communication_style", "normal")
            self._communication_style = CommunicationStyle(comm_val)
            self._confirmation_level = data.get("confirmation_level", 0.5)

            # Load timing
            self._session_durations = data.get("session_durations", [])
            self._preferred_start_times = data.get("preferred_start_times", [])

            logger.debug(f"Loaded preferences: {len(self._target_prefs)} targets")

        except Exception as e:
            logger.warning(f"Failed to load preferences: {e}")

    def reset(self):
        """Reset all preferences to defaults."""
        self._target_prefs.clear()
        self._type_counts.clear()
        self._constellation_counts.clear()
        self._imaging_prefs.clear()
        self._observation_style = ObservationStyle.UNKNOWN
        self._style_observations = {"deep_sky": 0, "planetary": 0}
        self._communication_style = CommunicationStyle.NORMAL
        self._confirmation_level = 0.5
        self._session_durations.clear()
        self._preferred_start_times.clear()

        if self._prefs_path.exists():
            self._prefs_path.unlink()

        logger.info("User preferences reset")

    # =========================================================================
    # Summary and Export
    # =========================================================================

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of user preferences."""
        return {
            "total_observations": sum(p.observation_count for p in self._target_prefs.values()),
            "unique_targets": len(self._target_prefs),
            "favorite_targets": self.get_favorite_targets(5),
            "favorite_types": self.get_favorite_object_types(3),
            "observation_style": self._observation_style.value,
            "communication_style": self._communication_style.value,
            "typical_session_minutes": self.get_typical_session_duration(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Export all preferences as dictionary."""
        return {
            "target_prefs": {
                tid: pref.to_dict()
                for tid, pref in self._target_prefs.items()
            },
            "imaging_prefs": {
                otype: pref.to_dict()
                for otype, pref in self._imaging_prefs.items()
            },
            "observation_style": self._observation_style.value,
            "communication_style": self._communication_style.value,
            "confirmation_level": self._confirmation_level,
        }


# =============================================================================
# Module-level instance and factory
# =============================================================================


_default_preferences: Optional[UserPreferences] = None


def get_user_preferences(prefs_path: Optional[Path] = None) -> UserPreferences:
    """
    Get or create the default user preferences manager.

    Args:
        prefs_path: Optional custom path for preferences file

    Returns:
        UserPreferences instance
    """
    global _default_preferences
    if _default_preferences is None:
        _default_preferences = UserPreferences(prefs_path=prefs_path)
    return _default_preferences
