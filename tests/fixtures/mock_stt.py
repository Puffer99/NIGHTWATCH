"""
Mock Speech-to-Text Service for Testing.

Simulates STT (Whisper) for unit and integration testing.
Provides configurable transcription responses and error injection.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, List, Any

logger = logging.getLogger("NIGHTWATCH.fixtures.MockSTT")


class MockSTTState(Enum):
    """STT service state."""
    DISCONNECTED = "disconnected"
    READY = "ready"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    ERROR = "error"


@dataclass
class TranscriptionResult:
    """Result of a transcription."""
    text: str
    confidence: float = 0.95
    language: str = "en"
    duration_sec: float = 0.0
    is_final: bool = True
    segments: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "language": self.language,
            "duration_sec": self.duration_sec,
            "is_final": self.is_final,
        }


@dataclass
class STTStats:
    """STT usage statistics."""
    total_transcriptions: int = 0
    total_audio_seconds: float = 0.0
    average_confidence: float = 0.0
    average_latency_sec: float = 0.0


class MockSTT:
    """
    Mock STT service for testing.

    Simulates Whisper speech-to-text with:
    - Configurable transcription responses
    - Wake word detection
    - Continuous listening mode
    - Confidence simulation
    - Error injection

    Example:
        stt = MockSTT()
        await stt.connect()

        # Set expected transcription
        stt.set_transcription("Go to Andromeda galaxy")

        result = await stt.transcribe(audio_data)
        print(result.text)  # "Go to Andromeda galaxy"
    """

    # Wake word configuration
    DEFAULT_WAKE_WORD = "hey nightwatch"

    # Common test phrases
    TEST_PHRASES = [
        "Go to Andromeda galaxy",
        "What's the weather like",
        "Park the telescope",
        "Take a 30 second exposure",
        "Start guiding",
        "What is the current status",
        "Focus the camera",
        "Stop all operations",
    ]

    def __init__(
        self,
        model_name: str = "whisper-large-v3",
        wake_word: str = DEFAULT_WAKE_WORD,
        simulate_delays: bool = True,
        transcription_time_sec: float = 0.3,
    ):
        """
        Initialize mock STT.

        Args:
            model_name: Model name for identification
            wake_word: Wake word for activation
            simulate_delays: Whether to simulate transcription time
            transcription_time_sec: Simulated transcription time
        """
        self.model_name = model_name
        self.wake_word = wake_word.lower()
        self.simulate_delays = simulate_delays
        self.transcription_time_sec = transcription_time_sec

        # State
        self._state = MockSTTState.DISCONNECTED
        self._stats = STTStats()
        self._is_listening = False

        # Configured responses
        self._next_transcription: Optional[str] = None
        self._transcription_queue: List[str] = []
        self._phrase_index = 0

        # Error injection
        self._inject_connect_error = False
        self._inject_transcribe_error = False
        self._inject_timeout = False
        self._inject_noise = False  # Return garbled text

        # Callbacks
        self._transcription_callbacks: List[Callable] = []
        self._wake_word_callbacks: List[Callable] = []

    @property
    def state(self) -> MockSTTState:
        """Get current state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if STT is connected."""
        return self._state != MockSTTState.DISCONNECTED

    @property
    def is_listening(self) -> bool:
        """Check if actively listening."""
        return self._is_listening

    async def connect(self) -> bool:
        """
        Connect to STT service.

        Returns:
            True if connected successfully
        """
        if self._inject_connect_error:
            raise ConnectionError("Mock: Simulated connection failure")

        if self.simulate_delays:
            await asyncio.sleep(0.1)

        self._state = MockSTTState.READY
        logger.info(f"MockSTT connected: {self.model_name}")
        return True

    async def disconnect(self):
        """Disconnect from STT service."""
        self._is_listening = False
        self._state = MockSTTState.DISCONNECTED
        logger.info("MockSTT disconnected")

    async def transcribe(
        self,
        audio_data: Any,
        language: str = "en",
    ) -> TranscriptionResult:
        """
        Transcribe audio data.

        Args:
            audio_data: Audio data (ignored in mock)
            language: Target language

        Returns:
            Transcription result
        """
        if not self.is_connected:
            raise RuntimeError("STT not connected")

        if self._inject_transcribe_error:
            raise RuntimeError("Mock: Simulated transcription failure")

        if self._inject_timeout:
            raise TimeoutError("Mock: Simulated transcription timeout")

        self._state = MockSTTState.TRANSCRIBING
        start_time = datetime.now()

        # Simulate transcription time
        if self.simulate_delays:
            await asyncio.sleep(self.transcription_time_sec)

        # Get transcription
        text = self._get_transcription()

        # Handle noise injection
        if self._inject_noise:
            text = self._add_noise(text)

        # Build result
        transcription_time = (datetime.now() - start_time).total_seconds()
        result = TranscriptionResult(
            text=text,
            confidence=0.95 if not self._inject_noise else 0.6,
            language=language,
            duration_sec=transcription_time,
            is_final=True,
        )

        # Update stats
        self._update_stats(result, transcription_time)

        self._state = MockSTTState.READY

        # Check for wake word
        if self.wake_word in text.lower():
            self._notify_wake_word(text)

        # Notify callbacks
        for callback in self._transcription_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Transcription callback error: {e}")

        return result

    def _get_transcription(self) -> str:
        """Get the configured or queued transcription."""
        # Check queue first
        if self._transcription_queue:
            return self._transcription_queue.pop(0)

        # Check explicit next transcription
        if self._next_transcription is not None:
            text = self._next_transcription
            self._next_transcription = None
            return text

        # Return from test phrases (cycling)
        text = self.TEST_PHRASES[self._phrase_index % len(self.TEST_PHRASES)]
        self._phrase_index += 1
        return text

    def _add_noise(self, text: str) -> str:
        """Add noise/errors to transcription."""
        # Simple noise simulation - replace some words
        words = text.split()
        if len(words) > 2:
            words[1] = "[unintelligible]"
        return " ".join(words)

    def _update_stats(self, result: TranscriptionResult, latency: float):
        """Update usage statistics."""
        n = self._stats.total_transcriptions + 1
        self._stats.total_transcriptions = n
        self._stats.total_audio_seconds += result.duration_sec

        # Update averages
        old_conf = self._stats.average_confidence
        self._stats.average_confidence = (old_conf * (n - 1) + result.confidence) / n

        old_lat = self._stats.average_latency_sec
        self._stats.average_latency_sec = (old_lat * (n - 1) + latency) / n

    def _notify_wake_word(self, text: str):
        """Notify wake word callbacks."""
        for callback in self._wake_word_callbacks:
            try:
                callback(text)
            except Exception as e:
                logger.error(f"Wake word callback error: {e}")

    def get_stats(self) -> STTStats:
        """Get usage statistics."""
        return self._stats

    # Listening mode
    async def start_listening(self):
        """Start continuous listening mode."""
        if not self.is_connected:
            raise RuntimeError("STT not connected")

        self._is_listening = True
        self._state = MockSTTState.LISTENING
        logger.info("MockSTT: Listening started")

    async def stop_listening(self):
        """Stop continuous listening mode."""
        self._is_listening = False
        self._state = MockSTTState.READY
        logger.info("MockSTT: Listening stopped")

    # Transcription configuration
    def set_transcription(self, text: str):
        """Set the next transcription result."""
        self._next_transcription = text

    def queue_transcription(self, text: str):
        """Queue a transcription to be returned."""
        self._transcription_queue.append(text)

    def queue_transcriptions(self, texts: List[str]):
        """Queue multiple transcriptions."""
        self._transcription_queue.extend(texts)

    def set_wake_word(self, wake_word: str):
        """Set the wake word."""
        self.wake_word = wake_word.lower()

    # Callbacks
    def set_transcription_callback(self, callback: Callable):
        """Register callback for transcription completion."""
        self._transcription_callbacks.append(callback)

    def set_wake_word_callback(self, callback: Callable):
        """Register callback for wake word detection."""
        self._wake_word_callbacks.append(callback)

    # Error injection
    def inject_connect_error(self, enable: bool = True):
        """Enable/disable connection error injection."""
        self._inject_connect_error = enable

    def inject_transcribe_error(self, enable: bool = True):
        """Enable/disable transcription error injection."""
        self._inject_transcribe_error = enable

    def inject_timeout(self, enable: bool = True):
        """Enable/disable timeout injection."""
        self._inject_timeout = enable

    def inject_noise(self, enable: bool = True):
        """Enable/disable noise injection (garbled transcription)."""
        self._inject_noise = enable

    def reset(self):
        """Reset mock to initial state."""
        self._state = MockSTTState.DISCONNECTED
        self._stats = STTStats()
        self._is_listening = False
        self._next_transcription = None
        self._transcription_queue = []
        self._phrase_index = 0
        self._inject_connect_error = False
        self._inject_transcribe_error = False
        self._inject_timeout = False
        self._inject_noise = False
