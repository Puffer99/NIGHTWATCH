"""
NIGHTWATCH Test Fixtures Package.

Provides mock implementations of observatory services for testing.
These fixtures enable unit and integration testing without requiring
actual hardware connections.

Available fixtures:
- MockMount: Simulates mount controller (LX200/OnStepX)
- MockWeather: Simulates weather service (Ecowitt)
- MockCamera: Simulates camera controller (ZWO ASI)
- MockGuider: Simulates guiding service (PHD2)
- MockFocuser: Simulates focus controller
- MockEnclosure: Simulates roll-off roof/dome
- MockPower: Simulates UPS/PDU power monitoring
- MockLLM: Simulates local LLM inference
- MockSTT: Simulates speech-to-text (Whisper)

Usage:
    from tests.fixtures import MockMount, MockWeather

    async def test_slew():
        mount = MockMount()
        await mount.connect()
        await mount.slew_to_coordinates(12.5, 45.0)
        assert mount.is_slewing
"""

from tests.fixtures.mock_mount import MockMount, MockMountState
from tests.fixtures.mock_weather import MockWeather, MockWeatherConditions
from tests.fixtures.mock_camera import MockCamera, MockCameraState
from tests.fixtures.mock_guider import MockGuider, MockGuiderState
from tests.fixtures.mock_focuser import MockFocuser, MockFocuserState
from tests.fixtures.mock_enclosure import MockEnclosure, MockEnclosureState
from tests.fixtures.mock_power import MockPower, PowerState
from tests.fixtures.mock_llm import MockLLM, MockLLMState, LLMResponse, ToolCall
from tests.fixtures.mock_stt import MockSTT, MockSTTState, TranscriptionResult

__all__ = [
    "MockMount",
    "MockMountState",
    "MockWeather",
    "MockWeatherConditions",
    "MockCamera",
    "MockCameraState",
    "MockGuider",
    "MockGuiderState",
    "MockFocuser",
    "MockFocuserState",
    "MockEnclosure",
    "MockEnclosureState",
    "MockPower",
    "PowerState",
    "MockLLM",
    "MockLLMState",
    "LLMResponse",
    "ToolCall",
    "MockSTT",
    "MockSTTState",
    "TranscriptionResult",
]
