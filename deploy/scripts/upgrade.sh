#!/usr/bin/env bash
#
# NIGHTWATCH Upgrade Script
#
# Updates an existing NIGHTWATCH installation to the latest version.
# Preserves configuration and data while updating code and dependencies.
#
# Usage:
#   sudo ./upgrade.sh [--prefix /opt/nightwatch] [--backup]
#
# Options:
#   --prefix DIR  Installation directory (default: /opt/nightwatch)
#   --backup      Create full backup before upgrade
#   --no-deps     Skip dependency update
#   --branch NAME Git branch to use (default: main)
#   --help        Show this help message

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

INSTALL_PREFIX="/opt/nightwatch"
CREATE_BACKUP=false
UPDATE_DEPS=true
GIT_BRANCH="main"
BACKUP_DIR="/var/backups/nightwatch"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# =============================================================================
# Pre-upgrade Checks
# =============================================================================

check_installation() {
    log_info "Checking existing installation..."

    if [[ ! -d "$INSTALL_PREFIX" ]]; then
        die "NIGHTWATCH not found at $INSTALL_PREFIX. Run install.sh first."
    fi

    if [[ ! -d "$INSTALL_PREFIX/.git" ]]; then
        die "Installation at $INSTALL_PREFIX is not a git repository"
    fi

    if [[ ! -d "$INSTALL_PREFIX/venv" ]]; then
        die "Virtual environment not found at $INSTALL_PREFIX/venv"
    fi

    # Get current version
    cd "$INSTALL_PREFIX"
    CURRENT_COMMIT=$(git rev-parse --short HEAD)
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    log_success "Found installation at $INSTALL_PREFIX"
    log_info "Current version: $CURRENT_BRANCH @ $CURRENT_COMMIT"
}

check_services() {
    log_info "Checking service status..."

    SERVICES_RUNNING=false

    if systemctl is-active --quiet nightwatch.service 2>/dev/null; then
        log_warn "nightwatch.service is running"
        SERVICES_RUNNING=true
    fi

    if systemctl is-active --quiet nightwatch-wyoming.service 2>/dev/null; then
        log_warn "nightwatch-wyoming.service is running"
        SERVICES_RUNNING=true
    fi

    if $SERVICES_RUNNING; then
        log_warn "Services will be stopped during upgrade"
        read -p "Continue? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            die "Upgrade cancelled"
        fi
    fi
}

# =============================================================================
# Backup
# =============================================================================

create_backup() {
    if ! $CREATE_BACKUP; then
        return
    fi

    log_info "Creating backup..."

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_PATH="$BACKUP_DIR/nightwatch_$TIMESTAMP"

    mkdir -p "$BACKUP_PATH"

    # Backup configuration
    if [[ -f /etc/nightwatch/config.yaml ]]; then
        cp /etc/nightwatch/config.yaml "$BACKUP_PATH/"
    fi

    # Backup data directory (optional, can be large)
    if [[ -d /var/lib/nightwatch ]]; then
        cp -r /var/lib/nightwatch "$BACKUP_PATH/lib/"
    fi

    # Backup logs
    if [[ -d /var/log/nightwatch ]]; then
        cp -r /var/log/nightwatch "$BACKUP_PATH/logs/"
    fi

    # Record current git state
    cd "$INSTALL_PREFIX"
    git rev-parse HEAD > "$BACKUP_PATH/git_commit"
    git diff > "$BACKUP_PATH/git_diff.patch" 2>/dev/null || true

    log_success "Backup created at $BACKUP_PATH"
}

# =============================================================================
# Stop Services
# =============================================================================

stop_services() {
    log_info "Stopping services..."

    systemctl stop nightwatch.service 2>/dev/null || true
    systemctl stop nightwatch-wyoming.service 2>/dev/null || true

    # Wait for graceful shutdown
    sleep 2

    log_success "Services stopped"
}

# =============================================================================
# Update Code
# =============================================================================

update_code() {
    log_info "Updating code from git..."

    cd "$INSTALL_PREFIX"

    # Stash any local changes
    if [[ -n $(git status --porcelain) ]]; then
        log_warn "Local changes detected, stashing..."
        git stash push -m "upgrade_$(date +%Y%m%d_%H%M%S)"
    fi

    # Fetch and update
    git fetch origin

    # Check for updates
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/$GIT_BRANCH)

    if [[ "$LOCAL" == "$REMOTE" ]]; then
        log_info "Already up to date"
    else
        log_info "Updating from $LOCAL to $REMOTE"
        git checkout $GIT_BRANCH
        git reset --hard origin/$GIT_BRANCH
    fi

    NEW_COMMIT=$(git rev-parse --short HEAD)
    log_success "Code updated to $GIT_BRANCH @ $NEW_COMMIT"
}

# =============================================================================
# Update Dependencies
# =============================================================================

update_dependencies() {
    if ! $UPDATE_DEPS; then
        log_info "Skipping dependency update (--no-deps)"
        return
    fi

    log_info "Updating Python dependencies..."

    source "$INSTALL_PREFIX/venv/bin/activate"

    # Upgrade pip first
    pip install --upgrade pip wheel setuptools

    # Update from requirements files
    if [[ -f "$INSTALL_PREFIX/services/requirements.txt" ]]; then
        pip install --upgrade -r "$INSTALL_PREFIX/services/requirements.txt"
    fi

    if [[ -f "$INSTALL_PREFIX/voice/requirements.txt" ]]; then
        pip install --upgrade -r "$INSTALL_PREFIX/voice/requirements.txt" || log_warn "Some voice deps may have failed"
    fi

    log_success "Dependencies updated"
}

# =============================================================================
# Update Systemd Services
# =============================================================================

update_services() {
    log_info "Updating systemd services..."

    if [[ -f "$INSTALL_PREFIX/deploy/systemd/nightwatch.service" ]]; then
        cp "$INSTALL_PREFIX/deploy/systemd/nightwatch.service" /etc/systemd/system/
        cp "$INSTALL_PREFIX/deploy/systemd/nightwatch-wyoming.service" /etc/systemd/system/
        systemctl daemon-reload
        log_success "Systemd services updated"
    fi
}

# =============================================================================
# Start Services
# =============================================================================

start_services() {
    log_info "Starting services..."

    # Check if services were enabled
    if systemctl is-enabled --quiet nightwatch-wyoming.service 2>/dev/null; then
        systemctl start nightwatch-wyoming.service
        log_success "nightwatch-wyoming.service started"
    fi

    if systemctl is-enabled --quiet nightwatch.service 2>/dev/null; then
        systemctl start nightwatch.service
        log_success "nightwatch.service started"
    fi
}

# =============================================================================
# Verify Upgrade
# =============================================================================

verify_upgrade() {
    log_info "Verifying upgrade..."

    # Check Python can import nightwatch
    source "$INSTALL_PREFIX/venv/bin/activate"

    if python -c "import nightwatch" 2>/dev/null; then
        log_success "Python imports working"
    else
        log_warn "Python import check failed (may be normal for partial install)"
    fi

    # Check service status
    if systemctl is-active --quiet nightwatch.service 2>/dev/null; then
        log_success "nightwatch.service is running"
    fi

    if systemctl is-active --quiet nightwatch-wyoming.service 2>/dev/null; then
        log_success "nightwatch-wyoming.service is running"
    fi
}

# =============================================================================
# Parse Arguments
# =============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --prefix)
                INSTALL_PREFIX="$2"
                shift 2
                ;;
            --backup)
                CREATE_BACKUP=true
                shift
                ;;
            --no-deps)
                UPDATE_DEPS=false
                shift
                ;;
            --branch)
                GIT_BRANCH="$2"
                shift 2
                ;;
            --help|-h)
                echo "NIGHTWATCH Upgrade Script"
                echo ""
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --prefix DIR  Installation directory (default: /opt/nightwatch)"
                echo "  --backup      Create full backup before upgrade"
                echo "  --no-deps     Skip dependency update"
                echo "  --branch NAME Git branch (default: main)"
                echo "  --help        Show this help message"
                exit 0
                ;;
            *)
                die "Unknown option: $1"
                ;;
        esac
    done
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo ""
    echo "=========================================="
    echo " NIGHTWATCH Upgrade Script"
    echo "=========================================="
    echo ""

    parse_args "$@"

    # Check if running as root for system installation
    if [[ $EUID -ne 0 ]] && [[ "$INSTALL_PREFIX" == "/opt/nightwatch" ]]; then
        die "Please run as root for system-wide upgrade: sudo $0"
    fi

    check_installation
    check_services
    create_backup
    stop_services
    update_code
    update_dependencies
    update_services
    start_services
    verify_upgrade

    echo ""
    echo "=========================================="
    echo " Upgrade Complete!"
    echo "=========================================="
    echo ""
    log_success "NIGHTWATCH upgraded successfully"
    echo ""
    echo "Check logs: journalctl -u nightwatch -f"
    echo ""
}

main "$@"
