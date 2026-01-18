"""
NIGHTWATCH Catalog Service

Provides astronomical object lookup from SQLite database.
"""

from .catalog import (
    CatalogService,
    CatalogDatabase,
    CatalogObject,
    ObjectType,
    load_messier_catalog,
    load_named_stars,
)

__all__ = [
    "CatalogService",
    "CatalogDatabase",
    "CatalogObject",
    "ObjectType",
    "load_messier_catalog",
    "load_named_stars",
]
