"""
NIGHTWATCH AI Services Facade Tests

Tests for the unified v0.5 AI Enhancement services facade.
"""

import pytest
from datetime import datetime
from pathlib import Path

from services.ai_services import (
    AIServices,
    AIServicesConfig,
    ServiceStatus,
    ServiceHealth,
    get_ai_services,
    create_ai_services,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def config():
    """Create a test configuration."""
    return AIServicesConfig(
        latitude_deg=35.0,
        longitude_deg=-120.0,
        lazy_init=True,
    )


@pytest.fixture
def ai_services(config):
    """Create AI services instance."""
    return AIServices(config)


@pytest.fixture
def eager_config():
    """Create config with eager initialization."""
    return AIServicesConfig(
        lazy_init=False,
        enable_scheduling=True,
        enable_nlp=True,
        enable_voice=True,
        enable_catalog=True,
    )


# =============================================================================
# ServiceStatus Tests
# =============================================================================


class TestServiceStatus:
    """Tests for ServiceStatus enum."""

    def test_status_values(self):
        """All status values defined."""
        assert ServiceStatus.NOT_INITIALIZED.value == "not_initialized"
        assert ServiceStatus.INITIALIZING.value == "initializing"
        assert ServiceStatus.READY.value == "ready"
        assert ServiceStatus.ERROR.value == "error"
        assert ServiceStatus.DEGRADED.value == "degraded"


# =============================================================================
# ServiceHealth Tests
# =============================================================================


class TestServiceHealth:
    """Tests for ServiceHealth dataclass."""

    def test_health_creation(self):
        """Create service health."""
        health = ServiceHealth(
            name="test_service",
            status=ServiceStatus.READY,
            message="All good",
        )

        assert health.name == "test_service"
        assert health.status == ServiceStatus.READY
        assert health.message == "All good"

    def test_health_has_timestamp(self):
        """Health includes timestamp."""
        health = ServiceHealth(
            name="test",
            status=ServiceStatus.READY,
        )

        assert health.last_check is not None
        assert isinstance(health.last_check, datetime)


# =============================================================================
# AIServicesConfig Tests
# =============================================================================


class TestAIServicesConfig:
    """Tests for AIServicesConfig dataclass."""

    def test_default_config(self):
        """Default configuration has sensible values."""
        config = AIServicesConfig()

        assert config.latitude_deg == 35.0
        assert config.longitude_deg == -120.0
        assert config.lazy_init is True
        assert config.enable_scheduling is True

    def test_custom_config(self):
        """Custom configuration is applied."""
        config = AIServicesConfig(
            latitude_deg=40.0,
            longitude_deg=-75.0,
            lazy_init=False,
        )

        assert config.latitude_deg == 40.0
        assert config.longitude_deg == -75.0
        assert config.lazy_init is False

    def test_data_dir_default(self):
        """Data directory defaults to home."""
        config = AIServicesConfig()
        assert config.data_dir == Path.home() / ".nightwatch"


# =============================================================================
# AIServices Initialization Tests
# =============================================================================


class TestAIServicesInit:
    """Tests for AIServices initialization."""

    def test_create_instance(self, config):
        """Create AI services instance."""
        ai = AIServices(config)

        assert ai is not None
        assert ai.config == config
        assert not ai.is_initialized

    def test_initialize_lazy(self, ai_services):
        """Initialize with lazy loading."""
        health = ai_services.initialize()

        assert ai_services.is_initialized
        # No services initialized yet with lazy loading
        assert len(health) == 0

    def test_initialize_eager(self, eager_config):
        """Initialize with eager loading."""
        ai = AIServices(eager_config)
        health = ai.initialize()

        assert ai.is_initialized
        # Services should be initialized
        assert len(health) > 0


# =============================================================================
# Scheduling Services Tests
# =============================================================================


class TestSchedulingServices:
    """Tests for scheduling services access."""

    def test_scheduler_access(self, ai_services):
        """Access scheduler service."""
        scheduler = ai_services.scheduler

        assert scheduler is not None
        # Check it's the right type
        from services.scheduling import ObservingScheduler
        assert isinstance(scheduler, ObservingScheduler)

    def test_scheduler_cached(self, ai_services):
        """Scheduler is cached."""
        s1 = ai_services.scheduler
        s2 = ai_services.scheduler

        assert s1 is s2

    def test_scheduler_health_tracked(self, ai_services):
        """Scheduler health is tracked."""
        _ = ai_services.scheduler

        health = ai_services.check_service("scheduler")
        assert health.status == ServiceStatus.READY

    def test_condition_provider_access(self, ai_services):
        """Access condition provider."""
        provider = ai_services.condition_provider

        assert provider is not None
        from services.scheduling import ConditionProvider
        assert isinstance(provider, ConditionProvider)

    def test_success_tracker_access(self, ai_services):
        """Access success tracker."""
        tracker = ai_services.success_tracker

        assert tracker is not None
        from services.catalog import SuccessTracker
        assert isinstance(tracker, SuccessTracker)


# =============================================================================
# NLP Services Tests
# =============================================================================


class TestNLPServices:
    """Tests for NLP services access."""

    def test_context_manager_access(self, ai_services):
        """Access context manager."""
        context = ai_services.context_manager

        assert context is not None
        from services.nlp import ConversationContext
        assert isinstance(context, ConversationContext)

    def test_clarification_access(self, ai_services):
        """Access clarification service."""
        clarification = ai_services.clarification

        assert clarification is not None
        from services.nlp import ClarificationService
        assert isinstance(clarification, ClarificationService)

    def test_suggestions_access(self, ai_services):
        """Access suggestions service."""
        suggestions = ai_services.suggestions

        assert suggestions is not None
        from services.nlp import SuggestionService
        assert isinstance(suggestions, SuggestionService)

    def test_user_preferences_access(self, ai_services):
        """Access user preferences."""
        prefs = ai_services.user_preferences

        assert prefs is not None
        from services.nlp import UserPreferences
        assert isinstance(prefs, UserPreferences)

    def test_sky_describer_access(self, ai_services):
        """Access sky describer."""
        describer = ai_services.sky_describer

        assert describer is not None
        from services.nlp import SkyDescriber
        assert isinstance(describer, SkyDescriber)

    def test_session_narrator_access(self, ai_services):
        """Access session narrator."""
        narrator = ai_services.session_narrator

        assert narrator is not None
        from services.nlp import SessionNarrator
        assert isinstance(narrator, SessionNarrator)


# =============================================================================
# Voice Services Tests
# =============================================================================


class TestVoiceServices:
    """Tests for voice services access."""

    def test_vocabulary_trainer_access(self, ai_services):
        """Access vocabulary trainer."""
        trainer = ai_services.vocabulary_trainer

        assert trainer is not None
        from services.voice import VocabularyTrainer
        assert isinstance(trainer, VocabularyTrainer)

    def test_wake_word_trainer_access(self, ai_services):
        """Access wake word trainer."""
        trainer = ai_services.wake_word_trainer

        assert trainer is not None
        from services.voice import WakeWordTrainer
        assert isinstance(trainer, WakeWordTrainer)


# =============================================================================
# Catalog Services Tests
# =============================================================================


class TestCatalogServices:
    """Tests for catalog services access."""

    def test_object_identifier_access(self, ai_services):
        """Access object identifier."""
        identifier = ai_services.object_identifier

        assert identifier is not None
        from services.catalog import ObjectIdentifier
        assert isinstance(identifier, ObjectIdentifier)


# =============================================================================
# Health Reporting Tests
# =============================================================================


class TestHealthReporting:
    """Tests for health reporting."""

    def test_get_health_report(self, ai_services):
        """Get health report."""
        # Access some services
        _ = ai_services.scheduler
        _ = ai_services.context_manager

        report = ai_services.get_health_report()

        assert "scheduler" in report
        assert "context_manager" in report
        assert report["scheduler"].status == ServiceStatus.READY

    def test_get_summary(self, ai_services):
        """Get status summary."""
        _ = ai_services.scheduler

        summary = ai_services.get_summary()

        assert summary["initialized"] is False  # Not explicitly initialized
        assert summary["services_ready"] >= 1
        assert summary["services_error"] == 0
        assert "config" in summary

    def test_check_uninitialized_service(self, ai_services):
        """Check health of uninitialized service."""
        health = ai_services.check_service("scheduler")

        assert health.status == ServiceStatus.NOT_INITIALIZED

    def test_check_initialized_service(self, ai_services):
        """Check health of initialized service."""
        _ = ai_services.scheduler

        health = ai_services.check_service("scheduler")

        assert health.status == ServiceStatus.READY


# =============================================================================
# Convenience Methods Tests
# =============================================================================


class TestConvenienceMethods:
    """Tests for convenience methods."""

    def test_schedule_tonight(self, ai_services):
        """Create tonight's schedule."""
        candidates = [
            {
                "id": "M31",
                "name": "Andromeda Galaxy",
                "ra_hours": 0.712,
                "dec_degrees": 41.269,
            },
            {
                "id": "M42",
                "name": "Orion Nebula",
                "ra_hours": 5.588,
                "dec_degrees": -5.391,
            },
        ]

        result = ai_services.schedule_tonight(candidates)

        assert "schedule" in result
        assert "narration" in result
        assert "target_count" in result
        assert isinstance(result["narration"], str)

    def test_describe_target(self, ai_services):
        """Get target description."""
        result = ai_services.describe_target(
            target_id="M31",
            ra_hours=0.712,
            dec_degrees=41.269,
            object_type="galaxy",
        )

        assert "target_id" in result
        assert "evaluation" in result
        assert "condition_scores" in result
        assert result["target_id"] == "M31"


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunctions:
    """Tests for module-level factories."""

    def test_get_ai_services(self):
        """get_ai_services returns instance."""
        ai = get_ai_services()
        assert isinstance(ai, AIServices)

    def test_get_ai_services_singleton(self):
        """get_ai_services returns same instance."""
        ai1 = get_ai_services()
        ai2 = get_ai_services()
        assert ai1 is ai2

    def test_create_ai_services(self, config):
        """create_ai_services creates new instance."""
        ai1 = create_ai_services(config)
        ai2 = create_ai_services(config)
        assert ai1 is not ai2


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for AI services."""

    def test_all_services_accessible(self, ai_services):
        """All services can be accessed."""
        # Scheduling
        assert ai_services.scheduler is not None
        assert ai_services.condition_provider is not None
        assert ai_services.success_tracker is not None

        # NLP
        assert ai_services.context_manager is not None
        assert ai_services.clarification is not None
        assert ai_services.suggestions is not None
        assert ai_services.user_preferences is not None
        assert ai_services.sky_describer is not None
        assert ai_services.session_narrator is not None

        # Voice
        assert ai_services.vocabulary_trainer is not None
        assert ai_services.wake_word_trainer is not None

        # Catalog
        assert ai_services.object_identifier is not None

    def test_all_services_healthy(self, ai_services):
        """All accessed services report healthy."""
        # Access all services
        _ = ai_services.scheduler
        _ = ai_services.condition_provider
        _ = ai_services.context_manager
        _ = ai_services.clarification
        _ = ai_services.sky_describer
        _ = ai_services.vocabulary_trainer
        _ = ai_services.object_identifier

        report = ai_services.get_health_report()

        for name, health in report.items():
            assert health.status == ServiceStatus.READY, f"{name} not ready"

    def test_complete_workflow(self, ai_services):
        """Test complete scheduling workflow."""
        # Create candidates
        candidates = [
            {
                "id": "M31",
                "name": "Andromeda Galaxy",
                "ra_hours": 0.712,
                "dec_degrees": 41.269,
                "magnitude": 3.4,
                "object_type": "galaxy",
            },
        ]

        # Schedule
        result = ai_services.schedule_tonight(candidates)
        assert result["target_count"] >= 0

        # Get target info
        info = ai_services.describe_target(
            "M31", 0.712, 41.269, "galaxy"
        )
        assert "evaluation" in info
        assert "condition_scores" in info

        # Check overall health
        summary = ai_services.get_summary()
        assert summary["services_error"] == 0


# =============================================================================
# Configuration Tests
# =============================================================================


class TestConfigurationHandling:
    """Tests for configuration handling."""

    def test_location_passed_to_scheduler(self):
        """Location config is passed to scheduler."""
        config = AIServicesConfig(
            latitude_deg=40.0,
            longitude_deg=-75.0,
        )
        ai = AIServices(config)

        scheduler = ai.scheduler
        assert scheduler.latitude == 40.0
        assert scheduler.longitude == -75.0

    def test_disabled_services_not_initialized(self):
        """Disabled services are not initialized."""
        config = AIServicesConfig(
            enable_scheduling=False,
            lazy_init=False,
        )
        ai = AIServices(config)
        ai.initialize()

        # Scheduler should not be in health report
        report = ai.get_health_report()
        assert "scheduler" not in report
