"""Smoke tests for the aura-brain scaffold.

These land here so CI has something honest to run against the 0.1.0
scaffold. They will grow as the beachhead source lands.
"""

import re

import aura_brain


def test_version_is_pep440_style() -> None:
    """The declared version must parse as X.Y.Z."""
    assert re.fullmatch(r"\d+\.\d+\.\d+", aura_brain.__version__), aura_brain.__version__


def test_package_exports_the_public_loop() -> None:
    """The package exposes the loop, not its internals."""
    assert set(aura_brain.__all__) == {"__version__", "advise", "record_outcome"}
    assert callable(aura_brain.advise)
    assert callable(aura_brain.record_outcome)
