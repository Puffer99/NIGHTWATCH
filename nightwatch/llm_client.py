"""
NIGHTWATCH LLM Client
Local-first LLM integration for voice command processing.

Provides a unified interface for LLM inference with support for:
- Local Llama 3.2 inference via llama-cpp-python (primary)
- Optional Anthropic Claude API fallback
- Optional OpenAI API fallback

The client handles tool/function calling, conversation context,
and response parsing for telescope command execution.

Usage:
    from nightwatch.llm_client import LLMClient, LLMConfig

    config = LLMConfig(backend="local", model="llama-3.2-3b")
    client = LLMClient(config)

    response = await client.chat(
        messages=[{"role": "user", "content": "Point the telescope at M31"}],
        tools=get_telescope_tools(),
    )
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger("NIGHTWATCH.LLMClient")


__all__ = [
    "LLMClient",
    "LLMBackend",
    "LLMResponse",
    "ToolCall",
    "TokenUsage",
    "ConversationMessage",
    "create_llm_client",
]


# =============================================================================
# Enums and Data Classes
# =============================================================================


class LLMBackend(Enum):
    """Supported LLM backends."""
    LOCAL = "local"          # llama-cpp-python local inference
    ANTHROPIC = "anthropic"  # Anthropic Claude API
    OPENAI = "openai"        # OpenAI API
    MOCK = "mock"            # Mock for testing


@dataclass
class TokenUsage:
    """Token usage statistics for a request (Step 291)."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    # Cumulative tracking
    session_prompt_tokens: int = 0
    session_completion_tokens: int = 0
    session_total_tokens: int = 0

    def add(self, prompt: int, completion: int):
        """Add token counts from a request."""
        self.prompt_tokens = prompt
        self.completion_tokens = completion
        self.total_tokens = prompt + completion

        self.session_prompt_tokens += prompt
        self.session_completion_tokens += completion
        self.session_total_tokens += prompt + completion

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "session_prompt_tokens": self.session_prompt_tokens,
            "session_completion_tokens": self.session_completion_tokens,
            "session_total_tokens": self.session_total_tokens,
        }


@dataclass
class ToolCall:
    """Represents a tool/function call from the LLM."""
    id: str
    name: str
    arguments: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolCall":
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            arguments=data.get("arguments", {}),
        )


@dataclass
class ConversationMessage:
    """A message in the conversation history."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls."""
        msg = {"role": self.role, "content": self.content}
        if self.tool_calls:
            msg["tool_calls"] = [
                {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                for tc in self.tool_calls
            ]
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        if self.name:
            msg["name"] = self.name
        return msg


@dataclass
class LLMResponse:
    """Response from LLM inference."""
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: str = ""
    model: str = ""
    usage: Optional[TokenUsage] = None
    latency_ms: float = 0.0

    @property
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return len(self.tool_calls) > 0


# =============================================================================
# System Prompt (Step 285)
# =============================================================================


OBSERVATORY_SYSTEM_PROMPT = """You are NIGHTWATCH, an AI assistant for controlling an autonomous astronomical observatory.

## Your Capabilities
You can control the telescope mount, camera, guider, and other observatory equipment through voice commands. You have access to tools for:
- Slewing the telescope to celestial objects by name (M31, NGC 7000, etc.) or coordinates
- Parking and unparking the telescope mount
- Checking weather conditions and safety status
- Getting information about celestial objects
- Managing observing sessions
- Controlling the camera for imaging
- Starting and stopping autoguiding

## Safety First
ALWAYS prioritize safety:
- Never attempt to move the telescope when weather conditions are unsafe
- Respect all safety vetoes from the safety monitor
- Park the telescope if conditions become dangerous
- Alert the operator to any safety concerns

## Response Style
- Be concise and direct - your responses will be spoken aloud via text-to-speech
- Use natural language appropriate for audio output
- Avoid technical jargon unless the user is clearly an expert
- Confirm critical actions before executing them
- Report the results of actions clearly

## Context
You are running locally on a DGX Spark system at a dark sky site in Nevada. The telescope is a reflecting telescope on an equatorial mount controlled via OnStepX. Weather monitoring is provided by an Ecowitt WS90 station.

When a user asks you to do something, select the appropriate tool(s) to accomplish the task. If you need clarification, ask the user before proceeding."""


# =============================================================================
# Base Client Interface
# =============================================================================


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Send chat completion request."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the backend is available."""
        pass


# =============================================================================
# Mock Client (for testing)
# =============================================================================


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing."""

    def __init__(self):
        self.responses: List[LLMResponse] = []
        self.call_count = 0

    def set_response(self, response: LLMResponse):
        """Set the next response to return."""
        self.responses.append(response)

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Return mock response."""
        self.call_count += 1

        if self.responses:
            return self.responses.pop(0)

        # Default response
        return LLMResponse(
            content="Mock response",
            model="mock",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )

    async def health_check(self) -> bool:
        """Mock always returns healthy."""
        return True


# =============================================================================
# Local Llama Client (Primary)
# =============================================================================


class LocalLlamaClient(BaseLLMClient):
    """
    Local LLM client using llama-cpp-python.

    This is the primary inference backend for NIGHTWATCH,
    running entirely on-premise on the DGX Spark.
    """

    def __init__(
        self,
        model_path: str,
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,  # -1 = all layers on GPU
        verbose: bool = False,
    ):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.verbose = verbose
        self._model = None
        self._loaded = False

    async def _ensure_loaded(self):
        """Lazily load the model."""
        if self._loaded:
            return

        try:
            from llama_cpp import Llama

            logger.info(f"Loading local model: {self.model_path}")
            self._model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                verbose=self.verbose,
            )
            self._loaded = True
            logger.info("Model loaded successfully")
        except ImportError:
            logger.error("llama-cpp-python not installed")
            raise RuntimeError("llama-cpp-python required for local inference")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Generate chat completion using local model."""
        await self._ensure_loaded()

        start_time = time.time()

        # Format messages for the model
        # Note: Tool handling depends on model's function calling support
        try:
            response = self._model.create_chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools if tools else None,
            )

            latency_ms = (time.time() - start_time) * 1000

            # Parse response
            choice = response["choices"][0]
            message = choice.get("message", {})

            # Extract tool calls if present
            tool_calls = []
            if "tool_calls" in message:
                for tc in message["tool_calls"]:
                    tool_calls.append(ToolCall(
                        id=tc.get("id", ""),
                        name=tc.get("function", {}).get("name", ""),
                        arguments=json.loads(tc.get("function", {}).get("arguments", "{}")),
                    ))

            # Token usage
            usage = TokenUsage()
            if "usage" in response:
                usage.add(
                    response["usage"].get("prompt_tokens", 0),
                    response["usage"].get("completion_tokens", 0),
                )

            return LLMResponse(
                content=message.get("content", ""),
                tool_calls=tool_calls,
                finish_reason=choice.get("finish_reason", ""),
                model=response.get("model", "local"),
                usage=usage,
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.error(f"Local inference failed: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if local model is loaded and working."""
        try:
            await self._ensure_loaded()
            return self._model is not None
        except Exception:
            return False


# =============================================================================
# Anthropic Client (Fallback)
# =============================================================================


class AnthropicClient(BaseLLMClient):
    """
    Anthropic Claude API client.

    Optional fallback when local inference is unavailable.
    Requires ANTHROPIC_API_KEY environment variable.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-haiku-20240307"):
        import os
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self._client = None

    async def _ensure_client(self):
        """Lazily initialize the client."""
        if self._client is not None:
            return

        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")

        try:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self.api_key)
        except ImportError:
            raise RuntimeError("anthropic package not installed")

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Generate chat completion using Anthropic API."""
        await self._ensure_client()

        start_time = time.time()

        # Extract system message
        system_content = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                chat_messages.append(msg)

        try:
            # Convert tools to Anthropic format
            anthropic_tools = None
            if tools:
                anthropic_tools = [
                    {
                        "name": t["function"]["name"],
                        "description": t["function"].get("description", ""),
                        "input_schema": t["function"].get("parameters", {}),
                    }
                    for t in tools
                ]

            response = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_content,
                messages=chat_messages,
                tools=anthropic_tools,
                temperature=temperature,
            )

            latency_ms = (time.time() - start_time) * 1000

            # Parse response
            content = ""
            tool_calls = []

            for block in response.content:
                if block.type == "text":
                    content = block.text
                elif block.type == "tool_use":
                    tool_calls.append(ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    ))

            usage = TokenUsage()
            usage.add(response.usage.input_tokens, response.usage.output_tokens)

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=response.stop_reason or "",
                model=self.model,
                usage=usage,
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if Anthropic API is reachable."""
        try:
            await self._ensure_client()
            # Simple test - just verify client exists
            return self._client is not None
        except Exception:
            return False


# =============================================================================
# OpenAI Client (Fallback)
# =============================================================================


class OpenAIClient(BaseLLMClient):
    """
    OpenAI API client.

    Optional fallback when local inference is unavailable.
    Requires OPENAI_API_KEY environment variable.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        import os
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self._client = None

    async def _ensure_client(self):
        """Lazily initialize the client."""
        if self._client is not None:
            return

        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not set")

        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)
        except ImportError:
            raise RuntimeError("openai package not installed")

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Generate chat completion using OpenAI API."""
        await self._ensure_client()

        start_time = time.time()

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            latency_ms = (time.time() - start_time) * 1000

            choice = response.choices[0]
            message = choice.message

            # Parse tool calls
            tool_calls = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append(ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    ))

            usage = TokenUsage()
            if response.usage:
                usage.add(response.usage.prompt_tokens, response.usage.completion_tokens)

            return LLMResponse(
                content=message.content or "",
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason or "",
                model=self.model,
                usage=usage,
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if OpenAI API is reachable."""
        try:
            await self._ensure_client()
            return self._client is not None
        except Exception:
            return False


# =============================================================================
# Main LLM Client (Step 288 - Client Selection)
# =============================================================================


class LLMClient:
    """
    Unified LLM client with automatic backend selection.

    Supports local inference (primary) with optional cloud fallbacks.
    Tracks token usage across sessions for cost monitoring.
    """

    def __init__(
        self,
        backend: Union[LLMBackend, str] = LLMBackend.LOCAL,
        model_path: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        fallback_backends: Optional[List[LLMBackend]] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize LLM client.

        Args:
            backend: Primary backend to use
            model_path: Path to local model (for LOCAL backend)
            api_key: API key (for cloud backends)
            model: Model name/identifier
            fallback_backends: Ordered list of fallback backends
            system_prompt: Custom system prompt (uses default if None)
        """
        if isinstance(backend, str):
            backend = LLMBackend(backend)

        self.backend = backend
        self.model_path = model_path
        self.api_key = api_key
        self.model = model
        self.fallback_backends = fallback_backends or []
        self.system_prompt = system_prompt or OBSERVATORY_SYSTEM_PROMPT

        # Token tracking (Step 291)
        self.token_usage = TokenUsage()

        # Conversation history
        self._conversation: List[ConversationMessage] = []
        self._max_history = 20  # Keep last N messages

        # Backend clients (lazily initialized)
        self._clients: Dict[LLMBackend, BaseLLMClient] = {}

        logger.info(f"LLM client initialized with backend: {backend.value}")

    def _get_client(self, backend: LLMBackend) -> BaseLLMClient:
        """Get or create client for backend."""
        if backend in self._clients:
            return self._clients[backend]

        if backend == LLMBackend.LOCAL:
            if not self.model_path:
                raise ValueError("model_path required for local backend")
            client = LocalLlamaClient(model_path=self.model_path)
        elif backend == LLMBackend.ANTHROPIC:
            client = AnthropicClient(api_key=self.api_key, model=self.model or "claude-3-haiku-20240307")
        elif backend == LLMBackend.OPENAI:
            client = OpenAIClient(api_key=self.api_key, model=self.model or "gpt-4o-mini")
        elif backend == LLMBackend.MOCK:
            client = MockLLMClient()
        else:
            raise ValueError(f"Unknown backend: {backend}")

        self._clients[backend] = client
        return client

    async def chat(
        self,
        message: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        include_history: bool = True,
    ) -> LLMResponse:
        """
        Send a chat message and get response.

        Args:
            message: User message
            tools: Available tools for function calling
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
            include_history: Include conversation history

        Returns:
            LLM response with content and/or tool calls
        """
        # Build messages list
        messages = [{"role": "system", "content": self.system_prompt}]

        if include_history:
            for msg in self._conversation[-self._max_history:]:
                messages.append(msg.to_dict())

        messages.append({"role": "user", "content": message})

        # Try primary backend, then fallbacks
        backends_to_try = [self.backend] + self.fallback_backends
        last_error = None

        for backend in backends_to_try:
            try:
                client = self._get_client(backend)

                if not await client.health_check():
                    logger.warning(f"Backend {backend.value} health check failed, trying next")
                    continue

                response = await client.chat(
                    messages=messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                # Update token tracking
                if response.usage:
                    self.token_usage.add(
                        response.usage.prompt_tokens,
                        response.usage.completion_tokens,
                    )

                # Update conversation history
                self._conversation.append(ConversationMessage(
                    role="user",
                    content=message,
                ))
                self._conversation.append(ConversationMessage(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls if response.tool_calls else None,
                ))

                logger.debug(f"Chat completed via {backend.value} in {response.latency_ms:.0f}ms")
                return response

            except Exception as e:
                logger.warning(f"Backend {backend.value} failed: {e}")
                last_error = e
                continue

        # All backends failed
        raise RuntimeError(f"All LLM backends failed. Last error: {last_error}")

    def add_tool_result(self, tool_call_id: str, tool_name: str, result: str):
        """Add a tool execution result to conversation history."""
        self._conversation.append(ConversationMessage(
            role="tool",
            content=result,
            tool_call_id=tool_call_id,
            name=tool_name,
        ))

    def clear_history(self):
        """Clear conversation history."""
        self._conversation.clear()
        logger.debug("Conversation history cleared")

    def get_token_usage(self) -> Dict[str, int]:
        """Get current token usage statistics (Step 291)."""
        return self.token_usage.to_dict()

    def reset_session_tokens(self):
        """Reset session token counters."""
        self.token_usage.session_prompt_tokens = 0
        self.token_usage.session_completion_tokens = 0
        self.token_usage.session_total_tokens = 0


# =============================================================================
# Factory Function
# =============================================================================


def create_llm_client(
    backend: str = "local",
    model_path: Optional[str] = None,
    **kwargs
) -> LLMClient:
    """
    Create an LLM client with configuration.

    Args:
        backend: Backend type ("local", "anthropic", "openai", "mock")
        model_path: Path to local model file
        **kwargs: Additional client configuration

    Returns:
        Configured LLMClient instance
    """
    return LLMClient(
        backend=LLMBackend(backend),
        model_path=model_path,
        **kwargs,
    )
