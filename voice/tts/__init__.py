"""
NIGHTWATCH Voice TTS Service

Text-to-speech output using Piper or system TTS.
"""

from .piper_service import (
    TTSService,
    TTSConfig,
    TTSBackend,
    VoiceStyle,
    PiperTTS,
    EspeakTTS,
    SystemTTS,
    ResponseLibrary,
)

__all__ = [
    "TTSService",
    "TTSConfig",
    "TTSBackend",
    "VoiceStyle",
    "PiperTTS",
    "EspeakTTS",
    "SystemTTS",
    "ResponseLibrary",
]
