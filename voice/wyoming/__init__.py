"""
NIGHTWATCH Wyoming Protocol Implementation

This module implements the Wyoming protocol for standardized voice service
communication. Wyoming is a protocol used by the Rhasspy voice assistant
ecosystem for interoperable speech services.

The protocol enables:
- Decoupled STT/TTS services that can run on different machines
- Compatibility with Home Assistant voice assistants
- A/B testing different speech backends
- Standard message format for audio streaming and transcription
"""

from .protocol import (
    MessageType,
    WyomingMessage,
    AudioChunk,
    AudioStart,
    AudioStop,
    Transcript,
    Synthesize,
    Info,
    Describe,
)
from .stt_server import WyomingSTTServer
from .tts_server import WyomingTTSServer

__all__ = [
    # Protocol types
    "MessageType",
    "WyomingMessage",
    "AudioChunk",
    "AudioStart",
    "AudioStop",
    "Transcript",
    "Synthesize",
    "Info",
    "Describe",
    # Servers
    "WyomingSTTServer",
    "WyomingTTSServer",
]
