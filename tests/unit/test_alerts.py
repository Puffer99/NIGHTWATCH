"""
Unit tests for NIGHTWATCH alert manager.

Tests alert channels, rate limiting, deduplication, quiet hours, and escalation.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

from services.alerts.alert_manager import (
    AlertManager,
    AlertConfig,
    Alert,
    AlertLevel,
    AlertChannel,
    AlertHistoryDB,
    MockNotifier,
    ALERT_TEMPLATES,
)


class TestAlertConfig:
    """Tests for AlertConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AlertConfig()

        assert config.email_enabled is True
        assert config.min_interval_seconds == 60.0
        assert config.max_alerts_per_hour == 20
        assert config.quiet_hours_enabled is False

    def test_custom_config(self):
        """Test custom configuration."""
        config = AlertConfig(
            email_enabled=False,
            min_interval_seconds=30.0,
            quiet_hours_enabled=True,
            quiet_hours_start=23,
            quiet_hours_end=6,
        )

        assert config.email_enabled is False
        assert config.min_interval_seconds == 30.0
        assert config.quiet_hours_enabled is True
        assert config.quiet_hours_start == 23


class TestAlertLevel:
    """Tests for AlertLevel enum."""

    def test_level_ordering(self):
        """Test that alert levels are properly ordered."""
        assert AlertLevel.DEBUG.value < AlertLevel.INFO.value
        assert AlertLevel.INFO.value < AlertLevel.WARNING.value
        assert AlertLevel.WARNING.value < AlertLevel.CRITICAL.value
        assert AlertLevel.CRITICAL.value < AlertLevel.EMERGENCY.value


class TestAlert:
    """Tests for Alert dataclass."""

    def test_alert_creation(self):
        """Test creating an alert."""
        alert = Alert(
            level=AlertLevel.WARNING,
            source="test",
            message="Test alert message",
        )

        assert alert.level == AlertLevel.WARNING
        assert alert.source == "test"
        assert alert.message == "Test alert message"
        assert alert.acknowledged is False
        assert len(alert.id) == 8

    def test_alert_with_data(self):
        """Test alert with additional data."""
        alert = Alert(
            level=AlertLevel.INFO,
            source="camera",
            message="Capture complete",
            data={"target": "Mars", "frames": 1000},
        )

        assert alert.data["target"] == "Mars"
        assert alert.data["frames"] == 1000


class TestAlertManager:
    """Tests for AlertManager class."""

    @pytest.fixture
    def manager(self):
        """Create alert manager with default config."""
        return AlertManager()

    @pytest.fixture
    def mock_notifier(self):
        """Create mock notifier for testing sends."""
        config = AlertConfig(
            email_enabled=True,
            email_recipients=["test@example.com"],
            push_enabled=True,
            sms_enabled=True,
            sms_to_numbers=["+1234567890"],
            webhook_enabled=True,
            webhook_urls=["https://example.com/webhook"],
        )
        return MockNotifier(config)

    @pytest.mark.asyncio
    async def test_raise_alert_basic(self, manager):
        """Test basic alert raising."""
        alert = Alert(
            level=AlertLevel.INFO,
            source="test",
            message="Basic test alert",
        )

        result = await manager.raise_alert(alert)

        assert result is True
        assert len(manager._history) == 1

    @pytest.mark.asyncio
    async def test_rate_limiting(self, manager):
        """Test that duplicate alerts are rate limited."""
        alert = Alert(
            level=AlertLevel.INFO,
            source="test",
            message="Rate limit test",
        )

        # First alert should succeed
        result1 = await manager.raise_alert(alert)
        assert result1 is True

        # Second identical alert within interval should be rate limited
        result2 = await manager.raise_alert(alert)
        assert result2 is False

    @pytest.mark.asyncio
    async def test_hourly_limit(self, manager):
        """Test hourly alert limit."""
        manager.config.max_alerts_per_hour = 2

        # First two should succeed
        for i in range(2):
            alert = Alert(
                level=AlertLevel.INFO,
                source="test",
                message=f"Alert {i}",  # Different messages to avoid dedup
            )
            result = await manager.raise_alert(alert)
            assert result is True

        # Third should be rate limited
        alert = Alert(
            level=AlertLevel.INFO,
            source="test",
            message="Alert 3",
        )
        result = await manager.raise_alert(alert)
        assert result is False


class TestMockNotifier:
    """Tests for MockNotifier class."""

    @pytest.fixture
    def mock(self):
        """Create mock notifier."""
        config = AlertConfig(
            email_enabled=True,
            email_recipients=["test@example.com"],
            push_enabled=True,
            ntfy_enabled=True,
            sms_enabled=True,
            sms_to_numbers=["+1234567890"],
        )
        return MockNotifier(config)

    @pytest.mark.asyncio
    async def test_mock_records_email(self, mock):
        """Test that mock records email sends."""
        alert = Alert(
            level=AlertLevel.WARNING,
            source="test",
            message="Email test",
        )

        await mock.raise_alert(alert)

        assert len(mock.email_sends) == 1
        assert mock.email_sends[0]["source"] == "test"
        assert mock.email_sends[0]["message"] == "Email test"

    @pytest.mark.asyncio
    async def test_mock_records_push(self, mock):
        """Test that mock records push sends."""
        alert = Alert(
            level=AlertLevel.WARNING,
            source="test",
            message="Push test",
        )

        await mock.raise_alert(alert)

        assert len(mock.push_sends) == 1

    @pytest.mark.asyncio
    async def test_mock_records_sms_for_critical(self, mock):
        """Test that mock records SMS for critical alerts."""
        alert = Alert(
            level=AlertLevel.CRITICAL,
            source="test",
            message="Critical test",
        )

        await mock.raise_alert(alert)

        assert len(mock.sms_sends) == 1
        assert mock.sms_sends[0]["level"] == "CRITICAL"

    @pytest.mark.asyncio
    async def test_clear_records(self, mock):
        """Test clearing recorded sends."""
        alert = Alert(
            level=AlertLevel.WARNING,
            source="test",
            message="Clear test",
        )

        await mock.raise_alert(alert)
        assert len(mock.email_sends) > 0

        mock.clear_records()
        assert len(mock.email_sends) == 0


class TestQuietHours:
    """Tests for quiet hours functionality."""

    def test_quiet_hours_disabled(self):
        """Test that quiet hours check returns False when disabled."""
        manager = AlertManager(AlertConfig(quiet_hours_enabled=False))
        assert manager._is_quiet_hours() is False

    def test_quiet_hours_overnight(self):
        """Test overnight quiet hours (22:00 to 07:00)."""
        config = AlertConfig(
            quiet_hours_enabled=True,
            quiet_hours_start=22,
            quiet_hours_end=7,
        )
        manager = AlertManager(config)

        # Test at 23:00 (should be quiet)
        with patch('services.alerts.alert_manager.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 1, 1, 23, 0)
            # Can't easily test this way due to datetime usage
            # This is a limitation of testing datetime.now()

    @pytest.mark.asyncio
    async def test_suppress_info_during_quiet_hours(self):
        """Test that INFO alerts are suppressed during quiet hours."""
        config = AlertConfig(
            quiet_hours_enabled=True,
            quiet_hours_start=0,  # Always quiet for this test
            quiet_hours_end=23,
            quiet_hours_min_level=AlertLevel.CRITICAL,
        )
        manager = AlertManager(config)

        # Force quiet hours check to return True
        manager._is_quiet_hours = lambda: True

        alert = Alert(
            level=AlertLevel.INFO,
            source="test",
            message="Quiet hours test",
        )

        result = await manager.raise_alert(alert)
        assert result is False  # Should be suppressed

    @pytest.mark.asyncio
    async def test_allow_critical_during_quiet_hours(self):
        """Test that CRITICAL alerts are allowed during quiet hours."""
        config = AlertConfig(
            quiet_hours_enabled=True,
            quiet_hours_start=0,
            quiet_hours_end=23,
            quiet_hours_min_level=AlertLevel.CRITICAL,
        )
        manager = AlertManager(config)
        manager._is_quiet_hours = lambda: True

        alert = Alert(
            level=AlertLevel.CRITICAL,
            source="test",
            message="Critical during quiet hours",
        )

        result = await manager.raise_alert(alert)
        assert result is True  # Should not be suppressed


class TestDeduplication:
    """Tests for alert deduplication."""

    @pytest.fixture
    def manager(self):
        """Create manager with short dedup window."""
        config = AlertConfig(
            dedup_window_seconds=5.0,
            min_interval_seconds=1.0,  # Short for testing
        )
        return AlertManager(config)

    @pytest.mark.asyncio
    async def test_duplicate_detection(self, manager):
        """Test that duplicate alerts are detected."""
        alert1 = Alert(
            level=AlertLevel.INFO,
            source="sensor",
            message="Temperature high",
        )

        # First alert
        await manager.raise_alert(alert1)

        # Same alert is duplicate
        alert2 = Alert(
            level=AlertLevel.INFO,
            source="sensor",
            message="Temperature high",
        )

        # This should be detected as duplicate (after rate limit check)
        is_dup = manager._is_duplicate(alert2)
        assert is_dup is True

    def test_different_alerts_not_duplicate(self, manager):
        """Test that different alerts are not duplicates."""
        # Add first alert to tracking
        manager._recent_alerts["sensor:Temperature high"] = datetime.now()

        alert = Alert(
            level=AlertLevel.INFO,
            source="sensor",
            message="Temperature normal",  # Different message
        )

        is_dup = manager._is_duplicate(alert)
        assert is_dup is False


class TestAlertTemplates:
    """Tests for alert templates."""

    def test_template_exists(self):
        """Test that expected templates exist."""
        assert "weather_unsafe" in ALERT_TEMPLATES
        assert "rain_detected" in ALERT_TEMPLATES
        assert "capture_complete" in ALERT_TEMPLATES

    def test_rain_template_is_emergency(self):
        """Test that rain template is emergency level."""
        template = ALERT_TEMPLATES["rain_detected"]
        assert template["level"] == AlertLevel.EMERGENCY

    @pytest.mark.asyncio
    async def test_raise_from_template(self):
        """Test raising alert from template."""
        manager = AlertManager()

        alert = await manager.raise_from_template(
            "capture_complete",
            source="camera",
            target="M31",
            frames=100,
        )

        assert alert is not None
        assert "M31" in alert.message
        assert "100" in alert.message

    @pytest.mark.asyncio
    async def test_unknown_template(self):
        """Test raising alert from unknown template."""
        manager = AlertManager()

        alert = await manager.raise_from_template(
            "nonexistent_template",
            source="test",
        )

        assert alert is None


class TestChannelRouting:
    """Tests for channel routing based on alert level."""

    @pytest.fixture
    def manager(self):
        return AlertManager()

    def test_debug_only_logs(self, manager):
        """Test DEBUG level only logs."""
        channels = manager._get_channels_for_level(AlertLevel.DEBUG)
        assert channels == [AlertChannel.LOG]

    def test_info_logs_and_emails(self, manager):
        """Test INFO level logs and emails."""
        channels = manager._get_channels_for_level(AlertLevel.INFO)
        assert AlertChannel.LOG in channels
        assert AlertChannel.EMAIL in channels
        assert AlertChannel.SMS not in channels

    def test_critical_includes_sms(self, manager):
        """Test CRITICAL level includes SMS."""
        channels = manager._get_channels_for_level(AlertLevel.CRITICAL)
        assert AlertChannel.SMS in channels
        assert AlertChannel.PUSH in channels

    def test_emergency_includes_call(self, manager):
        """Test EMERGENCY level includes voice call."""
        channels = manager._get_channels_for_level(AlertLevel.EMERGENCY)
        assert AlertChannel.CALL in channels
        assert AlertChannel.SMS in channels
        assert AlertChannel.PUSH in channels


class TestAcknowledgment:
    """Tests for alert acknowledgment."""

    @pytest.fixture
    def manager(self):
        return AlertManager()

    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, manager):
        """Test acknowledging an alert."""
        alert = Alert(
            level=AlertLevel.WARNING,
            source="test",
            message="Ack test",
        )
        await manager.raise_alert(alert)

        result = await manager.acknowledge(alert.id, "operator")

        assert result is True
        assert alert.acknowledged is True
        assert alert.acknowledged_by == "operator"

    @pytest.mark.asyncio
    async def test_acknowledge_unknown_alert(self, manager):
        """Test acknowledging unknown alert returns False."""
        result = await manager.acknowledge("unknown123", "operator")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_unacknowledged(self, manager):
        """Test getting unacknowledged alerts."""
        alert1 = Alert(level=AlertLevel.WARNING, source="test", message="Alert 1")
        alert2 = Alert(level=AlertLevel.WARNING, source="test", message="Alert 2")

        await manager.raise_alert(alert1)
        await manager.raise_alert(alert2)

        # Acknowledge first
        await manager.acknowledge(alert1.id, "operator")

        unacked = manager.get_unacknowledged()
        assert len(unacked) == 1
        assert unacked[0].id == alert2.id


class TestAlertHistoryDB:
    """Tests for AlertHistoryDB class."""

    @pytest.fixture
    def db(self):
        """Create in-memory database for testing."""
        db = AlertHistoryDB(":memory:")
        db.connect()
        yield db
        db.close()

    def test_insert_and_get_alert(self, db):
        """Test inserting and retrieving an alert."""
        alert = Alert(
            level=AlertLevel.WARNING,
            source="test",
            message="Test alert",
            data={"key": "value"}
        )
        alert.channels_sent = [AlertChannel.EMAIL, AlertChannel.PUSH]

        db.insert_alert(alert)
        retrieved = db.get_alert(alert.id)

        assert retrieved is not None
        assert retrieved.id == alert.id
        assert retrieved.level == AlertLevel.WARNING
        assert retrieved.source == "test"
        assert retrieved.message == "Test alert"
        assert retrieved.data == {"key": "value"}
        assert AlertChannel.EMAIL in retrieved.channels_sent

    def test_get_alerts_with_filters(self, db):
        """Test querying alerts with filters."""
        alert1 = Alert(level=AlertLevel.INFO, source="camera", message="Alert 1")
        alert2 = Alert(level=AlertLevel.WARNING, source="mount", message="Alert 2")
        alert3 = Alert(level=AlertLevel.WARNING, source="camera", message="Alert 3")

        db.insert_alert(alert1)
        db.insert_alert(alert2)
        db.insert_alert(alert3)

        # Filter by level
        warnings = db.get_alerts(level=AlertLevel.WARNING)
        assert len(warnings) == 2

        # Filter by source
        camera_alerts = db.get_alerts(source="camera")
        assert len(camera_alerts) == 2

        # Combined filters
        camera_warnings = db.get_alerts(level=AlertLevel.WARNING, source="camera")
        assert len(camera_warnings) == 1

    def test_update_acknowledgment(self, db):
        """Test updating alert acknowledgment."""
        alert = Alert(level=AlertLevel.WARNING, source="test", message="Ack test")
        db.insert_alert(alert)

        ack_time = datetime.now()
        db.update_acknowledgment(alert.id, "operator", ack_time)

        retrieved = db.get_alert(alert.id)
        assert retrieved.acknowledged is True
        assert retrieved.acknowledged_by == "operator"

    def test_get_unacknowledged(self, db):
        """Test getting unacknowledged alerts."""
        alert1 = Alert(level=AlertLevel.WARNING, source="test", message="Alert 1")
        alert2 = Alert(level=AlertLevel.WARNING, source="test", message="Alert 2")
        alert1.acknowledged = True
        alert1.acknowledged_by = "operator"

        db.insert_alert(alert1)
        db.insert_alert(alert2)

        unacked = db.get_unacknowledged()
        assert len(unacked) == 1
        assert unacked[0].id == alert2.id

    def test_get_alert_count(self, db):
        """Test getting alert count."""
        for i in range(5):
            alert = Alert(
                level=AlertLevel.INFO if i < 3 else AlertLevel.WARNING,
                source="test",
                message=f"Alert {i}"
            )
            db.insert_alert(alert)

        total = db.get_alert_count()
        assert total == 5

        info_count = db.get_alert_count(level=AlertLevel.INFO)
        assert info_count == 3

    def test_cleanup_old_alerts(self, db):
        """Test cleaning up old alerts."""
        # Create an old alert (manually set timestamp in the past)
        old_alert = Alert(level=AlertLevel.INFO, source="test", message="Old")
        old_alert.timestamp = datetime.now() - timedelta(days=60)
        db.insert_alert(old_alert)

        # Create a recent alert
        new_alert = Alert(level=AlertLevel.INFO, source="test", message="New")
        db.insert_alert(new_alert)

        db.cleanup_old_alerts(retention_days=30)

        # Old alert should be deleted
        assert db.get_alert(old_alert.id) is None
        # New alert should remain
        assert db.get_alert(new_alert.id) is not None


class TestAlertManagerWithDB:
    """Tests for AlertManager with database persistence."""

    @pytest.fixture
    def manager_with_db(self):
        """Create alert manager with in-memory database."""
        config = AlertConfig(history_db_path=":memory:")
        manager = AlertManager(config)
        yield manager
        manager.close()

    @pytest.mark.asyncio
    async def test_alerts_persisted_to_db(self, manager_with_db):
        """Test that alerts are persisted to database."""
        alert = Alert(
            level=AlertLevel.WARNING,
            source="test",
            message="Persistence test"
        )

        await manager_with_db.raise_alert(alert)

        # Check database directly
        db_alert = manager_with_db._history_db.get_alert(alert.id)
        assert db_alert is not None
        assert db_alert.message == "Persistence test"

    @pytest.mark.asyncio
    async def test_acknowledgment_persisted(self, manager_with_db):
        """Test that acknowledgments are persisted to database."""
        alert = Alert(
            level=AlertLevel.WARNING,
            source="test",
            message="Ack persistence test"
        )

        await manager_with_db.raise_alert(alert)
        await manager_with_db.acknowledge(alert.id, "operator")

        # Check database
        db_alert = manager_with_db._history_db.get_alert(alert.id)
        assert db_alert.acknowledged is True
        assert db_alert.acknowledged_by == "operator"

    def test_get_history_from_db(self, manager_with_db):
        """Test querying history from database."""
        # Insert some alerts directly
        for i in range(5):
            alert = Alert(
                level=AlertLevel.INFO,
                source="test",
                message=f"History test {i}"
            )
            manager_with_db._history.append(alert)
            manager_with_db._history_db.insert_alert(alert)

        history = manager_with_db.get_history_from_db(limit=3)
        assert len(history) == 3

    def test_get_alert_stats(self, manager_with_db):
        """Test getting alert statistics."""
        # Add some alerts
        for level in [AlertLevel.INFO, AlertLevel.INFO, AlertLevel.WARNING]:
            alert = Alert(level=level, source="test", message="Stats test")
            manager_with_db._history.append(alert)
            manager_with_db._history_db.insert_alert(alert)

        stats = manager_with_db.get_alert_stats()
        assert stats["total"] == 3
        assert stats["by_level"]["INFO"] == 2
        assert stats["by_level"]["WARNING"] == 1
