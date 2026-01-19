# NIGHTWATCH Installation Guide

This guide covers installing NIGHTWATCH on Linux and macOS systems.

## Quick Install

For most users, the automated installer is recommended:

```bash
curl -fsSL https://raw.githubusercontent.com/THOClabs/NIGHTWATCH/main/deploy/scripts/install.sh | sudo bash
```

Or download and run manually:

```bash
wget https://raw.githubusercontent.com/THOClabs/NIGHTWATCH/main/deploy/scripts/install.sh
chmod +x install.sh
sudo ./install.sh
```

## System Requirements

### Minimum Requirements
- **OS**: Ubuntu 20.04+, Debian 11+, Fedora 36+, or macOS 12+
- **Python**: 3.10 or higher (3.11 recommended)
- **RAM**: 4 GB (8 GB recommended for voice pipeline)
- **Storage**: 2 GB for base install, 10 GB+ for voice models

### For Voice Pipeline (Optional)
- **GPU**: NVIDIA GPU with CUDA support (recommended)
- **VRAM**: 4 GB minimum for Whisper base model
- **Audio**: USB microphone and speakers

### For Full Observatory Control
- **Network**: Ethernet or stable WiFi for mount/weather communication
- **Serial**: USB-to-serial adapter for mount connection (if not using network)

## Installation Options

### Option 1: System-Wide Installation (Recommended)

```bash
sudo ./install.sh
```

This installs to `/opt/nightwatch` with systemd services.

### Option 2: User Installation

```bash
./install.sh --user
```

Installs to `~/.local/nightwatch` without requiring root.

### Option 3: Custom Location

```bash
sudo ./install.sh --prefix /custom/path
```

### Option 4: Without Voice Pipeline

```bash
sudo ./install.sh --no-voice
```

Skips Whisper/Piper dependencies (saves ~2 GB).

### Option 5: Development Installation

```bash
sudo ./install.sh --dev
```

Includes pytest, ruff, mypy, and pre-commit hooks.

## Manual Installation

If the automated installer doesn't work for your system:

### 1. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y git python3.11 python3.11-venv python3-pip \
    portaudio19-dev libsndfile1 ffmpeg
```

**Fedora:**
```bash
sudo dnf install -y git python3.11 python3-pip python3-virtualenv \
    portaudio-devel libsndfile ffmpeg
```

**macOS (Homebrew):**
```bash
brew install python@3.11 portaudio libsndfile ffmpeg
```

### 2. Create Installation Directory

```bash
sudo mkdir -p /opt/nightwatch
sudo chown $USER:$USER /opt/nightwatch
```

### 3. Clone Repository

```bash
git clone https://github.com/THOClabs/NIGHTWATCH.git /opt/nightwatch
cd /opt/nightwatch
```

### 4. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip wheel setuptools
```

### 5. Install Python Dependencies

```bash
# Core dependencies
pip install -r services/requirements.txt

# Voice pipeline (optional)
pip install -r voice/requirements.txt
```

### 6. Create Configuration

```bash
sudo mkdir -p /etc/nightwatch
sudo cp deploy/scripts/config.yaml.example /etc/nightwatch/config.yaml
sudo nano /etc/nightwatch/config.yaml
```

### 7. Install Systemd Services (Linux)

```bash
sudo cp deploy/systemd/nightwatch.service /etc/systemd/system/
sudo cp deploy/systemd/nightwatch-wyoming.service /etc/systemd/system/
sudo systemctl daemon-reload
```

## Post-Installation Setup

### 1. Edit Configuration

Edit `/etc/nightwatch/config.yaml` with your site and hardware settings:

```yaml
# Required: Your observatory location
site:
  name: "My Observatory"
  latitude: 39.5501      # Your latitude
  longitude: -119.8143   # Your longitude (negative for West)
  elevation: 1373        # Meters above sea level
  timezone: "America/Los_Angeles"

# Configure your mount
mount:
  type: "lx200"          # or "onstepx", "indi", "alpaca"
  host: "192.168.1.100"  # Mount IP address
  port: 9999             # LX200 port
```

### 2. Create Service User (System Install)

```bash
sudo useradd -r -s /bin/false -d /opt/nightwatch nightwatch
sudo usermod -aG dialout,gpio,audio nightwatch
sudo chown -R nightwatch:nightwatch /opt/nightwatch
```

### 3. Test Installation

```bash
# Activate virtual environment
source /opt/nightwatch/venv/bin/activate

# Run quick test
python -c "from services.config import config; print('Config OK')"

# Test with simulators (no hardware needed)
python -m nightwatch.main --config /etc/nightwatch/config.yaml --dry-run
```

### 4. Start Services

```bash
# Enable services to start on boot
sudo systemctl enable nightwatch.service
sudo systemctl enable nightwatch-wyoming.service

# Start services
sudo systemctl start nightwatch-wyoming.service
sudo systemctl start nightwatch.service

# Check status
sudo systemctl status nightwatch.service
```

## Upgrading

Use the upgrade script to update to the latest version:

```bash
sudo /opt/nightwatch/deploy/scripts/upgrade.sh
```

Or with backup:

```bash
sudo /opt/nightwatch/deploy/scripts/upgrade.sh --backup
```

## Uninstallation

### Stop and Disable Services

```bash
sudo systemctl stop nightwatch.service nightwatch-wyoming.service
sudo systemctl disable nightwatch.service nightwatch-wyoming.service
sudo rm /etc/systemd/system/nightwatch*.service
sudo systemctl daemon-reload
```

### Remove Installation

```bash
sudo rm -rf /opt/nightwatch
sudo rm -rf /etc/nightwatch
sudo rm -rf /var/log/nightwatch
sudo userdel nightwatch
```

## Troubleshooting

### Python Version Issues

```bash
# Check Python version
python3 --version

# Install Python 3.11 on Ubuntu
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv
```

### Permission Errors

```bash
# Fix ownership
sudo chown -R nightwatch:nightwatch /opt/nightwatch

# Add user to hardware groups
sudo usermod -aG dialout,audio $USER
# Log out and back in for group changes to take effect
```

### Voice Pipeline Issues

```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# Test audio
python -c "import sounddevice; print(sounddevice.query_devices())"
```

### Service Won't Start

```bash
# Check logs
journalctl -u nightwatch -e

# Test configuration
/opt/nightwatch/venv/bin/python -m nightwatch.main --config /etc/nightwatch/config.yaml --dry-run
```

## Next Steps

1. [Configure your hardware](HARDWARE_SETUP.md)
2. [Learn voice commands](VOICE_COMMANDS.md)
3. [Review safety settings](CONFIGURATION.md#safety)
