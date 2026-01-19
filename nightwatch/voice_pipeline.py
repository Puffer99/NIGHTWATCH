"""
NIGHTWATCH Voice Pipeline
End-to-end voice command processing for telescope control.

Integrates Speech-to-Text (STT), Language Model (LLM), Tool Execution,
and Text-to-Speech (TTS) into a unified voice interface.

Pipeline Flow:
    Audio Input -> STT -> LLM (tool selection) -> Tool Executor ->
    Response Formatter -> TTS -> Audio Output

Usage:
    from nightwatch.voice_pipeline import VoicePipeline

    pipeline = VoicePipeline(orchestrator, llm_client)
    await pipeline.start()

    # Process voice command
    response = await pipeline.process_audio(audio_data)

    # Or process text directly
    response = await pipeline.process_text("Point to M31")
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger("NIGHTWATCH.VoicePipeline")


__all__ = [
    "VoicePipeline",
    "PipelineState",
    "PipelineResult",
    "VoicePipelineConfig",
]


# =============================================================================
# Enums and Data Classes
# =============================================================================


class PipelineState(Enum):
    """Voice pipeline states."""
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    PROCESSING = "processing"
    EXECUTING = "executing"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass
class PipelineResult:
    """Result from processing a voice command."""
    # Input
    transcript: str = ""

    # LLM response
    llm_response: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)

    # Tool execution
    tool_results: List[Dict[str, Any]] = field(default_factory=list)

    # Output
    spoken_response: str = ""
    audio_output: Optional[bytes] = None

    # Timing
    stt_latency_ms: float = 0.0
    llm_latency_ms: float = 0.0
    tool_latency_ms: float = 0.0
    tts_latency_ms: float = 0.0
    total_latency_ms: float = 0.0

    # Status
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def had_tool_calls(self) -> bool:
        """Check if any tools were called."""
        return len(self.tool_calls) > 0


@dataclass
class VoicePipelineConfig:
    """Configuration for voice pipeline."""
    # STT settings
    stt_model: str = "base"
    stt_device: str = "cuda"
    stt_compute_type: str = "float16"

    # TTS settings
    tts_model: str = "en_US-lessac-medium"
    tts_use_cuda: bool = True

    # Pipeline settings
    max_audio_length_sec: float = 30.0
    silence_threshold_sec: float = 1.5
    enable_vad: bool = True

    # Feedback
    play_acknowledgment: bool = True
    acknowledgment_sound: Optional[str] = None


# =============================================================================
# STT Interface
# =============================================================================


class STTInterface:
    """
    Speech-to-Text interface.

    Wraps faster-whisper for local transcription.
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cuda",
        compute_type: str = "float16",
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None
        self._loaded = False

    async def _ensure_loaded(self):
        """Lazily load the STT model."""
        if self._loaded:
            return

        try:
            from faster_whisper import WhisperModel

            logger.info(f"Loading STT model: {self.model_size}")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            self._loaded = True
            logger.info("STT model loaded")
        except ImportError:
            logger.warning("faster-whisper not installed, using mock STT")
            self._model = None
            self._loaded = True

    async def transcribe(self, audio_data: bytes) -> str:
        """
        Transcribe audio to text (Step 299).

        Args:
            audio_data: Raw audio bytes (16kHz, 16-bit, mono)

        Returns:
            Transcribed text
        """
        await self._ensure_loaded()

        if self._model is None:
            # Mock transcription for testing
            logger.warning("Using mock transcription")
            return "mock transcription"

        try:
            import numpy as np
            import io

            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

            # Transcribe
            segments, info = self._model.transcribe(
                audio_array,
                beam_size=5,
                language="en",
                vad_filter=True,
            )

            # Combine segments
            transcript = " ".join([segment.text for segment in segments])
            return transcript.strip()

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise


# =============================================================================
# TTS Interface
# =============================================================================


class TTSInterface:
    """
    Text-to-Speech interface.

    Wraps Piper TTS for local synthesis.
    """

    def __init__(
        self,
        model: str = "en_US-lessac-medium",
        use_cuda: bool = True,
    ):
        self.model = model
        self.use_cuda = use_cuda
        self._synthesizer = None
        self._loaded = False

    async def _ensure_loaded(self):
        """Lazily load the TTS model."""
        if self._loaded:
            return

        try:
            # Piper TTS loading would go here
            # For now, we'll use a mock
            logger.info(f"Loading TTS model: {self.model}")
            self._synthesizer = None  # Would be piper.PiperVoice
            self._loaded = True
            logger.info("TTS model loaded (mock)")
        except ImportError:
            logger.warning("piper-tts not installed, using mock TTS")
            self._synthesizer = None
            self._loaded = True

    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize speech from text (Step 304).

        Args:
            text: Text to synthesize

        Returns:
            Audio bytes (WAV format)
        """
        await self._ensure_loaded()

        if self._synthesizer is None:
            # Return mock audio for testing
            logger.warning("Using mock TTS synthesis")
            return self._generate_mock_audio(text)

        try:
            # Would use piper to synthesize
            # audio = self._synthesizer.synthesize(text)
            # return audio
            return self._generate_mock_audio(text)

        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            raise

    def _generate_mock_audio(self, text: str) -> bytes:
        """Generate mock audio data for testing."""
        import struct

        # Generate a simple WAV header + silence
        sample_rate = 22050
        duration_sec = len(text) * 0.05  # ~50ms per character
        num_samples = int(sample_rate * duration_sec)

        # WAV header
        header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',
            36 + num_samples * 2,
            b'WAVE',
            b'fmt ',
            16,  # PCM
            1,   # Audio format
            1,   # Channels
            sample_rate,
            sample_rate * 2,
            2,   # Block align
            16,  # Bits per sample
            b'data',
            num_samples * 2,
        )

        # Silent audio data
        audio_data = b'\x00' * (num_samples * 2)

        return header + audio_data


# =============================================================================
# Voice Pipeline (Steps 293-294)
# =============================================================================


class VoicePipeline:
    """
    End-to-end voice command pipeline.

    Coordinates STT, LLM, Tool Execution, and TTS for
    voice-controlled telescope operation.
    """

    def __init__(
        self,
        orchestrator,
        llm_client,
        tool_executor=None,
        response_formatter=None,
        config: Optional[VoicePipelineConfig] = None,
    ):
        """
        Initialize voice pipeline.

        Args:
            orchestrator: NIGHTWATCH orchestrator instance
            llm_client: LLM client for command processing
            tool_executor: Tool executor (uses orchestrator's if None)
            response_formatter: Response formatter (creates default if None)
            config: Pipeline configuration
        """
        self.orchestrator = orchestrator
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.response_formatter = response_formatter
        self.config = config or VoicePipelineConfig()

        # State
        self._state = PipelineState.IDLE
        self._running = False
        self._callbacks: List[Callable] = []

        # Components (lazy loaded)
        self._stt: Optional[STTInterface] = None
        self._tts: Optional[TTSInterface] = None

        # Metrics
        self._commands_processed = 0
        self._total_latency_ms = 0.0

        logger.info("Voice pipeline initialized")

    @property
    def state(self) -> PipelineState:
        """Get current pipeline state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if pipeline is running."""
        return self._running

    def _get_stt(self) -> STTInterface:
        """Get or create STT interface."""
        if self._stt is None:
            self._stt = STTInterface(
                model_size=self.config.stt_model,
                device=self.config.stt_device,
                compute_type=self.config.stt_compute_type,
            )
        return self._stt

    def _get_tts(self) -> TTSInterface:
        """Get or create TTS interface."""
        if self._tts is None:
            self._tts = TTSInterface(
                model=self.config.tts_model,
                use_cuda=self.config.tts_use_cuda,
            )
        return self._tts

    async def start(self):
        """Start the voice pipeline."""
        if self._running:
            logger.warning("Pipeline already running")
            return

        logger.info("Starting voice pipeline...")
        self._running = True
        self._state = PipelineState.IDLE
        logger.info("Voice pipeline started")

    async def stop(self):
        """Stop the voice pipeline."""
        if not self._running:
            return

        logger.info("Stopping voice pipeline...")
        self._running = False
        self._state = PipelineState.IDLE
        logger.info("Voice pipeline stopped")

    async def process_audio(self, audio_data: bytes) -> PipelineResult:
        """
        Process audio input through the full pipeline.

        Args:
            audio_data: Raw audio bytes

        Returns:
            Pipeline result with transcript, response, and audio
        """
        result = PipelineResult()
        start_time = time.time()

        try:
            # Step 1: Transcribe audio (Step 299)
            self._state = PipelineState.TRANSCRIBING
            stt_start = time.time()

            stt = self._get_stt()
            transcript = await stt.transcribe(audio_data)

            result.transcript = transcript
            result.stt_latency_ms = (time.time() - stt_start) * 1000

            if not transcript:
                result.spoken_response = "I didn't catch that. Could you repeat?"
                return result

            logger.info(f"Transcribed: {transcript}")

            # Step 2-4: Process the text command
            text_result = await self.process_text(transcript)

            # Copy text processing results
            result.llm_response = text_result.llm_response
            result.tool_calls = text_result.tool_calls
            result.tool_results = text_result.tool_results
            result.spoken_response = text_result.spoken_response
            result.llm_latency_ms = text_result.llm_latency_ms
            result.tool_latency_ms = text_result.tool_latency_ms

            # Step 5: Synthesize response audio (Step 304)
            self._state = PipelineState.SPEAKING
            tts_start = time.time()

            tts = self._get_tts()
            result.audio_output = await tts.synthesize(result.spoken_response)

            result.tts_latency_ms = (time.time() - tts_start) * 1000

            # Calculate total
            result.total_latency_ms = (time.time() - start_time) * 1000
            result.success = True

            # Update metrics
            self._commands_processed += 1
            self._total_latency_ms += result.total_latency_ms

            logger.info(f"Pipeline complete in {result.total_latency_ms:.0f}ms")

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            result.success = False
            result.error = str(e)
            result.spoken_response = "Sorry, an error occurred processing your command."
            self._state = PipelineState.ERROR

        finally:
            self._state = PipelineState.IDLE

        return result

    async def process_text(self, text: str) -> PipelineResult:
        """
        Process text command through LLM and tool execution.

        Args:
            text: Command text

        Returns:
            Pipeline result (no audio)
        """
        result = PipelineResult(transcript=text)
        start_time = time.time()

        try:
            # Step 2: Get LLM response with tools
            self._state = PipelineState.PROCESSING
            llm_start = time.time()

            # Get available tools from telescope_tools if available
            tools = self._get_tools()

            llm_response = await self.llm_client.chat(
                message=text,
                tools=tools,
            )

            result.llm_response = llm_response.content
            result.llm_latency_ms = (time.time() - llm_start) * 1000

            # Extract tool calls
            if llm_response.has_tool_calls:
                result.tool_calls = [
                    {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                    for tc in llm_response.tool_calls
                ]

            # Step 3: Execute tools (Step 302)
            if result.tool_calls:
                self._state = PipelineState.EXECUTING
                tool_start = time.time()

                for tool_call in result.tool_calls:
                    tool_result = await self._execute_tool(
                        tool_call["name"],
                        tool_call["arguments"],
                    )
                    result.tool_results.append(tool_result)

                    # Add tool result to LLM conversation
                    self.llm_client.add_tool_result(
                        tool_call["id"],
                        tool_call["name"],
                        str(tool_result.get("message", "")),
                    )

                result.tool_latency_ms = (time.time() - tool_start) * 1000

            # Step 4: Format response (Step 303)
            result.spoken_response = self._format_response(result)

            result.success = True

        except Exception as e:
            logger.error(f"Text processing error: {e}")
            result.success = False
            result.error = str(e)
            result.spoken_response = "Sorry, I couldn't process that command."

        return result

    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool via the orchestrator (Step 302).

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        logger.info(f"Executing tool: {tool_name} with args: {arguments}")

        # Use tool_executor if available
        if self.tool_executor:
            result = await self.tool_executor.execute(tool_name, arguments)
            return result.to_dict() if hasattr(result, 'to_dict') else {"message": str(result)}

        # Fall back to direct orchestrator method calls
        # This is a simplified version - real implementation would have full tool mapping
        try:
            if tool_name == "goto_object" and self.orchestrator.mount:
                obj_name = arguments.get("object_name", "")
                # Would resolve coordinates and slew
                return {
                    "status": "success",
                    "message": f"Slewing to {obj_name}",
                    "data": {"object": obj_name},
                }
            elif tool_name == "park_telescope" and self.orchestrator.mount:
                await self.orchestrator.mount.park()
                return {
                    "status": "success",
                    "message": "Telescope parked",
                }
            elif tool_name == "get_weather" and self.orchestrator.weather:
                conditions = self.orchestrator.weather.current_conditions
                return {
                    "status": "success",
                    "message": "Weather retrieved",
                    "data": conditions,
                }
            else:
                return {
                    "status": "not_found",
                    "message": f"Unknown tool: {tool_name}",
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
            }

    def _format_response(self, result: PipelineResult) -> str:
        """
        Format the response for speech output (Step 303).

        Args:
            result: Pipeline result with tool results

        Returns:
            Natural language response
        """
        # Use response formatter if available
        if self.response_formatter and result.tool_results:
            try:
                # Format the first tool result
                formatted = self.response_formatter.format(result.tool_results[0])
                if formatted:
                    return formatted
            except Exception as e:
                logger.warning(f"Formatter error: {e}")

        # Build response from tool results
        if result.tool_results:
            messages = []
            for tr in result.tool_results:
                msg = tr.get("message", "")
                if msg:
                    messages.append(msg)
            if messages:
                return " ".join(messages)

        # Fall back to LLM response
        if result.llm_response:
            return result.llm_response

        return "Command processed."

    def _get_tools(self) -> Optional[List[Dict[str, Any]]]:
        """Get tool definitions for LLM."""
        try:
            from nightwatch.telescope_tools import get_tool_definitions
            return get_tool_definitions()
        except ImportError:
            logger.warning("telescope_tools not available")
            return None

    def register_callback(self, callback: Callable[[PipelineState], None]):
        """Register callback for state changes."""
        self._callbacks.append(callback)

    def get_metrics(self) -> Dict[str, Any]:
        """Get pipeline metrics."""
        avg_latency = 0.0
        if self._commands_processed > 0:
            avg_latency = self._total_latency_ms / self._commands_processed

        return {
            "commands_processed": self._commands_processed,
            "total_latency_ms": self._total_latency_ms,
            "avg_latency_ms": avg_latency,
            "state": self._state.value,
        }


# =============================================================================
# Factory Function
# =============================================================================


def create_voice_pipeline(
    orchestrator,
    llm_client,
    **kwargs,
) -> VoicePipeline:
    """
    Create a voice pipeline instance.

    Args:
        orchestrator: NIGHTWATCH orchestrator
        llm_client: LLM client for command processing
        **kwargs: Additional configuration

    Returns:
        Configured VoicePipeline instance
    """
    config = VoicePipelineConfig(**{
        k: v for k, v in kwargs.items()
        if hasattr(VoicePipelineConfig, k)
    })

    return VoicePipeline(
        orchestrator=orchestrator,
        llm_client=llm_client,
        config=config,
    )
