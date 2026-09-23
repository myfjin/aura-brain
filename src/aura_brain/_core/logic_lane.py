#!/usr/bin/env python3
"""logic_lane.py — L4, the CONSCIENCE lane (MATHBRAIN-PARALLEL-VISION Stage 1).

The Brain's fourth consult lane. Where L3 (DS-EYE, ds_need.py) recalls WHICH pattern
fits, L4 recalls the AXIOM that pattern PROVED about itself — the checkable constraint
the conscious layer weighs its draft against before speaking. The library's verified
patterns, become the Brain's conscience.

Laws, inherited unchanged from the sibling lanes:
  - ADVISORY: surfaces the axiom + its run-witness; never blocks, never executes.
  - recognition-gated: below THRESHOLD → DEFER to the review queue, not a forced fire.
  - lanes INDEPENDENT: L4 does its OWN recognition over the belief-sentences (what the
    axiom CLAIMS) — a different semantic surface than L3's docstring key (what the method
    DOES) — and never reads another lane's output. Parallel means parallel.

The ✓ pass / ✗ violation / ? uncertain VERDICT is the PAUSE (PART B), NOT here: a true
verdict needs symbolic eval or an LLM second pass (whypass Tier-2). Evaluating a boolean
post-condition against free prose would be theater. L4's honest job is to put the right
constraint in front of the conscious layer, loud; the catch is the layer's own move.

Registry = logic_registry.jsonl (run-verified axioms; logic_extract.py). Fire-logging
carries lane="logic" so wisdom.log_fire tags it (grading = the ONE wisdom loop, no new
system): held = the pause happened and the axiom was weighed, outcome-blind.

Run:  python3 logic_lane.py "is my A/B conversion difference significant?"
      python3 logic_lane.py --selftest
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths  # published settings module (see VENDORING.md)

from constraint_filter import checkable_exprs  # noqa: E402  pure-stdlib, safe at import
REGISTRY = paths.LOGIC_REGISTRY
PATTERNS_DIR = paths.PATTERNS_DS
R_PATTERNS_DIR = paths.PATTERNS_R
SYS_PATTERNS_DIR = paths.PATTERNS_SYS
CACHE = HERE / "logic_keys_cache.npz"
QUEUE = paths.BRAIN_HOME / "logic_misses.jsonl"        # sovereign L4 defer log (same schema as ds)
LANE = "logic"


# Registry-scoped cache + defer-queue (2026-07-10): recognition can point at ANY sovereign
# registry (DS logic_registry.jsonl · sysadmin_registry.jsonl · a future sphere). Each gets
# its OWN embedding cache and miss queue — pooling them would thrash the cache and cross
# sovereign streams (PCE-0 citizenship). registry=None keeps the DS path byte-identical.
def _cache_for(registry) -> Path:
    return CACHE if registry is None else HERE / f"logic_keys_cache_{Path(registry).stem}.npz"


def _queue_for(registry) -> Path:
    return QUEUE if registry is None else HERE / f"{Path(registry).stem}_misses.jsonl"

# Inherited default from ds_need's measured 0.30; VERIFIED against this lane's own
# positives/negatives in selftest (the belief-sentence surface scores differently than
# the docstring surface). Re-calibrate from the queue if either side drifts — never
# widen the accept-set to force a fire (the ds_need KNOWN_MISSES discipline).
THRESHOLD = 0.30
assert 0.2 <= THRESHOLD <= 0.9


@dataclass
class LogicNeed:
    fired: bool
    axiom_id: str            # top axiom (pattern) name ("" when not fired)
    confidence: float        # top cosine score
    belief: str              # the plain belief-sentence (the conscience's words)
    post_conditions: list    # [{expr, msg, verified, tier}] — the checkable constraints
    witness: str             # runnable proof-of-mechanism ("" when not fired)
    candidates: list         # [(name, score), ...] top-3
    strength: str = "none"   # recovery > weak > none — HOW hard the CONSTRAINT pins (has a real assert?)
    is_axiom: bool = False   # TWO-AXIS (honest-pass 07-23): now = ORACLE-BACKED (>=1 of the 5 oracle kinds).
                             # "is there a checkable constraint?" is `strength != none`, a SEPARATE axis.
    oracle: dict = None      # {backed, kinds[], tier(hard|consensus|candidate), verdicts, ...} from honest_pass
    basis: str = ""          # "oracle-backed:<tier>" | "green-run-candidate"
    review: dict = None      # Ver's semantic verdict {trust, source_match, note, ...}
    lane: str = LANE


def _axioms(registry=None) -> list[dict]:
    reg = REGISTRY if registry is None else Path(registry)
    if not reg.exists():
        return []
    return [json.loads(l) for l in reg.read_text().splitlines() if l.strip()]


def _keys(rows: list[dict]) -> list[tuple[str, str]]:
    """(id, key_text) per axiom. The key is what the axiom CLAIMS — belief-sentence +
    core idea + category — deliberately NOT the docstring (that is L3's surface)."""
    out = []
    for r in rows:
        belief = (r.get("belief_sentence") or {}).get("text", "")
        key = (f"{r['id'].replace('_', ' ')}. Category: {r.get('category', '')}. "
               f"{belief} {r.get('core_idea', '')}")
        out.append((r["id"], key[:500]))
    return out


def _index(rows: list[dict], registry=None):
    """Names + embedded keys, cached PER REGISTRY; re-embeds only when that registry's keys
    change. Mirrors ds_need._index (same embedder, local + free — no budget)."""
    import numpy as np
    import brain

    cache = _cache_for(registry)
    keys = _keys(rows)
    digest = hashlib.md5(json.dumps(keys).encode()).hexdigest()
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        if str(z["digest"]) == digest:
            return list(z["names"]), z["K"]
    names = [n for n, _ in keys]
    K = brain.embed([k for _, k in keys])
    np.savez(cache, names=np.array(names), K=K, digest=np.array(digest))
    return names, K


def logic_need(situation: str, defer_log: bool = True, registry=None) -> LogicNeed:
    """Recognize the axiom a situation is in the territory of. `registry` selects the
    sovereign registry to recognize against (None = the DS logic_registry.jsonl, unchanged);
    pass sysadmin_registry.jsonl to give the sysadmin PCE its own recognition lane."""
    import numpy as np
    import brain

    rows = _axioms(registry)
    if not rows:
        return LogicNeed(False, "", 0.0, "", [], "", [])
    by_id = {r["id"]: r for r in rows}
    names, K = _index(rows, registry)
    v = brain.embed([situation])[0]
    scores = K @ v
    order = np.argsort(-scores)[:3]
    cands = [(str(names[i]), round(float(scores[i]), 3)) for i in order]
    top_name, top_score = cands[0]
    if top_score >= THRESHOLD:
        r = by_id[top_name]
        sphere = r.get("sphere")
        # Prefer the canonical library source path recorded at extraction (honest-pass merge
        # put all spheres in ONE registry, so the old per-sphere dir guess is unreliable).
        src = (r.get("extraction") or {}).get("src")
        if src:
            lib = paths.PATTERN_LIBRARY_ROOT / src
            witness = (f"Rscript {lib}" if src.endswith(".R")
                       else f"cargo/rustc {lib}" if src.endswith(".rs")
                       else f"python3 {lib}")
        else:
            witness = (f"Rscript {R_PATTERNS_DIR / (top_name + '.R')}" if sphere == "R"
                       else f"python3 {SYS_PATTERNS_DIR / (top_name + '.py')}" if sphere == "SYS"
                       else f"python3 {PATTERNS_DIR / (top_name + '.py')}")
        return LogicNeed(
            fired=True, axiom_id=top_name, confidence=top_score,
            belief=(r.get("belief_sentence") or {}).get("text", ""),
            post_conditions=r.get("post_conditions", []),
            witness=witness,
            candidates=cands,
            strength=r.get("strength", "none"), is_axiom=r.get("is_axiom", False),
            oracle=r.get("oracle") or {}, basis=r.get("basis", ""),
            review=r.get("review") or {"trust": "unreviewed"})
    if defer_log:
        rec = {"input": situation[:300], "stage": "logic_dispatch",
               "candidates": cands, "reason": f"top score {top_score} < {THRESHOLD}",
               "review_status": "pending",
               "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        with _queue_for(registry).open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return LogicNeed(False, "", top_score, "", [], "", cands)


# Recognition drift, recorded not hidden (same discipline as ds_need.KNOWN_MISSES):
# a known miss is FIXED by a build (rerank / graded feedback), never by widening accept.
KNOWN_MISSES: dict = {}


def selftest() -> int:
    """Known asks → expected top-1 axiom (or accept-set); prose must NOT fire. Prints
    the observed score gap so THRESHOLD stays measured, not asserted."""
    cases = [
        ("is the difference between my two conversion rates statistically significant",
         {"ab_test_proportions", "ab_test_srm_check", "permutation_test"}),
        ("check my sample ratio mismatch in the experiment assignment",
         {"ab_test_srm_check"}),
        ("integrate this smooth function to high accuracy",
         {"adaptive_simpson", "gauss_legendre_quadrature", "romberg_integration"}),
        ("fit an accelerated failure time survival model",
         {"accelerated_failure_time_lite", "weibull_aft_survival"}),
        ("boost weak stumps into a strong classifier",
         {"adaboost", "gradient_boosting_stumps", "gradient_boosting"}),
    ]
    negatives = [
        "restart the gateway daemon on the .8 machine",
        "write the LinkedIn post for the folder-nature launch",
        "how are you feeling today brother",
    ]
    if not REGISTRY.exists():
        print("✗ FAIL  logic_registry.jsonl missing — run logic_extract.py build first")
        return 1

    ok, known, regressions = 0, 0, 0
    pos_scores, neg_scores = [], []
    for q, accept in cases:
        r = logic_need(q, defer_log=False)
        pos_scores.append(r.confidence)
        hit = r.fired and r.axiom_id in accept
        if hit:
            ok += 1
            print(f"  ✓ {q[:56]!r} → {r.axiom_id} ({r.confidence})")
        elif q in KNOWN_MISSES:
            known += 1
            print(f"  ~ KNOWN-MISS {q[:48]!r} → {r.axiom_id or '(defer)'}")
        else:
            regressions += 1
            print(f"  ✗ {q[:56]!r} → {r.axiom_id or '(defer)'} ({r.confidence}) "
                  f"top3={r.candidates}")
    neg_ok = 0
    for q in negatives:
        r = logic_need(q, defer_log=False)
        neg_scores.append(r.confidence)
        good = not r.fired
        neg_ok += good
        print(f"  {'✓' if good else '✗'} NEG {q[:50]!r} → "
              f"{'defer (correct)' if good else f'FIRED {r.axiom_id} ({r.confidence})'}")

    # surface the axiom on a fired case — proving L4 returns the CONSTRAINT, not just a name
    demo = logic_need("is my A/B conversion difference significant", defer_log=False)
    axiom_surfaced = bool(demo.fired and demo.belief and demo.post_conditions)
    review_carried = bool(demo.fired and demo.review and demo.review.get("trust"))
    print(f"\n  {'✓' if axiom_surfaced else '✗'} surfaces a checkable axiom on fire:")
    if demo.fired:
        print(f"      belief: {demo.belief[:120]}")
        print(f"      constraints: {checkable_exprs(demo.post_conditions, limit=3)}")
        print(f"      strength={demo.strength}  ver-trust={demo.review.get('trust')}")
    print(f"  {'✓' if review_carried else '✗'} carries Ver's trust tier (reconciliation wired)")

    gap_ok = (min(pos_scores) > max(neg_scores)) if pos_scores and neg_scores else False
    print(f"\n  score gap — weakest positive {min(pos_scores):.3f} vs "
          f"strongest negative {max(neg_scores):.3f}  "
          f"({'clean gap, THRESHOLD sits inside' if gap_ok else 'OVERLAP — recalibrate'})")
    total = len(cases) + len(negatives)
    passed = ok + neg_ok
    print(f"\n{passed}/{total} passed · {known} known-miss · {regressions} NEW regressions "
          f"· axiom-surfaced={axiom_surfaced} · review-carried={review_carried}")
    return (0 if regressions == 0 and neg_ok == len(negatives)
            and axiom_surfaced and review_carried else 1)


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    if sys.argv[1] == "--selftest":
        raise SystemExit(selftest())
    r = logic_need(" ".join(sys.argv[1:]))
    if r.fired and r.strength == "none":
        print(f"L4 conscience: {r.axiom_id}  (confidence {r.confidence})")
        print(f"  recognized, but this pattern carries NO checkable constraint "
              f"(hollow asserts only) — I can name the method, I have no constraint to hand you.")
        print(f"  run-witness: {r.witness}")
    elif r.fired:
        trust = (r.review or {}).get("trust", "unreviewed")
        tier = (r.oracle or {}).get("tier", "candidate")
        verified = "ORACLE-BACKED" if r.is_axiom else "green-run candidate (no independent oracle)"
        print(f"L4 conscience: {r.axiom_id}  (confidence {r.confidence}, "
              f"strength {r.strength}, trust {trust}, evidence {verified} · tier {tier})")
        print(f"  belief:  {r.belief}")
        print(f"  weigh your draft against: {checkable_exprs(r.post_conditions)}")
        if trust == "ver-twin-rejected":
            print(f"  ⚠ Ver REJECTED this pattern's twin — read before trusting: "
                  f"{(r.review or {}).get('note', '')[:120]}")
        print(f"  run-witness: {r.witness}")
        print("  ADVISORY — L4 surfaces the constraint; the verdict is yours (the pause).")
    else:
        print(f"L4 conscience: no axiom fired (top {r.candidates}) → queued for review")


if __name__ == "__main__":
    main()
