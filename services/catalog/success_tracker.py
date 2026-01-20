"""
NIGHTWATCH Historical Success Rate Tracker (Step 119)

Tracks historical observation success rates and uses them to improve
target scheduling decisions. Learns from past observations to predict
future success probability.

Factors tracked:
- Per-target success rates and quality scores
- Condition-based success (weather, moon, altitude)
- Equipment-based success (focus quality, guiding accuracy)
- Time-based patterns (seasonal, nightly)

Usage:
    from services.catalog.success_tracker import SuccessTracker

    tracker = SuccessTracker()
    tracker.record_observation("M31", success=True, quality=0.85, conditions={...})

    # Get success prediction for scheduling
    prediction = tracker.predict_success("M31", current_conditions)
    adjusted_score = base_score * prediction.confidence_factor
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("NIGHTWATCH.SuccessTracker")


__all__ = [
    "SuccessTracker",
    "ObservationRecord",
    "SuccessPrediction",
    "ConditionBucket",
    "get_success_tracker",
]


# =============================================================================
# Data Classes
# =============================================================================


class ConditionBucket(Enum):
    """Buckets for condition-based analysis."""
    EXCELLENT = "excellent"  # Perfect conditions
    GOOD = "good"           # Good conditions
    FAIR = "fair"           # Acceptable conditions
    POOR = "poor"           # Marginal conditions


@dataclass
class ObservationRecord:
    """Record of a single observation attempt."""
    target_id: str
    timestamp: datetime
    success: bool
    quality_score: float  # 0.0-1.0

    # Condition factors at time of observation
    altitude_deg: Optional[float] = None
    moon_separation_deg: Optional[float] = None
    moon_illumination: Optional[float] = None
    seeing_arcsec: Optional[float] = None
    humidity_percent: Optional[float] = None

    # Equipment factors
    fwhm_arcsec: Optional[float] = None
    guiding_rms_arcsec: Optional[float] = None

    # Timing
    hour_angle: Optional[float] = None
    local_hour: Optional[int] = None
    month: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "target_id": self.target_id,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "quality_score": self.quality_score,
            "altitude_deg": self.altitude_deg,
            "moon_separation_deg": self.moon_separation_deg,
            "moon_illumination": self.moon_illumination,
            "seeing_arcsec": self.seeing_arcsec,
            "humidity_percent": self.humidity_percent,
            "fwhm_arcsec": self.fwhm_arcsec,
            "guiding_rms_arcsec": self.guiding_rms_arcsec,
            "hour_angle": self.hour_angle,
            "local_hour": self.local_hour,
            "month": self.month,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ObservationRecord":
        """Create from dictionary."""
        return cls(
            target_id=data["target_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            success=data["success"],
            quality_score=data["quality_score"],
            altitude_deg=data.get("altitude_deg"),
            moon_separation_deg=data.get("moon_separation_deg"),
            moon_illumination=data.get("moon_illumination"),
            seeing_arcsec=data.get("seeing_arcsec"),
            humidity_percent=data.get("humidity_percent"),
            fwhm_arcsec=data.get("fwhm_arcsec"),
            guiding_rms_arcsec=data.get("guiding_rms_arcsec"),
            hour_angle=data.get("hour_angle"),
            local_hour=data.get("local_hour"),
            month=data.get("month"),
        )


@dataclass
class SuccessPrediction:
    """Prediction of observation success probability."""
    target_id: str
    predicted_success_rate: float  # 0.0-1.0
    confidence: float  # 0.0-1.0 (based on sample size)
    confidence_factor: float  # Multiplier for target scoring

    # Contributing factors
    historical_rate: float
    condition_adjustment: float
    recency_adjustment: float

    # Sample info
    total_observations: int
    recent_observations: int  # Last 30 days

    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "target_id": self.target_id,
            "predicted_success_rate": self.predicted_success_rate,
            "confidence": self.confidence,
            "confidence_factor": self.confidence_factor,
            "historical_rate": self.historical_rate,
            "condition_adjustment": self.condition_adjustment,
            "recency_adjustment": self.recency_adjustment,
            "total_observations": self.total_observations,
            "recent_observations": self.recent_observations,
            "reason": self.reason,
        }


# =============================================================================
# Success Tracker
# =============================================================================


class SuccessTracker:
    """
    Tracks and analyzes historical observation success rates.

    Uses past observation data to predict future success probability
    and adjust target scoring accordingly.
    """

    DEFAULT_HISTORY_PATH = Path.home() / ".nightwatch" / "observation_history.json"
    MAX_HISTORY_RECORDS = 10000
    RECENT_WINDOW_DAYS = 30

    def __init__(self, history_path: Optional[Path] = None):
        """
        Initialize success tracker.

        Args:
            history_path: Path to history file (uses default if None)
        """
        self._history_path = history_path or self.DEFAULT_HISTORY_PATH

        # All observation records
        self._records: List[ObservationRecord] = []

        # Cached statistics by target
        self._target_stats: Dict[str, Dict[str, Any]] = {}

        # Condition-based statistics
        self._condition_stats: Dict[ConditionBucket, Dict[str, float]] = {
            bucket: {"success_count": 0, "total_count": 0}
            for bucket in ConditionBucket
        }

        # Load existing history
        self._load()
        self._rebuild_stats()

        logger.debug(f"SuccessTracker initialized with {len(self._records)} records")

    # =========================================================================
    # Recording Observations
    # =========================================================================

    def record_observation(
        self,
        target_id: str,
        success: bool,
        quality_score: float = 0.5,
        altitude_deg: Optional[float] = None,
        moon_separation_deg: Optional[float] = None,
        moon_illumination: Optional[float] = None,
        seeing_arcsec: Optional[float] = None,
        humidity_percent: Optional[float] = None,
        fwhm_arcsec: Optional[float] = None,
        guiding_rms_arcsec: Optional[float] = None,
        hour_angle: Optional[float] = None,
    ):
        """
        Record an observation attempt.

        Args:
            target_id: Target identifier
            success: Whether observation was successful
            quality_score: Quality of result (0.0-1.0)
            altitude_deg: Altitude at observation time
            moon_separation_deg: Angular separation from moon
            moon_illumination: Moon illumination fraction (0-1)
            seeing_arcsec: Atmospheric seeing
            humidity_percent: Relative humidity
            fwhm_arcsec: Measured FWHM
            guiding_rms_arcsec: Guiding RMS error
            hour_angle: Hour angle at observation
        """
        now = datetime.now()

        record = ObservationRecord(
            target_id=target_id,
            timestamp=now,
            success=success,
            quality_score=quality_score,
            altitude_deg=altitude_deg,
            moon_separation_deg=moon_separation_deg,
            moon_illumination=moon_illumination,
            seeing_arcsec=seeing_arcsec,
            humidity_percent=humidity_percent,
            fwhm_arcsec=fwhm_arcsec,
            guiding_rms_arcsec=guiding_rms_arcsec,
            hour_angle=hour_angle,
            local_hour=now.hour,
            month=now.month,
        )

        self._records.append(record)
        self._update_stats(record)

        # Prune old records if needed
        if len(self._records) > self.MAX_HISTORY_RECORDS:
            self._records = self._records[-self.MAX_HISTORY_RECORDS:]
            self._rebuild_stats()

        self._save()

        logger.debug(f"Recorded observation: {target_id} success={success} quality={quality_score:.2f}")

    # =========================================================================
    # Success Prediction
    # =========================================================================

    def predict_success(
        self,
        target_id: str,
        altitude_deg: Optional[float] = None,
        moon_separation_deg: Optional[float] = None,
        moon_illumination: Optional[float] = None,
        seeing_arcsec: Optional[float] = None,
    ) -> SuccessPrediction:
        """
        Predict success probability for a target under given conditions.

        Args:
            target_id: Target to predict
            altitude_deg: Expected altitude
            moon_separation_deg: Expected moon separation
            moon_illumination: Current moon illumination
            seeing_arcsec: Current seeing conditions

        Returns:
            SuccessPrediction with probability and confidence
        """
        stats = self._target_stats.get(target_id)

        # No history for this target
        if not stats or stats["total"] == 0:
            return self._predict_no_history(target_id, altitude_deg, moon_separation_deg)

        # Calculate base historical rate
        historical_rate = stats["success_count"] / stats["total"]

        # Calculate condition adjustment
        condition_adj = self._calculate_condition_adjustment(
            altitude_deg, moon_separation_deg, moon_illumination, seeing_arcsec
        )

        # Calculate recency adjustment (weight recent observations more)
        recency_adj = self._calculate_recency_adjustment(target_id)

        # Combine factors
        predicted_rate = historical_rate * condition_adj * recency_adj
        predicted_rate = max(0.1, min(1.0, predicted_rate))  # Clamp

        # Calculate confidence based on sample size
        confidence = self._calculate_confidence(stats["total"], stats["recent_count"])

        # Confidence factor for scoring (0.5-1.5 range)
        # High success + high confidence = boost
        # Low success + high confidence = penalty
        confidence_factor = 0.5 + predicted_rate * confidence

        reason = self._build_reason(stats, historical_rate, condition_adj, recency_adj)

        return SuccessPrediction(
            target_id=target_id,
            predicted_success_rate=predicted_rate,
            confidence=confidence,
            confidence_factor=confidence_factor,
            historical_rate=historical_rate,
            condition_adjustment=condition_adj,
            recency_adjustment=recency_adj,
            total_observations=stats["total"],
            recent_observations=stats["recent_count"],
            reason=reason,
        )

    def _predict_no_history(
        self,
        target_id: str,
        altitude_deg: Optional[float],
        moon_separation_deg: Optional[float],
    ) -> SuccessPrediction:
        """Predict for target with no history."""
        # Use global success rate if available
        total_obs = sum(s["total"] for s in self._target_stats.values())
        total_success = sum(s["success_count"] for s in self._target_stats.values())

        if total_obs > 0:
            global_rate = total_success / total_obs
        else:
            global_rate = 0.7  # Optimistic default

        return SuccessPrediction(
            target_id=target_id,
            predicted_success_rate=global_rate,
            confidence=0.3,  # Low confidence
            confidence_factor=1.0,  # Neutral
            historical_rate=global_rate,
            condition_adjustment=1.0,
            recency_adjustment=1.0,
            total_observations=0,
            recent_observations=0,
            reason="No history for target, using global average",
        )

    def _calculate_condition_adjustment(
        self,
        altitude_deg: Optional[float],
        moon_separation_deg: Optional[float],
        moon_illumination: Optional[float],
        seeing_arcsec: Optional[float],
    ) -> float:
        """Calculate adjustment based on current conditions."""
        adjustment = 1.0

        # Altitude adjustment
        if altitude_deg is not None:
            if altitude_deg < 20:
                adjustment *= 0.7
            elif altitude_deg < 30:
                adjustment *= 0.85
            elif altitude_deg > 60:
                adjustment *= 1.1

        # Moon adjustment
        if moon_separation_deg is not None and moon_illumination is not None:
            if moon_illumination > 0.5:  # Bright moon
                if moon_separation_deg < 30:
                    adjustment *= 0.6
                elif moon_separation_deg < 60:
                    adjustment *= 0.8

        # Seeing adjustment
        if seeing_arcsec is not None:
            if seeing_arcsec > 4.0:
                adjustment *= 0.7
            elif seeing_arcsec > 2.5:
                adjustment *= 0.9
            elif seeing_arcsec < 1.5:
                adjustment *= 1.1

        return adjustment

    def _calculate_recency_adjustment(self, target_id: str) -> float:
        """Weight recent success/failure more heavily."""
        recent_records = [
            r for r in self._records
            if r.target_id == target_id
            and (datetime.now() - r.timestamp).days <= self.RECENT_WINDOW_DAYS
        ]

        if not recent_records:
            return 1.0  # No recent data

        recent_success = sum(1 for r in recent_records if r.success)
        recent_rate = recent_success / len(recent_records)

        stats = self._target_stats.get(target_id, {})
        historical_rate = stats.get("success_count", 0) / max(1, stats.get("total", 1))

        # Blend: 60% recent, 40% historical
        if recent_rate > historical_rate:
            return 1.0 + 0.2 * (recent_rate - historical_rate)  # Boost
        else:
            return 1.0 - 0.2 * (historical_rate - recent_rate)  # Penalty

    def _calculate_confidence(self, total: int, recent: int) -> float:
        """Calculate confidence based on sample size."""
        # More observations = higher confidence
        # Recent observations also boost confidence
        base_confidence = min(1.0, total / 20)  # Max at 20 obs
        recency_bonus = min(0.2, recent / 10 * 0.2)  # Up to 0.2 bonus

        return min(1.0, base_confidence + recency_bonus)

    def _build_reason(
        self,
        stats: Dict,
        historical: float,
        condition_adj: float,
        recency_adj: float,
    ) -> str:
        """Build explanation string."""
        parts = [f"Historical rate: {historical:.0%}"]

        if condition_adj < 0.9:
            parts.append("conditions below optimal")
        elif condition_adj > 1.05:
            parts.append("good conditions")

        if recency_adj > 1.05:
            parts.append("recent success trend")
        elif recency_adj < 0.95:
            parts.append("recent difficulties")

        parts.append(f"({stats['total']} observations)")

        return ", ".join(parts)

    # =========================================================================
    # Statistics and Analysis
    # =========================================================================

    def get_target_statistics(self, target_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed statistics for a target."""
        stats = self._target_stats.get(target_id)
        if not stats:
            return None

        return {
            "target_id": target_id,
            "total_observations": stats["total"],
            "successful_observations": stats["success_count"],
            "success_rate": stats["success_count"] / stats["total"] if stats["total"] > 0 else 0,
            "average_quality": stats["total_quality"] / stats["success_count"] if stats["success_count"] > 0 else 0,
            "recent_observations": stats["recent_count"],
            "last_observed": stats["last_observed"].isoformat() if stats["last_observed"] else None,
        }

    def get_best_performing_targets(self, min_observations: int = 3, limit: int = 10) -> List[Dict[str, Any]]:
        """Get targets with best success rates."""
        targets = []

        for target_id, stats in self._target_stats.items():
            if stats["total"] >= min_observations:
                success_rate = stats["success_count"] / stats["total"]
                avg_quality = stats["total_quality"] / stats["success_count"] if stats["success_count"] > 0 else 0

                targets.append({
                    "target_id": target_id,
                    "success_rate": success_rate,
                    "average_quality": avg_quality,
                    "observations": stats["total"],
                })

        # Sort by success rate, then quality
        targets.sort(key=lambda t: (t["success_rate"], t["average_quality"]), reverse=True)

        return targets[:limit]

    def get_struggling_targets(self, min_observations: int = 3, limit: int = 10) -> List[Dict[str, Any]]:
        """Get targets with poor success rates that might need attention."""
        targets = []

        for target_id, stats in self._target_stats.items():
            if stats["total"] >= min_observations:
                success_rate = stats["success_count"] / stats["total"]
                if success_rate < 0.7:  # Below 70% success
                    targets.append({
                        "target_id": target_id,
                        "success_rate": success_rate,
                        "observations": stats["total"],
                        "failures": stats["total"] - stats["success_count"],
                    })

        # Sort by success rate (lowest first)
        targets.sort(key=lambda t: t["success_rate"])

        return targets[:limit]

    def get_condition_analysis(self) -> Dict[str, Any]:
        """Analyze success rates by condition bucket."""
        result = {}

        for bucket in ConditionBucket:
            stats = self._condition_stats[bucket]
            total = stats["total_count"]
            success = stats["success_count"]

            result[bucket.value] = {
                "total": total,
                "success": success,
                "rate": success / total if total > 0 else 0,
            }

        return result

    def get_overall_statistics(self) -> Dict[str, Any]:
        """Get overall success statistics."""
        total = len(self._records)
        if total == 0:
            return {
                "total_observations": 0,
                "unique_targets": 0,
                "overall_success_rate": 0,
            }

        success = sum(1 for r in self._records if r.success)
        recent_cutoff = datetime.now() - timedelta(days=self.RECENT_WINDOW_DAYS)
        recent = [r for r in self._records if r.timestamp > recent_cutoff]
        recent_success = sum(1 for r in recent if r.success)

        return {
            "total_observations": total,
            "unique_targets": len(self._target_stats),
            "overall_success_rate": success / total,
            "recent_observations": len(recent),
            "recent_success_rate": recent_success / len(recent) if recent else 0,
        }

    # =========================================================================
    # Internal Statistics Management
    # =========================================================================

    def _update_stats(self, record: ObservationRecord):
        """Update cached statistics with new record."""
        target_id = record.target_id

        if target_id not in self._target_stats:
            self._target_stats[target_id] = {
                "total": 0,
                "success_count": 0,
                "total_quality": 0.0,
                "recent_count": 0,
                "last_observed": None,
            }

        stats = self._target_stats[target_id]
        stats["total"] += 1
        if record.success:
            stats["success_count"] += 1
            stats["total_quality"] += record.quality_score
        stats["last_observed"] = record.timestamp

        # Update recent count
        recent_cutoff = datetime.now() - timedelta(days=self.RECENT_WINDOW_DAYS)
        if record.timestamp > recent_cutoff:
            stats["recent_count"] += 1

        # Update condition stats
        bucket = self._categorize_conditions(record)
        self._condition_stats[bucket]["total_count"] += 1
        if record.success:
            self._condition_stats[bucket]["success_count"] += 1

    def _rebuild_stats(self):
        """Rebuild all statistics from records."""
        self._target_stats.clear()
        for bucket in ConditionBucket:
            self._condition_stats[bucket] = {"success_count": 0, "total_count": 0}

        for record in self._records:
            self._update_stats(record)

    def _categorize_conditions(self, record: ObservationRecord) -> ConditionBucket:
        """Categorize observation conditions into bucket."""
        score = 0
        factors = 0

        if record.altitude_deg is not None:
            factors += 1
            if record.altitude_deg > 60:
                score += 3
            elif record.altitude_deg > 40:
                score += 2
            elif record.altitude_deg > 25:
                score += 1

        if record.moon_separation_deg is not None:
            factors += 1
            if record.moon_separation_deg > 90:
                score += 3
            elif record.moon_separation_deg > 60:
                score += 2
            elif record.moon_separation_deg > 30:
                score += 1

        if record.seeing_arcsec is not None:
            factors += 1
            if record.seeing_arcsec < 1.5:
                score += 3
            elif record.seeing_arcsec < 2.5:
                score += 2
            elif record.seeing_arcsec < 4.0:
                score += 1

        if factors == 0:
            return ConditionBucket.FAIR

        avg_score = score / factors
        if avg_score >= 2.5:
            return ConditionBucket.EXCELLENT
        elif avg_score >= 1.5:
            return ConditionBucket.GOOD
        elif avg_score >= 0.5:
            return ConditionBucket.FAIR
        else:
            return ConditionBucket.POOR

    # =========================================================================
    # Persistence
    # =========================================================================

    def _save(self):
        """Save history to disk."""
        try:
            self._history_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "version": 1,
                "saved_at": datetime.now().isoformat(),
                "records": [r.to_dict() for r in self._records],
            }

            with open(self._history_path, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to save history: {e}")

    def _load(self):
        """Load history from disk."""
        if not self._history_path.exists():
            return

        try:
            with open(self._history_path, "r") as f:
                data = json.load(f)

            self._records = [
                ObservationRecord.from_dict(r)
                for r in data.get("records", [])
            ]

            logger.debug(f"Loaded {len(self._records)} observation records")

        except Exception as e:
            logger.warning(f"Failed to load history: {e}")

    def clear_history(self):
        """Clear all observation history."""
        self._records.clear()
        self._target_stats.clear()
        for bucket in ConditionBucket:
            self._condition_stats[bucket] = {"success_count": 0, "total_count": 0}

        if self._history_path.exists():
            self._history_path.unlink()

        logger.info("Observation history cleared")


# =============================================================================
# Module-level instance and factory
# =============================================================================


_default_tracker: Optional[SuccessTracker] = None


def get_success_tracker(history_path: Optional[Path] = None) -> SuccessTracker:
    """
    Get or create the default success tracker.

    Args:
        history_path: Optional custom path for history file

    Returns:
        SuccessTracker instance
    """
    global _default_tracker
    if _default_tracker is None:
        _default_tracker = SuccessTracker(history_path=history_path)
    return _default_tracker
