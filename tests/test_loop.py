"""End-to-end: does the loop actually run — and does it fail where it should?

These tests run the real core against the SYNTHETIC fixtures. They are not a
benchmark: a number that comes out of here means nothing about how well the
brain works. They answer one question only — *can a stranger run this at all,
and does it behave sanely when it has no data?*

The negative control is the important one. A lane that fires on everything, or
that reports an error where it should report "not fired", is a lane nobody can
measure.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

FIRES_SITUATION = (
    "I am about to report that the checker passes, but I only ran it on the "
    "well-formed input. Should I claim it works?"
)
NULL_SITUATION = "ok. and then?"


def _home() -> Path:
    """The synthetic deployment conftest.py prepared before the core was imported."""
    return Path(os.environ["AURA_BRAIN_HOME"])


def test_advise_returns_a_set_not_a_single_move() -> None:
    """advise() must always answer, and must answer with the whole consult, not rank-1."""
    import aura_brain

    r = aura_brain.advise(FIRES_SITUATION, caller="fixture")
    assert isinstance(r, dict)
    for key in ("resolution", "advice", "consult", "situation"):
        assert key in r, f"advise() dropped {key!r}: {sorted(r)}"
    assert isinstance(r["consult"], dict), "the per-lane consult report must be present"


def test_outcome_lands_in_the_ledger() -> None:
    """A consult that writes no row did not happen."""
    import aura_brain

    before = (_home() / "outcomes.jsonl").read_text().strip().splitlines()
    aura_brain.record_outcome(
        "synthetic-verify-before-claiming", held=True, situation=FIRES_SITUATION
    )
    after = (_home() / "outcomes.jsonl").read_text().strip().splitlines()
    assert len(after) == len(before) + 1, "record_outcome() did not append to the ledger"
    row = json.loads(after[-1])
    assert row.get("held") is True
    assert row.get("pattern") == "synthetic-verify-before-claiming"


def test_negative_control_reports_not_fired_without_an_error() -> None:
    """A situation that should not fire must say so — cleanly.

    Two failure modes this pins, and they are different:
      * an input that fires when it should not  -> the fixture is rigged;
      * a lane that reports an ERROR where the honest answer is "below threshold"
        -> the lane looks measured while being dead.

    The second is the one that bit us in production: a missing registry raised
    ``ValueError: need at least one array to concatenate``, which surfaced as a
    lane error rather than as "not fired".
    """
    import aura_brain

    r = aura_brain.advise(NULL_SITUATION, caller="fixture")
    consult = r["consult"]
    assert consult, "no lanes reported at all"
    errored = {name: v.get("error") for name, v in consult.items() if v.get("error")}
    assert not errored, f"lane(s) errored on a null input instead of not firing: {errored}"
    # A lane may legitimately be SKIPPED: the embedder is an optional extra, and its
    # absence is a documented condition, not a defect. What must never happen is an
    # absent dependency surfacing as `error` — that is indistinguishable from a dead
    # lane, which is how a real defect hid. If a lane is skipped it must say why.
    for name, v in consult.items():
        if "skipped" in v:
            assert v["skipped"], f"lane {name!r} skipped without saying why"
    fired = [name for name, v in consult.items() if v.get("fired")]
    assert not fired, f"null input fired {fired} — either the fixture is rigged or a lane is greedy"
