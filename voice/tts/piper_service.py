"""
NIGHTWATCH Voice TTS Service
Text-to-Speech Output

This module provides text-to-speech capabilities for voice responses,
using Piper TTS for fast local inference on DGX Spark.

Supports:
- Piper TTS (recommended for low latency)
- Coqui TTS (alternative)
- System espeak (fallback)
"""

import asyncio
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Callable
import shutil

# Try to import audio playback
try:
    import sounddevice as sd
    import numpy as np
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

# Try to import piper
try:
    from piper import PiperVoice
    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False


class TTSBackend(Enum):
    """Available TTS backends."""
    PIPER = "piper"
    COQUI = "coqui"
    ESPEAK = "espeak"
    SYSTEM = "system"  # macOS say, Windows SAPI


class VoiceStyle(Enum):
    """Voice styles for different contexts."""
    NORMAL = "normal"
    ALERT = "alert"      # Faster, more urgent
    CALM = "calm"        # Slower, relaxed


@dataclass
class TTSConfig:
    """TTS configuration."""
    backend: TTSBackend = TTSBackend.PIPER
    voice: str = "en_US-lessac-medium"
    rate: float = 1.0      # Speech rate multiplier
    pitch: float = 1.0     # Pitch multiplier
    volume: float = 1.0    # Volume 0.0-1.0
    sample_rate: int = 22050


@dataclass
class SpeechOutput:
    """Generated speech output."""
    audio: bytes
    sample_rate: int
    duration_seconds: float
    text: str


class PiperTTS:
    """
    Piper TTS engine for fast local speech synthesis.

    Piper is optimized for low-latency on-device inference,
    making it ideal for interactive telescope control.
    """

    # Default voice models (download from Piper releases)
    VOICE_MODELS = {
        "en_US-lessac-medium": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/",
        "en_US-ryan-medium": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/",
        "en_GB-alan-medium": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/",
    }

    def __init__(self, config: Optional[TTSConfig] = None):
        """
        Initialize Piper TTS.

        Args:
            config: TTS configuration
        """
        self.config = config or TTSConfig()
        self._voice = None
        self._model_path: Optional[Path] = None
        self._initialized = False

    def initialize(self, model_path: Optional[str] = None):
        """
        Initialize TTS engine with voice model.

        Args:
            model_path: Path to Piper voice model (.onnx file)
        """
        if not PIPER_AVAILABLE:
            raise RuntimeError(
                "Piper not available. Install with: pip install piper-tts"
            )

        if model_path:
            self._model_path = Path(model_path)
        else:
            # Use default model location
            self._model_path = Path(__file__).parent / "models" / f"{self.config.voice}.onnx"

        if not self._model_path.exists():
            print(f"Warning: Voice model not found at {self._model_path}")
            print("Download voices from: https://github.com/rhasspy/piper/releases")
            return

        self._voice = PiperVoice.load(str(self._model_path))
        self._initialized = True
        print(f"Piper TTS initialized with voice: {self.config.voice}")

    def synthesize(self, text: str) -> Optional[SpeechOutput]:
        """
        Synthesize speech from text.

        Args:
            text: Text to speak

        Returns:
            SpeechOutput with audio data
        """
        if not self._initialized or not self._voice:
            return None

        # Generate audio
        audio_data = []
        for audio_bytes in self._voice.synthesize_stream_raw(text):
            audio_data.append(audio_bytes)

        if not audio_data:
            return None

        audio = b"".join(audio_data)

        # Calculate duration
        sample_rate = self._voice.config.sample_rate
        num_samples = len(audio) // 2  # 16-bit audio
        duration = num_samples / sample_rate

        return SpeechOutput(
            audio=audio,
            sample_rate=sample_rate,
            duration_seconds=duration,
            text=text
        )

    async def speak(self, text: str):
        """
        Synthesize and play speech.

        Args:
            text: Text to speak
        """
        output = self.synthesize(text)
        if output:
            await self._play_audio(output)

    async def _play_audio(self, output: SpeechOutput):
        """Play audio output."""
        if not SOUNDDEVICE_AVAILABLE:
            print("Audio playback not available (sounddevice not installed)")
            return

        # Convert bytes to numpy array
        audio = np.frombuffer(output.audio, dtype=np.int16).astype(np.float32)
        audio = audio / 32768.0  # Normalize to -1.0 to 1.0

        # Apply volume
        audio = audio * self.config.volume

        # Play audio
        sd.play(audio, output.sample_rate)
        sd.wait()


class EspeakTTS:
    """
    Espeak TTS fallback using system espeak command.

    Works on Linux systems with espeak installed.
    """

    def __init__(self, config: Optional[TTSConfig] = None):
        self.config = config or TTSConfig()
        self._espeak_available = shutil.which("espeak") is not None

    def initialize(self):
        """Check espeak availability."""
        if not self._espeak_available:
            raise RuntimeError("espeak not found. Install with: apt install espeak")
        print("Espeak TTS initialized")

    async def speak(self, text: str):
        """Speak text using espeak."""
        if not self._espeak_available:
            print(f"Would speak: {text}")
            return

        # Build espeak command
        rate = int(175 * self.config.rate)  # Default espeak rate is 175
        pitch = int(50 * self.config.pitch)  # Default pitch is 50

        cmd = [
            "espeak",
            "-s", str(rate),
            "-p", str(pitch),
            text
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await process.wait()


class SystemTTS:
    """
    System TTS using platform-specific commands.

    - macOS: say command
    - Windows: PowerShell SAPI
    - Linux: espeak fallback
    """

    def __init__(self, config: Optional[TTSConfig] = None):
        self.config = config or TTSConfig()
        import platform
        self._platform = platform.system()

    def initialize(self):
        """Initialize system TTS."""
        print(f"System TTS initialized for {self._platform}")

    async def speak(self, text: str):
        """Speak using system TTS."""
        if self._platform == "Darwin":
            # macOS
            rate = int(200 * self.config.rate)
            cmd = ["say", "-r", str(rate), text]
        elif self._platform == "Windows":
            # Windows PowerShell SAPI
            ps_script = f'Add-Type -AssemblyName System.Speech; $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; $speak.Speak("{text}")'
            cmd = ["powershell", "-Command", ps_script]
        else:
            # Linux - fall back to espeak
            cmd = ["espeak", text]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await process.wait()
        except FileNotFoundError:
            print(f"TTS command not found. Would speak: {text}")


# =============================================================================
# UNIFIED TTS SERVICE
# =============================================================================

class TTSService:
    """
    Unified TTS service with automatic backend selection.

    Tries backends in order: Piper -> Coqui -> espeak -> system
    """

    def __init__(self, config: Optional[TTSConfig] = None):
        self.config = config or TTSConfig()
        self._backend = None
        self._initialized = False

    def initialize(self):
        """Initialize best available TTS backend."""
        # Try Piper first (best quality/speed)
        if PIPER_AVAILABLE:
            try:
                self._backend = PiperTTS(self.config)
                self._backend.initialize()
                if self._backend._initialized:
                    self._initialized = True
                    print(f"Using Piper TTS")
                    return
            except Exception as e:
                print(f"Piper init failed: {e}")

        # Try espeak
        if shutil.which("espeak"):
            try:
                self._backend = EspeakTTS(self.config)
                self._backend.initialize()
                self._initialized = True
                print("Using espeak TTS")
                return
            except Exception as e:
                print(f"Espeak init failed: {e}")

        # Fall back to system TTS
        self._backend = SystemTTS(self.config)
        self._backend.initialize()
        self._initialized = True
        print("Using system TTS")

    async def speak(self, text: str, style: VoiceStyle = VoiceStyle.NORMAL):
        """
        Speak text with optional style.

        Args:
            text: Text to speak
            style: Voice style (affects rate/pitch)
        """
        if not self._initialized:
            self.initialize()

        # Adjust config for style
        original_rate = self.config.rate
        if style == VoiceStyle.ALERT:
            self.config.rate = 1.2
        elif style == VoiceStyle.CALM:
            self.config.rate = 0.9

        try:
            await self._backend.speak(text)
        finally:
            self.config.rate = original_rate

    async def announce(self, text: str):
        """Quick announcement (slightly faster speech)."""
        await self.speak(text, VoiceStyle.ALERT)

    async def respond(self, text: str):
        """Normal conversational response."""
        await self.speak(text, VoiceStyle.NORMAL)

    async def alert(self, text: str):
        """Alert message (fastest, most urgent)."""
        # Prepend attention sound if available
        await self.speak(f"Alert: {text}", VoiceStyle.ALERT)


# =============================================================================
# PRE-RECORDED RESPONSES
# =============================================================================

class ResponseLibrary:
    """
    Library of pre-recorded or pre-synthesized responses
    for faster playback of common phrases.
    """

    COMMON_RESPONSES = {
        "acknowledged": "Acknowledged.",
        "slewing": "Slewing to target.",
        "tracking": "Now tracking.",
        "parked": "Telescope parked.",
        "unsafe": "Conditions are not safe for observation.",
        "ready": "Ready for commands.",
        "not_found": "Object not found in catalog.",
        "below_horizon": "Target is below the horizon.",
    }

    def __init__(self, tts: TTSService, cache_dir: Optional[Path] = None):
        self.tts = tts
        self.cache_dir = cache_dir or Path(__file__).parent / "cache"
        self._cache: dict = {}

    async def preload(self):
        """Pre-synthesize common responses."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        for key, text in self.COMMON_RESPONSES.items():
            # Would cache synthesized audio here
            self._cache[key] = text

    async def play(self, key: str):
        """Play cached response or synthesize on demand."""
        if key in self._cache:
            await self.tts.speak(self._cache[key])
        else:
            await self.tts.speak(f"Unknown response: {key}")


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    print("NIGHTWATCH Voice TTS Service Test\n")

    print(f"Piper available: {PIPER_AVAILABLE}")
    print(f"Sounddevice available: {SOUNDDEVICE_AVAILABLE}")
    print(f"Espeak available: {shutil.which('espeak') is not None}")
    print()

    async def test():
        tts = TTSService()
        tts.initialize()
        print()

        test_phrases = [
            "NIGHTWATCH telescope system ready.",
            "Slewing to Mars at 45 degrees altitude.",
            "Warning: Wind speed exceeds safe limits.",
        ]

        for phrase in test_phrases:
            print(f"Speaking: {phrase}")
            await tts.speak(phrase)
            await asyncio.sleep(0.5)

    asyncio.run(test())
