"""Shared pytest fixtures for the RiskID Workbench suite.

The :func:`fixture_org` fixture builds the fixture organisation (round 3,
PLAN.md section 4) in a temporary directory so that every test works on a
fresh ``.riskid`` file and later rounds can reuse the same organisation
without re-deriving it.
"""

import sys
from pathlib import Path

import pytest

# make_org lives in tests/fixtures and is not a package; put it on the path so
# both the fixture and the tests can import it by name.
_FIXTURES_DIR = Path(__file__).parent / "fixtures"
if str(_FIXTURES_DIR) not in sys.path:
    sys.path.insert(0, str(_FIXTURES_DIR))

import make_org  # noqa: E402


@pytest.fixture
def fixture_org(tmp_path):
    """A freshly built fixture-organisation store, opened for the test."""
    store = make_org.build_org(tmp_path / "org.riskid")
    try:
        yield store
    finally:
        store.close()
