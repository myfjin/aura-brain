#!/usr/bin/env python3
"""brain_mcp.py — the Brain as an MCP service (the conscious layer, advisory).

The Brain's recognition + floor, exposed as a standard MCP socket so all three of us can
QUERY it. `advise(situation)` runs one grounded node-step (recognition → math front-door →
arbiter floor → resolve) and returns the Brain's ADVICE — non-binding. The caller decides.

Advisory by design: the Brain is UNPROVEN (Beta(1,1), few recorded outcomes) — so it
surfaces suggestions plus its own trust level; it never acts on its own. Trust grows ONLY
as `record_outcome()` feeds real outcomes back (node.close → Beta). This is the "connect us
all to the Brain" piece — same pattern as aura-router, held to the same floor: **it advises,
it does not command.**

Tools:
  advise(situation, recent_actions)     -> the grounded step + the parallel consult lanes
  review(draft, request)                -> the second pass + the L4 conscience axiom (the pause)
  record_outcome(move, held, situation) -> close the loop (did it hold?) → Beta grows

The conscience is wired here (2026-07-10): `advise` surfaces the L3 (ds) + L4 (logic) lanes
alongside the brain move (MATHBRAIN Stage-1 consult, made live), and `review` surfaces the
L4 axiom the draft should be weighed against (PART B, the pause). Both ADDITIVE — existing
keys unchanged; the conscience rides the call sites the gateway already uses.

Run (stdio MCP server):  python3 brain_mcp.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # published settings module (see VENDORING.md)

from constraint_filter import checkable_exprs  # noqa: E402  pure-stdlib, safe at import
import node       # noqa: E402
import outcomes   # noqa: E402  the earned-confidence ledger (recognition + review tracks)
import arbiter    # noqa: E402  the assembled second-pass (rails floor + numeric + depth)
import whypass    # noqa: E402  the why-pass (lie/ego footprints), Tier-1 free
try:              # PART B pause is OPTIONAL: a node missing pause.py/logic_lane.py must
    import pause  # noqa: E402  still run the brain (conscience degrades, never crashes).
except Exception as _pause_err:  # pragma: no cover
    pause = None
    print(f"[brain_mcp] pause layer unavailable ({_pause_err}) — conscience off, brain runs",
          file=sys.stderr)

from mcp.server.fastmcp import FastMCP  # noqa: E402

mcp = FastMCP("aura-brain")


@mcp.tool()
def advise(situation: str, recent_actions: list | None = None, caller: str = "") -> dict:
    """Run one grounded Brain step and return its ADVICE (non-binding): recognition → math
    front-door → arbiter floor → resolve. The Brain suggests; you decide.

    WISDOM LOOP (2026-07-04): every advised move logs a PENDING fire row (fail-open) —
    the harvester later proposes whether the fire caused a stop-to-think, a human
    confirms, and Beta grows as a deliberation counter (outcome-blind). Pass `caller`
    (e.g. 'claude', 'steward', 'illia') so the fire row knows who was advised."""
    s = node.step(situation, recent_actions=recent_actions)
    fired = s.read.get("fired") or []
    top = fired[0] if fired else None
    fire_hash = ""
    if top:
        import wisdom  # local module; log_fire NEVER raises and never writes stdout
        fire_hash = wisdom.log_fire(
            situation=situation, move=top["name"], fire=top["fire"],
            resolution=s.resolution, directive=s.directive,
            proposed=s.proposed or "", trust=str(top.get("trust", "")), caller=caller)
    # CONSULT LANES (MATHBRAIN Stage-1, made live): L3 ds · L4 logic, run on the same
    # situation, INDEPENDENT of the brain move, advisory. Recognition-only here (advise
    # already logged the brain fire; the lane fires belong to consult_all/pause). Fail-open.
    consult = {}
    for lname, lfn in (("ds", node._lane_ds), ("logic", node._lane_logic)):
        try:
            L = lfn(situation)
            entry = {"fired": L.fired, "suggestion": L.suggestion,
                     "confidence": L.confidence, "witness": L.witness}
            if lname == "logic" and L.fired and L.detail:
                rv = L.detail.get("review") or {}
                entry.update({
                    "strength": L.detail.get("strength"),
                    "trust": rv.get("trust", "unreviewed"),
                    "constraints": checkable_exprs(L.detail.get("post_conditions"), limit=3),
                    "belief": L.detail.get("belief", ""),
                })
            consult[lname] = entry
        except ImportError as e:
            # An OPTIONAL dependency that is not installed (chromadb, sympy) is a
            # documented condition, not a broken lane. Reporting it as `error` makes
            # it indistinguishable from a dead lane — which is how a real defect hid
            # (an empty registry raised ValueError and read as "the lane is broken").
            consult[lname] = {"fired": False, "skipped": f"optional dependency absent: {e}"}
        except Exception as e:  # a broken lane must not sink advise
            consult[lname] = {"fired": False, "error": f"{type(e).__name__}: {e}"}

    # APTNESS selftest (mechanism #2 — end loose-recognition false alarms): score the
    # surfaced move BEFORE it goes out, LOUD-FIRST (the score is shown; only a HARD fail —
    # a proven tautology / axiom-violation — argues for suppression). Fail-open.
    apt = None
    if top:
        try:
            import aptness, recognition
            cands = [(f["name"], f.get("fire", 0.0)) for f in fired]

            def _recall(sit):
                rr = recognition.recall(sit).get("fired") or []
                return [(f["name"], f.get("fire", 0.0)) for f in rr]

            rep = aptness.aptness(situation, top["name"], cands, recall_fn=_recall, lane="brain")
            apt = {"score": rep.score, "verdict": rep.verdict, "hard_fail": rep.hard_fail,
                   "checks": [{"name": c.name, "applicable": c.applicable,
                               "passed": c.passed, "detail": c.detail} for c in rep.checks]}
        except ImportError as e:  # optional dependency absent — documented, not a defect
            aptness = {"skipped": f"optional dependency absent: {e}"}
        except Exception as e:  # aptness must never break advise
            apt = {"error": f"{type(e).__name__}: {e}"}

    # ADVICE-CITIZENSHIP (mechanism #1 — end cross-dialogue leakage): is the surfaced move
    # domain-coherent with THIS prompt, or a leak (an ops move in a stats dialogue)? LOUD-
    # FIRST + SOFT — we FLAG + suggest an in-domain alternative, never auto-swap (the penalty
    # is not yet calibrated). Fail-open: no domains built / any error → no block.
    domain = None
    if top:
        try:
            import advice_domain
            cands = [(f["name"], f.get("fire", 0.0)) for f in fired]
            ranked, swapped = advice_domain.rerank(situation, cands)
            _, prompt_dom = advice_domain.domain_of(situation)
            mine = next((r for r in ranked if r["move"] == top["name"]), {})
            domain = {"prompt_domain": prompt_dom,
                      "move_coherent": mine.get("cross") is False,
                      "note": mine.get("note", ""),
                      "suggest_instead": ranked[0]["move"] if swapped else None}
        except ImportError as e:  # optional dependency absent — documented, not a defect
            domain = {"skipped": f"optional dependency absent: {e}"}
        except Exception as e:  # citizenship must never break advise
            domain = {"error": f"{type(e).__name__}: {e}"}

    return {
        "situation": situation,
        "resolution": s.resolution,                 # MATH | FLOOR | ACT | ESCALATE
        "binding": s.resolution == "FLOOR",         # only a rail-floor is non-overridable
        "directive": s.directive,
        "advice": ({"move": top["name"], "do": top.get("present_action", ""),
                    "id": top.get("id"),   # stable identity (B1) — grade against this
                    "fire": top["fire"], "trust": top["trust"],
                    # read-back: where this move has BROKEN, vs THIS situation (out loud)
                    "pain": top.get("pain"),
                    # ── RANK-1 IS NOT THE ANSWER — MEASURED 2026-08-22 ───────────────
                    # BRAIN_RECOGNITION_ROUND1.md: over 41 calls (9 situations x 5
                    # paraphrases), rank-1 was apt in 53.7%; an apt move was present
                    # in the top-3 in 85.4% (+31.7 pts). Rank-1 also FLIPS under
                    # paraphrase: 0/9 situations kept the same rank-1 across their 5
                    # paraphrases. Random control 19.4%/20.0% — retrieval IS working,
                    # the ORDERING is not. So surface the SET and let the caller pick.
                    # ⛔ Deliberately NOT gated on `gap`: gap does not predict aptness
                    #    (52.4% low-gap vs 55.0% high-gap). top1 looked predictive
                    #    (42.9% vs 65.0%) but is underpowered (9/21 vs 13/20) — not
                    #    earned, so no threshold is applied to either.
                    "rank1_reliability": "53.7% apt alone; 85.4% within this set",
                    "alternates": [{"move": f["name"], "id": f.get("id"),
                                    "fire": f.get("fire"),
                                    "do": (f.get("present_action") or "")[:220]}
                                   for f in fired[1:3]]} if top else None),
        "consult": consult,                         # L3 ds + L4 logic lanes (parallel consult, live)
        "aptness": apt,                             # mechanism #2: pre-advice aptness score (loud-first)
        "domain": domain,                           # mechanism #1: advice-citizenship (cross-dialogue leak flag)
        "math": s.math,                             # exact result if it was a computation
        "floor_label": s.floor_label,
        "novel": s.read.get("novel"),
        "fire_hash": fire_hash,                     # wisdom-loop pending row (grade later)
        "note": "ADVISORY — the Brain suggests; the caller decides. Trust is earned, not asserted.",
    }


@mcp.tool()
def review(draft: str, request: str = "", recent_actions: list | None = None) -> dict:
    """The mandatory SECOND PASS on a DRAFT, before you send it — ADVISORY, Tier-1, FREE.

    The Brain interrogates the draft you're about to send (whypass's own thesis: a single
    forward pass can't ask itself 'why' — a second pass that examines the first can). It runs:
      • the WHY-PASS (the locked LIE floor: A6 claimed-not-checked, A4 status>function,
        A5 over-determined) — 'are you about to lie / posture / over-claim?'
      • the NUMERIC floor (A7) — a computed assertion that doesn't hold under its frame,
      • the DEPTH/register read — 'what STYLE does this ask actually want?',
      • the R3 stuck-loop check on recent_actions (if given).

    Mandatory to HEAR, optional to OBEY — EXCEPT a fired FLOOR (an honesty rail), which stays
    binding by our own agreement. `binding` is True only then. Everything else: you decide.
    For a genuine SEMANTIC self-interrogation (not just tells), escalate to a Tier-2 paid pass
    (gated + capped) — not this call."""
    d = arbiter.arbitrate(request=request or None, draft=draft, recent_actions=recent_actions)
    lie = whypass.why_pass(draft, request or None)  # explicit lie/ego footprints (want #1)

    # THE PAUSE (PART B, live): also weigh the draft against the L4 conscience — the axiom
    # this draft is in the territory of, with its constraints + strength + Ver-trust. The
    # ✓/✗ verdict is left "?" (deterministic surfacing; the verdict is Haiku-gated). Surfacing
    # an axiom logs a lane-tagged fire so the pause grades via the ONE wisdom loop. Fail-open:
    # a degraded conscience must never break the second pass (the ego floor still binds).
    axiom, axiom_note = (pause._axiom(draft) if pause is not None
                         else (None, "pause layer unavailable on this node"))
    axiom_fire = ""
    if axiom:
        try:
            import wisdom
            axiom_fire = wisdom.log_fire(situation=draft, move=axiom["axiom_id"], fire=0.0,
                                         resolution="PAUSE", lane="logic", caller="review")
        except Exception:  # fail-open
            pass
    return {
        "draft_preview": draft[:200],
        "verdict": d.mode,                                  # RAIL | DEPTH | NONE
        "binding": d.floor,                                 # True ONLY when an honesty rail fired
        "rail": d.label if d.floor else None,               # A6 | A4 | A5 | A7 | R3
        "directive": d.directive,
        "lie_footprints": lie,                              # [] = clean on the lie floor
        "axiom": axiom,                                     # L4 conscience: constraint to weigh (or None)
        "axiom_note": axiom_note,                           # e.g. recognized-but-hollow
        "axiom_fire": axiom_fire,                           # wisdom-loop pending row for the pause
        "style": d.label if d.mode == "DEPTH" else None,    # register/depth the ask wants
        "signals": d.signals,
        "note": ("ADVISORY second-pass, Tier-1 (free) — now also the PAUSE (L4 axiom surfaced). "
                 "Mandatory to HEAR, optional to OBEY — except a fired FLOOR (honesty rail), "
                 "binding by agreement. Verdict on the axiom is '?' (deterministic; ✓/✗ is "
                 "Tier-2/Haiku-gated). Trust earned via record_outcome, not asserted."),
    }


@mcp.tool()
def record_outcome(move: str, held: bool, situation: str = "") -> dict:
    """Close the loop: did the advised move actually HOLD? Feeds node.close → outcomes →
    Beta, so the Brain's trust GROWS from real evidence (the only path to graduation)."""
    # Guard: a bad move (unknown pattern) or any record error must NOT drop the MCP
    # connection. Return the error to the caller; never let an exception escape the tool.
    try:
        conf = node.close(move, held, situation=situation)
    except Exception as e:
        return {"move": move, "held": held, "recorded": False,
                "error": f"{type(e).__name__}: {e}",
                "note": ("outcome NOT recorded — `move` must be a library pattern name "
                         "(from advise()'s advice.move). A review() verdict (DEPTH/A6/style) "
                         "is not a library move and has no outcome channel yet.")}
    return {"move": move, "held": held, "recorded": True, "confidence": conf,
            "note": "outcome recorded; Beta updated. Trust earned, not asserted."}


@mcp.tool()
def record_review_outcome(verdict: str, held: bool, situation: str = "", draft_hash: str = "") -> dict:
    """Close the loop on a review() SECOND-PASS verdict — its OWN trust track, separate from
    advise()'s recognition moves. `verdict` is the label review() returned: a rail ('A6',
    'A4', 'A5', 'A7', 'R3'), a depth style ('DEPTH:ANSWER_DIRECT', …), or 'NONE'.
    held=True = the read was RIGHT (a flagged lie was real / the style read fit); held=False
    = it misfired. This is how the second-pass EARNS trust — per-rail precision graded from
    real drafts, the only path off `unproven` for review().

    Pass `draft_hash` (from grade_queue's list, or the stream row) to also mark that fire
    graded in the review-verdict stream — so the ungraded-fires queue stays accurate no
    matter which path did the grading."""
    try:
        conf = outcomes.record_review(verdict, held, situation=situation, draft_hash=draft_hash)
    except Exception as e:
        return {"verdict": verdict, "held": held, "recorded": False,
                "error": f"{type(e).__name__}: {e}"}
    return {"verdict": verdict, "held": held, "recorded": True, "confidence": conf,
            "note": "review-verdict outcome recorded on its own track; Beta updated. Earned, not asserted."}


if __name__ == "__main__":
    mcp.run()
