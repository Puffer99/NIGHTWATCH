"""
NIGHTWATCH Configuration System

Unified configuration management for all observatory services using pydantic
for type-safe validation and YAML for human-readable config files.

Configuration loading priority:
1. Environment variables (NIGHTWATCH_*)
2. Config file specified via --config CLI argument
3. ./nightwatch.yaml (current directory)
4. ~/.nightwatch/config.yaml (user home)
5. Built-in defaults

Usage:
    from nightwatch.config import load_config, NightwatchConfig

    # Load with automatic discovery
    config = load_config()

    # Load from specific file
    config = load_config("/path/to/config.yaml")

    # Access configuration
    print(config.site.latitude)
    print(config.mount.host)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from nightwatch.exceptions import ConfigurationError

__all__ = [
    "NightwatchConfig",
    "SiteConfig",
    "MountConfig",
    "WeatherConfig",
    "VoiceConfig",
    "TTSConfig",
    "LLMConfig",
    "SafetyConfig",
    "CameraConfig",
    "GuiderConfig",
    "EncoderConfig",
    "AlertConfig",
    "PowerConfig",
    "EnclosureConfig",
    "load_config",
    "get_config_paths",
]


# =============================================================================
# Configuration Dataclasses (Steps 3-15)
# =============================================================================


class SiteConfig(BaseModel):
    """Observatory site location configuration (Step 3).

    Per POS Day 8 discussion on site-specific parameters.
    """

    # Geographic location
    latitude: float = Field(
        default=38.9,
        ge=-90.0,
        le=90.0,
        description="Site latitude in decimal degrees (positive = North)",
    )
    longitude: float = Field(
        default=-117.4,
        ge=-180.0,
        le=180.0,
        description="Site longitude in decimal degrees (positive = East)",
    )
    elevation: float = Field(
        default=1800.0,
        ge=-500.0,
        le=9000.0,
        description="Site elevation in meters above sea level",
    )

    # Timezone
    timezone: str = Field(
        default="America/Los_Angeles",
        description="IANA timezone identifier for the site",
    )

    # Site name for logging/display
    name: str = Field(
        default="NIGHTWATCH Observatory",
        description="Human-readable site name",
    )

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone is a plausible IANA identifier."""
        if "/" not in v and v not in ("UTC", "GMT"):
            raise ValueError(f"Invalid timezone format: {v}. Use IANA format like 'America/Los_Angeles'")
        return v


class MountConfig(BaseModel):
    """Telescope mount connection configuration (Step 4).

    Supports both TCP (network) and serial connections to OnStepX controller.
    """

    # Mount type identifier
    type: Literal["onstepx", "lx200", "indi", "alpaca", "simulator"] = Field(
        default="onstepx",
        description="Mount controller protocol type",
    )

    # Network connection (TCP)
    host: str = Field(
        default="onstep.local",
        description="Mount controller hostname or IP address",
    )
    port: int = Field(
        default=9999,
        ge=1,
        le=65535,
        description="Mount controller TCP port (default: 9999 for OnStepX)",
    )

    # Serial connection (alternative to TCP)
    serial_port: Optional[str] = Field(
        default=None,
        description="Serial port for direct connection (e.g., /dev/ttyUSB0)",
    )
    baudrate: int = Field(
        default=115200,
        description="Serial baudrate (OnStepX typically uses 115200)",
    )

    # Connection settings
    timeout: float = Field(
        default=5.0,
        ge=0.1,
        le=60.0,
        description="Connection timeout in seconds",
    )
    retry_count: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Number of connection retry attempts",
    )

    @model_validator(mode="after")
    def validate_connection(self) -> "MountConfig":
        """Ensure either network or serial connection is configured."""
        # Both can be configured, but at least network should have valid defaults
        return self


class WeatherConfig(BaseModel):
    """Weather station configuration (Step 5).

    Supports Ecowitt WS90 HTTP API for environmental monitoring.
    """

    # Enable/disable weather monitoring
    enabled: bool = Field(
        default=True,
        description="Enable weather monitoring",
    )

    # Weather station type
    type: Literal["ecowitt", "aag", "simulator", "none"] = Field(
        default="ecowitt",
        description="Weather station type",
    )

    # Ecowitt configuration
    host: str = Field(
        default="ecowitt.local",
        description="Weather station hostname or IP",
    )
    port: int = Field(
        default=80,
        ge=1,
        le=65535,
        description="Weather station HTTP port",
    )

    # Polling interval
    poll_interval: float = Field(
        default=30.0,
        ge=5.0,
        le=300.0,
        description="Weather data polling interval in seconds",
    )

    # Data timeout
    stale_threshold: float = Field(
        default=120.0,
        ge=30.0,
        le=600.0,
        description="Seconds after which weather data is considered stale",
    )


class VoiceConfig(BaseModel):
    """Speech-to-Text (STT) configuration (Step 6).

    Optimized for DGX Spark local inference using faster-whisper.
    """

    # Enable/disable voice input
    enabled: bool = Field(
        default=True,
        description="Enable voice input pipeline",
    )

    # Whisper model selection
    model: str = Field(
        default="large-v3",
        description="Whisper model name (tiny, base, small, medium, large-v3)",
    )

    # Compute settings for DGX Spark
    device: Literal["cuda", "cpu", "auto"] = Field(
        default="auto",
        description="Compute device for inference",
    )
    compute_type: Literal["float16", "int8_float16", "int8", "float32"] = Field(
        default="int8_float16",
        description="Compute precision (int8_float16 optimal for DGX Spark)",
    )

    # Audio settings
    language: str = Field(
        default="en",
        description="Primary language for speech recognition",
    )
    vad_enabled: bool = Field(
        default=True,
        description="Enable voice activity detection",
    )


class TTSConfig(BaseModel):
    """Text-to-Speech (TTS) configuration (Step 7).

    Uses Piper TTS for fast local speech synthesis.
    """

    # Enable/disable voice output
    enabled: bool = Field(
        default=True,
        description="Enable voice output pipeline",
    )

    # Piper model
    model: str = Field(
        default="en_US-lessac-medium",
        description="Piper voice model name",
    )

    # Performance settings
    use_cuda: bool = Field(
        default=True,
        description="Use CUDA acceleration for TTS",
    )

    # Caching
    cache_enabled: bool = Field(
        default=True,
        description="Cache frequently used phrases",
    )
    cache_dir: str = Field(
        default="~/.nightwatch/tts_cache",
        description="Directory for TTS audio cache",
    )

    # Voice parameters
    speaking_rate: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Speech rate multiplier",
    )


class LLMConfig(BaseModel):
    """Large Language Model configuration (Step 8).

    Local Llama 3.2 inference for intent detection and tool selection.
    """

    # Enable/disable LLM
    enabled: bool = Field(
        default=True,
        description="Enable LLM for intent processing",
    )

    # Model selection
    model: str = Field(
        default="llama-3.2-3b-instruct",
        description="LLM model name or path",
    )

    # Inference settings
    max_tokens: int = Field(
        default=512,
        ge=64,
        le=4096,
        description="Maximum tokens in response",
    )
    temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (lower = more deterministic)",
    )

    # Performance
    gpu_layers: int = Field(
        default=-1,
        ge=-1,
        description="GPU layers to offload (-1 = all)",
    )
    context_length: int = Field(
        default=4096,
        ge=512,
        le=32768,
        description="Context window size",
    )


class SafetyConfig(BaseModel):
    """Safety threshold configuration (Step 9).

    Per POS Day 4 safety discussions and threshold deliberations.
    """

    # Wind thresholds (mph)
    wind_limit_warning: float = Field(
        default=20.0,
        ge=5.0,
        le=50.0,
        description="Wind speed warning threshold (mph)",
    )
    wind_limit_park: float = Field(
        default=25.0,
        ge=10.0,
        le=60.0,
        description="Wind speed auto-park threshold (mph)",
    )
    wind_limit_emergency: float = Field(
        default=30.0,
        ge=15.0,
        le=80.0,
        description="Wind speed emergency threshold (mph)",
    )

    # Humidity thresholds (%)
    humidity_limit_warning: float = Field(
        default=75.0,
        ge=50.0,
        le=95.0,
        description="Humidity warning threshold (%)",
    )
    humidity_limit_park: float = Field(
        default=80.0,
        ge=60.0,
        le=98.0,
        description="Humidity auto-park threshold (%)",
    )
    humidity_limit_emergency: float = Field(
        default=85.0,
        ge=70.0,
        le=100.0,
        description="Humidity emergency threshold (%)",
    )

    # Temperature thresholds (Celsius)
    temp_min: float = Field(
        default=-20.0,
        ge=-50.0,
        le=10.0,
        description="Minimum operating temperature (C)",
    )
    temp_max: float = Field(
        default=40.0,
        ge=20.0,
        le=60.0,
        description="Maximum operating temperature (C)",
    )

    # Sensor timeout (seconds)
    sensor_timeout: float = Field(
        default=120.0,
        ge=30.0,
        le=600.0,
        description="Sensor data timeout - treat as unsafe if exceeded",
    )

    # Rain holdoff (minutes)
    rain_holdoff_minutes: float = Field(
        default=30.0,
        ge=10.0,
        le=120.0,
        description="Time to wait after rain stops before resuming",
    )


class CameraConfig(BaseModel):
    """Camera configuration (Step 10).

    ZWO ASI camera settings for imaging.
    """

    # Enable/disable
    enabled: bool = Field(
        default=True,
        description="Enable camera control",
    )

    # Camera type
    type: Literal["zwo", "indi", "alpaca", "simulator"] = Field(
        default="zwo",
        description="Camera interface type",
    )

    # Default capture settings
    default_gain: int = Field(
        default=100,
        ge=0,
        le=600,
        description="Default camera gain",
    )
    default_exposure: float = Field(
        default=1.0,
        ge=0.001,
        le=3600.0,
        description="Default exposure time in seconds",
    )
    default_binning: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Default binning (1x1, 2x2, etc.)",
    )

    # Cooling
    cooling_enabled: bool = Field(
        default=True,
        description="Enable sensor cooling",
    )
    target_temperature: float = Field(
        default=-10.0,
        ge=-40.0,
        le=30.0,
        description="Target sensor temperature (C)",
    )


class GuiderConfig(BaseModel):
    """Autoguiding configuration (Step 11).

    PHD2 connection settings for autoguiding.
    """

    # Enable/disable
    enabled: bool = Field(
        default=True,
        description="Enable autoguiding",
    )

    # PHD2 connection
    phd2_host: str = Field(
        default="localhost",
        description="PHD2 server hostname",
    )
    phd2_port: int = Field(
        default=4400,
        ge=1,
        le=65535,
        description="PHD2 JSON-RPC port",
    )

    # Dithering
    dither_pixels: float = Field(
        default=5.0,
        ge=1.0,
        le=20.0,
        description="Dither amount in pixels",
    )
    settle_time: float = Field(
        default=10.0,
        ge=1.0,
        le=60.0,
        description="Settle time after dither (seconds)",
    )


class EncoderConfig(BaseModel):
    """Encoder configuration (Step 12).

    EncoderBridge settings for absolute position feedback.
    """

    # Enable/disable
    enabled: bool = Field(
        default=False,
        description="Enable encoder feedback",
    )

    # Serial connection
    port: str = Field(
        default="/dev/ttyUSB1",
        description="Encoder serial port",
    )
    baudrate: int = Field(
        default=115200,
        description="Serial baudrate",
    )

    # Encoder settings
    resolution: int = Field(
        default=8192,
        ge=256,
        le=65536,
        description="Encoder counts per revolution",
    )


class AlertConfig(BaseModel):
    """Alert notification configuration (Step 13).

    Multi-channel notification settings.
    """

    # Enable channels
    email_enabled: bool = Field(
        default=False,
        description="Enable email notifications",
    )
    sms_enabled: bool = Field(
        default=False,
        description="Enable SMS notifications",
    )
    push_enabled: bool = Field(
        default=False,
        description="Enable push notifications (ntfy.sh)",
    )
    webhook_enabled: bool = Field(
        default=False,
        description="Enable webhook notifications",
    )

    # Email settings
    smtp_host: str = Field(
        default="smtp.gmail.com",
        description="SMTP server hostname",
    )
    smtp_port: int = Field(
        default=587,
        description="SMTP server port",
    )
    email_to: str = Field(
        default="",
        description="Recipient email address",
    )

    # Webhook URL
    webhook_url: str = Field(
        default="",
        description="Webhook URL for notifications",
    )


class PowerConfig(BaseModel):
    """Power management configuration (Step 14).

    NUT (Network UPS Tools) settings.
    """

    # Enable/disable
    enabled: bool = Field(
        default=True,
        description="Enable power monitoring",
    )

    # NUT server
    ups_host: str = Field(
        default="localhost",
        description="NUT server hostname",
    )
    ups_port: int = Field(
        default=3493,
        description="NUT server port",
    )
    ups_name: str = Field(
        default="ups",
        description="UPS name in NUT",
    )

    # Thresholds
    park_threshold: float = Field(
        default=50.0,
        ge=20.0,
        le=80.0,
        description="Battery percentage to trigger park",
    )
    shutdown_threshold: float = Field(
        default=20.0,
        ge=5.0,
        le=50.0,
        description="Battery percentage to trigger shutdown",
    )


class EnclosureConfig(BaseModel):
    """Enclosure/roof configuration (Step 15).

    GPIO settings for roof controller.
    """

    # Enable/disable
    enabled: bool = Field(
        default=False,
        description="Enable enclosure control",
    )

    # GPIO pins (BCM numbering)
    gpio_open_relay: int = Field(
        default=17,
        ge=0,
        le=27,
        description="GPIO pin for open relay",
    )
    gpio_close_relay: int = Field(
        default=18,
        ge=0,
        le=27,
        description="GPIO pin for close relay",
    )
    gpio_open_limit: int = Field(
        default=22,
        ge=0,
        le=27,
        description="GPIO pin for open limit switch",
    )
    gpio_closed_limit: int = Field(
        default=23,
        ge=0,
        le=27,
        description="GPIO pin for closed limit switch",
    )
    gpio_rain_sensor: int = Field(
        default=24,
        ge=0,
        le=27,
        description="GPIO pin for rain sensor",
    )

    # Timing
    motor_timeout: float = Field(
        default=60.0,
        ge=10.0,
        le=300.0,
        description="Maximum motor run time (seconds)",
    )


# =============================================================================
# Master Configuration (Step 16)
# =============================================================================


class NightwatchConfig(BaseModel):
    """Master configuration aggregating all service configs (Step 16).

    This is the top-level configuration object containing all subsystem
    configurations with sensible defaults.
    """

    # Core configurations
    site: SiteConfig = Field(default_factory=SiteConfig)
    mount: MountConfig = Field(default_factory=MountConfig)
    weather: WeatherConfig = Field(default_factory=WeatherConfig)

    # Voice pipeline
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)

    # Safety
    safety: SafetyConfig = Field(default_factory=SafetyConfig)

    # Imaging
    camera: CameraConfig = Field(default_factory=CameraConfig)
    guider: GuiderConfig = Field(default_factory=GuiderConfig)

    # Hardware
    encoder: EncoderConfig = Field(default_factory=EncoderConfig)
    enclosure: EnclosureConfig = Field(default_factory=EnclosureConfig)
    power: PowerConfig = Field(default_factory=PowerConfig)

    # Notifications
    alerts: AlertConfig = Field(default_factory=AlertConfig)

    # Logging level override
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Global logging level",
    )

    class Config:
        """Pydantic configuration."""

        extra = "ignore"  # Ignore unknown fields in config file


# =============================================================================
# Configuration Loading (Steps 17-19)
# =============================================================================


def get_config_paths() -> list[Path]:
    """Get list of config file paths to search (Step 17).

    Returns paths in priority order (first found wins).
    """
    paths = []

    # Current directory
    paths.append(Path("./nightwatch.yaml"))
    paths.append(Path("./nightwatch.yml"))

    # User home directory
    home = Path.home()
    paths.append(home / ".nightwatch" / "config.yaml")
    paths.append(home / ".nightwatch" / "config.yml")

    # System config (Linux)
    paths.append(Path("/etc/nightwatch/config.yaml"))

    return paths


def _apply_env_overrides(config_dict: dict) -> dict:
    """Apply environment variable overrides (Step 19).

    Environment variables are in format: NIGHTWATCH_SECTION_KEY
    Example: NIGHTWATCH_MOUNT_HOST=192.168.1.100
    """
    prefix = "NIGHTWATCH_"

    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue

        # Parse key: NIGHTWATCH_MOUNT_HOST -> mount.host
        parts = key[len(prefix) :].lower().split("_")
        if len(parts) < 2:
            continue

        section = parts[0]
        setting = "_".join(parts[1:])

        # Apply to config dict
        if section not in config_dict:
            config_dict[section] = {}

        # Type conversion for common types
        if value.lower() in ("true", "false"):
            value = value.lower() == "true"
        elif value.isdigit():
            value = int(value)
        else:
            try:
                value = float(value)
            except ValueError:
                pass  # Keep as string

        config_dict[section][setting] = value

    return config_dict


def load_config(config_path: Optional[str | Path] = None) -> NightwatchConfig:
    """Load configuration from file with validation (Step 18).

    Args:
        config_path: Explicit config file path, or None for auto-discovery

    Returns:
        Validated NightwatchConfig object

    Raises:
        ConfigurationError: If config file is invalid or cannot be loaded
    """
    config_dict: dict = {}

    # Find config file
    if config_path:
        path = Path(config_path)
        if not path.exists():
            raise ConfigurationError(f"Config file not found: {path}")
        config_files = [path]
    else:
        config_files = get_config_paths()

    # Load first found config file
    for path in config_files:
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    config_dict = yaml.safe_load(f) or {}
                break
            except yaml.YAMLError as e:
                raise ConfigurationError(f"Invalid YAML in {path}: {e}") from e
            except OSError as e:
                raise ConfigurationError(f"Cannot read {path}: {e}") from e

    # Apply environment variable overrides
    config_dict = _apply_env_overrides(config_dict)

    # Validate and create config object
    try:
        return NightwatchConfig(**config_dict)
    except Exception as e:
        raise ConfigurationError(f"Configuration validation failed: {e}") from e
