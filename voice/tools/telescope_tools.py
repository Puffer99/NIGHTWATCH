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
    GUIDING = "guiding"      # v2.0: Autoguiding control
    CAMERA = "camera"        # v2.0: Camera/imaging control
    ALERTS = "alerts"        # v2.0: Alert management
    FOCUS = "focus"          # v3.0: Focus control
    ASTROMETRY = "astrometry"  # v3.0: Plate solving
    ENCLOSURE = "enclosure"  # v3.0: Roof/dome control
    POWER = "power"          # v3.0: Power management


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

    # -------------------------------------------------------------------------
    # POS PANEL v1.0 ADDITIONS
    # -------------------------------------------------------------------------
    # These tools were added based on recommendations from the Panel of Specialists
    # design retreat (Bob Denny, Sierra Remote team, Howard Dutton)

    Tool(
        name="confirm_command",
        description="Request user confirmation before executing a critical command. "
                    "Use for park, sync, or other irreversible operations when voice "
                    "recognition confidence is below threshold.",
        category=ToolCategory.SESSION,
        parameters=[
            ToolParameter(
                name="action",
                type="string",
                description="The action requiring confirmation (e.g., 'park telescope', 'sync to M31')"
            ),
            ToolParameter(
                name="reason",
                type="string",
                description="Why confirmation is needed",
                required=False
            )
        ]
    ),

    Tool(
        name="abort_slew",
        description="Abort a slew in progress and stop all telescope motion. "
                    "Use when user says 'stop', 'abort', 'cancel', or 'wait'.",
        category=ToolCategory.MOUNT,
        parameters=[]
    ),

    Tool(
        name="get_observation_log",
        description="Get recent observation session history. "
                    "Shows what objects were observed and when.",
        category=ToolCategory.SESSION,
        parameters=[
            ToolParameter(
                name="limit",
                type="number",
                description="Maximum number of entries to return",
                required=False,
                default=10
            ),
            ToolParameter(
                name="session",
                type="string",
                description="Session ID to filter by ('current' for tonight, 'last' for previous)",
                required=False,
                enum=["current", "last", "all"]
            )
        ]
    ),

    Tool(
        name="get_sensor_health",
        description="Get health status of all observatory sensors. "
                    "Reports data freshness and any sensor failures.",
        category=ToolCategory.SAFETY,
        parameters=[]
    ),

    Tool(
        name="get_hysteresis_status",
        description="Get current safety hysteresis state. "
                    "Shows which conditions are in triggered state and clear thresholds.",
        category=ToolCategory.SAFETY,
        parameters=[]
    ),

    # -------------------------------------------------------------------------
    # POS PANEL v2.0 ADDITIONS - GUIDING
    # -------------------------------------------------------------------------
    # PHD2 integration tools (Craig Stark recommendations)

    Tool(
        name="start_guiding",
        description="Start autoguiding with PHD2. Automatically selects a guide star "
                    "and begins tracking corrections.",
        category=ToolCategory.GUIDING,
        parameters=[]
    ),

    Tool(
        name="stop_guiding",
        description="Stop autoguiding. Telescope will continue tracking but without "
                    "guide corrections.",
        category=ToolCategory.GUIDING,
        parameters=[]
    ),

    Tool(
        name="get_guiding_status",
        description="Get current autoguiding status including RMS error, SNR, "
                    "and guide star information.",
        category=ToolCategory.GUIDING,
        parameters=[]
    ),

    Tool(
        name="dither",
        description="Dither the telescope position for imaging. Moves the guide star "
                    "slightly to reduce fixed pattern noise in stacked images.",
        category=ToolCategory.GUIDING,
        parameters=[
            ToolParameter(
                name="pixels",
                type="number",
                description="Dither amount in pixels (default 5)",
                required=False,
                default=5.0
            )
        ]
    ),

    # -------------------------------------------------------------------------
    # POS PANEL v2.0 ADDITIONS - CAMERA
    # -------------------------------------------------------------------------
    # Camera control tools (Damian Peach recommendations)

    Tool(
        name="start_capture",
        description="Start planetary video capture. Records high-speed video "
                    "for later stacking into a single sharp image.",
        category=ToolCategory.CAMERA,
        parameters=[
            ToolParameter(
                name="target",
                type="string",
                description="Target name (e.g., 'Mars', 'Jupiter', 'Saturn')"
            ),
            ToolParameter(
                name="duration",
                type="number",
                description="Capture duration in seconds (default 60)",
                required=False,
                default=60.0
            )
        ]
    ),

    Tool(
        name="stop_capture",
        description="Stop the current capture session.",
        category=ToolCategory.CAMERA,
        parameters=[]
    ),

    Tool(
        name="get_camera_status",
        description="Get camera status including current settings, temperature, "
                    "and capture progress if active.",
        category=ToolCategory.CAMERA,
        parameters=[]
    ),

    Tool(
        name="set_camera_gain",
        description="Set camera gain for capture. Higher gain = brighter but noisier.",
        category=ToolCategory.CAMERA,
        parameters=[
            ToolParameter(
                name="gain",
                type="number",
                description="Gain value (0-500, typical: 250 for planets)"
            )
        ]
    ),

    Tool(
        name="set_camera_exposure",
        description="Set camera exposure time.",
        category=ToolCategory.CAMERA,
        parameters=[
            ToolParameter(
                name="exposure_ms",
                type="number",
                description="Exposure time in milliseconds (typical: 5-20ms for planets)"
            )
        ]
    ),

    # -------------------------------------------------------------------------
    # POS PANEL v2.0 ADDITIONS - ALERTS
    # -------------------------------------------------------------------------
    # Alert management tools

    Tool(
        name="get_alerts",
        description="Get recent alerts and their status.",
        category=ToolCategory.ALERTS,
        parameters=[
            ToolParameter(
                name="unacknowledged_only",
                type="boolean",
                description="Only show unacknowledged alerts",
                required=False,
                default=False
            )
        ]
    ),

    Tool(
        name="acknowledge_alert",
        description="Acknowledge an alert to stop escalation.",
        category=ToolCategory.ALERTS,
        parameters=[
            ToolParameter(
                name="alert_id",
                type="string",
                description="ID of the alert to acknowledge"
            )
        ]
    ),

    Tool(
        name="get_seeing_prediction",
        description="Get predicted astronomical seeing based on weather patterns. "
                    "Uses machine learning on weather history.",
        category=ToolCategory.WEATHER,
        parameters=[]
    ),

    # -------------------------------------------------------------------------
    # POS PANEL v3.0 ADDITIONS - FOCUS CONTROL
    # -------------------------------------------------------------------------
    # Auto-focus tools (Larry Weber recommendations)

    Tool(
        name="auto_focus",
        description="Run automatic focus routine using HFD measurement. "
                    "Finds optimal focus position by sampling V-curve.",
        category=ToolCategory.FOCUS,
        parameters=[]
    ),

    Tool(
        name="get_focus_status",
        description="Get current focus position, temperature, and whether "
                    "refocusing is needed based on temperature change.",
        category=ToolCategory.FOCUS,
        parameters=[]
    ),

    Tool(
        name="move_focus",
        description="Move focuser to specific position or by relative amount.",
        category=ToolCategory.FOCUS,
        parameters=[
            ToolParameter(
                name="position",
                type="number",
                description="Absolute position in steps, or relative steps if relative=true"
            ),
            ToolParameter(
                name="relative",
                type="boolean",
                description="If true, move by relative amount instead of absolute",
                required=False,
                default=False
            )
        ]
    ),

    Tool(
        name="enable_temp_compensation",
        description="Enable temperature-based focus compensation. "
                    "Automatically adjusts focus as temperature changes.",
        category=ToolCategory.FOCUS,
        parameters=[
            ToolParameter(
                name="enabled",
                type="boolean",
                description="True to enable, False to disable"
            )
        ]
    ),

    # -------------------------------------------------------------------------
    # POS PANEL v3.0 ADDITIONS - PLATE SOLVING
    # -------------------------------------------------------------------------
    # Astrometry tools (Dustin Lang recommendations)

    Tool(
        name="plate_solve",
        description="Plate solve current image to determine exact pointing. "
                    "Returns precise RA/DEC coordinates.",
        category=ToolCategory.ASTROMETRY,
        parameters=[
            ToolParameter(
                name="sync_mount",
                type="boolean",
                description="If true, sync mount to solved position",
                required=False,
                default=True
            )
        ]
    ),

    Tool(
        name="get_pointing_error",
        description="Get pointing error between expected and actual position "
                    "based on last plate solve.",
        category=ToolCategory.ASTROMETRY,
        parameters=[]
    ),

    Tool(
        name="center_object",
        description="Use plate solving to precisely center an object. "
                    "Iteratively solves and corrects until centered.",
        category=ToolCategory.ASTROMETRY,
        parameters=[
            ToolParameter(
                name="object_name",
                type="string",
                description="Name of object to center"
            ),
            ToolParameter(
                name="max_iterations",
                type="number",
                description="Maximum centering iterations",
                required=False,
                default=3
            )
        ]
    ),

    # -------------------------------------------------------------------------
    # POS PANEL v3.0 ADDITIONS - ENCLOSURE CONTROL
    # -------------------------------------------------------------------------
    # Roof/dome control tools (AAG CloudWatcher team recommendations)

    Tool(
        name="open_roof",
        description="Open the roll-off roof. Requires all safety conditions "
                    "to be met and telescope to be parked.",
        category=ToolCategory.ENCLOSURE,
        parameters=[]
    ),

    Tool(
        name="close_roof",
        description="Close the roll-off roof. Use emergency=true to bypass "
                    "safety checks in critical situations.",
        category=ToolCategory.ENCLOSURE,
        parameters=[
            ToolParameter(
                name="emergency",
                type="boolean",
                description="Emergency close - bypass all checks",
                required=False,
                default=False
            )
        ]
    ),

    Tool(
        name="get_roof_status",
        description="Get current roof status including position, safety conditions, "
                    "and whether it can be opened.",
        category=ToolCategory.ENCLOSURE,
        parameters=[]
    ),

    Tool(
        name="stop_roof",
        description="Immediately stop roof motion.",
        category=ToolCategory.ENCLOSURE,
        parameters=[]
    ),

    # -------------------------------------------------------------------------
    # POS PANEL v3.0 ADDITIONS - POWER MANAGEMENT
    # -------------------------------------------------------------------------
    # UPS and power control tools

    Tool(
        name="get_power_status",
        description="Get UPS status including battery level, runtime estimate, "
                    "and whether on mains or battery power.",
        category=ToolCategory.POWER,
        parameters=[]
    ),

    Tool(
        name="get_power_events",
        description="Get recent power events such as outages and restorations.",
        category=ToolCategory.POWER,
        parameters=[
            ToolParameter(
                name="hours",
                type="number",
                description="Number of hours of history to return",
                required=False,
                default=24
            )
        ]
    ),

    Tool(
        name="emergency_shutdown",
        description="Initiate emergency shutdown sequence. Closes roof, parks telescope, "
                    "and prepares for safe power loss.",
        category=ToolCategory.POWER,
        parameters=[
            ToolParameter(
                name="reason",
                type="string",
                description="Reason for emergency shutdown"
            )
        ]
    ),

    # -------------------------------------------------------------------------
    # ENCODER TOOLS (Phase 5.1 - EncoderBridge Integration)
    # -------------------------------------------------------------------------
    # High-resolution encoder feedback tools (hjd1964/EncoderBridge)

    Tool(
        name="get_encoder_position",
        description="Get high-resolution encoder position for both axes. "
                    "Returns absolute encoder readings for RA and DEC.",
        category=ToolCategory.MOUNT,
        parameters=[]
    ),

    Tool(
        name="get_pointing_correction",
        description="Get the current mount pointing error based on encoder feedback. "
                    "Compares encoder position to mount-reported position to detect "
                    "periodic error and backlash.",
        category=ToolCategory.MOUNT,
        parameters=[]
    ),

    # -------------------------------------------------------------------------
    # PEC TOOLS (Phase 5.1 - OnStepX Extended Commands)
    # -------------------------------------------------------------------------
    # Periodic Error Correction tools

    Tool(
        name="pec_status",
        description="Get periodic error correction (PEC) status. Shows if PEC is "
                    "recording, playing back, or ready for use.",
        category=ToolCategory.MOUNT,
        parameters=[]
    ),

    Tool(
        name="pec_start",
        description="Start periodic error correction playback. PEC must be trained "
                    "before playback can begin.",
        category=ToolCategory.MOUNT,
        parameters=[]
    ),

    Tool(
        name="pec_stop",
        description="Stop periodic error correction recording or playback.",
        category=ToolCategory.MOUNT,
        parameters=[]
    ),

    Tool(
        name="pec_record",
        description="Start recording periodic error for one worm gear cycle. "
                    "Run while autoguiding on a star for best results.",
        category=ToolCategory.MOUNT,
        parameters=[]
    ),

    Tool(
        name="get_driver_status",
        description="Get TMC stepper driver diagnostics for an axis. Reports "
                    "faults like open loads, shorts, and overtemperature.",
        category=ToolCategory.MOUNT,
        parameters=[
            ToolParameter(
                name="axis",
                type="number",
                description="Axis number (1=RA, 2=DEC)",
                required=False,
                default=1
            )
        ]
    ),

    # -------------------------------------------------------------------------
    # VOICE PIPELINE TOOLS (Phase 5.1 - Voice Interface Enhancement)
    # -------------------------------------------------------------------------
    # Voice style and feedback controls

    Tool(
        name="set_voice_style",
        description="Change the voice response style for different observing contexts. "
                    "Use 'alert' for urgent notifications, 'calm' for relaxed sessions, "
                    "'technical' for detailed diagnostic output, or 'normal' for default.",
        category=ToolCategory.SESSION,
        parameters=[
            ToolParameter(
                name="style",
                type="string",
                description="Voice style: normal, alert, calm, or technical",
                required=True,
                enum=["normal", "alert", "calm", "technical"]
            )
        ]
    ),

    # -------------------------------------------------------------------------
    # INDI DEVICE TOOLS (Phase 5.1 - INDI Integration)
    # -------------------------------------------------------------------------
    # INDI device control for cross-platform device layer (pyindi-client)

    Tool(
        name="indi_list_devices",
        description="List all connected INDI devices. Shows cameras, filter wheels, "
                    "focusers, and other equipment connected via INDI server.",
        category=ToolCategory.CAMERA,
        parameters=[]
    ),

    Tool(
        name="indi_set_filter",
        description="Change filter wheel position using INDI. Accepts filter name "
                    "(L, R, G, B, Ha, OIII, SII) or position number (1-7).",
        category=ToolCategory.CAMERA,
        parameters=[
            ToolParameter(
                name="filter_name",
                type="string",
                description="Filter name (L, R, G, B, Ha, OIII, SII) or position number (1-7)",
                required=True
            )
        ]
    ),

    Tool(
        name="indi_get_filter",
        description="Get the current filter wheel position and filter name.",
        category=ToolCategory.CAMERA,
        parameters=[]
    ),

    Tool(
        name="indi_move_focuser",
        description="Move INDI focuser to absolute position or by relative steps.",
        category=ToolCategory.FOCUS,
        parameters=[
            ToolParameter(
                name="position",
                type="number",
                description="Target position (absolute) or steps to move (if relative=true)"
            ),
            ToolParameter(
                name="relative",
                type="boolean",
                description="If true, move by relative steps instead of absolute position",
                required=False,
                default=False
            )
        ]
    ),

    Tool(
        name="indi_get_focuser_status",
        description="Get INDI focuser status including position, temperature, "
                    "and movement state.",
        category=ToolCategory.FOCUS,
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
    safety_monitor=None,
    encoder_bridge=None,
    onstepx_extended=None,
    tts_service=None,
    indi_client=None,
    indi_filter_wheel=None,
    indi_focuser=None,
) -> Dict[str, Callable]:
    """
    Create default handler functions connected to services.

    Args:
        mount_client: LX200Client instance
        catalog_service: CatalogService instance
        ephemeris_service: EphemerisService instance
        weather_client: EcowittClient instance
        safety_monitor: SafetyMonitor instance
        encoder_bridge: EncoderBridge instance for high-resolution position feedback
        onstepx_extended: OnStepXExtended instance for PEC and driver diagnostics
        tts_service: TTSService instance for voice style control
        indi_client: NightwatchINDIClient instance for INDI device communication
        indi_filter_wheel: INDIFilterWheel adapter instance
        indi_focuser: INDIFocuser adapter instance

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

    # -------------------------------------------------------------------------
    # POS PANEL v1.0 HANDLERS
    # -------------------------------------------------------------------------

    async def confirm_command(action: str, reason: str = None) -> str:
        """Request user confirmation for critical command."""
        # In production, this would trigger a confirmation prompt
        # and wait for user response via voice or button
        reason_text = f" ({reason})" if reason else ""
        return f"Please confirm: {action}{reason_text}. Say 'confirm' or 'cancel'."

    handlers["confirm_command"] = confirm_command

    async def abort_slew() -> str:
        """Abort slew and stop all motion."""
        if not mount_client:
            return "Mount not available"
        mount_client.stop()
        return "Slew aborted. Telescope stopped."

    handlers["abort_slew"] = abort_slew

    async def get_observation_log(limit: int = 10, session: str = "current") -> str:
        """Get observation session history."""
        # In production, this would query an observation database
        # For now, return a placeholder
        return f"Observation log ({session}, last {limit} entries): No observations recorded yet."

    handlers["get_observation_log"] = get_observation_log

    async def get_sensor_health() -> dict:
        """Get health status of all sensors."""
        if not safety_monitor:
            return {"error": "Safety monitor not available"}

        from datetime import datetime

        health = {
            "weather_sensor": {
                "name": "Ecowitt WS90",
                "status": "unknown",
                "last_update": None,
                "age_seconds": None
            },
            "cloud_sensor": {
                "name": "CloudWatcher",
                "status": "unknown",
                "last_update": None,
                "age_seconds": None
            },
            "ephemeris": {
                "name": "Skyfield",
                "status": "unknown",
                "last_update": None,
                "age_seconds": None
            }
        }

        # Check weather sensor
        if safety_monitor._weather_data:
            age = (datetime.now() - safety_monitor._weather_data.timestamp).total_seconds()
            health["weather_sensor"]["last_update"] = safety_monitor._weather_data.timestamp.isoformat()
            health["weather_sensor"]["age_seconds"] = round(age, 1)
            health["weather_sensor"]["status"] = "ok" if age < 120 else "stale"
        else:
            health["weather_sensor"]["status"] = "no_data"

        # Check cloud sensor
        if safety_monitor._cloud_data:
            age = (datetime.now() - safety_monitor._cloud_data.timestamp).total_seconds()
            health["cloud_sensor"]["last_update"] = safety_monitor._cloud_data.timestamp.isoformat()
            health["cloud_sensor"]["age_seconds"] = round(age, 1)
            health["cloud_sensor"]["status"] = "ok" if age < 180 else "stale"
        else:
            health["cloud_sensor"]["status"] = "no_data"

        # Check ephemeris
        if safety_monitor._sun_altitude_time:
            age = (datetime.now() - safety_monitor._sun_altitude_time).total_seconds()
            health["ephemeris"]["last_update"] = safety_monitor._sun_altitude_time.isoformat()
            health["ephemeris"]["age_seconds"] = round(age, 1)
            health["ephemeris"]["status"] = "ok" if age < 600 else "stale"
        else:
            health["ephemeris"]["status"] = "no_data"

        return health

    handlers["get_sensor_health"] = get_sensor_health

    async def get_hysteresis_status() -> dict:
        """Get current safety hysteresis state."""
        if not safety_monitor:
            return {"error": "Safety monitor not available"}

        return {
            "wind_triggered": safety_monitor._wind_triggered,
            "humidity_triggered": safety_monitor._humidity_triggered,
            "cloud_triggered": safety_monitor._cloud_triggered,
            "daylight_triggered": safety_monitor._daylight_triggered,
            "thresholds": {
                "wind_limit_mph": safety_monitor.thresholds.wind_limit_mph,
                "wind_clear_mph": safety_monitor.thresholds.wind_limit_mph - safety_monitor.thresholds.wind_hysteresis_mph,
                "humidity_limit": safety_monitor.thresholds.humidity_limit,
                "humidity_clear": safety_monitor.thresholds.humidity_limit - safety_monitor.thresholds.humidity_hysteresis
            }
        }

    handlers["get_hysteresis_status"] = get_hysteresis_status

    # -------------------------------------------------------------------------
    # ENCODER HANDLERS (Phase 5.1)
    # -------------------------------------------------------------------------

    async def get_encoder_position() -> str:
        """Get high-resolution encoder position."""
        if not encoder_bridge:
            return "Encoder bridge not available"

        position = await encoder_bridge.get_position()
        if not position:
            return "Could not read encoder position"

        return (
            f"Encoder position:\n"
            f"  Axis 1 (RA): {position.axis1_degrees:.4f}° ({position.axis1_counts} counts)\n"
            f"  Axis 2 (DEC): {position.axis2_degrees:.4f}° ({position.axis2_counts} counts)"
        )

    handlers["get_encoder_position"] = get_encoder_position

    async def get_pointing_correction() -> str:
        """Get pointing error from encoder vs mount position."""
        if not encoder_bridge or not mount_client:
            return "Encoder bridge or mount not available"

        # Get mount-reported position
        status = mount_client.get_status()
        if not status:
            return "Could not get mount position"

        # Convert mount position to degrees
        mount_ra_deg = (
            status.ra_hours + status.ra_minutes / 60 + status.ra_seconds / 3600
        ) * 15.0  # Convert hours to degrees
        mount_dec_deg = (
            status.dec_degrees
            + (status.dec_minutes / 60 if status.dec_degrees >= 0 else -status.dec_minutes / 60)
            + (status.dec_seconds / 3600 if status.dec_degrees >= 0 else -status.dec_seconds / 3600)
        )

        # Get encoder error
        error = await encoder_bridge.get_position_error(mount_ra_deg, mount_dec_deg)
        if not error:
            return "Could not calculate pointing error"

        error_ra, error_dec = error
        # Convert to arcseconds for readability
        error_ra_arcsec = error_ra * 3600
        error_dec_arcsec = error_dec * 3600

        return (
            f"Pointing error (encoder - mount):\n"
            f"  RA: {error_ra_arcsec:.1f}\" ({error_ra:.4f}°)\n"
            f"  DEC: {error_dec_arcsec:.1f}\" ({error_dec:.4f}°)"
        )

    handlers["get_pointing_correction"] = get_pointing_correction

    # -------------------------------------------------------------------------
    # PEC HANDLERS (Phase 5.1)
    # -------------------------------------------------------------------------

    async def pec_status() -> str:
        """Get PEC recording/playback status."""
        if not onstepx_extended:
            return "OnStepX extended commands not available"

        status = await onstepx_extended.pec_status()
        if status.playing:
            return "PEC is actively playing back corrections"
        elif status.recording:
            progress = f" ({status.record_progress * 100:.0f}% complete)" if status.record_progress > 0 else ""
            return f"PEC is recording{progress}"
        elif status.ready:
            return "PEC is trained and ready for playback"
        else:
            return "PEC is not configured (no data recorded)"

    handlers["pec_status"] = pec_status

    async def pec_start() -> str:
        """Start PEC playback."""
        if not onstepx_extended:
            return "OnStepX extended commands not available"

        if await onstepx_extended.pec_start_playback():
            return "PEC playback started - periodic error correction is now active"
        return "Failed to start PEC playback. Is PEC data available?"

    handlers["pec_start"] = pec_start

    async def pec_stop() -> str:
        """Stop PEC recording or playback."""
        if not onstepx_extended:
            return "OnStepX extended commands not available"

        if await onstepx_extended.pec_stop():
            return "PEC stopped"
        return "Failed to stop PEC"

    handlers["pec_stop"] = pec_stop

    async def pec_record() -> str:
        """Start PEC recording."""
        if not onstepx_extended:
            return "OnStepX extended commands not available"

        if await onstepx_extended.pec_record():
            return (
                "PEC recording started. Recording will capture one complete worm gear cycle. "
                "For best results, ensure autoguiding is active on a bright star."
            )
        return "Failed to start PEC recording"

    handlers["pec_record"] = pec_record

    async def get_driver_status(axis: int = 1) -> str:
        """Get TMC driver diagnostics."""
        if not onstepx_extended:
            return "OnStepX extended commands not available"

        status = await onstepx_extended.get_driver_status(axis)
        axis_name = "RA" if axis == 1 else "DEC"

        issues = []
        if status.open_load_a:
            issues.append("Open load on coil A")
        if status.open_load_b:
            issues.append("Open load on coil B")
        if status.short_to_ground_a:
            issues.append("Short to ground on coil A")
        if status.short_to_ground_b:
            issues.append("Short to ground on coil B")
        if status.overtemperature:
            issues.append("OVERTEMPERATURE WARNING")
        if status.overtemperature_pre:
            issues.append("Overtemperature pre-warning")
        if status.stallguard:
            issues.append("Stall detected")

        if issues:
            return f"Axis {axis} ({axis_name}) driver issues:\n  " + "\n  ".join(issues)
        elif status.standstill:
            return f"Axis {axis} ({axis_name}) driver: OK (motor at standstill)"
        else:
            return f"Axis {axis} ({axis_name}) driver: OK (motor running)"

    handlers["get_driver_status"] = get_driver_status

    # -------------------------------------------------------------------------
    # VOICE PIPELINE HANDLERS (Phase 5.1)
    # -------------------------------------------------------------------------

    # Track current voice style (module-level state for simplicity)
    _voice_state = {"style": "normal"}

    async def set_voice_style(style: str) -> str:
        """Set voice response style."""
        valid_styles = ["normal", "alert", "calm", "technical"]
        style_lower = style.lower()

        if style_lower not in valid_styles:
            return f"Invalid style '{style}'. Valid options: {', '.join(valid_styles)}"

        _voice_state["style"] = style_lower

        # Apply style to TTS service if available
        if tts_service and hasattr(tts_service, 'config'):
            if style_lower == "alert":
                tts_service.config.rate = 1.2  # Faster speech
            elif style_lower == "calm":
                tts_service.config.rate = 0.9  # Slower, relaxed
            elif style_lower == "technical":
                tts_service.config.rate = 1.0  # Normal speed, detailed output
            else:  # normal
                tts_service.config.rate = 1.0

        style_descriptions = {
            "normal": "Standard conversational responses",
            "alert": "Faster, more urgent notifications",
            "calm": "Slower, relaxed delivery for visual observation",
            "technical": "Detailed diagnostic output with precise values"
        }

        return f"Voice style set to {style_lower}. {style_descriptions[style_lower]}."

    handlers["set_voice_style"] = set_voice_style

    # -------------------------------------------------------------------------
    # INDI DEVICE HANDLERS (Phase 5.1)
    # -------------------------------------------------------------------------

    async def indi_list_devices() -> str:
        """List all connected INDI devices."""
        if not indi_client:
            return "INDI client not available. Ensure INDI server is running."

        devices = list(indi_client._devices.keys())
        if not devices:
            return "No INDI devices connected. Check INDI server status."

        # Group devices by type based on common naming conventions
        device_list = []
        for name in sorted(devices):
            device_list.append(f"  - {name}")

        return f"Connected INDI devices ({len(devices)}):\n" + "\n".join(device_list)

    handlers["indi_list_devices"] = indi_list_devices

    async def indi_set_filter(filter_name: str) -> str:
        """Set filter wheel position by name or number."""
        if not indi_filter_wheel:
            return "INDI filter wheel not available"

        # Check if it's a number
        try:
            position = int(filter_name)
            success = indi_filter_wheel.set_filter(position)
            if success:
                return f"Moving filter wheel to position {position}"
            return f"Failed to move filter wheel to position {position}"
        except ValueError:
            pass

        # It's a filter name - try to set by name
        filter_name_upper = filter_name.upper()
        if hasattr(indi_filter_wheel, 'set_filter_by_name'):
            success = indi_filter_wheel.set_filter_by_name(filter_name_upper)
            if success:
                return f"Moving filter wheel to {filter_name_upper} filter"
            return f"Failed to move to filter '{filter_name}'. Available filters may include: L, R, G, B, Ha, OIII, SII"
        else:
            # Fall back to looking up position from filter names
            filter_names = indi_filter_wheel.get_filter_names() if hasattr(indi_filter_wheel, 'get_filter_names') else []
            for idx, name in enumerate(filter_names):
                if name.upper() == filter_name_upper:
                    success = indi_filter_wheel.set_filter(idx + 1)
                    if success:
                        return f"Moving filter wheel to {filter_name_upper} filter (position {idx + 1})"
                    return f"Failed to move filter wheel to position {idx + 1}"
            return f"Filter '{filter_name}' not found. Available: {', '.join(filter_names) if filter_names else 'unknown'}"

    handlers["indi_set_filter"] = indi_set_filter

    async def indi_get_filter() -> str:
        """Get current filter wheel position."""
        if not indi_filter_wheel:
            return "INDI filter wheel not available"

        position = indi_filter_wheel.get_filter()
        if position is None:
            return "Could not read filter position"

        # Try to get filter name
        filter_name = None
        if hasattr(indi_filter_wheel, 'get_filter_name'):
            filter_name = indi_filter_wheel.get_filter_name()

        if filter_name:
            return f"Current filter: {filter_name} (position {position})"
        return f"Current filter position: {position}"

    handlers["indi_get_filter"] = indi_get_filter

    async def indi_move_focuser(position: int, relative: bool = False) -> str:
        """Move INDI focuser to position."""
        if not indi_focuser:
            return "INDI focuser not available"

        if relative:
            success = indi_focuser.move_relative(position)
            direction = "out" if position > 0 else "in"
            if success:
                return f"Moving focuser {abs(position)} steps {direction}"
            return f"Failed to move focuser"
        else:
            success = indi_focuser.move_absolute(position)
            if success:
                return f"Moving focuser to position {position}"
            return f"Failed to move focuser to position {position}"

    handlers["indi_move_focuser"] = indi_move_focuser

    async def indi_get_focuser_status() -> str:
        """Get INDI focuser status."""
        if not indi_focuser:
            return "INDI focuser not available"

        position = indi_focuser.get_position()
        is_moving = indi_focuser.is_moving() if hasattr(indi_focuser, 'is_moving') else None
        temperature = indi_focuser.get_temperature() if hasattr(indi_focuser, 'get_temperature') else None

        status_parts = []
        if position is not None:
            status_parts.append(f"Position: {position} steps")
        if is_moving is not None:
            status_parts.append(f"Moving: {'Yes' if is_moving else 'No'}")
        if temperature is not None:
            status_parts.append(f"Temperature: {temperature:.1f}°C")

        if not status_parts:
            return "Could not read focuser status"

        return "INDI Focuser status:\n  " + "\n  ".join(status_parts)

    handlers["indi_get_focuser_status"] = indi_get_focuser_status

    return handlers


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

TELESCOPE_SYSTEM_PROMPT = """You are NIGHTWATCH, an AI assistant for controlling an autonomous telescope observatory in central Nevada.

Observatory: Intes-Micro MN78 (7" f/6 Maksutov-Newtonian) on DIY harmonic drive GEM mount.
Location: Central Nevada dark sky site (~6000 ft elevation, 280+ clear nights/year).
Controller: OnStepX on Teensy 4.1 with TMC5160 drivers.
Imaging Camera: ZWO ASI662MC for planetary imaging.
Guide Camera: ASI120MM-S with PHD2 autoguiding.
Focuser: ZWO EAF with temperature compensation.
Enclosure: Roll-off roof with weather interlocks.
Power: APC Smart-UPS with NUT monitoring.
Version: 3.2 (POS Panel certified - Full Automation + INDI Support)

You help the user observe and image celestial objects by:
1. Managing the complete observatory (roof, power, safety)
2. Pointing and tracking celestial objects
3. Auto-focusing and plate solving for precision
4. Controlling camera capture and guiding
5. Monitoring conditions and responding to events

SAFETY PROTOCOL (POS Panel v1.0):
- Always check is_safe_to_observe before starting any observation session
- Use confirm_command for critical operations when voice confidence is low
- Respond immediately to "stop", "abort", or "cancel" with abort_slew
- Use get_sensor_health to diagnose connection issues
- The safety system uses hysteresis - conditions must improve past thresholds to clear

IMAGING WORKFLOW (POS Panel v2.0):
1. Check conditions with is_safe_to_observe and get_seeing_prediction
2. GOTO target with goto_object
3. Start autoguiding with start_guiding (wait for RMS < 1")
4. Begin capture with start_capture (60-90 seconds for planets)
5. Dither between captures with dither to reduce noise

FULL AUTOMATION WORKFLOW (POS Panel v3.0):
1. Check get_power_status to ensure UPS is healthy
2. Check conditions with is_safe_to_observe
3. Open roof with open_roof (verifies telescope parked, weather safe)
4. Unpark telescope with unpark_telescope
5. GOTO target with goto_object
6. Plate solve with plate_solve to verify pointing
7. Auto-focus with auto_focus (or enable_temp_compensation for continuous)
8. Start guiding with start_guiding
9. Begin imaging with start_capture
10. Monitor with get_focus_status, get_guiding_status, get_alerts
11. Close session: stop_capture, stop_guiding, park_telescope, close_roof

ENCLOSURE SAFETY (v3.0):
- NEVER open roof without checking get_roof_status first
- Roof will auto-close on rain detection (hardware interlock)
- Rain holdoff: 30 minutes after last rain before roof can reopen
- Telescope MUST be parked before roof can open
- Use close_roof with emergency=true only for critical situations

FOCUS MANAGEMENT (v3.0):
- Run auto_focus after large slews or temperature changes
- Use get_focus_status to check if refocus needed (every 2°C or 30 min)
- enable_temp_compensation for automated focus adjustment
- Temperature coefficient: ~2.5 steps/°C typical

PLATE SOLVING (v3.0):
- Use plate_solve after GOTO to verify pointing accuracy
- Use center_object to precisely center faint targets
- get_pointing_error shows deviation from expected position
- Sync improves pointing model for future GOTOs

POWER MANAGEMENT (v3.0):
- Monitor get_power_status for battery level
- At 50% battery: System auto-parks telescope
- At 20% battery: Emergency roof close and shutdown
- get_power_events shows recent power outages
- emergency_shutdown for manual safe shutdown

ENCODER FEEDBACK (v3.1 - EncoderBridge):
- get_encoder_position: Read high-resolution absolute encoder positions
- get_pointing_correction: Compare encoder vs mount positions to detect error
- Use for diagnosing periodic error and backlash
- Encoder provides "truth" for sub-arcsecond positioning accuracy

PERIODIC ERROR CORRECTION (v3.1 - PEC):
- pec_status: Check if PEC is recording, playing, or ready
- pec_record: Start recording PE for one worm gear cycle (use while guiding)
- pec_start: Begin playback of trained PEC data
- pec_stop: Stop PEC recording or playback
- get_driver_status: Check TMC5160 driver health for each axis
- PEC can reduce tracking error by 50% or more on harmonic drive mounts

VOICE INTERFACE (v3.1 - Voice Pipeline Enhancement):
- set_voice_style: Adjust response delivery for different contexts:
  - "normal": Standard conversational responses (default)
  - "alert": Faster, urgent delivery for time-sensitive notifications
  - "calm": Slower, relaxed delivery for visual observation sessions
  - "technical": Detailed diagnostic output with precise numerical values
- Switch to "calm" for relaxed visual observing, "alert" during imaging runs

INDI DEVICE CONTROL (v3.2 - Cross-Platform Device Layer):
- indi_list_devices: List all connected INDI devices (cameras, filter wheels, focusers)
- indi_set_filter: Change filter by name (L, R, G, B, Ha, OIII, SII) or position (1-7)
- indi_get_filter: Get current filter wheel position and name
- indi_move_focuser: Move INDI focuser to position (absolute or relative)
- indi_get_focuser_status: Get focuser position, temperature, and movement state
- INDI provides cross-platform device control via standard Linux drivers
- Use these tools when controlling devices through INDI server (port 7624)

Camera settings (Damian Peach recommendations):
- Mars: gain 280, exposure 8ms
- Jupiter: gain 250, exposure 12ms
- Saturn: gain 300, exposure 15ms

The MN78 is optimized for planetary observation. Mars, Jupiter, and Saturn are priority targets when visible. The high contrast design also excels on double stars and small planetary nebulae.

Respond conversationally but concisely. The user is at the telescope and wants quick, useful information. For autonomous operation, proactively monitor conditions and alert the user to issues.
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
