"""
NIGHTWATCH Object Identifier Tests

Tests for offline celestial object identification (Step 136).
"""

import pytest
import math

from services.catalog.object_identifier import (
    ObjectIdentifier,
    IdentificationMethod,
    ConfidenceLevel,
    ObjectMatch,
    FieldOfView,
    IdentificationResult,
    PatternMatch,
    get_object_identifier,
    ASTERISM_PATTERNS,
    OBJECT_CHARACTERISTICS,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def identifier():
    """Create an ObjectIdentifier."""
    return ObjectIdentifier()


@pytest.fixture
def m31_coordinates():
    """Coordinates of M31 (Andromeda Galaxy)."""
    return {"ra": 0.712, "dec": 41.269}


@pytest.fixture
def orion_nebula_coordinates():
    """Coordinates of M42 (Orion Nebula)."""
    return {"ra": 5.588, "dec": -5.391}


# =============================================================================
# ObjectMatch Tests
# =============================================================================


class TestObjectMatch:
    """Tests for ObjectMatch dataclass."""

    def test_match_creation(self):
        """Create a basic object match."""
        match = ObjectMatch(
            object_id="M31",
            object_name="Andromeda Galaxy",
            object_type="galaxy",
            confidence=0.95,
            confidence_level=ConfidenceLevel.CERTAIN,
            method=IdentificationMethod.COORDINATE_MATCH,
        )
        assert match.object_id == "M31"
        assert match.confidence == 0.95

    def test_match_with_details(self):
        """Create match with full details."""
        match = ObjectMatch(
            object_id="M42",
            object_name="Orion Nebula",
            object_type="nebula",
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
            method=IdentificationMethod.COORDINATE_MATCH,
            separation_arcmin=2.5,
            magnitude=4.0,
            size_arcmin=85.0,
            constellation="Orion",
        )
        assert match.separation_arcmin == 2.5
        assert match.constellation == "Orion"

    def test_match_to_dict(self):
        """Match converts to dict."""
        match = ObjectMatch(
            object_id="M31",
            object_name="Andromeda Galaxy",
            object_type="galaxy",
            confidence=0.95,
            confidence_level=ConfidenceLevel.CERTAIN,
            method=IdentificationMethod.COORDINATE_MATCH,
        )
        d = match.to_dict()
        assert d["object_id"] == "M31"
        assert d["confidence_level"] == "certain"
        assert d["method"] == "coordinate_match"


# =============================================================================
# FieldOfView Tests
# =============================================================================


class TestFieldOfView:
    """Tests for FieldOfView dataclass."""

    def test_fov_creation(self):
        """Create a field of view."""
        fov = FieldOfView(
            center_ra_hours=10.0,
            center_dec_degrees=45.0,
            width_arcmin=60.0,
            height_arcmin=40.0,
        )
        assert fov.center_ra_hours == 10.0
        assert fov.width_arcmin == 60.0

    def test_fov_radius(self):
        """FOV radius calculation."""
        fov = FieldOfView(
            center_ra_hours=10.0,
            center_dec_degrees=45.0,
            width_arcmin=60.0,
            height_arcmin=40.0,
        )
        # Radius should be diagonal/2
        expected = math.sqrt(60**2 + 40**2) / 2
        assert abs(fov.radius_arcmin - expected) < 0.1


# =============================================================================
# IdentificationResult Tests
# =============================================================================


class TestIdentificationResult:
    """Tests for IdentificationResult dataclass."""

    def test_result_creation(self):
        """Create identification result."""
        result = IdentificationResult()
        assert len(result.matches) == 0
        assert result.total_candidates == 0

    def test_best_match(self):
        """Get best match from results."""
        matches = [
            ObjectMatch("M31", None, "galaxy", 0.8, ConfidenceLevel.HIGH, IdentificationMethod.COORDINATE_MATCH),
            ObjectMatch("M33", None, "galaxy", 0.95, ConfidenceLevel.CERTAIN, IdentificationMethod.COORDINATE_MATCH),
            ObjectMatch("NGC 224", None, "galaxy", 0.7, ConfidenceLevel.MEDIUM, IdentificationMethod.COORDINATE_MATCH),
        ]
        result = IdentificationResult(matches=matches)

        best = result.best_match
        assert best.object_id == "M33"  # Highest confidence

    def test_certain_matches(self):
        """Get only certain matches."""
        matches = [
            ObjectMatch("M31", None, "galaxy", 0.98, ConfidenceLevel.CERTAIN, IdentificationMethod.COORDINATE_MATCH),
            ObjectMatch("M33", None, "galaxy", 0.7, ConfidenceLevel.MEDIUM, IdentificationMethod.COORDINATE_MATCH),
        ]
        result = IdentificationResult(matches=matches)

        certain = result.certain_matches
        assert len(certain) == 1
        assert certain[0].object_id == "M31"

    def test_result_to_dict(self):
        """Result converts to dict."""
        result = IdentificationResult(
            total_candidates=100,
            identification_time_ms=5.5,
        )
        d = result.to_dict()
        assert d["total_candidates"] == 100
        assert d["identification_time_ms"] == 5.5


# =============================================================================
# Coordinate Identification Tests
# =============================================================================


class TestCoordinateIdentification:
    """Tests for coordinate-based identification."""

    def test_identify_m31(self, identifier, m31_coordinates):
        """Identify M31 at its coordinates."""
        result = identifier.identify_at_coordinates(
            m31_coordinates["ra"],
            m31_coordinates["dec"],
            search_radius_arcmin=10,
        )

        assert len(result.matches) > 0
        best = result.best_match
        assert best.object_id == "M31"
        assert best.confidence >= 0.9

    def test_identify_m42(self, identifier, orion_nebula_coordinates):
        """Identify M42 at its coordinates."""
        result = identifier.identify_at_coordinates(
            orion_nebula_coordinates["ra"],
            orion_nebula_coordinates["dec"],
            search_radius_arcmin=10,
        )

        assert len(result.matches) > 0
        best = result.best_match
        assert best.object_id == "M42"

    def test_search_radius_affects_results(self, identifier, m31_coordinates):
        """Larger search radius finds more objects."""
        small_result = identifier.identify_at_coordinates(
            m31_coordinates["ra"],
            m31_coordinates["dec"],
            search_radius_arcmin=5,
        )

        large_result = identifier.identify_at_coordinates(
            m31_coordinates["ra"],
            m31_coordinates["dec"],
            search_radius_arcmin=600,  # 10 degrees
        )

        assert len(large_result.matches) >= len(small_result.matches)

    def test_magnitude_limit(self, identifier, m31_coordinates):
        """Magnitude limit filters results."""
        result = identifier.identify_at_coordinates(
            m31_coordinates["ra"],
            m31_coordinates["dec"],
            search_radius_arcmin=600,
            magnitude_limit=5.0,
        )

        # All matches should be brighter than limit
        for match in result.matches:
            assert match.magnitude <= 5.0

    def test_empty_region(self, identifier):
        """Handle region with no known objects."""
        result = identifier.identify_at_coordinates(
            12.0,  # RA in hours
            -80.0,  # Dec in degrees (far south)
            search_radius_arcmin=10,
        )

        # May or may not have matches, but should not error
        assert result is not None


# =============================================================================
# Field of View Tests
# =============================================================================


class TestFieldOfViewIdentification:
    """Tests for field of view identification."""

    def test_identify_in_field(self, identifier):
        """Identify objects in a field of view."""
        fov = FieldOfView(
            center_ra_hours=0.712,  # M31 area
            center_dec_degrees=41.269,
            width_arcmin=120,
            height_arcmin=80,
        )

        result = identifier.identify_in_field(fov)

        assert result.field_of_view is not None
        assert len(result.matches) > 0

    def test_fov_includes_nearby_objects(self, identifier):
        """FOV search finds nearby objects."""
        # M81/M82 area
        fov = FieldOfView(
            center_ra_hours=9.928,
            center_dec_degrees=69.4,
            width_arcmin=120,
            height_arcmin=120,
        )

        result = identifier.identify_in_field(fov)

        object_ids = [m.object_id for m in result.matches]
        # Both M81 and M82 should be found
        assert "M81" in object_ids or "M82" in object_ids


# =============================================================================
# Characteristic Matching Tests
# =============================================================================


class TestCharacteristicMatching:
    """Tests for characteristic-based identification."""

    def test_match_by_type(self, identifier):
        """Match objects by type."""
        result = identifier.identify_by_characteristics(
            object_type="galaxy",
        )

        assert len(result.matches) > 0
        for match in result.matches:
            assert match.object_type == "galaxy"

    def test_match_by_constellation(self, identifier):
        """Match objects by constellation."""
        result = identifier.identify_by_characteristics(
            constellation="Orion",
        )

        assert len(result.matches) > 0
        # Should find Orion objects
        orion_objects = [m for m in result.matches if m.constellation == "Orion"]
        assert len(orion_objects) > 0

    def test_match_by_magnitude(self, identifier):
        """Match objects by approximate magnitude."""
        result = identifier.identify_by_characteristics(
            magnitude=4.0,
        )

        assert len(result.matches) > 0
        # Matches should have similar magnitudes
        for match in result.matches:
            assert abs(match.magnitude - 4.0) <= 3

    def test_match_by_size(self, identifier):
        """Match objects by approximate size."""
        result = identifier.identify_by_characteristics(
            size_arcmin=100.0,  # Large object
        )

        assert len(result.matches) > 0

    def test_combined_characteristics(self, identifier):
        """Match by multiple characteristics."""
        result = identifier.identify_by_characteristics(
            object_type="nebula",
            constellation="Orion",
        )

        # Should find M42
        object_ids = [m.object_id for m in result.matches]
        assert "M42" in object_ids


# =============================================================================
# Pattern Matching Tests
# =============================================================================


class TestPatternMatching:
    """Tests for asterism/pattern matching."""

    def test_match_orion_belt(self, identifier):
        """Match Orion's Belt pattern."""
        matches = identifier.match_pattern(
            ["Alnitak", "Alnilam", "Mintaka"]
        )

        assert len(matches) > 0
        belt_match = next((m for m in matches if m.pattern_name == "orion_belt"), None)
        assert belt_match is not None
        assert belt_match.confidence == 1.0

    def test_partial_pattern_match(self, identifier):
        """Match with partial pattern."""
        # Only two of three stars
        matches = identifier.match_pattern(
            ["Alnitak", "Alnilam"]
        )

        belt_match = next((m for m in matches if m.pattern_name == "orion_belt"), None)
        assert belt_match is not None
        assert belt_match.confidence < 1.0  # Partial match

    def test_match_summer_triangle(self, identifier):
        """Match Summer Triangle pattern."""
        matches = identifier.match_pattern(
            ["Vega", "Deneb", "Altair"]
        )

        triangle = next((m for m in matches if m.pattern_name == "summer_triangle"), None)
        assert triangle is not None

    def test_no_pattern_match(self, identifier):
        """Handle no matching patterns."""
        matches = identifier.match_pattern(
            ["RandomStar1", "RandomStar2"]
        )

        assert len(matches) == 0


# =============================================================================
# Object Info Tests
# =============================================================================


class TestObjectInfo:
    """Tests for object information retrieval."""

    def test_get_object_info(self, identifier):
        """Get info for known object."""
        info = identifier.get_object_info("M31")

        assert info is not None
        assert info.object_id == "M31"
        assert info.object_name == "Andromeda Galaxy"
        assert info.constellation == "Andromeda"

    def test_get_object_info_case_insensitive(self, identifier):
        """Object lookup is case insensitive."""
        info = identifier.get_object_info("m42")

        assert info is not None
        assert info.object_id == "M42"

    def test_get_unknown_object(self, identifier):
        """Handle unknown object."""
        info = identifier.get_object_info("UNKNOWN123")

        assert info is None


# =============================================================================
# Description Tests
# =============================================================================


class TestObjectDescriptions:
    """Tests for object descriptions."""

    def test_get_description(self, identifier):
        """Get description for known object."""
        desc = identifier.get_object_description("M31")

        assert desc is not None
        assert "M31" in desc
        assert "Andromeda" in desc

    def test_description_includes_type(self, identifier):
        """Description includes object type."""
        desc = identifier.get_object_description("M42")

        assert "nebula" in desc.lower()

    def test_description_includes_visibility(self, identifier):
        """Description includes visibility info."""
        desc = identifier.get_object_description("M45")  # Pleiades, mag 1.6

        assert "naked eye" in desc.lower() or "visible" in desc.lower()

    def test_unknown_object_description(self, identifier):
        """Handle unknown object description."""
        desc = identifier.get_object_description("UNKNOWN")

        assert desc is None


# =============================================================================
# Suggestion Tests
# =============================================================================


class TestSuggestions:
    """Tests for nearby object suggestions."""

    def test_suggest_nearby(self, identifier, m31_coordinates):
        """Suggest nearby objects."""
        suggestions = identifier.suggest_nearby_objects(
            m31_coordinates["ra"],
            m31_coordinates["dec"],
            limit=5,
        )

        assert len(suggestions) > 0
        assert len(suggestions) <= 5

    def test_suggestions_sorted_by_brightness(self, identifier):
        """Suggestions favor brighter objects."""
        suggestions = identifier.suggest_nearby_objects(
            5.5,  # Orion area
            0.0,
            limit=5,
        )

        if len(suggestions) >= 2:
            # First should be brighter (lower magnitude) or closer
            assert suggestions[0].magnitude <= suggestions[-1].magnitude or \
                   suggestions[0].separation_arcmin <= suggestions[-1].separation_arcmin


# =============================================================================
# Constellation Tests
# =============================================================================


class TestConstellationIdentification:
    """Tests for constellation identification."""

    def test_identify_constellation(self, identifier, m31_coordinates):
        """Identify constellation from coordinates."""
        constellation = identifier.identify_constellation(
            m31_coordinates["ra"],
            m31_coordinates["dec"],
        )

        assert constellation == "Andromeda"

    def test_orion_constellation(self, identifier, orion_nebula_coordinates):
        """Identify Orion constellation."""
        constellation = identifier.identify_constellation(
            orion_nebula_coordinates["ra"],
            orion_nebula_coordinates["dec"],
        )

        assert constellation == "Orion"


# =============================================================================
# Confidence Level Tests
# =============================================================================


class TestConfidenceLevels:
    """Tests for confidence level handling."""

    def test_certain_confidence(self, identifier):
        """Very close match has certain confidence."""
        result = identifier.identify_at_coordinates(
            0.712,  # Exact M31 RA
            41.269,  # Exact M31 Dec
            search_radius_arcmin=5,
        )

        assert result.best_match.confidence_level == ConfidenceLevel.CERTAIN

    def test_confidence_decreases_with_distance(self, identifier):
        """Confidence decreases with separation."""
        # Offset from M31
        result = identifier.identify_at_coordinates(
            0.712 + 0.1,  # Slightly offset
            41.269 + 0.5,
            search_radius_arcmin=60,
        )

        m31_match = next((m for m in result.matches if m.object_id == "M31"), None)
        if m31_match:
            # Should have lower confidence due to offset
            assert m31_match.confidence < 1.0


# =============================================================================
# Enum Tests
# =============================================================================


class TestEnums:
    """Tests for enum values."""

    def test_identification_methods(self):
        """All identification methods defined."""
        assert IdentificationMethod.COORDINATE_MATCH.value == "coordinate_match"
        assert IdentificationMethod.PATTERN_MATCH.value == "pattern_match"
        assert IdentificationMethod.CHARACTERISTIC_MATCH.value == "characteristic_match"

    def test_confidence_levels(self):
        """All confidence levels defined."""
        assert ConfidenceLevel.CERTAIN.value == "certain"
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.LOW.value == "low"
        assert ConfidenceLevel.UNCERTAIN.value == "uncertain"


# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_asterism_patterns_exist(self):
        """Asterism patterns are defined."""
        assert "orion_belt" in ASTERISM_PATTERNS
        assert "big_dipper" in ASTERISM_PATTERNS
        assert "summer_triangle" in ASTERISM_PATTERNS

    def test_object_characteristics_exist(self):
        """Object characteristics are defined."""
        assert "galaxy" in OBJECT_CHARACTERISTICS
        assert "nebula" in OBJECT_CHARACTERISTICS
        assert "star" in OBJECT_CHARACTERISTICS


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunction:
    """Tests for module-level factory."""

    def test_get_object_identifier_returns_singleton(self):
        """get_object_identifier returns same instance."""
        i1 = get_object_identifier()
        i2 = get_object_identifier()
        assert i1 is i2

    def test_get_object_identifier_creates_instance(self):
        """get_object_identifier creates instance."""
        identifier = get_object_identifier()
        assert isinstance(identifier, ObjectIdentifier)
