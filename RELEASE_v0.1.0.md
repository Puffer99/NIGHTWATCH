# NIGHTWATCH v0.1.0 Release

**Release Date:** January 2024

We're excited to announce the first release of NIGHTWATCH, a voice-controlled autonomous observatory system designed to run entirely on-premise with no cloud dependencies.

## What is NIGHTWATCH?

NIGHTWATCH is a comprehensive telescope observatory control system that combines:

- **Voice Control**: Natural language commands via local AI (Whisper STT + Llama 3.2)
- **Autonomous Operation**: Safety-aware automation with environmental monitoring
- **Local Processing**: All AI inference runs on-premise (optimized for NVIDIA DGX Spark)
- **Open Standards**: ASCOM Alpaca, INDI, LX200, and Wyoming protocol support

## Key Features in v0.1.0

### Voice Pipeline
- Wake word detection ("NIGHTWATCH")
- Local speech-to-text via Whisper
- Natural language understanding with Llama 3.2
- Text-to-speech responses via Piper
- Wyoming protocol integration for Home Assistant compatibility

### Observatory Control
- Mount control via LX200 and OnStepX extended protocols
- Weather monitoring (Ecowitt WS90)
- Cloud detection (AAG CloudWatcher)
- Absolute encoder support via EncoderBridge
- PHD2 guiding integration

### Safety System
- Environmental safety monitoring (wind, humidity, temperature)
- Automatic park on unsafe conditions
- Rain detection with immediate response
- UPS monitoring and graceful shutdown
- Safety veto system for all operations

### Services Architecture
- Modular microservices design
- ASCOM Alpaca compatibility
- Comprehensive logging with correlation IDs
- Health monitoring and status reporting
- Graceful degradation for optional services

## Getting Started

### Quick Install

```bash
# Clone the repository
git clone https://github.com/THOC-Labs/NIGHTWATCH.git
cd NIGHTWATCH

# Run installer
./deploy/scripts/install.sh
```

### Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [Hardware Setup](docs/HARDWARE_SETUP.md)
- [Simulator Guide](docs/SIMULATOR_GUIDE.md)
- [Voice Commands](docs/VOICE_COMMANDS.md)
- [Pre-flight Checklist](docs/PREFLIGHT_CHECKLIST.md)

## System Requirements

### Minimum
- Python 3.11+
- 16GB RAM
- NVIDIA GPU (for local AI inference)
- USB microphone and speakers

### Recommended
- NVIDIA DGX Spark or equivalent
- 32GB+ RAM
- Quality USB microphone array (ReSpeaker)
- Dedicated observatory network

## Hardware Support

| Component | Supported Models |
|-----------|------------------|
| Mount | OnStepX, LX200-compatible |
| Weather | Ecowitt WS90 |
| Cloud Sensor | AAG CloudWatcher |
| Camera | ZWO ASI (planned) |
| Guider | PHD2 |
| Encoders | AMT103-V via EncoderBridge |

## Known Limitations

- Camera integration (ZWO ASI) is foundation only
- Plate solving backend not yet integrated
- Filter wheel support pending
- Dome/roof control is basic GPIO only

## What's Next (v0.2 Preview)

- Complete camera integration with capture workflows
- Astrometry.net and ASTAP plate solving
- Automated imaging sequences
- Enhanced voice commands for imaging
- Web dashboard for remote monitoring

## Contributing

NIGHTWATCH is open source under CC BY-NC-SA 4.0. We welcome contributions!

- See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines
- Report issues on GitHub
- Join discussions for feature requests

## Acknowledgments

- The OnStepX project for mount control protocols
- OpenAI Whisper for speech recognition
- Meta Llama for language understanding
- Piper TTS for voice synthesis
- Wyoming protocol for voice integration standards

## License

Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)

---

*NIGHTWATCH - Autonomous observatory control, voice activated, locally powered.*
