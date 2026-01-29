# NIGHTWATCH API Reference

Complete API documentation for NIGHTWATCH observatory services.

## Table of Contents

- [Mount Control Service](#mount-control-service)
- [Weather Service](#weather-service)
- [Safety Monitor Service](#safety-monitor-service)
- [Catalog Service](#catalog-service)
- [Ephemeris Service](#ephemeris-service)
- [Meteor Tracking Service](#meteor-tracking-service)
- [Voice Pipeline](#voice-pipeline)
- [Tool Handlers](#tool-handlers)

---

## Mount Control Service

**Module**: `services.mount_control.onstepx_client`

### OnStepXClient

TCP/IP client for OnStepX mount controller using LX200 protocol.

```python
from services.mount_control.onstepx_client import OnStepXClient

client = OnStepXClient(host="192.168.1.100", port=9999)
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `connect()` | - | `bool` | Establish connection to mount |
| `disconnect()` | - | `None` | Close connection |
| `get_ra()` | - | `float` | Get current RA in decimal hours |
| `get_dec()` | - | `float` | Get current Dec in decimal degrees |
| `get_alt()` | - | `float` | Get current altitude in degrees |
| `get_az()` | - | `float` | Get current azimuth in degrees |
| `slew_to_coordinates(ra, dec)` | `ra: float`, `dec: float` | `bool` | Slew to RA/Dec (J2000) |
| `slew_to_altaz(alt, az)` | `alt: float`, `az: float` | `bool` | Slew to Alt/Az |
| `sync(ra, dec)` | `ra: float`, `dec: float` | `bool` | Sync mount position |
| `park()` | - | `bool` | Park the mount |
| `unpark()` | - | `bool` | Unpark the mount |
| `stop()` | - | `bool` | Emergency stop all motion |
| `abort_slew()` | - | `bool` | Abort current slew |
| `set_tracking(enabled)` | `enabled: bool` | `bool` | Enable/disable tracking |
| `is_slewing()` | - | `bool` | Check if mount is slewing |
| `is_parked()` | - | `bool` | Check if mount is parked |
| `is_tracking()` | - | `bool` | Check if mount is tracking |
| `get_status()` | - | `dict` | Get full mount status |

#### Status Dictionary

```python
{
    "connected": True,
    "ra_hours": 10.5,
    "dec_degrees": 45.0,
    "alt_degrees": 60.0,
    "az_degrees": 180.0,
    "is_slewing": False,
    "is_parked": False,
    "is_tracking": True,
    "pier_side": "east"
}
```

---

## Weather Service

**Module**: `services.weather.ecowitt`

### EcowittWeather

Interface for Ecowitt weather station via GW1000/GW2000 gateway.

```python
from services.weather.ecowitt import EcowittWeather

weather = EcowittWeather(host="192.168.1.101")
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `connect()` | - | `bool` | Connect to weather station |
| `get_conditions()` | - | `dict` | Get current weather conditions |
| `get_temperature()` | - | `float` | Temperature in Celsius |
| `get_humidity()` | - | `float` | Relative humidity (0-100) |
| `get_wind_speed()` | - | `float` | Wind speed in m/s |
| `get_wind_gust()` | - | `float` | Wind gust in m/s |
| `get_wind_direction()` | - | `float` | Wind direction in degrees |
| `get_pressure()` | - | `float` | Barometric pressure in hPa |
| `get_rain_rate()` | - | `float` | Rain rate in mm/hr |
| `is_raining()` | - | `bool` | Check if rain detected |

#### Conditions Dictionary

```python
{
    "temperature_c": 15.5,
    "humidity_percent": 65,
    "wind_speed_ms": 3.2,
    "wind_gust_ms": 5.1,
    "wind_direction_deg": 225,
    "pressure_hpa": 1013.25,
    "rain_rate_mmhr": 0.0,
    "rain_detected": False,
    "dewpoint_c": 8.3,
    "timestamp": "2025-01-20T20:30:00Z"
}
```

---

## Safety Monitor Service

**Module**: `services.safety_monitor.safety`

### SafetyMonitor

Automated safety monitoring with configurable thresholds.

```python
from services.safety_monitor.safety import SafetyMonitor

safety = SafetyMonitor(config_path="config/safety.yaml")
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `is_safe()` | - | `bool` | Check overall safety status |
| `is_safe_to_slew()` | - | `bool` | Check if safe to slew mount |
| `is_safe_to_unpark()` | - | `bool` | Check if safe to unpark |
| `is_safe_to_open()` | - | `bool` | Check if safe to open enclosure |
| `get_conditions()` | - | `dict` | Get current safety conditions |
| `get_veto_reasons()` | - | `List[str]` | Get list of active safety concerns |
| `evaluate(weather_data)` | `weather_data: dict` | `dict` | Evaluate weather against thresholds |
| `set_threshold(name, value)` | `name: str`, `value: float` | `None` | Update a safety threshold |
| `get_thresholds()` | - | `dict` | Get all safety thresholds |

#### Safety Thresholds

| Threshold | Default | Description |
|-----------|---------|-------------|
| `max_wind_speed_ms` | 10.0 | Maximum safe wind speed |
| `max_humidity_percent` | 90 | Maximum safe humidity |
| `min_temperature_c` | -20 | Minimum operating temperature |
| `max_temperature_c` | 40 | Maximum operating temperature |
| `rain_holdoff_minutes` | 30 | Wait time after rain stops |
| `min_altitude_degrees` | 10 | Minimum slew altitude |

---

## Catalog Service

**Module**: `services.catalog.catalog`

### CatalogService

Astronomical object database with fuzzy search.

```python
from services.catalog.catalog import CatalogService

catalog = CatalogService()
catalog.initialize()
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `lookup(query)` | `query: str` | `CatalogObject` | Exact lookup by name/ID |
| `fuzzy_search(query, min_score, limit)` | `query: str`, `min_score: float=0.6`, `limit: int=10` | `List[Tuple]` | Fuzzy name matching |
| `suggest(query, limit)` | `query: str`, `limit: int=5` | `List[str]` | Get name suggestions |
| `resolve_object(query)` | `query: str` | `Tuple[float, float]` | Get RA/Dec coordinates |
| `what_is(query)` | `query: str` | `str` | Get human-readable description |
| `get_object_details(query)` | `query: str` | `dict` | Get full object details |
| `objects_in_area(ra, dec, radius, limit)` | RA, Dec, radius in arcmin | `List[Tuple]` | Cone search |
| `objects_by_type(type_name, max_mag, limit)` | type, magnitude, limit | `List[CatalogObject]` | Search by object type |
| `objects_in_constellation(name, max_mag, limit)` | constellation, magnitude, limit | `List[CatalogObject]` | Search by constellation |

#### CatalogObject

```python
@dataclass
class CatalogObject:
    catalog_id: str       # "M31", "NGC 224"
    name: str             # "Andromeda Galaxy"
    object_type: ObjectType
    ra_hours: float       # 0.7119
    dec_degrees: float    # 41.269
    magnitude: float      # 3.4
    size_arcmin: float    # 178.0
    constellation: str    # "Andromeda"
    description: str
    aliases: List[str]    # ["NGC 224", "UGC 454"]
```

#### Object Types

```python
class ObjectType(Enum):
    STAR = "star"
    DOUBLE_STAR = "double_star"
    OPEN_CLUSTER = "open_cluster"
    GLOBULAR_CLUSTER = "globular_cluster"
    NEBULA = "nebula"
    PLANETARY_NEBULA = "planetary_nebula"
    GALAXY = "galaxy"
    PLANET = "planet"
```

---

## Ephemeris Service

**Module**: `services.ephemeris.ephemeris`

### EphemerisService

Celestial calculations using Skyfield.

```python
from services.ephemeris.ephemeris import EphemerisService

ephemeris = EphemerisService(latitude=39.0, longitude=-117.0)
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_planet_position(planet)` | `planet: str` | `dict` | Get planet RA/Dec/Alt/Az |
| `get_sun_position()` | - | `dict` | Get Sun position and times |
| `get_moon_position()` | - | `dict` | Get Moon position and phase |
| `get_object_altitude(ra, dec)` | `ra: float`, `dec: float` | `float` | Calculate current altitude |
| `get_rise_set_times(ra, dec)` | `ra: float`, `dec: float` | `dict` | Get rise/transit/set times |
| `is_above_horizon(ra, dec)` | `ra: float`, `dec: float` | `bool` | Check if object is up |
| `get_lst()` | - | `float` | Get local sidereal time |
| `get_twilight_times()` | - | `dict` | Get astronomical twilight |

#### Planet Position Response

```python
{
    "name": "Jupiter",
    "ra_hours": 3.45,
    "dec_degrees": 18.2,
    "alt_degrees": 45.3,
    "az_degrees": 180.5,
    "magnitude": -2.5,
    "distance_au": 4.5,
    "rise_time": "18:30:00",
    "transit_time": "23:45:00",
    "set_time": "05:00:00"
}
```

---

## Meteor Tracking Service

**Module**: `services.meteor_tracking`

### MeteorTrackingService

Monitors fireball and meteor data from NASA CNEOS and American Meteor Society, generates alerts with Lexicon prayers.

```python
from services.meteor_tracking import get_meteor_service

MeteorTrackingService, MeteorConfig, MeteorAlert = get_meteor_service()

config = MeteorConfig(default_lat=38.9, default_lon=-117.4)
service = MeteorTrackingService(config)
await service.start()
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `start()` | - | `None` | Start monitoring loop |
| `stop()` | - | `None` | Stop monitoring |
| `add_watch(text)` | `text: str` | `str` | Create watch from natural language |
| `get_status()` | - | `str` | Get current status in Lexicon |
| `get_shower_info(name)` | `name: str \| None` | `str` | Get shower information |
| `check_now()` | - | `str` | Manual fireball check |
| `get_active_windows()` | - | `List[WatchWindow]` | Get active watch windows |

### WatchManager

Natural language parsing for meteor watch requests.

```python
from services.meteor_tracking import WatchManager

manager = WatchManager()
window = manager.add_watch("Perseids peak next week from Nevada")
```

### Lexicon Prayer Generation

```python
from services.meteor_tracking import generate_prayer_of_finding

prayer = generate_prayer_of_finding(
    timestamp=datetime.now(),
    lat=39.5, lon=-117.2,
    magnitude=-8,
    trajectory=trajectory_result,
    sky_conditions="nevada-sky-clear"
)
# Returns Lexicon-formatted prayer with coordinates and alchemical symbol
```

### Voice Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `watch_for_meteors` | `request: str` | Create watch window |
| `get_meteor_status` | - | Get tracking status |
| `get_meteor_shower_info` | `shower_name: str` | Get shower details |
| `check_for_fireballs` | - | Manual database check |
| `get_active_watch_windows` | - | List active windows |

---

## Voice Pipeline

**Module**: `voice.pipeline`

### VoicePipeline

Complete voice control pipeline: STT → LLM → TTS.

```python
from voice.pipeline import VoicePipeline

pipeline = VoicePipeline(config_path="config/voice.yaml")
await pipeline.start()
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `start()` | - | `None` | Start the voice pipeline |
| `stop()` | - | `None` | Stop the voice pipeline |
| `process_audio(audio_data)` | `audio_data: bytes` | `str` | Process audio and get response |
| `set_wake_word(word)` | `word: str` | `None` | Set wake word |
| `is_listening()` | - | `bool` | Check if pipeline is active |

### STT Service

**Module**: `voice.stt.whisper_stt`

```python
from voice.stt.whisper_stt import WhisperSTT

stt = WhisperSTT(model="base")
text = await stt.transcribe(audio_bytes)
```

### TTS Service

**Module**: `voice.tts.piper_tts`

```python
from voice.tts.piper_tts import PiperTTS

tts = PiperTTS(voice="en_US-lessac-medium")
audio = await tts.synthesize("Slewing to Andromeda Galaxy")
```

---

## Tool Handlers

**Module**: `voice.tools.telescope_tools`

### Available Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `goto_object` | `object_name: str` | Slew to catalog object |
| `goto_coordinates` | `ra: str`, `dec: str` | Slew to coordinates |
| `park_telescope` | `confirmed: bool` | Park the mount |
| `unpark_telescope` | - | Unpark the mount |
| `stop_telescope` | - | Emergency stop |
| `get_mount_status` | - | Get current status |
| `start_tracking` | - | Start sidereal tracking |
| `stop_tracking` | - | Stop tracking |
| `sync_position` | `object_name: str`, `confirmed: bool` | Sync to object |
| `lookup_object` | `object_name: str` | Get object info |
| `find_objects` | `object_type: str`, `constellation: str` | Search catalog |
| `get_weather` | - | Get weather conditions |
| `get_planet_position` | `planet: str` | Get planet position |
| `whats_up_tonight` | `object_type: str` | Get observing suggestions |

### Tool Response Format

```python
{
    "success": True,
    "message": "Slewing to Andromeda Galaxy",
    "data": {
        "target": "M31",
        "ra": "00:42:44",
        "dec": "+41:16:09"
    }
}
```

---

## Error Handling

All services use consistent error handling:

```python
class NightwatchError(Exception):
    """Base exception for NIGHTWATCH errors."""
    pass

class ConnectionError(NightwatchError):
    """Failed to connect to device/service."""
    pass

class SafetyError(NightwatchError):
    """Operation blocked by safety system."""
    pass

class CatalogError(NightwatchError):
    """Object not found in catalog."""
    pass
```

---

## Configuration

Services are configured via YAML files in `config/`:

```yaml
# config/nightwatch.yaml
mount:
  type: onstepx
  host: 192.168.1.100
  port: 9999
  timeout: 5.0

weather:
  type: ecowitt
  host: 192.168.1.101
  poll_interval: 60

safety:
  config_file: config/safety.yaml

catalog:
  database: nightwatch_catalog.db
  cache_size: 100
```

See [CONFIGURATION.md](CONFIGURATION.md) for full configuration reference.
