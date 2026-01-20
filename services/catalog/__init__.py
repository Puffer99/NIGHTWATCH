"""
NIGHTWATCH Catalog Service

Provides astronomical object lookup from SQLite database
and intelligent target scoring for observation planning.
"""

from .catalog import (
    CatalogService,
    CatalogDatabase,
    CatalogObject,
    ObjectType,
    load_messier_catalog,
    load_named_stars,
)

from .target_scorer import (
    TargetScorer,
    TargetScore,
    ScoringWeights,
    ScoringWeight,
    get_scorer,
)

__all__ = [
    "CatalogService",
    "CatalogDatabase",
    "CatalogObject",
    "ObjectType",
    "load_messier_catalog",
    "load_named_stars",
    "TargetScorer",
    "TargetScore",
    "ScoringWeights",
    "ScoringWeight",
    "get_scorer",
]
