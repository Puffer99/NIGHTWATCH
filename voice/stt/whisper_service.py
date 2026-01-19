"""
NIGHTWATCH Voice STT Service
Whisper Speech-to-Text Integration

This module provides speech-to-text capabilities using OpenAI's Whisper model,
optimized for running locally on DGX Spark for low-latency telescope control.

Supports:
- Local Whisper model inference (faster-whisper or whisper.cpp)
- Streaming audio input from microphone
- Voice activity detection
- Noise suppression for outdoor environment
"""

import asyncio
import queue
import threading
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Callable, List
import numpy as np

# Try to import audio libraries
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

# Try to import neural VAD (pymicro-vad)
try:
    from pymicro_vad import MicroVAD
    NEURAL_VAD_AVAILABLE = True
except ImportError:
    NEURAL_VAD_AVAILABLE = False

# Try to import Whisper
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
    WHISPER_BACKEND = "faster-whisper"
except ImportError:
    try:
        import whisper
        WHISPER_AVAILABLE = True
        WHISPER_BACKEND = "openai-whisper"
    except ImportError:
        WHISPER_AVAILABLE = False
        WHISPER_BACKEND = None


class WhisperModelSize(Enum):
    """Available Whisper model sizes."""
    TINY = "tiny"        # 39M params, fastest
    BASE = "base"        # 74M params
    SMALL = "small"      # 244M params
    MEDIUM = "medium"    # 769M params
    LARGE = "large-v3"   # 1.5B params, most accurate


@dataclass
class TranscriptionResult:
    """Result from speech transcription."""
    text: str
    confidence: float
    language: str
    duration_seconds: float
    timestamp: datetime
    segments: List[dict]  # Word-level timing if available

    @property
    def is_command(self) -> bool:
        """Check if transcription looks like a telescope command."""
        command_keywords = [
            "point", "go to", "goto", "slew", "track",
            "park", "home", "stop", "abort",
            "what", "where", "show", "find",
            "mars", "jupiter", "saturn", "moon", "sun",
            "messier", "ngc", "star",
        ]
        text_lower = self.text.lower()
        return any(kw in text_lower for kw in command_keywords)


@dataclass
class AudioConfig:
    """Audio input configuration."""
    sample_rate: int = 16000      # Whisper expects 16kHz
    channels: int = 1             # Mono
    dtype: str = "float32"
    chunk_duration: float = 0.5   # Seconds per audio chunk
    silence_threshold: float = 0.01
    silence_duration: float = 1.0  # Seconds of silence to end utterance
    max_duration: float = 30.0    # Max recording duration


class VoiceActivityDetector:
    """Simple voice activity detection using energy threshold."""

    def __init__(
        self,
        threshold: float = 0.01,
        min_speech_duration: float = 0.3,
        min_silence_duration: float = 0.8
    ):
        self.threshold = threshold
        self.min_speech_samples = int(min_speech_duration * 16000)
        self.min_silence_samples = int(min_silence_duration * 16000)

        self._is_speaking = False
        self._speech_samples = 0
        self._silence_samples = 0

    def process(self, audio_chunk: np.ndarray) -> bool:
        """
        Process audio chunk and return voice activity state.

        Args:
            audio_chunk: Audio samples as numpy array

        Returns:
            True if speech detected, False otherwise
        """
        # Calculate RMS energy
        energy = np.sqrt(np.mean(audio_chunk ** 2))

        if energy > self.threshold:
            self._speech_samples += len(audio_chunk)
            self._silence_samples = 0

            if self._speech_samples >= self.min_speech_samples:
                self._is_speaking = True
        else:
            self._silence_samples += len(audio_chunk)

            if self._is_speaking and self._silence_samples >= self.min_silence_samples:
                self._is_speaking = False
                self._speech_samples = 0

        return self._is_speaking

    def reset(self):
        """Reset detector state."""
        self._is_speaking = False
        self._speech_samples = 0
        self._silence_samples = 0

    @property
    def backend(self) -> str:
        """Return the VAD backend being used."""
        return "energy-threshold"


class EnhancedVAD:
    """
    Neural VAD using pymicro-vad for robust speech detection.

    This provides more accurate speech detection than energy-threshold VAD,
    especially in noisy outdoor telescope environments with wind, wildlife,
    and equipment sounds.

    Falls back to energy-threshold VAD if pymicro-vad is not available.
    """

    def __init__(self, threshold: float = 0.5, sample_rate: int = 16000):
        """
        Initialize enhanced VAD.

        Args:
            threshold: Speech probability threshold (0.0-1.0)
            sample_rate: Audio sample rate (must be 16kHz for pymicro-vad)
        """
        self.threshold = threshold
        self.sample_rate = sample_rate

        if NEURAL_VAD_AVAILABLE:
            self._vad = MicroVAD()
            self._use_neural = True
        else:
            self._vad = None
            self._use_neural = False
            # Fallback energy threshold
            self._energy_threshold = 0.01

        self._is_speaking = False
        self._speech_frames = 0
        self._silence_frames = 0
        self._min_speech_frames = 3   # Require consecutive speech frames
        self._min_silence_frames = 8  # Require consecutive silence frames

    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """
        Detect if audio chunk contains speech.

        Args:
            audio_chunk: Audio samples as numpy array (16kHz, float32)

        Returns:
            True if speech detected, False otherwise
        """
        if self._use_neural:
            return self._neural_detect(audio_chunk)
        else:
            return self._energy_detect(audio_chunk)

    def _neural_detect(self, audio_chunk: np.ndarray) -> bool:
        """Neural VAD detection using pymicro-vad."""
        # pymicro-vad expects 16kHz, 16-bit PCM bytes
        audio_int16 = (audio_chunk * 32767).astype(np.int16)
        probability = self._vad.process(audio_int16.tobytes())

        is_speech_frame = probability > self.threshold

        # Hysteresis: require consecutive frames to change state
        if is_speech_frame:
            self._speech_frames += 1
            self._silence_frames = 0
            if self._speech_frames >= self._min_speech_frames:
                self._is_speaking = True
        else:
            self._silence_frames += 1
            self._speech_frames = 0
            if self._is_speaking and self._silence_frames >= self._min_silence_frames:
                self._is_speaking = False

        return self._is_speaking

    def _energy_detect(self, audio_chunk: np.ndarray) -> bool:
        """Fallback energy-based detection."""
        energy = np.sqrt(np.mean(audio_chunk ** 2))

        if energy > self._energy_threshold:
            self._speech_frames += 1
            self._silence_frames = 0
            if self._speech_frames >= self._min_speech_frames:
                self._is_speaking = True
        else:
            self._silence_frames += 1
            self._speech_frames = 0
            if self._is_speaking and self._silence_frames >= self._min_silence_frames:
                self._is_speaking = False

        return self._is_speaking

    def reset(self):
        """Reset detector state."""
        if self._use_neural and self._vad:
            self._vad.reset()
        self._is_speaking = False
        self._speech_frames = 0
        self._silence_frames = 0

    def process(self, audio_chunk: np.ndarray) -> bool:
        """
        Process audio chunk (alias for is_speech for compatibility).

        Args:
            audio_chunk: Audio samples as numpy array

        Returns:
            True if speech detected, False otherwise
        """
        return self.is_speech(audio_chunk)

    @property
    def backend(self) -> str:
        """Return the VAD backend being used."""
        return "pymicro-vad" if self._use_neural else "energy-threshold"


class WhisperSTT:
    """
    Whisper-based speech-to-text service.

    Optimized for local inference on DGX Spark.
    """

    def __init__(
        self,
        model_size: WhisperModelSize = WhisperModelSize.SMALL,
        device: str = "cuda",
        compute_type: str = "float16",
        language: str = "en",
        use_enhanced_vad: bool = True
    ):
        """
        Initialize Whisper STT service.

        Args:
            model_size: Whisper model size
            device: "cuda" or "cpu"
            compute_type: "float16", "int8", or "float32"
            language: Language code for transcription
            use_enhanced_vad: Use neural VAD (pymicro-vad) if available
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language

        self._model = None
        self._audio_config = AudioConfig()

        # Use EnhancedVAD (neural) by default, falls back to energy-threshold
        if use_enhanced_vad:
            self._vad = EnhancedVAD()
        else:
            self._vad = VoiceActivityDetector()

        self._is_listening = False
        self._audio_queue: queue.Queue = queue.Queue()
        self._callbacks: List[Callable[[TranscriptionResult], None]] = []

    def initialize(self):
        """Load Whisper model."""
        if not WHISPER_AVAILABLE:
            raise RuntimeError(
                "Whisper not available. Install with: "
                "pip install faster-whisper or pip install openai-whisper"
            )

        print(f"Loading Whisper model: {self.model_size.value} ({WHISPER_BACKEND})")

        if WHISPER_BACKEND == "faster-whisper":
            self._model = WhisperModel(
                self.model_size.value,
                device=self.device,
                compute_type=self.compute_type
            )
        else:
            import whisper
            self._model = whisper.load_model(self.model_size.value)

        print("Whisper model loaded")

    def transcribe(self, audio: np.ndarray) -> TranscriptionResult:
        """
        Transcribe audio to text.

        Args:
            audio: Audio samples as numpy array (16kHz, mono, float32)

        Returns:
            TranscriptionResult with transcribed text
        """
        if self._model is None:
            raise RuntimeError("Model not initialized. Call initialize() first.")

        start_time = datetime.now()

        if WHISPER_BACKEND == "faster-whisper":
            segments, info = self._model.transcribe(
                audio,
                language=self.language,
                beam_size=5,
                vad_filter=True
            )

            text_parts = []
            segment_list = []
            for segment in segments:
                text_parts.append(segment.text)
                segment_list.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text
                })

            text = " ".join(text_parts).strip()
            confidence = 0.9  # faster-whisper doesn't provide confidence

        else:
            # OpenAI Whisper
            result = self._model.transcribe(
                audio,
                language=self.language,
                fp16=(self.device == "cuda")
            )
            text = result["text"].strip()
            segment_list = result.get("segments", [])
            confidence = 0.9

        duration = (datetime.now() - start_time).total_seconds()

        return TranscriptionResult(
            text=text,
            confidence=confidence,
            language=self.language,
            duration_seconds=duration,
            timestamp=datetime.now(),
            segments=segment_list
        )

    def register_callback(self, callback: Callable[[TranscriptionResult], None]):
        """Register callback for transcription results."""
        self._callbacks.append(callback)

    def _audio_callback(self, indata, frames, time, status):
        """Callback for audio input stream."""
        if status:
            print(f"Audio status: {status}")
        self._audio_queue.put(indata.copy())

    async def start_listening(self):
        """Start continuous listening for voice commands."""
        if not SOUNDDEVICE_AVAILABLE:
            raise RuntimeError("sounddevice not available. Install with: pip install sounddevice")

        self._is_listening = True
        audio_buffer = []

        print("Listening for voice commands...")

        with sd.InputStream(
            samplerate=self._audio_config.sample_rate,
            channels=self._audio_config.channels,
            dtype=self._audio_config.dtype,
            callback=self._audio_callback,
            blocksize=int(self._audio_config.chunk_duration * self._audio_config.sample_rate)
        ):
            while self._is_listening:
                try:
                    # Get audio chunk
                    chunk = self._audio_queue.get(timeout=0.1)
                    chunk = chunk.flatten()

                    # Voice activity detection
                    is_speech = self._vad.process(chunk)

                    if is_speech:
                        audio_buffer.append(chunk)

                        # Check max duration
                        total_samples = sum(len(c) for c in audio_buffer)
                        if total_samples / self._audio_config.sample_rate > self._audio_config.max_duration:
                            # Process what we have
                            await self._process_buffer(audio_buffer)
                            audio_buffer = []
                            self._vad.reset()

                    elif audio_buffer:
                        # Speech ended, process buffer
                        await self._process_buffer(audio_buffer)
                        audio_buffer = []
                        self._vad.reset()

                except queue.Empty:
                    await asyncio.sleep(0.01)

    async def _process_buffer(self, audio_buffer: List[np.ndarray]):
        """Process accumulated audio buffer."""
        if not audio_buffer:
            return

        # Concatenate audio chunks
        audio = np.concatenate(audio_buffer)

        # Skip if too short
        if len(audio) < self._audio_config.sample_rate * 0.5:
            return

        # Transcribe
        result = self.transcribe(audio)

        # Skip empty results
        if not result.text.strip():
            return

        print(f"Heard: {result.text}")

        # Notify callbacks
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(result)
                else:
                    callback(result)
            except Exception as e:
                print(f"Callback error: {e}")

    def stop_listening(self):
        """Stop listening for voice commands."""
        self._is_listening = False
        print("Stopped listening")

    async def transcribe_file(self, audio_path: str) -> TranscriptionResult:
        """
        Transcribe audio from file.

        Args:
            audio_path: Path to audio file

        Returns:
            TranscriptionResult
        """
        if not WHISPER_AVAILABLE:
            raise RuntimeError("Whisper not available")

        if WHISPER_BACKEND == "faster-whisper":
            segments, info = self._model.transcribe(audio_path, language=self.language)
            text = " ".join(s.text for s in segments).strip()
        else:
            result = self._model.transcribe(audio_path, language=self.language)
            text = result["text"].strip()

        return TranscriptionResult(
            text=text,
            confidence=0.9,
            language=self.language,
            duration_seconds=0,
            timestamp=datetime.now(),
            segments=[]
        )


# =============================================================================
# PUSH-TO-TALK MODE
# =============================================================================

class PushToTalkRecorder:
    """
    Push-to-talk style recording for noisy environments.

    Better for outdoor telescope use where continuous listening
    may pick up wind/ambient noise.
    """

    def __init__(self, stt: WhisperSTT, config: Optional[AudioConfig] = None):
        self.stt = stt
        self.config = config or AudioConfig()
        self._recording = False
        self._audio_buffer = []

    async def record_and_transcribe(self, duration: float = 5.0) -> TranscriptionResult:
        """
        Record audio for specified duration and transcribe.

        Args:
            duration: Recording duration in seconds

        Returns:
            TranscriptionResult
        """
        if not SOUNDDEVICE_AVAILABLE:
            raise RuntimeError("sounddevice not available")

        print(f"Recording for {duration} seconds...")

        audio = sd.rec(
            int(duration * self.config.sample_rate),
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype=self.config.dtype
        )
        sd.wait()

        print("Processing...")
        audio = audio.flatten()

        return self.stt.transcribe(audio)


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    print("NIGHTWATCH Voice STT Service Test\n")

    if not WHISPER_AVAILABLE:
        print("Whisper not available.")
        print("Install with: pip install faster-whisper")
        print("Or: pip install openai-whisper")
        exit(1)

    print(f"Backend: {WHISPER_BACKEND}")
    print(f"Audio available: {SOUNDDEVICE_AVAILABLE}")
    print(f"Neural VAD available: {NEURAL_VAD_AVAILABLE}")
    print()

    # Test with a simple transcription
    stt = WhisperSTT(model_size=WhisperModelSize.TINY, device="cpu")
    print(f"VAD backend: {stt._vad.backend}")

    print("Loading model (this may take a moment)...")
    stt.initialize()
    print("Model loaded!")
    print()

    if SOUNDDEVICE_AVAILABLE:
        # Test push-to-talk
        ptt = PushToTalkRecorder(stt)

        async def test_ptt():
            print("Press Enter to start recording (3 seconds)...")
            input()
            result = await ptt.record_and_transcribe(duration=3.0)
            print(f"Transcribed: {result.text}")
            print(f"Is command: {result.is_command}")

        asyncio.run(test_ptt())
    else:
        print("Audio input not available (sounddevice not installed)")
