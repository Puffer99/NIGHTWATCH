# NIGHTWATCH Systemd Services

This directory contains systemd unit files for running NIGHTWATCH as a Linux service.

## Services

| Service | Description | Port(s) |
|---------|-------------|---------|
| `nightwatch.service` | Main observatory controller | - |
| `nightwatch-wyoming.service` | Voice protocol (STT/TTS) | 10200, 10300 |

## Prerequisites

### Create Service User

```bash
sudo useradd -r -s /bin/false -d /opt/nightwatch nightwatch
sudo usermod -aG dialout,gpio,audio nightwatch
```

### Create Directories

```bash
sudo mkdir -p /opt/nightwatch
sudo mkdir -p /etc/nightwatch
sudo mkdir -p /var/log/nightwatch
sudo mkdir -p /var/lib/nightwatch
sudo mkdir -p /data/captures

sudo chown -R nightwatch:nightwatch /opt/nightwatch
sudo chown -R nightwatch:nightwatch /var/log/nightwatch
sudo chown -R nightwatch:nightwatch /var/lib/nightwatch
sudo chown -R nightwatch:nightwatch /data
```

### Install NIGHTWATCH

```bash
# Clone repository
sudo -u nightwatch git clone https://github.com/THOClabs/NIGHTWATCH /opt/nightwatch

# Create virtual environment
sudo -u nightwatch python3 -m venv /opt/nightwatch/venv

# Install dependencies
sudo -u nightwatch /opt/nightwatch/venv/bin/pip install -r /opt/nightwatch/services/requirements.txt
sudo -u nightwatch /opt/nightwatch/venv/bin/pip install -r /opt/nightwatch/voice/requirements.txt
```

### Create Configuration

```bash
sudo cp /opt/nightwatch/config/nightwatch.yaml.example /etc/nightwatch/config.yaml
sudo chmod 640 /etc/nightwatch/config.yaml
sudo chown nightwatch:nightwatch /etc/nightwatch/config.yaml

# Edit configuration
sudo nano /etc/nightwatch/config.yaml
```

## Installation

### Install Service Files

```bash
sudo cp /opt/nightwatch/deploy/systemd/nightwatch.service /etc/systemd/system/
sudo cp /opt/nightwatch/deploy/systemd/nightwatch-wyoming.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### Enable Services

```bash
# Enable services to start on boot
sudo systemctl enable nightwatch.service
sudo systemctl enable nightwatch-wyoming.service
```

### Start Services

```bash
# Start Wyoming (voice) first
sudo systemctl start nightwatch-wyoming.service

# Then start main controller
sudo systemctl start nightwatch.service
```

## Management

### Check Status

```bash
sudo systemctl status nightwatch.service
sudo systemctl status nightwatch-wyoming.service
```

### View Logs

```bash
# Real-time logs
journalctl -u nightwatch -f

# Wyoming service logs
journalctl -u nightwatch-wyoming -f

# Last 100 lines
journalctl -u nightwatch -n 100

# Logs since boot
journalctl -u nightwatch -b
```

### Restart Services

```bash
sudo systemctl restart nightwatch.service
sudo systemctl restart nightwatch-wyoming.service
```

### Stop Services

```bash
# Graceful stop (parks telescope, closes roof)
sudo systemctl stop nightwatch.service

# Stop Wyoming
sudo systemctl stop nightwatch-wyoming.service
```

## Service Features

### Automatic Restart

Both services are configured to restart on failure:

- **nightwatch.service**:
  - Restarts after 10 seconds on failure
  - Maximum 5 restart attempts in 5 minutes
  - Won't restart if exit code is 0 (clean shutdown)

- **nightwatch-wyoming.service**:
  - Restarts after 5 seconds on failure
  - Maximum 10 restart attempts in 5 minutes

### Watchdog

The main `nightwatch.service` uses systemd's watchdog feature:

- Service must send heartbeat every 30 seconds
- If heartbeat stops, systemd will restart the service
- Ensures the service hasn't hung or deadlocked

### Graceful Shutdown

When stopping `nightwatch.service`:

1. SIGTERM sent to process
2. Service runs shutdown sequence:
   - Parks telescope to safe position
   - Closes enclosure (if open)
   - Saves session log
3. Up to 120 seconds allowed for graceful shutdown
4. SIGKILL sent if still running after timeout

### Security Hardening

Both services include security restrictions:

- `NoNewPrivileges`: Cannot gain new privileges
- `ProtectSystem=strict`: Read-only access to most of filesystem
- `ProtectHome`: Cannot access /home directories
- `PrivateTmp`: Private /tmp namespace
- Limited write paths for logs and data

## Troubleshooting

### Service Won't Start

```bash
# Check for configuration errors
/opt/nightwatch/venv/bin/python -m nightwatch.main --config /etc/nightwatch/config.yaml --dry-run

# Check systemd journal for errors
journalctl -u nightwatch -e

# Verify file permissions
ls -la /opt/nightwatch
ls -la /etc/nightwatch/config.yaml
```

### Restart Loop

If the service keeps restarting:

```bash
# Check restart status
systemctl show nightwatch.service | grep -E "(Restart|NRestart)"

# Reset restart counter
sudo systemctl reset-failed nightwatch.service

# Check logs for crash reason
journalctl -u nightwatch --since "1 hour ago"
```

### Hardware Access Issues

```bash
# Verify user is in required groups
groups nightwatch

# Check serial port permissions
ls -la /dev/ttyUSB*

# Test serial port access
sudo -u nightwatch test -r /dev/ttyUSB0 && echo "OK" || echo "No access"
```

### Voice Service Issues

```bash
# Check CUDA availability
sudo -u nightwatch /opt/nightwatch/venv/bin/python -c "import torch; print(torch.cuda.is_available())"

# Test Wyoming ports
nc -zv localhost 10200  # TTS
nc -zv localhost 10300  # STT
```

## Environment Variables

### nightwatch.service

| Variable | Default | Description |
|----------|---------|-------------|
| `NIGHTWATCH_HOME` | `/opt/nightwatch` | Installation directory |
| `NIGHTWATCH_CONFIG` | `/etc/nightwatch/config.yaml` | Configuration file |
| `NIGHTWATCH_LOG_LEVEL` | `INFO` | Log verbosity |

### nightwatch-wyoming.service

| Variable | Default | Description |
|----------|---------|-------------|
| `WYOMING_STT_PORT` | `10300` | Speech-to-text port |
| `WYOMING_TTS_PORT` | `10200` | Text-to-speech port |
| `CUDA_VISIBLE_DEVICES` | `0` | GPU device for inference |

## Integration with Home Assistant

The Wyoming service can integrate with Home Assistant:

1. Install Wyoming protocol integration in Home Assistant
2. Add NIGHTWATCH STT/TTS services:
   - STT: `<nightwatch-host>:10300`
   - TTS: `<nightwatch-host>:10200`
3. Configure voice assistant to use NIGHTWATCH services
