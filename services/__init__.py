"""
NIGHTWATCH Services Package

This package contains all NIGHTWATCH service modules organized by function.

v0.5 AI Enhancement Services (Complete)
=======================================

The v0.5 milestone provides comprehensive AI-powered capabilities:

Intelligent Scheduling (services.scheduling)
--------------------------------------------
- ObservingScheduler: Weather-aware target scheduling
- ConditionProvider: Real-time condition data integration
- SuccessTracker: Historical observation success learning

Image Quality Analysis (services.camera)
----------------------------------------
- FrameAnalyzer: FWHM measurement, frame rejection, tracking error detection

Natural Language (services.nlp)
-------------------------------
- ConversationContext: Multi-turn conversation memory
- ClarificationService: Ambiguity resolution
- SuggestionService: Proactive observing suggestions
- UserPreferences: Learning user preferences
- SkyDescriber: Natural language sky descriptions
- SessionNarrator: Voice-friendly session narration

Voice Enhancement (services.voice)
----------------------------------
- VocabularyTrainer: Astronomy vocabulary optimization
- WakeWordTrainer: Custom wake word personalization

Object Recognition (services.catalog)
-------------------------------------
- ObjectIdentifier: Offline celestial object identification
- TargetScorer: Multi-factor target scoring

Unified Access
--------------
The AIServices facade provides single-point access to all v0.5 capabilities:

    from services import AIServices

    ai = AIServices()
    ai.initialize()

    # Schedule tonight's observations
    result = ai.schedule_tonight(candidates)

    # Get target information
    info = ai.describe_target("M31", ra, dec)

    # Check service health
    health = ai.get_health_report()

Core Services
=============

Equipment Control
-----------------
- services.alpaca: ASCOM Alpaca device control
- services.mount_control: Mount control (LX200, OnStepX)
- services.camera: Camera control (ZWO ASI)
- services.focus: Focuser control
- services.guiding: PHD2 guiding integration
- services.enclosure: Roof/dome control

Environmental
-------------
- services.weather: Weather station integration (Ecowitt, CloudWatcher)
- services.safety_monitor: Safety interlock system
- services.ephemeris: Astronomical calculations (Skyfield)

Data Management
---------------
- services.catalog: Object catalogs (Messier, NGC, IC)
- services.astrometry: Plate solving

Simulation
----------
- services.simulators: Hardware simulators for testing
"""

# v0.5 AI Enhancement - Unified Access Point
from .ai_services import (
    AIServices,
    AIServicesConfig,
    ServiceStatus,
    ServiceHealth,
    get_ai_services,
    create_ai_services,
)

__all__ = [
    # AI Services Facade (v0.5)
    "AIServices",
    "AIServicesConfig",
    "ServiceStatus",
    "ServiceHealth",
    "get_ai_services",
    "create_ai_services",
]

__version__ = "0.5.0"
