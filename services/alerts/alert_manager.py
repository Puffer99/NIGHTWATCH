"""
NIGHTWATCH Alert Manager
Multi-Channel Notification System

POS Panel v2.0 - Day 16 Recommendations (SRO Team + Bob Denny):
- Multi-channel alerts: Push, SMS, Email, Voice call
- Escalation based on severity and acknowledgment
- Alert templates for common situations
- Rate limiting to prevent alert storms
"""

import asyncio
import logging
import smtplib
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Optional, List, Dict, Callable, Any
import json
import uuid

logger = logging.getLogger("NIGHTWATCH.Alerts")


class AlertLevel(Enum):
    """Alert severity levels."""
    DEBUG = 0      # Detailed logging only
    INFO = 1       # Normal operations (email digest)
    WARNING = 2    # Attention needed (push notification)
    CRITICAL = 3   # Immediate action (SMS + push + email)
    EMERGENCY = 4  # System protection activated (all channels + call)


class AlertChannel(Enum):
    """Notification channels."""
    LOG = "log"           # Local logging only
    EMAIL = "email"       # Email notification
    PUSH = "push"         # Push notification (Firebase/APNS)
    SMS = "sms"           # SMS text message
    CALL = "call"         # Voice call
    WEBHOOK = "webhook"   # HTTP webhook (Slack, Discord, etc.)


@dataclass
class AlertConfig:
    """Alert system configuration."""
    # Email channel configuration
    email_enabled: bool = True
    email_recipients: List[str] = field(default_factory=list)
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_smtp_user: str = ""
    email_smtp_password: str = ""
    email_from_address: str = "nightwatch@observatory.local"
    email_from_name: str = "NIGHTWATCH Observatory"
    email_use_tls: bool = True
    email_timeout: float = 30.0

    push_enabled: bool = True
    push_firebase_key: str = ""

    sms_enabled: bool = True
    sms_twilio_sid: str = ""
    sms_twilio_token: str = ""
    sms_from_number: str = ""
    sms_to_numbers: List[str] = field(default_factory=list)

    call_enabled: bool = True
    call_to_numbers: List[str] = field(default_factory=list)

    webhook_enabled: bool = False
    webhook_urls: List[str] = field(default_factory=list)

    # ntfy.sh local push notification
    ntfy_enabled: bool = False
    ntfy_server: str = "https://ntfy.sh"  # Self-hosted or ntfy.sh
    ntfy_topic: str = "nightwatch"
    ntfy_auth_token: str = ""  # Optional authentication

    # Rate limiting
    min_interval_seconds: float = 60.0    # Minimum time between same alerts
    max_alerts_per_hour: int = 20         # Maximum alerts per hour
    email_min_interval_per_type: float = 3600.0  # 1 hour between same email alert type

    # Escalation
    escalation_timeout_sec: float = 300.0  # Time before escalation


@dataclass
class Alert:
    """System alert."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    level: AlertLevel = AlertLevel.INFO
    source: str = ""           # Subsystem that raised alert
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    data: Optional[Dict[str, Any]] = None  # Additional context
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    channels_sent: List[AlertChannel] = field(default_factory=list)


# Alert templates for common situations
ALERT_TEMPLATES = {
    "weather_unsafe": {
        "level": AlertLevel.WARNING,
        "message": "Weather conditions unsafe: {reason}. Telescope parking.",
        "channels": [AlertChannel.PUSH, AlertChannel.EMAIL]
    },
    "rain_detected": {
        "level": AlertLevel.EMERGENCY,
        "message": "RAIN DETECTED! Emergency close initiated.",
        "channels": [AlertChannel.PUSH, AlertChannel.SMS, AlertChannel.EMAIL, AlertChannel.CALL]
    },
    "guiding_failed": {
        "level": AlertLevel.WARNING,
        "message": "Autoguiding lost star. RMS was {rms}\".",
        "channels": [AlertChannel.PUSH]
    },
    "capture_complete": {
        "level": AlertLevel.INFO,
        "message": "Capture of {target} complete. {frames} frames captured.",
        "channels": [AlertChannel.EMAIL]
    },
    "sensor_offline": {
        "level": AlertLevel.CRITICAL,
        "message": "Sensor {sensor} offline for {duration}. Safety degraded.",
        "channels": [AlertChannel.PUSH, AlertChannel.SMS, AlertChannel.EMAIL]
    },
    "seeing_excellent": {
        "level": AlertLevel.INFO,
        "message": "Excellent seeing predicted: {seeing}\". Consider priority targets.",
        "channels": [AlertChannel.PUSH]
    },
    "mount_error": {
        "level": AlertLevel.CRITICAL,
        "message": "Mount error: {error}. Manual intervention may be required.",
        "channels": [AlertChannel.PUSH, AlertChannel.SMS, AlertChannel.EMAIL]
    },
    "system_startup": {
        "level": AlertLevel.INFO,
        "message": "NIGHTWATCH system started successfully.",
        "channels": [AlertChannel.EMAIL]
    },
    "system_shutdown": {
        "level": AlertLevel.INFO,
        "message": "NIGHTWATCH system shutting down: {reason}.",
        "channels": [AlertChannel.EMAIL]
    },
}


class AlertManager:
    """
    Multi-channel alert system for NIGHTWATCH.

    Features:
    - Multiple notification channels
    - Severity-based routing
    - Escalation for unacknowledged alerts
    - Rate limiting
    - Alert history
    """

    def __init__(self, config: Optional[AlertConfig] = None):
        """
        Initialize alert manager.

        Args:
            config: Alert configuration
        """
        self.config = config or AlertConfig()
        self._history: List[Alert] = []
        self._recent_alerts: Dict[str, datetime] = {}  # For rate limiting
        self._recent_emails: Dict[str, datetime] = {}  # Per-type email rate limiting
        self._alert_count_hour = 0
        self._last_hour_reset = datetime.now()
        self._escalation_tasks: Dict[str, asyncio.Task] = {}
        self._callbacks: List[Callable] = []
        self._http_session = None  # Lazy initialized for webhook/ntfy

    def _get_channels_for_level(self, level: AlertLevel) -> List[AlertChannel]:
        """Get notification channels for alert level."""
        if level == AlertLevel.DEBUG:
            return [AlertChannel.LOG]
        elif level == AlertLevel.INFO:
            return [AlertChannel.LOG, AlertChannel.EMAIL]
        elif level == AlertLevel.WARNING:
            return [AlertChannel.LOG, AlertChannel.PUSH, AlertChannel.EMAIL]
        elif level == AlertLevel.CRITICAL:
            return [AlertChannel.LOG, AlertChannel.PUSH, AlertChannel.SMS, AlertChannel.EMAIL]
        elif level == AlertLevel.EMERGENCY:
            return [AlertChannel.LOG, AlertChannel.PUSH, AlertChannel.SMS,
                    AlertChannel.EMAIL, AlertChannel.CALL]
        return [AlertChannel.LOG]

    def _should_rate_limit(self, alert: Alert) -> bool:
        """Check if alert should be rate limited."""
        # Reset hourly counter
        if (datetime.now() - self._last_hour_reset).total_seconds() > 3600:
            self._alert_count_hour = 0
            self._last_hour_reset = datetime.now()

        # Check hourly limit
        if self._alert_count_hour >= self.config.max_alerts_per_hour:
            return True

        # Check duplicate suppression
        key = f"{alert.source}:{alert.message}"
        if key in self._recent_alerts:
            elapsed = (datetime.now() - self._recent_alerts[key]).total_seconds()
            if elapsed < self.config.min_interval_seconds:
                return True

        return False

    async def raise_alert(self, alert: Alert) -> bool:
        """
        Raise an alert through appropriate channels.

        Args:
            alert: Alert to raise

        Returns:
            True if alert was sent
        """
        # Rate limiting
        if self._should_rate_limit(alert):
            logger.debug(f"Alert rate limited: {alert.message}")
            return False

        # Update tracking
        key = f"{alert.source}:{alert.message}"
        self._recent_alerts[key] = datetime.now()
        self._alert_count_hour += 1

        # Get channels
        channels = self._get_channels_for_level(alert.level)

        # Send to each channel
        for channel in channels:
            try:
                await self._send_to_channel(alert, channel)
                alert.channels_sent.append(channel)
            except Exception as e:
                logger.error(f"Failed to send to {channel.value}: {e}")

        # Store in history
        self._history.append(alert)

        # Start escalation timer for critical/emergency
        if alert.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
            self._start_escalation(alert)

        # Notify callbacks
        await self._notify_callbacks(alert)

        logger.log(
            self._level_to_logging(alert.level),
            f"Alert [{alert.level.name}] {alert.source}: {alert.message}"
        )

        return True

    async def _send_to_channel(self, alert: Alert, channel: AlertChannel):
        """Send alert to specific channel."""
        if channel == AlertChannel.LOG:
            # Already logged in raise_alert
            pass

        elif channel == AlertChannel.EMAIL:
            if self.config.email_enabled and self.config.email_recipients:
                await self._send_email(alert)

        elif channel == AlertChannel.PUSH:
            if self.config.push_enabled or self.config.ntfy_enabled:
                await self._send_push(alert)

        elif channel == AlertChannel.SMS:
            if self.config.sms_enabled and self.config.sms_to_numbers:
                await self._send_sms(alert)

        elif channel == AlertChannel.CALL:
            if self.config.call_enabled and self.config.call_to_numbers:
                await self._send_call(alert)

        elif channel == AlertChannel.WEBHOOK:
            if self.config.webhook_enabled and self.config.webhook_urls:
                await self._send_webhook(alert)

    async def _send_email(self, alert: Alert):
        """
        Send email notification via SMTP.

        Creates HTML and plain text versions of the email.
        Implements per-alert-type rate limiting (max 1 email per hour per type).
        """
        if not self.config.email_smtp_host:
            logger.warning("Email SMTP host not configured, skipping email")
            return

        # Check per-type email rate limiting
        email_key = f"{alert.source}:{alert.level.name}"
        if email_key in self._recent_emails:
            elapsed = (datetime.now() - self._recent_emails[email_key]).total_seconds()
            if elapsed < self.config.email_min_interval_per_type:
                logger.debug(
                    f"Email rate limited for {email_key}, "
                    f"last sent {elapsed:.0f}s ago"
                )
                return

        # Update rate limiting tracker
        self._recent_emails[email_key] = datetime.now()

        # Build email content
        subject = f"[NIGHTWATCH {alert.level.name}] {alert.source}: {alert.message[:50]}"

        # Plain text version
        text_body = self._format_email_plain(alert)

        # HTML version
        html_body = self._format_email_html(alert)

        # Send to each recipient
        for recipient in self.config.email_recipients:
            try:
                await self._send_smtp_email(recipient, subject, text_body, html_body)
                logger.debug(f"Email sent to {recipient}")
            except Exception as e:
                logger.error(f"Failed to send email to {recipient}: {e}")

    def _format_email_plain(self, alert: Alert) -> str:
        """Format alert as plain text email."""
        lines = [
            f"NIGHTWATCH ALERT",
            f"================",
            f"",
            f"Level: {alert.level.name}",
            f"Source: {alert.source}",
            f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"Message:",
            f"{alert.message}",
            f"",
        ]

        if alert.data:
            lines.append("Additional Data:")
            for key, value in alert.data.items():
                lines.append(f"  {key}: {value}")
            lines.append("")

        lines.extend([
            f"Alert ID: {alert.id}",
            f"",
            f"---",
            f"This is an automated message from NIGHTWATCH Observatory System.",
        ])

        return "\n".join(lines)

    def _format_email_html(self, alert: Alert) -> str:
        """Format alert as HTML email."""
        # Color coding based on level
        level_colors = {
            AlertLevel.DEBUG: "#6c757d",
            AlertLevel.INFO: "#17a2b8",
            AlertLevel.WARNING: "#ffc107",
            AlertLevel.CRITICAL: "#dc3545",
            AlertLevel.EMERGENCY: "#721c24",
        }
        level_color = level_colors.get(alert.level, "#333")

        data_rows = ""
        if alert.data:
            for key, value in alert.data.items():
                data_rows += f"<tr><td style='padding:4px 8px;'><strong>{key}</strong></td><td style='padding:4px 8px;'>{value}</td></tr>"

        html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5;">
  <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    <div style="background: {level_color}; color: white; padding: 20px;">
      <h1 style="margin: 0; font-size: 24px;">NIGHTWATCH Alert</h1>
      <p style="margin: 10px 0 0 0; opacity: 0.9;">{alert.level.name} - {alert.source}</p>
    </div>
    <div style="padding: 20px;">
      <p style="font-size: 18px; margin: 0 0 20px 0;">{alert.message}</p>
      <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
        <tr><td style="padding:4px 8px;"><strong>Time</strong></td><td style="padding:4px 8px;">{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
        <tr><td style="padding:4px 8px;"><strong>Alert ID</strong></td><td style="padding:4px 8px;">{alert.id}</td></tr>
        {data_rows}
      </table>
    </div>
    <div style="background: #f8f9fa; padding: 15px 20px; font-size: 12px; color: #6c757d;">
      Automated message from NIGHTWATCH Observatory System
    </div>
  </div>
</body>
</html>
"""
        return html

    async def _send_smtp_email(
        self,
        recipient: str,
        subject: str,
        text_body: str,
        html_body: str
    ):
        """Send email via SMTP (runs in executor to avoid blocking)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._send_smtp_email_sync,
            recipient, subject, text_body, html_body
        )

    def _send_smtp_email_sync(
        self,
        recipient: str,
        subject: str,
        text_body: str,
        html_body: str
    ):
        """Synchronous SMTP send (called from executor)."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.config.email_from_name} <{self.config.email_from_address}>"
        msg["To"] = recipient

        # Attach both plain and HTML versions
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        # Connect and send
        if self.config.email_use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(
                self.config.email_smtp_host,
                self.config.email_smtp_port,
                timeout=self.config.email_timeout
            ) as server:
                server.starttls(context=context)
                if self.config.email_smtp_user:
                    server.login(
                        self.config.email_smtp_user,
                        self.config.email_smtp_password
                    )
                server.sendmail(
                    self.config.email_from_address,
                    recipient,
                    msg.as_string()
                )
        else:
            with smtplib.SMTP(
                self.config.email_smtp_host,
                self.config.email_smtp_port,
                timeout=self.config.email_timeout
            ) as server:
                if self.config.email_smtp_user:
                    server.login(
                        self.config.email_smtp_user,
                        self.config.email_smtp_password
                    )
                server.sendmail(
                    self.config.email_from_address,
                    recipient,
                    msg.as_string()
                )

    async def _send_push(self, alert: Alert):
        """
        Send push notification via ntfy.sh (self-hosted or public).

        ntfy.sh is a simple HTTP-based pub/sub notification service
        that works great for local/self-hosted observatory systems.
        """
        if not self.config.ntfy_enabled:
            logger.debug(f"ntfy not enabled, skipping push: {alert.message}")
            return

        try:
            import aiohttp
        except ImportError:
            logger.warning("aiohttp not installed, cannot send ntfy push")
            return

        url = f"{self.config.ntfy_server.rstrip('/')}/{self.config.ntfy_topic}"

        # Map alert level to ntfy priority
        priority_map = {
            AlertLevel.DEBUG: "1",      # min
            AlertLevel.INFO: "2",       # low
            AlertLevel.WARNING: "3",    # default
            AlertLevel.CRITICAL: "4",   # high
            AlertLevel.EMERGENCY: "5",  # urgent
        }
        priority = priority_map.get(alert.level, "3")

        # Map alert level to emoji tag
        emoji_map = {
            AlertLevel.DEBUG: "information_source",
            AlertLevel.INFO: "information_source",
            AlertLevel.WARNING: "warning",
            AlertLevel.CRITICAL: "rotating_light",
            AlertLevel.EMERGENCY: "sos",
        }
        emoji = emoji_map.get(alert.level, "telescope")

        headers = {
            "Title": f"NIGHTWATCH {alert.level.name}",
            "Priority": priority,
            "Tags": f"{emoji},{alert.source}",
        }

        if self.config.ntfy_auth_token:
            headers["Authorization"] = f"Bearer {self.config.ntfy_auth_token}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    data=alert.message,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.debug(f"ntfy push sent: {alert.message[:50]}")
                    else:
                        logger.error(f"ntfy push failed: {response.status}")
        except Exception as e:
            logger.error(f"ntfy push error: {e}")

    async def _send_sms(self, alert: Alert):
        """Send SMS notification."""
        # Would use Twilio
        logger.debug(f"Would send SMS: {alert.message}")

    async def _send_call(self, alert: Alert):
        """Initiate voice call."""
        # Would use Twilio Voice
        logger.debug(f"Would make call: {alert.message}")

    async def _send_webhook(self, alert: Alert):
        """
        Send webhook notification (generic JSON POST).

        Supports Slack, Discord, and generic webhook endpoints.
        """
        try:
            import aiohttp
        except ImportError:
            logger.warning("aiohttp not installed, cannot send webhook")
            return

        # Build generic JSON payload
        payload = {
            "id": alert.id,
            "level": alert.level.name,
            "source": alert.source,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat(),
            "data": alert.data or {},
        }

        # Build Slack-compatible payload
        slack_color_map = {
            AlertLevel.DEBUG: "#6c757d",
            AlertLevel.INFO: "#17a2b8",
            AlertLevel.WARNING: "#ffc107",
            AlertLevel.CRITICAL: "#dc3545",
            AlertLevel.EMERGENCY: "#721c24",
        }

        slack_payload = {
            "attachments": [{
                "color": slack_color_map.get(alert.level, "#333"),
                "title": f"NIGHTWATCH {alert.level.name}",
                "text": alert.message,
                "fields": [
                    {"title": "Source", "value": alert.source, "short": True},
                    {"title": "Time", "value": alert.timestamp.strftime('%H:%M:%S'), "short": True},
                ],
                "footer": f"Alert ID: {alert.id}",
            }]
        }

        # Build Discord-compatible payload (different format)
        discord_payload = {
            "embeds": [{
                "title": f"NIGHTWATCH {alert.level.name}",
                "description": alert.message,
                "color": int(slack_color_map.get(alert.level, "#333").replace("#", ""), 16),
                "fields": [
                    {"name": "Source", "value": alert.source, "inline": True},
                    {"name": "Time", "value": alert.timestamp.strftime('%H:%M:%S'), "inline": True},
                ],
                "footer": {"text": f"Alert ID: {alert.id}"},
            }]
        }

        for webhook_url in self.config.webhook_urls:
            try:
                # Determine payload based on URL
                if "slack" in webhook_url.lower() or "hooks.slack.com" in webhook_url:
                    send_payload = slack_payload
                elif "discord" in webhook_url.lower() or "discord.com/api/webhooks" in webhook_url:
                    send_payload = discord_payload
                else:
                    send_payload = payload

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        webhook_url,
                        json=send_payload,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status in (200, 204):
                            logger.debug(f"Webhook sent to {webhook_url[:50]}")
                        else:
                            logger.error(f"Webhook failed: {response.status}")
            except Exception as e:
                logger.error(f"Webhook error for {webhook_url[:30]}: {e}")

    def _level_to_logging(self, level: AlertLevel) -> int:
        """Convert AlertLevel to logging level."""
        mapping = {
            AlertLevel.DEBUG: logging.DEBUG,
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.CRITICAL: logging.ERROR,
            AlertLevel.EMERGENCY: logging.CRITICAL,
        }
        return mapping.get(level, logging.INFO)

    # =========================================================================
    # TEMPLATES
    # =========================================================================

    async def raise_from_template(self, template_name: str,
                                   source: str,
                                   **kwargs) -> Optional[Alert]:
        """
        Raise alert from template.

        Args:
            template_name: Name of template
            source: Source subsystem
            **kwargs: Template parameters

        Returns:
            Created alert or None if template not found
        """
        template = ALERT_TEMPLATES.get(template_name)
        if not template:
            logger.error(f"Unknown alert template: {template_name}")
            return None

        message = template["message"].format(**kwargs)

        alert = Alert(
            level=template["level"],
            source=source,
            message=message,
            data=kwargs
        )

        await self.raise_alert(alert)
        return alert

    # =========================================================================
    # ACKNOWLEDGMENT
    # =========================================================================

    async def acknowledge(self, alert_id: str, user: str) -> bool:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert ID
            user: User acknowledging

        Returns:
            True if acknowledged
        """
        for alert in self._history:
            if alert.id == alert_id and not alert.acknowledged:
                alert.acknowledged = True
                alert.acknowledged_by = user
                alert.acknowledged_at = datetime.now()

                # Cancel escalation
                if alert_id in self._escalation_tasks:
                    self._escalation_tasks[alert_id].cancel()
                    del self._escalation_tasks[alert_id]

                logger.info(f"Alert {alert_id} acknowledged by {user}")
                return True

        return False

    def get_unacknowledged(self) -> List[Alert]:
        """Get all unacknowledged alerts."""
        return [a for a in self._history if not a.acknowledged]

    def get_recent(self, hours: float = 24.0) -> List[Alert]:
        """Get alerts from the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [a for a in self._history if a.timestamp > cutoff]

    # =========================================================================
    # ESCALATION
    # =========================================================================

    def _start_escalation(self, alert: Alert):
        """Start escalation timer for an alert."""
        task = asyncio.create_task(self._escalation_timer(alert))
        self._escalation_tasks[alert.id] = task

    async def _escalation_timer(self, alert: Alert):
        """Escalation timer coroutine."""
        try:
            await asyncio.sleep(self.config.escalation_timeout_sec)

            # Check if still unacknowledged
            if not alert.acknowledged:
                logger.warning(f"Alert {alert.id} escalating (unacknowledged)")

                # Re-send through all channels
                for channel in [AlertChannel.PUSH, AlertChannel.SMS, AlertChannel.CALL]:
                    try:
                        await self._send_to_channel(alert, channel)
                    except Exception as e:
                        logger.error(f"Escalation send failed: {e}")

        except asyncio.CancelledError:
            pass  # Acknowledged before timeout

    # =========================================================================
    # CALLBACKS
    # =========================================================================

    def register_callback(self, callback: Callable):
        """Register callback for new alerts."""
        self._callbacks.append(callback)

    async def _notify_callbacks(self, alert: Alert):
        """Notify registered callbacks."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Callback error: {e}")


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    async def test():
        print("NIGHTWATCH Alert Manager Test\n")

        manager = AlertManager()

        # Test direct alert
        alert = Alert(
            level=AlertLevel.WARNING,
            source="test",
            message="This is a test warning"
        )
        await manager.raise_alert(alert)
        print(f"Raised alert: {alert.id}")

        # Test template
        await manager.raise_from_template(
            "capture_complete",
            source="camera",
            target="Mars",
            frames=5000
        )

        # Check history
        print(f"\nAlert history: {len(manager._history)} alerts")
        for a in manager._history:
            print(f"  [{a.level.name}] {a.message}")

        # Test acknowledgment
        await manager.acknowledge(alert.id, "operator")
        print(f"\nUnacknowledged: {len(manager.get_unacknowledged())}")

    asyncio.run(test())
