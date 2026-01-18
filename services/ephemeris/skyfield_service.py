"""
NIGHTWATCH Ephemeris Service
Skyfield-based Astronomical Calculations

This module provides ephemeris calculations for:
- Planet positions (Mercury through Neptune, plus Pluto)
- Sun and Moon positions
- Rise/set/transit times
- Altitude/azimuth for any object
- Coordinate transformations (J2000 <-> JNow)
- Twilight calculations

Uses the Skyfield library with JPL DE440 ephemeris data.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, List, Tuple
import math

try:
    from skyfield.api import load, Topos, Star, wgs84
    from skyfield.almanac import find_discrete, risings_and_settings, dark_twilight_day
    from skyfield import almanac
    SKYFIELD_AVAILABLE = True
except ImportError:
    SKYFIELD_AVAILABLE = False
    print("Warning: Skyfield not installed. Run: pip install skyfield")


class CelestialBody(Enum):
    """Solar system bodies available for ephemeris."""
    SUN = "sun"
    MOON = "moon"
    MERCURY = "mercury"
    VENUS = "venus"
    MARS = "mars"
    JUPITER = "jupiter"
    SATURN = "saturn"
    URANUS = "uranus"
    NEPTUNE = "neptune"
    PLUTO = "pluto"


class TwilightPhase(Enum):
    """Twilight phases."""
    DAY = "day"                      # Sun > 0°
    CIVIL = "civil"                  # Sun -6° to 0°
    NAUTICAL = "nautical"            # Sun -12° to -6°
    ASTRONOMICAL = "astronomical"    # Sun -18° to -12°
    NIGHT = "night"                  # Sun < -18°


@dataclass
class Position:
    """Celestial position."""
    ra_hours: float          # Right Ascension (hours, 0-24)
    dec_degrees: float       # Declination (degrees, -90 to +90)
    distance_au: float       # Distance in AU

    # Apparent position (corrected for precession, nutation, aberration)
    ra_apparent: Optional[float] = None
    dec_apparent: Optional[float] = None

    @property
    def ra_hms(self) -> str:
        """RA in HH:MM:SS format."""
        h = int(self.ra_hours)
        m = int((self.ra_hours - h) * 60)
        s = ((self.ra_hours - h) * 60 - m) * 60
        return f"{h:02d}:{m:02d}:{s:05.2f}"

    @property
    def dec_dms(self) -> str:
        """DEC in sDD:MM:SS format."""
        sign = "+" if self.dec_degrees >= 0 else "-"
        d = abs(self.dec_degrees)
        deg = int(d)
        m = int((d - deg) * 60)
        s = ((d - deg) * 60 - m) * 60
        return f"{sign}{deg:02d}:{m:02d}:{s:05.2f}"


@dataclass
class HorizontalPosition:
    """Altitude/Azimuth position."""
    altitude_degrees: float  # Degrees above horizon (-90 to +90)
    azimuth_degrees: float   # Degrees from North (0-360)

    @property
    def is_visible(self) -> bool:
        """Check if object is above horizon."""
        return self.altitude_degrees > 0

    @property
    def compass_direction(self) -> str:
        """Get compass direction string."""
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                      "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        index = round(self.azimuth_degrees / 22.5) % 16
        return directions[index]


@dataclass
class RiseTransitSet:
    """Rise, transit, and set times for an object."""
    rise_time: Optional[datetime]
    transit_time: Optional[datetime]
    set_time: Optional[datetime]
    rise_azimuth: Optional[float] = None
    transit_altitude: Optional[float] = None
    set_azimuth: Optional[float] = None


@dataclass
class ObserverLocation:
    """Observer's location on Earth."""
    latitude: float       # Degrees
    longitude: float      # Degrees (negative = West)
    elevation_m: float    # Meters above sea level
    name: str = "Observer"

    @classmethod
    def nevada_site(cls) -> "ObserverLocation":
        """Default NIGHTWATCH location in central Nevada."""
        return cls(
            latitude=39.0,
            longitude=-117.0,
            elevation_m=1800,
            name="NIGHTWATCH Nevada"
        )


class EphemerisService:
    """
    Skyfield-based ephemeris service for NIGHTWATCH.

    Provides high-precision astronomical calculations for
    telescope pointing and observing session planning.
    """

    # Ephemeris data directory
    DATA_DIR = Path(__file__).parent / "data"

    # Body name mappings for Skyfield
    BODY_NAMES = {
        CelestialBody.SUN: "sun",
        CelestialBody.MOON: "moon",
        CelestialBody.MERCURY: "mercury barycenter",
        CelestialBody.VENUS: "venus barycenter",
        CelestialBody.MARS: "mars barycenter",
        CelestialBody.JUPITER: "jupiter barycenter",
        CelestialBody.SATURN: "saturn barycenter",
        CelestialBody.URANUS: "uranus barycenter",
        CelestialBody.NEPTUNE: "neptune barycenter",
        CelestialBody.PLUTO: "pluto barycenter",
    }

    def __init__(self, location: Optional[ObserverLocation] = None):
        """
        Initialize ephemeris service.

        Args:
            location: Observer location (defaults to Nevada site)
        """
        self.location = location or ObserverLocation.nevada_site()
        self._ts = None
        self._eph = None
        self._earth = None
        self._observer = None
        self._initialized = False

    def initialize(self):
        """Load ephemeris data (can be slow on first run)."""
        if not SKYFIELD_AVAILABLE:
            raise RuntimeError("Skyfield library not available")

        # Create data directory
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Load timescale
        self._ts = load.timescale()

        # Load ephemeris (downloads if not cached)
        # DE440 is the current JPL ephemeris (1550-2650)
        self._eph = load('de440s.bsp')

        # Get Earth
        self._earth = self._eph['earth']

        # Create observer position
        self._observer = self._earth + wgs84.latlon(
            self.location.latitude,
            self.location.longitude,
            elevation_m=self.location.elevation_m
        )

        self._initialized = True

    def _ensure_initialized(self):
        """Ensure service is initialized."""
        if not self._initialized:
            self.initialize()

    def _get_time(self, dt: Optional[datetime] = None):
        """Get Skyfield time object."""
        if dt is None:
            dt = datetime.now(timezone.utc)
        elif dt.tzinfo is None:
            # Assume UTC if no timezone
            dt = dt.replace(tzinfo=timezone.utc)
        return self._ts.from_datetime(dt)

    def get_body_position(
        self,
        body: CelestialBody,
        when: Optional[datetime] = None
    ) -> Position:
        """
        Get position of a solar system body.

        Args:
            body: Celestial body to locate
            when: Time for calculation (default: now)

        Returns:
            Position with RA/DEC coordinates
        """
        self._ensure_initialized()
        t = self._get_time(when)

        # Get body from ephemeris
        target = self._eph[self.BODY_NAMES[body]]

        # Compute astrometric position from observer
        astrometric = self._observer.at(t).observe(target)

        # Get apparent position (includes aberration, etc.)
        apparent = astrometric.apparent()
        ra_app, dec_app, dist = apparent.radec()

        # Get J2000 position
        ra, dec, _ = astrometric.radec(epoch='J2000')

        return Position(
            ra_hours=ra.hours,
            dec_degrees=dec.degrees,
            distance_au=dist.au,
            ra_apparent=ra_app.hours,
            dec_apparent=dec_app.degrees
        )

    def get_body_altaz(
        self,
        body: CelestialBody,
        when: Optional[datetime] = None
    ) -> HorizontalPosition:
        """
        Get altitude/azimuth of a solar system body.

        Args:
            body: Celestial body to locate
            when: Time for calculation (default: now)

        Returns:
            HorizontalPosition with alt/az
        """
        self._ensure_initialized()
        t = self._get_time(when)

        target = self._eph[self.BODY_NAMES[body]]
        astrometric = self._observer.at(t).observe(target)
        apparent = astrometric.apparent()

        alt, az, _ = apparent.altaz()

        return HorizontalPosition(
            altitude_degrees=alt.degrees,
            azimuth_degrees=az.degrees
        )

    def get_star_altaz(
        self,
        ra_hours: float,
        dec_degrees: float,
        when: Optional[datetime] = None
    ) -> HorizontalPosition:
        """
        Get altitude/azimuth for fixed coordinates (star/DSO).

        Args:
            ra_hours: Right Ascension in hours (J2000)
            dec_degrees: Declination in degrees (J2000)
            when: Time for calculation (default: now)

        Returns:
            HorizontalPosition with alt/az
        """
        self._ensure_initialized()
        t = self._get_time(when)

        # Create a "star" at fixed coordinates
        star = Star(ra_hours=ra_hours, dec_degrees=dec_degrees)

        astrometric = self._observer.at(t).observe(star)
        apparent = astrometric.apparent()

        alt, az, _ = apparent.altaz()

        return HorizontalPosition(
            altitude_degrees=alt.degrees,
            azimuth_degrees=az.degrees
        )

    def get_sun_altitude(self, when: Optional[datetime] = None) -> float:
        """Get current sun altitude in degrees."""
        pos = self.get_body_altaz(CelestialBody.SUN, when)
        return pos.altitude_degrees

    def get_moon_phase(self, when: Optional[datetime] = None) -> float:
        """
        Get moon phase as illumination percentage.

        Returns:
            Float from 0.0 (new) to 1.0 (full)
        """
        self._ensure_initialized()
        t = self._get_time(when)

        sun = self._eph['sun']
        moon = self._eph['moon']
        earth = self._eph['earth']

        # Calculate phase angle
        e = earth.at(t)
        s = e.observe(sun).apparent()
        m = e.observe(moon).apparent()

        # Elongation angle between sun and moon
        elongation = s.separation_from(m)

        # Phase illumination (simplified)
        phase = (1 - math.cos(elongation.radians)) / 2

        return phase

    def get_twilight_phase(self, when: Optional[datetime] = None) -> TwilightPhase:
        """
        Determine current twilight phase.

        Returns:
            TwilightPhase enum value
        """
        sun_alt = self.get_sun_altitude(when)

        if sun_alt > 0:
            return TwilightPhase.DAY
        elif sun_alt > -6:
            return TwilightPhase.CIVIL
        elif sun_alt > -12:
            return TwilightPhase.NAUTICAL
        elif sun_alt > -18:
            return TwilightPhase.ASTRONOMICAL
        else:
            return TwilightPhase.NIGHT

    def is_astronomical_night(self, when: Optional[datetime] = None) -> bool:
        """Check if it's astronomical night (sun < -18°)."""
        return self.get_twilight_phase(when) == TwilightPhase.NIGHT

    def get_visible_planets(
        self,
        when: Optional[datetime] = None,
        min_altitude: float = 10.0
    ) -> List[Tuple[CelestialBody, HorizontalPosition]]:
        """
        Get list of planets currently above horizon.

        Args:
            when: Time for calculation
            min_altitude: Minimum altitude in degrees

        Returns:
            List of (body, position) tuples, sorted by altitude
        """
        planets = [
            CelestialBody.MERCURY,
            CelestialBody.VENUS,
            CelestialBody.MARS,
            CelestialBody.JUPITER,
            CelestialBody.SATURN,
            CelestialBody.URANUS,
            CelestialBody.NEPTUNE,
        ]

        visible = []
        for planet in planets:
            pos = self.get_body_altaz(planet, when)
            if pos.altitude_degrees >= min_altitude:
                visible.append((planet, pos))

        # Sort by altitude (highest first)
        visible.sort(key=lambda x: x[1].altitude_degrees, reverse=True)
        return visible

    def get_best_planet_tonight(
        self,
        when: Optional[datetime] = None
    ) -> Optional[Tuple[CelestialBody, HorizontalPosition]]:
        """
        Get the best planet for observation tonight.

        Prioritizes Mars for NIGHTWATCH planetary focus.

        Returns:
            Tuple of (body, position) or None
        """
        visible = self.get_visible_planets(when)

        if not visible:
            return None

        # Priority order for NIGHTWATCH (planetary focus)
        priority = [
            CelestialBody.MARS,
            CelestialBody.JUPITER,
            CelestialBody.SATURN,
            CelestialBody.VENUS,
            CelestialBody.MERCURY,
            CelestialBody.URANUS,
            CelestialBody.NEPTUNE,
        ]

        for planet in priority:
            for body, pos in visible:
                if body == planet:
                    return (body, pos)

        return visible[0]  # Fallback to highest

    def j2000_to_jnow(
        self,
        ra_hours: float,
        dec_degrees: float,
        when: Optional[datetime] = None
    ) -> Tuple[float, float]:
        """
        Convert J2000 coordinates to JNow (current epoch).

        Applies precession, nutation, and aberration corrections.

        Args:
            ra_hours: J2000 Right Ascension in hours
            dec_degrees: J2000 Declination in degrees
            when: Target time (default: now)

        Returns:
            Tuple of (ra_hours, dec_degrees) in JNow
        """
        self._ensure_initialized()
        t = self._get_time(when)

        star = Star(ra_hours=ra_hours, dec_degrees=dec_degrees)
        astrometric = self._observer.at(t).observe(star)
        apparent = astrometric.apparent()

        ra, dec, _ = apparent.radec(epoch=t)
        return (ra.hours, dec.degrees)

    def jnow_to_j2000(
        self,
        ra_hours: float,
        dec_degrees: float,
        when: Optional[datetime] = None
    ) -> Tuple[float, float]:
        """
        Convert JNow coordinates to J2000.

        This is an approximation using reverse precession.

        Args:
            ra_hours: JNow Right Ascension in hours
            dec_degrees: JNow Declination in degrees
            when: Source time (default: now)

        Returns:
            Tuple of (ra_hours, dec_degrees) in J2000
        """
        self._ensure_initialized()
        t = self._get_time(when)

        # This is approximate - proper inversion is complex
        # For most telescope work, the difference is small
        star = Star(ra_hours=ra_hours, dec_degrees=dec_degrees, epoch=t)
        astrometric = self._observer.at(t).observe(star)

        ra, dec, _ = astrometric.radec(epoch='J2000')
        return (ra.hours, dec.degrees)

    def format_planet_info(self, body: CelestialBody, when: Optional[datetime] = None) -> str:
        """
        Get formatted info string for voice output.

        Args:
            body: Planet to describe
            when: Time for calculation

        Returns:
            Human-readable description
        """
        pos = self.get_body_position(body, when)
        altaz = self.get_body_altaz(body, when)

        name = body.value.capitalize()

        if altaz.is_visible:
            return (
                f"{name} is currently at {altaz.altitude_degrees:.1f} degrees altitude, "
                f"in the {altaz.compass_direction}. "
                f"Right Ascension {pos.ra_hms}, Declination {pos.dec_dms}."
            )
        else:
            return f"{name} is currently below the horizon at {altaz.altitude_degrees:.1f} degrees."


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_default_service: Optional[EphemerisService] = None


def get_service(location: Optional[ObserverLocation] = None) -> EphemerisService:
    """Get or create default ephemeris service."""
    global _default_service
    if _default_service is None:
        _default_service = EphemerisService(location)
        _default_service.initialize()
    return _default_service


def planet_position(body: str) -> Optional[Position]:
    """Quick lookup of planet position by name."""
    try:
        body_enum = CelestialBody(body.lower())
        return get_service().get_body_position(body_enum)
    except (ValueError, KeyError):
        return None


def is_dark() -> bool:
    """Check if it's astronomical night."""
    return get_service().is_astronomical_night()


def sun_altitude() -> float:
    """Get current sun altitude."""
    return get_service().get_sun_altitude()


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    print("NIGHTWATCH Ephemeris Service Test\n")

    if not SKYFIELD_AVAILABLE:
        print("Skyfield not installed. Install with: pip install skyfield")
        exit(1)

    service = EphemerisService()
    print("Initializing (may download ephemeris data)...")
    service.initialize()
    print(f"Location: {service.location.name}")
    print(f"  Lat: {service.location.latitude}°, Lon: {service.location.longitude}°")
    print()

    # Current conditions
    twilight = service.get_twilight_phase()
    sun_alt = service.get_sun_altitude()
    moon_phase = service.get_moon_phase()

    print(f"Current Conditions:")
    print(f"  Twilight: {twilight.value}")
    print(f"  Sun altitude: {sun_alt:.1f}°")
    print(f"  Moon phase: {moon_phase*100:.0f}% illuminated")
    print()

    # Planet positions
    print("Planet Positions:")
    for body in [CelestialBody.MARS, CelestialBody.JUPITER, CelestialBody.SATURN]:
        pos = service.get_body_position(body)
        altaz = service.get_body_altaz(body)
        status = "visible" if altaz.is_visible else "below horizon"
        print(f"  {body.value.capitalize():10} RA {pos.ra_hms}  DEC {pos.dec_dms}  Alt {altaz.altitude_degrees:+6.1f}° ({status})")

    print()

    # Visible planets
    visible = service.get_visible_planets()
    if visible:
        print("Visible Planets (>10° altitude):")
        for body, pos in visible:
            print(f"  {body.value.capitalize()}: {pos.altitude_degrees:.1f}° alt, {pos.compass_direction}")
    else:
        print("No planets currently visible above 10°")

    print()

    # Best planet
    best = service.get_best_planet_tonight()
    if best:
        body, pos = best
        print(f"Best planet for tonight: {body.value.capitalize()}")
        print(service.format_planet_info(body))
