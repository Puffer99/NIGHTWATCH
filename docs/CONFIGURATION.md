# NIGHTWATCH Configuration Guide

This guide covers all configuration options for the NIGHTWATCH observatory system.

## Configuration File Location

The main configuration file is located at:
- **System install**: `/etc/nightwatch/config.yaml`
- **User install**: `~/.config/nightwatch/config.yaml`
- **Development**: `./config/config.yaml`

## Site Configuration

Configure your observatory location for accurate ephemeris calculations:

```yaml
site:
  name: "My Observatory"
  latitude: 34.8697        # Decimal degrees (positive = North)
  longitude: -111.7610     # Decimal degrees (negative = West)
  elevation: 1373          # Meters above sea level
  timezone: "America/Los_Angeles"

  # Horizon limits (degrees above horizon)
  min_altitude: 15         # Objects below this won't be targeted

  # Twilight preferences
  twilight_sun_altitude: -12  # Nautical twilight threshold
```

## Mount Configuration

### LX200 Protocol (OnStepX, Meade, etc.)

```yaml
mount:
  type: "lx200"
  host: "192.168.1.100"    # Mount IP address or hostname
  port: 9999               # LX200 TCP port

  # Connection settings
  timeout_sec: 10
  retry_count: 3

  # Slew limits
  max_slew_rate: 3.0       # Degrees per second

  # Park position
  park_altitude: 45        # Degrees
  park_azimuth: 0          # Degrees (North)
```

### INDI Protocol

```yaml
mount:
  type: "indi"
  host: "localhost"        # INDI server host
  port: 7624               # INDI server port
  device: "OnStepX"        # Device name in INDI
```

### Alpaca/ASCOM Protocol

```yaml
mount:
  type: "alpaca"
  host: "192.168.1.101"
  port: 11111
  device_number: 0
```

## Weather Station Configuration

### Ecowitt Weather Station

```yaml
weather:
  type: "ecowitt"
  host: "192.168.1.50"     # Weather station IP
  poll_interval_sec: 60

  # Safety thresholds
  max_humidity_pct: 85
  max_wind_kph: 40
  max_rain_rate_mmh: 0.0   # Any rain = unsafe
```

### AAG CloudWatcher

```yaml
weather:
  type: "cloudwatcher"
  serial_port: "/dev/ttyUSB0"
  baud_rate: 9600

  # Cloud detection thresholds
  cloud_temp_diff: -15     # Sky-ambient temperature difference
  clear_temp_diff: -25     # Threshold for "clear" sky
```

## Camera Configuration

### ZWO ASI Cameras

```yaml
camera:
  type: "zwo"
  camera_id: 0             # Camera index (0 = first)

  # Default capture settings
  gain: 100
  offset: 10
  binning: 1

  # Cooling
  cooling_enabled: true
  target_temp_c: -10

  # File output
  output_dir: "/data/images"
  file_format: "fits"      # "fits" or "png"
```

## Guider Configuration (PHD2)

```yaml
guider:
  type: "phd2"
  host: "localhost"
  port: 4400               # PHD2 JSON-RPC port

  # Guiding parameters
  settle_pixels: 1.5       # Max deviation during settle
  settle_time_sec: 10      # Minimum settle time
  settle_timeout_sec: 60   # Max settle wait

  # Dither settings
  dither_pixels: 5.0
  dither_ra_only: false
```

## Focuser Configuration

```yaml
focuser:
  type: "moonlite"         # Or "indi", "alpaca"
  serial_port: "/dev/ttyUSB1"

  # Movement limits
  min_position: 0
  max_position: 50000

  # Auto-focus settings
  step_size: 100
  backlash_compensation: 50
```

## Enclosure Configuration

```yaml
enclosure:
  type: "gpio"             # Roll-off roof via GPIO

  # GPIO pins (BCM numbering)
  motor_open_pin: 17
  motor_close_pin: 18
  open_limit_pin: 22
  closed_limit_pin: 23
  rain_sensor_pin: 24

  # Safety settings
  motor_timeout_sec: 60    # Max motor run time
  rain_holdoff_min: 30     # Wait after rain before opening
```

## Power Management (UPS)

```yaml
power:
  type: "nut"              # Network UPS Tools
  ups_name: "ups"
  nut_host: "localhost"
  nut_port: 3493

  # Battery thresholds
  park_threshold_pct: 50   # Start park sequence
  emergency_threshold_pct: 20  # Emergency shutdown
  resume_threshold_pct: 80 # Battery level to resume
```

## Alert Configuration

```yaml
alerts:
  # Email notifications
  email_enabled: true
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  smtp_user: "observatory@example.com"
  smtp_password: "${SMTP_PASSWORD}"  # Use environment variable
  email_recipients:
    - "operator@example.com"

  # Push notifications (ntfy.sh)
  ntfy_enabled: true
  ntfy_topic: "nightwatch-alerts"

  # SMS (Twilio)
  sms_enabled: false
  twilio_sid: "${TWILIO_SID}"
  twilio_token: "${TWILIO_TOKEN}"
  twilio_from: "+1234567890"
  sms_recipients:
    - "+1987654321"

  # Rate limiting
  min_interval_sec: 60
  max_alerts_per_hour: 20

  # Quiet hours
  quiet_hours_enabled: true
  quiet_hours_start: 8     # 8 AM local
  quiet_hours_end: 18      # 6 PM local
```

## Voice Pipeline Configuration

```yaml
voice:
  enabled: true

  # Wake word detection
  wake_word: "nightwatch"
  wake_word_sensitivity: 0.5

  # Speech recognition (Whisper)
  whisper_model: "base"    # "tiny", "base", "small", "medium"
  whisper_device: "cuda"   # "cuda" or "cpu"

  # Text-to-speech (Piper)
  piper_voice: "en_US-lessac-medium"

  # Audio settings
  sample_rate: 16000
  input_device: "default"
  output_device: "default"
```

## Logging Configuration

```yaml
logging:
  level: "INFO"            # DEBUG, INFO, WARNING, ERROR
  file: "/var/log/nightwatch/nightwatch.log"
  max_size_mb: 10
  backup_count: 5

  # Per-module levels
  modules:
    NIGHTWATCH.Mount: "DEBUG"
    NIGHTWATCH.Weather: "INFO"
    NIGHTWATCH.Voice: "WARNING"
```

## Session Configuration

```yaml
session:
  # Auto-start/stop
  auto_start_enabled: false
  auto_stop_enabled: true  # Stop at dawn

  # Target selection
  min_altitude_deg: 30
  prefer_meridian_targets: true

  # Imaging defaults
  default_exposure_sec: 60
  dither_every_n_frames: 5
```

## Environment Variables

Sensitive values can be set via environment variables:

```bash
# In /etc/nightwatch/nightwatch.env
NIGHTWATCH_SMTP_PASSWORD=your_password
NIGHTWATCH_TWILIO_SID=your_sid
NIGHTWATCH_TWILIO_TOKEN=your_token
```

Reference in config.yaml:
```yaml
smtp_password: "${NIGHTWATCH_SMTP_PASSWORD}"
```

## Validation

Validate your configuration:

```bash
# Check syntax
python -m nightwatch.config --validate /etc/nightwatch/config.yaml

# Test connections
python -m nightwatch.config --test-connections
```

## See Also

- [Installation Guide](INSTALLATION.md)
- [Hardware Setup](HARDWARE_SETUP.md)
- [Voice Commands](VOICE_COMMANDS.md)
