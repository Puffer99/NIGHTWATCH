# Changelog

All notable changes to NIGHTWATCH will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure and documentation
- Core service implementations (mount control, weather, safety, guiding, encoder, camera, catalog, astrometry, alerts, power, enclosure, focus, ephemeris)
- Voice pipeline foundation (Wyoming protocol, STT/TTS services, telescope tools)
- INDI and ASCOM Alpaca client implementations
- LX200 and OnStepX extended protocol support
- Unit test suite foundation
- **Correlation ID support for request tracing** (Step 27)
  - `correlation_context()` context manager for scoped correlation IDs
  - `get_correlation_id()` and `set_correlation_id()` functions
  - `generate_correlation_id()` for unique ID generation
  - `CorrelationIdFilter` for automatic log record enrichment
  - Thread-safe implementation using ContextVars
- **Development tooling improvements**
  - `requirements-dev.txt` with pinned dev dependencies (Step 32)
  - pytest-cov for test coverage reporting (Step 33)
  - ruff for linting, mypy for type checking
  - pre-commit hooks support

### Changed
- Updated `.gitignore` with comprehensive Python patterns (Step 62)
  - Added mypy cache, pytest cache, coverage artifacts
  - Added ruff cache and hypothesis directories
- Version pinned `services/requirements.txt` for reproducible builds (Step 30)
- Version pinned `voice/requirements.txt` for reproducible builds (Step 31)

## [0.1.0] - TBD

### Added
- `nightwatch` package foundation with version 0.1.0-dev
- Custom exception hierarchy (`nightwatch.exceptions`)
  - `NightwatchError` base class
  - Connection errors: `DeviceConnectionError`, `ServiceConnectionError`
  - Device errors: `DeviceNotReadyError`, `DeviceBusyError`, `DeviceTimeoutError`
  - Safety errors: `SafetyVetoError`, `SafetyInterlockError`
  - Command errors: `InvalidCommandError`, `CommandTimeoutError`
  - Catalog errors: `ObjectNotFoundError`
- Shared constants module (`nightwatch.constants`)
  - Safety thresholds (POS Panel calibrated for Nevada 6000ft site)
  - Timing and interval constants
  - Network and protocol defaults
  - Physical limits and camera settings
  - Voice and AI configuration defaults
- Shared type definitions (`nightwatch.types`)
  - Coordinate types: `Coordinates`, `AltAz`, `SiteLocation`
  - State enumerations: `MountState`, `RoofState`, `CameraState`, `SafetyState`, etc.
  - TypedDicts: `WeatherData`, `MountStatus`, `CameraSettings`, `SolveResult`, `CatalogObject`
  - Protocol definitions: `Connectable`, `Positionable`, `Slewable`, `Parkable`
  - Callback type aliases for sync and async handlers
- PEP 561 `py.typed` marker for type hint support

### Architecture
- Local-first design: All AI/voice/control processing on-premise (DGX Spark)
- Modular microservices: ASCOM Alpaca, Wyoming protocol, OnStepX, INDI compliance
- Safety-first: Environmental interlocks via safety_monitor service
- Expert-driven: POS methodology for novel decisions

### Services (Partial Implementation)
- **Mount Control**: LX200 protocol, OnStepX extended commands
- **Weather**: Ecowitt WS90 integration
- **Safety Monitor**: Environmental condition checks, veto system
- **Guiding**: PHD2 client integration
- **Encoder**: EncoderBridge for absolute encoders
- **Camera**: ZWO ASI camera foundation
- **Catalog**: Celestial object database foundation
- **Astrometry**: Plate solver backend foundation
- **Alerts**: Notification system foundation
- **Power**: UPS monitoring via NUT foundation
- **Enclosure**: Roll-off roof controller foundation
- **Focus**: Focuser service foundation
- **Ephemeris**: Skyfield service integration

### Voice Pipeline (Partial Implementation)
- Wyoming protocol implementation
- Whisper STT service
- Piper TTS service
- Telescope tool handlers foundation

### Testing
- Unit tests for Alpaca client
- Unit tests for encoder bridge
- Unit tests for INDI adapters
- Unit tests for LX200 client
- Unit tests for OnStepX extended
- Unit tests for Piper service
- Unit tests for telescope tools
- Unit tests for Whisper service
- Unit tests for Wyoming protocol
- Integration test foundation for device layer

### Documentation
- POS Panel deliberation records
- Architecture documentation
- Service interface specifications
- Hardware integration guides

### License
- CC BY-NC-SA 4.0 (Non-commercial, Share-alike)

---

## Version History

| Version | Date | Milestone |
|---------|------|-----------|
| 0.1.0 | TBD | Initial v0.1 release - Core functionality |

[Unreleased]: https://github.com/THOC-Labs/NIGHTWATCH/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/THOC-Labs/NIGHTWATCH/releases/tag/v0.1.0
