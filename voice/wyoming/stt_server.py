"""
NIGHTWATCH Wyoming STT Server

Exposes the WhisperSTT service via the Wyoming protocol over TCP,
enabling decoupled speech-to-text services that can run on different
machines and integrate with the Home Assistant ecosystem.

Usage:
    server = WyomingSTTServer(whisper_stt, port=10300)
    await server.start()
"""

import asyncio
import logging
import numpy as np
from typing import Optional, List, Callable
from dataclasses import dataclass

from .protocol import (
    MessageType,
    WyomingMessage,
    AudioChunk,
    AudioStart,
    AudioStop,
    Transcript,
    Info,
    AsrProgram,
    read_message,
    write_message,
)

# Import WhisperSTT - handle case where it might not be available
try:
    from ..stt.whisper_service import WhisperSTT, WHISPER_BACKEND
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False
    WHISPER_BACKEND = None

logger = logging.getLogger(__name__)


@dataclass
class ClientSession:
    """State for a connected client session."""
    audio_buffer: List[bytes]
    audio_format: Optional[AudioStart]
    is_streaming: bool

    def __init__(self):
        self.audio_buffer = []
        self.audio_format = None
        self.is_streaming = False

    def reset(self):
        """Reset session state for new audio stream."""
        self.audio_buffer = []
        self.is_streaming = False


class WyomingSTTServer:
    """
    Wyoming protocol server for NIGHTWATCH speech-to-text.

    Exposes WhisperSTT via Wyoming protocol over TCP, allowing:
    - Remote STT clients to stream audio and receive transcripts
    - Integration with Home Assistant voice assistants
    - Service discovery via the Wyoming info endpoint
    """

    DEFAULT_PORT = 10300

    def __init__(
        self,
        stt: Optional["WhisperSTT"] = None,
        host: str = "0.0.0.0",
        port: int = DEFAULT_PORT,
    ):
        """
        Initialize Wyoming STT server.

        Args:
            stt: WhisperSTT instance (will create default if None)
            host: Host to bind to
            port: Port to listen on
        """
        self.stt = stt
        self.host = host
        self.port = port
        self._server = None
        self._running = False
        self._clients: List[asyncio.Task] = []
        self._on_transcript_callbacks: List[Callable[[str], None]] = []

    def _ensure_stt(self):
        """Ensure STT service is available."""
        if not STT_AVAILABLE:
            raise RuntimeError(
                "WhisperSTT not available. "
                "Install with: pip install faster-whisper"
            )
        if self.stt is None:
            from ..stt.whisper_service import WhisperSTT, WhisperModelSize
            logger.info("Creating default WhisperSTT instance")
            self.stt = WhisperSTT(model_size=WhisperModelSize.BASE)
            self.stt.initialize()

    def register_transcript_callback(self, callback: Callable[[str], None]):
        """Register callback for received transcripts."""
        self._on_transcript_callbacks.append(callback)

    async def handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ):
        """
        Handle a connected Wyoming client.

        Processes incoming Wyoming messages, accumulates audio chunks,
        and returns transcripts when audio stream completes.

        Args:
            reader: Stream reader for client connection
            writer: Stream writer for client connection
        """
        client_addr = writer.get_extra_info("peername")
        logger.info(f"Client connected: {client_addr}")

        session = ClientSession()

        try:
            while True:
                message = await read_message(reader)
                if message is None:
                    logger.debug(f"Client disconnected: {client_addr}")
                    break

                response = await self._handle_message(message, session)
                if response:
                    await write_message(writer, response)

        except asyncio.CancelledError:
            logger.debug(f"Client handler cancelled: {client_addr}")
        except Exception as e:
            logger.error(f"Error handling client {client_addr}: {e}")
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
        session: ClientSession
    ) -> Optional[WyomingMessage]:
        """
        Process a Wyoming message and return response if needed.

        Args:
            message: Incoming Wyoming message
            session: Client session state

        Returns:
            Response message or None
        """
        if message.type == MessageType.DESCRIBE:
            # Return service info
            return self._get_info_response()

        elif message.type == MessageType.AUDIO_START:
            # Start new audio stream
            session.reset()
            session.audio_format = message.data
            session.is_streaming = True
            logger.debug(f"Audio stream started: {session.audio_format}")
            return None

        elif message.type == MessageType.AUDIO_CHUNK:
            # Accumulate audio data
            if session.is_streaming and isinstance(message.data, AudioChunk):
                session.audio_buffer.append(message.data.audio)
            return None

        elif message.type == MessageType.AUDIO_STOP:
            # Process accumulated audio and return transcript
            if session.audio_buffer:
                transcript = await self._transcribe_buffer(session)
                session.reset()
                return transcript
            session.reset()
            return WyomingMessage.transcript("", confidence=0.0)

        elif message.type == MessageType.VOICE_STARTED:
            logger.debug("Voice activity started")
            return None

        elif message.type == MessageType.VOICE_STOPPED:
            logger.debug("Voice activity stopped")
            return None

        else:
            logger.warning(f"Unhandled message type: {message.type}")
            return None

    async def _transcribe_buffer(
        self,
        session: ClientSession
    ) -> WyomingMessage:
        """
        Transcribe accumulated audio buffer.

        Args:
            session: Client session with audio buffer

        Returns:
            Transcript message
        """
        self._ensure_stt()

        # Concatenate audio chunks
        audio_bytes = b"".join(session.audio_buffer)

        # Get audio format, default to 16kHz mono 16-bit
        rate = 16000
        width = 2
        if session.audio_format:
            rate = session.audio_format.rate
            width = session.audio_format.width

        # Convert bytes to numpy array
        if width == 2:
            # 16-bit signed integer
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
            audio = audio_int16.astype(np.float32) / 32768.0
        elif width == 4:
            # 32-bit float
            audio = np.frombuffer(audio_bytes, dtype=np.float32)
        else:
            # Assume 16-bit
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
            audio = audio_int16.astype(np.float32) / 32768.0

        # Resample if needed (Whisper expects 16kHz)
        if rate != 16000:
            # Simple resampling using linear interpolation
            factor = 16000 / rate
            new_length = int(len(audio) * factor)
            indices = np.linspace(0, len(audio) - 1, new_length)
            audio = np.interp(indices, np.arange(len(audio)), audio)

        logger.debug(f"Transcribing {len(audio)} samples")

        # Run transcription in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.stt.transcribe, audio)

        logger.info(f"Transcript: {result.text}")

        # Notify callbacks
        for callback in self._on_transcript_callbacks:
            try:
                callback(result.text)
            except Exception as e:
                logger.error(f"Transcript callback error: {e}")

        return WyomingMessage.transcript(
            text=result.text,
            confidence=result.confidence,
            is_final=True,
        )

    def _get_info_response(self) -> WyomingMessage:
        """Get service information response."""
        asr_programs = [
            AsrProgram(
                name="nightwatch-whisper",
                description="NIGHTWATCH Whisper STT for telescope voice control",
                installed=STT_AVAILABLE,
                attribution="OpenAI Whisper via faster-whisper",
                version=WHISPER_BACKEND or "unknown",
            )
        ]
        return WyomingMessage.info(asr=asr_programs)

    async def start(self):
        """Start the Wyoming STT server."""
        self._ensure_stt()

        self._server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port,
        )

        self._running = True
        addr = self._server.sockets[0].getsockname()
        logger.info(f"Wyoming STT server listening on {addr}")

        async with self._server:
            await self._server.serve_forever()

    async def start_background(self):
        """Start server in background task."""
        self._ensure_stt()

        self._server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port,
        )

        self._running = True
        addr = self._server.sockets[0].getsockname()
        logger.info(f"Wyoming STT server listening on {addr}")

        # Start serving in background
        asyncio.create_task(self._server.serve_forever())

    def stop(self):
        """Stop the Wyoming STT server."""
        self._running = False
        if self._server:
            self._server.close()

        # Cancel client handlers
        for task in self._clients:
            task.cancel()
        self._clients.clear()

        logger.info("Wyoming STT server stopped")


# =============================================================================
# Standalone server runner
# =============================================================================

async def run_server(
    model_size: str = "base",
    device: str = "cuda",
    host: str = "0.0.0.0",
    port: int = 10300,
):
    """
    Run Wyoming STT server as standalone service.

    Args:
        model_size: Whisper model size (tiny, base, small, medium, large-v3)
        device: Device to run inference on (cuda, cpu)
        host: Host to bind to
        port: Port to listen on
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    if not STT_AVAILABLE:
        logger.error("WhisperSTT not available. Install faster-whisper first.")
        return

    from ..stt.whisper_service import WhisperSTT, WhisperModelSize

    # Map model size string to enum
    size_map = {
        "tiny": WhisperModelSize.TINY,
        "base": WhisperModelSize.BASE,
        "small": WhisperModelSize.SMALL,
        "medium": WhisperModelSize.MEDIUM,
        "large-v3": WhisperModelSize.LARGE,
    }
    model_enum = size_map.get(model_size, WhisperModelSize.BASE)

    logger.info(f"Initializing Whisper STT ({model_size} on {device})...")
    stt = WhisperSTT(
        model_size=model_enum,
        device=device,
        compute_type="int8_float16" if device == "cuda" else "int8",
    )
    stt.initialize()

    server = WyomingSTTServer(stt, host=host, port=port)

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.stop()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NIGHTWATCH Wyoming STT Server")
    parser.add_argument("--model", default="base", help="Whisper model size")
    parser.add_argument("--device", default="cuda", help="Device (cuda/cpu)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=10300, help="Port to listen on")

    args = parser.parse_args()

    asyncio.run(run_server(
        model_size=args.model,
        device=args.device,
        host=args.host,
        port=args.port,
    ))
