# NIGHTWATCH Pre-Flight Checklist

This checklist ensures all systems are ready before beginning an observing session.

## Quick Reference

**Minimum Requirements for Safe Operation:**
- [ ] Weather conditions safe (wind < 25 mph, humidity < 85%)
- [ ] Cloud sensor showing clear sky
- [ ] Mount communication verified
- [ ] Voice pipeline responding
- [ ] Safety interlocks active

---

## 1. Environmental Checks

### Weather Conditions
- [ ] Check current weather conditions
  ```bash
  curl http://localhost:8080/weather/current
  ```
- [ ] Wind speed below 25 mph
- [ ] Wind gusts below 35 mph
- [ ] Humidity below 85%
- [ ] Temperature within operating range (-20°C to 40°C)
- [ ] No rain detected
- [ ] No precipitation in forecast for session duration

### Cloud Conditions
- [ ] Check cloud sensor status
  ```bash
  curl http://localhost:8080/cloud/current
  ```
- [ ] Sky temperature indicates clear (< -15°C)
- [ ] CloudWatcher switch status is "safe"
- [ ] Visual confirmation of clear sky (if possible)

### Site Conditions
- [ ] Observatory area clear of obstructions
- [ ] No wildlife or debris on roof track
- [ ] Dew heaters connected (if applicable)
- [ ] No nearby light sources active

---

## 2. Hardware Verification

### Mount Controller
- [ ] Mount powered on
- [ ] Verify LX200 connection
  ```bash
  nc -v 192.168.1.100 9999
  echo ":GR#" | nc 192.168.1.100 9999  # Should return RA
  ```
- [ ] Mount in parked position
- [ ] Counterweights balanced
- [ ] Cables have sufficient slack for full rotation

### Encoders (if equipped)
- [ ] Encoder bridge connected
  ```bash
  python -m tests.hardware.test_encoder
  ```
- [ ] Position readings stable
- [ ] No encoder errors in log

### Camera
- [ ] Camera connected and detected
- [ ] Cooling system functional (if applicable)
- [ ] Lens cap removed / dust cover open
- [ ] Filter wheel in correct position

### Guider (if used)
- [ ] Guide camera connected
- [ ] PHD2 service running
  ```bash
  curl http://localhost:4400/status
  ```

### Focuser
- [ ] Focuser connected
- [ ] Position within range
- [ ] Temperature compensation enabled

---

## 3. Software Services

### Core Services
- [ ] NIGHTWATCH service running
  ```bash
  systemctl status nightwatch
  ```
- [ ] All required services healthy
  ```bash
  curl http://localhost:8080/health
  ```

### Voice Pipeline
- [ ] Wyoming STT service running
  ```bash
  curl http://localhost:10300/info
  ```
- [ ] Wyoming TTS service running
  ```bash
  curl http://localhost:10200/info
  ```
- [ ] Microphone detected and working
  ```bash
  arecord -d 2 /tmp/test.wav && aplay /tmp/test.wav
  ```
- [ ] Speakers working
  ```bash
  speaker-test -c 2 -t wav -l 1
  ```

### Safety Monitor
- [ ] Safety service active
- [ ] All sensors reporting
- [ ] Veto system armed
  ```bash
  curl http://localhost:8080/safety/status
  ```

---

## 4. Network Connectivity

### Local Network
- [ ] Mount controller reachable
  ```bash
  ping -c 3 192.168.1.100
  ```
- [ ] Weather gateway reachable
  ```bash
  ping -c 3 192.168.1.101
  ```

### Service Ports
- [ ] LX200 port (9999) accessible
- [ ] Alpaca port (11111) accessible (if used)
- [ ] Weather webhook receiving data

---

## 5. Power Systems

### UPS Status
- [ ] UPS online and charging
  ```bash
  upsc ups@localhost
  ```
- [ ] Battery charge > 80%
- [ ] Load within capacity
- [ ] No alarms active

### Equipment Power
- [ ] Mount powered
- [ ] Camera powered
- [ ] Focuser powered
- [ ] Dew heaters powered
- [ ] Computer on UPS

---

## 6. Enclosure / Roof

### Pre-Open Checks
- [ ] Weather safe for opening
- [ ] No obstructions on roof track
- [ ] Roof controller responding
  ```bash
  curl http://localhost:8080/enclosure/status
  ```

### Opening Sequence
- [ ] Initiate roof open command
- [ ] Wait for full open confirmation
- [ ] Verify open sensor triggered
- [ ] Visual confirmation (if camera available)

---

## 7. Mount Initialization

### Startup Sequence
- [ ] Unpark mount
  ```bash
  curl -X POST http://localhost:8080/mount/unpark
  ```
- [ ] Enable tracking
- [ ] Verify tracking rate (sidereal)
- [ ] Check RA/DEC coordinates reasonable

### Alignment (if needed)
- [ ] Slew to known bright star
- [ ] Center star in FOV
- [ ] Sync mount position
- [ ] Verify pointing accuracy with second star

---

## 8. Final Verification

### Voice Command Test
- [ ] Say "NIGHTWATCH, status report"
- [ ] Confirm voice response heard
- [ ] Test simple command: "What is the current temperature?"

### Safety Test
- [ ] Verify weather veto working
  ```bash
  curl -X POST http://localhost:8080/safety/test-veto
  ```
- [ ] Confirm park-on-unsafe enabled

### Log Check
- [ ] Review recent logs for errors
  ```bash
  journalctl -u nightwatch --since "10 minutes ago"
  ```
- [ ] No critical warnings

---

## Ready for Observation

When all checks pass:

```
✓ Weather: SAFE
✓ Hardware: CONNECTED
✓ Services: RUNNING
✓ Voice: ACTIVE
✓ Safety: ARMED
```

**You are clear to begin observing.**

Say: "NIGHTWATCH, begin observing session"

---

## Emergency Procedures

### Immediate Shutdown
If conditions become unsafe:
- Say: "NIGHTWATCH, emergency park"
- Or manually: `curl -X POST http://localhost:8080/mount/emergency-park`

### Weather Alert
System will automatically:
1. Abort any active slew
2. Park the mount
3. Close the roof
4. Send alert notification

### Power Failure
UPS will:
1. Provide battery backup
2. Trigger graceful shutdown at 30% battery
3. Park mount before power loss

---

## Checklist Version

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-01-19 | Initial pre-flight checklist |
