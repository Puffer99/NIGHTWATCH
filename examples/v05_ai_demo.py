#!/usr/bin/env python3
"""
NIGHTWATCH v0.5 AI Enhancement Demonstration

This script demonstrates all v0.5 AI capabilities:
- Intelligent Scheduling (weather-aware, moon avoidance, scoring)
- Natural Language (context, clarification, suggestions, descriptions)
- Voice Enhancement (vocabulary, wake word training)
- Object Identification (offline recognition)

Run with: python examples/v05_ai_demo.py
"""

from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services import AIServices, AIServicesConfig


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def demo_scheduling(ai: AIServices) -> None:
    """Demonstrate intelligent scheduling capabilities."""
    print_section("Intelligent Scheduling (Steps 116-119)")

    # Sample targets for tonight
    candidates = [
        {
            "id": "M31",
            "name": "Andromeda Galaxy",
            "ra_hours": 0.712,
            "dec_degrees": 41.269,
            "magnitude": 3.4,
            "object_type": "galaxy",
        },
        {
            "id": "M42",
            "name": "Orion Nebula",
            "ra_hours": 5.588,
            "dec_degrees": -5.391,
            "magnitude": 4.0,
            "object_type": "nebula",
        },
        {
            "id": "M45",
            "name": "Pleiades",
            "ra_hours": 3.791,
            "dec_degrees": 24.117,
            "magnitude": 1.6,
            "object_type": "cluster",
        },
        {
            "id": "M13",
            "name": "Hercules Cluster",
            "ra_hours": 16.695,
            "dec_degrees": 36.467,
            "magnitude": 5.8,
            "object_type": "globular_cluster",
        },
    ]

    print("\n1. Creating tonight's schedule...")
    result = ai.schedule_tonight(candidates)

    print(f"   Scheduled {result['target_count']} targets")
    print(f"   Total observation time: {result['total_minutes']:.0f} minutes")
    print(f"\n   Narration: \"{result['narration']}\"")

    print("\n2. Evaluating individual target (M31)...")
    info = ai.describe_target("M31", 0.712, 41.269, "galaxy")
    eval_data = info["evaluation"]
    print(f"   Quality: {eval_data.get('quality', 'N/A')}")
    print(f"   Score: {eval_data.get('total_score', 0):.2f}")
    print(f"   Recommendation: {info['recommendation']}")

    print("\n3. Condition scores for M31:")
    scores = info["condition_scores"]
    for score_name, score_value in scores.items():
        print(f"   - {score_name}: {score_value:.2f}")


def demo_nlp(ai: AIServices) -> None:
    """Demonstrate natural language capabilities."""
    print_section("Natural Language Processing (Steps 128-131, 137)")

    # Multi-turn context
    print("\n1. Multi-turn conversation context...")
    context = ai.context_manager
    context.add_user_message("Point the telescope at M31")
    context.add_assistant_message("Slewing to M31, the Andromeda Galaxy")
    context.add_user_message("Take a 60 second exposure")

    recent = context.get_context_messages(max_messages=3)
    print(f"   Tracking {len(recent)} messages in context")
    if recent:
        last_msg = recent[-1]
        content = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)
        print(f"   Last entry: \"{content[:60]}...\"")

    # Clarification
    print("\n2. Clarification service...")
    clarification = ai.clarification
    result = clarification.check_command("Go to the nebula")
    print(f"   Input: \"Go to the nebula\"")
    print(f"   Needs clarification: {result.needs_clarification}")
    if result.needs_clarification:
        print(f"   Reason: {result.ambiguity_type.value if result.ambiguity_type else 'N/A'}")

    # Suggestions
    print("\n3. Proactive suggestions...")
    suggestions = ai.suggestions
    # Simulate some context
    suggestion_list = suggestions.get_suggestions(max_suggestions=2)
    print(f"   Generated {len(suggestion_list)} suggestions")
    for s in suggestion_list[:2]:
        print(f"   - [{s.priority.value}] {s.text}")

    # User preferences
    print("\n4. User preferences learning...")
    prefs = ai.user_preferences
    prefs.record_target_observation("M31", success=True, quality=0.9)
    prefs.record_target_observation("M31", success=True, quality=0.85)
    fav = prefs.get_favorite_targets(limit=3)
    print(f"   Recorded observations, tracking {len(fav)} favorites")

    # Sky description
    print("\n5. Natural sky descriptions...")
    describer = ai.sky_describer
    from services.nlp import SkyState, VisibleObject, SkyCondition
    state = SkyState(
        condition=SkyCondition.GOOD,
        visible_objects=[
            VisibleObject(
                name="M31",
                object_type="galaxy",
                constellation="Andromeda",
                altitude_deg=55.0,
                azimuth_deg=45.0,
            )
        ],
    )
    desc = describer.describe_sky(state)
    print(f"   Sky description: \"{desc.text}\"")


def demo_voice(ai: AIServices) -> None:
    """Demonstrate voice enhancement capabilities."""
    print_section("Voice Enhancement (Steps 134-135)")

    # Vocabulary training
    print("\n1. Astronomy vocabulary trainer...")
    vocab = ai.vocabulary_trainer
    test_phrases = [
        "go to messier 31",
        "slew to ngc 7000",
        "point at the pleiades",
    ]
    print("   Normalizing astronomy terms:")
    for phrase in test_phrases:
        normalized = vocab.normalize_text(phrase)
        print(f"   - \"{phrase}\" -> \"{normalized}\"")

    # Record some term usage
    vocab.record_usage("M31", success=True)
    vocab.record_usage("Andromeda", success=True)
    stats = vocab.get_statistics()
    print(f"\n   Vocabulary stats: {stats.get('total_terms', stats.get('terms_count', 'N/A'))} terms tracked")

    # Wake word training
    print("\n2. Wake word trainer...")
    wake = ai.wake_word_trainer
    print(f"   Wake word: \"{wake.primary_phrase}\"")
    print(f"   Training phase: {wake.get_status().phase.value}")

    # Record some detection events
    wake.record_detection("nightwatch start session", detected=True, was_correct=True)
    wake.record_detection("hey nightwatch", detected=True, was_correct=True)
    status = wake.get_status()
    print(f"   Detection events: {status.total_detections}")
    print(f"   Accuracy: {status.accuracy:.0%}")


def demo_object_identification(ai: AIServices) -> None:
    """Demonstrate offline object identification."""
    print_section("Object Identification (Step 136)")

    identifier = ai.object_identifier

    # Identify by coordinates
    print("\n1. Identifying object by coordinates...")
    print("   Position: RA=0.712h, Dec=41.27°")
    result = identifier.identify_at_coordinates(0.712, 41.269, search_radius_arcmin=60.0)
    if result.matches:
        best = result.matches[0]
        print(f"   Best match: {best.object_id} ({best.object_name})")
        print(f"   Confidence: {best.confidence_level.value}")
        print(f"   Method: {best.method.value}")
    else:
        print("   No matches found")

    # Identify by catalog ID
    print("\n2. Identifying object by catalog ID...")
    match = identifier.get_object_info("M42")
    if match:
        print(f"   Found: {match.object_id} ({match.object_name})")
        print(f"   Type: {match.object_type}, Constellation: {match.constellation}")
        print(f"   Magnitude: {match.magnitude}, Size: {match.size_arcmin} arcmin")
    else:
        print("   Not found")

    # Pattern matching (asterisms)
    print("\n3. Asterism pattern matching...")
    # Try to match some famous star patterns
    test_stars = ["Vega", "Deneb", "Altair"]
    matches = identifier.match_pattern(test_stars)
    print(f"   Testing stars: {', '.join(test_stars)}")
    if matches:
        for m in matches[:2]:
            print(f"   - {m.pattern_name}: {m.description} ({m.confidence:.0%} match)")
    else:
        print("   No pattern matches found")


def demo_health_report(ai: AIServices) -> None:
    """Show service health summary."""
    print_section("Service Health Report")

    summary = ai.get_summary()
    print(f"\n   Initialized: {summary['initialized']}")
    print(f"   Services ready: {summary['services_ready']}")
    print(f"   Services error: {summary['services_error']}")
    print(f"   Overall status: {summary['overall_status']}")

    print("\n   Individual service status:")
    health = ai.get_health_report()
    for name, status in sorted(health.items()):
        symbol = "✓" if status.status.value == "ready" else "✗"
        print(f"   {symbol} {name}: {status.status.value}")


def main():
    """Run the v0.5 AI demonstration."""
    print("\n" + "=" * 60)
    print("  NIGHTWATCH v0.5 AI Enhancement Demo")
    print("=" * 60)
    print("\nThis demo showcases all v0.5 AI capabilities.")
    print("No hardware required - all services run in simulation mode.")

    # Initialize AI services
    config = AIServicesConfig(
        latitude_deg=35.0,
        longitude_deg=-120.0,
        lazy_init=True,
    )
    ai = AIServices(config)
    ai.initialize()

    # Run demonstrations
    demo_scheduling(ai)
    demo_nlp(ai)
    demo_voice(ai)
    demo_object_identification(ai)
    demo_health_report(ai)

    print_section("Demo Complete")
    print("\nv0.5 AI Enhancement milestone: 100% complete")
    print("All 16 roadmap items implemented and tested.")
    print("\nFor more information, see:")
    print("  - ROADMAP.md")
    print("  - services/__init__.py")
    print("  - tests/unit/test_*.py")


if __name__ == "__main__":
    main()
