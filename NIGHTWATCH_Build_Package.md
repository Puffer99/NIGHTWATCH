# Project NIGHTWATCH
## Autonomous Mak-Newt Observatory System
### Combined Build Package: Russian Giant × Autonomous Station
### Central Nevada Dark Sky Permanent Installation

---

## Document Purpose

This document serves as the complete specification and research handoff for an autonomous telescope system combining the optical excellence of the Intes-Micro MN76 Maksutov-Newtonian (also listed as MN78) with the automation infrastructure of a fully encoder-equipped, weather-aware observatory. The target environment is an isolated dark sky property in central Nevada with no neighbors, enabling permanent installation without constraints on noise, light, or operating hours.

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

**From the Russian Giant (#2):** The Intes-Micro MN76 (frequently listed as "MN78" due to historical naming variations) represents peak optical engineering in an unusual configuration. The 178mm (7-inch) f/6 Maksutov-Newtonian combines closed-tube thermal stability with fast Newtonian-class focal ratios and minimal central obstruction. Hand-figured Russian optics deliver planetary performance that rivals APO refractors at a fraction of the cost-per-inch. Though Intes-Micro ceased production in the mid-2010s, the closed tube design remains ideal for Nevada's dusty, high-temperature-swing desert environment—and no modern equivalent exists.

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
| Optical Tube Assembly | Intes-Micro MN76 (178mm f/6 Mak-Newt, also listed as MN78) |
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

### Intes-Micro MN76 Specifications

> **Model Naming Note:** The target OTA is the Intes Micro MN76, though it is frequently listed as "MN78" in classifieds and dealer records. Both designations refer to the same instrument—the 178mm aperture, f/6 Maksutov-Newtonian. When sourcing, search for both "MN76" and "MN78" to maximize coverage.

The MN76 was the flagship planetary instrument from Intes-Micro, a Russian manufacturer with four decades of experience producing premium amateur optics before ceasing operations in the mid-2010s. The Maksutov-Newtonian design uses a full-aperture meniscus corrector (like a Maksutov-Cassegrain) but routes light to a Newtonian-style side-mounted focuser rather than through a hole in the primary.

| Parameter | Specification |
|-----------|---------------|
| Manufacturer | Intes-Micro (Russia, production ceased ~2015) |
| Model Designations | MN76 / MN78 (same instrument) |
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

### Why This Optic Remains Ideal

Despite Intes-Micro ceasing production (the company wound down following the founder's passing), the MN76/MN78 remains one of the finest planetary instruments ever produced for amateur astronomers. No current production Mak-Newt offers this combination of aperture, optical quality, and environmental resilience.

**Optical Quality:** Intes-Micro hand-figured optics to 1/8 wave or better. The Mak-Newt design eliminates coma (the bane of fast Newtonians) while maintaining faster focal ratios than Mak-Cass designs. The 25% central obstruction is significantly smaller than typical SCTs (33-35%), yielding superior contrast transfer at medium spatial frequencies—exactly where planetary detail lives.

**Thermal Behavior:** The closed tube design is critical for Nevada. Open-tube Newtonians suffer from thermal currents rising off the mirror when ambient temperature drops. The MN76's sealed tube dramatically reduces this effect. The corrector plate acts as a thermal buffer. While cooldown time exceeds open designs, a permanent installation can pre-equilibrate hours before observing.

**Mechanical Robustness:** The closed tube protects optics from dust, insects, and the occasional curious wildlife. Nevada's alkaline dust is particularly damaging to exposed optical surfaces. The MN76 can remain on its pier under a cover for months without optical degradation.

**Focal Ratio Sweet Spot:** At f/6, the MN76 is fast enough for efficient lucky imaging (good frame rates) while slow enough that the optical design remains manageable. Faster Mak-Newts exist but become significantly more expensive and thermally challenging.

### Sourcing Strategy

The MN76/MN78 is a **rare vintage optic** that appears on the used market infrequently. Expect to monitor listings for several months before a specimen surfaces. When one appears, act quickly—these instruments typically sell within days.

**Recommended Search Terms:**
- "Intes Micro MN76" / "Intes Micro MN78"
- "Intes MN76" / "Intes MN78"
- "178mm Mak-Newt" / "178mm Maksutov-Newtonian"
- "7 inch Maksutov Newtonian"

**Primary Search Venues:**

| Venue | Notes |
|-------|-------|
| Astromart Classifieds | Best US source; set email alerts |
| Cloudy Nights Classifieds | Active community, good prices |
| eBay (worldwide) | Use saved searches with alerts |
| APM Telescopes Germany | May have old stock or leads |
	| Teleskop-Service Germany | European dealer network |
| European Markets (general) | Higher availability in EU/UK due to proximity to original production |

**European Considerations:** Factor in shipping (~$150-300 USD) and potential import duties (2.5% for optical instruments) when budgeting European purchases.

```
RESEARCH_TASK: MN76_SOURCING
Priority: HIGH
Objective: Locate and acquire Intes-Micro MN76/MN78

Action items:
- [ ] Set email alerts on Astromart, Cloudy Nights, eBay for all search terms
- [ ] Email APM Telescopes (info@apm-telescopes.net) for any remaining stock/leads
- [ ] Post "WTB" threads on Cloudy Nights and Stargazers Lounge forums
- [ ] Monitor European classifieds (Astrotreff.de, UK Astronomy Buy & Sell)
- [ ] Set Google Alerts for "Intes Micro MN76" and "Intes Micro MN78"
- [ ] Contact vintage telescope dealers specializing in Russian optics

Expected price range (used market):
- Excellent condition: $1,500 - $2,200
- Good condition (may need cleaning): $1,000 - $1,500
- NOS/mint (rare): $2,500 - $3,500
```

### Alternative OTAs (If MN76 Unavailable)

If extended searching fails to locate an MN76/MN78, consider these alternatives in order of preference:

| Alternative | Aperture | Notes | Est. Price |
|-------------|----------|-------|------------|
| Intes-Micro MN86 | 8" (203mm) f/6 | Larger, same design; heavier (~12 kg); even rarer | $2,500-3,500 used |
| Intes-Micro MN66 | 6" (152mm) f/6 | Same optics, smaller; more available; lighter (~6 kg) | $800-1,200 used |
| APM/LZOS 180mm f/8 | 7" (180mm) f/8 | Modern production; slower focal ratio; premium price | $4,000-5,000 new |
| Explore Scientific MN-152 | 6" (152mm) | In production; mass-produced; budget option | $700-900 new |

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

The MN76 weighs ~9 kg. Add counterweights (~9 kg), dovetail, accessories, and cameras: total rotating mass ~22 kg. The CSF-32 on RA is rated for significantly higher loads, providing safety margin for:
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
| **Optics** | Intes-Micro MN76 (used) | $1,800 |
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
- Mount MN76 on system
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
| MN76/MN78 unavailable (rare vintage optic) | Medium-High | High | Set alerts on all venues; consider MN66/MN86 alternatives; monitor for months |
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

1. **MN76/MN78 sourcing timeline?** Intes-Micro ceased production ~2015; used market only. How long to expect before finding one?
2. **MN76 vs. MN86 trade-off?** Larger 8" version exists—worth the weight/cost increase and even greater rarity?
3. **MN66 as fallback?** If MN76 proves impossible to source, is the 6" version acceptable for primary planetary work?
4. **Corrector plate coating maintenance?** Nevada dust cleaning protocol for vintage Russian optics?

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

*Research conducted 2026-01-18 - See docs/research/SOURCING_RESEARCH.md for details*

> **International Builders:** For vendors, forums, and search terms in multiple languages (German, French, Spanish, Russian, Japanese, Chinese, and 10+ more), see **[docs/research/INTERNATIONAL_SOURCING_GUIDE.md](docs/research/INTERNATIONAL_SOURCING_GUIDE.md)**

### Optical Tube Assembly

| Component | Vendor | URL | Price Est. | Notes |
|-----------|--------|-----|------------|-------|
| MN76/MN78 OTA (used) | Astromart | astromart.com | $1,500-2,200 | Primary search venue; set alerts |
| MN76/MN78 OTA (used) | Cloudy Nights | cloudynights.com/classifieds | $1,500-2,200 | Active community |
| MN76/MN78 OTA (used) | eBay worldwide | ebay.com | $1,500-3,500 | Global search; use alerts |
| MN76/MN78 (old stock) | APM Telescopes | apm-telescopes.net | Contact | May have leads or remaining stock |
| MN76/MN78 (EU market) | Teleskop-Service | teleskop-service.de | Contact | European dealer |
| MN66 (backup) | Various | used market | $800-1,200 | 6" alternative; more available |
| MN86 (backup) | Various | used market | $2,500-3,500 | 8" alternative; very rare |

### Harmonic Drives

| Component | Vendor | URL | Price Est. | Notes |
|-----------|--------|-----|------------|-------|
| CSF-32-100 | Harmonic Drive LLC | harmonicdrive.net | $800-1,200 | 30+ week lead time |
| CSF-32-100 | eBay (surplus) | ebay.com | $400-600 | Verify completeness |
| CSF-25-80 | Harmonic Drive LLC | harmonicdrive.net | $600-900 | 30+ week lead time |
| CSF-25-80 | eBay (surplus) | ebay.com | $300-500 | Verify completeness |
| CSF-xx (Chinese) | Alibaba | alibaba.com | $150-400 | Higher risk, lower cost |

### Electronics

| Component | Vendor | URL | Price | Notes |
|-----------|--------|-----|-------|-------|
| Teensy 4.1 | PJRC | pjrc.com | $30 | Main controller |
| TMC5160 (Watterott) | Digikey | digikey.com | $25 each | Ground CLK pin |
| TMC5160 (BTT) | Amazon/AliExpress | various | $15 each | Cut CLK pin only |
| AMT103-V | CUI Devices | cuidevices.com | $50 each | Motor-side encoder |
| AS5600 | Amazon/AliExpress | various | $5 each | Axis-side absolute |
| NEMA17 + 27:1 gearbox | StepperOnline | stepperonline.com | $80 each | Integrated unit |

### Reference DIY Projects

| Project | GitHub | Notes |
|---------|--------|-------|
| HEMY v2 | github.com/polvinc/HEMY | Best reference, <4kg, 15kg capacity |
| DHEM | github.com/polvinc/DHEM | No machine tools needed |
| Alkaid | alanz.info/blog/alkaid-mount | 5.5kg, waterjet aluminum |

### Software/Firmware

| Component | Source | URL | Notes |
|-----------|--------|-----|-------|
| OnStepX | GitHub | github.com/hjd1964/OnStepX | v10.24i+ required |
| OnStep Wiki | Groups.io | onstep.groups.io/g/main/wiki | Configuration reference |
| HEMY Config | GitHub | github.com/polvinc/HEMY | Adapted for NIGHTWATCH |

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

*Structure created 2026-01-18*

```
NIGHTWATCH/
├── NIGHTWATCH_Build_Package.md      # This specification document
├── firmware/
│   └── onstepx_config/
│       └── Config.h                 # CREATED - Initial OnStepX config
├── services/
│   ├── catalog/                     # CREATED - SQLite object database
│   ├── ephemeris/                   # Pending - Skyfield integration
│   ├── mount_control/               # CREATED - LX200 protocol client
│   ├── weather/                     # CREATED - Ecowitt API integration
│   └── safety_monitor/              # CREATED - Automation logic
├── voice/
│   ├── stt/                         # Pending - Whisper integration
│   ├── llm/                         # Pending - Llama 3.x tools
│   ├── tools/                       # Pending - Function calling
│   └── tts/                         # Pending - Piper/Coqui
├── dashboard/
│   └── web/                         # Pending - Remote monitoring UI
├── scripts/
│   ├── install.sh                   # Pending
│   └── calibration/                 # Pending - Encoder/PEC routines
└── docs/
    ├── SCIENTIFIC_FOUNDATIONS.md   # CREATED - PhD-level optical/atmospheric theory
    ├── assembly/                    # Pending - Build instructions
    ├── operation/                   # Pending - User manual
    └── research/
        └── SOURCING_RESEARCH.md     # CREATED - Component sourcing
```

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-17 | Claude | Initial combined build package |
| 1.1 | 2026-01-18 | Claude | Component sourcing research completed, Appendix A populated |
| 1.2 | 2026-01-18 | Claude | Core Python services implemented |
| 1.3 | 2026-01-19 | Claude | Expanded optics section with detailed MN76 Mak-Newtonian rationale; corrected model designation to MN76 (sometimes called MN78) |
| 1.4 | 2026-01-19 | Claude | Added SCIENTIFIC_FOUNDATIONS.md with PhD-level optical theory, atmospheric physics, and peer-reviewed references |

---

## Progress Log

### 2026-01-18: Core Services Implemented

**Completed:**
- Mount Control Service (services/mount_control/)
  - LX200 protocol client for OnStepX communication
  - TCP and serial connection support
  - Full command set: goto, tracking, parking, status
- Weather Service (services/weather/)
  - Ecowitt WS90 API integration
  - Real-time data polling with safety thresholds
- Safety Monitor (services/safety_monitor/)
  - Automated observatory safety logic
  - Weather, cloud, and daylight evaluation
  - Emergency park capability
- Catalog Service (services/catalog/)
  - SQLite astronomical object database
  - Messier, NGC, IC, named star support
  - Voice-friendly lookup interface

**HEMY Reference Design Analysis:**
- Mount type: Harmonic drive with timing belts
- Payload: 15 kg without counterweights
- Weight: < 4 kg excluding base
- Performance: ~1 arcsec RMS, ~0.14 arcsec resolution
- Electronics: Teensy 4.0 MicroMod + TMC5160 drivers
- Cost: 800-1000 EUR total build

### 2026-01-18: Research Phase Initiated

**Completed:**
- Created project directory structure per Appendix D specification
- Researched MN76/MN78 telescope sourcing (used market primary, European dealers for leads)
- Researched harmonic drive sourcing (HD LLC, eBay surplus, Alibaba)
- Identified reference DIY projects (HEMY, DHEM, Alkaid)
- Researched OnStepX configuration for TMC5160 + encoder feedback
- Created initial OnStepX Config.h for NIGHTWATCH hardware
- Documented all findings in docs/research/SOURCING_RESEARCH.md

**Key Findings:**
- Harmonic drives: 30+ week lead time from HD LLC; eBay surplus is viable
- MN76/MN78: Production ceased ~2015; used market only; set alerts on all venues
- HEMY project: Best reference design (<4kg, 15kg capacity, ~1 arcsec RMS)
- OnStepX: v10.24i or later required for HEMY-style configurations

**Next Steps:**
- Set up MN76/MN78 search alerts on Astromart, Cloudy Nights, eBay
- Set eBay alerts for CSF-32 and CSF-25 harmonic drives
- Implement ephemeris service with Skyfield
- Begin voice pipeline development

---

*This document is designed for handoff to Claude Code for detailed research, design completion, and build execution.*
