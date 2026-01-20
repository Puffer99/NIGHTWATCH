"""
NIGHTWATCH Object Identifier

Offline celestial object identification (Step 136).

This module provides:
- Coordinate-based object identification from plate solving results
- Star pattern matching for constellation identification
- Brightness and size characteristic matching
- Field-of-view object enumeration
- Object classification from visual characteristics
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import math


# =============================================================================
# Enums and Constants
# =============================================================================


class IdentificationMethod(Enum):
    """Method used to identify an object."""

    COORDINATE_MATCH = "coordinate_match"      # Matched by RA/Dec
    PATTERN_MATCH = "pattern_match"            # Matched star pattern
    BRIGHTNESS_MATCH = "brightness_match"      # Matched by magnitude
    CHARACTERISTIC_MATCH = "characteristic_match"  # Matched by size/type
    FIELD_SEARCH = "field_search"              # Found in field of view


class ConfidenceLevel(Enum):
    """Confidence level of identification."""

    CERTAIN = "certain"      # >95% confidence
    HIGH = "high"            # 80-95% confidence
    MEDIUM = "medium"        # 60-80% confidence
    LOW = "low"              # 40-60% confidence
    UNCERTAIN = "uncertain"  # <40% confidence


# Object type characteristics for matching
OBJECT_CHARACTERISTICS = {
    "galaxy": {
        "typical_size_arcmin": (1.0, 180.0),
        "typical_magnitude": (6.0, 14.0),
        "extended": True,
        "description": "fuzzy, extended object",
    },
    "nebula": {
        "typical_size_arcmin": (1.0, 300.0),
        "typical_magnitude": (4.0, 12.0),
        "extended": True,
        "description": "diffuse, often colorful cloud",
    },
    "planetary_nebula": {
        "typical_size_arcmin": (0.1, 15.0),
        "typical_magnitude": (7.0, 14.0),
        "extended": True,
        "description": "small, often circular nebula",
    },
    "open_cluster": {
        "typical_size_arcmin": (2.0, 120.0),
        "typical_magnitude": (1.0, 10.0),
        "extended": True,
        "description": "group of scattered stars",
    },
    "globular_cluster": {
        "typical_size_arcmin": (1.0, 30.0),
        "typical_magnitude": (4.0, 10.0),
        "extended": True,
        "description": "dense ball of stars",
    },
    "star": {
        "typical_size_arcmin": (0.0, 0.1),
        "typical_magnitude": (-1.5, 6.0),
        "extended": False,
        "description": "point source",
    },
    "double_star": {
        "typical_size_arcmin": (0.0, 1.0),
        "typical_magnitude": (0.0, 8.0),
        "extended": False,
        "description": "two close point sources",
    },
}

# Common asterisms for pattern matching
ASTERISM_PATTERNS = {
    "orion_belt": {
        "stars": ["Alnitak", "Alnilam", "Mintaka"],
        "constellation": "Orion",
        "description": "Three stars in a row",
        "angular_size_deg": 2.7,
    },
    "big_dipper": {
        "stars": ["Alkaid", "Mizar", "Alioth", "Megrez", "Phecda", "Merak", "Dubhe"],
        "constellation": "Ursa Major",
        "description": "Seven stars forming a ladle shape",
        "angular_size_deg": 25.0,
    },
    "summer_triangle": {
        "stars": ["Vega", "Deneb", "Altair"],
        "constellation": None,  # Spans multiple
        "description": "Large triangle of bright stars",
        "angular_size_deg": 35.0,
    },
    "cassiopeia_w": {
        "stars": ["Schedar", "Caph", "Gamma Cas", "Ruchbah", "Segin"],
        "constellation": "Cassiopeia",
        "description": "W-shaped pattern",
        "angular_size_deg": 13.0,
    },
    "southern_cross": {
        "stars": ["Acrux", "Mimosa", "Gacrux", "Imai"],
        "constellation": "Crux",
        "description": "Cross-shaped pattern",
        "angular_size_deg": 6.0,
    },
    "pleiades": {
        "stars": ["Alcyone", "Atlas", "Electra", "Maia", "Merope", "Taygeta", "Pleione"],
        "constellation": "Taurus",
        "description": "Tight cluster of blue stars",
        "angular_size_deg": 2.0,
    },
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ObjectMatch:
    """A matched celestial object."""

    object_id: str  # e.g., "M31", "NGC 7000"
    object_name: Optional[str]  # e.g., "Andromeda Galaxy"
    object_type: str  # galaxy, nebula, cluster, etc.
    confidence: float  # 0.0 to 1.0
    confidence_level: ConfidenceLevel
    method: IdentificationMethod
    separation_arcmin: Optional[float] = None  # Distance from search center
    magnitude: Optional[float] = None
    size_arcmin: Optional[float] = None
    constellation: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "object_id": self.object_id,
            "object_name": self.object_name,
            "object_type": self.object_type,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level.value,
            "method": self.method.value,
            "separation_arcmin": self.separation_arcmin,
            "magnitude": self.magnitude,
            "size_arcmin": self.size_arcmin,
            "constellation": self.constellation,
            "notes": self.notes,
        }


@dataclass
class FieldOfView:
    """Describes a field of view for object search."""

    center_ra_hours: float  # Center RA in decimal hours
    center_dec_degrees: float  # Center Dec in degrees
    width_arcmin: float  # FOV width in arcminutes
    height_arcmin: float  # FOV height in arcminutes
    rotation_degrees: float = 0.0  # Field rotation

    @property
    def radius_arcmin(self) -> float:
        """Get radius that encompasses the full FOV."""
        return math.sqrt(self.width_arcmin**2 + self.height_arcmin**2) / 2


@dataclass
class IdentificationResult:
    """Result of object identification."""

    matches: list[ObjectMatch] = field(default_factory=list)
    field_of_view: Optional[FieldOfView] = None
    search_radius_arcmin: Optional[float] = None
    total_candidates: int = 0
    identification_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def best_match(self) -> Optional[ObjectMatch]:
        """Get the highest confidence match."""
        if not self.matches:
            return None
        return max(self.matches, key=lambda m: m.confidence)

    @property
    def certain_matches(self) -> list[ObjectMatch]:
        """Get matches with certain confidence."""
        return [m for m in self.matches if m.confidence_level == ConfidenceLevel.CERTAIN]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "matches": [m.to_dict() for m in self.matches],
            "total_candidates": self.total_candidates,
            "identification_time_ms": self.identification_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class PatternMatch:
    """Result of asterism/pattern matching."""

    pattern_name: str
    constellation: Optional[str]
    matched_stars: list[str]
    confidence: float
    description: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "pattern_name": self.pattern_name,
            "constellation": self.constellation,
            "matched_stars": self.matched_stars,
            "confidence": self.confidence,
            "description": self.description,
        }


# =============================================================================
# Object Identifier
# =============================================================================


class ObjectIdentifier:
    """
    Identifies celestial objects offline using various methods.

    Features:
    - Coordinate-based identification from plate solving
    - Star pattern/asterism matching
    - Object characteristic matching (size, brightness)
    - Field of view enumeration
    - Constellation identification
    """

    # Built-in catalog of notable objects for offline identification
    # In production, this would load from the catalog database
    NOTABLE_OBJECTS = {
        # Messier objects with coordinates (J2000)
        "M1": {"name": "Crab Nebula", "ra": 5.575, "dec": 22.017, "type": "supernova_remnant", "mag": 8.4, "size": 6.0, "con": "Taurus"},
        "M13": {"name": "Hercules Cluster", "ra": 16.695, "dec": 36.467, "type": "globular_cluster", "mag": 5.8, "size": 20.0, "con": "Hercules"},
        "M27": {"name": "Dumbbell Nebula", "ra": 19.994, "dec": 22.722, "type": "planetary_nebula", "mag": 7.5, "size": 8.0, "con": "Vulpecula"},
        "M31": {"name": "Andromeda Galaxy", "ra": 0.712, "dec": 41.269, "type": "galaxy", "mag": 3.4, "size": 178.0, "con": "Andromeda"},
        "M33": {"name": "Triangulum Galaxy", "ra": 1.564, "dec": 30.660, "type": "galaxy", "mag": 5.7, "size": 73.0, "con": "Triangulum"},
        "M42": {"name": "Orion Nebula", "ra": 5.588, "dec": -5.391, "type": "nebula", "mag": 4.0, "size": 85.0, "con": "Orion"},
        "M45": {"name": "Pleiades", "ra": 3.791, "dec": 24.117, "type": "open_cluster", "mag": 1.6, "size": 110.0, "con": "Taurus"},
        "M51": {"name": "Whirlpool Galaxy", "ra": 13.498, "dec": 47.195, "type": "galaxy", "mag": 8.4, "size": 11.0, "con": "Canes Venatici"},
        "M57": {"name": "Ring Nebula", "ra": 18.893, "dec": 33.029, "type": "planetary_nebula", "mag": 8.8, "size": 1.4, "con": "Lyra"},
        "M81": {"name": "Bode's Galaxy", "ra": 9.926, "dec": 69.065, "type": "galaxy", "mag": 6.9, "size": 27.0, "con": "Ursa Major"},
        "M82": {"name": "Cigar Galaxy", "ra": 9.931, "dec": 69.680, "type": "galaxy", "mag": 8.4, "size": 11.0, "con": "Ursa Major"},
        "M101": {"name": "Pinwheel Galaxy", "ra": 14.053, "dec": 54.349, "type": "galaxy", "mag": 7.9, "size": 29.0, "con": "Ursa Major"},
        "M104": {"name": "Sombrero Galaxy", "ra": 12.666, "dec": -11.622, "type": "galaxy", "mag": 8.0, "size": 9.0, "con": "Virgo"},
        # NGC objects
        "NGC 7000": {"name": "North America Nebula", "ra": 20.987, "dec": 44.333, "type": "nebula", "mag": 4.0, "size": 120.0, "con": "Cygnus"},
        "NGC 6992": {"name": "Eastern Veil Nebula", "ra": 20.941, "dec": 31.717, "type": "supernova_remnant", "mag": 7.0, "size": 60.0, "con": "Cygnus"},
        "NGC 869": {"name": "Double Cluster (h)", "ra": 2.320, "dec": 57.133, "type": "open_cluster", "mag": 4.3, "size": 30.0, "con": "Perseus"},
        "NGC 884": {"name": "Double Cluster (χ)", "ra": 2.374, "dec": 57.150, "type": "open_cluster", "mag": 4.4, "size": 30.0, "con": "Perseus"},
        "NGC 2237": {"name": "Rosette Nebula", "ra": 6.527, "dec": 4.950, "type": "nebula", "mag": 9.0, "size": 80.0, "con": "Monoceros"},
        # Notable stars
        "Polaris": {"name": "North Star", "ra": 2.530, "dec": 89.264, "type": "star", "mag": 2.0, "size": 0.0, "con": "Ursa Minor"},
        "Vega": {"name": "Alpha Lyrae", "ra": 18.616, "dec": 38.784, "type": "star", "mag": 0.0, "size": 0.0, "con": "Lyra"},
        "Sirius": {"name": "Dog Star", "ra": 6.752, "dec": -16.716, "type": "star", "mag": -1.46, "size": 0.0, "con": "Canis Major"},
        "Betelgeuse": {"name": "Alpha Orionis", "ra": 5.919, "dec": 7.407, "type": "star", "mag": 0.5, "size": 0.0, "con": "Orion"},
        "Rigel": {"name": "Beta Orionis", "ra": 5.242, "dec": -8.202, "type": "star", "mag": 0.13, "size": 0.0, "con": "Orion"},
    }

    def __init__(
        self,
        default_search_radius_arcmin: float = 30.0,
        min_confidence: float = 0.4,
    ):
        """
        Initialize object identifier.

        Args:
            default_search_radius_arcmin: Default search radius
            min_confidence: Minimum confidence to include in results
        """
        self.default_search_radius = default_search_radius_arcmin
        self.min_confidence = min_confidence

    def identify_at_coordinates(
        self,
        ra_hours: float,
        dec_degrees: float,
        search_radius_arcmin: Optional[float] = None,
        magnitude_limit: Optional[float] = None,
    ) -> IdentificationResult:
        """
        Identify objects at given coordinates.

        Args:
            ra_hours: Right Ascension in decimal hours
            dec_degrees: Declination in degrees
            search_radius_arcmin: Search radius in arcminutes
            magnitude_limit: Only include objects brighter than this

        Returns:
            IdentificationResult with matched objects
        """
        import time
        start_time = time.time()

        radius = search_radius_arcmin or self.default_search_radius
        matches = []
        total_candidates = 0

        for obj_id, obj_data in self.NOTABLE_OBJECTS.items():
            total_candidates += 1

            # Check magnitude limit
            if magnitude_limit and obj_data["mag"] > magnitude_limit:
                continue

            # Calculate angular separation
            separation = self._angular_separation(
                ra_hours, dec_degrees,
                obj_data["ra"], obj_data["dec"]
            )
            separation_arcmin = separation * 60  # Convert degrees to arcmin

            # Check if within search radius
            if separation_arcmin <= radius:
                # Calculate confidence based on separation
                confidence = self._calculate_coordinate_confidence(
                    separation_arcmin, radius
                )

                if confidence >= self.min_confidence:
                    match = ObjectMatch(
                        object_id=obj_id,
                        object_name=obj_data["name"],
                        object_type=obj_data["type"],
                        confidence=confidence,
                        confidence_level=self._confidence_to_level(confidence),
                        method=IdentificationMethod.COORDINATE_MATCH,
                        separation_arcmin=separation_arcmin,
                        magnitude=obj_data["mag"],
                        size_arcmin=obj_data["size"],
                        constellation=obj_data["con"],
                    )
                    matches.append(match)

        # Sort by confidence (highest first)
        matches.sort(key=lambda m: m.confidence, reverse=True)

        elapsed_ms = (time.time() - start_time) * 1000

        return IdentificationResult(
            matches=matches,
            search_radius_arcmin=radius,
            total_candidates=total_candidates,
            identification_time_ms=elapsed_ms,
        )

    def identify_in_field(
        self,
        fov: FieldOfView,
        magnitude_limit: Optional[float] = None,
    ) -> IdentificationResult:
        """
        Identify all objects within a field of view.

        Args:
            fov: Field of view specification
            magnitude_limit: Only include objects brighter than this

        Returns:
            IdentificationResult with all objects in FOV
        """
        result = self.identify_at_coordinates(
            fov.center_ra_hours,
            fov.center_dec_degrees,
            fov.radius_arcmin,
            magnitude_limit,
        )
        result.field_of_view = fov
        return result

    def identify_by_characteristics(
        self,
        object_type: Optional[str] = None,
        magnitude: Optional[float] = None,
        size_arcmin: Optional[float] = None,
        constellation: Optional[str] = None,
    ) -> IdentificationResult:
        """
        Identify objects matching visual characteristics.

        Args:
            object_type: Type of object (galaxy, nebula, etc.)
            magnitude: Approximate magnitude
            size_arcmin: Approximate angular size
            constellation: Constellation to search in

        Returns:
            IdentificationResult with matching objects
        """
        import time
        start_time = time.time()

        matches = []
        total_candidates = 0

        for obj_id, obj_data in self.NOTABLE_OBJECTS.items():
            total_candidates += 1
            confidence = 1.0

            # Type matching
            if object_type:
                if obj_data["type"] != object_type:
                    continue

            # Constellation matching
            if constellation:
                if obj_data["con"].lower() != constellation.lower():
                    confidence *= 0.5

            # Magnitude matching (within 2 magnitudes)
            if magnitude is not None:
                mag_diff = abs(obj_data["mag"] - magnitude)
                if mag_diff > 3:
                    continue
                confidence *= max(0.5, 1.0 - mag_diff / 4)

            # Size matching (within factor of 3)
            if size_arcmin is not None and obj_data["size"] > 0:
                size_ratio = max(size_arcmin, obj_data["size"]) / max(0.1, min(size_arcmin, obj_data["size"]))
                if size_ratio > 5:
                    continue
                confidence *= max(0.5, 1.0 - (size_ratio - 1) / 5)

            if confidence >= self.min_confidence:
                match = ObjectMatch(
                    object_id=obj_id,
                    object_name=obj_data["name"],
                    object_type=obj_data["type"],
                    confidence=confidence,
                    confidence_level=self._confidence_to_level(confidence),
                    method=IdentificationMethod.CHARACTERISTIC_MATCH,
                    magnitude=obj_data["mag"],
                    size_arcmin=obj_data["size"],
                    constellation=obj_data["con"],
                )
                matches.append(match)

        matches.sort(key=lambda m: m.confidence, reverse=True)
        elapsed_ms = (time.time() - start_time) * 1000

        return IdentificationResult(
            matches=matches,
            total_candidates=total_candidates,
            identification_time_ms=elapsed_ms,
        )

    def match_pattern(
        self,
        star_names: list[str],
    ) -> list[PatternMatch]:
        """
        Match a list of star names against known asterism patterns.

        Args:
            star_names: List of identified star names

        Returns:
            List of matched patterns with confidence
        """
        matches = []
        star_names_lower = [s.lower() for s in star_names]

        for pattern_name, pattern_data in ASTERISM_PATTERNS.items():
            pattern_stars = [s.lower() for s in pattern_data["stars"]]

            # Count matching stars
            matched = [s for s in pattern_stars if s in star_names_lower]
            match_ratio = len(matched) / len(pattern_stars)

            if match_ratio >= 0.5:  # At least half the stars matched
                matches.append(PatternMatch(
                    pattern_name=pattern_name,
                    constellation=pattern_data["constellation"],
                    matched_stars=matched,
                    confidence=match_ratio,
                    description=pattern_data["description"],
                ))

        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches

    def identify_constellation(
        self,
        ra_hours: float,
        dec_degrees: float,
    ) -> Optional[str]:
        """
        Identify which constellation contains the given coordinates.

        Args:
            ra_hours: Right Ascension in decimal hours
            dec_degrees: Declination in degrees

        Returns:
            Constellation name or None
        """
        # Find nearest notable object and use its constellation
        # In production, would use proper constellation boundary data
        result = self.identify_at_coordinates(
            ra_hours, dec_degrees,
            search_radius_arcmin=300,  # 5 degrees
        )

        if result.matches:
            return result.matches[0].constellation

        return None

    def get_object_info(self, object_id: str) -> Optional[ObjectMatch]:
        """
        Get information about a specific object by ID.

        Args:
            object_id: Object identifier (e.g., "M31", "NGC 7000")

        Returns:
            ObjectMatch with object information or None
        """
        obj_data = self.NOTABLE_OBJECTS.get(object_id)
        if not obj_data:
            # Try case-insensitive search
            for oid, data in self.NOTABLE_OBJECTS.items():
                if oid.lower() == object_id.lower():
                    obj_data = data
                    object_id = oid
                    break

        if not obj_data:
            return None

        return ObjectMatch(
            object_id=object_id,
            object_name=obj_data["name"],
            object_type=obj_data["type"],
            confidence=1.0,
            confidence_level=ConfidenceLevel.CERTAIN,
            method=IdentificationMethod.COORDINATE_MATCH,
            magnitude=obj_data["mag"],
            size_arcmin=obj_data["size"],
            constellation=obj_data["con"],
        )

    def get_object_description(self, object_id: str) -> Optional[str]:
        """
        Get a natural language description of an object.

        Args:
            object_id: Object identifier

        Returns:
            Description string or None
        """
        match = self.get_object_info(object_id)
        if not match:
            return None

        characteristics = OBJECT_CHARACTERISTICS.get(
            match.object_type,
            {"description": "celestial object"}
        )

        parts = []

        # Name and type
        if match.object_name:
            parts.append(f"{match.object_id}, also known as {match.object_name}")
        else:
            parts.append(match.object_id)

        parts.append(f"is a {match.object_type.replace('_', ' ')}")

        # Location
        if match.constellation:
            parts.append(f"in {match.constellation}")

        # Brightness
        if match.magnitude is not None:
            if match.magnitude <= 4:
                parts.append("visible to the naked eye")
            elif match.magnitude <= 6:
                parts.append("visible with binoculars")
            else:
                parts.append("requiring a telescope")

        # Size
        if match.size_arcmin and match.size_arcmin > 10:
            parts.append(f"spanning {match.size_arcmin:.0f} arcminutes")

        return ", ".join(parts) + "."

    def suggest_nearby_objects(
        self,
        ra_hours: float,
        dec_degrees: float,
        limit: int = 5,
    ) -> list[ObjectMatch]:
        """
        Suggest interesting objects near given coordinates.

        Args:
            ra_hours: Center RA
            dec_degrees: Center Dec
            limit: Maximum suggestions

        Returns:
            List of nearby objects sorted by interest/brightness
        """
        result = self.identify_at_coordinates(
            ra_hours, dec_degrees,
            search_radius_arcmin=600,  # 10 degrees
        )

        # Sort by magnitude (brightest first) then distance
        sorted_matches = sorted(
            result.matches,
            key=lambda m: (m.magnitude or 15, m.separation_arcmin or 1000),
        )

        return sorted_matches[:limit]

    def _angular_separation(
        self,
        ra1_hours: float,
        dec1_deg: float,
        ra2_hours: float,
        dec2_deg: float,
    ) -> float:
        """Calculate angular separation in degrees between two points."""
        # Convert to radians
        ra1 = math.radians(ra1_hours * 15)  # hours to degrees to radians
        ra2 = math.radians(ra2_hours * 15)
        dec1 = math.radians(dec1_deg)
        dec2 = math.radians(dec2_deg)

        # Haversine formula
        dra = ra2 - ra1
        ddec = dec2 - dec1

        a = math.sin(ddec/2)**2 + math.cos(dec1) * math.cos(dec2) * math.sin(dra/2)**2
        c = 2 * math.asin(math.sqrt(a))

        return math.degrees(c)

    def _calculate_coordinate_confidence(
        self,
        separation_arcmin: float,
        search_radius: float,
    ) -> float:
        """Calculate confidence based on separation distance."""
        if separation_arcmin < 1:
            return 1.0  # Very close match
        elif separation_arcmin < 5:
            return 0.95
        elif separation_arcmin < 15:
            return 0.85
        else:
            # Linear decay
            return max(0.4, 1.0 - (separation_arcmin / search_radius))

    def _confidence_to_level(self, confidence: float) -> ConfidenceLevel:
        """Convert numeric confidence to level."""
        if confidence >= 0.95:
            return ConfidenceLevel.CERTAIN
        elif confidence >= 0.80:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.60:
            return ConfidenceLevel.MEDIUM
        elif confidence >= 0.40:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.UNCERTAIN


# =============================================================================
# Module-level singleton
# =============================================================================

_identifier: Optional[ObjectIdentifier] = None


def get_object_identifier() -> ObjectIdentifier:
    """Get the global object identifier instance."""
    global _identifier
    if _identifier is None:
        _identifier = ObjectIdentifier()
    return _identifier
