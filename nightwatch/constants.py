"""
NIGHTWATCH Shared Constants

Centralizes magic numbers, default values, and configuration constants used
across the NIGHTWATCH observatory control system. This module eliminates
scattered literals and provides a single source of truth for system parameters.

Constants are organized by category:
    - Safety thresholds (from POS Panel recommendations)
    - Timing and intervals
    - Network and protocol defaults
    - Physical limits and positions
    - File paths and formats

All thresholds have been calibrated per POS Panel deliberations for the
Nevada dark sky site at ~6000ft elevation.
"""

from typing import Final

# =============================================================================
# Version and Identity
# =============================================================================

NIGHTWATCH_VERSION: Final[str] = "0.1.0-dev"
NIGHTWATCH_NAME: Final[str] = "NIGHTWATCH"
NIGHTWATCH_AUTHOR: Final[str] = "THOC Labs"

# =============================================================================
# Safety Thresholds (POS Panel Calibrated)
# =============================================================================
# Source: POS Day 4 deliberations, calibrated for Nevada 6000ft elevation

# Wind limits (mph)
WIND_LIMIT_MPH: Final[float] = 25.0
WIND_GUST_LIMIT_MPH: Final[float] = 35.0
WIND_HYSTERESIS_MPH: Final[float] = 5.0  # Must drop below limit - hysteresis to clear

# Wind condition thresholds (mph)
WIND_CALM_THRESHOLD_MPH: Final[float] = 5.0
WIND_LIGHT_THRESHOLD_MPH: Final[float] = 15.0
WIND_MODERATE_THRESHOLD_MPH: Final[float] = 25.0

# Humidity limits (percent)
HUMIDITY_LIMIT_PERCENT: Final[float] = 85.0
HUMIDITY_HYSTERESIS_PERCENT: Final[float] = 5.0

# Temperature limits (Fahrenheit)
TEMP_MIN_F: Final[float] = 20.0
TEMP_MAX_F: Final[float] = 100.0

# Dew point margin (degrees F)
DEW_POINT_MARGIN_F: Final[float] = 5.0

# Cloud coverage limits (percent)
CLOUD_LIMIT_PERCENT: Final[float] = 50.0
CLOUD_HYSTERESIS_PERCENT: Final[float] = 10.0

# Sun altitude for daylight (degrees)
SUN_ALTITUDE_DAYLIGHT_DEG: Final[float] = -6.0  # Civil twilight
SUN_ALTITUDE_ASTRONOMICAL_DEG: Final[float] = -18.0  # Astronomical twilight

# =============================================================================
# Timing Constants
# =============================================================================

# Command and operation timeouts (seconds)
DEFAULT_COMMAND_TIMEOUT_SEC: Final[float] = 5.0
SLEW_TIMEOUT_SEC: Final[float] = 300.0  # 5 minutes for long slews
PARK_TIMEOUT_SEC: Final[float] = 180.0  # 3 minutes for parking
SOLVE_TIMEOUT_SEC: Final[float] = 30.0  # Plate solving timeout
CAPTURE_TIMEOUT_SEC: Final[float] = 600.0  # 10 minutes for long exposures

# Motor and hardware timeouts (seconds)
MOTOR_TIMEOUT_SEC: Final[float] = 60.0  # Roof motor max run time
PARK_VERIFY_TIMEOUT_SEC: Final[float] = 10.0

# Polling intervals (seconds)
STATUS_POLL_INTERVAL_SEC: Final[float] = 1.0
WEATHER_POLL_INTERVAL_SEC: Final[float] = 30.0
SAFETY_CHECK_INTERVAL_SEC: Final[float] = 10.0
HEALTH_CHECK_INTERVAL_SEC: Final[float] = 60.0

# Holdoff and hysteresis periods (minutes)
RAIN_HOLDOFF_MIN: Final[float] = 30.0  # Wait after rain clears
SENSOR_TIMEOUT_MIN: Final[float] = 5.0  # Sensor data staleness

# Alert rate limiting
ALERT_RATE_LIMIT_HOURS: Final[float] = 1.0  # Max 1 alert per type per hour

# =============================================================================
# Network Defaults
# =============================================================================

# OnStepX / Mount control
MOUNT_DEFAULT_HOST: Final[str] = "192.168.1.100"
MOUNT_DEFAULT_TCP_PORT: Final[int] = 9999
MOUNT_DEFAULT_SERIAL_BAUDRATE: Final[int] = 115200

# INDI server
INDI_DEFAULT_HOST: Final[str] = "localhost"
INDI_DEFAULT_PORT: Final[int] = 7624

# PHD2 guiding
PHD2_DEFAULT_HOST: Final[str] = "localhost"
PHD2_DEFAULT_PORT: Final[int] = 4400

# ASCOM Alpaca
ALPACA_DEFAULT_PORT: Final[int] = 11111
ALPACA_DISCOVERY_PORT: Final[int] = 32227

# Wyoming protocol (voice)
WYOMING_DEFAULT_PORT: Final[int] = 10400

# =============================================================================
# Protocol Constants
# =============================================================================

# LX200 protocol
LX200_TERMINATOR: Final[str] = "#"
LX200_ACK: Final[str] = "\x06"

# Serial communication
DEFAULT_SERIAL_BAUDRATE: Final[int] = 115200
DEFAULT_SERIAL_TIMEOUT_SEC: Final[float] = 1.0

# Encoder bridge
ENCODER_DEFAULT_BAUDRATE: Final[int] = 115200

# =============================================================================
# Physical Limits and Positions
# =============================================================================

# Roof positions (percent)
ROOF_OPEN_POSITION: Final[int] = 100
ROOF_CLOSED_POSITION: Final[int] = 0

# Motor current limits (amps)
MOTOR_CURRENT_LIMIT_A: Final[float] = 5.0

# Altitude limits (degrees)
ALTITUDE_MIN_DEG: Final[float] = 0.0
ALTITUDE_MAX_DEG: Final[float] = 90.0
ALTITUDE_HORIZON_LIMIT_DEG: Final[float] = 15.0  # Below this, unsafe to observe

# Position precision
RA_PRECISION_ARCSEC: Final[float] = 1.0
DEC_PRECISION_ARCSEC: Final[float] = 1.0

# =============================================================================
# Camera and Imaging
# =============================================================================

# Default camera settings
DEFAULT_CAMERA_GAIN: Final[int] = 100
DEFAULT_CAMERA_BINNING: Final[int] = 1
DEFAULT_EXPOSURE_SEC: Final[float] = 1.0

# Binning options
BINNING_1X1: Final[int] = 1
BINNING_2X2: Final[int] = 2
BINNING_4X4: Final[int] = 4

# Cooling
COOLING_SETPOINT_C: Final[float] = -10.0
COOLING_TOLERANCE_C: Final[float] = 1.0

# =============================================================================
# Power Management
# =============================================================================
# UPS thresholds (battery percent)

UPS_PARK_THRESHOLD_PERCENT: Final[int] = 50  # Park telescope at this level
UPS_SHUTDOWN_THRESHOLD_PERCENT: Final[int] = 20  # Emergency shutdown

# =============================================================================
# File Paths and Formats
# =============================================================================

# Configuration file search paths
CONFIG_FILENAME: Final[str] = "nightwatch.yaml"
CONFIG_SEARCH_PATHS: Final[tuple[str, ...]] = (
    "./nightwatch.yaml",
    "~/.nightwatch/config.yaml",
    "/etc/nightwatch/config.yaml",
)

# Log settings
LOG_MAX_BYTES: Final[int] = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT: Final[int] = 5
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

# Image formats
FITS_EXTENSION: Final[str] = ".fits"
SER_EXTENSION: Final[str] = ".ser"
PNG_EXTENSION: Final[str] = ".png"

# =============================================================================
# Catalog and Astrometry
# =============================================================================

# Catalog database
CATALOG_DB_FILENAME: Final[str] = "nightwatch_catalog.db"

# Messier catalog range
MESSIER_MIN: Final[int] = 1
MESSIER_MAX: Final[int] = 110

# Astrometry pixel scale hints (arcsec/pixel) for MN76 @ 610mm FL
PIXEL_SCALE_HINT_ARCSEC: Final[float] = 1.5  # Approximate for common sensors

# =============================================================================
# Voice and AI
# =============================================================================

# Whisper STT defaults
WHISPER_DEFAULT_MODEL: Final[str] = "medium"
WHISPER_DEFAULT_DEVICE: Final[str] = "cuda"
WHISPER_DEFAULT_COMPUTE_TYPE: Final[str] = "float16"

# Piper TTS defaults
PIPER_DEFAULT_MODEL: Final[str] = "en_US-lessac-medium"

# LLM defaults (Llama 3.2 local)
LLM_DEFAULT_MODEL: Final[str] = "llama3.2"
LLM_DEFAULT_MAX_TOKENS: Final[int] = 1024
LLM_DEFAULT_TEMPERATURE: Final[float] = 0.7

# Audio settings
AUDIO_SAMPLE_RATE_HZ: Final[int] = 16000
AUDIO_CHANNELS: Final[int] = 1
