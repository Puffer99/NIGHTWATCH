"""
Unit tests for NIGHTWATCH enclosure/roof controller.

Tests GPIO interface, roof state machine, safety interlocks, and emergency stop.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from services.enclosure.roof_controller import (
    GPIOInterface,
    GPIOBackend,
    RoofController,
    RoofConfig,
    RoofState,
    RoofStatus,
    SafetyCondition,
)


class TestGPIOBackend:
    """Tests for GPIOBackend enum."""

    def test_backends_exist(self):
        """Test all GPIO backends exist."""
        assert GPIOBackend.MOCK.value == "mock"
        assert GPIOBackend.RPIGPIO.value == "rpigpio"
        assert GPIOBackend.GPIOZERO.value == "gpiozero"


class TestGPIOInterface:
    """Tests for GPIO interface abstraction."""

    @pytest.fixture
    def gpio(self):
        """Create mock GPIO interface."""
        return GPIOInterface(backend=GPIOBackend.MOCK)

    def test_initialization(self, gpio):
        """Test GPIO interface initialization."""
        assert gpio.backend == GPIOBackend.MOCK
        assert not gpio._initialized

    def test_initialize_mock(self, gpio):
        """Test initializing mock backend."""
        result = gpio.initialize()

        assert result is True
        assert gpio._initialized is True
        assert gpio._gpio is not None

    def test_initialize_idempotent(self, gpio):
        """Test initialize can be called multiple times."""
        gpio.initialize()
        gpio.initialize()

        assert gpio._initialized is True

    def test_cleanup(self, gpio):
        """Test GPIO cleanup."""
        gpio.initialize()
        gpio.cleanup()

        assert gpio._initialized is False

    def test_cleanup_without_init(self, gpio):
        """Test cleanup without initialization is safe."""
        gpio.cleanup()  # Should not raise

    def test_motor_open_relay(self, gpio):
        """Test motor open relay control."""
        gpio.initialize()

        gpio.set_motor_open_relay(True)
        assert gpio._gpio["motor_open"] is True

        gpio.set_motor_open_relay(False)
        assert gpio._gpio["motor_open"] is False

    def test_motor_close_relay(self, gpio):
        """Test motor close relay control."""
        gpio.initialize()

        gpio.set_motor_close_relay(True)
        assert gpio._gpio["motor_close"] is True

        gpio.set_motor_close_relay(False)
        assert gpio._gpio["motor_close"] is False

    def test_stop_motor(self, gpio):
        """Test stopping motor deactivates both relays."""
        gpio.initialize()
        gpio._gpio["motor_open"] = True
        gpio._gpio["motor_close"] = True

        gpio.stop_motor()

        assert gpio._gpio["motor_open"] is False
        assert gpio._gpio["motor_close"] is False

    def test_read_open_limit(self, gpio):
        """Test reading open limit switch."""
        gpio.initialize()
        gpio._gpio["open_limit"] = True

        assert gpio.read_open_limit() is True

        gpio._gpio["open_limit"] = False
        assert gpio.read_open_limit() is False

    def test_read_closed_limit(self, gpio):
        """Test reading closed limit switch."""
        gpio.initialize()

        # Mock starts with closed_limit = True
        assert gpio.read_closed_limit() is True

    def test_read_rain_sensor(self, gpio):
        """Test reading rain sensor."""
        gpio.initialize()
        gpio._gpio["rain_sensor"] = False

        assert gpio.read_rain_sensor() is False

        gpio._gpio["rain_sensor"] = True
        assert gpio.read_rain_sensor() is True

    def test_mock_set_open_limit(self, gpio):
        """Test setting mock open limit for testing."""
        gpio.initialize()

        gpio.mock_set_open_limit(True)
        assert gpio._gpio["open_limit"] is True

        gpio.mock_set_open_limit(False)
        assert gpio._gpio["open_limit"] is False

    def test_mock_set_closed_limit(self, gpio):
        """Test setting mock closed limit for testing."""
        gpio.initialize()

        gpio.mock_set_closed_limit(False)
        assert gpio._gpio["closed_limit"] is False

    def test_mock_set_rain_sensor(self, gpio):
        """Test setting mock rain sensor for testing."""
        gpio.initialize()

        gpio.mock_set_rain_sensor(True)
        assert gpio._gpio["rain_sensor"] is True

    def test_relay_without_init_is_safe(self, gpio):
        """Test relay control without init doesn't crash."""
        # Should not raise
        gpio.set_motor_open_relay(True)
        gpio.set_motor_close_relay(True)

    def test_read_without_init_returns_false(self, gpio):
        """Test reading without init returns False."""
        assert gpio.read_open_limit() is False
        assert gpio.read_closed_limit() is False
        assert gpio.read_rain_sensor() is False


class TestRoofState:
    """Tests for RoofState enum."""

    def test_roof_states_exist(self):
        """Test all roof states exist."""
        assert RoofState.OPEN.value == "open"
        assert RoofState.CLOSED.value == "closed"
        assert RoofState.OPENING.value == "opening"
        assert RoofState.CLOSING.value == "closing"
        assert RoofState.UNKNOWN.value == "unknown"
        assert RoofState.ERROR.value == "error"


class TestSafetyCondition:
    """Tests for SafetyCondition enum."""

    def test_safety_conditions_exist(self):
        """Test all safety conditions exist."""
        assert SafetyCondition.WEATHER_SAFE.value == "weather_safe"
        assert SafetyCondition.TELESCOPE_PARKED.value == "telescope_parked"
        assert SafetyCondition.RAIN_HOLDOFF.value == "rain_holdoff"
        assert SafetyCondition.POWER_OK.value == "power_ok"
        assert SafetyCondition.HARDWARE_INTERLOCK.value == "hardware_interlock"


class TestRoofConfig:
    """Tests for RoofConfig dataclass."""

    def test_default_config(self):
        """Test default roof configuration."""
        config = RoofConfig()

        assert config.motor_timeout_sec == 60.0
        assert config.rain_holdoff_min == 30.0
        assert config.use_hardware_interlock is True
        assert config.max_position == 100

    def test_custom_config(self):
        """Test custom roof configuration."""
        config = RoofConfig(
            motor_timeout_sec=90.0,
            rain_holdoff_min=45.0,
            invert_motor=True,
        )

        assert config.motor_timeout_sec == 90.0
        assert config.rain_holdoff_min == 45.0
        assert config.invert_motor is True


class TestRoofStatus:
    """Tests for RoofStatus dataclass."""

    def test_default_status(self):
        """Test default roof status."""
        status = RoofStatus(state=RoofState.CLOSED)

        assert status.state == RoofState.CLOSED
        assert status.position_percent == 0
        assert status.can_close is True

    def test_status_with_values(self):
        """Test roof status with custom values."""
        status = RoofStatus(
            state=RoofState.OPEN,
            position_percent=100,
            open_limit=True,
            closed_limit=False,
            can_open=False,
            motor_running=False,
        )

        assert status.state == RoofState.OPEN
        assert status.position_percent == 100
        assert status.open_limit is True


class TestRoofController:
    """Tests for RoofController class."""

    @pytest.fixture
    def controller(self):
        """Create roof controller without services."""
        config = RoofConfig()
        return RoofController(config)

    @pytest.fixture
    def controller_with_mocks(self):
        """Create roof controller with mock services."""
        config = RoofConfig()
        mock_weather = MagicMock()
        mock_weather.is_safe = MagicMock(return_value=True)
        mock_mount = MagicMock()
        mock_mount.is_parked = True

        controller = RoofController(
            config,
            weather_service=mock_weather,
            mount_service=mock_mount,
        )
        return controller, mock_weather, mock_mount

    def test_initialization(self, controller):
        """Test roof controller initialization."""
        assert controller.config is not None
        assert controller._state == RoofState.UNKNOWN
        assert controller._connected is False

    def test_connected_property(self, controller):
        """Test connected property."""
        assert controller.connected is False

    def test_state_property(self, controller):
        """Test state property."""
        controller._state = RoofState.CLOSED
        assert controller.state == RoofState.CLOSED

    def test_is_open_property(self, controller):
        """Test is_open property."""
        controller._state = RoofState.OPEN
        assert controller.is_open is True

        controller._state = RoofState.CLOSED
        assert controller.is_open is False

    def test_is_closed_property(self, controller):
        """Test is_closed property."""
        controller._state = RoofState.CLOSED
        assert controller.is_closed is True

        controller._state = RoofState.OPEN
        assert controller.is_closed is False

    def test_status_property(self, controller):
        """Test status property returns RoofStatus."""
        status = controller.status

        assert isinstance(status, RoofStatus)
        assert status.state == RoofState.UNKNOWN

    def test_can_open_all_conditions_met(self, controller):
        """Test _can_open when all conditions met."""
        # Set all safety conditions to True
        for condition in SafetyCondition:
            controller._safety[condition] = True

        assert controller._can_open() is True

    def test_can_open_weather_unsafe(self, controller):
        """Test _can_open when weather unsafe."""
        for condition in SafetyCondition:
            controller._safety[condition] = True
        controller._safety[SafetyCondition.WEATHER_SAFE] = False

        assert controller._can_open() is False

    def test_can_open_telescope_not_parked(self, controller):
        """Test _can_open when telescope not parked."""
        for condition in SafetyCondition:
            controller._safety[condition] = True
        controller._safety[SafetyCondition.TELESCOPE_PARKED] = False

        assert controller._can_open() is False

    def test_can_open_emergency_stop_active(self, controller):
        """Test _can_open when emergency stop is active."""
        for condition in SafetyCondition:
            controller._safety[condition] = True
        controller._emergency_stop_active = True

        assert controller._can_open() is False

    def test_status_can_close_always_true(self, controller):
        """Test status can_close is always true (safety close)."""
        status = controller.status
        assert status.can_close is True


class TestRoofControllerSafety:
    """Tests for roof controller safety features."""

    @pytest.fixture
    def controller(self):
        """Create roof controller."""
        return RoofController(RoofConfig())

    def test_initial_safety_conditions(self, controller):
        """Test initial safety condition values."""
        assert controller._safety[SafetyCondition.WEATHER_SAFE] is False
        assert controller._safety[SafetyCondition.TELESCOPE_PARKED] is False
        assert controller._safety[SafetyCondition.RAIN_HOLDOFF] is True
        assert controller._safety[SafetyCondition.POWER_OK] is True

    def test_safety_conditions_in_status(self, controller):
        """Test safety conditions are included in status."""
        controller._safety[SafetyCondition.WEATHER_SAFE] = True

        status = controller.status
        assert SafetyCondition.WEATHER_SAFE in status.safety_conditions
        assert status.safety_conditions[SafetyCondition.WEATHER_SAFE] is True

    def test_emergency_stop_flag(self, controller):
        """Test emergency stop flag."""
        assert controller._emergency_stop_active is False

        controller._emergency_stop_active = True
        assert controller._can_open() is False


class TestRoofControllerCallbacks:
    """Tests for roof controller callback system."""

    @pytest.fixture
    def controller(self):
        """Create roof controller."""
        return RoofController(RoofConfig())

    def test_callback_registration(self, controller):
        """Test registering callbacks."""
        callback = MagicMock()
        controller._callbacks.append(callback)

        assert callback in controller._callbacks

    def test_status_callback_structure(self, controller):
        """Test status callback dictionary structure."""
        assert "opening" in controller._status_callbacks
        assert "open" in controller._status_callbacks
        assert "closing" in controller._status_callbacks
        assert "closed" in controller._status_callbacks
        assert "error" in controller._status_callbacks
        assert "emergency_stop" in controller._status_callbacks


class TestRoofControllerMotion:
    """Tests for roof controller motion states."""

    @pytest.fixture
    def controller(self):
        """Create roof controller."""
        return RoofController(RoofConfig())

    def test_motor_running_flag(self, controller):
        """Test motor running flag in status."""
        controller._motor_running = True

        status = controller.status
        assert status.motor_running is True

    def test_position_tracking(self, controller):
        """Test position percent tracking."""
        controller._position = 50

        status = controller.status
        assert status.position_percent == 50

    def test_state_transitions(self, controller):
        """Test basic state transitions."""
        controller._state = RoofState.CLOSED
        assert controller.is_closed is True

        controller._state = RoofState.OPENING
        assert controller.is_closed is False
        assert controller.is_open is False

        controller._state = RoofState.OPEN
        assert controller.is_open is True


class TestRoofControllerConfig:
    """Tests for roof controller configuration options."""

    def test_motor_timeout_config(self):
        """Test motor timeout configuration."""
        config = RoofConfig(motor_timeout_sec=120.0)
        controller = RoofController(config)

        assert controller.config.motor_timeout_sec == 120.0

    def test_rain_holdoff_config(self):
        """Test rain holdoff configuration."""
        config = RoofConfig(rain_holdoff_min=60.0)
        controller = RoofController(config)

        assert controller.config.rain_holdoff_min == 60.0

    def test_hardware_interlock_config(self):
        """Test hardware interlock configuration."""
        config = RoofConfig(use_hardware_interlock=False)
        controller = RoofController(config)

        assert controller.config.use_hardware_interlock is False

    def test_position_limits_config(self):
        """Test position limits configuration."""
        config = RoofConfig(max_position=200, open_position=200)
        controller = RoofController(config)

        assert controller.config.max_position == 200
        assert controller.config.open_position == 200
