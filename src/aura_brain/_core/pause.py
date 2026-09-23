#!/usr/bin/env python3
"""pause.py — PART B: the "I care" pause (deterministic), grounding the existing floor.

4Q's heart + Gemini's dialogue: the pause is the space between a drafted reply and speaking
it, where the model checks itself against validated truth. "I care" == "held" == the pause
HAPPENED (deliberation), outcome-blind — the wisdom-loop's locked law. This is NOT a new
grader and NOT a rebuild of the floor: it COMPOSES two organs already built —

  1. whypass.why_pass  — the ego floor (A4 status>function · A5 over-determined ·
                          A6 claimed-not-checked). The PUBLIC twin, untouched. [ground it]
  2. logic_lane.logic_need — L4 the conscience: recognizes the axiom the draft is in the
                          territory of, and surfaces its CHECKABLE constraints + strength
                          + Ver-trust. [the private registry — kept OUT of whypass so the
                          public twin stays clean].

DELIBERATELY DETERMINISTIC (my lean, Illia's go 07-10): the pause SURFACES the constraint
to weigh the draft against; it does NOT compute the ✓ pass / ✗ violation verdict. A real
verdict needs symbolic eval where the claim is evaluable, or a Tier-2 LLM pass (whypass
Tier-2) — that is Haiku-BUDGET-GATED and left for the conscious layer to resolve. So every
surfaced axiom carries verdict "?" with its constraints shown. Honest floor: put the right
thing in front of the layer, loud; the catch is the layer's move.

NOT mandatory-every-response: the axiom-check is threshold-gated (logic_need fires or stays
quiet) — proportional, like advise. NOT a humility quota: we measure CALIBRATION by SHOWING
the axiom's strength (recovery/weak) and trust (ver-corroborated/…), honesty in BOTH
directions — never dressing "unproven" as 50%.

Grade via the ONE wisdom loop: when the pause surfaces an axiom it logs a lane-tagged fire
(caller="pause"); held = the pause happened + the axiom was weighed, outcome-blind.

  python3 pause.py "your draft text here"
  python3 pause.py --selftest
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from constraint_filter import checkable_exprs  # noqa: E402  pure-stdlib, safe at import

VERDICT_UNRESOLVED = ("? uncertain — deterministic surfacing only; resolve by weighing the "
                      "constraints, or a Tier-2 pass (Haiku-gated)")


@dataclass
class PauseResult:
    draft: str
    footprints: list                 # [{footprint, directive}] — whypass ego floor (A4/A5/A6)
    axiom: dict | None = None        # {axiom_id, belief, constraints, strength, trust, witness, verdict}
    note: str = ""                   # degradation / recognized-but-hollow notes
    logged: str = ""                 # fire_hash when a fire was logged, else ""

    def held(self) -> bool:
        """The 'I care' signal: did the pause DO something — catch an ego footprint OR
        surface a checkable axiom? Outcome-blind: held is the stop-to-think, not the verdict."""
        return bool(self.footprints or self.axiom)


def _footprints(draft: str, request: str | None) -> tuple[list, str]:
    try:
        import whypass
        return whypass.why_pass(draft, request), ""
    except Exception as e:  # fail-open: the ego floor degrading must not sink the pause
        return [], f"whypass unavailable ({type(e).__name__}: {e})"


def _axiom(draft: str) -> tuple[dict | None, str]:
    """Recognize the axiom the DRAFT is in the territory of (the claim being made), and
    surface its constraints. Returns (axiom_dict | None, note)."""
    try:
        import logic_lane
        r = logic_lane.logic_need(draft, defer_log=False)
        if not r.fired:
            return None, ""
        # TWO-AXIS gate (honest-pass 07-23): surface the constraint when there IS one
        # (strength != none). Do NOT suppress on is_axiom — that now means ORACLE-BACKED,
        # and a green-run recovery/weak candidate still carries a real assert worth weighing.
        # The honest floor is preserved: strength == none (hollow-only) → nothing to hand over.
        if r.strength == "none":
            return None, (f"recognized {r.axiom_id} but it carries NO checkable constraint "
                          f"(hollow asserts only) — nothing to weigh against")
        rv = r.review or {}
        oracle = r.oracle or {}
        ax = {
            "axiom_id": r.axiom_id,
            "belief": r.belief,
            # falsifiable constraints only — weighing a draft against `False` is theater
            "constraints": checkable_exprs(r.post_conditions),
            "strength": r.strength,
            "trust": rv.get("trust", "unreviewed"),
            # confidence axis: is this claim independently oracle-verified, or green-run only?
            "oracle_backed": bool(r.is_axiom),
            "oracle_tier": oracle.get("tier", "candidate"),
            "oracle_kinds": oracle.get("kinds", []),
            "basis": r.basis or ("oracle-backed" if r.is_axiom else "green-run-candidate"),
            "witness": r.witness,
            "verdict": VERDICT_UNRESOLVED,
        }
        if rv.get("trust") == "ver-twin-rejected":
            ax["caveat"] = f"⚠ Ver rejected this pattern's twin — {rv.get('note', '')[:120]}"
        return ax, ""
    except Exception as e:  # fail-open: the conscience degrading falls back to the ego floor
        return None, f"logic_lane unavailable ({type(e).__name__}: {e})"


def pause(draft: str, request: str | None = None, log: bool = True,
          fires_path: Path = None) -> PauseResult:
    """The deepened pause on an outgoing DRAFT: ego footprints (whypass) + the axiom the
    draft should be weighed against (L4). Deterministic; the ✓/✗ verdict is NOT computed."""
    fps, note1 = _footprints(draft, request)
    ax, note2 = _axiom(draft)
    note = "; ".join(n for n in (note1, note2) if n)

    logged = ""
    if log and ax:
        try:
            import wisdom
            logged = wisdom.log_fire(situation=draft, move=ax["axiom_id"], fire=0.0,
                                     resolution="PAUSE", lane="logic", caller="pause",
                                     fires_path=fires_path)
        except Exception as e:  # fail-open
            print(f"[pause] fire-logging fail-open: {e}", file=sys.stderr)
    return PauseResult(draft, fps, ax, note, logged)


def render(p: PauseResult) -> str:
    """Human-readable pause — what the conscious layer reads BEFORE speaking."""
    lines = [f"— pause on draft: {p.draft[:70]!r} —"]
    if not p.held():
        lines.append("  ✓ nothing caught: no ego footprint, no axiom in territory. Speak.")
    if p.footprints:
        lines.append("  ego floor (whypass):")
        for f in p.footprints:
            lines.append(f"    ⚑ {f['footprint']}: {f['directive'][:100]}")
    if p.axiom:
        a = p.axiom
        evidence = (f"ORACLE-BACKED·{a['oracle_tier']}" if a.get("oracle_backed")
                    else "green-run candidate (no independent oracle)")
        lines.append(f"  conscience (L4): {a['axiom_id']}  "
                     f"[strength {a['strength']} · trust {a['trust']} · evidence {evidence}]")
        lines.append(f"    belief:  {a['belief'][:120]}")
        lines.append(f"    weigh your draft against: {a['constraints'][:3]}")
        if a.get("caveat"):
            lines.append(f"    {a['caveat']}")
        lines.append(f"    verdict: {a['verdict']}")
    if p.note:
        lines.append(f"  note: {p.note}")
    lines.append(f"  held={p.held()} (I care = the pause happened; outcome-blind).")
    return "\n".join(lines)


def selftest() -> int:
    checks = []

    # 1. an overclaiming draft → ego footprints fire (A5/A6), pause held.
    p1 = pause("This is definitely fixed and I successfully verified everything works.",
               log=False)
    checks.append(("overclaim draft → ego footprints fire", bool(p1.footprints)))
    checks.append(("overclaim pause held", p1.held() is True))

    # 2. a draft about a DS method → the L4 axiom surfaces with constraints + strength + trust.
    p2 = pause("The A/B test shows the conversion difference is statistically significant.",
               log=False)
    checks.append(("method draft → axiom surfaced", p2.axiom is not None))
    checks.append(("axiom carries constraints to weigh against",
                   bool(p2.axiom and p2.axiom.get("constraints"))))
    checks.append(("axiom carries strength + trust (calibration, both directions)",
                   bool(p2.axiom and p2.axiom.get("strength") and p2.axiom.get("trust"))))
    checks.append(("axiom carries oracle evidence axis (backed + tier + basis)",
                   bool(p2.axiom and "oracle_backed" in p2.axiom
                        and p2.axiom.get("oracle_tier") and p2.axiom.get("basis"))))
    checks.append(("verdict left UNRESOLVED (not faked ✓/✗)",
                   bool(p2.axiom) and p2.axiom["verdict"].startswith("?")))

    # TWO-AXIS regression guard (honest-pass 07-23): a pattern with a REAL constraint
    # (strength != none) but NO oracle backing (is_axiom False) must STILL surface — the
    # honest pass must not silence green-run candidates. Simulated via a stub LogicNeed.
    import logic_lane as _ll
    _stub = _ll.LogicNeed(
        fired=True, axiom_id="stub_candidate", confidence=0.9,
        belief="stub guarantees x > 0", post_conditions=[{"expr": "x > 0"}],
        witness="python3 stub.py", candidates=[("stub_candidate", 0.9)],
        strength="recovery", is_axiom=False, oracle={"tier": "candidate", "kinds": []},
        basis="green-run-candidate", review={"trust": "unreviewed"})
    _orig = _ll.logic_need
    try:
        _ll.logic_need = lambda *a, **k: _stub
        pc = pause("some draft in stub territory", log=False)
    finally:
        _ll.logic_need = _orig
    checks.append(("green-run candidate (real constraint, NO oracle) STILL surfaces",
                   pc.axiom is not None and pc.axiom.get("oracle_backed") is False
                   and pc.axiom.get("constraints") == ["x > 0"]))

    # 3. a clean, humble draft → no footprints; pause may be empty (held False is honest).
    p3 = pause("I haven't verified this yet — let me open the file and check.", log=False)
    checks.append(("humble draft → no ego footprint", not p3.footprints))

    # 4. a draft that is BOTH an overclaim AND about a method → both organs speak.
    p4 = pause("The A/B test definitely proves it — I successfully confirmed significance.",
               log=False)
    checks.append(("both-organs draft → footprints AND axiom",
                   bool(p4.footprints) and p4.axiom is not None))

    # 5. surfacing an axiom logs a lane-tagged fire (temp stream — never the real one).
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / "fires.jsonl"
        p5 = pause("the A/B conversion difference is significant", log=True, fires_path=fp)
        import json
        rows = ([json.loads(x) for x in fp.read_text().splitlines() if x.strip()]
                if fp.exists() else [])
        checks.append(("pause fire is logged + lane-tagged 'logic', caller 'pause'",
                       bool(p5.logged) and any(r.get("lane") == "logic"
                       and r.get("caller") == "pause" for r in rows)))

    # 6. held is outcome-blind — it is TRUE whenever something surfaced, regardless of verdict.
    checks.append(("held = something surfaced (outcome-blind)",
                   p2.held() is True and p4.held() is True))

    ok = 0
    for name, passed in checks:
        print(f"  {'✓' if passed else '✗ FAIL'}  {name}")
        ok += passed
    print(f"\n{ok}/{len(checks)} checks passed"
          + ("" if ok == len(checks) else " — FIX BEFORE TRUSTING"))
    return 0 if ok == len(checks) else 1


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    if sys.argv[1] == "--selftest":
        raise SystemExit(selftest())
    print(render(pause(" ".join(sys.argv[1:]))))


if __name__ == "__main__":
    main()
