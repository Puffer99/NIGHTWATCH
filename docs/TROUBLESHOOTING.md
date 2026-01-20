# NIGHTWATCH Troubleshooting Guide

Solutions to common issues with the NIGHTWATCH observatory system.

## Table of Contents

- [Mount Connection Issues](#mount-connection-issues)
- [Weather Station Issues](#weather-station-issues)
- [Voice Pipeline Issues](#voice-pipeline-issues)
- [Safety System Issues](#safety-system-issues)
- [Catalog and Ephemeris Issues](#catalog-and-ephemeris-issues)
- [Docker and Deployment Issues](#docker-and-deployment-issues)
- [Performance Issues](#performance-issues)

---

## Mount Connection Issues

### Cannot Connect to OnStepX

**Symptoms**: Connection timeout, "Failed to connect to mount" errors.

**Solutions**:

1. **Verify network connectivity**:
   ```bash
   ping 192.168.1.100  # Replace with your mount IP
   ```

2. **Check port availability**:
   ```bash
   nc -zv 192.168.1.100 9999
   ```

3. **Verify OnStepX is running**:
   - Check that the Teensy is powered and LED is blinking
   - Connect via serial to verify firmware is responding

4. **Check firewall rules**:
   ```bash
   sudo ufw allow 9999/tcp
   ```

5. **Test with telnet**:
   ```bash
   telnet 192.168.1.100 9999
   # Type: :GR#
   # Should return current RA
   ```

### Mount Not Responding to Commands

**Symptoms**: Commands sent but mount doesn't move.

**Solutions**:

1. **Check if mount is parked**:
   ```python
   if client.is_parked():
       client.unpark()
   ```

2. **Verify tracking is enabled**:
   ```python
   client.set_tracking(True)
   ```

3. **Check for safety lockouts**:
   ```python
   safety.get_veto_reasons()  # Check for active vetoes
   ```

4. **Reset mount controller**:
   - Power cycle the Teensy
   - Wait 10 seconds before reconnecting

### Slew Fails or Stops Unexpectedly

**Symptoms**: Mount starts slewing then stops before reaching target.

**Causes and Solutions**:

1. **Target below horizon limit**:
   - Check target altitude: `ephemeris.get_object_altitude(ra, dec)`
   - Default minimum is 10 degrees

2. **Meridian flip required**:
   - Mount may refuse if flip would exceed limits
   - Try slewing to intermediate position first

3. **Motor stall detected**:
   - Check for mechanical obstructions
   - Verify counterweight balance

---

## Weather Station Issues

### Ecowitt Station Not Responding

**Symptoms**: "Connection refused" or timeout errors.

**Solutions**:

1. **Verify gateway IP**:
   ```bash
   # Check your router's DHCP table for the gateway
   nmap -sP 192.168.1.0/24 | grep -i ecowitt
   ```

2. **Check gateway web interface**:
   - Open `http://192.168.1.101` in browser
   - Verify device is online

3. **Restart the gateway**:
   - Power cycle the Ecowitt GW1000/GW2000
   - Wait 60 seconds for reconnection

4. **Check network mode**:
   - Gateway must be in "Local API" mode, not cloud-only

### Weather Data Stale or Missing

**Symptoms**: Old timestamps, missing sensor values.

**Solutions**:

1. **Check sensor batteries**:
   - Replace batteries in outdoor sensors
   - WS90 uses solar power but has backup battery

2. **Check sensor range**:
   - Move sensors closer to gateway
   - Avoid metal structures between sensor and gateway

3. **Verify sensor pairing**:
   - Re-pair sensors via gateway web interface

---

## Voice Pipeline Issues

### Microphone Not Detected

**Symptoms**: "No audio input device found" errors.

**Solutions**:

1. **List available devices**:
   ```python
   import sounddevice as sd
   print(sd.query_devices())
   ```

2. **Set correct device**:
   ```python
   sd.default.device = 1  # Use device index from query
   ```

3. **Check permissions**:
   ```bash
   # Add user to audio group
   sudo usermod -a -G audio $USER
   ```

4. **Install ALSA utilities**:
   ```bash
   sudo apt install alsa-utils
   arecord -l  # List capture devices
   ```

### Speech Recognition Poor Accuracy

**Symptoms**: Commands misheard, wrong objects identified.

**Solutions**:

1. **Use larger Whisper model**:
   ```python
   stt = WhisperSTT(model="small")  # or "medium"
   ```

2. **Reduce background noise**:
   - Use directional microphone
   - Add noise gate in audio preprocessing

3. **Speak clearly and slowly**:
   - Pause between words for object names
   - "Slew to... Andromeda Galaxy"

4. **Add custom vocabulary boost**:
   - Configure astronomy terms in STT settings

### TTS Audio Not Playing

**Symptoms**: Text processed but no audio output.

**Solutions**:

1. **Check audio output device**:
   ```bash
   aplay -l  # List playback devices
   speaker-test -t wav  # Test speakers
   ```

2. **Verify Piper installation**:
   ```bash
   echo "Test" | piper --model en_US-lessac-medium --output_file test.wav
   aplay test.wav
   ```

3. **Check audio permissions**:
   ```bash
   pulseaudio --check
   systemctl --user status pulseaudio
   ```

---

## Safety System Issues

### False Safety Triggers

**Symptoms**: Operations blocked when conditions seem safe.

**Solutions**:

1. **Check threshold configuration**:
   ```yaml
   # config/safety.yaml
   thresholds:
     max_wind_speed_ms: 10.0  # May be too conservative
     max_humidity_percent: 90
   ```

2. **View active vetoes**:
   ```python
   reasons = safety.get_veto_reasons()
   print(reasons)  # See why blocked
   ```

3. **Check sensor calibration**:
   - Weather station may report incorrect values
   - Compare with independent measurement

### Rain Holdoff Won't Clear

**Symptoms**: "Rain holdoff active" persists after rain stops.

**Solutions**:

1. **Check holdoff duration**:
   ```yaml
   # config/safety.yaml
   thresholds:
     rain_holdoff_minutes: 30  # Reduce if too long
   ```

2. **Check rain sensor**:
   - Sensor may be stuck or dirty
   - Clean rain sensor surface

3. **Manual override** (use with caution):
   ```python
   safety.clear_rain_holdoff()  # If implemented
   ```

### Emergency Stop Won't Release

**Symptoms**: Mount locked after emergency stop.

**Solutions**:

1. **Clear emergency state**:
   ```python
   safety.clear_emergency()
   mount.unpark()
   ```

2. **Power cycle mount**:
   - Turn off mount power
   - Wait 10 seconds
   - Power on and reinitialize

---

## Catalog and Ephemeris Issues

### Object Not Found

**Symptoms**: "Object not found in catalog" for known objects.

**Solutions**:

1. **Check spelling**:
   ```python
   # Use fuzzy search for typos
   results = catalog.fuzzy_search("andromdea")
   ```

2. **Try alternate names**:
   - M31 = Andromeda Galaxy = NGC 224
   - Use catalog ID if common name fails

3. **Check catalog is loaded**:
   ```python
   stats = catalog.db.get_stats()
   print(f"Objects loaded: {stats['total']}")
   ```

### Ephemeris Calculations Wrong

**Symptoms**: Planets in wrong position, incorrect rise/set times.

**Solutions**:

1. **Verify location settings**:
   ```python
   print(f"Lat: {ephemeris.latitude}, Lon: {ephemeris.longitude}")
   ```

2. **Check timezone**:
   ```bash
   timedatectl  # Verify system timezone
   ```

3. **Update ephemeris data**:
   ```python
   # Skyfield auto-downloads, but may need refresh
   from skyfield.api import load
   load.download('de421.bsp')
   ```

---

## Docker and Deployment Issues

### Container Won't Start

**Symptoms**: Docker container exits immediately.

**Solutions**:

1. **Check logs**:
   ```bash
   docker compose logs nightwatch
   ```

2. **Verify configuration**:
   ```bash
   docker compose config  # Validate compose file
   ```

3. **Check volume mounts**:
   - Ensure config files exist at mount points
   - Check file permissions

### Simulator Connection Failed

**Symptoms**: Tests fail with "simulator not available".

**Solutions**:

1. **Start simulators**:
   ```bash
   docker compose -f docker/docker-compose.dev.yml up -d
   ```

2. **Check simulator health**:
   ```bash
   curl http://localhost:11111/management/apiversions
   ```

3. **Wait for startup**:
   ```bash
   # Simulators may take 30-60 seconds to initialize
   sleep 60
   ```

---

## Performance Issues

### Slow Response Times

**Symptoms**: Commands take several seconds to process.

**Solutions**:

1. **Check STT model size**:
   - Use "tiny" or "base" model for faster response
   - Trade accuracy for speed

2. **Enable GPU acceleration**:
   ```bash
   # Verify CUDA is available
   python -c "import torch; print(torch.cuda.is_available())"
   ```

3. **Reduce logging verbosity**:
   ```yaml
   logging:
     level: WARNING  # Instead of DEBUG
   ```

### High Memory Usage

**Symptoms**: System runs out of memory, OOM kills.

**Solutions**:

1. **Use smaller models**:
   - Whisper tiny: ~75MB
   - Whisper base: ~150MB
   - Whisper small: ~500MB

2. **Limit catalog cache**:
   ```python
   catalog = CatalogService(cache_size=50)  # Reduce from 100
   ```

3. **Monitor memory**:
   ```bash
   watch -n 1 free -h
   ```

---

## Getting More Help

If these solutions don't resolve your issue:

1. **Check logs**:
   ```bash
   # Application logs
   tail -f logs/nightwatch.log

   # System logs
   journalctl -f -u nightwatch
   ```

2. **Enable debug mode**:
   ```yaml
   logging:
     level: DEBUG
   ```

3. **Report an issue**:
   - [GitHub Issues](https://github.com/THOClabs/NIGHTWATCH/issues)
   - Include logs, configuration, and steps to reproduce

4. **Community support**:
   - [GitHub Discussions](https://github.com/THOClabs/NIGHTWATCH/discussions)
