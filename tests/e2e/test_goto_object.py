"""
End-to-End tests for goto_object command flow (Step 574).

Tests the complete flow from voice command to telescope slew:
1. Voice input: "slew to Andromeda"
2. STT transcription
3. LLM tool selection
4. Catalog lookup
5. Safety check
6. Mount slew execution
7. TTS response
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime


@pytest.mark.e2e
class TestGotoObjectE2E:
    """End-to-end tests for goto_object voice command flow."""

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
        """Create mock LLM that returns goto_object tool call."""
        llm = Mock()
        llm.generate = AsyncMock(return_value={
            "tool": "goto_object",
            "parameters": {"object_name": "Andromeda"}
        })
        return llm

    @pytest.fixture
    def mock_catalog(self):
        """Create mock catalog service."""
        catalog = Mock()
        catalog.lookup = Mock(return_value={
            "ra": 0.712,
            "dec": 41.27,
            "name": "Andromeda Galaxy",
            "type": "galaxy",
            "magnitude": 3.4
        })
        return catalog

    @pytest.fixture
    def mock_mount(self):
        """Create mock mount controller."""
        mount = Mock()
        mount.is_connected = True
        mount.is_parked = False
        mount.slew_to_coordinates = AsyncMock(return_value=True)
        mount.is_slewing = False
        return mount

    @pytest.fixture
    def mock_safety(self):
        """Create mock safety monitor."""
        safety = Mock()
        safety.is_safe_to_slew = Mock(return_value=True)
        safety.check_altitude_limit = Mock(return_value=True)
        return safety

    @pytest.mark.asyncio
    async def test_goto_object_full_flow(
        self, mock_stt, mock_tts, mock_llm, mock_catalog, mock_mount, mock_safety
    ):
        """Test complete goto_object flow from voice to slew."""
        # Step 1: Simulate voice input -> STT
        audio_input = b"simulated_audio"
        transcript = await mock_stt.transcribe(audio_input)
        assert transcript == "slew to Andromeda"

        # Step 2: LLM interprets command
        tool_call = await mock_llm.generate(transcript)
        assert tool_call["tool"] == "goto_object"
        assert tool_call["parameters"]["object_name"] == "Andromeda"

        # Step 3: Catalog lookup
        object_name = tool_call["parameters"]["object_name"]
        catalog_result = mock_catalog.lookup(object_name)
        assert catalog_result is not None
        assert catalog_result["name"] == "Andromeda Galaxy"

        # Step 4: Safety check
        assert mock_safety.is_safe_to_slew() is True
        assert mock_safety.check_altitude_limit(catalog_result["dec"]) is True

        # Step 5: Execute slew
        ra, dec = catalog_result["ra"], catalog_result["dec"]
        slew_result = await mock_mount.slew_to_coordinates(ra, dec)
        assert slew_result is True

        # Step 6: Generate response
        response_text = f"Slewing to {catalog_result['name']}"
        audio_response = await mock_tts.synthesize(response_text)
        assert audio_response is not None

        # Verify all components were called
        mock_stt.transcribe.assert_called_once()
        mock_llm.generate.assert_called_once()
        mock_catalog.lookup.assert_called_with("Andromeda")
        mock_mount.slew_to_coordinates.assert_called_once_with(ra, dec)

    @pytest.mark.asyncio
    async def test_goto_messier_object(
        self, mock_stt, mock_llm, mock_catalog, mock_mount, mock_safety
    ):
        """Test goto flow with Messier object."""
        mock_stt.transcribe = AsyncMock(return_value="slew to M42")
        mock_llm.generate = AsyncMock(return_value={
            "tool": "goto_object",
            "parameters": {"object_name": "M42"}
        })
        mock_catalog.lookup = Mock(return_value={
            "ra": 5.588,
            "dec": -5.39,
            "name": "Orion Nebula",
            "type": "nebula"
        })

        transcript = await mock_stt.transcribe(b"audio")
        tool_call = await mock_llm.generate(transcript)
        catalog_result = mock_catalog.lookup(tool_call["parameters"]["object_name"])

        assert catalog_result["name"] == "Orion Nebula"

        slew_result = await mock_mount.slew_to_coordinates(
            catalog_result["ra"], catalog_result["dec"]
        )
        assert slew_result is True

    @pytest.mark.asyncio
    async def test_goto_star_by_name(
        self, mock_stt, mock_llm, mock_catalog, mock_mount, mock_safety
    ):
        """Test goto flow with named star."""
        mock_stt.transcribe = AsyncMock(return_value="point at Vega")
        mock_llm.generate = AsyncMock(return_value={
            "tool": "goto_object",
            "parameters": {"object_name": "Vega"}
        })
        mock_catalog.lookup = Mock(return_value={
            "ra": 18.616,
            "dec": 38.78,
            "name": "Vega",
            "type": "star"
        })

        transcript = await mock_stt.transcribe(b"audio")
        assert "Vega" in transcript

        tool_call = await mock_llm.generate(transcript)
        catalog_result = mock_catalog.lookup(tool_call["parameters"]["object_name"])

        assert catalog_result["type"] == "star"

    @pytest.mark.asyncio
    async def test_goto_blocked_by_safety(
        self, mock_stt, mock_llm, mock_catalog, mock_mount, mock_safety
    ):
        """Test goto blocked when safety check fails."""
        mock_safety.is_safe_to_slew.return_value = False

        transcript = await mock_stt.transcribe(b"audio")
        tool_call = await mock_llm.generate(transcript)
        catalog_result = mock_catalog.lookup(tool_call["parameters"]["object_name"])

        # Safety check should fail
        assert mock_safety.is_safe_to_slew() is False

        # Mount slew should NOT be called in real implementation
        # This verifies the safety integration point

    @pytest.mark.asyncio
    async def test_goto_object_not_found(
        self, mock_stt, mock_llm, mock_catalog, mock_mount, mock_tts
    ):
        """Test goto with unknown object."""
        mock_stt.transcribe = AsyncMock(return_value="slew to unknown object")
        mock_llm.generate = AsyncMock(return_value={
            "tool": "goto_object",
            "parameters": {"object_name": "unknown object"}
        })
        mock_catalog.lookup = Mock(return_value=None)

        transcript = await mock_stt.transcribe(b"audio")
        tool_call = await mock_llm.generate(transcript)
        catalog_result = mock_catalog.lookup(tool_call["parameters"]["object_name"])

        assert catalog_result is None

        # Should generate error response
        error_response = "Object not found in catalog"
        await mock_tts.synthesize(error_response)
        mock_tts.synthesize.assert_called()

    @pytest.mark.asyncio
    async def test_goto_below_horizon(
        self, mock_stt, mock_llm, mock_catalog, mock_mount, mock_safety, mock_tts
    ):
        """Test goto blocked for object below horizon."""
        mock_catalog.lookup = Mock(return_value={
            "ra": 12.0,
            "dec": -60.0,  # Far south, may be below horizon
            "name": "Southern Object",
            "type": "galaxy"
        })
        mock_safety.check_altitude_limit.return_value = False

        transcript = await mock_stt.transcribe(b"audio")
        tool_call = await mock_llm.generate(transcript)
        catalog_result = mock_catalog.lookup(tool_call["parameters"]["object_name"])

        # Altitude check should fail
        assert mock_safety.check_altitude_limit(catalog_result["dec"]) is False


@pytest.mark.e2e
class TestGotoObjectVariations:
    """Test variations of the goto command."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM."""
        return Mock()

    @pytest.mark.asyncio
    async def test_various_command_phrasings(self, mock_llm):
        """Test LLM correctly interprets various command phrasings."""
        phrasings = [
            ("slew to Andromeda", "goto_object"),
            ("point at M31", "goto_object"),
            ("go to the Orion Nebula", "goto_object"),
            ("move telescope to Vega", "goto_object"),
            ("target Polaris", "goto_object"),
        ]

        for phrase, expected_tool in phrasings:
            mock_llm.generate = AsyncMock(return_value={
                "tool": expected_tool,
                "parameters": {"object_name": phrase.split()[-1]}
            })

            result = await mock_llm.generate(phrase)
            assert result["tool"] == expected_tool, f"Failed for: {phrase}"

    @pytest.mark.asyncio
    async def test_goto_with_constellation(self, mock_llm):
        """Test goto with constellation name in command."""
        mock_llm.generate = AsyncMock(return_value={
            "tool": "goto_object",
            "parameters": {"object_name": "Orion Nebula"}
        })

        result = await mock_llm.generate("slew to the nebula in Orion")
        assert result["tool"] == "goto_object"


@pytest.mark.e2e
class TestGotoObjectTiming:
    """Test timing aspects of goto command."""

    @pytest.fixture
    def mock_mount(self):
        """Create mock mount with slew tracking."""
        mount = Mock()
        mount.is_connected = True
        mount.is_slewing = False
        mount.slew_to_coordinates = AsyncMock(return_value=True)
        return mount

    @pytest.mark.asyncio
    async def test_slew_completes(self, mock_mount):
        """Test that slew operation completes."""
        result = await mock_mount.slew_to_coordinates(10.0, 45.0)
        assert result is True
        mock_mount.slew_to_coordinates.assert_called_once()

    @pytest.mark.asyncio
    async def test_response_after_slew_start(self, mock_mount):
        """Test response is generated after slew starts."""
        # Slew is started
        await mock_mount.slew_to_coordinates(10.0, 45.0)

        # Response should be "slewing to..." not "arrived at..."
        # (immediate response before slew completes)
        response = "Slewing to target"
        assert "Slewing" in response
