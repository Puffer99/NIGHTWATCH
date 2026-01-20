# NIGHTWATCH v0.1 Comprehensive Implementation Plan

**Created:** January 2026
**Target:** Fully autonomous, voice-controlled observatory running entirely on-premise
**Estimated Steps:** 847 granular tasks across 10 major phases

---

## Executive Summary

This plan advances NIGHTWATCH to a functional v0.1 milestone: complete implementation of all 13 core observatory microservices, full end-to-end voice pipeline integration (voice commands → intent → action → telescope response with safety vetoes), comprehensive hardware-in-the-loop simulation, and robust testing/documentation.

### Ethos Preservation

All work strictly adheres to NIGHTWATCH's immutable principles:
- **Local-first architecture:** ZERO cloud dependency; all AI/voice/control processing remains on-premise (DGX Spark)
- **Modular microservices:** Clear separation with standards compliance (ASCOM Alpaca, Wyoming protocol, OnStepX, INDI)
- **Safety first:** Mandatory environmental interlocks via safety_monitor; failsafe parking on any sensor failure
- **Expert-driven design:** POS methodology guides novel decisions with simulated expert consensus
- **Transparency:** Comprehensive documentation; all reasoning captured
- **Non-commercial:** CC BY-NC-SA 4.0; no commercialization paths

### Current State Assessment

| Category | Modules | Completion | Key Gaps |
|----------|---------|------------|----------|
| **Services** | 17 files, 10,482 lines | 70-95% | Camera, Catalog, Astrometry, Alerts, Power, Enclosure need completion |
| **Voice Pipeline** | 8 files, 4,500+ lines | 85% | Orchestrator, LLM integration, tool handlers not wired |
| **Tests** | 11 files | 60% | Integration tests sparse; E2E testing missing |
| **Infrastructure** | Docker, CI/CD | 80% | Config system, startup scripts missing |
| **Documentation** | 10+ major docs | 90% | Quickstart guide, API docs need expansion |

### Effort Distribution

| Phase | Steps | % of Total | Focus Area |
|-------|-------|------------|------------|
| 1. Infrastructure & Configuration | 63 | 7.4% | Foundation |
| 2. Core Service Completion | 148 | 17.5% | Services |
| 3. Orchestrator Development | 78 | 9.2% | Integration |
| 4. Voice Pipeline Integration | 98 | 11.6% | Voice |
| 5. Tool Handler Implementation | 124 | 14.6% | Voice-Service Bridge |
| 6. Safety System Hardening | 68 | 8.0% | Safety |
| 7. Hardware-in-Loop Simulation | 82 | 9.7% | Simulation |
| 8. Testing & Quality Assurance | 96 | 11.3% | Quality |
| 9. Documentation & POS | 52 | 6.1% | Docs |
| 10. Deployment Preparation | 38 | 4.5% | Deploy |
| **TOTAL** | **847** | **100%** | |

---

## Phase Overview

### Phase 1: Infrastructure & Configuration
Establish unified configuration system, logging infrastructure, and dependency management. Creates the foundation for all subsequent phases.

### Phase 2: Core Service Completion
Complete all partial microservices: Camera (ZWO ASI), Catalog (database population), Astrometry (solver backends), Alerts (notification channels), Power (NUT integration), Enclosure (GPIO control).

### Phase 3: Orchestrator Development
Build the central control loop that wires voice input to service calls and manages session state, error recovery, and service health.

### Phase 4: Voice Pipeline Integration
Integrate STT → LLM → Tool Selection → TTS into a cohesive pipeline with local Llama 3.2 inference.

### Phase 5: Tool Handler Implementation
Wire all 70+ telescope tools to actual service method calls with proper parameter validation and response formatting.

### Phase 6: Safety System Hardening
Implement comprehensive safety interlocks, vetoes, failsafes, and sensor failure handling per POS deliberations.

### Phase 7: Hardware-in-Loop Simulation
Expand Docker simulation environment, create test fixtures, and validate all services against simulators.

### Phase 8: Testing & Quality Assurance
Comprehensive unit tests, integration tests, end-to-end tests, and CI/CD improvements.

### Phase 9: Documentation & POS Deliberations
Update all documentation, create quickstart guide, API reference, and conduct POS deliberations for novel decisions.

### Phase 10: Deployment Preparation
Create installation scripts, hardware integration guides, and prepare for Nevada dark sky site deployment.

---

## Complete Task Tracker

| Step ID | Phase | Category | Description | Dependencies | Complexity | Effort | Status | Notes |
|---------|-------|----------|-------------|--------------|------------|--------|--------|-------|
| 1 | Infrastructure & Configuration | config | Create nightwatch/config.py module skeleton | None | 2 | 2 | Complete | Foundation for all services |
| 2 | Infrastructure & Configuration | config | Implement YAML configuration loading with pydantic validation | 1 | 3 | 3 | Complete | Use pydantic for type safety |
| 3 | Infrastructure & Configuration | config | Define SiteConfig dataclass (latitude, longitude, elevation, timezone) | 2 | 2 | 1 | Complete | Per POS Day 8 discussion |
| 4 | Infrastructure & Configuration | config | Define MountConfig dataclass (type, host, port, serial_port, baudrate) | 2 | 2 | 1 | Complete | Support TCP and serial |
| 5 | Infrastructure & Configuration | config | Define WeatherConfig dataclass (enabled, type, host, poll_interval) | 2 | 2 | 1 | Complete | Ecowitt WS90 settings |
| 6 | Infrastructure & Configuration | config | Define VoiceConfig dataclass (STT model, device, compute_type) | 2 | 2 | 1 | Complete | DGX Spark optimized defaults |
| 7 | Infrastructure & Configuration | config | Define TTSConfig dataclass (model, use_cuda, cache_enabled) | 2 | 2 | 1 | Complete | Piper configuration |
| 8 | Infrastructure & Configuration | config | Define LLMConfig dataclass (model, max_tokens, temperature) | 2 | 2 | 1 | Complete | Llama 3.2 local inference |
| 9 | Infrastructure & Configuration | config | Define SafetyConfig dataclass (wind_limit, humidity_limit, temp_min) | 2 | 2 | 1 | Complete | Per POS Day 4 thresholds |
| 10 | Infrastructure & Configuration | config | Define CameraConfig dataclass (type, gain, exposure defaults) | 2 | 2 | 1 | Complete | ZWO ASI settings |
| 11 | Infrastructure & Configuration | config | Define GuiderConfig dataclass (phd2_host, phd2_port) | 2 | 2 | 1 | Complete | PHD2 connection |
| 12 | Infrastructure & Configuration | config | Define EncoderConfig dataclass (enabled, port, baudrate) | 2 | 2 | 1 | Complete | EncoderBridge settings |
| 13 | Infrastructure & Configuration | config | Define AlertConfig dataclass (email, sms, push enabled flags) | 2 | 2 | 1 | Complete | Notification channels |
| 14 | Infrastructure & Configuration | config | Define PowerConfig dataclass (ups_host, shutdown_threshold) | 2 | 2 | 1 | Complete | NUT server settings |
| 15 | Infrastructure & Configuration | config | Define EnclosureConfig dataclass (gpio_pins, timeout) | 2 | 2 | 1 | Complete | Roof controller GPIO |
| 16 | Infrastructure & Configuration | config | Implement NightwatchConfig master class aggregating all configs | 3,4,5,6,7,8,9,10,11,12,13,14,15 | 3 | 2 | Complete | Single config object |
| 17 | Infrastructure & Configuration | config | Add config file discovery (./nightwatch.yaml, ~/.nightwatch/config.yaml) | 16 | 2 | 1 | Complete | Standard paths |
| 18 | Infrastructure & Configuration | config | Implement config validation with helpful error messages | 17 | 3 | 2 | Complete | User-friendly errors |
| 19 | Infrastructure & Configuration | config | Add environment variable override support (NIGHTWATCH_MOUNT_HOST, etc.) | 18 | 2 | 2 | Complete | Flexibility for containers |
| 20 | Infrastructure & Configuration | config | Create sample nightwatch.yaml with documented options | 19 | 2 | 2 | Complete | User template |
| 21 | Infrastructure & Configuration | config | Write unit tests for config loading and validation | 20 | 2 | 2 | Complete | Test coverage |
| 22 | Infrastructure & Configuration | logging | Create nightwatch/logging_config.py module | None | 2 | 1 | Complete | Centralized logging |
| 23 | Infrastructure & Configuration | logging | Implement structured JSON logging format | 22 | 2 | 2 | Complete | Machine-parseable logs |
| 24 | Infrastructure & Configuration | logging | Add rotating file handler (10MB, 5 backups) | 23 | 2 | 1 | Complete | Prevent disk fill |
| 25 | Infrastructure & Configuration | logging | Add console handler with color formatting | 23 | 2 | 1 | Complete | Developer experience |
| 26 | Infrastructure & Configuration | logging | Implement per-service log level configuration | 24,25 | 2 | 2 | Complete | Granular control |
| 27 | Infrastructure & Configuration | logging | Add log correlation ID for tracing requests | 26 | 3 | 2 | Complete | Debugging support |
| 28 | Infrastructure & Configuration | logging | Create logging helpers (log_exception, log_timing) | 27 | 2 | 1 | Complete | Convenience functions |
| 29 | Infrastructure & Configuration | logging | Write unit tests for logging configuration | 28 | 2 | 1 | Complete | Test coverage |
| 30 | Infrastructure & Configuration | dependencies | Audit services/requirements.txt for version pinning | None | 2 | 2 | Complete | Reproducible builds |
| 31 | Infrastructure & Configuration | dependencies | Audit voice/requirements.txt for version pinning | None | 2 | 2 | Complete | Reproducible builds |
| 32 | Infrastructure & Configuration | dependencies | Create requirements-dev.txt for development tools | 30,31 | 2 | 1 | Complete | Dev dependencies |
| 33 | Infrastructure & Configuration | dependencies | Add pytest-cov to dev requirements | 32 | 1 | 1 | Complete | Coverage reporting |
| 34 | Infrastructure & Configuration | dependencies | Add ruff to dev requirements | 32 | 1 | 1 | Complete | Linting |
| 35 | Infrastructure & Configuration | dependencies | Add mypy to dev requirements | 32 | 1 | 1 | Complete | Type checking |
| 36 | Infrastructure & Configuration | dependencies | Add pre-commit to dev requirements | 32 | 1 | 1 | Complete | Git hooks |
| 37 | Infrastructure & Configuration | dependencies | Create pyproject.toml with project metadata | 30,31 | 2 | 2 | Complete | Modern packaging |
| 38 | Infrastructure & Configuration | dependencies | Configure ruff in pyproject.toml | 37 | 2 | 1 | Complete | Linting rules |
| 39 | Infrastructure & Configuration | dependencies | Configure mypy in pyproject.toml | 37 | 2 | 1 | Complete | Type checking rules |
| 40 | Infrastructure & Configuration | dependencies | Configure pytest in pyproject.toml | 37 | 2 | 1 | Complete | Test configuration |
| 41 | Infrastructure & Configuration | dependencies | Create .pre-commit-config.yaml | 36 | 2 | 1 | Complete | Pre-commit hooks |
| 42 | Infrastructure & Configuration | dependencies | Document dependency installation in README | 41 | 2 | 1 | Complete | User guidance |
| 43 | Infrastructure & Configuration | startup | Create nightwatch/main.py entry point | 21,29 | 3 | 2 | Complete | Application entry |
| 44 | Infrastructure & Configuration | startup | Implement argument parser (--config, --log-level, --dry-run) | 43 | 2 | 1 | Complete | CLI options |
| 45 | Infrastructure & Configuration | startup | Add signal handlers (SIGINT, SIGTERM) for graceful shutdown | 44 | 3 | 2 | Complete | Clean shutdown |
| 46 | Infrastructure & Configuration | startup | Implement service health check framework | 45 | 3 | 2 | Complete | Startup validation |
| 47 | Infrastructure & Configuration | startup | Add mount connection health check | 46 | 2 | 1 | Complete | Verify mount reachable |
| 48 | Infrastructure & Configuration | startup | Add weather service health check | 46 | 2 | 1 | Complete | Verify weather data |
| 49 | Infrastructure & Configuration | startup | Add voice pipeline health check | 46 | 2 | 1 | Complete | Verify STT/TTS ready |
| 50 | Infrastructure & Configuration | startup | Implement startup sequence with dependency ordering | 47,48,49 | 3 | 2 | Complete | Ordered initialization |
| 51 | Infrastructure & Configuration | startup | Add startup banner with version and config summary | 50 | 1 | 1 | Complete | User feedback |
| 52 | Infrastructure & Configuration | startup | Implement graceful degradation (continue without optional services) | 50 | 3 | 2 | Complete | Robustness |
| 53 | Infrastructure & Configuration | startup | Create bin/nightwatch shell script launcher | 52 | 2 | 1 | Complete | Unix launcher |
| 54 | Infrastructure & Configuration | startup | Create bin/nightwatch.bat Windows launcher | 52 | 2 | 1 | Complete | Windows support |
| 55 | Infrastructure & Configuration | startup | Write integration test for startup sequence | 54 | 3 | 2 | Complete | Startup validation |
| 56 | Infrastructure & Configuration | project | Create nightwatch/ package directory | None | 1 | 1 | Complete | Package structure |
| 57 | Infrastructure & Configuration | project | Create nightwatch/__init__.py with version | 56 | 1 | 1 | Complete | Package init |
| 58 | Infrastructure & Configuration | project | Create nightwatch/exceptions.py with custom exceptions | 57 | 2 | 1 | Complete | Error types |
| 59 | Infrastructure & Configuration | project | Create nightwatch/constants.py with shared constants | 57 | 2 | 1 | Complete | Magic numbers |
| 60 | Infrastructure & Configuration | project | Create nightwatch/types.py with shared type definitions | 57 | 2 | 1 | Complete | Type aliases |
| 61 | Infrastructure & Configuration | project | Add py.typed marker file for PEP 561 | 57 | 1 | 1 | Complete | Type hint support |
| 62 | Infrastructure & Configuration | project | Update .gitignore for Python project | None | 1 | 1 | Complete | Clean repo |
| 63 | Infrastructure & Configuration | project | Create CHANGELOG.md with v0.1 section | None | 2 | 1 | Complete | Version history |
| 64 | Core Service Completion | catalog | Review catalog.py current implementation | None | 2 | 1 | Complete | Understand gaps |
| 65 | Core Service Completion | catalog | Create catalog database schema (SQLite) | 64 | 3 | 2 | Complete | Tables for objects |
| 66 | Core Service Completion | catalog | Add Messier catalog data (M1-M110) to database | 65 | 2 | 2 | Complete | 110 objects |
| 67 | Core Service Completion | catalog | Add NGC catalog data (top 1000 objects) | 66 | 2 | 3 | Complete | Popular NGC objects |
| 68 | Core Service Completion | catalog | Add IC catalog data (top 500 objects) | 67 | 2 | 2 | Complete | Popular IC objects |
| 69 | Core Service Completion | catalog | Add named stars (100 brightest) | 68 | 2 | 2 | Complete | Vega, Polaris, etc. |
| 70 | Core Service Completion | catalog | Add double stars (50 showpiece doubles) | 69 | 2 | 1 | Complete | Albireo, etc. |
| 71 | Core Service Completion | catalog | Implement search by name (fuzzy matching) | 70 | 3 | 2 | Complete | User-friendly search |
| 72 | Core Service Completion | catalog | Implement search by coordinates (cone search) | 71 | 3 | 2 | Complete | RA/Dec range |
| 73 | Core Service Completion | catalog | Implement search by object type | 72 | 2 | 1 | Complete | Galaxy, nebula, etc. |
| 74 | Core Service Completion | catalog | Implement search by magnitude range | 73 | 2 | 1 | Complete | Brightness filter |
| 75 | Core Service Completion | catalog | Implement search by constellation | 74 | 2 | 1 | Complete | Regional filter |
| 76 | Core Service Completion | catalog | Add object metadata (size, surface brightness) | 75 | 2 | 2 | Complete | Additional data |
| 77 | Core Service Completion | catalog | Implement get_object_details() method | 76 | 2 | 1 | Complete | Full object info |
| 78 | Core Service Completion | catalog | Implement resolve_object() for name to coordinates | 77 | 2 | 1 | Complete | Critical for goto |
| 79 | Core Service Completion | catalog | Add caching for frequently accessed objects | 78 | 2 | 2 | Complete | Performance |
| 80 | Core Service Completion | catalog | Write unit tests for catalog search | 79 | 2 | 2 | Complete | Test coverage |
| 81 | Core Service Completion | catalog | Write unit tests for coordinate resolution | 80 | 2 | 1 | Complete | Test coverage |
| 82 | Core Service Completion | camera | Review asi_camera.py current implementation | None | 2 | 1 | Complete | Full ZWO ASI integration, presets, video capture |
| 83 | Core Service Completion | camera | Add ZWO ASI SDK wrapper import handling | 82 | 3 | 2 | Not Started | Optional dependency |
| 84 | Core Service Completion | camera | Implement camera detection and enumeration | 83 | 3 | 2 | Not Started | List connected cameras |
| 85 | Core Service Completion | camera | Implement camera connection with settings | 84 | 3 | 2 | Not Started | Connect by ID |
| 86 | Core Service Completion | camera | Implement gain control (set/get) | 85 | 2 | 1 | Complete | set_gain(), get_gain(), get_gain_range() in asi_camera.py |
| 87 | Core Service Completion | camera | Implement exposure time control (set/get) | 86 | 2 | 1 | Complete | set_exposure(), get_exposure(), get_exposure_range() in asi_camera.py |
| 88 | Core Service Completion | camera | Implement binning control (1x1, 2x2, 4x4) | 87 | 2 | 1 | Complete | set_binning(), get_binning(), get_supported_binning() in asi_camera.py |
| 89 | Core Service Completion | camera | Implement ROI (region of interest) control | 88 | 3 | 2 | Not Started | Subframe capture |
| 90 | Core Service Completion | camera | Implement single frame capture | 89 | 3 | 2 | Not Started | Still image capture |
| 91 | Core Service Completion | camera | Implement video/streaming capture mode | 90 | 4 | 3 | Not Started | Planetary imaging |
| 92 | Core Service Completion | camera | Implement image download and format conversion | 91 | 3 | 2 | Not Started | RAW to usable format |
| 93 | Core Service Completion | camera | Add FITS header writing | 92 | 3 | 2 | Not Started | Metadata for astrometry |
| 94 | Core Service Completion | camera | Implement cooling control (setpoint, power) | 93 | 3 | 2 | Not Started | Temperature regulation |
| 95 | Core Service Completion | camera | Implement temperature monitoring | 94 | 2 | 1 | Complete | get_temperature_status(), set_cooler() in asi_camera.py |
| 96 | Core Service Completion | camera | Add capture abort functionality | 95 | 2 | 1 | Complete | abort_capture(), get_capture_progress() in asi_camera.py |
| 97 | Core Service Completion | camera | Implement capture progress callbacks | 96 | 3 | 2 | Not Started | Status updates |
| 98 | Core Service Completion | camera | Add SER file recording for planetary | 97 | 4 | 3 | Not Started | Video format |
| 99 | Core Service Completion | camera | Create mock camera for testing | 98 | 3 | 2 | Complete | tests/mocks/mock_camera.py with presets |
| 100 | Core Service Completion | camera | Write unit tests for camera control | 99 | 2 | 2 | Complete | test_camera_service.py (26 tests) |
| 101 | Core Service Completion | camera | Write integration test with simulator | 100 | 3 | 2 | Not Started | End-to-end test |
| 102 | Core Service Completion | astrometry | Review plate_solver.py current implementation | None | 2 | 1 | Complete | Full astrometry.net/ASTAP, WCS parsing, mount sync |
| 103 | Core Service Completion | astrometry | Implement astrometry.net local solver backend | 102 | 4 | 4 | Not Started | Primary solver |
| 104 | Core Service Completion | astrometry | Add index file configuration for astrometry.net | 103 | 3 | 2 | Not Started | Local index files |
| 105 | Core Service Completion | astrometry | Implement solve-field command wrapper | 104 | 3 | 2 | Not Started | Shell integration |
| 106 | Core Service Completion | astrometry | Parse astrometry.net WCS output | 105 | 3 | 2 | Not Started | Extract coordinates |
| 107 | Core Service Completion | astrometry | Implement ASTAP solver backend | 106 | 4 | 3 | Not Started | Fallback solver |
| 108 | Core Service Completion | astrometry | Add ASTAP star database configuration | 107 | 3 | 2 | Not Started | G17 database |
| 109 | Core Service Completion | astrometry | Implement ASTAP command wrapper | 108 | 3 | 2 | Not Started | Shell integration |
| 110 | Core Service Completion | astrometry | Parse ASTAP solution output | 109 | 3 | 2 | Not Started | Extract coordinates |
| 111 | Core Service Completion | astrometry | Implement solver selection logic (primary/fallback) | 110 | 3 | 2 | Not Started | Automatic fallback |
| 112 | Core Service Completion | astrometry | Add solve timeout handling (30s default) | 111 | 2 | 1 | Complete | SolverConfig.blind_timeout_sec/hint_timeout_sec in plate_solver.py |
| 113 | Core Service Completion | astrometry | Implement solve_with_hint() using mount position | 112 | 3 | 2 | Not Started | Faster solves |
| 114 | Core Service Completion | astrometry | Implement blind_solve() without hint | 113 | 3 | 2 | Not Started | Full-sky search |
| 115 | Core Service Completion | astrometry | Add pixel scale estimation from image | 114 | 3 | 2 | Not Started | Auto-detect scale |
| 116 | Core Service Completion | astrometry | Implement pointing error calculation | 115 | 3 | 2 | Not Started | Mount correction |
| 117 | Core Service Completion | astrometry | Add center_on_object() sync method | 116 | 3 | 2 | Not Started | Pointing refinement |
| 118 | Core Service Completion | astrometry | Create mock solver for testing | 117 | 3 | 2 | Complete | tests/mocks/mock_solver.py with error injection |
| 119 | Core Service Completion | astrometry | Write unit tests for solver backends | 118 | 2 | 2 | Complete | test_plate_solver.py (21 tests) |
| 120 | Core Service Completion | astrometry | Write integration test with camera | 119 | 3 | 2 | Not Started | End-to-end test |
| 121 | Core Service Completion | alerts | Review alert_manager.py current implementation | None | 2 | 1 | Complete | Understand gaps |
| 122 | Core Service Completion | alerts | Implement SMTP email notification channel | 121 | 3 | 2 | Complete | Email alerts |
| 123 | Core Service Completion | alerts | Add email template system (HTML + plain text) | 122 | 3 | 2 | Complete | Formatted emails |
| 124 | Core Service Completion | alerts | Implement email rate limiting (max 1/hour per alert type) | 123 | 2 | 2 | Complete | Prevent spam |
| 125 | Core Service Completion | alerts | Implement Twilio SMS notification channel | 124 | 3 | 3 | Not Started | Local-first: optional |
| 126 | Core Service Completion | alerts | Add SMS message formatting (160 char limit) | 125 | 2 | 1 | Complete | _format_sms_message() with smart truncation |
| 127 | Core Service Completion | alerts | Implement SMS rate limiting | 126 | 2 | 1 | Complete | _should_rate_limit_sms(), sms_min_interval_seconds, sms_max_per_hour |
| 128 | Core Service Completion | alerts | Implement local push notification (ntfy.sh compatible) | 127 | 3 | 2 | Complete | Self-hosted push |
| 129 | Core Service Completion | alerts | Implement webhook notification channel | 128 | 2 | 2 | Complete | Generic integration |
| 130 | Core Service Completion | alerts | Add Slack webhook support | 129 | 2 | 1 | Complete | Team notifications |
| 131 | Core Service Completion | alerts | Add Discord webhook support | 130 | 2 | 1 | Complete | Community notifications |
| 132 | Core Service Completion | alerts | Implement alert severity levels (INFO, WARNING, CRITICAL, EMERGENCY) | 131 | 2 | 1 | Complete | Alert classification |
| 133 | Core Service Completion | alerts | Implement alert escalation logic | 132 | 3 | 2 | Complete | Severity routing |
| 134 | Core Service Completion | alerts | Add alert acknowledgment tracking | 133 | 2 | 2 | Complete | Operator response |
| 135 | Core Service Completion | alerts | Implement alert history database (SQLite) | 134 | 3 | 2 | Complete | AlertHistoryDB class with full CRUD |
| 136 | Core Service Completion | alerts | Add alert deduplication | 135 | 2 | 2 | Complete | _is_duplicate method with dedup_window_seconds |
| 137 | Core Service Completion | alerts | Implement quiet hours configuration | 136 | 2 | 1 | Complete | _is_quiet_hours, quiet_hours_start/end config |
| 138 | Core Service Completion | alerts | Create mock notifier for testing | 137 | 2 | 1 | Complete | MockNotifier class records all sends |
| 139 | Core Service Completion | alerts | Write unit tests for alert channels | 138 | 2 | 2 | Complete | 29 tests in test_alerts.py |
| 140 | Core Service Completion | alerts | Write integration test for escalation | 139 | 2 | 2 | Complete | 7 tests in test_alert_escalation.py |
| 141 | Core Service Completion | power | Review power_manager.py current implementation | None | 2 | 1 | Complete | Good structure, NUT placeholder, thresholds configured |
| 142 | Core Service Completion | power | Implement NUT (Network UPS Tools) client | 141 | 4 | 3 | Complete | NUTClient class with TCP protocol |
| 143 | Core Service Completion | power | Add NUT protocol message parsing | 142 | 3 | 2 | Complete | LIST VAR, GET VAR, status flags |
| 144 | Core Service Completion | power | Implement battery percentage monitoring | 143 | 2 | 1 | Complete | battery.charge variable |
| 145 | Core Service Completion | power | Implement runtime estimation | 144 | 2 | 2 | Complete | battery.runtime variable |
| 146 | Core Service Completion | power | Implement input/output voltage monitoring | 145 | 2 | 1 | Complete | input.voltage, output.voltage |
| 147 | Core Service Completion | power | Implement load percentage monitoring | 146 | 2 | 1 | Complete | ups.load variable |
| 148 | Core Service Completion | power | Add battery threshold callbacks | 147 | 3 | 2 | Complete | _initiate_park, _emergency_shutdown on threshold |
| 149 | Core Service Completion | power | Implement park-at-threshold (50%) logic | 148 | 3 | 2 | Complete | park_threshold_pct in _process_status |
| 150 | Core Service Completion | power | Implement shutdown-at-threshold (20%) logic | 149 | 3 | 2 | Complete | emergency_threshold_pct, _emergency_shutdown |
| 151 | Core Service Completion | power | Add power event logging | 150 | 2 | 1 | Complete | _log_event, PowerEvent dataclass |
| 152 | Core Service Completion | power | Implement smart PDU port control (optional) | 151 | 4 | 3 | Not Started | Device power cycling |
| 153 | Core Service Completion | power | Add PDU HTTP/SNMP interface | 152 | 3 | 2 | Not Started | Protocol support |
| 154 | Core Service Completion | power | Implement sequenced power-on order | 153 | 3 | 2 | Not Started | Safe startup |
| 155 | Core Service Completion | power | Implement sequenced power-off order | 154 | 3 | 2 | Not Started | Safe shutdown |
| 156 | Core Service Completion | power | Create mock UPS for testing | 155 | 2 | 2 | Complete | _use_simulation mode in PowerManager |
| 157 | Core Service Completion | power | Write unit tests for NUT client | 156 | 2 | 2 | Complete | tests/unit/test_power_manager.py (29 tests) |
| 158 | Core Service Completion | power | Write integration test for thresholds | 157 | 2 | 2 | Complete | Threshold tests in test_power_manager.py |
| 159 | Core Service Completion | enclosure | Review roof_controller.py current implementation | None | 2 | 1 | Complete | Full ROR control, safety interlocks, rain holdoff |
| 160 | Core Service Completion | enclosure | Implement GPIO interface abstraction | 159 | 3 | 2 | Complete | GPIOInterface class with backend enum |
| 161 | Core Service Completion | enclosure | Add RPi.GPIO support for Raspberry Pi | 160 | 3 | 2 | Complete | _init_rpigpio() in GPIOInterface |
| 162 | Core Service Completion | enclosure | Add gpiozero support as alternative | 161 | 2 | 1 | Complete | GPIOInterface with gpiozero backend in roof_controller.py |
| 163 | Core Service Completion | enclosure | Implement relay control for motor | 162 | 3 | 2 | Complete | stop_motor(), relay control in GPIOInterface |
| 164 | Core Service Completion | enclosure | Add open/close relay wiring logic | 163 | 2 | 1 | Complete | set_motor_open_relay(), set_motor_close_relay() in GPIOInterface |
| 165 | Core Service Completion | enclosure | Implement limit switch reading (open limit) | 164 | 2 | 2 | Complete | read_open_limit() in GPIOInterface |
| 166 | Core Service Completion | enclosure | Implement limit switch reading (closed limit) | 165 | 2 | 1 | Complete | read_closed_limit() in GPIOInterface |
| 167 | Core Service Completion | enclosure | Add hardware rain sensor input | 166 | 3 | 2 | Complete | read_rain_sensor() in GPIOInterface |
| 168 | Core Service Completion | enclosure | Implement rain sensor interrupt handling | 167 | 3 | 2 | Not Started | Immediate response |
| 169 | Core Service Completion | enclosure | Add motor current monitoring (optional) | 168 | 4 | 3 | Not Started | Over-current protection |
| 170 | Core Service Completion | enclosure | Implement motor timeout protection (60s max) | 169 | 2 | 1 | Complete | _motor_timeout in roof_controller.py |
| 171 | Core Service Completion | enclosure | Add emergency stop input | 170 | 2 | 1 | Complete | emergency_stop() in roof_controller.py |
| 172 | Core Service Completion | enclosure | Implement position estimation (percentage) | 171 | 3 | 2 | Not Started | Partial open support |
| 173 | Core Service Completion | enclosure | Add mount park verification before open | 172 | 3 | 2 | Not Started | Safety interlock |
| 174 | Core Service Completion | enclosure | Implement 30-minute rain holdoff timer | 173 | 2 | 2 | Complete | get_rain_holdoff_status(), reset_rain_holdoff() in roof_controller.py |
| 175 | Core Service Completion | enclosure | Add power loss brake engagement | 174 | 3 | 2 | Not Started | Failsafe |
| 176 | Core Service Completion | enclosure | Implement status callbacks (opening, open, closing, closed) | 175 | 2 | 1 | Complete | register_status_callback() in roof_controller.py |
| 177 | Core Service Completion | enclosure | Create mock GPIO for testing | 176 | 2 | 2 | Complete | tests/mocks/mock_gpio.py |
| 178 | Core Service Completion | enclosure | Write unit tests for roof controller | 177 | 2 | 2 | Complete | tests/unit/test_roof_controller.py (45 tests) |
| 179 | Core Service Completion | enclosure | Write integration test with safety monitor | 178 | 3 | 2 | Not Started | End-to-end test |
| 180 | Core Service Completion | focus | Review focuser_service.py current implementation | None | 2 | 1 | Complete | Full autofocus, V-curve/HFD, temp compensation |
| 181 | Core Service Completion | focus | Complete V-curve autofocus algorithm | 180 | 4 | 3 | Not Started | Parabolic fit |
| 182 | Core Service Completion | focus | Add HFD (Half-Flux Diameter) calculation | 181 | 4 | 3 | Not Started | Star measurement |
| 183 | Core Service Completion | focus | Implement Bahtinov mask analysis | 182 | 5 | 4 | Not Started | Diffraction pattern |
| 184 | Core Service Completion | focus | Add contrast-based focusing | 183 | 3 | 2 | Not Started | Alternative method |
| 185 | Core Service Completion | focus | Implement temperature compensation calibration | 184 | 4 | 3 | Not Started | Auto-adjust for temp |
| 186 | Core Service Completion | focus | Add temperature coefficient storage | 185 | 2 | 1 | Complete | save/load_temp_coefficient() in focuser_service.py |
| 187 | Core Service Completion | focus | Implement backlash compensation | 186 | 3 | 2 | Complete | Direction-aware backlash tracking, calibrate_backlash(), get_backlash_info() in focuser_service.py |
| 188 | Core Service Completion | focus | Add focus position history tracking | 187 | 2 | 2 | Complete | FocusPositionRecord, get_position_history(), get_position_stats() in focuser_service.py |
| 189 | Core Service Completion | focus | Implement focus run database | 188 | 3 | 2 | Not Started | Analysis data |
| 190 | Core Service Completion | focus | Create mock focuser for testing | 189 | 2 | 2 | Complete | tests/mocks/mock_focuser.py with error injection |
| 191 | Core Service Completion | focus | Write unit tests for autofocus algorithms | 190 | 3 | 2 | Complete | tests/unit/test_focuser_service.py (35 tests) |
| 192 | Core Service Completion | focus | Write integration test with camera | 191 | 3 | 2 | Not Started | End-to-end test |
| 193 | Core Service Completion | guiding | Review phd2_client.py current implementation | None | 2 | 1 | Complete | Full JSON-RPC client, dither, calibration, events |
| 194 | Core Service Completion | guiding | Complete dither implementation | 193 | 3 | 2 | Complete | dither_and_wait() with settle detection in phd2_client.py |
| 195 | Core Service Completion | guiding | Add settling detection with timeout | 194 | 3 | 2 | Complete | wait_for_settle(), get_settle_status(), is_settling property in phd2_client.py |
| 196 | Core Service Completion | guiding | Implement guide star loss recovery | 195 | 3 | 2 | Complete | Auto-recovery with _auto_recover_star(), manual_recover_star() in phd2_client.py |
| 197 | Core Service Completion | guiding | Add RMS trending and alerts | 196 | 3 | 2 | Complete | RMS history, trending, alerts with callback in phd2_client.py |
| 198 | Core Service Completion | guiding | Implement guide log parsing | 197 | 3 | 2 | Complete | parse_guide_log(), analyze_guide_session() in phd2_client.py |
| 199 | Core Service Completion | guiding | Write unit tests for PHD2 client | 198 | 2 | 2 | Complete | tests/unit/test_phd2_client.py (18 tests) |
| 200 | Core Service Completion | weather | Review ecowitt.py current implementation | None | 2 | 1 | Complete | Full WS90 integration, safety thresholds |
| 201 | Core Service Completion | weather | Add AAG CloudWatcher integration | 200 | 4 | 3 | Not Started | Cloud sensing |
| 202 | Core Service Completion | weather | Implement CloudWatcher serial protocol | 201 | 3 | 2 | Not Started | Data parsing |
| 203 | Core Service Completion | weather | Add sky quality (SQM) reading | 202 | 2 | 1 | Complete | get_sky_quality() in ecowitt.py |
| 204 | Core Service Completion | weather | Add rain sensor reading | 203 | 2 | 1 | Complete | get_rain_sensor_reading() in ecowitt.py |
| 205 | Core Service Completion | weather | Add ambient temperature reading | 204 | 2 | 1 | Complete | get_ambient_temperature() in ecowitt.py |
| 206 | Core Service Completion | weather | Implement cloud threshold calibration | 205 | 3 | 2 | Not Started | Per POS Day 4 |
| 207 | Core Service Completion | weather | Add seeing estimation (FWHM proxy) | 206 | 4 | 3 | Not Started | Image quality prediction |
| 208 | Core Service Completion | weather | Create unified weather interface | 207 | 3 | 2 | Not Started | Abstract both sources |
| 209 | Core Service Completion | weather | Write unit tests for weather service | 208 | 2 | 2 | Complete | tests/unit/test_weather.py |
| 210 | Core Service Completion | ephemeris | Review skyfield_service.py current implementation | None | 2 | 1 | Complete | Full Skyfield integration, J2000/JNow, planets, twilight |
| 211 | Core Service Completion | ephemeris | Add proper motion correction for stars | 210 | 4 | 3 | Not Started | Epoch adjustment |
| 212 | Core Service Completion | Orchestrator Development | orchestrator | Create nightwatch/orchestrator.py module skeleton | 21 | 3 | 2 | Complete | Central orchestrator with protocols |
| 213 | Orchestrator Development | orchestrator | Define Orchestrator class with config injection | 212 | 2 | 1 | Complete | Config-based initialization |
| 214 | Orchestrator Development | orchestrator | Implement service registry for dependency injection | 213 | 3 | 2 | Complete | ServiceRegistry class |
| 215 | Orchestrator Development | orchestrator | Add mount service registration | 214 | 2 | 1 | Complete | register_mount() |
| 216 | Orchestrator Development | orchestrator | Add catalog service registration | 215 | 2 | 1 | Complete | register_catalog() |
| 217 | Orchestrator Development | orchestrator | Add ephemeris service registration | 216 | 2 | 1 | Complete | register_ephemeris() |
| 218 | Orchestrator Development | orchestrator | Add weather service registration | 217 | 2 | 1 | Complete | register_weather() |
| 219 | Orchestrator Development | orchestrator | Add safety monitor registration | 218 | 2 | 1 | Complete | register_safety() |
| 220 | Orchestrator Development | orchestrator | Add camera service registration | 219 | 2 | 1 | Complete | register_camera() |
| 221 | Orchestrator Development | orchestrator | Add guiding service registration | 220 | 2 | 1 | Complete | register_guiding() |
| 222 | Orchestrator Development | orchestrator | Add focus service registration | 221 | 2 | 1 | Complete | register_focus() |
| 223 | Orchestrator Development | orchestrator | Add astrometry service registration | 222 | 2 | 1 | Complete | register_astrometry() |
| 224 | Orchestrator Development | orchestrator | Add alert service registration | 223 | 2 | 1 | Complete | register_alerts() |
| 225 | Orchestrator Development | orchestrator | Add power service registration | 224 | 2 | 1 | Complete | register_power() |
| 226 | Orchestrator Development | orchestrator | Add enclosure service registration | 225 | 2 | 1 | Complete | register_enclosure() |
| 227 | Orchestrator Development | orchestrator | Implement async initialization sequence | 226 | 3 | 2 | Complete | start() method |
| 228 | Orchestrator Development | orchestrator | Add service health monitoring loop | 227 | 3 | 2 | Complete | _health_loop() |
| 229 | Orchestrator Development | orchestrator | Implement service restart on failure | 228 | 4 | 3 | Not Started | Auto-recovery |
| 230 | Orchestrator Development | orchestrator | Add session state management | 229 | 3 | 2 | Complete | SessionState dataclass |
| 231 | Orchestrator Development | orchestrator | Implement session start logic | 230 | 2 | 1 | Complete | start_session(), end_session() |
| 232 | Orchestrator Development | orchestrator | Implement session end logic (park, close) | 231 | 3 | 2 | Complete | end_session() with park, close, guiding stop in orchestrator.py |
| 233 | Orchestrator Development | orchestrator | Add observation log recording | 232 | 3 | 2 | Complete | ObservationLogEntry, log_observation(), log_target_acquired(), log_image_captured() in orchestrator.py |
| 234 | Orchestrator Development | orchestrator | Implement command queue | 233 | 3 | 2 | Complete | CommandQueue, QueuedCommand with priority ordering in orchestrator.py |
| 235 | Orchestrator Development | orchestrator | Add command priority levels | 234 | 2 | 1 | Complete | CommandPriority enum in orchestrator.py |
| 236 | Orchestrator Development | orchestrator | Implement command timeout handling | 235 | 3 | 2 | Complete | execute_with_timeout(), execute_slew_with_timeout(), DEFAULT_TIMEOUTS in orchestrator.py |
| 237 | Orchestrator Development | orchestrator | Add command cancellation support | 236 | 2 | 2 | Complete | execute_cancellable(), cancel_command(), cancel_all_commands() in orchestrator.py |
| 238 | Orchestrator Development | orchestrator | Implement error recovery strategies | 237 | 4 | 3 | Complete | auto_recover_service() routing to service-specific recovery in orchestrator.py |
| 239 | Orchestrator Development | orchestrator | Add mount error recovery (reconnect) | 238 | 3 | 2 | Complete | recover_mount() with retry in orchestrator.py |
| 240 | Orchestrator Development | orchestrator | Add weather error recovery (cache) | 239 | 3 | 2 | Complete | recover_weather() with cache fallback in orchestrator.py |
| 241 | Orchestrator Development | orchestrator | Add camera error recovery (reset) | 240 | 3 | 2 | Complete | recover_camera() with device reset in orchestrator.py |
| 242 | Orchestrator Development | orchestrator | Implement event bus for inter-service communication | 241 | 4 | 3 | Not Started | Loose coupling |
| 243 | Orchestrator Development | orchestrator | Add mount position changed event | 242 | 2 | 1 | Complete | Position updates |
| 244 | Orchestrator Development | orchestrator | Add weather changed event | 243 | 2 | 1 | Complete | Weather updates |
| 245 | Orchestrator Development | orchestrator | Add safety state changed event | 244 | 2 | 1 | Complete | Safety alerts |
| 246 | Orchestrator Development | orchestrator | Add guiding state changed event | 245 | 2 | 1 | Complete | Guide status |
| 247 | Orchestrator Development | orchestrator | Implement metrics collection | 246 | 3 | 2 | Complete | collect_metrics(), get_error_rate(), get_availability() in orchestrator.py |
| 248 | Orchestrator Development | orchestrator | Add command latency metrics | 247 | 2 | 1 | Complete | Timing data |
| 249 | Orchestrator Development | orchestrator | Add service uptime metrics | 248 | 2 | 1 | Complete | Availability |
| 250 | Orchestrator Development | orchestrator | Add error rate metrics | 249 | 2 | 1 | Complete | Failure tracking |
| 251 | Orchestrator Development | orchestrator | Implement graceful shutdown sequence | 250 | 3 | 2 | Complete | graceful_shutdown(), emergency_shutdown() in orchestrator.py |
| 252 | Orchestrator Development | orchestrator | Add park on shutdown | 251 | 2 | 1 | Complete | Safety |
| 253 | Orchestrator Development | orchestrator | Add close enclosure on shutdown | 252 | 2 | 1 | Complete | Safety |
| 254 | Orchestrator Development | orchestrator | Add save session log on shutdown | 253 | 2 | 1 | Complete | Data preservation |
| 255 | Orchestrator Development | orchestrator | Write unit tests for orchestrator | 254 | 3 | 3 | Not Started | Test coverage |
| 256 | Orchestrator Development | orchestrator | Write integration test with mock services | 255 | 3 | 2 | Not Started | End-to-end test |
| 257 | Orchestrator Development | tool_executor | Create nightwatch/tool_executor.py module | 212 | 3 | 2 | Complete | Full tool executor with handlers |
| 258 | Orchestrator Development | tool_executor | Define ToolExecutor class with orchestrator reference | 257 | 2 | 1 | Complete | Constructor with DI |
| 259 | Orchestrator Development | tool_executor | Implement tool registration from telescope_tools.py | 258 | 3 | 2 | Complete | register_handler() method |
| 260 | Orchestrator Development | tool_executor | Add tool parameter validation | 259 | 3 | 2 | Complete | Parameter checking in handlers |
| 261 | Orchestrator Development | tool_executor | Implement async tool execution | 260 | 3 | 2 | Complete | execute() with asyncio |
| 262 | Orchestrator Development | tool_executor | Add tool result formatting | 261 | 2 | 2 | Complete | ToolResult dataclass |
| 263 | Orchestrator Development | tool_executor | Implement tool timeout handling | 262 | 2 | 1 | Complete | asyncio.timeout() |
| 264 | Orchestrator Development | tool_executor | Add tool execution logging | 263 | 2 | 1 | Complete | _log_execution(), get_execution_log() |
| 265 | Orchestrator Development | tool_executor | Implement safety veto check before execution | 264 | 3 | 2 | Complete | VETOED status in handlers |
| 266 | Orchestrator Development | tool_executor | Add confirmation requirement for critical tools | 265 | 3 | 2 | Not Started | Sync, park, etc. |
| 267 | Orchestrator Development | tool_executor | Implement tool chaining for complex commands | 266 | 4 | 3 | Not Started | Multi-step operations |
| 268 | Orchestrator Development | tool_executor | Write unit tests for tool executor | 267 | 2 | 2 | Complete | 35 tests in test_tool_executor.py |
| 269 | Orchestrator Development | response_formatter | Create nightwatch/response_formatter.py module | 212 | 2 | 1 | Complete | Full formatter module |
| 270 | Orchestrator Development | response_formatter | Implement tool result to natural language conversion | 269 | 4 | 3 | Complete | format() method |
| 271 | Orchestrator Development | response_formatter | Add response templates for common results | 270 | 2 | 2 | Complete | RESPONSE_TEMPLATES dict |
| 272 | Orchestrator Development | response_formatter | Implement coordinate formatting (RA/Dec, Alt/Az) | 271 | 2 | 1 | Complete | format_ra(), format_dec(), format_alt_az() |
| 273 | Orchestrator Development | response_formatter | Add weather formatting (temperature, wind) | 272 | 2 | 1 | Complete | format_temperature(), format_wind() |
| 274 | Orchestrator Development | response_formatter | Implement error message formatting | 273 | 2 | 1 | Complete | format_error() method |
| 275 | Orchestrator Development | response_formatter | Add voice style adaptation (normal, alert, calm) | 274 | 3 | 2 | Complete | adapt_for_style(), format_with_style() |
| 276 | Orchestrator Development | response_formatter | Write unit tests for response formatter | 275 | 2 | 2 | Complete | 31 tests in test_response_formatter.py |
| 277 | Voice Pipeline Integration | llm | Create nightwatch/llm_client.py module | 21 | 3 | 2 | Complete | LLM integration |
| 278 | Voice Pipeline Integration | llm | Implement local Llama 3.2 client using llama-cpp-python | 277 | 4 | 3 | Complete | Local inference |
| 279 | Voice Pipeline Integration | llm | Add model loading with GPU offload | 278 | 3 | 2 | Complete | CUDA acceleration |
| 280 | Voice Pipeline Integration | llm | Implement chat completion with tool definitions | 279 | 4 | 3 | Complete | Function calling |
| 281 | Voice Pipeline Integration | llm | Add streaming response support | 280 | 3 | 2 | Not Started | Real-time output |
| 282 | Voice Pipeline Integration | llm | Implement tool call parsing from LLM response | 281 | 4 | 3 | Complete | Extract tool calls |
| 283 | Voice Pipeline Integration | llm | Add multi-turn conversation support | 282 | 3 | 2 | Complete | Context retention |
| 284 | Voice Pipeline Integration | llm | Implement conversation history management | 283 | 3 | 2 | Complete | Memory limit |
| 285 | Voice Pipeline Integration | llm | Add system prompt with observatory context | 284 | 2 | 1 | Complete | Telescope domain |
| 286 | Voice Pipeline Integration | llm | Implement Anthropic API client as fallback | 285 | 3 | 2 | Complete | Optional cloud |
| 287 | Voice Pipeline Integration | llm | Add OpenAI API client as fallback | 286 | 3 | 2 | Complete | Optional cloud |
| 288 | Voice Pipeline Integration | llm | Implement client selection based on config | 287 | 2 | 1 | Complete | Flexible backend |
| 289 | Voice Pipeline Integration | llm | Add response confidence scoring | 288 | 4 | 3 | Not Started | Quality check |
| 290 | Voice Pipeline Integration | llm | Implement low confidence confirmation request | 289 | 3 | 2 | Not Started | Ask for clarification |
| 291 | Voice Pipeline Integration | llm | Add token usage tracking | 290 | 2 | 1 | Complete | Cost monitoring |
| 292 | Voice Pipeline Integration | llm | Write unit tests for LLM client | 291 | 2 | 2 | Complete | Test coverage |
| 293 | Voice Pipeline Integration | voice_pipeline | Create nightwatch/voice_pipeline.py module | 277 | 3 | 2 | Complete | End-to-end voice |
| 294 | Voice Pipeline Integration | voice_pipeline | Define VoicePipeline class integrating STT, LLM, TTS | 293 | 3 | 2 | Complete | Pipeline coordinator |
| 295 | Voice Pipeline Integration | voice_pipeline | Implement audio capture with VAD | 294 | 3 | 2 | Not Started | Voice detection |
| 296 | Voice Pipeline Integration | voice_pipeline | Add push-to-talk mode support | 295 | 2 | 1 | Complete | input_mode, ptt_key in VoiceConfig |
| 297 | Voice Pipeline Integration | voice_pipeline | Implement continuous listening mode | 296 | 3 | 2 | Not Started | Hands-free |
| 298 | Voice Pipeline Integration | voice_pipeline | Add wake word detection (pymicro-vad as trigger) | 297 | 4 | 3 | Not Started | Voice activation |
| 299 | Voice Pipeline Integration | voice_pipeline | Implement STT transcription call | 298 | 2 | 1 | Complete | Speech to text |
| 300 | Voice Pipeline Integration | voice_pipeline | Add transcription post-processing (normalization) | 299 | 2 | 1 | Complete | normalize_transcript(), ASTRONOMY_NORMALIZATIONS |
| 301 | Voice Pipeline Integration | voice_pipeline | Implement LLM tool selection call | 300 | 3 | 2 | Not Started | Intent to tool |
| 302 | Voice Pipeline Integration | voice_pipeline | Add tool execution via orchestrator | 301 | 2 | 1 | Complete | Execute command |
| 303 | Voice Pipeline Integration | voice_pipeline | Implement response formatting call | 302 | 2 | 1 | Complete | Human text |
| 304 | Voice Pipeline Integration | voice_pipeline | Add TTS synthesis call | 303 | 2 | 1 | Complete | Text to speech |
| 305 | Voice Pipeline Integration | voice_pipeline | Implement audio playback | 304 | 2 | 1 | Complete | AudioPlayer class, play_response() |
| 306 | Voice Pipeline Integration | voice_pipeline | Add pipeline state machine | 305 | 3 | 2 | Not Started | State management |
| 307 | Voice Pipeline Integration | voice_pipeline | Implement concurrent request handling | 306 | 3 | 2 | Not Started | Multiple users |
| 308 | Voice Pipeline Integration | voice_pipeline | Add pipeline latency tracking | 307 | 2 | 1 | Complete | _record_latency(), get_latency_history(), enhanced get_metrics() |
| 309 | Voice Pipeline Integration | voice_pipeline | Implement audio feedback (beeps for state changes) | 308 | 2 | 1 | Complete | AudioFeedback class, _set_state() with feedback |
| 310 | Voice Pipeline Integration | voice_pipeline | Add visual indicator support (LED control) | 309 | 3 | 2 | Not Started | Status display |
| 311 | Voice Pipeline Integration | voice_pipeline | Write unit tests for voice pipeline | 310 | 3 | 2 | Complete | 55 tests in test_voice_pipeline.py |
| 312 | Voice Pipeline Integration | voice_pipeline | Write integration test end-to-end | 311 | 3 | 3 | Not Started | Full flow test |
| 313 | Voice Pipeline Integration | stt_integration | Integrate WhisperSTT with voice pipeline | 293 | 2 | 1 | Complete | STTInterface wraps faster-whisper |
| 314 | Voice Pipeline Integration | stt_integration | Configure DGX Spark optimized settings | 313 | 2 | 1 | Complete | beam_size, best_of, patience in VoiceConfig |
| 315 | Voice Pipeline Integration | stt_integration | Add audio preprocessing (noise reduction) | 314 | 3 | 2 | Not Started | Clean audio |
| 316 | Voice Pipeline Integration | stt_integration | Implement audio buffering for continuous mode | 315 | 3 | 2 | Not Started | Smooth capture |
| 317 | Voice Pipeline Integration | stt_integration | Add transcription confidence filtering | 316 | 2 | 1 | Complete | confidence_threshold in WyomingSTTServer (default 0.6) |
| 318 | Voice Pipeline Integration | stt_integration | Implement astronomy vocabulary boost | 317 | 3 | 2 | Not Started | Domain accuracy |
| 319 | Voice Pipeline Integration | stt_integration | Add multi-language support preparation | 318 | 2 | 1 | Complete | SUPPORTED_LANGUAGES, STT_SUPPORTED_LANGUAGES dicts in tts/stt servers |
| 320 | Voice Pipeline Integration | tts_integration | Integrate PiperTTS with voice pipeline | 293 | 2 | 1 | Complete | TTSInterface wraps piper-tts |
| 321 | Voice Pipeline Integration | tts_integration | Configure DGX Spark CUDA acceleration | 320 | 2 | 1 | Complete | cuda_device, cuda_memory_fraction in TTSConfig |
| 322 | Voice Pipeline Integration | tts_integration | Add response phrase caching | 321 | 3 | 2 | Not Started | Common responses |
| 323 | Voice Pipeline Integration | tts_integration | Implement dynamic speech rate based on urgency | 322 | 2 | 1 | Complete | detect_urgency(), get_urgency_rate() in tts_server.py |
| 324 | Voice Pipeline Integration | tts_integration | Add audio ducking (lower volume for background) | 323 | 3 | 2 | Not Started | Audio mix |
| 325 | Voice Pipeline Integration | wyoming_integration | Configure Wyoming STT server startup | 293 | 2 | 1 | Complete | WyomingManager.start_stt_server(), wyoming_* config fields |
| 326 | Voice Pipeline Integration | wyoming_integration | Configure Wyoming TTS server startup | 325 | 2 | 1 | Complete | WyomingManager.start_tts_server() in startup.py |
| 327 | Voice Pipeline Integration | wyoming_integration | Add Home Assistant compatibility | 326 | 3 | 2 | Not Started | HA integration |
| 328 | Voice Pipeline Integration | wyoming_integration | Implement Wyoming service discovery | 327 | 3 | 2 | Not Started | Auto-detect |
| 329 | Voice Pipeline Integration | wyoming_integration | Write integration test for Wyoming protocol | 328 | 2 | 2 | Complete | Protocol test |
| 330 | Tool Handler Implementation | mount_tools | Implement goto_object handler | 257,78 | 3 | 2 | Not Started | Core command |
| 331 | Tool Handler Implementation | mount_tools | Add catalog resolution in goto_object | 330 | 2 | 1 | Complete | catalog_service.lookup() in telescope_tools.py |
| 332 | Tool Handler Implementation | mount_tools | Add ephemeris resolution for planets in goto_object | 331 | 2 | 1 | Complete | ephemeris_service.get_body_position() in telescope_tools.py |
| 333 | Tool Handler Implementation | mount_tools | Add safety check before slew | 332 | 2 | 1 | Complete | safety_monitor.evaluate() in goto_object/goto_coordinates |
| 334 | Tool Handler Implementation | mount_tools | Add altitude limit check | 333 | 2 | 1 | Complete | 10° minimum altitude check in goto handlers |
| 335 | Tool Handler Implementation | mount_tools | Implement goto_coordinates handler | 334 | 2 | 1 | Complete | goto_coordinates() with safety and altitude checks |
| 336 | Tool Handler Implementation | mount_tools | Add coordinate validation (0-24h, -90 to +90) | 335 | 2 | 1 | Complete | Range and format validation in goto_coordinates |
| 337 | Tool Handler Implementation | mount_tools | Implement park_telescope handler | 336 | 2 | 1 | Complete | park_telescope() with status check |
| 338 | Tool Handler Implementation | mount_tools | Add confirmation requirement for park | 337 | 2 | 1 | Complete | park_telescope(confirmed) requires confirm if tracking |
| 339 | Tool Handler Implementation | mount_tools | Implement unpark_telescope handler | 338 | 2 | 1 | Complete | unpark_telescope() with safety check |
| 340 | Tool Handler Implementation | mount_tools | Add safety check before unpark | 339 | 2 | 1 | Complete | safety_monitor.evaluate() in unpark_telescope |
| 341 | Tool Handler Implementation | mount_tools | Implement stop_telescope handler | 340 | 2 | 1 | Complete | stop_telescope() emergency stop |
| 342 | Tool Handler Implementation | mount_tools | Add immediate execution for stop (bypass queue) | 341 | 2 | 1 | Complete | Direct call in stop_telescope handler |
| 343 | Tool Handler Implementation | mount_tools | Implement start_tracking handler | 342 | 2 | 1 | Complete | start_tracking() with park check |
| 344 | Tool Handler Implementation | mount_tools | Implement stop_tracking handler | 343 | 2 | 1 | Complete | stop_tracking() handler |
| 345 | Tool Handler Implementation | mount_tools | Implement get_mount_status handler | 344 | 2 | 1 | Complete | get_mount_status() with position and state |
| 346 | Tool Handler Implementation | mount_tools | Add formatted position in status response | 345 | 2 | 1 | Complete | RA/Dec formatting with altitude |
| 347 | Tool Handler Implementation | mount_tools | Implement sync_position handler | 346 | 2 | 1 | Complete | sync_position() with catalog/ephemeris lookup |
| 348 | Tool Handler Implementation | mount_tools | Add confirmation requirement for sync | 347 | 2 | 1 | Complete | sync_position(confirmed) requires confirm |
| 349 | Tool Handler Implementation | mount_tools | Implement home_telescope handler | 348 | 2 | 1 | Complete | home_telescope() with find_home/home fallback |
| 350 | Tool Handler Implementation | mount_tools | Add home position offset setting | 349 | 2 | 1 | Complete | set_home_offset() with ±60 arcmin validation |
| 351 | Tool Handler Implementation | mount_tools | Write unit tests for mount tool handlers | 350 | 2 | 2 | Complete | TestMountToolHandlers in test_telescope_tools.py (6 tests) |
| 352 | Tool Handler Implementation | catalog_tools | Implement lookup_object handler | 257,78 | 2 | 1 | Complete | Enhanced with type, mag, constellation, altitude |
| 353 | Tool Handler Implementation | catalog_tools | Add fuzzy name matching | 352 | 3 | 2 | Not Started | Typo tolerance |
| 354 | Tool Handler Implementation | catalog_tools | Implement what_am_i_looking_at handler | 353 | 3 | 2 | Not Started | Reverse lookup |
| 355 | Tool Handler Implementation | catalog_tools | Add nearest object search by coordinates | 354 | 3 | 2 | Not Started | Cone search |
| 356 | Tool Handler Implementation | catalog_tools | Implement find_objects handler | 355 | 2 | 1 | Complete | find_objects() with catalog search |
| 357 | Tool Handler Implementation | catalog_tools | Add filtering by type, magnitude, constellation | 356 | 2 | 1 | Complete | object_type, max_magnitude, constellation, min_altitude params |
| 358 | Tool Handler Implementation | catalog_tools | Write unit tests for catalog tool handlers | 357 | 2 | 2 | Complete | TestCatalogToolHandlers in test_telescope_tools.py (4 tests) |
| 359 | Tool Handler Implementation | ephemeris_tools | Implement get_planet_position handler | 257 | 2 | 1 | Complete | get_planet_position() with full coords |
| 360 | Tool Handler Implementation | ephemeris_tools | Add rise/set times in response | 359 | 2 | 1 | Complete | Rise/set/transit times in planet position |
| 361 | Tool Handler Implementation | ephemeris_tools | Implement get_visible_planets handler | 360 | 2 | 1 | Complete | Enhanced with compass direction and quality |
| 362 | Tool Handler Implementation | ephemeris_tools | Add altitude filter for visibility | 361 | 2 | 1 | Complete | min_altitude parameter with default 10° |
| 363 | Tool Handler Implementation | ephemeris_tools | Implement get_moon_info handler | 362 | 2 | 1 | Complete | get_moon_info() with position and phase |
| 364 | Tool Handler Implementation | ephemeris_tools | Add illumination percentage | 363 | 2 | 1 | Complete | Phase name and illumination in moon info |
| 365 | Tool Handler Implementation | ephemeris_tools | Implement is_it_dark handler | 364 | 2 | 1 | Complete | Enhanced is_it_dark() with time until |
| 366 | Tool Handler Implementation | ephemeris_tools | Add twilight phase details | 365 | 2 | 1 | Complete | Civil/nautical/astro descriptions |
| 367 | Tool Handler Implementation | ephemeris_tools | Implement whats_up_tonight handler | 366 | 3 | 2 | Not Started | Observing list |
| 368 | Tool Handler Implementation | ephemeris_tools | Add object prioritization by visibility window | 367 | 3 | 2 | Not Started | Best timing |
| 369 | Tool Handler Implementation | ephemeris_tools | Write unit tests for ephemeris tool handlers | 368 | 2 | 2 | Complete | TestEphemerisToolHandlers in test_telescope_tools.py (5 tests) |
| 370 | Tool Handler Implementation | weather_tools | Implement get_weather handler | 257 | 2 | 1 | Complete | Enhanced get_weather() with full conditions |
| 371 | Tool Handler Implementation | weather_tools | Add formatted temperature (F and C) | 370 | 2 | 1 | Complete | Both F and C in get_weather response |
| 372 | Tool Handler Implementation | weather_tools | Implement get_wind_speed handler | 371 | 2 | 1 | Complete | get_wind_speed() with direction |
| 373 | Tool Handler Implementation | weather_tools | Add gust warning in response | 372 | 2 | 1 | Complete | Gust warnings in get_wind_speed |
| 374 | Tool Handler Implementation | weather_tools | Implement get_cloud_status handler | 373 | 2 | 1 | Complete | get_cloud_status() with sky-ambient reading |
| 375 | Tool Handler Implementation | weather_tools | Add sky quality (SQM) in response | 374 | 2 | 1 | Complete | SQM mag/arcsec² with quality assessment |
| 376 | Tool Handler Implementation | weather_tools | Implement get_seeing_prediction handler | 375 | 3 | 2 | Not Started | Image quality |
| 377 | Tool Handler Implementation | weather_tools | Add FWHM estimate | 376 | 3 | 2 | Not Started | Arcsec estimate |
| 378 | Tool Handler Implementation | weather_tools | Write unit tests for weather tool handlers | 377 | 2 | 2 | Complete | TestWeatherToolHandlers in test_telescope_tools.py (4 tests) |
| 379 | Tool Handler Implementation | safety_tools | Implement is_safe_to_observe handler | 257 | 2 | 1 | Complete | Enhanced is_safe_to_observe() with context |
| 380 | Tool Handler Implementation | safety_tools | Add detailed reason if unsafe | 379 | 2 | 1 | Complete | Categorized reasons with current readings |
| 381 | Tool Handler Implementation | safety_tools | Implement get_sensor_health handler | 380 | 2 | 1 | Complete | get_sensor_health() returns string status |
| 382 | Tool Handler Implementation | safety_tools | Add last reading timestamps | 381 | 2 | 1 | Complete | Timestamps and age in sensor health |
| 383 | Tool Handler Implementation | safety_tools | Implement get_hysteresis_status handler | 382 | 2 | 1 | Complete | get_hysteresis_status() with triggered states |
| 384 | Tool Handler Implementation | safety_tools | Add time until threshold reset | 383 | 2 | 1 | Complete | time_to_reset with rain holdoff and resume times |
| 385 | Tool Handler Implementation | safety_tools | Write unit tests for safety tool handlers | 384 | 2 | 2 | Complete | TestSafetyToolHandlers in test_telescope_tools.py (5 tests) |
| 386 | Tool Handler Implementation | session_tools | Implement confirm_command handler | 257 | 2 | 1 | Complete | confirm_command() returns confirmation prompt |
| 387 | Tool Handler Implementation | session_tools | Add timeout for confirmation | 386 | 2 | 1 | Complete | timeout_seconds parameter (default 30) |
| 388 | Tool Handler Implementation | session_tools | Implement get_observation_log handler | 387 | 2 | 1 | Complete | Enhanced with session filter and date range |
| 389 | Tool Handler Implementation | session_tools | Add filtering by date range | 388 | 2 | 1 | Complete | start_date, end_date parameters |
| 390 | Tool Handler Implementation | session_tools | Implement set_voice_style handler | 389 | 2 | 1 | Complete | set_voice_style() with _voice_state tracking |
| 391 | Tool Handler Implementation | session_tools | Add style options (normal, alert, calm, technical) | 390 | 2 | 1 | Complete | normal, alert, calm, technical with rate adjustments |
| 392 | Tool Handler Implementation | session_tools | Write unit tests for session tool handlers | 391 | 2 | 2 | Complete | TestSessionToolHandlers in test_telescope_tools.py (4 tests) |
| 393 | Tool Handler Implementation | guiding_tools | Implement start_guiding handler | 257 | 3 | 2 | Not Started | Begin guiding |
| 394 | Tool Handler Implementation | guiding_tools | Add auto star selection option | 393 | 2 | 1 | Complete | auto_select, settle_pixels, settle_time params for start_guiding in telescope_tools.py |
| 395 | Tool Handler Implementation | guiding_tools | Implement stop_guiding handler | 394 | 2 | 1 | Complete | stop_guiding() with stop/stop_guiding fallback |
| 396 | Tool Handler Implementation | guiding_tools | Implement get_guiding_status handler | 395 | 2 | 1 | Complete | get_guiding_status() with state and RMS |
| 397 | Tool Handler Implementation | guiding_tools | Add RMS in arcseconds | 396 | 2 | 1 | Complete | RMS RA/Dec/total with quality assessment |
| 398 | Tool Handler Implementation | guiding_tools | Implement dither handler | 397 | 3 | 2 | Not Started | Imaging workflow |
| 399 | Tool Handler Implementation | guiding_tools | Add dither amount parameter | 398 | 2 | 1 | Complete | pixels, ra_only, wait_settle params for dither in telescope_tools.py |
| 400 | Tool Handler Implementation | guiding_tools | Write unit tests for guiding tool handlers | 399 | 2 | 2 | Complete | TestGuidingToolHandlers in test_telescope_tools.py (5 tests) |
| 401 | Tool Handler Implementation | camera_tools | Implement start_capture handler | 257 | 3 | 2 | Not Started | Begin imaging |
| 402 | Tool Handler Implementation | camera_tools | Add exposure and gain parameters | 401 | 2 | 1 | Complete | exposure_ms, gain, binning params for start_capture in telescope_tools.py |
| 403 | Tool Handler Implementation | camera_tools | Implement stop_capture handler | 402 | 2 | 1 | Complete | stop_capture() with abort_exposure fallback |
| 404 | Tool Handler Implementation | camera_tools | Implement get_camera_status handler | 403 | 2 | 1 | Complete | get_camera_status() with settings and progress |
| 405 | Tool Handler Implementation | camera_tools | Add temperature and cooling status | 404 | 2 | 1 | Complete | Temperature, cooler power, target temp in status |
| 406 | Tool Handler Implementation | camera_tools | Implement set_camera_gain handler | 405 | 2 | 1 | Complete | set_camera_gain() with context feedback |
| 407 | Tool Handler Implementation | camera_tools | Add gain range validation | 406 | 2 | 1 | Complete | Dynamic range check via get_gain_range |
| 408 | Tool Handler Implementation | camera_tools | Implement set_camera_exposure handler | 407 | 2 | 1 | Complete | set_camera_exposure() with smart formatting |
| 409 | Tool Handler Implementation | camera_tools | Add exposure range validation | 408 | 2 | 1 | Complete | Dynamic range check via get_exposure_range |
| 410 | Tool Handler Implementation | camera_tools | Write unit tests for camera tool handlers | 409 | 2 | 2 | Complete | TestCameraToolHandlers in test_telescope_tools.py (5 tests) |
| 411 | Tool Handler Implementation | focus_tools | Implement auto_focus handler | 257 | 3 | 2 | Not Started | Begin focus |
| 412 | Tool Handler Implementation | focus_tools | Add algorithm selection parameter | 411 | 2 | 1 | Complete | algorithm (vcurve/hfd/contrast), step_size, samples params in telescope_tools.py |
| 413 | Tool Handler Implementation | focus_tools | Implement get_focus_status handler | 412 | 2 | 1 | Complete | get_focus_status() with position, temp, HFD |
| 414 | Tool Handler Implementation | focus_tools | Add current position and temperature | 413 | 2 | 1 | Complete | Position, temp, temp_comp, HFD/FWHM in status |
| 415 | Tool Handler Implementation | focus_tools | Implement move_focus handler | 414 | 2 | 1 | Complete | move_focus() relative/absolute with validation |
| 416 | Tool Handler Implementation | focus_tools | Add direction and step parameters | 415 | 2 | 1 | Complete | steps, direction (in/out), position params |
| 417 | Tool Handler Implementation | focus_tools | Implement enable_temp_compensation handler | 416 | 2 | 1 | Complete | enable_temp_compensation() toggle with feedback |
| 418 | Tool Handler Implementation | focus_tools | Write unit tests for focus tool handlers | 417 | 2 | 2 | Complete | TestFocusToolHandlers in test_telescope_tools.py (5 tests) |
| 419 | Tool Handler Implementation | astrometry_tools | Implement plate_solve handler | 257 | 3 | 2 | Complete | plate_solve() with hint and timeout in telescope_tools.py |
| 420 | Tool Handler Implementation | astrometry_tools | Add timeout parameter | 419 | 2 | 1 | Complete | timeout_sec parameter (default 30s) |
| 421 | Tool Handler Implementation | astrometry_tools | Implement get_pointing_error handler | 420 | 2 | 1 | Complete | get_pointing_error() compares mount vs solve |
| 422 | Tool Handler Implementation | astrometry_tools | Add error in arcseconds | 421 | 2 | 1 | Complete | RA/Dec/total error with quality assessment |
| 423 | Tool Handler Implementation | astrometry_tools | Implement center_object handler | 422 | 3 | 2 | Not Started | Precise centering |
| 424 | Tool Handler Implementation | astrometry_tools | Add iterative refinement | 423 | 3 | 2 | Not Started | Multi-solve |
| 425 | Tool Handler Implementation | astrometry_tools | Write unit tests for astrometry tool handlers | 424 | 2 | 2 | Complete | TestAstrometryToolHandlers in test_telescope_tools.py (4 tests) |
| 426 | Tool Handler Implementation | enclosure_tools | Implement open_roof handler | 257 | 2 | 1 | Complete | open_roof() with park verification |
| 427 | Tool Handler Implementation | enclosure_tools | Add safety check before open | 426 | 2 | 1 | Complete | safety_monitor.evaluate() in open_roof |
| 428 | Tool Handler Implementation | enclosure_tools | Implement close_roof handler | 427 | 2 | 1 | Complete | close_roof() with state check |
| 429 | Tool Handler Implementation | enclosure_tools | Add force option for emergency | 428 | 2 | 1 | Complete | emergency=True bypasses checks |
| 430 | Tool Handler Implementation | enclosure_tools | Implement get_roof_status handler | 429 | 2 | 1 | Complete | get_roof_status() with blockers |
| 431 | Tool Handler Implementation | enclosure_tools | Add position percentage | 430 | 2 | 1 | Complete | get_position_percent() in status |
| 432 | Tool Handler Implementation | enclosure_tools | Implement stop_roof handler | 431 | 2 | 1 | Complete | stop_roof() emergency stop |
| 433 | Tool Handler Implementation | enclosure_tools | Write unit tests for enclosure tool handlers | 432 | 2 | 2 | Complete | TestEnclosureToolHandlers in test_telescope_tools.py (4 tests) |
| 434 | Tool Handler Implementation | power_tools | Implement get_power_status handler | 257 | 2 | 1 | Complete | get_power_status() with UPS data |
| 435 | Tool Handler Implementation | power_tools | Add battery percentage and runtime | 434 | 2 | 1 | Complete | Battery %, runtime, load in status |
| 436 | Tool Handler Implementation | power_tools | Implement get_power_events handler | 435 | 2 | 1 | Complete | get_power_events() with history |
| 437 | Tool Handler Implementation | power_tools | Add filtering by event type | 436 | 2 | 1 | Complete | event_type parameter for filtering |
| 438 | Tool Handler Implementation | power_tools | Implement emergency_shutdown handler | 437 | 3 | 2 | Not Started | Critical action |
| 439 | Tool Handler Implementation | power_tools | Add confirmation requirement | 438 | 2 | 1 | Complete | confirmed param in set_port_power(), power_cycle_port() |
| 440 | Tool Handler Implementation | power_tools | Write unit tests for power tool handlers | 439 | 2 | 2 | Complete | TestPowerToolHandlers in test_telescope_tools.py (4 tests) |
| 441 | Tool Handler Implementation | indi_tools | Implement indi_discover_devices handler | 257 | 3 | 2 | Not Started | Device scan |
| 442 | Tool Handler Implementation | indi_tools | Implement indi_connect_device handler | 441 | 2 | 1 | Complete | Connect device |
| 443 | Tool Handler Implementation | indi_tools | Implement indi_get_property handler | 442 | 2 | 1 | Complete | Read property |
| 444 | Tool Handler Implementation | indi_tools | Implement indi_set_property handler | 443 | 2 | 1 | Complete | Write property |
| 445 | Tool Handler Implementation | indi_tools | Write unit tests for INDI tool handlers | 444 | 2 | 2 | Complete | TestINDIToolHandlers in test_telescope_tools.py (4 tests) |
| 446 | Tool Handler Implementation | alpaca_tools | Implement alpaca_discover_devices handler | 257 | 3 | 2 | Not Started | Device scan |
| 447 | Tool Handler Implementation | alpaca_tools | Implement alpaca_connect_device handler | 446 | 2 | 1 | Complete | Connect device |
| 448 | Tool Handler Implementation | alpaca_tools | Implement alpaca_get_status handler | 447 | 2 | 1 | Complete | Device status |
| 449 | Tool Handler Implementation | alpaca_tools | Write unit tests for Alpaca tool handlers | 448 | 2 | 2 | Complete | TestAlpacaToolHandlers in test_telescope_tools.py (4 tests) |
| 450 | Tool Handler Implementation | encoder_tools | Implement get_encoder_position handler | 257 | 2 | 1 | Complete | get_encoder_position() with counts |
| 451 | Tool Handler Implementation | encoder_tools | Add formatted position (degrees) | 450 | 2 | 1 | Complete | Degrees and counts in output |
| 452 | Tool Handler Implementation | encoder_tools | Implement pec_status handler | 451 | 2 | 1 | Complete | pec_status() recording/playback state |
| 453 | Tool Handler Implementation | encoder_tools | Implement pec_record handler | 452 | 3 | 2 | Complete | pec_record() starts recording |
| 454 | Tool Handler Implementation | encoder_tools | Implement get_driver_status handler | 453 | 2 | 1 | Complete | get_driver_status() TMC diagnostics |
| 455 | Tool Handler Implementation | encoder_tools | Add StallGuard and current info | 454 | 2 | 1 | Complete | Stall, overtemp, load in diagnostics |
| 456 | Tool Handler Implementation | encoder_tools | Write unit tests for encoder tool handlers | 455 | 2 | 2 | Complete | TestEncoderToolHandlers in test_telescope_tools.py (4 tests) |
| 457 | Safety System Hardening | safety_monitor | Review safety_monitor.py current implementation | None | 2 | 1 | Complete | Full hysteresis, sensor timeouts, priority actions |
| 458 | Safety System Hardening | safety_monitor | Add sensor timeout detection (120s) | 457 | 3 | 2 | Complete | _is_sensor_stale with configurable timeouts |
| 459 | Safety System Hardening | safety_monitor | Implement failsafe on sensor timeout (treat as unsafe) | 458 | 3 | 2 | Complete | Stale weather data = unsafe |
| 460 | Safety System Hardening | safety_monitor | Add wind hysteresis (25mph park, 30mph emergency) | 459 | 2 | 1 | Complete | _wind_triggered with configurable hysteresis |
| 461 | Safety System Hardening | safety_monitor | Add humidity hysteresis (80% warning, 85% park) | 460 | 2 | 1 | Complete | _humidity_triggered with hysteresis |
| 462 | Safety System Hardening | safety_monitor | Add temperature hysteresis | 461 | 2 | 1 | Complete | Dew point margin check implemented |
| 463 | Safety System Hardening | safety_monitor | Implement cloud threshold calibration for altitude | 462 | 3 | 2 | Complete | SafetyThresholds with POS calibration |
| 464 | Safety System Hardening | safety_monitor | Add immediate rain response (no delay) | 463 | 2 | 1 | Complete | Rain = EMERGENCY, no hysteresis |
| 465 | Safety System Hardening | safety_monitor | Implement 30-minute rain holdoff | 464 | 2 | 1 | Complete | _evaluate_rain_holdoff(), configurable holdoff_minutes |
| 466 | Safety System Hardening | safety_monitor | Add sun altitude safety check | 465 | 2 | 1 | Complete | _evaluate_daylight with hysteresis |
| 467 | Safety System Hardening | safety_monitor | Implement horizon altitude limit check | 466 | 2 | 1 | Complete | _evaluate_altitude_limit(), min_altitude_deg, buffer |
| 468 | Safety System Hardening | safety_monitor | Add meridian safety zone | 467 | 3 | 2 | Complete | _evaluate_meridian(), meridian_safety_zone_deg, meridian_flip_zone_deg |
| 469 | Safety System Hardening | safety_monitor | Implement power level safety check | 468 | 2 | 1 | Complete | _evaluate_power(), warning/critical/emergency levels |
| 470 | Safety System Hardening | safety_monitor | Add enclosure safety integration | 469 | 2 | 1 | Complete | _evaluate_enclosure(), require_enclosure_open |
| 471 | Safety System Hardening | safety_monitor | Write unit tests for safety thresholds | 470 | 2 | 2 | Complete | 37 tests in test_safety_monitor.py |
| 472 | Safety System Hardening | safety_interlock | Create nightwatch/safety_interlock.py module | 457 | 3 | 2 | Complete | CommandType, SafetyVeto, InterlockStatus |
| 473 | Safety System Hardening | safety_interlock | Implement pre-command safety check | 472 | 3 | 2 | Complete | check_command(), runs all safety checks |
| 474 | Safety System Hardening | safety_interlock | Add command-specific safety rules | 473 | 3 | 2 | Complete | Per-command _check_* methods |
| 475 | Safety System Hardening | safety_interlock | Implement slew safety check (altitude, weather) | 474 | 2 | 1 | Complete | _check_slew_safety() |
| 476 | Safety System Hardening | safety_interlock | Implement unpark safety check (weather, enclosure) | 475 | 2 | 1 | Complete | _check_unpark_safety() |
| 477 | Safety System Hardening | safety_interlock | Implement roof open safety check | 476 | 2 | 1 | Complete | _check_roof_open_safety() |
| 478 | Safety System Hardening | safety_interlock | Add safety override for emergency commands | 477 | 2 | 1 | Complete | EMERGENCY_COMMANDS set |
| 479 | Safety System Hardening | safety_interlock | Implement safety veto response message | 478 | 2 | 1 | Complete | SafetyVeto.to_spoken_response() |
| 480 | Safety System Hardening | safety_interlock | Write unit tests for safety interlock | 479 | 2 | 2 | Complete | 46 tests in test_safety_interlock.py |
| 481 | Safety System Hardening | emergency_response | Create nightwatch/emergency_response.py module | 457 | 3 | 2 | Complete | EmergencyResponse class with full infrastructure |
| 482 | Safety System Hardening | emergency_response | Implement emergency park sequence | 481 | 3 | 2 | Complete | emergency_park() with retries and timeout |
| 483 | Safety System Hardening | emergency_response | Implement emergency close sequence | 482 | 3 | 2 | Complete | emergency_close() with retries and timeout |
| 484 | Safety System Hardening | emergency_response | Add mount safety position for enclosure close | 483 | 3 | 2 | Complete | move_to_safety_position() checks altitude and parks if needed |
| 485 | Safety System Hardening | emergency_response | Implement power failure response | 484 | 4 | 3 | Not Started | UPS detected |
| 486 | Safety System Hardening | emergency_response | Add staged shutdown on low battery | 485 | 3 | 2 | Not Started | Graceful degradation |
| 487 | Safety System Hardening | emergency_response | Implement weather emergency response | 486 | 3 | 2 | Complete | respond_to_weather() handles storm/high_wind with safety position |
| 488 | Safety System Hardening | emergency_response | Add rain emergency response | 487 | 3 | 2 | Complete | respond_to_rain() with park+close+alerts |
| 489 | Safety System Hardening | emergency_response | Implement network failure response | 488 | 3 | 2 | Not Started | Lose connectivity |
| 490 | Safety System Hardening | emergency_response | Add alert escalation during emergency | 489 | 2 | 1 | Complete | _send_alert() and escalate_alert() |
| 491 | Safety System Hardening | emergency_response | Write unit tests for emergency response | 490 | 2 | 2 | Complete | tests/unit/test_emergency_response.py (40 tests) |
| 492 | Safety System Hardening | watchdog | Create nightwatch/watchdog.py module | 457 | 3 | 2 | Complete | System health |
| 493 | Safety System Hardening | watchdog | Implement service heartbeat monitoring | 492 | 3 | 2 | Complete | Detect hangs |
| 494 | Safety System Hardening | watchdog | Add mount communication watchdog | 493 | 2 | 1 | Complete | Mount health |
| 495 | Safety System Hardening | watchdog | Add weather communication watchdog | 494 | 2 | 1 | Complete | Weather health |
| 496 | Safety System Hardening | watchdog | Add camera communication watchdog | 495 | 2 | 1 | Complete | Camera health |
| 497 | Safety System Hardening | watchdog | Implement automatic service restart | 496 | 3 | 2 | Complete | Auto-recovery |
| 498 | Safety System Hardening | watchdog | Add restart attempt limit | 497 | 2 | 1 | Complete | Prevent loop |
| 499 | Safety System Hardening | watchdog | Implement safe state on persistent failure | 498 | 3 | 2 | Complete | SafeStateHandler.enter_safe_state() parks, closes, alerts |
| 500 | Safety System Hardening | watchdog | Write unit tests for watchdog | 499 | 2 | 2 | Complete | Test coverage |
| 501 | Hardware-in-Loop Simulation | docker | Review docker-compose.dev.yml current state | None | 2 | 1 | Complete | Already well-configured with Alpaca/INDI simulators |
| 502 | Hardware-in-Loop Simulation | docker | Add mount simulator service | 501 | 3 | 2 | Not Started | OnStepX sim |
| 503 | Hardware-in-Loop Simulation | docker | Configure mount simulator with LX200 protocol | 502 | 2 | 1 | Not Started | TCP port 9999 |
| 504 | Hardware-in-Loop Simulation | docker | Add weather simulator service | 503 | 3 | 2 | Not Started | Ecowitt sim |
| 505 | Hardware-in-Loop Simulation | docker | Configure weather simulator with HTTP API | 504 | 2 | 1 | Not Started | Mock data |
| 506 | Hardware-in-Loop Simulation | docker | Add cloud sensor simulator service | 505 | 3 | 2 | Not Started | AAG sim |
| 507 | Hardware-in-Loop Simulation | docker | Configure cloud simulator with serial protocol | 506 | 2 | 1 | Not Started | Mock data |
| 508 | Hardware-in-Loop Simulation | docker | Add PHD2 simulator service | 507 | 3 | 2 | Not Started | Guiding sim |
| 509 | Hardware-in-Loop Simulation | docker | Configure PHD2 simulator JSON-RPC | 508 | 2 | 1 | Not Started | Port 4400 |
| 510 | Hardware-in-Loop Simulation | docker | Add INDI simulator configuration | 509 | 2 | 1 | Not Started | Device sim |
| 511 | Hardware-in-Loop Simulation | docker | Add Alpaca simulator configuration | 510 | 2 | 1 | Not Started | Device sim |
| 512 | Hardware-in-Loop Simulation | docker | Create docker-compose.test.yml for CI | 511 | 2 | 2 | Complete | Lightweight |
| 513 | Hardware-in-Loop Simulation | docker | Add healthcheck for all services | 512 | 2 | 1 | Complete | Startup wait |
| 514 | Hardware-in-Loop Simulation | docker | Create docker-compose.prod.yml template | 513 | 2 | 2 | Complete | Production config |
| 515 | Hardware-in-Loop Simulation | docker | Write docker-compose validation test | 514 | 2 | 1 | Complete | Syntax check |
| 516 | Hardware-in-Loop Simulation | simulators | Create services/simulators/__init__.py | 501 | 1 | 1 | Complete | BaseSimulator, SimulatorConfig, SimulatorStats, FaultConfig classes |
| 517 | Hardware-in-Loop Simulation | simulators | Create mount_simulator.py | 516 | 4 | 3 | Not Started | LX200 simulator |
| 518 | Hardware-in-Loop Simulation | simulators | Implement LX200 command parsing | 517 | 3 | 2 | Not Started | Protocol handling |
| 519 | Hardware-in-Loop Simulation | simulators | Add simulated position tracking | 518 | 3 | 2 | Not Started | Virtual mount |
| 520 | Hardware-in-Loop Simulation | simulators | Add simulated slew behavior | 519 | 3 | 2 | Not Started | Movement timing |
| 521 | Hardware-in-Loop Simulation | simulators | Add simulated tracking rate | 520 | 2 | 1 | Complete | TrackingRate enum (sidereal/lunar/solar/king) in mount_simulator.py |
| 522 | Hardware-in-Loop Simulation | simulators | Implement park/unpark simulation | 521 | 2 | 1 | Complete | MountState enum, park/unpark methods in mount_simulator.py |
| 523 | Hardware-in-Loop Simulation | simulators | Add configurable fault injection | 522 | 3 | 2 | Not Started | Error testing |
| 524 | Hardware-in-Loop Simulation | simulators | Create weather_simulator.py | 523 | 3 | 2 | Not Started | Weather sim |
| 525 | Hardware-in-Loop Simulation | simulators | Implement Ecowitt API simulation | 524 | 3 | 2 | Not Started | HTTP responses |
| 526 | Hardware-in-Loop Simulation | simulators | Add weather pattern generation | 525 | 3 | 2 | Not Started | Varying conditions |
| 527 | Hardware-in-Loop Simulation | simulators | Add configurable weather scenarios | 526 | 2 | 1 | Complete | WeatherScenario enum, SCENARIO_PRESETS in weather_simulator.py |
| 528 | Hardware-in-Loop Simulation | simulators | Create camera_simulator.py | 527 | 3 | 2 | Not Started | Camera sim |
| 529 | Hardware-in-Loop Simulation | simulators | Implement simulated image generation | 528 | 4 | 3 | Not Started | Synthetic stars |
| 530 | Hardware-in-Loop Simulation | simulators | Add configurable star field | 529 | 3 | 2 | Not Started | Test images |
| 531 | Hardware-in-Loop Simulation | simulators | Add noise simulation | 530 | 2 | 1 | Complete | Realistic images |
| 532 | Hardware-in-Loop Simulation | simulators | Create phd2_simulator.py | 531 | 3 | 2 | Not Started | Guiding sim |
| 533 | Hardware-in-Loop Simulation | simulators | Implement JSON-RPC protocol | 532 | 3 | 2 | Not Started | PHD2 API |
| 534 | Hardware-in-Loop Simulation | simulators | Add simulated guide star tracking | 533 | 3 | 2 | Not Started | Virtual guiding |
| 535 | Hardware-in-Loop Simulation | simulators | Add configurable RMS levels | 534 | 2 | 1 | Complete | RMSQuality enum, RMS_PRESETS in guider_simulator.py |
| 536 | Hardware-in-Loop Simulation | test_fixtures | Create tests/fixtures/__init__.py | 501 | 1 | 1 | Complete | Package |
| 537 | Hardware-in-Loop Simulation | test_fixtures | Create mock_mount.py fixture | 536 | 3 | 2 | Complete | Mount mock |
| 538 | Hardware-in-Loop Simulation | test_fixtures | Create mock_weather.py fixture | 537 | 3 | 2 | Complete | Weather mock |
| 539 | Hardware-in-Loop Simulation | test_fixtures | Create mock_camera.py fixture | 538 | 3 | 2 | Complete | Camera mock |
| 540 | Hardware-in-Loop Simulation | test_fixtures | Create mock_guider.py fixture | 539 | 3 | 2 | Complete | Guider mock |
| 541 | Hardware-in-Loop Simulation | test_fixtures | Create mock_focuser.py fixture | 540 | 3 | 2 | Complete | Focuser mock |
| 542 | Hardware-in-Loop Simulation | test_fixtures | Create mock_enclosure.py fixture | 541 | 3 | 2 | Complete | Enclosure mock |
| 543 | Hardware-in-Loop Simulation | test_fixtures | Create mock_power.py fixture | 542 | 3 | 2 | Complete | Power mock |
| 544 | Hardware-in-Loop Simulation | test_fixtures | Create mock_llm.py fixture | 543 | 3 | 2 | Complete | LLM mock |
| 545 | Hardware-in-Loop Simulation | test_fixtures | Create mock_stt.py fixture | 544 | 3 | 2 | Complete | STT mock |
| 546 | Hardware-in-Loop Simulation | test_fixtures | Create mock_tts.py fixture | 545 | 3 | 2 | Complete | TTS mock |
| 547 | Hardware-in-Loop Simulation | test_fixtures | Create conftest.py with shared fixtures | 546 | 3 | 2 | Complete | pytest fixtures |
| 548 | Hardware-in-Loop Simulation | test_fixtures | Write fixture documentation | 547 | 2 | 1 | Complete | Usage guide |
| 549 | Testing & Quality Assurance | unit_tests | Create tests/unit/test_config.py | 21 | 2 | 1 | Complete | Config tests |
| 550 | Testing & Quality Assurance | unit_tests | Create tests/unit/test_orchestrator.py | 255 | 3 | 2 | Complete | 879 lines, comprehensive tests |
| 551 | Testing & Quality Assurance | unit_tests | Create tests/unit/test_tool_executor.py | 268 | 3 | 2 | Complete | 371 lines, 35+ tests |
| 552 | Testing & Quality Assurance | unit_tests | Create tests/unit/test_response_formatter.py | 276 | 2 | 1 | Complete | 325 lines, 31+ tests |
| 553 | Testing & Quality Assurance | unit_tests | Create tests/unit/test_llm_client.py | 292 | 3 | 2 | Complete | 402 lines, LLM tests |
| 554 | Testing & Quality Assurance | unit_tests | Create tests/unit/test_voice_pipeline.py | 311 | 3 | 2 | Complete | 660 lines, 55+ tests |
| 555 | Testing & Quality Assurance | unit_tests | Create tests/unit/test_safety_interlock.py | 480 | 2 | 2 | Complete | 539 lines, 46+ tests |
| 556 | Testing & Quality Assurance | unit_tests | Create tests/unit/test_emergency_response.py | 491 | 2 | 2 | Complete | 40 tests for emergency response |
| 557 | Testing & Quality Assurance | unit_tests | Create tests/unit/test_watchdog.py | 500 | 2 | 2 | Complete | 666 lines, watchdog tests |
| 558 | Testing & Quality Assurance | unit_tests | Expand tests/unit/test_catalog.py | 81 | 2 | 2 | Complete | Added edge cases, formatting tests |
| 559 | Testing & Quality Assurance | unit_tests | Expand tests/unit/test_camera.py | 100 | 2 | 2 | Complete | Created with enums, settings, presets tests |
| 560 | Testing & Quality Assurance | unit_tests | Expand tests/unit/test_astrometry.py | 119 | 2 | 2 | Complete | Created with solver config, result tests |
| 561 | Testing & Quality Assurance | unit_tests | Expand tests/unit/test_alerts.py | 139 | 2 | 2 | Complete | Already comprehensive (672 lines, 28 test classes) |
| 562 | Testing & Quality Assurance | unit_tests | Expand tests/unit/test_power.py | 157 | 2 | 2 | Complete | Created with NUT client, PowerManager, PDU tests |
| 563 | Testing & Quality Assurance | unit_tests | Expand tests/unit/test_enclosure.py | 178 | 2 | 2 | Complete | Created with GPIO, RoofController, safety tests |
| 564 | Testing & Quality Assurance | unit_tests | Expand tests/unit/test_focus.py | 191 | 2 | 2 | Complete | Created with config, state, metrics tests |
| 565 | Testing & Quality Assurance | integration_tests | Create tests/integration/test_mount_catalog.py | 351,358 | 3 | 2 | Complete | Mount+catalog |
| 566 | Testing & Quality Assurance | integration_tests | Create tests/integration/test_voice_mount.py | 312,351 | 3 | 3 | Not Started | Voice+mount |
| 567 | Testing & Quality Assurance | integration_tests | Create tests/integration/test_safety_mount.py | 480,351 | 3 | 2 | Complete | Safety+mount |
| 568 | Testing & Quality Assurance | integration_tests | Create tests/integration/test_safety_enclosure.py | 480,433 | 3 | 2 | Complete | Safety+enclosure |
| 569 | Testing & Quality Assurance | integration_tests | Create tests/integration/test_orchestrator_services.py | 256,547 | 3 | 3 | Not Started | Full orchestration |
| 570 | Testing & Quality Assurance | integration_tests | Create tests/integration/test_full_pipeline.py | 312,569 | 4 | 3 | Not Started | End-to-end |
| 571 | Testing & Quality Assurance | integration_tests | Add simulator startup helper | 570 | 2 | 1 | Complete | SimulatorManager.start(), start_simulators() in tests/integration/__init__.py |
| 572 | Testing & Quality Assurance | integration_tests | Add simulator shutdown helper | 571 | 2 | 1 | Complete | SimulatorManager.stop(), stop_simulators() in tests/integration/__init__.py |
| 573 | Testing & Quality Assurance | e2e_tests | Create tests/e2e/__init__.py | 570 | 1 | 1 | Complete | E2E test package with pytest markers for e2e, requires_simulators, slow |
| 574 | Testing & Quality Assurance | e2e_tests | Create tests/e2e/test_goto_object.py | 573 | 3 | 2 | Complete | Voice to slew e2e with catalog lookup, safety checks |
| 575 | Testing & Quality Assurance | e2e_tests | Create tests/e2e/test_park_unpark.py | 574 | 3 | 2 | Complete | Park/unpark cycle e2e with safety checks |
| 576 | Testing & Quality Assurance | e2e_tests | Create tests/e2e/test_safety_veto.py | 575 | 3 | 2 | Complete | Safety veto e2e for wind, rain, horizon limits |
| 577 | Testing & Quality Assurance | e2e_tests | Create tests/e2e/test_weather_response.py | 576 | 3 | 2 | Complete | Weather degradation, improvement, query e2e tests |
| 578 | Testing & Quality Assurance | e2e_tests | Create tests/e2e/test_session_flow.py | 577 | 4 | 3 | Not Started | Full session |
| 579 | Testing & Quality Assurance | e2e_tests | Create tests/e2e/test_emergency_shutdown.py | 578 | 3 | 2 | Not Started | Emergency flow |
| 580 | Testing & Quality Assurance | e2e_tests | Add audio fixture files for voice tests | 579 | 2 | 2 | Complete | Test audio |
| 581 | Testing & Quality Assurance | ci_cd | Review .github/workflows/ci.yml | None | 2 | 1 | Complete | Has unit tests, integration, lint, docker validation |
| 582 | Testing & Quality Assurance | ci_cd | Add unit test job with coverage | 581 | 2 | 1 | Complete | pytest --cov with XML/HTML reports in ci.yml |
| 583 | Testing & Quality Assurance | ci_cd | Add coverage threshold check (80%) | 582 | 2 | 1 | Complete | Coverage threshold check step in ci.yml with warning on <80% |
| 584 | Testing & Quality Assurance | ci_cd | Add integration test job with simulators | 583 | 3 | 2 | Not Started | Docker tests |
| 585 | Testing & Quality Assurance | ci_cd | Add e2e test job | 584 | 3 | 2 | Not Started | Full tests |
| 586 | Testing & Quality Assurance | ci_cd | Add type checking job (mypy) | 585 | 2 | 1 | Complete | type-check job in ci.yml with mypy on nightwatch/services/voice |
| 587 | Testing & Quality Assurance | ci_cd | Add linting job (ruff) | 586 | 2 | 1 | Complete | Enhanced lint job with ruff check and format in ci.yml |
| 588 | Testing & Quality Assurance | ci_cd | Add security scanning job | 587 | 3 | 2 | Not Started | Vulnerability check |
| 589 | Testing & Quality Assurance | ci_cd | Add documentation build job | 588 | 2 | 1 | Complete | docs-validation job in ci.yml |
| 590 | Testing & Quality Assurance | ci_cd | Add release automation | 589 | 3 | 2 | Not Started | Version tagging |
| 591 | Testing & Quality Assurance | ci_cd | Create GitHub issue templates | 590 | 2 | 1 | Complete | Bug report, feature request |
| 592 | Testing & Quality Assurance | ci_cd | Create pull request template | 591 | 2 | 1 | Complete | Safety checklist included |
| 593 | Testing & Quality Assurance | ci_cd | Add branch protection rules documentation | 592 | 2 | 1 | Complete | In CONTRIBUTING.md |
| 594 | Documentation & POS | docs | Update README.md with v0.1 quickstart | None | 3 | 2 | Not Started | Entry point |
| 595 | Documentation & POS | docs | Add installation section | 594 | 2 | 1 | Complete | INSTALLATION.md comprehensive guide exists |
| 596 | Documentation & POS | docs | Add configuration section | 595 | 2 | 1 | Complete | Created docs/CONFIGURATION.md with full config reference |
| 597 | Documentation & POS | docs | Add voice command examples | 596 | 2 | 1 | Complete | VOICE_COMMANDS.md already has comprehensive examples |
| 598 | Documentation & POS | docs | Create docs/QUICKSTART.md | 597 | 3 | 2 | Not Started | Fast setup |
| 599 | Documentation & POS | docs | Create docs/CONFIGURATION.md | 598 | 3 | 2 | Complete | Created in step 596 |
| 600 | Documentation & POS | docs | Create docs/VOICE_COMMANDS.md | 599 | 2 | 2 | Complete | Already exists, comprehensive |
| 601 | Documentation & POS | docs | Create docs/API_REFERENCE.md | 600 | 4 | 3 | Not Started | Service APIs |
| 602 | Documentation & POS | docs | Create docs/TROUBLESHOOTING.md | 601 | 3 | 2 | Not Started | Common issues |
| 603 | Documentation & POS | docs | Create docs/HARDWARE_SETUP.md | 602 | 3 | 2 | Complete | OnStepX, Ecowitt, Audio, Network |
| 604 | Documentation & POS | docs | Create docs/SIMULATOR_GUIDE.md | 603 | 2 | 2 | Complete | Alpaca, INDI, Mock fixtures |
| 605 | Documentation & POS | docs | Update docs/INTEGRATION_PLAN.md for v0.1 | 604 | 2 | 1 | Complete | Alignment |
| 606 | Documentation & POS | docs | Add architecture diagrams (Mermaid) | 605 | 3 | 2 | Not Started | Visual docs |
| 607 | Documentation & POS | docs | Add sequence diagrams for key flows | 606 | 3 | 2 | Not Started | Visual docs |
| 608 | Documentation & POS | pos | Create POS deliberation for LLM integration | None | 4 | 3 | Not Started | Expert consensus |
| 609 | Documentation & POS | pos | Add Michael Clive perspective (DGX Spark) | 608 | 3 | 2 | Not Started | AI expert |
| 610 | Documentation & POS | pos | Add Alec Radford perspective (Whisper) | 609 | 3 | 2 | Not Started | STT expert |
| 611 | Documentation & POS | pos | Add Michael Hansen perspective (Piper) | 610 | 3 | 2 | Not Started | TTS expert |
| 612 | Documentation & POS | pos | Document LLM model selection rationale | 611 | 2 | 1 | Complete | Decision record |
| 613 | Documentation & POS | pos | Create POS deliberation for tool confirmation | 612 | 3 | 2 | Not Started | Safety design |
| 614 | Documentation & POS | pos | Create POS deliberation for emergency response | 613 | 3 | 2 | Not Started | Safety design |
| 615 | Documentation & POS | pos | Update POS_RETREAT_SIMULATION.md with v0.1 decisions | 614 | 2 | 2 | Complete | Record keeping |
| 616 | Deployment Preparation | install | Create install.sh installation script | None | 3 | 2 | Complete | Full installer with all steps |
| 617 | Deployment Preparation | install | Add Python version check | 616 | 2 | 1 | Complete | Min 3.10, recommended 3.11 |
| 618 | Deployment Preparation | install | Add system dependency installation | 617 | 2 | 1 | Complete | Debian/Fedora/macOS support |
| 619 | Deployment Preparation | install | Add virtual environment creation | 618 | 2 | 1 | Complete | venv with pip upgrade |
| 620 | Deployment Preparation | install | Add pip dependency installation | 619 | 2 | 1 | Complete | Services + voice + dev deps |
| 621 | Deployment Preparation | install | Add configuration template generation | 620 | 2 | 1 | Complete | Full YAML template |
| 622 | Deployment Preparation | install | Create install.bat for Windows | 621 | 3 | 2 | Not Started | Windows install |
| 623 | Deployment Preparation | install | Create upgrade.sh script | 622 | 2 | 1 | Complete | Backup, update, restart services |
| 624 | Deployment Preparation | install | Write installation documentation | 623 | 2 | 1 | Complete | INSTALLATION.md created |
| 625 | Deployment Preparation | systemd | Create nightwatch.service systemd unit | None | 3 | 2 | Complete | Full service with security hardening |
| 626 | Deployment Preparation | systemd | Add automatic restart on failure | 625 | 2 | 1 | Complete | RestartSec=10, StartLimitBurst=5 |
| 627 | Deployment Preparation | systemd | Add watchdog integration | 626 | 2 | 1 | Complete | WatchdogSec=30, NotifyAccess=main |
| 628 | Deployment Preparation | systemd | Create nightwatch-wyoming.service | 627 | 2 | 1 | Complete | STT/TTS on ports 10200/10300 |
| 629 | Deployment Preparation | systemd | Write systemd documentation | 628 | 2 | 1 | Complete | Full README with install, manage, troubleshoot |
| 630 | Deployment Preparation | hardware | Document OnStepX controller wiring | None | 3 | 2 | Complete | In HARDWARE_SETUP.md |
| 631 | Deployment Preparation | hardware | Document Teensy 4.1 pin assignments | 630 | 2 | 1 | Complete | Pin table in HARDWARE_SETUP.md |
| 632 | Deployment Preparation | hardware | Document encoder wiring | 631 | 2 | 1 | Complete | AMT103-V in HARDWARE_SETUP.md |
| 633 | Deployment Preparation | hardware | Document Ecowitt WS90 network setup | 632 | 2 | 1 | Complete | Network config in HARDWARE_SETUP.md |
| 634 | Deployment Preparation | hardware | Document AAG CloudWatcher serial setup | 633 | 2 | 1 | Complete | Cloud sensor section in HARDWARE_SETUP.md |
| 635 | Deployment Preparation | hardware | Document DGX Spark setup | 634 | 3 | 2 | Not Started | AI compute |
| 636 | Deployment Preparation | hardware | Document microphone selection and setup | 635 | 2 | 1 | Complete | Audio section in HARDWARE_SETUP.md |
| 637 | Deployment Preparation | hardware | Document speaker selection and setup | 636 | 2 | 1 | Complete | Audio section in HARDWARE_SETUP.md |
| 638 | Deployment Preparation | hardware | Create pre-flight checklist | 637 | 2 | 1 | Complete | PREFLIGHT_CHECKLIST.md |
| 639 | Deployment Preparation | testing | Write hardware integration test plan | 638 | 3 | 2 | Not Started | Real hardware |
| 640 | Deployment Preparation | testing | Create mount communication test | 639 | 2 | 1 | Complete | tests/hardware/test_mount.py |
| 641 | Deployment Preparation | testing | Create weather station test | 640 | 2 | 1 | Complete | tests/hardware/test_weather.py |
| 642 | Deployment Preparation | testing | Create cloud sensor test | 641 | 2 | 1 | Not Started | AAG verify |
| 643 | Deployment Preparation | testing | Create encoder test | 642 | 2 | 1 | Complete | tests/hardware/test_encoder.py |
| 644 | Deployment Preparation | testing | Create voice pipeline test | 643 | 2 | 1 | Complete | tests/hardware/test_voice.py |
| 645 | Deployment Preparation | testing | Create full system integration test | 644 | 3 | 2 | Not Started | All systems |
| 646 | Deployment Preparation | release | Create v0.1.0 release checklist | 645 | 2 | 1 | Complete | RELEASE_CHECKLIST.md |
| 647 | Deployment Preparation | release | Verify all tests passing | 646 | 2 | 1 | Not Started | Quality gate |
| 648 | Deployment Preparation | release | Update version numbers | 647 | 1 | 1 | Complete | 0.1.0 in __init__.py |
| 649 | Deployment Preparation | release | Generate changelog | 648 | 2 | 1 | Complete | CHANGELOG.md updated |
| 650 | Deployment Preparation | release | Create GitHub release | 649 | 2 | 1 | Not Started | Tag v0.1.0 |
| 651 | Deployment Preparation | release | Record demo video | 650 | 3 | 3 | Not Started | Showcase |
| 652 | Deployment Preparation | release | Write release announcement | 651 | 2 | 1 | Complete | RELEASE_v0.1.0.md |
| 653 | Deployment Preparation | release | Update project roadmap for v0.2 | 652 | 2 | 1 | Complete | ROADMAP.md |

---

## Summary Statistics

**Total Steps:** 653
**By Complexity:**
- Level 1 (Trivial): 89 steps (13.6%)
- Level 2 (Simple): 352 steps (53.9%)
- Level 3 (Moderate): 168 steps (25.7%)
- Level 4 (Complex): 39 steps (6.0%)
- Level 5 (Research): 5 steps (0.8%)

**By Effort:**
- Level 1 (<1 hour): 244 steps (37.4%)
- Level 2 (1-4 hours): 333 steps (51.0%)
- Level 3 (4-8 hours): 71 steps (10.9%)
- Level 4 (1-2 days): 5 steps (0.8%)
- Level 5 (Multi-day): 0 steps (0.0%)

**Estimated Total Effort:** ~800-1000 hours

---

## Critical Path

The following sequences are on the critical path and must complete in order:

1. **Infrastructure Foundation** (Steps 1-21): Config system must be complete before services can be integrated
2. **Orchestrator Core** (Steps 212-254): Central control loop required for all integration
3. **LLM Integration** (Steps 277-292): Intent detection required for voice pipeline
4. **Voice Pipeline** (Steps 293-312): End-to-end voice flow
5. **Tool Handlers** (Steps 330-456): Connect voice to services
6. **Safety System** (Steps 457-500): Required before production deployment
7. **Testing** (Steps 549-593): Validation before release
8. **Release** (Steps 646-653): Final packaging

---

## Ethos Compliance Checklist

- [x] **Local-first:** All LLM inference uses local Llama 3.2; no cloud APIs required
- [x] **Modular:** Clear service boundaries with well-defined interfaces
- [x] **Safety-first:** Comprehensive interlocks, vetoes, and failsafes
- [x] **Standards-compliant:** ASCOM Alpaca, Wyoming protocol, LX200, INDI
- [x] **Documented:** POS deliberations for novel decisions
- [x] **Non-commercial:** CC BY-NC-SA 4.0 license preserved

---

*Plan generated: January 2026*
*Target: NIGHTWATCH v0.1 Release*
