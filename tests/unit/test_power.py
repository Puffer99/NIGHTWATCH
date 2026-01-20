"""
Unit tests for NIGHTWATCH power management service.

Tests NUT client, UPS monitoring, power events, and PDU control.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from services.power.power_manager import (
    NUTClient,
    PowerManager,
    PowerConfig,
    PowerState,
    ShutdownReason,
    UPSStatus,
    PowerEvent,
)


class TestNUTClient:
    """Tests for NUT protocol client."""

    def test_client_initialization(self):
        """Test NUT client creation with defaults."""
        client = NUTClient()

        assert client.host == "localhost"
        assert client.port == 3493
        assert client.timeout == 10.0
        assert client._socket is None

    def test_client_custom_config(self):
        """Test NUT client with custom configuration."""
        client = NUTClient(host="192.168.1.100", port=3500, timeout=5.0)

        assert client.host == "192.168.1.100"
        assert client.port == 3500
        assert client.timeout == 5.0

    def test_connect_failure_returns_false(self):
        """Test connection failure returns False."""
        client = NUTClient(host="nonexistent.local", timeout=0.1)
        result = client.connect()

        assert result is False
        assert client._socket is None

    def test_disconnect_without_connection(self):
        """Test disconnect when not connected is safe."""
        client = NUTClient()
        # Should not raise
        client.disconnect()
        assert client._socket is None


class TestPowerConfig:
    """Tests for PowerConfig dataclass."""

    def test_default_config(self):
        """Test default power configuration."""
        config = PowerConfig()

        assert config.ups_name == "ups"
        assert config.nut_host == "localhost"
        assert config.nut_port == 3493
        assert config.park_threshold_pct == 50
        assert config.emergency_threshold_pct == 20
        assert config.resume_threshold_pct == 80

    def test_custom_config(self):
        """Test custom power configuration."""
        config = PowerConfig(
            ups_name="myups",
            park_threshold_pct=60,
            emergency_threshold_pct=25,
            power_restore_delay_sec=600.0,
        )

        assert config.ups_name == "myups"
        assert config.park_threshold_pct == 60
        assert config.emergency_threshold_pct == 25
        assert config.power_restore_delay_sec == 600.0


class TestPowerState:
    """Tests for PowerState enum."""

    def test_power_states_exist(self):
        """Test all expected power states exist."""
        assert PowerState.ONLINE.value == "online"
        assert PowerState.ON_BATTERY.value == "on_battery"
        assert PowerState.LOW_BATTERY.value == "low_battery"
        assert PowerState.CHARGING.value == "charging"
        assert PowerState.UNKNOWN.value == "unknown"


class TestShutdownReason:
    """Tests for ShutdownReason enum."""

    def test_shutdown_reasons_exist(self):
        """Test all shutdown reasons exist."""
        assert ShutdownReason.LOW_BATTERY.value == "low_battery"
        assert ShutdownReason.POWER_FAILURE.value == "power_failure"
        assert ShutdownReason.UPS_FAILURE.value == "ups_failure"
        assert ShutdownReason.USER_REQUEST.value == "user_request"
        assert ShutdownReason.SCHEDULED.value == "scheduled"


class TestUPSStatus:
    """Tests for UPSStatus dataclass."""

    def test_default_status(self):
        """Test default UPS status values."""
        status = UPSStatus()

        assert status.state == PowerState.UNKNOWN
        assert status.battery_percent == 100
        assert status.on_mains is True
        assert status.battery_low is False

    def test_status_with_values(self):
        """Test UPS status with custom values."""
        status = UPSStatus(
            state=PowerState.ON_BATTERY,
            battery_percent=75,
            battery_runtime_sec=1800,
            on_mains=False,
        )

        assert status.state == PowerState.ON_BATTERY
        assert status.battery_percent == 75
        assert status.battery_runtime_sec == 1800
        assert status.on_mains is False

    def test_runtime_minutes_property(self):
        """Test runtime conversion to minutes."""
        status = UPSStatus(battery_runtime_sec=3600)

        assert status.runtime_minutes == 60.0


class TestPowerEvent:
    """Tests for PowerEvent dataclass."""

    def test_power_event_creation(self):
        """Test creating a power event."""
        event = PowerEvent(
            timestamp=datetime.now(),
            event_type="POWER_LOST",
            description="Mains power lost",
            battery_percent=95,
            on_mains=False,
        )

        assert event.event_type == "POWER_LOST"
        assert event.description == "Mains power lost"
        assert event.battery_percent == 95
        assert event.on_mains is False


class TestPowerManager:
    """Tests for PowerManager class."""

    @pytest.fixture
    def manager(self):
        """Create power manager with simulation mode."""
        config = PowerConfig()
        mgr = PowerManager(config)
        mgr._use_simulation = True
        return mgr

    @pytest.fixture
    def manager_with_mocks(self):
        """Create power manager with mock controllers."""
        config = PowerConfig()
        mock_mount = MagicMock()
        mock_mount.park = AsyncMock()
        mock_roof = MagicMock()
        mock_roof.close = AsyncMock()

        mgr = PowerManager(
            config,
            roof_controller=mock_roof,
            mount_controller=mock_mount,
        )
        mgr._use_simulation = True
        return mgr, mock_mount, mock_roof

    def test_manager_initialization(self, manager):
        """Test power manager initialization."""
        assert manager.config is not None
        assert manager._running is False
        assert manager._use_simulation is True

    def test_status_property(self, manager):
        """Test status property returns UPSStatus."""
        status = manager.status

        assert isinstance(status, UPSStatus)

    def test_event_log_property(self, manager):
        """Test event log returns copy."""
        # Add an event
        manager._log_event("TEST", "Test event")

        log1 = manager.event_log
        log2 = manager.event_log

        assert log1 == log2
        assert log1 is not manager._event_log  # Returns copy

    @pytest.mark.asyncio
    async def test_start_and_stop(self, manager):
        """Test starting and stopping power manager."""
        await manager.start()

        assert manager._running is True
        assert manager._monitor_task is not None

        await manager.stop()

        assert manager._running is False

    @pytest.mark.asyncio
    async def test_query_nut_simulation(self, manager):
        """Test querying NUT in simulation mode."""
        status = await manager._query_nut()

        assert isinstance(status, UPSStatus)
        assert status.battery_percent == 100
        assert status.on_mains is True

    def test_log_event(self, manager):
        """Test logging power events."""
        manager._log_event("POWER_LOST", "Test power loss")

        assert len(manager._event_log) == 1
        assert manager._event_log[0].event_type == "POWER_LOST"
        assert manager._event_log[0].description == "Test power loss"

    def test_log_event_limit(self, manager):
        """Test event log size limit."""
        # Add more than 1000 events
        for i in range(1100):
            manager._log_event("TEST", f"Event {i}")

        assert len(manager._event_log) == 1000

    def test_get_events_since(self, manager):
        """Test filtering events by time."""
        past = datetime.now() - timedelta(hours=1)
        manager._log_event("OLD", "Old event")
        manager._event_log[0].timestamp = past

        manager._log_event("NEW", "New event")

        since = datetime.now() - timedelta(minutes=30)
        recent = manager.get_events_since(since)

        assert len(recent) == 1
        assert recent[0].event_type == "NEW"

    @pytest.mark.asyncio
    async def test_callback_registration(self, manager):
        """Test registering and notifying callbacks."""
        callback_called = []

        async def callback(event, data):
            callback_called.append((event, data))

        manager.register_callback(callback)
        await manager._notify_callbacks("test_event", {"key": "value"})

        assert len(callback_called) == 1
        assert callback_called[0][0] == "test_event"
        assert callback_called[0][1] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_sync_callback(self, manager):
        """Test sync callback is called."""
        callback_called = []

        def sync_callback(event, data):
            callback_called.append(event)

        manager.register_callback(sync_callback)
        await manager._notify_callbacks("sync_test")

        assert "sync_test" in callback_called


class TestPowerManagerPDU:
    """Tests for PDU port control with confirmation."""

    @pytest.fixture
    def manager(self):
        """Create power manager."""
        config = PowerConfig()
        mgr = PowerManager(config)
        mgr._use_simulation = True
        return mgr

    @pytest.mark.asyncio
    async def test_set_port_requires_confirmation(self, manager):
        """Test that port power change requires confirmation."""
        result = await manager.set_port_power(1, True)

        assert result["success"] is False
        assert result["requires_confirmation"] is True
        assert result["port"] == 1

    @pytest.mark.asyncio
    async def test_set_port_with_confirmation(self, manager):
        """Test port power change with confirmation."""
        result = await manager.set_port_power(1, True, confirmed=True)

        assert result["success"] is True
        assert result["requires_confirmation"] is False
        assert result["action"] == "ON"

    @pytest.mark.asyncio
    async def test_set_port_with_confirmation_code(self, manager):
        """Test port power change with confirmation code."""
        result = await manager.set_port_power(
            2, False, confirmation_code="NIGHTWATCH_POWER_CONFIRM"
        )

        assert result["success"] is True
        assert result["action"] == "OFF"

    @pytest.mark.asyncio
    async def test_power_cycle_requires_confirmation(self, manager):
        """Test that power cycle requires confirmation."""
        result = await manager.power_cycle_port(1)

        assert result["success"] is False
        assert result["requires_confirmation"] is True

    @pytest.mark.asyncio
    async def test_power_cycle_with_confirmation(self, manager):
        """Test power cycle with confirmation."""
        result = await manager.power_cycle_port(1, delay_sec=0.1, confirmed=True)

        assert result["success"] is True
        assert result["port"] == 1


class TestPowerManagerEmergency:
    """Tests for emergency power handling."""

    @pytest.fixture
    def manager_with_mocks(self):
        """Create manager with mock controllers."""
        config = PowerConfig(
            park_threshold_pct=50,
            emergency_threshold_pct=20,
        )
        mock_mount = MagicMock()
        mock_mount.park = AsyncMock()
        mock_roof = MagicMock()
        mock_roof.close = AsyncMock()
        mock_alerts = MagicMock()
        mock_alerts.raise_alert = AsyncMock()

        mgr = PowerManager(
            config,
            roof_controller=mock_roof,
            mount_controller=mock_mount,
            alert_manager=mock_alerts,
        )
        mgr._use_simulation = True
        return mgr, mock_mount, mock_roof, mock_alerts

    @pytest.mark.asyncio
    async def test_on_power_lost(self, manager_with_mocks):
        """Test power lost event handling."""
        manager, mock_mount, mock_roof, mock_alerts = manager_with_mocks

        await manager._on_power_lost()

        assert manager._power_lost_time is not None
        assert manager._status.state == PowerState.ON_BATTERY
        assert len(manager._event_log) == 1
        assert manager._event_log[0].event_type == "POWER_LOST"

    @pytest.mark.asyncio
    async def test_initiate_park(self, manager_with_mocks):
        """Test park initiation on low battery."""
        manager, mock_mount, mock_roof, mock_alerts = manager_with_mocks

        await manager._initiate_park()

        assert manager._park_initiated is True
        mock_mount.park.assert_called_once()

    @pytest.mark.asyncio
    async def test_simulate_power_failure(self, manager_with_mocks):
        """Test simulated power failure."""
        manager, mock_mount, mock_roof, mock_alerts = manager_with_mocks

        # Use short duration for test
        task = asyncio.create_task(manager.simulate_power_failure(0.1))
        await asyncio.sleep(0.05)

        # Should be on battery during simulation
        assert manager._was_on_mains is False

        await task

        # Should be back on mains after simulation
        assert manager._was_on_mains is True


class TestPowerManagerStateTransitions:
    """Tests for power state transitions."""

    @pytest.fixture
    def manager(self):
        """Create power manager."""
        config = PowerConfig()
        mgr = PowerManager(config)
        mgr._use_simulation = True
        return mgr

    @pytest.mark.asyncio
    async def test_process_status_mains_to_battery(self, manager):
        """Test transition from mains to battery."""
        manager._was_on_mains = True
        manager._status = UPSStatus(
            state=PowerState.ON_BATTERY,
            on_mains=False,
            battery_percent=90,
        )

        with patch.object(manager, '_on_power_lost', new_callable=AsyncMock) as mock:
            await manager._process_status()
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_status_battery_to_mains(self, manager):
        """Test transition from battery to mains."""
        manager._was_on_mains = False
        manager._status = UPSStatus(
            state=PowerState.ONLINE,
            on_mains=True,
            battery_percent=95,
        )

        with patch.object(manager, '_on_power_restored', new_callable=AsyncMock) as mock:
            await manager._process_status()
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_status_low_battery_triggers_park(self, manager):
        """Test low battery triggers park."""
        manager._was_on_mains = False
        manager._status = UPSStatus(
            state=PowerState.ON_BATTERY,
            on_mains=False,
            battery_percent=45,  # Below 50% threshold
        )
        manager._park_initiated = False

        with patch.object(manager, '_initiate_park', new_callable=AsyncMock) as mock:
            await manager._process_status()
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_status_critical_battery_triggers_shutdown(self, manager):
        """Test critical battery triggers emergency shutdown."""
        manager._was_on_mains = False
        manager._status = UPSStatus(
            state=PowerState.ON_BATTERY,
            on_mains=False,
            battery_percent=15,  # Below 20% emergency threshold
        )
        manager._shutdown_initiated = False

        with patch.object(manager, '_emergency_shutdown', new_callable=AsyncMock) as mock:
            await manager._process_status()
            mock.assert_called_once()
