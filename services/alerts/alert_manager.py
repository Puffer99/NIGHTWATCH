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
import sqlite3
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from pathlib import Path
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

    # Quiet hours (suppress non-critical notifications)
    quiet_hours_enabled: bool = False
    quiet_hours_start: int = 22  # 10 PM (24-hour format)
    quiet_hours_end: int = 7     # 7 AM
    quiet_hours_min_level: AlertLevel = AlertLevel.CRITICAL  # Only this and above during quiet

    # Deduplication
    dedup_window_seconds: float = 300.0  # 5 minute window for dedup

    # Alert history database
    history_db_path: str = ""  # SQLite database path, empty for in-memory only
    history_retention_days: int = 30  # How long to keep alerts


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


class AlertHistoryDB:
    """
    SQLite database for persistent alert history.

    Stores all alerts with their metadata for audit trail and analysis.
    """

    def __init__(self, db_path: str = ":memory:"):
        """
        Initialize alert history database.

        Args:
            db_path: Path to SQLite database, ":memory:" for in-memory
        """
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self):
        """Connect to database and create tables."""
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _create_tables(self):
        """Create database tables."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                level TEXT NOT NULL,
                source TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                data TEXT,
                acknowledged INTEGER DEFAULT 0,
                acknowledged_by TEXT,
                acknowledged_at TEXT,
                channels_sent TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_alerts_timestamp
                ON alerts(timestamp);
            CREATE INDEX IF NOT EXISTS idx_alerts_level
                ON alerts(level);
            CREATE INDEX IF NOT EXISTS idx_alerts_source
                ON alerts(source);
            CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged
                ON alerts(acknowledged);
        """)
        self._conn.commit()

    def insert_alert(self, alert: Alert):
        """Insert alert into database."""
        if not self._conn:
            return

        channels_json = json.dumps([c.value for c in alert.channels_sent])
        data_json = json.dumps(alert.data) if alert.data else None

        self._conn.execute("""
            INSERT OR REPLACE INTO alerts
            (id, level, source, message, timestamp, data,
             acknowledged, acknowledged_by, acknowledged_at, channels_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert.id,
            alert.level.name,
            alert.source,
            alert.message,
            alert.timestamp.isoformat(),
            data_json,
            1 if alert.acknowledged else 0,
            alert.acknowledged_by,
            alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            channels_json
        ))
        self._conn.commit()

    def update_acknowledgment(self, alert_id: str, user: str, timestamp: datetime):
        """Update alert acknowledgment."""
        if not self._conn:
            return

        self._conn.execute("""
            UPDATE alerts
            SET acknowledged = 1, acknowledged_by = ?, acknowledged_at = ?
            WHERE id = ?
        """, (user, timestamp.isoformat(), alert_id))
        self._conn.commit()

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID."""
        if not self._conn:
            return None

        cursor = self._conn.execute(
            "SELECT * FROM alerts WHERE id = ?", (alert_id,)
        )
        row = cursor.fetchone()
        if row:
            return self._row_to_alert(row)
        return None

    def get_alerts(
        self,
        since: Optional[datetime] = None,
        level: Optional[AlertLevel] = None,
        source: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100
    ) -> List[Alert]:
        """
        Query alerts with optional filters.

        Args:
            since: Only alerts after this time
            level: Filter by level
            source: Filter by source
            acknowledged: Filter by acknowledgment status
            limit: Maximum results

        Returns:
            List of matching alerts
        """
        if not self._conn:
            return []

        query = "SELECT * FROM alerts WHERE 1=1"
        params = []

        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())

        if level:
            query += " AND level = ?"
            params.append(level.name)

        if source:
            query += " AND source = ?"
            params.append(source)

        if acknowledged is not None:
            query += " AND acknowledged = ?"
            params.append(1 if acknowledged else 0)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = self._conn.execute(query, params)
        return [self._row_to_alert(row) for row in cursor.fetchall()]

    def get_unacknowledged(self) -> List[Alert]:
        """Get all unacknowledged alerts."""
        return self.get_alerts(acknowledged=False, limit=1000)

    def get_alert_count(
        self,
        since: Optional[datetime] = None,
        level: Optional[AlertLevel] = None
    ) -> int:
        """Get count of alerts matching criteria."""
        if not self._conn:
            return 0

        query = "SELECT COUNT(*) FROM alerts WHERE 1=1"
        params = []

        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())

        if level:
            query += " AND level = ?"
            params.append(level.name)

        cursor = self._conn.execute(query, params)
        return cursor.fetchone()[0]

    def cleanup_old_alerts(self, retention_days: int):
        """Delete alerts older than retention period."""
        if not self._conn:
            return

        cutoff = datetime.now() - timedelta(days=retention_days)
        self._conn.execute(
            "DELETE FROM alerts WHERE timestamp < ?",
            (cutoff.isoformat(),)
        )
        self._conn.commit()
        logger.info(f"Cleaned up alerts older than {retention_days} days")

    def _row_to_alert(self, row: sqlite3.Row) -> Alert:
        """Convert database row to Alert object."""
        channels = []
        if row["channels_sent"]:
            channel_values = json.loads(row["channels_sent"])
            channels = [AlertChannel(v) for v in channel_values]

        data = None
        if row["data"]:
            data = json.loads(row["data"])

        return Alert(
            id=row["id"],
            level=AlertLevel[row["level"]],
            source=row["source"],
            message=row["message"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            data=data,
            acknowledged=bool(row["acknowledged"]),
            acknowledged_by=row["acknowledged_by"],
            acknowledged_at=(
                datetime.fromisoformat(row["acknowledged_at"])
                if row["acknowledged_at"] else None
            ),
            channels_sent=channels
        )


class AlertManager:
    """
    Multi-channel alert system for NIGHTWATCH.

    Features:
    - Multiple notification channels
    - Severity-based routing
    - Escalation for unacknowledged alerts
    - Rate limiting
    - Alert history (in-memory and optional SQLite persistence)
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

        # Initialize history database if configured
        self._history_db: Optional[AlertHistoryDB] = None
        if self.config.history_db_path:
            self._history_db = AlertHistoryDB(self.config.history_db_path)
            self._history_db.connect()
            logger.info(f"Alert history database: {self.config.history_db_path}")

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

    def _is_duplicate(self, alert: Alert) -> bool:
        """
        Check if alert is a duplicate within the dedup window.

        Uses source + message hash to identify duplicates.
        """
        key = f"{alert.source}:{alert.message}"
        if key in self._recent_alerts:
            elapsed = (datetime.now() - self._recent_alerts[key]).total_seconds()
            return elapsed < self.config.dedup_window_seconds
        return False

    def _is_quiet_hours(self) -> bool:
        """Check if currently in quiet hours."""
        if not self.config.quiet_hours_enabled:
            return False

        current_hour = datetime.now().hour
        start = self.config.quiet_hours_start
        end = self.config.quiet_hours_end

        # Handle overnight quiet hours (e.g., 22:00 to 07:00)
        if start > end:
            return current_hour >= start or current_hour < end
        else:
            return start <= current_hour < end

    def _should_suppress_for_quiet_hours(self, alert: Alert) -> bool:
        """Check if alert should be suppressed due to quiet hours."""
        if not self._is_quiet_hours():
            return False

        # Allow alerts at or above the minimum quiet hours level
        return alert.level.value < self.config.quiet_hours_min_level.value

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

        # Deduplication check
        if self._is_duplicate(alert):
            logger.debug(f"Alert deduplicated: {alert.message}")
            return False

        # Quiet hours check
        if self._should_suppress_for_quiet_hours(alert):
            logger.debug(f"Alert suppressed (quiet hours): {alert.message}")
            # Still log it, just don't send notifications
            self._history.append(alert)
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

        # Store in history (both in-memory and database)
        self._history.append(alert)
        if self._history_db:
            self._history_db.insert_alert(alert)

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

                # Update database
                if self._history_db:
                    self._history_db.update_acknowledgment(
                        alert_id, user, alert.acknowledged_at
                    )

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

    def get_history_from_db(
        self,
        since: Optional[datetime] = None,
        level: Optional[AlertLevel] = None,
        source: Optional[str] = None,
        limit: int = 100
    ) -> List[Alert]:
        """
        Query alerts from persistent database.

        Args:
            since: Only alerts after this time
            level: Filter by level
            source: Filter by source
            limit: Maximum results

        Returns:
            List of matching alerts
        """
        if not self._history_db:
            # Fall back to in-memory if no database
            results = self._history
            if since:
                results = [a for a in results if a.timestamp >= since]
            if level:
                results = [a for a in results if a.level == level]
            if source:
                results = [a for a in results if a.source == source]
            return results[:limit]

        return self._history_db.get_alerts(
            since=since, level=level, source=source, limit=limit
        )

    def get_alert_stats(self, hours: float = 24.0) -> Dict[str, Any]:
        """
        Get alert statistics for the specified period.

        Returns:
            Dict with counts by level, source, and acknowledgment rate
        """
        cutoff = datetime.now() - timedelta(hours=hours)

        if self._history_db:
            # Use database for stats
            stats = {
                "total": self._history_db.get_alert_count(since=cutoff),
                "by_level": {},
                "unacknowledged": len(self._history_db.get_unacknowledged()),
            }
            for level in AlertLevel:
                stats["by_level"][level.name] = self._history_db.get_alert_count(
                    since=cutoff, level=level
                )
        else:
            # Use in-memory history
            recent = [a for a in self._history if a.timestamp >= cutoff]
            stats = {
                "total": len(recent),
                "by_level": {},
                "unacknowledged": len([a for a in recent if not a.acknowledged]),
            }
            for level in AlertLevel:
                stats["by_level"][level.name] = len(
                    [a for a in recent if a.level == level]
                )

        return stats

    def cleanup_old_alerts(self):
        """Clean up old alerts from database based on retention policy."""
        if self._history_db:
            self._history_db.cleanup_old_alerts(self.config.history_retention_days)

    def close(self):
        """Close alert manager and cleanup resources."""
        # Cancel all escalation tasks
        for task in self._escalation_tasks.values():
            task.cancel()
        self._escalation_tasks.clear()

        # Close database
        if self._history_db:
            self._history_db.close()
            self._history_db = None

        logger.info("Alert manager closed")

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
# MOCK NOTIFIER FOR TESTING
# =============================================================================

class MockNotifier(AlertManager):
    """
    Mock alert manager for testing.

    Records all alerts and channel sends without actually sending.
    Useful for unit tests and simulation mode.
    """

    def __init__(self, config: Optional[AlertConfig] = None):
        super().__init__(config)
        self.sent_alerts: List[Alert] = []
        self.sent_channels: Dict[str, List[AlertChannel]] = {}
        self.email_sends: List[dict] = []
        self.push_sends: List[dict] = []
        self.sms_sends: List[dict] = []
        self.webhook_sends: List[dict] = []

    async def _send_email(self, alert: Alert):
        """Record email send instead of actually sending."""
        self.email_sends.append({
            "alert_id": alert.id,
            "level": alert.level.name,
            "source": alert.source,
            "message": alert.message,
            "recipients": list(self.config.email_recipients),
        })
        logger.debug(f"[MOCK] Email recorded: {alert.message[:50]}")

    async def _send_push(self, alert: Alert):
        """Record push send instead of actually sending."""
        self.push_sends.append({
            "alert_id": alert.id,
            "level": alert.level.name,
            "source": alert.source,
            "message": alert.message,
        })
        logger.debug(f"[MOCK] Push recorded: {alert.message[:50]}")

    async def _send_sms(self, alert: Alert):
        """Record SMS send instead of actually sending."""
        self.sms_sends.append({
            "alert_id": alert.id,
            "level": alert.level.name,
            "source": alert.source,
            "message": alert.message,
            "to_numbers": list(self.config.sms_to_numbers),
        })
        logger.debug(f"[MOCK] SMS recorded: {alert.message[:50]}")

    async def _send_webhook(self, alert: Alert):
        """Record webhook send instead of actually sending."""
        self.webhook_sends.append({
            "alert_id": alert.id,
            "level": alert.level.name,
            "source": alert.source,
            "message": alert.message,
            "urls": list(self.config.webhook_urls),
        })
        logger.debug(f"[MOCK] Webhook recorded: {alert.message[:50]}")

    async def _send_call(self, alert: Alert):
        """Record call instead of actually calling."""
        logger.debug(f"[MOCK] Call recorded: {alert.message[:50]}")

    def clear_records(self):
        """Clear all recorded sends."""
        self.sent_alerts.clear()
        self.sent_channels.clear()
        self.email_sends.clear()
        self.push_sends.clear()
        self.sms_sends.clear()
        self.webhook_sends.clear()

    def get_sends_for_alert(self, alert_id: str) -> dict:
        """Get all sends for a specific alert."""
        return {
            "emails": [e for e in self.email_sends if e["alert_id"] == alert_id],
            "pushes": [p for p in self.push_sends if p["alert_id"] == alert_id],
            "sms": [s for s in self.sms_sends if s["alert_id"] == alert_id],
            "webhooks": [w for w in self.webhook_sends if w["alert_id"] == alert_id],
        }


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
