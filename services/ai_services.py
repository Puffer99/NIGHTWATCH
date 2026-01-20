"""
NIGHTWATCH AI Enhancement Services Facade (v0.5)

Unified entry point for all v0.5 AI Enhancement components.

This module provides:
- Single initialization for all AI services
- Proper dependency ordering
- Convenient access to all v0.5 capabilities
- Service health checks and status reporting

v0.5 Components:
- Intelligent Scheduling: scheduler, condition_provider, success_tracker
- Image Quality: frame_analyzer (external)
- Natural Language: conversation_context, clarification, suggestions,
                   user_preferences, sky_describer, session_narrator
- Model Updates: vocabulary_trainer, wake_word_trainer, object_identifier
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from enum import Enum
from pathlib import Path


# =============================================================================
# Enums
# =============================================================================


class ServiceStatus(Enum):
    """Service initialization status."""

    NOT_INITIALIZED = "not_initialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    DEGRADED = "degraded"  # Partial functionality


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ServiceHealth:
    """Health status for a single service."""

    name: str
    status: ServiceStatus
    message: Optional[str] = None
    last_check: datetime = field(default_factory=datetime.now)


@dataclass
class AIServicesConfig:
    """Configuration for AI services initialization."""

    # Data paths
    data_dir: Path = field(default_factory=lambda: Path.home() / ".nightwatch")

    # Observer location
    latitude_deg: float = 35.0
    longitude_deg: float = -120.0

    # Service toggles (disable for testing/resource constraints)
    enable_scheduling: bool = True
    enable_nlp: bool = True
    enable_voice: bool = True
    enable_catalog: bool = True

    # Initialization options
    lazy_init: bool = True  # Initialize on first access vs. all at once


# =============================================================================
# AI Services Facade
# =============================================================================


class AIServices:
    """
    Unified facade for all v0.5 AI Enhancement services.

    Provides centralized access to:
    - Intelligent Scheduling (scheduler, conditions, success tracking)
    - Natural Language (context, clarification, suggestions, preferences)
    - Voice Enhancement (vocabulary, wake word training)
    - Object Identification (offline recognition, descriptions)

    Example:
        ai = AIServices()
        ai.initialize()

        # Use scheduling
        schedule = ai.scheduler.create_schedule(candidates)

        # Use NLP
        description = ai.sky_describer.describe_object(obj, state)

        # Check status
        health = ai.get_health_report()
    """

    def __init__(self, config: Optional[AIServicesConfig] = None):
        """
        Initialize the AI services facade.

        Args:
            config: Configuration options (uses defaults if not provided)
        """
        self.config = config or AIServicesConfig()
        self._initialized = False
        self._init_time: Optional[datetime] = None

        # Service instances (lazy loaded)
        self._scheduler = None
        self._condition_provider = None
        self._success_tracker = None
        self._context_manager = None
        self._clarification = None
        self._suggestions = None
        self._user_preferences = None
        self._sky_describer = None
        self._session_narrator = None
        self._vocabulary_trainer = None
        self._wake_word_trainer = None
        self._object_identifier = None

        # Health tracking
        self._service_health: dict[str, ServiceHealth] = {}

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def initialize(self) -> dict[str, ServiceHealth]:
        """
        Initialize all enabled services.

        Returns:
            Dictionary of service health statuses
        """
        self._init_time = datetime.now()

        if not self.config.lazy_init:
            # Initialize everything now
            if self.config.enable_scheduling:
                _ = self.scheduler
                _ = self.condition_provider
                _ = self.success_tracker

            if self.config.enable_nlp:
                _ = self.context_manager
                _ = self.clarification
                _ = self.suggestions
                _ = self.user_preferences
                _ = self.sky_describer
                _ = self.session_narrator

            if self.config.enable_voice:
                _ = self.vocabulary_trainer
                _ = self.wake_word_trainer

            if self.config.enable_catalog:
                _ = self.object_identifier

        self._initialized = True
        return self.get_health_report()

    @property
    def is_initialized(self) -> bool:
        """Check if facade has been initialized."""
        return self._initialized

    # -------------------------------------------------------------------------
    # Scheduling Services (Steps 116-119)
    # -------------------------------------------------------------------------

    @property
    def scheduler(self):
        """Get the observing scheduler."""
        if self._scheduler is None:
            self._scheduler = self._init_service(
                "scheduler",
                self._create_scheduler
            )
        return self._scheduler

    @property
    def condition_provider(self):
        """Get the condition provider."""
        if self._condition_provider is None:
            self._condition_provider = self._init_service(
                "condition_provider",
                self._create_condition_provider
            )
        return self._condition_provider

    @property
    def success_tracker(self):
        """Get the success tracker."""
        if self._success_tracker is None:
            self._success_tracker = self._init_service(
                "success_tracker",
                self._create_success_tracker
            )
        return self._success_tracker

    # -------------------------------------------------------------------------
    # NLP Services (Steps 128-131, 137)
    # -------------------------------------------------------------------------

    @property
    def context_manager(self):
        """Get the conversation context manager."""
        if self._context_manager is None:
            self._context_manager = self._init_service(
                "context_manager",
                self._create_context_manager
            )
        return self._context_manager

    @property
    def clarification(self):
        """Get the clarification service."""
        if self._clarification is None:
            self._clarification = self._init_service(
                "clarification",
                self._create_clarification
            )
        return self._clarification

    @property
    def suggestions(self):
        """Get the suggestions service."""
        if self._suggestions is None:
            self._suggestions = self._init_service(
                "suggestions",
                self._create_suggestions
            )
        return self._suggestions

    @property
    def user_preferences(self):
        """Get user preferences."""
        if self._user_preferences is None:
            self._user_preferences = self._init_service(
                "user_preferences",
                self._create_user_preferences
            )
        return self._user_preferences

    @property
    def sky_describer(self):
        """Get the sky describer."""
        if self._sky_describer is None:
            self._sky_describer = self._init_service(
                "sky_describer",
                self._create_sky_describer
            )
        return self._sky_describer

    @property
    def session_narrator(self):
        """Get the session narrator."""
        if self._session_narrator is None:
            self._session_narrator = self._init_service(
                "session_narrator",
                self._create_session_narrator
            )
        return self._session_narrator

    # -------------------------------------------------------------------------
    # Voice Services (Steps 134-135)
    # -------------------------------------------------------------------------

    @property
    def vocabulary_trainer(self):
        """Get the vocabulary trainer."""
        if self._vocabulary_trainer is None:
            self._vocabulary_trainer = self._init_service(
                "vocabulary_trainer",
                self._create_vocabulary_trainer
            )
        return self._vocabulary_trainer

    @property
    def wake_word_trainer(self):
        """Get the wake word trainer."""
        if self._wake_word_trainer is None:
            self._wake_word_trainer = self._init_service(
                "wake_word_trainer",
                self._create_wake_word_trainer
            )
        return self._wake_word_trainer

    # -------------------------------------------------------------------------
    # Catalog Services (Step 136)
    # -------------------------------------------------------------------------

    @property
    def object_identifier(self):
        """Get the object identifier."""
        if self._object_identifier is None:
            self._object_identifier = self._init_service(
                "object_identifier",
                self._create_object_identifier
            )
        return self._object_identifier

    # -------------------------------------------------------------------------
    # Service Factory Methods
    # -------------------------------------------------------------------------

    def _create_scheduler(self):
        """Create scheduler instance."""
        from services.scheduling import ObservingScheduler
        return ObservingScheduler(
            latitude_deg=self.config.latitude_deg,
            longitude_deg=self.config.longitude_deg,
        )

    def _create_condition_provider(self):
        """Create condition provider instance."""
        from services.scheduling import ConditionProvider
        return ConditionProvider()

    def _create_success_tracker(self):
        """Create success tracker instance."""
        from services.catalog import SuccessTracker
        history_path = self.config.data_dir / "observation_history.json"
        return SuccessTracker(history_path=history_path)

    def _create_context_manager(self):
        """Create context manager instance."""
        from services.nlp import ConversationContext
        return ConversationContext()

    def _create_clarification(self):
        """Create clarification service instance."""
        from services.nlp import ClarificationService
        return ClarificationService()

    def _create_suggestions(self):
        """Create suggestions service instance."""
        from services.nlp import SuggestionService
        return SuggestionService()

    def _create_user_preferences(self):
        """Create user preferences instance."""
        from services.nlp import UserPreferences
        prefs_path = self.config.data_dir / "user_preferences.json"
        return UserPreferences(prefs_path=prefs_path)

    def _create_sky_describer(self):
        """Create sky describer instance."""
        from services.nlp import SkyDescriber
        return SkyDescriber()

    def _create_session_narrator(self):
        """Create session narrator instance."""
        from services.nlp import SessionNarrator
        return SessionNarrator()

    def _create_vocabulary_trainer(self):
        """Create vocabulary trainer instance."""
        from services.voice import VocabularyTrainer
        return VocabularyTrainer()

    def _create_wake_word_trainer(self):
        """Create wake word trainer instance."""
        from services.voice import WakeWordTrainer
        return WakeWordTrainer()

    def _create_object_identifier(self):
        """Create object identifier instance."""
        from services.catalog import ObjectIdentifier
        return ObjectIdentifier()

    # -------------------------------------------------------------------------
    # Service Initialization Helper
    # -------------------------------------------------------------------------

    def _init_service(self, name: str, factory) -> Any:
        """
        Initialize a service with health tracking.

        Args:
            name: Service name for health tracking
            factory: Callable that creates the service instance

        Returns:
            Service instance
        """
        self._service_health[name] = ServiceHealth(
            name=name,
            status=ServiceStatus.INITIALIZING,
        )

        try:
            instance = factory()
            self._service_health[name] = ServiceHealth(
                name=name,
                status=ServiceStatus.READY,
                message="Service initialized successfully",
            )
            return instance
        except Exception as e:
            self._service_health[name] = ServiceHealth(
                name=name,
                status=ServiceStatus.ERROR,
                message=str(e),
            )
            raise

    # -------------------------------------------------------------------------
    # Health Reporting
    # -------------------------------------------------------------------------

    def get_health_report(self) -> dict[str, ServiceHealth]:
        """
        Get health status of all services.

        Returns:
            Dictionary mapping service names to health status
        """
        return dict(self._service_health)

    def get_summary(self) -> dict[str, Any]:
        """
        Get summary of AI services status.

        Returns:
            Dictionary with status summary
        """
        health = self.get_health_report()

        ready_count = sum(
            1 for h in health.values()
            if h.status == ServiceStatus.READY
        )
        error_count = sum(
            1 for h in health.values()
            if h.status == ServiceStatus.ERROR
        )

        return {
            "initialized": self._initialized,
            "init_time": self._init_time.isoformat() if self._init_time else None,
            "services_ready": ready_count,
            "services_error": error_count,
            "services_total": len(health),
            "overall_status": (
                "ready" if error_count == 0 and ready_count > 0
                else "degraded" if ready_count > 0
                else "error" if error_count > 0
                else "not_initialized"
            ),
            "config": {
                "latitude": self.config.latitude_deg,
                "longitude": self.config.longitude_deg,
                "lazy_init": self.config.lazy_init,
            },
        }

    def check_service(self, name: str) -> ServiceHealth:
        """
        Check health of a specific service.

        Args:
            name: Service name

        Returns:
            ServiceHealth for the service
        """
        if name in self._service_health:
            return self._service_health[name]
        return ServiceHealth(
            name=name,
            status=ServiceStatus.NOT_INITIALIZED,
            message="Service not yet accessed",
        )

    # -------------------------------------------------------------------------
    # Convenience Methods
    # -------------------------------------------------------------------------

    def schedule_tonight(
        self,
        candidates: list[dict],
        constraints: Optional[dict] = None,
    ) -> dict:
        """
        Create tonight's observing schedule.

        Convenience method combining scheduler with session narrator.

        Args:
            candidates: List of candidate targets
            constraints: Optional scheduling constraints

        Returns:
            Dictionary with schedule and narration
        """
        from services.scheduling import SchedulingConstraints

        # Create schedule
        sched_constraints = None
        if constraints:
            sched_constraints = SchedulingConstraints(**constraints)

        result = self.scheduler.create_schedule(
            candidates,
            constraints=sched_constraints,
        )

        # Generate narration
        self.session_narrator.load_schedule(result.to_dict())
        plan_narration = self.session_narrator.narrate_plan()

        return {
            "schedule": result.to_dict(),
            "narration": plan_narration.text,
            "target_count": result.target_count,
            "total_minutes": result.total_observation_minutes,
        }

    def describe_target(
        self,
        target_id: str,
        ra_hours: float,
        dec_degrees: float,
        object_type: Optional[str] = None,
    ) -> dict:
        """
        Get comprehensive target description.

        Combines scheduler evaluation with sky description.

        Args:
            target_id: Target identifier
            ra_hours: Right ascension
            dec_degrees: Declination
            object_type: Optional object type

        Returns:
            Dictionary with evaluation and description
        """
        # Get scheduler evaluation
        target = {
            "id": target_id,
            "ra_hours": ra_hours,
            "dec_degrees": dec_degrees,
            "object_type": object_type,
        }
        evaluation = self.scheduler.evaluate_target(target)

        # Get condition scores
        scores = self.condition_provider.get_scores(
            target_id, ra_hours, dec_degrees, object_type
        )

        return {
            "target_id": target_id,
            "evaluation": evaluation,
            "condition_scores": scores,
            "recommendation": evaluation.get("recommendation", ""),
        }


# =============================================================================
# Module-level singleton
# =============================================================================

_ai_services: Optional[AIServices] = None


def get_ai_services(config: Optional[AIServicesConfig] = None) -> AIServices:
    """
    Get the global AI services instance.

    Args:
        config: Configuration (only used on first call)

    Returns:
        AIServices singleton instance
    """
    global _ai_services
    if _ai_services is None:
        _ai_services = AIServices(config)
    return _ai_services


def create_ai_services(config: Optional[AIServicesConfig] = None) -> AIServices:
    """
    Create a new AI services instance (not singleton).

    Args:
        config: Configuration options

    Returns:
        New AIServices instance
    """
    return AIServices(config)
