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
    "STTInterface",
    "TTSInterface",
    "AudioPlayer",
    "AudioCapture",
    "LEDIndicator",
    "create_voice_pipeline",
    "normalize_transcript",
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

    # Step 295: Audio capture settings
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    vad_aggressiveness: int = 2  # 0-3, higher = more aggressive
    vad_frame_ms: int = 30  # Frame duration in ms

    # Step 297: Continuous listening settings
    continuous_mode: bool = False
    wake_word: Optional[str] = None  # Optional wake word to trigger

    # Step 307: Concurrent request settings
    max_concurrent_requests: int = 3
    request_timeout_sec: float = 30.0

    # Step 310: LED indicator settings
    led_enabled: bool = False
    led_gpio_pin: int = 18  # Default GPIO pin for LED


# =============================================================================
# Transcription Normalization (Step 300)
# =============================================================================


# Common astronomy word mappings for speech recognition
ASTRONOMY_NORMALIZATIONS = {
    # Messier objects
    "m 31": "M31",
    "m31": "M31",
    "messier 31": "M31",
    "m 42": "M42",
    "m42": "M42",
    "messier 42": "M42",
    "m 1": "M1",
    "m1": "M1",
    "messier 1": "M1",
    # NGC objects
    "ngc 7000": "NGC 7000",
    "n g c 7000": "NGC 7000",
    # Stars
    "polaris": "Polaris",
    "vega": "Vega",
    "sirius": "Sirius",
    "betelgeuse": "Betelgeuse",
    "beetle juice": "Betelgeuse",
    # Constellations
    "orion": "Orion",
    "andromeda": "Andromeda",
    "cassiopeia": "Cassiopeia",
    # Planets
    "jupiter": "Jupiter",
    "saturn": "Saturn",
    "mars": "Mars",
    "venus": "Venus",
    "mercury": "Mercury",
    "uranus": "Uranus",
    "neptune": "Neptune",
    # Commands
    "slew to": "slew to",
    "go to": "goto",
    "point to": "point to",
    "park": "park",
    "unpark": "unpark",
    "stop": "stop",
}


# =============================================================================
# Audio Feedback Sounds (Step 309)
# =============================================================================


class AudioFeedback:
    """
    Generate audio feedback sounds for pipeline state changes.

    Provides simple beeps and tones to indicate:
    - Listening started (low beep)
    - Command received (higher beep)
    - Processing complete (two-tone)
    - Error (descending tone)
    """

    # Audio parameters
    SAMPLE_RATE = 22050
    DURATION_MS = 150

    @staticmethod
    def _generate_tone(frequency: float, duration_ms: int, volume: float = 0.5) -> bytes:
        """Generate a pure sine wave tone as WAV bytes."""
        import struct
        import math

        sample_rate = AudioFeedback.SAMPLE_RATE
        num_samples = int(sample_rate * duration_ms / 1000)

        # Generate sine wave samples
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            sample = int(32767 * volume * math.sin(2 * math.pi * frequency * t))
            samples.append(sample)

        # Apply fade in/out to avoid clicks
        fade_samples = min(100, num_samples // 4)
        for i in range(fade_samples):
            factor = i / fade_samples
            samples[i] = int(samples[i] * factor)
            samples[-(i + 1)] = int(samples[-(i + 1)] * factor)

        # Pack as WAV
        header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',
            36 + num_samples * 2,
            b'WAVE',
            b'fmt ',
            16,
            1,  # PCM
            1,  # Mono
            sample_rate,
            sample_rate * 2,
            2,
            16,
            b'data',
            num_samples * 2,
        )
        audio_data = struct.pack(f'<{num_samples}h', *samples)
        return header + audio_data

    @classmethod
    def listening_started(cls) -> bytes:
        """Generate listening started beep (low pitch)."""
        return cls._generate_tone(440, 100, 0.3)  # A4

    @classmethod
    def command_received(cls) -> bytes:
        """Generate command received beep (higher pitch)."""
        return cls._generate_tone(880, 100, 0.3)  # A5

    @classmethod
    def processing_complete(cls) -> bytes:
        """Generate processing complete sound (two-tone ascending)."""
        tone1 = cls._generate_tone(523, 80, 0.3)  # C5
        tone2 = cls._generate_tone(659, 80, 0.3)  # E5
        # Combine tones (simple concatenation)
        return tone1 + tone2[44:]  # Skip header of second tone

    @classmethod
    def error_sound(cls) -> bytes:
        """Generate error sound (descending tone)."""
        tone1 = cls._generate_tone(440, 100, 0.4)  # A4
        tone2 = cls._generate_tone(330, 150, 0.4)  # E4
        return tone1 + tone2[44:]

    @classmethod
    def get_feedback_for_state(cls, state: "PipelineState") -> Optional[bytes]:
        """Get feedback sound for a state transition."""
        state_sounds = {
            PipelineState.LISTENING: cls.listening_started,
            PipelineState.TRANSCRIBING: cls.command_received,
            PipelineState.IDLE: cls.processing_complete,
            PipelineState.ERROR: cls.error_sound,
        }
        generator = state_sounds.get(state)
        return generator() if generator else None


# =============================================================================
# Audio Playback (Step 305)
# =============================================================================


class AudioPlayer:
    """
    Audio playback interface for voice pipeline output.

    Supports playing synthesized speech and feedback sounds.
    Uses sounddevice for cross-platform audio output.
    """

    def __init__(self, device: Optional[str] = None):
        """
        Initialize audio player.

        Args:
            device: Audio output device name (None for default)
        """
        self.device = device
        self._sd = None
        self._loaded = False

    async def _ensure_loaded(self):
        """Lazily load sounddevice."""
        if self._loaded:
            return

        try:
            import sounddevice as sd
            self._sd = sd
            self._loaded = True
            logger.info("Audio player initialized")
        except ImportError:
            logger.warning("sounddevice not installed, using mock audio player")
            self._sd = None
            self._loaded = True

    async def play(self, audio_data: bytes, blocking: bool = True) -> bool:
        """
        Play audio data (Step 305).

        Args:
            audio_data: WAV format audio bytes
            blocking: Wait for playback to complete

        Returns:
            True if playback succeeded
        """
        await self._ensure_loaded()

        if self._sd is None:
            # Mock playback - just log
            logger.info(f"Mock audio playback: {len(audio_data)} bytes")
            return True

        try:
            import numpy as np
            import io
            import wave

            # Parse WAV data
            wav_io = io.BytesIO(audio_data)
            with wave.open(wav_io, 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                n_channels = wav_file.getnchannels()
                n_frames = wav_file.getnframes()
                audio_frames = wav_file.readframes(n_frames)

            # Convert to numpy array
            audio_array = np.frombuffer(audio_frames, dtype=np.int16)
            audio_array = audio_array.astype(np.float32) / 32768.0

            if n_channels > 1:
                audio_array = audio_array.reshape(-1, n_channels)

            # Play audio
            if blocking:
                self._sd.play(audio_array, sample_rate, device=self.device)
                self._sd.wait()
            else:
                self._sd.play(audio_array, sample_rate, device=self.device)

            logger.debug(f"Audio playback complete: {n_frames} frames")
            return True

        except Exception as e:
            logger.error(f"Audio playback failed: {e}")
            return False

    async def play_feedback(self, state: "PipelineState") -> bool:
        """
        Play audio feedback for state change (Step 309).

        Args:
            state: New pipeline state

        Returns:
            True if feedback played
        """
        sound = AudioFeedback.get_feedback_for_state(state)
        if sound:
            return await self.play(sound, blocking=False)
        return False

    def stop(self):
        """Stop any currently playing audio."""
        if self._sd:
            try:
                self._sd.stop()
            except Exception:
                pass


# =============================================================================
# Audio Capture with VAD (Step 295)
# =============================================================================


class AudioCapture:
    """
    Audio capture with Voice Activity Detection (Step 295).

    Captures audio from microphone with VAD to detect speech start/end,
    enabling hands-free voice command input.

    Usage:
        capture = AudioCapture(sample_rate=16000, vad_aggressiveness=2)
        audio_data = await capture.capture_until_silence()
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        vad_aggressiveness: int = 2,
        frame_duration_ms: int = 30,
        silence_threshold_sec: float = 1.5,
        max_duration_sec: float = 30.0,
        device: Optional[str] = None,
    ):
        """
        Initialize audio capture.

        Args:
            sample_rate: Audio sample rate (must be 8000, 16000, 32000, or 48000 for VAD)
            channels: Number of audio channels
            vad_aggressiveness: VAD sensitivity 0-3 (higher = more aggressive)
            frame_duration_ms: Frame duration for VAD (10, 20, or 30 ms)
            silence_threshold_sec: Seconds of silence to stop recording
            max_duration_sec: Maximum recording duration
            device: Audio input device name
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.vad_aggressiveness = vad_aggressiveness
        self.frame_duration_ms = frame_duration_ms
        self.silence_threshold_sec = silence_threshold_sec
        self.max_duration_sec = max_duration_sec
        self.device = device

        self._vad = None
        self._sd = None
        self._loaded = False
        self._capturing = False

    async def _ensure_loaded(self):
        """Lazily load dependencies."""
        if self._loaded:
            return

        try:
            import sounddevice as sd
            self._sd = sd
        except ImportError:
            logger.warning("sounddevice not installed, audio capture disabled")
            self._sd = None

        try:
            import webrtcvad
            self._vad = webrtcvad.Vad(self.vad_aggressiveness)
        except ImportError:
            logger.warning("webrtcvad not installed, VAD disabled")
            self._vad = None

        self._loaded = True

    @property
    def is_capturing(self) -> bool:
        """Check if currently capturing audio."""
        return self._capturing

    async def capture_until_silence(self) -> Optional[bytes]:
        """
        Capture audio until silence is detected (Step 295).

        Records audio starting when speech is detected and stops
        after a period of silence.

        Returns:
            Raw audio bytes (16-bit PCM) or None if capture failed
        """
        await self._ensure_loaded()

        if self._sd is None:
            logger.error("sounddevice not available for capture")
            return None

        self._capturing = True
        frames = []
        speech_started = False
        silence_frames = 0
        frame_size = int(self.sample_rate * self.frame_duration_ms / 1000)
        silence_frame_threshold = int(self.silence_threshold_sec * 1000 / self.frame_duration_ms)
        max_frames = int(self.max_duration_sec * 1000 / self.frame_duration_ms)

        logger.info("Starting audio capture with VAD")

        try:
            import numpy as np
            import queue

            audio_queue = queue.Queue()

            def audio_callback(indata, frames_count, time_info, status):
                if status:
                    logger.warning(f"Audio capture status: {status}")
                audio_queue.put(indata.copy())

            with self._sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='int16',
                blocksize=frame_size,
                callback=audio_callback,
                device=self.device,
            ):
                frame_count = 0
                while self._capturing and frame_count < max_frames:
                    try:
                        # Get audio frame with timeout
                        frame_data = audio_queue.get(timeout=0.1)
                        frame_bytes = frame_data.tobytes()

                        # Check for speech with VAD
                        is_speech = True  # Default if VAD not available
                        if self._vad:
                            try:
                                is_speech = self._vad.is_speech(frame_bytes, self.sample_rate)
                            except Exception:
                                pass

                        if is_speech:
                            speech_started = True
                            silence_frames = 0
                            frames.append(frame_bytes)
                        elif speech_started:
                            frames.append(frame_bytes)
                            silence_frames += 1
                            if silence_frames >= silence_frame_threshold:
                                logger.info("Silence detected, stopping capture")
                                break

                        frame_count += 1

                        # Yield to event loop
                        await asyncio.sleep(0)

                    except queue.Empty:
                        continue

        except Exception as e:
            logger.error(f"Audio capture error: {e}")
            return None
        finally:
            self._capturing = False

        if not frames:
            logger.warning("No audio captured")
            return None

        # Combine frames
        audio_data = b''.join(frames)
        logger.info(f"Captured {len(audio_data)} bytes of audio")
        return audio_data

    def stop_capture(self):
        """Stop ongoing capture."""
        self._capturing = False


# =============================================================================
# LED Indicator Support (Step 310)
# =============================================================================


class LEDIndicator:
    """
    Visual LED indicator for pipeline state (Step 310).

    Controls an LED (via GPIO) to indicate pipeline state:
    - Off: Idle
    - Solid: Listening
    - Fast blink: Processing
    - Slow blink: Speaking
    - Double blink: Error

    Supports both real GPIO (Raspberry Pi) and mock mode for testing.
    """

    # Blink patterns (on_ms, off_ms, repeat)
    PATTERNS = {
        PipelineState.IDLE: None,  # LED off
        PipelineState.LISTENING: (1000, 0, 1),  # Solid on
        PipelineState.TRANSCRIBING: (100, 100, -1),  # Fast blink
        PipelineState.PROCESSING: (100, 100, -1),  # Fast blink
        PipelineState.EXECUTING: (200, 200, -1),  # Medium blink
        PipelineState.SPEAKING: (500, 500, -1),  # Slow blink
        PipelineState.ERROR: (100, 100, 2),  # Double blink
    }

    def __init__(self, gpio_pin: int = 18, enabled: bool = True):
        """
        Initialize LED indicator.

        Args:
            gpio_pin: GPIO pin number for LED
            enabled: Whether LED control is enabled
        """
        self.gpio_pin = gpio_pin
        self.enabled = enabled
        self._gpio = None
        self._loaded = False
        self._blink_task: Optional[asyncio.Task] = None
        self._current_state = PipelineState.IDLE

    async def _ensure_loaded(self):
        """Lazily load GPIO library."""
        if self._loaded or not self.enabled:
            return

        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.gpio_pin, GPIO.OUT)
            GPIO.output(self.gpio_pin, GPIO.LOW)
            self._gpio = GPIO
            logger.info(f"LED indicator initialized on GPIO {self.gpio_pin}")
        except (ImportError, RuntimeError):
            logger.info("GPIO not available, LED indicator in mock mode")
            self._gpio = None

        self._loaded = True

    def _set_led(self, on: bool):
        """Set LED state."""
        if self._gpio:
            self._gpio.output(self.gpio_pin, self._gpio.HIGH if on else self._gpio.LOW)
        else:
            logger.debug(f"LED {'ON' if on else 'OFF'} (mock)")

    async def _blink_pattern(self, on_ms: int, off_ms: int, repeat: int):
        """Execute blink pattern."""
        count = 0
        while repeat < 0 or count < repeat:
            self._set_led(True)
            await asyncio.sleep(on_ms / 1000)
            if off_ms > 0:
                self._set_led(False)
                await asyncio.sleep(off_ms / 1000)
            count += 1

    async def set_state(self, state: PipelineState):
        """
        Set LED to indicate pipeline state (Step 310).

        Args:
            state: New pipeline state
        """
        await self._ensure_loaded()

        if state == self._current_state:
            return

        self._current_state = state

        # Cancel existing blink task
        if self._blink_task:
            self._blink_task.cancel()
            try:
                await self._blink_task
            except asyncio.CancelledError:
                pass
            self._blink_task = None

        pattern = self.PATTERNS.get(state)

        if pattern is None:
            # LED off
            self._set_led(False)
        else:
            on_ms, off_ms, repeat = pattern
            if off_ms == 0:
                # Solid on
                self._set_led(True)
            else:
                # Start blink task
                self._blink_task = asyncio.create_task(
                    self._blink_pattern(on_ms, off_ms, repeat)
                )

    async def cleanup(self):
        """Cleanup GPIO resources."""
        if self._blink_task:
            self._blink_task.cancel()
            try:
                await self._blink_task
            except asyncio.CancelledError:
                pass

        self._set_led(False)

        if self._gpio:
            self._gpio.cleanup(self.gpio_pin)


def normalize_transcript(text: str) -> str:
    """
    Normalize transcribed text for better command processing (Step 300).

    Applies:
    - Case normalization
    - Whitespace normalization
    - Astronomy term standardization
    - Common speech-to-text error correction

    Args:
        text: Raw transcription from STT

    Returns:
        Normalized text ready for LLM processing
    """
    if not text:
        return ""

    # Strip and normalize whitespace
    result = " ".join(text.split())

    # Apply astronomy normalizations
    lower_result = result.lower()
    for pattern, replacement in ASTRONOMY_NORMALIZATIONS.items():
        if pattern in lower_result:
            # Find the actual position and replace preserving case structure
            idx = lower_result.find(pattern)
            result = result[:idx] + replacement + result[idx + len(pattern):]
            lower_result = result.lower()

    # Remove filler words common in speech
    filler_words = [
        "um", "uh", "like", "you know", "basically", "actually",
        "so", "well", "okay so", "alright so"
    ]
    words = result.split()
    filtered_words = []
    for word in words:
        if word.lower() not in filler_words:
            filtered_words.append(word)
    result = " ".join(filtered_words)

    # Ensure proper sentence ending
    if result and not result[-1] in ".?!":
        # Don't add period for commands
        pass

    return result.strip()


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
        self._audio_player: Optional[AudioPlayer] = None

        # Step 295: Audio capture with VAD
        self._audio_capture: Optional[AudioCapture] = None

        # Step 297: Continuous listening mode
        self._continuous_listening = False

        # Step 310: LED indicator
        self._led_indicator: Optional[LEDIndicator] = None
        if self.config.led_enabled:
            self._led_indicator = LEDIndicator(
                gpio_pin=self.config.led_gpio_pin,
                enabled=True
            )

        # Metrics (Step 308 - enhanced latency tracking)
        self._commands_processed = 0
        self._total_latency_ms = 0.0
        self._min_latency_ms = float('inf')
        self._max_latency_ms = 0.0
        self._latency_history: List[Dict[str, float]] = []

        # Audio feedback enabled
        self._enable_feedback = config.play_acknowledgment if config else True

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

    def _get_audio_player(self) -> AudioPlayer:
        """Get or create audio player (Step 305)."""
        if self._audio_player is None:
            self._audio_player = AudioPlayer()
        return self._audio_player

    async def _set_state(self, new_state: PipelineState):
        """
        Set pipeline state with optional audio feedback (Step 309).

        Args:
            new_state: New pipeline state
        """
        old_state = self._state
        self._state = new_state

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(new_state)
            except Exception as e:
                logger.warning(f"State callback error: {e}")

        # Play audio feedback if enabled
        if self._enable_feedback and old_state != new_state:
            try:
                player = self._get_audio_player()
                await player.play_feedback(new_state)
            except Exception as e:
                logger.debug(f"Audio feedback error: {e}")

    def _record_latency(self, result: PipelineResult):
        """
        Record latency metrics (Step 308).

        Args:
            result: Pipeline result with timing info
        """
        total = result.total_latency_ms

        # Update min/max
        if total < self._min_latency_ms:
            self._min_latency_ms = total
        if total > self._max_latency_ms:
            self._max_latency_ms = total

        # Record history (keep last 100)
        self._latency_history.append({
            "stt_ms": result.stt_latency_ms,
            "llm_ms": result.llm_latency_ms,
            "tool_ms": result.tool_latency_ms,
            "tts_ms": result.tts_latency_ms,
            "total_ms": total,
            "timestamp": result.timestamp.isoformat(),
        })
        if len(self._latency_history) > 100:
            self._latency_history.pop(0)

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
            await self._set_state(PipelineState.TRANSCRIBING)
            stt_start = time.time()

            stt = self._get_stt()
            raw_transcript = await stt.transcribe(audio_data)

            # Step 300: Normalize transcript
            transcript = normalize_transcript(raw_transcript)
            result.transcript = transcript
            result.stt_latency_ms = (time.time() - stt_start) * 1000

            if not transcript:
                result.spoken_response = "I didn't catch that. Could you repeat?"
                await self._set_state(PipelineState.IDLE)
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
            await self._set_state(PipelineState.SPEAKING)
            tts_start = time.time()

            tts = self._get_tts()
            result.audio_output = await tts.synthesize(result.spoken_response)

            result.tts_latency_ms = (time.time() - tts_start) * 1000

            # Calculate total
            result.total_latency_ms = (time.time() - start_time) * 1000
            result.success = True

            # Update metrics (Step 308)
            self._commands_processed += 1
            self._total_latency_ms += result.total_latency_ms
            self._record_latency(result)

            logger.info(f"Pipeline complete in {result.total_latency_ms:.0f}ms")

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            result.success = False
            result.error = str(e)
            result.spoken_response = "Sorry, an error occurred processing your command."
            await self._set_state(PipelineState.ERROR)

        finally:
            await self._set_state(PipelineState.IDLE)

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
            await self._set_state(PipelineState.PROCESSING)
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
                await self._set_state(PipelineState.EXECUTING)
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
        """Get pipeline metrics (Step 308 - enhanced latency tracking)."""
        avg_latency = 0.0
        if self._commands_processed > 0:
            avg_latency = self._total_latency_ms / self._commands_processed

        # Calculate component averages from history
        avg_stt = avg_llm = avg_tool = avg_tts = 0.0
        if self._latency_history:
            n = len(self._latency_history)
            avg_stt = sum(h["stt_ms"] for h in self._latency_history) / n
            avg_llm = sum(h["llm_ms"] for h in self._latency_history) / n
            avg_tool = sum(h["tool_ms"] for h in self._latency_history) / n
            avg_tts = sum(h["tts_ms"] for h in self._latency_history) / n

        return {
            "commands_processed": self._commands_processed,
            "total_latency_ms": self._total_latency_ms,
            "avg_latency_ms": avg_latency,
            "min_latency_ms": self._min_latency_ms if self._commands_processed > 0 else 0.0,
            "max_latency_ms": self._max_latency_ms,
            "avg_stt_latency_ms": avg_stt,
            "avg_llm_latency_ms": avg_llm,
            "avg_tool_latency_ms": avg_tool,
            "avg_tts_latency_ms": avg_tts,
            "state": self._state.value,
        }

    def get_latency_history(self) -> List[Dict[str, float]]:
        """Get latency history for analysis (Step 308)."""
        return list(self._latency_history)

    async def play_response(self, audio_data: bytes) -> bool:
        """
        Play audio response through speaker (Step 305).

        Args:
            audio_data: WAV format audio bytes

        Returns:
            True if playback succeeded
        """
        player = self._get_audio_player()
        return await player.play(audio_data, blocking=True)

    # =========================================================================
    # Continuous Listening Mode (Step 297)
    # =========================================================================

    async def listen_continuous(self, callback: Optional[Callable] = None):
        """
        Start continuous listening mode (Step 297).

        Continuously captures audio commands and processes them,
        enabling hands-free operation.

        Args:
            callback: Optional callback for each processed command

        Note:
            Call stop() to exit continuous listening mode.
        """
        if not self._running:
            await self.start()

        if self._audio_capture is None:
            self._audio_capture = AudioCapture(
                sample_rate=self.config.audio_sample_rate,
                channels=self.config.audio_channels,
                vad_aggressiveness=self.config.vad_aggressiveness,
                frame_duration_ms=self.config.vad_frame_ms,
                silence_threshold_sec=self.config.silence_threshold_sec,
                max_duration_sec=self.config.max_audio_length_sec,
            )

        logger.info("Starting continuous listening mode")
        self._continuous_listening = True

        while self._running and self._continuous_listening:
            try:
                # Set state to listening
                await self._set_state(PipelineState.LISTENING)

                # Update LED indicator if enabled
                if self._led_indicator:
                    await self._led_indicator.set_state(PipelineState.LISTENING)

                # Capture audio with VAD
                audio_data = await self._audio_capture.capture_until_silence()

                if audio_data:
                    # Process the captured audio
                    result = await self.process_audio(audio_data)

                    # Call callback if provided
                    if callback:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(result)
                            else:
                                callback(result)
                        except Exception as e:
                            logger.error(f"Continuous listening callback error: {e}")

                    # Play the response
                    if result.audio_output:
                        await self.play_response(result.audio_output)

                # Small delay before next listen cycle
                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Continuous listening error: {e}")
                await asyncio.sleep(1)  # Prevent tight loop on errors

        logger.info("Exited continuous listening mode")

    def stop_continuous_listening(self):
        """Stop continuous listening mode."""
        self._continuous_listening = False
        if self._audio_capture:
            self._audio_capture.stop_capture()

    # =========================================================================
    # Concurrent Request Handling (Step 307)
    # =========================================================================

    async def process_concurrent(
        self,
        requests: List[Union[str, bytes]],
        max_concurrent: Optional[int] = None,
    ) -> List[PipelineResult]:
        """
        Process multiple requests concurrently (Step 307).

        Args:
            requests: List of text commands or audio bytes
            max_concurrent: Max concurrent requests (uses config default if None)

        Returns:
            List of PipelineResult for each request
        """
        max_concurrent = max_concurrent or self.config.max_concurrent_requests
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []

        async def process_with_semaphore(request, index):
            async with semaphore:
                try:
                    if isinstance(request, bytes):
                        result = await asyncio.wait_for(
                            self.process_audio(request),
                            timeout=self.config.request_timeout_sec,
                        )
                    else:
                        result = await asyncio.wait_for(
                            self.process_text(request),
                            timeout=self.config.request_timeout_sec,
                        )
                    return index, result
                except asyncio.TimeoutError:
                    result = PipelineResult(
                        transcript=request if isinstance(request, str) else "",
                        success=False,
                        error="Request timed out",
                    )
                    return index, result
                except Exception as e:
                    result = PipelineResult(
                        transcript=request if isinstance(request, str) else "",
                        success=False,
                        error=str(e),
                    )
                    return index, result

        # Create tasks for all requests
        tasks = [
            process_with_semaphore(req, i)
            for i, req in enumerate(requests)
        ]

        # Wait for all tasks
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        # Sort by original index and extract results
        sorted_results = [None] * len(requests)
        for item in completed:
            if isinstance(item, tuple):
                index, result = item
                sorted_results[index] = result
            else:
                # Exception case
                logger.error(f"Concurrent request error: {item}")

        return [r for r in sorted_results if r is not None]

    async def submit_request(self, request: Union[str, bytes]) -> asyncio.Task:
        """
        Submit a request for background processing (Step 307).

        Args:
            request: Text command or audio bytes

        Returns:
            Task that can be awaited for result
        """
        if isinstance(request, bytes):
            task = asyncio.create_task(self.process_audio(request))
        else:
            task = asyncio.create_task(self.process_text(request))

        return task

    # =========================================================================
    # LED Indicator Integration (Step 310)
    # =========================================================================

    def enable_led_indicator(self, gpio_pin: Optional[int] = None):
        """
        Enable LED indicator for pipeline state (Step 310).

        Args:
            gpio_pin: GPIO pin for LED (uses config default if None)
        """
        pin = gpio_pin or self.config.led_gpio_pin
        self._led_indicator = LEDIndicator(gpio_pin=pin, enabled=True)
        logger.info(f"LED indicator enabled on GPIO {pin}")

    def disable_led_indicator(self):
        """Disable LED indicator."""
        if self._led_indicator:
            asyncio.create_task(self._led_indicator.cleanup())
            self._led_indicator = None


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
