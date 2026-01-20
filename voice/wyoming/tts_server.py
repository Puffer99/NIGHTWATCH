"""
NIGHTWATCH Wyoming TTS Server

Exposes the Piper TTS service via the Wyoming protocol over TCP,
enabling decoupled text-to-speech services that can run on different
machines and integrate with the Home Assistant ecosystem.

Usage:
    server = WyomingTTSServer(piper_tts, port=10301)
    await server.start()
"""

import asyncio
import logging
from typing import Optional, List, Callable
from dataclasses import dataclass

from .protocol import (
    MessageType,
    WyomingMessage,
    AudioChunk,
    AudioStart,
    AudioStop,
    Synthesize,
    Info,
    TtsProgram,
    read_message,
    write_message,
)

# Import PiperTTS - handle case where it might not be available
try:
    from ..tts.piper_service import PiperTTS, PIPER_AVAILABLE
    TTS_AVAILABLE = PIPER_AVAILABLE
except ImportError:
    TTS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class TTSSettings:
    """TTS synthesis settings."""
    voice: Optional[str] = None
    rate: float = 1.0
    volume: float = 1.0
    language: str = "en"


# Step 319: Multi-language support preparation
# Language codes supported by NIGHTWATCH voice system
SUPPORTED_LANGUAGES = {
    "en": {"name": "English", "voice_prefix": "en_US", "tts_available": True},
    "de": {"name": "German", "voice_prefix": "de_DE", "tts_available": True},
    "es": {"name": "Spanish", "voice_prefix": "es_ES", "tts_available": True},
    "fr": {"name": "French", "voice_prefix": "fr_FR", "tts_available": True},
    "it": {"name": "Italian", "voice_prefix": "it_IT", "tts_available": True},
    "nl": {"name": "Dutch", "voice_prefix": "nl_NL", "tts_available": True},
    "pt": {"name": "Portuguese", "voice_prefix": "pt_BR", "tts_available": True},
    "pl": {"name": "Polish", "voice_prefix": "pl_PL", "tts_available": True},
    "uk": {"name": "Ukrainian", "voice_prefix": "uk_UA", "tts_available": True},
    "ru": {"name": "Russian", "voice_prefix": "ru_RU", "tts_available": True},
}


def get_language_voice(language: str, default_voice: str = "en_US-lessac-medium") -> str:
    """
    Get appropriate TTS voice for language (Step 319).

    Args:
        language: Language code (e.g., "en", "de")
        default_voice: Fallback voice if language not supported

    Returns:
        Voice name appropriate for the language
    """
    lang_info = SUPPORTED_LANGUAGES.get(language)
    if lang_info and lang_info.get("tts_available"):
        # Return a default voice for that language prefix
        # Actual voice selection would be more sophisticated
        prefix = lang_info["voice_prefix"]
        return f"{prefix}-medium"  # Placeholder voice pattern
    return default_voice


def is_language_supported(language: str) -> bool:
    """Check if language is supported (Step 319)."""
    return language in SUPPORTED_LANGUAGES


# Step 323: Urgency keywords for dynamic speech rate adjustment
URGENCY_KEYWORDS = {
    "high": [
        "emergency", "warning", "danger", "critical", "abort", "stop",
        "immediately", "urgent", "unsafe", "fail", "error", "alert"
    ],
    "low": [
        "observing", "viewing", "looking at", "current altitude",
        "magnitude", "constellation", "info", "status"
    ]
}


def detect_urgency(text: str) -> str:
    """
    Detect urgency level from text content (Step 323).

    Args:
        text: Text to analyze

    Returns:
        Urgency level: "high", "normal", or "low"
    """
    text_lower = text.lower()

    # Check for high urgency keywords
    for keyword in URGENCY_KEYWORDS["high"]:
        if keyword in text_lower:
            return "high"

    # Check for low urgency keywords (calm, informational)
    for keyword in URGENCY_KEYWORDS["low"]:
        if keyword in text_lower:
            return "low"

    return "normal"


def get_urgency_rate(urgency: str) -> float:
    """
    Get speech rate multiplier for urgency level (Step 323).

    Args:
        urgency: Urgency level

    Returns:
        Rate multiplier (1.0 = normal, >1.0 = faster, <1.0 = slower)
    """
    rates = {
        "high": 1.25,    # Faster for urgent alerts
        "normal": 1.0,   # Normal speed
        "low": 0.9,      # Slightly slower for calm observation info
    }
    return rates.get(urgency, 1.0)


class WyomingTTSServer:
    """
    Wyoming protocol server for NIGHTWATCH text-to-speech.

    Exposes PiperTTS via Wyoming protocol over TCP, allowing:
    - Remote TTS clients to request speech synthesis
    - Streaming audio back to clients in chunks
    - Integration with Home Assistant voice assistants
    - Service discovery via the Wyoming info endpoint
    """

    DEFAULT_PORT = 10301
    CHUNK_SIZE = 4096  # Bytes per audio chunk

    def __init__(
        self,
        tts: Optional["PiperTTS"] = None,
        host: str = "0.0.0.0",
        port: int = DEFAULT_PORT,
        stream_audio: bool = True,
    ):
        """
        Initialize Wyoming TTS server.

        Args:
            tts: PiperTTS instance (will create default if None)
            host: Host to bind to
            port: Port to listen on
            stream_audio: If True, stream audio in chunks; otherwise send all at once
        """
        self.tts = tts
        self.host = host
        self.port = port
        self.stream_audio = stream_audio
        self._server = None
        self._running = False
        self._clients: List[asyncio.Task] = []
        self._available_voices: List[str] = []

    def _ensure_tts(self):
        """Ensure TTS service is available."""
        if not TTS_AVAILABLE:
            raise RuntimeError(
                "PiperTTS not available. "
                "Install with: pip install piper-tts"
            )
        if self.tts is None:
            from ..tts.piper_service import PiperTTS
            logger.info("Creating default PiperTTS instance")
            self.tts = PiperTTS()
            self.tts.initialize()

    async def handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ):
        """
        Handle a connected Wyoming client.

        Processes incoming Wyoming messages and returns synthesized audio.

        Args:
            reader: Stream reader for client connection
            writer: Stream writer for client connection
        """
        client_addr = writer.get_extra_info("peername")
        logger.info(f"TTS client connected: {client_addr}")

        settings = TTSSettings()

        try:
            while True:
                message = await read_message(reader)
                if message is None:
                    logger.debug(f"TTS client disconnected: {client_addr}")
                    break

                responses = await self._handle_message(message, settings)
                for response in responses:
                    await write_message(writer, response)

        except asyncio.CancelledError:
            logger.debug(f"TTS client handler cancelled: {client_addr}")
        except Exception as e:
            logger.error(f"Error handling TTS client {client_addr}: {e}")
            error_response = WyomingMessage.error(str(e))
            try:
                await write_message(writer, error_response)
            except Exception:
                pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _handle_message(
        self,
        message: WyomingMessage,
        settings: TTSSettings
    ) -> List[WyomingMessage]:
        """
        Process a Wyoming message and return responses.

        Args:
            message: Incoming Wyoming message
            settings: Current TTS settings

        Returns:
            List of response messages
        """
        if message.type == MessageType.DESCRIBE:
            # Return service info
            return [self._get_info_response()]

        elif message.type == MessageType.SYNTHESIZE:
            # Synthesize speech and return audio
            if isinstance(message.data, Synthesize):
                return await self._synthesize(message.data, settings)
            return [WyomingMessage.error("Invalid synthesize request")]

        else:
            logger.warning(f"Unhandled TTS message type: {message.type}")
            return []

    async def _synthesize(
        self,
        request: Synthesize,
        settings: TTSSettings
    ) -> List[WyomingMessage]:
        """
        Synthesize speech from text request.

        Args:
            request: Synthesize request with text
            settings: TTS settings

        Returns:
            List of messages: audio-start, audio-chunk(s), audio-stop
        """
        self._ensure_tts()

        text = request.text
        if not text:
            return [WyomingMessage.error("Empty text")]

        logger.info(f"Synthesizing: {text[:50]}...")

        # Apply request parameters if provided
        if request.voice:
            settings.voice = request.voice
        if request.rate:
            settings.rate = request.rate

        # Step 323: Apply dynamic speech rate based on urgency
        urgency = detect_urgency(text)
        urgency_rate = get_urgency_rate(urgency)
        effective_rate = settings.rate * urgency_rate

        if urgency != "normal":
            logger.debug(f"Urgency detected: {urgency}, rate adjusted to {effective_rate:.2f}")

        # Apply rate to TTS if supported
        if hasattr(self.tts, 'set_rate'):
            self.tts.set_rate(effective_rate)
        elif hasattr(self.tts, 'config') and hasattr(self.tts.config, 'speed'):
            self.tts.config.speed = effective_rate

        # Run synthesis in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(
            None,
            self.tts.synthesize,
            text
        )

        if not output:
            return [WyomingMessage.error("Synthesis failed")]

        messages = []

        # Get sample rate from TTS output
        sample_rate = output.sample_rate

        # Send audio-start
        messages.append(WyomingMessage.audio_start(
            rate=sample_rate,
            width=2,  # 16-bit audio
            channels=1,  # Mono
        ))

        # Send audio data in chunks
        audio_bytes = output.audio
        if self.stream_audio:
            # Stream in chunks
            for i in range(0, len(audio_bytes), self.CHUNK_SIZE):
                chunk = audio_bytes[i:i + self.CHUNK_SIZE]
                messages.append(WyomingMessage.audio_chunk(
                    audio=chunk,
                    rate=sample_rate,
                    width=2,
                    channels=1,
                ))
        else:
            # Send all at once
            messages.append(WyomingMessage.audio_chunk(
                audio=audio_bytes,
                rate=sample_rate,
                width=2,
                channels=1,
            ))

        # Send audio-stop
        messages.append(WyomingMessage.audio_stop())

        logger.debug(f"Sent {len(messages)} messages for synthesis")
        return messages

    def _get_info_response(self) -> WyomingMessage:
        """Get service information response."""
        # List available voices
        voices = []
        if self.tts and hasattr(self.tts, 'VOICE_MODELS'):
            voices = list(self.tts.VOICE_MODELS.keys())
        elif TTS_AVAILABLE:
            voices = ["en_US-lessac-medium"]  # Default voice

        tts_programs = [
            TtsProgram(
                name="nightwatch-piper",
                description="NIGHTWATCH Piper TTS for telescope voice responses",
                installed=TTS_AVAILABLE,
                attribution="Piper by Rhasspy",
                version="1.0.0",
                voices=voices,
            )
        ]
        return WyomingMessage.info(tts=tts_programs)

    async def start(self):
        """Start the Wyoming TTS server."""
        self._ensure_tts()

        self._server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port,
        )

        self._running = True
        addr = self._server.sockets[0].getsockname()
        logger.info(f"Wyoming TTS server listening on {addr}")

        async with self._server:
            await self._server.serve_forever()

    async def start_background(self):
        """Start server in background task."""
        self._ensure_tts()

        self._server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port,
        )

        self._running = True
        addr = self._server.sockets[0].getsockname()
        logger.info(f"Wyoming TTS server listening on {addr}")

        # Start serving in background
        asyncio.create_task(self._server.serve_forever())

    def stop(self):
        """Stop the Wyoming TTS server."""
        self._running = False
        if self._server:
            self._server.close()

        # Cancel client handlers
        for task in self._clients:
            task.cancel()
        self._clients.clear()

        logger.info("Wyoming TTS server stopped")


# =============================================================================
# Wyoming TTS Client for remote synthesis
# =============================================================================

class WyomingTTSClient:
    """
    Wyoming protocol client for remote text-to-speech.

    Connects to a Wyoming TTS server and requests speech synthesis.
    Useful for distributed setups where TTS runs on a different machine.
    """

    def __init__(self, host: str = "localhost", port: int = 10301):
        """
        Initialize Wyoming TTS client.

        Args:
            host: Server host
            port: Server port
        """
        self.host = host
        self.port = port
        self._reader = None
        self._writer = None

    async def connect(self) -> bool:
        """Connect to Wyoming TTS server."""
        try:
            self._reader, self._writer = await asyncio.open_connection(
                self.host, self.port
            )
            logger.info(f"Connected to Wyoming TTS server at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to TTS server: {e}")
            return False

    async def disconnect(self):
        """Disconnect from server."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        self._reader = None
        self._writer = None

    async def synthesize(self, text: str, voice: Optional[str] = None) -> Optional[bytes]:
        """
        Request speech synthesis and receive audio.

        Args:
            text: Text to synthesize
            voice: Optional voice name

        Returns:
            Audio bytes (16-bit PCM) or None on failure
        """
        if not self._writer:
            if not await self.connect():
                return None

        # Send synthesize request
        request = WyomingMessage.synthesize(text, voice)
        await write_message(self._writer, request)

        # Receive audio response
        audio_chunks = []
        sample_rate = 22050  # Default

        while True:
            message = await read_message(self._reader)
            if message is None:
                break

            if message.type == MessageType.AUDIO_START:
                if isinstance(message.data, AudioStart):
                    sample_rate = message.data.rate

            elif message.type == MessageType.AUDIO_CHUNK:
                if isinstance(message.data, AudioChunk):
                    audio_chunks.append(message.data.audio)

            elif message.type == MessageType.AUDIO_STOP:
                break

            elif message.type == MessageType.ERROR:
                logger.error(f"TTS error: {message.data}")
                return None

        if not audio_chunks:
            return None

        return b"".join(audio_chunks)

    async def get_info(self) -> Optional[Info]:
        """Get server info including available voices."""
        if not self._writer:
            if not await self.connect():
                return None

        await write_message(self._writer, WyomingMessage.describe())
        message = await read_message(self._reader)

        if message and message.type == MessageType.INFO:
            return message.data
        return None


# =============================================================================
# Standalone server runner
# =============================================================================

async def run_server(
    voice: str = "en_US-lessac-medium",
    use_cuda: bool = False,
    host: str = "0.0.0.0",
    port: int = 10301,
    model_path: Optional[str] = None,
):
    """
    Run Wyoming TTS server as standalone service.

    Args:
        voice: Piper voice name
        use_cuda: Enable GPU acceleration
        host: Host to bind to
        port: Port to listen on
        model_path: Optional path to voice model file
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    if not TTS_AVAILABLE:
        logger.error("PiperTTS not available. Install piper-tts first.")
        return

    from ..tts.piper_service import PiperTTS, TTSConfig

    logger.info(f"Initializing Piper TTS ({voice}, CUDA={use_cuda})...")

    config = TTSConfig(voice=voice)
    tts = PiperTTS(config=config, use_cuda=use_cuda)

    if model_path:
        tts.initialize(model_path=model_path)
    else:
        tts.initialize()

    server = WyomingTTSServer(tts, host=host, port=port)

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.stop()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NIGHTWATCH Wyoming TTS Server")
    parser.add_argument("--voice", default="en_US-lessac-medium", help="Voice name")
    parser.add_argument("--cuda", action="store_true", help="Enable CUDA")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=10301, help="Port to listen on")
    parser.add_argument("--model", help="Path to voice model file")

    args = parser.parse_args()

    asyncio.run(run_server(
        voice=args.voice,
        use_cuda=args.cuda,
        host=args.host,
        port=args.port,
        model_path=args.model,
    ))
