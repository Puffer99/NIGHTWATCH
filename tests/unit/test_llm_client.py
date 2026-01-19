"""
Unit tests for NIGHTWATCH LLM Client.

Tests LLM client functionality, backend selection, and token tracking.
"""

import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import pytest

from nightwatch.llm_client import (
    LLMClient,
    LLMBackend,
    LLMResponse,
    ToolCall,
    TokenUsage,
    ConversationMessage,
    MockLLMClient,
    OBSERVATORY_SYSTEM_PROMPT,
    create_llm_client,
)


class TestTokenUsage:
    """Tests for TokenUsage dataclass."""

    def test_default_values(self):
        """Test default token counts."""
        usage = TokenUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0
        assert usage.session_total_tokens == 0

    def test_add_tokens(self):
        """Test adding token counts."""
        usage = TokenUsage()
        usage.add(100, 50)

        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150
        assert usage.session_prompt_tokens == 100
        assert usage.session_completion_tokens == 50
        assert usage.session_total_tokens == 150

    def test_cumulative_tracking(self):
        """Test session token accumulation."""
        usage = TokenUsage()
        usage.add(100, 50)
        usage.add(200, 100)

        # Current request
        assert usage.prompt_tokens == 200
        assert usage.completion_tokens == 100

        # Session totals
        assert usage.session_prompt_tokens == 300
        assert usage.session_completion_tokens == 150
        assert usage.session_total_tokens == 450

    def test_to_dict(self):
        """Test dictionary conversion."""
        usage = TokenUsage()
        usage.add(100, 50)

        d = usage.to_dict()
        assert d["prompt_tokens"] == 100
        assert d["completion_tokens"] == 50
        assert d["total_tokens"] == 150
        assert d["session_total_tokens"] == 150


class TestToolCall:
    """Tests for ToolCall dataclass."""

    def test_create_tool_call(self):
        """Test creating a tool call."""
        tc = ToolCall(
            id="call_123",
            name="goto_object",
            arguments={"object_name": "M31"}
        )

        assert tc.id == "call_123"
        assert tc.name == "goto_object"
        assert tc.arguments["object_name"] == "M31"

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "id": "call_456",
            "name": "park_telescope",
            "arguments": {}
        }
        tc = ToolCall.from_dict(data)

        assert tc.id == "call_456"
        assert tc.name == "park_telescope"


class TestConversationMessage:
    """Tests for ConversationMessage dataclass."""

    def test_user_message(self):
        """Test creating user message."""
        msg = ConversationMessage(
            role="user",
            content="Point to M31"
        )

        assert msg.role == "user"
        assert msg.content == "Point to M31"
        assert msg.timestamp is not None

    def test_assistant_message_with_tools(self):
        """Test assistant message with tool calls."""
        tc = ToolCall(id="1", name="goto", arguments={})
        msg = ConversationMessage(
            role="assistant",
            content="",
            tool_calls=[tc]
        )

        assert msg.tool_calls is not None
        assert len(msg.tool_calls) == 1

    def test_to_dict(self):
        """Test dictionary conversion."""
        msg = ConversationMessage(role="user", content="Hello")
        d = msg.to_dict()

        assert d["role"] == "user"
        assert d["content"] == "Hello"

    def test_to_dict_with_tool_calls(self):
        """Test dictionary conversion with tool calls."""
        tc = ToolCall(id="1", name="test", arguments={"a": 1})
        msg = ConversationMessage(
            role="assistant",
            content="Calling tool",
            tool_calls=[tc]
        )
        d = msg.to_dict()

        assert "tool_calls" in d
        assert d["tool_calls"][0]["name"] == "test"


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_basic_response(self):
        """Test basic response."""
        response = LLMResponse(
            content="Hello!",
            model="test-model",
            latency_ms=100.0
        )

        assert response.content == "Hello!"
        assert response.model == "test-model"
        assert response.has_tool_calls is False

    def test_response_with_tool_calls(self):
        """Test response with tool calls."""
        tc = ToolCall(id="1", name="goto", arguments={})
        response = LLMResponse(
            content="",
            tool_calls=[tc]
        )

        assert response.has_tool_calls is True
        assert len(response.tool_calls) == 1


class TestMockLLMClient:
    """Tests for MockLLMClient."""

    @pytest.mark.asyncio
    async def test_default_response(self):
        """Test default mock response."""
        client = MockLLMClient()
        response = await client.chat(messages=[])

        assert response.content == "Mock response"
        assert response.model == "mock"

    @pytest.mark.asyncio
    async def test_custom_response(self):
        """Test setting custom response."""
        client = MockLLMClient()
        custom = LLMResponse(content="Custom", model="test")
        client.set_response(custom)

        response = await client.chat(messages=[])

        assert response.content == "Custom"

    @pytest.mark.asyncio
    async def test_call_count(self):
        """Test call counting."""
        client = MockLLMClient()
        await client.chat(messages=[])
        await client.chat(messages=[])

        assert client.call_count == 2

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test mock health check."""
        client = MockLLMClient()
        assert await client.health_check() is True


class TestLLMClient:
    """Tests for main LLMClient class."""

    @pytest.fixture
    def mock_client(self):
        """Create client with mock backend."""
        return LLMClient(backend=LLMBackend.MOCK)

    def test_init_with_string_backend(self):
        """Test initializing with string backend."""
        client = LLMClient(backend="mock")
        assert client.backend == LLMBackend.MOCK

    def test_init_with_enum_backend(self):
        """Test initializing with enum backend."""
        client = LLMClient(backend=LLMBackend.MOCK)
        assert client.backend == LLMBackend.MOCK

    def test_default_system_prompt(self, mock_client):
        """Test default system prompt is set."""
        assert mock_client.system_prompt == OBSERVATORY_SYSTEM_PROMPT
        assert "NIGHTWATCH" in mock_client.system_prompt

    def test_custom_system_prompt(self):
        """Test custom system prompt."""
        custom = "You are a test bot."
        client = LLMClient(backend="mock", system_prompt=custom)
        assert client.system_prompt == custom

    def test_token_tracking_initialized(self, mock_client):
        """Test token usage tracker is initialized."""
        assert mock_client.token_usage is not None
        assert mock_client.token_usage.session_total_tokens == 0

    @pytest.mark.asyncio
    async def test_chat_basic(self, mock_client):
        """Test basic chat call."""
        response = await mock_client.chat("Hello")

        assert response is not None
        assert response.content == "Mock response"

    @pytest.mark.asyncio
    async def test_chat_updates_token_usage(self, mock_client):
        """Test chat updates token tracking."""
        await mock_client.chat("Hello")

        usage = mock_client.get_token_usage()
        assert usage["session_total_tokens"] == 15  # Mock returns 10+5

    @pytest.mark.asyncio
    async def test_chat_updates_history(self, mock_client):
        """Test chat updates conversation history."""
        await mock_client.chat("Hello")

        assert len(mock_client._conversation) == 2  # user + assistant
        assert mock_client._conversation[0].role == "user"
        assert mock_client._conversation[1].role == "assistant"

    @pytest.mark.asyncio
    async def test_chat_with_tools(self, mock_client):
        """Test chat with tool definitions."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "A test tool",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
        response = await mock_client.chat("Use the tool", tools=tools)

        assert response is not None

    def test_add_tool_result(self, mock_client):
        """Test adding tool result to history."""
        mock_client.add_tool_result("call_1", "test_tool", "Result data")

        assert len(mock_client._conversation) == 1
        msg = mock_client._conversation[0]
        assert msg.role == "tool"
        assert msg.tool_call_id == "call_1"
        assert msg.name == "test_tool"
        assert msg.content == "Result data"

    def test_clear_history(self, mock_client):
        """Test clearing conversation history."""
        mock_client._conversation.append(
            ConversationMessage(role="user", content="test")
        )
        mock_client.clear_history()

        assert len(mock_client._conversation) == 0

    def test_get_token_usage(self, mock_client):
        """Test getting token usage dict."""
        mock_client.token_usage.add(100, 50)
        usage = mock_client.get_token_usage()

        assert usage["prompt_tokens"] == 100
        assert usage["completion_tokens"] == 50
        assert "session_total_tokens" in usage

    def test_reset_session_tokens(self, mock_client):
        """Test resetting session token counters."""
        mock_client.token_usage.add(100, 50)
        mock_client.reset_session_tokens()

        assert mock_client.token_usage.session_total_tokens == 0
        # Current request tokens preserved
        assert mock_client.token_usage.prompt_tokens == 100


class TestLLMClientFallback:
    """Tests for LLM client fallback behavior."""

    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self):
        """Test fallback to secondary backend when primary fails."""
        client = LLMClient(
            backend=LLMBackend.MOCK,
            fallback_backends=[LLMBackend.MOCK]
        )

        # Make primary fail health check
        primary = client._get_client(LLMBackend.MOCK)
        primary.health_check = AsyncMock(return_value=False)

        # Create a second mock that will succeed
        fallback = MockLLMClient()
        fallback.set_response(LLMResponse(content="Fallback response", model="fallback"))
        client._clients[LLMBackend.MOCK] = fallback

        response = await client.chat("Hello")
        assert response.content == "Fallback response"


class TestLLMBackend:
    """Tests for LLMBackend enum."""

    def test_backend_values(self):
        """Test backend enum values."""
        assert LLMBackend.LOCAL.value == "local"
        assert LLMBackend.ANTHROPIC.value == "anthropic"
        assert LLMBackend.OPENAI.value == "openai"
        assert LLMBackend.MOCK.value == "mock"


class TestCreateLLMClient:
    """Tests for factory function."""

    def test_create_mock_client(self):
        """Test creating mock client."""
        client = create_llm_client(backend="mock")
        assert client.backend == LLMBackend.MOCK

    def test_create_with_custom_prompt(self):
        """Test creating client with custom prompt."""
        client = create_llm_client(
            backend="mock",
            system_prompt="Custom prompt"
        )
        assert client.system_prompt == "Custom prompt"


class TestSystemPrompt:
    """Tests for observatory system prompt."""

    def test_prompt_contains_key_info(self):
        """Test system prompt contains necessary context."""
        assert "NIGHTWATCH" in OBSERVATORY_SYSTEM_PROMPT
        assert "telescope" in OBSERVATORY_SYSTEM_PROMPT.lower()
        assert "safety" in OBSERVATORY_SYSTEM_PROMPT.lower()
        assert "tool" in OBSERVATORY_SYSTEM_PROMPT.lower()

    def test_prompt_emphasizes_safety(self):
        """Test safety is emphasized in prompt."""
        assert "Safety First" in OBSERVATORY_SYSTEM_PROMPT
        assert "safety" in OBSERVATORY_SYSTEM_PROMPT.lower()

    def test_prompt_mentions_local_operation(self):
        """Test local operation is mentioned."""
        assert "local" in OBSERVATORY_SYSTEM_PROMPT.lower() or "DGX" in OBSERVATORY_SYSTEM_PROMPT
