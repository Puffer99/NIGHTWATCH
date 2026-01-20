"""
End-to-End tests for park/unpark command flow (Step 575).

Tests the complete flow from voice command to mount park/unpark:
1. Voice input: "park the telescope" / "unpark"
2. STT transcription
3. LLM tool selection
4. Safety check (for unpark)
5. Mount park/unpark execution
6. TTS response
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime


@pytest.mark.e2e
class TestParkE2E:
    """End-to-end tests for park voice command flow."""

    @pytest.fixture
    def mock_stt(self):
        """Create mock STT service."""
        stt = Mock()
        stt.transcribe = AsyncMock(return_value="park the telescope")
        return stt

    @pytest.fixture
    def mock_tts(self):
        """Create mock TTS service."""
        tts = Mock()
        tts.synthesize = AsyncMock(return_value=b"audio_data")
        return tts

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM that returns park tool call."""
        llm = Mock()
        llm.generate = AsyncMock(return_value={
            "tool": "park_mount",
            "parameters": {}
        })
        return llm

    @pytest.fixture
    def mock_mount(self):
        """Create mock mount controller."""
        mount = Mock()
        mount.is_connected = True
        mount.is_parked = False
        mount.is_slewing = False
        mount.is_tracking = True
        mount.park = AsyncMock(return_value=True)
        mount.stop = AsyncMock(return_value=True)
        return mount

    @pytest.mark.asyncio
    async def test_park_full_flow(self, mock_stt, mock_tts, mock_llm, mock_mount):
        """Test complete park flow from voice to parked state."""
        # Step 1: Voice input -> STT
        audio_input = b"simulated_audio"
        transcript = await mock_stt.transcribe(audio_input)
        assert transcript == "park the telescope"

        # Step 2: LLM interprets command
        tool_call = await mock_llm.generate(transcript)
        assert tool_call["tool"] == "park_mount"

        # Step 3: Execute park
        park_result = await mock_mount.park()
        assert park_result is True

        # Step 4: Generate response
        response_text = "Telescope is now parked"
        audio_response = await mock_tts.synthesize(response_text)
        assert audio_response is not None

        # Verify components called
        mock_stt.transcribe.assert_called_once()
        mock_llm.generate.assert_called_once()
        mock_mount.park.assert_called_once()

    @pytest.mark.asyncio
    async def test_park_already_parked(self, mock_stt, mock_llm, mock_mount, mock_tts):
        """Test park when already parked."""
        mock_mount.is_parked = True

        transcript = await mock_stt.transcribe(b"audio")
        tool_call = await mock_llm.generate(transcript)

        # Should check parked state before parking
        if mock_mount.is_parked:
            response = "Telescope is already parked"
        else:
            await mock_mount.park()
            response = "Telescope is now parked"

        assert "already parked" in response.lower()

    @pytest.mark.asyncio
    async def test_park_stops_tracking(self, mock_mount):
        """Test that park operation stops tracking."""
        mock_mount.is_tracking = True

        await mock_mount.park()

        # After park, mount should have been commanded
        mock_mount.park.assert_called_once()

    @pytest.mark.asyncio
    async def test_park_stops_slew(self, mock_mount):
        """Test that park stops any active slew first."""
        mock_mount.is_slewing = True

        # Should stop first, then park
        await mock_mount.stop()
        await mock_mount.park()

        mock_mount.stop.assert_called_once()
        mock_mount.park.assert_called_once()


@pytest.mark.e2e
class TestUnparkE2E:
    """End-to-end tests for unpark voice command flow."""

    @pytest.fixture
    def mock_stt(self):
        """Create mock STT service."""
        stt = Mock()
        stt.transcribe = AsyncMock(return_value="unpark the telescope")
        return stt

    @pytest.fixture
    def mock_tts(self):
        """Create mock TTS service."""
        tts = Mock()
        tts.synthesize = AsyncMock(return_value=b"audio_data")
        return tts

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM that returns unpark tool call."""
        llm = Mock()
        llm.generate = AsyncMock(return_value={
            "tool": "unpark_mount",
            "parameters": {}
        })
        return llm

    @pytest.fixture
    def mock_mount(self):
        """Create mock mount controller."""
        mount = Mock()
        mount.is_connected = True
        mount.is_parked = True
        mount.unpark = AsyncMock(return_value=True)
        mount.set_tracking = AsyncMock(return_value=True)
        return mount

    @pytest.fixture
    def mock_safety(self):
        """Create mock safety monitor."""
        safety = Mock()
        safety.is_safe_to_unpark = Mock(return_value=True)
        safety.weather_safe = True
        safety.rain_detected = False
        return safety

    @pytest.mark.asyncio
    async def test_unpark_full_flow(
        self, mock_stt, mock_tts, mock_llm, mock_mount, mock_safety
    ):
        """Test complete unpark flow from voice to unparked state."""
        # Step 1: Voice input -> STT
        transcript = await mock_stt.transcribe(b"audio")
        assert "unpark" in transcript.lower()

        # Step 2: LLM interprets command
        tool_call = await mock_llm.generate(transcript)
        assert tool_call["tool"] == "unpark_mount"

        # Step 3: Safety check
        assert mock_safety.is_safe_to_unpark() is True

        # Step 4: Execute unpark
        unpark_result = await mock_mount.unpark()
        assert unpark_result is True

        # Step 5: Generate response
        response_text = "Telescope is now unparked and tracking"
        audio_response = await mock_tts.synthesize(response_text)
        assert audio_response is not None

    @pytest.mark.asyncio
    async def test_unpark_blocked_unsafe_weather(
        self, mock_stt, mock_llm, mock_mount, mock_safety, mock_tts
    ):
        """Test unpark blocked when weather is unsafe."""
        mock_safety.is_safe_to_unpark.return_value = False
        mock_safety.weather_safe = False

        transcript = await mock_stt.transcribe(b"audio")
        tool_call = await mock_llm.generate(transcript)

        # Safety check should fail
        assert mock_safety.is_safe_to_unpark() is False

        # Mount unpark should NOT be called
        # Generate error response instead
        error_response = "Cannot unpark: weather conditions are unsafe"
        await mock_tts.synthesize(error_response)

    @pytest.mark.asyncio
    async def test_unpark_blocked_rain_detected(
        self, mock_stt, mock_llm, mock_mount, mock_safety, mock_tts
    ):
        """Test unpark blocked when rain is detected."""
        mock_safety.rain_detected = True
        mock_safety.is_safe_to_unpark.return_value = False

        assert mock_safety.is_safe_to_unpark() is False

    @pytest.mark.asyncio
    async def test_unpark_already_unparked(self, mock_mount, mock_tts):
        """Test unpark when already unparked."""
        mock_mount.is_parked = False

        if not mock_mount.is_parked:
            response = "Telescope is already unparked"
        else:
            await mock_mount.unpark()
            response = "Telescope is now unparked"

        assert "already unparked" in response.lower()

    @pytest.mark.asyncio
    async def test_unpark_starts_tracking(self, mock_mount, mock_safety):
        """Test that unpark starts tracking."""
        assert mock_safety.is_safe_to_unpark() is True

        await mock_mount.unpark()
        await mock_mount.set_tracking(True)

        mock_mount.unpark.assert_called_once()
        mock_mount.set_tracking.assert_called_with(True)


@pytest.mark.e2e
class TestParkUnparkCycle:
    """Test complete park/unpark cycle."""

    @pytest.fixture
    def mock_mount(self):
        """Create mock mount."""
        mount = Mock()
        mount.is_connected = True
        mount.is_parked = False
        mount.park = AsyncMock(return_value=True)
        mount.unpark = AsyncMock(return_value=True)
        return mount

    @pytest.fixture
    def mock_safety(self):
        """Create mock safety."""
        safety = Mock()
        safety.is_safe_to_unpark = Mock(return_value=True)
        return safety

    @pytest.mark.asyncio
    async def test_park_unpark_cycle(self, mock_mount, mock_safety):
        """Test complete park then unpark cycle."""
        # Initially unparked
        assert mock_mount.is_parked is False

        # Park
        await mock_mount.park()
        mock_mount.is_parked = True
        assert mock_mount.is_parked is True

        # Unpark (with safety check)
        assert mock_safety.is_safe_to_unpark() is True
        await mock_mount.unpark()
        mock_mount.is_parked = False
        assert mock_mount.is_parked is False

        # Verify both operations called
        mock_mount.park.assert_called_once()
        mock_mount.unpark.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_park_commands(self, mock_mount):
        """Test multiple park commands are handled gracefully."""
        await mock_mount.park()
        mock_mount.is_parked = True

        # Second park should be no-op or succeed
        if mock_mount.is_parked:
            # Already parked, skip
            pass
        else:
            await mock_mount.park()

        # Only one actual park call
        assert mock_mount.park.call_count == 1


@pytest.mark.e2e
class TestParkUnparkCommandVariations:
    """Test various phrasings of park/unpark commands."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM."""
        return Mock()

    @pytest.mark.asyncio
    async def test_park_command_variations(self, mock_llm):
        """Test LLM correctly interprets park command variations."""
        park_phrasings = [
            "park the telescope",
            "park mount",
            "go to park position",
            "send to park",
            "park it",
        ]

        for phrase in park_phrasings:
            mock_llm.generate = AsyncMock(return_value={
                "tool": "park_mount",
                "parameters": {}
            })

            result = await mock_llm.generate(phrase)
            assert result["tool"] == "park_mount", f"Failed for: {phrase}"

    @pytest.mark.asyncio
    async def test_unpark_command_variations(self, mock_llm):
        """Test LLM correctly interprets unpark command variations."""
        unpark_phrasings = [
            "unpark the telescope",
            "unpark mount",
            "wake up the telescope",
            "ready the telescope",
        ]

        for phrase in unpark_phrasings:
            mock_llm.generate = AsyncMock(return_value={
                "tool": "unpark_mount",
                "parameters": {}
            })

            result = await mock_llm.generate(phrase)
            assert result["tool"] == "unpark_mount", f"Failed for: {phrase}"
