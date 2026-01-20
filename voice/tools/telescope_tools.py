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
                    "Use this to safely stow the telescope. "
                    "Requires confirmation if currently tracking.",
        category=ToolCategory.MOUNT,
        parameters=[
            ToolParameter(
                name="confirmed",
                type="boolean",
                description="Set to true to confirm park while tracking",
                required=False,
                default=False
            )
        ]
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
                    "Use after centering an object to improve pointing accuracy. "
                    "Requires confirmation as it modifies the pointing model.",
        category=ToolCategory.MOUNT,
        parameters=[
            ToolParameter(
                name="object_name",
                type="string",
                description="Name of centered object to sync on"
            ),
            ToolParameter(
                name="confirmed",
                type="boolean",
                description="Set to true to confirm sync operation",
                required=False,
                default=False
            )
        ]
    ),

    Tool(
        name="home_telescope",
        description="Find the telescope's home position using encoders or limit switches. "
                    "Use to recalibrate the mount's position reference.",
        category=ToolCategory.MOUNT,
        parameters=[]
    ),

    Tool(
        name="set_home_offset",
        description="Set home position offset for calibration. "
                    "Adjusts the reference point used by home_telescope.",
        category=ToolCategory.MOUNT,
        parameters=[
            ToolParameter(
                name="ra_offset_arcmin",
                type="number",
                description="Right Ascension offset in arcminutes (±60 max)",
                required=False,
                default=0.0
            ),
            ToolParameter(
                name="dec_offset_arcmin",
                type="number",
                description="Declination offset in arcminutes (±60 max)",
                required=False,
                default=0.0
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
        description="Search for objects matching criteria. "
                    "Returns objects filtered by type, constellation, magnitude, and visibility.",
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
                description="Maximum (dimmest) magnitude to include",
                required=False
            ),
            ToolParameter(
                name="min_altitude",
                type="number",
                description="Minimum altitude in degrees (default 10)",
                required=False,
                default=10.0
            ),
            ToolParameter(
                name="limit",
                type="number",
                description="Maximum number of results (default 10)",
                required=False,
                default=10
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
        description="List planets currently visible above the horizon. "
                    "Shows altitude, direction, and observation quality.",
        category=ToolCategory.EPHEMERIS,
        parameters=[
            ToolParameter(
                name="min_altitude",
                type="number",
                description="Minimum altitude in degrees (default 10)",
                required=False,
                default=10.0
            )
        ]
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
            ),
            ToolParameter(
                name="timeout_seconds",
                type="number",
                description="Seconds to wait for confirmation before auto-cancel (default 30)",
                required=False,
                default=30
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
            ),
            ToolParameter(
                name="start_date",
                type="string",
                description="Start date filter in YYYY-MM-DD format",
                required=False
            ),
            ToolParameter(
                name="end_date",
                type="string",
                description="End date filter in YYYY-MM-DD format",
                required=False
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
        description="Start autoguiding with PHD2. Can automatically select a guide star "
                    "or use a previously selected star. Begins tracking corrections.",
        category=ToolCategory.GUIDING,
        parameters=[
            ToolParameter(
                name="auto_select",
                type="boolean",
                description="Automatically select the best guide star (default True). "
                            "Set to False to use a previously selected star.",
                required=False,
                default=True
            ),
            ToolParameter(
                name="settle_pixels",
                type="number",
                description="Maximum settle distance in pixels (default 1.0)",
                required=False,
                default=1.0
            ),
            ToolParameter(
                name="settle_time",
                type="number",
                description="Time to remain settled in seconds (default 10)",
                required=False,
                default=10.0
            )
        ]
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
                description="Dither amount in pixels (default 5). Typical range is 3-10 pixels.",
                required=False,
                default=5.0
            ),
            ToolParameter(
                name="ra_only",
                type="boolean",
                description="Only dither in RA direction (default False). "
                            "Useful for some camera orientations.",
                required=False,
                default=False
            ),
            ToolParameter(
                name="wait_settle",
                type="boolean",
                description="Wait for guiding to settle after dither (default True). "
                            "Set to False for faster operation.",
                required=False,
                default=True
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
            ),
            ToolParameter(
                name="exposure_ms",
                type="number",
                description="Exposure time in milliseconds (default auto). "
                            "Use 1-10ms for bright planets, 10-50ms for dim targets.",
                required=False,
                default=None
            ),
            ToolParameter(
                name="gain",
                type="number",
                description="Camera gain (default auto). Higher gain = more sensitivity "
                            "but more noise. Range typically 0-500.",
                required=False,
                default=None
            ),
            ToolParameter(
                name="binning",
                type="number",
                description="Pixel binning (1, 2, or 4). Higher binning = faster capture "
                            "but lower resolution. Default 1.",
                required=False,
                default=1
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
        parameters=[
            ToolParameter(
                name="algorithm",
                type="string",
                description="Focus algorithm to use: 'vcurve' (default, most accurate), "
                            "'hfd' (faster), or 'contrast' (for extended objects).",
                required=False,
                default="vcurve"
            ),
            ToolParameter(
                name="step_size",
                type="number",
                description="Step size for focus sampling (default auto). "
                            "Smaller steps = more accurate but slower.",
                required=False,
                default=None
            ),
            ToolParameter(
                name="samples",
                type="number",
                description="Number of samples per position (default 3). "
                            "More samples = better accuracy in poor seeing.",
                required=False,
                default=3
            )
        ]
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

    # Step 442-444: Additional INDI device control tools
    Tool(
        name="indi_connect_device",
        description="Connect to an INDI device by name. Use indi_list_devices first "
                    "to see available devices.",
        category=ToolCategory.CAMERA,
        parameters=[
            ToolParameter(
                name="device_name",
                type="string",
                description="Name of the INDI device to connect to",
                required=True
            )
        ]
    ),

    Tool(
        name="indi_get_property",
        description="Get the value of an INDI device property. Properties control "
                    "device settings like exposure, gain, temperature setpoint.",
        category=ToolCategory.CAMERA,
        parameters=[
            ToolParameter(
                name="device_name",
                type="string",
                description="Name of the INDI device",
                required=True
            ),
            ToolParameter(
                name="property_name",
                type="string",
                description="Name of the property to read (e.g., CCD_EXPOSURE, CCD_TEMPERATURE)",
                required=True
            )
        ]
    ),

    Tool(
        name="indi_set_property",
        description="Set an INDI device property value. Use with caution as this "
                    "directly controls hardware.",
        category=ToolCategory.CAMERA,
        parameters=[
            ToolParameter(
                name="device_name",
                type="string",
                description="Name of the INDI device",
                required=True
            ),
            ToolParameter(
                name="property_name",
                type="string",
                description="Name of the property to set",
                required=True
            ),
            ToolParameter(
                name="value",
                type="string",
                description="Value to set (will be converted to appropriate type)",
                required=True
            )
        ]
    ),

    # -------------------------------------------------------------------------
    # ALPACA DEVICE TOOLS (Phase 5.1 - Alpaca Integration)
    # -------------------------------------------------------------------------
    # ASCOM Alpaca device control for network-based cross-platform device layer

    Tool(
        name="alpaca_discover_devices",
        description="Discover all ASCOM Alpaca devices on the local network. "
                    "Uses UDP broadcast to find Alpaca servers and their devices.",
        category=ToolCategory.CAMERA,
        parameters=[]
    ),

    Tool(
        name="alpaca_set_filter",
        description="Change Alpaca filter wheel position. Accepts filter name "
                    "(L, R, G, B, Ha, OIII, SII) or position number (0-6).",
        category=ToolCategory.CAMERA,
        parameters=[
            ToolParameter(
                name="filter_name",
                type="string",
                description="Filter name (L, R, G, B, Ha, OIII, SII) or position number (0-6)",
                required=True
            )
        ]
    ),

    Tool(
        name="alpaca_get_filter",
        description="Get the current Alpaca filter wheel position and filter name.",
        category=ToolCategory.CAMERA,
        parameters=[]
    ),

    Tool(
        name="alpaca_move_focuser",
        description="Move Alpaca focuser to absolute position or by relative steps.",
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
        name="alpaca_get_focuser_status",
        description="Get Alpaca focuser status including position, temperature, "
                    "movement state, and temperature compensation status.",
        category=ToolCategory.FOCUS,
        parameters=[]
    ),

    # Step 447-448: Additional Alpaca device control tools
    Tool(
        name="alpaca_connect_device",
        description="Connect to an Alpaca device by type and number. "
                    "Device types include: telescope, camera, filterwheel, focuser.",
        category=ToolCategory.CAMERA,
        parameters=[
            ToolParameter(
                name="device_type",
                type="string",
                description="Device type (telescope, camera, filterwheel, focuser, dome, etc.)",
                required=True,
                enum=["telescope", "camera", "filterwheel", "focuser", "dome", "rotator", "safetymonitor"]
            ),
            ToolParameter(
                name="device_number",
                type="number",
                description="Device number (0 for first device of type)",
                required=False,
                default=0
            ),
            ToolParameter(
                name="host",
                type="string",
                description="Alpaca server hostname or IP (default: localhost)",
                required=False,
                default="localhost"
            ),
            ToolParameter(
                name="port",
                type="number",
                description="Alpaca server port (default: 11111)",
                required=False,
                default=11111
            )
        ]
    ),

    Tool(
        name="alpaca_get_status",
        description="Get comprehensive status of a connected Alpaca device including "
                    "connection state, device-specific properties, and capabilities.",
        category=ToolCategory.CAMERA,
        parameters=[
            ToolParameter(
                name="device_type",
                type="string",
                description="Device type (telescope, camera, filterwheel, focuser)",
                required=True,
                enum=["telescope", "camera", "filterwheel", "focuser", "dome"]
            ),
            ToolParameter(
                name="device_number",
                type="number",
                description="Device number (0 for first device)",
                required=False,
                default=0
            )
        ]
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
    alpaca_discovery=None,
    alpaca_filter_wheel=None,
    alpaca_focuser=None,
    roof_controller=None,
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
        alpaca_discovery: AlpacaDiscovery instance for network device discovery
        alpaca_filter_wheel: AlpacaFilterWheel adapter instance
        alpaca_focuser: AlpacaFocuser adapter instance
        roof_controller: RoofController instance for enclosure control

    Returns:
        Dictionary of handler functions
    """
    handlers = {}

    # Mount handlers
    async def goto_object(object_name: str) -> str:
        if not catalog_service or not mount_client:
            return "Service not available"

        # Step 333: Safety check before slew
        if safety_monitor:
            status = safety_monitor.evaluate()
            if not status.is_safe:
                reasons = "; ".join(status.reasons) if status.reasons else "unknown"
                return f"Cannot slew - unsafe conditions: {reasons}"

        # Look up coordinates
        obj = catalog_service.lookup(object_name)
        ra_deg = None
        dec_deg = None
        target_name = object_name

        if not obj:
            # Step 332: Try ephemeris for planets
            if ephemeris_service:
                try:
                    from services.ephemeris import CelestialBody
                    body = CelestialBody(object_name.lower())
                    pos = ephemeris_service.get_body_position(body)
                    ra = pos.ra_hms
                    dec = pos.dec_dms
                    # Convert to degrees for altitude check
                    ra_deg = pos.ra_degrees if hasattr(pos, 'ra_degrees') else None
                    dec_deg = pos.dec_degrees if hasattr(pos, 'dec_degrees') else None

                    # Step 334: Altitude limit check for planets
                    if ephemeris_service and ra_deg is not None and dec_deg is not None:
                        try:
                            alt = ephemeris_service.get_altitude_for_coords(ra_deg, dec_deg)
                            if alt is not None and alt < 10.0:
                                return f"Cannot slew to {object_name} - below minimum altitude ({alt:.1f}° < 10°)"
                        except Exception:
                            pass  # Continue if altitude check fails

                    success = mount_client.goto_ra_dec(ra, dec)
                    if success:
                        return f"Slewing to {object_name}"
                    return f"Failed to slew to {object_name}"
                except (ValueError, KeyError):
                    pass
            return f"Object '{object_name}' not found in catalog"

        # Step 331: Catalog resolution
        ra = obj.ra_hms
        dec = obj.dec_dms
        target_name = obj.name or obj.catalog_id

        # Convert catalog coords to degrees for altitude check
        if hasattr(obj, 'ra_degrees'):
            ra_deg = obj.ra_degrees
        if hasattr(obj, 'dec_degrees'):
            dec_deg = obj.dec_degrees

        # Step 334: Altitude limit check for catalog objects
        if ephemeris_service and ra_deg is not None and dec_deg is not None:
            try:
                alt = ephemeris_service.get_altitude_for_coords(ra_deg, dec_deg)
                if alt is not None and alt < 10.0:
                    return f"Cannot slew to {target_name} - below minimum altitude ({alt:.1f}° < 10°)"
                elif alt is not None and alt < 20.0:
                    # Warning for low altitude objects
                    pass  # Continue but could add warning
            except Exception:
                pass  # Continue if altitude check fails

        success = mount_client.goto_ra_dec(ra, dec)
        if success:
            return f"Slewing to {target_name} at RA {ra}, DEC {dec}"
        return f"Failed to slew to {object_name}"

    handlers["goto_object"] = goto_object

    async def goto_coordinates(ra: str, dec: str) -> str:
        """Slew to specific RA/DEC coordinates (Step 335)."""
        if not mount_client:
            return "Mount not available"

        # Step 333: Safety check before slew
        if safety_monitor:
            status = safety_monitor.evaluate()
            if not status.is_safe:
                reasons = "; ".join(status.reasons) if status.reasons else "unknown"
                return f"Cannot slew - unsafe conditions: {reasons}"

        # Step 336: Coordinate validation and parsing
        try:
            # Parse RA string (HH:MM:SS or HH:MM.M)
            ra_parts = ra.replace("h", ":").replace("m", ":").replace("s", "").split(":")
            ra_hours = float(ra_parts[0])
            ra_minutes = float(ra_parts[1]) if len(ra_parts) > 1 else 0
            ra_seconds = float(ra_parts[2]) if len(ra_parts) > 2 else 0

            # Validate RA range (0-24 hours)
            total_ra_hours = ra_hours + ra_minutes / 60 + ra_seconds / 3600
            if total_ra_hours < 0 or total_ra_hours >= 24:
                return f"Invalid RA: {ra}. Must be between 0h and 24h."
            if ra_minutes < 0 or ra_minutes >= 60:
                return f"Invalid RA minutes: {ra_minutes}. Must be between 0 and 59."
            if ra_seconds < 0 or ra_seconds >= 60:
                return f"Invalid RA seconds: {ra_seconds}. Must be between 0 and 59."

            ra_deg = total_ra_hours * 15.0

            # Parse DEC string (sDD:MM:SS)
            dec_clean = dec.replace("°", ":").replace("'", ":").replace('"', "")
            dec_parts = dec_clean.split(":")
            dec_sign = -1 if dec_clean.startswith("-") else 1
            dec_degrees = abs(float(dec_parts[0]))
            dec_minutes = float(dec_parts[1]) if len(dec_parts) > 1 else 0
            dec_seconds = float(dec_parts[2]) if len(dec_parts) > 2 else 0

            # Validate DEC range (-90 to +90 degrees)
            total_dec_deg = dec_sign * (dec_degrees + dec_minutes / 60 + dec_seconds / 3600)
            if total_dec_deg < -90 or total_dec_deg > 90:
                return f"Invalid DEC: {dec}. Must be between -90° and +90°."
            if dec_minutes < 0 or dec_minutes >= 60:
                return f"Invalid DEC minutes: {dec_minutes}. Must be between 0 and 59."
            if dec_seconds < 0 or dec_seconds >= 60:
                return f"Invalid DEC seconds: {dec_seconds}. Must be between 0 and 59."

            dec_deg = total_dec_deg

        except (ValueError, IndexError) as e:
            return f"Invalid coordinate format: {e}. Use HH:MM:SS for RA and sDD:MM:SS for DEC."

        # Step 334: Altitude limit check
        if ephemeris_service:
            try:
                alt = ephemeris_service.get_altitude_for_coords(ra_deg, dec_deg)
                if alt is not None and alt < 10.0:
                    return f"Cannot slew - coordinates below minimum altitude ({alt:.1f}° < 10°)"
            except Exception:
                pass  # Continue if altitude check fails

        success = mount_client.goto_ra_dec(ra, dec)
        if success:
            return f"Slewing to RA {ra}, DEC {dec}"
        return f"Failed to slew to RA {ra}, DEC {dec}"

    handlers["goto_coordinates"] = goto_coordinates

    async def park_telescope(confirmed: bool = False) -> str:
        """Park telescope at home position (Steps 337-338)."""
        if not mount_client:
            return "Mount not available"

        # Check if already parked
        status = mount_client.get_status()
        if status and status.is_parked:
            return "Telescope is already parked"

        # Step 338: Require confirmation if currently tracking/observing
        if status and status.is_tracking and not confirmed:
            return "Telescope is currently tracking. Say 'confirm park' to park and end tracking."

        success = mount_client.park()
        if success:
            return "Parking telescope. Please wait for park to complete."
        return "Failed to park telescope"

    handlers["park_telescope"] = park_telescope

    async def unpark_telescope() -> str:
        """Unpark telescope to resume observations (Step 339)."""
        if not mount_client:
            return "Mount not available"

        # Step 340: Safety check before unpark
        if safety_monitor:
            status = safety_monitor.evaluate()
            if not status.is_safe:
                reasons = "; ".join(status.reasons) if status.reasons else "unknown"
                return f"Cannot unpark - unsafe conditions: {reasons}"

        # Check if already unparked
        mount_status = mount_client.get_status()
        if mount_status and not mount_status.is_parked:
            return "Telescope is already unparked"

        success = mount_client.unpark()
        if success:
            return "Telescope unparked and ready for observation"
        return "Failed to unpark telescope"

    handlers["unpark_telescope"] = unpark_telescope

    async def stop_telescope() -> str:
        """Emergency stop - immediately halt all telescope motion (Step 341)."""
        if not mount_client:
            return "Mount not available"

        # Step 342: Immediate execution - stop is always high priority
        mount_client.stop()
        return "STOP - All telescope motion halted"

    handlers["stop_telescope"] = stop_telescope

    async def start_tracking() -> str:
        """Start sidereal tracking (Step 343)."""
        if not mount_client:
            return "Mount not available"

        # Check if parked
        status = mount_client.get_status()
        if status and status.is_parked:
            return "Cannot start tracking - telescope is parked. Unpark first."

        if status and status.is_tracking:
            return "Tracking is already enabled"

        success = mount_client.set_tracking(True)
        if success:
            return "Sidereal tracking started"
        return "Failed to start tracking"

    handlers["start_tracking"] = start_tracking

    async def stop_tracking() -> str:
        """Stop tracking (Step 344)."""
        if not mount_client:
            return "Mount not available"

        status = mount_client.get_status()
        if status and not status.is_tracking:
            return "Tracking is already disabled"

        success = mount_client.set_tracking(False)
        if success:
            return "Tracking stopped. Telescope will remain stationary."
        return "Failed to stop tracking"

    handlers["stop_tracking"] = stop_tracking

    async def get_mount_status() -> str:
        """Get current telescope position and status (Steps 345-346)."""
        if not mount_client:
            return "Mount not available"

        status = mount_client.get_status()
        if not status:
            return "Could not get mount status"

        # Step 346: Format position in human-readable form
        ra_str = f"{status.ra_hours}h {status.ra_minutes}m {status.ra_seconds:.1f}s"
        dec_sign = "+" if status.dec_degrees >= 0 else ""
        dec_str = f"{dec_sign}{status.dec_degrees}° {abs(status.dec_minutes)}' {abs(status.dec_seconds):.1f}\""

        # Build status message
        parts = [f"Position: RA {ra_str}, Dec {dec_str}"]

        if status.is_parked:
            parts.append("Status: Parked")
        elif status.is_tracking:
            parts.append("Status: Tracking")
        else:
            parts.append("Status: Idle (not tracking)")

        parts.append(f"Pier side: {status.pier_side.value}")

        # Add slewing status if available
        if hasattr(status, 'is_slewing') and status.is_slewing:
            parts.append("Currently slewing")

        # Add altitude if ephemeris available
        if ephemeris_service:
            try:
                ra_deg = (status.ra_hours + status.ra_minutes / 60 + status.ra_seconds / 3600) * 15.0
                dec_deg = status.dec_degrees + status.dec_minutes / 60 + status.dec_seconds / 3600
                if status.dec_degrees < 0:
                    dec_deg = status.dec_degrees - status.dec_minutes / 60 - status.dec_seconds / 3600
                alt = ephemeris_service.get_altitude_for_coords(ra_deg, dec_deg)
                if alt is not None:
                    parts.append(f"Altitude: {alt:.1f}°")
            except Exception:
                pass

        return ". ".join(parts)

    handlers["get_mount_status"] = get_mount_status

    async def sync_position(object_name: str, confirmed: bool = False) -> str:
        """Sync telescope position to a known object (Steps 347-348)."""
        if not mount_client:
            return "Mount not available"

        # Step 348: Require confirmation for sync - it changes pointing model
        if not confirmed:
            return f"Sync will update pointing model to match '{object_name}'. Say 'confirm sync' to proceed."

        # Look up object coordinates
        obj = None
        ra = None
        dec = None

        if catalog_service:
            obj = catalog_service.lookup(object_name)
            if obj:
                ra = obj.ra_hms
                dec = obj.dec_dms

        if not obj and ephemeris_service:
            # Try planets
            try:
                from services.ephemeris import CelestialBody
                body = CelestialBody(object_name.lower())
                pos = ephemeris_service.get_body_position(body)
                ra = pos.ra_hms
                dec = pos.dec_dms
            except (ValueError, KeyError):
                pass

        if not ra or not dec:
            return f"Cannot sync - object '{object_name}' not found"

        # Perform sync
        if hasattr(mount_client, 'sync'):
            success = mount_client.sync(ra, dec)
        elif hasattr(mount_client, 'sync_ra_dec'):
            success = mount_client.sync_ra_dec(ra, dec)
        else:
            return "Mount does not support sync operation"

        if success:
            return f"Position synced to {object_name}. Pointing model updated."
        return f"Failed to sync position to {object_name}"

    handlers["sync_position"] = sync_position

    async def home_telescope() -> str:
        """Send telescope to home position (Step 349)."""
        if not mount_client:
            return "Mount not available"

        # Check if already at home
        status = mount_client.get_status()
        if status and hasattr(status, 'at_home') and status.at_home:
            return "Telescope is already at home position"

        # Stop any current motion first
        mount_client.stop()

        # Send home command
        if hasattr(mount_client, 'find_home'):
            success = mount_client.find_home()
        elif hasattr(mount_client, 'home'):
            success = mount_client.home()
        else:
            # Fall back to park if no home command
            success = mount_client.park()
            if success:
                return "Home command not available - parked telescope instead"
            return "Mount does not support home operation"

        if success:
            return "Finding home position. Please wait for completion."
        return "Failed to start home sequence"

    handlers["home_telescope"] = home_telescope

    async def set_home_offset(ra_offset_arcmin: float = 0.0, dec_offset_arcmin: float = 0.0) -> str:
        """Set home position offset for calibration (Step 350)."""
        if not mount_client:
            return "Mount not available"

        # Validate offset ranges (reasonable limits for home calibration)
        max_offset = 60.0  # Maximum 1 degree offset
        if abs(ra_offset_arcmin) > max_offset:
            return f"RA offset too large: {ra_offset_arcmin}' (max ±{max_offset}')"
        if abs(dec_offset_arcmin) > max_offset:
            return f"Dec offset too large: {dec_offset_arcmin}' (max ±{max_offset}')"

        # Apply offset to mount if supported
        if hasattr(mount_client, 'set_home_offset'):
            success = mount_client.set_home_offset(ra_offset_arcmin, dec_offset_arcmin)
            if success:
                return (f"Home position offset set: RA {ra_offset_arcmin:+.1f}', "
                        f"Dec {dec_offset_arcmin:+.1f}'")
            return "Failed to set home offset"

        # Alternative: store offset in OnStepX extended commands
        if onstepx_extended and hasattr(onstepx_extended, 'set_home_offset'):
            success = onstepx_extended.set_home_offset(ra_offset_arcmin, dec_offset_arcmin)
            if success:
                return (f"Home position offset set via OnStepX: RA {ra_offset_arcmin:+.1f}', "
                        f"Dec {dec_offset_arcmin:+.1f}'")

        # If no native support, provide guidance
        return (f"Mount does not support programmatic home offset. "
                f"Please adjust mechanically or via mount firmware: "
                f"RA {ra_offset_arcmin:+.1f}', Dec {dec_offset_arcmin:+.1f}'")

    handlers["set_home_offset"] = set_home_offset

    # Catalog handlers
    async def lookup_object(object_name: str) -> str:
        """Look up information about a celestial object (Step 352)."""
        if not catalog_service:
            return "Catalog not available"

        # Try catalog lookup first
        obj = catalog_service.lookup(object_name)

        if obj:
            parts = []

            # Object identification
            name = obj.name or obj.catalog_id
            parts.append(f"{name}")

            # Object type if available
            if hasattr(obj, 'object_type') and obj.object_type:
                parts.append(f"Type: {obj.object_type}")

            # Coordinates
            parts.append(f"Position: RA {obj.ra_hms}, Dec {obj.dec_dms}")

            # Magnitude if available
            if hasattr(obj, 'magnitude') and obj.magnitude is not None:
                parts.append(f"Magnitude: {obj.magnitude:.1f}")

            # Size if available
            if hasattr(obj, 'size_arcmin') and obj.size_arcmin:
                parts.append(f"Size: {obj.size_arcmin}' arcmin")

            # Constellation if available
            if hasattr(obj, 'constellation') and obj.constellation:
                parts.append(f"Constellation: {obj.constellation}")

            # Description if available
            if hasattr(obj, 'description') and obj.description:
                parts.append(obj.description)

            # Current altitude if ephemeris available
            if ephemeris_service:
                try:
                    ra_deg = None
                    if hasattr(obj, 'ra_degrees'):
                        ra_deg = obj.ra_degrees
                    elif hasattr(obj, 'ra_hms'):
                        # Parse RA to degrees
                        ra_parts = obj.ra_hms.replace('h', ':').replace('m', ':').replace('s', '').split(':')
                        ra_deg = (float(ra_parts[0]) + float(ra_parts[1])/60 + float(ra_parts[2])/3600) * 15

                    dec_deg = None
                    if hasattr(obj, 'dec_degrees'):
                        dec_deg = obj.dec_degrees

                    if ra_deg is not None and dec_deg is not None:
                        alt = ephemeris_service.get_altitude_for_coords(ra_deg, dec_deg)
                        if alt is not None:
                            if alt < 0:
                                parts.append(f"Currently below horizon ({alt:.1f}°)")
                            elif alt < 10:
                                parts.append(f"Low altitude: {alt:.1f}° - poor for observation")
                            else:
                                parts.append(f"Current altitude: {alt:.1f}°")
                except Exception:
                    pass

            return ". ".join(parts)

        # Try what_is for description
        description = catalog_service.what_is(object_name)
        if description and "not found" not in description.lower():
            return description

        return f"Object '{object_name}' not found in catalog"

    handlers["lookup_object"] = lookup_object

    async def find_objects(
        object_type: str = None,
        constellation: str = None,
        max_magnitude: float = None,
        min_altitude: float = 10.0,
        limit: int = 10
    ) -> str:
        """Find celestial objects matching criteria (Steps 356-357)."""
        if not catalog_service:
            return "Catalog not available"

        parts = []
        results = []

        # Build filter description
        filters = []
        if object_type:
            filters.append(f"type={object_type}")
        if constellation:
            filters.append(f"constellation={constellation}")
        if max_magnitude:
            filters.append(f"mag<={max_magnitude}")
        if min_altitude > 0:
            filters.append(f"altitude>={min_altitude}°")

        filter_str = ", ".join(filters) if filters else "all objects"

        # Step 357: Apply filters using catalog service
        try:
            # Try to use catalog's search method
            if hasattr(catalog_service, 'search'):
                search_results = catalog_service.search(
                    object_type=object_type,
                    constellation=constellation,
                    max_magnitude=max_magnitude
                )
            elif hasattr(catalog_service, 'find_objects'):
                search_results = catalog_service.find_objects(
                    object_type=object_type,
                    constellation=constellation,
                    max_magnitude=max_magnitude
                )
            else:
                # Fallback: iterate through catalog
                search_results = []
                if hasattr(catalog_service, 'get_all_objects'):
                    all_objects = catalog_service.get_all_objects()
                    for obj in all_objects:
                        # Filter by type
                        if object_type:
                            obj_type = getattr(obj, 'object_type', '').lower()
                            if object_type.lower() not in obj_type:
                                continue
                        # Filter by constellation
                        if constellation:
                            obj_const = getattr(obj, 'constellation', '').lower()
                            if constellation.lower() != obj_const:
                                continue
                        # Filter by magnitude
                        if max_magnitude:
                            obj_mag = getattr(obj, 'magnitude', None)
                            if obj_mag is None or obj_mag > max_magnitude:
                                continue
                        search_results.append(obj)

            # Filter by altitude if ephemeris available
            for obj in search_results[:limit * 2]:  # Get extra for altitude filtering
                if len(results) >= limit:
                    break

                # Check altitude
                if ephemeris_service and min_altitude > 0:
                    try:
                        ra_deg = getattr(obj, 'ra_degrees', None)
                        dec_deg = getattr(obj, 'dec_degrees', None)
                        if ra_deg is not None and dec_deg is not None:
                            alt = ephemeris_service.get_altitude_for_coords(ra_deg, dec_deg)
                            if alt is not None and alt < min_altitude:
                                continue
                            obj._current_alt = alt
                    except Exception:
                        pass

                results.append(obj)

            if not results:
                return f"No objects found matching: {filter_str}"

            parts.append(f"Found {len(results)} objects ({filter_str}):")
            for obj in results:
                name = getattr(obj, 'name', None) or getattr(obj, 'catalog_id', 'Unknown')
                obj_type = getattr(obj, 'object_type', '')
                mag = getattr(obj, 'magnitude', None)
                alt = getattr(obj, '_current_alt', None)

                line = f"  {name}"
                if obj_type:
                    line += f" ({obj_type})"
                if mag is not None:
                    line += f" mag {mag:.1f}"
                if alt is not None:
                    line += f" at {alt:.0f}°"
                parts.append(line)

            return "\n".join(parts)

        except Exception as e:
            return f"Error searching catalog: {e}"

    handlers["find_objects"] = find_objects

    async def what_am_i_looking_at() -> str:
        """Identify what object is at current telescope position (Step 354).

        Performs reverse lookup based on current mount coordinates to identify
        nearby catalog objects. Useful for confirming slew targets or
        identifying objects in the field of view.
        """
        if not mount_controller:
            return "Mount not available"

        if not catalog_service:
            return "Catalog not available"

        try:
            # Get current mount position
            ra_hours = mount_controller.get_ra()
            dec_degrees = mount_controller.get_dec()

            if ra_hours is None or dec_degrees is None:
                return "Unable to read mount position"

            # Convert to RA degrees if needed
            ra_degrees = ra_hours * 15.0

            # Search for objects within 1 degree (60 arcmin) of current position
            search_radius = 60.0  # arcminutes
            nearby_objects = []

            # Use cone search if available
            if hasattr(catalog_service, 'objects_in_area'):
                nearby = catalog_service.objects_in_area(
                    ra_hours, dec_degrees, search_radius, limit=5
                )
                for name, dist in nearby:
                    nearby_objects.append((name, dist))
            elif hasattr(catalog_service, 'db') and hasattr(catalog_service.db, 'cone_search'):
                results = catalog_service.db.cone_search(
                    ra_hours, dec_degrees, search_radius, limit=5
                )
                for obj, dist in results:
                    name = obj.name or obj.catalog_id
                    nearby_objects.append((name, dist))

            if not nearby_objects:
                # Format current position for response
                ra_h = int(ra_hours)
                ra_m = int((ra_hours - ra_h) * 60)
                ra_s = ((ra_hours - ra_h) * 60 - ra_m) * 60
                ra_str = f"{ra_h:02d}h {ra_m:02d}m {ra_s:04.1f}s"

                dec_sign = "+" if dec_degrees >= 0 else "-"
                dec_abs = abs(dec_degrees)
                dec_d = int(dec_abs)
                dec_m = int((dec_abs - dec_d) * 60)
                dec_s = ((dec_abs - dec_d) * 60 - dec_m) * 60
                dec_str = f"{dec_sign}{dec_d:02d}° {dec_m:02d}' {dec_s:04.1f}\""

                return f"No cataloged objects within 1 degree of current position: RA {ra_str}, Dec {dec_str}"

            # Build response
            parts = []
            closest = nearby_objects[0]
            parts.append(f"Pointing at {closest[0]} ({closest[1]:.1f}' away)")

            if len(nearby_objects) > 1:
                others = [f"{name} ({dist:.1f}')" for name, dist in nearby_objects[1:4]]
                parts.append(f"Also nearby: {', '.join(others)}")

            return ". ".join(parts)

        except Exception as e:
            return f"Error identifying target: {e}"

    handlers["what_am_i_looking_at"] = what_am_i_looking_at

    async def nearest_objects(
        ra: str = None,
        dec: str = None,
        radius_arcmin: float = 60.0,
        limit: int = 10
    ) -> str:
        """Find objects near specified coordinates or current position (Step 355).

        Args:
            ra: Right Ascension (HH:MM:SS or decimal hours). If None, uses mount position.
            dec: Declination (sDD:MM:SS or decimal degrees). If None, uses mount position.
            radius_arcmin: Search radius in arcminutes (default 60')
            limit: Maximum number of objects to return

        Returns:
            List of objects within the search cone, sorted by distance.
        """
        if not catalog_service:
            return "Catalog not available"

        try:
            # Determine search center
            if ra is None or dec is None:
                # Use current mount position
                if not mount_controller:
                    return "Specify coordinates or connect mount"

                ra_hours = mount_controller.get_ra()
                dec_degrees = mount_controller.get_dec()
                if ra_hours is None or dec_degrees is None:
                    return "Unable to read mount position"
                position_source = "current mount position"
            else:
                # Parse provided coordinates
                # Parse RA
                if ':' in str(ra):
                    parts = str(ra).replace('h', ':').replace('m', ':').replace('s', '').split(':')
                    ra_hours = float(parts[0]) + float(parts[1])/60
                    if len(parts) > 2:
                        ra_hours += float(parts[2])/3600
                else:
                    ra_hours = float(ra)

                # Parse Dec
                if ':' in str(dec) or '°' in str(dec):
                    dec_str = str(dec).replace('°', ':').replace("'", ':').replace('"', '').replace('+', '')
                    negative = dec_str.startswith('-')
                    dec_str = dec_str.lstrip('-')
                    parts = dec_str.split(':')
                    dec_degrees = float(parts[0]) + float(parts[1])/60
                    if len(parts) > 2:
                        dec_degrees += float(parts[2])/3600
                    if negative:
                        dec_degrees = -dec_degrees
                else:
                    dec_degrees = float(dec)

                position_source = f"RA {ra}, Dec {dec}"

            # Perform cone search
            nearby_objects = []
            if hasattr(catalog_service, 'objects_in_area'):
                nearby = catalog_service.objects_in_area(
                    ra_hours, dec_degrees, radius_arcmin, limit=limit
                )
                for name, dist in nearby:
                    nearby_objects.append((name, dist))
            elif hasattr(catalog_service, 'db') and hasattr(catalog_service.db, 'cone_search'):
                results = catalog_service.db.cone_search(
                    ra_hours, dec_degrees, radius_arcmin, limit=limit
                )
                for obj, dist in results:
                    name = obj.name or obj.catalog_id
                    nearby_objects.append((name, dist))

            if not nearby_objects:
                return f"No objects found within {radius_arcmin}' of {position_source}"

            # Build response
            parts = [f"Objects within {radius_arcmin}' of {position_source}:"]
            for name, dist in nearby_objects:
                parts.append(f"  {name}: {dist:.1f}' away")

            return "\n".join(parts)

        except ValueError as e:
            return f"Invalid coordinates: {e}"
        except Exception as e:
            return f"Error searching: {e}"

    handlers["nearest_objects"] = nearest_objects

    # Ephemeris handlers
    async def get_planet_position(planet: str) -> str:
        """Get current position of a planet (Steps 359-360)."""
        if not ephemeris_service:
            return "Ephemeris not available"

        try:
            from services.ephemeris import CelestialBody
            body = CelestialBody(planet.lower())
            pos = ephemeris_service.get_body_position(body)

            # Format position
            ra_str = pos.ra_hms if hasattr(pos, 'ra_hms') else f"{pos.ra_hours:.2f}h"
            dec_str = pos.dec_dms if hasattr(pos, 'dec_dms') else f"{pos.dec_degrees:.1f}°"

            parts = [f"{planet.capitalize()} is at RA {ra_str}, Dec {dec_str}"]
            parts.append(f"Altitude: {pos.altitude_degrees:.1f}°, Azimuth: {pos.azimuth_degrees:.1f}°")

            # Step 360: Add rise/set times if available
            if hasattr(ephemeris_service, 'get_rise_set_times'):
                try:
                    times = ephemeris_service.get_rise_set_times(body)
                    if times:
                        if times.get('rise'):
                            parts.append(f"Rises at {times['rise'].strftime('%H:%M')}")
                        if times.get('set'):
                            parts.append(f"Sets at {times['set'].strftime('%H:%M')}")
                        if times.get('transit'):
                            parts.append(f"Transits at {times['transit'].strftime('%H:%M')}")
                except Exception:
                    pass

            # Add visibility status
            if pos.altitude_degrees < 0:
                parts.append("Currently below the horizon")
            elif pos.altitude_degrees < 10:
                parts.append("Low on the horizon - poor for observation")
            elif pos.altitude_degrees > 60:
                parts.append("Excellent for observation")

            return ". ".join(parts)

        except (ValueError, KeyError):
            return f"Unknown planet: {planet}. Try: Mercury, Venus, Mars, Jupiter, Saturn, Uranus, or Neptune."

    handlers["get_planet_position"] = get_planet_position

    async def get_visible_planets(min_altitude: float = 10.0) -> str:
        """Get list of currently visible planets (Steps 361-362)."""
        if not ephemeris_service:
            return "Ephemeris not available"

        try:
            from services.ephemeris import CelestialBody

            # Get all planet positions
            planets = [
                CelestialBody.MERCURY, CelestialBody.VENUS, CelestialBody.MARS,
                CelestialBody.JUPITER, CelestialBody.SATURN, CelestialBody.URANUS,
                CelestialBody.NEPTUNE
            ]

            visible = []
            below_horizon = []

            for planet in planets:
                try:
                    pos = ephemeris_service.get_body_position(planet)
                    if pos:
                        # Step 362: Filter by altitude
                        if pos.altitude_degrees >= min_altitude:
                            visible.append((planet, pos))
                        elif pos.altitude_degrees > 0:
                            # Above horizon but below filter
                            below_horizon.append((planet, pos))
                except Exception:
                    continue

            if not visible:
                if below_horizon:
                    low_list = ", ".join([f"{p.value.capitalize()} ({pos.altitude_degrees:.0f}°)"
                                          for p, pos in below_horizon])
                    return f"No planets above {min_altitude}° altitude. Low on horizon: {low_list}"
                return f"No planets currently visible above {min_altitude}° altitude"

            # Sort by altitude (highest first)
            visible.sort(key=lambda x: x[1].altitude_degrees, reverse=True)

            parts = ["Visible planets:"]
            for body, pos in visible:
                name = body.value.capitalize()
                alt = pos.altitude_degrees
                az = pos.azimuth_degrees

                # Convert azimuth to compass direction
                directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                              "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
                dir_idx = int((az + 11.25) / 22.5) % 16
                compass = directions[dir_idx]

                # Add visibility assessment
                if alt > 60:
                    quality = "excellent"
                elif alt > 30:
                    quality = "good"
                else:
                    quality = "fair"

                parts.append(f"  {name}: {alt:.0f}° altitude, {compass} ({quality})")

            return "\n".join(parts)

        except Exception as e:
            # Fallback to basic method if available
            if hasattr(ephemeris_service, 'get_visible_planets'):
                visible = ephemeris_service.get_visible_planets()
                if not visible:
                    return "No planets currently visible"
                planet_list = ", ".join([f"{b.value.capitalize()} at {p.altitude_degrees:.1f}°"
                                         for b, p in visible])
                return f"Visible planets: {planet_list}"
            return f"Error getting planet visibility: {e}"

    handlers["get_visible_planets"] = get_visible_planets

    async def get_moon_info() -> str:
        """Get moon position and phase (Steps 363-364)."""
        if not ephemeris_service:
            return "Ephemeris not available"

        try:
            from services.ephemeris import CelestialBody
            pos = ephemeris_service.get_body_position(CelestialBody.MOON)

            parts = []

            # Position
            parts.append(f"Moon is at altitude {pos.altitude_degrees:.1f}°, azimuth {pos.azimuth_degrees:.1f}°")

            # Step 364: Add illumination percentage
            if hasattr(ephemeris_service, 'get_moon_phase'):
                phase_info = ephemeris_service.get_moon_phase()
                if phase_info:
                    illumination = phase_info.get('illumination', 0) * 100
                    phase_name = phase_info.get('phase_name', 'unknown')
                    parts.append(f"Phase: {phase_name}, {illumination:.0f}% illuminated")
            elif hasattr(ephemeris_service, 'get_moon_illumination'):
                illumination = ephemeris_service.get_moon_illumination() * 100
                parts.append(f"Illumination: {illumination:.0f}%")

            # Rise/set times
            if hasattr(ephemeris_service, 'get_rise_set_times'):
                try:
                    times = ephemeris_service.get_rise_set_times(CelestialBody.MOON)
                    if times:
                        if times.get('rise'):
                            parts.append(f"Moonrise: {times['rise'].strftime('%H:%M')}")
                        if times.get('set'):
                            parts.append(f"Moonset: {times['set'].strftime('%H:%M')}")
                except Exception:
                    pass

            # Visibility assessment
            if pos.altitude_degrees < 0:
                parts.append("Moon is below the horizon")
            elif pos.altitude_degrees > 30:
                parts.append("Moon is up - may affect deep sky observation")

            return ". ".join(parts)

        except Exception as e:
            return f"Could not get moon information: {e}"

    handlers["get_moon_info"] = get_moon_info

    async def is_it_dark() -> str:
        """Check if it's astronomical night (Steps 365-366)."""
        if not ephemeris_service:
            return "Ephemeris not available"

        sun_alt = ephemeris_service.get_sun_altitude()
        phase = ephemeris_service.get_twilight_phase()

        # Step 366: Add twilight phase details
        if ephemeris_service.is_astronomical_night():
            parts = ["Yes, it is astronomical night"]
            parts.append(f"Sun is {abs(sun_alt):.1f}° below the horizon")

            # Add time until dawn
            if hasattr(ephemeris_service, 'get_twilight_times'):
                try:
                    times = ephemeris_service.get_twilight_times()
                    if times and times.get('astronomical_dawn'):
                        from datetime import datetime
                        now = datetime.now(times['astronomical_dawn'].tzinfo) if times['astronomical_dawn'].tzinfo else datetime.now()
                        remaining = times['astronomical_dawn'] - now
                        hours = int(remaining.total_seconds() // 3600)
                        minutes = int((remaining.total_seconds() % 3600) // 60)
                        if hours > 0:
                            parts.append(f"Astronomical twilight begins in {hours}h {minutes}m")
                        elif minutes > 0:
                            parts.append(f"Astronomical twilight begins in {minutes} minutes")
                except Exception:
                    pass

            return ". ".join(parts)
        else:
            # Describe current twilight phase
            phase_descriptions = {
                "day": "Daytime - sun is above the horizon",
                "civil_twilight": "Civil twilight - sun is 0-6° below horizon. Sky is still bright.",
                "nautical_twilight": "Nautical twilight - sun is 6-12° below horizon. Stars becoming visible.",
                "astronomical_twilight": "Astronomical twilight - sun is 12-18° below horizon. Most stars visible but sky not fully dark."
            }
            phase_str = phase.value if hasattr(phase, 'value') else str(phase)
            description = phase_descriptions.get(phase_str, f"Current phase: {phase_str}")

            parts = [f"No, it is not yet astronomical night"]
            parts.append(description)
            parts.append(f"Sun altitude: {sun_alt:.1f}°")

            # Add time until astronomical darkness
            if hasattr(ephemeris_service, 'get_twilight_times'):
                try:
                    times = ephemeris_service.get_twilight_times()
                    if times and times.get('astronomical_dusk'):
                        from datetime import datetime
                        now = datetime.now(times['astronomical_dusk'].tzinfo) if times['astronomical_dusk'].tzinfo else datetime.now()
                        remaining = times['astronomical_dusk'] - now
                        if remaining.total_seconds() > 0:
                            hours = int(remaining.total_seconds() // 3600)
                            minutes = int((remaining.total_seconds() % 3600) // 60)
                            if hours > 0:
                                parts.append(f"Astronomical darkness in {hours}h {minutes}m")
                            elif minutes > 0:
                                parts.append(f"Astronomical darkness in {minutes} minutes")
                except Exception:
                    pass

            return ". ".join(parts)

    handlers["is_it_dark"] = is_it_dark

    # Weather handlers
    async def get_weather() -> str:
        """Get current weather conditions (Steps 370-371)."""
        if not weather_client:
            return "Weather station not available"
        data = await weather_client.fetch_data()
        if not data:
            return "Could not fetch weather data"

        parts = []

        # Step 371: Format temperature in both F and C
        temp_c = (data.temperature_f - 32) * 5 / 9
        parts.append(f"Temperature: {data.temperature_f:.1f}°F ({temp_c:.1f}°C)")

        parts.append(f"Humidity: {data.humidity_percent:.0f}%")

        # Wind with direction
        parts.append(f"Wind: {data.wind_speed_mph:.1f} mph from {data.wind_direction_str}")

        # Add dew point if available
        if hasattr(data, 'dew_point_f') and data.dew_point_f is not None:
            dew_c = (data.dew_point_f - 32) * 5 / 9
            parts.append(f"Dew point: {data.dew_point_f:.1f}°F ({dew_c:.1f}°C)")

        # Add pressure if available
        if hasattr(data, 'pressure_hpa') and data.pressure_hpa is not None:
            parts.append(f"Pressure: {data.pressure_hpa:.1f} hPa")

        parts.append(f"Condition: {data.condition.value}")

        return ". ".join(parts)

    handlers["get_weather"] = get_weather

    async def get_wind_speed() -> str:
        """Get wind speed and gust information (Steps 372-373)."""
        if not weather_client:
            return "Weather station not available"
        data = await weather_client.fetch_data()
        if not data:
            return "Could not fetch weather data"

        parts = []
        parts.append(f"Wind speed: {data.wind_speed_mph:.1f} mph from {data.wind_direction_str}")

        # Step 373: Add gust warning
        if hasattr(data, 'wind_gust_mph') and data.wind_gust_mph is not None:
            parts.append(f"Gusts: {data.wind_gust_mph:.1f} mph")
            if data.wind_gust_mph > 25:
                parts.append("WARNING: Gusts exceed safe limit for observation")
            elif data.wind_gust_mph > 20:
                parts.append("Caution: Gusty conditions may affect tracking")

        # Safety assessment
        if data.wind_speed_mph > 30:
            parts.append("UNSAFE: Wind speed exceeds emergency threshold")
        elif data.wind_speed_mph > 25:
            parts.append("WARNING: Approaching wind safety limit")
        elif data.wind_speed_mph > 15:
            parts.append("Moderate wind - may affect long exposures")
        else:
            parts.append("Wind conditions are good for observation")

        return ". ".join(parts)

    handlers["get_wind_speed"] = get_wind_speed

    async def get_cloud_status() -> str:
        """Get cloud cover and sky quality status (Steps 374-375)."""
        parts = []

        # Get cloud sensor data from safety monitor
        if safety_monitor:
            if hasattr(safety_monitor, '_cloud_data') and safety_monitor._cloud_data:
                cloud_data = safety_monitor._cloud_data
                sky_diff = cloud_data.value

                # Interpret sky-ambient temperature differential
                if sky_diff < -25:
                    parts.append("Sky condition: Clear")
                    cloud_pct = 0
                elif sky_diff < -20:
                    parts.append("Sky condition: Mostly clear")
                    cloud_pct = 20
                elif sky_diff < -15:
                    parts.append("Sky condition: Partly cloudy")
                    cloud_pct = 50
                elif sky_diff < -10:
                    parts.append("Sky condition: Mostly cloudy")
                    cloud_pct = 75
                else:
                    parts.append("Sky condition: Overcast")
                    cloud_pct = 100

                parts.append(f"Cloud sensor reading: {sky_diff:.1f}°C (sky-ambient)")
                parts.append(f"Estimated cloud cover: {cloud_pct}%")

                # Sensor timestamp
                from datetime import datetime
                age = (datetime.now() - cloud_data.timestamp).total_seconds()
                if age < 60:
                    parts.append(f"Reading: {age:.0f} seconds ago")
                else:
                    parts.append(f"Reading: {age/60:.0f} minutes ago")
            else:
                parts.append("Cloud sensor data not available")

        # Step 375: Add sky quality (SQM) if available
        # SQM measures sky brightness in magnitudes per square arcsecond
        # Darker = higher number (21+ is excellent, 18- is light polluted)
        if safety_monitor and hasattr(safety_monitor, '_sqm_reading'):
            sqm = safety_monitor._sqm_reading
            if sqm is not None:
                parts.append(f"Sky quality: {sqm:.2f} mag/arcsec²")
                if sqm >= 21.5:
                    parts.append("Excellent dark sky conditions")
                elif sqm >= 20.5:
                    parts.append("Good dark sky conditions")
                elif sqm >= 19.5:
                    parts.append("Rural sky conditions")
                elif sqm >= 18.5:
                    parts.append("Suburban sky conditions")
                else:
                    parts.append("Light polluted sky")
        else:
            # Estimate from cloud cover if no SQM
            if 'Clear' in parts[0] if parts else '':
                parts.append("Sky quality: Good (estimated from cloud sensor)")

        if not parts:
            return "Cloud status not available - no sensors connected"

        return ". ".join(parts)

    handlers["get_cloud_status"] = get_cloud_status

    async def get_seeing_prediction(include_fwhm: bool = True) -> str:
        """Predict astronomical seeing conditions (Steps 376-377).

        Estimates seeing quality based on weather conditions including
        temperature stability, humidity, wind, and atmospheric pressure.
        Optionally includes FWHM estimate for the current optical setup.

        Args:
            include_fwhm: Whether to include FWHM estimate in arcseconds
        """
        if not weather_client:
            return "Weather data not available for seeing prediction"

        try:
            data = await weather_client.fetch_data()
            if not data:
                return "Could not fetch weather data"

            parts = []
            seeing_score = 5  # Start at "average" (1=excellent, 9=terrible)

            # Factor 1: Wind speed (major factor)
            wind_mph = data.wind_speed_mph
            if wind_mph < 5:
                wind_factor = -1  # Calm - good
                parts.append(f"Wind calm ({wind_mph:.0f} mph) - favorable")
            elif wind_mph < 10:
                wind_factor = 0  # Light - neutral
                parts.append(f"Light wind ({wind_mph:.0f} mph) - acceptable")
            elif wind_mph < 15:
                wind_factor = 1  # Moderate - degraded
                parts.append(f"Moderate wind ({wind_mph:.0f} mph) - may affect seeing")
            elif wind_mph < 20:
                wind_factor = 2  # Strong - poor
                parts.append(f"Strong wind ({wind_mph:.0f} mph) - poor conditions")
            else:
                wind_factor = 3  # Very strong - terrible
                parts.append(f"High wind ({wind_mph:.0f} mph) - very poor")
            seeing_score += wind_factor

            # Factor 2: Humidity (affects transparency and stability)
            humidity = data.humidity_percent
            if humidity < 50:
                humidity_factor = -1  # Low humidity - stable
                parts.append(f"Low humidity ({humidity:.0f}%) - stable air")
            elif humidity < 70:
                humidity_factor = 0  # Moderate - neutral
            elif humidity < 85:
                humidity_factor = 1  # High - some degradation
                parts.append(f"High humidity ({humidity:.0f}%) - some scintillation")
            else:
                humidity_factor = 2  # Very high - poor
                parts.append(f"Very high humidity ({humidity:.0f}%) - poor transparency")
            seeing_score += humidity_factor

            # Factor 3: Temperature trend (stability indicator)
            # If we have dewpoint, check temperature margin
            if hasattr(data, 'dew_point_f') and data.dew_point_f is not None:
                temp_margin = data.temperature_f - data.dew_point_f
                if temp_margin < 5:
                    parts.append(f"Near dew point (margin: {temp_margin:.1f}°F) - risk of dew")
                    seeing_score += 1
                elif temp_margin > 15:
                    parts.append("Good temperature margin above dew point")
                    seeing_score -= 1

            # Factor 4: Pressure trend (if available)
            if hasattr(data, 'pressure_hpa') and data.pressure_hpa:
                pressure = data.pressure_hpa
                if pressure > 1020:
                    parts.append("High pressure system - typically stable")
                    seeing_score -= 1
                elif pressure < 1000:
                    parts.append("Low pressure - possible instability")
                    seeing_score += 1

            # Clamp score to valid range
            seeing_score = max(1, min(9, seeing_score))

            # Convert score to descriptive rating
            seeing_ratings = {
                1: "Excellent",
                2: "Very Good",
                3: "Good",
                4: "Above Average",
                5: "Average",
                6: "Below Average",
                7: "Poor",
                8: "Very Poor",
                9: "Terrible"
            }
            rating = seeing_ratings[seeing_score]

            # Step 377: Add FWHM estimate
            fwhm_estimate = None
            if include_fwhm:
                # Typical seeing FWHM estimates based on conditions
                # Base seeing at good site: ~1.5 arcsec
                # Adjusted by seeing score
                base_fwhm = 1.5  # arcsec at excellent conditions
                fwhm_estimate = base_fwhm + (seeing_score - 1) * 0.4

                # Adjust for altitude (Nevada site at ~6000ft)
                # Higher altitude = better seeing baseline
                fwhm_estimate *= 0.9  # 10% improvement for high altitude

                parts.append(f"Estimated FWHM: {fwhm_estimate:.1f}\"")

            # Build final response
            result_parts = [f"Seeing prediction: {rating} (score {seeing_score}/9)"]
            result_parts.extend(parts)

            # Add recommendation
            if seeing_score <= 3:
                result_parts.append("Excellent for high-resolution imaging")
            elif seeing_score <= 5:
                result_parts.append("Suitable for most imaging")
            elif seeing_score <= 7:
                result_parts.append("Consider shorter exposures or binning")
            else:
                result_parts.append("Consider postponing high-resolution work")

            return ". ".join(result_parts)

        except Exception as e:
            return f"Error predicting seeing: {e}"

    handlers["get_seeing_prediction"] = get_seeing_prediction

    async def is_safe_to_observe() -> str:
        """Check if conditions are safe for observation (Steps 379-380)."""
        if not safety_monitor:
            return "Safety monitor not available"

        status = safety_monitor.evaluate()

        if status.is_safe:
            parts = ["Yes, conditions are safe for observation"]

            # Add current readings for context
            if safety_monitor._weather_data:
                wd = safety_monitor._weather_data
                parts.append(f"Wind: {wd.wind_speed_mph:.1f} mph")
                parts.append(f"Humidity: {wd.humidity_percent:.0f}%")

            return ". ".join(parts)
        else:
            # Step 380: Add detailed reasons if unsafe
            parts = ["No, conditions are currently unsafe"]

            # Categorize and explain each reason
            for reason in status.reasons:
                reason_lower = reason.lower()
                if "wind" in reason_lower:
                    parts.append(f"Wind issue: {reason}")
                    if safety_monitor._weather_data:
                        parts.append(f"Current wind: {safety_monitor._weather_data.wind_speed_mph:.1f} mph")
                elif "humidity" in reason_lower or "dew" in reason_lower:
                    parts.append(f"Moisture issue: {reason}")
                    if safety_monitor._weather_data:
                        parts.append(f"Current humidity: {safety_monitor._weather_data.humidity_percent:.0f}%")
                elif "rain" in reason_lower:
                    parts.append(f"Precipitation: {reason}")
                elif "cloud" in reason_lower:
                    parts.append(f"Sky condition: {reason}")
                elif "sun" in reason_lower or "daylight" in reason_lower:
                    parts.append(f"Daylight: {reason}")
                elif "stale" in reason_lower or "timeout" in reason_lower:
                    parts.append(f"Sensor issue: {reason}")
                else:
                    parts.append(reason)

            # Add recommended action based on priority
            if hasattr(status, 'priority') and status.priority:
                if status.priority.value == "emergency":
                    parts.append("ACTION REQUIRED: Immediate park and close recommended")
                elif status.priority.value == "park":
                    parts.append("Recommendation: Park telescope until conditions improve")

            return ". ".join(parts)

    handlers["is_safe_to_observe"] = is_safe_to_observe

    # -------------------------------------------------------------------------
    # POS PANEL v1.0 HANDLERS
    # -------------------------------------------------------------------------

    async def confirm_command(action: str, reason: str = None, timeout_seconds: int = 30) -> str:
        """Request user confirmation for critical command (Steps 386-387)."""
        # In production, this would trigger a confirmation prompt
        # and wait for user response via voice or button
        reason_text = f" ({reason})" if reason else ""

        # Step 387: Add timeout for confirmation
        if timeout_seconds > 0:
            return (f"Please confirm: {action}{reason_text}. "
                    f"Say 'confirm' or 'cancel' within {timeout_seconds} seconds.")
        return f"Please confirm: {action}{reason_text}. Say 'confirm' or 'cancel'."

    handlers["confirm_command"] = confirm_command

    async def abort_slew() -> str:
        """Abort slew and stop all motion."""
        if not mount_client:
            return "Mount not available"
        mount_client.stop()
        return "Slew aborted. Telescope stopped."

    handlers["abort_slew"] = abort_slew

    async def get_observation_log(
        limit: int = 10,
        session: str = "current",
        start_date: str = None,
        end_date: str = None
    ) -> str:
        """Get observation session history (Step 388)."""
        from datetime import datetime, timedelta

        # In a production system, this would query a database.
        # For now, we provide a structured placeholder that shows the interface.

        parts = []

        # Parse date filters if provided
        date_filter_str = ""
        if start_date or end_date:
            if start_date and end_date:
                date_filter_str = f" from {start_date} to {end_date}"
            elif start_date:
                date_filter_str = f" since {start_date}"
            elif end_date:
                date_filter_str = f" until {end_date}"

        if session == "current":
            parts.append(f"Current session log (last {limit} entries{date_filter_str}):")
        elif session == "last":
            parts.append(f"Previous session log (last {limit} entries{date_filter_str}):")
        else:
            parts.append(f"Session '{session}' log (last {limit} entries{date_filter_str}):")

        # Placeholder: In production, query observation database
        # Example format for future implementation:
        # observations = db.query_observations(session=session, limit=limit,
        #                                      start_date=start_date, end_date=end_date)
        # for obs in observations:
        #     parts.append(f"  {obs.timestamp}: {obs.target} - {obs.status}")

        parts.append("  No observations recorded yet.")
        parts.append("  (Observation logging will be enabled when session management is active)")

        return "\n".join(parts)

    handlers["get_observation_log"] = get_observation_log

    async def get_sensor_health() -> str:
        """Get health status of all sensors (Steps 381-382)."""
        if not safety_monitor:
            return "Safety monitor not available"

        from datetime import datetime

        parts = []
        all_ok = True

        # Check weather sensor
        if safety_monitor._weather_data:
            age = (datetime.now() - safety_monitor._weather_data.timestamp).total_seconds()
            # Step 382: Add last reading timestamp
            time_str = safety_monitor._weather_data.timestamp.strftime("%H:%M:%S")
            if age < 120:
                parts.append(f"Weather sensor: OK (last update {time_str}, {age:.0f}s ago)")
            else:
                parts.append(f"Weather sensor: STALE (last update {time_str}, {age:.0f}s ago - exceeds 120s limit)")
                all_ok = False
        else:
            parts.append("Weather sensor: NO DATA - sensor may be offline")
            all_ok = False

        # Check cloud sensor
        if hasattr(safety_monitor, '_cloud_data') and safety_monitor._cloud_data:
            age = (datetime.now() - safety_monitor._cloud_data.timestamp).total_seconds()
            time_str = safety_monitor._cloud_data.timestamp.strftime("%H:%M:%S")
            if age < 180:
                parts.append(f"Cloud sensor: OK (last update {time_str}, {age:.0f}s ago)")
            else:
                parts.append(f"Cloud sensor: STALE (last update {time_str}, {age:.0f}s ago - exceeds 180s limit)")
                all_ok = False
        else:
            parts.append("Cloud sensor: NO DATA - sensor may be offline")
            all_ok = False

        # Check ephemeris
        if hasattr(safety_monitor, '_sun_altitude_time') and safety_monitor._sun_altitude_time:
            age = (datetime.now() - safety_monitor._sun_altitude_time).total_seconds()
            time_str = safety_monitor._sun_altitude_time.strftime("%H:%M:%S")
            if age < 600:
                parts.append(f"Ephemeris: OK (last calculation {time_str}, {age:.0f}s ago)")
            else:
                parts.append(f"Ephemeris: STALE (last calculation {time_str}, {age:.0f}s ago)")
                all_ok = False
        else:
            parts.append("Ephemeris: NOT INITIALIZED")
            all_ok = False

        # Summary
        if all_ok:
            parts.insert(0, "All sensors healthy")
        else:
            parts.insert(0, "WARNING: One or more sensors have issues")

        return ". ".join(parts)

    handlers["get_sensor_health"] = get_sensor_health

    async def get_hysteresis_status() -> dict:
        """Get current safety hysteresis state (Steps 383-384)."""
        if not safety_monitor:
            return {"error": "Safety monitor not available"}

        from datetime import datetime

        result = {
            "wind_triggered": safety_monitor._wind_triggered,
            "humidity_triggered": safety_monitor._humidity_triggered,
            "cloud_triggered": safety_monitor._cloud_triggered,
            "daylight_triggered": safety_monitor._daylight_triggered,
            "thresholds": {
                "wind_limit_mph": safety_monitor.thresholds.wind_limit_mph,
                "wind_clear_mph": safety_monitor.thresholds.wind_limit_mph - safety_monitor.thresholds.wind_hysteresis_mph,
                "humidity_limit": safety_monitor.thresholds.humidity_limit,
                "humidity_clear": safety_monitor.thresholds.humidity_limit - safety_monitor.thresholds.humidity_hysteresis
            },
            # Step 384: Time until threshold reset
            "time_to_reset": {}
        }

        # Calculate time until rain holdoff clears
        if hasattr(safety_monitor, '_last_rain_time') and safety_monitor._last_rain_time:
            elapsed = (datetime.now() - safety_monitor._last_rain_time).total_seconds() / 60.0
            holdoff = safety_monitor.thresholds.rain_holdoff_minutes
            if elapsed < holdoff:
                remaining = holdoff - elapsed
                result["time_to_reset"]["rain_holdoff_minutes"] = round(remaining, 1)

        # Calculate time until safe to resume (if currently unsafe)
        if hasattr(safety_monitor, '_safe_since') and safety_monitor._safe_since:
            safe_duration = (datetime.now() - safety_monitor._safe_since).total_seconds()
            resume_threshold = safety_monitor.thresholds.safe_duration_to_resume
            if safe_duration < resume_threshold:
                remaining = (resume_threshold - safe_duration) / 60.0
                result["time_to_reset"]["safe_resume_minutes"] = round(remaining, 1)

        # If unsafe, show time since unsafe started
        if hasattr(safety_monitor, '_unsafe_since') and safety_monitor._unsafe_since:
            unsafe_duration = (datetime.now() - safety_monitor._unsafe_since).total_seconds()
            result["unsafe_duration_seconds"] = round(unsafe_duration, 0)

        return result

    handlers["get_hysteresis_status"] = get_hysteresis_status

    # -------------------------------------------------------------------------
    # ENCLOSURE HANDLERS (Steps 426-432)
    # -------------------------------------------------------------------------

    async def open_roof() -> str:
        """Open the roll-off roof (Steps 426-427)."""
        if not roof_controller:
            return "Roof controller not available"

        # Step 427: Safety check before open
        if safety_monitor:
            status = safety_monitor.evaluate()
            if not status.is_safe:
                reasons = "; ".join(status.reasons) if status.reasons else "unknown"
                return f"Cannot open roof - unsafe conditions: {reasons}"

        # Check if telescope is parked (safety requirement)
        if mount_client:
            mount_status = mount_client.get_status()
            if mount_status and not mount_status.is_parked:
                return "Cannot open roof - telescope must be parked first"

        # Check current state
        state = roof_controller.get_state()
        if hasattr(state, 'value'):
            state_str = state.value
        else:
            state_str = str(state)

        if state_str == "open":
            return "Roof is already open"
        if state_str == "opening":
            return "Roof is already opening"

        # Check emergency stop
        if hasattr(roof_controller, 'is_emergency_stopped') and roof_controller.is_emergency_stopped:
            return "Cannot open roof - emergency stop is active. Clear emergency stop first."

        success = await roof_controller.open()
        if success:
            return "Opening roof. Please wait for operation to complete."
        return "Failed to open roof - check controller status"

    handlers["open_roof"] = open_roof

    async def close_roof(emergency: bool = False) -> str:
        """Close the roll-off roof (Steps 428-429)."""
        if not roof_controller:
            return "Roof controller not available"

        # Step 429: Force option for emergency - bypass safety checks
        if not emergency:
            # Normal close - check if safe to close
            state = roof_controller.get_state()
            if hasattr(state, 'value'):
                state_str = state.value
            else:
                state_str = str(state)

            if state_str == "closed":
                return "Roof is already closed"
            if state_str == "closing":
                return "Roof is already closing"
        else:
            # Emergency close - log warning
            pass  # Logger would log here in production

        success = await roof_controller.close()
        if success:
            if emergency:
                return "EMERGENCY CLOSE initiated - roof closing immediately"
            return "Closing roof. Please wait for operation to complete."
        return "Failed to close roof - check controller status"

    handlers["close_roof"] = close_roof

    async def get_roof_status() -> str:
        """Get current roof status (Steps 430-431)."""
        if not roof_controller:
            return "Roof controller not available"

        parts = []

        # Get state
        state = roof_controller.get_state()
        if hasattr(state, 'value'):
            state_str = state.value
        else:
            state_str = str(state)

        parts.append(f"Roof state: {state_str}")

        # Step 431: Add position percentage if available
        if hasattr(roof_controller, 'get_position_percent'):
            position = roof_controller.get_position_percent()
            if position is not None:
                parts.append(f"Position: {position:.0f}% open")

        # Check emergency stop
        if hasattr(roof_controller, 'is_emergency_stopped') and roof_controller.is_emergency_stopped:
            parts.append("WARNING: Emergency stop is active")

        # Check if can open
        can_open = True
        open_blockers = []

        if safety_monitor:
            status = safety_monitor.evaluate()
            if not status.is_safe:
                can_open = False
                open_blockers.extend(status.reasons)

        if mount_client:
            mount_status = mount_client.get_status()
            if mount_status and not mount_status.is_parked:
                can_open = False
                open_blockers.append("Telescope not parked")

        if can_open:
            parts.append("Safe to open")
        else:
            parts.append(f"Cannot open: {'; '.join(open_blockers)}")

        return ". ".join(parts)

    handlers["get_roof_status"] = get_roof_status

    async def stop_roof() -> str:
        """Emergency stop - immediately halt roof motion (Step 432)."""
        if not roof_controller:
            return "Roof controller not available"

        # Use emergency stop if available
        if hasattr(roof_controller, 'emergency_stop'):
            await roof_controller.emergency_stop()
            return "EMERGENCY STOP - Roof motion halted immediately"
        else:
            # Fallback to regular stop
            await roof_controller.stop()
            return "Roof motion stopped"

    handlers["stop_roof"] = stop_roof

    # -------------------------------------------------------------------------
    # POWER HANDLERS (Steps 434-437)
    # -------------------------------------------------------------------------

    async def get_power_status() -> str:
        """Get UPS and power status (Steps 434-435)."""
        # Check if we have a UPS monitor available
        if not safety_monitor:
            return "Power monitoring not available"

        parts = []

        # Get power data from safety monitor if available
        if hasattr(safety_monitor, '_power_data') and safety_monitor._power_data:
            pd = safety_monitor._power_data

            # Step 435: Battery percentage and runtime
            if hasattr(pd, 'on_battery'):
                if pd.on_battery:
                    parts.append("Power source: BATTERY (mains power lost)")
                else:
                    parts.append("Power source: Mains AC")

            if hasattr(pd, 'battery_percent') and pd.battery_percent is not None:
                parts.append(f"Battery level: {pd.battery_percent:.0f}%")

                # Warning levels
                if pd.battery_percent < 20:
                    parts.append("WARNING: Battery critically low")
                elif pd.battery_percent < 50:
                    parts.append("Caution: Battery below 50%")

            if hasattr(pd, 'runtime_minutes') and pd.runtime_minutes is not None:
                hours = int(pd.runtime_minutes // 60)
                mins = int(pd.runtime_minutes % 60)
                if hours > 0:
                    parts.append(f"Estimated runtime: {hours}h {mins}m")
                else:
                    parts.append(f"Estimated runtime: {mins} minutes")

            if hasattr(pd, 'load_percent') and pd.load_percent is not None:
                parts.append(f"UPS load: {pd.load_percent:.0f}%")

            if hasattr(pd, 'input_voltage') and pd.input_voltage is not None:
                parts.append(f"Input voltage: {pd.input_voltage:.1f}V")

        else:
            parts.append("No UPS data available - UPS may not be configured")

        if not parts:
            return "Power status unknown"

        return ". ".join(parts)

    handlers["get_power_status"] = get_power_status

    async def get_power_events(event_type: str = None, limit: int = 10) -> str:
        """Get recent power events (Steps 436-437)."""
        if not safety_monitor:
            return "Power monitoring not available"

        # Check for power event history
        if not hasattr(safety_monitor, '_power_events') or not safety_monitor._power_events:
            return "No power events recorded"

        events = safety_monitor._power_events

        # Step 437: Filter by event type if specified
        if event_type:
            event_type_lower = event_type.lower()
            filtered = [e for e in events if event_type_lower in e.get('type', '').lower()]
            events = filtered

        # Limit results
        events = events[-limit:] if len(events) > limit else events

        if not events:
            if event_type:
                return f"No {event_type} events found"
            return "No power events recorded"

        parts = [f"Power events (last {len(events)}):"]
        for event in reversed(events):  # Most recent first
            timestamp = event.get('timestamp', 'unknown')
            if hasattr(timestamp, 'strftime'):
                timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            event_type_str = event.get('type', 'unknown')
            description = event.get('description', '')
            parts.append(f"  [{timestamp}] {event_type_str}: {description}")

        return "\n".join(parts)

    handlers["get_power_events"] = get_power_events

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

    # Step 442: indi_connect_device handler
    async def indi_connect_device(device_name: str) -> str:
        """Connect to an INDI device by name."""
        if not indi_client:
            return "INDI client not available. Ensure INDI server is running."

        # Check if device exists
        if device_name not in indi_client._devices:
            available = list(indi_client._devices.keys())
            if not available:
                return f"Device '{device_name}' not found. No devices available."
            return f"Device '{device_name}' not found. Available: {', '.join(available)}"

        try:
            device = indi_client._devices[device_name]

            # Try to connect the device
            if hasattr(device, 'connect'):
                success = device.connect()
                if success:
                    return f"Connected to INDI device: {device_name}"
                return f"Failed to connect to device: {device_name}"

            # If no connect method, check if it's already connected
            if hasattr(device, 'is_connected') and device.is_connected():
                return f"Device {device_name} is already connected"

            return f"Device {device_name} found but connection method not available"

        except Exception as e:
            return f"Error connecting to {device_name}: {e}"

    handlers["indi_connect_device"] = indi_connect_device

    # Step 443: indi_get_property handler
    async def indi_get_property(device_name: str, property_name: str) -> str:
        """Get an INDI device property value."""
        if not indi_client:
            return "INDI client not available. Ensure INDI server is running."

        if device_name not in indi_client._devices:
            return f"Device '{device_name}' not found"

        try:
            device = indi_client._devices[device_name]

            # Try different methods to get property
            if hasattr(device, 'get_property'):
                prop = device.get_property(property_name)
                if prop is not None:
                    return f"{device_name}.{property_name} = {prop}"

            # Try getting property vector
            if hasattr(device, 'getNumber'):
                value = device.getNumber(property_name)
                if value is not None:
                    return f"{device_name}.{property_name} = {value}"

            if hasattr(device, 'getText'):
                value = device.getText(property_name)
                if value is not None:
                    return f"{device_name}.{property_name} = {value}"

            if hasattr(device, 'getSwitch'):
                value = device.getSwitch(property_name)
                if value is not None:
                    return f"{device_name}.{property_name} = {value}"

            return f"Property '{property_name}' not found on device '{device_name}'"

        except Exception as e:
            return f"Error reading property: {e}"

    handlers["indi_get_property"] = indi_get_property

    # Step 444: indi_set_property handler
    async def indi_set_property(device_name: str, property_name: str, value: str) -> str:
        """Set an INDI device property value."""
        if not indi_client:
            return "INDI client not available. Ensure INDI server is running."

        if device_name not in indi_client._devices:
            return f"Device '{device_name}' not found"

        try:
            device = indi_client._devices[device_name]

            # Try to convert value to appropriate type
            # First try as number
            try:
                num_value = float(value)
                if hasattr(device, 'setNumber'):
                    success = device.setNumber(property_name, num_value)
                    if success:
                        return f"Set {device_name}.{property_name} = {num_value}"
            except ValueError:
                pass

            # Try as text/string
            if hasattr(device, 'setText'):
                success = device.setText(property_name, value)
                if success:
                    return f"Set {device_name}.{property_name} = '{value}'"

            # Try as switch (on/off/true/false)
            if value.lower() in ('on', 'true', '1', 'yes'):
                if hasattr(device, 'setSwitch'):
                    success = device.setSwitch(property_name, True)
                    if success:
                        return f"Set {device_name}.{property_name} = ON"
            elif value.lower() in ('off', 'false', '0', 'no'):
                if hasattr(device, 'setSwitch'):
                    success = device.setSwitch(property_name, False)
                    if success:
                        return f"Set {device_name}.{property_name} = OFF"

            return f"Could not set property '{property_name}' on device '{device_name}'"

        except Exception as e:
            return f"Error setting property: {e}"

    handlers["indi_set_property"] = indi_set_property

    # -------------------------------------------------------------------------
    # ALPACA DEVICE HANDLERS (Phase 5.1)
    # -------------------------------------------------------------------------

    async def alpaca_discover_devices() -> str:
        """Discover Alpaca devices on the network."""
        if not alpaca_discovery:
            # Try to use AlpacaDiscovery directly
            try:
                from services.alpaca.alpaca_client import AlpacaDiscovery
                devices = AlpacaDiscovery.discover(timeout=2.0)
            except ImportError:
                return "Alpaca discovery not available. Ensure alpyca is installed."
            except Exception as e:
                return f"Alpaca discovery failed: {e}"
        else:
            devices = alpaca_discovery.discover(timeout=2.0)

        if not devices:
            return "No Alpaca devices found on network. Check that Alpaca servers are running."

        # Group devices by type
        by_type = {}
        for dev in devices:
            dev_type = dev.device_type
            if dev_type not in by_type:
                by_type[dev_type] = []
            by_type[dev_type].append(dev)

        lines = [f"Found {len(devices)} Alpaca device(s):"]
        for dev_type, devs in sorted(by_type.items()):
            lines.append(f"\n  {dev_type}:")
            for dev in devs:
                lines.append(f"    - {dev.name} at {dev.address}:{dev.port} (#{dev.device_number})")

        return "\n".join(lines)

    handlers["alpaca_discover_devices"] = alpaca_discover_devices

    async def alpaca_set_filter(filter_name: str) -> str:
        """Set Alpaca filter wheel position by name or number."""
        if not alpaca_filter_wheel:
            return "Alpaca filter wheel not available"

        # Check if it's a number (0-indexed for Alpaca)
        try:
            position = int(filter_name)
            success = alpaca_filter_wheel.set_position(position)
            if success:
                return f"Moving Alpaca filter wheel to position {position}"
            return f"Failed to move Alpaca filter wheel to position {position}"
        except ValueError:
            pass

        # It's a filter name - try to set by name
        filter_name_upper = filter_name.upper()
        success = alpaca_filter_wheel.set_filter_by_name(filter_name_upper)
        if success:
            return f"Moving Alpaca filter wheel to {filter_name_upper} filter"
        available = alpaca_filter_wheel.filter_names
        return f"Failed to move to filter '{filter_name}'. Available: {', '.join(available) if available else 'unknown'}"

    handlers["alpaca_set_filter"] = alpaca_set_filter

    async def alpaca_get_filter() -> str:
        """Get current Alpaca filter wheel position."""
        if not alpaca_filter_wheel:
            return "Alpaca filter wheel not available"

        position = alpaca_filter_wheel.position
        if position < 0:
            return "Could not read Alpaca filter position"

        filter_name = alpaca_filter_wheel.current_filter

        if filter_name and filter_name != "Unknown":
            return f"Current Alpaca filter: {filter_name} (position {position})"
        return f"Current Alpaca filter position: {position}"

    handlers["alpaca_get_filter"] = alpaca_get_filter

    async def alpaca_move_focuser(position: int, relative: bool = False) -> str:
        """Move Alpaca focuser to position."""
        if not alpaca_focuser:
            return "Alpaca focuser not available"

        if relative:
            success = alpaca_focuser.move_relative(position)
            direction = "out" if position > 0 else "in"
            if success:
                return f"Moving Alpaca focuser {abs(position)} steps {direction}"
            return "Failed to move Alpaca focuser"
        else:
            success = alpaca_focuser.move_absolute(position)
            if success:
                return f"Moving Alpaca focuser to position {position}"
            return f"Failed to move Alpaca focuser to position {position}"

    handlers["alpaca_move_focuser"] = alpaca_move_focuser

    async def alpaca_get_focuser_status() -> str:
        """Get Alpaca focuser status."""
        if not alpaca_focuser:
            return "Alpaca focuser not available"

        status = alpaca_focuser.get_status()

        status_parts = []
        if status.get("position") is not None:
            status_parts.append(f"Position: {status['position']} / {status.get('max_position', '?')} steps")
        if status.get("is_moving") is not None:
            status_parts.append(f"Moving: {'Yes' if status['is_moving'] else 'No'}")
        if status.get("temperature") is not None:
            status_parts.append(f"Temperature: {status['temperature']:.1f}°C")
        if status.get("temp_comp") is not None:
            status_parts.append(f"Temp compensation: {'Enabled' if status['temp_comp'] else 'Disabled'}")

        if not status_parts:
            return "Could not read Alpaca focuser status"

        return "Alpaca Focuser status:\n  " + "\n  ".join(status_parts)

    handlers["alpaca_get_focuser_status"] = alpaca_get_focuser_status

    # Step 447: alpaca_connect_device handler
    async def alpaca_connect_device(
        device_type: str,
        device_number: int = 0,
        host: str = "localhost",
        port: int = 11111
    ) -> str:
        """Connect to an Alpaca device."""
        try:
            # Try to import alpyca for direct connection
            try:
                import alpyca
            except ImportError:
                return "Alpaca library (alpyca) not installed. Run: pip install alpyca"

            # Normalize device type
            device_type_lower = device_type.lower()

            # Map device types to alpyca classes
            device_classes = {
                "telescope": "Telescope",
                "camera": "Camera",
                "filterwheel": "FilterWheel",
                "focuser": "Focuser",
                "dome": "Dome",
                "rotator": "Rotator",
                "safetymonitor": "SafetyMonitor",
            }

            if device_type_lower not in device_classes:
                return f"Unknown device type: {device_type}. Supported: {', '.join(device_classes.keys())}"

            class_name = device_classes[device_type_lower]

            # Create device instance
            device_class = getattr(alpyca, class_name, None)
            if device_class is None:
                return f"Device class {class_name} not available in alpyca"

            device = device_class(f"{host}:{port}", device_number)

            # Try to connect
            device.Connected = True

            if device.Connected:
                name = getattr(device, 'Name', 'Unknown')
                return f"Connected to Alpaca {device_type}: {name} at {host}:{port} (device #{device_number})"
            else:
                return f"Failed to connect to Alpaca {device_type} at {host}:{port}"

        except Exception as e:
            return f"Error connecting to Alpaca device: {e}"

    handlers["alpaca_connect_device"] = alpaca_connect_device

    # Step 448: alpaca_get_status handler
    async def alpaca_get_status(device_type: str, device_number: int = 0) -> str:
        """Get comprehensive Alpaca device status."""
        try:
            try:
                import alpyca
            except ImportError:
                return "Alpaca library (alpyca) not installed"

            device_type_lower = device_type.lower()

            # Map device types to alpyca classes
            device_classes = {
                "telescope": "Telescope",
                "camera": "Camera",
                "filterwheel": "FilterWheel",
                "focuser": "Focuser",
                "dome": "Dome",
            }

            if device_type_lower not in device_classes:
                return f"Unknown device type: {device_type}"

            class_name = device_classes[device_type_lower]
            device_class = getattr(alpyca, class_name, None)
            if device_class is None:
                return f"Device class {class_name} not available"

            # Create device instance (using default localhost:11111)
            device = device_class("localhost:11111", device_number)

            status_lines = [f"Alpaca {device_type} #{device_number} Status:"]

            # Common properties
            try:
                status_lines.append(f"  Connected: {device.Connected}")
            except Exception:
                status_lines.append("  Connected: Unknown")

            try:
                status_lines.append(f"  Name: {device.Name}")
            except Exception:
                pass

            try:
                status_lines.append(f"  Description: {device.Description}")
            except Exception:
                pass

            # Device-specific properties
            if device_type_lower == "telescope":
                try:
                    status_lines.append(f"  Tracking: {device.Tracking}")
                    status_lines.append(f"  RA: {device.RightAscension:.4f}h")
                    status_lines.append(f"  Dec: {device.Declination:.4f}°")
                    status_lines.append(f"  Parked: {device.AtPark}")
                    status_lines.append(f"  Slewing: {device.Slewing}")
                except Exception:
                    pass

            elif device_type_lower == "camera":
                try:
                    status_lines.append(f"  Camera State: {device.CameraState}")
                    status_lines.append(f"  CCD Temp: {device.CCDTemperature:.1f}°C")
                    status_lines.append(f"  Cooler On: {device.CoolerOn}")
                except Exception:
                    pass

            elif device_type_lower == "focuser":
                try:
                    status_lines.append(f"  Position: {device.Position}")
                    status_lines.append(f"  Moving: {device.IsMoving}")
                    status_lines.append(f"  Temp Comp: {device.TempComp}")
                except Exception:
                    pass

            elif device_type_lower == "filterwheel":
                try:
                    status_lines.append(f"  Position: {device.Position}")
                    status_lines.append(f"  Filter Names: {device.Names}")
                except Exception:
                    pass

            return "\n".join(status_lines)

        except Exception as e:
            return f"Error getting Alpaca status: {e}"

    handlers["alpaca_get_status"] = alpaca_get_status

    # -------------------------------------------------------------------------
    # GUIDING HANDLERS (Steps 395-397)
    # -------------------------------------------------------------------------

    async def stop_guiding() -> str:
        """Stop autoguiding (Step 395)."""
        if not guiding_client:
            return "Guiding system not available"

        try:
            if hasattr(guiding_client, 'stop_guiding'):
                success = guiding_client.stop_guiding()
            elif hasattr(guiding_client, 'stop'):
                success = guiding_client.stop()
            else:
                return "Guiding client does not support stop operation"

            if success:
                return "Autoguiding stopped"
            return "Failed to stop guiding"
        except Exception as e:
            return f"Error stopping guiding: {e}"

    handlers["stop_guiding"] = stop_guiding

    async def get_guiding_status() -> str:
        """Get autoguiding status with RMS (Steps 396-397)."""
        if not guiding_client:
            return "Guiding system not available"

        try:
            parts = []

            # Get guiding state
            if hasattr(guiding_client, 'is_guiding'):
                is_guiding = guiding_client.is_guiding()
                parts.append(f"Guiding: {'Active' if is_guiding else 'Inactive'}")
            elif hasattr(guiding_client, 'get_status'):
                status = guiding_client.get_status()
                if status:
                    is_guiding = status.get('guiding', False)
                    parts.append(f"Guiding: {'Active' if is_guiding else 'Inactive'}")

            # Step 397: Get RMS in arcseconds
            if hasattr(guiding_client, 'get_rms'):
                rms = guiding_client.get_rms()
                if rms:
                    ra_rms = rms.get('ra_arcsec', 0)
                    dec_rms = rms.get('dec_arcsec', 0)
                    total_rms = rms.get('total_arcsec', 0)
                    parts.append(f"RMS: {total_rms:.2f}\" total (RA: {ra_rms:.2f}\", Dec: {dec_rms:.2f}\")")

                    # Quality assessment
                    if total_rms < 0.5:
                        parts.append("Guiding quality: Excellent")
                    elif total_rms < 1.0:
                        parts.append("Guiding quality: Good")
                    elif total_rms < 2.0:
                        parts.append("Guiding quality: Fair")
                    else:
                        parts.append("Guiding quality: Poor - consider recalibration")

            # Get guide star info
            if hasattr(guiding_client, 'get_guide_star'):
                star = guiding_client.get_guide_star()
                if star:
                    parts.append(f"Guide star: SNR {star.get('snr', 0):.1f}")

            # Get calibration status
            if hasattr(guiding_client, 'is_calibrated'):
                is_cal = guiding_client.is_calibrated()
                parts.append(f"Calibrated: {'Yes' if is_cal else 'No'}")

            if not parts:
                return "Could not retrieve guiding status"

            return "\n".join(parts)

        except Exception as e:
            return f"Error getting guiding status: {e}"

    handlers["get_guiding_status"] = get_guiding_status

    # -------------------------------------------------------------------------
    # CAMERA HANDLERS (Steps 403-405)
    # -------------------------------------------------------------------------

    async def stop_capture() -> str:
        """Stop current camera capture (Step 403)."""
        if not camera_client:
            return "Camera not available"

        try:
            if hasattr(camera_client, 'abort_exposure'):
                success = camera_client.abort_exposure()
            elif hasattr(camera_client, 'stop_capture'):
                success = camera_client.stop_capture()
            elif hasattr(camera_client, 'stop'):
                success = camera_client.stop()
            else:
                return "Camera does not support abort operation"

            if success:
                return "Capture aborted"
            return "Failed to stop capture (may not have been active)"
        except Exception as e:
            return f"Error stopping capture: {e}"

    handlers["stop_capture"] = stop_capture

    async def get_camera_status() -> str:
        """Get camera status with temperature (Steps 404-405)."""
        if not camera_client:
            return "Camera not available"

        try:
            parts = []

            # Get camera state
            if hasattr(camera_client, 'get_status'):
                status = camera_client.get_status()
                if status:
                    state = status.get('state', 'unknown')
                    parts.append(f"State: {state}")

                    if status.get('exposure_progress'):
                        progress = status['exposure_progress'] * 100
                        parts.append(f"Exposure progress: {progress:.0f}%")

            # Check if capturing
            if hasattr(camera_client, 'is_capturing'):
                is_cap = camera_client.is_capturing()
                parts.append(f"Capturing: {'Yes' if is_cap else 'No'}")

            # Get current settings
            if hasattr(camera_client, 'get_gain'):
                gain = camera_client.get_gain()
                parts.append(f"Gain: {gain}")

            if hasattr(camera_client, 'get_exposure'):
                exp = camera_client.get_exposure()
                if exp < 1:
                    parts.append(f"Exposure: {exp*1000:.1f}ms")
                else:
                    parts.append(f"Exposure: {exp:.2f}s")

            if hasattr(camera_client, 'get_binning'):
                binning = camera_client.get_binning()
                parts.append(f"Binning: {binning}x{binning}")

            # Step 405: Temperature and cooling status
            if hasattr(camera_client, 'get_temperature'):
                temp = camera_client.get_temperature()
                parts.append(f"Sensor temperature: {temp:.1f}°C")

            if hasattr(camera_client, 'get_cooler_status'):
                cooler = camera_client.get_cooler_status()
                if cooler:
                    power = cooler.get('power_percent', 0)
                    target = cooler.get('target_temp')
                    is_on = cooler.get('enabled', False)
                    parts.append(f"Cooler: {'On' if is_on else 'Off'} ({power:.0f}% power)")
                    if target is not None:
                        parts.append(f"Target temp: {target:.0f}°C")
            elif hasattr(camera_client, 'is_cooler_on'):
                is_on = camera_client.is_cooler_on()
                parts.append(f"Cooler: {'On' if is_on else 'Off'}")

            if not parts:
                return "Could not retrieve camera status"

            return "Camera status:\n  " + "\n  ".join(parts)

        except Exception as e:
            return f"Error getting camera status: {e}"

    handlers["get_camera_status"] = get_camera_status

    async def set_camera_gain(gain: int) -> str:
        """Set camera gain with validation (Steps 406-407)."""
        if not camera_client:
            return "Camera not available"

        try:
            # Step 407: Validate gain range
            min_gain = 0
            max_gain = 500  # Default max

            if hasattr(camera_client, 'get_gain_range'):
                gain_range = camera_client.get_gain_range()
                if gain_range:
                    min_gain = gain_range.get('min', 0)
                    max_gain = gain_range.get('max', 500)
            elif hasattr(camera_client, 'gain_min') and hasattr(camera_client, 'gain_max'):
                min_gain = camera_client.gain_min
                max_gain = camera_client.gain_max

            if gain < min_gain or gain > max_gain:
                return f"Gain {gain} out of range. Valid range: {min_gain} - {max_gain}"

            # Set the gain
            if hasattr(camera_client, 'set_gain'):
                success = camera_client.set_gain(gain)
            elif hasattr(camera_client, 'gain'):
                camera_client.gain = gain
                success = True
            else:
                return "Camera does not support gain control"

            if success:
                # Provide context for typical use cases
                if gain < 100:
                    context = "(low - good for bright targets)"
                elif gain < 250:
                    context = "(medium - balanced)"
                else:
                    context = "(high - sensitive but noisy)"
                return f"Camera gain set to {gain} {context}"
            return f"Failed to set gain to {gain}"

        except Exception as e:
            return f"Error setting gain: {e}"

    handlers["set_camera_gain"] = set_camera_gain

    async def set_camera_exposure(exposure_ms: float) -> str:
        """Set camera exposure time with validation (Steps 408-409)."""
        if not camera_client:
            return "Camera not available"

        try:
            # Step 409: Validate exposure range
            min_exp_ms = 0.001  # 1 microsecond
            max_exp_ms = 3600000  # 1 hour

            if hasattr(camera_client, 'get_exposure_range'):
                exp_range = camera_client.get_exposure_range()
                if exp_range:
                    min_exp_ms = exp_range.get('min_ms', 0.001)
                    max_exp_ms = exp_range.get('max_ms', 3600000)
            elif hasattr(camera_client, 'exposure_min') and hasattr(camera_client, 'exposure_max'):
                min_exp_ms = camera_client.exposure_min * 1000
                max_exp_ms = camera_client.exposure_max * 1000

            if exposure_ms < min_exp_ms or exposure_ms > max_exp_ms:
                if max_exp_ms >= 60000:
                    max_str = f"{max_exp_ms/60000:.0f} minutes"
                elif max_exp_ms >= 1000:
                    max_str = f"{max_exp_ms/1000:.0f} seconds"
                else:
                    max_str = f"{max_exp_ms:.1f} ms"
                return f"Exposure {exposure_ms}ms out of range. Valid: {min_exp_ms:.3f}ms - {max_str}"

            # Convert to seconds for API if needed
            exposure_sec = exposure_ms / 1000.0

            # Set the exposure
            if hasattr(camera_client, 'set_exposure'):
                success = camera_client.set_exposure(exposure_sec)
            elif hasattr(camera_client, 'set_exposure_ms'):
                success = camera_client.set_exposure_ms(exposure_ms)
            elif hasattr(camera_client, 'exposure'):
                camera_client.exposure = exposure_sec
                success = True
            else:
                return "Camera does not support exposure control"

            if success:
                # Format for display
                if exposure_ms < 1:
                    exp_str = f"{exposure_ms*1000:.0f}µs"
                elif exposure_ms < 1000:
                    exp_str = f"{exposure_ms:.1f}ms"
                else:
                    exp_str = f"{exposure_ms/1000:.2f}s"

                # Provide context
                if exposure_ms < 10:
                    context = "(fast - planetary imaging)"
                elif exposure_ms < 1000:
                    context = "(short - lucky imaging)"
                elif exposure_ms < 60000:
                    context = "(medium - deep sky)"
                else:
                    context = "(long - faint targets)"
                return f"Camera exposure set to {exp_str} {context}"
            return f"Failed to set exposure to {exposure_ms}ms"

        except Exception as e:
            return f"Error setting exposure: {e}"

    handlers["set_camera_exposure"] = set_camera_exposure

    # -------------------------------------------------------------------------
    # FOCUS HANDLERS (Step 413)
    # -------------------------------------------------------------------------

    async def get_focus_status() -> str:
        """Get focuser status (Step 413)."""
        if not focuser_service:
            return "Focuser not available"

        try:
            parts = []

            # Get focuser position
            if hasattr(focuser_service, 'get_position'):
                pos = focuser_service.get_position()
                parts.append(f"Position: {pos} steps")

            if hasattr(focuser_service, 'get_max_position'):
                max_pos = focuser_service.get_max_position()
                parts.append(f"Range: 0 - {max_pos} steps")

            # Get movement status
            if hasattr(focuser_service, 'is_moving'):
                is_moving = focuser_service.is_moving()
                parts.append(f"Moving: {'Yes' if is_moving else 'No'}")

            # Get temperature compensation
            if hasattr(focuser_service, 'get_temp_compensation'):
                temp_comp = focuser_service.get_temp_compensation()
                parts.append(f"Temp compensation: {'Enabled' if temp_comp else 'Disabled'}")

            # Get temperature
            if hasattr(focuser_service, 'get_temperature'):
                temp = focuser_service.get_temperature()
                if temp is not None:
                    parts.append(f"Temperature: {temp:.1f}°C")

            # Get last HFD/FWHM if available
            if hasattr(focuser_service, 'get_last_hfd'):
                hfd = focuser_service.get_last_hfd()
                if hfd is not None:
                    parts.append(f"Last HFD: {hfd:.2f} pixels")

            if hasattr(focuser_service, 'get_last_fwhm'):
                fwhm = focuser_service.get_last_fwhm()
                if fwhm is not None:
                    parts.append(f"Last FWHM: {fwhm:.2f} arcsec")

            # Get autofocus status
            if hasattr(focuser_service, 'is_autofocus_running'):
                is_af = focuser_service.is_autofocus_running()
                if is_af:
                    parts.append("Autofocus: Running")

            if not parts:
                return "Could not retrieve focuser status"

            return "Focuser status:\n  " + "\n  ".join(parts)

        except Exception as e:
            return f"Error getting focus status: {e}"

    handlers["get_focus_status"] = get_focus_status

    async def move_focus(steps: int = None, direction: str = None, position: int = None) -> str:
        """Move focuser by steps or to absolute position (Steps 415-416)."""
        if not focuser_service:
            return "Focuser not available"

        try:
            # Step 416: Handle direction and step parameters
            if position is not None:
                # Absolute move
                if hasattr(focuser_service, 'get_max_position'):
                    max_pos = focuser_service.get_max_position()
                    if position < 0 or position > max_pos:
                        return f"Position {position} out of range. Valid: 0 - {max_pos}"

                if hasattr(focuser_service, 'move_to'):
                    success = focuser_service.move_to(position)
                elif hasattr(focuser_service, 'move_absolute'):
                    success = focuser_service.move_absolute(position)
                else:
                    return "Focuser does not support absolute positioning"

                if success:
                    return f"Moving focuser to position {position}"
                return f"Failed to move focuser to position {position}"

            elif steps is not None:
                # Relative move
                actual_steps = steps
                if direction:
                    dir_lower = direction.lower()
                    if dir_lower in ['in', 'inward', '-']:
                        actual_steps = -abs(steps)
                    elif dir_lower in ['out', 'outward', '+']:
                        actual_steps = abs(steps)

                if hasattr(focuser_service, 'move_relative'):
                    success = focuser_service.move_relative(actual_steps)
                elif hasattr(focuser_service, 'move'):
                    success = focuser_service.move(actual_steps)
                else:
                    return "Focuser does not support relative movement"

                dir_str = "inward" if actual_steps < 0 else "outward"
                if success:
                    return f"Moving focuser {abs(actual_steps)} steps {dir_str}"
                return f"Failed to move focuser {abs(actual_steps)} steps"

            else:
                return "Specify either 'steps' (with optional 'direction') or 'position'"

        except Exception as e:
            return f"Error moving focuser: {e}"

    handlers["move_focus"] = move_focus

    async def enable_temp_compensation(enabled: bool = True) -> str:
        """Enable or disable temperature compensation (Step 417)."""
        if not focuser_service:
            return "Focuser not available"

        try:
            if hasattr(focuser_service, 'set_temp_compensation'):
                success = focuser_service.set_temp_compensation(enabled)
            elif hasattr(focuser_service, 'temp_compensation'):
                focuser_service.temp_compensation = enabled
                success = True
            elif hasattr(focuser_service, 'enable_temp_comp'):
                success = focuser_service.enable_temp_comp(enabled)
            else:
                return "Focuser does not support temperature compensation"

            if success:
                status = "enabled" if enabled else "disabled"
                if enabled:
                    return f"Temperature compensation {status}. Focus will auto-adjust with temperature changes."
                return f"Temperature compensation {status}. Focus position is now fixed."
            return f"Failed to {'enable' if enabled else 'disable'} temperature compensation"

        except Exception as e:
            return f"Error setting temperature compensation: {e}"

    handlers["enable_temp_compensation"] = enable_temp_compensation

    # -------------------------------------------------------------------------
    # ASTROMETRY HANDLERS (Steps 420-422)
    # -------------------------------------------------------------------------

    async def plate_solve(timeout_sec: float = 30.0, use_hint: bool = True) -> str:
        """Plate solve current image with timeout (Step 420)."""
        if not astrometry_service:
            return "Astrometry service not available"

        try:
            # Get current camera image or last captured
            image_path = None
            if camera_client and hasattr(camera_client, 'get_last_image_path'):
                image_path = camera_client.get_last_image_path()

            if not image_path:
                return "No image available for plate solving. Capture an image first."

            # Get position hint from mount if available
            hint = None
            if use_hint and mount_client:
                status = mount_client.get_status()
                if status and hasattr(status, 'ra_degrees') and hasattr(status, 'dec_degrees'):
                    from services.astrometry.plate_solver import PlateSolveHint
                    hint = PlateSolveHint(
                        ra_deg=status.ra_degrees,
                        dec_deg=status.dec_degrees,
                        radius_deg=5.0
                    )

            # Solve with timeout
            result = await astrometry_service.solve(image_path, hint=hint, timeout=timeout_sec)

            if result.status.value == "success":
                parts = [
                    f"Plate solve successful in {result.solve_time_sec:.1f}s",
                    f"Position: {result.ra_hms} {result.dec_dms}"
                ]
                if result.pixel_scale:
                    parts.append(f"Scale: {result.pixel_scale:.2f} arcsec/pixel")
                if result.rotation_deg is not None:
                    parts.append(f"Rotation: {result.rotation_deg:.1f}°")
                return "\n".join(parts)
            elif result.status.value == "timeout":
                return f"Plate solve timed out after {timeout_sec}s. Try increasing timeout or check image quality."
            else:
                return f"Plate solve failed: {result.error_message or 'Unknown error'}"

        except Exception as e:
            return f"Error during plate solve: {e}"

    handlers["plate_solve"] = plate_solve

    async def get_pointing_error() -> str:
        """Get pointing error from last solve in arcseconds (Steps 421-422)."""
        if not astrometry_service:
            return "Astrometry service not available"
        if not mount_client:
            return "Mount not available"

        try:
            # Get mount's current position
            status = mount_client.get_status()
            if not status or not hasattr(status, 'ra_degrees'):
                return "Cannot get mount position"

            expected_ra = status.ra_degrees
            expected_dec = status.dec_degrees

            # Get last solve result
            if hasattr(astrometry_service, '_solve_history') and astrometry_service._solve_history:
                last_solve = astrometry_service._solve_history[-1]

                if last_solve.status.value != "success":
                    return "Last plate solve was not successful. Run plate_solve first."

                # Step 422: Calculate error in arcseconds
                ra_error, dec_error, total_error = astrometry_service.calculate_pointing_error(
                    expected_ra, expected_dec, last_solve
                )

                parts = [
                    f"Pointing error: {total_error:.1f}\" total",
                    f"  RA error: {ra_error:+.1f}\" {'East' if ra_error > 0 else 'West'}",
                    f"  Dec error: {dec_error:+.1f}\" {'North' if dec_error > 0 else 'South'}"
                ]

                # Quality assessment
                if total_error < 10:
                    parts.append("Pointing accuracy: Excellent")
                elif total_error < 30:
                    parts.append("Pointing accuracy: Good")
                elif total_error < 60:
                    parts.append("Pointing accuracy: Fair - consider sync")
                else:
                    parts.append("Pointing accuracy: Poor - sync recommended")

                return "\n".join(parts)
            else:
                return "No plate solve results available. Run plate_solve first."

        except Exception as e:
            return f"Error calculating pointing error: {e}"

    handlers["get_pointing_error"] = get_pointing_error

    # Guiding handlers (Step 393)
    async def start_guiding(
        settle_time: float = 10.0,
        settle_tolerance: float = 1.5
    ) -> str:
        """Start autoguiding with PHD2 (Step 393).

        Initiates guide star selection and begins autoguiding.

        Args:
            settle_time: Time to wait for guiding to settle (seconds)
            settle_tolerance: RMS threshold to consider settled (arcsec)
        """
        # Check if guider service is available
        guider = None
        if 'guider_client' in dir() and guider_client:
            guider = guider_client
        elif 'phd2_client' in dir():
            guider = phd2_client if phd2_client else None

        if not guider:
            return "Guiding service (PHD2) not available"

        # Safety check - ensure mount is tracking
        if mount_client:
            try:
                status = mount_client.get_status()
                if status and hasattr(status, 'is_tracking') and not status.is_tracking:
                    return "Cannot start guiding - mount is not tracking"
                if status and hasattr(status, 'is_parked') and status.is_parked:
                    return "Cannot start guiding - mount is parked"
            except Exception:
                pass

        try:
            # Check current guiding state
            if hasattr(guider, 'is_guiding') and guider.is_guiding():
                return "Guiding is already active"

            # Start guide star selection and guiding
            if hasattr(guider, 'start_guiding'):
                result = await guider.start_guiding(
                    settle_time=settle_time,
                    settle_tolerance=settle_tolerance
                )
                if result:
                    return f"Guiding started. Settling with {settle_tolerance}\" tolerance."
                return "Failed to start guiding - check guide camera"

            elif hasattr(guider, 'guide'):
                # Alternative method name
                success = guider.guide()
                if success:
                    return "Guiding started"
                return "Failed to start guiding"

            return "Guiding start method not available"

        except Exception as e:
            return f"Error starting guiding: {e}"

    handlers["start_guiding"] = start_guiding

    async def stop_guiding() -> str:
        """Stop autoguiding (Step 394)."""
        guider = None
        if 'guider_client' in dir() and guider_client:
            guider = guider_client
        elif 'phd2_client' in dir():
            guider = phd2_client if phd2_client else None

        if not guider:
            return "Guiding service not available"

        try:
            if hasattr(guider, 'stop_guiding'):
                guider.stop_guiding()
                return "Guiding stopped"
            elif hasattr(guider, 'stop'):
                guider.stop()
                return "Guiding stopped"
            return "Stop method not available"
        except Exception as e:
            return f"Error stopping guiding: {e}"

    handlers["stop_guiding"] = stop_guiding

    async def get_guiding_status() -> str:
        """Get current guiding status and RMS (Step 395)."""
        guider = None
        if 'guider_client' in dir() and guider_client:
            guider = guider_client
        elif 'phd2_client' in dir():
            guider = phd2_client if phd2_client else None

        if not guider:
            return "Guiding service not available"

        try:
            parts = []

            # Check if guiding
            is_guiding = False
            if hasattr(guider, 'is_guiding'):
                is_guiding = guider.is_guiding()
                parts.append(f"Guiding: {'Active' if is_guiding else 'Inactive'}")

            # Get RMS if guiding
            if is_guiding:
                if hasattr(guider, 'get_rms'):
                    rms = guider.get_rms()
                    if rms:
                        parts.append(f"RMS: {rms.total:.2f}\" (RA: {rms.ra:.2f}\", Dec: {rms.dec:.2f}\")")
                        if rms.total < 1.0:
                            parts.append("Guiding quality: Excellent")
                        elif rms.total < 1.5:
                            parts.append("Guiding quality: Good")
                        elif rms.total < 2.5:
                            parts.append("Guiding quality: Fair")
                        else:
                            parts.append("Guiding quality: Poor - consider recalibration")

            # Get guide star info
            if hasattr(guider, 'get_star_info'):
                star = guider.get_star_info()
                if star:
                    parts.append(f"Guide star SNR: {star.snr:.1f}")

            return ". ".join(parts) if parts else "No guiding information available"

        except Exception as e:
            return f"Error getting guiding status: {e}"

    handlers["get_guiding_status"] = get_guiding_status

    # Device discovery handlers (Steps 441, 446)
    async def indi_discover_devices() -> str:
        """Discover INDI devices on the server (Step 441).

        Scans the INDI server for available devices and returns
        their names, types, and connection status.
        """
        # Check for INDI client
        indi = None
        if 'indi_client' in dir() and indi_client:
            indi = indi_client

        if not indi:
            return "INDI client not available. Check INDI server connection."

        try:
            devices = []

            # Get device list
            if hasattr(indi, 'get_devices'):
                device_list = indi.get_devices()
                for device in device_list:
                    name = device.name if hasattr(device, 'name') else str(device)
                    dev_type = device.device_type if hasattr(device, 'device_type') else 'unknown'
                    connected = device.connected if hasattr(device, 'connected') else False
                    devices.append({
                        'name': name,
                        'type': dev_type,
                        'connected': connected
                    })

            elif hasattr(indi, 'devices'):
                # Alternative attribute
                for name, device in indi.devices.items():
                    dev_type = getattr(device, 'device_type', 'unknown')
                    connected = getattr(device, 'connected', False)
                    devices.append({
                        'name': name,
                        'type': dev_type,
                        'connected': connected
                    })

            if not devices:
                return "No INDI devices found. Ensure INDI server is running with device drivers."

            # Format response
            parts = [f"Found {len(devices)} INDI device(s):"]
            for dev in devices:
                status = "connected" if dev['connected'] else "available"
                parts.append(f"  • {dev['name']} ({dev['type']}) - {status}")

            return "\n".join(parts)

        except Exception as e:
            return f"Error discovering INDI devices: {e}"

    handlers["indi_discover_devices"] = indi_discover_devices

    async def alpaca_discover_devices(timeout: float = 5.0) -> str:
        """Discover Alpaca devices via broadcast (Step 446).

        Performs Alpaca device discovery using UDP broadcast
        to find ASCOM Alpaca servers on the local network.

        Args:
            timeout: Discovery timeout in seconds
        """
        # Check for Alpaca client
        alpaca = None
        if 'alpaca_client' in dir() and alpaca_client:
            alpaca = alpaca_client

        try:
            devices = []

            # Try using alpaca client discovery
            if alpaca and hasattr(alpaca, 'discover'):
                discovered = await alpaca.discover(timeout=timeout)
                for server in discovered:
                    devices.append({
                        'server': server.get('address', 'unknown'),
                        'port': server.get('port', 11111),
                        'name': server.get('name', 'Alpaca Server')
                    })

            # Fallback: try direct UDP broadcast discovery
            if not devices:
                import asyncio
                import socket
                import json

                # Alpaca discovery port
                DISCOVERY_PORT = 32227

                try:
                    # Create UDP socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    sock.settimeout(timeout)

                    # Send discovery request
                    discovery_msg = json.dumps({"alpacaport": 0}).encode()
                    sock.sendto(discovery_msg, ('255.255.255.255', DISCOVERY_PORT))

                    # Collect responses
                    start = asyncio.get_event_loop().time()
                    while asyncio.get_event_loop().time() - start < timeout:
                        try:
                            data, addr = sock.recvfrom(1024)
                            response = json.loads(data.decode())
                            devices.append({
                                'server': addr[0],
                                'port': response.get('AlpacaPort', 11111),
                                'name': response.get('ServerName', 'Alpaca Server')
                            })
                        except socket.timeout:
                            break
                        except Exception:
                            continue

                    sock.close()
                except Exception:
                    pass

            if not devices:
                return "No Alpaca devices found. Ensure Alpaca server is running on the network."

            # Get device details from each server
            parts = [f"Found {len(devices)} Alpaca server(s):"]
            for server in devices:
                parts.append(f"  • {server['name']} at {server['server']}:{server['port']}")

                # Try to get device list from server
                if alpaca and hasattr(alpaca, 'get_configured_devices'):
                    try:
                        server_devices = await alpaca.get_configured_devices(
                            server['server'], server['port']
                        )
                        for dev in server_devices:
                            parts.append(f"      - {dev['DeviceType']}/{dev['DeviceNumber']}: {dev.get('DeviceName', 'unnamed')}")
                    except Exception:
                        pass

            return "\n".join(parts)

        except Exception as e:
            return f"Error discovering Alpaca devices: {e}"

    handlers["alpaca_discover_devices"] = alpaca_discover_devices

    # Observing suggestions handler
    async def whats_up_tonight(
        object_type: str = None,
        min_altitude: float = 20.0,
        max_magnitude: float = 10.0,
        limit: int = 10
    ) -> str:
        """Get observing suggestions for tonight (Step 367).

        Returns a summary of what's visible and recommended for observation,
        including planets, notable deep sky objects, and seasonal highlights.

        Args:
            object_type: Filter by type (galaxy, nebula, cluster, planet)
            min_altitude: Minimum altitude in degrees (default 20)
            max_magnitude: Maximum magnitude/brightness limit (default 10)
            limit: Maximum number of suggestions (default 10)
        """
        parts = []

        # Check if it's dark enough to observe
        is_dark = False
        if ephemeris_service:
            try:
                is_dark = ephemeris_service.is_astronomical_night()
                if not is_dark:
                    sun_alt = ephemeris_service.get_sun_altitude()
                    if sun_alt > 0:
                        parts.append("The sun is still up. Wait for sunset to observe.")
                    else:
                        parts.append(f"Twilight in progress. Sun is {abs(sun_alt):.1f}° below horizon.")
                        parts.append("Deep sky objects may not be visible yet.")
            except Exception:
                pass

        suggestions = []

        # Get visible planets
        if not object_type or object_type.lower() == "planet":
            if ephemeris_service:
                try:
                    from services.ephemeris import CelestialBody
                    planets = [
                        CelestialBody.VENUS, CelestialBody.MARS,
                        CelestialBody.JUPITER, CelestialBody.SATURN
                    ]
                    for planet in planets:
                        try:
                            pos = ephemeris_service.get_body_position(planet)
                            if pos and pos.altitude_degrees >= min_altitude:
                                suggestions.append({
                                    'name': planet.value.capitalize(),
                                    'type': 'planet',
                                    'altitude': pos.altitude_degrees,
                                    'azimuth': pos.azimuth_degrees,
                                    'description': f"Visible at {pos.altitude_degrees:.0f}° altitude"
                                })
                        except Exception:
                            continue
                except Exception:
                    pass

        # Get Moon info (important for planning)
        moon_warning = None
        if ephemeris_service:
            try:
                from services.ephemeris import CelestialBody
                moon_pos = ephemeris_service.get_body_position(CelestialBody.MOON)
                if moon_pos and moon_pos.altitude_degrees > 0:
                    illumination = 50  # default
                    if hasattr(ephemeris_service, 'get_moon_phase'):
                        phase = ephemeris_service.get_moon_phase()
                        if phase:
                            illumination = phase.get('illumination', 0.5) * 100
                    if illumination > 50:
                        moon_warning = f"Moon is up ({illumination:.0f}% illuminated) - may affect faint objects"
            except Exception:
                pass

        # Get deep sky objects from catalog
        if catalog_service and (not object_type or object_type.lower() != "planet"):
            try:
                # Get objects by type if specified
                type_filter = None
                if object_type:
                    type_map = {
                        'galaxy': 'galaxy',
                        'galaxies': 'galaxy',
                        'nebula': 'nebula',
                        'nebulae': 'nebula',
                        'cluster': 'open_cluster',
                        'clusters': 'open_cluster',
                        'globular': 'globular_cluster',
                        'planetary': 'planetary_nebula'
                    }
                    type_filter = type_map.get(object_type.lower())

                # Try to get objects visible tonight
                dso_list = []

                if hasattr(catalog_service, 'objects_by_type') and type_filter:
                    results = catalog_service.objects_by_type(
                        type_filter, max_magnitude, limit=limit*2
                    )
                    for obj in results:
                        dso_list.append(obj)
                elif hasattr(catalog_service, 'db'):
                    # Query database directly for bright objects
                    if hasattr(catalog_service.db, 'get_all_objects'):
                        all_objs = catalog_service.db.get_all_objects()
                        # Filter by magnitude
                        for obj in all_objs:
                            if obj.magnitude and obj.magnitude <= max_magnitude:
                                if not type_filter or (obj.object_type and obj.object_type.value == type_filter):
                                    dso_list.append(obj)

                # Filter by altitude if ephemeris available
                for obj in dso_list[:limit*2]:
                    if len(suggestions) >= limit:
                        break

                    # Check if above horizon
                    is_visible = True
                    obj_alt = None
                    if ephemeris_service and hasattr(obj, 'ra_hours') and hasattr(obj, 'dec_degrees'):
                        try:
                            obj_alt = ephemeris_service.get_object_altitude(
                                obj.ra_hours, obj.dec_degrees
                            )
                            if obj_alt < min_altitude:
                                is_visible = False
                        except Exception:
                            pass

                    if is_visible:
                        name = obj.name or obj.catalog_id
                        obj_type = obj.object_type.value if hasattr(obj.object_type, 'value') else str(obj.object_type)
                        desc = f"Magnitude {obj.magnitude:.1f}" if obj.magnitude else ""
                        if obj_alt:
                            desc += f", altitude {obj_alt:.0f}°"

                        suggestions.append({
                            'name': name,
                            'type': obj_type,
                            'altitude': obj_alt,
                            'magnitude': obj.magnitude,
                            'description': desc
                        })
            except Exception as e:
                parts.append(f"(Catalog search limited: {e})")

        # Step 368: Add visibility window prioritization
        # Calculate time until set for each object
        for suggestion in suggestions:
            suggestion['hours_visible'] = None
            suggestion['priority_score'] = 0

            if ephemeris_service and suggestion.get('altitude'):
                try:
                    # Estimate hours visible based on altitude and declination
                    # Objects near transit have more time, objects setting soon have less
                    alt = suggestion['altitude']

                    # Higher altitude = more time remaining (simplified)
                    # Objects above 60° are likely near transit
                    # Objects at 20-30° are likely setting soon
                    if alt > 60:
                        suggestion['hours_visible'] = 4.0
                        suggestion['visibility_note'] = "Near transit - excellent timing"
                    elif alt > 45:
                        suggestion['hours_visible'] = 3.0
                        suggestion['visibility_note'] = "Good visibility window"
                    elif alt > 30:
                        suggestion['hours_visible'] = 2.0
                        suggestion['visibility_note'] = "Observe soon"
                    else:
                        suggestion['hours_visible'] = 1.0
                        suggestion['visibility_note'] = "Setting soon - observe now"

                    # Priority score combines altitude and visibility window
                    # Higher = better target to observe now
                    if suggestion['hours_visible']:
                        # Prefer objects setting soon but still at good altitude
                        if alt > 30 and suggestion['hours_visible'] <= 2.0:
                            suggestion['priority_score'] = 100  # Urgent - setting soon
                        elif alt > 45:
                            suggestion['priority_score'] = 80   # Good position
                        elif alt > 60:
                            suggestion['priority_score'] = 60   # Can wait - near transit
                        else:
                            suggestion['priority_score'] = 40   # Low priority
                except Exception:
                    pass

        # Build response
        if moon_warning:
            parts.append(moon_warning)

        if not suggestions:
            parts.append("No objects matching criteria currently visible.")
            if not is_dark:
                parts.append("Try again after astronomical twilight.")
            return " ".join(parts)

        # Sort by priority score (objects needing observation soonest first)
        # Then by altitude as tiebreaker
        suggestions.sort(key=lambda x: (x.get('priority_score') or 0, x.get('altitude') or 0), reverse=True)
        suggestions = suggestions[:limit]

        # Group by type
        planets = [s for s in suggestions if s['type'] == 'planet']
        dso = [s for s in suggestions if s['type'] != 'planet']

        if planets:
            parts.append("Visible planets:")
            for p in planets:
                desc = p['description']
                if p.get('visibility_note'):
                    desc += f" - {p['visibility_note']}"
                parts.append(f"  • {p['name']}: {desc}")

        if dso:
            parts.append("Recommended objects (prioritized by visibility window):")
            for obj in dso:
                desc = obj['description']
                if obj.get('visibility_note'):
                    desc += f" - {obj['visibility_note']}"
                parts.append(f"  • {obj['name']} ({obj['type']}): {desc}")

        return "\n".join(parts)

    handlers["whats_up_tonight"] = whats_up_tonight

    return handlers


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

TELESCOPE_SYSTEM_PROMPT = """You are NIGHTWATCH, an AI assistant for controlling an autonomous telescope observatory in central Nevada.

Observatory: Intes Micro MN76 (7" f/6 Maksutov-Newtonian, sometimes designated MN78) on DIY harmonic drive GEM mount.
Location: Central Nevada dark sky site (~6000 ft elevation, 280+ clear nights/year).
Controller: OnStepX on Teensy 4.1 with TMC5160 drivers.
Imaging Camera: ZWO ASI662MC for planetary imaging.
Guide Camera: ASI120MM-S with PHD2 autoguiding.
Focuser: ZWO EAF with temperature compensation.
Enclosure: Roll-off roof with weather interlocks.
Power: APC Smart-UPS with NUT monitoring.
Version: 3.3 (POS Panel certified - Full Automation + Cross-Platform Device Support)

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

ALPACA DEVICE CONTROL (v3.3 - Network Device Layer):
- alpaca_discover_devices: Discover all ASCOM Alpaca devices on local network
- alpaca_set_filter: Change filter by name (L, R, G, B, Ha, OIII, SII) or position (0-6)
- alpaca_get_filter: Get current Alpaca filter wheel position and name
- alpaca_move_focuser: Move Alpaca focuser to position (absolute or relative)
- alpaca_get_focuser_status: Get focuser position, temperature, and temp compensation status
- Alpaca provides network-based device control via REST API (port 11111)
- Use these tools when controlling devices through Alpaca servers (Windows/cross-platform)
- Alpaca positions are 0-indexed (vs INDI 1-indexed)

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
