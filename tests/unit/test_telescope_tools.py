"""
NIGHTWATCH Unit Tests - Telescope Tools

Tests for the voice LLM tool definitions and registry.
These tests validate tool structure, format conversion, and registry operations.

Run:
    pytest tests/unit/test_telescope_tools.py -v

Note: This module imports telescope_tools.py directly to avoid numpy dependency
from the parent voice package during CI testing.
"""

import pytest
import json
import importlib.util
from pathlib import Path
from typing import List


def _import_telescope_tools():
    """
    Import telescope_tools module directly from file.

    This avoids importing the voice package which has numpy dependencies
    that may not be available during CI unit testing.
    """
    # Calculate path to telescope_tools.py relative to this test file
    test_dir = Path(__file__).parent
    project_root = test_dir.parent.parent
    module_path = project_root / "voice" / "tools" / "telescope_tools.py"

    spec = importlib.util.spec_from_file_location("telescope_tools", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Import directly from file to avoid numpy dependency in voice/__init__.py
_tt = _import_telescope_tools()
Tool = _tt.Tool
ToolParameter = _tt.ToolParameter
ToolCategory = _tt.ToolCategory
ToolRegistry = _tt.ToolRegistry
TELESCOPE_TOOLS = _tt.TELESCOPE_TOOLS
TELESCOPE_SYSTEM_PROMPT = _tt.TELESCOPE_SYSTEM_PROMPT
create_default_handlers = _tt.create_default_handlers


# ============================================================================
# Tool Definition Tests
# ============================================================================

class TestToolDefinitions:
    """Tests for individual tool definitions."""

    def test_tools_list_not_empty(self):
        """Verify TELESCOPE_TOOLS contains tools."""
        assert len(TELESCOPE_TOOLS) > 0
        assert len(TELESCOPE_TOOLS) >= 40  # Plan specifies 44+ tools

    def test_all_tools_have_required_fields(self):
        """Verify all tools have required name, description, and category."""
        for tool in TELESCOPE_TOOLS:
            assert tool.name, f"Tool missing name: {tool}"
            assert len(tool.name) > 0, f"Tool has empty name: {tool}"
            assert tool.description, f"Tool {tool.name} missing description"
            assert len(tool.description) > 10, f"Tool {tool.name} has too short description"
            assert tool.category is not None, f"Tool {tool.name} missing category"
            assert isinstance(tool.category, ToolCategory), f"Tool {tool.name} has invalid category"

    def test_tool_names_are_unique(self):
        """Verify all tool names are unique."""
        names = [tool.name for tool in TELESCOPE_TOOLS]
        assert len(names) == len(set(names)), "Duplicate tool names found"

    def test_tool_names_are_valid_identifiers(self):
        """Verify tool names are valid Python identifiers (no spaces, etc.)."""
        for tool in TELESCOPE_TOOLS:
            assert " " not in tool.name, f"Tool name contains space: {tool.name}"
            assert tool.name.replace("_", "").isalnum(), \
                f"Tool name contains invalid characters: {tool.name}"

    def test_required_tools_exist(self):
        """Verify core tools required by the system are defined."""
        required_tools = [
            # Mount control (Phase 2)
            "goto_object",
            "park_telescope",
            "stop_telescope",
            "get_mount_status",
            # Encoder/PEC (Phase 2/5.1)
            "get_encoder_position",
            "pec_status",
            "pec_start",
            # INDI tools (Phase 5.1)
            "indi_list_devices",
            "indi_set_filter",
            "indi_move_focuser",
            # Alpaca tools (Phase 5.1)
            "alpaca_discover_devices",
            "alpaca_set_filter",
            "alpaca_move_focuser",
            # Voice style (Phase 5.1)
            "set_voice_style",
        ]

        tool_names = {tool.name for tool in TELESCOPE_TOOLS}
        for required in required_tools:
            assert required in tool_names, f"Required tool '{required}' not found"


class TestToolParameters:
    """Tests for tool parameter definitions."""

    def test_parameters_have_valid_types(self):
        """Verify all parameters have valid JSON schema types."""
        valid_types = {"string", "number", "boolean", "array", "object"}

        for tool in TELESCOPE_TOOLS:
            for param in tool.parameters:
                assert param.type in valid_types, \
                    f"Tool {tool.name} parameter {param.name} has invalid type: {param.type}"

    def test_required_parameters_marked(self):
        """Verify required parameters are properly marked."""
        for tool in TELESCOPE_TOOLS:
            for param in tool.parameters:
                assert isinstance(param.required, bool), \
                    f"Tool {tool.name} parameter {param.name} 'required' should be boolean"

    def test_enum_parameters_have_values(self):
        """Verify parameters with enum have at least 2 values."""
        for tool in TELESCOPE_TOOLS:
            for param in tool.parameters:
                if param.enum is not None:
                    assert len(param.enum) >= 2, \
                        f"Tool {tool.name} parameter {param.name} enum should have >= 2 values"


# ============================================================================
# Tool Category Tests
# ============================================================================

class TestToolCategories:
    """Tests for tool categories."""

    def test_all_categories_have_tools(self):
        """Verify each category has at least one tool."""
        tools_by_category = {}
        for tool in TELESCOPE_TOOLS:
            cat = tool.category
            if cat not in tools_by_category:
                tools_by_category[cat] = []
            tools_by_category[cat].append(tool)

        # Core categories should have tools
        required_categories = [
            ToolCategory.MOUNT,
            ToolCategory.CATALOG,
            ToolCategory.WEATHER,
            ToolCategory.CAMERA,
            ToolCategory.FOCUS,
        ]

        for cat in required_categories:
            assert cat in tools_by_category, f"Category {cat} has no tools"
            assert len(tools_by_category[cat]) > 0, f"Category {cat} is empty"

    def test_mount_category_has_encoder_and_pec(self):
        """Verify MOUNT category includes encoder and PEC tools (Phase 5.1)."""
        mount_tools = [t for t in TELESCOPE_TOOLS if t.category == ToolCategory.MOUNT]
        mount_names = {t.name for t in mount_tools}

        assert "get_encoder_position" in mount_names, "Encoder tool missing from MOUNT"
        assert "pec_status" in mount_names, "PEC tool missing from MOUNT"


# ============================================================================
# Format Conversion Tests
# ============================================================================

class TestFormatConversion:
    """Tests for tool format conversion (OpenAI/Anthropic)."""

    def test_to_openai_format_structure(self):
        """Verify OpenAI format has correct structure."""
        tool = TELESCOPE_TOOLS[0]
        openai_format = tool.to_openai_format()

        assert "type" in openai_format
        assert openai_format["type"] == "function"
        assert "function" in openai_format
        assert "name" in openai_format["function"]
        assert "description" in openai_format["function"]
        assert "parameters" in openai_format["function"]

    def test_to_openai_format_parameters(self):
        """Verify OpenAI format parameters structure."""
        # Find a tool with parameters
        tool = next(t for t in TELESCOPE_TOOLS if len(t.parameters) > 0)
        openai_format = tool.to_openai_format()

        params = openai_format["function"]["parameters"]
        assert params["type"] == "object"
        assert "properties" in params
        assert "required" in params
        assert isinstance(params["required"], list)

    def test_to_anthropic_format_structure(self):
        """Verify Anthropic format has correct structure."""
        tool = TELESCOPE_TOOLS[0]
        anthropic_format = tool.to_anthropic_format()

        assert "name" in anthropic_format
        assert "description" in anthropic_format
        assert "input_schema" in anthropic_format
        assert anthropic_format["input_schema"]["type"] == "object"

    def test_openai_format_is_valid_json(self):
        """Verify OpenAI format produces valid JSON."""
        for tool in TELESCOPE_TOOLS[:10]:  # Test first 10 tools
            openai_format = tool.to_openai_format()
            json_str = json.dumps(openai_format)
            parsed = json.loads(json_str)
            assert parsed["function"]["name"] == tool.name

    def test_anthropic_format_is_valid_json(self):
        """Verify Anthropic format produces valid JSON."""
        for tool in TELESCOPE_TOOLS[:10]:
            anthropic_format = tool.to_anthropic_format()
            json_str = json.dumps(anthropic_format)
            parsed = json.loads(json_str)
            assert parsed["name"] == tool.name


# ============================================================================
# Tool Registry Tests
# ============================================================================

class TestToolRegistry:
    """Tests for ToolRegistry class."""

    def test_registry_initialization(self):
        """Verify registry initializes with all tools."""
        registry = ToolRegistry()
        all_tools = registry.get_all_tools()

        assert len(all_tools) == len(TELESCOPE_TOOLS)

    def test_registry_get_tool_by_name(self):
        """Verify getting tool by name works."""
        registry = ToolRegistry()

        tool = registry.get_tool("goto_object")
        assert tool is not None
        assert tool.name == "goto_object"

        tool = registry.get_tool("nonexistent_tool")
        assert tool is None

    def test_registry_get_tools_by_category(self):
        """Verify filtering tools by category."""
        registry = ToolRegistry()

        mount_tools = registry.get_tools_by_category(ToolCategory.MOUNT)
        assert len(mount_tools) > 0
        assert all(t.category == ToolCategory.MOUNT for t in mount_tools)

    def test_registry_to_openai_format(self):
        """Verify registry can export all tools in OpenAI format."""
        registry = ToolRegistry()
        openai_tools = registry.to_openai_format()

        assert isinstance(openai_tools, list)
        assert len(openai_tools) == len(TELESCOPE_TOOLS)
        assert all("function" in t for t in openai_tools)

    def test_registry_to_anthropic_format(self):
        """Verify registry can export all tools in Anthropic format."""
        registry = ToolRegistry()
        anthropic_tools = registry.to_anthropic_format()

        assert isinstance(anthropic_tools, list)
        assert len(anthropic_tools) == len(TELESCOPE_TOOLS)
        assert all("input_schema" in t for t in anthropic_tools)

    def test_registry_register_custom_tool(self):
        """Verify registering a custom tool."""
        registry = ToolRegistry()
        initial_count = len(registry.get_all_tools())

        custom_tool = Tool(
            name="test_custom_tool",
            description="A test tool",
            category=ToolCategory.SESSION,
            parameters=[]
        )

        registry.register(custom_tool)

        assert len(registry.get_all_tools()) == initial_count + 1
        assert registry.get_tool("test_custom_tool") is not None

    def test_registry_set_handler(self):
        """Verify setting handler for a tool."""
        registry = ToolRegistry()

        async def custom_handler():
            return "test result"

        registry.set_handler("goto_object", custom_handler)

        # Verify handler is set (accessing internal state for test)
        assert "goto_object" in registry._handlers


# ============================================================================
# System Prompt Tests
# ============================================================================

class TestSystemPrompt:
    """Tests for the system prompt."""

    def test_system_prompt_exists(self):
        """Verify system prompt is defined."""
        assert TELESCOPE_SYSTEM_PROMPT is not None
        assert len(TELESCOPE_SYSTEM_PROMPT) > 1000  # Should be substantial

    def test_system_prompt_mentions_key_features(self):
        """Verify system prompt documents key features."""
        prompt_lower = TELESCOPE_SYSTEM_PROMPT.lower()

        # Phase 5.1 features should be documented
        assert "encoder" in prompt_lower, "Encoder not mentioned in prompt"
        assert "pec" in prompt_lower, "PEC not mentioned in prompt"
        assert "indi" in prompt_lower, "INDI not mentioned in prompt"
        assert "alpaca" in prompt_lower, "Alpaca not mentioned in prompt"
        assert "voice" in prompt_lower, "Voice not mentioned in prompt"

    def test_system_prompt_version(self):
        """Verify system prompt has version info."""
        # Version 3.3 per last commit
        assert "3.3" in TELESCOPE_SYSTEM_PROMPT or "version" in TELESCOPE_SYSTEM_PROMPT.lower()


# ============================================================================
# Handler Creation Tests
# ============================================================================

class TestHandlerCreation:
    """Tests for default handler creation."""

    def test_create_handlers_without_services(self):
        """Verify handlers can be created without any services."""
        handlers = create_default_handlers()

        assert isinstance(handlers, dict)
        assert len(handlers) > 0

    def test_handlers_are_callable(self):
        """Verify all handlers are callable."""
        handlers = create_default_handlers()

        for name, handler in handlers.items():
            assert callable(handler), f"Handler {name} is not callable"


# ============================================================================
# Mount Tool Handler Tests (Step 351)
# ============================================================================

class TestMountToolHandlers:
    """Tests for mount tool handlers."""

    def test_mount_tools_defined(self):
        """Verify all mount control tools are defined."""
        mount_tool_names = [
            "goto_object",
            "goto_coordinates",
            "park_telescope",
            "unpark_telescope",
            "stop_telescope",
            "start_tracking",
            "stop_tracking",
            "get_mount_status",
            "sync_position",
            "home_telescope",
        ]
        tool_names = {t.name for t in TELESCOPE_TOOLS}
        for name in mount_tool_names:
            assert name in tool_names, f"Mount tool '{name}' not found"

    def test_goto_object_parameters(self):
        """Verify goto_object has object_name parameter."""
        registry = ToolRegistry()
        tool = registry.get_tool("goto_object")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "object_name" in param_names

        # object_name should be required
        object_param = next(p for p in tool.parameters if p.name == "object_name")
        assert object_param.required is True
        assert object_param.type == "string"

    def test_goto_coordinates_parameters(self):
        """Verify goto_coordinates has ra and dec parameters."""
        registry = ToolRegistry()
        tool = registry.get_tool("goto_coordinates")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "ra" in param_names
        assert "dec" in param_names

        # Both should be required
        for p in tool.parameters:
            if p.name in ("ra", "dec"):
                assert p.required is True
                assert p.type == "string"

    def test_park_telescope_parameters(self):
        """Verify park_telescope has optional confirmed parameter."""
        registry = ToolRegistry()
        tool = registry.get_tool("park_telescope")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "confirmed" in param_names

        confirmed_param = next(p for p in tool.parameters if p.name == "confirmed")
        assert confirmed_param.required is False
        assert confirmed_param.type == "boolean"

    def test_sync_position_parameters(self):
        """Verify sync_position has object_name and confirmed parameters."""
        registry = ToolRegistry()
        tool = registry.get_tool("sync_position")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "object_name" in param_names
        assert "confirmed" in param_names

    def test_mount_handlers_created(self):
        """Verify mount handlers are created in default handlers."""
        handlers = create_default_handlers()

        mount_handlers = [
            "goto_object",
            "goto_coordinates",
            "park_telescope",
            "unpark_telescope",
            "stop_telescope",
            "start_tracking",
            "stop_tracking",
            "get_mount_status",
            "sync_position",
            "home_telescope",
        ]

        for handler_name in mount_handlers:
            assert handler_name in handlers, f"Handler '{handler_name}' not created"
            assert callable(handlers[handler_name])


# ============================================================================
# Catalog Tool Handler Tests (Step 358)
# ============================================================================

class TestCatalogToolHandlers:
    """Tests for catalog tool handlers."""

    def test_catalog_tools_defined(self):
        """Verify all catalog tools are defined."""
        catalog_tool_names = [
            "lookup_object",
            "find_objects",
        ]
        tool_names = {t.name for t in TELESCOPE_TOOLS}
        for name in catalog_tool_names:
            assert name in tool_names, f"Catalog tool '{name}' not found"

    def test_lookup_object_parameters(self):
        """Verify lookup_object has object_name parameter."""
        registry = ToolRegistry()
        tool = registry.get_tool("lookup_object")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "object_name" in param_names

        name_param = next(p for p in tool.parameters if p.name == "object_name")
        assert name_param.required is True
        assert name_param.type == "string"

    def test_find_objects_parameters(self):
        """Verify find_objects has filtering parameters."""
        registry = ToolRegistry()
        tool = registry.get_tool("find_objects")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        # Should have some filtering parameters
        assert len(param_names) > 0

    def test_catalog_handlers_created(self):
        """Verify catalog handlers are created in default handlers."""
        handlers = create_default_handlers()

        catalog_handlers = [
            "lookup_object",
            "find_objects",
        ]

        for handler_name in catalog_handlers:
            assert handler_name in handlers, f"Handler '{handler_name}' not created"
            assert callable(handlers[handler_name])


# ============================================================================
# Safety Tool Handler Tests (Step 385)
# ============================================================================

class TestSafetyToolHandlers:
    """Tests for safety tool handlers."""

    def test_safety_tools_defined(self):
        """Verify all safety tools are defined."""
        safety_tool_names = [
            "is_safe_to_observe",
            "get_sensor_health",
            "get_hysteresis_status",
        ]
        tool_names = {t.name for t in TELESCOPE_TOOLS}
        for name in safety_tool_names:
            assert name in tool_names, f"Safety tool '{name}' not found"

    def test_is_safe_to_observe_no_required_params(self):
        """Verify is_safe_to_observe has no required parameters."""
        registry = ToolRegistry()
        tool = registry.get_tool("is_safe_to_observe")
        assert tool is not None

        # Should have no required parameters or all optional
        required_params = [p for p in tool.parameters if p.required]
        assert len(required_params) == 0

    def test_get_sensor_health_no_required_params(self):
        """Verify get_sensor_health has no required parameters."""
        registry = ToolRegistry()
        tool = registry.get_tool("get_sensor_health")
        assert tool is not None

        required_params = [p for p in tool.parameters if p.required]
        assert len(required_params) == 0

    def test_safety_handlers_created(self):
        """Verify safety handlers are created in default handlers."""
        handlers = create_default_handlers()

        safety_handlers = [
            "is_safe_to_observe",
            "get_sensor_health",
            "get_hysteresis_status",
        ]

        for handler_name in safety_handlers:
            assert handler_name in handlers, f"Handler '{handler_name}' not created"
            assert callable(handlers[handler_name])

    def test_safety_tools_in_correct_category(self):
        """Verify safety tools are in SAFETY category."""
        registry = ToolRegistry()
        safety_tools = registry.get_tools_by_category(ToolCategory.SAFETY)
        safety_names = {t.name for t in safety_tools}

        expected = ["is_safe_to_observe", "get_sensor_health", "get_hysteresis_status"]
        for name in expected:
            assert name in safety_names, f"'{name}' not in SAFETY category"


# ============================================================================
# Run Configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
