"""
NIGHTWATCH Catalog Service
Astronomical Object Database

This module provides lookup services for astronomical objects including:
- Messier catalog (M1-M110)
- NGC catalog (NGC 1 - NGC 7840+)
- IC catalog (IC 1 - IC 5386)
- Named stars (Polaris, Vega, etc.)
- Planets (via ephemeris service)
- Common names (Orion Nebula, Ring Nebula, etc.)

Data stored in SQLite for fast local queries with voice control.
"""

import sqlite3
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, List, Tuple


class ObjectType(Enum):
    """Astronomical object types."""
    STAR = "star"
    DOUBLE_STAR = "double_star"
    VARIABLE_STAR = "variable_star"
    OPEN_CLUSTER = "open_cluster"
    GLOBULAR_CLUSTER = "globular_cluster"
    NEBULA = "nebula"
    PLANETARY_NEBULA = "planetary_nebula"
    GALAXY = "galaxy"
    GALAXY_CLUSTER = "galaxy_cluster"
    SUPERNOVA_REMNANT = "supernova_remnant"
    PLANET = "planet"
    ASTEROID = "asteroid"
    COMET = "comet"
    OTHER = "other"


@dataclass
class CatalogObject:
    """Astronomical object from catalog."""
    catalog_id: str           # e.g., "M31", "NGC 224", "IC 434"
    name: Optional[str]       # Common name, e.g., "Andromeda Galaxy"
    object_type: ObjectType
    ra_hours: float           # Right Ascension in decimal hours (J2000)
    dec_degrees: float        # Declination in decimal degrees (J2000)
    magnitude: Optional[float]
    size_arcmin: Optional[float]
    constellation: Optional[str]
    description: Optional[str]
    aliases: List[str]        # Alternative designations

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


class CatalogDatabase:
    """
    SQLite-based astronomical catalog database.

    Provides fast local queries for object lookup by various identifiers.
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS objects (
        id INTEGER PRIMARY KEY,
        catalog_id TEXT UNIQUE NOT NULL,
        name TEXT,
        object_type TEXT NOT NULL,
        ra_hours REAL NOT NULL,
        dec_degrees REAL NOT NULL,
        magnitude REAL,
        size_arcmin REAL,
        constellation TEXT,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS aliases (
        id INTEGER PRIMARY KEY,
        object_id INTEGER NOT NULL,
        alias TEXT NOT NULL,
        FOREIGN KEY (object_id) REFERENCES objects(id),
        UNIQUE(object_id, alias)
    );

    CREATE INDEX IF NOT EXISTS idx_catalog_id ON objects(catalog_id);
    CREATE INDEX IF NOT EXISTS idx_name ON objects(name);
    CREATE INDEX IF NOT EXISTS idx_alias ON aliases(alias);
    CREATE INDEX IF NOT EXISTS idx_constellation ON objects(constellation);
    CREATE INDEX IF NOT EXISTS idx_type ON objects(object_type);
    """

    def __init__(self, db_path: str = "nightwatch_catalog.db"):
        self.db_path = db_path
        self._conn = None

    def connect(self):
        """Connect to database and create schema if needed."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(self.SCHEMA)
        self._conn.commit()

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def insert_object(self, obj: CatalogObject):
        """Insert an object into the catalog."""
        cursor = self._conn.cursor()

        # Check if object already exists
        cursor.execute(
            "SELECT id FROM objects WHERE catalog_id = ?",
            (obj.catalog_id,)
        )
        existing = cursor.fetchone()

        if existing:
            object_id = existing[0]
            # Update existing object
            cursor.execute("""
                UPDATE objects SET
                    name = ?, object_type = ?, ra_hours = ?, dec_degrees = ?,
                    magnitude = ?, size_arcmin = ?, constellation = ?, description = ?
                WHERE id = ?
            """, (
                obj.name,
                obj.object_type.value,
                obj.ra_hours,
                obj.dec_degrees,
                obj.magnitude,
                obj.size_arcmin,
                obj.constellation,
                obj.description,
                object_id
            ))
        else:
            # Insert new object
            cursor.execute("""
                INSERT INTO objects
                (catalog_id, name, object_type, ra_hours, dec_degrees,
                 magnitude, size_arcmin, constellation, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obj.catalog_id,
                obj.name,
                obj.object_type.value,
                obj.ra_hours,
                obj.dec_degrees,
                obj.magnitude,
                obj.size_arcmin,
                obj.constellation,
                obj.description
            ))
            object_id = cursor.lastrowid

        # Insert aliases (ignore duplicates)
        for alias in obj.aliases:
            cursor.execute("""
                INSERT OR IGNORE INTO aliases (object_id, alias)
                VALUES (?, ?)
            """, (object_id, alias.upper()))

        self._conn.commit()

    def lookup(self, query: str) -> Optional[CatalogObject]:
        """
        Look up an object by catalog ID, name, or alias.

        Args:
            query: Search string (e.g., "M31", "Andromeda", "NGC 224")

        Returns:
            CatalogObject if found, None otherwise
        """
        query = query.strip().upper()
        cursor = self._conn.cursor()

        # Try exact catalog_id match
        cursor.execute("""
            SELECT * FROM objects WHERE UPPER(catalog_id) = ?
        """, (query,))
        row = cursor.fetchone()

        if not row:
            # Try name match
            cursor.execute("""
                SELECT * FROM objects WHERE UPPER(name) = ?
            """, (query,))
            row = cursor.fetchone()

        if not row:
            # Try alias match
            cursor.execute("""
                SELECT o.* FROM objects o
                JOIN aliases a ON o.id = a.object_id
                WHERE a.alias = ?
            """, (query,))
            row = cursor.fetchone()

        if not row:
            # Try partial name match
            cursor.execute("""
                SELECT * FROM objects WHERE UPPER(name) LIKE ?
                ORDER BY LENGTH(name) LIMIT 1
            """, (f"%{query}%",))
            row = cursor.fetchone()

        if row:
            return self._row_to_object(row)
        return None

    def search(
        self,
        query: Optional[str] = None,
        object_type: Optional[ObjectType] = None,
        constellation: Optional[str] = None,
        min_altitude: Optional[float] = None,
        max_magnitude: Optional[float] = None,
        limit: int = 50
    ) -> List[CatalogObject]:
        """
        Search catalog with filters.

        Args:
            query: Text search in name/description
            object_type: Filter by object type
            constellation: Filter by constellation
            min_altitude: Minimum altitude (requires ephemeris)
            max_magnitude: Maximum (brightest) magnitude
            limit: Maximum results to return

        Returns:
            List of matching CatalogObject
        """
        cursor = self._conn.cursor()

        sql = "SELECT * FROM objects WHERE 1=1"
        params = []

        if query:
            sql += " AND (UPPER(name) LIKE ? OR UPPER(description) LIKE ?)"
            params.extend([f"%{query.upper()}%", f"%{query.upper()}%"])

        if object_type:
            sql += " AND object_type = ?"
            params.append(object_type.value)

        if constellation:
            sql += " AND UPPER(constellation) = ?"
            params.append(constellation.upper())

        if max_magnitude is not None:
            sql += " AND magnitude <= ?"
            params.append(max_magnitude)

        sql += " ORDER BY magnitude LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        return [self._row_to_object(row) for row in cursor.fetchall()]

    def get_messier_catalog(self) -> List[CatalogObject]:
        """Get all Messier objects."""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT * FROM objects WHERE catalog_id LIKE 'M%'
            ORDER BY CAST(SUBSTR(catalog_id, 2) AS INTEGER)
        """)
        return [self._row_to_object(row) for row in cursor.fetchall()]

    def cone_search(
        self,
        ra_hours: float,
        dec_degrees: float,
        radius_arcmin: float,
        limit: int = 50
    ) -> List[Tuple[CatalogObject, float]]:
        """
        Search for objects within a cone (circular region) on the sky.

        Uses spherical geometry approximation suitable for small search radii.

        Args:
            ra_hours: Center RA in decimal hours (0-24)
            dec_degrees: Center Dec in decimal degrees (-90 to +90)
            radius_arcmin: Search radius in arcminutes
            limit: Maximum results to return

        Returns:
            List of (CatalogObject, distance_arcmin) tuples sorted by distance
        """
        import math

        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM objects")
        rows = cursor.fetchall()

        results = []
        radius_deg = radius_arcmin / 60.0

        # Convert center to radians
        ra_center_rad = math.radians(ra_hours * 15.0)  # hours to degrees to radians
        dec_center_rad = math.radians(dec_degrees)

        for row in rows:
            obj_ra_hours = row[4]
            obj_dec_deg = row[5]

            # Convert object coords to radians
            ra_rad = math.radians(obj_ra_hours * 15.0)
            dec_rad = math.radians(obj_dec_deg)

            # Spherical law of cosines for angular separation
            cos_sep = (
                math.sin(dec_center_rad) * math.sin(dec_rad) +
                math.cos(dec_center_rad) * math.cos(dec_rad) *
                math.cos(ra_center_rad - ra_rad)
            )
            # Clamp to valid range for acos
            cos_sep = max(-1.0, min(1.0, cos_sep))
            separation_rad = math.acos(cos_sep)
            separation_deg = math.degrees(separation_rad)

            if separation_deg <= radius_deg:
                obj = self._row_to_object(row)
                distance_arcmin = separation_deg * 60.0
                results.append((obj, distance_arcmin))

        # Sort by distance and limit
        results.sort(key=lambda x: x[1])
        return results[:limit]

    def search_by_type(
        self,
        object_type: ObjectType,
        max_magnitude: Optional[float] = None,
        limit: int = 50
    ) -> List[CatalogObject]:
        """
        Search for objects by type.

        Args:
            object_type: Type of object (galaxy, nebula, etc.)
            max_magnitude: Optional brightness limit
            limit: Maximum results

        Returns:
            List of CatalogObject sorted by magnitude
        """
        cursor = self._conn.cursor()

        sql = "SELECT * FROM objects WHERE object_type = ?"
        params: List = [object_type.value]

        if max_magnitude is not None:
            sql += " AND magnitude <= ?"
            params.append(max_magnitude)

        sql += " ORDER BY magnitude LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        return [self._row_to_object(row) for row in cursor.fetchall()]

    def search_by_magnitude(
        self,
        min_magnitude: Optional[float] = None,
        max_magnitude: Optional[float] = None,
        limit: int = 50
    ) -> List[CatalogObject]:
        """
        Search for objects by magnitude range.

        Args:
            min_magnitude: Minimum (faintest) magnitude
            max_magnitude: Maximum (brightest) magnitude
            limit: Maximum results

        Returns:
            List of CatalogObject sorted by magnitude
        """
        cursor = self._conn.cursor()

        sql = "SELECT * FROM objects WHERE magnitude IS NOT NULL"
        params: List = []

        if min_magnitude is not None:
            sql += " AND magnitude >= ?"
            params.append(min_magnitude)

        if max_magnitude is not None:
            sql += " AND magnitude <= ?"
            params.append(max_magnitude)

        sql += " ORDER BY magnitude LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        return [self._row_to_object(row) for row in cursor.fetchall()]

    def search_by_constellation(
        self,
        constellation: str,
        object_type: Optional[ObjectType] = None,
        max_magnitude: Optional[float] = None,
        limit: int = 50
    ) -> List[CatalogObject]:
        """
        Search for objects in a constellation.

        Args:
            constellation: Constellation name (e.g., "Orion", "Cygnus")
            object_type: Optional type filter
            max_magnitude: Optional brightness limit
            limit: Maximum results

        Returns:
            List of CatalogObject sorted by magnitude
        """
        cursor = self._conn.cursor()

        sql = "SELECT * FROM objects WHERE UPPER(constellation) = ?"
        params: List = [constellation.upper()]

        if object_type is not None:
            sql += " AND object_type = ?"
            params.append(object_type.value)

        if max_magnitude is not None:
            sql += " AND magnitude <= ?"
            params.append(max_magnitude)

        sql += " ORDER BY magnitude LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        return [self._row_to_object(row) for row in cursor.fetchall()]

    def _row_to_object(self, row: tuple) -> CatalogObject:
        """Convert database row to CatalogObject."""
        cursor = self._conn.cursor()

        # Get aliases
        cursor.execute("""
            SELECT alias FROM aliases WHERE object_id = ?
        """, (row[0],))
        aliases = [r[0] for r in cursor.fetchall()]

        return CatalogObject(
            catalog_id=row[1],
            name=row[2],
            object_type=ObjectType(row[3]),
            ra_hours=row[4],
            dec_degrees=row[5],
            magnitude=row[6],
            size_arcmin=row[7],
            constellation=row[8],
            description=row[9],
            aliases=aliases
        )

    def get_stats(self) -> dict:
        """Get catalog statistics."""
        cursor = self._conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM objects")
        total = cursor.fetchone()[0]

        cursor.execute("""
            SELECT object_type, COUNT(*) FROM objects
            GROUP BY object_type
        """)
        by_type = {row[0]: row[1] for row in cursor.fetchall()}

        return {"total": total, "by_type": by_type}


# =============================================================================
# FUZZY MATCHING
# =============================================================================

def _levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def _similarity_score(query: str, target: str) -> float:
    """Calculate similarity score (0-1) between query and target string."""
    query = query.upper()
    target = target.upper()

    # Exact match
    if query == target:
        return 1.0

    # Starts with bonus
    if target.startswith(query):
        return 0.95

    # Contains bonus
    if query in target:
        return 0.85

    # Levenshtein-based similarity
    max_len = max(len(query), len(target))
    if max_len == 0:
        return 0.0

    distance = _levenshtein_distance(query, target)
    return max(0.0, 1.0 - (distance / max_len))


# =============================================================================
# CATALOG DATA LOADERS
# =============================================================================

def load_messier_catalog(db: CatalogDatabase):
    """Load complete Messier catalog (M1-M110)."""
    try:
        from services.catalog.messier_data import get_messier_catalog
        messier = get_messier_catalog()
    except ImportError:
        messier = []

    for obj in messier:
        db.insert_object(obj)


def load_ngc_catalog(db: CatalogDatabase):
    """Load NGC catalog (popular objects)."""
    try:
        from services.catalog.catalog_data import get_ngc_catalog
        ngc = get_ngc_catalog()
    except ImportError:
        ngc = []

    for obj in ngc:
        db.insert_object(obj)


def load_ic_catalog(db: CatalogDatabase):
    """Load IC catalog (popular objects)."""
    try:
        from services.catalog.catalog_data import get_ic_catalog
        ic = get_ic_catalog()
    except ImportError:
        ic = []

    for obj in ic:
        db.insert_object(obj)


def load_named_stars(db: CatalogDatabase):
    """Load bright named stars."""
    try:
        from services.catalog.catalog_data import get_named_stars
        stars = get_named_stars()
    except ImportError:
        stars = []

    for star in stars:
        db.insert_object(star)


def load_double_stars(db: CatalogDatabase):
    """Load showpiece double stars."""
    try:
        from services.catalog.catalog_data import get_double_stars
        doubles = get_double_stars()
    except ImportError:
        doubles = []

    for double in doubles:
        db.insert_object(double)


# =============================================================================
# HIGH-LEVEL API
# =============================================================================

class CatalogService:
    """
    High-level catalog service for NIGHTWATCH.

    Provides simple lookup interface for voice commands.
    """

    def __init__(self, db_path: str = "nightwatch_catalog.db"):
        self.db = CatalogDatabase(db_path)

    def initialize(self):
        """Initialize database with all catalog data."""
        self.db.connect()

        # Load catalogs if database is empty
        stats = self.db.get_stats()
        if stats["total"] == 0:
            load_messier_catalog(self.db)
            load_ngc_catalog(self.db)
            load_ic_catalog(self.db)
            load_named_stars(self.db)
            load_double_stars(self.db)

    def close(self):
        """Close database connection."""
        self.db.close()

    def lookup(self, query: str) -> Optional[CatalogObject]:
        """
        Look up an object by name or catalog ID.

        Examples:
            lookup("M31") -> Andromeda Galaxy
            lookup("Andromeda") -> Andromeda Galaxy
            lookup("Orion Nebula") -> M42
        """
        return self.db.lookup(query)

    def what_is(self, query: str) -> str:
        """
        Get a description of an object (for voice response).

        Returns:
            Human-readable description string
        """
        obj = self.lookup(query)
        if not obj:
            return f"I couldn't find {query} in the catalog."

        parts = [f"{obj.catalog_id}"]
        if obj.name:
            parts[0] = f"{obj.name} ({obj.catalog_id})"

        parts.append(f"is a {obj.object_type.value.replace('_', ' ')}")

        if obj.constellation:
            parts.append(f"in {obj.constellation}")

        if obj.magnitude:
            parts.append(f"with magnitude {obj.magnitude}")

        if obj.description:
            parts.append(f"- {obj.description}")

        return " ".join(parts)

    def get_coordinates(self, query: str) -> Optional[Tuple[str, str]]:
        """
        Get coordinates for an object.

        Returns:
            Tuple of (RA in HH:MM:SS, DEC in sDD:MM:SS) or None
        """
        obj = self.lookup(query)
        if obj:
            return (obj.ra_hms, obj.dec_dms)
        return None

    def fuzzy_search(
        self,
        query: str,
        min_score: float = 0.6,
        limit: int = 10
    ) -> List[Tuple[CatalogObject, float]]:
        """
        Search for objects using fuzzy name matching.

        Useful for voice control where names may be misheard or
        partially spoken. Returns results sorted by match score.

        Args:
            query: Search string (can be partial or misspelled)
            min_score: Minimum similarity score (0-1) to include
            limit: Maximum results to return

        Returns:
            List of (CatalogObject, score) tuples sorted by score descending

        Examples:
            fuzzy_search("andromdea") -> [(Andromeda Galaxy, 0.91), ...]
            fuzzy_search("orion") -> [(Orion Nebula, 0.95), ...]
            fuzzy_search("betle") -> [(Betelgeuse, 0.75), ...]
        """
        cursor = self.db._conn.cursor()

        # Get all objects with names
        cursor.execute("SELECT * FROM objects WHERE name IS NOT NULL")
        rows = cursor.fetchall()

        results = []
        for row in rows:
            obj = self.db._row_to_object(row)
            if obj.name:
                score = _similarity_score(query, obj.name)
                if score >= min_score:
                    results.append((obj, score))

            # Also check aliases
            for alias in obj.aliases:
                alias_score = _similarity_score(query, alias)
                if alias_score >= min_score and alias_score > score:
                    results.append((obj, alias_score))
                    break

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def suggest(self, query: str, limit: int = 5) -> List[str]:
        """
        Get name suggestions for partial input (autocomplete).

        Useful for voice control confirmation.

        Args:
            query: Partial name input
            limit: Maximum suggestions

        Returns:
            List of suggested object names
        """
        results = self.fuzzy_search(query, min_score=0.5, limit=limit)
        suggestions = []
        for obj, score in results:
            if obj.name:
                suggestions.append(obj.name)
            else:
                suggestions.append(obj.catalog_id)
        return suggestions

    def get_object_details(self, query: str) -> Optional[dict]:
        """
        Get full details for an object as a dictionary.

        Useful for display, logging, or API responses.

        Args:
            query: Object name or catalog ID

        Returns:
            Dictionary with all object details, or None if not found

        Example:
            get_object_details("M31") -> {
                "catalog_id": "M31",
                "name": "Andromeda Galaxy",
                "type": "galaxy",
                "ra": "00:42:44",
                "dec": "+41:16:09",
                "magnitude": 3.4,
                ...
            }
        """
        obj = self.lookup(query)
        if not obj:
            return None

        return {
            "catalog_id": obj.catalog_id,
            "name": obj.name,
            "type": obj.object_type.value,
            "ra_hours": obj.ra_hours,
            "dec_degrees": obj.dec_degrees,
            "ra": obj.ra_hms,
            "dec": obj.dec_dms,
            "magnitude": obj.magnitude,
            "size_arcmin": obj.size_arcmin,
            "constellation": obj.constellation,
            "description": obj.description,
            "aliases": obj.aliases,
        }

    def resolve_object(self, query: str) -> Optional[Tuple[float, float]]:
        """
        Resolve an object name to RA/Dec coordinates.

        Critical for goto functionality - converts user-provided name
        to mount-ready coordinates.

        Args:
            query: Object name, catalog ID, or alias

        Returns:
            Tuple of (ra_hours, dec_degrees) or None if not found

        Example:
            resolve_object("M31") -> (0.7119..., 41.269...)
            resolve_object("Andromeda Galaxy") -> (0.7119..., 41.269...)
            resolve_object("NGC 224") -> (0.7119..., 41.269...)
        """
        obj = self.lookup(query)
        if obj:
            return (obj.ra_hours, obj.dec_degrees)
        return None

    def objects_in_area(
        self,
        ra_hours: float,
        dec_degrees: float,
        radius_arcmin: float = 60.0,
        limit: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Find objects near a given sky position.

        Useful for "what's near here?" queries or identifying
        objects near the current telescope pointing.

        Args:
            ra_hours: Center RA in decimal hours
            dec_degrees: Center Dec in decimal degrees
            radius_arcmin: Search radius in arcminutes
            limit: Maximum results

        Returns:
            List of (object_name_or_id, distance_arcmin) tuples
        """
        results = self.db.cone_search(ra_hours, dec_degrees, radius_arcmin, limit)
        return [(obj.name or obj.catalog_id, dist) for obj, dist in results]

    def objects_by_type(
        self,
        type_name: str,
        max_magnitude: Optional[float] = None,
        limit: int = 20
    ) -> List[CatalogObject]:
        """
        Find objects by type name (for voice control).

        Args:
            type_name: Type name (e.g., "galaxy", "nebula", "cluster")
            max_magnitude: Optional brightness limit
            limit: Maximum results

        Returns:
            List of CatalogObject
        """
        # Map common voice variations to ObjectType
        type_map = {
            "galaxy": ObjectType.GALAXY,
            "galaxies": ObjectType.GALAXY,
            "nebula": ObjectType.NEBULA,
            "nebulae": ObjectType.NEBULA,
            "planetary": ObjectType.PLANETARY_NEBULA,
            "planetary nebula": ObjectType.PLANETARY_NEBULA,
            "cluster": ObjectType.OPEN_CLUSTER,
            "open cluster": ObjectType.OPEN_CLUSTER,
            "globular": ObjectType.GLOBULAR_CLUSTER,
            "globular cluster": ObjectType.GLOBULAR_CLUSTER,
            "star": ObjectType.STAR,
            "double": ObjectType.DOUBLE_STAR,
            "double star": ObjectType.DOUBLE_STAR,
            "variable": ObjectType.VARIABLE_STAR,
            "supernova": ObjectType.SUPERNOVA_REMNANT,
        }

        obj_type = type_map.get(type_name.lower())
        if not obj_type:
            return []

        return self.db.search_by_type(obj_type, max_magnitude, limit)

    def objects_in_constellation(
        self,
        constellation: str,
        max_magnitude: Optional[float] = None,
        limit: int = 20
    ) -> List[CatalogObject]:
        """
        Find objects in a constellation (for voice control).

        Args:
            constellation: Constellation name
            max_magnitude: Optional brightness limit
            limit: Maximum results

        Returns:
            List of CatalogObject
        """
        return self.db.search_by_constellation(constellation, None, max_magnitude, limit)


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    service = CatalogService(":memory:")  # In-memory for testing
    service.initialize()

    # Get stats
    stats = service.db.get_stats()
    print(f"Catalog loaded: {stats['total']} objects")
    print(f"By type: {stats['by_type']}\n")

    # Test lookups
    print("Testing catalog lookups:\n")

    queries = ["M31", "Andromeda", "Orion Nebula", "Polaris", "M13", "Sirius",
               "NGC 7000", "Albireo", "Horsehead"]

    for q in queries:
        result = service.lookup(q)
        if result:
            print(f"{q:15} -> {result.catalog_id:8} {result.name or ''}")
            print(f"              RA: {result.ra_hms}  DEC: {result.dec_dms}")
        else:
            print(f"{q:15} -> Not found")
        print()

    # Test what_is
    print("\nVoice response test:")
    print(service.what_is("Ring Nebula"))

    # Test fuzzy search
    print("\n\nFuzzy search tests:")
    fuzzy_queries = ["andromdea", "orion", "betle", "pleiads", "horshead"]
    for q in fuzzy_queries:
        results = service.fuzzy_search(q, limit=3)
        print(f"\n'{q}' matches:")
        for obj, score in results:
            print(f"  {score:.2f} - {obj.name or obj.catalog_id}")

    # Test suggestions
    print("\n\nSuggestion tests:")
    for partial in ["and", "ori", "veg"]:
        suggestions = service.suggest(partial)
        print(f"'{partial}' -> {suggestions}")

    # Test resolve_object (for goto)
    print("\n\nResolve object tests (for goto):")
    for name in ["M31", "Andromeda Galaxy", "NGC 224"]:
        coords = service.resolve_object(name)
        if coords:
            print(f"{name:20} -> RA={coords[0]:.4f}h, Dec={coords[1]:.4f}°")

    # Test get_object_details
    print("\n\nObject details test:")
    details = service.get_object_details("M42")
    if details:
        print(f"  ID: {details['catalog_id']}")
        print(f"  Name: {details['name']}")
        print(f"  Type: {details['type']}")
        print(f"  Coords: {details['ra']} / {details['dec']}")
        print(f"  Mag: {details['magnitude']}")

    # Test cone search (objects near M31)
    print("\n\nCone search (60' around M31):")
    m31_coords = service.resolve_object("M31")
    if m31_coords:
        nearby = service.objects_in_area(m31_coords[0], m31_coords[1], 60.0)
        for name, dist in nearby:
            print(f"  {name:25} at {dist:.1f}'")

    # Test search by type
    print("\n\nBrightest galaxies:")
    galaxies = service.objects_by_type("galaxy", max_magnitude=10.0, limit=5)
    for g in galaxies:
        print(f"  {g.catalog_id:8} {g.name or '':25} mag {g.magnitude}")

    # Test search by constellation
    print("\n\nObjects in Orion:")
    orion_objs = service.objects_in_constellation("Orion", limit=8)
    for obj in orion_objs:
        print(f"  {obj.catalog_id:8} {obj.name or '':25} ({obj.object_type.value})")

    service.close()
