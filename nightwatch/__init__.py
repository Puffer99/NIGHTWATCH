"""
NIGHTWATCH - Voice-Controlled Autonomous Observatory System

A fully autonomous, voice-controlled telescope observatory running entirely
on-premise with local AI processing. No cloud dependencies.

Architecture:
    - Local-first: All AI/voice/control processing on DGX Spark
    - Modular microservices: ASCOM Alpaca, Wyoming protocol, OnStepX, INDI
    - Safety-first: Environmental interlocks via safety_monitor
    - Expert-driven: POS methodology for novel decisions

License: CC BY-NC-SA 4.0
"""

__version__ = "0.1.0-dev"
__author__ = "THOC Labs"
__license__ = "CC BY-NC-SA 4.0"

# Version tuple for programmatic comparison
VERSION_INFO = (0, 1, 0, "dev")

# Core exceptions (import base class for convenience)
from nightwatch.exceptions import NightwatchError

# Core constants (import commonly used constants for convenience)
from nightwatch.constants import (
    NIGHTWATCH_VERSION,
    NIGHTWATCH_NAME,
)
