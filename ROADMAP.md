# NIGHTWATCH Development Roadmap

This document outlines the planned development trajectory for NIGHTWATCH.

## Current Release: v0.1.0

**Status:** Released (January 2024)

Core foundation with voice control, mount operation, weather monitoring, and safety systems.

---

## v0.2.0 - Imaging Foundation

**Target:** Q2 2024

### Camera Integration
- [ ] Complete ZWO ASI SDK integration
- [ ] Camera detection and enumeration
- [ ] Exposure control (gain, time, binning)
- [ ] Cooling control with temperature monitoring
- [ ] FITS header generation with WCS hints
- [ ] SER video recording for planetary

### Plate Solving
- [ ] Astrometry.net local solver backend
- [ ] ASTAP solver as fallback
- [ ] Automatic mount sync from solve results
- [ ] Blind solve capability for lost orientation
- [ ] Solve result caching for repeated targets

### Voice Commands (Imaging)
- [ ] "Take a 30 second exposure"
- [ ] "Start planetary capture"
- [ ] "Solve current position"
- [ ] "Set gain to 200"
- [ ] "Cool camera to -10"

### Quality Improvements
- [ ] Increased unit test coverage (80%+)
- [ ] Integration test suite with simulators
- [ ] Performance profiling and optimization
- [ ] Memory usage optimization for edge devices

---

## v0.3.0 - Automated Sequences

**Target:** Q3 2024

### Sequence Engine
- [ ] Observation sequence definition format
- [ ] Target list with priorities
- [ ] Automated target selection based on altitude
- [ ] Meridian flip handling
- [ ] Dither patterns for imaging

### Imaging Automation
- [ ] Automated focus routine (HFD-based)
- [ ] Periodic refocus based on temperature
- [ ] Automated guider calibration
- [ ] Guiding start/stop with imaging
- [ ] Flat frame automation

### Filter Wheel Support
- [ ] Filter wheel device integration
- [ ] Filter-specific exposure settings
- [ ] Automated LRGB sequences
- [ ] Narrowband filter support

### Voice Commands (Sequences)
- [ ] "Run M31 sequence"
- [ ] "Add NGC 7000 to tonight's targets"
- [ ] "How many frames have we captured?"
- [ ] "Skip to next target"

---

## v0.4.0 - Advanced Safety & Monitoring

**Target:** Q4 2024

### Enhanced Safety
- [ ] Multi-sensor redundancy voting
- [ ] Predictive weather alerts (trend analysis)
- [ ] Equipment temperature monitoring
- [ ] Power consumption tracking
- [ ] Network connectivity monitoring

### All-Sky Camera Integration
- [ ] Cloud detection via all-sky imagery
- [ ] Satellite/aircraft avoidance
- [ ] Light pollution monitoring
- [ ] Aurora/airglow detection

### Alert System
- [ ] Push notifications (Pushover, Telegram)
- [ ] Email alerts with images
- [ ] SMS critical alerts
- [ ] Configurable alert thresholds
- [ ] Alert acknowledgment and escalation

### Remote Access
- [ ] Secure web dashboard
- [ ] Live status monitoring
- [ ] Manual override capabilities
- [ ] Session history and logs

---

## v0.5.0 - AI Enhancement

**Target:** Q1 2025

### Intelligent Scheduling
- [ ] Weather-aware scheduling optimization
- [ ] Moon avoidance calculations
- [ ] Target scoring based on conditions
- [ ] Historical success rate learning

### Image Quality Analysis
- [ ] Real-time star FWHM measurement
- [ ] Automatic frame rejection
- [ ] Tracking error detection
- [ ] Focus quality trends

### Natural Language Improvements
- [ ] Multi-turn conversation context
- [ ] Clarification requests
- [ ] Proactive suggestions
- [ ] Learning user preferences

### Model Updates
- [ ] Fine-tuned astronomy vocabulary
- [ ] Custom wake word training
- [ ] Offline object identification
- [ ] Natural sky description generation

---

## Future Considerations (Beyond v0.5)

### Hardware Expansion
- Rotator support
- Adaptive optics integration
- Multiple telescope coordination
- Remote dome controller support
- Environmental sensors (seeing, sky quality)

### Data Management
- Automatic image organization
- Cloud backup (optional, user-controlled)
- FITS database with search
- Integration with PixInsight/Siril

### Community Features
- Target recommendation sharing
- Equipment profile library
- Sequence template marketplace
- Multi-user observatory support

### Scientific Applications
- Asteroid detection pipeline
- Variable star monitoring
- Supernova patrol support
- Exoplanet transit timing

---

## Versioning Policy

NIGHTWATCH follows semantic versioning:

- **Major (X.0.0)**: Breaking changes, architecture overhauls
- **Minor (0.X.0)**: New features, backward compatible
- **Patch (0.0.X)**: Bug fixes, documentation updates

## Contributing to the Roadmap

Have ideas for NIGHTWATCH? We welcome input:

1. **Feature Requests**: Open a GitHub issue with the "enhancement" label
2. **Discussions**: Join roadmap discussions in GitHub Discussions
3. **Pull Requests**: Contribute implementations for roadmap items

## Principles

All development follows NIGHTWATCH core principles:

1. **Local-First**: No required cloud dependencies
2. **Safety-First**: Environmental interlocks are non-negotiable
3. **Voice-Native**: All features accessible via voice
4. **Open Standards**: ASCOM, INDI, Wyoming compatibility
5. **Non-Commercial**: CC BY-NC-SA 4.0 license

---

*Last updated: January 2024*
