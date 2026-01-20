"""
Integration tests for Wyoming Protocol (Step 329).

Tests end-to-end Wyoming protocol communication between client and server,
including message serialization, streaming, and error handling.
"""

import asyncio
import pytest
import struct
from unittest.mock import Mock, AsyncMock, patch, MagicMock

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


class MockStreamReader:
    """Mock asyncio StreamReader for testing."""

    def __init__(self, messages: list):
        """
        Initialize with list of messages to return.

        Args:
            messages: List of WyomingMessage objects to return
        """
        self._messages = list(messages)
        self._index = 0
        self._buffer = b""
        self._prepare_buffer()

    def _prepare_buffer(self):
        """Prepare buffer with serialized messages."""
        for msg in self._messages:
            # Serialize message
            json_str = msg.to_json()
            json_bytes = json_str.encode("utf-8")
            # Length prefix (4 bytes, big-endian)
            length_bytes = struct.pack(">I", len(json_bytes))
            self._buffer += length_bytes + json_bytes

    async def read(self, n: int) -> bytes:
        """Read n bytes from buffer."""
        if not self._buffer:
            return b""
        result = self._buffer[:n]
        self._buffer = self._buffer[n:]
        return result

    async def readexactly(self, n: int) -> bytes:
        """Read exactly n bytes from buffer."""
        if len(self._buffer) < n:
            raise asyncio.IncompleteReadError(self._buffer, n)
        result = self._buffer[:n]
        self._buffer = self._buffer[n:]
        return result


class MockStreamWriter:
    """Mock asyncio StreamWriter for testing."""

    def __init__(self):
        self.data = b""
        self.closed = False

    def write(self, data: bytes):
        """Write data to buffer."""
        self.data += data

    async def drain(self):
        """Simulate drain."""
        pass

    def close(self):
        """Close the writer."""
        self.closed = True

    async def wait_closed(self):
        """Wait for close."""
        pass

    def get_messages(self) -> list:
        """Parse written messages from buffer."""
        messages = []
        buf = self.data
        while len(buf) >= 4:
            length = struct.unpack(">I", buf[:4])[0]
            if len(buf) < 4 + length:
                break
            json_bytes = buf[4:4 + length]
            msg = WyomingMessage.from_json(json_bytes.decode("utf-8"))
            messages.append(msg)
            buf = buf[4 + length:]
        return messages


class TestWyomingMessageRoundtrip:
    """Test message serialization roundtrip through stream."""

    @pytest.mark.asyncio
    async def test_audio_start_roundtrip(self):
        """Test AudioStart message roundtrip."""
        original = AudioStart(
            rate=16000,
            width=2,
            channels=1
        )
        msg = WyomingMessage.from_payload(original)

        # Write to mock writer
        writer = MockStreamWriter()
        await write_message(writer, msg)

        # Read from mock reader with written data
        reader = MockStreamReader([msg])
        reader._buffer = writer.data
        result = await read_message(reader)

        assert result is not None
        assert result.type == MessageType.AUDIO_START
        assert result.payload.rate == 16000
        assert result.payload.width == 2
        assert result.payload.channels == 1

    @pytest.mark.asyncio
    async def test_audio_chunk_roundtrip(self):
        """Test AudioChunk message roundtrip."""
        audio_data = bytes([0] * 1600)  # 100ms of 16kHz mono 16-bit
        original = AudioChunk(
            audio=audio_data,
            rate=16000,
            width=2,
            channels=1
        )
        msg = WyomingMessage.from_payload(original)

        writer = MockStreamWriter()
        await write_message(writer, msg)

        reader = MockStreamReader([msg])
        reader._buffer = writer.data
        result = await read_message(reader)

        assert result is not None
        assert result.type == MessageType.AUDIO_CHUNK
        assert len(result.payload.audio) == 1600

    @pytest.mark.asyncio
    async def test_transcript_roundtrip(self):
        """Test Transcript message roundtrip."""
        original = Transcript(text="slew to Andromeda")
        msg = WyomingMessage.from_payload(original)

        writer = MockStreamWriter()
        await write_message(writer, msg)

        reader = MockStreamReader([msg])
        reader._buffer = writer.data
        result = await read_message(reader)

        assert result is not None
        assert result.type == MessageType.TRANSCRIPT
        assert result.payload.text == "slew to Andromeda"

    @pytest.mark.asyncio
    async def test_synthesize_roundtrip(self):
        """Test Synthesize message roundtrip."""
        original = Synthesize(text="Slewing to Andromeda Galaxy")
        msg = WyomingMessage.from_payload(original)

        writer = MockStreamWriter()
        await write_message(writer, msg)

        reader = MockStreamReader([msg])
        reader._buffer = writer.data
        result = await read_message(reader)

        assert result is not None
        assert result.type == MessageType.SYNTHESIZE
        assert result.payload.text == "Slewing to Andromeda Galaxy"

    @pytest.mark.asyncio
    async def test_error_roundtrip(self):
        """Test Error message roundtrip."""
        original = Error(
            code="STT_ERROR",
            text="Failed to transcribe audio"
        )
        msg = WyomingMessage.from_payload(original)

        writer = MockStreamWriter()
        await write_message(writer, msg)

        reader = MockStreamReader([msg])
        reader._buffer = writer.data
        result = await read_message(reader)

        assert result is not None
        assert result.type == MessageType.ERROR
        assert result.payload.code == "STT_ERROR"
        assert result.payload.text == "Failed to transcribe audio"


class TestWyomingStreamingSession:
    """Test complete Wyoming streaming session."""

    @pytest.mark.asyncio
    async def test_stt_session_flow(self):
        """Test complete STT session: start -> chunks -> stop -> transcript."""
        # Prepare message sequence
        messages = [
            WyomingMessage.from_payload(AudioStart(rate=16000, width=2, channels=1)),
            WyomingMessage.from_payload(AudioChunk(audio=bytes(1600), rate=16000, width=2, channels=1)),
            WyomingMessage.from_payload(AudioChunk(audio=bytes(1600), rate=16000, width=2, channels=1)),
            WyomingMessage.from_payload(AudioStop()),
        ]

        reader = MockStreamReader(messages)
        writer = MockStreamWriter()

        # Simulate reading the session
        audio_buffer = []
        session_active = False

        for _ in range(4):
            msg = await read_message(reader)
            if msg is None:
                break

            if msg.type == MessageType.AUDIO_START:
                session_active = True
                audio_buffer = []
            elif msg.type == MessageType.AUDIO_CHUNK and session_active:
                audio_buffer.append(msg.payload.audio)
            elif msg.type == MessageType.AUDIO_STOP:
                session_active = False
                # Send transcript response
                response = WyomingMessage.from_payload(
                    Transcript(text="park the telescope")
                )
                await write_message(writer, response)

        # Verify response was written
        responses = writer.get_messages()
        assert len(responses) == 1
        assert responses[0].type == MessageType.TRANSCRIPT
        assert responses[0].payload.text == "park the telescope"

    @pytest.mark.asyncio
    async def test_tts_session_flow(self):
        """Test complete TTS session: synthesize -> audio chunks -> stop."""
        # Receive synthesize request
        synthesize_msg = WyomingMessage.from_payload(
            Synthesize(text="Observatory ready for observation")
        )
        reader = MockStreamReader([synthesize_msg])
        writer = MockStreamWriter()

        msg = await read_message(reader)
        assert msg.type == MessageType.SYNTHESIZE

        # Simulate TTS response
        await write_message(writer, WyomingMessage.from_payload(
            AudioStart(rate=22050, width=2, channels=1)
        ))

        # Send audio chunks
        for _ in range(5):
            await write_message(writer, WyomingMessage.from_payload(
                AudioChunk(audio=bytes(4410), rate=22050, width=2, channels=1)
            ))

        await write_message(writer, WyomingMessage.from_payload(AudioStop()))

        # Verify responses
        responses = writer.get_messages()
        assert len(responses) == 7  # 1 start + 5 chunks + 1 stop
        assert responses[0].type == MessageType.AUDIO_START
        assert responses[-1].type == MessageType.AUDIO_STOP


class TestWyomingServiceDiscovery:
    """Test Wyoming service discovery protocol."""

    @pytest.mark.asyncio
    async def test_describe_asr_response(self):
        """Test ASR service description."""
        describe_msg = WyomingMessage.from_payload(Describe())
        reader = MockStreamReader([describe_msg])
        writer = MockStreamWriter()

        msg = await read_message(reader)
        assert msg.type == MessageType.DESCRIBE

        # Respond with service info
        info = Info(
            asr=[AsrProgram(
                name="nightwatch-stt",
                description="NIGHTWATCH Speech-to-Text Service",
                attribution="faster-whisper",
                installed=True,
                version="0.1.0",
                languages=["en", "de", "es", "fr"],
            )]
        )
        await write_message(writer, WyomingMessage.from_payload(info))

        responses = writer.get_messages()
        assert len(responses) == 1
        assert responses[0].type == MessageType.INFO
        assert len(responses[0].payload.asr) == 1
        assert responses[0].payload.asr[0].name == "nightwatch-stt"

    @pytest.mark.asyncio
    async def test_describe_tts_response(self):
        """Test TTS service description."""
        describe_msg = WyomingMessage.from_payload(Describe())
        reader = MockStreamReader([describe_msg])
        writer = MockStreamWriter()

        msg = await read_message(reader)
        assert msg.type == MessageType.DESCRIBE

        # Respond with TTS info
        info = Info(
            tts=[TtsProgram(
                name="nightwatch-tts",
                description="NIGHTWATCH Text-to-Speech Service",
                attribution="piper",
                installed=True,
                version="0.1.0",
                voices=["amy", "lessac"],
            )]
        )
        await write_message(writer, WyomingMessage.from_payload(info))

        responses = writer.get_messages()
        assert len(responses) == 1
        assert responses[0].type == MessageType.INFO
        assert len(responses[0].payload.tts) == 1
        assert responses[0].payload.tts[0].name == "nightwatch-tts"


class TestWyomingErrorHandling:
    """Test Wyoming error handling."""

    @pytest.mark.asyncio
    async def test_empty_audio_error(self):
        """Test error response for empty audio."""
        messages = [
            WyomingMessage.from_payload(AudioStart(rate=16000, width=2, channels=1)),
            WyomingMessage.from_payload(AudioStop()),  # No audio chunks
        ]
        reader = MockStreamReader(messages)
        writer = MockStreamWriter()

        # Read messages
        await read_message(reader)  # AudioStart
        await read_message(reader)  # AudioStop

        # Send error response
        error = Error(code="EMPTY_AUDIO", text="No audio data received")
        await write_message(writer, WyomingMessage.from_payload(error))

        responses = writer.get_messages()
        assert len(responses) == 1
        assert responses[0].type == MessageType.ERROR
        assert responses[0].payload.code == "EMPTY_AUDIO"

    @pytest.mark.asyncio
    async def test_incomplete_read_handling(self):
        """Test handling of incomplete reads."""
        reader = MockStreamReader([])  # Empty reader

        with pytest.raises(asyncio.IncompleteReadError):
            await read_message(reader)


class TestWyomingAudioFormats:
    """Test various audio format configurations."""

    @pytest.mark.parametrize("rate,width,channels", [
        (16000, 2, 1),   # Standard Whisper input
        (22050, 2, 1),   # Piper output
        (44100, 2, 2),   # CD quality stereo
        (48000, 2, 1),   # Professional audio
    ])
    @pytest.mark.asyncio
    async def test_audio_format_configurations(self, rate, width, channels):
        """Test various audio format configurations."""
        original = AudioStart(rate=rate, width=width, channels=channels)
        msg = WyomingMessage.from_payload(original)

        writer = MockStreamWriter()
        await write_message(writer, msg)

        reader = MockStreamReader([msg])
        reader._buffer = writer.data
        result = await read_message(reader)

        assert result.payload.rate == rate
        assert result.payload.width == width
        assert result.payload.channels == channels
