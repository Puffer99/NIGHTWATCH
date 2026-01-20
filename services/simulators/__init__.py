"""
NIGHTWATCH Simulators Package

Hardware-in-loop simulators for testing without physical hardware.
These simulators implement the same protocols as real devices:
- LX200 protocol for mount simulation
- Ecowitt HTTP API for weather simulation
- ZWO ASI SDK for camera simulation
- PHD2 JSON-RPC for guider simulation

All simulators support:
- Configurable behavior and responses
- Fault injection for error testing
- Realistic timing and delays
- State persistence during session
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


class SimulatorState(Enum):
    """Common states for all simulators."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    PAUSED = "paused"


@dataclass
class FaultConfig:
    """Configuration for fault injection."""
    enabled: bool = False
    fault_type: str = "none"  # "timeout", "error", "corrupt", "disconnect"
    probability: float = 0.0  # 0.0 to 1.0
    delay_ms: int = 0  # Additional delay before fault
    message: str = ""  # Custom error message


@dataclass
class SimulatorConfig:
    """Base configuration for simulators."""
    name: str = "simulator"
    host: str = "localhost"
    port: int = 0
    log_commands: bool = True
    response_delay_ms: int = 0  # Simulated latency
    fault_config: FaultConfig = field(default_factory=FaultConfig)


@dataclass
class SimulatorStats:
    """Statistics tracked by simulators."""
    started_at: Optional[datetime] = None
    commands_received: int = 0
    commands_succeeded: int = 0
    commands_failed: int = 0
    faults_injected: int = 0
    bytes_received: int = 0
    bytes_sent: int = 0

    def reset(self) -> None:
        """Reset all statistics."""
        self.started_at = None
        self.commands_received = 0
        self.commands_succeeded = 0
        self.commands_failed = 0
        self.faults_injected = 0
        self.bytes_received = 0
        self.bytes_sent = 0


class BaseSimulator:
    """
    Base class for all hardware simulators.

    Provides common functionality:
    - State management
    - Statistics tracking
    - Fault injection
    - Logging
    """

    def __init__(self, config: Optional[SimulatorConfig] = None):
        self.config = config or SimulatorConfig()
        self.state = SimulatorState.STOPPED
        self.stats = SimulatorStats()
        self._command_log: List[Dict[str, Any]] = []

    async def start(self) -> bool:
        """Start the simulator. Override in subclasses."""
        self.state = SimulatorState.RUNNING
        self.stats.started_at = datetime.now()
        return True

    async def stop(self) -> bool:
        """Stop the simulator. Override in subclasses."""
        self.state = SimulatorState.STOPPED
        return True

    def is_running(self) -> bool:
        """Check if simulator is running."""
        return self.state == SimulatorState.RUNNING

    def get_stats(self) -> Dict[str, Any]:
        """Get simulator statistics."""
        return {
            "name": self.config.name,
            "state": self.state.value,
            "started_at": self.stats.started_at.isoformat() if self.stats.started_at else None,
            "commands_received": self.stats.commands_received,
            "commands_succeeded": self.stats.commands_succeeded,
            "commands_failed": self.stats.commands_failed,
            "faults_injected": self.stats.faults_injected,
            "bytes_received": self.stats.bytes_received,
            "bytes_sent": self.stats.bytes_sent,
        }

    def log_command(self, command: str, response: str, success: bool) -> None:
        """Log a command for debugging."""
        if self.config.log_commands:
            self._command_log.append({
                "timestamp": datetime.now().isoformat(),
                "command": command,
                "response": response,
                "success": success,
            })
            # Keep only last 1000 commands
            if len(self._command_log) > 1000:
                self._command_log = self._command_log[-1000:]

    def get_command_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent command log entries."""
        return self._command_log[-limit:]

    def should_inject_fault(self) -> bool:
        """Check if a fault should be injected based on config."""
        import random
        if not self.config.fault_config.enabled:
            return False
        return random.random() < self.config.fault_config.probability

    def inject_fault(self) -> str:
        """Inject a fault and return error message."""
        self.stats.faults_injected += 1
        fault_type = self.config.fault_config.fault_type
        message = self.config.fault_config.message or f"Simulated {fault_type} fault"
        return message


# Import simulators for easy access
from .mount_simulator import MountSimulator, MountSimulatorConfig, MountState, TrackingRate
from .weather_simulator import WeatherSimulator, WeatherSimulatorConfig, WeatherScenario
from .guider_simulator import GuiderSimulator, GuiderSimulatorConfig, RMSQuality, GuideState


# Version info
__version__ = "0.1.0"
__all__ = [
    # Base classes
    "SimulatorState",
    "FaultConfig",
    "SimulatorConfig",
    "SimulatorStats",
    "BaseSimulator",
    # Mount simulator (Steps 521-522)
    "MountSimulator",
    "MountSimulatorConfig",
    "MountState",
    "TrackingRate",
    # Weather simulator (Step 527)
    "WeatherSimulator",
    "WeatherSimulatorConfig",
    "WeatherScenario",
    # Guider simulator (Step 535)
    "GuiderSimulator",
    "GuiderSimulatorConfig",
    "RMSQuality",
    "GuideState",
]
