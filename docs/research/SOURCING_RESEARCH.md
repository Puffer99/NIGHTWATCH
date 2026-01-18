# NIGHTWATCH Component Sourcing Research
## Research Date: 2026-01-18

---

## 1. Intes-Micro MN78 Telescope Sourcing

### Status: ACTIVE RESEARCH REQUIRED

#### Current Availability

The Intes-Micro MN78 (7" f/6 Maksutov-Newtonian) remains a sought-after planetary telescope. Key findings:

**Primary Sources:**
- **ENS Optical UK** (https://ensoptical.co.uk) - Lists MN78 7" F/8 with Crayford focuser
- **APM Telescopes Germany** (https://www.apm-telescopes.net) - Official Intes-Micro distributor
  - APM offers premium versions with Matthias Wirth tubes and Starlight Feather Touch focusers
  - Also sells raw Intes-Micro optics in custom configurations
- **Astromart Classifieds** (https://astromart.com) - Active used market listings

**Production Status:**
- As of March 2025, Intes-Micro still produces MN56 (127mm, 760mm FL) and MN76 (178mm, 1050mm FL)
- MN78 specific availability requires direct inquiry to distributors
- Factory located in Russia; export logistics may be complicated

**Pricing Estimates:**
| Condition | Price Range (USD) | Notes |
|-----------|-------------------|-------|
| New (standard) | $2,200 - $3,000 | Direct from distributor |
| New (APM/Wirth premium) | $3,500 - $5,000 | German machined tube, premium focuser |
| Used (excellent) | $1,500 - $2,200 | Check Astromart, Cloudy Nights |

#### Backup Options

1. **Intes-Micro MN66** (6" f/6) - $1,295 historical price, lighter, easier to source
2. **APM 8" f/6 Mak-Newt** - Larger aperture, uses Intes optics, premium tube
3. **Explore Scientific MN-152** (6" Mak-Newt) - More readily available commercial option

#### Action Items

- [ ] Email APM Telescopes (info@apm-telescopes.net) for MN78 pricing and lead time
- [ ] Check Astromart and Cloudy Nights classifieds weekly
- [ ] Contact ENS Optical UK for availability
- [ ] Investigate direct Russia purchase if needed

---

## 2. Harmonic Drive Sourcing (CSF-32-100, CSF-25-80)

### Status: MULTIPLE OPTIONS IDENTIFIED

#### Official Manufacturer

**Harmonic Drive LLC** (Beverly, MA, USA)
- Website: https://www.harmonicdrive.net
- CSF-GH series: Zero-backlash gearheads
- Reduction ratios: 50:1 to 160:1
- Peak torque: 18Nm to 2,630Nm
- Accuracy: <1 arc-min
- Repeatability: ±4 to ±10 arc-sec

**CRITICAL NOTE:** Lead times can exceed 30 weeks for new orders. Contact early.

#### eBay/Surplus Options

| Source | Model | Condition | Est. Price |
|--------|-------|-----------|------------|
| eBay | CSF-32-50-2UH-SP | New surplus | $300-500 |
| eBay | CSF-32-50-2UH-SPA995 | Used/surplus | $200-400 |
| Various | CSF-25-xx units | Surplus | $150-300 |

**Recommended eBay sellers:**
- Surplus industrial automation specialists (Japan)
- Large surplus equipment dealers (North America, since 2001)
- Robot parts & accessories category

#### Alibaba Chinese Alternatives

- CSF/XSF series harmonic drives
- Factory direct pricing
- MOQ typically 1-2 pieces
- **Caution:** Verify authenticity, may be clones

**Chinese alternatives (lower cost, higher risk):**
- Leadshine harmonic drives
- LMI harmonic reducers
- Cost: 30-50% less than genuine HD LLC units

#### Component Set Verification

For any harmonic drive purchase, verify:
- Wave generator (input)
- Flexspline (output)
- Circular spline (fixed)
- Correct mounting flange configuration
- Input/output shaft specifications

#### Pricing Summary

| Component | New (HD LLC) | Surplus (eBay) | Chinese Clone |
|-----------|--------------|----------------|---------------|
| CSF-32-100 | $800-1,200 | $400-600 | $200-400 |
| CSF-25-80 | $600-900 | $300-500 | $150-300 |

---

## 3. DIY Harmonic Drive Mount References

### HEMY (Harmonic Equatorial Mount Yourself)

**GitHub:** https://github.com/polvinc/HEMY

**Key Specifications:**
- Load capacity: 15 kg (no counterweights)
- Weight: < 4 kg
- Build cost: 800-1000 EUR total
- Machined parts: < 400 EUR

**Electronics:**
- Teensy 4.0 MicroMod running OnStepX
- TMC5160 stepper drivers (2x)
- Optional RA brake for power loss protection
- WiFi/Bluetooth/GPS onboard
- LilyGO T-01 C3 WiFi module

**Performance:**
- ~1 arcsecond RMS guiding achieved (March 2025 testing)
- OnStepX firmware 10.24i or later required

**Documentation:**
- Assembly: https://github.com/polvinc/HEMY/blob/main/docs/v2/Assembly.md
- Software: https://github.com/polvinc/HEMY/blob/main/software/software.md
- Discord community available

### DHEM (DIY Harmonic Equatorial Mount)

**GitHub:** https://github.com/polvinc/DHEM

- No machine tools required
- Shopping list + screwdriver + saw approach
- Lower cost entry point

### Alkaid Mount

**Creator:** Alan (Jialiang) Zhao
**URL:** https://alanz.info/blog/alkaid-mount.html

**Design:**
- NEMA-17 stepper + 27:1 planetary gearbox + harmonic reducer
- 10mm aluminum plates, waterjet cut + milled
- Total weight: ~5.5 kg (less than half HEQ-5)
- No counterweights needed

### $399 DIY Harmonic Mount

**Forum:** Stargazers Lounge
**URL:** https://stargazerslounge.com/topic/427814-build-your-399-harmonic-mount-with-me-step-by-step/

**Components:**
- OnStep board: $30
- TMA 17 motors: $30
- Harmonic drivers: $250
- Assembly: ~30 minutes

---

## 4. OnStepX Configuration Research

### Firmware Source

**GitHub:** https://github.com/hjd1964/OnStepX

**Latest Release:** 10.24c (as of Feb 2025)
**Minimum for HEMY:** 10.24i

### TMC5160 Configuration

The TMC5160 is Trinamic's flagship stepper driver.

**SPI Mode Requirements:**
- Both Axis1 and Axis2 should use TMC5160 in SPI mode
- Current setting based on Rsense = 0.075 Ohms

**Hardware Notes:**
| Brand | Model | Modification Required |
|-------|-------|----------------------|
| Watterott | TMC5160 v1.3/v1.4/v1.5 | Ground CLK pin, cut off |
| BigTreeTech | TMC5160 v1.2 | Only cut CLK pin |

### Encoder Feedback Configuration

**Motor-Side Encoders (AMT103):**
```cpp
#define AXIS1_ENCODER           ON
#define AXIS1_ENCODER_PPR       8192
```

**Axis-Side Encoders (AS5600):**
- Requires SERIAL_BRIDGE configuration
- WeMos D1 Mini ESP32 recommended
- Encoder Bridge firmware on second microcontroller

**Pin Assignments:**
- AXIS1_ENCODER_A_PIN → AXIS3_STEP_PIN (default)
- AXIS1_ENCODER_B_PIN → AXIS3_DIR_PIN (default)
- Override in Config.h if needed

### NIGHTWATCH Specific Config

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

// Site (Central Nevada)
#define SITE_LATITUDE_DEFAULT   39.0
#define SITE_LONGITUDE_DEFAULT  -117.0

// Network
#define SERIAL_IP_MODE          ETHERNET
```

### Community Resources

- **OnStep Groups.io:** https://onstep.groups.io/g/main
- **Wiki:** https://onstep.groups.io/g/main/wiki
- **TMC Driver Info:** https://onstep.groups.io/g/main/wiki/7233

---

## 5. Pre-Built Harmonic Mount Options (Reference)

For comparison with DIY approach:

| Mount | Price | Payload | Weight |
|-------|-------|---------|--------|
| ZWO AM3 | $1,499 | 13 kg | 3.5 kg |
| Sky-Watcher Wave 100i | $1,695-2,630 | 10-15 kg | 4.3 kg |
| Rainbow Astro RST-300 | $8,490 | 30-50 kg | 11 kg |

---

## 6. Next Steps

### Immediate Actions

1. **Contact APM Telescopes** - Request MN78 quote and availability
2. **Monitor eBay** - Set alerts for CSF-32 and CSF-25 harmonic drives
3. **Clone HEMY Repository** - Study design for NIGHTWATCH adaptation
4. **Join OnStep Groups.io** - Engage community before build

### Design Phase

1. Adapt HEMY/Alkaid frame design for MN78 payload (9 kg OTA)
2. Size harmonic drives for 25 kg total capacity
3. Design encoder mounting strategy
4. Create complete BOM with suppliers

---

## Sources

### MN78 Research
- [ENS Optical UK - Intes MN78](https://ensoptical.co.uk)
- [APM Telescopes - Maksutov Newton](https://www.apm-telescopes.net/en/maksutov-newton)
- [Cloudy Nights - Intes-Micro Discussions](https://www.cloudynights.com/topic/168496-intes-micro-maksutov-newton/)
- [Astromart Classifieds](https://www.astromart.com)

### Harmonic Drive Research
- [Harmonic Drive LLC](https://www.harmonicdrive.net)
- [eBay Harmonic Drives](https://www.ebay.com/shop/harmonic-drives)
- [Alibaba CSF Harmonic Drives](https://www.alibaba.com/showroom/csf-harmonic-drive.html)

### DIY Mount Research
- [HEMY GitHub](https://github.com/polvinc/HEMY)
- [DHEM GitHub](https://github.com/polvinc/DHEM)
- [Alkaid Mount](https://alanz.info/blog/alkaid-mount.html)
- [Hackaday - DIY Harmonic Drive Mount](https://hackaday.com/2022/11/10/a-diy-equatorial-mount-using-harmonic-drives/)

### OnStepX Research
- [OnStepX GitHub](https://github.com/hjd1964/OnStepX)
- [OnStep Groups.io Wiki](https://onstep.groups.io/g/main/wiki)
- [TMC5160 Driver Configuration](https://onstep.groups.io/g/main/wiki/7233)
