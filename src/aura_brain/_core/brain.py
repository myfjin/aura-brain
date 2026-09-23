#!/usr/bin/env python3
"""The brain that builds its own logic.

Illia's definition (2026-06-27): PCE is "a brain with logic who builds himself
logic — literally a brain." The key word is *himself*. We do NOT hand it the
categories (that was the regex decomposer's mistake — five pre-written sysadmin
types). Instead the brain FORMS its own concepts
from the real dialogue:

    perception      → read real turns from state.db (not telemetry)
    concept-formation → embed + cluster, unsupervised → emergent logic   ← THIS FILE
    recognition     → a new turn → which self-formed concepts fire        (next)
    reasoning       → compose fired concepts                              (next)
    growth          → re-ingest more dialogue → re-form the logic         (next)

This file is stage 2: concept-formation. The clusters it produces are the logic
the brain built ITSELF from your actual words. No category is named in advance;
naming happens AFTER, by describing what emerged.

Run:  python3 brain.py [role] [limit]
  role  : user (default) | assistant | all
  limit : max recent substantive turns to use (default 1500)
"""
from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import paths  # published settings module (see VENDORING.md)

STATE_DB = paths.STATE_DB  # YOUR corpus; unset -> ~/.aura-brain/dialogue.db
OUT = paths.BRAIN_OUT

# ── perception: pull REAL dialogue, strip the noise ───────────────────────
# Status/tool/rate-limit lines are not reasoning. A turn is a conversational
# turn (40–4000 chars); giant pastes (docs) are not voice, so we skip them.
_NOISE_PREFIX = ("⏱️", "💻", "✍️", "🔧", "🔍", "⚙️", "🐍", "💾", "📊", "⏳", "✅",
                 "❌", "🔄", "🤖")
_NOISE_SUBSTR = (
    "rate-limiting", "still working", "approved once", "approved permanently",
    "interrupting current task", "self-improvement review", "the user sent a text document",
)
_MIN_CHARS, _MAX_CHARS = 40, 4000


def _is_noise(text: str) -> bool:
    s = text.strip()
    if not s or s.startswith(_NOISE_PREFIX):
        return True
    low = s.lower()
    return any(tok in low for tok in _NOISE_SUBSTR)


def load_dialogue(role: str = "user", limit: int = 1500) -> list[dict]:
    con = sqlite3.connect(f"file:{STATE_DB}?mode=ro", uri=True)
    where = "" if role == "all" else "AND role = ?"
    args = () if role == "all" else (role,)
    rows = con.execute(
        f"""SELECT id, session_id, role, content, timestamp FROM messages
            WHERE content IS NOT NULL AND role IN ('user','assistant') {where}
            ORDER BY timestamp DESC""",
        args,
    ).fetchall()
    con.close()
    turns = []
    for mid, sid, r, content, ts in rows:
        c = content.strip()
        if _MIN_CHARS <= len(c) <= _MAX_CHARS and not _is_noise(c):
            # id + session_id carried for provenance — every distilled pattern
            # must be openable back to the real message (A6).
            turns.append({"id": mid, "session_id": sid, "role": r, "text": c, "ts": ts})
        if len(turns) >= limit:
            break
    turns.reverse()  # back to chronological
    return turns


# ── concept-formation: embed, then let clusters form THEMSELVES ───────────
def embed(texts: list[str]):
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
    import numpy as np
    vecs = np.array(DefaultEmbeddingFunction()(texts), dtype="float32")
    # L2-normalize → cosine == dot product
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


def kmeans_cosine(X, k: int, iters: int = 60, seed: int = 7):
    """Spherical k-means (cosine). numpy-only, no sklearn dependency."""
    import numpy as np
    rng = np.random.default_rng(seed)
    # k-means++ style seed: first random, rest far from chosen
    idx = [int(rng.integers(len(X)))]
    for _ in range(k - 1):
        sims = (X @ X[idx].T).max(axis=1)      # similarity to nearest center
        d = 1.0 - sims                          # distance
        p = np.clip(d, 1e-9, None); p /= p.sum()
        idx.append(int(rng.choice(len(X), p=p)))
    C = X[idx].copy()
    labels = np.zeros(len(X), dtype=int)
    for _ in range(iters):
        sims = X @ C.T                           # (n,k) cosine
        new = sims.argmax(axis=1)
        if (new == labels).all():
            break
        labels = new
        for j in range(k):
            members = X[labels == j]
            if len(members):
                v = members.mean(axis=0)
                n = np.linalg.norm(v)
                C[j] = v / n if n else C[j]
    return labels, C


# ── naming: describe what EMERGED (after the fact, never before) ───────────
_STOP = set("""the a an and or but if then so to of in on for with at by from as is are was were
be been being it its this that these those i you he she we they me my your our their his her them us
do does did done have has had not no yes can could will would should may might must just now here there
what which who whom whose when where why how all any some more most other into out up down off over
will im i'm dont don't its it's we're you're that's so we get got like really want need know about smth""".split())
_WORD = re.compile(r"[a-zA-Z']{3,}")


def cluster_terms(texts: list[str], top: int = 6) -> list[str]:
    c = Counter()
    for t in texts:
        seen = set(w.lower() for w in _WORD.findall(t))
        for w in seen:
            if w not in _STOP:
                c[w] += 1
    return [w for w, _ in c.most_common(top)]


def main():
    role = sys.argv[1] if len(sys.argv) > 1 else "user"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
    import numpy as np

    print(f"[perception] loading real {role} turns from state.db (limit {limit})…")
    turns = load_dialogue(role, limit)
    texts = [t["text"] for t in turns]
    n = len(texts)
    print(f"[perception] {n} substantive turns (noise stripped)\n")
    if n < 20:
        print("not enough turns; widen role/limit."); return

    print(f"[concept-formation] embedding {n} turns…")
    X = embed(texts)
    k = max(8, min(24, n // 60))
    print(f"[concept-formation] forming concepts: k={k} (emergent, no preset categories)\n")
    labels, C = kmeans_cosine(X, k)

    # order concepts by size; describe each by emergent terms + central exemplar
    concepts = []
    for j in range(k):
        members = [i for i in range(n) if labels[i] == j]
        if not members:
            continue
        sims = X[members] @ C[j]
        central = members[int(np.argmax(sims))]
        cohesion = float(sims.mean())          # tight = real concept, loose = vague
        terms = cluster_terms([texts[i] for i in members])
        concepts.append({
            "size": len(members), "cohesion": round(cohesion, 3),
            "terms": terms,
            "exemplar": texts[central][:160].replace("\n", " "),
        })
    concepts.sort(key=lambda c: -c["size"])

    print("=" * 72)
    print("THE LOGIC THE BRAIN BUILT ITSELF (emergent concepts, your voice)")
    print("=" * 72)
    for i, c in enumerate(concepts, 1):
        print(f"\n[{i}] {c['size']} turns · cohesion {c['cohesion']}  ·  {', '.join(c['terms'])}")
        print(f"    e.g. {c['exemplar']!r}")

    OUT.write_text(json.dumps({
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "role": role, "n_turns": n, "k": k, "concepts": concepts,
    }, ensure_ascii=False, indent=2))
    print(f"\n[persist] {len(concepts)} self-formed concepts → {OUT}")
    print("[honest] this is concept-FORMATION only. recognition/reasoning/growth next.")


if __name__ == "__main__":
    main()
