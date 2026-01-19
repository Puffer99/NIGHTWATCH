#!/usr/bin/env bash
#
# NIGHTWATCH Installation Script
#
# Installs NIGHTWATCH autonomous observatory controller on Linux systems.
# Supports Ubuntu/Debian and macOS (with Homebrew).
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/THOClabs/NIGHTWATCH/main/deploy/scripts/install.sh | bash
#   # or
#   ./install.sh [--dev] [--no-voice] [--prefix /opt/nightwatch]
#
# Options:
#   --dev        Install development dependencies (pytest, ruff, mypy)
#   --no-voice   Skip voice pipeline dependencies (Whisper, Piper)
#   --prefix     Installation directory (default: /opt/nightwatch)
#   --user       Install for current user only (default: system-wide)
#   --help       Show this help message

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

NIGHTWATCH_VERSION="0.1.0"
NIGHTWATCH_REPO="https://github.com/THOClabs/NIGHTWATCH.git"
MIN_PYTHON_VERSION="3.10"
RECOMMENDED_PYTHON_VERSION="3.11"

# Default options
INSTALL_PREFIX="/opt/nightwatch"
INSTALL_DEV=false
INSTALL_VOICE=true
INSTALL_USER=false
CONFIG_DIR="/etc/nightwatch"
DATA_DIR="/data"
LOG_DIR="/var/log/nightwatch"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

die() {
    log_error "$1"
    exit 1
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        return 0
    else
        return 1
    fi
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            echo "debian"
        elif command -v dnf &> /dev/null; then
            echo "fedora"
        elif command -v pacman &> /dev/null; then
            echo "arch"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

# Compare version numbers
version_ge() {
    # Returns 0 if $1 >= $2
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

# =============================================================================
# Step 617: Python Version Check
# =============================================================================

check_python() {
    log_info "Checking Python installation..."

    # Find Python
    PYTHON_CMD=""
    for cmd in python3.11 python3.10 python3; do
        if command -v "$cmd" &> /dev/null; then
            PYTHON_CMD="$cmd"
            break
        fi
    done

    if [[ -z "$PYTHON_CMD" ]]; then
        die "Python 3.10+ not found. Please install Python first."
    fi

    # Check version
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

    if ! version_ge "$PYTHON_VERSION" "$MIN_PYTHON_VERSION"; then
        die "Python $PYTHON_VERSION is too old. Minimum required: $MIN_PYTHON_VERSION"
    fi

    log_success "Found Python $PYTHON_VERSION ($PYTHON_CMD)"

    if ! version_ge "$PYTHON_VERSION" "$RECOMMENDED_PYTHON_VERSION"; then
        log_warn "Python $RECOMMENDED_PYTHON_VERSION is recommended for best performance"
    fi

    export PYTHON_CMD
}

# =============================================================================
# Step 618: System Dependency Installation
# =============================================================================

install_system_deps() {
    log_info "Installing system dependencies..."

    OS=$(detect_os)

    case "$OS" in
        debian)
            log_info "Detected Debian/Ubuntu system"
            if check_root; then
                apt-get update
                apt-get install -y \
                    git \
                    build-essential \
                    python3-dev \
                    python3-pip \
                    python3-venv \
                    libffi-dev \
                    libssl-dev \
                    portaudio19-dev \
                    libsndfile1 \
                    ffmpeg \
                    libatlas-base-dev

                if $INSTALL_VOICE; then
                    apt-get install -y \
                        libespeak-ng1 \
                        espeak-ng
                fi
            else
                log_warn "Not running as root. Skipping system package installation."
                log_warn "You may need to install: git python3-dev python3-venv portaudio19-dev"
            fi
            ;;

        fedora)
            log_info "Detected Fedora/RHEL system"
            if check_root; then
                dnf install -y \
                    git \
                    gcc \
                    python3-devel \
                    python3-pip \
                    python3-virtualenv \
                    libffi-devel \
                    openssl-devel \
                    portaudio-devel \
                    libsndfile \
                    ffmpeg
            else
                log_warn "Not running as root. Skipping system package installation."
            fi
            ;;

        macos)
            log_info "Detected macOS"
            if ! command -v brew &> /dev/null; then
                die "Homebrew not found. Please install from https://brew.sh"
            fi

            brew install \
                git \
                python@3.11 \
                portaudio \
                libsndfile \
                ffmpeg || true

            if $INSTALL_VOICE; then
                brew install espeak-ng || true
            fi
            ;;

        *)
            log_warn "Unknown OS. Skipping system dependency installation."
            log_warn "Please ensure git, python3, and audio libraries are installed."
            ;;
    esac

    log_success "System dependencies installed"
}

# =============================================================================
# Step 619: Virtual Environment Creation
# =============================================================================

create_venv() {
    log_info "Creating virtual environment..."

    VENV_DIR="$INSTALL_PREFIX/venv"

    if [[ -d "$VENV_DIR" ]]; then
        log_warn "Virtual environment already exists at $VENV_DIR"
        read -p "Remove and recreate? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$VENV_DIR"
        else
            log_info "Keeping existing virtual environment"
            return
        fi
    fi

    $PYTHON_CMD -m venv "$VENV_DIR"

    # Activate venv for subsequent commands
    source "$VENV_DIR/bin/activate"

    # Upgrade pip
    pip install --upgrade pip wheel setuptools

    log_success "Virtual environment created at $VENV_DIR"
}

# =============================================================================
# Step 620: Pip Dependency Installation
# =============================================================================

install_python_deps() {
    log_info "Installing Python dependencies..."

    VENV_DIR="$INSTALL_PREFIX/venv"
    source "$VENV_DIR/bin/activate"

    # Core service dependencies
    if [[ -f "$INSTALL_PREFIX/services/requirements.txt" ]]; then
        pip install -r "$INSTALL_PREFIX/services/requirements.txt"
    else
        # Fallback: install core packages directly
        pip install \
            aiohttp \
            asyncio \
            pydantic \
            pyyaml \
            skyfield \
            pyserial \
            numpy \
            requests
    fi

    # Voice pipeline dependencies
    if $INSTALL_VOICE; then
        log_info "Installing voice pipeline dependencies..."
        if [[ -f "$INSTALL_PREFIX/voice/requirements.txt" ]]; then
            pip install -r "$INSTALL_PREFIX/voice/requirements.txt"
        else
            pip install \
                faster-whisper \
                piper-tts \
                sounddevice \
                soundfile \
                webrtcvad || log_warn "Some voice dependencies may have failed"
        fi
    fi

    # Development dependencies
    if $INSTALL_DEV; then
        log_info "Installing development dependencies..."
        pip install \
            pytest \
            pytest-asyncio \
            pytest-cov \
            ruff \
            mypy \
            pre-commit
    fi

    log_success "Python dependencies installed"
}

# =============================================================================
# Step 621: Configuration Template Generation
# =============================================================================

create_config() {
    log_info "Creating configuration..."

    # Create config directory
    if check_root; then
        mkdir -p "$CONFIG_DIR"
    else
        CONFIG_DIR="$HOME/.nightwatch"
        mkdir -p "$CONFIG_DIR"
    fi

    CONFIG_FILE="$CONFIG_DIR/config.yaml"

    if [[ -f "$CONFIG_FILE" ]]; then
        log_warn "Configuration already exists at $CONFIG_FILE"
        log_info "Skipping config generation (backup at $CONFIG_FILE.example)"
        cp "$CONFIG_FILE" "$CONFIG_FILE.backup.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
    fi

    # Generate config template
    cat > "$CONFIG_FILE.example" << 'CONFIGEOF'
# NIGHTWATCH Configuration
# Generated by install.sh

# Site location (required for ephemeris calculations)
site:
  name: "My Observatory"
  latitude: 39.5501      # Degrees North
  longitude: -119.8143   # Degrees East (negative for West)
  elevation: 1373        # Meters above sea level
  timezone: "America/Los_Angeles"

# Mount configuration
mount:
  type: "lx200"          # lx200, onstepx, indi, alpaca
  host: "localhost"
  port: 9999
  # serial_port: "/dev/ttyUSB0"  # For serial connection
  # baudrate: 9600

# Weather station
weather:
  enabled: true
  type: "ecowitt"
  host: "192.168.1.100"
  poll_interval_sec: 60

# Safety thresholds (per POS Day 4)
safety:
  wind_limit_mph: 25
  humidity_limit_pct: 85
  temp_min_c: -20
  temp_max_c: 40
  rain_close_immediate: true
  rain_holdoff_minutes: 30

# Voice pipeline
voice:
  enabled: true
  stt_model: "base.en"     # tiny.en, base.en, small.en, medium.en
  tts_voice: "en_US-lessac-medium"
  wake_word: "nightwatch"
  device: "cuda"           # cuda, cpu

# LLM configuration (local Llama)
llm:
  model: "llama-3.2-3b-instruct"
  max_tokens: 512
  temperature: 0.7
  device: "cuda"

# Camera (ZWO ASI)
camera:
  enabled: false
  # type: "zwo"
  # camera_index: 0

# Logging
logging:
  level: "INFO"
  file: "/var/log/nightwatch/nightwatch.log"
  max_size_mb: 10
  backup_count: 5
CONFIGEOF

    if [[ ! -f "$CONFIG_FILE" ]]; then
        cp "$CONFIG_FILE.example" "$CONFIG_FILE"
        log_success "Configuration created at $CONFIG_FILE"
        log_info "Please edit $CONFIG_FILE with your site and hardware settings"
    fi
}

# =============================================================================
# Clone/Update Repository
# =============================================================================

clone_repo() {
    log_info "Setting up NIGHTWATCH installation directory..."

    if [[ -d "$INSTALL_PREFIX/.git" ]]; then
        log_info "Existing installation found, updating..."
        cd "$INSTALL_PREFIX"
        git fetch origin
        git reset --hard origin/main
    else
        if [[ -d "$INSTALL_PREFIX" ]] && [[ "$(ls -A $INSTALL_PREFIX)" ]]; then
            die "Installation directory $INSTALL_PREFIX exists and is not empty"
        fi

        mkdir -p "$INSTALL_PREFIX"
        git clone "$NIGHTWATCH_REPO" "$INSTALL_PREFIX"
    fi

    log_success "NIGHTWATCH code installed at $INSTALL_PREFIX"
}

# =============================================================================
# Create Directories and User
# =============================================================================

setup_directories() {
    log_info "Setting up directories..."

    if check_root; then
        # Create nightwatch user if doesn't exist
        if ! id -u nightwatch &>/dev/null; then
            useradd -r -s /bin/false -d "$INSTALL_PREFIX" nightwatch
            log_success "Created nightwatch user"
        fi

        # Create directories
        mkdir -p "$LOG_DIR"
        mkdir -p "$DATA_DIR/captures"
        mkdir -p /var/lib/nightwatch

        # Set ownership
        chown -R nightwatch:nightwatch "$INSTALL_PREFIX"
        chown -R nightwatch:nightwatch "$LOG_DIR"
        chown -R nightwatch:nightwatch "$DATA_DIR"
        chown -R nightwatch:nightwatch /var/lib/nightwatch
        chown nightwatch:nightwatch "$CONFIG_DIR/config.yaml" 2>/dev/null || true

        # Add user to hardware groups
        usermod -aG dialout nightwatch 2>/dev/null || true
        usermod -aG gpio nightwatch 2>/dev/null || true
        usermod -aG audio nightwatch 2>/dev/null || true

        log_success "Directories and permissions configured"
    else
        mkdir -p "$HOME/.nightwatch/data"
        mkdir -p "$HOME/.nightwatch/logs"
        log_info "User installation: data in $HOME/.nightwatch/"
    fi
}

# =============================================================================
# Install Systemd Services
# =============================================================================

install_services() {
    if ! check_root; then
        log_info "Skipping systemd service installation (not root)"
        return
    fi

    log_info "Installing systemd services..."

    if [[ -f "$INSTALL_PREFIX/deploy/systemd/nightwatch.service" ]]; then
        cp "$INSTALL_PREFIX/deploy/systemd/nightwatch.service" /etc/systemd/system/
        cp "$INSTALL_PREFIX/deploy/systemd/nightwatch-wyoming.service" /etc/systemd/system/
        systemctl daemon-reload
        log_success "Systemd services installed"
        log_info "Enable with: sudo systemctl enable nightwatch.service"
    else
        log_warn "Systemd service files not found"
    fi
}

# =============================================================================
# Parse Arguments
# =============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dev)
                INSTALL_DEV=true
                shift
                ;;
            --no-voice)
                INSTALL_VOICE=false
                shift
                ;;
            --prefix)
                INSTALL_PREFIX="$2"
                shift 2
                ;;
            --user)
                INSTALL_USER=true
                INSTALL_PREFIX="$HOME/.local/nightwatch"
                CONFIG_DIR="$HOME/.nightwatch"
                shift
                ;;
            --help|-h)
                echo "NIGHTWATCH Installation Script v$NIGHTWATCH_VERSION"
                echo ""
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --dev        Install development dependencies"
                echo "  --no-voice   Skip voice pipeline dependencies"
                echo "  --prefix DIR Installation directory (default: /opt/nightwatch)"
                echo "  --user       Install for current user only"
                echo "  --help       Show this help message"
                exit 0
                ;;
            *)
                die "Unknown option: $1"
                ;;
        esac
    done
}

# =============================================================================
# Main Installation
# =============================================================================

main() {
    echo ""
    echo "=========================================="
    echo " NIGHTWATCH Installation Script v$NIGHTWATCH_VERSION"
    echo "=========================================="
    echo ""

    parse_args "$@"

    log_info "Installation prefix: $INSTALL_PREFIX"
    log_info "Voice pipeline: $INSTALL_VOICE"
    log_info "Dev dependencies: $INSTALL_DEV"
    echo ""

    # Run installation steps
    check_python
    install_system_deps
    clone_repo
    create_venv
    install_python_deps
    create_config
    setup_directories
    install_services

    echo ""
    echo "=========================================="
    echo " Installation Complete!"
    echo "=========================================="
    echo ""
    log_success "NIGHTWATCH installed at $INSTALL_PREFIX"
    echo ""
    echo "Next steps:"
    echo "  1. Edit configuration: $CONFIG_DIR/config.yaml"
    echo "  2. Start NIGHTWATCH:"
    if check_root; then
        echo "     sudo systemctl start nightwatch.service"
    else
        echo "     source $INSTALL_PREFIX/venv/bin/activate"
        echo "     python -m nightwatch.main --config $CONFIG_DIR/config.yaml"
    fi
    echo ""
    echo "Documentation: https://github.com/THOClabs/NIGHTWATCH"
    echo ""
}

# Run main
main "$@"
