# NIGHTWATCH

[![Status: v0.1 Development](https://img.shields.io/badge/Status-v0.1%20Development-blue)](https://github.com/THOClabs/NIGHTWATCH)
[![CI](https://github.com/THOClabs/NIGHTWATCH/actions/workflows/ci.yml/badge.svg)](https://github.com/THOClabs/NIGHTWATCH/actions/workflows/ci.yml)
[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![OnStepX](https://img.shields.io/badge/Controller-OnStepX-green.svg)](https://onstep.groups.io/)

**Autonomous Maksutov-Newtonian Observatory System**

Voice-controlled telescope observatory designed for central Nevada dark sky installation. Combines optics excellence with modern automation and local AI inference — no cloud dependency, full local control.

> **Project Status:** v0.1 development in progress — core services implemented. See the [Full Build Specification](NIGHTWATCH_Build_Package.md) for hardware details.

---

## v0.1 Quickstart

Get started with NIGHTWATCH in under 5 minutes:

```bash
# Clone and setup
git clone https://github.com/THOClabs/NIGHTWATCH.git
cd NIGHTWATCH
python -m venv .venv && source .venv/bin/activate
pip install -r services/requirements.txt

# Run tests to verify installation
pytest tests/unit/ -v

# Start with simulators (no hardware required)
python -m nightwatch.cli --simulate
```

**Voice Commands** (examples):
- "Slew to Andromeda"
- "What's the current position?"
- "Park the telescope"
- "What's the weather like?"

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for detailed setup instructions.

---

## Key Components

| Component | Description |
|-----------|-------------|
| **Optical Tube** | Intes Micro MN76 (178 mm f/6 Maksutov-Newtonian, sometimes designated MN78) — hand-figured Russian optics renowned for planetary contrast |
| **Mount** | DIY harmonic drive German Equatorial Mount — smooth, backlash-free tracking |
| **Controller** | OnStepX on Teensy 4.1 — mature, community-supported open-source control |
| **Weather** | Ecowitt WS90 weather station + AAG CloudWatcher — comprehensive environmental monitoring |
| **Edge AI** | NVIDIA DGX Spark — local voice pipeline and automation, zero cloud latency |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         NIGHTWATCH System                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐     ┌──────────────┐     ┌───────────────────┐    │
│  │   Voice     │     │   Safety     │     │    Observatory    │    │
│  │  Pipeline   │────▶│   Monitor    │────▶│     Services      │    │
│  │ (DGX Spark) │     │              │     │                   │    │
│  └─────────────┘     └──────────────┘     └───────────────────┘    │
│        │                    │                       │              │
│        │              ┌─────┴─────┐                 │              │
│        ▼              ▼           ▼                 ▼              │
│  ┌───────────┐  ┌──────────┐ ┌─────────┐    ┌────────────┐        │
│  │  Whisper  │  │ Weather  │ │  Cloud  │    │   Mount    │        │
│  │   STT     │  │ Station  │ │ Watcher │    │  Control   │        │
│  └───────────┘  │ (WS90)   │ │  (AAG)  │    │ (OnStepX)  │        │
│        │        └──────────┘ └─────────┘    └────────────┘        │
│        ▼                                           │              │
│  ┌───────────┐                              ┌──────┴──────┐       │
│  │   Piper   │                              │   Intes     │       │
│  │   TTS     │                              │  MN76 OTA   │       │
│  └───────────┘                              │  + Camera   │       │
│                                             └─────────────┘       │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

## Design Methodology: Panel of Specialists

NIGHTWATCH uses an innovative **Panel of Specialists (POS)** framework — a simulated 30-day design retreat where 12 domain experts collaboratively refine every aspect of the system.

| Specialist | Domain | Contribution |
|------------|--------|--------------|
| Howard Dutton | OnStepX Firmware | Mount control, encoder integration |
| Damian Peach | Astrophotography | Imaging workflow optimization |
| Yuri Petrunin | Russian Optics | MN76 thermal management |
| Michael Clive | NVIDIA AI | DGX Spark voice pipeline |
| C.W. Musser | Harmonic Drives | Precision mount mechanics |
| Alec Radford | Speech Recognition | Whisper STT integration |
| Michael Hansen | Voice Synthesis | Piper TTS deployment |
| Antonio García | Weather Sensing | Safety interlocks |
| Richard Hedrick | Precision Mounts | Frame design, FEA |
| Craig Stark | Autoguiding | PHD2 integration |
| Bob Denny | Integration | ASCOM/ACP standards |
| SRO Team | Remote Ops | Power/network resilience |

This multi-perspective deliberation process produces robust designs with documented reasoning. See [pos/README.md](pos/README.md) for the full methodology.

## Repository Structure

```
NIGHTWATCH/
├── docs/research/          # Research documentation and sourcing
├── firmware/onstepx_config/ # OnStepX controller configuration
├── pos/agents/             # POS retreat simulation personalities
├── services/               # 13 observatory microservices
│   ├── mount_control/      # Telescope mount interface
│   ├── camera/             # Imaging and capture
│   ├── weather/            # Environmental monitoring
│   ├── safety_monitor/     # Automated safety systems
│   ├── ephemeris/          # Celestial calculations
│   └── ...                 # guiding, focus, astrometry, etc.
└── voice/                  # Voice control pipeline
    ├── stt/                # Speech-to-text (Whisper)
    ├── tts/                # Text-to-speech (Piper)
    └── tools/              # Telescope voice commands
```

## Requirements

### Hardware
- NVIDIA DGX Spark (or compatible CUDA-enabled device)
- Teensy 4.1 microcontroller
- Ecowitt WS90 weather station
- AAG CloudWatcher cloud sensor

### Software
- Python 3.11+ (3.12 also supported)
- OnStepX firmware
- CUDA toolkit (for DGX Spark inference)

## Installation

### Quick Start (Development)

```bash
# Clone the repository
git clone https://github.com/THOClabs/NIGHTWATCH.git
cd NIGHTWATCH

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies in order
pip install -r services/requirements.txt    # Observatory services
pip install -r voice/requirements.txt       # Voice pipeline
pip install -r requirements-dev.txt         # Development tools

# Install pre-commit hooks (recommended)
pre-commit install
```

### Using pyproject.toml (Alternative)

```bash
# Install core package only
pip install -e .

# Install with all optional dependencies
pip install -e ".[all]"

# Install specific features
pip install -e ".[services]"    # Observatory services
pip install -e ".[voice]"       # Voice pipeline
pip install -e ".[dev]"         # Development tools
```

### Verify Installation

```bash
# Run tests
pytest

# Check linting
ruff check .

# Check types
mypy nightwatch/
```

## Documentation

| Document | Description |
|----------|-------------|
| [**Quickstart Guide**](docs/QUICKSTART.md) | Get up and running quickly |
| [**Installation**](docs/INSTALLATION.md) | Full installation instructions |
| [**Configuration**](docs/CONFIGURATION.md) | System configuration reference |
| [**Voice Commands**](docs/VOICE_COMMANDS.md) | Complete voice command reference |
| [**Hardware Setup**](docs/HARDWARE_SETUP.md) | Hardware connection guide |
| [**Build Specification**](NIGHTWATCH_Build_Package.md) | Complete build spec — optics, mount, electronics |
| [**Panel of Specialists**](pos/README.md) | Design methodology and expert panel |

## Roadmap

- [ ] Complete optical tube assembly sourcing
- [ ] Finalize harmonic drive mount design
- [ ] Build OnStepX controller assembly
- [ ] Deploy weather monitoring station
- [ ] Integrate voice pipeline with observatory services
- [ ] First light at Nevada dark sky site

## License

This project is licensed under **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International** (CC BY-NC-SA 4.0).

You are free to share and adapt this material for non-commercial purposes, with attribution and under the same license terms.

See [LICENSE](LICENSE) for full details.

---

## Contributing

Contributions, feedback, and ideas are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Whether you're experienced with OnStepX, astrophotography automation, or edge AI — we'd love to hear from you.

---

<sub>*NIGHTWATCH: Where Russian optics meet Nevada skies.*</sub>
