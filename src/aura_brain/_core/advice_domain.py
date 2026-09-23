#!/usr/bin/env python3
"""advice_domain.py — MECHANISM #1: advice-citizenship (end cross-dialogue leakage).

The false-alarm's #1 mechanism, found by reading the surfacing path (claude_advise_hook →
advise → recognition.recall over ONE shared 935-move library): my prompt embedding-matches
an OFF-DOMAIN move (an ops move surfaces in a conscience dialogue) because the pool mixes
every domain and the moves carry NO origin tag. FIX = give each move an origin DOMAIN, then
DOWN-WEIGHT domain-incoherent moves at advise-time — LOUD-FIRST (the domain + penalty are
SHOWN; only a soft re-rank, never a hard silence — the mirror trap).

Domain = empirical (Illia's lean, mirrors the 7-noun ontology): cluster the 935 moves by
their OWN content (cluster_terms + name + trigger), label each cluster by its top terms.
No trialogue re-tagging, no fixed taxonomy — the moves tell us their domains.

A move surfaced by recall is checked for DOMAIN COHERENCE with the current prompt: if the
prompt's domain != the move's domain, the move is down-weighted (a cross-domain narrow-cue
match, e.g. "cross-architecture-model-deployment" (ops) on an A/B-stats prompt).

  python3 advice_domain.py build [K]    # cluster the moves → domains, cache, PRINT them
  python3 advice_domain.py domain "<text>"   # which domain does this text belong to?
  python3 advice_domain.py selftest
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths  # published settings module (see VENDORING.md)

MOVES = paths.PATTERNS_LIBRARY
CACHE = HERE / "advice_domains.npz"
LABELS = HERE / "advice_domains.json"
DEFAULT_K = 12
SEED = 0


def _move_text(r: dict) -> str:
    """The move's DOMAIN content — its broad meaning, not just the narrow trigger that a
    recall matched on. cluster_terms is the distilled domain vocabulary (best signal)."""
    terms = " ".join(r.get("cluster_terms") or [])
    return f"{r.get('name', '').replace('-', ' ')}. {terms}. {(r.get('trigger') or '')[:160]}"


def _load_moves() -> list:
    return [json.loads(l) for l in MOVES.read_text().splitlines() if l.strip()]


def _normalize(X):
    import numpy as np
    n = np.linalg.norm(X, axis=1, keepdims=True)
    return X / np.clip(n, 1e-9, None)


def _spherical_kmeans(X, k, iters=60, seed=SEED):
    """Cosine k-means (X pre-normalized): assign by max dot, re-center, renormalize.
    Deterministic (seeded). Empty clusters re-seed to the worst-served point."""
    import numpy as np
    rng = np.random.default_rng(seed)
    C = X[rng.choice(len(X), k, replace=False)].copy()
    labels = np.zeros(len(X), dtype=int)
    for _ in range(iters):
        sims = X @ C.T
        new = sims.argmax(1)
        if (new == labels).all() and _ > 0:
            break
        labels = new
        for j in range(k):
            m = labels == j
            if m.any():
                C[j] = X[m].mean(0)
            else:  # empty cluster → steal the point least similar to its own centroid
                worst = (X * C[labels]).sum(1).argmin()
                C[j] = X[worst]
        C = _normalize(C)
    return labels, C


def build(k: int = DEFAULT_K, verbose: bool = True):
    """Cluster the moves into k domains; cache centroids + move→domain + top-term labels."""
    import numpy as np
    import brain
    rows = _load_moves()
    X = _normalize(brain.embed([_move_text(r) for r in rows]))
    labels, C = _spherical_kmeans(X, k)

    # label each domain by the top distinctive words in its members' NAMES (cluster_terms
    # are too sparse on this corpus); the name IS the move's distilled meaning.
    from collections import Counter
    _STOP = {"and", "the", "to", "of", "for", "with", "on", "in", "from", "by", "a", "an",
             "then", "user", "assistant", "via", "when", "after", "before", "into"}
    domain_labels = {}
    for j in range(k):
        toks = Counter()
        for i, r in enumerate(rows):
            if labels[i] == j:
                for t in r.get("name", "").replace("-", " ").split():
                    t = t.lower()
                    if len(t) > 2 and t not in _STOP:
                        toks[t] += 1
        top = [t for t, _ in toks.most_common(6)]
        domain_labels[str(j)] = {"label": " · ".join(top[:4]) or f"domain-{j}",
                                 "top_terms": top, "size": int((labels == j).sum())}

    move_domain = {rows[i]["name"]: int(labels[i]) for i in range(len(rows))}
    # cache the move-content embeddings too (normalized) — the flag DECISION is now soft
    # similarity (prompt vs move content), measured to discriminate better than hard cluster
    # equality (which over-flagged 63% by tripping on adjacent domains). Clusters stay for
    # the loud-first LABELS only.
    np.savez(CACHE, C=C, k=k, M=X, names=np.array([r["name"] for r in rows]))
    LABELS.write_text(json.dumps({"labels": domain_labels, "move_domain": move_domain}, indent=0))

    if verbose:
        print(f"=== {k} empirical domains over {len(rows)} moves ===")
        for j in range(k):
            dl = domain_labels[str(j)]
            ex = [rows[i]["name"] for i in range(len(rows)) if labels[i] == j][:3]
            print(f"  D{j:<2} [{dl['size']:>3}]  {dl['label'][:52]}")
            print(f"        e.g. {', '.join(ex)}")
    return move_domain, domain_labels


def _centroids():
    import numpy as np
    if not CACHE.exists():
        return None, None
    z = np.load(CACHE)
    lab = json.loads(LABELS.read_text()) if LABELS.exists() else {"labels": {}, "move_domain": {}}
    return z["C"], lab


def domain_of(text: str):
    """(domain_id, label) of the nearest centroid for arbitrary text, or (None, '') if
    unbuilt. Used to place the current PROMPT in domain-space."""
    import numpy as np
    import brain
    C, lab = _centroids()
    if C is None:
        return None, ""
    v = _normalize(brain.embed([text]))[0]
    j = int((C @ v).argmax())
    return j, lab["labels"].get(str(j), {}).get("label", f"domain-{j}")


def move_domain_of(move_name: str):
    """(domain_id, label) a MOVE was clustered into (from the cached map)."""
    _, lab = _centroids()
    if not lab:
        return None, ""
    j = lab["move_domain"].get(move_name)
    if j is None:
        return None, ""
    return j, lab["labels"].get(str(j), {}).get("label", f"domain-{j}")


# FLAG_FLOOR — the soft-sim below which a move is "distant" from the prompt (a leak
# candidate). MEASURED 2026-07-10 from 397 live fires: soft-sim 10th pct ≈ 0.10, 25th ≈
# 0.185 → a floor here flags the bottom ~decile (genuinely distant), NOT the 63% that hard
# cluster-equality over-flagged. Re-measure if the fire distribution drifts. LOUD-FIRST:
# a flag is advisory (shown + soft down-weight), never a hard silence.
FLAG_FLOOR = 0.12


def _move_embs():
    """(names_list, M normalized) from the cache, lazy. ([],None) if unbuilt/legacy cache."""
    import numpy as np
    if not CACHE.exists():
        return [], None
    z = np.load(CACHE, allow_pickle=True)
    if "M" not in z or "names" not in z:
        return [], None
    return list(z["names"]), z["M"]


def _move_emb(move_name: str):
    names, M = _move_embs()
    if M is None or move_name not in names:
        return None
    return M[names.index(move_name)]


def coherent(prompt: str, move_name: str) -> tuple[bool, str]:
    """Is `move_name` coherent with `prompt`? SOFT: cosine(prompt, move-content) >= FLAG_FLOOR.
    Fail-open (unknown move / unbuilt → coherent, no penalty). The domain LABELS ride along
    for the loud-first explanation ('an ops move in a stats dialogue')."""
    import numpy as np
    import brain
    me = _move_emb(move_name)
    if me is None:
        return True, "move unknown — no penalty (fail-open)"
    v = _normalize(brain.embed([prompt]))[0]
    sim = float(v @ me)
    _, pl = domain_of(prompt)
    _, ml = move_domain_of(move_name)
    if sim >= FLAG_FLOOR:
        return True, f"coherent (soft-sim {sim:.3f}) · prompt∈[{pl}] move∈[{ml}]"
    return False, f"DISTANT (soft-sim {sim:.3f} < {FLAG_FLOOR}): move∈[{ml}] far from prompt∈[{pl}]"


def rerank(prompt: str, candidates: list, penalty: float = 0.6):
    """Advice-citizenship at surface-time: DOWN-WEIGHT domain-incoherent candidates and
    re-sort. candidates=[(move, score)]. Returns (reranked=[{move,score,orig,cross,note}],
    swapped). LOUD-FIRST + SOFT: a cross-domain move is penalized, NEVER hard-dropped — it
    may be genuinely cross-cutting, and the score+note are shown so the layer decides."""
    import numpy as np
    import brain
    v = _normalize(brain.embed([prompt]))[0]        # embed the prompt ONCE
    _, pl = domain_of(prompt)
    out = []
    for name, score in candidates:
        me = _move_emb(name)
        if me is None:
            cross, sim, note = False, None, "move unknown (no penalty)"
        else:
            sim = float(v @ me)
            cross = sim < FLAG_FLOOR
            _, ml = move_domain_of(name)
            note = (f"DISTANT soft-sim {sim:.3f}<{FLAG_FLOOR}: move∈[{ml}] · prompt∈[{pl}] ×{penalty}"
                    if cross else f"coherent soft-sim {sim:.3f} [{pl}]")
        s = round(float(score) * penalty, 3) if cross else round(float(score), 3)
        out.append({"move": name, "score": s, "orig": round(float(score), 3),
                    "cross": cross, "sim": sim, "note": note})
    out.sort(key=lambda x: -x["score"])
    swapped = bool(out and candidates and out[0]["move"] != candidates[0][0])
    return out, swapped


def selftest() -> int:
    if not CACHE.exists():
        print("  building domains first…")
        build(verbose=False)
    checks = []
    import numpy as np
    import brain
    rows = _load_moves()
    by_name = {r["name"]: r for r in rows}
    _, lab = _centroids()
    names, M = _move_embs()
    a_move = names[0]
    a_text = _move_text(by_name[a_move])
    v = _normalize(brain.embed([a_text]))[0]
    sims = M @ v
    # SELF: a move's own content is ~identical → soft-sim ≈ 1.0 → coherent (no penalty).
    checks.append(("move's own content → coherent (high soft-sim)",
                   coherent(a_text, a_move)[0] is True))
    checks.append(("self soft-sim >> most-distant soft-sim",
                   float(M[names.index(a_move)] @ v) > float(sims.min()) + 0.3))
    r1, _ = rerank(a_text, [(a_move, 0.5)])
    checks.append(("self candidate not penalized", r1[0]["cross"] is False and r1[0]["score"] == 0.5))
    # DISTANT: an off-topic prompt makes its lowest-sim move a flagged leak candidate.
    off = "the warm summer weather with birds singing in the quiet green garden"
    vo = _normalize(brain.embed([off]))[0]
    far = names[int((M @ vo).argmin())]
    r2, _ = rerank(off, [(far, 0.5)])
    far_cross = r2[0]["cross"]
    checks.append(("a genuinely distant move is FLAGGED + down-weighted",
                   far_cross is True and r2[0]["score"] < 0.5))
    # SWAP: with a_text as prompt, a_move is coherent (self); the move most-distant from
    # a_text, if flagged, is penalized below a_move → swaps to the coherent runner-up.
    far_a = names[int(sims.argmin())]
    r3, swapped = rerank(a_text, [(far_a, 0.5), (a_move, 0.4)])
    fa_cross = next((x["cross"] for x in r3 if x["move"] == far_a), False)
    a_coh = next((x for x in r3 if x["move"] == a_move), {})
    checks.append(("re-rank displaces a distant leader for the coherent self runner-up",
                   (fa_cross and a_coh.get("cross") is False and swapped and r3[0]["move"] == a_move)
                   or (not fa_cross)))
    checks.append(("fail-open on unknown move (no penalty)",
                   coherent("anything", "no-such-move-xyz")[0] is True))
    checks.append(("FLAG_FLOOR set + domains labeled",
                   0.0 < FLAG_FLOOR < 1.0 and len(lab["labels"]) >= 2))

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
    cmd = sys.argv[1]
    if cmd == "build":
        build(int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_K)
    elif cmd == "domain":
        j, l = domain_of(" ".join(sys.argv[2:]))
        print(f"domain D{j}: {l}")
    elif cmd == "selftest":
        raise SystemExit(selftest())
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
