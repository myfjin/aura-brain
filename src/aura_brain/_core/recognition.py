#!/usr/bin/env python3
"""Recognition — the "brain directly tells what to do" (the subconscious surface).

Illia, 2026-06-27: two kinds of thinking — conscious (on-demand, request/response,
"all that noise") and subconscious (background, automatic, it just hands you the
move). The consolidator is the background; THIS is the surface: a situation comes
in → the already-formed MOVES fire → it tells you what to do. No LLM, no request.

The heavy work was pre-paid offline (consolidator built + merged the patterns).
At runtime we embed only the one new input and match it against the library.

Primary: fire the merged reasoning MOVES (patterns_library.jsonl) → surface
present_action ("here's what you do"). Falls back to the coarse concept library
(concept_library.*) if no moves exist yet.

Run:
  python3 recognition.py build [role] [limit]        # (re)consolidate concept library
  python3 recognition.py "they keep misunderstanding what I mean"
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # published settings module (see VENDORING.md)

try:  # the published tree ships without brain.py — it opens the private dialogue corpus.
    import brain  # noqa: E402
except ImportError:  # fail OPEN and loud (CONTRIBUTING: "fail open with a loud WARN")
    brain = None
    print("[recognition] brain.py unavailable — dialogue recall off (fail-open)", file=sys.stderr)

HERE = Path(__file__).resolve().parent
PATTERNS = paths.PATTERNS_LIBRARY     # merged reasoning MOVES (primary)
LIB_VEC = paths.CONCEPT_LIBRARY_NPY          # coarse concepts (fallback)
LIB_META = paths.CONCEPT_LIBRARY_JSON
FIRE_THRESHOLD = 0.32   # cosine; below this nothing fires → novel → escalate to conscious


# ── consolidate the coarse concept library (the fallback) ──────────────────
def build(role: str = "user", limit: int = 1500):
    import numpy as np
    print(f"[consolidate] loading real {role} turns (limit {limit})…")
    turns = brain.load_dialogue(role, limit)
    texts = [t["text"] for t in turns]
    print(f"[consolidate] embedding {len(texts)} turns (the offline pre-payment)…")
    X = brain.embed(texts)
    k = max(8, min(24, len(texts) // 60))
    labels, C = brain.kmeans_cosine(X, k)
    meta, rows = [], []
    for j in range(k):
        idxs = [i for i in range(len(texts)) if labels[i] == j]
        if not idxs:
            continue
        sims = X[idxs] @ C[j]
        central = idxs[int(np.argmax(sims))]
        rows.append(C[j])
        meta.append({
            "terms": brain.cluster_terms([texts[i] for i in idxs]),
            "exemplar": texts[central][:200].replace("\n", " "),
            "size": len(idxs),
            "last_observed": datetime.fromtimestamp(
                max(turns[i]["ts"] for i in idxs), tz=timezone.utc).date().isoformat(),
        })
    np.save(LIB_VEC, np.array(rows, dtype="float32"))
    LIB_META.write_text(json.dumps({"concepts": meta}, ensure_ascii=False, indent=2))
    print(f"[consolidate] {len(meta)} concepts saved.")


# ── PRIMARY: fire the merged reasoning MOVES → surface what to do ───────────
def _move_keys(p: dict, con) -> list:
    """Recognition match-keys = the REAL example situations that triggered this move
    (grounded USER turns, first-person, same register as an incoming situation) + the
    trigger as a fallback. Match like-with-like; ALL examples kept (centrality-capping
    was tested 2026-06-27 and REGRESSED — it traded count-bias for coverage loss)."""
    keys = []
    ids = p.get("source_component_ids", [])
    if ids:
        q = f"SELECT role, content FROM messages WHERE id IN ({','.join('?' * len(ids))})"
        for role, content in con.execute(q, ids).fetchall():
            if role == "user" and content and content.strip():
                keys.append(content.strip()[:300])
    keys.append(p.get("trigger", ""))
    return [k for k in keys if k.strip()]


_KEYS_CACHE = paths.BRAIN_HOME / "keys_cache.npz"


def _keys_matrix(pats):
    """Embed every move's grounded match-keys ONCE and cache to disk — the expensive
    part. Re-embeds only when patterns_library.jsonl changes (content hash). This is
    what makes the CONTINUOUS loop viable: otherwise we'd re-embed thousands of keys
    every cycle, forever. Returns (K, owner): K's L2-normalized rows align to
    owner[i] → pattern index. (max over ALL examples per move stays load-bearing —
    key-capping was tested 2026-06-27 and REGRESSED.)"""
    import numpy as np
    sig = hashlib.sha1(PATTERNS.read_bytes()).hexdigest()
    if _KEYS_CACHE.exists():
        d = np.load(_KEYS_CACHE, allow_pickle=False)
        if str(d["sig"]) == sig and d["K"].shape[0] == d["owner"].shape[0]:
            return d["K"], d["owner"]
    con = sqlite3.connect(f"file:{brain.STATE_DB}?mode=ro", uri=True)
    all_keys, owner = [], []
    for pi, p in enumerate(pats):
        for k in _move_keys(p, con):
            all_keys.append(k); owner.append(pi)
    con.close()
    if not all_keys:
        return None, None
    K = brain.embed(all_keys)
    np.savez(_KEYS_CACHE, K=K, owner=np.array(owner), sig=np.array(sig))
    return K, np.array(owner)


def _embedder_available() -> bool:
    """Is the embeddings extra installed?

    The embedder ships as an optional dependency (chromadb's local MiniLM — no API
    key, no network). Absent, no lane can match anything. That is a documented
    condition, NOT a broken lane — so every embedding call site checks here first
    and fails OPEN with a loud line, rather than raising something that surfaces as
    a lane `error` indistinguishable from a real defect.
    """
    try:
        # Test the import that will actually be used. `find_spec` would answer
        # "findable", which is not the same as "importable" — a broken or partial
        # install passes find_spec and then fails at the call.
        import chromadb.utils.embedding_functions  # noqa: F401
    except Exception:
        return False
    return True


def _fire(text: str, top: int = 3):
    """Core recognition: embed only the NEW situation, dot it against the cached
    library key-matrix (max over each move's examples). Shared by coverage(), recall(),
    and _recognize_moves. Returns None if no move library yet."""
    import numpy as np
    if not (PATTERNS.exists() and PATTERNS.read_text().strip()):
        return None
    if not _embedder_available():
        print("[recognition] embedder unavailable (pip install aura-brain[embeddings])"
              " — recall off (fail-open)", file=sys.stderr)
        return None
    pats = [json.loads(l) for l in PATTERNS.read_text().splitlines() if l.strip()]
    # T4.2 suppression: entries marked {"suppressed": true} (pruned moves) do not load,
    # so they no longer fire. Reversible — unsuppress restores the entry.
    pats = [p for p in pats if not p.get("suppressed")]
    K, owner = _keys_matrix(pats)
    if K is None:
        return None
    v = brain.embed([text])[0]
    key_sims = K @ v
    sims = np.full(len(pats), -1.0)
    for idx in range(len(owner)):
        pi = int(owner[idx])
        sims[pi] = max(sims[pi], float(key_sims[idx]))
    order = np.argsort(-sims)
    fired = [int(i) for i in order if sims[i] >= FIRE_THRESHOLD][:top]
    graph = json.loads((HERE / "graph.json").read_text()) if (HERE / "graph.json").exists() else {}
    return {"pats": pats, "sims": sims, "order": order, "fired": fired, "graph": graph, "v": v}


def _shape(f) -> dict:
    """Coverage-distribution shape (top1/top2/gap/best) from a _fire result."""
    sims, order, pats = f["sims"], f["order"], f["pats"]
    t1 = float(sims[order[0]]); t2 = float(sims[order[1]]) if len(order) > 1 else 0.0
    return {"top1": round(t1, 3), "top2": round(t2, 3), "gap": round(t1 - t2, 3),
            "best": pats[int(order[0])]["name"]}


def coverage(text: str) -> dict:
    """Coverage signal for the depth-regulator: how confident a READ do we have?
    Returns the distribution *shape* (top1, top2, gap, novel, best move), not just
    the max — because Q2 proved the max alone doesn't separate depth."""
    f = _fire(text)
    if not f:
        return {"top1": 0.0, "top2": 0.0, "gap": 0.0, "novel": True, "best": None}
    s = _shape(f)
    s["novel"] = s["top1"] < FIRE_THRESHOLD
    return s


def recall(text: str, top: int = 3) -> dict:
    """Structured recognition for the loop — what the brain HANDS BACK as data (no
    printing): the read coverage + the fired MOVES (name, present_action, trust,
    graph successors, grounded ids). novel=True → nothing fired → escalate to
    conscious. This is the live "subconscious surface" the grounded loop consumes."""
    f = _fire(text, top)
    if not f:
        return {"novel": True, "coverage": {"top1": 0.0, "top2": 0.0, "gap": 0.0, "best": None}, "fired": []}
    sims, fired, graph, pats = f["sims"], f["fired"], f["graph"], f["pats"]
    moves = []
    for i in fired:
        p = pats[i]
        c = p.get("confidence", {})
        proven = c.get("hits", 0) + c.get("misses", 0)
        succ = sorted(graph.get(p["name"], {}).items(), key=lambda x: -x[1])[:2]
        moves.append({
            "name": p["name"],
            "fire": round(float(sims[i]), 3),
            "present_action": p.get("present_action", ""),
            "action_sequence": p.get("action_sequence") or [],
            "occurrence_count": p.get("occurrence_count", 1),
            "proven": proven,
            "mean": c.get("mean"),
            "std": c.get("std"),
            "trust": "unproven" if not proven else f"{c.get('mean')}±{c.get('std')} ({c.get('hits')}✓/{c.get('misses')}✗)",
            "successors": [{"name": n, "weight": w} for n, w in succ],
            "grounded_ids": p.get("source_component_ids", [])[:8],
            # stable identity (B1): trust/pain key to this, names are for humans
            "id": p.get("id"),
            # READ-BACK (wisdom loop build ④): where this move has BROKEN before,
            # checked against THIS situation. Surfacing only — fire score untouched.
            "pain": _pain(p, f["v"]),
        })
    return {"novel": len(fired) == 0, "coverage": _shape(f), "fired": moves}


def _pain(p: dict, v):
    """Lazy, isolated read-back call: a wisdom-module failure must never take down
    recognition (the subconscious surface stays up even if the ledger read breaks).
    id-aware (B1): pain follows the move's raw lineage, not its mutable name."""
    try:
        import wisdom
        return wisdom.pain(p["name"], v=v, id_set=set(p.get("id_set") or []))
    except Exception:
        return None


def _recognize_moves(text: str, top: int = 3) -> bool:
    if not (PATTERNS.exists() and PATTERNS.read_text().strip()):
        return False
    r = recall(text, top)
    print(f'\nsituation: {text!r}\n')
    if r["novel"]:
        print(f"  ⚡ NO MOVE FIRES (top {r['coverage']['top1']:.2f} < {FIRE_THRESHOLD}) — NOVEL.")
        print("     → escalate to conscious reasoning; the brain has no move for this yet.")
        return True
    print("  the brain recognizes — these MOVES fire (no LLM, instant):")
    for rank, m in enumerate(r["fired"], 1):
        print(f"\n  [{rank}] fire={m['fire']:.2f} · trust={m['trust']} · {m['name']}  ({m['occurrence_count']}× seen)")
        if m["successors"]:
            print("      ↪ tends to lead to: " + ", ".join(f"{s['name']} (×{s['weight']})" for s in m["successors"]))
        print(f"      → DO: {m['present_action']}")
        for s in m["action_sequence"][:5]:
            print(f"         • {s}")
        print(f"      grounded by ids (openable): {m['grounded_ids']}")
    print("\n  → that's the subconscious: a situation came in, the move came back. You didn't ask it to think.")
    return True


# ── FALLBACK: coarse concept recognition (domain, not move) ─────────────────
def _recognize_concepts(text: str, top: int = 3):
    import numpy as np
    if not LIB_VEC.exists():
        print("no library yet — run:  python3 recognition.py build  (and consolidator.py for moves)")
        return
    C = np.load(LIB_VEC)
    meta = json.loads(LIB_META.read_text())["concepts"]
    v = brain.embed([text])[0]
    sims = C @ v
    order = np.argsort(-sims)
    fired = [i for i in order if sims[i] >= FIRE_THRESHOLD][:top]
    print(f'\nsituation: {text!r}   (no moves yet — falling back to coarse concepts)\n')
    if not fired:
        print(f"  ⚡ NOTHING FIRES (top {sims[int(order[0])]:.2f}) — NOVEL → escalate."); return
    for rank, i in enumerate(fired, 1):
        m = meta[i]
        print(f"  [{rank}] fire={sims[i]:.2f}  ·  {', '.join(m['terms'])}")
        print(f"      you usually: {m['exemplar']!r}")


def recognize(text: str):
    if not _recognize_moves(text):
        _recognize_concepts(text)


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    if sys.argv[1] == "build":
        role = sys.argv[2] if len(sys.argv) > 2 else "user"
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 1500
        build(role, limit)
    else:
        recognize(" ".join(sys.argv[1:]))


if __name__ == "__main__":
    main()
