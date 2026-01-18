"""
NIGHTWATCH Voice STT Service

Speech-to-text using Whisper for voice commands.
"""

from .whisper_service import (
    WhisperSTT,
    WhisperModelSize,
    TranscriptionResult,
    AudioConfig,
    VoiceActivityDetector,
    PushToTalkRecorder,
)

__all__ = [
    "WhisperSTT",
    "WhisperModelSize",
    "TranscriptionResult",
    "AudioConfig",
    "VoiceActivityDetector",
    "PushToTalkRecorder",
]
