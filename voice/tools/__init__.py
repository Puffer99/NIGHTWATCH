"""
NIGHTWATCH Voice Tools

LLM function calling tools for telescope control.
"""

from .telescope_tools import (
    Tool,
    ToolParameter,
    ToolCategory,
    ToolRegistry,
    TELESCOPE_TOOLS,
    TELESCOPE_SYSTEM_PROMPT,
    create_default_handlers,
)

__all__ = [
    "Tool",
    "ToolParameter",
    "ToolCategory",
    "ToolRegistry",
    "TELESCOPE_TOOLS",
    "TELESCOPE_SYSTEM_PROMPT",
    "create_default_handlers",
]
