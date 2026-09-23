#!/usr/bin/env python3
"""identity.py — first identity analysis (I↔C dialogue) = the character-model seed.

Reads a pasted Claude+Illia transcript, segments by speaker (HEURISTIC — the export
has no labels), and measures a STYLE SIGNATURE per voice: the fingerprint each
character-model will be grounded in. "See it working" = two measurable, distinct
identities pulled straight from the real text.

Honest: segmentation is heuristic. High-confidence blocks build the signatures;
ambiguous ones are counted, not used. A label-tagged re-export sharpens it. This is
the descriptive seed; the generative character-model is built on top of it later.

Run: python3 identity.py [file]
"""
from __future__ import annotations

import re
import statistics
import sys
from collections import Counter
from pathlib import Path
import paths  # published settings module (see VENDORING.md)

F = Path(sys.argv[1]) if len(sys.argv) > 1 else paths.BRAIN_HOME / "persona.txt"

# UI action-stubs / tool traces to drop (not prose)
_NOISE = re.compile(
    r"^(ran\b|edited\b|read$|reading\b|located\b|applying\b|verified all|confirmed:|"
    r"phased?\b|gathering\b|starting phase|intel gathered|ran \d)", re.I)

_CLAUDE_PHRASE = ("let me", "before i", "i'll ", "i need to", "confirmed", "verified",
                  "here's", "to be clear", "the honest", "that said", "straight")
_ILLIA_PHRASE = ("brother", "bro ", "ahaha", "hah ", "plz", "smth", " im ", " dont ",
                 " cant ", "u@", "wanna", "lets ")
_WORD = re.compile(r"[a-zA-Z']+")
_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿\U0001F900-\U0001F9FF\U0001FA00-\U0001FAFF]")
_STOP = set("the a an and or but to of in on for with is are was be i you we it this that "
            "he she they my your our me so as at if can will not no yes do have has had".split())


def blocks(text: str) -> list:
    out = []
    for b in re.split(r"\n\s*\n", text):
        b = b.strip()
        if len(b) < 15:
            continue
        if len(b) < 70 and _NOISE.match(b):   # short action-stub
            continue
        out.append(b)
    return out


def claude_score(b: str) -> int:
    low = b.lower(); s = 0
    if "**" in b:
        s += 2
    if re.search(r"(^|\n)\s*(\d\.|[-•])", b):    # lists
        s += 1
    if "—" in b:
        s += 1
    s += sum(1 for p in _CLAUDE_PHRASE if p in low)
    if b[:1].isupper():
        s += 1
    return s


def illia_score(b: str) -> int:
    low = " " + b.lower() + " "; s = 0
    s += sum(2 for p in _ILLIA_PHRASE if p in low)
    if b[:1].islower():
        s += 2
    if "?" in b and "**" not in b:
        s += 1
    return s


def label(b: str) -> str:
    c, i = claude_score(b), illia_score(b)
    if c - i >= 2:
        return "CLAUDE"
    if i - c >= 2:
        return "ILLIA"
    return "?"


def signature(texts: list) -> dict:
    n = max(len(texts), 1)
    chars = [len(t) for t in texts] or [0]
    total = max(sum(chars), 1)
    words = Counter()
    for t in texts:
        for w in _WORD.findall(t.lower()):
            if w not in _STOP and len(w) > 2:
                words[w] += 1
    return {
        "blocks": len(texts),
        "avg_len": round(statistics.mean(chars)),
        "q_per_1k": round(sum(t.count("?") for t in texts) / total * 1000, 2),
        "excl_per_1k": round(sum(t.count("!") for t in texts) / total * 1000, 2),
        "ellipsis_per_blk": round(sum(t.count("...") for t in texts) / n, 2),
        "emoji_per_blk": round(sum(len(_EMOJI.findall(t)) for t in texts) / n, 2),
        "lowercase_start": round(sum(1 for t in texts if t[:1].islower()) / n, 2),
        "markdown_rate": round(sum(1 for t in texts if "**" in t) / n, 2),
        "top_words": [w for w, _ in words.most_common(14)],
    }


def main():
    text = F.read_text(encoding="utf-8", errors="ignore")
    bs = blocks(text)
    g = {"CLAUDE": [], "ILLIA": [], "?": []}
    for b in bs:
        g[label(b)].append(b)
    print(f"file: {F.name}  ·  {len(bs)} blocks  ·  "
          f"ILLIA {len(g['ILLIA'])} / CLAUDE {len(g['CLAUDE'])} / ambiguous {len(g['?'])}\n")
    sigs = {}
    for who in ("ILLIA", "CLAUDE"):
        sg = signature(g[who]); sigs[who] = sg
        print(f"=== {who} identity signature ({sg['blocks']} blocks) ===")
        for k, v in sg.items():
            if k == "top_words":
                print(f"   signature words : {', '.join(v)}")
            elif k != "blocks":
                print(f"   {k:16}: {v}")
        print()
    # distinctiveness — the axes that separate the two voices most
    print("=== what separates the two voices ===")
    for k in ("lowercase_start", "markdown_rate", "emoji_per_blk", "ellipsis_per_blk",
              "q_per_1k", "excl_per_1k", "avg_len"):
        i, c = sigs["ILLIA"][k], sigs["CLAUDE"][k]
        print(f"   {k:16}  ILLIA {i:>7}   CLAUDE {c:>7}   Δ {round(abs(i - c), 2)}")


if __name__ == "__main__":
    main()
