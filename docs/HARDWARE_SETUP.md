# NIGHTWATCH Hardware Setup Guide

This guide covers hardware configuration for NIGHTWATCH observatory control.

## Table of Contents
- [Mount Controller (OnStepX)](#mount-controller-onstepx)
- [Weather Station (Ecowitt WS90)](#weather-station-ecowitt-ws90)
- [Cloud Sensor (AAG CloudWatcher)](#cloud-sensor-aag-cloudwatcher)
- [Audio Hardware](#audio-hardware)
- [Network Architecture](#network-architecture)

---

## Mount Controller (OnStepX)

### Overview

NIGHTWATCH supports OnStepX-based telescope controllers using the Teensy 4.1 microcontroller. OnStepX provides:
- LX200 protocol compatibility
- Extended command set for advanced features
- High-resolution encoder support
- Periodic Error Correction (PEC)

### Hardware Requirements

| Component | Specification |
|-----------|---------------|
| Controller | Teensy 4.1 |
| Motor Drivers | TMC2130 or TMC5160 |
| Stepper Motors | NEMA 17 or NEMA 23 |
| Encoders | AMT103-V (optional) |
| Power Supply | 12-24V DC, 5A minimum |

### Wiring Diagram

```
                    +------------------+
                    |    Teensy 4.1    |
                    +------------------+
                    |                  |
  RA Motor    <-----|  Step: Pin 2    |
  (TMC2130)   <-----|  Dir:  Pin 3    |
                    |  EN:   Pin 4    |
                    |                  |
  DEC Motor   <-----|  Step: Pin 5    |
  (TMC2130)   <-----|  Dir:  Pin 6    |
                    |  EN:   Pin 7    |
                    |                  |
  RA Encoder  ----->|  A:    Pin 22   |
  (AMT103-V)  ----->|  B:    Pin 23   |
                    |  Z:    Pin 21   |
                    |                  |
  DEC Encoder ----->|  A:    Pin 20   |
  (AMT103-V)  ----->|  B:    Pin 19   |
                    |  Z:    Pin 18   |
                    |                  |
  USB/Serial  <---->|  USB / Serial1  |
                    +------------------+
```

### Pin Assignments (Teensy 4.1)

| Function | Pin | Notes |
|----------|-----|-------|
| RA Step | 2 | PWM capable |
| RA Dir | 3 | - |
| RA Enable | 4 | Active LOW |
| DEC Step | 5 | PWM capable |
| DEC Dir | 6 | - |
| DEC Enable | 7 | Active LOW |
| RA Encoder A | 22 | Interrupt capable |
| RA Encoder B | 23 | Interrupt capable |
| RA Encoder Z | 21 | Index pulse |
| DEC Encoder A | 20 | Interrupt capable |
| DEC Encoder B | 19 | Interrupt capable |
| DEC Encoder Z | 18 | Index pulse |
| Status LED | 13 | Onboard LED |

### Encoder Wiring (AMT103-V)

The AMT103-V encoder provides 2048 PPR (pulses per revolution):

```
AMT103-V          Teensy 4.1
---------         ----------
VCC (Red)    -->  3.3V
GND (Black)  -->  GND
A (White)    -->  Encoder A pin
B (Green)    -->  Encoder B pin
Z (Yellow)   -->  Encoder Z pin (optional)
```

**Important:** Use shielded cable for encoder connections to reduce noise.

### OnStepX Configuration

Edit `Config.h` before flashing:

```cpp
// Mount type
#define MOUNT_TYPE GEM

// Axis 1 (RA) settings
#define AXIS1_STEPS_PER_DEGREE 12800.0
#define AXIS1_DRIVER TMC2130
#define AXIS1_ENCODER AMT_SERIAL

// Axis 2 (DEC) settings
#define AXIS2_STEPS_PER_DEGREE 12800.0
#define AXIS2_DRIVER TMC2130
#define AXIS2_ENCODER AMT_SERIAL

// Communication
#define SERIAL_BAUD 9600
#define WIFI_ENABLED true
#define WIFI_STATION_ENABLED true
```

### Network Connection

OnStepX can connect via:
1. **USB Serial**: Direct connection to host computer
2. **WiFi Station**: Connect to observatory network
3. **WiFi AP**: Create its own access point

For NIGHTWATCH, WiFi Station mode is recommended:

```yaml
# /etc/nightwatch/config.yaml
mount:
  type: "lx200"
  host: "192.168.1.100"  # OnStepX IP address
  port: 9999              # LX200 port
```

### Verifying Connection

```bash
# Test LX200 connection
nc -v 192.168.1.100 9999

# Send GR command (get RA)
echo ":GR#" | nc 192.168.1.100 9999
```

---

## Weather Station (Ecowitt WS90)

### Overview

The Ecowitt WS90 is a wireless weather station that provides:
- Temperature, humidity, pressure
- Wind speed and direction
- Rain detection
- Solar radiation / UV index

### Network Setup

#### Step 1: Connect Gateway

1. Power on the GW1100 gateway
2. Connect gateway to router via Ethernet (recommended) or WiFi
3. Gateway will obtain IP via DHCP

#### Step 2: Configure Local API

Using the Ecowitt app or web interface:

1. Navigate to **Settings > Weather Services**
2. Enable **Customized** upload
3. Configure:
   - **Server IP**: Your NIGHTWATCH server IP
   - **Port**: 8080 (or configured port)
   - **Upload Protocol**: Ecowitt
   - **Upload Interval**: 60 seconds

#### Step 3: Static IP (Recommended)

Assign a static IP to the gateway in your router's DHCP settings:
```
Device: Ecowitt GW1100
MAC: XX:XX:XX:XX:XX:XX
IP: 192.168.1.100
```

### NIGHTWATCH Configuration

```yaml
# /etc/nightwatch/config.yaml
weather:
  enabled: true
  type: "ecowitt"
  host: "192.168.1.100"
  poll_interval_sec: 60

# Safety thresholds (per POS Day 4)
safety:
  wind_limit_mph: 25
  humidity_limit_pct: 85
  temp_min_c: -20
  temp_max_c: 40
  rain_close_immediate: true
```

### Data Fields

| Field | Description | Safety Relevant |
|-------|-------------|-----------------|
| `tempf` | Temperature (°F) | Yes |
| `humidity` | Relative humidity (%) | Yes |
| `windspeedmph` | Wind speed (mph) | Yes |
| `windgustmph` | Wind gust (mph) | Yes |
| `rainratein` | Rain rate (in/hr) | Yes |
| `solarradiation` | Solar radiation (W/m²) | No |
| `uv` | UV index | No |
| `baromrelin` | Barometric pressure | No |

### Verifying Data

```bash
# Check if receiving data
curl http://localhost:8080/weather/current

# Response:
{
  "temperature_f": 65.3,
  "humidity": 45,
  "wind_mph": 5.2,
  "wind_gust_mph": 12.1,
  "rain_rate": 0.0,
  "is_safe": true
}
```

---

## Cloud Sensor (AAG CloudWatcher)

### Overview

The AAG CloudWatcher is a cloud and rain detector providing real-time sky conditions for safety monitoring. NIGHTWATCH uses it as an additional safety sensor complementing the Ecowitt weather station.

### Hardware Requirements

| Component | Specification |
|-----------|---------------|
| Model | AAG CloudWatcher Solo or Pocket |
| Interface | RS-232 Serial (9-pin) |
| Adapter | USB to RS-232 (FTDI recommended) |
| Power | 12V DC, 500mA |
| Cable | DB9 serial cable (straight-through) |

### Wiring Diagram

```
AAG CloudWatcher          USB-Serial Adapter          NIGHTWATCH Server
-----------------         ------------------          ------------------
DB9 Connector    <------> DB9 or USB-Serial  <------> USB Port
Pin 2 (TX)       -------> Pin 2 (RX)
Pin 3 (RX)       <------- Pin 3 (TX)
Pin 5 (GND)      -------> Pin 5 (GND)

Power Supply (12V DC)
```

### Serial Connection Settings

| Parameter | Value |
|-----------|-------|
| Baud Rate | 9600 |
| Data Bits | 8 |
| Stop Bits | 1 |
| Parity | None |
| Flow Control | None |

### USB Serial Adapter Setup

```bash
# List USB serial devices
ls -la /dev/ttyUSB*

# Check which device is the CloudWatcher
dmesg | grep -i "ttyUSB\|ftdi\|serial"

# Add user to dialout group for serial access
sudo usermod -aG dialout $USER

# Create persistent device symlink (optional)
sudo tee /etc/udev/rules.d/99-cloudwatcher.rules << 'EOF'
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", SYMLINK+="cloudwatcher"
EOF

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Testing Serial Communication

```bash
# Test with screen
screen /dev/ttyUSB0 9600

# Or with minicom
minicom -D /dev/ttyUSB0 -b 9600

# Send command and read response (Python)
python3 -c "
import serial
ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=2)
ser.write(b'!2')  # Request sensor data
print(ser.read(100))
ser.close()
"
```

### AAG Protocol Commands

| Command | Description | Response |
|---------|-------------|----------|
| `!1` | Get firmware version | Version string |
| `!2` | Get sensor readings | Temperature, sky IR, rain |
| `!3` | Get thresholds | Current threshold settings |
| `!K` | Get constants | Device calibration values |

### Data Fields

| Field | Description | Safety Relevant |
|-------|-------------|-----------------|
| Sky Temperature | IR temperature of sky (°C) | Yes |
| Ambient Temperature | Sensor temperature (°C) | No |
| Rain Frequency | Rain sensor oscillator (Hz) | Yes |
| Light Level | Ambient light (rel. units) | No |
| Switch Status | Open/Closed recommendation | Yes |

### NIGHTWATCH Configuration

```yaml
# /etc/nightwatch/config.yaml
cloud_sensor:
  enabled: true
  type: "aag_cloudwatcher"
  port: "/dev/ttyUSB0"  # Or /dev/cloudwatcher with udev rule
  baudrate: 9600
  poll_interval_sec: 30

# Safety thresholds for cloud sensor
safety:
  # Sky temperature thresholds (lower = clearer sky)
  sky_temp_clear_c: -20      # Below this = clear
  sky_temp_cloudy_c: -5      # Above this = cloudy
  sky_temp_overcast_c: 0     # Above this = overcast (unsafe)

  # Rain sensor thresholds
  rain_threshold_hz: 2000    # Below this = rain detected

  # Use CloudWatcher switch status for safety
  cloud_sensor_veto: true
```

### Interpreting Sky Temperature

The sky IR temperature indicates cloud cover:

| Sky Temp (°C) | Condition | Safe for Observing |
|---------------|-----------|-------------------|
| < -25 | Very Clear | Yes |
| -25 to -15 | Clear | Yes |
| -15 to -5 | Partly Cloudy | Marginal |
| -5 to 0 | Cloudy | No |
| > 0 | Overcast/Rain | No |

**Note:** Actual thresholds depend on ambient temperature and local conditions. Calibrate for your site.

### Verifying Data

```bash
# Check if receiving data
curl http://localhost:8080/cloud/current

# Expected response:
{
  "sky_temp_c": -22.5,
  "ambient_temp_c": 15.2,
  "rain_hz": 3200,
  "switch_safe": true,
  "condition": "clear",
  "is_safe": true
}
```

### Troubleshooting

#### No Response from Device

```bash
# Verify serial port exists
ls -la /dev/ttyUSB*

# Check permissions
groups $USER  # Should include 'dialout'

# Test with different baud rates
stty -F /dev/ttyUSB0 9600
```

#### Erratic Readings

- Check 12V power supply is stable
- Verify serial cable connections
- Clean the IR sensor lens
- Shield from direct sunlight during day

#### Rain Sensor False Positives

- Clean rain sensor surface with distilled water
- Check heater is functioning (keeps sensor dry)
- Adjust rain threshold in configuration

---

## Audio Hardware

### Microphone Selection

For reliable voice recognition, use a quality USB microphone array:

| Recommended | Model | Notes |
|-------------|-------|-------|
| Best | ReSpeaker USB Mic Array | 4-mic array, beamforming |
| Good | Blue Yeti | Cardioid pattern, gain control |
| Budget | PlayStation Eye | Inexpensive, decent quality |

### Microphone Setup

#### ReSpeaker USB Mic Array

```bash
# Install dependencies
sudo apt install -y pulseaudio pulseaudio-utils

# List audio devices
arecord -l

# Test recording
arecord -D plughw:1,0 -f S16_LE -r 16000 -c 1 test.wav

# Set as default input
pactl set-default-source alsa_input.usb-SEEED_ReSpeaker_4_Mic_Array-00.mono-fallback
```

#### PulseAudio Configuration

Create `/etc/pulse/default.pa.d/nightwatch.pa`:

```
# Set ReSpeaker as default source
set-default-source alsa_input.usb-SEEED_ReSpeaker_4_Mic_Array-00.mono-fallback

# Disable automatic volume adjustments
unload-module module-role-cork
```

### Speaker Selection

For clear voice output:

| Type | Recommendation | Notes |
|------|----------------|-------|
| Powered | JBL Flip / UE Boom | Bluetooth or 3.5mm |
| Passive | Logitech Z200 | USB powered |
| Built-in | Monitor speakers | May have latency |

### Speaker Setup

```bash
# List playback devices
aplay -l

# Test playback
speaker-test -c 2 -t wav

# Set default output
pactl set-default-sink alsa_output.usb-xxx
```

### Audio Configuration

```yaml
# /etc/nightwatch/config.yaml
voice:
  enabled: true
  stt_model: "base.en"
  tts_voice: "en_US-lessac-medium"

  # Audio device hints (optional)
  audio_input_device: "plughw:1,0"
  audio_output_device: "default"

  # Wake word
  wake_word: "nightwatch"
  wake_word_sensitivity: 0.5
```

### Testing Voice Pipeline

```bash
# Test speech recognition
python -m voice.whisper_service --test

# Test text-to-speech
python -m voice.piper_service --test "Hello, this is NIGHTWATCH"

# Full voice test
python -m nightwatch.main --voice-test
```

### Audio Troubleshooting

#### No Microphone Detected

```bash
# Check USB devices
lsusb

# Check ALSA devices
cat /proc/asound/cards

# Reload audio
pulseaudio -k && pulseaudio --start
```

#### Poor Recognition

- Reduce background noise
- Increase microphone gain
- Use noise-canceling microphone
- Try larger Whisper model (`small.en` instead of `base.en`)

#### Choppy Audio Output

- Check CPU usage during TTS
- Reduce Piper voice quality
- Use wired audio instead of Bluetooth

---

## Network Architecture

### Recommended Setup

```
Internet
    |
[Router]---[Observatory Network: 192.168.1.0/24]
    |
    +---[NIGHTWATCH Server: .10]
    |      - Voice processing
    |      - LLM inference
    |      - Orchestration
    |
    +---[OnStepX Mount: .100]
    |      - LX200 port 9999
    |
    +---[Ecowitt Gateway: .101]
    |      - Weather data
    |
    +---[DGX Spark: .20] (optional)
           - GPU inference
```

### Firewall Rules

Allow these ports on the NIGHTWATCH server:

| Port | Service | Direction |
|------|---------|-----------|
| 9999 | LX200 (mount) | Outbound |
| 8080 | Weather webhook | Inbound |
| 10200 | Wyoming TTS | Inbound |
| 10300 | Wyoming STT | Inbound |
| 11111 | Alpaca API | Inbound/Outbound |

```bash
# UFW example
sudo ufw allow 8080/tcp  # Weather
sudo ufw allow 10200/tcp # TTS
sudo ufw allow 10300/tcp # STT
```

### Network Security

- Use WPA3 or WPA2-Enterprise for WiFi
- Consider VLAN isolation for observatory devices
- Enable firewall on NIGHTWATCH server
- Use SSH keys instead of passwords
