"""
Mock LLM Client for Testing.

Simulates local LLM inference for unit and integration testing.
Provides configurable responses and tool call simulation.
"""

import asyncio
import logging
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, List, Dict, Any

logger = logging.getLogger("NIGHTWATCH.fixtures.MockLLM")


class MockLLMState(Enum):
    """LLM client state."""
    DISCONNECTED = "disconnected"
    READY = "ready"
    GENERATING = "generating"
    ERROR = "error"


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""
    tool_name: str
    arguments: Dict[str, Any]
    call_id: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "call_id": self.call_id,
        }


@dataclass
class LLMResponse:
    """Response from the LLM."""
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"
    tokens_used: int = 0
    generation_time_sec: float = 0.0

    @property
    def has_tool_calls(self) -> bool:
        """Check if response includes tool calls."""
        return len(self.tool_calls) > 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "finish_reason": self.finish_reason,
            "tokens_used": self.tokens_used,
        }


@dataclass
class LLMStats:
    """LLM usage statistics."""
    total_requests: int = 0
    total_tokens: int = 0
    total_tool_calls: int = 0
    average_generation_time: float = 0.0


class MockLLM:
    """
    Mock LLM client for testing.

    Simulates local LLM inference (Llama 3.2) with:
    - Configurable response patterns
    - Tool call simulation
    - Intent recognition
    - Generation time simulation
    - Error injection

    Example:
        llm = MockLLM()
        await llm.connect()

        # Set up expected response
        llm.set_response("The current time is 10:30 PM.")

        # Or set up a tool call response
        llm.set_tool_call("get_mount_status", {})

        response = await llm.generate("What time is it?")
    """

    # Common intent patterns for testing
    INTENT_PATTERNS = {
        "slew": ["go to", "slew to", "point at", "move to", "find"],
        "park": ["park", "go home", "safe position"],
        "weather": ["weather", "conditions", "temperature", "humidity", "wind"],
        "status": ["status", "how is", "what's the", "current state"],
        "capture": ["take a photo", "capture", "expose", "image"],
        "focus": ["focus", "autofocus", "sharp"],
        "guide": ["guide", "guiding", "track"],
        "abort": ["stop", "abort", "cancel", "halt"],
    }

    def __init__(
        self,
        model_name: str = "llama-3.2-8b-instruct",
        simulate_delays: bool = True,
        generation_time_sec: float = 0.5,
    ):
        """
        Initialize mock LLM.

        Args:
            model_name: Model name for identification
            simulate_delays: Whether to simulate generation time
            generation_time_sec: Simulated generation time
        """
        self.model_name = model_name
        self.simulate_delays = simulate_delays
        self.generation_time_sec = generation_time_sec

        # State
        self._state = MockLLMState.DISCONNECTED
        self._stats = LLMStats()

        # Configured responses
        self._next_response: Optional[str] = None
        self._next_tool_calls: List[ToolCall] = []
        self._response_queue: List[LLMResponse] = []

        # Auto-response patterns
        self._auto_respond = True
        self._custom_handlers: Dict[str, Callable] = {}

        # Error injection
        self._inject_connect_error = False
        self._inject_generate_error = False
        self._inject_timeout = False

        # Callbacks
        self._generation_callbacks: List[Callable] = []

    @property
    def state(self) -> MockLLMState:
        """Get current state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if LLM is connected."""
        return self._state != MockLLMState.DISCONNECTED

    @property
    def is_generating(self) -> bool:
        """Check if currently generating."""
        return self._state == MockLLMState.GENERATING

    async def connect(self, host: str = "localhost", port: int = 8080) -> bool:
        """
        Connect to LLM service.

        Args:
            host: Service host (ignored in mock)
            port: Service port (ignored in mock)

        Returns:
            True if connected successfully
        """
        if self._inject_connect_error:
            raise ConnectionError("Mock: Simulated connection failure")

        if self.simulate_delays:
            await asyncio.sleep(0.1)

        self._state = MockLLMState.READY
        logger.info(f"MockLLM connected: {self.model_name}")
        return True

    async def disconnect(self):
        """Disconnect from LLM service."""
        self._state = MockLLMState.DISCONNECTED
        logger.info("MockLLM disconnected")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            tools: Optional list of available tools
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            LLM response
        """
        if not self.is_connected:
            raise RuntimeError("LLM not connected")

        if self._inject_generate_error:
            raise RuntimeError("Mock: Simulated generation failure")

        if self._inject_timeout:
            raise TimeoutError("Mock: Simulated generation timeout")

        self._state = MockLLMState.GENERATING
        start_time = datetime.now()

        # Simulate generation time
        if self.simulate_delays:
            await asyncio.sleep(self.generation_time_sec)

        # Get response
        response = self._get_response(prompt, tools)

        # Update stats
        generation_time = (datetime.now() - start_time).total_seconds()
        response.generation_time_sec = generation_time
        self._update_stats(response)

        self._state = MockLLMState.READY

        # Notify callbacks
        for callback in self._generation_callbacks:
            try:
                callback(response)
            except Exception as e:
                logger.error(f"Generation callback error: {e}")

        return response

    def _get_response(
        self,
        prompt: str,
        tools: Optional[List[Dict]] = None,
    ) -> LLMResponse:
        """Get the configured or auto-generated response."""
        # Check for queued responses first
        if self._response_queue:
            return self._response_queue.pop(0)

        # Check for explicit next response
        if self._next_response is not None:
            response = LLMResponse(
                content=self._next_response,
                tool_calls=self._next_tool_calls.copy(),
                tokens_used=len(self._next_response.split()) * 2,
            )
            self._next_response = None
            self._next_tool_calls = []
            return response

        # Check custom handlers
        for pattern, handler in self._custom_handlers.items():
            if pattern.lower() in prompt.lower():
                return handler(prompt)

        # Auto-generate response based on intent
        if self._auto_respond:
            return self._auto_generate(prompt, tools)

        # Default response
        return LLMResponse(
            content="I understand. How can I help you?",
            tokens_used=10,
        )

    def _auto_generate(
        self,
        prompt: str,
        tools: Optional[List[Dict]] = None,
    ) -> LLMResponse:
        """Auto-generate response based on detected intent."""
        prompt_lower = prompt.lower()

        # Detect intent and generate appropriate response
        for intent, patterns in self.INTENT_PATTERNS.items():
            if any(p in prompt_lower for p in patterns):
                return self._generate_intent_response(intent, prompt, tools)

        # Default conversational response
        return LLMResponse(
            content="I can help you with telescope operations. What would you like to do?",
            tokens_used=15,
        )

    def _generate_intent_response(
        self,
        intent: str,
        prompt: str,
        tools: Optional[List[Dict]] = None,
    ) -> LLMResponse:
        """Generate response for detected intent."""
        if intent == "slew":
            # Extract target if possible
            return LLMResponse(
                content="I'll slew the telescope to that target.",
                tool_calls=[ToolCall(
                    tool_name="slew_to_object",
                    arguments={"object_name": "target"},
                    call_id="call_1",
                )],
                finish_reason="tool_calls",
                tokens_used=25,
            )

        elif intent == "park":
            return LLMResponse(
                content="Parking the telescope now.",
                tool_calls=[ToolCall(
                    tool_name="park_mount",
                    arguments={},
                    call_id="call_1",
                )],
                finish_reason="tool_calls",
                tokens_used=15,
            )

        elif intent == "weather":
            return LLMResponse(
                content="Let me check the current weather conditions.",
                tool_calls=[ToolCall(
                    tool_name="get_weather",
                    arguments={},
                    call_id="call_1",
                )],
                finish_reason="tool_calls",
                tokens_used=20,
            )

        elif intent == "status":
            return LLMResponse(
                content="Let me get the current status.",
                tool_calls=[ToolCall(
                    tool_name="get_system_status",
                    arguments={},
                    call_id="call_1",
                )],
                finish_reason="tool_calls",
                tokens_used=18,
            )

        elif intent == "capture":
            return LLMResponse(
                content="Starting image capture.",
                tool_calls=[ToolCall(
                    tool_name="capture_image",
                    arguments={"exposure_sec": 10.0},
                    call_id="call_1",
                )],
                finish_reason="tool_calls",
                tokens_used=20,
            )

        elif intent == "abort":
            return LLMResponse(
                content="Stopping all operations.",
                tool_calls=[ToolCall(
                    tool_name="emergency_stop",
                    arguments={},
                    call_id="call_1",
                )],
                finish_reason="tool_calls",
                tokens_used=15,
            )

        # Default
        return LLMResponse(
            content=f"Processing {intent} request.",
            tokens_used=10,
        )

    def _update_stats(self, response: LLMResponse):
        """Update usage statistics."""
        self._stats.total_requests += 1
        self._stats.total_tokens += response.tokens_used
        self._stats.total_tool_calls += len(response.tool_calls)

        # Update average generation time
        n = self._stats.total_requests
        old_avg = self._stats.average_generation_time
        self._stats.average_generation_time = (
            old_avg * (n - 1) + response.generation_time_sec
        ) / n

    def get_stats(self) -> LLMStats:
        """Get usage statistics."""
        return self._stats

    # Response configuration
    def set_response(self, content: str):
        """Set the next response content."""
        self._next_response = content
        self._next_tool_calls = []

    def set_tool_call(self, tool_name: str, arguments: Dict[str, Any]):
        """Set a tool call for the next response."""
        self._next_tool_calls.append(ToolCall(
            tool_name=tool_name,
            arguments=arguments,
            call_id=f"call_{len(self._next_tool_calls) + 1}",
        ))

    def queue_response(self, response: LLMResponse):
        """Queue a response to be returned."""
        self._response_queue.append(response)

    def add_custom_handler(self, pattern: str, handler: Callable):
        """Add a custom handler for specific patterns."""
        self._custom_handlers[pattern] = handler

    def set_auto_respond(self, enabled: bool):
        """Enable/disable auto-response generation."""
        self._auto_respond = enabled

    # Callbacks
    def set_generation_callback(self, callback: Callable):
        """Register callback for generation completion."""
        self._generation_callbacks.append(callback)

    # Error injection
    def inject_connect_error(self, enable: bool = True):
        """Enable/disable connection error injection."""
        self._inject_connect_error = enable

    def inject_generate_error(self, enable: bool = True):
        """Enable/disable generation error injection."""
        self._inject_generate_error = enable

    def inject_timeout(self, enable: bool = True):
        """Enable/disable timeout injection."""
        self._inject_timeout = enable

    def reset(self):
        """Reset mock to initial state."""
        self._state = MockLLMState.DISCONNECTED
        self._stats = LLMStats()
        self._next_response = None
        self._next_tool_calls = []
        self._response_queue = []
        self._inject_connect_error = False
        self._inject_generate_error = False
        self._inject_timeout = False
