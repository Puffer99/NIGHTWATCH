"""
NIGHTWATCH Voice Control Pipeline

Complete voice control system for telescope operation:
- STT: Whisper-based speech-to-text
- Tools: LLM function calling for telescope control
- TTS: Piper-based text-to-speech output

Designed for local inference on DGX Spark with <2 second latency target.
"""

from .stt import WhisperSTT, TranscriptionResult
from .tools import ToolRegistry, TELESCOPE_SYSTEM_PROMPT
from .tts import TTSService

__all__ = [
    "WhisperSTT",
    "TranscriptionResult",
    "ToolRegistry",
    "TELESCOPE_SYSTEM_PROMPT",
    "TTSService",
]
