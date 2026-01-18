"""
NIGHTWATCH Safety Monitor Service

Provides automated safety monitoring and control for observatory operation.
"""

from .monitor import (
    SafetyMonitor,
    SafetyStatus,
    SafetyAction,
    SafetyThresholds,
    ObservatoryState,
    AlertLevel,
    NightwatchSafetySystem,
)

__all__ = [
    "SafetyMonitor",
    "SafetyStatus",
    "SafetyAction",
    "SafetyThresholds",
    "ObservatoryState",
    "AlertLevel",
    "NightwatchSafetySystem",
]
