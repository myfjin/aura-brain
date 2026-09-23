#!/usr/bin/env python3
"""The distiller — cluster of real traces → ONE structured reasoning-pattern.

This is brain stage 3 (see brain.py). It is the EXACT step Steward faked
(2026-06-27: hand-typed two patterns, called them "extracted"). Done honestly,
the difference is one rule: **every field must cite real source ids you can
open** — and if the cluster has no shared reasoning move, the distiller must
REJECT, not invent. Better an honest "no pattern here" than fabrication.

Pipeline:
  1. brain.load_dialogue → real turns WITH message ids (provenance)
  2. brain.embed + kmeans_cosine → the same emergent clusters
  3. pick a cluster (by --match keyword or --cluster rank)
  4. a capable model reads the REAL members and distills the schema,
     citing [id=N] for every field; or returns coherent:false
  5. validate cited ids ⊆ member ids (anti-hallucination, enforced in code)
  6. confidence = Beta(1,1) prior — UNPROVEN (earned later from outcomes,
     never asserted by the LLM); occurrence_count = real recurrence in corpus
  7. append to reasoning_patterns.jsonl (openable) + print + show real sources

Run: python3 distiller.py [--match cloud] [--cluster N] [--role user] [--limit 1500]
Reuses llm_namer.py's auth pattern (ANTHROPIC_API_KEY from steward .env).
"""
from __future__ import annotations

import argparse
import os
import json
import re
import sqlite3
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # published settings module (see VENDORING.md)

import brain  # noqa: E402  (load_dialogue, embed, kmeans_cosine, cluster_terms, STATE_DB)

ENV = paths.ENV_FILE
OUT = paths.BRAIN_HOME / "reasoning_patterns.jsonl"
DEFAULT_MODEL = "claude-sonnet-4-6"   # distillation is rare + high-value → quality over Haiku
MAX_MEMBERS_IN_PROMPT = 60
MAX_CHARS_PER_MEMBER = 400


# ── the pattern object (Illia's §6B schema, present/past/future) ───────────
@dataclass
class ReasoningPattern:
    name: str
    trigger: str                      # situation signature — when it applies
    past_context: str                 # what precedent says
    present_action: str               # what to do/think now
    future_anticipation: str          # what's predicted to follow
    hypothesis: str                   # the causal/predictive claim
    action_sequence: list             # the steps
    source_component_ids: list        # provenance — openable real message ids (A6)
    occurrence_count: int             # real recurrence in the corpus
    last_observed: str                # ISO date of the most recent supporting trace
    # confidence is EARNED, never asserted: starts at the Beta(1,1) prior.
    confidence: dict = field(default_factory=lambda: {
        "mean": 0.5, "hits": 0, "misses": 0,
        "method": "Beta(1,1) prior — UNPROVEN until applied against outcomes",
    })
    outcomes: list = field(default_factory=list)   # did it hold when applied? (none yet)
    grounding: dict = field(default_factory=dict)  # field -> [ids that genuinely back it] (A6, verified)
    distilled_at: str = ""
    distilled_by: str = ""
    cluster_terms: list = field(default_factory=list)


# ── auth: mirror llm_namer.py (ANTHROPIC_API_KEY from steward .env) ────────
def _load_key() -> str:
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            if line.strip().startswith("ANTHROPIC_API_KEY"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    import os
    k = os.environ.get("ANTHROPIC_API_KEY", "")
    if not k:
        raise RuntimeError(f"ANTHROPIC_API_KEY not found in {ENV} or env")
    return k


_SYSTEM = """You are a reasoning-pattern distiller for a system that learns how a person thinks.

You are given a CLUSTER of real dialogue excerpts, each tagged [id=N], that an
unsupervised clustering grouped together. Find the ONE recurring REASONING MOVE
they share — a way of thinking/deciding/interacting — and express it in the schema.

HARD RULES (violating any = failure):
1. Abstract ONLY what is actually present in the excerpts. Invent nothing.
2. Every field must be supported by specific excerpts. List the supporting [id=N]
   numbers in "source_ids" (integers only, drawn from the ids shown).
3. A reasoning MOVE, not a topic. "Talks about models" is a topic — reject it.
   "Corrects a recurring misconception when the other party repeats it" is a move.
4. If the cluster is only topical overlap with no shared reasoning move, return
   {"coherent": false, "reason": "<why>"}. Rejecting is correct and valued.
5. Assign "class" (Ver's taxonomy, ratified 2026-08-14):
   STATE = the move asserts an EXTERNAL FACT (a file/process/number is true or false).
   PROCEDURE = names a SEQUENCE, PRIORITY, or ORDERING of work across turns
     (validate-before-execute, fix-first-then-understand, confirm-before-archive).
   PRESCRIPTION = names a STYLE, REGISTER, DEPTH, or MODE for the current turn.
   UNCLASSIFIED = none of these (e.g. a metacognitive note on the agent's own state).

Return ONLY JSON, no prose:
{
  "coherent": true,
  "name": "kebab-case-name",
  "trigger": "the situation signature — when this applies",
  "past_context": "what precedent/history the move draws on",
  "present_action": "what to do/think in the moment",
  "future_anticipation": "what is predicted to follow",
  "hypothesis": "the causal/predictive claim behind the move",
  "action_sequence": ["step 1", "step 2", "..."],
  "class": "STATE | PROCEDURE | PRESCRIPTION | UNCLASSIFIED",
  "source_ids": [<int>, <int>, ...]
}
OR {"coherent": false, "reason": "..."}"""


def _build_prompt(members: list, header: str = "Cluster excerpts:") -> str:
    lines = [header + "\n"]
    for m in members[:MAX_MEMBERS_IN_PROMPT]:
        day = datetime.fromtimestamp(m["ts"], tz=timezone.utc).date().isoformat()
        who = f", {m['role']}" if m.get("role") else ""
        txt = m["text"][:MAX_CHARS_PER_MEMBER].replace("\n", " ")
        lines.append(f'[id={m["id"]}] ({day}{who}) "{txt}"')
    return "\n".join(lines)


def _parse_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def distill(members: list, terms: list, model: str, system: str = _SYSTEM,
            header: str = "Cluster excerpts:"):
    import anthropic
    client = anthropic.Anthropic(api_key=_load_key(), timeout=90.0)
    started = time.monotonic()
    msg = client.messages.create(
        model=model, max_tokens=1500, system=system,
        messages=[{"role": "user", "content": _build_prompt(members, header)}],
    )
    elapsed = time.monotonic() - started
    text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    data = _parse_json(text)
    usage = f"in={getattr(msg.usage,'input_tokens',0)} out={getattr(msg.usage,'output_tokens',0)} {elapsed:.1f}s"
    return data, text, usage


# ── grounding-verify pass (A6: keep only ids that genuinely SUPPORT) ───────
_VERIFY_SYSTEM = """You are a grounding verifier. Verify before claim (A6).

Given a reasoning PATTERN and candidate SOURCE excerpts (each [id=N]), decide for
EACH id whether it provides real evidence for AT LEAST ONE field of the pattern.
A source need NOT show the whole pattern — backing ONE field is enough. But a mere
topic mention that evidences no field does NOT count.

Fields: trigger, past_context, present_action, future_anticipation, hypothesis.

Return ONLY compact JSON, one entry per id, no prose, no "why":
{"<id>": {"s": 1, "f": ["present_action"]}, "<id>": {"s": 0, "f": []}, ...}
s = 1 if it backs ≥1 field else 0; f = the field names it backs."""


def _full_text(ids: list) -> dict:
    con = sqlite3.connect(f"file:{brain.STATE_DB}?mode=ro", uri=True)
    out = {}
    for i in ids:
        row = con.execute("SELECT content FROM messages WHERE id=?", (i,)).fetchone()
        if row:
            out[i] = row[0]
    con.close()
    return out


def verify_grounding(pat: "ReasoningPattern", ids: list, model: str):
    import anthropic
    client = anthropic.Anthropic(api_key=_load_key(), timeout=90.0)
    texts = _full_text(ids)
    pat_summary = json.dumps({
        "name": pat.name, "trigger": pat.trigger, "past_context": pat.past_context,
        "present_action": pat.present_action, "future_anticipation": pat.future_anticipation,
        "hypothesis": pat.hypothesis,
    }, ensure_ascii=False)
    src = [f'[id={i}] "{texts.get(i,"")[:600].strip().replace(chr(10),"  ")}"' for i in ids]
    user = f"PATTERN:\n{pat_summary}\n\nSOURCES:\n" + "\n".join(src)
    msg = client.messages.create(
        model=model, max_tokens=4000, system=_VERIFY_SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    out_tok = int(getattr(msg.usage, "output_tokens", 0))
    truncated = getattr(msg, "stop_reason", None) == "max_tokens"
    data = _parse_json(text) or {}
    supported, grounding = [], {}
    for k, v in data.items():
        try:
            i = int(k)
        except (ValueError, TypeError):
            continue
        if i in ids and isinstance(v, dict) and v.get("s"):
            supported.append(i)
            for f in v.get("f", []):
                grounding.setdefault(f, []).append(i)
    usage = (f"in={getattr(msg.usage,'input_tokens',0)} out={out_tok}"
             + ("  ⚠TRUNCATED — raise max_tokens" if truncated else ""))
    return supported, grounding, usage


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--match", default="cloud", help="select cluster whose terms contain this word")
    ap.add_argument("--cluster", type=int, default=None, help="select cluster by size-rank instead")
    ap.add_argument("--role", default="user")
    ap.add_argument("--limit", type=int, default=1500)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--verify-model", default="claude-haiku-4-5", help="grounding verifier (cheap is fine)")
    args = ap.parse_args()

    print(f"[1] loading real {args.role} turns (limit {args.limit})…")
    turns = brain.load_dialogue(args.role, args.limit)
    texts = [t["text"] for t in turns]
    print(f"    {len(texts)} turns")

    print("[2] embedding + clustering (same emergent clusters as brain.py)…")
    X = brain.embed(texts)
    k = max(8, min(24, len(texts) // 60))
    labels, _ = brain.kmeans_cosine(X, k)

    # build clusters with members + terms
    clusters = []
    for j in range(k):
        idxs = [i for i in range(len(texts)) if labels[i] == j]
        if not idxs:
            continue
        clusters.append({
            "members": [turns[i] for i in idxs],
            "terms": brain.cluster_terms([texts[i] for i in idxs]),
            "size": len(idxs),
        })
    clusters.sort(key=lambda c: -c["size"])

    # select
    if args.cluster is not None:
        target = clusters[args.cluster]
    else:
        target = next((c for c in clusters if args.match.lower() in c["terms"]), None)
        if target is None:
            print(f"    no cluster with term {args.match!r}; available terms:")
            for c in clusters:
                print(f"      ({c['size']}) {', '.join(c['terms'])}")
            return
    print(f"[3] target cluster: {target['size']} turns · {', '.join(target['terms'])}\n")

    print(f"[4] distilling with {args.model} (reads the REAL traces, must cite ids)…")
    data, raw, usage = distill(target["members"], target["terms"], args.model)
    print(f"    {usage}\n")
    if data is None:
        print("    ✗ model returned unparseable output:\n", raw[:400]); return

    if not data.get("coherent", False):
        print("=" * 70)
        print("HONEST REJECTION (no shared reasoning move — this is a WIN, not a fail)")
        print("=" * 70)
        print(f"  reason: {data.get('reason','(none)')}")
        print("\n  → the guardrail worked: it refused to fabricate. Likely means this")
        print("    cluster is topical. Next refinement: feed EPISODES (turn sequences),")
        print("    not single-turn topic clusters — reasoning moves live in arcs.")
        return

    # validate cited ids ⊆ member ids (anti-hallucination, enforced in code)
    member_ids = {m["id"] for m in target["members"]}
    cited = [i for i in data.get("source_ids", []) if i in member_ids]
    dropped = [i for i in data.get("source_ids", []) if i not in member_ids]
    if dropped:
        print(f"    ⚠ dropped {len(dropped)} hallucinated ids not in cluster: {dropped}")
    if not cited:
        print("    ✗ no valid source ids — rejecting (a pattern with no provenance is theater)."); return

    ts_by_id = {m["id"]: m["ts"] for m in target["members"]}
    last = max(ts_by_id[i] for i in cited)
    pat = ReasoningPattern(
        name=data.get("name", "unnamed")[:60],
        trigger=data.get("trigger", ""),
        past_context=data.get("past_context", ""),
        present_action=data.get("present_action", ""),
        future_anticipation=data.get("future_anticipation", ""),
        hypothesis=data.get("hypothesis", ""),
        action_sequence=data.get("action_sequence", []),
        source_component_ids=cited,
        occurrence_count=target["size"],
        last_observed=datetime.fromtimestamp(last, tz=timezone.utc).date().isoformat(),
        distilled_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        distilled_by=f"anthropic:{args.model}",
        cluster_terms=target["terms"],
    )

    print("=" * 70)
    print(f"DISTILLED PATTERN:  {pat.name}")
    print("=" * 70)
    print(f"  trigger : {pat.trigger}")
    print(f"  past    : {pat.past_context}")
    print(f"  present : {pat.present_action}")
    print(f"  future  : {pat.future_anticipation}")
    print(f"  hypoth. : {pat.hypothesis}")
    print(f"  steps   : {pat.action_sequence}")
    print(f"  conf    : {pat.confidence['method']}")
    print(f"  seen    : {pat.occurrence_count}× in corpus · last {pat.last_observed}")
    print(f"  cited   : {len(cited)} ids (cluster-level, pre-verify)")

    # ── grounding-verify pass (A6: keep only ids that genuinely support) ──
    print(f"\n[5] grounding-verify ({args.verify_model} reads each source's full text; topic≠support)…")
    supported, grounding, vusage = verify_grounding(pat, cited, args.verify_model)
    dropped = [i for i in cited if i not in supported]
    print(f"    {vusage} · kept {len(supported)}/{len(cited)} · dropped {len(dropped)} topic-only")
    if dropped:
        print(f"    dropped: {dropped}")

    if not supported:
        print("\n    ✗ NO id survived verification — pattern is not grounded. NOT persisting.")
        print("      (this is the guardrail: an ungrounded pattern is theater, even if it sounds right.)")
        return

    pat.source_component_ids = supported
    pat.grounding = grounding
    pat.last_observed = datetime.fromtimestamp(
        max(ts_by_id[i] for i in supported), tz=timezone.utc).date().isoformat()
    if len(supported) < 3:
        pat.confidence["method"] += " · LOW-GROUNDING (<3 verified sources)"

    print("\n  tightened grounding (field → the real evidence that backs it):")
    for f in ("trigger", "past_context", "present_action", "future_anticipation", "hypothesis"):
        if grounding.get(f):
            print(f"    {f:20s} ← {grounding[f]}")

    # PROVE it — open the surviving sources (A6, demonstrated not claimed)
    print("\n  --- open the verified sources (these genuinely hold the pattern up) ---")
    con = sqlite3.connect(f"file:{brain.STATE_DB}?mode=ro", uri=True)
    for sid in supported[:4]:
        row = con.execute("SELECT content FROM messages WHERE id=?", (sid,)).fetchone()
        excerpt = (row[0][:160].replace("\n", " ") if row else "(not found)")
        print(f"    [id={sid}] {excerpt!r}")
    con.close()

    rec = asdict(pat)
    # Ver's taxonomy (2026-08-14): carry the move's class straight from the model
    # output. `class` is a Python keyword so it cannot be a ReasoningPattern field;
    # inject it into the record here instead. Default UNCLASSIFIED, never guess.
    rec["class"] = data.get("class", "UNCLASSIFIED")
    # B1: mint the stable id at BIRTH (raw is append-only; this id never changes,
    # and trust recorded against any canonical containing it follows it forever)
    import pattern_id
    rec["id"] = pattern_id.raw_id(rec)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"\n[6] appended (verified-grounded) → {OUT}")
    print(f"    verify any source yourself:  sqlite3 {brain.STATE_DB} 'SELECT content FROM messages WHERE id=<id>'")

    # [7] auto-close the pipeline: propagate raw → patterns_library so recognition can
    # actually fire this new move (otherwise it's distilled-but-invisible — the seam that
    # went 5 days stale, 2026-07-03). FREE variant only (--no-abstract); auto-running the
    # PAID full merge would be an unattended credit-spender (standing constraint).
    import subprocess
    merge_py = Path(__file__).resolve().parent / "merge.py"
    print("\n[7] auto-merge (--no-abstract, free) → patterns_library.jsonl …")
    try:
        subprocess.run([sys.executable, str(merge_py), "--no-abstract"], check=False, timeout=180)
    except Exception as e:
        print(f"    ⚠ auto-merge failed (raw is safe; run `python merge.py --no-abstract`): {e}")


if __name__ == "__main__":
    main()
