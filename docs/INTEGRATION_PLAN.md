# NIGHTWATCH External Repository Integration Plan

*Created: January 2026*

This document outlines a comprehensive plan to integrate external repositories identified in `pos/PANEL_RESOURCES.md` into the NIGHTWATCH observatory system.

---

## Executive Summary

The NIGHTWATCH system currently has a well-architected microservices foundation with 13 services, a 44-tool voice pipeline, and comprehensive safety monitoring. This plan describes how to integrate key external projects to achieve:

1. **Optimized Voice Pipeline** — 4x faster STT, standardized service communication
2. **Enhanced Mount Control** — High-precision encoder feedback, extended OnStepX functionality
3. **Cross-Platform Device Layer** — INDI (Linux) and ASCOM Alpaca (network) support
4. **Development Infrastructure** — Hardware simulation for testing without physical equipment

---

## Architecture Integration Points

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         NIGHTWATCH Integration Map                        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  VOICE LAYER                                                              │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐                 │
│  │ faster-     │───→│ Wyoming      │───→│ Piper TTS   │                 │
│  │ whisper     │    │ Protocol     │    │ + VAD       │                 │
│  └─────────────┘    └──────────────┘    └─────────────┘                 │
│        │                   │                   │                         │
│        └───────────────────┼───────────────────┘                         │
│                            ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    ToolRegistry (Extended)                       │    │
│  │   + INDI tools  + Encoder tools  + Extended mount commands      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                            │                                             │
│        ┌───────────────────┼───────────────────┐                         │
│        ▼                   ▼                   ▼                         │
│  DEVICE LAYER                                                            │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐                 │
│  │ pyindi-     │    │ LX200 +      │    │ alpyca      │                 │
│  │ client      │    │ EncoderBridge│    │ (Alpaca)    │                 │
│  └─────────────┘    └──────────────┘    └─────────────┘                 │
│        │                   │                   │                         │
│        ▼                   ▼                   ▼                         │
│  HARDWARE/SIMULATION                                                     │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐                 │
│  │ INDI        │    │ OnStepX +    │    │ Alpaca      │                 │
│  │ Drivers     │    │ Plugins      │    │ Simulators  │                 │
│  └─────────────┘    └──────────────┘    └─────────────┘                 │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Voice Pipeline Optimization

**Goal:** Achieve <500ms end-to-end voice response latency on DGX Spark

### 1.1 Faster-Whisper Integration

**Source:** [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper)

**Current State:** `voice/stt/whisper_service.py` already supports faster-whisper as primary backend.

**Enhancements Required:**

| Task | File | Description |
|------|------|-------------|
| CUDA optimization | `whisper_service.py` | Enable int8 quantization for DGX Spark |
| Batched inference | `whisper_service.py` | Process multiple audio chunks simultaneously |
| Model preloading | `whisper_service.py` | Keep model in GPU memory between invocations |

**Implementation:**

```python
# voice/stt/whisper_service.py - Enhanced initialization
class WhisperSTT:
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cuda",
        compute_type: str = "int8_float16",  # NEW: Optimized for DGX Spark
        cpu_threads: int = 4,
        num_workers: int = 2,  # NEW: Parallel decoding
    ):
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            cpu_threads=cpu_threads,
            num_workers=num_workers,
        )
        # Pre-warm the model
        self._warm_up()

    def _warm_up(self):
        """Pre-load model weights into GPU memory."""
        dummy_audio = np.zeros(16000, dtype=np.float32)
        list(self.model.transcribe(dummy_audio))
```

**Metrics Target:**
- Transcription latency: <200ms for 5-second utterance
- GPU memory: <2GB with int8 quantization

---

### 1.2 Wyoming Protocol Adoption

**Source:** [rhasspy/wyoming](https://github.com/rhasspy/wyoming)

**Purpose:** Standardize voice service communication for modularity and future expansion.

**New Files to Create:**

```
voice/
├── wyoming/
│   ├── __init__.py
│   ├── protocol.py      # Wyoming message types
│   ├── stt_server.py    # STT as Wyoming service
│   └── tts_server.py    # TTS as Wyoming service
```

**Protocol Implementation:**

```python
# voice/wyoming/protocol.py
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import json

class MessageType(Enum):
    AUDIO_CHUNK = "audio-chunk"
    AUDIO_START = "audio-start"
    AUDIO_STOP = "audio-stop"
    TRANSCRIPT = "transcript"
    SYNTHESIZE = "synthesize"

@dataclass
class WyomingMessage:
    type: MessageType
    payload: dict

    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value,
            "data": self.payload
        })

    @classmethod
    def from_json(cls, data: str) -> "WyomingMessage":
        parsed = json.loads(data)
        return cls(
            type=MessageType(parsed["type"]),
            payload=parsed.get("data", {})
        )

# voice/wyoming/stt_server.py
class WyomingSTTServer:
    """Expose WhisperSTT via Wyoming protocol over TCP."""

    def __init__(self, whisper_stt: WhisperSTT, port: int = 10300):
        self.stt = whisper_stt
        self.port = port

    async def handle_client(self, reader, writer):
        audio_buffer = []
        while True:
            data = await reader.readline()
            if not data:
                break
            msg = WyomingMessage.from_json(data.decode())

            if msg.type == MessageType.AUDIO_CHUNK:
                audio_buffer.append(msg.payload["audio"])
            elif msg.type == MessageType.AUDIO_STOP:
                # Process accumulated audio
                audio = np.concatenate(audio_buffer)
                result = self.stt.transcribe(audio)
                response = WyomingMessage(
                    type=MessageType.TRANSCRIPT,
                    payload={"text": result.text, "confidence": result.confidence}
                )
                writer.write(response.to_json().encode() + b"\n")
                await writer.drain()
                audio_buffer = []

    async def start(self):
        server = await asyncio.start_server(
            self.handle_client, "0.0.0.0", self.port
        )
        await server.serve_forever()
```

**Benefits:**
- Decoupled STT/TTS services can run on different machines
- Compatible with Home Assistant ecosystem
- Enables A/B testing different STT backends

---

### 1.3 Voice Activity Detection Enhancement

**Source:** [rhasspy/pymicro-vad](https://github.com/rhasspy/pymicro-vad)

**Current State:** Basic energy-threshold VAD in `whisper_service.py`

**Enhancement:**

```python
# voice/stt/whisper_service.py - Replace VoiceActivityDetector
from pymicro_vad import MicroVAD

class EnhancedVAD:
    """Neural VAD using pymicro-vad for robust speech detection."""

    def __init__(self, threshold: float = 0.5):
        self.vad = MicroVAD()
        self.threshold = threshold

    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """Detect if audio chunk contains speech."""
        # pymicro-vad expects 16kHz, 16-bit PCM
        audio_int16 = (audio_chunk * 32767).astype(np.int16)
        probability = self.vad.process(audio_int16.tobytes())
        return probability > self.threshold

    def reset(self):
        self.vad.reset()
```

---

### 1.4 Piper TTS Enhancements

**Source:** [rhasspy/piper-recording-studio](https://github.com/rhasspy/piper-recording-studio)

**Future Enhancement:** Train custom NIGHTWATCH voice persona.

**Immediate Optimizations:**

```python
# voice/tts/piper_service.py - Performance tuning
class PiperTTS:
    def __init__(
        self,
        model_path: str,
        use_cuda: bool = True,  # NEW: GPU acceleration
        length_scale: float = 1.0,
        noise_scale: float = 0.667,
        noise_w: float = 0.8,
    ):
        self.voice = PiperVoice.load(
            model_path,
            use_cuda=use_cuda,
        )
        self.length_scale = length_scale
        # Pre-synthesize common phrases
        self._cache = self._build_cache()

    def _build_cache(self) -> dict:
        """Pre-synthesize frequently used responses."""
        common_phrases = [
            "Slewing to target",
            "Tracking started",
            "Weather alert",
            "Guiding active",
            "Exposure complete",
            "Park position reached",
        ]
        cache = {}
        for phrase in common_phrases:
            cache[phrase] = self._synthesize_raw(phrase)
        return cache

    def synthesize(self, text: str) -> np.ndarray:
        # Check cache first
        if text in self._cache:
            return self._cache[text]
        return self._synthesize_raw(text)
```

---

## Phase 2: Enhanced Mount Control

**Goal:** Sub-arcsecond positioning accuracy with encoder feedback

### 2.1 EncoderBridge Integration

**Source:** [hjd1964/EncoderBridge](https://github.com/hjd1964/EncoderBridge)

**Purpose:** High-resolution absolute encoder feedback for harmonic drive correction.

**New Service:**

```
services/
├── encoder/
│   ├── __init__.py
│   └── encoder_bridge.py
```

**Implementation:**

```python
# services/encoder/encoder_bridge.py
import serial
import asyncio
from dataclasses import dataclass
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)

@dataclass
class EncoderPosition:
    """High-resolution encoder position data."""
    axis1_counts: int      # RA/Az encoder counts
    axis2_counts: int      # Dec/Alt encoder counts
    axis1_degrees: float   # Computed position
    axis2_degrees: float   # Computed position
    timestamp: float       # Unix timestamp

class EncoderBridge:
    """
    Interface to EncoderBridge for high-resolution position feedback.

    The EncoderBridge provides absolute encoder readings that can be
    used to correct for harmonic drive periodic error and backlash.
    """

    # EncoderBridge serial protocol commands
    CMD_GET_POSITION = "Q"
    CMD_SET_ZERO = "Z"
    CMD_GET_STATUS = "S"

    def __init__(
        self,
        port: str = "/dev/ttyUSB1",
        baudrate: int = 115200,
        counts_per_rev_axis1: int = 16384,  # 14-bit encoder
        counts_per_rev_axis2: int = 16384,
    ):
        self.port = port
        self.baudrate = baudrate
        self.counts_per_rev = (counts_per_rev_axis1, counts_per_rev_axis2)
        self.serial: Optional[serial.Serial] = None
        self._callbacks: list[Callable] = []
        self._running = False

    async def connect(self) -> bool:
        """Connect to EncoderBridge."""
        try:
            self.serial = serial.Serial(
                self.port,
                self.baudrate,
                timeout=1.0
            )
            # Verify connection
            status = await self._send_command(self.CMD_GET_STATUS)
            if status and status.startswith("OK"):
                logger.info(f"EncoderBridge connected on {self.port}")
                return True
            return False
        except serial.SerialException as e:
            logger.error(f"EncoderBridge connection failed: {e}")
            return False

    async def get_position(self) -> Optional[EncoderPosition]:
        """Read current encoder positions."""
        response = await self._send_command(self.CMD_GET_POSITION)
        if not response:
            return None

        # Parse response: "axis1_counts,axis2_counts"
        try:
            parts = response.strip().split(",")
            counts1 = int(parts[0])
            counts2 = int(parts[1])

            return EncoderPosition(
                axis1_counts=counts1,
                axis2_counts=counts2,
                axis1_degrees=(counts1 / self.counts_per_rev[0]) * 360.0,
                axis2_degrees=(counts2 / self.counts_per_rev[1]) * 360.0,
                timestamp=asyncio.get_event_loop().time()
            )
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to parse encoder response: {e}")
            return None

    async def _send_command(self, cmd: str) -> Optional[str]:
        """Send command and read response."""
        if not self.serial:
            return None
        try:
            self.serial.write(f":{cmd}#".encode())
            response = self.serial.read_until(b"#")
            return response.decode().rstrip("#")
        except Exception as e:
            logger.error(f"EncoderBridge command failed: {e}")
            return None

    def register_callback(self, callback: Callable[[EncoderPosition], None]):
        """Register callback for position updates."""
        self._callbacks.append(callback)

    async def start_continuous_read(self, interval: float = 0.1):
        """Start continuous position monitoring."""
        self._running = True
        while self._running:
            position = await self.get_position()
            if position:
                for callback in self._callbacks:
                    callback(position)
            await asyncio.sleep(interval)

    def stop(self):
        """Stop continuous reading."""
        self._running = False
```

### 2.2 Mount Control Enhancement

**Integrate encoder feedback with LX200 client:**

```python
# services/mount_control/lx200.py - Add encoder correction
class LX200Client:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 9999,
        encoder_bridge: Optional[EncoderBridge] = None,  # NEW
    ):
        self.encoder = encoder_bridge
        self._encoder_offset = (0.0, 0.0)  # Calibration offsets

    async def get_corrected_position(self) -> Optional[MountStatus]:
        """Get position with encoder correction applied."""
        mount_pos = await self.get_status()
        if not mount_pos or not self.encoder:
            return mount_pos

        encoder_pos = await self.encoder.get_position()
        if not encoder_pos:
            return mount_pos

        # Apply encoder correction
        # The encoder provides absolute truth; calculate error
        mount_ra_deg = self._ra_to_degrees(mount_pos.ra)
        mount_dec_deg = self._dec_to_degrees(mount_pos.dec)

        error_ra = encoder_pos.axis1_degrees - mount_ra_deg
        error_dec = encoder_pos.axis2_degrees - mount_dec_deg

        # Log periodic error for analysis
        logger.debug(f"Mount error: RA={error_ra:.4f}° Dec={error_dec:.4f}°")

        # Return corrected position
        corrected_status = MountStatus(
            ra=self._degrees_to_ra(encoder_pos.axis1_degrees),
            dec=self._degrees_to_dec(encoder_pos.axis2_degrees),
            is_tracking=mount_pos.is_tracking,
            is_slewing=mount_pos.is_slewing,
            is_parked=mount_pos.is_parked,
            pier_side=mount_pos.pier_side,
        )
        return corrected_status
```

### 2.3 OnStepX Plugin Support

**Source:** [hjd1964/OnStepX-Plugins](https://github.com/hjd1964/OnStepX-Plugins)

**Purpose:** Extended mount commands beyond standard LX200 protocol.

**Extended Commands to Support:**

| Command | Description | Use Case |
|---------|-------------|----------|
| `:GXnn#` | Get extended status | Detailed diagnostics |
| `:SXnn,vv#` | Set extended parameter | Runtime tuning |
| `:$Qn#` | PEC control | Periodic error correction |
| `:rc#` / `:rC#` | Reticle brightness | Visual observation mode |

```python
# services/mount_control/onstepx_extended.py
class OnStepXExtended(LX200Client):
    """Extended OnStepX commands beyond standard LX200."""

    # PEC (Periodic Error Correction) commands
    async def pec_status(self) -> dict:
        """Get PEC recording/playback status."""
        response = await self._send_command(":$QZ#")
        return {
            "recording": response == "R",
            "playing": response == "P",
            "ready": response == "r",
        }

    async def pec_start_playback(self) -> bool:
        """Start PEC playback."""
        return await self._send_command(":$QZ+#") == "1"

    async def pec_stop(self) -> bool:
        """Stop PEC recording/playback."""
        return await self._send_command(":$QZ-#") == "1"

    async def pec_record(self) -> bool:
        """Start PEC recording (one worm period)."""
        return await self._send_command(":$QZR#") == "1"

    # Extended status
    async def get_driver_status(self, axis: int = 1) -> dict:
        """Get TMC stepper driver status."""
        # OnStepX extended command for driver diagnostics
        response = await self._send_command(f":GXU{axis}#")
        if not response:
            return {}
        # Parse TMC5160 status flags
        status = int(response, 16) if response else 0
        return {
            "standstill": bool(status & 0x80000000),
            "open_load_a": bool(status & 0x40000000),
            "open_load_b": bool(status & 0x20000000),
            "overtemperature": bool(status & 0x04000000),
            "stallguard": bool(status & 0x01000000),
        }

    # Tracking rate fine-tuning
    async def set_tracking_offset(self, offset_ppm: float) -> bool:
        """Fine-tune tracking rate in parts-per-million."""
        # Useful for refraction correction
        cmd = f":ST{offset_ppm:+.4f}#"
        return await self._send_command(cmd) == "1"
```

---

## Phase 3: Cross-Platform Device Layer

**Goal:** Support INDI (Linux) and ASCOM Alpaca (network) devices

### 3.1 INDI Client Integration

**Source:** [indilib/pyindi-client](https://github.com/indilib/pyindi-client)

**New Service:**

```
services/
├── indi/
│   ├── __init__.py
│   ├── indi_client.py
│   └── device_adapters.py
```

**Implementation:**

```python
# services/indi/indi_client.py
import PyIndi
from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable
import logging
import threading

logger = logging.getLogger(__name__)

@dataclass
class INDIProperty:
    """Wrapper for INDI property values."""
    name: str
    device: str
    type: str  # "number", "switch", "text", "light", "blob"
    values: Dict[str, Any]
    state: str  # "Idle", "Ok", "Busy", "Alert"

class NightwatchINDIClient(PyIndi.BaseClient):
    """
    INDI client for NIGHTWATCH device communication.

    Provides async-friendly interface to INDI server for controlling
    cameras, filter wheels, focusers, and other astronomy devices.
    """

    def __init__(self, host: str = "localhost", port: int = 7624):
        super().__init__()
        self.host = host
        self.port = port
        self._devices: Dict[str, PyIndi.BaseDevice] = {}
        self._property_callbacks: Dict[str, list[Callable]] = {}
        self._connected = False

    def connect(self) -> bool:
        """Connect to INDI server."""
        self.setServer(self.host, self.port)
        if not self.connectServer():
            logger.error(f"Failed to connect to INDI server at {self.host}:{self.port}")
            return False
        self._connected = True
        logger.info(f"Connected to INDI server at {self.host}:{self.port}")
        return True

    def newDevice(self, d):
        """Callback: New device connected."""
        self._devices[d.getDeviceName()] = d
        logger.info(f"INDI device discovered: {d.getDeviceName()}")

    def newProperty(self, p):
        """Callback: New property available."""
        prop_name = f"{p.getDeviceName()}.{p.getName()}"
        if prop_name in self._property_callbacks:
            for callback in self._property_callbacks[prop_name]:
                callback(self._wrap_property(p))

    def _wrap_property(self, p) -> INDIProperty:
        """Convert INDI property to dataclass."""
        values = {}
        prop_type = "unknown"

        if p.getType() == PyIndi.INDI_NUMBER:
            prop_type = "number"
            for elem in p.getNumber():
                values[elem.name] = elem.value
        elif p.getType() == PyIndi.INDI_SWITCH:
            prop_type = "switch"
            for elem in p.getSwitch():
                values[elem.name] = elem.s == PyIndi.ISS_ON
        elif p.getType() == PyIndi.INDI_TEXT:
            prop_type = "text"
            for elem in p.getText():
                values[elem.name] = elem.text

        state_map = {
            PyIndi.IPS_IDLE: "Idle",
            PyIndi.IPS_OK: "Ok",
            PyIndi.IPS_BUSY: "Busy",
            PyIndi.IPS_ALERT: "Alert",
        }

        return INDIProperty(
            name=p.getName(),
            device=p.getDeviceName(),
            type=prop_type,
            values=values,
            state=state_map.get(p.getState(), "Unknown"),
        )

    def get_device(self, name: str) -> Optional[PyIndi.BaseDevice]:
        """Get device by name."""
        return self._devices.get(name)

    def get_property(self, device: str, property: str) -> Optional[INDIProperty]:
        """Get current property value."""
        dev = self.get_device(device)
        if not dev:
            return None
        prop = dev.getProperty(property)
        if not prop:
            return None
        return self._wrap_property(prop)

    def set_number(self, device: str, property: str, values: Dict[str, float]) -> bool:
        """Set number property values."""
        dev = self.get_device(device)
        if not dev:
            return False
        prop = dev.getNumber(property)
        if not prop:
            return False
        for name, value in values.items():
            for elem in prop:
                if elem.name == name:
                    elem.value = value
        self.sendNewNumber(prop)
        return True

    def set_switch(self, device: str, property: str, switch_name: str) -> bool:
        """Set switch property (turns on specified switch, others off)."""
        dev = self.get_device(device)
        if not dev:
            return False
        prop = dev.getSwitch(property)
        if not prop:
            return False
        # Turn all off, then set requested one
        for elem in prop:
            elem.s = PyIndi.ISS_ON if elem.name == switch_name else PyIndi.ISS_OFF
        self.sendNewSwitch(prop)
        return True

    def register_callback(self, device: str, property: str, callback: Callable):
        """Register callback for property changes."""
        key = f"{device}.{property}"
        if key not in self._property_callbacks:
            self._property_callbacks[key] = []
        self._property_callbacks[key].append(callback)
```

### 3.2 INDI Device Adapters

```python
# services/indi/device_adapters.py
from .indi_client import NightwatchINDIClient, INDIProperty
from typing import Optional
import asyncio

class INDIFilterWheel:
    """INDI filter wheel adapter."""

    def __init__(self, client: NightwatchINDIClient, device_name: str):
        self.client = client
        self.device = device_name
        self.filter_names: list[str] = []

    def set_filter(self, position: int) -> bool:
        """Set filter position (1-indexed)."""
        return self.client.set_number(
            self.device, "FILTER_SLOT", {"FILTER_SLOT_VALUE": position}
        )

    def get_filter(self) -> Optional[int]:
        """Get current filter position."""
        prop = self.client.get_property(self.device, "FILTER_SLOT")
        if prop:
            return int(prop.values.get("FILTER_SLOT_VALUE", 0))
        return None

class INDIFocuser:
    """INDI focuser adapter."""

    def __init__(self, client: NightwatchINDIClient, device_name: str):
        self.client = client
        self.device = device_name

    def move_absolute(self, position: int) -> bool:
        """Move to absolute position."""
        return self.client.set_number(
            self.device, "ABS_FOCUS_POSITION", {"FOCUS_ABSOLUTE_POSITION": position}
        )

    def move_relative(self, steps: int) -> bool:
        """Move relative steps (positive=out, negative=in)."""
        direction = "FOCUS_OUTWARD" if steps > 0 else "FOCUS_INWARD"
        self.client.set_switch(self.device, "FOCUS_MOTION", direction)
        return self.client.set_number(
            self.device, "REL_FOCUS_POSITION", {"FOCUS_RELATIVE_POSITION": abs(steps)}
        )

    def get_position(self) -> Optional[int]:
        """Get current position."""
        prop = self.client.get_property(self.device, "ABS_FOCUS_POSITION")
        if prop:
            return int(prop.values.get("FOCUS_ABSOLUTE_POSITION", 0))
        return None
```

### 3.3 ASCOM Alpaca Integration

**Source:** [ASCOMInitiative/alpyca](https://github.com/ASCOMInitiative/alpyca)

**New Service:**

```
services/
├── alpaca/
│   ├── __init__.py
│   └── alpaca_client.py
```

**Implementation:**

```python
# services/alpaca/alpaca_client.py
from alpaca.telescope import Telescope
from alpaca.camera import Camera
from alpaca.focuser import Focuser
from alpaca.filterwheel import FilterWheel
from alpaca.discovery import search_ipv4
from dataclasses import dataclass
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

@dataclass
class AlpacaDevice:
    """Discovered Alpaca device info."""
    name: str
    device_type: str
    address: str
    port: int
    device_number: int

class AlpacaDiscovery:
    """Discover Alpaca devices on the network."""

    @staticmethod
    def discover(timeout: float = 2.0) -> List[AlpacaDevice]:
        """Search for Alpaca devices via UDP broadcast."""
        devices = []
        try:
            results = search_ipv4(timeout=timeout)
            for result in results:
                for api in result.get("api_versions", []):
                    devices.append(AlpacaDevice(
                        name=result.get("ServerName", "Unknown"),
                        device_type=api.get("DeviceType", "Unknown"),
                        address=result.get("Address", ""),
                        port=result.get("Port", 11111),
                        device_number=api.get("DeviceNumber", 0),
                    ))
        except Exception as e:
            logger.error(f"Alpaca discovery failed: {e}")
        return devices

class AlpacaTelescope:
    """ASCOM Alpaca telescope adapter for NIGHTWATCH."""

    def __init__(self, address: str, port: int = 11111, device_number: int = 0):
        self.telescope = Telescope(address, device_number, port)

    def connect(self) -> bool:
        """Connect to telescope."""
        try:
            self.telescope.Connected = True
            return self.telescope.Connected
        except Exception as e:
            logger.error(f"Alpaca telescope connection failed: {e}")
            return False

    @property
    def ra(self) -> float:
        """Get RA in hours."""
        return self.telescope.RightAscension

    @property
    def dec(self) -> float:
        """Get Dec in degrees."""
        return self.telescope.Declination

    @property
    def is_tracking(self) -> bool:
        return self.telescope.Tracking

    @property
    def is_slewing(self) -> bool:
        return self.telescope.Slewing

    def slew_to_coordinates(self, ra: float, dec: float) -> bool:
        """Slew to RA/Dec (async)."""
        try:
            self.telescope.SlewToCoordinatesAsync(ra, dec)
            return True
        except Exception as e:
            logger.error(f"Slew failed: {e}")
            return False

    def park(self) -> bool:
        """Park the telescope."""
        try:
            self.telescope.Park()
            return True
        except Exception as e:
            logger.error(f"Park failed: {e}")
            return False

    def set_tracking(self, enabled: bool):
        """Enable/disable tracking."""
        self.telescope.Tracking = enabled
```

---

## Phase 4: Development Infrastructure

**Goal:** Enable full system testing without physical hardware

### 4.1 Alpaca Simulator Integration

**Source:** [ASCOMInitiative/ASCOM.Alpaca.Simulators](https://github.com/ASCOMInitiative/ASCOM.Alpaca.Simulators)

**Docker Compose Configuration:**

```yaml
# docker/docker-compose.dev.yml
version: '3.8'

services:
  alpaca-simulators:
    image: ascom/alpaca-simulators:latest
    ports:
      - "11111:11111"
    environment:
      - ASPNETCORE_URLS=http://+:11111
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11111/management/apiversions"]
      interval: 10s
      timeout: 5s
      retries: 3

  indi-server:
    image: indilib/indi-full:latest
    ports:
      - "7624:7624"
    command: ["indiserver", "indi_simulator_telescope", "indi_simulator_ccd", "indi_simulator_focus"]
```

### 4.2 Integration Test Framework

```python
# tests/integration/test_device_layer.py
import pytest
import asyncio
from services.alpaca.alpaca_client import AlpacaTelescope, AlpacaDiscovery
from services.indi.indi_client import NightwatchINDIClient

@pytest.fixture
async def alpaca_telescope():
    """Fixture for Alpaca simulator telescope."""
    telescope = AlpacaTelescope("localhost", 11111, 0)
    telescope.connect()
    yield telescope
    telescope.telescope.Connected = False

@pytest.fixture
async def indi_client():
    """Fixture for INDI simulator client."""
    client = NightwatchINDIClient("localhost", 7624)
    client.connect()
    await asyncio.sleep(1)  # Wait for device discovery
    yield client

class TestAlpacaIntegration:
    async def test_slew_to_target(self, alpaca_telescope):
        """Test slewing to coordinates."""
        result = alpaca_telescope.slew_to_coordinates(12.0, 45.0)
        assert result is True

        # Wait for slew to complete
        while alpaca_telescope.is_slewing:
            await asyncio.sleep(0.5)

        assert abs(alpaca_telescope.ra - 12.0) < 0.01
        assert abs(alpaca_telescope.dec - 45.0) < 0.01

    async def test_tracking_control(self, alpaca_telescope):
        """Test tracking enable/disable."""
        alpaca_telescope.set_tracking(True)
        assert alpaca_telescope.is_tracking is True

        alpaca_telescope.set_tracking(False)
        assert alpaca_telescope.is_tracking is False

class TestINDIIntegration:
    async def test_device_discovery(self, indi_client):
        """Test INDI device discovery."""
        devices = list(indi_client._devices.keys())
        assert len(devices) > 0
        assert "Telescope Simulator" in devices

    async def test_focuser_movement(self, indi_client):
        """Test INDI focuser control."""
        from services.indi.device_adapters import INDIFocuser
        focuser = INDIFocuser(indi_client, "Focuser Simulator")

        result = focuser.move_absolute(5000)
        assert result is True

        await asyncio.sleep(2)  # Wait for movement
        position = focuser.get_position()
        assert abs(position - 5000) < 100
```

---

## Phase 5: Tool Registry Extension

**Goal:** Expose all new capabilities through voice interface

### 5.1 New Tool Definitions

```python
# voice/tools/telescope_tools.py - Extensions

# Encoder tools
Tool(
    name="get_encoder_position",
    description="Get high-resolution encoder position for both axes",
    category=ToolCategory.MOUNT,
    parameters=[],
),
Tool(
    name="get_pointing_correction",
    description="Get the current mount pointing error based on encoder feedback",
    category=ToolCategory.MOUNT,
    parameters=[],
),

# PEC tools
Tool(
    name="pec_status",
    description="Get periodic error correction status",
    category=ToolCategory.MOUNT,
    parameters=[],
),
Tool(
    name="pec_start",
    description="Start periodic error correction playback",
    category=ToolCategory.MOUNT,
    parameters=[],
),
Tool(
    name="pec_record",
    description="Start recording periodic error for one worm cycle",
    category=ToolCategory.MOUNT,
    parameters=[],
),

# INDI tools
Tool(
    name="indi_list_devices",
    description="List all connected INDI devices",
    category=ToolCategory.CAMERA,
    parameters=[],
),
Tool(
    name="indi_set_filter",
    description="Change filter wheel position",
    category=ToolCategory.CAMERA,
    parameters=[
        ToolParameter(
            name="filter_name",
            type="string",
            description="Filter name (L, R, G, B, Ha, OIII, SII) or position number",
            required=True,
        ),
    ],
),

# Voice pipeline tools
Tool(
    name="set_voice_style",
    description="Change voice response style",
    category=ToolCategory.SESSION,
    parameters=[
        ToolParameter(
            name="style",
            type="string",
            description="Voice style: normal, alert, calm, or technical",
            required=True,
        ),
    ],
),
```

### 5.2 Handler Registration

```python
# voice/tools/telescope_tools.py - Extended handlers
def create_extended_handlers(
    mount_client: Optional[LX200Client] = None,
    encoder_bridge: Optional[EncoderBridge] = None,
    onstepx_extended: Optional[OnStepXExtended] = None,
    indi_client: Optional[NightwatchINDIClient] = None,
    # ... existing handlers ...
) -> dict:
    """Create handlers including new integrations."""

    handlers = create_default_handlers(mount_client, ...)

    # Encoder handlers
    if encoder_bridge:
        async def get_encoder_position() -> str:
            pos = await encoder_bridge.get_position()
            if not pos:
                return "Encoder bridge not responding"
            return f"Encoder position: Axis1={pos.axis1_degrees:.4f}° Axis2={pos.axis2_degrees:.4f}°"

        handlers["get_encoder_position"] = get_encoder_position

    # PEC handlers
    if onstepx_extended:
        async def pec_status() -> str:
            status = await onstepx_extended.pec_status()
            if status["playing"]:
                return "PEC is actively correcting"
            elif status["recording"]:
                return "PEC is recording"
            elif status["ready"]:
                return "PEC is trained and ready"
            return "PEC is not configured"

        async def pec_start() -> str:
            if await onstepx_extended.pec_start_playback():
                return "PEC playback started"
            return "Failed to start PEC"

        handlers["pec_status"] = pec_status
        handlers["pec_start"] = pec_start

    # INDI handlers
    if indi_client:
        async def indi_list_devices() -> str:
            devices = list(indi_client._devices.keys())
            if not devices:
                return "No INDI devices connected"
            return f"Connected devices: {', '.join(devices)}"

        handlers["indi_list_devices"] = indi_list_devices

    return handlers
```

---

## Implementation Timeline

### Week 1-2: Voice Pipeline Optimization
- [x] Enable int8 quantization in faster-whisper
- [x] Implement model pre-warming
- [x] Integrate pymicro-vad for robust speech detection
- [x] Add TTS phrase caching

### Week 3-4: Mount Control Enhancement
- [x] Implement EncoderBridge service
- [x] Create OnStepXExtended class
- [x] Add PEC control commands
- [x] Integrate encoder feedback into mount status

### Week 5-6: Device Layer
- [x] Implement INDI client wrapper
- [x] Create device adapters (focuser, filter wheel)
- [x] Implement Alpaca client
- [x] Add device discovery

### Week 7-8: Testing Infrastructure
- [x] Configure Docker compose for simulators
- [x] Write integration tests
- [x] Create CI/CD pipeline for automated testing

### Week 9-10: Tool Registry & Documentation
- [x] Add new tool definitions
- [x] Implement handlers
- [x] Update system prompts
- [x] Document voice commands

---

## Dependencies Summary

### Python Packages (add to requirements.txt)

```txt
# Voice Pipeline
faster-whisper>=0.10.0
pymicro-vad>=1.0.0
piper-tts>=1.2.0

# Device Communication
pyindi-client>=2.0.0
alpyca>=2.0.0

# Testing
pytest-asyncio>=0.21.0
docker>=6.0.0
```

### System Requirements

- **INDI Server:** `apt install indi-bin`
- **Alpaca Simulators:** Docker or .NET 6+ runtime
- **CUDA:** 12.x for faster-whisper GPU acceleration

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| INDI driver compatibility | Use simulator for development; test with specific hardware early |
| Encoder calibration drift | Implement periodic sync with plate solving |
| Wyoming protocol changes | Pin to specific version; monitor upstream |
| TTS latency on cold start | Pre-warm models during startup sequence |
| Network device timeout | Implement reconnection logic with exponential backoff |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Voice response latency | <500ms | End-to-end timing |
| Pointing accuracy | <2 arcsec RMS | Plate solve verification |
| Device discovery time | <5s | Startup benchmark |
| Test coverage | >80% | pytest --cov |
| PEC improvement | >50% reduction | Guide RMS before/after |

---

## Integration Status

**Status: COMPLETE** ✓

All planned integration phases have been successfully implemented as of January 2026.

### Completed Components

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Voice Pipeline Optimization | ✓ Complete |
| Phase 2 | Enhanced Mount Control | ✓ Complete |
| Phase 3 | Cross-Platform Device Layer | ✓ Complete |
| Phase 4 | Development Infrastructure | ✓ Complete |
| Phase 5 | Tool Registry Extension | ✓ Complete |

### Next Steps

1. **Validation:** Run full integration test suite against hardware simulators
2. **Benchmarking:** Measure actual latency metrics against success criteria
3. **Hardware Testing:** Deploy to physical telescope and validate encoder feedback
4. **Documentation:** Update user guide with new INDI/Alpaca voice commands

---

## v0.1 Release Status (Step 605)

**Version:** 0.1.0
**Target Completion:** 74% (490/663 steps)
**Last Updated:** January 2026

### v0.1 Feature Summary

| Feature Area | Status | Key Components |
|--------------|--------|----------------|
| Voice Pipeline | ✓ Complete | faster-whisper STT, Piper TTS, Wyoming protocol |
| Mount Control | ✓ Complete | LX200 client, OnStepX extended commands, encoder bridge |
| Device Layer | ✓ Complete | INDI adapters, Alpaca client, unified device abstraction |
| Safety System | ✓ Complete | Safety monitor, interlock, emergency response, watchdog |
| Docker Infrastructure | ✓ Complete | Dev/test/prod compose files, healthchecks, CI integration |
| Tool Handlers | 90% Complete | 44+ voice tools, INDI/Alpaca handlers, power control |
| Testing | 80% Complete | Unit tests, integration tests, hardware-in-loop simulation |
| Documentation | 75% Complete | Installation, configuration, voice commands, API reference |

### Docker Infrastructure (v0.1)

| File | Purpose | Status |
|------|---------|--------|
| `docker-compose.dev.yml` | Development with full simulators | ✓ Ready |
| `docker-compose.test.yml` | Lightweight CI testing | ✓ Ready |
| `docker-compose.prod.yml` | Production deployment template | ✓ Ready |

### v0.1 Known Limitations

1. Camera service requires ZWO ASI SDK (not included, platform-specific)
2. Astrometry solving requires local installation of astrometry.net or ASTAP
3. PHD2 guiding requires separate PHD2 installation
4. Weather station requires physical Ecowitt hardware or simulator

---

*Document maintained by NIGHTWATCH development team. See `pos/PANEL_RESOURCES.md` for source repository links.*
*Last updated: January 2026 - v0.1 release preparation*
