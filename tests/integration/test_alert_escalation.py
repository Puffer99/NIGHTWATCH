"""
Integration tests for NIGHTWATCH alert escalation.

Tests the full escalation flow: alert -> wait -> escalation.
"""

import asyncio
from datetime import datetime, timedelta

import pytest

from services.alerts.alert_manager import (
    AlertManager,
    AlertConfig,
    Alert,
    AlertLevel,
    AlertChannel,
    MockNotifier,
)


class TestAlertEscalation:
    """Integration tests for alert escalation."""

    @pytest.fixture
    def fast_escalation_config(self):
        """Create config with fast escalation for testing."""
        return AlertConfig(
            email_enabled=True,
            email_recipients=["test@example.com"],
            push_enabled=True,
            ntfy_enabled=True,
            sms_enabled=True,
            sms_to_numbers=["+1234567890"],
            escalation_timeout_sec=0.5,  # 500ms for fast testing
        )

    @pytest.fixture
    def mock_notifier(self, fast_escalation_config):
        """Create mock notifier for testing."""
        return MockNotifier(fast_escalation_config)

    @pytest.mark.asyncio
    async def test_critical_alert_escalates_when_unacknowledged(self, mock_notifier):
        """Test that critical alerts escalate when not acknowledged."""
        alert = Alert(
            level=AlertLevel.CRITICAL,
            source="test",
            message="Critical escalation test",
        )

        # Raise the alert
        await mock_notifier.raise_alert(alert)

        # Initial sends should include SMS (for CRITICAL)
        initial_sms_count = len(mock_notifier.sms_sends)
        initial_push_count = len(mock_notifier.push_sends)
        assert initial_sms_count >= 1, "CRITICAL should send SMS"
        assert initial_push_count >= 1, "CRITICAL should send push"

        # Wait for escalation timeout plus buffer
        await asyncio.sleep(0.7)

        # Check that escalation sent additional notifications
        # Escalation resends to PUSH, SMS, CALL channels
        assert len(mock_notifier.sms_sends) > initial_sms_count, \
            "Escalation should send additional SMS"
        assert len(mock_notifier.push_sends) > initial_push_count, \
            "Escalation should send additional push"

    @pytest.mark.asyncio
    async def test_acknowledged_alert_does_not_escalate(self, mock_notifier):
        """Test that acknowledged alerts do not escalate."""
        alert = Alert(
            level=AlertLevel.CRITICAL,
            source="test",
            message="Acknowledged alert test",
        )

        # Raise the alert
        await mock_notifier.raise_alert(alert)

        initial_sms_count = len(mock_notifier.sms_sends)

        # Acknowledge before escalation timeout
        await mock_notifier.acknowledge(alert.id, "operator")

        # Wait past escalation timeout
        await asyncio.sleep(0.7)

        # Should NOT have additional sends after acknowledgment
        assert len(mock_notifier.sms_sends) == initial_sms_count, \
            "Acknowledged alert should not escalate"

    @pytest.mark.asyncio
    async def test_info_alert_does_not_escalate(self, mock_notifier):
        """Test that INFO alerts do not escalate."""
        alert = Alert(
            level=AlertLevel.INFO,
            source="test",
            message="Info no escalation test",
        )

        await mock_notifier.raise_alert(alert)

        # INFO shouldn't have SMS at all
        initial_sms_count = len(mock_notifier.sms_sends)

        # Wait past escalation timeout
        await asyncio.sleep(0.7)

        # Still no SMS
        assert len(mock_notifier.sms_sends) == initial_sms_count, \
            "INFO should not escalate to SMS"

    @pytest.mark.asyncio
    async def test_emergency_alert_escalates(self, mock_notifier):
        """Test that EMERGENCY alerts escalate with full channels."""
        alert = Alert(
            level=AlertLevel.EMERGENCY,
            source="test",
            message="Emergency escalation test",
        )

        await mock_notifier.raise_alert(alert)

        initial_push = len(mock_notifier.push_sends)
        initial_sms = len(mock_notifier.sms_sends)

        # Wait for escalation
        await asyncio.sleep(0.7)

        # EMERGENCY should escalate through all channels
        assert len(mock_notifier.push_sends) > initial_push
        assert len(mock_notifier.sms_sends) > initial_sms

    @pytest.mark.asyncio
    async def test_multiple_alerts_escalate_independently(self, mock_notifier):
        """Test that multiple alerts have independent escalation timers."""
        alert1 = Alert(
            level=AlertLevel.CRITICAL,
            source="test1",
            message="Alert 1",
        )
        alert2 = Alert(
            level=AlertLevel.CRITICAL,
            source="test2",
            message="Alert 2",
        )

        # Raise first alert
        await mock_notifier.raise_alert(alert1)
        await asyncio.sleep(0.2)

        # Raise second alert
        await mock_notifier.raise_alert(alert2)

        # Acknowledge first, leave second unacknowledged
        await mock_notifier.acknowledge(alert1.id, "operator")

        initial_sms = len(mock_notifier.sms_sends)

        # Wait for escalation
        await asyncio.sleep(0.7)

        # Only alert2 should have escalated
        # Check that we got additional SMS (from alert2 escalation)
        assert len(mock_notifier.sms_sends) > initial_sms


class TestEscalationWithDatabase:
    """Test escalation with database persistence."""

    @pytest.fixture
    def manager_with_db(self):
        """Create alert manager with in-memory database and fast escalation."""
        config = AlertConfig(
            history_db_path=":memory:",
            escalation_timeout_sec=0.5,
        )
        manager = AlertManager(config)
        yield manager
        manager.close()

    @pytest.mark.asyncio
    async def test_escalation_state_persisted(self, manager_with_db):
        """Test that alert state is persisted during escalation."""
        alert = Alert(
            level=AlertLevel.CRITICAL,
            source="test",
            message="Persistence during escalation",
        )

        await manager_with_db.raise_alert(alert)

        # Verify persisted in database
        db_alert = manager_with_db._history_db.get_alert(alert.id)
        assert db_alert is not None
        assert db_alert.acknowledged is False

        # Acknowledge
        await manager_with_db.acknowledge(alert.id, "operator")

        # Verify acknowledgment persisted
        db_alert = manager_with_db._history_db.get_alert(alert.id)
        assert db_alert.acknowledged is True
        assert db_alert.acknowledged_by == "operator"

    @pytest.mark.asyncio
    async def test_escalation_history_tracked(self, manager_with_db):
        """Test that escalated alerts remain in history."""
        alert = Alert(
            level=AlertLevel.CRITICAL,
            source="test",
            message="History tracking test",
        )

        await manager_with_db.raise_alert(alert)

        # Wait for escalation
        await asyncio.sleep(0.7)

        # Alert should still be in history
        assert len(manager_with_db._history) == 1
        assert manager_with_db._history[0].id == alert.id

        # Should also be in database
        db_alerts = manager_with_db._history_db.get_alerts(limit=10)
        assert any(a.id == alert.id for a in db_alerts)
