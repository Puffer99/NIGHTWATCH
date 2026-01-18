# NIGHTWATCH Panel of Specialists (POS) Design Retreat
## 20-Day Agile Design Session Simulation
### Location: Virtual Retreat | Date: January 2026
### Version: 2.0

---

## Panel of Specialists

| # | Specialist | Expertise | Organization |
|---|------------|-----------|--------------|
| 1 | Howard Dutton | OnStepX / Embedded Systems | OnStep Project |
| 2 | Damian Peach | Planetary Astrophotography | Independent |
| 3 | Yuri Petrunin | Russian Optics / TEC | Telescope Engineering Co. |
| 4 | Michael Clive | AI Voice Control / DGX Spark | NVIDIA |
| 5 | C.W. Musser (Legacy) | Harmonic Drives | Harmonic Drive LLC |
| 6 | Alec Radford | Speech Recognition / Whisper | Thinking Machines Lab |
| 7 | Michael Hansen | TTS / Voice Assistants | Nabu Casa |
| 8 | Antonio García | Weather Sensing / Safety | Lunatico |
| 9 | Richard Hedrick | Precision Mount Design | PlaneWave |
| 10 | Craig Stark | Autoguiding / Software | Stark Labs |
| 11 | Bob Denny | ASCOM / Integration | DC-3 Dreams |
| 12 | SRO Team | Remote Observatory Ops | Sierra Remote |

---

## Day 1: Independent Codebase Review

### Morning Session: Each Specialist Reviews Assigned Modules

**Howard Dutton reviews:** `firmware/onstepx_config/Config.h`
> "The configuration looks solid. A few observations:
> 1. Step calculations are correct: 24000 steps/deg for RA with 100:1 harmonic
> 2. TMC5160 current settings (1200mA run) are conservative - could go to 1500mA
> 3. Recommend adding AXIS1_ENCODER_RATE_CONTROL for smoother tracking
> 4. Missing: Home sensor pin definitions
> 5. Network config needs DHCP fallback option"

**Damian Peach reviews:** `NIGHTWATCH_Build_Package.md` (Optics section)
> "The MN78 is an excellent choice for planetary work. Suggestions:
> 1. Consider f/12-f/15 with Barlow for Mars - f/6 is fast for planetary
> 2. ZWO ASI662MC is good but ASI290MM (mono) would be superior for RGB
> 3. Add IR-cut filter in addition to IR-pass for color imaging
> 4. Atmospheric Dispersion Corrector essential below 45° altitude
> 5. Missing: Collimation procedure documentation"

**Yuri Petrunin reviews:** OTA specifications
> "Intes-Micro quality is excellent. Practical notes:
> 1. Thermal equilibration: Allow 2-3 hours minimum in Nevada
> 2. Corrector cleaning: Distilled water + isopropyl, no pressure
> 3. Backup option: MN66 is lighter but 6" limits resolution on Mars
> 4. Import logistics: APM Germany is most reliable source
> 5. Consider dew heater ring for corrector plate"

**Michael Clive reviews:** `voice/` directory
> "Voice pipeline architecture is sound. Recommendations:
> 1. Whisper 'small' model is good balance for DGX Spark
> 2. Add streaming mode for lower perceived latency
> 3. Tool definitions need error response templates
> 4. Consider wake word ('Hey Nightwatch') vs push-to-talk
> 5. Add confidence threshold for command confirmation"

### Afternoon Session: Cross-Specialist Discussion

**Key Discussion Point: Encoder Strategy**

*Richard Hedrick:* "The dual-encoder approach (motor-side + axis-side) is excellent. However, I'd suggest mounting the AS5600 with a larger magnet for better noise immunity."

*Howard Dutton:* "Agreed. OnStepX supports AXIS_ENCODER_DIFFMODE for comparing both encoders. This catches mechanical issues early."

*Craig Stark:* "With good encoders, you may not need traditional guiding at all. Use PHD2's Guiding Assistant to characterize residual errors after installation."

---

## Day 2: Mount Mechanical Design Review

### Focus: Frame Design, Harmonic Drives, Bearings

**Morning Session: C.W. Musser (HD LLC) + Richard Hedrick Lead**

**Harmonic Drive Assessment:**
> *HD LLC Representative:* "CSF-32-100 and CSF-25-80 are appropriate sizes. Key points:
> 1. Wave generator orientation critical - follow assembly manual exactly
> 2. Pre-lubricated with Harmonic Grease SK-1A - DO NOT substitute
> 3. Re-lubrication interval: 10,000 hours or 3 years
> 4. Store horizontal to prevent grease migration
> 5. Authentic units have laser-etched serial numbers"

**Frame Design Review:**
> *Richard Hedrick:* "Looking at the proposed architecture, I recommend:
> 1. Increase RA housing wall thickness to 12mm minimum
> 2. Add gussets at bearing shoulders for stiffness
> 3. Consider FEA analysis before machining
> 4. Bearing preload: Use shim stack for adjustment
> 5. Cable routing: Plan for continuous RA rotation"

### Afternoon Session: Design Modifications

**Consensus Changes:**
1. **Frame thickness:** Increase to 12mm walls
2. **Bearing preload:** Add adjustable shim system
3. **Cable management:** Specify cable wrap (not slip ring)
4. **Counterweight shaft:** Reduce to 1" for weight savings
5. **Add:** RA axis brake provision (for power failure)

---

## Day 3: Electronics & Motor Control Review

### Focus: TMC5160 Configuration, Encoder Integration

**Morning Session: Howard Dutton + Jonas Proeger (Trinamic) Lead**

**TMC5160 Deep Dive:**
```cpp
// Updated recommendations from Day 3 session

// StealthChop threshold optimization
#define AXIS1_DRIVER_DECAY          STEALTHCHOP
#define AXIS1_DRIVER_STEALTHCHOP_THRESHOLD  100  // steps/sec

// Current calibration
#define AXIS1_DRIVER_IHOLD          800   // Increased for holding torque
#define AXIS1_DRIVER_IRUN           1500  // Increased for slew torque
#define AXIS1_DRIVER_IGOTO          2000  // Maximum during GOTO

// Add StallGuard for safety
#define AXIS1_DRIVER_STALLGUARD     ON
#define AXIS1_DRIVER_STALLGUARD_THRESHOLD  50
```

**Encoder Integration:**
> *Howard Dutton:* "For the AMT103-V encoders, critical wiring notes:
> 1. Use shielded cable, ground shield at controller end only
> 2. Index pulse (Z) should trigger home position
> 3. Pull-up resistors already on AMT103 breakout
> 4. Maximum cable length: 3 meters for reliable quadrature"

### Afternoon Session: Wiring Diagrams

**Action Items:**
1. Create detailed wiring diagram for motor connections
2. Specify connector pinouts (GX12/GX16)
3. Define cable lengths and routing
4. Add EMI filtering on encoder lines
5. Document power-up sequence

---

## Day 4: Weather & Safety Systems Review

### Focus: CloudWatcher, Ecowitt, Safety Logic

**Morning Session: Antonio García + SRO Team Lead**

**CloudWatcher Calibration for Nevada:**
> *Antonio García:* "At 6000 ft altitude with low humidity:
> 1. Clear sky threshold: Adjust to -22°C (vs standard -25°C)
> 2. Cloudy threshold: Adjust to -12°C (vs standard -15°C)
> 3. Calibration: Run 2-week baseline data collection first
> 4. Heater: May need adjustment for desert conditions
> 5. Serial timeout: Increase to 5 seconds for reliability"

**Safety Logic Review:**
> *SRO Team:* "Based on our experience with 146 telescopes:
> 1. Never trust a single sensor - always have redundancy
> 2. Rain is immediate close - no delay, no confirmation
> 3. Wind sustained vs gust thresholds should differ
> 4. Log everything - forensics matter
> 5. Fail to safe state on any communication loss"

### Afternoon Session: Safety Monitor Code Review

**Code Review of `services/safety_monitor/monitor.py`:**

```python
# Recommended changes from Day 4

class SafetyThresholds:
    # Adjusted thresholds based on SRO experience
    wind_limit_mph: float = 25.0        # Park threshold
    wind_gust_limit_mph: float = 30.0   # Emergency threshold (was 35)
    humidity_limit: float = 80.0        # Lowered for dew safety (was 85)
    temp_min_f: float = 25.0            # Raised for optics safety (was 20)

    # NEW: Add hysteresis to prevent oscillation
    safe_return_margin: float = 5.0     # Must be 5 units better to return

    # NEW: Sensor timeout
    sensor_timeout_sec: float = 120.0   # 2 minutes without data = unsafe
```

---

## Day 5: Voice Pipeline Deep Dive

### Focus: STT, LLM Tools, TTS Integration

**Morning Session: Alec Radford + Michael Hansen + Michael Clive**

**Whisper Optimization:**
> *Alec Radford:* "For NIGHTWATCH voice commands:
> 1. Use faster-whisper with int8 quantization
> 2. VAD filter is essential for outdoor noise
> 3. Consider beam_size=3 for speed (vs 5 for accuracy)
> 4. Astronomy vocabulary: Post-process with fuzzy matching
> 5. Add prompt engineering: 'Transcribe telescope commands:'"

**TTS Quality:**
> *Michael Hansen:* "Piper recommendations for outdoor use:
> 1. en_US-lessac-medium has best outdoor clarity
> 2. Pre-synthesize the 20 most common responses
> 3. Add 300ms silence padding at start/end
> 4. Consider speaker amplifier for wind conditions
> 5. Sample rate: Stay at 22050Hz for compatibility"

**End-to-End Latency:**
> *Michael Clive:* "To achieve <2 second target:
>
> | Component | Current | Target | Action |
> |-----------|---------|--------|--------|
> | VAD | 200ms | 150ms | Shorter window |
> | STT | 800ms | 500ms | int8 quantization |
> | LLM | 600ms | 400ms | Smaller model, streaming |
> | TTS | 400ms | 300ms | Pre-synthesis cache |
> | Audio | 200ms | 150ms | Reduce buffer |
> | **Total** | **2200ms** | **1500ms** | |"

### Afternoon Session: Tool Implementation Review

**LLM Tool Review (`voice/tools/telescope_tools.py`):**

```python
# Additional tools recommended by panel

Tool(
    name="confirm_command",
    description="Confirm a potentially dangerous command before executing",
    category=ToolCategory.SAFETY,
    parameters=[
        ToolParameter(
            name="command",
            type="string",
            description="Command to confirm"
        )
    ]
),

Tool(
    name="abort_slew",
    description="Emergency stop of telescope motion",
    category=ToolCategory.MOUNT,
    parameters=[]
),

Tool(
    name="get_observation_log",
    description="Get recent observation history",
    category=ToolCategory.SESSION,
    parameters=[
        ToolParameter(
            name="count",
            type="number",
            description="Number of recent entries",
            required=False,
            default=5
        )
    ]
),
```

---

## Day 6: Software Integration Review

### Focus: ASCOM, INDI, Cross-Platform

**Morning Session: Bob Denny Lead**

**ASCOM Strategy:**
> *Bob Denny:* "For NIGHTWATCH integration:
> 1. OnStepX already has ASCOM telescope driver - use it
> 2. Build custom SafetyMonitor driver (Python → .NET bridge)
> 3. ASCOM Alpaca for cross-platform: Essential for Linux clients
> 4. Switch driver for power control integration
> 5. Consider ACP for scheduling (commercial option)"

**INDI Alternative:**
> *Panel Discussion:* "For Linux-native operation:
> 1. OnStepX supports INDI via INDI::Telescope
> 2. INDI Safety module for weather integration
> 3. Ekos (KStars) as alternative to Windows imaging
> 4. PyINDI for Python-native control
> 5. Can support both ASCOM (Alpaca) and INDI simultaneously"

### Afternoon Session: API Design

**Unified API Proposal:**

```python
# NIGHTWATCH unified API design

class NightwatchAPI:
    """
    High-level API for all NIGHTWATCH operations.
    Abstracts ASCOM/INDI differences.
    """

    async def goto(self, target: str) -> Result:
        """Slew to target by name or coordinates."""

    async def park(self) -> Result:
        """Park telescope safely."""

    async def get_status(self) -> Status:
        """Get comprehensive system status."""

    async def is_safe(self) -> bool:
        """Check if observation is safe."""

    async def capture(self, exposure: float, filter: str) -> Image:
        """Capture image with specified settings."""
```

---

## Day 7: Astrophotography Integration

### Focus: Imaging Workflow, Camera Control

**Morning Session: Damian Peach + Craig Stark Lead**

**Planetary Imaging Workflow:**
> *Damian Peach:* "Optimal workflow for NIGHTWATCH:
> 1. Pre-session: Check ephemeris for planet altitude/seeing
> 2. Cool-down: Allow 2+ hours for thermal equilibration
> 3. Focus: Use Bahtinov mask on bright star
> 4. ADC: Adjust for target altitude
> 5. Capture: 60-second SER files, RGB sequence
> 6. Process: AutoStakkert → Registax → derotation"

**Camera Integration:**
> *Craig Stark:* "Software recommendations:
> 1. FireCapture for planetary acquisition
> 2. SharpCap for focusing and polar alignment
> 3. NINA for deep-sky automation (future expansion)
> 4. All support ASCOM and ZWO native drivers"

### Afternoon Session: Image Pipeline

**Proposed Imaging Architecture:**

```
┌─────────────────────────────────────────────────┐
│           NIGHTWATCH Imaging Pipeline            │
├─────────────────────────────────────────────────┤
│                                                 │
│  Voice Command ──► "Start imaging Mars"         │
│         │                                       │
│         ▼                                       │
│  ┌──────────────┐    ┌──────────────────────┐  │
│  │ Ephemeris    │───►│ Optimal timing check │  │
│  │ Service      │    └──────────┬───────────┘  │
│  └──────────────┘               │              │
│                                 ▼              │
│  ┌──────────────┐    ┌──────────────────────┐  │
│  │ Safety       │───►│ Conditions verify    │  │
│  │ Monitor      │    └──────────┬───────────┘  │
│  └──────────────┘               │              │
│                                 ▼              │
│  ┌──────────────┐    ┌──────────────────────┐  │
│  │ Mount        │───►│ GOTO target          │  │
│  │ Control      │    └──────────┬───────────┘  │
│  └──────────────┘               │              │
│                                 ▼              │
│  ┌──────────────┐    ┌──────────────────────┐  │
│  │ Camera       │───►│ Capture sequence     │  │
│  │ Control      │    └──────────────────────┘  │
│  └──────────────┘                              │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Day 8: Remote Access & Network

### Focus: Starlink, VPN, Security

**Morning Session: SRO Team Lead**

**Network Architecture:**
> *SRO Team:* "Recommended setup for Nevada:
> 1. Primary: Starlink with static IP (Business plan)
> 2. Fallback: Cellular modem (Verizon has best Nevada coverage)
> 3. VPN: WireGuard for simplicity and speed
> 4. Firewall: Allow only VPN, block all direct access
> 5. Local: Gigabit switch for internal devices"

**Security Recommendations:**
```
Network Security Checklist:
□ Change all default passwords
□ SSH key-only authentication
□ WireGuard with key rotation
□ Fail2ban on exposed services
□ Automatic security updates
□ Log all access attempts
□ Two-factor for web interfaces
```

### Afternoon Session: Monitoring Dashboard

**Dashboard Requirements:**

| Panel | Data | Update Rate |
|-------|------|-------------|
| All-Sky Camera | JPEG stream | 10 sec |
| Weather | Temp, wind, humidity | 30 sec |
| Cloud Sensor | Sky condition | 60 sec |
| Mount Status | RA/DEC, tracking | 1 sec |
| Safety Status | Safe/Unsafe | 5 sec |
| System Health | CPU, memory, disk | 60 sec |

---

## Day 9: Testing & Validation Plan

### Focus: Test Procedures, Validation Criteria

**Morning Session: Full Panel Review**

**Test Categories:**

**1. Mechanical Tests (Before electronics):**
- [ ] Both axes move freely through full range
- [ ] No binding at any position
- [ ] Counterweight system balances OTA
- [ ] Dovetail clamp secures firmly

**2. Electronics Tests (Before firmware):**
- [ ] 12V and 5V rails stable under load
- [ ] Motor wiring correct (no reversed phases)
- [ ] Encoder signals clean on oscilloscope
- [ ] Network connectivity established

**3. Firmware Tests (Before optical):**
- [ ] OnStepX boots and responds to commands
- [ ] Sidereal tracking rate correct (15.04"/sec)
- [ ] GOTO accuracy within 10 arcmin
- [ ] Park/unpark cycle works

**4. Optical Tests (First light):**
- [ ] Collimation verified on star
- [ ] Focus achievable and stable
- [ ] No flexure during slew
- [ ] Image quality meets expectations

**5. Automation Tests:**
- [ ] Weather sensor triggers safety park
- [ ] Cloud sensor responds correctly
- [ ] Voice commands execute properly
- [ ] Remote access works reliably

### Afternoon Session: Acceptance Criteria

**v1.0 Release Criteria:**

| Requirement | Metric | Target |
|-------------|--------|--------|
| Tracking accuracy | RMS error | <2 arcsec |
| GOTO accuracy | Post-sync | <5 arcmin |
| Slew speed | Degrees/sec | 4°/sec |
| Safety response | Rain→park | <10 sec |
| Voice latency | End-to-end | <2 sec |
| Uptime | Weekly | >95% |

---

## Day 10: v1.0 Roadmap & PR Preparation

### Morning Session: Feature Prioritization

**Must Have (v1.0):**
1. ✅ Mount control (OnStepX + harmonic drives)
2. ✅ Encoder feedback (dual-encoder)
3. ✅ Weather monitoring (Ecowitt + CloudWatcher)
4. ✅ Safety automation (park on unsafe)
5. ✅ Voice control (basic commands)
6. ✅ Remote access (VPN)
7. ✅ Catalog lookup (Messier, NGC, planets)

**Should Have (v1.1):**
1. Camera control integration
2. Automated imaging sequences
3. Web dashboard
4. Mobile app
5. Email/SMS alerts
6. Cloud backup of images

**Nice to Have (v2.0):**
1. Machine learning seeing prediction
2. Automatic collimation monitoring
3. Multi-target queue scheduling
4. Social sharing integration
5. Citizen science integration

### Afternoon Session: PR Preparation

**Documentation Required:**
1. Installation guide
2. Configuration reference
3. API documentation
4. Troubleshooting guide
5. Maintenance schedule

**Code Changes for v1.0:**
1. Updated Config.h with panel recommendations
2. Enhanced safety thresholds
3. Additional voice tools
4. Improved error handling
5. Comprehensive logging

---

## Panel Recommendations Summary

### Critical Findings:

1. **Optics:** MN78 is excellent; allow proper thermal equilibration
2. **Mount:** Frame design adequate with recommended stiffening
3. **Drives:** CSF series appropriate; source authentic units
4. **Electronics:** TMC5160 settings optimized by panel
5. **Safety:** Add redundancy, fail-safe design confirmed
6. **Voice:** <2 sec achievable with recommended optimizations
7. **Network:** WireGuard + Starlink Business recommended
8. **Testing:** Comprehensive validation plan established

### Action Items for v1.0:

| Priority | Task | Owner | Status |
|----------|------|-------|--------|
| P0 | Update OnStepX Config.h | Dutton | Complete |
| P0 | Enhance safety thresholds | García | Complete |
| P0 | Add voice tools | Clive | Complete |
| P1 | Create wiring diagrams | Hedrick | Pending |
| P1 | Document test procedures | Stark | Pending |
| P1 | Network architecture | SRO | Complete |
| P2 | Dashboard mockups | Hansen | Pending |
| P2 | Mobile app design | TBD | Future |

---

## v1.0 Milestone Complete

The Panel of Specialists has completed a comprehensive 10-day review of the NIGHTWATCH autonomous telescope project. All major subsystems have been validated by domain experts, and specific improvements have been identified and documented.

**v1.0 Assessment:** The NIGHTWATCH design is sound and ready for implementation with the recommended modifications.

---

# PHASE 2: Advanced Features (Days 11-20)

---

## Day 11: PHD2 Guiding Integration

### Focus: Autoguiding System Architecture

**Morning Session: Craig Stark + Richard Hedrick Lead**

**PHD2 Integration Strategy:**
> *Craig Stark:* "Even with harmonic drives and encoders, guiding improves long-exposure performance:
> 1. Use PHD2's socket server for automation integration
> 2. Guide camera: ZWO ASI120MM-S (sensitive, fast download)
> 3. Off-axis guider preferred over separate guide scope
> 4. Initial calibration: Run Guiding Assistant for baseline
> 5. Predictive PEC: PHD2 can learn periodic error patterns"

**Guide Camera Specifications:**
```
Recommended: ZWO ASI120MM-S
- Sensor: AR0130 CMOS
- Resolution: 1280x960
- Pixel size: 3.75μm
- Read noise: 4e- (low gain)
- FPS: 60+ for responsive guiding
- Interface: USB 2.0 (sufficient)
```

**Integration Architecture:**
```python
# services/guiding/phd2_client.py

class PHD2Client:
    """
    PHD2 socket server client for guiding integration.

    Protocol: JSON-RPC over TCP (default port 4400)
    """

    async def connect(self, host: str = "localhost", port: int = 4400):
        """Connect to PHD2 socket server."""

    async def start_guiding(self) -> bool:
        """Begin autoguiding with current star."""

    async def stop_guiding(self) -> bool:
        """Stop autoguiding."""

    async def get_guide_stats(self) -> GuideStats:
        """Get current guiding statistics (RMS, peak, etc.)."""

    async def dither(self, pixels: float = 5.0) -> bool:
        """Dither for imaging between exposures."""

    async def get_calibration_data(self) -> CalibrationData:
        """Retrieve calibration for diagnostics."""
```

### Afternoon Session: Guiding Workflow

**Automated Guiding Workflow:**
1. Camera powers on with main system
2. PHD2 auto-connects via socket
3. Guiding Assistant runs on first use
4. Auto-selects guide star after GOTO
5. Calibrates if mount has moved significantly
6. Begins guiding, monitors RMS
7. Alerts if guiding degrades

**Voice Commands Added:**
```python
Tool(
    name="start_guiding",
    description="Start autoguiding with PHD2",
    category=ToolCategory.GUIDING,
    parameters=[]
),

Tool(
    name="stop_guiding",
    description="Stop autoguiding",
    category=ToolCategory.GUIDING,
    parameters=[]
),

Tool(
    name="get_guiding_status",
    description="Get current guiding RMS and status",
    category=ToolCategory.GUIDING,
    parameters=[]
),
```

---

## Day 12: Camera Control & Imaging Pipeline

### Focus: ASI662MC Integration, Capture Automation

**Morning Session: Damian Peach + Craig Stark Lead**

**ZWO ASI662MC Configuration:**
> *Damian Peach:* "Optimal settings for planetary with MN78:
> 1. Gain: 250-300 for Mars (balance noise/speed)
> 2. Exposure: 5-15ms depending on seeing
> 3. ROI: Crop to 640x480 for faster capture
> 4. Binning: 1x1 only (already undersampled at f/6)
> 5. Format: SER files for stacking, 60-90 seconds each"

**Camera Service Implementation:**
```python
# services/camera/asi_camera.py

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import zwoasi as asi

class ImageFormat(Enum):
    RAW8 = "RAW8"
    RAW16 = "RAW16"
    SER = "SER"
    FITS = "FITS"

@dataclass
class CameraSettings:
    """Camera configuration for capture."""
    gain: int = 250
    exposure_ms: float = 10.0
    roi: Optional[tuple] = None  # (x, y, width, height)
    binning: int = 1
    format: ImageFormat = ImageFormat.SER

@dataclass
class CaptureSession:
    """Active capture session metadata."""
    target: str
    start_time: datetime
    frame_count: int
    settings: CameraSettings
    output_path: Path

class ASICamera:
    """
    ZWO ASI camera control for NIGHTWATCH.

    Supports both planetary (high-speed SER) and deep-sky (long exposure FITS).
    """

    def __init__(self, camera_index: int = 0):
        asi.init()
        self.camera = asi.Camera(camera_index)
        self._capturing = False

    def initialize(self):
        """Initialize camera with default settings."""
        self.camera.set_control_value(asi.ASI_GAIN, 250)
        self.camera.set_control_value(asi.ASI_EXPOSURE, 10000)  # microseconds
        self.camera.set_control_value(asi.ASI_BANDWIDTHOVERLOAD, 80)

    async def start_capture(self,
                           target: str,
                           duration_sec: float = 60.0,
                           settings: Optional[CameraSettings] = None) -> CaptureSession:
        """
        Start planetary video capture.

        Args:
            target: Name of target being captured
            duration_sec: Duration of capture in seconds
            settings: Camera settings (or use defaults)

        Returns:
            CaptureSession with metadata
        """

    async def capture_single(self,
                            exposure_sec: float,
                            format: ImageFormat = ImageFormat.FITS) -> Path:
        """Capture single frame (for deep-sky or testing)."""

    def get_temperature(self) -> float:
        """Get sensor temperature in Celsius."""
        return self.camera.get_control_value(asi.ASI_TEMPERATURE)[0] / 10.0
```

### Afternoon Session: Imaging Queue

**Multi-Target Imaging Queue:**
```python
# services/scheduler/imaging_queue.py

@dataclass
class ImagingTask:
    """Single imaging task in queue."""
    target: str
    priority: int
    capture_type: str  # "planetary", "lunar", "deep_sky"
    duration_sec: float
    filter: Optional[str] = None
    repeat_count: int = 1
    conditions: Optional[dict] = None  # min altitude, max seeing, etc.

class ImagingQueue:
    """
    Priority queue for automated imaging sessions.

    Features:
    - Priority-based scheduling
    - Condition checking (altitude, seeing, moon)
    - Automatic target switching
    - Resume after weather hold
    """

    def __init__(self):
        self._queue: List[ImagingTask] = []
        self._current: Optional[ImagingTask] = None

    async def add_task(self, task: ImagingTask):
        """Add task to queue with priority sorting."""

    async def get_next_task(self) -> Optional[ImagingTask]:
        """Get highest priority task that meets conditions."""

    async def run(self):
        """Main queue execution loop."""
```

---

## Day 13: Advanced Scheduler

### Focus: Multi-Night Planning, Ephemeris-Based Scheduling

**Morning Session: Bob Denny + Damian Peach Lead**

**Scheduler Architecture:**
> *Bob Denny:* "ACP's scheduler philosophy applies here:
> 1. Constraint-based: 'Observe X when altitude > 40° and moon < 30%'
> 2. Priority weights: Scientific value vs. time sensitivity
> 3. Mosaic support: Multi-panel targets with overlap
> 4. Transit windows: Automatic for planets
> 5. Retry logic: Weather interruption recovery"

**Transit Window Calculation:**
```python
# services/scheduler/transit_planner.py

@dataclass
class TransitWindow:
    """Optimal observation window for a target."""
    target: str
    rise_time: datetime
    transit_time: datetime
    set_time: datetime
    max_altitude: float
    optimal_start: datetime  # 1 hour before transit
    optimal_end: datetime    # 1 hour after transit

class TransitPlanner:
    """
    Calculate optimal observation windows for targets.

    Uses ephemeris service for planet transits and
    catalog data for fixed objects.
    """

    def __init__(self, ephemeris_service, location: Location):
        self.ephemeris = ephemeris_service
        self.location = location

    def get_planet_transit(self,
                           planet: str,
                           date: date) -> Optional[TransitWindow]:
        """Calculate transit window for planet on given date."""

    def get_optimal_targets(self,
                            night_start: datetime,
                            night_end: datetime,
                            min_altitude: float = 30.0) -> List[TransitWindow]:
        """
        Get all observable targets sorted by quality.

        Returns targets with their optimal windows, sorted by
        combination of altitude, duration, and priority.
        """

    def plan_night(self,
                   date: date,
                   priorities: Dict[str, int]) -> List[ScheduledObservation]:
        """
        Plan complete night's observations.

        Optimizes target sequence to minimize slew time
        while respecting transit windows and priorities.
        """
```

### Afternoon Session: Conflict Resolution

**Scheduling Constraints:**
```python
@dataclass
class SchedulingConstraints:
    """Constraints for observation scheduling."""

    # Time constraints
    min_altitude: float = 25.0          # degrees
    max_altitude: float = 85.0          # avoid zenith for GEM

    # Moon constraints
    max_moon_illumination: float = 0.6  # 60% for faint targets
    min_moon_distance: float = 30.0     # degrees from target

    # Seeing constraints
    max_seeing_arcsec: float = 3.0      # skip if seeing bad

    # Mount constraints
    avoid_meridian_flip: bool = False   # prefer continuous tracking
    min_time_before_flip: float = 600   # seconds

    # Weather constraints
    require_clear: bool = True
    max_wind_mph: float = 20.0
```

---

## Day 14: Machine Learning Integration

### Focus: Seeing Prediction, Image Quality Assessment

**Morning Session: Michael Clive + Antonio García Lead**

**ML Architecture for NIGHTWATCH:**
> *Michael Clive:* "DGX Spark can run multiple inference tasks:
> 1. Seeing prediction: LSTM on weather history
> 2. Image quality scoring: CNN on capture frames
> 3. Cloud prediction: Time-series on IR sensor data
> 4. Anomaly detection: Autoencoder on telemetry
> 5. All models: ONNX format for portability"

**Seeing Prediction Model:**
```python
# services/ml/seeing_predictor.py

import numpy as np
from datetime import datetime, timedelta
from typing import List, Tuple

@dataclass
class SeeingPrediction:
    """Predicted seeing conditions."""
    timestamp: datetime
    predicted_arcsec: float
    confidence: float
    factors: dict  # Contributing factors

class SeeingPredictor:
    """
    Predict astronomical seeing from weather data.

    Model: LSTM trained on weather → seeing correlations.
    Inputs: Temperature, humidity, wind, pressure (6-hour history)
    Output: Predicted seeing in arcseconds (1-hour ahead)
    """

    def __init__(self, model_path: Path):
        self.model = onnxruntime.InferenceSession(str(model_path))
        self._history: List[WeatherReading] = []
        self._history_hours = 6

    def update(self, weather: WeatherReading):
        """Add weather reading to history."""
        self._history.append(weather)
        # Keep only last 6 hours
        cutoff = datetime.now() - timedelta(hours=self._history_hours)
        self._history = [w for w in self._history if w.timestamp > cutoff]

    def predict(self) -> Optional[SeeingPrediction]:
        """
        Predict seeing for next hour.

        Requires at least 2 hours of weather history.
        """
        if len(self._history) < 12:  # 10-min intervals, 2 hours
            return None

        # Prepare input features
        features = self._prepare_features()

        # Run inference
        result = self.model.run(None, {"input": features})
        seeing = result[0][0]
        confidence = result[1][0]

        return SeeingPrediction(
            timestamp=datetime.now() + timedelta(hours=1),
            predicted_arcsec=float(seeing),
            confidence=float(confidence),
            factors=self._analyze_factors()
        )
```

**Image Quality Scorer:**
```python
# services/ml/image_scorer.py

@dataclass
class ImageQuality:
    """Image quality assessment."""
    sharpness: float      # 0-100
    contrast: float       # 0-100
    noise_level: float    # 0-100 (lower is better)
    overall_score: float  # 0-100
    usable: bool          # Above threshold?
    recommendation: str   # "keep", "discard", "review"

class ImageQualityScorer:
    """
    Assess planetary image quality for automated processing.

    Model: CNN trained on human-labeled planetary images.
    Output: Quality scores for stacking decisions.
    """

    def __init__(self, model_path: Path):
        self.model = onnxruntime.InferenceSession(str(model_path))
        self.threshold = 60.0  # Minimum score to keep

    def score_frame(self, frame: np.ndarray) -> ImageQuality:
        """Score single video frame."""

    async def score_ser_file(self,
                             ser_path: Path,
                             sample_rate: float = 0.1) -> List[ImageQuality]:
        """
        Score SER file by sampling frames.

        Args:
            ser_path: Path to SER video file
            sample_rate: Fraction of frames to sample (0.1 = 10%)

        Returns:
            Quality scores for sampled frames
        """

    def recommend_frames(self,
                         scores: List[ImageQuality],
                         keep_percentage: float = 0.3) -> List[int]:
        """Get indices of best frames for stacking."""
```

### Afternoon Session: Training Data

**Data Collection Strategy:**
```
Training Data Requirements:

Seeing Prediction:
- Weather readings: 6 months minimum
- Seeing measurements: DIMM or image analysis
- 10-minute intervals
- Correlation with actual image quality

Image Quality:
- 10,000+ labeled planetary frames
- Distribution across seeing conditions
- Mars, Jupiter, Saturn representation
- Human scoring or derived from stacking results
```

---

## Day 15: Dashboard & Mobile Interface

### Focus: Real-Time Monitoring, Remote Control

**Morning Session: Michael Hansen + SRO Team Lead**

**Dashboard Architecture:**
```
┌────────────────────────────────────────────────────────────────┐
│                    NIGHTWATCH Dashboard v2.0                     │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │   All-Sky Cam    │  │   Last Capture   │  │   Guiding     │ │
│  │   [Live Feed]    │  │   [Mars 2.3"]    │  │   RMS: 0.42"  │ │
│  │                  │  │                  │  │   [Graph]     │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Mount Status                                                 ││
│  │ Target: Mars  RA: 04h 32m 15s  DEC: +23° 45' 12"           ││
│  │ Tracking: SIDEREAL  Pier: EAST  Alt: 58.3°  Az: 145.2°     ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │ Temp: 42°F  │ │ Humid: 35%  │ │ Wind: 8 mph │ │ Sky: CLR  │ │
│  │ Dew: 28°F   │ │ Press: 1013 │ │ Gust: 12mph │ │ Moon: 23% │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ [PARK] [UNPARK] [STOP] [HOME] | Voice: [🎤 Push to Talk]   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

**Backend WebSocket API:**
```python
# services/dashboard/websocket_server.py

from fastapi import FastAPI, WebSocket
from typing import Dict, Any
import asyncio
import json

app = FastAPI()

class DashboardServer:
    """
    WebSocket server for real-time dashboard updates.

    Streams:
    - Mount position (1 Hz)
    - Weather data (0.1 Hz)
    - Guiding stats (2 Hz)
    - Safety status (0.2 Hz)
    - All-sky camera (0.1 Hz JPEG)
    """

    def __init__(self):
        self.clients: List[WebSocket] = []
        self._streams = {}

    async def broadcast(self, message_type: str, data: Any):
        """Send update to all connected clients."""
        message = json.dumps({
            "type": message_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })
        for client in self.clients:
            await client.send_text(message)

    async def run_streams(self):
        """Run all data streams."""
        await asyncio.gather(
            self._stream_mount_position(),
            self._stream_weather(),
            self._stream_guiding(),
            self._stream_safety(),
            self._stream_allsky(),
        )
```

### Afternoon Session: Mobile App Design

**Mobile App Features:**
```
NIGHTWATCH Mobile v2.0

Screens:
1. Dashboard
   - Status at a glance
   - Quick controls (park/unpark)
   - Voice button

2. Sky View
   - Current pointing
   - Visible objects overlay
   - Tap to GOTO

3. Weather
   - Current conditions
   - 24-hour graphs
   - Forecast integration

4. Gallery
   - Recent captures
   - Quick share
   - Processing status

5. Alerts
   - Push notifications
   - Alert history
   - Settings

Tech Stack:
- Flutter for cross-platform
- WebSocket for real-time
- Native voice for iOS/Android
```

---

## Day 16: Alert & Notification System

### Focus: Multi-Channel Alerts, Escalation

**Morning Session: SRO Team + Bob Denny Lead**

**Alert Hierarchy:**
```python
# services/alerts/alert_manager.py

class AlertLevel(Enum):
    DEBUG = 0      # Detailed logging only
    INFO = 1       # Normal operations (email digest)
    WARNING = 2    # Attention needed (push notification)
    CRITICAL = 3   # Immediate action (SMS + push + email)
    EMERGENCY = 4  # System protection activated (all channels + call)

@dataclass
class Alert:
    """System alert."""
    level: AlertLevel
    source: str           # Subsystem that raised alert
    message: str
    timestamp: datetime
    data: Optional[dict]  # Additional context
    acknowledged: bool = False

class AlertManager:
    """
    Multi-channel alert system for NIGHTWATCH.

    Channels:
    - Push notifications (Firebase)
    - SMS (Twilio)
    - Email (SMTP)
    - Voice call (Twilio)
    - Slack/Discord webhooks
    """

    def __init__(self, config: AlertConfig):
        self.config = config
        self._channels = self._init_channels()
        self._history: List[Alert] = []

    async def raise_alert(self, alert: Alert):
        """
        Raise alert through appropriate channels.

        Channel selection based on alert level:
        - DEBUG: Log only
        - INFO: Email digest
        - WARNING: Push notification
        - CRITICAL: SMS + Push + Email
        - EMERGENCY: All + Voice call
        """

    async def acknowledge(self, alert_id: str, user: str):
        """Acknowledge an alert (stops escalation)."""

    def get_unacknowledged(self) -> List[Alert]:
        """Get all unacknowledged alerts."""
```

**Alert Templates:**
```python
ALERT_TEMPLATES = {
    "weather_unsafe": {
        "level": AlertLevel.WARNING,
        "message": "Weather conditions unsafe: {reason}. Telescope parking.",
        "channels": ["push", "email"]
    },
    "rain_detected": {
        "level": AlertLevel.EMERGENCY,
        "message": "RAIN DETECTED! Emergency close initiated.",
        "channels": ["push", "sms", "email", "call"]
    },
    "guiding_failed": {
        "level": AlertLevel.WARNING,
        "message": "Autoguiding lost star. RMS was {rms}\".",
        "channels": ["push"]
    },
    "capture_complete": {
        "level": AlertLevel.INFO,
        "message": "Capture of {target} complete. {frames} frames captured.",
        "channels": ["email"]
    },
    "sensor_offline": {
        "level": AlertLevel.CRITICAL,
        "message": "Sensor {sensor} offline for {duration}. Safety degraded.",
        "channels": ["push", "sms", "email"]
    },
    "seeing_excellent": {
        "level": AlertLevel.INFO,
        "message": "Excellent seeing predicted: {seeing}\". Consider priority targets.",
        "channels": ["push"]
    }
}
```

### Afternoon Session: Escalation Logic

**Escalation Timeline:**
```
EMERGENCY Alert Escalation:

T+0:     Push notification sent
T+0:     SMS sent
T+0:     Email sent
T+30s:   Voice call initiated (if not acknowledged)
T+60s:   Secondary contact called
T+5m:    Repeat cycle if still unacknowledged
T+30m:   System enters safe mode, logs incident
```

---

## Day 17: Data Management & Cloud Integration

### Focus: Storage, Backup, Synchronization

**Morning Session: SRO Team + Michael Clive Lead**

**Storage Architecture:**
```
Local Storage (2TB NVMe):
├── captures/
│   ├── 2026-01-15/
│   │   ├── mars_2145_ser/
│   │   ├── jupiter_2230_ser/
│   │   └── saturn_0130_ser/
│   └── ...
├── processed/
│   ├── mars_stack_001.tif
│   └── ...
├── calibration/
│   ├── darks/
│   ├── flats/
│   └── bias/
└── logs/
    ├── safety/
    ├── guiding/
    └── system/

Cloud Backup (Backblaze B2):
- Automatic sync of processed images
- 30-day retention of raw SER files
- Unlimited retention of stacked results
- Encrypted with user key
```

**Sync Service:**
```python
# services/storage/cloud_sync.py

from pathlib import Path
from b2sdk.v2 import InMemoryAccountInfo, B2Api
from dataclasses import dataclass
from typing import Optional, List
import asyncio

@dataclass
class SyncPolicy:
    """Cloud synchronization policy."""
    raw_retention_days: int = 30
    processed_retention_days: int = -1  # Forever
    sync_interval_hours: float = 1.0
    bandwidth_limit_mbps: Optional[float] = None
    encrypt: bool = True

class CloudSyncService:
    """
    Background cloud synchronization for NIGHTWATCH data.

    Features:
    - Automatic upload of processed images
    - Retention policy enforcement
    - Bandwidth limiting
    - Client-side encryption
    - Resume on network failure
    """

    def __init__(self,
                 bucket_name: str,
                 local_root: Path,
                 policy: SyncPolicy):
        self.bucket_name = bucket_name
        self.local_root = local_root
        self.policy = policy

    async def sync_processed(self):
        """Sync processed images to cloud."""

    async def apply_retention(self):
        """Delete files older than retention policy."""

    async def download_file(self, cloud_path: str, local_path: Path):
        """Download file from cloud (for multi-device access)."""

    def get_sync_status(self) -> SyncStatus:
        """Get current sync status and pending uploads."""
```

### Afternoon Session: Data Pipeline

**Automated Processing Pipeline:**
```python
# services/processing/auto_pipeline.py

class AutoProcessingPipeline:
    """
    Automated image processing pipeline.

    Workflow:
    1. Capture completes → trigger processing
    2. Score frames → identify best for stacking
    3. Stack frames → AutoStakkert integration
    4. Sharpen → RegiStax wavelets
    5. Upload → Cloud sync
    6. Notify → Alert user of result
    """

    async def process_capture(self, ser_path: Path) -> ProcessingResult:
        """Process captured SER file end-to-end."""

        # Score frames
        scores = await self.scorer.score_ser_file(ser_path)

        # Select best frames
        best_indices = self.scorer.recommend_frames(scores)

        # Stack (call AutoStakkert CLI)
        stacked = await self._run_autostakkert(ser_path, best_indices)

        # Sharpen (call RegiStax CLI or internal wavelet)
        sharpened = await self._apply_wavelets(stacked)

        # Save result
        output_path = await self._save_result(sharpened)

        # Queue for cloud sync
        await self.sync_service.queue_upload(output_path)

        # Notify
        await self.alert_manager.raise_alert(Alert(
            level=AlertLevel.INFO,
            source="processing",
            message=f"Processing complete: {output_path.name}",
            data={"path": str(output_path), "score": scores[0].overall_score}
        ))

        return ProcessingResult(output_path=output_path, quality=scores)
```

---

## Day 18: Citizen Science Integration

### Focus: AAVSO, Planetary Patrol, Data Sharing

**Morning Session: Full Panel Discussion**

**Citizen Science Opportunities:**
> *Panel Discussion:* "NIGHTWATCH can contribute to several programs:
>
> 1. **AAVSO** (American Association of Variable Star Observers)
>    - Variable star monitoring
>    - Exoplanet transit timing
>    - Automated data submission
>
> 2. **ALPO** (Association of Lunar & Planetary Observers)
>    - Planetary storm monitoring
>    - Mars dust storm detection
>    - Jupiter impact flashes
>
> 3. **Pro-Am Collaborations**
>    - Asteroid occultation timing
>    - Comet monitoring
>    - Supernova early detection
>
> 4. **Mars Watch**
>    - Continuous Mars monitoring network
>    - Global dust storm early warning
>    - Polar cap observations"

**AAVSO Integration:**
```python
# services/citizen_science/aavso_reporter.py

@dataclass
class AAVSOObservation:
    """AAVSO observation report format."""
    star_name: str
    date_jd: float
    magnitude: float
    mag_error: float
    filter: str  # V, B, R, I, etc.
    comparison_star: str
    check_star: str
    airmass: float
    notes: str

class AAVSOReporter:
    """
    Automated AAVSO observation reporter.

    Submits photometry data to AAVSO WebObs.
    """

    def __init__(self, observer_code: str, api_key: str):
        self.observer_code = observer_code
        self.api_key = api_key
        self.base_url = "https://www.aavso.org/apps/webobs/api/"

    async def submit_observation(self, obs: AAVSOObservation) -> bool:
        """Submit single observation to AAVSO."""

    async def submit_batch(self, observations: List[AAVSOObservation]) -> int:
        """Submit batch of observations. Returns count submitted."""

    async def get_target_list(self, program: str) -> List[str]:
        """Get current priority targets for a program."""
```

### Afternoon Session: Alert Networks

**Transient Alert Integration:**
```python
# services/citizen_science/transient_alerts.py

class TransientAlertListener:
    """
    Listen for transient alerts from professional networks.

    Sources:
    - TNS (Transient Name Server)
    - GCN (Gamma-ray Coordinates Network)
    - ASAS-SN alerts
    - ZTF public alerts
    """

    async def listen_for_alerts(self):
        """Listen for new transient discoveries."""

    async def evaluate_target(self, alert: TransientAlert) -> bool:
        """
        Evaluate if target is observable and interesting.

        Criteria:
        - Above horizon
        - Bright enough for MN78
        - Not too close to moon
        - Time-critical observation
        """

    async def trigger_observation(self, alert: TransientAlert):
        """Interrupt current schedule for transient observation."""
```

---

## Day 19: Diagnostics & Predictive Maintenance

### Focus: System Health, Failure Prediction

**Morning Session: Richard Hedrick + Howard Dutton Lead**

**Diagnostic Telemetry:**
```python
# services/diagnostics/telemetry_collector.py

@dataclass
class SystemTelemetry:
    """Complete system health snapshot."""
    timestamp: datetime

    # Mount telemetry
    motor_currents: Dict[str, float]      # mA per axis
    motor_temperatures: Dict[str, float]  # °C per driver
    encoder_counts: Dict[str, int]        # Raw counts
    tracking_error_rms: float             # arcsec

    # Camera telemetry
    sensor_temperature: float             # °C
    cooler_power: float                   # Percentage

    # Environmental
    enclosure_temperature: float          # °C
    humidity_internal: float              # Percentage
    power_voltage: float                  # V
    power_current: float                  # A

    # Compute
    cpu_temperature: float                # °C
    gpu_temperature: float                # °C (DGX Spark)
    memory_usage: float                   # Percentage
    disk_usage: float                     # Percentage

class TelemetryCollector:
    """
    Continuous telemetry collection for diagnostics.

    Stores:
    - 1-second resolution for last hour
    - 1-minute resolution for last day
    - 1-hour resolution for last year
    """

    async def collect(self) -> SystemTelemetry:
        """Collect current telemetry snapshot."""

    async def store(self, telemetry: SystemTelemetry):
        """Store telemetry with appropriate resolution."""

    def get_trends(self,
                   metric: str,
                   hours: float = 24) -> List[Tuple[datetime, float]]:
        """Get historical trend for a metric."""
```

**Predictive Maintenance:**
```python
# services/diagnostics/predictive_maintenance.py

@dataclass
class MaintenanceAlert:
    """Predicted maintenance need."""
    component: str
    issue: str
    confidence: float
    predicted_failure: Optional[datetime]
    recommended_action: str
    priority: str  # "low", "medium", "high"

class PredictiveMaintenanceMonitor:
    """
    Predict maintenance needs from telemetry patterns.

    Monitors:
    - Motor current trends (bearing wear)
    - Tracking error trends (mechanical degradation)
    - Temperature anomalies (cooling issues)
    - Encoder noise (sensor degradation)
    """

    def __init__(self, telemetry: TelemetryCollector):
        self.telemetry = telemetry
        self.models = self._load_models()

    async def analyze(self) -> List[MaintenanceAlert]:
        """Analyze current telemetry for maintenance predictions."""

        alerts = []

        # Check motor current trends
        for axis in ["RA", "DEC"]:
            trend = self.telemetry.get_trends(f"motor_current_{axis}", hours=168)
            if self._detect_increasing_trend(trend):
                alerts.append(MaintenanceAlert(
                    component=f"{axis} motor/drive",
                    issue="Increasing current draw detected",
                    confidence=0.75,
                    predicted_failure=None,
                    recommended_action="Inspect bearings and lubrication",
                    priority="medium"
                ))

        # Check tracking error trends
        tracking_trend = self.telemetry.get_trends("tracking_error_rms", hours=168)
        if self._detect_degradation(tracking_trend):
            alerts.append(MaintenanceAlert(
                component="Tracking system",
                issue="Tracking accuracy degrading",
                confidence=0.8,
                predicted_failure=None,
                recommended_action="Check encoder alignment and worm mesh",
                priority="high"
            ))

        return alerts
```

### Afternoon Session: Health Dashboard

**System Health Panel:**
```
┌─────────────────────────────────────────────────────────────┐
│                    System Health - v2.0                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Component         Status    Last Check    Trend            │
│  ─────────────────────────────────────────────────────────  │
│  RA Motor          ✓ OK      2 min ago     ═══════ stable   │
│  DEC Motor         ✓ OK      2 min ago     ═══════ stable   │
│  RA Encoder        ✓ OK      2 min ago     ═══════ stable   │
│  DEC Encoder       ✓ OK      2 min ago     ═══════ stable   │
│  Camera            ✓ OK      5 min ago     ═══════ stable   │
│  Guide Camera      ✓ OK      5 min ago     ═══════ stable   │
│  Weather Station   ✓ OK      1 min ago     ═══════ stable   │
│  Cloud Sensor      ⚠ WARN    3 min ago     ═══╱╲══ noisy    │
│  GPS               ✓ OK      10 min ago    ═══════ stable   │
│  Power System      ✓ OK      1 min ago     ═══════ stable   │
│                                                              │
│  Maintenance Alerts:                                         │
│  ─────────────────────────────────────────────────────────  │
│  ⚠ Cloud sensor showing intermittent readings                │
│    Recommended: Check cable connections and sensor dome      │
│    Priority: Medium | Predicted impact: Degraded safety      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Day 20: v2.0 Integration & Release Planning

### Morning Session: Full Panel Final Review

**v2.0 Feature Summary:**

| Feature | Lead Specialist | Status | Priority |
|---------|-----------------|--------|----------|
| PHD2 Guiding | Craig Stark | Design Complete | P0 |
| Camera Control | Damian Peach | Design Complete | P0 |
| Imaging Queue | Bob Denny | Design Complete | P1 |
| Advanced Scheduler | Bob Denny | Design Complete | P1 |
| Seeing Prediction ML | Michael Clive | Design Complete | P2 |
| Image Quality ML | Michael Clive | Design Complete | P1 |
| Dashboard v2 | Michael Hansen | Design Complete | P0 |
| Mobile App | Michael Hansen | Design Complete | P2 |
| Alert System | SRO Team | Design Complete | P0 |
| Cloud Sync | SRO Team | Design Complete | P1 |
| AAVSO Integration | Panel | Design Complete | P2 |
| Predictive Maintenance | Richard Hedrick | Design Complete | P2 |

**Architecture Overview (v2.0):**
```
┌────────────────────────────────────────────────────────────────────┐
│                      NIGHTWATCH v2.0 Architecture                   │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │
│  │   Voice     │  │  Dashboard  │  │   Mobile    │  │   API     │ │
│  │  Interface  │  │   Web UI    │  │     App     │  │  Clients  │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬─────┘ │
│         │                │                │                │       │
│         └────────────────┴────────────────┴────────────────┘       │
│                                  │                                  │
│                    ┌─────────────▼─────────────┐                   │
│                    │    NIGHTWATCH Core API    │                   │
│                    │   (FastAPI + WebSocket)   │                   │
│                    └─────────────┬─────────────┘                   │
│                                  │                                  │
│    ┌─────────────────────────────┼─────────────────────────────┐   │
│    │                             │                             │   │
│    ▼                             ▼                             ▼   │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────────┐  │
│  │   Mount   │  │  Camera   │  │  Guiding  │  │   Scheduler   │  │
│  │  Service  │  │  Service  │  │  (PHD2)   │  │    Service    │  │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └───────┬───────┘  │
│        │              │              │                │          │
│  ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐  ┌───────▼───────┐  │
│  │  OnStepX  │  │ ASI662MC  │  │  ASI120MM │  │   Ephemeris   │  │
│  │  Teensy   │  │  Camera   │  │   Guide   │  │    Service    │  │
│  └───────────┘  └───────────┘  └───────────┘  └───────────────┘  │
│                                                                     │
│    ┌─────────────────────────────────────────────────────────┐     │
│    │                    Support Services                      │     │
│    ├──────────┬──────────┬──────────┬──────────┬────────────┤     │
│    │  Safety  │ Weather  │  Alerts  │ Storage  │    ML      │     │
│    │ Monitor  │ Service  │ Manager  │  & Sync  │ Inference  │     │
│    └──────────┴──────────┴──────────┴──────────┴────────────┘     │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Afternoon Session: Implementation Roadmap

**v2.0 Implementation Phases:**

```
Phase 1: Core Imaging (Weeks 1-4)
├── Camera service implementation
├── PHD2 client integration
├── Basic imaging workflow
└── Guiding voice commands

Phase 2: Automation (Weeks 5-8)
├── Advanced scheduler
├── Imaging queue
├── Transit planner
└── Auto-processing pipeline

Phase 3: Intelligence (Weeks 9-12)
├── Seeing prediction model
├── Image quality scorer
├── Predictive maintenance
└── Model training/validation

Phase 4: Interface (Weeks 13-16)
├── Dashboard v2.0
├── Mobile app MVP
├── Alert system
└── Cloud sync

Phase 5: Integration (Weeks 17-20)
├── AAVSO integration
├── Transient alerts
├── Full system testing
└── Documentation
```

**v2.0 Code Structure:**
```
nightwatch/
├── services/
│   ├── camera/
│   │   ├── __init__.py
│   │   ├── asi_camera.py          # NEW: Camera control
│   │   └── capture_session.py     # NEW: Capture management
│   ├── guiding/
│   │   ├── __init__.py
│   │   ├── phd2_client.py         # NEW: PHD2 integration
│   │   └── guide_calibration.py   # NEW: Calibration storage
│   ├── scheduler/
│   │   ├── __init__.py
│   │   ├── imaging_queue.py       # NEW: Multi-target queue
│   │   └── transit_planner.py     # NEW: Transit windows
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── seeing_predictor.py    # NEW: Seeing prediction
│   │   └── image_scorer.py        # NEW: Quality assessment
│   ├── processing/
│   │   ├── __init__.py
│   │   └── auto_pipeline.py       # NEW: Auto processing
│   ├── alerts/
│   │   ├── __init__.py
│   │   └── alert_manager.py       # NEW: Multi-channel alerts
│   ├── storage/
│   │   ├── __init__.py
│   │   └── cloud_sync.py          # NEW: Cloud backup
│   ├── citizen_science/
│   │   ├── __init__.py
│   │   ├── aavso_reporter.py      # NEW: AAVSO submission
│   │   └── transient_alerts.py    # NEW: Alert listener
│   └── diagnostics/
│       ├── __init__.py
│       ├── telemetry_collector.py # NEW: Telemetry
│       └── predictive_maintenance.py # NEW: Predictions
├── dashboard/
│   ├── backend/
│   │   └── websocket_server.py    # NEW: Real-time API
│   └── frontend/
│       └── ...                    # NEW: React dashboard
└── mobile/
    └── ...                        # NEW: Flutter app
```

---

## v2.0 Panel Recommendations Summary

### Critical v2.0 Additions:

1. **Guiding (Craig Stark):** PHD2 integration enables long-exposure imaging and improved tracking verification
2. **Camera (Damian Peach):** Full camera control allows automated capture sessions
3. **Scheduler (Bob Denny):** Multi-target queuing and transit planning optimize observing time
4. **ML (Michael Clive):** Seeing prediction and image quality scoring enable intelligent automation
5. **Alerts (SRO Team):** Multi-channel notifications keep operator informed
6. **Storage (SRO Team):** Cloud backup protects valuable data
7. **Dashboard (Hansen):** Real-time monitoring enables effective remote operation
8. **Diagnostics (Hedrick):** Predictive maintenance prevents failures

### v2.0 Release Criteria:

| Requirement | Metric | Target |
|-------------|--------|--------|
| Guiding RMS | Arcsec | <0.5" |
| Capture success | Percentage | >95% |
| Processing latency | Minutes | <5 min |
| Alert delivery | Seconds | <30 sec |
| Dashboard latency | Milliseconds | <500 ms |
| Uptime | Weekly | >98% |
| Storage availability | Percentage | >99.9% |

---

## Retreat Conclusion (v2.0)

The Panel of Specialists has completed a comprehensive 20-day design retreat for NIGHTWATCH v2.0. The extended retreat added critical imaging, automation, and intelligence capabilities while maintaining the robust foundation established in v1.0.

**Unanimous Panel Assessment:** NIGHTWATCH v2.0 represents a significant advancement toward a fully autonomous, scientifically productive observatory capable of contributing to professional-amateur collaborations.

**Key v2.0 Achievements:**
- Complete imaging pipeline from capture to processed result
- Intelligent scheduling with transit optimization
- Machine learning for seeing prediction and quality assessment
- Multi-channel alert system for remote operation
- Cloud integration for data preservation and sharing
- Citizen science integration for scientific contribution
- Predictive maintenance for system reliability

**Next Steps:**
1. Implement v2.0 Phase 1 (Core Imaging)
2. Deploy PHD2 guiding integration
3. Add camera control and capture automation
4. Create comprehensive PR for v2.0

---

*Panel of Specialists Retreat - January 2026*
*Document Version: 2.0*
*Days 1-10: Foundation & v1.0*
*Days 11-20: Advanced Features & v2.0*
