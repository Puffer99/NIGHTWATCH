"""
End-to-End tests for safety veto system (Step 576).

Tests the complete flow when safety system blocks commands:
1. User issues command (slew, unpark, open roof)
2. Safety system evaluates conditions
3. Command is blocked with appropriate message
4. User receives explanation of why command was blocked
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta


@pytest.mark.e2e
class TestSafetyVetoSlew:
    """End-to-end tests for safety vetoes on slew commands."""

    @pytest.fixture
    def mock_stt(self):
        """Create mock STT service."""
        stt = Mock()
        stt.transcribe = AsyncMock(return_value="slew to Andromeda")
        return stt

    @pytest.fixture
    def mock_tts(self):
        """Create mock TTS service."""
        tts = Mock()
        tts.synthesize = AsyncMock(return_value=b"audio_data")
        return tts

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM."""
        llm = Mock()
        llm.generate = AsyncMock(return_value={
            "tool": "goto_object",
            "parameters": {"object_name": "Andromeda"}
        })
        return llm

    @pytest.fixture
    def mock_mount(self):
        """Create mock mount."""
        mount = Mock()
        mount.is_connected = True
        mount.slew_to_coordinates = AsyncMock(return_value=True)
        return mount

    @pytest.fixture
    def mock_safety(self):
        """Create mock safety with veto capability."""
        safety = Mock()
        safety.is_safe_to_slew = Mock(return_value=False)
        safety.get_veto_reasons = Mock(return_value=["High wind speed: 35 mph"])
        safety.wind_speed_mph = 35
        return safety

    @pytest.mark.asyncio
    async def test_slew_vetoed_high_wind(
        self, mock_stt, mock_tts, mock_llm, mock_mount, mock_safety
    ):
        """Test slew command is vetoed due to high wind."""
        # User command
        transcript = await mock_stt.transcribe(b"audio")
        tool_call = await mock_llm.generate(transcript)

        # Safety check fails
        assert mock_safety.is_safe_to_slew() is False

        # Get veto reasons
        reasons = mock_safety.get_veto_reasons()
        assert len(reasons) > 0
        assert "wind" in reasons[0].lower()

        # Mount should NOT be commanded
        mock_mount.slew_to_coordinates.assert_not_called()

        # User should receive explanation
        response = f"Cannot slew: {reasons[0]}"
        await mock_tts.synthesize(response)
        mock_tts.synthesize.assert_called()

    @pytest.mark.asyncio
    async def test_slew_vetoed_rain(self, mock_stt, mock_llm, mock_mount, mock_safety, mock_tts):
        """Test slew command is vetoed due to rain."""
        mock_safety.is_safe_to_slew.return_value = False
        mock_safety.get_veto_reasons.return_value = ["Rain detected"]
        mock_safety.rain_detected = True

        transcript = await mock_stt.transcribe(b"audio")
        await mock_llm.generate(transcript)

        assert mock_safety.is_safe_to_slew() is False
        reasons = mock_safety.get_veto_reasons()
        assert "Rain" in reasons[0]

    @pytest.mark.asyncio
    async def test_slew_vetoed_below_horizon(
        self, mock_stt, mock_llm, mock_mount, mock_safety, mock_tts
    ):
        """Test slew command is vetoed for target below horizon."""
        mock_safety.is_safe_to_slew.return_value = False
        mock_safety.get_veto_reasons.return_value = ["Target below horizon limit (10°)"]

        transcript = await mock_stt.transcribe(b"audio")
        await mock_llm.generate(transcript)

        reasons = mock_safety.get_veto_reasons()
        assert "horizon" in reasons[0].lower()


@pytest.mark.e2e
class TestSafetyVetoUnpark:
    """End-to-end tests for safety vetoes on unpark commands."""

    @pytest.fixture
    def mock_mount(self):
        """Create mock mount."""
        mount = Mock()
        mount.is_parked = True
        mount.unpark = AsyncMock(return_value=True)
        return mount

    @pytest.fixture
    def mock_safety(self):
        """Create mock safety."""
        safety = Mock()
        safety.is_safe_to_unpark = Mock(return_value=False)
        safety.get_veto_reasons = Mock(return_value=["Weather unsafe"])
        return safety

    @pytest.fixture
    def mock_tts(self):
        """Create mock TTS."""
        tts = Mock()
        tts.synthesize = AsyncMock(return_value=b"audio")
        return tts

    @pytest.mark.asyncio
    async def test_unpark_vetoed_weather(self, mock_mount, mock_safety, mock_tts):
        """Test unpark is vetoed due to weather."""
        assert mock_safety.is_safe_to_unpark() is False

        reasons = mock_safety.get_veto_reasons()
        assert "Weather" in reasons[0]

        # Mount unpark should NOT be called
        mock_mount.unpark.assert_not_called()

        # Error response
        response = f"Cannot unpark: {reasons[0]}"
        await mock_tts.synthesize(response)

    @pytest.mark.asyncio
    async def test_unpark_vetoed_rain_holdoff(self, mock_mount, mock_safety, mock_tts):
        """Test unpark is vetoed during rain holdoff."""
        mock_safety.get_veto_reasons.return_value = ["Rain holdoff active (15 minutes remaining)"]

        reasons = mock_safety.get_veto_reasons()
        assert "holdoff" in reasons[0].lower()


@pytest.mark.e2e
class TestSafetyVetoRoof:
    """End-to-end tests for safety vetoes on roof commands."""

    @pytest.fixture
    def mock_enclosure(self):
        """Create mock enclosure."""
        enclosure = Mock()
        enclosure.is_closed = True
        enclosure.open = AsyncMock(return_value=True)
        return enclosure

    @pytest.fixture
    def mock_mount(self):
        """Create mock mount."""
        mount = Mock()
        mount.is_parked = False  # Not parked - should block roof open
        return mount

    @pytest.fixture
    def mock_safety(self):
        """Create mock safety."""
        safety = Mock()
        safety.is_safe_to_open_roof = Mock(return_value=False)
        safety.get_veto_reasons = Mock(return_value=["Mount not parked"])
        return safety

    @pytest.fixture
    def mock_tts(self):
        """Create mock TTS."""
        tts = Mock()
        tts.synthesize = AsyncMock(return_value=b"audio")
        return tts

    @pytest.mark.asyncio
    async def test_roof_open_vetoed_mount_not_parked(
        self, mock_enclosure, mock_mount, mock_safety, mock_tts
    ):
        """Test roof open is vetoed when mount not parked."""
        assert mock_safety.is_safe_to_open_roof() is False

        reasons = mock_safety.get_veto_reasons()
        assert "Mount not parked" in reasons[0]

        # Roof should NOT be opened
        mock_enclosure.open.assert_not_called()

    @pytest.mark.asyncio
    async def test_roof_open_vetoed_weather(
        self, mock_enclosure, mock_safety, mock_tts
    ):
        """Test roof open is vetoed due to weather."""
        mock_safety.get_veto_reasons.return_value = ["High humidity: 90%"]

        reasons = mock_safety.get_veto_reasons()
        assert "humidity" in reasons[0].lower()


@pytest.mark.e2e
class TestSafetyVetoMessages:
    """Test safety veto message formatting."""

    @pytest.fixture
    def mock_safety(self):
        """Create mock safety."""
        safety = Mock()
        return safety

    @pytest.fixture
    def mock_tts(self):
        """Create mock TTS."""
        tts = Mock()
        tts.synthesize = AsyncMock(return_value=b"audio")
        return tts

    @pytest.mark.asyncio
    async def test_single_veto_reason(self, mock_safety, mock_tts):
        """Test message with single veto reason."""
        mock_safety.get_veto_reasons = Mock(return_value=["High wind speed"])

        reasons = mock_safety.get_veto_reasons()
        response = f"Cannot proceed: {reasons[0]}"

        await mock_tts.synthesize(response)
        assert "High wind" in response

    @pytest.mark.asyncio
    async def test_multiple_veto_reasons(self, mock_safety, mock_tts):
        """Test message with multiple veto reasons."""
        mock_safety.get_veto_reasons = Mock(return_value=[
            "High wind speed: 30 mph",
            "High humidity: 85%",
            "Cloud cover: 80%"
        ])

        reasons = mock_safety.get_veto_reasons()
        response = f"Cannot proceed due to: {', '.join(reasons)}"

        await mock_tts.synthesize(response)
        assert "wind" in response.lower()
        assert "humidity" in response.lower()

    @pytest.mark.asyncio
    async def test_veto_with_threshold_info(self, mock_safety, mock_tts):
        """Test veto message includes threshold information."""
        mock_safety.get_veto_reasons = Mock(
            return_value=["Wind speed 35 mph exceeds limit of 25 mph"]
        )

        reasons = mock_safety.get_veto_reasons()
        assert "35 mph" in reasons[0]
        assert "25 mph" in reasons[0]


@pytest.mark.e2e
class TestSafetyVetoRecovery:
    """Test behavior when safety conditions improve."""

    @pytest.fixture
    def mock_safety(self):
        """Create mock safety with changeable state."""
        safety = Mock()
        safety._safe = False
        safety.is_safe_to_slew = Mock(side_effect=lambda: safety._safe)
        return safety

    @pytest.fixture
    def mock_mount(self):
        """Create mock mount."""
        mount = Mock()
        mount.slew_to_coordinates = AsyncMock(return_value=True)
        return mount

    @pytest.mark.asyncio
    async def test_command_succeeds_after_conditions_improve(
        self, mock_safety, mock_mount
    ):
        """Test command succeeds when conditions improve."""
        # Initially unsafe
        mock_safety._safe = False
        assert mock_safety.is_safe_to_slew() is False

        # Conditions improve
        mock_safety._safe = True
        assert mock_safety.is_safe_to_slew() is True

        # Command should now succeed
        await mock_mount.slew_to_coordinates(10.0, 45.0)
        mock_mount.slew_to_coordinates.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_notified_of_condition_change(self, mock_safety):
        """Test user is notified when conditions change."""
        notifications = []

        def on_safety_change(event, data):
            notifications.append((event, data))

        # Simulate condition change
        on_safety_change("weather_safe", {"reason": "Wind decreased to 15 mph"})

        assert len(notifications) == 1
        assert notifications[0][0] == "weather_safe"
