"""
NIGHTWATCH Voice LLM Tools
Telescope Control Function Definitions

This module defines the tool/function calling interface for the LLM
to control the telescope through natural language commands.

Tools are defined following the OpenAI/Anthropic function calling format
for compatibility with various LLM backends (Llama 3.x, etc.).
"""

import json
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
import asyncio


class ToolCategory(Enum):
    """Tool categories for organization."""
    MOUNT = "mount"          # Telescope mount control
    CATALOG = "catalog"      # Object lookup
    EPHEMERIS = "ephemeris"  # Planet/sun/moon positions
    WEATHER = "weather"      # Weather conditions
    SAFETY = "safety"        # Safety status
    SESSION = "session"      # Observing session management


@dataclass
class ToolParameter:
    """Parameter definition for a tool."""
    name: str
    type: str  # "string", "number", "boolean", "array"
    description: str
    required: bool = True
    enum: Optional[List[str]] = None
    default: Optional[Any] = None


@dataclass
class Tool:
    """Tool definition for LLM function calling."""
    name: str
    description: str
    category: ToolCategory
    parameters: List[ToolParameter]
    handler: Optional[Callable] = None

    def to_openai_format(self) -> dict:
        """Convert to OpenAI function calling format."""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

    def to_anthropic_format(self) -> dict:
        """Convert to Anthropic tool format."""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

TELESCOPE_TOOLS: List[Tool] = [
    # -------------------------------------------------------------------------
    # MOUNT CONTROL TOOLS
    # -------------------------------------------------------------------------
    Tool(
        name="goto_object",
        description="Slew the telescope to point at a celestial object by name. "
                    "Accepts Messier numbers (M31), NGC/IC numbers, star names, "
                    "or planet names.",
        category=ToolCategory.MOUNT,
        parameters=[
            ToolParameter(
                name="object_name",
                type="string",
                description="Name of object to observe (e.g., 'Mars', 'M31', 'Orion Nebula', 'Vega')"
            )
        ]
    ),

    Tool(
        name="goto_coordinates",
        description="Slew telescope to specific RA/DEC coordinates.",
        category=ToolCategory.MOUNT,
        parameters=[
            ToolParameter(
                name="ra",
                type="string",
                description="Right Ascension in HH:MM:SS format"
            ),
            ToolParameter(
                name="dec",
                type="string",
                description="Declination in sDD:MM:SS format (e.g., +45:30:00)"
            )
        ]
    ),

    Tool(
        name="park_telescope",
        description="Park the telescope at its home/park position. "
                    "Use this to safely stow the telescope.",
        category=ToolCategory.MOUNT,
        parameters=[]
    ),

    Tool(
        name="unpark_telescope",
        description="Unpark the telescope to resume observations.",
        category=ToolCategory.MOUNT,
        parameters=[]
    ),

    Tool(
        name="stop_telescope",
        description="Immediately stop all telescope motion. "
                    "Use for emergency stops.",
        category=ToolCategory.MOUNT,
        parameters=[]
    ),

    Tool(
        name="start_tracking",
        description="Start sidereal tracking to follow the sky.",
        category=ToolCategory.MOUNT,
        parameters=[]
    ),

    Tool(
        name="stop_tracking",
        description="Stop tracking. The telescope will remain stationary.",
        category=ToolCategory.MOUNT,
        parameters=[]
    ),

    Tool(
        name="get_mount_status",
        description="Get current telescope position and status.",
        category=ToolCategory.MOUNT,
        parameters=[]
    ),

    Tool(
        name="sync_position",
        description="Sync the telescope's position to a known object. "
                    "Use after centering an object to improve pointing accuracy.",
        category=ToolCategory.MOUNT,
        parameters=[
            ToolParameter(
                name="object_name",
                type="string",
                description="Name of centered object to sync on"
            )
        ]
    ),

    # -------------------------------------------------------------------------
    # CATALOG TOOLS
    # -------------------------------------------------------------------------
    Tool(
        name="lookup_object",
        description="Look up information about a celestial object. "
                    "Returns coordinates, type, magnitude, and description.",
        category=ToolCategory.CATALOG,
        parameters=[
            ToolParameter(
                name="object_name",
                type="string",
                description="Object name or catalog ID (e.g., 'M31', 'Ring Nebula')"
            )
        ]
    ),

    Tool(
        name="what_am_i_looking_at",
        description="Identify what object the telescope is currently pointed at "
                    "based on its coordinates.",
        category=ToolCategory.CATALOG,
        parameters=[]
    ),

    Tool(
        name="find_objects",
        description="Search for objects matching criteria.",
        category=ToolCategory.CATALOG,
        parameters=[
            ToolParameter(
                name="object_type",
                type="string",
                description="Type of object to find",
                required=False,
                enum=["galaxy", "nebula", "cluster", "star", "planet"]
            ),
            ToolParameter(
                name="constellation",
                type="string",
                description="Constellation to search in",
                required=False
            ),
            ToolParameter(
                name="max_magnitude",
                type="number",
                description="Maximum (brightest) magnitude",
                required=False
            )
        ]
    ),

    # -------------------------------------------------------------------------
    # EPHEMERIS TOOLS
    # -------------------------------------------------------------------------
    Tool(
        name="get_planet_position",
        description="Get the current position of a planet.",
        category=ToolCategory.EPHEMERIS,
        parameters=[
            ToolParameter(
                name="planet",
                type="string",
                description="Planet name",
                enum=["mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"]
            )
        ]
    ),

    Tool(
        name="get_visible_planets",
        description="List planets currently visible above the horizon.",
        category=ToolCategory.EPHEMERIS,
        parameters=[]
    ),

    Tool(
        name="get_moon_info",
        description="Get current moon position and phase.",
        category=ToolCategory.EPHEMERIS,
        parameters=[]
    ),

    Tool(
        name="is_it_dark",
        description="Check if it's currently astronomical night "
                    "(sun more than 18 degrees below horizon).",
        category=ToolCategory.EPHEMERIS,
        parameters=[]
    ),

    Tool(
        name="whats_up_tonight",
        description="Get a summary of what's visible and recommended for observation tonight.",
        category=ToolCategory.EPHEMERIS,
        parameters=[]
    ),

    # -------------------------------------------------------------------------
    # WEATHER TOOLS
    # -------------------------------------------------------------------------
    Tool(
        name="get_weather",
        description="Get current weather conditions from the weather station.",
        category=ToolCategory.WEATHER,
        parameters=[]
    ),

    Tool(
        name="is_safe_to_observe",
        description="Check if current conditions are safe for telescope operation.",
        category=ToolCategory.SAFETY,
        parameters=[]
    ),

    Tool(
        name="get_wind_speed",
        description="Get current wind speed.",
        category=ToolCategory.WEATHER,
        parameters=[]
    ),

    Tool(
        name="get_cloud_status",
        description="Get current cloud coverage from the cloud sensor.",
        category=ToolCategory.WEATHER,
        parameters=[]
    ),
]


# =============================================================================
# TOOL REGISTRY
# =============================================================================

class ToolRegistry:
    """
    Registry of available tools for the LLM.

    Manages tool definitions and dispatches function calls.
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._handlers: Dict[str, Callable] = {}

        # Register default tools
        for tool in TELESCOPE_TOOLS:
            self.register(tool)

    def register(self, tool: Tool, handler: Optional[Callable] = None):
        """Register a tool."""
        self._tools[tool.name] = tool
        if handler:
            self._handlers[tool.name] = handler
        elif tool.handler:
            self._handlers[tool.name] = tool.handler

    def set_handler(self, tool_name: str, handler: Callable):
        """Set handler function for a tool."""
        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        self._handlers[tool_name] = handler

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self._tools.get(name)

    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_tools_by_category(self, category: ToolCategory) -> List[Tool]:
        """Get tools in a category."""
        return [t for t in self._tools.values() if t.category == category]

    def to_openai_format(self) -> List[dict]:
        """Get all tools in OpenAI format."""
        return [t.to_openai_format() for t in self._tools.values()]

    def to_anthropic_format(self) -> List[dict]:
        """Get all tools in Anthropic format."""
        return [t.to_anthropic_format() for t in self._tools.values()]

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute a tool with given arguments.

        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments as dictionary

        Returns:
            Result string for LLM response
        """
        if tool_name not in self._tools:
            return f"Error: Unknown tool '{tool_name}'"

        handler = self._handlers.get(tool_name)
        if not handler:
            return f"Error: No handler registered for '{tool_name}'"

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)

            if isinstance(result, dict):
                return json.dumps(result, indent=2)
            return str(result)

        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"


# =============================================================================
# DEFAULT HANDLERS (stubs - connect to actual services)
# =============================================================================

def create_default_handlers(
    mount_client=None,
    catalog_service=None,
    ephemeris_service=None,
    weather_client=None,
    safety_monitor=None
) -> Dict[str, Callable]:
    """
    Create default handler functions connected to services.

    Args:
        mount_client: LX200Client instance
        catalog_service: CatalogService instance
        ephemeris_service: EphemerisService instance
        weather_client: EcowittClient instance
        safety_monitor: SafetyMonitor instance

    Returns:
        Dictionary of handler functions
    """
    handlers = {}

    # Mount handlers
    async def goto_object(object_name: str) -> str:
        if not catalog_service or not mount_client:
            return "Service not available"

        # Look up coordinates
        obj = catalog_service.lookup(object_name)
        if not obj:
            # Try ephemeris for planets
            if ephemeris_service:
                try:
                    from services.ephemeris import CelestialBody
                    body = CelestialBody(object_name.lower())
                    pos = ephemeris_service.get_body_position(body)
                    ra = pos.ra_hms
                    dec = pos.dec_dms
                    success = mount_client.goto_ra_dec(ra, dec)
                    if success:
                        return f"Slewing to {object_name}"
                    return f"Failed to slew to {object_name}"
                except (ValueError, KeyError):
                    pass
            return f"Object '{object_name}' not found in catalog"

        ra = obj.ra_hms
        dec = obj.dec_dms
        success = mount_client.goto_ra_dec(ra, dec)
        if success:
            name = obj.name or obj.catalog_id
            return f"Slewing to {name} at RA {ra}, DEC {dec}"
        return f"Failed to slew to {object_name}"

    handlers["goto_object"] = goto_object

    async def park_telescope() -> str:
        if not mount_client:
            return "Mount not available"
        success = mount_client.park()
        return "Parking telescope" if success else "Failed to park"

    handlers["park_telescope"] = park_telescope

    async def stop_telescope() -> str:
        if not mount_client:
            return "Mount not available"
        mount_client.stop()
        return "Telescope stopped"

    handlers["stop_telescope"] = stop_telescope

    async def get_mount_status() -> dict:
        if not mount_client:
            return {"error": "Mount not available"}
        status = mount_client.get_status()
        if status:
            return {
                "ra": f"{status.ra_hours}h {status.ra_minutes}m {status.ra_seconds}s",
                "dec": f"{status.dec_degrees}° {status.dec_minutes}' {status.dec_seconds}\"",
                "tracking": status.is_tracking,
                "parked": status.is_parked,
                "pier_side": status.pier_side.value
            }
        return {"error": "Could not get status"}

    handlers["get_mount_status"] = get_mount_status

    # Catalog handlers
    async def lookup_object(object_name: str) -> str:
        if not catalog_service:
            return "Catalog not available"
        return catalog_service.what_is(object_name)

    handlers["lookup_object"] = lookup_object

    # Ephemeris handlers
    async def get_visible_planets() -> str:
        if not ephemeris_service:
            return "Ephemeris not available"
        visible = ephemeris_service.get_visible_planets()
        if not visible:
            return "No planets currently visible above 10 degrees"
        parts = []
        for body, pos in visible:
            parts.append(f"{body.value.capitalize()} at {pos.altitude_degrees:.1f}° altitude")
        return "Visible planets: " + ", ".join(parts)

    handlers["get_visible_planets"] = get_visible_planets

    async def is_it_dark() -> str:
        if not ephemeris_service:
            return "Ephemeris not available"
        if ephemeris_service.is_astronomical_night():
            return "Yes, it is astronomical night. Sun is more than 18 degrees below horizon."
        phase = ephemeris_service.get_twilight_phase()
        sun_alt = ephemeris_service.get_sun_altitude()
        return f"No, it is currently {phase.value}. Sun altitude is {sun_alt:.1f} degrees."

    handlers["is_it_dark"] = is_it_dark

    # Weather handlers
    async def get_weather() -> str:
        if not weather_client:
            return "Weather station not available"
        data = await weather_client.fetch_data()
        if not data:
            return "Could not fetch weather data"
        return (
            f"Temperature: {data.temperature_f:.1f}°F, "
            f"Humidity: {data.humidity_percent:.0f}%, "
            f"Wind: {data.wind_speed_mph:.1f} mph from {data.wind_direction_str}, "
            f"Condition: {data.condition.value}"
        )

    handlers["get_weather"] = get_weather

    async def is_safe_to_observe() -> str:
        if not safety_monitor:
            return "Safety monitor not available"
        status = safety_monitor.evaluate()
        if status.is_safe:
            return "Yes, conditions are safe for observation."
        return f"No, unsafe conditions: {'; '.join(status.reasons)}"

    handlers["is_safe_to_observe"] = is_safe_to_observe

    return handlers


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

TELESCOPE_SYSTEM_PROMPT = """You are NIGHTWATCH, an AI assistant for controlling an autonomous telescope observatory in central Nevada.

You help the user observe celestial objects by:
1. Looking up objects in the catalog (Messier, NGC, IC, stars, planets)
2. Pointing the telescope at objects
3. Checking weather and safety conditions
4. Providing information about what's visible tonight

When the user asks to observe an object:
1. First use lookup_object to verify it exists and get its coordinates
2. Then use goto_object to slew the telescope

When the user asks "what's up tonight" or similar:
1. Check if it's dark using is_it_dark
2. Get visible planets using get_visible_planets
3. Suggest interesting objects based on conditions

Always check is_safe_to_observe before starting any observation session.

The telescope is an Intes-Micro MN78 (7" Maksutov-Newtonian), optimized for planetary observation. Mars, Jupiter, and Saturn are priority targets when visible.

Respond conversationally but concisely. The user is at the telescope and wants quick, useful information.
"""


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    print("NIGHTWATCH Telescope Tools\n")

    registry = ToolRegistry()

    print(f"Registered {len(registry.get_all_tools())} tools:\n")

    for category in ToolCategory:
        tools = registry.get_tools_by_category(category)
        if tools:
            print(f"{category.value.upper()}:")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description[:60]}...")
            print()

    print("\nOpenAI format sample:")
    print(json.dumps(registry.get_all_tools()[0].to_openai_format(), indent=2))
