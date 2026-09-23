"""Smoke tests for the package surface.

The loop itself is covered in ``test_loop.py``. These tests only pin what the
package exposes and how it names itself — the surface a user meets first.
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
