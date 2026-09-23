#!/usr/bin/env python3
"""gate.py — the grounding-gate: is a generated turn FAITHFUL to the real person,
or eloquent-drift?

For each character it builds a VOICE REFERENCE from their REAL turns (embedded
sample), then scores any turn by how near it sits to that real voice (max cosine to
real utterances + centroid cosine). Calibrated against the REAL BASELINE — real
held-out turns scored against the reference — so the verdict is "in the person's
real range, or below it," not an arbitrary number. This is what separates a
faithful character-model from two of Claude's cousins doing improv in costume.

Run: python3 gate.py
"""
from __future__ import annotations

import glob
import json
import os
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths  # published settings module (see VENDORING.md)

import identity      # noqa: E402
import brain         # noqa: E402
import filter_tg     # noqa: E402

# ── offline corpora ─────────────────────────────────────────────────────────
# These are the gate/generator path ONLY — nothing on the advice loop reads them,
# and the published package does not ship the files. Env-overridable so a
# deployment can point them anywhere (the published copy routes them through
# `paths.py`; see VENDORING.md). They were hardcoded HERE-relative, which meant
# the published code read crew-specific filenames by a path that cannot exist
# for anyone else.
PERSONA_TXT = paths.PERSONA_TXT
TG_EXPORT = paths.TG_EXPORT
MOVE_SPACES = paths.MOVE_SPACES

random.seed(7)
REF_N = 400          # real turns embedded as the voice reference
BASE_N = 60          # held-out real turns to measure the real baseline


def illia_claude_turns() -> dict:
    text = PERSONA_TXT.read_text(errors="ignore")
    g = {"Illia": [], "Claude": []}
    for b in identity.blocks(text):
        lab = identity.label(b)
        if lab == "ILLIA":
            g["Illia"].append(b)
        elif lab == "CLAUDE":
            g["Claude"].append(b)
    return g


def _tg_turns(sender: str) -> list:
    d = json.load(open(TG_EXPORT, encoding="utf-8"))
    out = []
    for m in d.get("messages", []):
        if m.get("type") != "message" or m.get("from") != sender:
            continue
        t = m.get("text")
        if isinstance(t, list):
            t = "".join(x if isinstance(x, str) else x.get("text", "") for x in t)
        if not isinstance(t, str):
            continue
        c = filter_tg.clean_message(t)
        if len(c) >= 80 and not c.lower().startswith("unknown command") and not filter_tg.is_noise_turn(c):
            out.append(c)
    return out


def steward_turns() -> list:
    return _tg_turns("Steward")


def illia_turns() -> list:               # labeled, plentiful (~4962) — proper Illia voice
    return _tg_turns("human agent")


def illia_corpus() -> list:
    """Illia is BOTH personas — SYNTHESIS (his correction 2026-06-28): his transcript voice +
    his telegram voice, unioned + deduped. One canonical corpus so the persona is TRAINED and
    MEASURED on the same whole-of-Illia (fixes the train/measure mismatch by union, not choice)."""
    seen, out = set(), []
    for t in illia_claude_turns()["Illia"] + illia_turns():
        k = t.strip()[:120]
        if k and k not in seen:
            seen.add(k); out.append(t)
    return out


def claude_turns() -> list:              # MY real turns — clean, role-labeled, full range
    out = []
    for f in glob.glob(str(paths.LAB_ROOT / ".claude/projects/**/*.jsonl"), recursive=True):
        for line in open(f, encoding="utf-8", errors="ignore"):
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if o.get("type") != "assistant":
                continue
            c = (o.get("message") or {}).get("content")
            if not isinstance(c, list):
                continue
            txt = "".join(b.get("text", "") for b in c
                          if isinstance(b, dict) and b.get("type") == "text").strip()
            if len(txt) >= 80 and not filter_tg.is_noise_turn(txt):
                out.append(txt)
    return out


def voice_score(text: str, R):
    """max cosine to any real utterance + cosine to the voice centroid."""
    import numpy as np
    v = brain.embed([text])[0]
    sims = R @ v
    cen = R.mean(axis=0)
    cen = cen / (np.linalg.norm(cen) or 1.0)
    return float(sims.max()), float(cen @ v)


# ── move-libraries (per character that has one) — the SUBSTANCE / novelty-safe axis ──
_MOVE_LIB = {
    "Steward": (MOVE_SPACES / "steward_moves.npy", MOVE_SPACES / "steward_moves.json"),
    "Illia": (MOVE_SPACES / "illia_moves.npy", MOVE_SPACES / "illia_moves.json"),
    "Claude": (MOVE_SPACES / "claude_moves.npy", MOVE_SPACES / "claude_moves.json"),
}


def load_moves(name: str):
    import numpy as np
    pair = _MOVE_LIB.get(name)
    if not pair or not pair[0].exists():
        return None, None
    M = np.load(pair[0])
    fams = json.loads(pair[1].read_text())["moves"] if pair[1].exists() else []
    return M, fams


def move_score(text: str, M):
    """max cosine to any recurring move-centroid + which move it landed in."""
    v = brain.embed([text])[0]
    sims = M @ v
    j = int(sims.argmax())
    return float(sims[j]), j


def build_reference(turns: list, ref_n: int = REF_N, base_n: int = BASE_N):
    """Returns (R, baseline) — the voice-reference matrix + the REAL baseline
    (held-out real turns vs the reference). Reusable by the live gate in generator."""
    import numpy as np
    pool = turns[:]
    random.shuffle(pool)
    n_ref = min(ref_n, max(1, int(len(pool) * 0.7)))
    ref, held = pool[:n_ref], pool[n_ref:n_ref + base_n]
    if not ref:
        return None, 0.0
    R = brain.embed(ref)
    base = [voice_score(t, R)[0] for t in held]
    return R, (float(np.mean(base)) if base else 0.0)


def build_move_reference(name: str, turns: list, base_n: int = BASE_N):
    """The SUBSTANCE axis, per character: load their move-library (recurring reasoning-move
    centroids) + measure their REAL move baseline (how near their own turns land to it).
    Returns (M, fams, move_baseline), or (None, None, 0.0) if no move-lib exists for `name`.
    Complements build_reference: voice = sounds-like-them, move = reasons-like-them."""
    import numpy as np
    M, fams = load_moves(name)
    if M is None:
        return None, None, 0.0
    pool = turns[:]
    random.shuffle(pool)
    mb = [move_score(t, M)[0] for t in pool[:base_n]]
    return M, fams, (float(np.mean(mb)) if mb else 0.0)


def main():
    import numpy as np
    chars = {}
    g = illia_claude_turns()
    chars["Illia"] = illia_turns()        # telegram (labeled, plentiful) — fixes the 0.0 baseline
    chars["Claude"] = g["Claude"]         # transcript heuristic — only Claude source we have
    chars["Steward"] = steward_turns()

    refs, baselines = {}, {}
    print("building voice references (embedding real turns)…\n")
    for name, turns in chars.items():
        pool = turns[:]; random.shuffle(pool)
        n_ref = min(REF_N, max(1, int(len(pool) * 0.7)))   # always leave held-out for a baseline
        ref, held = pool[:n_ref], pool[n_ref:n_ref + BASE_N]
        if not ref:
            continue
        R = brain.embed(ref)
        refs[name] = R
        base = [voice_score(t, R)[0] for t in held]
        baselines[name] = float(np.mean(base)) if base else 0.0
        print(f"  {name:8} · ref {len(R)} turns · REAL baseline max-sim = "
              f"{baselines[name]:.3f}  (n={len(base)} held-out)")

    # load move-libraries + their REAL move baselines (substance axis)
    move_libs = {}
    for name in chars:
        M, fams = load_moves(name)
        if M is None:
            continue
        pool = chars[name][:]; random.shuffle(pool)
        mb = [move_score(t, M)[0] for t in pool[:BASE_N]]
        move_libs[name] = (M, fams, float(np.mean(mb)) if mb else 0.0)
        print(f"  {name:8} · move-lib {len(M)} families · REAL move baseline = {move_libs[name][2]:.3f}")

    for fname in ("generated_claude_steward.jsonl", "generated_dialogue.jsonl"):
        p = HERE / fname
        if not p.exists():
            continue
        print(f"\n=== {fname} ===")
        vacc, macc = {}, {}
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            t = json.loads(line); spk = t["speaker"]
            R, base = refs.get(spk), baselines.get(spk)
            if R is None:
                continue
            mx, _ = voice_score(t["text"], R)
            vacc.setdefault(spk, []).append(mx)
            vtag = "voice✓" if mx >= base - 0.05 else ("voice~" if mx >= base - 0.12 else "voice✗")
            ml = move_libs.get(spk)
            if ml:
                M, fams, mbase = ml
                msc, mj = move_score(t["text"], M)
                macc.setdefault(spk, []).append(msc)
                fired = ", ".join(fams[mj]["terms"][:3]) if fams and mj < len(fams) else str(mj)
                mtag = "move✓" if msc >= mbase - 0.05 else ("move~" if msc >= mbase - 0.12 else "move✗")
                # FAITHFUL if it sounds like him OR makes a real move (substance, novelty-safe)
                faith = "FAITHFUL" if ("✓" in vtag or "✓" in mtag) else (
                        "weak" if ("~" in vtag or "~" in mtag) else "DRIFT")
                print(f"  turn {t['turn']:>2} {spk:8} {vtag}({mx:.2f}/{base:.2f}) "
                      f"{mtag}({msc:.2f}/{mbase:.2f}) [{fired}]  → {faith}")
            else:
                gap = mx - base
                faith = "FAITHFUL" if gap >= -0.05 else ("weak" if gap >= -0.12 else "DRIFT")
                print(f"  turn {t['turn']:>2} {spk:8} {vtag}({mx:.2f}/{base:.2f})  → {faith}")
        print("  --- summary ---")
        for spk in vacc:
            vm = float(np.mean(vacc[spk])); base = baselines[spk]
            out = f"  {spk:8} voice {vm:.3f}/{base:.2f}"
            if spk in macc:
                mm = float(np.mean(macc[spk])); mb = move_libs[spk][2]
                sub = "FAITHFUL" if mm >= mb - 0.05 else ("weak" if mm >= mb - 0.12 else "DRIFT")
                out += f"  ·  move {mm:.3f}/{mb:.2f}  →  substance: {sub}"
            else:
                out += f"  →  {'FAITHFUL' if vm >= base-0.05 else 'weak' if vm >= base-0.12 else 'DRIFT'}"
            print(out)


if __name__ == "__main__":
    main()
