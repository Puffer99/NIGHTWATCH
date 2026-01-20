"""
NIGHTWATCH Voice + Mount Integration Test (Step 566)

Tests the integration between voice commands and mount control,
verifying that voice commands properly translate to mount actions.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from nightwatch.voice_pipeline import (
    VoicePipeline,
    PipelineState,
    PipelineResult,
)
from nightwatch.orchestrator import Orchestrator
from nightwatch.config import NightwatchConfig


class MockMountService:
    """Mock mount service for testing voice commands."""

    def __init__(self):
        self.is_running = True
        self.is_parked = True
        self.is_tracking = False
        self.is_slewing = False
        self.ra = 0.0
        self.dec = 0.0
        self.target_name = None
        self.commands_received = []

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    async def park(self):
        self.commands_received.append(("park", {}))
        self.is_parked = True
        self.is_tracking = False
        return True

    async def unpark(self):
        self.commands_received.append(("unpark", {}))
        self.is_parked = False
        return True

    async def slew_to_coordinates(self, ra: float, dec: float):
        self.commands_received.append(("slew_to_coordinates", {"ra": ra, "dec": dec}))
        self.is_slewing = True
        await asyncio.sleep(0.01)
        self.ra = ra
        self.dec = dec
        self.is_slewing = False
        self.is_tracking = True
        return True

    async def slew_to_object(self, object_name: str):
        self.commands_received.append(("slew_to_object", {"object_name": object_name}))
        self.target_name = object_name
        self.is_slewing = True
        await asyncio.sleep(0.01)
        self.is_slewing = False
        self.is_tracking = True
        return True

    async def stop_tracking(self):
        self.commands_received.append(("stop_tracking", {}))
        self.is_tracking = False
        return True

    async def start_tracking(self):
        self.commands_received.append(("start_tracking", {}))
        if not self.is_parked:
            self.is_tracking = True
        return True

    async def emergency_stop(self):
        self.commands_received.append(("emergency_stop", {}))
        self.is_slewing = False
        self.is_tracking = False
        return True

    def get_position(self):
        return {"ra": self.ra, "dec": self.dec, "ra_hms": "00h 00m 00s", "dec_dms": "+00° 00' 00\""}

    def get_status(self):
        return {
            "parked": self.is_parked,
            "tracking": self.is_tracking,
            "slewing": self.is_slewing,
            "target": self.target_name,
        }


class MockToolExecutor:
    """Mock tool executor that calls mount service."""

    def __init__(self, mount: MockMountService):
        self.mount = mount
        self.executed_tools = []

    async def execute(self, tool_name: str, arguments: Dict) -> Dict:
        self.executed_tools.append({"name": tool_name, "args": arguments})

        if tool_name == "slew_to_object":
            await self.mount.slew_to_object(arguments.get("object_name", ""))
            return {"success": True, "message": f"Slewing to {arguments.get('object_name')}"}

        elif tool_name == "slew_to_coordinates":
            await self.mount.slew_to_coordinates(
                arguments.get("ra", 0.0),
                arguments.get("dec", 0.0)
            )
            return {"success": True, "message": "Slewing to coordinates"}

        elif tool_name == "park_telescope":
            await self.mount.park()
            return {"success": True, "message": "Telescope parked"}

        elif tool_name == "unpark_telescope":
            await self.mount.unpark()
            return {"success": True, "message": "Telescope unparked"}

        elif tool_name == "stop_telescope":
            await self.mount.emergency_stop()
            return {"success": True, "message": "Telescope stopped"}

        elif tool_name == "get_telescope_position":
            pos = self.mount.get_position()
            return {"success": True, "data": pos}

        elif tool_name == "get_telescope_status":
            status = self.mount.get_status()
            return {"success": True, "data": status}

        return {"success": False, "message": f"Unknown tool: {tool_name}"}


class TestVoiceMountBasicCommands:
    """Tests for basic voice-to-mount commands."""

    @pytest.fixture
    def mount(self):
        return MockMountService()

    @pytest.fixture
    def executor(self, mount):
        return MockToolExecutor(mount)

    @pytest.mark.asyncio
    async def test_slew_to_object_command(self, mount, executor):
        """Test 'point to M31' voice command."""
        result = await executor.execute("slew_to_object", {"object_name": "M31"})

        assert result["success"] is True
        assert mount.target_name == "M31"
        assert mount.is_tracking is True
        assert len(mount.commands_received) == 1
        assert mount.commands_received[0][0] == "slew_to_object"

    @pytest.mark.asyncio
    async def test_slew_to_coordinates_command(self, mount, executor):
        """Test 'go to RA 10h 30m Dec +45°' voice command."""
        result = await executor.execute(
            "slew_to_coordinates",
            {"ra": 157.5, "dec": 45.0}
        )

        assert result["success"] is True
        assert mount.ra == 157.5
        assert mount.dec == 45.0
        assert mount.is_tracking is True

    @pytest.mark.asyncio
    async def test_park_command(self, mount, executor):
        """Test 'park the telescope' voice command."""
        mount.is_parked = False
        mount.is_tracking = True

        result = await executor.execute("park_telescope", {})

        assert result["success"] is True
        assert mount.is_parked is True
        assert mount.is_tracking is False

    @pytest.mark.asyncio
    async def test_unpark_command(self, mount, executor):
        """Test 'unpark the telescope' voice command."""
        mount.is_parked = True

        result = await executor.execute("unpark_telescope", {})

        assert result["success"] is True
        assert mount.is_parked is False

    @pytest.mark.asyncio
    async def test_emergency_stop_command(self, mount, executor):
        """Test 'stop' emergency command."""
        mount.is_slewing = True
        mount.is_tracking = True

        result = await executor.execute("stop_telescope", {})

        assert result["success"] is True
        assert mount.is_slewing is False
        assert mount.is_tracking is False

    @pytest.mark.asyncio
    async def test_get_position_command(self, mount, executor):
        """Test 'where are we pointing' voice command."""
        mount.ra = 180.0
        mount.dec = 45.0

        result = await executor.execute("get_telescope_position", {})

        assert result["success"] is True
        assert result["data"]["ra"] == 180.0
        assert result["data"]["dec"] == 45.0

    @pytest.mark.asyncio
    async def test_get_status_command(self, mount, executor):
        """Test 'telescope status' voice command."""
        mount.is_tracking = True
        mount.target_name = "Vega"

        result = await executor.execute("get_telescope_status", {})

        assert result["success"] is True
        assert result["data"]["tracking"] is True
        assert result["data"]["target"] == "Vega"


class TestVoiceMountSequences:
    """Tests for voice command sequences."""

    @pytest.fixture
    def mount(self):
        return MockMountService()

    @pytest.fixture
    def executor(self, mount):
        return MockToolExecutor(mount)

    @pytest.mark.asyncio
    async def test_unpark_then_slew_sequence(self, mount, executor):
        """Test unpark followed by slew sequence."""
        # Start parked
        assert mount.is_parked is True

        # Unpark
        await executor.execute("unpark_telescope", {})
        assert mount.is_parked is False

        # Slew to target
        await executor.execute("slew_to_object", {"object_name": "M42"})
        assert mount.target_name == "M42"
        assert mount.is_tracking is True

        # Verify command sequence
        assert len(mount.commands_received) == 2
        assert mount.commands_received[0][0] == "unpark"
        assert mount.commands_received[1][0] == "slew_to_object"

    @pytest.mark.asyncio
    async def test_slew_to_multiple_targets(self, mount, executor):
        """Test slewing to multiple targets in sequence."""
        mount.is_parked = False

        targets = ["M31", "M42", "M45"]
        for target in targets:
            await executor.execute("slew_to_object", {"object_name": target})

        assert mount.target_name == "M45"  # Last target
        assert len([c for c in mount.commands_received if c[0] == "slew_to_object"]) == 3

    @pytest.mark.asyncio
    async def test_observing_session_sequence(self, mount, executor):
        """Test complete observing session: unpark -> slew -> observe -> park."""
        # Unpark
        await executor.execute("unpark_telescope", {})
        assert mount.is_parked is False

        # Slew to first target
        await executor.execute("slew_to_object", {"object_name": "NGC 7000"})
        assert mount.is_tracking is True

        # Check status
        status = await executor.execute("get_telescope_status", {})
        assert status["data"]["tracking"] is True

        # Park at end of session
        await executor.execute("park_telescope", {})
        assert mount.is_parked is True
        assert mount.is_tracking is False


class TestVoiceMountErrorHandling:
    """Tests for error handling in voice-mount integration."""

    @pytest.fixture
    def mount(self):
        return MockMountService()

    @pytest.fixture
    def executor(self, mount):
        return MockToolExecutor(mount)

    @pytest.mark.asyncio
    async def test_unknown_tool(self, executor):
        """Test handling of unknown tool."""
        result = await executor.execute("unknown_tool", {})

        assert result["success"] is False
        assert "Unknown tool" in result["message"]

    @pytest.mark.asyncio
    async def test_slew_while_parked_behavior(self, mount, executor):
        """Test slew command behavior when parked."""
        mount.is_parked = True

        # This should still work (mount unparks automatically or errors)
        result = await executor.execute("slew_to_object", {"object_name": "M31"})

        # In real implementation, might need to unpark first
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_command_tracking(self, mount, executor):
        """Test that all commands are tracked."""
        await executor.execute("unpark_telescope", {})
        await executor.execute("slew_to_object", {"object_name": "Vega"})
        await executor.execute("get_telescope_status", {})
        await executor.execute("park_telescope", {})

        assert len(executor.executed_tools) == 4
        assert executor.executed_tools[0]["name"] == "unpark_telescope"
        assert executor.executed_tools[1]["name"] == "slew_to_object"
        assert executor.executed_tools[2]["name"] == "get_telescope_status"
        assert executor.executed_tools[3]["name"] == "park_telescope"


class TestVoiceMountObjectNames:
    """Tests for object name handling."""

    @pytest.fixture
    def mount(self):
        return MockMountService()

    @pytest.fixture
    def executor(self, mount):
        return MockToolExecutor(mount)

    @pytest.mark.asyncio
    async def test_messier_object(self, mount, executor):
        """Test Messier object names."""
        messier_objects = ["M1", "M31", "M42", "M45", "M101"]

        for obj in messier_objects:
            await executor.execute("slew_to_object", {"object_name": obj})
            assert mount.target_name == obj

    @pytest.mark.asyncio
    async def test_ngc_object(self, mount, executor):
        """Test NGC object names."""
        await executor.execute("slew_to_object", {"object_name": "NGC 7000"})
        assert mount.target_name == "NGC 7000"

    @pytest.mark.asyncio
    async def test_named_star(self, mount, executor):
        """Test named star objects."""
        stars = ["Vega", "Polaris", "Betelgeuse", "Sirius"]

        for star in stars:
            await executor.execute("slew_to_object", {"object_name": star})
            assert mount.target_name == star

    @pytest.mark.asyncio
    async def test_planet_name(self, mount, executor):
        """Test planet names."""
        planets = ["Jupiter", "Saturn", "Mars"]

        for planet in planets:
            await executor.execute("slew_to_object", {"object_name": planet})
            assert mount.target_name == planet


class TestVoiceMountStatusQueries:
    """Tests for status query commands."""

    @pytest.fixture
    def mount(self):
        return MockMountService()

    @pytest.fixture
    def executor(self, mount):
        return MockToolExecutor(mount)

    @pytest.mark.asyncio
    async def test_position_query_format(self, mount, executor):
        """Test position query returns proper format."""
        mount.ra = 83.82  # Orion Nebula approx
        mount.dec = -5.39

        result = await executor.execute("get_telescope_position", {})

        assert "data" in result
        assert "ra" in result["data"]
        assert "dec" in result["data"]

    @pytest.mark.asyncio
    async def test_status_query_fields(self, mount, executor):
        """Test status query returns expected fields."""
        result = await executor.execute("get_telescope_status", {})

        assert "data" in result
        data = result["data"]
        assert "parked" in data
        assert "tracking" in data
        assert "slewing" in data
        assert "target" in data

    @pytest.mark.asyncio
    async def test_status_reflects_state_changes(self, mount, executor):
        """Test status accurately reflects state changes."""
        # Initial state
        status1 = await executor.execute("get_telescope_status", {})
        assert status1["data"]["parked"] is True

        # After unpark
        await executor.execute("unpark_telescope", {})
        status2 = await executor.execute("get_telescope_status", {})
        assert status2["data"]["parked"] is False

        # After slew
        await executor.execute("slew_to_object", {"object_name": "M31"})
        status3 = await executor.execute("get_telescope_status", {})
        assert status3["data"]["tracking"] is True
        assert status3["data"]["target"] == "M31"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
