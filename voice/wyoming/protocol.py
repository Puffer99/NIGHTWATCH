"""
NIGHTWATCH Wyoming Protocol Message Types

Implements the Wyoming protocol message format for voice service communication.
This enables standardized communication between STT, TTS, and voice assistant
components following the Rhasspy Wyoming specification.

Reference: https://github.com/rhasspy/wyoming
"""

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, Any, List, Union
import base64


class MessageType(Enum):
    """Wyoming protocol message types."""
    # Audio events
    AUDIO_CHUNK = "audio-chunk"
    AUDIO_START = "audio-start"
    AUDIO_STOP = "audio-stop"

    # STT events
    TRANSCRIPT = "transcript"

    # TTS events
    SYNTHESIZE = "synthesize"

    # Service discovery
    INFO = "info"
    DESCRIBE = "describe"

    # Error handling
    ERROR = "error"

    # Voice activity
    VOICE_STARTED = "voice-started"
    VOICE_STOPPED = "voice-stopped"


@dataclass
class AudioFormat:
    """Audio format specification."""
    rate: int = 16000       # Sample rate in Hz
    width: int = 2          # Sample width in bytes (2 = 16-bit)
    channels: int = 1       # Number of audio channels

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioFormat":
        return cls(
            rate=data.get("rate", 16000),
            width=data.get("width", 2),
            channels=data.get("channels", 1),
        )


@dataclass
class AudioChunk:
    """Audio data chunk for streaming."""
    audio: bytes                           # Raw audio bytes
    rate: int = 16000                      # Sample rate
    width: int = 2                         # Sample width
    channels: int = 1                      # Channels
    timestamp: Optional[float] = None      # Optional timestamp in seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audio": base64.b64encode(self.audio).decode("ascii"),
            "rate": self.rate,
            "width": self.width,
            "channels": self.channels,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioChunk":
        return cls(
            audio=base64.b64decode(data["audio"]),
            rate=data.get("rate", 16000),
            width=data.get("width", 2),
            channels=data.get("channels", 1),
            timestamp=data.get("timestamp"),
        )


@dataclass
class AudioStart:
    """Signals the start of an audio stream."""
    rate: int = 16000
    width: int = 2
    channels: int = 1
    timestamp: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rate": self.rate,
            "width": self.width,
            "channels": self.channels,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioStart":
        return cls(
            rate=data.get("rate", 16000),
            width=data.get("width", 2),
            channels=data.get("channels", 1),
            timestamp=data.get("timestamp"),
        )


@dataclass
class AudioStop:
    """Signals the end of an audio stream."""
    timestamp: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioStop":
        return cls(timestamp=data.get("timestamp"))


@dataclass
class Transcript:
    """Speech-to-text transcription result."""
    text: str                              # Transcribed text
    confidence: float = 1.0                # Confidence score (0.0 - 1.0)
    is_final: bool = True                  # True if this is a final result
    language: Optional[str] = None         # Detected/used language code
    start_time: Optional[float] = None     # Start time in audio
    end_time: Optional[float] = None       # End time in audio

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "is_final": self.is_final,
            "language": self.language,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transcript":
        return cls(
            text=data["text"],
            confidence=data.get("confidence", 1.0),
            is_final=data.get("is_final", True),
            language=data.get("language"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
        )


@dataclass
class Synthesize:
    """Text-to-speech synthesis request."""
    text: str                              # Text to synthesize
    voice: Optional[str] = None            # Voice name/identifier
    rate: Optional[float] = None           # Speaking rate multiplier
    volume: Optional[float] = None         # Volume (0.0 - 1.0)
    language: Optional[str] = None         # Language code

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "voice": self.voice,
            "rate": self.rate,
            "volume": self.volume,
            "language": self.language,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Synthesize":
        return cls(
            text=data["text"],
            voice=data.get("voice"),
            rate=data.get("rate"),
            volume=data.get("volume"),
            language=data.get("language"),
        )


@dataclass
class AsrProgram:
    """ASR (Automatic Speech Recognition) program info."""
    name: str
    description: str = ""
    installed: bool = True
    attribution: Optional[str] = None
    version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TtsProgram:
    """TTS (Text-to-Speech) program info."""
    name: str
    description: str = ""
    installed: bool = True
    attribution: Optional[str] = None
    version: Optional[str] = None
    voices: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Info:
    """Service information response."""
    asr: Optional[List[AsrProgram]] = None
    tts: Optional[List[TtsProgram]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.asr:
            result["asr"] = [a.to_dict() for a in self.asr]
        if self.tts:
            result["tts"] = [t.to_dict() for t in self.tts]
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Info":
        asr = None
        tts = None
        if "asr" in data:
            asr = [AsrProgram(**a) for a in data["asr"]]
        if "tts" in data:
            tts = [TtsProgram(**t) for t in data["tts"]]
        return cls(asr=asr, tts=tts)


@dataclass
class Describe:
    """Request for service information."""
    pass

    def to_dict(self) -> Dict[str, Any]:
        return {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Describe":
        return cls()


@dataclass
class Error:
    """Error response."""
    text: str
    code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "code": self.code}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Error":
        return cls(text=data["text"], code=data.get("code"))


# Type alias for all payload types
PayloadType = Union[
    AudioChunk, AudioStart, AudioStop,
    Transcript, Synthesize,
    Info, Describe, Error,
    Dict[str, Any]
]


@dataclass
class WyomingMessage:
    """
    Wyoming protocol message container.

    Messages are JSON-encoded and newline-delimited for streaming over TCP.
    Each message has a type and an optional data payload.
    """
    type: MessageType
    data: Optional[PayloadType] = None

    def to_json(self) -> str:
        """Serialize message to JSON string."""
        payload: Dict[str, Any] = {"type": self.type.value}

        if self.data is not None:
            if hasattr(self.data, "to_dict"):
                payload["data"] = self.data.to_dict()
            elif isinstance(self.data, dict):
                payload["data"] = self.data
            else:
                payload["data"] = asdict(self.data)

        return json.dumps(payload)

    def to_bytes(self) -> bytes:
        """Serialize message to bytes with newline terminator."""
        return (self.to_json() + "\n").encode("utf-8")

    @classmethod
    def from_json(cls, json_str: str) -> "WyomingMessage":
        """Deserialize message from JSON string."""
        parsed = json.loads(json_str)
        msg_type = MessageType(parsed["type"])
        data = parsed.get("data", {})

        # Parse data based on message type
        payload: Optional[PayloadType] = None
        if data:
            if msg_type == MessageType.AUDIO_CHUNK:
                payload = AudioChunk.from_dict(data)
            elif msg_type == MessageType.AUDIO_START:
                payload = AudioStart.from_dict(data)
            elif msg_type == MessageType.AUDIO_STOP:
                payload = AudioStop.from_dict(data)
            elif msg_type == MessageType.TRANSCRIPT:
                payload = Transcript.from_dict(data)
            elif msg_type == MessageType.SYNTHESIZE:
                payload = Synthesize.from_dict(data)
            elif msg_type == MessageType.INFO:
                payload = Info.from_dict(data)
            elif msg_type == MessageType.DESCRIBE:
                payload = Describe.from_dict(data)
            elif msg_type == MessageType.ERROR:
                payload = Error.from_dict(data)
            else:
                payload = data

        return cls(type=msg_type, data=payload)

    @classmethod
    def from_bytes(cls, data: bytes) -> "WyomingMessage":
        """Deserialize message from bytes."""
        return cls.from_json(data.decode("utf-8").strip())

    # Factory methods for common message types
    @classmethod
    def audio_start(
        cls,
        rate: int = 16000,
        width: int = 2,
        channels: int = 1
    ) -> "WyomingMessage":
        """Create an audio-start message."""
        return cls(
            type=MessageType.AUDIO_START,
            data=AudioStart(rate=rate, width=width, channels=channels)
        )

    @classmethod
    def audio_chunk(
        cls,
        audio: bytes,
        rate: int = 16000,
        width: int = 2,
        channels: int = 1
    ) -> "WyomingMessage":
        """Create an audio-chunk message."""
        return cls(
            type=MessageType.AUDIO_CHUNK,
            data=AudioChunk(audio=audio, rate=rate, width=width, channels=channels)
        )

    @classmethod
    def audio_stop(cls) -> "WyomingMessage":
        """Create an audio-stop message."""
        return cls(type=MessageType.AUDIO_STOP, data=AudioStop())

    @classmethod
    def transcript(
        cls,
        text: str,
        confidence: float = 1.0,
        is_final: bool = True
    ) -> "WyomingMessage":
        """Create a transcript message."""
        return cls(
            type=MessageType.TRANSCRIPT,
            data=Transcript(text=text, confidence=confidence, is_final=is_final)
        )

    @classmethod
    def synthesize(cls, text: str, voice: Optional[str] = None) -> "WyomingMessage":
        """Create a synthesize request message."""
        return cls(
            type=MessageType.SYNTHESIZE,
            data=Synthesize(text=text, voice=voice)
        )

    @classmethod
    def describe(cls) -> "WyomingMessage":
        """Create a describe request message."""
        return cls(type=MessageType.DESCRIBE, data=Describe())

    @classmethod
    def info(
        cls,
        asr: Optional[List[AsrProgram]] = None,
        tts: Optional[List[TtsProgram]] = None
    ) -> "WyomingMessage":
        """Create an info response message."""
        return cls(type=MessageType.INFO, data=Info(asr=asr, tts=tts))

    @classmethod
    def error(cls, text: str, code: Optional[str] = None) -> "WyomingMessage":
        """Create an error message."""
        return cls(type=MessageType.ERROR, data=Error(text=text, code=code))


async def read_message(reader) -> Optional[WyomingMessage]:
    """
    Read a Wyoming message from an async stream reader.

    Args:
        reader: asyncio.StreamReader

    Returns:
        WyomingMessage or None if connection closed
    """
    try:
        line = await reader.readline()
        if not line:
            return None
        return WyomingMessage.from_bytes(line)
    except Exception:
        return None


async def write_message(writer, message: WyomingMessage):
    """
    Write a Wyoming message to an async stream writer.

    Args:
        writer: asyncio.StreamWriter
        message: WyomingMessage to send
    """
    writer.write(message.to_bytes())
    await writer.drain()
