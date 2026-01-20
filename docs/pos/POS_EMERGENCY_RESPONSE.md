# Panel of Specialists: Emergency Response Design

**Document Type:** POS (Panel of Specialists) Deliberation
**Topic:** Emergency Response Architecture for Autonomous Observatory
**Date:** 2025-01-20
**Status:** Design Recommendation

---

## Executive Summary

This document defines how NIGHTWATCH responds to emergency conditions that threaten equipment safety or data integrity. The panel establishes a hierarchy of emergency types, response actions, and recovery procedures.

**Consensus Recommendation:** Implement a layered emergency response system with hardware-level failsafes, software-level automation, and graceful degradation. The system must fail safe (protect equipment) when uncertain, and provide clear status communication throughout.

---

## Panel Members

1. **Safety Systems Engineer** - Hazard analysis and failsafe design
2. **Real-Time Systems Expert** - Response timing and reliability
3. **Observatory Operations Expert** - Recovery procedures and field experience
4. **Electrical/Mechanical Engineer** - Hardware protection requirements

---

## Emergency Classifications

### Level 1: ADVISORY
Non-critical conditions requiring attention but not immediate action.

| Trigger | Response |
|---------|----------|
| High humidity (>80%) | Voice alert, log warning |
| Wind gusts (>15 mph) | Voice alert, consider pausing long exposures |
| Moon interference | Suggest alternative targets |
| Low disk space (<20%) | Alert, continue operation |

### Level 2: WARNING
Degraded conditions that may require intervention.

| Trigger | Response |
|---------|----------|
| Humidity >90% | Pause imaging, alert user |
| Sustained wind >20 mph | Stop guiding, continue tracking |
| Cloud cover increasing | Complete current exposure, pause sequence |
| Communication timeout | Retry, alert after 3 failures |

### Level 3: CRITICAL
Conditions requiring immediate automated response.

| Trigger | Response |
|---------|----------|
| Rain detected | Emergency park, close enclosure |
| Wind >30 mph | Emergency park |
| Humidity >95% | Emergency park, close enclosure |
| Safety sensor failure | Assume worst, emergency park |
| Power failure (on UPS) | Graceful shutdown sequence |

### Level 4: EMERGENCY STOP
Immediate halt of all motion, highest priority.

| Trigger | Response |
|---------|----------|
| Physical E-stop button | Immediate motor disable |
| Voice command "emergency stop" | Immediate motor disable |
| Collision detection | Immediate motor disable |
| Motor stall/overcurrent | Immediate motor disable |

---

## Response Timing Requirements

```
┌─────────────────────────────────────────────────────────────────┐
│                    Response Time Budget                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Rain Detection ──► Park Complete                                │
│  Target: < 60 seconds                                            │
│                                                                  │
│  ├── Rain sensor trigger:     0 ms                               │
│  ├── Software detection:    < 100 ms                             │
│  ├── Emergency park issued: < 200 ms                             │
│  ├── Slew to park position: < 45 sec (worst case)               │
│  ├── Park confirmation:     < 50 sec                             │
│  └── Enclosure close start: < 55 sec                             │
│                                                                  │
│  E-Stop ──► Motor Disable                                        │
│  Target: < 100 ms                                                │
│                                                                  │
│  ├── Button press:            0 ms                               │
│  ├── Hardware interrupt:    < 1 ms                               │
│  └── Motor power cut:       < 50 ms                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Expert Perspectives

### Safety Systems Engineer

**Failsafe Hierarchy:**

```
Level 0: Hardware Failsafes (always active)
├── E-stop button cuts motor power directly
├── Rain sensor can trigger relay independent of software
├── UPS provides shutdown power
└── Mechanical stops prevent over-travel

Level 1: Watchdog Layer
├── Hardware watchdog resets system if software hangs
├── Independent safety microcontroller monitors conditions
└── Heartbeat timeout triggers safe state

Level 2: Software Safety Monitor
├── Continuous condition evaluation
├── Veto system for unsafe commands
└── Automated emergency responses

Level 3: Application Layer
├── User-initiated commands
├── Scheduled operations
└── Imaging sequences
```

**Key Principles:**
1. **Defense in Depth:** Multiple independent layers of protection
2. **Fail Safe:** Unknown state = assume unsafe = protect equipment
3. **No Single Point of Failure:** Any single component failure should not compromise safety
4. **Testable:** All safety systems must be regularly tested

### Real-Time Systems Expert

**Response Architecture:**

```python
class EmergencyManager:
    """Manages emergency detection and response."""

    # Priority levels (lower = higher priority)
    PRIORITY = {
        EmergencyType.E_STOP: 0,      # Immediate
        EmergencyType.RAIN: 1,         # Critical
        EmergencyType.WIND: 2,         # Critical
        EmergencyType.POWER: 3,        # Critical
        EmergencyType.HUMIDITY: 4,     # Warning
    }

    async def handle_emergency(self, emergency: Emergency):
        """Handle emergency with appropriate priority."""

        # E-stop bypasses everything
        if emergency.type == EmergencyType.E_STOP:
            await self._immediate_stop()
            return

        # Check if higher priority emergency already active
        if self._active_emergency:
            if self.PRIORITY[emergency.type] >= self.PRIORITY[self._active_emergency.type]:
                return  # Lower priority, ignore

        # Execute response
        self._active_emergency = emergency
        response = RESPONSE_MAP[emergency.type]

        try:
            await asyncio.wait_for(
                response.execute(),
                timeout=response.max_duration
            )
        except asyncio.TimeoutError:
            # Response timed out, escalate
            await self._escalate(emergency)
```

**Timing Guarantees:**
- Use `asyncio` with strict timeouts
- Critical paths avoid blocking I/O
- Watchdog timer ensures response completion

### Observatory Operations Expert

**Recovery Procedures:**

```
After Rain Emergency:
├── 1. Verify enclosure closed
├── 2. Verify mount parked
├── 3. Wait for rain holdoff (30 min default)
├── 4. Check all sensor readings
├── 5. Voice announcement: "Rain emergency cleared"
├── 6. Await user command to resume
└── 7. Log full incident report

After Power Failure:
├── 1. UPS provides graceful shutdown time
├── 2. Save current state to disk
├── 3. Park mount if time permits
├── 4. Close enclosure if time permits
├── 5. Log shutdown reason
├── 6. On power restore: boot to safe state
└── 7. Require manual inspection before resume

After E-Stop:
├── 1. Motors disabled, system halted
├── 2. Preserve all state information
├── 3. Await physical reset of E-stop
├── 4. Require voice command "resume operations"
├── 5. Perform system self-check
└── 6. Allow normal operation
```

**Field Experience Notes:**
- Rain can arrive faster than weather radar predicts in Nevada
- Morning dew is sneaky - humidity rises rapidly at dawn
- Wind gusts at altitude can exceed sustained by 2x
- Power fluctuations often precede outages

### Electrical/Mechanical Engineer

**Hardware Protection:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Hardware Safety Circuit                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│    ┌──────────┐     ┌──────────┐     ┌──────────┐              │
│    │ E-STOP   │────►│ SAFETY   │────►│ MOTOR    │              │
│    │ BUTTON   │     │ RELAY    │     │ POWER    │              │
│    └──────────┘     └────┬─────┘     └──────────┘              │
│                          │                                       │
│    ┌──────────┐          │                                       │
│    │ RAIN     │──────────┤                                       │
│    │ SENSOR   │          │                                       │
│    └──────────┘          │                                       │
│                          │                                       │
│    ┌──────────┐          │                                       │
│    │ SOFTWARE │──────────┘                                       │
│    │ TRIGGER  │                                                  │
│    └──────────┘                                                  │
│                                                                  │
│    Note: E-stop and rain sensor have hardware path to relay     │
│    Software cannot override hardware safety                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Protection Requirements:**
1. **Motor Overcurrent:** Drivers have built-in protection, software monitors
2. **Limit Switches:** Hard stops with micro-switches on all axes
3. **Thermal Protection:** Temperature monitoring with auto-shutdown at 60°C
4. **Surge Protection:** MOVs on all external connections

---

## Emergency Response Flowchart

```
┌─────────────────────────────────────────────────────────────────┐
│                     Emergency Detected                           │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Classify Level     │
                    │  (1-4)              │
                    └─────────────────────┘
                               │
         ┌─────────┬──────────┼──────────┬─────────┐
         ▼         ▼          ▼          ▼         ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
    │ Level 1 │ │ Level 2 │ │ Level 3 │ │ Level 4 │
    │ ADVISORY│ │ WARNING │ │CRITICAL │ │ E-STOP  │
    └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
         │          │           │            │
         ▼          ▼           ▼            ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
    │ Alert   │ │ Pause   │ │Emergency│ │Immediate│
    │ User    │ │ & Alert │ │ Park    │ │ Stop    │
    └─────────┘ └─────────┘ └────┬────┘ └─────────┘
                                 │
                                 ▼
                          ┌─────────────┐
                          │ Close       │
                          │ Enclosure   │
                          └──────┬──────┘
                                 │
                                 ▼
                          ┌─────────────┐
                          │ Enter       │
                          │ Safe State  │
                          └──────┬──────┘
                                 │
                                 ▼
                          ┌─────────────┐
                          │ Await       │
                          │ Clear/Reset │
                          └─────────────┘
```

---

## Communication During Emergency

### Voice Announcements

```python
EMERGENCY_ANNOUNCEMENTS = {
    EmergencyType.RAIN: [
        "Rain detected! Emergency park initiated.",
        "Parking telescope.",
        "Closing enclosure.",
        "Emergency park complete. Enclosure secured."
    ],
    EmergencyType.WIND: [
        "Wind speed critical at {speed} miles per hour.",
        "Parking telescope for safety.",
        "Parked. Will resume when wind drops below {threshold}."
    ],
    EmergencyType.POWER: [
        "Power failure detected. Running on UPS.",
        "Initiating graceful shutdown.",
        "Parking telescope.",
        "System will shut down in {seconds} seconds."
    ],
    EmergencyType.E_STOP: [
        "Emergency stop activated. All motion halted.",
        "Reset e-stop and say 'resume' when ready."
    ]
}
```

### Status Indicators

| State | LED | Voice | Display |
|-------|-----|-------|---------|
| Normal | Green | Silent | "Tracking M31" |
| Advisory | Yellow blink | Alert tone | "Warning: High humidity" |
| Warning | Yellow solid | Voice alert | "PAUSED: Wind warning" |
| Critical | Red blink | Urgent alert | "EMERGENCY PARK" |
| E-Stop | Red solid | Alarm | "E-STOP ACTIVE" |

---

## Recovery and Resumption

### Automatic Recovery Conditions

```python
RECOVERY_CONDITIONS = {
    EmergencyType.RAIN: {
        "holdoff_minutes": 30,
        "requires": ["rain_stopped", "humidity_safe"],
        "auto_resume": False  # Require user command
    },
    EmergencyType.WIND: {
        "holdoff_minutes": 10,
        "requires": ["wind_below_threshold"],
        "auto_resume": True  # Can auto-resume
    },
    EmergencyType.HUMIDITY: {
        "holdoff_minutes": 15,
        "requires": ["humidity_below_threshold"],
        "auto_resume": True
    }
}
```

### Manual Recovery Required

- After E-stop activation
- After power failure
- After rain event (equipment inspection recommended)
- After any unrecognized emergency

---

## Testing Requirements

1. **Monthly:** Test rain response with simulated rain signal
2. **Monthly:** Test E-stop button functionality
3. **Quarterly:** Full emergency drill (rain + wind + power)
4. **Annually:** UPS runtime test under load

---

*Document prepared by the NIGHTWATCH Panel of Specialists*
