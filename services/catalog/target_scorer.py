"""
NIGHTWATCH Target Scorer
Intelligent Target Scoring for Observation Scheduling (Step 118)

This module implements target scoring based on observing conditions,
a key component of the v0.5 AI Enhancement features for intelligent
scheduling optimization.

Scoring factors include:
- Altitude (higher = better visibility, less atmosphere)
- Moon separation and phase (dark sky quality)
- Hour angle / meridian proximity (tracking quality)
- Object size vs seeing conditions
- Magnitude vs sky brightness
- Time to set (observation window remaining)
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, List, Tuple, Dict, Any

from services.catalog.catalog import CatalogObject, ObjectType


class ScoringWeight(Enum):
    """Predefined scoring weight profiles for different imaging goals."""
    BALANCED = "balanced"           # General purpose
    DEEP_SKY = "deep_sky"          # Prioritize dark sky, long exposures
    PLANETARY = "planetary"         # Prioritize altitude, seeing
    WIDEFIELD = "widefield"         # Prioritize altitude, less moon sensitive


@dataclass
class ScoringWeights:
    """
    Configurable weights for target scoring factors.

    All weights should sum to approximately 1.0 for normalized scoring.
    Higher weight = more important factor.
    """
    altitude: float = 0.25           # Object altitude above horizon
    moon_penalty: float = 0.20       # Moon interference (inverted)
    hour_angle: float = 0.15         # Distance from meridian
    time_remaining: float = 0.15     # Time until object sets
    magnitude: float = 0.10          # Object brightness vs conditions
    size_match: float = 0.10         # Object size vs FOV/seeing
    airmass: float = 0.05            # Atmospheric extinction

    @classmethod
    def balanced(cls) -> "ScoringWeights":
        """Balanced weights for general observing."""
        return cls()

    @classmethod
    def deep_sky(cls) -> "ScoringWeights":
        """Weights optimized for deep sky imaging."""
        return cls(
            altitude=0.20,
            moon_penalty=0.30,    # Moon matters more for DSO
            hour_angle=0.15,
            time_remaining=0.15,
            magnitude=0.05,       # Exposure time handles faint objects
            size_match=0.10,
            airmass=0.05,
        )

    @classmethod
    def planetary(cls) -> "ScoringWeights":
        """Weights optimized for planetary imaging."""
        return cls(
            altitude=0.35,        # Altitude critical for seeing
            moon_penalty=0.05,    # Moon doesn't affect bright planets much
            hour_angle=0.20,      # Near meridian for best seeing
            time_remaining=0.15,
            magnitude=0.05,
            size_match=0.10,
            airmass=0.10,         # Less atmosphere = sharper
        )

    @classmethod
    def widefield(cls) -> "ScoringWeights":
        """Weights optimized for widefield imaging."""
        return cls(
            altitude=0.30,
            moon_penalty=0.15,    # Less sensitive with short FL
            hour_angle=0.15,
            time_remaining=0.20,  # More time for mosaics
            magnitude=0.05,
            size_match=0.10,
            airmass=0.05,
        )


@dataclass
class TargetScore:
    """
    Complete scoring result for a target.

    Contains individual factor scores and the weighted total.
    """
    target_id: str                    # Catalog ID or name
    ra_hours: float                   # Target coordinates
    dec_degrees: float

    # Individual factor scores (0.0 to 1.0, higher = better)
    altitude_score: float = 0.0
    moon_score: float = 0.0           # Inverted moon penalty
    hour_angle_score: float = 0.0
    time_remaining_score: float = 0.0
    magnitude_score: float = 0.0
    size_match_score: float = 0.0
    airmass_score: float = 0.0

    # Weighted total score
    total_score: float = 0.0

    # Additional info
    altitude_deg: float = 0.0         # Current altitude
    hours_until_set: float = 0.0      # Time remaining
    moon_separation_deg: float = 0.0  # Distance from moon
    recommendation: str = ""          # Text recommendation

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "target_id": self.target_id,
            "ra_hours": self.ra_hours,
            "dec_degrees": self.dec_degrees,
            "scores": {
                "altitude": self.altitude_score,
                "moon": self.moon_score,
                "hour_angle": self.hour_angle_score,
                "time_remaining": self.time_remaining_score,
                "magnitude": self.magnitude_score,
                "size_match": self.size_match_score,
                "airmass": self.airmass_score,
            },
            "total_score": self.total_score,
            "altitude_deg": self.altitude_deg,
            "hours_until_set": self.hours_until_set,
            "moon_separation_deg": self.moon_separation_deg,
            "recommendation": self.recommendation,
        }


class TargetScorer:
    """
    Intelligent target scoring for observation planning (Step 118).

    Integrates with ephemeris service for position calculations
    and moon avoidance. Produces scores that can be used by
    scheduling algorithms to prioritize observations.

    Usage:
        scorer = TargetScorer(ephemeris_service)
        score = scorer.score_target(ra_hours=5.5, dec_degrees=22.0)
        print(f"Score: {score.total_score:.2f} - {score.recommendation}")
    """

    # Altitude thresholds
    MIN_ALTITUDE = 10.0      # Below this is unobservable
    GOOD_ALTITUDE = 30.0     # Decent conditions
    EXCELLENT_ALTITUDE = 60.0  # Excellent conditions

    # Hour angle thresholds (hours from meridian)
    EXCELLENT_HA = 0.5       # Very close to meridian
    GOOD_HA = 2.0            # Good tracking

    def __init__(
        self,
        ephemeris_service=None,
        weights: Optional[ScoringWeights] = None,
        observer_latitude: float = 39.0,  # Default Nevada site
    ):
        """
        Initialize target scorer.

        Args:
            ephemeris_service: EphemerisService instance (optional)
            weights: Scoring weights (defaults to balanced)
            observer_latitude: Observer latitude in degrees
        """
        self._ephemeris = ephemeris_service
        self.weights = weights or ScoringWeights.balanced()
        self.observer_latitude = observer_latitude

    def set_weights(self, weights: ScoringWeights) -> None:
        """Update scoring weights."""
        self.weights = weights

    def set_profile(self, profile: ScoringWeight) -> None:
        """Set weights from a predefined profile."""
        if profile == ScoringWeight.BALANCED:
            self.weights = ScoringWeights.balanced()
        elif profile == ScoringWeight.DEEP_SKY:
            self.weights = ScoringWeights.deep_sky()
        elif profile == ScoringWeight.PLANETARY:
            self.weights = ScoringWeights.planetary()
        elif profile == ScoringWeight.WIDEFIELD:
            self.weights = ScoringWeights.widefield()

    def _calculate_altitude_score(self, altitude_deg: float) -> float:
        """
        Score based on altitude above horizon.

        Higher altitude = less atmosphere = better image quality.
        Score is 0 below minimum, scales up to 1.0 at excellent altitude.
        """
        if altitude_deg < self.MIN_ALTITUDE:
            return 0.0

        if altitude_deg >= self.EXCELLENT_ALTITUDE:
            return 1.0

        # Linear interpolation between min and excellent
        range_size = self.EXCELLENT_ALTITUDE - self.MIN_ALTITUDE
        return (altitude_deg - self.MIN_ALTITUDE) / range_size

    def _calculate_hour_angle_score(self, hour_angle_hours: float) -> float:
        """
        Score based on hour angle (distance from meridian).

        Objects near meridian have best tracking and minimal
        field rotation for alt-az mounts. German EQ mounts
        prefer post-meridian for imaging runs.

        Args:
            hour_angle_hours: Hours from meridian (-12 to +12)

        Returns:
            Score 0.0 to 1.0
        """
        abs_ha = abs(hour_angle_hours)

        if abs_ha <= self.EXCELLENT_HA:
            return 1.0

        if abs_ha >= 6.0:  # Near horizon
            return 0.0

        # Gaussian-like decay from meridian
        return math.exp(-(abs_ha - self.EXCELLENT_HA)**2 / 4.0)

    def _calculate_time_remaining_score(self, hours_until_set: float) -> float:
        """
        Score based on time remaining until object sets.

        More time = more flexibility for long exposures.
        """
        if hours_until_set <= 0:
            return 0.0

        if hours_until_set >= 4.0:  # 4+ hours is excellent
            return 1.0

        # Linear scale for shorter windows
        return hours_until_set / 4.0

    def _calculate_airmass_score(self, altitude_deg: float) -> float:
        """
        Score based on airmass (atmospheric path length).

        Airmass = 1/sin(altitude) for simple approximation.
        Lower airmass = less extinction = better.
        """
        if altitude_deg <= 0:
            return 0.0

        # Calculate airmass
        alt_rad = math.radians(altitude_deg)
        airmass = 1.0 / math.sin(alt_rad)

        # Airmass 1.0 (zenith) = score 1.0
        # Airmass 2.0 (30° alt) = score ~0.5
        # Airmass 3.0 (19° alt) = score ~0.33
        if airmass <= 1.0:
            return 1.0

        return 1.0 / airmass

    def _calculate_moon_score(
        self,
        ra_hours: float,
        dec_degrees: float,
        when: Optional[datetime] = None
    ) -> Tuple[float, float]:
        """
        Calculate moon interference score.

        Uses moon_penalty from ephemeris service if available,
        otherwise estimates based on separation.

        Returns:
            Tuple of (score, separation_deg)
        """
        if self._ephemeris is None:
            # No ephemeris - assume moderate conditions
            return (0.5, 45.0)

        try:
            penalty = self._ephemeris.get_moon_penalty(ra_hours, dec_degrees, when)
            separation = self._ephemeris.get_moon_separation(ra_hours, dec_degrees, when)
            # Invert penalty to get score (low penalty = high score)
            return (1.0 - penalty, separation)
        except Exception:
            return (0.5, 45.0)

    def _calculate_magnitude_score(
        self,
        magnitude: Optional[float],
        object_type: Optional[ObjectType] = None
    ) -> float:
        """
        Score based on object magnitude.

        Brighter objects are easier to image. Score adjusts
        based on object type (galaxies harder than clusters).
        """
        if magnitude is None:
            return 0.5  # Unknown magnitude = average score

        # Base score: brighter = better
        # Mag 4 = excellent (1.0), Mag 10 = good (0.6), Mag 14 = fair (0.2)
        if magnitude <= 4.0:
            base_score = 1.0
        elif magnitude >= 14.0:
            base_score = 0.2
        else:
            base_score = 1.0 - (magnitude - 4.0) * 0.08

        # Adjust for object type
        if object_type == ObjectType.GALAXY:
            # Galaxies have lower surface brightness
            base_score *= 0.9
        elif object_type == ObjectType.NEBULA:
            base_score *= 0.95

        return max(0.0, min(1.0, base_score))

    def _calculate_size_match_score(
        self,
        size_arcmin: Optional[float],
        fov_arcmin: float = 60.0
    ) -> float:
        """
        Score based on object size vs field of view.

        Objects that fill 30-70% of FOV are ideal.
        Too small = less detail, too large = doesn't fit.
        """
        if size_arcmin is None:
            return 0.5  # Unknown size = average

        # Calculate fill percentage
        fill_pct = size_arcmin / fov_arcmin

        # Ideal is 30-70% fill
        if 0.3 <= fill_pct <= 0.7:
            return 1.0

        if fill_pct < 0.1:
            # Too small
            return 0.3 + (fill_pct / 0.1) * 0.3
        elif fill_pct < 0.3:
            # Somewhat small
            return 0.6 + ((fill_pct - 0.1) / 0.2) * 0.4
        elif fill_pct <= 1.0:
            # Somewhat large
            return 1.0 - ((fill_pct - 0.7) / 0.3) * 0.3
        else:
            # Larger than FOV
            return max(0.2, 0.7 - (fill_pct - 1.0) * 0.5)

    def _estimate_hours_until_set(
        self,
        ra_hours: float,
        dec_degrees: float,
        when: Optional[datetime] = None
    ) -> float:
        """
        Estimate hours until object sets below minimum altitude.

        Simple approximation based on hour angle calculation.
        For precise values, use ephemeris service.
        """
        if self._ephemeris:
            try:
                altaz = self._ephemeris.get_star_altaz(ra_hours, dec_degrees, when)
                if altaz.altitude_degrees < self.MIN_ALTITUDE:
                    return 0.0
            except Exception:
                pass

        # Simple estimate: objects near meridian have ~6 hours
        # This is a rough approximation
        if when is None:
            when = datetime.now(timezone.utc)

        # Calculate local sidereal time (simplified)
        # LST ≈ UT + longitude/15 (very rough)
        lst_hours = (when.hour + when.minute / 60.0) % 24

        # Hour angle = LST - RA
        hour_angle = lst_hours - ra_hours
        if hour_angle > 12:
            hour_angle -= 24
        elif hour_angle < -12:
            hour_angle += 24

        # If already past meridian, estimate time to set
        if hour_angle > 0:
            # Rough estimate: sets in (6 - HA) hours
            return max(0.0, 6.0 - hour_angle)
        else:
            # Rising or at meridian
            return max(0.0, 6.0 + abs(hour_angle))

    def _get_recommendation(self, score: TargetScore) -> str:
        """Generate text recommendation based on scores."""
        total = score.total_score

        if total >= 0.8:
            return "Excellent target - highly recommended"
        elif total >= 0.6:
            return "Good target for current conditions"
        elif total >= 0.4:
            return "Acceptable target - some compromises"
        elif total >= 0.2:
            return "Marginal target - consider alternatives"
        else:
            return "Poor conditions - not recommended"

    def score_target(
        self,
        ra_hours: float,
        dec_degrees: float,
        target_id: str = "target",
        magnitude: Optional[float] = None,
        size_arcmin: Optional[float] = None,
        object_type: Optional[ObjectType] = None,
        fov_arcmin: float = 60.0,
        when: Optional[datetime] = None,
    ) -> TargetScore:
        """
        Calculate comprehensive score for a target (Step 118).

        Args:
            ra_hours: Target Right Ascension in hours (J2000)
            dec_degrees: Target Declination in degrees (J2000)
            target_id: Identifier for the target
            magnitude: Object magnitude (optional)
            size_arcmin: Object size in arcminutes (optional)
            object_type: Type of object (optional)
            fov_arcmin: Camera field of view in arcminutes
            when: Time for calculation (default: now)

        Returns:
            TargetScore with all factor scores and total
        """
        result = TargetScore(
            target_id=target_id,
            ra_hours=ra_hours,
            dec_degrees=dec_degrees,
        )

        # Get current altitude if ephemeris available
        altitude = 45.0  # Default estimate
        hour_angle = 0.0

        if self._ephemeris:
            try:
                altaz = self._ephemeris.get_star_altaz(ra_hours, dec_degrees, when)
                altitude = altaz.altitude_degrees
            except Exception:
                pass

        result.altitude_deg = altitude

        # Calculate individual scores
        result.altitude_score = self._calculate_altitude_score(altitude)

        # Hour angle (simplified calculation if no ephemeris)
        if when is None:
            when = datetime.now(timezone.utc)
        lst_approx = (when.hour + when.minute / 60.0) % 24
        hour_angle = lst_approx - ra_hours
        if hour_angle > 12:
            hour_angle -= 24
        elif hour_angle < -12:
            hour_angle += 24
        result.hour_angle_score = self._calculate_hour_angle_score(hour_angle)

        # Time remaining
        hours_remaining = self._estimate_hours_until_set(ra_hours, dec_degrees, when)
        result.hours_until_set = hours_remaining
        result.time_remaining_score = self._calculate_time_remaining_score(hours_remaining)

        # Moon score
        moon_score, moon_sep = self._calculate_moon_score(ra_hours, dec_degrees, when)
        result.moon_score = moon_score
        result.moon_separation_deg = moon_sep

        # Airmass
        result.airmass_score = self._calculate_airmass_score(altitude)

        # Magnitude
        result.magnitude_score = self._calculate_magnitude_score(magnitude, object_type)

        # Size match
        result.size_match_score = self._calculate_size_match_score(size_arcmin, fov_arcmin)

        # Calculate weighted total
        w = self.weights
        result.total_score = (
            w.altitude * result.altitude_score +
            w.moon_penalty * result.moon_score +
            w.hour_angle * result.hour_angle_score +
            w.time_remaining * result.time_remaining_score +
            w.magnitude * result.magnitude_score +
            w.size_match * result.size_match_score +
            w.airmass * result.airmass_score
        )

        # Generate recommendation
        result.recommendation = self._get_recommendation(result)

        return result

    def score_catalog_object(
        self,
        obj: CatalogObject,
        fov_arcmin: float = 60.0,
        when: Optional[datetime] = None,
    ) -> TargetScore:
        """
        Score a catalog object directly.

        Convenience method that extracts coordinates and metadata
        from a CatalogObject.
        """
        return self.score_target(
            ra_hours=obj.ra_hours,
            dec_degrees=obj.dec_degrees,
            target_id=obj.catalog_id,
            magnitude=obj.magnitude,
            size_arcmin=obj.size_arcmin,
            object_type=obj.object_type,
            fov_arcmin=fov_arcmin,
            when=when,
        )

    def rank_targets(
        self,
        targets: List[Tuple[float, float, str]],
        when: Optional[datetime] = None,
        min_score: float = 0.2,
    ) -> List[TargetScore]:
        """
        Rank multiple targets by score (Step 118).

        Args:
            targets: List of (ra_hours, dec_degrees, target_id) tuples
            when: Time for calculation
            min_score: Minimum score to include in results

        Returns:
            List of TargetScore sorted by total_score descending
        """
        scores = []
        for ra, dec, target_id in targets:
            score = self.score_target(ra, dec, target_id, when=when)
            if score.total_score >= min_score:
                scores.append(score)

        # Sort by total score descending
        scores.sort(key=lambda s: s.total_score, reverse=True)
        return scores

    def rank_catalog_objects(
        self,
        objects: List[CatalogObject],
        fov_arcmin: float = 60.0,
        when: Optional[datetime] = None,
        min_score: float = 0.2,
    ) -> List[TargetScore]:
        """
        Rank catalog objects by observability score.

        Args:
            objects: List of CatalogObject instances
            fov_arcmin: Camera field of view
            when: Time for calculation
            min_score: Minimum score threshold

        Returns:
            List of TargetScore sorted by score descending
        """
        scores = []
        for obj in objects:
            score = self.score_catalog_object(obj, fov_arcmin, when)
            if score.total_score >= min_score:
                scores.append(score)

        scores.sort(key=lambda s: s.total_score, reverse=True)
        return scores

    def format_score_summary(self, score: TargetScore) -> str:
        """
        Format score for voice output.

        Returns human-readable summary of target observability.
        """
        parts = [f"{score.target_id}: "]

        # Overall assessment
        if score.total_score >= 0.8:
            parts.append("Excellent choice. ")
        elif score.total_score >= 0.6:
            parts.append("Good target. ")
        elif score.total_score >= 0.4:
            parts.append("Acceptable. ")
        else:
            parts.append("Not ideal. ")

        # Altitude
        if score.altitude_deg < 20:
            parts.append(f"Low altitude at {score.altitude_deg:.0f} degrees. ")
        elif score.altitude_deg > 60:
            parts.append(f"High in the sky at {score.altitude_deg:.0f} degrees. ")

        # Moon
        if score.moon_score < 0.5:
            parts.append(f"Moon interference expected at {score.moon_separation_deg:.0f} degrees separation. ")

        # Time
        if score.hours_until_set < 2:
            parts.append(f"Only {score.hours_until_set:.1f} hours until it sets. ")

        parts.append(f"Overall score: {score.total_score:.0%}.")

        return "".join(parts)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def get_scorer(ephemeris_service=None, profile: str = "balanced") -> TargetScorer:
    """
    Create a TargetScorer with the specified profile.

    Args:
        ephemeris_service: Optional ephemeris service
        profile: One of "balanced", "deep_sky", "planetary", "widefield"

    Returns:
        Configured TargetScorer instance
    """
    scorer = TargetScorer(ephemeris_service)

    profile_map = {
        "balanced": ScoringWeight.BALANCED,
        "deep_sky": ScoringWeight.DEEP_SKY,
        "planetary": ScoringWeight.PLANETARY,
        "widefield": ScoringWeight.WIDEFIELD,
    }

    if profile in profile_map:
        scorer.set_profile(profile_map[profile])

    return scorer


# =============================================================================
# MAIN (for testing)
# =============================================================================


if __name__ == "__main__":
    print("NIGHTWATCH Target Scorer Test\n")

    # Create scorer without ephemeris (standalone test)
    scorer = TargetScorer()

    # Test targets (RA in hours, Dec in degrees)
    test_targets = [
        (5.59, 22.01, "M1", 8.4, 6.0),      # Crab Nebula
        (0.71, 41.27, "M31", 3.4, 178.0),   # Andromeda
        (13.42, 28.38, "M3", 6.2, 18.0),    # Globular cluster
        (18.87, 33.03, "M57", 8.8, 1.4),    # Ring Nebula
        (5.92, -5.45, "M42", 4.0, 85.0),    # Orion Nebula
    ]

    print("Target Scores (balanced profile):\n")
    print(f"{'Target':<8} {'Score':>6} {'Alt':>5} {'Moon':>5} {'HA':>5} {'Time':>5} Recommendation")
    print("-" * 70)

    for ra, dec, name, mag, size in test_targets:
        score = scorer.score_target(
            ra_hours=ra,
            dec_degrees=dec,
            target_id=name,
            magnitude=mag,
            size_arcmin=size,
        )
        print(f"{name:<8} {score.total_score:>5.0%} {score.altitude_score:>5.0%} "
              f"{score.moon_score:>5.0%} {score.hour_angle_score:>5.0%} "
              f"{score.time_remaining_score:>5.0%} {score.recommendation}")

    print("\n\nDeep Sky Profile Scores:\n")
    scorer.set_profile(ScoringWeight.DEEP_SKY)

    for ra, dec, name, mag, size in test_targets:
        score = scorer.score_target(ra, dec, name, mag, size)
        print(f"{name:<8} {score.total_score:>5.0%}")

    print("\n\nVoice Output Test:")
    scorer.set_profile(ScoringWeight.BALANCED)
    score = scorer.score_target(5.59, 22.01, "M1", 8.4, 6.0)
    print(scorer.format_score_summary(score))
