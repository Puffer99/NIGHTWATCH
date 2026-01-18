# Project NIGHTWATCH
## Autonomous Mak-Newt Observatory System
### Combined Build Package: Russian Giant × Autonomous Station
### Central Nevada Dark Sky Permanent Installation

---

## Document Purpose

This document serves as the complete specification and research handoff for an autonomous telescope system combining the optical excellence of the Intes-Micro MN78 Maksutov-Newtonian with the automation infrastructure of a fully encoder-equipped, weather-aware observatory. The target environment is an isolated dark sky property in central Nevada with no neighbors, enabling permanent installation without constraints on noise, light, or operating hours.

This package is designed to be unpacked by Claude Code for:
1. Component research and sourcing
2. Mechanical design completion
3. Electrical system design
4. Software architecture development
5. Build sequence planning
6. Integration testing protocols

---

## Executive Summary

### Core Philosophy

NIGHTWATCH merges two distinct telescope philosophies into a single coherent system:

**From the Russian Giant (#2):** The Intes-Micro MN78 represents peak optical engineering in an unusual configuration. The 7-inch f/6 Maksutov-Newtonian combines closed-tube thermal stability with fast Newtonian-class focal ratios and minimal central obstruction. Hand-figured Russian optics deliver planetary performance that rivals APO refractors at a fraction of the cost-per-inch. The closed tube is ideal for Nevada's dusty, high-temperature-swing desert environment.

**From the Autonomous Station (#15):** Full encoder feedback on both axes enables precise positioning without drift or lost-step concerns. Weather awareness through integrated sensors allows autonomous operation decisions. All-sky camera provides cloud monitoring and session logging. The system can operate unattended within defined safety parameters, capturing data while the owner sleeps or is off-property.

### Primary Use Cases

| Priority | Use Case | Rating Target |
|----------|----------|---------------|
| 1 | Mars surface feature observation | 5/5 |
| 2 | Lucky imaging (high-speed planetary capture) | 5/5 |
| 3 | Autonomous overnight operation | 5/5 |
| 4 | Remote monitoring and control | 5/5 |
| 5 | Dark sky deep-sky visual (bonus) | 4/5 |

### Key Specifications Summary

| Parameter | Specification |
|-----------|---------------|
| Optical Tube Assembly | Intes-Micro MN78 (178mm f/6 Mak-Newt) |
| Focal Length | 1068mm native, 2136mm+ with Barlow |
| Mount Type | DIY German Equatorial, harmonic drive |
| Payload Capacity | 25 kg (55 lb) minimum |
| Tracking Accuracy | Sub-arcsecond with encoder feedback |
| Encoder Type | Absolute encoders, both axes |
| Controller | OnStepX on STM32/Teensy 4.1 |
| Voice Integration | DGX Spark local inference |
| Weather Awareness | Full station with cloud sensor |
| Remote Access | Network-enabled, VPN secured |
| Installation | Permanent concrete pier |
| Budget Target | $8,500 - $9,500 |

---

## Optical Tube Assembly

### Intes-Micro MN78 Specifications

The MN78 is the flagship planetary instrument from Intes-Micro, a Russian manufacturer with four decades of experience producing premium amateur optics. The Maksutov-Newtonian design uses a full-aperture meniscus corrector (like a Maksutov-Cassegrain) but routes light to a Newtonian-style side-mounted focuser rather than through a hole in the primary.

| Parameter | Specification |
|-----------|---------------|
| Manufacturer | Intes-Micro (Russia) |
| Design | Maksutov-Newtonian |
| Aperture | 178mm (7.0 inches) |
| Focal Length | 1068mm |
| Focal Ratio | f/6 |
| Central Obstruction | ~25% by diameter |
| Corrector | Full-aperture meniscus |
| Primary Mirror | Spherical (corrector handles aberration) |
| Secondary Mirror | Flat diagonal |
| Focuser | 2" Crayford, 10:1 fine focus |
| Tube Material | Aluminum, closed design |
| Tube Length | ~700mm |
| Weight | ~9 kg (19.8 lb) |
| Dovetail | Losmandy-style recommended |

### Why This OTA

**Optical Quality:** Intes-Micro hand-figures optics to 1/8 wave or better. The Mak-Newt design eliminates coma (the bane of fast Newtonians) while maintaining faster focal ratios than Mak-Cass designs. The 25% central obstruction is significantly smaller than typical SCTs (33-35%), yielding superior contrast transfer at medium spatial frequencies—exactly where planetary detail lives.

**Thermal Behavior:** The closed tube design is critical for Nevada. Open-tube Newtonians suffer from thermal currents rising off the mirror when ambient temperature drops. The MN78's sealed tube dramatically reduces this effect. The corrector plate acts as a thermal buffer. While cooldown time exceeds open designs, a permanent installation can pre-equilibrate hours before observing.

**Mechanical Robustness:** The closed tube protects optics from dust, insects, and the occasional curious wildlife. Nevada's alkaline dust is particularly damaging to exposed optical surfaces. The MN78 can remain on its pier under a cover for months without optical degradation.

**Focal Ratio Sweet Spot:** At f/6, the MN78 is fast enough for efficient lucky imaging (good frame rates) while slow enough that the optical design remains manageable. Faster Mak-Newts exist but become significantly more expensive and thermally challenging.

### Sourcing Research Tasks

```
RESEARCH_TASK: MN78_SOURCING
Priority: HIGH
Objective: Identify current availability and pricing for Intes-Micro MN78

Search targets:
- Intes-Micro direct (Russia) - inquire about export process
- APM Telescopes (Germany) - known Intes distributor
- Telescope Service (Germany) - European dealer network
- Astronomics (USA) - check if carrying Intes
- Used market: Cloudy Nights classifieds, Astromart, eBay
- Russian astronomy forums (may require translation)

Data to collect:
- Current new price (if available)
- Typical used price range
- Lead time for new orders
- Shipping logistics from Russia/Europe to USA
- Import duties and customs considerations
- Warranty terms and service options
- Alternative: Intes-Micro MN66 (6" f/6) if MN78 unavailable

Expected price range: $2,200 - $3,000 new, $1,500 - $2,200 used
```

### Optical Accessories

| Component | Specification | Purpose | Est. Cost |
|-----------|---------------|---------|-----------|
| Diagonal | Baader 2" Maxbright II or equiv | Visual observing | $200-280 |
| Barlow | Tele Vue 2x Powermate | 2136mm f/12 config | $290 |
| IR-Pass Filter | Baader IR-Pass 685nm | Atmospheric dispersion reduction | $80 |
| ADC | ZWO Atmospheric Dispersion Corrector | Low-altitude planetary | $180 |
| Eyepiece Set | Tele Vue Delos 4.5mm, 8mm, 14mm | High-end visual | $900 |
| Planetary Camera | ZWO ASI662MC or Player One Mars-C II | Lucky imaging | $350-400 |

---

## Mount System

### Design Philosophy

The mount is the heart of any serious telescope installation. For NIGHTWATCH, we're building a German Equatorial Mount (GEM) using harmonic (strain wave) drives on both axes, with absolute encoder feedback, controlled by OnStepX firmware. The goal is professional-grade tracking accuracy in a DIY package that can be built, maintained, and upgraded by the owner.

### Harmonic Drive Selection

Harmonic drives (strain wave gears) provide zero-backlash motion transmission with high reduction ratios in compact packages. They're used in industrial robotics, satellite pointing systems, and increasingly in premium amateur telescope mounts.

| Axis | Drive Model | Ratio | Torque Rating | Est. Cost |
|------|-------------|-------|---------------|-----------|
| RA | CSF-32-100-2A-GR | 100:1 | 127 Nm | $580 |
| DEC | CSF-25-80-2A-GR | 80:1 | 70 Nm | $450 |

**Sizing Rationale:**

The MN78 weighs ~9 kg. Add counterweights (~9 kg), dovetail, accessories, and cameras: total rotating mass ~22 kg. The CSF-32 on RA is rated for significantly higher loads, providing safety margin for:
- Future heavier OTAs
- Wind loading
- Asymmetric accessory mounting
- Long-term reliability

The CSF-25 on DEC sees less continuous load (no tracking torque) and can be slightly smaller.

```
RESEARCH_TASK: HARMONIC_DRIVE_SOURCING
Priority: HIGH
Objective: Source CSF-series harmonic drives at best price

Search targets:
- Harmonic Drive LLC (USA) - OEM distributor
- eBay sellers (new/surplus units)
- Alibaba suppliers (verify authenticity)
- Robot parts suppliers (FIRST Robotics channels)
- Surplus electronics dealers

Verify:
- Exact model numbers match (CSF-XX-XXX-2A-GR series)
- New vs. refurbished vs. pulled from equipment
- Component set completeness (wave generator, flexspline, circular spline)
- Input/output shaft configurations
- Mounting flange dimensions

Alternative: Leadshine/LMI harmonic drives (Chinese) at lower cost
Risk assessment needed for non-Harmonic Drive LLC units
```

### Motor Selection

| Axis | Motor | Gearbox | Combined Ratio | Est. Cost |
|------|-------|---------|----------------|-----------|
| RA | NEMA17 stepper (1.8°/step) | 27:1 planetary | 2700:1 total | $80 |
| DEC | NEMA17 stepper (1.8°/step) | 27:1 planetary | 2160:1 total | $80 |

**Calculation:**

RA axis must complete 360° in 23h 56m 4s (sidereal day) = 86164 seconds.

With 2700:1 total reduction:
- Motor must rotate 2700 × 360° = 972,000° in 86164 seconds
- Motor speed = 972,000 / 86164 = 11.28°/second = 1.88 RPM

This is well within stepper capability. At 200 steps/rev (1.8° motor) with 16x microstepping:
- 3200 microsteps/rev
- Step rate = 3200 × 1.88 / 60 = 100 steps/second

Comfortable for silent, smooth operation.

### Motor Driver Selection

| Component | Model | Features | Est. Cost |
|-----------|-------|----------|-----------|
| Stepper Drivers | TMC5160 (×2) | Silent operation, StealthChop, encoder input | $50 each |

**TMC5160 Rationale:**

The TMC5160 is Trinamic's flagship stepper driver, featuring:
- StealthChop2: Near-silent operation at low speeds (critical for tracking)
- SpreadCycle: High-torque mode for slewing
- Stall detection: Motor protection
- Integrated encoder interface: Direct feedback to driver
- SPI control: Full parameter access from OnStepX

For a site with no neighbors, silence isn't strictly necessary, but TMC5160s also provide superior low-speed smoothness that translates to better tracking.

### Encoder Selection

| Axis | Encoder Type | Resolution | Interface | Est. Cost |
|------|--------------|------------|-----------|-----------|
| RA | AMT103-V (CUI Devices) | 8192 PPR | Quadrature | $50 |
| DEC | AMT103-V (CUI Devices) | 8192 PPR | Quadrature | $50 |

**Alternative for absolute positioning:**

| Axis | Encoder Type | Resolution | Interface | Est. Cost |
|------|--------------|------------|-----------|-----------|
| Both | AS5600 magnetic | 12-bit (4096 positions) | I2C/Analog | $5 each |

**Encoder Strategy:**

Two levels of feedback are possible:

1. **Motor-side encoders (AMT103):** Mount on motor shaft before gearbox. Detect motor movement, not final axis position. High resolution, catches skipped steps, but doesn't measure backlash or flex.

2. **Axis-side encoders (AS5600 or Renishaw):** Mount on final output shaft. Measure true telescope pointing. Lower effective resolution after gear reduction, but capture full mechanical chain.

For NIGHTWATCH, recommend **both**:
- AMT103 on motors for step verification
- AS5600 on output shafts for absolute position

OnStepX supports dual-encoder configurations.

```
RESEARCH_TASK: ENCODER_ARCHITECTURE
Priority: MEDIUM
Objective: Design encoder mounting and integration strategy

Questions to resolve:
- AS5600 magnet mounting on RA/DEC output shafts
- AMT103 coupling to motor shaft (flex coupling or direct)
- OnStepX configuration for dual-encoder operation
- Calibration procedure for absolute encoders
- Homing routine if using incremental encoders only
- Index pulse utilization strategy

Reference designs:
- OnStep forum encoder discussions
- 10 Micron mount encoder architecture
- iOptron CEM encoder implementation
```

### Mechanical Frame Design

The mount frame must be:
- Rigid enough to avoid flexure under load
- Machinable from common aluminum stock
- Compatible with standard bearings
- Mountable on a pier adapter plate

**Proposed Architecture:**

```
                    ┌─────────────────┐
                    │   Dovetail      │
                    │   Saddle        │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │   DEC Axis      │
                    │   Housing       │
                    │  (CSF-25-80)    │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              │      RA Axis Housing        │
              │       (CSF-32-100)          │
              │                             │
              └──────────────┬──────────────┘
                             │
                    ┌────────┴────────┐
                    │   Pier Adapter  │
                    │   Plate         │
                    └─────────────────┘
```

**Material Specifications:**

| Component | Material | Stock Size | Process |
|-----------|----------|------------|---------|
| RA Housing | 6061-T6 Aluminum | 8" × 8" × 3" plate | CNC mill |
| DEC Housing | 6061-T6 Aluminum | 6" × 6" × 2.5" plate | CNC mill |
| Counterweight Shaft | 303 Stainless | 1.25" diameter rod | Lathe |
| Pier Adapter | 6061-T6 Aluminum | 10" × 10" × 0.75" plate | Waterjet + drill |
| Dovetail Saddle | 6061-T6 Aluminum | Losmandy D profile | Purchase or mill |

**Bearing Selection:**

| Location | Bearing Type | Size | Quantity | Est. Cost |
|----------|--------------|------|----------|-----------|
| RA Output | Angular contact pair | 6008-2RS | 2 | $40 |
| DEC Output | Angular contact pair | 6006-2RS | 2 | $30 |
| RA Input | Deep groove | 608-2RS | 2 | $5 |
| DEC Input | Deep groove | 606-2RS | 2 | $5 |

```
RESEARCH_TASK: FRAME_DESIGN
Priority: HIGH
Objective: Complete mechanical design for mount frame

Deliverables needed:
- CAD models (Fusion 360 or FreeCAD) of all frame components
- Bearing bore and shoulder dimensions
- Harmonic drive mounting bolt patterns
- Motor mounting provisions
- Encoder mounting provisions
- Cable routing channels
- Counterweight shaft attachment method
- Dovetail saddle interface specification
- Pier adapter bolt pattern (standard or custom)
- Tolerance analysis for bearing preload
- FEA analysis of deflection under 25 kg load

Reference designs:
- OpenAstroMount project
- OnStep community mount builds
- Losmandy G11 architecture (for dovetail interface)
- Avalon M-Uno (harmonic drive commercial reference)
```

### Counterweight System

| Component | Specification | Est. Cost |
|-----------|---------------|-----------|
| Shaft | 1.25" stainless, 18" long | $40 |
| Weights | 2 × 5 kg, 1 × 2.5 kg standard | $60 |
| Safety Stop | Threaded end cap | $10 |

Standard 1.25" shaft accommodates most aftermarket counterweights.

---

## Control Electronics

### Controller Selection

**Primary Controller: STM32F411 BlackPill or Teensy 4.1**

OnStepX supports multiple microcontrollers. For NIGHTWATCH, the Teensy 4.1 is recommended:

| Feature | Teensy 4.1 | STM32F411 |
|---------|------------|-----------|
| Clock Speed | 600 MHz | 100 MHz |
| RAM | 1024 KB | 128 KB |
| Flash | 8 MB | 512 KB |
| Native USB | Yes | Yes |
| Ethernet | Via add-on | No |
| WiFi | Via add-on | Via add-on |
| Price | $30 | $8 |

The Teensy's additional resources support:
- Dual encoder feedback processing
- Network stack for remote access
- Future expansion (autoguiding, dome control)

### OnStepX Configuration

OnStepX is the evolution of the OnStep telescope controller firmware. Key configuration parameters for NIGHTWATCH:

```cpp
// Config.h excerpts for NIGHTWATCH

// RA Axis
#define AXIS1_DRIVER_MODEL      TMC5160
#define AXIS1_STEPS_PER_DEGREE  (200 * 16 * 27 * 100 / 360.0)  // ~24000 steps/degree
#define AXIS1_ENCODER           ON
#define AXIS1_ENCODER_PPR       8192

// DEC Axis  
#define AXIS2_DRIVER_MODEL      TMC5160
#define AXIS2_STEPS_PER_DEGREE  (200 * 16 * 27 * 80 / 360.0)   // ~19200 steps/degree
#define AXIS2_ENCODER           ON
#define AXIS2_ENCODER_PPR       8192

// Tracking
#define TRACK_AUTOSTART         ON
#define TRACK_REFRACTION_TYPE   REFRACTION_CALC_FULL

// Goto
#define GOTO_RATE               4.0   // degrees/second
#define GOTO_ACCELERATION       2.0   // degrees/second^2

// Site
#define SITE_LATITUDE_DEFAULT   39.0  // Central Nevada approximate
#define SITE_LONGITUDE_DEFAULT  -117.0

// Network
#define SERIAL_IP_MODE          ETHERNET
```

```
RESEARCH_TASK: ONSTEPX_CONFIGURATION
Priority: HIGH
Objective: Complete OnStepX configuration for NIGHTWATCH hardware

Tasks:
- Verify step rate calculations for chosen gear ratios
- Configure TMC5160 driver parameters (current limits, StealthChop thresholds)
- Test encoder feedback integration
- Configure network stack (Ethernet or WiFi)
- Set up LX200 protocol compatibility
- Test ASCOM driver connectivity
- Configure PEC (Periodic Error Correction) parameters
- Set up meridian flip logic
- Configure park positions
- Implement homing routine with absolute encoders

Reference:
- OnStepX GitHub repository and wiki
- OnStep Groups.io forum
- Specific TMC5160 application notes
```

### Electronics Housing

| Component | Specification | Est. Cost |
|-----------|---------------|-----------|
| Enclosure | IP65 aluminum box, 200×150×75mm | $40 |
| Power Distribution | 12V 10A, 5V 3A rails | $30 |
| Fusing | Blade fuses, per-subsystem | $10 |
| Connectors | Aviation plugs (GX12/GX16) | $30 |
| Cable Glands | IP68 rated | $15 |

**Power Architecture:**

```
AC Input (120V) ──► Outdoor-rated junction box
                           │
                           ▼
                   ┌───────────────┐
                   │ 12V 20A PSU   │
                   └───────┬───────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ Mount    │    │ Camera   │    │ Aux 12V  │
    │ 12V 5A   │    │ 12V 3A   │    │ 12V 2A   │
    └──────────┘    └──────────┘    └──────────┘
           │
           ▼
    ┌──────────┐
    │ 5V 3A    │ (stepped down for Teensy, encoders)
    │ Buck     │
    └──────────┘
```

---

## Weather Awareness System

### Core Components

| Component | Model | Function | Est. Cost |
|-----------|-------|----------|-----------|
| Weather Station | Ecowitt WS90 | Wind, rain, temp, humidity, UV | $150 |
| Cloud Sensor | AAG CloudWatcher Solo | IR sky temp differential | $400 |
| All-Sky Camera | ZWO ASI120MM Mini + fisheye | Visual cloud monitoring | $200 |
| Rain Sensor | Hydreon RG-11 | Backup rain detection | $60 |

### Weather Station Details

The Ecowitt WS90 is a consumer weather station with:
- Ultrasonic wind sensor (no moving parts, desert-friendly)
- Integrated rain gauge
- Temperature/humidity sensor
- Solar radiation sensor
- WiFi connectivity to Ecowitt cloud + local API

**Integration Path:**

Ecowitt provides a local HTTP API. A Python service on the DGX Spark polls the station and makes decisions:

```python
# weather_monitor.py pseudocode

def check_conditions():
    data = fetch_ecowitt_api()
    
    if data['rain_rate'] > 0:
        return SafetyStatus.CLOSE_IMMEDIATELY
    
    if data['wind_speed'] > 25:  # mph
        return SafetyStatus.PARK_AND_CLOSE
    
    if data['humidity'] > 85:
        return SafetyStatus.DEW_WARNING
    
    if data['temperature'] < 20:  # °F
        return SafetyStatus.COLD_WARNING
    
    return SafetyStatus.SAFE_TO_OBSERVE
```

### Cloud Sensor Details

The AAG CloudWatcher measures infrared sky temperature. Clear sky reads significantly colder than ambient (IR radiates to space). Clouds read warmer (IR trapped/re-emitted).

| Condition | Sky-Ambient Differential |
|-----------|--------------------------|
| Clear | < -25°C |
| Partly Cloudy | -25°C to -15°C |
| Cloudy | -15°C to -5°C |
| Overcast | > -5°C |

The CloudWatcher outputs:
- Serial data stream (RS-232)
- Relay contacts (for direct automation)

```
RESEARCH_TASK: CLOUD_SENSOR_INTEGRATION
Priority: MEDIUM
Objective: Integrate AAG CloudWatcher with NIGHTWATCH automation

Tasks:
- Serial protocol documentation review
- Python driver for CloudWatcher serial stream
- Calibration procedure for Nevada altitude/humidity
- Threshold tuning for local conditions
- Integration with safety logic
- Relay output wiring for backup automation

Alternative evaluation:
- DIY cloud sensor (MLX90614 IR thermometer)
- Cost savings vs. AAG CloudWatcher reliability
- Weatherproofing requirements for DIY solution
```

### All-Sky Camera

The all-sky camera provides:
- Visual confirmation of sky conditions
- Time-lapse cloud motion tracking
- Meteor/satellite capture (bonus)
- Remote session monitoring

| Component | Specification | Est. Cost |
|-----------|---------------|---------|
| Camera | ZWO ASI120MM Mini | $150 |
| Lens | 1.55mm fisheye (180° FOV) | $30 |
| Housing | 3D printed or acrylic dome | $20 |
| Dew Heater | Resistor ring, 2W | $10 |

**Software Stack:**

AllSky (open source) provides:
- Automatic day/night exposure switching
- Keogram generation (time vs. azimuth strip)
- Startrails compositing
- Web interface for remote viewing
- Timelapse video generation

```
RESEARCH_TASK: ALLSKY_DEPLOYMENT
Priority: LOW
Objective: Deploy all-sky camera system

Tasks:
- AllSky software installation on Raspberry Pi
- Camera driver configuration
- Lens focus setting (infinity)
- Housing weatherproofing
- Network integration for remote viewing
- Optional: integrate feed into NIGHTWATCH dashboard
```

---

## Remote Access and Automation

### Network Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     NIGHTWATCH Network                          │
│                                                                 │
│   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐   │
│   │ DGX Spark   │◄────►│   Router    │◄────►│  Internet   │   │
│   │ (Primary)   │      │ (Starlink?) │      │             │   │
│   └──────┬──────┘      └─────────────┘      └─────────────┘   │
│          │                    ▲                                 │
│          │                    │                                 │
│   ┌──────┴──────┐      ┌─────┴─────┐                          │
│   │   OnStepX   │      │ Ecowitt   │                          │
│   │   Teensy    │      │ Gateway   │                          │
│   └──────┬──────┘      └───────────┘                          │
│          │                                                      │
│   ┌──────┴──────┐      ┌───────────┐      ┌───────────┐       │
│   │  Ethernet   │      │ AllSky    │      │CloudWatch │       │
│   │  (mount)    │      │ RPi       │      │ (serial)  │       │
│   └─────────────┘      └───────────┘      └───────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Remote Access Strategy

| Method | Purpose | Security |
|--------|---------|----------|
| WireGuard VPN | Secure tunnel to property network | Strong encryption |
| SSH | Command-line access to DGX Spark | Key-based auth only |
| VNC/RDP | GUI access for imaging software | Via VPN only |
| INDI Web Manager | Telescope/camera control | Via VPN only |

**Starlink Considerations:**

Central Nevada likely requires Starlink for internet connectivity. Key considerations:
- CGNAT (Carrier-Grade NAT) blocks incoming connections
- Solution: WireGuard tunnel to external VPS, or Starlink business plan
- Latency: 20-40ms typical, acceptable for remote control
- Bandwidth: Sufficient for live camera feeds

```
RESEARCH_TASK: NETWORK_INFRASTRUCTURE
Priority: MEDIUM
Objective: Design reliable remote access architecture

Tasks:
- Starlink service availability at target location
- CGNAT workaround options (VPS relay, Starlink business)
- WireGuard server configuration
- Automatic reconnection handling
- Bandwidth requirements for camera feeds
- Failsafe behavior when network is down
- Power backup for network equipment
```

### Automation Logic

The DGX Spark runs the automation brain. Core logic:

```python
# observatory_controller.py pseudocode

class ObservatoryState(Enum):
    CLOSED = "closed"
    OPENING = "opening"
    OPEN = "open"
    OBSERVING = "observing"
    PARKING = "parking"
    EMERGENCY_CLOSE = "emergency_close"

class SafetyMonitor:
    def evaluate(self):
        weather = self.weather_station.get_conditions()
        clouds = self.cloud_sensor.get_status()
        sun = self.ephemeris.sun_altitude()
        
        if weather.rain_detected:
            return Action.EMERGENCY_CLOSE
        
        if weather.wind_speed > WIND_LIMIT:
            return Action.PARK_AND_CLOSE
        
        if clouds.status == CloudStatus.OVERCAST:
            return Action.PARK_AND_WAIT
        
        if sun > -12:  # Astronomical twilight
            return Action.PARK_FOR_DAYLIGHT
        
        return Action.SAFE_TO_OBSERVE

class SessionManager:
    def run_scheduled_session(self, session):
        while session.has_targets():
            if self.safety.evaluate() != Action.SAFE_TO_OBSERVE:
                self.handle_unsafe_condition()
                continue
            
            target = session.next_target()
            self.mount.goto(target.coordinates)
            self.camera.capture_sequence(target.exposure_plan)
            self.log_observation(target)
```

---

## Voice Control Integration

### Architecture (from NVIDIA Michael Clive reference)

```
┌─────────────────────────────────────────────────────────────────┐
│                     DGX Spark Voice Pipeline                     │
│                                                                 │
│   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐   │
│   │ Microphone  │─────►│   Whisper   │─────►│    LLM      │   │
│   │   Array     │      │    STT      │      │ (Llama 3.x) │   │
│   └─────────────┘      └─────────────┘      └──────┬──────┘   │
│                                                     │           │
│                              ┌──────────────────────┘           │
│                              │                                  │
│                              ▼                                  │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                   Tool Orchestration                     │  │
│   │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────┐ │  │
│   │  │ Catalog   │ │ Ephemeris │ │ Coordinate│ │ Mount   │ │  │
│   │  │ Lookup    │ │ Service   │ │ Transform │ │ Control │ │  │
│   │  └───────────┘ └───────────┘ └───────────┘ └─────────┘ │  │
│   └─────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│   ┌─────────────┐      ┌─────────────┐                        │
│   │   TTS       │◄─────│  Response   │                        │
│   │ (Piper/etc) │      │  Generator  │                        │
│   └──────┬──────┘      └─────────────┘                        │
│          │                                                      │
│          ▼                                                      │
│   ┌─────────────┐                                              │
│   │  Speakers   │                                              │
│   └─────────────┘                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Microservices Definition

| Service | Function | Implementation |
|---------|----------|----------------|
| Catalog Lookup | NGC, IC, Messier, named stars, planets | SQLite + Skyfield |
| Ephemeris | Planet/Moon/satellite positions | Skyfield + TLE database |
| Coordinate Transform | J2000 ↔ JNow, precession, nutation, refraction | Skyfield/ERFA |
| Mount Control | LX200 protocol generation, status parsing | Serial/TCP to OnStepX |
| Weather Query | Current conditions, forecast | API to Ecowitt + NWS |
| Session Log | Observation recording, target tracking | SQLite + filesystem |

### Example Voice Commands

| User Says | System Action |
|-----------|---------------|
| "Point at Mars" | Ephemeris → Coordinate → Mount GOTO |
| "What's visible tonight?" | Ephemeris → filter by altitude/time → respond |
| "Start lucky imaging session" | Camera control → begin capture sequence |
| "What's the wind speed?" | Weather service → respond |
| "Park the telescope" | Mount control → park command |
| "Is it safe to observe?" | Safety monitor → evaluate → respond |
| "Show me Messier 31" | Catalog → Coordinate → Mount GOTO |
| "What am I pointed at?" | Mount position → Coordinate inverse → Catalog → respond |

```
RESEARCH_TASK: VOICE_PIPELINE_IMPLEMENTATION
Priority: MEDIUM
Objective: Implement voice control pipeline on DGX Spark

Tasks:
- Whisper model selection and optimization for Spark
- LLM selection (Llama 3.x 8B or similar)
- Tool definition schema (function calling format)
- Skyfield integration for ephemeris/coordinates
- SQLite catalog database design
- LX200 protocol client library
- TTS engine selection (Piper, Coqui, etc.)
- Wake word detection (optional)
- Noise handling for outdoor environment
- Latency optimization (<2 second response target)

Reference:
- Michael Clive NVIDIA telescope video
- Skyfield documentation
- LX200 protocol specification
- OnStepX serial command reference
```

---

## Pier and Infrastructure

### Concrete Pier Specification

| Parameter | Specification |
|-----------|---------------|
| Diameter | 12" (Sonotube form) |
| Depth | 36" below grade (frost line + stability) |
| Above Grade | 36" (adjustable to site) |
| Concrete | 4000 PSI, fiber-reinforced |
| Rebar | #4 vertical (4), #3 hoop (3 levels) |
| J-Bolts | 5/8"-11 × 10", (4) in square pattern |
| Top Plate | 3/8" steel, 12" × 12" |

**Construction Sequence:**

1. Excavate 18" diameter hole, 36" deep
2. Set Sonotube form, level
3. Install rebar cage
4. Pour concrete to 6" below final height
5. Set J-bolt template, verify square
6. Pour remaining concrete, finish top
7. Cure 7 days minimum
8. Attach steel adapter plate
9. Shim for final level

```
RESEARCH_TASK: PIER_DESIGN
Priority: LOW
Objective: Complete pier construction documentation

Tasks:
- Final dimension drawing
- J-bolt template fabrication drawing
- Steel plate drilling pattern
- Leveling shim system design
- Grounding electrode installation
- Conduit stub for power/data
- Moisture barrier considerations
- Frost heave risk assessment for Nevada site
```

### Shelter Options

For weather protection when not observing:

| Option | Est. Cost | Pros | Cons |
|--------|-----------|------|------|
| Roll-off Roof Shed | $2,000-3,500 | Full sky access, simple | Requires track system |
| Clamshell Dome | $3,000-5,000 | Weatherproof, wind protection | Limited sky access |
| Scope Cover Only | $100-200 | Cheapest | No human shelter |

**Recommendation for Phase 1:** Scope cover only. Observatory structure can be added later.

---

## Budget Summary

### Core System

| Category | Component | Est. Cost |
|----------|-----------|-----------|
| **Optics** | Intes-Micro MN78 | $2,400 |
| | Baader 2" diagonal | $250 |
| | Tele Vue 2x Powermate | $290 |
| | ZWO ADC | $180 |
| | Baader IR-Pass 685nm | $80 |
| | Tele Vue Delos eyepieces (3) | $900 |
| | ZWO ASI662MC camera | $400 |
| **Subtotal Optics** | | **$4,500** |
| **Mount** | CSF-32-100 harmonic drive | $580 |
| | CSF-25-80 harmonic drive | $450 |
| | NEMA17 motors + gearboxes (2) | $160 |
| | TMC5160 drivers (2) | $100 |
| | AMT103 encoders (2) | $100 |
| | AS5600 absolute encoders (2) | $20 |
| | Teensy 4.1 + Ethernet | $50 |
| | Bearings, hardware | $100 |
| | Aluminum stock (frame) | $200 |
| | Machining services | $400 |
| | Counterweight system | $110 |
| | Electronics enclosure + power | $125 |
| **Subtotal Mount** | | **$2,395** |
| **Automation** | Ecowitt WS90 weather station | $150 |
| | AAG CloudWatcher Solo | $400 |
| | ZWO ASI120MM + fisheye | $200 |
| | Hydreon RG-11 rain sensor | $60 |
| **Subtotal Automation** | | **$810** |
| **Infrastructure** | Concrete pier materials | $200 |
| | Pier steel plate + hardware | $100 |
| | Power distribution | $100 |
| | Network equipment | $100 |
| | Cables, connectors | $100 |
| **Subtotal Infrastructure** | | **$600** |

### Total Budget

| Category | Amount |
|----------|--------|
| Optics | $4,500 |
| Mount | $2,395 |
| Automation | $810 |
| Infrastructure | $600 |
| **TOTAL** | **$8,305** |
| Contingency (15%) | $1,245 |
| **TOTAL WITH CONTINGENCY** | **$9,550** |

*Note: DGX Spark not included (owned separately)*

---

## Build Phases

### Phase 1: Mount Mechanical (Weeks 1-6)

**Objectives:**
- Complete mechanical CAD design
- Source harmonic drives
- Machine frame components
- Assemble mount mechanical system

**Deliverables:**
- Functional mount that can be manually moved
- Counterweight system operational
- Dovetail saddle mounted

**Exit Criteria:**
- Mount holds OTA weight without slipping
- Axes move smoothly through full range
- No binding at any position

### Phase 2: Mount Electronics (Weeks 7-10)

**Objectives:**
- Wire motors and encoders
- Flash OnStepX firmware
- Configure tracking parameters
- Test goto accuracy

**Deliverables:**
- Motorized mount responding to OnStepX commands
- Encoder feedback operational
- Sidereal tracking functional

**Exit Criteria:**
- Goto accuracy within 10 arcminutes (before polar alignment)
- Sidereal tracking holds target for 5+ minutes
- No motor stalls or lost steps during operation

### Phase 3: OTA Integration (Weeks 11-12)

**Objectives:**
- Mount MN78 on system
- Balance on both axes
- Initial collimation check
- First light observation

**Deliverables:**
- Complete telescope system operational
- Visual observation of bright star (focus test)
- Planetary observation test (if available)

**Exit Criteria:**
- Stars focus to diffraction limit
- Mount tracks and gotos function under load
- System is stable for manual observing sessions

### Phase 4: Pier Installation (Weeks 13-16)

**Objectives:**
- Pour concrete pier at Nevada site
- Install electrical service
- Network connectivity operational
- Mount telescope on pier

**Deliverables:**
- Permanent pier installation
- Power and network at pier
- Telescope operational on-site

**Exit Criteria:**
- Pier is level and stable
- Polar alignment achieved
- Remote network access functional

### Phase 5: Automation Integration (Weeks 17-22)

**Objectives:**
- Install weather station
- Install cloud sensor
- Deploy all-sky camera
- Implement safety logic on DGX Spark
- Test autonomous operation

**Deliverables:**
- Full automation stack operational
- Safety logic prevents damage conditions
- Remote monitoring functional

**Exit Criteria:**
- System correctly parks on unsafe weather
- Cloud sensor triggers appropriate responses
- All-sky camera streaming to remote interface

### Phase 6: Voice Integration (Weeks 23-26)

**Objectives:**
- Deploy voice pipeline on DGX Spark
- Implement catalog and ephemeris services
- Test voice command recognition
- Tune response latency

**Deliverables:**
- Functional voice control
- Natural language telescope control
- Catalog lookups and gotos via voice

**Exit Criteria:**
- Voice commands recognized in outdoor environment
- End-to-end latency under 2 seconds
- Successful voice-commanded observation session

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| MN78 unavailable/long lead time | Medium | High | Identify backup OTAs, monitor used market |
| Harmonic drive sourcing issues | Low | High | Multiple supplier research, budget for premium pricing |
| Machining quality problems | Medium | Medium | Use reputable shop, inspect before assembly |
| OnStepX configuration difficulty | Medium | Medium | Engage OnStep community early, study reference configs |
| Nevada site access limitations | Low | High | Confirm property access before pier construction |
| Network connectivity issues | Medium | Medium | Starlink backup, local operation fallback |
| Weather sensor false positives | Medium | Low | Multiple sensor redundancy, tunable thresholds |
| Voice recognition outdoor challenges | Medium | Low | Noise cancellation, push-to-talk fallback |

---

## Open Research Questions

### Optics

1. **MN78 current production status?** Is Intes-Micro still manufacturing, or used market only?
2. **MN78 vs. MN86 trade-off?** Larger 8" version exists—worth the weight/cost increase?
3. **Corrector plate coating maintenance?** Nevada dust cleaning protocol?

### Mount

4. **Harmonic drive lubrication schedule?** CSF units come pre-greased—relubrication interval?
5. **Encoder absolute position persistence?** AS5600 maintains position through power cycle?
6. **Optimal preload for angular contact bearings?** Balance stiffness vs. drag.
7. **Cable management for continuous rotation?** RA axis cable wrap or slip ring?

### Automation

8. **CloudWatcher calibration for 6,000+ ft altitude?** Does elevation affect IR readings?
9. **Starlink CGNAT workaround best practice?** VPS relay vs. business plan vs. Tailscale?
10. **Power consumption budget?** Size solar/battery backup if desired.

### Voice

11. **Optimal LLM size for Spark?** 8B vs. 13B vs. smaller fine-tuned model?
12. **Wake word vs. push-to-talk?** User preference and ambient noise considerations.
13. **Hallucination prevention for catalog queries?** Force tool calls, never answer from training data.

---

## Reference Materials

### Documentation to Acquire

| Document | Source | Purpose |
|----------|--------|---------|
| CSF harmonic drive datasheet | Harmonic Drive LLC | Mounting dimensions, torque specs |
| TMC5160 application note | Trinamic | Driver configuration |
| OnStepX configuration guide | GitHub wiki | Firmware setup |
| LX200 protocol specification | Meade (historical) | Mount communication |
| Skyfield documentation | rhodesmill.org | Ephemeris calculations |
| AAG CloudWatcher manual | Lunatico | Sensor integration |
| Ecowitt API documentation | Ecowitt | Weather data access |

### Community Resources

| Resource | URL | Purpose |
|----------|-----|---------|
| OnStep Groups.io | groups.io/g/onstep | Community support |
| Cloudy Nights DIY forum | cloudynights.com | Mount building experience |
| INDI Library | indilib.org | Linux telescope control |
| Stellarium | stellarium.org | Planetarium software |
| KStars/Ekos | edu.kde.org/kstars | Full observatory control suite |

---

## Appendix A: Component Links

*To be populated during research phase*

| Component | Vendor | URL | Price | Notes |
|-----------|--------|-----|-------|-------|
| MN78 | TBD | | | |
| CSF-32-100 | TBD | | | |
| CSF-25-80 | TBD | | | |
| TMC5160 | TBD | | | |
| Teensy 4.1 | PJRC | pjrc.com | $30 | |
| ... | | | | |

---

## Appendix B: CAD File Manifest

*To be created during design phase*

| File | Description | Status |
|------|-------------|--------|
| NIGHTWATCH_RA_Housing.step | RA axis main housing | Pending |
| NIGHTWATCH_DEC_Housing.step | DEC axis main housing | Pending |
| NIGHTWATCH_PierAdapter.step | Pier interface plate | Pending |
| NIGHTWATCH_Assembly.step | Complete mount assembly | Pending |
| NIGHTWATCH_Electronics.step | Control box layout | Pending |

---

## Appendix C: Wiring Diagrams

*To be created during electronics design phase*

| Diagram | Description | Status |
|---------|-------------|--------|
| NIGHTWATCH_Power_Distribution.pdf | 12V/5V power routing | Pending |
| NIGHTWATCH_Motor_Wiring.pdf | Stepper connections | Pending |
| NIGHTWATCH_Encoder_Wiring.pdf | Encoder signal routing | Pending |
| NIGHTWATCH_Network.pdf | Ethernet/serial topology | Pending |

---

## Appendix D: Software Repository Structure

```
nightwatch/
├── firmware/
│   └── onstepx_config/
│       ├── Config.h
│       └── Config.*.h
├── services/
│   ├── catalog/
│   ├── ephemeris/
│   ├── mount_control/
│   ├── weather/
│   └── safety_monitor/
├── voice/
│   ├── stt/
│   ├── llm/
│   ├── tools/
│   └── tts/
├── dashboard/
│   └── web/
├── scripts/
│   ├── install.sh
│   └── calibration/
└── docs/
    ├── assembly/
    └── operation/
```

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-17 | Claude | Initial combined build package |

---

*This document is designed for handoff to Claude Code for detailed research, design completion, and build execution.*
