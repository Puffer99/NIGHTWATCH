"""
NIGHTWATCH Emergency Response Module.

Implements automated emergency response sequences for critical situations:
- Weather emergencies (rain, high wind)
- Power failures
- Communication failures
- Equipment failures

All emergency responses follow the principle: SAFETY FIRST
When in doubt, park the telescope and close the enclosure.

Steps implemented:
- 481: Create emergency_response.py module
- 482: Emergency park sequence
- 483: Emergency close sequence
- 488: Rain emergency response
- 490: Alert escalation
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Callable, Dict, Any

logger = logging.getLogger("NIGHTWATCH.EmergencyResponse")


class EmergencyType(Enum):
    """Types of emergencies that can trigger response."""
    RAIN = "rain"
    HIGH_WIND = "high_wind"
    POWER_FAILURE = "power_failure"
    LOW_BATTERY = "low_battery"
    WEATHER_UNSAFE = "weather_unsafe"
    COMMUNICATION_LOST = "communication_lost"
    EQUIPMENT_FAILURE = "equipment_failure"
    SENSOR_FAILURE = "sensor_failure"
    USER_TRIGGERED = "user_triggered"


class EmergencyState(Enum):
    """Current state of emergency response."""
    IDLE = "idle"
    RESPONDING = "responding"
    PARKING = "parking"
    CLOSING = "closing"
    ALERTING = "alerting"
    COMPLETED = "completed"
    FAILED = "failed"


class AlertLevel(Enum):
    """Alert escalation levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class EmergencyEvent:
    """Record of an emergency event."""
    emergency_type: EmergencyType
    timestamp: datetime
    description: str
    state: EmergencyState = EmergencyState.IDLE
    response_started: Optional[datetime] = None
    response_completed: Optional[datetime] = None
    alerts_sent: List[str] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class EmergencyConfig:
    """Configuration for emergency response behavior."""
    # Timeouts (seconds)
    park_timeout: float = 60.0
    close_timeout: float = 45.0
    alert_timeout: float = 10.0

    # Retry settings
    max_park_retries: int = 3
    max_close_retries: int = 3
    retry_delay: float = 2.0

    # Alert settings
    enable_voice_alerts: bool = True
    enable_push_alerts: bool = True
    enable_email_alerts: bool = False

    # Escalation delays (seconds)
    warning_to_critical_delay: float = 30.0
    critical_to_emergency_delay: float = 60.0


class EmergencyResponse:
    """
    Manages emergency response sequences for the observatory.

    This class coordinates automated responses to emergency situations,
    ensuring the telescope and equipment are protected.
    """

    def __init__(
        self,
        mount_client=None,
        roof_controller=None,
        safety_monitor=None,
        config: Optional[EmergencyConfig] = None,
    ):
        """
        Initialize emergency response system.

        Args:
            mount_client: LX200Client for telescope control
            roof_controller: RoofController for enclosure
            safety_monitor: SafetyMonitor for condition checks
            config: Emergency response configuration
        """
        self._mount = mount_client
        self._roof = roof_controller
        self._safety = safety_monitor
        self.config = config or EmergencyConfig()

        self._state = EmergencyState.IDLE
        self._current_event: Optional[EmergencyEvent] = None
        self._event_history: List[EmergencyEvent] = []

        # Alert callbacks
        self._alert_callbacks: Dict[AlertLevel, List[Callable]] = {
            AlertLevel.INFO: [],
            AlertLevel.WARNING: [],
            AlertLevel.CRITICAL: [],
            AlertLevel.EMERGENCY: [],
        }

        # Response lock to prevent concurrent responses
        self._response_lock = asyncio.Lock()

        logger.info("Emergency response system initialized")

    @property
    def state(self) -> EmergencyState:
        """Get current emergency state."""
        return self._state

    @property
    def is_responding(self) -> bool:
        """Check if currently responding to an emergency."""
        return self._state not in (EmergencyState.IDLE, EmergencyState.COMPLETED, EmergencyState.FAILED)

    def register_alert_callback(
        self,
        level: AlertLevel,
        callback: Callable[[str, EmergencyType], None],
    ) -> None:
        """
        Register a callback for alert notifications.

        Args:
            level: Alert level to trigger callback
            callback: Function to call with (message, emergency_type)
        """
        self._alert_callbacks[level].append(callback)
        logger.debug(f"Registered alert callback for level {level.value}")

    # =========================================================================
    # Emergency Park Sequence (Step 482)
    # =========================================================================

    async def emergency_park(self) -> bool:
        """
        Execute emergency park sequence (Step 482).

        Immediately parks the telescope with minimal checks.
        This is the highest priority action in an emergency.

        Returns:
            True if park successful, False otherwise
        """
        logger.warning("EMERGENCY PARK initiated")

        if not self._mount:
            logger.error("Cannot park - mount not available")
            return False

        self._state = EmergencyState.PARKING

        for attempt in range(self.config.max_park_retries):
            try:
                # Stop any current motion first
                self._mount.stop()
                await asyncio.sleep(0.5)

                # Execute park command
                success = self._mount.park()

                if success:
                    # Wait for park to complete
                    park_start = datetime.now()
                    while (datetime.now() - park_start).total_seconds() < self.config.park_timeout:
                        await asyncio.sleep(1.0)
                        status = self._mount.get_status()
                        if status and status.is_parked:
                            logger.info("Emergency park completed successfully")
                            if self._current_event:
                                self._current_event.actions_taken.append("Mount parked")
                            return True

                    logger.warning(f"Park timeout on attempt {attempt + 1}")
                else:
                    logger.warning(f"Park command failed on attempt {attempt + 1}")

            except Exception as e:
                logger.error(f"Emergency park error on attempt {attempt + 1}: {e}")
                if self._current_event:
                    self._current_event.errors.append(f"Park error: {e}")

            if attempt < self.config.max_park_retries - 1:
                await asyncio.sleep(self.config.retry_delay)

        logger.error("Emergency park FAILED after all retries")
        return False

    # =========================================================================
    # Emergency Close Sequence (Step 483)
    # =========================================================================

    async def emergency_close(self) -> bool:
        """
        Execute emergency close sequence (Step 483).

        Immediately closes the enclosure. Should be called after
        emergency_park to ensure telescope is in safe position.

        Returns:
            True if close successful, False otherwise
        """
        logger.warning("EMERGENCY CLOSE initiated")

        if not self._roof:
            logger.error("Cannot close - roof controller not available")
            return False

        self._state = EmergencyState.CLOSING

        for attempt in range(self.config.max_close_retries):
            try:
                # Execute close command (force mode - bypass checks)
                success = await self._roof.close()

                if success:
                    # Wait for close to complete
                    close_start = datetime.now()
                    while (datetime.now() - close_start).total_seconds() < self.config.close_timeout:
                        await asyncio.sleep(1.0)
                        state = self._roof.get_state()
                        state_str = state.value if hasattr(state, 'value') else str(state)
                        if state_str == "closed":
                            logger.info("Emergency close completed successfully")
                            if self._current_event:
                                self._current_event.actions_taken.append("Roof closed")
                            return True

                    logger.warning(f"Close timeout on attempt {attempt + 1}")
                else:
                    logger.warning(f"Close command failed on attempt {attempt + 1}")

            except Exception as e:
                logger.error(f"Emergency close error on attempt {attempt + 1}: {e}")
                if self._current_event:
                    self._current_event.errors.append(f"Close error: {e}")

            if attempt < self.config.max_close_retries - 1:
                await asyncio.sleep(self.config.retry_delay)

        logger.error("Emergency close FAILED after all retries")
        return False

    # =========================================================================
    # Mount Safety Position (Step 484)
    # =========================================================================

    async def move_to_safety_position(self) -> bool:
        """
        Move mount to safety position for enclosure close (Step 484).

        The safety position ensures the telescope is clear of the
        roof path before closing. This is typically a low position
        pointing away from the roof opening path.

        Returns:
            True if mount is in safe position, False otherwise
        """
        logger.info("Moving mount to safety position for enclosure close")

        if not self._mount:
            logger.warning("Cannot move to safety - mount not available")
            return True  # Assume safe if no mount

        try:
            # Stop any current motion
            self._mount.stop()
            await asyncio.sleep(0.5)

            # Check if already parked (parked = safe)
            status = self._mount.get_status()
            if status and status.is_parked:
                logger.info("Mount already parked - in safety position")
                if self._current_event:
                    self._current_event.actions_taken.append("Mount verified parked")
                return True

            # Check current altitude if available
            # For roll-off roofs, we need telescope below certain altitude
            # to clear the roof path (typically < 60 degrees)
            if hasattr(status, 'altitude_degrees'):
                if status.altitude_degrees < 60:
                    logger.info(f"Mount at safe altitude ({status.altitude_degrees}°)")
                    if self._current_event:
                        self._current_event.actions_taken.append(
                            f"Mount at safe altitude {status.altitude_degrees}°"
                        )
                    return True

            # If not parked and not at safe altitude, park it
            logger.info("Mount not in safety position - initiating park")
            return await self.emergency_park()

        except Exception as e:
            logger.error(f"Error checking/moving to safety position: {e}")
            if self._current_event:
                self._current_event.errors.append(f"Safety position error: {e}")
            return False

    # =========================================================================
    # Weather Emergency Response (Step 487)
    # =========================================================================

    async def respond_to_weather(self, condition: str = "storm") -> bool:
        """
        Execute weather emergency response (Step 487).

        Handles various weather emergencies (storm, high wind, etc.)
        with appropriate response based on severity.

        Args:
            condition: Weather condition (storm, high_wind, etc.)

        Returns:
            True if response successful, False otherwise
        """
        logger.critical(f"WEATHER EMERGENCY ({condition}) - Initiating response")

        async with self._response_lock:
            emergency_type = EmergencyType.HIGH_WIND if "wind" in condition.lower() else EmergencyType.WEATHER_UNSAFE

            self._current_event = EmergencyEvent(
                emergency_type=emergency_type,
                timestamp=datetime.now(),
                description=f"Weather emergency: {condition}",
                state=EmergencyState.RESPONDING,
                response_started=datetime.now(),
            )
            self._state = EmergencyState.RESPONDING

            await self._send_alert(
                AlertLevel.EMERGENCY,
                f"WEATHER ALERT: {condition.upper()} - Securing observatory",
                emergency_type,
            )

            success = True

            # Step 1: Move to safety position
            if self._mount:
                safety_ok = await self.move_to_safety_position()
                if not safety_ok:
                    # Try direct park as fallback
                    park_ok = await self.emergency_park()
                    if not park_ok:
                        success = False
                        await self._send_alert(
                            AlertLevel.CRITICAL,
                            f"WARNING: Could not secure mount during {condition}",
                            emergency_type,
                        )

            # Step 2: Close enclosure
            if self._roof:
                close_ok = await self.emergency_close()
                if not close_ok:
                    success = False
                    await self._send_alert(
                        AlertLevel.CRITICAL,
                        f"CRITICAL: Enclosure close failed during {condition}",
                        emergency_type,
                    )

            # Complete event
            self._current_event.response_completed = datetime.now()
            if success:
                self._current_event.state = EmergencyState.COMPLETED
                self._state = EmergencyState.COMPLETED
                logger.info(f"Weather emergency ({condition}) response completed")
                await self._send_alert(
                    AlertLevel.INFO,
                    f"Observatory secured. Weather emergency ({condition}) response complete.",
                    emergency_type,
                )
            else:
                self._current_event.state = EmergencyState.FAILED
                self._state = EmergencyState.FAILED
                logger.error(f"Weather emergency ({condition}) response completed with errors")

            self._event_history.append(self._current_event)
            return success

    # =========================================================================
    # Rain Emergency Response (Step 488)
    # =========================================================================

    async def respond_to_rain(self) -> bool:
        """
        Execute rain emergency response (Step 488).

        Rain is the highest priority weather emergency. This sequence:
        1. Immediately stops all motion
        2. Parks the telescope
        3. Closes the enclosure
        4. Sends emergency alerts

        Returns:
            True if all actions successful, False otherwise
        """
        logger.critical("RAIN EMERGENCY - Initiating immediate response")

        async with self._response_lock:
            # Create event record
            self._current_event = EmergencyEvent(
                emergency_type=EmergencyType.RAIN,
                timestamp=datetime.now(),
                description="Rain detected - immediate closure required",
                state=EmergencyState.RESPONDING,
                response_started=datetime.now(),
            )
            self._state = EmergencyState.RESPONDING

            # Step 490: Send immediate alert
            await self._send_alert(
                AlertLevel.EMERGENCY,
                "RAIN DETECTED - Emergency closure in progress",
                EmergencyType.RAIN,
            )

            success = True

            # Step 1: Emergency park
            if self._mount:
                park_ok = await self.emergency_park()
                if not park_ok:
                    success = False
                    await self._send_alert(
                        AlertLevel.CRITICAL,
                        "WARNING: Emergency park failed during rain response",
                        EmergencyType.RAIN,
                    )

            # Step 2: Emergency close (even if park failed)
            if self._roof:
                close_ok = await self.emergency_close()
                if not close_ok:
                    success = False
                    await self._send_alert(
                        AlertLevel.CRITICAL,
                        "CRITICAL: Emergency close failed - manual intervention required",
                        EmergencyType.RAIN,
                    )

            # Complete the event
            self._current_event.response_completed = datetime.now()
            if success:
                self._current_event.state = EmergencyState.COMPLETED
                self._state = EmergencyState.COMPLETED
                logger.info("Rain emergency response completed successfully")
            else:
                self._current_event.state = EmergencyState.FAILED
                self._state = EmergencyState.FAILED
                logger.error("Rain emergency response completed with errors")

            # Archive event
            self._event_history.append(self._current_event)

            return success

    # =========================================================================
    # Alert Escalation (Step 490)
    # =========================================================================

    async def _send_alert(
        self,
        level: AlertLevel,
        message: str,
        emergency_type: EmergencyType,
    ) -> None:
        """
        Send alert through registered callbacks (Step 490).

        Alerts are escalated based on severity:
        - INFO: Logged only
        - WARNING: Voice + log
        - CRITICAL: Voice + push + log
        - EMERGENCY: Voice + push + email + log

        Args:
            level: Alert severity level
            message: Alert message
            emergency_type: Type of emergency
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {level.value.upper()}: {message}"

        # Log the alert
        if level == AlertLevel.EMERGENCY:
            logger.critical(full_message)
        elif level == AlertLevel.CRITICAL:
            logger.error(full_message)
        elif level == AlertLevel.WARNING:
            logger.warning(full_message)
        else:
            logger.info(full_message)

        # Record in event
        if self._current_event:
            self._current_event.alerts_sent.append(full_message)

        # Call registered callbacks
        for callback in self._alert_callbacks[level]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message, emergency_type)
                else:
                    callback(message, emergency_type)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

        # Also call callbacks for lower severity levels
        if level == AlertLevel.EMERGENCY:
            for lower_level in [AlertLevel.CRITICAL, AlertLevel.WARNING, AlertLevel.INFO]:
                for callback in self._alert_callbacks[lower_level]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(message, emergency_type)
                        else:
                            callback(message, emergency_type)
                    except Exception as e:
                        logger.error(f"Alert callback error: {e}")

    async def escalate_alert(
        self,
        current_level: AlertLevel,
        message: str,
        emergency_type: EmergencyType,
    ) -> AlertLevel:
        """
        Escalate alert to next severity level.

        Args:
            current_level: Current alert level
            message: Alert message
            emergency_type: Type of emergency

        Returns:
            New alert level after escalation
        """
        escalation_map = {
            AlertLevel.INFO: AlertLevel.WARNING,
            AlertLevel.WARNING: AlertLevel.CRITICAL,
            AlertLevel.CRITICAL: AlertLevel.EMERGENCY,
            AlertLevel.EMERGENCY: AlertLevel.EMERGENCY,  # Max level
        }

        new_level = escalation_map[current_level]

        if new_level != current_level:
            logger.warning(f"Escalating alert from {current_level.value} to {new_level.value}")
            await self._send_alert(new_level, f"ESCALATED: {message}", emergency_type)

        return new_level

    # =========================================================================
    # Full Emergency Sequence
    # =========================================================================

    async def respond_to_emergency(
        self,
        emergency_type: EmergencyType,
        description: str = "",
    ) -> bool:
        """
        Execute full emergency response sequence.

        Args:
            emergency_type: Type of emergency
            description: Optional description

        Returns:
            True if response successful, False otherwise
        """
        # Route to specific handlers
        if emergency_type == EmergencyType.RAIN:
            return await self.respond_to_rain()

        # Generic emergency response
        logger.critical(f"EMERGENCY: {emergency_type.value} - {description}")

        async with self._response_lock:
            self._current_event = EmergencyEvent(
                emergency_type=emergency_type,
                timestamp=datetime.now(),
                description=description or f"{emergency_type.value} emergency",
                state=EmergencyState.RESPONDING,
                response_started=datetime.now(),
            )
            self._state = EmergencyState.RESPONDING

            await self._send_alert(
                AlertLevel.EMERGENCY,
                f"{emergency_type.value.upper()}: {description}",
                emergency_type,
            )

            success = True

            # Park if mount available
            if self._mount:
                if not await self.emergency_park():
                    success = False

            # Close if roof available
            if self._roof:
                if not await self.emergency_close():
                    success = False

            # Complete event
            self._current_event.response_completed = datetime.now()
            self._current_event.state = EmergencyState.COMPLETED if success else EmergencyState.FAILED
            self._state = self._current_event.state
            self._event_history.append(self._current_event)

            return success

    # =========================================================================
    # Status and History
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get current emergency response status."""
        return {
            "state": self._state.value,
            "is_responding": self.is_responding,
            "current_event": {
                "type": self._current_event.emergency_type.value,
                "started": self._current_event.response_started.isoformat() if self._current_event and self._current_event.response_started else None,
                "actions": self._current_event.actions_taken if self._current_event else [],
            } if self._current_event else None,
            "event_count": len(self._event_history),
        }

    def get_event_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent emergency event history."""
        events = self._event_history[-limit:] if len(self._event_history) > limit else self._event_history
        return [
            {
                "type": e.emergency_type.value,
                "timestamp": e.timestamp.isoformat(),
                "description": e.description,
                "state": e.state.value,
                "actions": e.actions_taken,
                "errors": e.errors,
            }
            for e in reversed(events)
        ]

    def reset(self) -> None:
        """Reset emergency state to idle."""
        if self.is_responding:
            logger.warning("Resetting emergency state while response in progress")
        self._state = EmergencyState.IDLE
        self._current_event = None
        logger.info("Emergency response state reset to IDLE")


# =============================================================================
# Convenience functions
# =============================================================================

async def emergency_park_and_close(
    mount_client=None,
    roof_controller=None,
) -> bool:
    """
    Quick emergency park and close sequence.

    Convenience function for immediate emergency response.

    Args:
        mount_client: LX200Client instance
        roof_controller: RoofController instance

    Returns:
        True if both operations successful
    """
    responder = EmergencyResponse(
        mount_client=mount_client,
        roof_controller=roof_controller,
    )
    return await responder.respond_to_emergency(
        EmergencyType.USER_TRIGGERED,
        "Manual emergency park and close",
    )
