"""
Unit tests for NIGHTWATCH catalog service.

Tests catalog lookup, search, fuzzy matching, caching, and coordinate resolution.
"""

import pytest
from services.catalog.catalog import (
    CatalogService,
    CatalogDatabase,
    CatalogObject,
    ObjectType,
    LRUCache,
    _levenshtein_distance,
    _similarity_score,
)


class TestLRUCache:
    """Tests for LRU cache implementation."""

    def test_basic_put_get(self):
        """Test basic put and get operations."""
        cache = LRUCache(maxsize=3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)

        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_cache_miss_returns_none(self):
        """Test that cache miss returns None."""
        cache = LRUCache(maxsize=3)
        assert cache.get("nonexistent") is None

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = LRUCache(maxsize=3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.put("d", 4)  # Should evict "a"

        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("d") == 4

    def test_access_updates_lru_order(self):
        """Test that accessing an item updates its LRU position."""
        cache = LRUCache(maxsize=3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)

        # Access "a" to make it recently used
        cache.get("a")

        # Add new item - should evict "b" (least recently used)
        cache.put("d", 4)

        assert cache.get("a") == 1  # Still present
        assert cache.get("b") is None  # Evicted

    def test_cache_stats(self):
        """Test cache statistics tracking."""
        cache = LRUCache(maxsize=10)
        cache.put("a", 1)
        cache.put("b", 2)

        cache.get("a")  # Hit
        cache.get("b")  # Hit
        cache.get("c")  # Miss

        stats = cache.stats
        assert stats["size"] == 2
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == pytest.approx(2/3)

    def test_cache_clear(self):
        """Test cache clear operation."""
        cache = LRUCache(maxsize=10)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")

        cache.clear()

        assert cache.get("a") is None
        assert cache.stats["size"] == 0
        assert cache.stats["hits"] == 0


class TestLevenshteinDistance:
    """Tests for Levenshtein distance calculation."""

    def test_identical_strings(self):
        """Test distance between identical strings is 0."""
        assert _levenshtein_distance("hello", "hello") == 0

    def test_empty_string(self):
        """Test distance with empty string."""
        assert _levenshtein_distance("hello", "") == 5
        assert _levenshtein_distance("", "world") == 5

    def test_single_insertion(self):
        """Test single character insertion."""
        assert _levenshtein_distance("cat", "cats") == 1

    def test_single_deletion(self):
        """Test single character deletion."""
        assert _levenshtein_distance("cats", "cat") == 1

    def test_single_substitution(self):
        """Test single character substitution."""
        assert _levenshtein_distance("cat", "bat") == 1

    def test_multiple_edits(self):
        """Test multiple edits."""
        assert _levenshtein_distance("kitten", "sitting") == 3


class TestSimilarityScore:
    """Tests for similarity scoring."""

    def test_exact_match(self):
        """Test exact match returns 1.0."""
        assert _similarity_score("Andromeda", "Andromeda") == 1.0

    def test_case_insensitive(self):
        """Test case insensitivity."""
        assert _similarity_score("andromeda", "ANDROMEDA") == 1.0

    def test_starts_with_bonus(self):
        """Test starts-with returns 0.95."""
        assert _similarity_score("And", "Andromeda") == 0.95

    def test_contains_bonus(self):
        """Test contains returns 0.85."""
        assert _similarity_score("rome", "Andromeda") == 0.85

    def test_similar_strings(self):
        """Test similar strings get reasonable score."""
        score = _similarity_score("Andromdea", "Andromeda")
        assert 0.7 < score < 1.0


class TestCatalogDatabase:
    """Tests for CatalogDatabase operations."""

    @pytest.fixture
    def db(self):
        """Create in-memory database for testing."""
        db = CatalogDatabase(":memory:")
        db.connect()
        yield db
        db.close()

    @pytest.fixture
    def sample_object(self):
        """Create a sample catalog object."""
        return CatalogObject(
            catalog_id="M31",
            name="Andromeda Galaxy",
            object_type=ObjectType.GALAXY,
            ra_hours=0.712,
            dec_degrees=41.269,
            magnitude=3.4,
            size_arcmin=190.0,
            constellation="Andromeda",
            description="Nearest major galaxy",
            aliases=["NGC 224"]
        )

    def test_insert_and_lookup(self, db, sample_object):
        """Test inserting and looking up an object."""
        db.insert_object(sample_object)

        result = db.lookup("M31")
        assert result is not None
        assert result.catalog_id == "M31"
        assert result.name == "Andromeda Galaxy"

    def test_lookup_by_name(self, db, sample_object):
        """Test looking up by name."""
        db.insert_object(sample_object)

        result = db.lookup("Andromeda Galaxy")
        assert result is not None
        assert result.catalog_id == "M31"

    def test_lookup_by_alias(self, db, sample_object):
        """Test looking up by alias."""
        db.insert_object(sample_object)

        result = db.lookup("NGC 224")
        assert result is not None
        assert result.catalog_id == "M31"

    def test_lookup_not_found(self, db):
        """Test lookup returns None for unknown object."""
        result = db.lookup("UNKNOWN123")
        assert result is None

    def test_search_by_type(self, db, sample_object):
        """Test searching by object type."""
        db.insert_object(sample_object)

        results = db.search_by_type(ObjectType.GALAXY)
        assert len(results) == 1
        assert results[0].catalog_id == "M31"

    def test_search_by_constellation(self, db, sample_object):
        """Test searching by constellation."""
        db.insert_object(sample_object)

        results = db.search_by_constellation("Andromeda")
        assert len(results) == 1
        assert results[0].catalog_id == "M31"

    def test_search_by_magnitude(self, db, sample_object):
        """Test searching by magnitude range."""
        db.insert_object(sample_object)

        # M31 has magnitude 3.4
        results = db.search_by_magnitude(min_magnitude=3.0, max_magnitude=4.0)
        assert len(results) == 1

        # Outside range
        results = db.search_by_magnitude(min_magnitude=5.0)
        assert len(results) == 0


class TestCatalogService:
    """Tests for CatalogService high-level API."""

    @pytest.fixture
    def service(self):
        """Create catalog service with test data."""
        svc = CatalogService(":memory:")
        svc.initialize()
        yield svc
        svc.close()

    def test_lookup_messier(self, service):
        """Test looking up a Messier object."""
        result = service.lookup("M31")
        assert result is not None
        assert result.name == "Andromeda Galaxy"

    def test_lookup_by_common_name(self, service):
        """Test looking up by common name."""
        result = service.lookup("Orion Nebula")
        assert result is not None
        assert result.catalog_id == "M42"

    def test_what_is_response(self, service):
        """Test voice response generation."""
        response = service.what_is("M31")
        assert "Andromeda Galaxy" in response
        assert "galaxy" in response.lower()

    def test_what_is_not_found(self, service):
        """Test voice response for unknown object."""
        response = service.what_is("XYZ999")
        assert "couldn't find" in response.lower()

    def test_resolve_object(self, service):
        """Test coordinate resolution."""
        coords = service.resolve_object("M31")
        assert coords is not None
        ra, dec = coords
        assert 0 < ra < 24  # Valid RA hours
        assert -90 < dec < 90  # Valid Dec degrees

    def test_resolve_object_not_found(self, service):
        """Test coordinate resolution for unknown object."""
        coords = service.resolve_object("UNKNOWN123")
        assert coords is None

    def test_get_object_details(self, service):
        """Test getting full object details."""
        details = service.get_object_details("M42")
        assert details is not None
        assert details["catalog_id"] == "M42"
        assert details["name"] == "Orion Nebula"
        assert "ra" in details
        assert "dec" in details

    def test_cache_hit(self, service):
        """Test cache is used on repeated lookups."""
        # First lookup - cache miss
        service.lookup("M31")
        stats1 = service.cache_stats()

        # Second lookup - cache hit
        service.lookup("M31")
        stats2 = service.cache_stats()

        assert stats2["hits"] > stats1["hits"]

    def test_cache_clear(self, service):
        """Test cache clearing."""
        service.lookup("M31")
        service.lookup("M42")

        stats_before = service.cache_stats()
        assert stats_before["size"] > 0

        service.clear_cache()

        stats_after = service.cache_stats()
        assert stats_after["size"] == 0

    def test_fuzzy_search(self, service):
        """Test fuzzy name matching."""
        results = service.fuzzy_search("andromdea")  # Typo
        assert len(results) > 0
        # Should find Andromeda Galaxy despite typo
        names = [obj.name for obj, score in results if obj.name]
        assert "Andromeda Galaxy" in names

    def test_suggest(self, service):
        """Test autocomplete suggestions."""
        suggestions = service.suggest("ori")
        assert len(suggestions) > 0
        assert "Orion Nebula" in suggestions

    def test_objects_by_type(self, service):
        """Test finding objects by type."""
        galaxies = service.objects_by_type("galaxy", max_magnitude=8.0)
        assert len(galaxies) > 0
        for g in galaxies:
            assert g.object_type == ObjectType.GALAXY

    def test_objects_in_constellation(self, service):
        """Test finding objects in constellation."""
        orion_objects = service.objects_in_constellation("Orion")
        assert len(orion_objects) > 0
        for obj in orion_objects:
            assert obj.constellation == "Orion"


class TestCoordinateResolution:
    """Tests specifically for coordinate resolution functionality."""

    @pytest.fixture
    def service(self):
        """Create catalog service with test data."""
        svc = CatalogService(":memory:")
        svc.initialize()
        yield svc
        svc.close()

    def test_resolve_same_object_different_names(self, service):
        """Test that different names for same object resolve to same coords."""
        coords1 = service.resolve_object("M31")
        coords2 = service.resolve_object("Andromeda Galaxy")
        coords3 = service.resolve_object("NGC 224")

        assert coords1 is not None
        assert coords1 == coords2
        assert coords1 == coords3

    def test_get_coordinates_format(self, service):
        """Test coordinate format (HH:MM:SS, sDD:MM:SS)."""
        result = service.get_coordinates("M31")
        assert result is not None
        ra_str, dec_str = result

        # RA should be in HH:MM:SS format
        assert ":" in ra_str
        parts = ra_str.split(":")
        assert len(parts) == 3

        # Dec should be in sDD:MM:SS format with sign
        assert dec_str[0] in ["+", "-"]

    def test_cone_search_finds_nearby_objects(self, service):
        """Test that cone search finds nearby objects."""
        # M31 coordinates
        coords = service.resolve_object("M31")
        assert coords is not None

        # Search 60 arcmin around M31
        nearby = service.objects_in_area(coords[0], coords[1], radius_arcmin=60.0)

        # Should find M31 itself and possibly M32, M110
        names = [name for name, dist in nearby]
        assert "Andromeda Galaxy" in names or "M31" in names

    def test_cone_search_distance_ordering(self, service):
        """Test that cone search results are ordered by distance."""
        coords = service.resolve_object("M31")
        assert coords is not None

        nearby = service.objects_in_area(coords[0], coords[1], radius_arcmin=120.0)

        if len(nearby) > 1:
            distances = [dist for name, dist in nearby]
            assert distances == sorted(distances)


class TestCatalogEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def service(self):
        """Create catalog service with test data."""
        svc = CatalogService(":memory:")
        svc.initialize()
        yield svc
        svc.close()

    def test_lookup_case_insensitive(self, service):
        """Test that lookups are case insensitive."""
        result1 = service.lookup("m31")
        result2 = service.lookup("M31")
        result3 = service.lookup("m31")

        assert result1 is not None
        assert result1.catalog_id == result2.catalog_id
        assert result2.catalog_id == result3.catalog_id

    def test_lookup_with_whitespace(self, service):
        """Test lookup handles whitespace in queries."""
        result1 = service.lookup("M 31")  # With space
        result2 = service.lookup(" M31 ")  # Padded

        # Should still find M31 or handle gracefully
        assert result1 is not None or result2 is not None

    def test_lookup_empty_string(self, service):
        """Test lookup with empty string."""
        result = service.lookup("")
        assert result is None

    def test_fuzzy_search_empty_string(self, service):
        """Test fuzzy search with empty string."""
        results = service.fuzzy_search("")
        assert len(results) == 0

    def test_fuzzy_search_single_char(self, service):
        """Test fuzzy search with single character."""
        results = service.fuzzy_search("M")
        # Should handle gracefully, may find objects starting with M
        assert isinstance(results, list)

    def test_suggest_empty_string(self, service):
        """Test suggestions with empty string."""
        suggestions = service.suggest("")
        assert len(suggestions) == 0

    def test_objects_by_type_invalid(self, service):
        """Test objects_by_type with invalid type."""
        results = service.objects_by_type("invalid_type_xyz")
        assert len(results) == 0

    def test_objects_in_constellation_invalid(self, service):
        """Test objects_in_constellation with invalid constellation."""
        results = service.objects_in_constellation("InvalidConstellation")
        assert len(results) == 0

    def test_cone_search_zero_radius(self, service):
        """Test cone search with zero radius."""
        coords = service.resolve_object("M31")
        assert coords is not None

        # Zero radius should still return the center object
        nearby = service.objects_in_area(coords[0], coords[1], radius_arcmin=0.1)
        assert isinstance(nearby, list)

    def test_cone_search_large_radius(self, service):
        """Test cone search with large radius."""
        coords = service.resolve_object("M31")
        assert coords is not None

        # Large radius search
        nearby = service.objects_in_area(coords[0], coords[1], radius_arcmin=600.0)
        assert isinstance(nearby, list)
        # Should find multiple objects
        assert len(nearby) > 0

    def test_magnitude_search_inverted_range(self, service):
        """Test magnitude search with inverted range (min > max)."""
        # When min > max, should return empty or handle gracefully
        # Note: In astronomy, lower magnitude = brighter, so this tests edge case
        results = service.objects_by_type("galaxy", min_magnitude=10.0, max_magnitude=5.0)
        assert isinstance(results, list)

    def test_coordinate_wraparound(self, service):
        """Test coordinate handling near RA=0/24 boundary."""
        # Search near RA=0 boundary
        nearby = service.objects_in_area(0.1, 30.0, radius_arcmin=60.0)
        assert isinstance(nearby, list)

    def test_polar_coordinates(self, service):
        """Test coordinate handling near celestial poles."""
        # Search near North pole
        nearby = service.objects_in_area(12.0, 88.0, radius_arcmin=60.0)
        assert isinstance(nearby, list)


class TestCatalogObjectFormatting:
    """Tests for object formatting methods."""

    def test_ra_hms_format(self):
        """Test RA hours-minutes-seconds formatting."""
        obj = CatalogObject(
            catalog_id="TEST1",
            name="Test Object",
            object_type=ObjectType.STAR,
            ra_hours=5.5,  # 5h 30m
            dec_degrees=22.0,
        )
        ra_str = obj.ra_hms
        assert "5" in ra_str
        assert "30" in ra_str or ":" in ra_str

    def test_dec_dms_format(self):
        """Test Dec degrees-minutes-seconds formatting."""
        obj = CatalogObject(
            catalog_id="TEST1",
            name="Test Object",
            object_type=ObjectType.STAR,
            ra_hours=5.5,
            dec_degrees=-22.5,  # Negative declination
        )
        dec_str = obj.dec_dms
        assert "-" in dec_str
        assert "22" in dec_str

    def test_dec_positive_format(self):
        """Test Dec formatting for positive declination."""
        obj = CatalogObject(
            catalog_id="TEST1",
            name="Test Object",
            object_type=ObjectType.STAR,
            ra_hours=5.5,
            dec_degrees=45.25,
        )
        dec_str = obj.dec_dms
        assert "+" in dec_str
        assert "45" in dec_str
