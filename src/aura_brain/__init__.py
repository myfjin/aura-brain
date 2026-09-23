"""aura-brain — an advice organ for a small crew.

The LLM decides; aura-brain helps it decide deeper and wider.

**0.2.0** lands the core. The loop is: ``advise`` a situation → the agent decides
→ the agent records the outcome → the derived rate moves. Everything under
``_core/`` is vendored, unchanged except for its data paths, from the system we
run in production — see ``VENDORING.md`` for why, and what that costs.

Nothing in this package reads anyone's private corpus. All paths come from
``aura_brain._core.paths`` and default to an empty ``~/.aura-brain``, so every
lane fails open with a loud warning until you point it at your own data.

The public API is two calls: :func:`advise` and :func:`record_outcome`.
"""

from __future__ import annotations

import os as _os
import sys as _sys

__version__ = "0.2.0"

# The vendored core keeps the flat-import idiom it grew up with (`import outcomes`,
# `import paths`). Putting its directory on sys.path lets those resolve unchanged,
# which is what keeps the published copy diffable against the canonical tree.
_CORE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "_core")
if _CORE not in _sys.path:
    _sys.path.insert(0, _CORE)


def advise(
    situation: str, recent_actions: list | None = None, caller: str = ""
) -> dict:
    """Ask the brain about a situation. Returns a dict; never raises on a bad lane.

    The returned set — not its rank-1 — is the signal: read ``moves`` (top-3 plus
    alternates) and ``consult`` (which lanes fired, and whether any errored).
    """
    from aura_brain._core import brain_mcp

    return brain_mcp.advise(situation, recent_actions=recent_actions, caller=caller)


def record_outcome(move: str, held: bool, situation: str = "") -> dict:
    """Record whether a move actually helped. This is the only signal the engine lacks.

    Influence requires the advice to have arrived BEFORE the action; a consult made
    after the fact is not a \"held\" — record it honestly and the rate stays honest.
    """
    from aura_brain._core import brain_mcp

    return brain_mcp.record_outcome(move, held, situation=situation)


__all__ = ["__version__", "advise", "record_outcome"]
