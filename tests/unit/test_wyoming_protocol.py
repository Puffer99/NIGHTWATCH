"""
NIGHTWATCH Unit Tests - Wyoming Protocol Module

Tests for the Wyoming protocol implementation (Phase 1.2 of INTEGRATION_PLAN).
Validates message serialization, deserialization, factory methods, and roundtrip
encoding for voice service communication.

Run:
    pytest tests/unit/test_wyoming_protocol.py -v
"""

import json
import base64
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio

# Import Wyoming protocol components
from voice.wyoming.protocol import (
    MessageType,
    AudioFormat,
    AudioChunk,
    AudioStart,
    AudioStop,
    Transcript,
    Synthesize,
    Info,
    Describe,
    Error,
    AsrProgram,
    TtsProgram,
    WyomingMessage,
    read_message,
    write_message,
)


# ============================================================================
# MessageType Tests
# ============================================================================

class TestMessageType:
    """Tests for Wyoming MessageType enum."""

    def test_audio_types_exist(self):
        """Verify audio-related message types are defined."""
        assert MessageType.AUDIO_CHUNK.value == "audio-chunk"
        assert MessageType.AUDIO_START.value == "audio-start"
        assert MessageType.AUDIO_STOP.value == "audio-stop"

    def test_stt_types_exist(self):
        """Verify STT-related message types are defined."""
        assert MessageType.TRANSCRIPT.value == "transcript"

    def test_tts_types_exist(self):
        """Verify TTS-related message types are defined."""
        assert MessageType.SYNTHESIZE.value == "synthesize"

    def test_service_discovery_types_exist(self):
        """Verify service discovery message types are defined."""
        assert MessageType.INFO.value == "info"
        assert MessageType.DESCRIBE.value == "describe"

    def test_error_type_exists(self):
        """Verify error message type is defined."""
        assert MessageType.ERROR.value == "error"

    def test_voice_activity_types_exist(self):
        """Verify voice activity message types are defined."""
        assert MessageType.VOICE_STARTED.value == "voice-started"
        assert MessageType.VOICE_STOPPED.value == "voice-stopped"

    def test_message_type_from_string(self):
        """Test creating MessageType from string value."""
        assert MessageType("audio-chunk") == MessageType.AUDIO_CHUNK
        assert MessageType("transcript") == MessageType.TRANSCRIPT


# ============================================================================
# AudioFormat Tests
# ============================================================================

class TestAudioFormat:
    """Tests for AudioFormat dataclass."""

    def test_default_values(self):
        """Test AudioFormat has correct defaults."""
        fmt = AudioFormat()
        assert fmt.rate == 16000
        assert fmt.width == 2
        assert fmt.channels == 1

    def test_custom_values(self):
        """Test AudioFormat with custom values."""
        fmt = AudioFormat(rate=44100, width=4, channels=2)
        assert fmt.rate == 44100
        assert fmt.width == 4
        assert fmt.channels == 2

    def test_to_dict(self):
        """Test serialization to dictionary."""
        fmt = AudioFormat(rate=22050, width=2, channels=1)
        d = fmt.to_dict()
        assert d == {"rate": 22050, "width": 2, "channels": 1}

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        d = {"rate": 48000, "width": 4, "channels": 2}
        fmt = AudioFormat.from_dict(d)
        assert fmt.rate == 48000
        assert fmt.width == 4
        assert fmt.channels == 2

    def test_from_dict_with_defaults(self):
        """Test deserialization uses defaults for missing keys."""
        fmt = AudioFormat.from_dict({})
        assert fmt.rate == 16000
        assert fmt.width == 2
        assert fmt.channels == 1


# ============================================================================
# AudioChunk Tests
# ============================================================================

class TestAudioChunk:
    """Tests for AudioChunk dataclass with base64 encoding."""

    def test_basic_creation(self):
        """Test creating AudioChunk with audio data."""
        audio_data = b"\x00\x01\x02\x03\x04\x05"
        chunk = AudioChunk(audio=audio_data)
        assert chunk.audio == audio_data
        assert chunk.rate == 16000  # default

    def test_to_dict_base64_encodes_audio(self):
        """Test that audio bytes are base64 encoded in dict."""
        audio_data = b"Hello audio data"
        chunk = AudioChunk(audio=audio_data, rate=22050)
        d = chunk.to_dict()

        expected_b64 = base64.b64encode(audio_data).decode("ascii")
        assert d["audio"] == expected_b64
        assert d["rate"] == 22050

    def test_from_dict_base64_decodes_audio(self):
        """Test that base64 audio is decoded back to bytes."""
        audio_data = b"Test audio bytes"
        encoded = base64.b64encode(audio_data).decode("ascii")
        d = {"audio": encoded, "rate": 44100, "width": 2, "channels": 1}

        chunk = AudioChunk.from_dict(d)
        assert chunk.audio == audio_data
        assert chunk.rate == 44100

    def test_roundtrip_preserves_audio(self):
        """Test that to_dict -> from_dict preserves audio data."""
        original_audio = bytes(range(256))  # All byte values
        chunk1 = AudioChunk(audio=original_audio, rate=16000, width=2, channels=1)

        d = chunk1.to_dict()
        chunk2 = AudioChunk.from_dict(d)

        assert chunk2.audio == original_audio
        assert chunk2.rate == chunk1.rate

    def test_timestamp_optional(self):
        """Test timestamp is optional."""
        chunk = AudioChunk(audio=b"data")
        assert chunk.timestamp is None

        chunk_with_ts = AudioChunk(audio=b"data", timestamp=1.5)
        assert chunk_with_ts.timestamp == 1.5


# ============================================================================
# AudioStart Tests
# ============================================================================

class TestAudioStart:
    """Tests for AudioStart message."""

    def test_default_values(self):
        """Test AudioStart has correct defaults."""
        start = AudioStart()
        assert start.rate == 16000
        assert start.width == 2
        assert start.channels == 1
        assert start.timestamp is None

    def test_to_dict(self):
        """Test serialization to dictionary."""
        start = AudioStart(rate=48000, width=4, channels=2, timestamp=0.0)
        d = start.to_dict()
        assert d["rate"] == 48000
        assert d["width"] == 4
        assert d["channels"] == 2
        assert d["timestamp"] == 0.0

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        d = {"rate": 22050, "width": 2, "channels": 1, "timestamp": 1.23}
        start = AudioStart.from_dict(d)
        assert start.rate == 22050
        assert start.timestamp == 1.23


# ============================================================================
# AudioStop Tests
# ============================================================================

class TestAudioStop:
    """Tests for AudioStop message."""

    def test_default_values(self):
        """Test AudioStop with no timestamp."""
        stop = AudioStop()
        assert stop.timestamp is None

    def test_with_timestamp(self):
        """Test AudioStop with timestamp."""
        stop = AudioStop(timestamp=5.67)
        assert stop.timestamp == 5.67

    def test_to_dict(self):
        """Test serialization."""
        stop = AudioStop(timestamp=2.5)
        d = stop.to_dict()
        assert d == {"timestamp": 2.5}

    def test_from_dict(self):
        """Test deserialization."""
        stop = AudioStop.from_dict({"timestamp": 3.14})
        assert stop.timestamp == 3.14


# ============================================================================
# Transcript Tests
# ============================================================================

class TestTranscript:
    """Tests for Transcript message."""

    def test_basic_creation(self):
        """Test creating transcript with text."""
        t = Transcript(text="Hello world")
        assert t.text == "Hello world"
        assert t.confidence == 1.0  # default
        assert t.is_final is True  # default

    def test_full_creation(self):
        """Test transcript with all fields."""
        t = Transcript(
            text="Go to Mars",
            confidence=0.95,
            is_final=True,
            language="en",
            start_time=0.0,
            end_time=1.5,
        )
        assert t.text == "Go to Mars"
        assert t.confidence == 0.95
        assert t.language == "en"

    def test_to_dict(self):
        """Test serialization."""
        t = Transcript(text="Test", confidence=0.8, is_final=False)
        d = t.to_dict()
        assert d["text"] == "Test"
        assert d["confidence"] == 0.8
        assert d["is_final"] is False

    def test_from_dict(self):
        """Test deserialization."""
        d = {
            "text": "Park the telescope",
            "confidence": 0.92,
            "is_final": True,
            "language": "en",
        }
        t = Transcript.from_dict(d)
        assert t.text == "Park the telescope"
        assert t.confidence == 0.92
        assert t.language == "en"


# ============================================================================
# Synthesize Tests
# ============================================================================

class TestSynthesize:
    """Tests for Synthesize request message."""

    def test_basic_creation(self):
        """Test creating synthesize request with text."""
        s = Synthesize(text="Slewing to target")
        assert s.text == "Slewing to target"
        assert s.voice is None
        assert s.rate is None

    def test_full_creation(self):
        """Test synthesize with all options."""
        s = Synthesize(
            text="Weather alert",
            voice="en_US-amy-medium",
            rate=1.2,
            volume=0.8,
            language="en-US",
        )
        assert s.text == "Weather alert"
        assert s.voice == "en_US-amy-medium"
        assert s.rate == 1.2
        assert s.volume == 0.8

    def test_to_dict(self):
        """Test serialization."""
        s = Synthesize(text="Test", voice="default")
        d = s.to_dict()
        assert d["text"] == "Test"
        assert d["voice"] == "default"

    def test_from_dict(self):
        """Test deserialization."""
        d = {"text": "Tracking started", "rate": 1.5}
        s = Synthesize.from_dict(d)
        assert s.text == "Tracking started"
        assert s.rate == 1.5


# ============================================================================
# Error Tests
# ============================================================================

class TestError:
    """Tests for Error message."""

    def test_basic_creation(self):
        """Test creating error with text."""
        e = Error(text="Connection failed")
        assert e.text == "Connection failed"
        assert e.code is None

    def test_with_code(self):
        """Test error with code."""
        e = Error(text="Not found", code="404")
        assert e.text == "Not found"
        assert e.code == "404"

    def test_to_dict(self):
        """Test serialization."""
        e = Error(text="Timeout", code="TIMEOUT")
        d = e.to_dict()
        assert d["text"] == "Timeout"
        assert d["code"] == "TIMEOUT"

    def test_from_dict(self):
        """Test deserialization."""
        d = {"text": "Invalid request", "code": "400"}
        e = Error.from_dict(d)
        assert e.text == "Invalid request"
        assert e.code == "400"


# ============================================================================
# AsrProgram / TtsProgram Tests
# ============================================================================

class TestAsrProgram:
    """Tests for ASR program info."""

    def test_basic_creation(self):
        """Test creating ASR program info."""
        asr = AsrProgram(name="whisper", description="OpenAI Whisper")
        assert asr.name == "whisper"
        assert asr.installed is True

    def test_to_dict(self):
        """Test serialization."""
        asr = AsrProgram(
            name="faster-whisper",
            description="Fast Whisper implementation",
            version="0.10.0",
        )
        d = asr.to_dict()
        assert d["name"] == "faster-whisper"
        assert d["version"] == "0.10.0"


class TestTtsProgram:
    """Tests for TTS program info."""

    def test_basic_creation(self):
        """Test creating TTS program info."""
        tts = TtsProgram(name="piper", description="Neural TTS")
        assert tts.name == "piper"
        assert tts.voices == []

    def test_with_voices(self):
        """Test TTS with voice list."""
        voices = ["en_US-lessac", "en_GB-alba"]
        tts = TtsProgram(name="piper", description="", voices=voices)
        assert tts.voices == voices

    def test_to_dict(self):
        """Test serialization."""
        tts = TtsProgram(
            name="piper",
            description="Fast TTS",
            voices=["voice1", "voice2"],
        )
        d = tts.to_dict()
        assert d["name"] == "piper"
        assert d["voices"] == ["voice1", "voice2"]


# ============================================================================
# Info / Describe Tests
# ============================================================================

class TestInfo:
    """Tests for Info service response."""

    def test_empty_info(self):
        """Test Info with no programs."""
        info = Info()
        assert info.asr is None
        assert info.tts is None

    def test_with_asr(self):
        """Test Info with ASR programs."""
        asr_list = [AsrProgram(name="whisper", description="Test")]
        info = Info(asr=asr_list)
        assert len(info.asr) == 1

    def test_to_dict(self):
        """Test serialization."""
        asr = [AsrProgram(name="whisper", description="")]
        tts = [TtsProgram(name="piper", description="")]
        info = Info(asr=asr, tts=tts)
        d = info.to_dict()
        assert "asr" in d
        assert "tts" in d
        assert d["asr"][0]["name"] == "whisper"

    def test_from_dict(self):
        """Test deserialization."""
        d = {
            "asr": [{"name": "whisper", "description": "Test"}],
            "tts": [{"name": "piper", "description": "Test", "voices": []}],
        }
        info = Info.from_dict(d)
        assert len(info.asr) == 1
        assert len(info.tts) == 1


class TestDescribe:
    """Tests for Describe request."""

    def test_creation(self):
        """Test creating Describe message."""
        d = Describe()
        assert d is not None

    def test_to_dict(self):
        """Test serialization returns empty dict."""
        d = Describe()
        assert d.to_dict() == {}

    def test_from_dict(self):
        """Test deserialization."""
        d = Describe.from_dict({})
        assert isinstance(d, Describe)


# ============================================================================
# WyomingMessage Tests
# ============================================================================

class TestWyomingMessage:
    """Tests for WyomingMessage container class."""

    def test_basic_creation(self):
        """Test creating message with type and data."""
        msg = WyomingMessage(
            type=MessageType.TRANSCRIPT,
            data=Transcript(text="Hello"),
        )
        assert msg.type == MessageType.TRANSCRIPT
        assert isinstance(msg.data, Transcript)

    def test_to_json_format(self):
        """Test JSON serialization format."""
        msg = WyomingMessage(
            type=MessageType.TRANSCRIPT,
            data=Transcript(text="Test"),
        )
        json_str = msg.to_json()
        parsed = json.loads(json_str)

        assert parsed["type"] == "transcript"
        assert "data" in parsed
        assert parsed["data"]["text"] == "Test"

    def test_to_bytes_adds_newline(self):
        """Test that to_bytes adds newline terminator."""
        msg = WyomingMessage(type=MessageType.DESCRIBE, data=Describe())
        data = msg.to_bytes()
        assert data.endswith(b"\n")

    def test_from_json(self):
        """Test JSON deserialization."""
        json_str = '{"type": "transcript", "data": {"text": "Hello world", "confidence": 0.9}}'
        msg = WyomingMessage.from_json(json_str)

        assert msg.type == MessageType.TRANSCRIPT
        assert isinstance(msg.data, Transcript)
        assert msg.data.text == "Hello world"
        assert msg.data.confidence == 0.9

    def test_from_bytes(self):
        """Test bytes deserialization."""
        json_str = '{"type": "error", "data": {"text": "Failed"}}\n'
        msg = WyomingMessage.from_bytes(json_str.encode())

        assert msg.type == MessageType.ERROR
        assert isinstance(msg.data, Error)
        assert msg.data.text == "Failed"

    def test_roundtrip_audio_chunk(self):
        """Test roundtrip for audio chunk with binary data."""
        audio = bytes(range(256))
        original = WyomingMessage.audio_chunk(audio, rate=16000)

        json_str = original.to_json()
        restored = WyomingMessage.from_json(json_str)

        assert restored.type == MessageType.AUDIO_CHUNK
        assert isinstance(restored.data, AudioChunk)
        assert restored.data.audio == audio

    def test_roundtrip_transcript(self):
        """Test roundtrip for transcript message."""
        original = WyomingMessage.transcript("Go to M31", confidence=0.95)

        json_str = original.to_json()
        restored = WyomingMessage.from_json(json_str)

        assert restored.type == MessageType.TRANSCRIPT
        assert restored.data.text == "Go to M31"
        assert restored.data.confidence == 0.95


# ============================================================================
# WyomingMessage Factory Methods Tests
# ============================================================================

class TestWyomingMessageFactories:
    """Tests for WyomingMessage factory methods."""

    def test_audio_start_factory(self):
        """Test audio_start factory method."""
        msg = WyomingMessage.audio_start(rate=44100, width=2, channels=1)
        assert msg.type == MessageType.AUDIO_START
        assert isinstance(msg.data, AudioStart)
        assert msg.data.rate == 44100

    def test_audio_chunk_factory(self):
        """Test audio_chunk factory method."""
        audio = b"\x00\x01\x02\x03"
        msg = WyomingMessage.audio_chunk(audio, rate=16000, width=2, channels=1)
        assert msg.type == MessageType.AUDIO_CHUNK
        assert isinstance(msg.data, AudioChunk)
        assert msg.data.audio == audio

    def test_audio_stop_factory(self):
        """Test audio_stop factory method."""
        msg = WyomingMessage.audio_stop()
        assert msg.type == MessageType.AUDIO_STOP
        assert isinstance(msg.data, AudioStop)

    def test_transcript_factory(self):
        """Test transcript factory method."""
        msg = WyomingMessage.transcript("Test text", confidence=0.9, is_final=True)
        assert msg.type == MessageType.TRANSCRIPT
        assert isinstance(msg.data, Transcript)
        assert msg.data.text == "Test text"
        assert msg.data.confidence == 0.9

    def test_synthesize_factory(self):
        """Test synthesize factory method."""
        msg = WyomingMessage.synthesize("Hello world", voice="en_US-lessac")
        assert msg.type == MessageType.SYNTHESIZE
        assert isinstance(msg.data, Synthesize)
        assert msg.data.text == "Hello world"
        assert msg.data.voice == "en_US-lessac"

    def test_describe_factory(self):
        """Test describe factory method."""
        msg = WyomingMessage.describe()
        assert msg.type == MessageType.DESCRIBE
        assert isinstance(msg.data, Describe)

    def test_info_factory(self):
        """Test info factory method."""
        asr = [AsrProgram(name="whisper", description="")]
        msg = WyomingMessage.info(asr=asr)
        assert msg.type == MessageType.INFO
        assert isinstance(msg.data, Info)
        assert len(msg.data.asr) == 1

    def test_error_factory(self):
        """Test error factory method."""
        msg = WyomingMessage.error("Something went wrong", code="500")
        assert msg.type == MessageType.ERROR
        assert isinstance(msg.data, Error)
        assert msg.data.text == "Something went wrong"
        assert msg.data.code == "500"


# ============================================================================
# Message Parsing Tests - All Types
# ============================================================================

class TestMessageParsing:
    """Tests for parsing all message types from JSON."""

    def test_parse_audio_start(self):
        """Test parsing audio-start message."""
        json_str = '{"type": "audio-start", "data": {"rate": 22050, "width": 2, "channels": 1}}'
        msg = WyomingMessage.from_json(json_str)
        assert msg.type == MessageType.AUDIO_START
        assert msg.data.rate == 22050

    def test_parse_audio_stop(self):
        """Test parsing audio-stop message."""
        json_str = '{"type": "audio-stop", "data": {"timestamp": 5.0}}'
        msg = WyomingMessage.from_json(json_str)
        assert msg.type == MessageType.AUDIO_STOP
        assert msg.data.timestamp == 5.0

    def test_parse_synthesize(self):
        """Test parsing synthesize message."""
        json_str = '{"type": "synthesize", "data": {"text": "Hello", "voice": "default"}}'
        msg = WyomingMessage.from_json(json_str)
        assert msg.type == MessageType.SYNTHESIZE
        assert msg.data.text == "Hello"

    def test_parse_info(self):
        """Test parsing info message."""
        json_str = '{"type": "info", "data": {"asr": [{"name": "whisper", "description": ""}]}}'
        msg = WyomingMessage.from_json(json_str)
        assert msg.type == MessageType.INFO
        assert len(msg.data.asr) == 1

    def test_parse_describe(self):
        """Test parsing describe message."""
        json_str = '{"type": "describe", "data": {}}'
        msg = WyomingMessage.from_json(json_str)
        assert msg.type == MessageType.DESCRIBE

    def test_parse_voice_activity(self):
        """Test parsing voice activity messages."""
        # Voice started
        msg1 = WyomingMessage.from_json('{"type": "voice-started", "data": {}}')
        assert msg1.type == MessageType.VOICE_STARTED

        # Voice stopped
        msg2 = WyomingMessage.from_json('{"type": "voice-stopped", "data": {}}')
        assert msg2.type == MessageType.VOICE_STOPPED


# ============================================================================
# Async I/O Tests
# ============================================================================

class TestAsyncIO:
    """Tests for async read/write functions."""

    @pytest.mark.asyncio
    async def test_read_message(self):
        """Test reading message from async stream."""
        # Create mock reader
        json_data = '{"type": "transcript", "data": {"text": "Hello"}}\n'
        reader = AsyncMock()
        reader.readline = AsyncMock(return_value=json_data.encode())

        msg = await read_message(reader)
        assert msg is not None
        assert msg.type == MessageType.TRANSCRIPT
        assert msg.data.text == "Hello"

    @pytest.mark.asyncio
    async def test_read_message_empty(self):
        """Test read_message returns None for empty data."""
        reader = AsyncMock()
        reader.readline = AsyncMock(return_value=b"")

        msg = await read_message(reader)
        assert msg is None

    @pytest.mark.asyncio
    async def test_read_message_exception(self):
        """Test read_message handles exceptions gracefully."""
        reader = AsyncMock()
        reader.readline = AsyncMock(side_effect=Exception("Connection error"))

        msg = await read_message(reader)
        assert msg is None

    @pytest.mark.asyncio
    async def test_write_message(self):
        """Test writing message to async stream."""
        writer = AsyncMock()
        writer.drain = AsyncMock()

        msg = WyomingMessage.transcript("Test")
        await write_message(writer, msg)

        # Verify write was called with bytes ending in newline
        writer.write.assert_called_once()
        written_data = writer.write.call_args[0][0]
        assert written_data.endswith(b"\n")
        assert b"transcript" in written_data


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_audio_chunk(self):
        """Test AudioChunk with empty audio."""
        chunk = AudioChunk(audio=b"")
        d = chunk.to_dict()
        restored = AudioChunk.from_dict(d)
        assert restored.audio == b""

    def test_large_audio_chunk(self):
        """Test AudioChunk with large audio data."""
        # Simulate 1 second of 16kHz 16-bit audio
        large_audio = bytes(16000 * 2)  # 32KB
        chunk = AudioChunk(audio=large_audio)
        d = chunk.to_dict()
        restored = AudioChunk.from_dict(d)
        assert restored.audio == large_audio

    def test_unicode_text(self):
        """Test messages with unicode text."""
        text = "Slewing to Alpha Centauri \u2728 \u2b50"
        t = Transcript(text=text)
        d = t.to_dict()
        restored = Transcript.from_dict(d)
        assert restored.text == text

    def test_special_characters_in_text(self):
        """Test messages with special characters."""
        text = 'Command: "park" executed with error code <500>'
        e = Error(text=text)
        d = e.to_dict()
        restored = Error.from_dict(d)
        assert restored.text == text

    def test_message_without_data(self):
        """Test message with no data payload."""
        msg = WyomingMessage(type=MessageType.DESCRIBE, data=None)
        json_str = msg.to_json()
        parsed = json.loads(json_str)
        assert "data" not in parsed or parsed.get("data") is None

    def test_nested_json_in_message(self):
        """Test that complex nested data is handled."""
        # Info with multiple ASR and TTS programs
        asr = [
            AsrProgram(name="whisper", description="OpenAI Whisper", version="1.0"),
            AsrProgram(name="vosk", description="Vosk STT", version="0.3"),
        ]
        tts = [
            TtsProgram(name="piper", description="Neural TTS", voices=["v1", "v2"]),
        ]
        msg = WyomingMessage.info(asr=asr, tts=tts)

        json_str = msg.to_json()
        restored = WyomingMessage.from_json(json_str)

        assert len(restored.data.asr) == 2
        assert len(restored.data.tts) == 1
        assert restored.data.tts[0].voices == ["v1", "v2"]


# ============================================================================
# Integration-like Tests
# ============================================================================

class TestProtocolWorkflow:
    """Tests simulating real protocol workflows."""

    def test_stt_workflow_messages(self):
        """Test typical STT workflow message sequence."""
        # Client sends: audio-start, audio-chunk(s), audio-stop
        # Server responds: transcript

        # 1. Audio start
        start_msg = WyomingMessage.audio_start(rate=16000, width=2, channels=1)
        assert start_msg.type == MessageType.AUDIO_START

        # 2. Audio chunks
        chunk1 = WyomingMessage.audio_chunk(b"\x00" * 1000, rate=16000)
        chunk2 = WyomingMessage.audio_chunk(b"\x01" * 1000, rate=16000)
        assert chunk1.type == MessageType.AUDIO_CHUNK

        # 3. Audio stop
        stop_msg = WyomingMessage.audio_stop()
        assert stop_msg.type == MessageType.AUDIO_STOP

        # 4. Server response
        response = WyomingMessage.transcript("Go to Mars", confidence=0.95)
        assert response.type == MessageType.TRANSCRIPT

    def test_tts_workflow_messages(self):
        """Test typical TTS workflow message sequence."""
        # Client sends: synthesize
        # Server responds: audio-start, audio-chunk(s), audio-stop

        # 1. Synthesize request
        request = WyomingMessage.synthesize("Tracking started", voice="en_US-lessac")
        assert request.type == MessageType.SYNTHESIZE

        # 2. Server sends audio back
        audio_start = WyomingMessage.audio_start(rate=22050, width=2, channels=1)
        assert audio_start.data.rate == 22050

        # 3. Audio chunks
        audio_data = b"\x00" * 4096
        chunk = WyomingMessage.audio_chunk(audio_data, rate=22050)
        assert len(chunk.data.audio) == 4096

        # 4. Audio stop
        stop = WyomingMessage.audio_stop()
        assert stop.type == MessageType.AUDIO_STOP

    def test_service_discovery_workflow(self):
        """Test service discovery workflow."""
        # Client sends describe
        describe = WyomingMessage.describe()
        assert describe.type == MessageType.DESCRIBE

        # Server responds with info
        asr = [AsrProgram(
            name="nightwatch-whisper",
            description="NIGHTWATCH Whisper STT",
            installed=True,
            version="0.10.0",
        )]
        info = WyomingMessage.info(asr=asr)

        assert info.type == MessageType.INFO
        assert info.data.asr[0].name == "nightwatch-whisper"


# ============================================================================
# Run Configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
