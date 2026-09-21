"""Smoke tests for the aura-brain scaffold.

These land here so CI has something honest to run against the 0.1.0
scaffold. They will grow as the beachhead source lands.
"""

import re

import aura_brain


def test_version_is_pep440_style() -> None:
    """The declared version must parse as X.Y.Z."""
    assert re.fullmatch(r"\d+\.\d+\.\d+", aura_brain.__version__), aura_brain.__version__


def test_package_exports_version_only() -> None:
    """0.1.0 is a scaffold; __all__ must be minimal and match __version__."""
    assert aura_brain.__all__ == ["__version__"]
