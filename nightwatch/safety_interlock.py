"""
NIGHTWATCH Safety Interlock Module.

Implements pre-command safety validation to prevent unsafe operations.
This module acts as a gatekeeper for all telescope commands, checking
safety conditions before allowing execution.

Safety Priority:
1. Emergency commands (park, close) always allowed
2. Weather conditions must be safe
3. Enclosure must be open for observation
4. Target altitude must be above horizon
5. Power level must be adequate
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable

logger = logging.getLogger("NIGHTWATCH.SafetyInterlock")


class CommandType(Enum):
    """Types of telescope commands."""
    # Mount commands
    SLEW = "slew"
    GOTO = "goto"
    PARK = "park"
    UNPARK = "unpark"
    STOP = "stop"
    TRACK = "track"
    SYNC = "sync"

    # Enclosure commands
    OPEN_ROOF = "open_roof"
    CLOSE_ROOF = "close_roof"

    # Camera commands
    CAPTURE = "capture"
    FOCUS = "focus"

    # Guiding commands
    START_GUIDING = "start_guiding"
    STOP_GUIDING = "stop_guiding"
    DITHER = "dither"

    # System commands
    EMERGENCY_STOP = "emergency_stop"
    SHUTDOWN = "shutdown"


class SafetyCheckResult(Enum):
    """Result of a safety check."""
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    WARNING = "warning"


@dataclass
class SafetyVeto:
    """
    Represents a safety veto preventing command execution (Step 479).

    Provides detailed explanation of why a command was blocked.
    """
    command: CommandType
    reason: str
    check_name: str
    timestamp: datetime = field(default_factory=datetime.now)
    severity: str = "warning"  # warning, critical, emergency
    suggested_action: Optional[str] = None

    def to_spoken_response(self) -> str:
        """Generate a human-friendly response for TTS."""
        response = f"Cannot {self.command.value}. {self.reason}"
        if self.suggested_action:
            response += f" {self.suggested_action}"
        return response

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/API."""
        return {
            "command": self.command.value,
            "reason": self.reason,
            "check_name": self.check_name,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity,
            "suggested_action": self.suggested_action,
        }


@dataclass
class InterlockStatus:
    """Current interlock status."""
    result: SafetyCheckResult
    vetoes: List[SafetyVeto] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def is_allowed(self) -> bool:
        """Check if command is allowed."""
        return self.result == SafetyCheckResult.ALLOWED

    @property
    def primary_reason(self) -> Optional[str]:
        """Get the primary reason for blocking."""
        if self.vetoes:
            return self.vetoes[0].reason
        return None

    def to_spoken_response(self) -> str:
        """Generate spoken response explaining the result."""
        if self.is_allowed:
            if self.warnings:
                return f"Proceeding with caution. {self.warnings[0]}"
            return "Command approved."

        if self.vetoes:
            return self.vetoes[0].to_spoken_response()
        return "Command blocked for safety reasons."


# =============================================================================
# Emergency Commands (Step 478)
# =============================================================================

# Commands that are always allowed regardless of safety state
EMERGENCY_COMMANDS = {
    CommandType.PARK,
    CommandType.CLOSE_ROOF,
    CommandType.STOP,
    CommandType.EMERGENCY_STOP,
    CommandType.STOP_GUIDING,
}

# Commands that require full safety clearance
RESTRICTED_COMMANDS = {
    CommandType.SLEW,
    CommandType.GOTO,
    CommandType.UNPARK,
    CommandType.OPEN_ROOF,
    CommandType.CAPTURE,
    CommandType.START_GUIDING,
}


# =============================================================================
# Safety Interlock Class
# =============================================================================

class SafetyInterlock:
    """
    Pre-command safety validation system (Steps 472-478).

    Checks safety conditions before allowing command execution.
    Integrates with SafetyMonitor for real-time status.
    """

    def __init__(
        self,
        safety_monitor=None,
        altitude_limit_deg: float = 10.0,
        require_enclosure: bool = True,
        min_battery_percent: float = 25.0,
    ):
        """
        Initialize safety interlock.

        Args:
            safety_monitor: SafetyMonitor instance for status
            altitude_limit_deg: Minimum target altitude
            require_enclosure: Require enclosure open for observation
            min_battery_percent: Minimum battery for operations
        """
        self.safety_monitor = safety_monitor
        self.altitude_limit_deg = altitude_limit_deg
        self.require_enclosure = require_enclosure
        self.min_battery_percent = min_battery_percent

        # Current state cache
        self._weather_safe: bool = True
        self._enclosure_open: Optional[bool] = None
        self._battery_percent: Optional[float] = None
        self._on_battery: bool = False
        self._target_altitude: Optional[float] = None

        # Veto history for debugging
        self._veto_history: List[SafetyVeto] = []

        logger.info("Safety interlock initialized")

    def update_weather_status(self, is_safe: bool):
        """Update weather safety status."""
        self._weather_safe = is_safe

    def update_enclosure_status(self, is_open: bool):
        """Update enclosure open status."""
        self._enclosure_open = is_open

    def update_power_status(self, battery_percent: float, on_battery: bool = False):
        """Update power status."""
        self._battery_percent = battery_percent
        self._on_battery = on_battery

    def update_target_altitude(self, altitude_deg: float):
        """Update target altitude for next slew."""
        self._target_altitude = altitude_deg

    def _check_weather(self, command: CommandType) -> Optional[SafetyVeto]:
        """
        Check weather conditions for command (part of Step 473).

        Args:
            command: Command to check

        Returns:
            SafetyVeto if blocked, None if OK
        """
        if command in EMERGENCY_COMMANDS:
            return None  # Always allow emergency commands

        if not self._weather_safe:
            return SafetyVeto(
                command=command,
                reason="Weather conditions unsafe for telescope operation.",
                check_name="weather_check",
                severity="critical",
                suggested_action="Wait for weather to clear.",
            )

        return None

    def _check_slew_safety(
        self,
        command: CommandType,
        target_altitude: Optional[float] = None,
    ) -> Optional[SafetyVeto]:
        """
        Check slew/goto safety (Step 475).

        Args:
            command: Command to check
            target_altitude: Target altitude in degrees

        Returns:
            SafetyVeto if blocked, None if OK
        """
        if command not in {CommandType.SLEW, CommandType.GOTO}:
            return None

        # Use provided altitude or cached value
        altitude = target_altitude or self._target_altitude

        if altitude is not None and altitude < self.altitude_limit_deg:
            return SafetyVeto(
                command=command,
                reason=f"Target altitude {altitude:.1f}° is below minimum {self.altitude_limit_deg}°.",
                check_name="slew_altitude_check",
                severity="critical",  # Block, not just warn
                suggested_action="Choose a target higher above the horizon.",
            )

        # Weather check for slew
        if not self._weather_safe:
            return SafetyVeto(
                command=command,
                reason="Cannot slew during unsafe weather conditions.",
                check_name="slew_weather_check",
                severity="critical",
                suggested_action="Wait for weather to improve.",
            )

        return None

    def _check_unpark_safety(self, command: CommandType) -> Optional[SafetyVeto]:
        """
        Check unpark safety (Step 476).

        Args:
            command: Command to check

        Returns:
            SafetyVeto if blocked, None if OK
        """
        if command != CommandType.UNPARK:
            return None

        # Weather must be safe
        if not self._weather_safe:
            return SafetyVeto(
                command=command,
                reason="Cannot unpark during unsafe weather.",
                check_name="unpark_weather_check",
                severity="critical",
                suggested_action="Wait for weather conditions to improve.",
            )

        # Enclosure should be open (or at least not closed)
        if self.require_enclosure and self._enclosure_open is False:
            return SafetyVeto(
                command=command,
                reason="Cannot unpark with enclosure closed.",
                check_name="unpark_enclosure_check",
                severity="critical",  # Block, not just warn
                suggested_action="Open the roof first.",
            )

        # Check power
        if self._battery_percent is not None:
            if self._battery_percent < self.min_battery_percent:
                return SafetyVeto(
                    command=command,
                    reason=f"Battery too low ({self._battery_percent:.0f}%) to unpark safely.",
                    check_name="unpark_power_check",
                    severity="critical",
                    suggested_action="Wait for power to be restored.",
                )

        return None

    def _check_roof_open_safety(self, command: CommandType) -> Optional[SafetyVeto]:
        """
        Check roof open safety (Step 477).

        Args:
            command: Command to check

        Returns:
            SafetyVeto if blocked, None if OK
        """
        if command != CommandType.OPEN_ROOF:
            return None

        # Weather must be safe
        if not self._weather_safe:
            return SafetyVeto(
                command=command,
                reason="Cannot open roof during unsafe weather.",
                check_name="roof_weather_check",
                severity="critical",
                suggested_action="Wait for weather to improve before opening.",
            )

        # Check power
        if self._battery_percent is not None:
            if self._battery_percent < self.min_battery_percent:
                return SafetyVeto(
                    command=command,
                    reason=f"Battery too low ({self._battery_percent:.0f}%) to open roof safely.",
                    check_name="roof_power_check",
                    severity="critical",
                    suggested_action="Ensure power is available before opening.",
                )

        return None

    def _check_power(self, command: CommandType) -> Optional[SafetyVeto]:
        """
        Check power status for command.

        Args:
            command: Command to check

        Returns:
            SafetyVeto if blocked, None if OK
        """
        if command in EMERGENCY_COMMANDS:
            return None  # Always allow emergency commands

        if self._battery_percent is None:
            return None  # No power data, assume OK

        if self._battery_percent < self.min_battery_percent:
            return SafetyVeto(
                command=command,
                reason=f"Battery level critical ({self._battery_percent:.0f}%).",
                check_name="power_check",
                severity="critical",
                suggested_action="Wait for power to be restored or charge battery.",
            )

        return None

    def _check_enclosure(self, command: CommandType) -> Optional[SafetyVeto]:
        """
        Check enclosure status for observation commands.

        Args:
            command: Command to check

        Returns:
            SafetyVeto if blocked, None if OK
        """
        if command in EMERGENCY_COMMANDS:
            return None

        # Only check for commands that need open sky
        observation_commands = {
            CommandType.SLEW,
            CommandType.GOTO,
            CommandType.CAPTURE,
            CommandType.START_GUIDING,
        }

        if command not in observation_commands:
            return None

        if self.require_enclosure and self._enclosure_open is False:
            return SafetyVeto(
                command=command,
                reason="Enclosure is closed.",
                check_name="enclosure_check",
                severity="warning",
                suggested_action="Open the roof before observing.",
            )

        return None

    def check_command(
        self,
        command: CommandType,
        target_altitude: Optional[float] = None,
        **kwargs,
    ) -> InterlockStatus:
        """
        Perform full safety check for a command (Step 473).

        Args:
            command: Command type to check
            target_altitude: Target altitude for slew commands
            **kwargs: Additional command parameters

        Returns:
            InterlockStatus with result and any vetoes
        """
        vetoes = []
        warnings = []

        # Step 478: Emergency commands are always allowed
        if command in EMERGENCY_COMMANDS:
            logger.debug(f"Emergency command {command.value} allowed without checks")
            return InterlockStatus(
                result=SafetyCheckResult.ALLOWED,
                vetoes=[],
                warnings=[],
            )

        # Run all safety checks
        checks = [
            self._check_weather(command),
            self._check_slew_safety(command, target_altitude),
            self._check_unpark_safety(command),
            self._check_roof_open_safety(command),
            self._check_power(command),
            self._check_enclosure(command),
        ]

        for veto in checks:
            if veto is not None:
                vetoes.append(veto)
                self._veto_history.append(veto)
                logger.warning(f"Safety veto: {veto.reason}")

        # Determine result
        if vetoes:
            # Check if all vetoes are warnings (not critical)
            all_warnings = all(v.severity == "warning" for v in vetoes)
            if all_warnings:
                result = SafetyCheckResult.WARNING
                warnings = [v.reason for v in vetoes]
                vetoes = []  # Move to warnings
            else:
                result = SafetyCheckResult.BLOCKED
        else:
            result = SafetyCheckResult.ALLOWED

        # Add on-battery warning if applicable
        if self._on_battery and result == SafetyCheckResult.ALLOWED:
            warnings.append("Running on battery power")

        status = InterlockStatus(
            result=result,
            vetoes=vetoes,
            warnings=warnings,
        )

        logger.info(f"Safety check for {command.value}: {result.value}")
        return status

    def get_veto_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent veto history."""
        return [v.to_dict() for v in self._veto_history[-limit:]]

    def clear_veto_history(self):
        """Clear veto history."""
        self._veto_history.clear()

    def is_safe_for_observation(self) -> bool:
        """Quick check if conditions are safe for observation."""
        return (
            self._weather_safe and
            (not self.require_enclosure or self._enclosure_open is not False) and
            (self._battery_percent is None or self._battery_percent >= self.min_battery_percent)
        )


# =============================================================================
# Decorator for Command Safety
# =============================================================================

def require_safety_check(command_type: CommandType):
    """
    Decorator to require safety check before command execution.

    Usage:
        @require_safety_check(CommandType.SLEW)
        async def slew_to_target(self, ra, dec):
            ...
    """
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            # Get interlock from self if available
            interlock = getattr(self, '_safety_interlock', None)
            if interlock is None:
                # No interlock configured, proceed
                return await func(self, *args, **kwargs)

            # Extract target altitude if present
            target_alt = kwargs.get('altitude') or kwargs.get('alt')

            # Check safety
            status = interlock.check_command(command_type, target_altitude=target_alt)

            if not status.is_allowed:
                raise SafetyInterlockError(
                    f"Command {command_type.value} blocked: {status.primary_reason}",
                    status=status,
                )

            # Log warnings
            for warning in status.warnings:
                logger.warning(f"Safety warning: {warning}")

            return await func(self, *args, **kwargs)
        return wrapper
    return decorator


class SafetyInterlockError(Exception):
    """Exception raised when a command is blocked by safety interlock."""

    def __init__(self, message: str, status: Optional[InterlockStatus] = None):
        super().__init__(message)
        self.status = status

    @property
    def spoken_response(self) -> str:
        """Get spoken response for TTS."""
        if self.status:
            return self.status.to_spoken_response()
        return str(self)


# =============================================================================
# Factory Function
# =============================================================================

def create_safety_interlock(
    safety_monitor=None,
    **kwargs,
) -> SafetyInterlock:
    """
    Create a safety interlock instance.

    Args:
        safety_monitor: Optional SafetyMonitor for status updates
        **kwargs: Additional configuration

    Returns:
        Configured SafetyInterlock instance
    """
    return SafetyInterlock(
        safety_monitor=safety_monitor,
        **kwargs,
    )
