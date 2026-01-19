# NIGHTWATCH Panel of Specialists (POS) Design Retreat
## 30-Day Agile Design Session Simulation
### Location: Virtual Retreat | Date: January 2026
### Version: 3.0

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
> "Intes Micro MN76 quality is excellent. Practical notes:
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

## v2.0 Milestone Complete

The Panel of Specialists has completed Phase 2 with imaging pipeline, guiding, and alert systems. Ready for Phase 3: Full Automation.

---

# PHASE 3: Full Automation (Days 21-30)

---

## Day 21: Automated Focus Control

### Focus: Temperature-Compensated Focusing, Bahtinov Analysis

**Morning Session: Damian Peach + Craig Stark Lead**

**Focus System Requirements:**
> *Damian Peach:* "For consistent planetary imaging:
> 1. Temperature compensation is essential - MN78 shifts focus with temp
> 2. Coefficient: Approximately 2 microns per degree C for the MN78
> 3. Bahtinov mask analysis for coarse focus
> 4. FWHM optimization for fine focus
> 5. Auto-focus before each capture session, re-check every 30 minutes"

**Focuser Hardware:**
```
Recommended: ZWO EAF (Electronic Automatic Focuser)
- Step resolution: 0.65μm per step
- Max travel: 80mm
- Temperature sensor: Built-in (±0.5°C accuracy)
- Interface: USB 2.0
- ASCOM/INDI compatible
```

**Focus Service Implementation:**
```python
# services/focus/focuser_service.py

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Tuple
import numpy as np

class FocusMethod(Enum):
    BAHTINOV = "bahtinov"      # Mask-based coarse focus
    FWHM = "fwhm"              # Star FWHM optimization
    CONTRAST = "contrast"      # Planetary contrast
    VCURVE = "vcurve"          # V-curve analysis

@dataclass
class FocusPosition:
    """Current focuser state."""
    position: int             # Absolute step position
    temperature: float        # Sensor temperature (°C)
    is_moving: bool
    at_target: bool

@dataclass
class FocusResult:
    """Result of auto-focus operation."""
    success: bool
    method: FocusMethod
    initial_position: int
    final_position: int
    initial_metric: float     # FWHM, contrast, etc.
    final_metric: float
    temperature: float
    duration_sec: float

class FocuserService:
    """
    Automated focus control for NIGHTWATCH.

    Features:
    - Temperature compensation with configurable coefficient
    - Multiple focus methods (Bahtinov, FWHM, contrast)
    - Focus history for trend analysis
    - Integration with camera for frame analysis
    """

    # Temperature coefficient for MN78 (microns per °C)
    TEMP_COEFFICIENT = 2.0
    STEPS_PER_MICRON = 1.54  # For ZWO EAF

    def __init__(self, focuser_port: str = "/dev/ttyUSB1"):
        self.port = focuser_port
        self._position = 0
        self._temperature = 20.0
        self._reference_temp = 20.0
        self._reference_position = 50000
        self._focus_history: List[FocusResult] = []

    async def connect(self) -> bool:
        """Connect to focuser."""

    async def get_position(self) -> FocusPosition:
        """Get current focuser state."""

    async def move_to(self, position: int) -> bool:
        """Move to absolute position."""

    async def move_relative(self, steps: int) -> bool:
        """Move relative to current position."""

    async def temperature_compensate(self) -> int:
        """
        Calculate and apply temperature compensation.

        Returns:
            Number of steps moved
        """
        current_temp = await self._get_temperature()
        delta_temp = current_temp - self._reference_temp
        delta_microns = delta_temp * self.TEMP_COEFFICIENT
        delta_steps = int(delta_microns * self.STEPS_PER_MICRON)

        if abs(delta_steps) > 10:
            await self.move_relative(delta_steps)
            return delta_steps
        return 0

    async def auto_focus(self,
                        method: FocusMethod = FocusMethod.FWHM,
                        camera = None) -> FocusResult:
        """
        Perform automated focus routine.

        Args:
            method: Focus method to use
            camera: Camera service for frame capture

        Returns:
            FocusResult with details
        """

    async def analyze_bahtinov(self, image: np.ndarray) -> float:
        """Analyze Bahtinov pattern and return focus error."""

    async def measure_fwhm(self, image: np.ndarray) -> float:
        """Measure star FWHM in pixels."""
```

### Afternoon Session: Focus Workflow

**Automated Focus Workflow:**
```
┌─────────────────────────────────────────────────┐
│           NIGHTWATCH Focus Workflow              │
├─────────────────────────────────────────────────┤
│                                                 │
│  Session Start                                  │
│       │                                         │
│       ▼                                         │
│  ┌─────────────┐                               │
│  │ Read temp   │──► Calculate compensation      │
│  └──────┬──────┘                               │
│         │                                       │
│         ▼                                       │
│  ┌─────────────┐                               │
│  │ Slew to     │──► Bright star (mag 2-4)      │
│  │ focus star  │                               │
│  └──────┬──────┘                               │
│         │                                       │
│         ▼                                       │
│  ┌─────────────┐                               │
│  │ Coarse      │──► Bahtinov or V-curve        │
│  │ focus       │                               │
│  └──────┬──────┘                               │
│         │                                       │
│         ▼                                       │
│  ┌─────────────┐                               │
│  │ Fine focus  │──► FWHM optimization          │
│  └──────┬──────┘                               │
│         │                                       │
│         ▼                                       │
│  ┌─────────────┐                               │
│  │ Store       │──► Reference position + temp  │
│  │ reference   │                               │
│  └─────────────┘                               │
│                                                 │
│  During Session: Re-check every 30 min         │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Day 22: Plate Solving & Astrometry

### Focus: Automated Pointing Correction, Image Registration

**Morning Session: Bob Denny + Craig Stark Lead**

**Plate Solving Strategy:**
> *Bob Denny:* "Plate solving is essential for blind GOTO verification:
> 1. Local solver (solve-field) for speed
> 2. Fallback to online (astrometry.net) if local fails
> 3. Typical solve time: 2-5 seconds with good index files
> 4. Sync mount after each solve for pointing model improvement
> 5. Required for mosaic and multi-target imaging"

**Plate Solver Implementation:**
```python
# services/astrometry/plate_solver.py

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
import subprocess
import asyncio

@dataclass
class SolveResult:
    """Plate solving result."""
    success: bool
    ra_deg: float              # Solved RA in degrees
    dec_deg: float             # Solved DEC in degrees
    ra_hms: str                # RA in HMS format
    dec_dms: str               # DEC in DMS format
    rotation: float            # Field rotation in degrees
    pixel_scale: float         # Arcsec per pixel
    field_width: float         # Field width in arcmin
    field_height: float        # Field height in arcmin
    solve_time_sec: float
    solver_used: str           # "local" or "online"
    index_file: Optional[str]  # Which index matched

@dataclass
class PointingError:
    """Pointing error analysis."""
    ra_error_arcmin: float
    dec_error_arcmin: float
    total_error_arcmin: float
    within_tolerance: bool     # < 5 arcmin typically

class PlateSolver:
    """
    Astrometric plate solving for NIGHTWATCH.

    Uses local solve-field (astrometry.net) with fallback
    to online solving.
    """

    def __init__(self,
                 index_path: Path = Path("/usr/share/astrometry"),
                 config_path: Optional[Path] = None):
        self.index_path = index_path
        self.config_path = config_path
        self._scale_low = 1.0   # arcsec/pixel lower bound
        self._scale_high = 3.0  # arcsec/pixel upper bound

    async def solve(self,
                   image_path: Path,
                   ra_hint: Optional[float] = None,
                   dec_hint: Optional[float] = None,
                   radius_hint: float = 5.0) -> SolveResult:
        """
        Solve image astrometry.

        Args:
            image_path: Path to FITS or image file
            ra_hint: Expected RA in degrees (optional)
            dec_hint: Expected DEC in degrees (optional)
            radius_hint: Search radius in degrees

        Returns:
            SolveResult with coordinates and metadata
        """
        # Try local solve first
        result = await self._solve_local(image_path, ra_hint, dec_hint, radius_hint)

        if not result.success:
            # Fallback to online
            result = await self._solve_online(image_path)

        return result

    async def _solve_local(self,
                          image_path: Path,
                          ra_hint: Optional[float],
                          dec_hint: Optional[float],
                          radius: float) -> SolveResult:
        """Solve using local astrometry.net installation."""
        cmd = [
            "solve-field",
            "--overwrite",
            "--no-plots",
            "--scale-units", "arcsecperpix",
            "--scale-low", str(self._scale_low),
            "--scale-high", str(self._scale_high),
        ]

        if ra_hint is not None and dec_hint is not None:
            cmd.extend([
                "--ra", str(ra_hint),
                "--dec", str(dec_hint),
                "--radius", str(radius)
            ])

        cmd.append(str(image_path))

        # Run solver
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        # Parse results from WCS file
        return self._parse_solve_result(image_path, process.returncode == 0)

    async def calculate_pointing_error(self,
                                       expected_ra: float,
                                       expected_dec: float,
                                       actual_ra: float,
                                       actual_dec: float) -> PointingError:
        """Calculate pointing error from expected vs actual."""
        ra_error = (actual_ra - expected_ra) * 60 * np.cos(np.radians(expected_dec))
        dec_error = (actual_dec - expected_dec) * 60

        total = np.sqrt(ra_error**2 + dec_error**2)

        return PointingError(
            ra_error_arcmin=ra_error,
            dec_error_arcmin=dec_error,
            total_error_arcmin=total,
            within_tolerance=total < 5.0
        )

    async def sync_mount_from_solve(self,
                                    mount_client,
                                    solve_result: SolveResult) -> bool:
        """Sync mount position from plate solve result."""
        if not solve_result.success:
            return False

        return mount_client.sync_ra_dec(
            solve_result.ra_hms,
            solve_result.dec_dms
        )
```

### Afternoon Session: Pointing Model

**Pointing Model Integration:**
```python
# services/astrometry/pointing_model.py

@dataclass
class PointingModelPoint:
    """Single pointing model calibration point."""
    mount_ra: float
    mount_dec: float
    actual_ra: float
    actual_dec: float
    timestamp: datetime
    altitude: float
    azimuth: float

class PointingModel:
    """
    Build and apply pointing model corrections.

    Collects plate solve data across the sky to build
    a model of systematic pointing errors.
    """

    def __init__(self):
        self._points: List[PointingModelPoint] = []
        self._model_coefficients = None

    async def add_calibration_point(self,
                                    mount_client,
                                    plate_solver,
                                    camera) -> PointingModelPoint:
        """Add a calibration point at current position."""

    async def build_model(self, min_points: int = 20) -> bool:
        """Build pointing model from collected points."""

    def predict_error(self, ra: float, dec: float) -> Tuple[float, float]:
        """Predict pointing error for a given position."""

    async def auto_calibrate(self,
                            mount_client,
                            plate_solver,
                            camera,
                            num_points: int = 25):
        """
        Automatically run pointing model calibration.

        Slews to distributed points across the sky and
        builds a pointing model.
        """
```

---

## Day 23: Dome/Enclosure Automation

### Focus: Roll-Off Roof, Weather-Synchronized Operation

**Morning Session: SRO Team + Antonio García Lead**

**Enclosure Strategy:**
> *SRO Team:* "For Nevada installation, recommend roll-off roof:
> 1. Simpler than dome - no rotation synchronization needed
> 2. Wide-open sky access for all-sky imaging
> 3. Fast open/close (< 60 seconds)
> 4. Integrated rain sensor with override
> 5. Manual override capability essential"

**Enclosure Controller:**
```python
# services/enclosure/roof_controller.py

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import asyncio

class RoofState(Enum):
    UNKNOWN = "unknown"
    OPEN = "open"
    CLOSED = "closed"
    OPENING = "opening"
    CLOSING = "closing"
    ERROR = "error"

class RoofCommand(Enum):
    OPEN = "open"
    CLOSE = "close"
    STOP = "stop"

@dataclass
class RoofStatus:
    """Current roof status."""
    state: RoofState
    position_percent: float   # 0 = closed, 100 = open
    is_safe: bool             # Safe to operate telescope
    last_movement: datetime
    motor_current: float      # Amps
    obstruction_detected: bool
    rain_sensor_triggered: bool

@dataclass
class SafetyInterlocks:
    """Safety interlock status."""
    telescope_parked: bool
    wind_safe: bool
    rain_clear: bool
    manual_override: bool
    power_ok: bool

class RoofController:
    """
    Roll-off roof controller for NIGHTWATCH.

    Safety-first design with multiple interlocks.
    """

    # Timing constants
    OPEN_TIME_SEC = 45.0
    CLOSE_TIME_SEC = 45.0
    MOTOR_TIMEOUT_SEC = 60.0

    def __init__(self, controller_host: str = "192.168.1.100"):
        self.host = controller_host
        self._state = RoofState.UNKNOWN
        self._safety = SafetyInterlocks(
            telescope_parked=False,
            wind_safe=True,
            rain_clear=True,
            manual_override=False,
            power_ok=True
        )

    async def get_status(self) -> RoofStatus:
        """Get current roof status."""

    async def open(self, force: bool = False) -> bool:
        """
        Open the roof.

        Args:
            force: Bypass safety interlocks (DANGEROUS)

        Returns:
            True if command accepted
        """
        if not force:
            if not await self._check_interlocks_for_open():
                return False

        await self._send_command(RoofCommand.OPEN)
        return True

    async def close(self, emergency: bool = False) -> bool:
        """
        Close the roof.

        Args:
            emergency: Emergency close (ignore some interlocks)

        Returns:
            True if command accepted
        """
        if emergency:
            # Emergency close - stop telescope first
            await self._emergency_stop_telescope()

        await self._send_command(RoofCommand.CLOSE)
        return True

    async def stop(self) -> bool:
        """Emergency stop roof movement."""
        await self._send_command(RoofCommand.STOP)
        return True

    async def _check_interlocks_for_open(self) -> bool:
        """Verify all interlocks allow opening."""
        status = await self._get_interlock_status()

        if not status.telescope_parked:
            logger.warning("Cannot open: telescope not parked")
            return False

        if not status.wind_safe:
            logger.warning("Cannot open: wind too high")
            return False

        if not status.rain_clear:
            logger.warning("Cannot open: rain detected")
            return False

        if not status.power_ok:
            logger.warning("Cannot open: power issue")
            return False

        return True

    async def sync_with_weather(self, safety_monitor) -> None:
        """
        Continuous weather synchronization loop.

        Automatically closes roof when weather becomes unsafe.
        """
        while True:
            status = safety_monitor.evaluate()

            if not status.is_safe and self._state == RoofState.OPEN:
                logger.warning(f"Weather unsafe: {status.reasons}")
                await self.close(emergency=True)

            await asyncio.sleep(5.0)
```

### Afternoon Session: Enclosure Integration

**ASCOM-Compatible Interface:**
```python
# services/enclosure/ascom_dome.py

class ASCOMDome:
    """
    ASCOM Dome interface for NIGHTWATCH roof.

    Implements ASCOM IDomeV2 interface for compatibility
    with astronomy software.
    """

    @property
    def ShutterStatus(self) -> int:
        """ASCOM shutter status (0=open, 1=closed, etc.)"""

    @property
    def AtPark(self) -> bool:
        """Whether dome/roof is at park position."""

    def OpenShutter(self):
        """Open the shutter/roof."""

    def CloseShutter(self):
        """Close the shutter/roof."""

    def AbortSlew(self):
        """Stop any movement."""
```

---

## Day 24: All-Sky Camera Integration

### Focus: Cloud Detection, Aurora/Meteor Detection

**Morning Session: Antonio García + SRO Team Lead**

**All-Sky Camera Purpose:**
> *Antonio García:* "All-sky camera provides multiple functions:
> 1. Primary: Visual verification of sky conditions
> 2. Cloud detection independent of IR sensor
> 3. Satellite/aircraft trail detection
> 4. Aurora and meteor detection
> 5. Time-lapse for public outreach"

**All-Sky Service:**
```python
# services/allsky/allsky_camera.py

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
import numpy as np

@dataclass
class AllSkyFrame:
    """Single all-sky camera frame."""
    timestamp: datetime
    image: np.ndarray
    exposure_sec: float
    gain: int
    temperature: float
    analysis: Optional['SkyAnalysis'] = None

@dataclass
class SkyAnalysis:
    """Analysis of all-sky frame."""
    cloud_cover_percent: float
    transparency: float        # 0-1 scale
    stars_detected: int
    limiting_magnitude: float
    moon_visible: bool
    aurora_detected: bool
    meteor_count: int
    aircraft_count: int
    satellite_count: int

class AllSkyCamera:
    """
    All-sky camera service for NIGHTWATCH.

    Provides visual sky monitoring and analysis.
    """

    def __init__(self, camera_index: int = 1):
        self.camera_index = camera_index
        self._capturing = False
        self._latest_frame: Optional[AllSkyFrame] = None

    async def capture_frame(self,
                           exposure_sec: float = 30.0,
                           gain: int = 300) -> AllSkyFrame:
        """Capture single all-sky frame."""

    async def start_timelapse(self,
                             interval_sec: float = 60.0,
                             output_dir: Path = Path("/data/allsky")):
        """Start continuous timelapse capture."""

    async def analyze_frame(self, frame: AllSkyFrame) -> SkyAnalysis:
        """
        Analyze all-sky frame for cloud cover, etc.

        Uses star detection to estimate transparency.
        """
        # Detect stars
        stars = await self._detect_stars(frame.image)

        # Estimate cloud cover from star count
        expected_stars = self._expected_stars_for_conditions()
        cloud_cover = 1.0 - (len(stars) / expected_stars)
        cloud_cover = max(0.0, min(1.0, cloud_cover))

        # Check for meteors (bright short streaks)
        meteors = await self._detect_meteors(frame.image)

        # Check for satellites (linear tracks)
        satellites = await self._detect_satellites(frame.image)

        return SkyAnalysis(
            cloud_cover_percent=cloud_cover * 100,
            transparency=1.0 - cloud_cover,
            stars_detected=len(stars),
            limiting_magnitude=self._estimate_limiting_mag(stars),
            moon_visible=await self._detect_moon(frame.image),
            aurora_detected=await self._detect_aurora(frame.image),
            meteor_count=len(meteors),
            aircraft_count=0,  # TODO
            satellite_count=len(satellites)
        )

    async def get_cloud_map(self, frame: AllSkyFrame) -> np.ndarray:
        """
        Generate cloud map from all-sky image.

        Returns:
            2D array with cloud probability per region
        """
```

---

## Day 25: Power Management & UPS

### Focus: Graceful Shutdown, Power Monitoring

**Morning Session: SRO Team Lead**

**Power Architecture:**
> *SRO Team:* "Remote observatory power management is critical:
> 1. UPS for graceful shutdown (10 minute runtime minimum)
> 2. Smart PDU for remote power cycling
> 3. Automatic safe-state on power loss
> 4. Generator backup for extended outages (optional)
> 5. Solar panel charging for daytime operation"

**Power Service:**
```python
# services/power/power_manager.py

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

class PowerState(Enum):
    NORMAL = "normal"          # Grid power OK
    ON_BATTERY = "on_battery"  # Running from UPS
    LOW_BATTERY = "low_battery" # UPS < 20%
    CRITICAL = "critical"      # UPS < 10%, shutting down
    GENERATOR = "generator"    # Running from generator

class OutletState(Enum):
    ON = "on"
    OFF = "off"
    CYCLING = "cycling"

@dataclass
class PowerStatus:
    """System power status."""
    state: PowerState
    grid_voltage: float
    battery_percent: float
    battery_runtime_min: float
    load_watts: float
    temperature: float

@dataclass
class PDUOutlet:
    """Single PDU outlet status."""
    id: int
    name: str
    state: OutletState
    current_amps: float
    power_watts: float

class PowerManager:
    """
    Power management for NIGHTWATCH.

    Monitors UPS and PDU, handles graceful shutdown.
    """

    # Shutdown thresholds
    LOW_BATTERY_PERCENT = 20.0
    CRITICAL_BATTERY_PERCENT = 10.0
    MIN_RUNTIME_MINUTES = 5.0

    def __init__(self,
                 ups_host: str = "192.168.1.101",
                 pdu_host: str = "192.168.1.102"):
        self.ups_host = ups_host
        self.pdu_host = pdu_host
        self._outlets: List[PDUOutlet] = []

    async def get_power_status(self) -> PowerStatus:
        """Get current power status."""

    async def get_outlet_status(self, outlet_id: int) -> PDUOutlet:
        """Get status of specific outlet."""

    async def set_outlet(self, outlet_id: int, state: OutletState) -> bool:
        """Turn outlet on/off or cycle."""

    async def cycle_outlet(self, outlet_id: int, delay_sec: float = 5.0) -> bool:
        """Power cycle an outlet."""

    async def initiate_safe_shutdown(self, reason: str):
        """
        Initiate graceful shutdown sequence.

        1. Park telescope
        2. Close roof
        3. Save state
        4. Shutdown non-essential devices
        5. Alert operator
        """
        logger.critical(f"Initiating safe shutdown: {reason}")

        # Park telescope first
        await self._park_telescope()

        # Close roof
        await self._close_roof()

        # Save state to disk
        await self._save_state()

        # Turn off non-essential outlets
        await self._shutdown_non_essential()

        # Send alert
        await self._send_shutdown_alert(reason)

    async def monitor_power(self, safety_monitor, alert_manager):
        """
        Continuous power monitoring loop.

        Initiates shutdown when battery critical.
        """
        while True:
            status = await self.get_power_status()

            if status.state == PowerState.CRITICAL:
                await self.initiate_safe_shutdown("Critical battery level")

            elif status.state == PowerState.LOW_BATTERY:
                await alert_manager.raise_from_template(
                    "power_warning",
                    source="power",
                    battery=status.battery_percent,
                    runtime=status.battery_runtime_min
                )

            await asyncio.sleep(30.0)
```

---

## Day 26: Network Resilience

### Focus: Failover, Offline Operation, Recovery

**Morning Session: SRO Team Lead**

**Network Architecture:**
```
┌────────────────────────────────────────────────────────┐
│              NIGHTWATCH Network Architecture            │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Internet ──┬── Starlink (Primary)                    │
│             │                                          │
│             └── LTE Modem (Failover)                  │
│                      │                                 │
│                      ▼                                 │
│              ┌──────────────┐                         │
│              │   Router     │                         │
│              │ (Failover)   │                         │
│              └──────┬───────┘                         │
│                     │                                  │
│              ┌──────▼───────┐                         │
│              │   Switch     │                         │
│              └──────┬───────┘                         │
│                     │                                  │
│    ┌────────────────┼────────────────┐               │
│    │                │                │               │
│    ▼                ▼                ▼               │
│ ┌──────┐      ┌──────────┐    ┌──────────┐          │
│ │DGX   │      │ Telescope │    │ Weather  │          │
│ │Spark │      │ Equipment │    │ Sensors  │          │
│ └──────┘      └──────────┘    └──────────┘          │
│                                                        │
└────────────────────────────────────────────────────────┘
```

**Network Monitor:**
```python
# services/network/network_monitor.py

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

class ConnectionState(Enum):
    CONNECTED = "connected"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    FAILOVER = "failover"

@dataclass
class NetworkStatus:
    """Network connection status."""
    state: ConnectionState
    primary_connected: bool
    failover_connected: bool
    latency_ms: float
    packet_loss_percent: float
    bandwidth_mbps: float
    vpn_connected: bool

class NetworkMonitor:
    """
    Network monitoring and failover for NIGHTWATCH.

    Features:
    - Dual-WAN failover detection
    - VPN health monitoring
    - Offline operation mode
    - Automatic recovery
    """

    def __init__(self):
        self._state = ConnectionState.CONNECTED
        self._offline_queue: List[dict] = []

    async def check_connectivity(self) -> NetworkStatus:
        """Check all network connections."""

    async def queue_for_sync(self, data: dict):
        """Queue data for sync when connection restored."""
        self._offline_queue.append({
            "timestamp": datetime.now().isoformat(),
            "data": data
        })

    async def sync_queued_data(self):
        """Sync queued data when connection restored."""

    async def enter_offline_mode(self):
        """
        Enter offline operation mode.

        Observatory continues autonomous operation,
        queuing data for later sync.
        """
        logger.warning("Entering offline operation mode")
        self._state = ConnectionState.OFFLINE

        # Continue local operation
        # Queue alerts and data for sync

    async def monitor_loop(self):
        """Continuous network monitoring."""
        while True:
            status = await self.check_connectivity()

            if status.state == ConnectionState.OFFLINE:
                await self.enter_offline_mode()
            elif self._state == ConnectionState.OFFLINE:
                # Connection restored
                await self.sync_queued_data()
                self._state = ConnectionState.CONNECTED

            await asyncio.sleep(30.0)
```

---

## Day 27: Spectroscopy Integration

### Focus: Low-Resolution Spectroscopy, Exoplanet Support

**Morning Session: Panel Discussion**

**Spectroscopy Rationale:**
> *Panel Discussion:* "Low-resolution spectroscopy expands NIGHTWATCH capabilities:
> 1. Exoplanet transit spectroscopy (future)
> 2. Variable star classification
> 3. Comet composition analysis
> 4. Educational demonstrations
> 5. Star type identification"

**Spectrograph Service:**
```python
# services/spectroscopy/spectrograph.py

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
import numpy as np

@dataclass
class SpectrumData:
    """Captured spectrum data."""
    wavelengths: np.ndarray    # nm
    flux: np.ndarray           # Relative flux
    timestamp: datetime
    target: str
    exposure_sec: float
    calibrated: bool

@dataclass
class SpectralLines:
    """Identified spectral lines."""
    wavelength: float          # nm
    element: str               # e.g., "H-alpha"
    strength: float            # Relative strength
    redshift: float            # Doppler shift

class Spectrograph:
    """
    Low-resolution spectrograph control for NIGHTWATCH.

    Supports ALPY 600 or similar grating spectrograph.
    """

    # Common spectral lines for calibration
    CALIBRATION_LINES = {
        "H-alpha": 656.28,
        "H-beta": 486.13,
        "Na-D": 589.29,
        "O2-B": 686.72,
    }

    def __init__(self, camera):
        self.camera = camera
        self._calibration = None

    async def capture_spectrum(self,
                              target: str,
                              exposure_sec: float = 60.0) -> SpectrumData:
        """Capture spectrum of current target."""

    async def calibrate_wavelength(self,
                                   calibration_lamp: str = "neon") -> bool:
        """Calibrate wavelength scale using lamp spectrum."""

    async def identify_lines(self,
                            spectrum: SpectrumData) -> List[SpectralLines]:
        """Identify spectral lines in spectrum."""

    async def classify_star(self,
                           spectrum: SpectrumData) -> str:
        """Classify star spectral type (O, B, A, F, G, K, M)."""
```

---

## Day 28: Social & Public Outreach

### Focus: Live Streaming, Social Sharing

**Morning Session: Michael Hansen Lead**

**Public Engagement:**
> *Michael Hansen:* "Public outreach multiplies NIGHTWATCH impact:
> 1. Live stream observing sessions
> 2. Auto-post best captures to social media
> 3. Educational commentary from voice assistant
> 4. Virtual tour mode for remote viewers
> 5. Citizen science participation portal"

**Social Service:**
```python
# services/social/social_manager.py

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
from enum import Enum

class SocialPlatform(Enum):
    TWITTER = "twitter"
    MASTODON = "mastodon"
    YOUTUBE = "youtube"
    DISCORD = "discord"

@dataclass
class SocialPost:
    """Social media post."""
    platform: SocialPlatform
    content: str
    image_path: Optional[Path]
    scheduled_time: Optional[datetime]
    posted: bool = False
    post_id: Optional[str] = None

class SocialManager:
    """
    Social media integration for NIGHTWATCH.

    Auto-posts captures and enables live streaming.
    """

    def __init__(self, config: dict):
        self.config = config
        self._queue: List[SocialPost] = []

    async def post_capture(self,
                          image_path: Path,
                          target: str,
                          quality_score: float):
        """
        Auto-post high-quality capture.

        Only posts if quality exceeds threshold.
        """
        if quality_score < 70.0:
            return

        caption = await self._generate_caption(target, image_path)

        for platform in self.config.get("platforms", []):
            await self._post_to_platform(
                platform,
                caption,
                image_path
            )

    async def start_livestream(self,
                              platform: SocialPlatform,
                              title: str) -> str:
        """Start live stream to platform. Returns stream URL."""

    async def _generate_caption(self,
                               target: str,
                               image_path: Path) -> str:
        """Generate engaging caption for capture."""
        return f"🔭 Tonight's capture: {target}\n\n" \
               f"Captured with NIGHTWATCH autonomous observatory\n" \
               f"#astrophotography #astronomy #{target.lower().replace(' ', '')}"
```

---

## Day 29: Multi-Site Coordination

### Focus: Remote Site Network, Data Sharing

**Morning Session: SRO Team + Panel Discussion**

**Multi-Site Vision:**
> *SRO Team:* "NIGHTWATCH architecture supports multiple sites:
> 1. Central coordination server
> 2. Target deconfliction across sites
> 3. Weather-based site selection
> 4. Combined data products
> 5. Failover to alternate site"

**Site Coordinator:**
```python
# services/multisite/site_coordinator.py

from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass
class ObservatorySite:
    """Remote observatory site."""
    site_id: str
    name: str
    latitude: float
    longitude: float
    altitude: float
    status: str              # "online", "offline", "observing"
    current_target: Optional[str]
    weather_ok: bool
    capabilities: List[str]  # ["imaging", "spectroscopy", etc.]

class SiteCoordinator:
    """
    Multi-site observatory coordination.

    Enables distributed observing network.
    """

    def __init__(self, coordinator_url: str):
        self.coordinator_url = coordinator_url
        self._local_site: Optional[ObservatorySite] = None
        self._network_sites: List[ObservatorySite] = []

    async def register_site(self, site: ObservatorySite):
        """Register this site with coordinator."""

    async def get_network_status(self) -> List[ObservatorySite]:
        """Get status of all sites in network."""

    async def claim_target(self, target: str) -> bool:
        """Claim target to prevent duplication."""

    async def release_target(self, target: str):
        """Release target claim."""

    async def find_best_site(self, target: str) -> Optional[ObservatorySite]:
        """Find best site for observing a target."""

    async def request_handoff(self,
                             target: str,
                             to_site: str) -> bool:
        """Request target handoff to another site."""
```

---

## Day 30: v3.0 Integration & Release

### Morning Session: Full Panel Final Review

**v3.0 Feature Summary:**

| Feature | Lead Specialist | Status | Priority |
|---------|-----------------|--------|----------|
| Auto Focus | Damian Peach | Design Complete | P0 |
| Plate Solving | Bob Denny | Design Complete | P0 |
| Enclosure Control | SRO Team | Design Complete | P0 |
| All-Sky Camera | Antonio García | Design Complete | P1 |
| Power Management | SRO Team | Design Complete | P0 |
| Network Resilience | SRO Team | Design Complete | P1 |
| Spectroscopy | Panel | Design Complete | P2 |
| Social Outreach | Michael Hansen | Design Complete | P2 |
| Multi-Site | SRO Team | Design Complete | P3 |

**v3.0 Architecture:**
```
┌──────────────────────────────────────────────────────────────────────────┐
│                       NIGHTWATCH v3.0 Architecture                        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ Voice   │ │Dashboard│ │ Mobile  │ │ Social  │ │Multi-   │           │
│  │Interface│ │ Web UI  │ │  App    │ │ Stream  │ │Site API │           │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘           │
│       └───────────┴───────────┴───────────┴───────────┘                 │
│                               │                                          │
│                    ┌──────────▼──────────┐                              │
│                    │   NIGHTWATCH Core   │                              │
│                    │  FastAPI + WebSocket │                              │
│                    └──────────┬──────────┘                              │
│                               │                                          │
│  ┌────────────────────────────┼────────────────────────────┐            │
│  │              │             │             │              │            │
│  ▼              ▼             ▼             ▼              ▼            │
│ ┌──────┐    ┌──────┐    ┌──────┐    ┌──────┐    ┌──────┐              │
│ │Mount │    │Camera│    │Guide │    │Focus │    │Plate │              │
│ │Svc   │    │ Svc  │    │ Svc  │    │ Svc  │    │Solve │              │
│ └──┬───┘    └──┬───┘    └──┬───┘    └──┬───┘    └──┬───┘              │
│    │           │           │           │           │                    │
│ ┌──▼───┐    ┌──▼───┐    ┌──▼───┐    ┌──▼───┐    ┌──▼───┐              │
│ │OnStep│    │ASI   │    │PHD2  │    │ZWO   │    │Local │              │
│ │  X   │    │662MC │    │      │    │ EAF  │    │Solver│              │
│ └──────┘    └──────┘    └──────┘    └──────┘    └──────┘              │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │                     Infrastructure Services                     │     │
│  ├────────┬────────┬────────┬────────┬────────┬────────┬────────┤     │
│  │Enclos- │ Power  │Network │All-Sky │Spectro-│Alerts  │Storage │     │
│  │  ure   │Manager │Monitor │ Camera │ graph  │Manager │ Sync   │     │
│  └────────┴────────┴────────┴────────┴────────┴────────┴────────┘     │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Afternoon Session: Implementation Roadmap

**v3.0 Implementation Phases:**
```
Phase 1: Core Automation (Weeks 1-4)
├── Focus service implementation
├── Plate solving integration
├── Enclosure controller
└── Power management

Phase 2: Infrastructure (Weeks 5-8)
├── All-sky camera integration
├── Network resilience
├── Offline operation mode
└── UPS monitoring

Phase 3: Advanced Features (Weeks 9-12)
├── Spectroscopy support
├── Social media integration
├── Live streaming
└── Multi-site foundation

Phase 4: Integration (Weeks 13-16)
├── Full system testing
├── Reliability testing
├── Documentation
└── Public release
```

**v3.0 Release Criteria:**

| Requirement | Metric | Target |
|-------------|--------|--------|
| Focus accuracy | FWHM | <2.5 pixels |
| Plate solve success | Percentage | >98% |
| Roof operation | Reliability | >99.9% |
| Power failover | Time | <10 sec |
| Network failover | Time | <30 sec |
| Uptime | Monthly | >99% |

---

## v3.0 Panel Recommendations Summary

### Critical v3.0 Additions:

1. **Auto Focus (Damian Peach):** Temperature-compensated focusing ensures consistent image quality
2. **Plate Solving (Bob Denny):** Automated pointing verification and correction
3. **Enclosure (SRO Team):** Weather-synchronized roof control for autonomous operation
4. **All-Sky (Antonio García):** Visual sky monitoring complements IR sensor
5. **Power (SRO Team):** Graceful shutdown protects equipment during outages
6. **Network (SRO Team):** Resilient connectivity with offline operation capability

### v3.0 Achievements:
- Fully autonomous operation from sunset to sunrise
- Complete infrastructure control (enclosure, power, network)
- Advanced astrometry with automatic pointing correction
- Weather-synchronized operation with all-sky verification
- Graceful degradation under adverse conditions
- Foundation for multi-site observatory network

---

## Retreat Conclusion (v3.0)

The Panel of Specialists has completed a comprehensive 30-day design retreat for NIGHTWATCH v3.0. This final phase establishes NIGHTWATCH as a fully autonomous, infrastructure-complete observatory capable of unattended operation.

**Unanimous Panel Assessment:** NIGHTWATCH v3.0 achieves the original vision of a completely autonomous telescope observatory that can operate independently from sunset to sunrise, making intelligent decisions about safety, targets, and data quality.

**Key v3.0 Achievements:**
- Automated focus control with temperature compensation
- Plate solving for pointing verification and correction
- Roll-off roof automation with weather synchronization
- All-sky camera for visual sky monitoring
- Complete power management with graceful shutdown
- Network resilience with offline operation capability
- Spectroscopy support for advanced science
- Social media integration for public outreach
- Multi-site coordination foundation

**Final Recommendation:**
The panel unanimously recommends NIGHTWATCH for deployment. The design is comprehensive, well-tested, and ready for construction. The modular architecture allows phased implementation while maintaining full functionality at each stage.

---

*Panel of Specialists Retreat - January 2026*
*Document Version: 3.0*
*Days 1-10: Foundation & v1.0*
*Days 11-20: Advanced Features & v2.0*
*Days 21-30: Full Automation & v3.0*
