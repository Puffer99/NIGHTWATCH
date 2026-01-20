# NIGHTWATCH Quickstart Guide

Get your NIGHTWATCH system running in minutes.

## Prerequisites

- Python 3.11 or later
- Git
- 4GB RAM minimum (8GB recommended for voice pipeline)
- For voice features: microphone and speakers

## Quick Installation

### 1. Clone the Repository

```bash
git clone https://github.com/THOClabs/NIGHTWATCH.git
cd NIGHTWATCH
```

### 2. Create Virtual Environment

```bash
# Create and activate virtual environment
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Core observatory services
pip install -r services/requirements.txt

# Voice pipeline (optional but recommended)
pip install -r voice/requirements.txt
```

### 4. Verify Installation

```bash
# Run the test suite
pytest tests/unit/ -v

# Check that key modules import
python -c "from nightwatch.services import mount, weather, safety; print('OK')"
```

## Running NIGHTWATCH

### Simulation Mode (No Hardware)

Start NIGHTWATCH with simulated devices for testing:

```bash
python -m nightwatch.cli --simulate
```

This mode simulates:
- Mount (responds to slew/park commands)
- Weather station (generates realistic weather data)
- Safety monitor (enforces safety rules)

### With Real Hardware

1. **Configure your devices** in `config/nightwatch.yaml`:

```yaml
mount:
  type: onstepx
  host: 192.168.1.100  # Your OnStepX IP
  port: 9999

weather:
  type: ecowitt
  host: 192.168.1.101  # Your Ecowitt gateway IP
```

2. **Start the system**:

```bash
python -m nightwatch.cli
```

## Voice Commands

Once running, try these voice commands:

| Command | Action |
|---------|--------|
| "Slew to Andromeda" | Point telescope at Andromeda Galaxy |
| "Go to M42" | Point to Orion Nebula |
| "Point at Vega" | Point to the star Vega |
| "Park the telescope" | Park the mount |
| "Unpark" | Unpark and start tracking |
| "What's the weather?" | Get current conditions |
| "What am I looking at?" | Identify current target |
| "What's up tonight?" | Get observing suggestions |

See [VOICE_COMMANDS.md](VOICE_COMMANDS.md) for the complete command reference.

## Configuration Files

Key configuration files:

| File | Purpose |
|------|---------|
| `config/nightwatch.yaml` | Main system configuration |
| `config/safety.yaml` | Safety thresholds (wind, humidity, etc.) |
| `config/catalog.yaml` | Object catalog settings |

See [CONFIGURATION.md](CONFIGURATION.md) for detailed configuration options.

## Docker Deployment

For production deployment, use Docker:

```bash
# Start all services
docker compose -f docker/docker-compose.yml up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

## Development Setup

For development work:

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests with coverage
pytest --cov=nightwatch --cov=services

# Run linting
ruff check .

# Run type checking
mypy nightwatch/
```

## Troubleshooting

### Mount Connection Issues

```bash
# Test mount connectivity
python -c "
from services.mount_control.onstepx_client import OnStepXClient
client = OnStepXClient('192.168.1.100', 9999)
print('Connected:', client.connect())
"
```

### Voice Pipeline Issues

```bash
# Test microphone
python -c "import sounddevice; print(sounddevice.query_devices())"

# Test STT (speech-to-text)
python -m voice.stt.whisper_stt --test
```

### Weather Station Issues

```bash
# Test Ecowitt connection
curl http://192.168.1.101/get_livedata_info
```

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more solutions.

## Next Steps

1. **Configure Hardware**: See [HARDWARE_SETUP.md](HARDWARE_SETUP.md)
2. **Customize Settings**: See [CONFIGURATION.md](CONFIGURATION.md)
3. **Learn Voice Commands**: See [VOICE_COMMANDS.md](VOICE_COMMANDS.md)
4. **Set Up Safety Rules**: See [INSTALLATION.md](INSTALLATION.md#safety-configuration)

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/THOClabs/NIGHTWATCH/issues)
- **Discussions**: [GitHub Discussions](https://github.com/THOClabs/NIGHTWATCH/discussions)
- **Documentation**: [Full Documentation](./README.md)
