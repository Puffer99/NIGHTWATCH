"""
Unit tests for NIGHTWATCH Safety Interlock.

Tests pre-command safety validation including weather, altitude,
power, enclosure checks, and emergency command overrides.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from nightwatch.safety_interlock import (
    SafetyInterlock,
    CommandType,
    SafetyCheckResult,
    SafetyVeto,
    InterlockStatus,
    SafetyInterlockError,
    EMERGENCY_COMMANDS,
    RESTRICTED_COMMANDS,
    create_safety_interlock,
    require_safety_check,
)


class TestCommandType:
    """Tests for CommandType enum."""

    def test_mount_commands(self):
        """Test mount command types exist."""
        assert CommandType.SLEW.value == "slew"
        assert CommandType.GOTO.value == "goto"
        assert CommandType.PARK.value == "park"
        assert CommandType.UNPARK.value == "unpark"

    def test_enclosure_commands(self):
        """Test enclosure command types exist."""
        assert CommandType.OPEN_ROOF.value == "open_roof"
        assert CommandType.CLOSE_ROOF.value == "close_roof"

    def test_emergency_commands(self):
        """Test emergency commands are defined."""
        assert CommandType.EMERGENCY_STOP.value == "emergency_stop"
        assert CommandType.STOP.value == "stop"


class TestSafetyVeto:
    """Tests for SafetyVeto dataclass."""

    def test_create_veto(self):
        """Test creating a safety veto."""
        veto = SafetyVeto(
            command=CommandType.SLEW,
            reason="Weather unsafe",
            check_name="weather_check",
        )

        assert veto.command == CommandType.SLEW
        assert veto.reason == "Weather unsafe"
        assert veto.check_name == "weather_check"

    def test_to_spoken_response(self):
        """Test spoken response generation."""
        veto = SafetyVeto(
            command=CommandType.SLEW,
            reason="Target below horizon.",
            check_name="altitude_check",
            suggested_action="Choose a higher target.",
        )

        response = veto.to_spoken_response()
        assert "slew" in response.lower()
        assert "below horizon" in response.lower()
        assert "higher target" in response.lower()

    def test_to_dict(self):
        """Test dictionary conversion."""
        veto = SafetyVeto(
            command=CommandType.PARK,
            reason="Test reason",
            check_name="test_check",
            severity="warning",
        )

        d = veto.to_dict()
        assert d["command"] == "park"
        assert d["reason"] == "Test reason"
        assert d["severity"] == "warning"
        assert "timestamp" in d


class TestInterlockStatus:
    """Tests for InterlockStatus dataclass."""

    def test_allowed_status(self):
        """Test allowed interlock status."""
        status = InterlockStatus(
            result=SafetyCheckResult.ALLOWED,
            vetoes=[],
            warnings=[],
        )

        assert status.is_allowed is True
        assert status.primary_reason is None

    def test_blocked_status(self):
        """Test blocked interlock status."""
        veto = SafetyVeto(
            command=CommandType.SLEW,
            reason="Weather unsafe",
            check_name="weather_check",
        )
        status = InterlockStatus(
            result=SafetyCheckResult.BLOCKED,
            vetoes=[veto],
        )

        assert status.is_allowed is False
        assert status.primary_reason == "Weather unsafe"

    def test_spoken_response_allowed(self):
        """Test spoken response for allowed command."""
        status = InterlockStatus(
            result=SafetyCheckResult.ALLOWED,
            vetoes=[],
            warnings=[],
        )

        response = status.to_spoken_response()
        assert "approved" in response.lower()

    def test_spoken_response_with_warning(self):
        """Test spoken response with warnings."""
        status = InterlockStatus(
            result=SafetyCheckResult.ALLOWED,
            vetoes=[],
            warnings=["Running on battery power"],
        )

        response = status.to_spoken_response()
        assert "caution" in response.lower()


class TestEmergencyCommands:
    """Tests for emergency command handling (Step 478)."""

    @pytest.fixture
    def interlock(self):
        """Create interlock for testing."""
        return SafetyInterlock()

    def test_park_always_allowed(self, interlock):
        """Test PARK is always allowed."""
        # Set unsafe conditions
        interlock.update_weather_status(False)
        interlock.update_power_status(5.0)  # Critical low

        status = interlock.check_command(CommandType.PARK)
        assert status.is_allowed is True

    def test_close_roof_always_allowed(self, interlock):
        """Test CLOSE_ROOF is always allowed."""
        interlock.update_weather_status(False)

        status = interlock.check_command(CommandType.CLOSE_ROOF)
        assert status.is_allowed is True

    def test_stop_always_allowed(self, interlock):
        """Test STOP is always allowed."""
        interlock.update_weather_status(False)

        status = interlock.check_command(CommandType.STOP)
        assert status.is_allowed is True

    def test_emergency_stop_always_allowed(self, interlock):
        """Test EMERGENCY_STOP is always allowed."""
        interlock.update_weather_status(False)
        interlock.update_power_status(1.0)  # Nearly dead

        status = interlock.check_command(CommandType.EMERGENCY_STOP)
        assert status.is_allowed is True

    def test_emergency_commands_set(self):
        """Test emergency commands are properly defined."""
        assert CommandType.PARK in EMERGENCY_COMMANDS
        assert CommandType.CLOSE_ROOF in EMERGENCY_COMMANDS
        assert CommandType.STOP in EMERGENCY_COMMANDS
        assert CommandType.STOP_GUIDING in EMERGENCY_COMMANDS


class TestWeatherSafetyCheck:
    """Tests for weather safety check (Step 473)."""

    @pytest.fixture
    def interlock(self):
        """Create interlock for testing."""
        return SafetyInterlock()

    def test_safe_weather_allows_commands(self, interlock):
        """Test commands allowed with safe weather."""
        interlock.update_weather_status(True)
        interlock.update_enclosure_status(True)

        status = interlock.check_command(CommandType.SLEW)
        assert status.is_allowed is True

    def test_unsafe_weather_blocks_slew(self, interlock):
        """Test unsafe weather blocks slew."""
        interlock.update_weather_status(False)

        status = interlock.check_command(CommandType.SLEW)
        assert status.is_allowed is False
        assert any("weather" in v.reason.lower() for v in status.vetoes)

    def test_unsafe_weather_blocks_capture(self, interlock):
        """Test unsafe weather blocks capture."""
        interlock.update_weather_status(False)

        status = interlock.check_command(CommandType.CAPTURE)
        assert status.is_allowed is False


class TestSlewSafetyCheck:
    """Tests for slew safety check (Step 475)."""

    @pytest.fixture
    def interlock(self):
        """Create interlock with 10° altitude limit."""
        return SafetyInterlock(altitude_limit_deg=10.0)

    def test_high_altitude_allowed(self, interlock):
        """Test slew to high altitude allowed."""
        interlock.update_weather_status(True)
        interlock.update_enclosure_status(True)

        status = interlock.check_command(CommandType.SLEW, target_altitude=45.0)
        assert status.is_allowed is True

    def test_low_altitude_blocked(self, interlock):
        """Test slew to low altitude blocked."""
        interlock.update_weather_status(True)
        interlock.update_enclosure_status(True)

        status = interlock.check_command(CommandType.SLEW, target_altitude=5.0)
        assert status.is_allowed is False
        assert any("altitude" in v.reason.lower() for v in status.vetoes)

    def test_uses_cached_altitude(self, interlock):
        """Test slew uses cached target altitude."""
        interlock.update_weather_status(True)
        interlock.update_enclosure_status(True)
        interlock.update_target_altitude(5.0)  # Below limit

        status = interlock.check_command(CommandType.SLEW)
        assert status.is_allowed is False

    def test_goto_same_as_slew(self, interlock):
        """Test GOTO has same checks as SLEW."""
        interlock.update_weather_status(True)
        interlock.update_enclosure_status(True)

        status = interlock.check_command(CommandType.GOTO, target_altitude=5.0)
        assert status.is_allowed is False


class TestUnparkSafetyCheck:
    """Tests for unpark safety check (Step 476)."""

    @pytest.fixture
    def interlock(self):
        """Create interlock for testing."""
        return SafetyInterlock(require_enclosure=True)

    def test_safe_conditions_allow_unpark(self, interlock):
        """Test unpark allowed with safe conditions."""
        interlock.update_weather_status(True)
        interlock.update_enclosure_status(True)
        interlock.update_power_status(100.0)

        status = interlock.check_command(CommandType.UNPARK)
        assert status.is_allowed is True

    def test_unsafe_weather_blocks_unpark(self, interlock):
        """Test unsafe weather blocks unpark."""
        interlock.update_weather_status(False)
        interlock.update_enclosure_status(True)

        status = interlock.check_command(CommandType.UNPARK)
        assert status.is_allowed is False
        assert any("weather" in v.reason.lower() for v in status.vetoes)

    def test_closed_enclosure_blocks_unpark(self, interlock):
        """Test closed enclosure blocks unpark."""
        interlock.update_weather_status(True)
        interlock.update_enclosure_status(False)

        status = interlock.check_command(CommandType.UNPARK)
        assert status.is_allowed is False
        assert any("enclosure" in v.reason.lower() for v in status.vetoes)

    def test_low_battery_blocks_unpark(self, interlock):
        """Test low battery blocks unpark."""
        interlock.update_weather_status(True)
        interlock.update_enclosure_status(True)
        interlock.update_power_status(10.0)  # Below 25% threshold

        status = interlock.check_command(CommandType.UNPARK)
        assert status.is_allowed is False
        assert any("battery" in v.reason.lower() for v in status.vetoes)


class TestRoofOpenSafetyCheck:
    """Tests for roof open safety check (Step 477)."""

    @pytest.fixture
    def interlock(self):
        """Create interlock for testing."""
        return SafetyInterlock()

    def test_safe_conditions_allow_open(self, interlock):
        """Test roof open allowed with safe conditions."""
        interlock.update_weather_status(True)
        interlock.update_power_status(100.0)

        status = interlock.check_command(CommandType.OPEN_ROOF)
        assert status.is_allowed is True

    def test_unsafe_weather_blocks_open(self, interlock):
        """Test unsafe weather blocks roof open."""
        interlock.update_weather_status(False)

        status = interlock.check_command(CommandType.OPEN_ROOF)
        assert status.is_allowed is False
        assert any("weather" in v.reason.lower() for v in status.vetoes)

    def test_low_battery_blocks_open(self, interlock):
        """Test low battery blocks roof open."""
        interlock.update_weather_status(True)
        interlock.update_power_status(10.0)

        status = interlock.check_command(CommandType.OPEN_ROOF)
        assert status.is_allowed is False
        assert any("battery" in v.reason.lower() for v in status.vetoes)


class TestEnclosureCheck:
    """Tests for enclosure safety check."""

    @pytest.fixture
    def interlock(self):
        """Create interlock requiring enclosure."""
        return SafetyInterlock(require_enclosure=True)

    def test_open_enclosure_allows_observation(self, interlock):
        """Test open enclosure allows observation commands."""
        interlock.update_weather_status(True)
        interlock.update_enclosure_status(True)

        status = interlock.check_command(CommandType.CAPTURE)
        assert status.is_allowed is True

    def test_closed_enclosure_blocks_observation(self, interlock):
        """Test closed enclosure blocks observation."""
        interlock.update_weather_status(True)
        interlock.update_enclosure_status(False)

        status = interlock.check_command(CommandType.CAPTURE)
        assert status.is_allowed is False

    def test_enclosure_check_can_be_disabled(self):
        """Test enclosure check can be disabled."""
        interlock = SafetyInterlock(require_enclosure=False)
        interlock.update_weather_status(True)
        interlock.update_enclosure_status(False)

        status = interlock.check_command(CommandType.CAPTURE)
        # Should still be blocked by other checks but not enclosure
        # Actually with weather safe and no enclosure req, should be allowed
        assert status.is_allowed is True


class TestPowerCheck:
    """Tests for power safety check."""

    @pytest.fixture
    def interlock(self):
        """Create interlock with 25% battery threshold."""
        return SafetyInterlock(min_battery_percent=25.0)

    def test_full_battery_allowed(self, interlock):
        """Test full battery allows commands."""
        interlock.update_weather_status(True)
        interlock.update_enclosure_status(True)
        interlock.update_power_status(100.0)

        status = interlock.check_command(CommandType.SLEW)
        assert status.is_allowed is True

    def test_low_battery_blocks_commands(self, interlock):
        """Test low battery blocks non-emergency commands."""
        interlock.update_weather_status(True)
        interlock.update_enclosure_status(True)
        interlock.update_power_status(10.0)

        status = interlock.check_command(CommandType.SLEW)
        assert status.is_allowed is False

    def test_on_battery_warning(self, interlock):
        """Test on-battery adds warning."""
        interlock.update_weather_status(True)
        interlock.update_enclosure_status(True)
        interlock.update_power_status(80.0, on_battery=True)

        status = interlock.check_command(CommandType.SLEW)
        assert status.is_allowed is True
        assert any("battery" in w.lower() for w in status.warnings)


class TestVetoHistory:
    """Tests for veto history tracking."""

    @pytest.fixture
    def interlock(self):
        """Create interlock for testing."""
        return SafetyInterlock()

    def test_vetoes_recorded(self, interlock):
        """Test vetoes are recorded in history."""
        interlock.update_weather_status(False)

        # This should create a veto
        interlock.check_command(CommandType.SLEW)

        history = interlock.get_veto_history()
        assert len(history) > 0
        assert history[0]["command"] == "slew"

    def test_history_limit(self, interlock):
        """Test history respects limit."""
        interlock.update_weather_status(False)

        # Create many vetoes
        for _ in range(100):
            interlock.check_command(CommandType.SLEW)

        # Request limited history
        history = interlock.get_veto_history(limit=10)
        assert len(history) == 10

    def test_clear_history(self, interlock):
        """Test history can be cleared."""
        interlock.update_weather_status(False)
        interlock.check_command(CommandType.SLEW)

        interlock.clear_veto_history()
        history = interlock.get_veto_history()
        assert len(history) == 0


class TestIsSafeForObservation:
    """Tests for quick safety check."""

    @pytest.fixture
    def interlock(self):
        """Create interlock for testing."""
        return SafetyInterlock()

    def test_all_safe_returns_true(self, interlock):
        """Test returns true when all conditions safe."""
        interlock.update_weather_status(True)
        interlock.update_enclosure_status(True)
        interlock.update_power_status(100.0)

        assert interlock.is_safe_for_observation() is True

    def test_unsafe_weather_returns_false(self, interlock):
        """Test returns false with unsafe weather."""
        interlock.update_weather_status(False)
        interlock.update_enclosure_status(True)

        assert interlock.is_safe_for_observation() is False

    def test_closed_enclosure_returns_false(self, interlock):
        """Test returns false with closed enclosure."""
        interlock.update_weather_status(True)
        interlock.update_enclosure_status(False)

        assert interlock.is_safe_for_observation() is False

    def test_low_battery_returns_false(self, interlock):
        """Test returns false with low battery."""
        interlock.update_weather_status(True)
        interlock.update_power_status(10.0)

        assert interlock.is_safe_for_observation() is False


class TestSafetyInterlockError:
    """Tests for SafetyInterlockError."""

    def test_error_message(self):
        """Test error contains message."""
        error = SafetyInterlockError("Test error")
        assert str(error) == "Test error"

    def test_error_with_status(self):
        """Test error with interlock status."""
        status = InterlockStatus(
            result=SafetyCheckResult.BLOCKED,
            vetoes=[SafetyVeto(
                command=CommandType.SLEW,
                reason="Test reason",
                check_name="test",
            )],
        )
        error = SafetyInterlockError("Blocked", status=status)

        assert error.status == status
        assert "Test reason" in error.spoken_response


class TestCreateSafetyInterlock:
    """Tests for factory function."""

    def test_create_basic(self):
        """Test basic creation."""
        interlock = create_safety_interlock()
        assert interlock is not None
        assert isinstance(interlock, SafetyInterlock)

    def test_create_with_options(self):
        """Test creation with options."""
        interlock = create_safety_interlock(
            altitude_limit_deg=15.0,
            min_battery_percent=30.0,
        )

        assert interlock.altitude_limit_deg == 15.0
        assert interlock.min_battery_percent == 30.0
