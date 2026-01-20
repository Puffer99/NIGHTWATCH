"""
NIGHTWATCH NLP Services

Natural Language Processing services for voice command understanding.
"""

from .conversation_context import (
    ConversationContext,
    EntityType,
    TrackedEntity,
    ContextMessage,
    UserIntent,
    get_context_manager,
)

from .clarification import (
    ClarificationService,
    ClarificationResult,
    AmbiguityType,
    ClarificationOption,
    get_clarification_service,
)

from .suggestions import (
    SuggestionService,
    Suggestion,
    SuggestionType,
    SuggestionPriority,
    get_suggestion_service,
)

from .user_preferences import (
    UserPreferences,
    PreferenceCategory,
    ObservationStyle,
    CommunicationStyle,
    TargetPreference,
    ImagingPreference,
    get_user_preferences,
)

__all__ = [
    # Conversation Context
    "ConversationContext",
    "EntityType",
    "TrackedEntity",
    "ContextMessage",
    "UserIntent",
    "get_context_manager",
    # Clarification
    "ClarificationService",
    "ClarificationResult",
    "AmbiguityType",
    "ClarificationOption",
    "get_clarification_service",
    # Suggestions
    "SuggestionService",
    "Suggestion",
    "SuggestionType",
    "SuggestionPriority",
    "get_suggestion_service",
    # User Preferences
    "UserPreferences",
    "PreferenceCategory",
    "ObservationStyle",
    "CommunicationStyle",
    "TargetPreference",
    "ImagingPreference",
    "get_user_preferences",
]
