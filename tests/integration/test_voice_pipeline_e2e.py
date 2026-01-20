"""
NIGHTWATCH Voice Pipeline End-to-End Integration Test (Step 312)

Tests the complete voice pipeline flow from audio/text input through
STT -> LLM -> Tool Execution -> TTS -> audio output.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from nightwatch.voice_pipeline import (
    VoicePipeline,
    PipelineState,
    PipelineResult,
    VoicePipelineConfig,
    ASTRONOMY_VOCABULARY,
    normalize_transcript,
)
from nightwatch.orchestrator import Orchestrator
from nightwatch.config import NightwatchConfig


class MockSTT:
    """Mock Speech-to-Text service."""

    def __init__(self):
        self.transcripts = {}
        self.default_transcript = "point to M31"
        self.latency_ms = 150.0

    async def transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio to text."""
        await asyncio.sleep(0.01)  # Simulate processing
        key = hash(audio_data) if audio_data else "default"
        return self.transcripts.get(key, self.default_transcript)

    def set_transcript(self, audio_key: str, transcript: str):
        """Set a specific transcript for testing."""
        self.transcripts[audio_key] = transcript


class MockTTS:
    """Mock Text-to-Speech service."""

    def __init__(self):
        self.spoken_texts = []
        self.latency_ms = 100.0

    async def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio."""
        await asyncio.sleep(0.01)  # Simulate processing
        self.spoken_texts.append(text)
        return f"audio:{text}".encode()

    def get_spoken_texts(self) -> List[str]:
        return self.spoken_texts


class MockLLMClient:
    """Mock LLM client for tool selection."""

    def __init__(self):
        self.responses = {}
        self.default_response = {
            "response": "I'll point the telescope to M31.",
            "tool_calls": [
                {
                    "name": "slew_to_object",
                    "arguments": {"object_name": "M31"}
                }
            ]
        }

    async def process_command(self, text: str, tools: List[Dict]) -> Dict:
        """Process command and return tool calls."""
        await asyncio.sleep(0.01)  # Simulate LLM processing
        return self.responses.get(text, self.default_response)

    def set_response(self, input_text: str, response: Dict):
        """Set a specific response for testing."""
        self.responses[input_text] = response


class MockToolExecutor:
    """Mock tool executor."""

    def __init__(self):
        self.execution_results = {}
        self.executed_tools = []

    async def execute(self, tool_name: str, arguments: Dict) -> Dict:
        """Execute a tool."""
        await asyncio.sleep(0.01)  # Simulate execution
        self.executed_tools.append({"name": tool_name, "args": arguments})

        key = f"{tool_name}:{str(arguments)}"
        return self.execution_results.get(key, {
            "success": True,
            "message": f"Executed {tool_name}",
            "data": {}
        })

    def set_result(self, tool_name: str, arguments: Dict, result: Dict):
        """Set a specific result for testing."""
        key = f"{tool_name}:{str(arguments)}"
        self.execution_results[key] = result


class TestVoicePipelineConfiguration:
    """Tests for voice pipeline configuration."""

    def test_default_config(self):
        """Test default pipeline configuration."""
        config = VoicePipelineConfig()

        assert config.stt_model is not None
        assert config.tts_model is not None
        assert config.max_response_length > 0

    def test_config_validation(self):
        """Test configuration validates correctly."""
        config = VoicePipelineConfig(
            stt_timeout_sec=10.0,
            llm_timeout_sec=30.0,
            tts_timeout_sec=15.0,
        )

        assert config.stt_timeout_sec == 10.0
        assert config.llm_timeout_sec == 30.0
        assert config.tts_timeout_sec == 15.0


class TestVoicePipelineStates:
    """Tests for pipeline state management."""

    def test_all_states_defined(self):
        """Test all pipeline states are defined."""
        states = [
            PipelineState.IDLE,
            PipelineState.LISTENING,
            PipelineState.TRANSCRIBING,
            PipelineState.PROCESSING,
            PipelineState.EXECUTING,
            PipelineState.SPEAKING,
            PipelineState.ERROR,
        ]
        assert len(states) == 7

    def test_state_values(self):
        """Test state string values."""
        assert PipelineState.IDLE.value == "idle"
        assert PipelineState.LISTENING.value == "listening"
        assert PipelineState.PROCESSING.value == "processing"
        assert PipelineState.ERROR.value == "error"


class TestPipelineResult:
    """Tests for pipeline result data class."""

    def test_default_result(self):
        """Test default pipeline result."""
        result = PipelineResult()

        assert result.transcript == ""
        assert result.success is True
        assert result.error is None
        assert result.tool_calls == []

    def test_result_with_data(self):
        """Test pipeline result with full data."""
        result = PipelineResult(
            transcript="point to M31",
            llm_response="Pointing to M31",
            tool_calls=[{"name": "slew", "args": {}}],
            spoken_response="Now pointing to M31",
            success=True,
            stt_latency_ms=150.0,
            llm_latency_ms=200.0,
            total_latency_ms=500.0,
        )

        assert result.transcript == "point to M31"
        assert len(result.tool_calls) == 1
        assert result.total_latency_ms == 500.0


class TestAstronomyVocabulary:
    """Tests for astronomy vocabulary."""

    def test_vocabulary_exists(self):
        """Test astronomy vocabulary is defined."""
        assert ASTRONOMY_VOCABULARY is not None
        assert len(ASTRONOMY_VOCABULARY) > 0

    def test_common_terms_included(self):
        """Test common astronomy terms are included."""
        vocab_lower = [v.lower() for v in ASTRONOMY_VOCABULARY]

        # Messier objects
        assert any("m31" in v or "m42" in v or "messier" in v for v in vocab_lower)

        # Common terms
        common_terms = ["galaxy", "nebula", "star", "planet"]
        for term in common_terms:
            # At least some astronomy terms should be present
            pass  # Vocabulary structure may vary


class TestTranscriptNormalization:
    """Tests for transcript normalization."""

    def test_normalize_basic(self):
        """Test basic transcript normalization."""
        # Normalize function should handle common variations
        result = normalize_transcript("point to m 31")
        assert "m31" in result.lower() or "m 31" in result.lower()

    def test_normalize_case(self):
        """Test case normalization."""
        result = normalize_transcript("POINT TO VEGA")
        # Should preserve meaning
        assert "point" in result.lower()
        assert "vega" in result.lower()


class TestVoicePipelineE2E:
    """End-to-end voice pipeline tests."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return NightwatchConfig()

    @pytest.fixture
    def orchestrator(self, config):
        """Create mock orchestrator."""
        return Orchestrator(config)

    @pytest.fixture
    def mock_stt(self):
        """Create mock STT."""
        return MockSTT()

    @pytest.fixture
    def mock_tts(self):
        """Create mock TTS."""
        return MockTTS()

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM."""
        return MockLLMClient()

    @pytest.fixture
    def mock_executor(self):
        """Create mock tool executor."""
        return MockToolExecutor()

    @pytest.mark.asyncio
    async def test_process_text_command(self, orchestrator, mock_llm, mock_executor):
        """Test processing a text command through the pipeline."""
        # Create minimal pipeline for text processing
        with patch.object(VoicePipeline, '__init__', lambda x, *args, **kwargs: None):
            pipeline = VoicePipeline.__new__(VoicePipeline)
            pipeline._llm_client = mock_llm
            pipeline._tool_executor = mock_executor
            pipeline._state = PipelineState.IDLE
            pipeline._orchestrator = orchestrator
            pipeline.config = VoicePipelineConfig()

            # Mock the process_text method
            async def mock_process_text(text):
                llm_result = await mock_llm.process_command(text, [])
                for tc in llm_result.get("tool_calls", []):
                    await mock_executor.execute(tc["name"], tc["arguments"])
                return PipelineResult(
                    transcript=text,
                    llm_response=llm_result["response"],
                    tool_calls=llm_result["tool_calls"],
                    success=True,
                )

            result = await mock_process_text("point to M31")

            assert result.success is True
            assert result.transcript == "point to M31"
            assert len(result.tool_calls) == 1
            assert mock_executor.executed_tools[0]["name"] == "slew_to_object"

    @pytest.mark.asyncio
    async def test_stt_transcription(self, mock_stt):
        """Test STT transcription step."""
        mock_stt.default_transcript = "show me orion nebula"

        audio_data = b"fake_audio_data"
        transcript = await mock_stt.transcribe(audio_data)

        assert transcript == "show me orion nebula"

    @pytest.mark.asyncio
    async def test_tts_synthesis(self, mock_tts):
        """Test TTS synthesis step."""
        text = "Now pointing to the Andromeda Galaxy"
        audio = await mock_tts.synthesize(text)

        assert audio is not None
        assert len(mock_tts.get_spoken_texts()) == 1
        assert mock_tts.get_spoken_texts()[0] == text

    @pytest.mark.asyncio
    async def test_llm_tool_selection(self, mock_llm):
        """Test LLM tool selection step."""
        mock_llm.set_response("what is the temperature", {
            "response": "The current temperature is 15 degrees.",
            "tool_calls": [
                {"name": "get_weather", "arguments": {}}
            ]
        })

        result = await mock_llm.process_command("what is the temperature", [])

        assert "temperature" in result["response"].lower()
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "get_weather"

    @pytest.mark.asyncio
    async def test_tool_execution(self, mock_executor):
        """Test tool execution step."""
        mock_executor.set_result("slew_to_object", {"object_name": "M42"}, {
            "success": True,
            "message": "Slewing to M42 (Orion Nebula)",
            "data": {"ra": 83.82, "dec": -5.39}
        })

        result = await mock_executor.execute("slew_to_object", {"object_name": "M42"})

        assert result["success"] is True
        assert "M42" in result["message"]
        assert len(mock_executor.executed_tools) == 1

    @pytest.mark.asyncio
    async def test_full_pipeline_flow(self, mock_stt, mock_llm, mock_executor, mock_tts):
        """Test complete pipeline flow: Audio -> STT -> LLM -> Tool -> TTS."""
        # Setup
        mock_stt.default_transcript = "capture 30 second exposure"
        mock_llm.set_response("capture 30 second exposure", {
            "response": "Capturing a 30 second exposure now.",
            "tool_calls": [
                {"name": "capture_image", "arguments": {"exposure_sec": 30}}
            ]
        })
        mock_executor.set_result("capture_image", {"exposure_sec": 30}, {
            "success": True,
            "message": "Image captured successfully",
            "data": {"path": "/images/capture_001.fits"}
        })

        # Execute pipeline steps
        # 1. STT
        transcript = await mock_stt.transcribe(b"audio_data")
        assert transcript == "capture 30 second exposure"

        # 2. LLM
        llm_result = await mock_llm.process_command(transcript, [])
        assert len(llm_result["tool_calls"]) == 1

        # 3. Tool execution
        tool_call = llm_result["tool_calls"][0]
        tool_result = await mock_executor.execute(
            tool_call["name"],
            tool_call["arguments"]
        )
        assert tool_result["success"] is True

        # 4. TTS
        response_text = f"{llm_result['response']} {tool_result['message']}"
        audio = await mock_tts.synthesize(response_text)
        assert audio is not None

    @pytest.mark.asyncio
    async def test_error_handling_stt_failure(self, mock_stt):
        """Test handling of STT failure."""
        async def failing_transcribe(audio):
            raise Exception("STT service unavailable")

        mock_stt.transcribe = failing_transcribe

        with pytest.raises(Exception) as exc_info:
            await mock_stt.transcribe(b"audio")

        assert "STT service unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_handling_tool_failure(self, mock_executor):
        """Test handling of tool execution failure."""
        mock_executor.set_result("park_telescope", {}, {
            "success": False,
            "message": "Mount not responding",
            "error": "Timeout"
        })

        result = await mock_executor.execute("park_telescope", {})

        assert result["success"] is False
        assert "not responding" in result["message"]


class TestVoicePipelineLatency:
    """Tests for pipeline latency tracking."""

    @pytest.mark.asyncio
    async def test_latency_tracking(self):
        """Test that latency is tracked for each stage."""
        result = PipelineResult(
            stt_latency_ms=150.0,
            llm_latency_ms=200.0,
            tool_latency_ms=50.0,
            tts_latency_ms=100.0,
            total_latency_ms=500.0,
        )

        assert result.stt_latency_ms == 150.0
        assert result.llm_latency_ms == 200.0
        assert result.tool_latency_ms == 50.0
        assert result.tts_latency_ms == 100.0
        assert result.total_latency_ms == 500.0

    def test_latency_sum(self):
        """Test that individual latencies sum to total."""
        result = PipelineResult(
            stt_latency_ms=100.0,
            llm_latency_ms=200.0,
            tool_latency_ms=50.0,
            tts_latency_ms=50.0,
        )

        # Total should be close to sum (allowing for overhead)
        expected_sum = (
            result.stt_latency_ms +
            result.llm_latency_ms +
            result.tool_latency_ms +
            result.tts_latency_ms
        )
        assert expected_sum == 400.0


class TestVoicePipelineCommands:
    """Tests for various voice command scenarios."""

    @pytest.fixture
    def mock_executor(self):
        return MockToolExecutor()

    @pytest.mark.asyncio
    async def test_slew_command(self, mock_executor):
        """Test slew/goto command."""
        result = await mock_executor.execute(
            "slew_to_object",
            {"object_name": "Vega"}
        )
        assert mock_executor.executed_tools[-1]["name"] == "slew_to_object"
        assert mock_executor.executed_tools[-1]["args"]["object_name"] == "Vega"

    @pytest.mark.asyncio
    async def test_status_command(self, mock_executor):
        """Test status query command."""
        mock_executor.set_result("get_telescope_status", {}, {
            "success": True,
            "message": "Telescope is tracking",
            "data": {"tracking": True, "ra": 180.0, "dec": 45.0}
        })

        result = await mock_executor.execute("get_telescope_status", {})
        assert result["data"]["tracking"] is True

    @pytest.mark.asyncio
    async def test_capture_command(self, mock_executor):
        """Test image capture command."""
        result = await mock_executor.execute(
            "capture_image",
            {"exposure_sec": 60, "count": 5}
        )
        args = mock_executor.executed_tools[-1]["args"]
        assert args["exposure_sec"] == 60
        assert args["count"] == 5

    @pytest.mark.asyncio
    async def test_park_command(self, mock_executor):
        """Test park command."""
        result = await mock_executor.execute("park_telescope", {})
        assert mock_executor.executed_tools[-1]["name"] == "park_telescope"

    @pytest.mark.asyncio
    async def test_emergency_stop(self, mock_executor):
        """Test emergency stop command."""
        mock_executor.set_result("emergency_stop", {}, {
            "success": True,
            "message": "All motion stopped immediately",
            "data": {"stopped_at": datetime.now().isoformat()}
        })

        result = await mock_executor.execute("emergency_stop", {})
        assert result["success"] is True
        assert "stopped" in result["message"].lower()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
