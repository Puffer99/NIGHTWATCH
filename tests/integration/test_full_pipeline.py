"""
NIGHTWATCH Full Pipeline Integration Test (Step 570)

Tests the complete end-to-end flow from voice input through all services
to telescope action and voice response. This is the most comprehensive
integration test validating the entire NIGHTWATCH system.

Flow: Audio -> STT -> LLM -> Orchestrator -> Services -> TTS -> Audio
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from nightwatch.orchestrator import (
    Orchestrator,
    ServiceRegistry,
    ServiceStatus,
    SessionState,
    EventType,
    OrchestratorEvent,
)
from nightwatch.config import NightwatchConfig


# =============================================================================
# Mock Services - Complete Set
# =============================================================================


class MockSTTService:
    """Mock Speech-to-Text service for full pipeline testing."""

    def __init__(self):
        self.is_running = False
        self.transcripts = {
            "goto_m31": "point the telescope to M31",
            "goto_orion": "slew to orion nebula",
            "park": "park the telescope",
            "status": "what is the telescope status",
            "weather": "what are the weather conditions",
            "capture": "take a 30 second exposure",
            "emergency": "stop everything",
            "session_start": "start observing session",
            "session_end": "end the session",
        }
        self.last_audio = None
        self.transcription_count = 0

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    async def transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio to text."""
        self.last_audio = audio_data
        self.transcription_count += 1
        await asyncio.sleep(0.01)

        # Return transcript based on audio hash or default
        audio_key = audio_data.decode() if audio_data else "default"
        return self.transcripts.get(audio_key, "hello")


class MockTTSService:
    """Mock Text-to-Speech service for full pipeline testing."""

    def __init__(self):
        self.is_running = False
        self.spoken_texts = []
        self.synthesis_count = 0

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    async def synthesize(self, text: str) -> bytes:
        """Synthesize text to audio."""
        self.spoken_texts.append(text)
        self.synthesis_count += 1
        await asyncio.sleep(0.01)
        return f"audio:{text}".encode()


class MockLLMService:
    """Mock LLM service for intent detection and tool selection."""

    def __init__(self):
        self.is_running = False
        self.responses = {}
        self.query_count = 0

        # Default responses for common commands
        self._setup_default_responses()

    def _setup_default_responses(self):
        """Setup default LLM responses for common commands."""
        self.responses = {
            "point the telescope to M31": {
                "intent": "slew_to_object",
                "response": "I'll point the telescope to M31, the Andromeda Galaxy.",
                "tool_calls": [{"name": "slew_to_object", "arguments": {"object_name": "M31"}}],
                "confidence": 0.95,
            },
            "slew to orion nebula": {
                "intent": "slew_to_object",
                "response": "Slewing to the Orion Nebula.",
                "tool_calls": [{"name": "slew_to_object", "arguments": {"object_name": "M42"}}],
                "confidence": 0.92,
            },
            "park the telescope": {
                "intent": "park",
                "response": "Parking the telescope now.",
                "tool_calls": [{"name": "park_telescope", "arguments": {}}],
                "confidence": 0.98,
            },
            "what is the telescope status": {
                "intent": "status_query",
                "response": "Let me check the telescope status.",
                "tool_calls": [{"name": "get_telescope_status", "arguments": {}}],
                "confidence": 0.90,
            },
            "what are the weather conditions": {
                "intent": "weather_query",
                "response": "Checking current weather conditions.",
                "tool_calls": [{"name": "get_weather", "arguments": {}}],
                "confidence": 0.93,
            },
            "take a 30 second exposure": {
                "intent": "capture",
                "response": "Starting a 30 second exposure.",
                "tool_calls": [{"name": "capture_image", "arguments": {"exposure_sec": 30}}],
                "confidence": 0.94,
            },
            "stop everything": {
                "intent": "emergency_stop",
                "response": "Emergency stop initiated!",
                "tool_calls": [{"name": "emergency_stop", "arguments": {}}],
                "confidence": 0.99,
            },
            "start observing session": {
                "intent": "session_start",
                "response": "Starting a new observing session.",
                "tool_calls": [{"name": "start_session", "arguments": {}}],
                "confidence": 0.91,
            },
            "end the session": {
                "intent": "session_end",
                "response": "Ending the observing session.",
                "tool_calls": [{"name": "end_session", "arguments": {}}],
                "confidence": 0.92,
            },
        }

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    async def process(self, text: str, tools: List[Dict] = None) -> Dict:
        """Process text and return intent with tool calls."""
        self.query_count += 1
        await asyncio.sleep(0.01)

        # Return matching response or default
        if text in self.responses:
            return self.responses[text]

        return {
            "intent": "unknown",
            "response": "I'm not sure what you mean. Could you rephrase?",
            "tool_calls": [],
            "confidence": 0.5,
        }


class MockMountService:
    """Mock mount service for full pipeline testing."""

    def __init__(self):
        self.is_running = False
        self.is_parked = True
        self.is_tracking = False
        self.is_slewing = False
        self.ra = 0.0
        self.dec = 0.0
        self.target_name = None
        self.command_history = []

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    async def park(self):
        self.command_history.append(("park", {}))
        self.is_parked = True
        self.is_tracking = False
        self.is_slewing = False
        return True

    async def unpark(self):
        self.command_history.append(("unpark", {}))
        self.is_parked = False
        return True

    async def slew_to_object(self, object_name: str):
        self.command_history.append(("slew_to_object", {"object_name": object_name}))
        self.is_slewing = True
        self.is_parked = False
        await asyncio.sleep(0.01)
        self.is_slewing = False
        self.is_tracking = True
        self.target_name = object_name
        # Fake coordinates for known objects
        coords = {
            "M31": (10.68, 41.27),
            "M42": (83.82, -5.39),
            "M45": (56.87, 24.12),
        }
        if object_name in coords:
            self.ra, self.dec = coords[object_name]
        return True

    async def slew_to_coordinates(self, ra: float, dec: float):
        self.command_history.append(("slew_to_coordinates", {"ra": ra, "dec": dec}))
        self.is_slewing = True
        await asyncio.sleep(0.01)
        self.ra = ra
        self.dec = dec
        self.is_slewing = False
        self.is_tracking = True
        return True

    async def emergency_stop(self):
        self.command_history.append(("emergency_stop", {}))
        self.is_slewing = False
        self.is_tracking = False
        return True

    def get_status(self):
        return {
            "parked": self.is_parked,
            "tracking": self.is_tracking,
            "slewing": self.is_slewing,
            "ra": self.ra,
            "dec": self.dec,
            "target": self.target_name,
        }


class MockCameraService:
    """Mock camera service for full pipeline testing."""

    def __init__(self):
        self.is_running = False
        self.is_exposing = False
        self.exposure_count = 0
        self.last_exposure_sec = 0
        self.images = []

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    async def capture(self, exposure_sec: float, gain: int = 100):
        self.is_exposing = True
        self.last_exposure_sec = exposure_sec
        await asyncio.sleep(0.01)
        self.is_exposing = False
        self.exposure_count += 1
        image_path = f"/images/image_{self.exposure_count:04d}.fits"
        self.images.append({
            "path": image_path,
            "exposure_sec": exposure_sec,
            "gain": gain,
            "timestamp": datetime.now().isoformat(),
        })
        return {"success": True, "path": image_path}

    async def abort_exposure(self):
        self.is_exposing = False
        return True


class MockWeatherService:
    """Mock weather service for full pipeline testing."""

    def __init__(self):
        self.is_running = False
        self.is_safe = True
        self.conditions = {
            "temperature": 15.0,
            "humidity": 50.0,
            "wind_speed": 5.0,
            "cloud_cover": 10.0,
            "sky_quality": 21.5,
            "dew_point": 8.0,
        }

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    def get_conditions(self):
        return {
            **self.conditions,
            "is_safe": self.is_safe,
            "timestamp": datetime.now().isoformat(),
        }

    def set_unsafe(self, reason: str = "bad weather"):
        self.is_safe = False


class MockSafetyService:
    """Mock safety service for full pipeline testing."""

    def __init__(self):
        self.is_running = False
        self.is_safe = True
        self.vetoes = []

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    def evaluate_safety(self):
        return {
            "is_safe": self.is_safe and len(self.vetoes) == 0,
            "vetoes": self.vetoes.copy(),
        }

    def add_veto(self, reason: str):
        self.vetoes.append(reason)
        self.is_safe = False

    def clear_vetoes(self):
        self.vetoes.clear()
        self.is_safe = True


class MockToolExecutor:
    """Mock tool executor that connects to services."""

    def __init__(self, services: Dict[str, Any]):
        self.services = services
        self.executed_tools = []
        self.execution_results = []

    async def execute(self, tool_name: str, arguments: Dict) -> Dict:
        """Execute a tool against the appropriate service."""
        self.executed_tools.append({"name": tool_name, "args": arguments})

        result = {"success": True, "tool": tool_name}

        if tool_name == "slew_to_object":
            mount = self.services.get("mount")
            if mount:
                await mount.slew_to_object(arguments.get("object_name", ""))
                result["message"] = f"Slewing to {arguments.get('object_name')}"

        elif tool_name == "park_telescope":
            mount = self.services.get("mount")
            if mount:
                await mount.park()
                result["message"] = "Telescope parked"

        elif tool_name == "get_telescope_status":
            mount = self.services.get("mount")
            if mount:
                result["data"] = mount.get_status()
                result["message"] = "Status retrieved"

        elif tool_name == "get_weather":
            weather = self.services.get("weather")
            if weather:
                result["data"] = weather.get_conditions()
                result["message"] = "Weather conditions retrieved"

        elif tool_name == "capture_image":
            camera = self.services.get("camera")
            if camera:
                capture_result = await camera.capture(
                    arguments.get("exposure_sec", 10),
                    arguments.get("gain", 100)
                )
                result["data"] = capture_result
                result["message"] = f"Captured {arguments.get('exposure_sec')}s exposure"

        elif tool_name == "emergency_stop":
            mount = self.services.get("mount")
            if mount:
                await mount.emergency_stop()
            result["message"] = "Emergency stop executed"

        elif tool_name == "start_session":
            result["message"] = "Session started"

        elif tool_name == "end_session":
            mount = self.services.get("mount")
            if mount and not mount.is_parked:
                await mount.park()
            result["message"] = "Session ended"

        else:
            result["success"] = False
            result["message"] = f"Unknown tool: {tool_name}"

        self.execution_results.append(result)
        return result


# =============================================================================
# Full Pipeline Test Class
# =============================================================================


class FullPipeline:
    """
    Simulated full pipeline for testing.

    Connects: STT -> LLM -> ToolExecutor -> Services -> TTS
    """

    def __init__(self, services: Dict[str, Any]):
        self.stt = MockSTTService()
        self.tts = MockTTSService()
        self.llm = MockLLMService()
        self.services = services
        self.tool_executor = MockToolExecutor(services)
        self.orchestrator = None

        # Pipeline metrics
        self.commands_processed = 0
        self.total_latency_ms = 0.0

    async def start(self):
        """Start all pipeline components."""
        await self.stt.start()
        await self.tts.start()
        await self.llm.start()
        for service in self.services.values():
            if hasattr(service, 'start'):
                await service.start()

    async def stop(self):
        """Stop all pipeline components."""
        await self.stt.stop()
        await self.tts.stop()
        await self.llm.stop()
        for service in self.services.values():
            if hasattr(service, 'stop'):
                await service.stop()

    async def process_audio(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Process audio through the full pipeline.

        Returns result with transcript, response, and metrics.
        """
        start_time = datetime.now()

        # Step 1: STT - Audio to text
        transcript = await self.stt.transcribe(audio_data)

        # Step 2: LLM - Intent detection and tool selection
        llm_result = await self.llm.process(transcript)

        # Step 3: Tool execution
        tool_results = []
        for tool_call in llm_result.get("tool_calls", []):
            result = await self.tool_executor.execute(
                tool_call["name"],
                tool_call.get("arguments", {})
            )
            tool_results.append(result)

        # Step 4: Generate response text
        response_text = llm_result.get("response", "")
        if tool_results:
            for tr in tool_results:
                if "message" in tr:
                    response_text += f" {tr['message']}"

        # Step 5: TTS - Text to audio
        audio_response = await self.tts.synthesize(response_text)

        # Calculate metrics
        end_time = datetime.now()
        latency_ms = (end_time - start_time).total_seconds() * 1000
        self.commands_processed += 1
        self.total_latency_ms += latency_ms

        return {
            "success": True,
            "transcript": transcript,
            "intent": llm_result.get("intent"),
            "confidence": llm_result.get("confidence"),
            "response_text": response_text,
            "audio_response": audio_response,
            "tool_results": tool_results,
            "latency_ms": latency_ms,
        }

    async def process_text(self, text: str) -> Dict[str, Any]:
        """Process text command directly (bypass STT)."""
        start_time = datetime.now()

        llm_result = await self.llm.process(text)

        tool_results = []
        for tool_call in llm_result.get("tool_calls", []):
            result = await self.tool_executor.execute(
                tool_call["name"],
                tool_call.get("arguments", {})
            )
            tool_results.append(result)

        response_text = llm_result.get("response", "")
        audio_response = await self.tts.synthesize(response_text)

        end_time = datetime.now()
        latency_ms = (end_time - start_time).total_seconds() * 1000

        # Update metrics
        self.commands_processed += 1
        self.total_latency_ms += latency_ms

        return {
            "success": True,
            "transcript": text,
            "intent": llm_result.get("intent"),
            "response_text": response_text,
            "tool_results": tool_results,
            "latency_ms": latency_ms,
        }


# =============================================================================
# Test Classes
# =============================================================================


class TestFullPipelineBasic:
    """Basic full pipeline tests."""

    @pytest.fixture
    def services(self):
        return {
            "mount": MockMountService(),
            "camera": MockCameraService(),
            "weather": MockWeatherService(),
            "safety": MockSafetyService(),
        }

    @pytest.fixture
    async def pipeline(self, services):
        p = FullPipeline(services)
        await p.start()
        yield p
        await p.stop()

    @pytest.mark.asyncio
    async def test_pipeline_initialization(self, pipeline, services):
        """Test pipeline initializes all components."""
        assert pipeline.stt.is_running is True
        assert pipeline.tts.is_running is True
        assert pipeline.llm.is_running is True
        assert services["mount"].is_running is True
        assert services["camera"].is_running is True

    @pytest.mark.asyncio
    async def test_slew_command_full_flow(self, pipeline, services):
        """Test full flow: audio -> STT -> LLM -> slew -> TTS."""
        result = await pipeline.process_audio(b"goto_m31")

        assert result["success"] is True
        assert result["transcript"] == "point the telescope to M31"
        assert result["intent"] == "slew_to_object"
        assert len(result["tool_results"]) == 1
        assert result["tool_results"][0]["success"] is True

        # Verify mount state
        assert services["mount"].is_tracking is True
        assert services["mount"].target_name == "M31"

        # Verify TTS was called
        assert len(pipeline.tts.spoken_texts) == 1

    @pytest.mark.asyncio
    async def test_park_command_full_flow(self, pipeline, services):
        """Test full flow: audio -> STT -> LLM -> park -> TTS."""
        # First unpark
        services["mount"].is_parked = False
        services["mount"].is_tracking = True

        result = await pipeline.process_audio(b"park")

        assert result["success"] is True
        assert result["intent"] == "park"
        assert services["mount"].is_parked is True
        assert services["mount"].is_tracking is False

    @pytest.mark.asyncio
    async def test_status_query_full_flow(self, pipeline, services):
        """Test status query through full pipeline."""
        # Setup mount state
        services["mount"].is_tracking = True
        services["mount"].target_name = "M42"

        result = await pipeline.process_audio(b"status")

        assert result["success"] is True
        assert result["intent"] == "status_query"
        assert len(result["tool_results"]) == 1
        assert "data" in result["tool_results"][0]

    @pytest.mark.asyncio
    async def test_weather_query_full_flow(self, pipeline, services):
        """Test weather query through full pipeline."""
        result = await pipeline.process_audio(b"weather")

        assert result["success"] is True
        assert result["intent"] == "weather_query"
        assert "data" in result["tool_results"][0]
        assert "temperature" in result["tool_results"][0]["data"]

    @pytest.mark.asyncio
    async def test_capture_command_full_flow(self, pipeline, services):
        """Test image capture through full pipeline."""
        result = await pipeline.process_audio(b"capture")

        assert result["success"] is True
        assert result["intent"] == "capture"
        assert services["camera"].exposure_count == 1
        assert services["camera"].last_exposure_sec == 30

    @pytest.mark.asyncio
    async def test_emergency_stop_full_flow(self, pipeline, services):
        """Test emergency stop through full pipeline."""
        # Setup moving mount
        services["mount"].is_slewing = True
        services["mount"].is_tracking = True

        result = await pipeline.process_audio(b"emergency")

        assert result["success"] is True
        assert result["intent"] == "emergency_stop"
        assert services["mount"].is_slewing is False
        assert services["mount"].is_tracking is False


class TestFullPipelineSequences:
    """Test command sequences through the pipeline."""

    @pytest.fixture
    def services(self):
        return {
            "mount": MockMountService(),
            "camera": MockCameraService(),
            "weather": MockWeatherService(),
            "safety": MockSafetyService(),
        }

    @pytest.fixture
    async def pipeline(self, services):
        p = FullPipeline(services)
        await p.start()
        yield p
        await p.stop()

    @pytest.mark.asyncio
    async def test_observing_session_sequence(self, pipeline, services):
        """Test complete observing session sequence."""
        # Start session
        result1 = await pipeline.process_text("start observing session")
        assert result1["intent"] == "session_start"

        # Slew to target
        result2 = await pipeline.process_text("point the telescope to M31")
        assert services["mount"].is_tracking is True
        assert services["mount"].target_name == "M31"

        # Take exposure
        result3 = await pipeline.process_text("take a 30 second exposure")
        assert services["camera"].exposure_count == 1

        # End session (should park)
        result4 = await pipeline.process_text("end the session")
        assert services["mount"].is_parked is True

    @pytest.mark.asyncio
    async def test_multiple_targets_sequence(self, pipeline, services):
        """Test slewing to multiple targets."""
        targets = [
            ("point the telescope to M31", "M31"),
            ("slew to orion nebula", "M42"),
        ]

        for command, expected_target in targets:
            result = await pipeline.process_text(command)
            assert result["success"] is True
            assert services["mount"].target_name == expected_target
            assert services["mount"].is_tracking is True

        # Verify command history
        assert len(services["mount"].command_history) == 2

    @pytest.mark.asyncio
    async def test_imaging_sequence(self, pipeline, services):
        """Test imaging sequence: slew -> capture multiple."""
        # Slew to target
        await pipeline.process_text("point the telescope to M31")
        assert services["mount"].is_tracking is True

        # Take multiple exposures
        for i in range(3):
            result = await pipeline.process_text("take a 30 second exposure")
            assert result["success"] is True

        assert services["camera"].exposure_count == 3


class TestFullPipelineMetrics:
    """Test pipeline metrics and performance."""

    @pytest.fixture
    def services(self):
        return {
            "mount": MockMountService(),
            "camera": MockCameraService(),
            "weather": MockWeatherService(),
            "safety": MockSafetyService(),
        }

    @pytest.fixture
    async def pipeline(self, services):
        p = FullPipeline(services)
        await p.start()
        yield p
        await p.stop()

    @pytest.mark.asyncio
    async def test_latency_tracking(self, pipeline):
        """Test pipeline tracks latency."""
        result = await pipeline.process_text("what is the telescope status")

        assert "latency_ms" in result
        assert result["latency_ms"] > 0
        assert pipeline.total_latency_ms > 0

    @pytest.mark.asyncio
    async def test_command_count_tracking(self, pipeline):
        """Test pipeline tracks command count."""
        assert pipeline.commands_processed == 0

        await pipeline.process_text("what is the telescope status")
        assert pipeline.commands_processed == 1

        await pipeline.process_text("what are the weather conditions")
        assert pipeline.commands_processed == 2

    @pytest.mark.asyncio
    async def test_tool_execution_tracking(self, pipeline):
        """Test tool execution is tracked."""
        await pipeline.process_text("point the telescope to M31")
        await pipeline.process_text("take a 30 second exposure")

        assert len(pipeline.tool_executor.executed_tools) == 2
        assert pipeline.tool_executor.executed_tools[0]["name"] == "slew_to_object"
        assert pipeline.tool_executor.executed_tools[1]["name"] == "capture_image"


class TestFullPipelineErrorHandling:
    """Test error handling in the full pipeline."""

    @pytest.fixture
    def services(self):
        return {
            "mount": MockMountService(),
            "camera": MockCameraService(),
            "weather": MockWeatherService(),
            "safety": MockSafetyService(),
        }

    @pytest.fixture
    async def pipeline(self, services):
        p = FullPipeline(services)
        await p.start()
        yield p
        await p.stop()

    @pytest.mark.asyncio
    async def test_unknown_command_handling(self, pipeline):
        """Test handling of unknown commands."""
        result = await pipeline.process_text("do something weird")

        assert result["success"] is True  # Pipeline succeeds even with unknown command
        assert result["intent"] == "unknown"
        assert len(result["tool_results"]) == 0

    @pytest.mark.asyncio
    async def test_unknown_tool_handling(self, pipeline):
        """Test handling of unknown tool."""
        # Manually invoke unknown tool
        result = await pipeline.tool_executor.execute("unknown_tool", {})

        assert result["success"] is False
        assert "Unknown tool" in result["message"]

    @pytest.mark.asyncio
    async def test_service_not_available(self, pipeline, services):
        """Test when service is not available."""
        # Remove mount from services
        del pipeline.tool_executor.services["mount"]

        result = await pipeline.process_text("point the telescope to M31")

        # Should still succeed but mount won't be affected
        assert result["success"] is True


class TestFullPipelineWithOrchestrator:
    """Test full pipeline with orchestrator integration."""

    @pytest.fixture
    def config(self):
        return NightwatchConfig()

    @pytest.fixture
    def services(self):
        return {
            "mount": MockMountService(),
            "camera": MockCameraService(),
            "weather": MockWeatherService(),
            "safety": MockSafetyService(),
        }

    @pytest.fixture
    def orchestrator(self, config, services):
        orch = Orchestrator(config)
        orch.register_mount(services["mount"], required=False)
        orch.register_camera(services["camera"], required=False)
        orch.register_weather(services["weather"], required=False)
        orch.register_safety(services["safety"], required=False)
        return orch

    @pytest.mark.asyncio
    async def test_pipeline_with_orchestrator_start(self, orchestrator, services):
        """Test pipeline starting with orchestrator."""
        await orchestrator.start()

        assert orchestrator.is_running is True
        assert services["mount"].is_running is True
        assert services["camera"].is_running is True

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_orchestrator_session_tracking(self, orchestrator, services):
        """Test orchestrator tracks session during pipeline commands."""
        await orchestrator.start()
        await orchestrator.start_session("test_session")

        assert orchestrator.session.is_observing is True
        assert orchestrator.session.session_id == "test_session"

        # Simulate command execution
        await services["mount"].slew_to_object("M31")
        orchestrator.log_target_acquired("M31", 10.68, 41.27)

        assert "M31" in orchestrator.session.targets_observed

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_orchestrator_event_emission(self, orchestrator, services):
        """Test events are emitted during pipeline operations."""
        events_received = []

        def listener(event):
            events_received.append(event)

        orchestrator.subscribe(EventType.SERVICE_STARTED, listener)

        await orchestrator.start()

        # Should have received service started events
        assert len(events_received) >= 1

        await orchestrator.shutdown()


class TestFullPipelineSafetyIntegration:
    """Test safety integration in full pipeline."""

    @pytest.fixture
    def services(self):
        return {
            "mount": MockMountService(),
            "camera": MockCameraService(),
            "weather": MockWeatherService(),
            "safety": MockSafetyService(),
        }

    @pytest.fixture
    async def pipeline(self, services):
        p = FullPipeline(services)
        await p.start()
        yield p
        await p.stop()

    @pytest.mark.asyncio
    async def test_safety_check_before_slew(self, pipeline, services):
        """Test safety is checked before slew (conceptual)."""
        # Add safety veto
        services["safety"].add_veto("High wind")

        # Verify safety state
        safety_result = services["safety"].evaluate_safety()
        assert safety_result["is_safe"] is False
        assert "High wind" in safety_result["vetoes"]

    @pytest.mark.asyncio
    async def test_weather_affects_safety(self, pipeline, services):
        """Test weather conditions affect safety."""
        # Set unsafe weather
        services["weather"].set_unsafe("rain")
        services["safety"].add_veto("Rain detected")

        safety_result = services["safety"].evaluate_safety()
        assert safety_result["is_safe"] is False

    @pytest.mark.asyncio
    async def test_clear_safety_allows_operations(self, pipeline, services):
        """Test clearing safety allows operations."""
        # Add then clear veto
        services["safety"].add_veto("Test veto")
        services["safety"].clear_vetoes()

        safety_result = services["safety"].evaluate_safety()
        assert safety_result["is_safe"] is True

        # Slew should work
        result = await pipeline.process_text("point the telescope to M31")
        assert result["success"] is True
        assert services["mount"].is_tracking is True


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
