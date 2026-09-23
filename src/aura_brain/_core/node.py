#!/usr/bin/env python3
"""node.py — the grounded node-step. First node of the architecture locked 2026-06-28.

(Not to be confused with loop.py, which is the parallel-SIMULATION Loop object. This
is the live per-node step that replicates across .5/.8/.13: floor local on each node,
brain singular and shared from .5.)

ONE node-step joins the two organs that already exist:
  the BRAIN  (recognition.recall — the singular soul on .5) hands back a move →
  the FLOOR  (arbiter.arbitrate — the local rails) vets it BEFORE it is emitted →
  resolve   → record the OUTCOME so confidence (Beta) is EARNED, never asserted.
Self-redirecting: each step's result is carried into the next step's situation.

THE HONEST GATE (the maturation path), in precedence order:
  1. FLOOR binds          → rail wins, non-overridable (R3 failure-loop / A6 overclaim)
  2. move fired + PROVEN   → ACT autonomously ("the brain directly tells what to do")
  3. otherwise             → ESCALATE to conscious; the move is ADVISORY only

Every move starts UNPROVEN (Beta(1,1)), so TODAY the node advises + escalates —
nothing acts blind. As real outcomes are recorded (outcomes.record / node.close),
moves cross the act-gate and graduate to autonomous. This is *why* the known-bad
novelty threshold can't hurt us yet: the gate to ACTION is earned TRUST, not raw
similarity. Similarity only chooses which move to advise; trust decides whether to act.

NOTE (honest scope): the A6 floor properly vets the node's real OUTGOING DRAFT — the
response produced by the conscious/generator step. Here we vet the brain's proposed
action as a stand-in; full A6 vetting lands when the generator is wired in. R3
(action history) already applies cleanly.

Run: python3 node.py            # demo: real situations through one grounded step
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths  # published settings module (see VENDORING.md)

# SH-T7.9: module-level imports made lazy — the beachhead 7-file set does not
# include constraint_filter, brain, recognition, arbiter, or math_need.  Making
# them lazy lets the file import cleanly without the full mesh installed.
# node.run() / re-anchor is OUT OF SCOPE for the beachhead — a contributor who
# needs it must install the full lab-from-future-brain tree.
def _lazy_import(name):
    import importlib
    return importlib.import_module(name)

constraint_filter = None
brain = None
recognition = None
arbiter = None
outcomes = None
math_need = None

def _ensure_deps():
    """Lazily import heavy deps only when node.run() is actually called."""
    global constraint_filter, brain, recognition, arbiter, outcomes, math_need
    if constraint_filter is None:
        from constraint_filter import checkable_exprs as _ce
        constraint_filter = type("M", (), {"checkable_exprs": _ce})()
    if brain is None:
        # brain.py is a HARD dependency of the published tree: it SHIPS (see
        # VENDORING.md) and supplies embed() plus a corpus reader behind $STATE_DB.
        # recognition.py guards its own import because that module can be imported
        # on its own; node cannot run without brain, so the asymmetry is deliberate
        # — a missing brain.py is a packaging bug, not a runtime condition to survive.
        brain = _lazy_import("brain")
    if recognition is None:
        recognition = _lazy_import("recognition")
    if arbiter is None:
        arbiter = _lazy_import("arbiter")
    if outcomes is None:
        outcomes = _lazy_import("outcomes")
    if math_need is None:
        math_need = _lazy_import("math_need")

ACT_MEAN = 0.6        # a move acts autonomously only above this earned Beta-mean…
ACT_MIN_OUTCOMES = 3  # …and only after at least this many recorded outcomes


@dataclass
class Step:
    situation: str
    move: str | None          # the move the brain advises/applies
    fire: float               # recognition similarity for that move
    read: dict                # full recall (coverage + fired)
    resolution: str           # "FLOOR" | "ACT" | "ESCALATE"
    directive: str            # what to do / rail directive / depth directive
    proposed: str | None      # the brain's present_action (the suggested move)
    floor_label: str | None   # rail label if a floor bound
    math: dict | None = None  # exact-math result when the math front-door routed (Step 2)


def step(situation: str, recent_actions: list = None) -> Step:
    """One grounded step: brain recalls → floor vets → resolve by the honest gate.

    Step 2 (2026-07-01): a MATH front-door runs alongside recognition. When the situation
    is an explicit computation, mathbrain supplies the EXACT result — but it is TOOL-USE,
    not an organ yet, so it does NOT bypass the floor: the exact result is vetted by the
    arbiter like any other draft (it becomes the non-bypassable numeric floor only at
    Step 3). Ambiguous/deferred math never forces — it flows to normal reasoning.
    """
    _ensure_deps()  # SH-T7.9 fix: lazy deps must be loaded on entry
    r = recognition.recall(situation)
    top = r["fired"][0] if r["fired"] else None
    proposed = top["present_action"] if top else None

    # 0. MATH front-door — cheap + deterministic (regex, no LLM). Takes over ONLY when an
    #    explicit computation is present AND mathbrain returns an EXACT result.
    need = math_need.math_need(situation)
    if need.is_math:
        import mathbrain  # lazy: keep sympy off the common (no-math) path
        res = mathbrain.solve(need.for_mathbrain(), source=situation)
        if res.exact:
            math_draft = f"{need.expression}  →  {res.answer}"
            info = {"expression": need.expression, "op": res.op, "answer": res.answer,
                    "pattern": res.pattern, "confidence": need.confidence}
            # FLOOR STILL RUNS — math is tool-use; it does NOT bypass the honesty floor.
            d = arbiter.arbitrate(request=situation, draft=math_draft, recent_actions=recent_actions)
            if d.floor:
                return Step(situation, (top or {}).get("name"), (top or {}).get("fire", 0.0),
                            r, "FLOOR", d.directive, proposed, d.label, math=info)
            return Step(situation, f"math:{res.op or 'compute'}", 1.0, r, "MATH",
                        f"exact ({res.op or 'compute'}): {math_draft}", math_draft, None, math=info)
        # not exact (deferred / sympy error) → do NOT force; fall through to reasoning.

    # 1. FLOOR — the arbiter checks the action history (R3) and the outgoing draft
    #    (A6, here the proposed action). A bound rail is non-overridable.
    d = arbiter.arbitrate(request=situation, draft=proposed, recent_actions=recent_actions)
    if d.floor:
        return Step(situation, (top or {}).get("name"), (top or {}).get("fire", 0.0),
                    r, "FLOOR", d.directive, proposed, d.label)

    # 2. ACT — only a fired move that has EARNED enough trust may act on its own.
    if top and top["proven"] >= ACT_MIN_OUTCOMES and (top["mean"] or 0) >= ACT_MEAN:
        return Step(situation, top["name"], top["fire"], r, "ACT", proposed, proposed, None)

    # 3. ESCALATE — advise only; the conscious step decides. Carry the depth directive.
    return Step(situation, (top or {}).get("name"), (top or {}).get("fire", 0.0),
                r, "ESCALATE", d.directive, proposed, None)


def close(step_or_name, held: bool, situation: str = "") -> dict:
    """Close the loop on a step: record whether the move HELD → Beta updates → trust
    is earned. This is the only way a move ever crosses the act-gate."""
    _ensure_deps()  # SH-T7.9 fix: lazy deps must be loaded on entry
    name = step_or_name.move if isinstance(step_or_name, Step) else step_or_name
    if not name:
        return {}
    return outcomes.record(name, held, situation=situation)


# ─────────────────────────────────────────────────────────────────────────────
# consult_all — MATHBRAIN-PARALLEL-VISION Stage 1: the parallel consult.
#
# step() stays the live per-node path (untouched). consult_all() is a NEW, additive
# surface: the four organs run on the SAME situation as INDEPENDENT lanes (no lane reads
# another's output — parallel means parallel), and it returns a CONSULT REPORT. No
# arbitration — the conscious layer (Claude/Steward/Illia) reads all lanes. ADVISORY law
# untouched; the FLOOR still binds the eventual DRAFT downstream (this is pre-draft advice,
# never a bypass). Each fired non-math lane logs a wisdom fire tagged with its lane —
# grading stays the ONE wisdom loop (no new system). Stage 2 (per-lane earned P(hold))
# is NOT here — this is the wiring only.
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Lane:
    name: str                 # brain | math | ds | logic
    fired: bool
    suggestion: str           # the move / answer / method / axiom ("" when quiet)
    confidence: float
    witness: str = ""         # runnable proof / evidence ("" when none)
    detail: dict = None       # lane-specific payload (logic: strength+review+constraints, …)


@dataclass
class ConsultReport:
    situation: str
    lanes: list               # [Lane] — always the four, in order brain·math·ds·logic

    def by_name(self, n: str):
        return next((l for l in self.lanes if l.name == n), None)

    def fired(self):
        return [l for l in self.lanes if l.fired]


def _lane_brain(situation: str) -> Lane:
    _ensure_deps()  # SH-T7.9 fix: lazy deps must be loaded on entry
    r = recognition.recall(situation)
    fired = r.get("fired") or []
    top = fired[0] if fired else None
    if not top:
        return Lane("brain", False, "", 0.0, "", {"coverage": r.get("coverage")})
    return Lane("brain", True, top["name"], round(float(top.get("fire", 0.0)), 3), "",
                {"proposed": top.get("present_action", ""), "trust": top.get("trust"),
                 "pain": top.get("pain")})


def _lane_math(situation: str) -> Lane:
    _ensure_deps()  # SH-T7.9 fix: lazy deps must be loaded on entry
    need = math_need.math_need(situation)
    if not need.is_math:
        return Lane("math", False, "", round(need.confidence, 3), "")
    import mathbrain  # lazy: keep sympy off the no-math path
    res = mathbrain.solve(need.for_mathbrain())
    if not res.exact:
        return Lane("math", False, "", round(need.confidence, 3), "",
                    {"deferred": True, "expression": need.expression})
    return Lane("math", True, str(res.answer), round(need.confidence, 3),
                f"{need.expression} → {res.answer}", {"op": res.op, "pattern": res.pattern})


def _lane_ds(situation: str) -> Lane:
    import ds_need  # lazy: embedding index
    d = ds_need.ds_need(situation, defer_log=False)
    return Lane("ds", d.fired, d.pattern, round(float(d.confidence), 3), d.witness,
                {"sphere": d.sphere, "candidates": d.candidates})


def _lane_logic(situation: str) -> Lane:
    import logic_lane  # lazy: embedding index — L4, the conscience
    l = logic_lane.logic_need(situation, defer_log=False)
    return Lane("logic", l.fired, l.axiom_id, round(float(l.confidence), 3), l.witness,
                {"belief": l.belief, "post_conditions": l.post_conditions,
                 "strength": l.strength, "is_axiom": l.is_axiom, "review": l.review})


def consult_all(situation: str, log: bool = True, fires_path: Path = None) -> ConsultReport:
    """Run L1 brain · L2 math · L3 ds · L4 logic on the SAME situation, independently, and
    return the consult report. Each lane fails OPEN (a broken lane must not sink the consult
    or the others). No arbitration; the floor is not called here (it binds the draft later)."""
    lanes = []
    for name, fn in (("brain", _lane_brain), ("math", _lane_math),
                     ("ds", _lane_ds), ("logic", _lane_logic)):
        try:
            lanes.append(fn(situation))
        except Exception as e:
            lanes.append(Lane(name, False, "", 0.0, "",
                              {"error": f"{type(e).__name__}: {e}"}))
    if log:
        try:
            import wisdom
            for l in lanes:
                # math:* is not a library move (log_fire skips it too); log the rest tagged.
                if l.fired and l.name != "math":
                    wisdom.log_fire(situation=situation, move=l.suggestion, fire=l.confidence,
                                    resolution="CONSULT", lane=l.name, caller="consult_all",
                                    fires_path=fires_path)
        except Exception as e:  # fail-open: logging never breaks the consult
            print(f"[consult_all] fire-logging fail-open: {e}", file=sys.stderr)
    return ConsultReport(situation, lanes)


def _show_consult(rep: ConsultReport) -> None:
    print(f"\n■ consult: {rep.situation!r}")
    for l in rep.lanes:
        if not l.fired:
            why = f" [{l.detail['error']}]" if (l.detail or {}).get("error") else ""
            print(f"   ·   L·{l.name:5} quiet{why}")
            continue
        extra = ""
        if l.name == "logic":
            rv = (l.detail or {}).get("review") or {}
            extra = f"  · strength={l.detail.get('strength')} · trust={rv.get('trust')}"
        elif l.name == "ds":
            extra = f"  · sphere={l.detail.get('sphere')}"
        print(f"   ✓ L·{l.name:5} {l.suggestion}  ({l.confidence}){extra}")
        if l.witness:
            print(f"            witness: {l.witness}")
        if l.name == "logic" and (l.detail or {}).get("post_conditions"):
            print(f"            weigh draft against: "
                  f"{checkable_exprs(l.detail['post_conditions'], limit=3)}")
    print("   ADVISORY consult report — lanes independent, no arbitration; "
          "the FLOOR still binds the draft downstream.")


def selftest_consult() -> int:
    """Planted asks route to the expected lane(s); a pure-judgment ask keeps math quiet;
    the logic lane carries its conscience payload; fires are lane-tagged (temp stream)."""
    _ensure_deps()  # SH-T7.9 fix: lazy deps must be loaded on entry
    import tempfile
    checks = []
    routing = [
        ("solve x**2 - 5*x + 6 = 0", "math"),                       # pure computation → L2
        ("is my A/B conversion difference significant", "logic"),    # method → L4 (and L3)
        ("find near-duplicate documents in this collection", "ds"),  # method → L3
    ]
    for sit, want in routing:
        rep = consult_all(sit, log=False)
        lane = rep.by_name(want)
        checks.append((f"{want}-lane fires on {sit[:38]!r}", bool(lane and lane.fired)))

    judgment = consult_all("they keep misunderstanding what I mean", log=False)
    checks.append(("report always carries the 4 lanes",
                   [l.name for l in judgment.lanes] == ["brain", "math", "ds", "logic"]))
    checks.append(("math lane quiet on a pure-judgment ask",
                   not judgment.by_name("math").fired))

    ab = consult_all("is my A/B conversion difference significant", log=False)
    lg = ab.by_name("logic")
    checks.append(("logic fire carries the conscience payload (strength+review+constraints)",
                   bool(lg.fired and lg.detail.get("strength")
                        and (lg.detail.get("review") or {}).get("trust")
                        and lg.detail.get("post_conditions"))))
    checks.append(("lanes are independent (ds & logic both fire on a method ask, distinctly)",
                   ab.by_name("ds").fired and lg.fired))

    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / "fires.jsonl"
        consult_all("is my A/B conversion difference significant", log=True, fires_path=fp)
        rows = ([json.loads(x) for x in fp.read_text().splitlines() if x.strip()]
                if fp.exists() else [])
        tagged = {r.get("lane") for r in rows}
        checks.append(("consult fires are lane-tagged in the wisdom stream",
                       "logic" in tagged and "ds" in tagged and "math" not in tagged))

    # the FLOOR is untouched — prove it still binds a planted overclaim (arbiter, not consult).
    try:
        d = arbiter.arbitrate(request="status?", draft="everything is fixed and working now",
                              recent_actions=[{"action": "cmake build", "ok": False}] * 3)
        checks.append(("floor still binds a planted overclaim (advisory law intact)", bool(d.floor)))
    except Exception as e:
        checks.append((f"floor check ran (arbiter: {e})", False))

    ok = 0
    for name, passed in checks:
        print(f"  {'✓' if passed else '✗ FAIL'}  {name}")
        ok += passed
    print(f"\n{ok}/{len(checks)} checks passed"
          + ("" if ok == len(checks) else " — FIX BEFORE TRUSTING"))
    return 0 if ok == len(checks) else 1


def _show(s: Step):
    cov = s.read["coverage"]
    print(f"\n■ situation: {s.situation!r}")
    print(f"   read: best={cov['best']} · top1={cov['top1']} · gap={cov['gap']} · novel={s.read['novel']}")
    if s.math:
        m = s.math
        print(f"   math front-door → {m['op'] or 'compute'}({m['expression']!r}) = {m['answer']}  [exact, sympy]")
    if s.proposed:
        print(f"   brain advises → {s.move}  (fire {s.fire})")
        print(f"        DO: {s.proposed[:110]}")
        pn = (s.read["fired"][0].get("pain") if s.read.get("fired") else None)
        if pn:
            print(f"        ⚠ PAIN read-back: {pn['whisper']}")
    tag = {
        "FLOOR":    "⛔ FLOOR — rail bound, non-overridable",
        "ACT":      "✅ ACT — move proven, autonomous",
        "ESCALATE": "↑ ESCALATE to conscious — move is ADVISORY (not yet proven)",
        "MATH":     "🔢 MATH — exact result, floor passed (tool-use, NOT bypassed)",
    }[s.resolution]
    print(f"   → {tag}" + (f"  [{s.floor_label}]" if s.floor_label else ""))
    print(f"     directive: {s.directive[:140]}")
    if s.resolution == "ESCALATE" and s.move:
        m = s.read["fired"][0]
        print(f"     (to graduate to ACT: needs ≥{ACT_MIN_OUTCOMES} outcomes & mean≥{ACT_MEAN}; "
              f"now: {m['trust']})")


_DEMO = [
    "they keep misunderstanding what I mean",
    "i'm so happy this finally works, it's a real success",
    "explain me your understanding of aura so we align",
    "solve x**2 - 5*x + 6 = 0",   # math front-door → exact result, floor still runs
]


def _library() -> dict:
    _ensure_deps()  # SH-T7.9 fix: lazy deps must be loaded on entry
    pats = ([json.loads(l) for l in recognition.PATTERNS.read_text().splitlines() if l.strip()]
            if recognition.PATTERNS.exists() else [])
    return {p["name"]: p for p in pats}


def run(seed: str, max_cycles: int = 5, reanchor_every: int = 3, recent_actions=None):
    """The continuous self-redirecting loop (bounded). From a seed situation the node
    steps; then it SELF-REDIRECTS by following the fired move's top graph-successor —
    the brain predicting its OWN next move — and feeding that successor's trigger back
    as the next situation. The destination feeds the next beginning (the physics of
    momentum). Bounded + floored + re-anchored so momentum can't become drift.

    Every `reanchor_every` cycles it re-grounds to a REAL recent turn from the substrate
    instead of its own prediction — the anti-drift anchor.

    Honest scope: the self-redirect here rolls forward through the LEARNED move-graph
    (grounded transitions), advisory only. The pure self-GENERATED redirect (the node
    inventing its next utterance via the generator) attaches when the generator is wired.
    """
    _ensure_deps()  # SH-T7.9 fix: lazy deps must be loaded on entry
    lib = _library()
    graph = (json.loads((recognition.HERE / "graph.json").read_text())
             if (recognition.HERE / "graph.json").exists() else {})
    recent = list(recent_actions or [])
    situation, visited, traj = seed, [], []

    for cycle in range(1, max_cycles + 1):
        reanchored = cycle > 1 and (cycle - 1) % reanchor_every == 0
        if reanchored:
            real = brain.load_dialogue("user", 1)
            if real:
                situation = real[-1]["text"][:300]
        s = step(situation, recent_actions=recent)
        traj.append((cycle, reanchored, s))
        recent.append({"action": s.move or "novel", "ok": s.resolution != "FLOOR"})

        if s.resolution == "FLOOR":
            return traj, f"FLOOR bound — the rail stopped the momentum ({s.floor_label})"
        if s.move in visited:
            return traj, f"convergence — rolled back to '{s.move}', loop closed"
        visited.append(s.move)
        succ = sorted(graph.get(s.move or "", {}).items(), key=lambda x: -x[1])
        if not succ:
            return traj, f"dead-end — '{s.move}' has no learned successor"
        nxt = succ[0][0]
        if nxt not in lib:
            return traj, f"successor '{nxt}' not yet in the library"
        situation = lib[nxt].get("trigger") or lib[nxt].get("present_action", "")
    return traj, f"reached cycle bound ({max_cycles})"


def _show_run(traj, stop):
    print("\n— continuous self-redirecting loop (bounded rollout through the move-graph) —")
    for cycle, reanchored, s in traj:
        tag = "⟲ re-anchored to REAL data" if reanchored else "↻ self-redirect (graph) "
        print(f"  cycle {cycle:>2} [{tag}]  {s.resolution:>8} · fire {s.fire:>5} · {s.move}")
    print(f"  ⊣ stopped: {stop}")


def run_generative(seed: str, max_turns: int = 4, budget_usd: float = 0.10,
                   model: str = "claude-haiku-4-5", stop_on_floor: bool = True):
    """The GENERATIVE self-redirect — kills the circularity. Instead of feeding a move's
    own trigger back (self-confirming, fire≈1.0), the node GENERATES the next turn (a real
    new utterance, voice-gated) and recognizes THAT. Two characters (Illia↔Claude) alternate;
    every generated turn is recognized (brain) + vetted (floor). BudgetGuard caps spend.

    This is the loop made genuinely generative: a real generated turn feeds the next
    beginning, and recognition does NON-trivial work on it (fire < 1.0). Spends credit —
    so it is never in the free default demo; call it explicitly with a hard cap."""
    import anthropic
    import generator
    chars = generator.build_characters(generator.CORPUS)
    order = list(chars.values())
    budget = generator.BudgetGuard(budget_usd, model)
    client = anthropic.Anthropic(api_key=generator._key(), timeout=60.0)
    transcript, recent, traj = [], [], []

    for i in range(max_turns):
        if budget.exceeded():
            traj.append(("[budget cap]", None)); break
        spk = order[i % len(order)]
        convo = "\n\n".join(f"{t['speaker']}: {t['text']}" for t in transcript[-6:]) or f"(opening) {seed}"
        text, fid, base, tries, verdict, cverd, mscore, mbase = generator.gen_turn(client, spk, convo, budget, model)
        s = step(text, recent_actions=recent)          # the node recognizes + vets the GENERATED turn
        recent.append({"action": s.move or "novel", "ok": s.resolution != "FLOOR"})
        transcript.append({"speaker": spk.name, "text": text})
        traj.append((spk.name, fid, base, verdict, s, text))
        if s.resolution == "FLOOR" and stop_on_floor:
            return traj, budget, f"FLOOR bound on a generated turn ({s.floor_label})"
    floors = sum(1 for r in traj if len(r) > 2 and r[4].resolution == "FLOOR")
    return traj, budget, f"reached turn bound ({max_turns})" + (f"; {floors} floored turn(s) flagged" if floors else "")


def _show_gen(traj, budget, stop):
    print("\n— GENERATIVE self-redirecting loop (real generated turns, voice-gated, brain+floor) —")
    for row in traj:
        if len(row) == 2:
            print(f"  {row[0]}"); continue
        spk, fid, base, verdict, s, text = row
        print(f"\n  {spk}  (voice {fid:.2f}/{base:.2f} · {verdict})")
        print(f"    “{text[:150]}”")
        print(f"    → brain: {s.move}  (fire {s.fire} — NON-circular) · {s.resolution}")
    print(f"\n  ⊣ stopped: {stop}")
    print(f"  {budget.report()}")


def main():
    print("grounded node — first node (.5):  brain → floor → resolve")
    print(f"(act-gate: ≥{ACT_MIN_OUTCOMES} recorded outcomes AND Beta-mean ≥ {ACT_MEAN};"
          " until earned, the brain only ADVISES)")
    recent = []
    for sit in _DEMO:
        _show(step(sit, recent_actions=recent))

    print("\n— FLOOR demonstration (must bind and override the brain) —")
    _show(step("just tell them everything is fixed and working now",
               recent_actions=[{"action": "cmake build", "ok": False}] * 3))

    _show_run(*run("they keep misunderstanding what I mean", max_cycles=5, reanchor_every=3))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--consult-selftest":
        raise SystemExit(selftest_consult())
    if len(sys.argv) > 2 and sys.argv[1] == "consult":
        _show_consult(consult_all(" ".join(sys.argv[2:])))
    else:
        main()
