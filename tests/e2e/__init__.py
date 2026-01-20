"""
NIGHTWATCH End-to-End Tests Package

End-to-end tests verify the complete system behavior from
voice input through to telescope/observatory response.

Test Categories:
- Voice pipeline tests: STT -> LLM -> Tool -> TTS
- Observing session tests: Start session, slew, capture, end
- Safety tests: Emergency shutdown, weather alerts
- Integration tests: Full system with simulators

Running E2E Tests:
    # Run all e2e tests
    pytest tests/e2e/ -v

    # Run specific test category
    pytest tests/e2e/test_voice_pipeline.py -v

    # Run with simulators (requires docker)
    pytest tests/e2e/ -v --use-simulators

Fixtures:
    - orchestrator: Configured Orchestrator with mock services
    - voice_pipeline: Complete voice pipeline with mock STT/TTS
    - simulator_env: Docker environment with all simulators

Note: E2E tests may take longer than unit tests as they
exercise the full system. Use pytest-timeout to prevent hangs.
"""

import pytest
from typing import Optional


# Mark all tests in this package as e2e
pytestmark = pytest.mark.e2e


def pytest_configure(config):
    """Register custom markers for e2e tests."""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "requires_simulators: mark test as requiring Docker simulators"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# Package version
__version__ = "0.1.0"
