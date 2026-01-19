"""
Unit tests for NIGHTWATCH Voice Pipeline.

Tests the end-to-end voice command processing pipeline.
"""

import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock, patch

import pytest

from nightwatch.voice_pipeline import (
    VoicePipeline,
    PipelineState,
    PipelineResult,
    VoicePipelineConfig,
    STTInterface,
    TTSInterface,
    create_voice_pipeline,
)
from nightwatch.llm_client import LLMClient, LLMResponse, ToolCall, LLMBackend


class TestPipelineState:
    """Tests for PipelineState enum."""

    def test_state_values(self):
        """Test pipeline state values."""
        assert PipelineState.IDLE.value == "idle"
        assert PipelineState.LISTENING.value == "listening"
        assert PipelineState.TRANSCRIBING.value == "transcribing"
        assert PipelineState.PROCESSING.value == "processing"
        assert PipelineState.EXECUTING.value == "executing"
        assert PipelineState.SPEAKING.value == "speaking"
        assert PipelineState.ERROR.value == "error"


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_default_values(self):
        """Test default result values."""
        result = PipelineResult()

        assert result.transcript == ""
        assert result.llm_response == ""
        assert result.tool_calls == []
        assert result.tool_results == []
        assert result.spoken_response == ""
        assert result.success is True
        assert result.had_tool_calls is False

    def test_with_tool_calls(self):
        """Test result with tool calls."""
        result = PipelineResult(
            tool_calls=[{"id": "1", "name": "goto", "arguments": {}}]
        )

        assert result.had_tool_calls is True

    def test_timing_fields(self):
        """Test timing fields."""
        result = PipelineResult(
            stt_latency_ms=100.0,
            llm_latency_ms=200.0,
            tool_latency_ms=50.0,
            tts_latency_ms=75.0,
            total_latency_ms=425.0,
        )

        assert result.stt_latency_ms == 100.0
        assert result.total_latency_ms == 425.0


class TestVoicePipelineConfig:
    """Tests for VoicePipelineConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = VoicePipelineConfig()

        assert config.stt_model == "base"
        assert config.stt_device == "cuda"
        assert config.tts_model == "en_US-lessac-medium"
        assert config.tts_use_cuda is True
        assert config.max_audio_length_sec == 30.0
        assert config.enable_vad is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = VoicePipelineConfig(
            stt_model="large",
            stt_device="cpu",
            tts_use_cuda=False,
        )

        assert config.stt_model == "large"
        assert config.stt_device == "cpu"
        assert config.tts_use_cuda is False


class TestSTTInterface:
    """Tests for STTInterface."""

    def test_init(self):
        """Test STT initialization."""
        stt = STTInterface(
            model_size="small",
            device="cpu",
            compute_type="int8",
        )

        assert stt.model_size == "small"
        assert stt.device == "cpu"
        assert stt.compute_type == "int8"
        assert stt._loaded is False

    @pytest.mark.asyncio
    async def test_transcribe_mock(self):
        """Test mock transcription."""
        stt = STTInterface()

        # Without faster-whisper, should return mock
        result = await stt.transcribe(b"audio data")

        assert result == "mock transcription"


class TestTTSInterface:
    """Tests for TTSInterface."""

    def test_init(self):
        """Test TTS initialization."""
        tts = TTSInterface(
            model="en_GB-alan-medium",
            use_cuda=False,
        )

        assert tts.model == "en_GB-alan-medium"
        assert tts.use_cuda is False

    @pytest.mark.asyncio
    async def test_synthesize_mock(self):
        """Test mock synthesis."""
        tts = TTSInterface()

        audio = await tts.synthesize("Hello world")

        # Should return WAV bytes
        assert audio is not None
        assert len(audio) > 44  # WAV header is 44 bytes
        assert audio[:4] == b'RIFF'

    @pytest.mark.asyncio
    async def test_synthesize_length_varies(self):
        """Test audio length varies with text."""
        tts = TTSInterface()

        short_audio = await tts.synthesize("Hi")
        long_audio = await tts.synthesize("This is a much longer sentence.")

        assert len(long_audio) > len(short_audio)


class TestVoicePipeline:
    """Tests for VoicePipeline class."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator."""
        orch = Mock()
        orch.mount = None
        orch.weather = None
        orch.safety = None
        return orch

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = LLMClient(backend=LLMBackend.MOCK)
        return client

    @pytest.fixture
    def pipeline(self, mock_orchestrator, mock_llm_client):
        """Create pipeline for testing."""
        return VoicePipeline(mock_orchestrator, mock_llm_client)

    def test_init(self, pipeline):
        """Test pipeline initialization."""
        assert pipeline.orchestrator is not None
        assert pipeline.llm_client is not None
        assert pipeline.state == PipelineState.IDLE
        assert pipeline.is_running is False

    def test_init_with_config(self, mock_orchestrator, mock_llm_client):
        """Test pipeline with custom config."""
        config = VoicePipelineConfig(stt_model="large")
        pipeline = VoicePipeline(
            mock_orchestrator,
            mock_llm_client,
            config=config,
        )

        assert pipeline.config.stt_model == "large"

    @pytest.mark.asyncio
    async def test_start(self, pipeline):
        """Test starting pipeline."""
        await pipeline.start()

        assert pipeline.is_running is True
        assert pipeline.state == PipelineState.IDLE

    @pytest.mark.asyncio
    async def test_start_already_running(self, pipeline):
        """Test starting already running pipeline."""
        await pipeline.start()
        await pipeline.start()  # Should not error

        assert pipeline.is_running is True

    @pytest.mark.asyncio
    async def test_stop(self, pipeline):
        """Test stopping pipeline."""
        await pipeline.start()
        await pipeline.stop()

        assert pipeline.is_running is False

    @pytest.mark.asyncio
    async def test_process_text_basic(self, pipeline):
        """Test basic text processing."""
        result = await pipeline.process_text("Hello")

        assert result.transcript == "Hello"
        assert result.success is True
        assert result.spoken_response != ""

    @pytest.mark.asyncio
    async def test_process_text_with_llm_response(self, pipeline):
        """Test text processing with LLM response."""
        # Initialize the mock client by calling _get_client
        mock_client = pipeline.llm_client._get_client(LLMBackend.MOCK)
        mock_client.set_response(
            LLMResponse(content="I'll point to M31", model="mock")
        )

        result = await pipeline.process_text("Point to M31")

        assert result.llm_response == "I'll point to M31"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_process_text_with_tool_call(self, pipeline, mock_orchestrator):
        """Test text processing with tool call."""
        # Initialize the mock client by calling _get_client
        mock_client = pipeline.llm_client._get_client(LLMBackend.MOCK)
        mock_response = LLMResponse(
            content="",
            tool_calls=[ToolCall(id="1", name="goto_object", arguments={"object_name": "M31"})],
            model="mock",
        )
        mock_client.set_response(mock_response)

        result = await pipeline.process_text("Point to M31")

        assert result.had_tool_calls is True
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["name"] == "goto_object"

    @pytest.mark.asyncio
    async def test_process_audio(self, pipeline):
        """Test audio processing."""
        result = await pipeline.process_audio(b"fake audio data")

        assert result.transcript == "mock transcription"
        assert result.audio_output is not None
        assert result.stt_latency_ms > 0
        assert result.tts_latency_ms > 0
        assert result.total_latency_ms > 0

    @pytest.mark.asyncio
    async def test_process_audio_empty_transcript(self, pipeline):
        """Test handling empty transcript."""
        # Mock empty transcription
        pipeline._stt = Mock()
        pipeline._stt.transcribe = AsyncMock(return_value="")

        result = await pipeline.process_audio(b"silence")

        assert "didn't catch" in result.spoken_response.lower()

    def test_get_metrics(self, pipeline):
        """Test getting metrics."""
        metrics = pipeline.get_metrics()

        assert "commands_processed" in metrics
        assert "avg_latency_ms" in metrics
        assert "state" in metrics
        assert metrics["state"] == "idle"

    @pytest.mark.asyncio
    async def test_metrics_update(self, pipeline):
        """Test metrics update after processing."""
        await pipeline.process_text("Test command")

        metrics = pipeline.get_metrics()
        assert metrics["commands_processed"] == 0  # Text-only doesn't count

        await pipeline.process_audio(b"audio")
        metrics = pipeline.get_metrics()
        assert metrics["commands_processed"] == 1

    def test_register_callback(self, pipeline):
        """Test registering callback."""
        callback = Mock()
        pipeline.register_callback(callback)

        assert callback in pipeline._callbacks


class TestToolExecution:
    """Tests for tool execution in pipeline."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create orchestrator with mock mount."""
        orch = Mock()
        orch.mount = AsyncMock()
        orch.mount.park = AsyncMock(return_value=True)
        orch.weather = Mock()
        orch.weather.current_conditions = {"temperature": 15.0}
        return orch

    @pytest.fixture
    def pipeline(self, mock_orchestrator):
        """Create pipeline with mock services."""
        client = LLMClient(backend=LLMBackend.MOCK)
        return VoicePipeline(mock_orchestrator, client)

    @pytest.mark.asyncio
    async def test_execute_goto_object(self, pipeline):
        """Test goto_object tool execution."""
        result = await pipeline._execute_tool(
            "goto_object",
            {"object_name": "M31"}
        )

        assert result["status"] == "success"
        assert "M31" in result["message"]

    @pytest.mark.asyncio
    async def test_execute_park_telescope(self, pipeline):
        """Test park_telescope tool execution."""
        result = await pipeline._execute_tool("park_telescope", {})

        assert result["status"] == "success"
        pipeline.orchestrator.mount.park.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_get_weather(self, pipeline):
        """Test get_weather tool execution."""
        result = await pipeline._execute_tool("get_weather", {})

        assert result["status"] == "success"
        assert "data" in result

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, pipeline):
        """Test unknown tool execution."""
        result = await pipeline._execute_tool("unknown_tool", {})

        assert result["status"] == "not_found"


class TestResponseFormatting:
    """Tests for response formatting in pipeline."""

    @pytest.fixture
    def pipeline(self):
        """Create pipeline."""
        orch = Mock()
        client = LLMClient(backend=LLMBackend.MOCK)
        return VoicePipeline(orch, client)

    def test_format_with_tool_results(self, pipeline):
        """Test formatting with tool results."""
        result = PipelineResult(
            tool_results=[{"message": "Slewing to M31"}]
        )

        response = pipeline._format_response(result)
        assert "Slewing to M31" in response

    def test_format_with_llm_response(self, pipeline):
        """Test formatting with LLM response only."""
        result = PipelineResult(
            llm_response="I'll help you with that"
        )

        response = pipeline._format_response(result)
        assert response == "I'll help you with that"

    def test_format_default(self, pipeline):
        """Test default formatting."""
        result = PipelineResult()

        response = pipeline._format_response(result)
        assert response == "Command processed."


class TestCreateVoicePipeline:
    """Tests for factory function."""

    def test_create_basic(self):
        """Test basic pipeline creation."""
        orch = Mock()
        client = LLMClient(backend=LLMBackend.MOCK)

        pipeline = create_voice_pipeline(orch, client)

        assert pipeline is not None
        assert pipeline.orchestrator is orch
        assert pipeline.llm_client is client

    def test_create_with_config(self):
        """Test pipeline creation with config."""
        orch = Mock()
        client = LLMClient(backend=LLMBackend.MOCK)

        pipeline = create_voice_pipeline(
            orch,
            client,
            stt_model="large",
            tts_use_cuda=False,
        )

        assert pipeline.config.stt_model == "large"
        assert pipeline.config.tts_use_cuda is False
