# Panel of Specialists: Tool Confirmation Design

**Document Type:** POS (Panel of Specialists) Deliberation
**Topic:** Confirmation Requirements for Voice-Activated Telescope Operations
**Date:** 2025-01-20
**Status:** Design Recommendation

---

## Executive Summary

This document presents expert perspectives on when and how NIGHTWATCH should require user confirmation before executing voice commands. The goal is to balance safety (preventing accidental destructive operations) with usability (avoiding confirmation fatigue for routine operations).

**Consensus Recommendation:** Implement a tiered confirmation system based on operation risk level, with immediate execution for safe operations and explicit confirmation for destructive or irreversible actions.

---

## Panel Members

1. **Safety Systems Engineer** - Risk assessment and hazard analysis
2. **UX/Voice Interface Specialist** - User experience and interaction design
3. **Observatory Operations Expert** - Real-world telescope operation patterns
4. **Software Architect** - Implementation considerations

---

## Question for Deliberation

> What operations should require explicit user confirmation, and how should the confirmation interaction be designed for a voice-first interface?

---

## Risk Classification Framework

### Tier 1: Immediate Execution (No Confirmation)

Operations that are safe, reversible, and commonly used.

| Operation | Rationale |
|-----------|-----------|
| `goto_object` / `slew_to` | Slews are abortable, pass through safety checks |
| `lookup_object` | Read-only query |
| `get_weather` | Read-only query |
| `get_mount_status` | Read-only query |
| `whats_up_tonight` | Read-only query |
| `start_tracking` | Safe, can be stopped immediately |
| `stop_tracking` | Safe, preserves position |
| `abort_slew` | Emergency action, should never be delayed |

### Tier 2: Soft Confirmation (Announce Before Execute)

Operations that change state but are easily reversible.

| Operation | Confirmation Style |
|-----------|-------------------|
| `unpark` | "Unparking telescope and starting tracking." |
| `start_guiding` | "Starting autoguiding. Say stop to cancel." |
| `start_capture` | "Beginning capture sequence. {n} frames at {exp}s." |
| `auto_focus` | "Running autofocus routine. This will take about 2 minutes." |

### Tier 3: Explicit Confirmation Required

Operations that are destructive, irreversible, or have significant consequences.

| Operation | Confirmation Prompt |
|-----------|-------------------|
| `park_telescope` | "Park telescope? This will stop any active imaging. Say 'confirm' to proceed." |
| `sync_position` | "Sync mount to {object}? This updates pointing model. Say 'confirm' to proceed." |
| `emergency_shutdown` | "Emergency shutdown requested. All operations will stop. Say 'confirm' or 'abort'." |
| `clear_pointing_model` | "Clear pointing model? This cannot be undone. Say 'confirm' to proceed." |

### Tier 4: Double Confirmation (Critical Operations)

Operations that could cause equipment damage or data loss.

| Operation | Confirmation Flow |
|-----------|------------------|
| `format_camera_storage` | Two-step: "Format storage? Say 'yes' to continue." → "Are you sure? All images will be deleted. Say 'format' to confirm." |
| `override_safety` | "Safety override requested for {reason}. This bypasses protection. Say 'I understand the risk' to proceed." |
| `firmware_update` | "Update firmware to {version}? Do not power off during update. Say 'proceed with update' to confirm." |

---

## Expert Perspectives

### Safety Systems Engineer

**Risk-Based Approach:**

```
Risk Score = Severity × Probability × Detectability

Where:
- Severity: Impact if something goes wrong (1-5)
- Probability: Likelihood of user error (1-5)
- Detectability: How quickly error is noticed (1-5)
```

**Classification:**
```python
CONFIRMATION_LEVELS = {
    "none": risk_score < 10,      # Safe operations
    "announce": risk_score < 25,   # Reversible state changes
    "confirm": risk_score < 50,    # Destructive operations
    "double": risk_score >= 50     # Critical operations
}
```

**Key Principle:** The time cost of confirmation must be weighed against the recovery cost of an erroneous operation. A 3-second confirmation for parking is worthwhile if it prevents accidentally stopping a 2-hour imaging session.

### UX/Voice Interface Specialist

**Confirmation Fatigue Prevention:**

1. **Context-Aware Confirmation:**
   ```python
   # Only require confirmation if there's something to lose
   if imaging_session_active and command == "park":
       require_confirmation()
   else:
       execute_immediately()  # Nothing running, safe to park
   ```

2. **Natural Language Confirmations:**
   - Bad: "Please say 'yes' to confirm."
   - Good: "Park now? Say 'park it' or 'cancel'."
   - Best: "Ready to park. Currently imaging M31 - say 'finish and park' or 'cancel'."

3. **Timeout Behavior:**
   ```python
   CONFIRMATION_TIMEOUT = 10  # seconds
   # If no response, assume user reconsidered
   # Don't default to execution
   ```

4. **Undo Instead of Confirm:**
   - For some operations, immediate execution with easy undo is better UX
   - "Started slewing to M42. Say 'stop' to abort."

### Observatory Operations Expert

**Real-World Patterns:**

1. **Common Sequences Don't Need Interruption:**
   ```
   "Slew to M31" → Execute immediately
   "Start tracking" → Execute immediately
   "Begin guiding" → Announce, then execute
   ```

2. **Context Matters:**
   - "Park" at end of session → Quick confirmation
   - "Park" during active imaging → Strong confirmation with context

3. **Emergency Commands Are Sacred:**
   - NEVER require confirmation for `abort`, `stop`, `emergency_stop`
   - These must execute immediately regardless of state

4. **Operator Fatigue Consideration:**
   - At 3am after 6 hours of observing, confirmation prompts become annoying
   - Consider "experienced mode" that reduces confirmations
   - Log all confirmations skipped for audit

### Software Architect

**Implementation Design:**

```python
class ConfirmationManager:
    """Manages confirmation requirements for tool execution."""

    TIERS = {
        # Tier 1: No confirmation
        "goto_object": ConfirmLevel.NONE,
        "lookup_object": ConfirmLevel.NONE,
        "abort_slew": ConfirmLevel.NONE,  # Emergency - never delay

        # Tier 2: Announce before execute
        "unpark": ConfirmLevel.ANNOUNCE,
        "start_guiding": ConfirmLevel.ANNOUNCE,

        # Tier 3: Explicit confirmation
        "park_telescope": ConfirmLevel.CONFIRM,
        "sync_position": ConfirmLevel.CONFIRM,

        # Tier 4: Double confirmation
        "override_safety": ConfirmLevel.DOUBLE,
    }

    async def check_confirmation(
        self,
        tool_name: str,
        context: SessionContext
    ) -> ConfirmationResult:
        """Check if confirmation is needed based on tool and context."""

        base_level = self.TIERS.get(tool_name, ConfirmLevel.NONE)

        # Upgrade level based on context
        if context.imaging_active and tool_name in IMAGING_DISRUPTIVE:
            base_level = max(base_level, ConfirmLevel.CONFIRM)

        # Downgrade if nothing at risk
        if context.is_idle and base_level == ConfirmLevel.CONFIRM:
            base_level = ConfirmLevel.ANNOUNCE

        return ConfirmationResult(
            level=base_level,
            prompt=self._generate_prompt(tool_name, context),
            timeout=CONFIRMATION_TIMEOUT,
            valid_responses=self._get_valid_responses(base_level)
        )
```

**Voice Response Patterns:**

```python
CONFIRMATION_PROMPTS = {
    ConfirmLevel.ANNOUNCE: "{action}. Say stop to cancel.",
    ConfirmLevel.CONFIRM: "{action}? Say confirm to proceed, or cancel.",
    ConfirmLevel.DOUBLE: "{action}. {warning}. Say '{magic_phrase}' to proceed.",
}

VALID_RESPONSES = {
    ConfirmLevel.CONFIRM: ["confirm", "yes", "proceed", "do it", "go ahead"],
    ConfirmLevel.CANCEL: ["cancel", "no", "stop", "abort", "never mind"],
}
```

---

## Consensus Design

### Confirmation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Voice Command Received                        │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Parse Command      │
                    │  Identify Tool      │
                    └─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Check Base Tier    │
                    │  (from config)      │
                    └─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Apply Context      │
                    │  Modifiers          │
                    └─────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │  NONE    │    │ ANNOUNCE │    │ CONFIRM  │
        │ Execute  │    │ Say then │    │ Wait for │
        │ silently │    │ execute  │    │ response │
        └──────────┘    └──────────┘    └──────────┘
```

### Context Modifiers

| Context | Effect |
|---------|--------|
| Imaging session active | +1 tier for disruptive commands |
| Mount parked | -1 tier for unpark |
| Weather unsafe | Block command, no confirmation needed |
| Emergency mode | All confirmations skipped |

### Response Timeout Behavior

- **Tier 2 (Announce):** Execute after announcement, no wait
- **Tier 3 (Confirm):** Cancel after 10s silence, inform user
- **Tier 4 (Double):** Cancel after 15s, require restart

---

## Implementation Recommendations

1. **Start Conservative:** Begin with more confirmations, reduce based on user feedback
2. **Log Everything:** Record all confirmations (given and skipped) for safety audit
3. **User Preferences:** Allow experienced users to reduce confirmation levels
4. **Emergency Override:** Physical button should always work, bypassing all confirmation

---

*Document prepared by the NIGHTWATCH Panel of Specialists*
