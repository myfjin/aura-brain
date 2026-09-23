#!/usr/bin/env python3
"""constraint_filter.py — the single gate between the registry and every reader (2026-07-26).

WHY THIS EXISTS (external bug report, Mark's Claude, 2026-07-26):
114 signed library cards carried a "Checkable constraint" that read `False`.

The extractor was NOT wrong. `assert False, "should have raised ValueError"` is the
unreachable-marker idiom of a GOOD pattern — it causes the disaster and proves the
error is raised (THE ONE LAW). logic_extract.py records it faithfully and tags it
`tier=hollow, tag=assert-constant`, and the belief-sentence builder already drops it.

The defect was that six independent readers re-rendered post_conditions RAW, ignoring
the tag the extractor took the trouble to write: gen_pattern_docs.py (→ signed cards),
pause.py (→ the "I care" gate), brain_mcp.py, i_care.py, node.py, logic_lane.py.
A constraint that reads `False` asserts nothing: it is unfalsifiable noise in exactly
the field a skeptical buyer inspects first, and weighing a draft against it is theater.

So the gate lives HERE, once, and every reader goes through it. Adding a reader that
prints `[p["expr"] for p in post_conditions]` directly reintroduces the bug.

TWO INDEPENDENT GATES, deliberately redundant (verify-the-verification):
  1. the extractor's tag  (`assert-constant`)
  2. the expression itself parsing to a bare constant literal
Either one alone catches today's 192 rows. Both together mean a future extractor that
forgets the tag, or one that emits `True`/`None`/`0` under some new tag, still cannot
put an unfalsifiable claim on a signed artifact.

This filters PRESENTATION only. Nothing here mutates the registry: the hollow rows stay
on disk, carrying their `msg` ("should have raised ValueError on missing binary") as the
audit trail of the negative test, and `strength` is still computed over the full set.
"""
from __future__ import annotations

# Bare literals that assert nothing, across the library's five languages.
# (Python/Go/Rust/C++/R spellings — the registry is fed by five extractors.)
_CONSTANT_EXPRS = {
    "False", "True", "None", "null", "nil",
    "false", "true", "FALSE", "TRUE", "NULL", "NA",
    "0", "1", "-1", "0.0", "1.0", "''", '""', "``",
}

# Tags the extractors use to mark a constant-valued assert.
_CONSTANT_TAGS = {"assert-constant"}


def is_checkable(pc: dict) -> bool:
    """True if this post-condition states something a reader could actually falsify.

    A missing/empty expr is not checkable. A bare constant is not checkable — it has the
    same truth value on every input, so it pins nothing about the pattern's behaviour.
    """
    if not isinstance(pc, dict):
        return False
    expr = str(pc.get("expr") or "").strip()
    if not expr:
        return False
    if pc.get("tag") in _CONSTANT_TAGS:      # gate 1: the extractor already said so
        return False
    if expr in _CONSTANT_EXPRS:              # gate 2: it reads as a bare literal anyway
        return False
    return True


def checkable_exprs(post_conditions, limit: int | None = None) -> list[str]:
    """The constraint expressions fit to show a reader, junk removed.

    `limit` is applied AFTER filtering — so a truncated list spends its slots on real
    constraints instead of on `False` (this alone restored a real constraint to 31 rows
    that the pre-filter [:8] cap had pushed off the card)."""
    out = [str(p["expr"]).strip() for p in (post_conditions or []) if is_checkable(p)]
    return out[:limit] if limit else out


def selftest() -> int:
    real = {"expr": "sum(received['i']) == 100", "tag": "eq-literal", "tier": "recovery"}
    tagged = {"expr": "False", "tag": "assert-constant", "tier": "hollow",
              "msg": "should have raised ValueError on missing binary"}
    untagged = {"expr": "False", "tag": "some-future-tag", "tier": "weak"}
    other_const = {"expr": "True", "tag": "bare-flag", "tier": "hollow"}
    weak_but_real = {"expr": "ok", "tag": "bare-flag", "tier": "hollow"}
    empty = {"expr": "", "tag": "no-check", "tier": "hollow"}

    checks = [
        ("a real constraint survives", is_checkable(real)),
        ("the tagged constant is dropped", not is_checkable(tagged)),
        ("an UNTAGGED `False` is still dropped (gate 2)", not is_checkable(untagged)),
        ("a bare `True` is dropped even under another tag", not is_checkable(other_const)),
        ("a hollow-but-named flag SURVIVES (we drop constants, not weak claims)",
         is_checkable(weak_but_real)),
        ("an empty expr is dropped", not is_checkable(empty)),
        ("not a dict → dropped, never raises", not is_checkable("False")),
        ("limit is applied after filtering",
         checkable_exprs([tagged, real, weak_but_real], limit=2) == [real["expr"], "ok"]),
        ("empty input → empty list", checkable_exprs(None) == []),
    ]
    bad = 0
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
        bad += not ok
    print(f"\n{len(checks) - bad}/{len(checks)} passed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(selftest())
