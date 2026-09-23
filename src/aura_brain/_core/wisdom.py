#!/usr/bin/env python3
"""wisdom.py — the Wisdom Loop: fire stream + harvester.

Build ①+② of WISDOM-LOOP-DESIGN-2026-07-04.md (gap #3 of the 07-03 report). Before
this file, advise() fires EVAPORATED — 2 move-outcomes ever recorded, node.step frozen
advisory forever. Now every real consultation logs a PENDING fire row, and the
harvester scans the shared record (the trialogue) AFTER each fire to PROPOSE the
wisdom-loop facts for a human to confirm:

  held        — did the fire cause a STOP-TO-THINK? (def 1: trust pays for the HEAR,
                not the OBEY). LOUD-FIRST (def 5): only a visible track counts.
  detected_by — who noticed a failure: self|other|none (def 4: self-detection is the
                graduation currency; other-detected while autonomous = demotion).
  conclusion / outcome — wisdom content, recorded but NEVER paid (def 3:
                thought+succeeded ≡ thought+failed).

Machine proposes, human disposes — a proposal never enters the ledger unconfirmed
(same law as grade_queue; no fabricated outcomes, no farming pain for data).
The gate/demotion calculator over the motion window is build step ⑤ — NOT here.

HONEST v1 caveats: the signature lists are seeds mined from our lived register, and
that register is thick with deliberation words — expect OVER-proposal of held=true;
the human confirm is the filter, by design. Quiet thinking is missed on purpose:
loud-first is the law at this trust stage.

  python3 wisdom.py harvest        # scan new fires vs the trialogue → write proposals
  python3 wisdom.py list           # pending proposals + evidence
  python3 wisdom.py confirm <hash> <y|n> [--conclusion adopted|rejected|modified]
        [--outcome worked|failed|unknown] [--detected self|other|none]
        [--fixed bounded|unfixed] [--note "..."]
  python3 wisdom.py dismiss <hash> # rehearsed/test fire — mark, record NOTHING
  python3 wisdom.py selftest       # deterministic; temp files only, no real data
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths  # published settings module (see VENDORING.md)


FIRES = paths.MOVE_FIRES
TRIALOGUE = paths.TRIALOGUE

# pce-0 citizenship (DEPLOYMENTS.yaml, sealed 2026-07-05): every fire row this
# module writes belongs to brain-dialogue. Trust never transfers across deployments.
DEPLOYMENT = "brain-dialogue"

WINDOW_MIN = 90      # how far after a fire the harvester looks (engineering default)
MAX_ENTRIES = 15     # …and at most this many record entries

# Signature seeds (v1, deterministic — the bullshit-detector must not itself be an LLM).
# Deliberation = loud tracks of a stop-to-think in the turns after the fire.
DELIBERATION = (
    "let me think", "let me verify", "verify before", "let me check", "checked",
    "i ran", "ran it", "ran the", "tested", "push back", "pushing back", "i disagree",
    "hold on", "wait —", "wait,", "before claiming", "the hole", "counter-", "actually,",
    "re-read", "read it first", "grounded", "verified",
)
# Correction = an OTHER voice catching a failure (detected_by=other — the demotion axis).
CORRECTION = (
    "no brother", "that's not what i", "not what i mean", "you misunderstood",
    "you misunderstand", "wrong space", "that's wrong", "you missed", "i didn't ask",
    "actually no", "stop brother", "you keep misunderstanding",
)
# Self-catch = the actor flagging its OWN failure (detected_by=self — the wisdom signature).
SELF_CATCH = (
    "i was wrong", "my mistake", "correcting myself", "i misfired", "false positive",
    "caught my own", "let me retract", "i overclaimed", "i over-corrected", "reverting",
    "i owned the", "own the miss", "my miss",
)


PAIN_SIM = 0.40   # "shaped like this" cosine (engineering default; tune from motion)
_PAIN_CACHE: dict = {}   # (move, ledger mtime) -> failure-situation embeddings


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _load(p: Path) -> list:
    """Per-line parse. 2026-08-22: this raised on the first malformed line and
    nothing caught it, so `wisdom.py harvest` died with a traceback for 9 days
    once the trialogue took 10 corrupt lines. Loud was right; fatal was not."""
    if not p.exists():
        return []
    rows, bad = [], 0
    for l in p.read_text().splitlines():
        if not l.strip():
            continue
        try:
            rows.append(json.loads(l))
        except Exception:
            bad += 1
    if bad:
        print("[wisdom] WARNING: skipped %d malformed line(s) in %s"
              % (bad, p.name), file=sys.stderr)
    return rows


def _save(p: Path, rows: list) -> None:
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def log_fire(*, situation: str, move: str | None, fire: float = 0.0, resolution: str = "",
             directive: str = "", proposed: str = "", trust: str = "", caller: str = "",
             lane: str = "", fires_path: Path | None = None) -> str:
    """Append one PENDING fire row; returns its hash. NEVER raises (runs on the MCP
    advise path — a logging failure must not break the advice) and never writes stdout
    (JSON-RPC stream). Math front-door results are skipped: `math:*` is not a library
    move and has no deliberation to grade."""
    try:
        if not move or str(move).startswith("math:"):
            return ""
        p = fires_path or FIRES
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        h = hashlib.sha1(f"{situation}|{ts}".encode()).hexdigest()[:12]
        p.parent.mkdir(parents=True, exist_ok=True)
        evt = {"fire_hash": h, "ts": ts, "caller": caller, "situation": situation[:500],
               "move": move, "fire": fire, "resolution": resolution,
               "directive": (directive or "")[:200], "proposed": (proposed or "")[:200],
               "trust": str(trust), "lane": lane or "brain", "harvested": False,
               "graded": False, "deployment": DEPLOYMENT}
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(evt, ensure_ascii=False) + "\n")
        return h
    except Exception as e:  # fail-open, stderr only
        print(f"[wisdom.log_fire] fail-open: {e}", file=sys.stderr)
        return ""


def _scan(entries: list, move: str) -> list:
    """Tier-1 evidence scan over the record entries after a fire. One hit per kind
    per entry (a turn that deliberates loudly twice is still one deliberation)."""
    ev = []
    for e in entries:
        text = e.get("content", "")
        low = text.lower()
        for kind, sigs in (("deliberation", DELIBERATION), ("correction", CORRECTION),
                           ("self_catch", SELF_CATCH)):
            for s in sigs:
                i = low.find(s)
                if i >= 0:
                    ev.append({"kind": kind, "speaker": e.get("speaker", "?"),
                               "ts": e.get("timestamp", ""),
                               "quote": text[max(0, i - 40):i + 90].strip()})
                    break
        if move and move in text:
            ev.append({"kind": "engagement", "speaker": e.get("speaker", "?"),
                       "ts": e.get("timestamp", ""), "quote": f"(names the move {move!r})"})
    return ev


def harvest(fires_path: Path | None = None, trialogue_path: Path | None = None,
            window_min: int = WINDOW_MIN, max_entries: int = MAX_ENTRIES,
            now: datetime | None = None) -> int:
    """Scan unharvested fires against the shared record; write a PROPOSAL onto each.
    A fire younger than the window with nothing after it yet stays pending (the next
    harvest will see more record). Returns how many proposals were written."""
    fp = fires_path or FIRES
    rows = _load(fp)
    tl = _load(trialogue_path or TRIALOGUE)
    now = now or datetime.now(timezone.utc)
    all_fire_ts = sorted(_ts(x["ts"]) for x in rows)
    n = 0
    for r in rows:
        if r.get("harvested") or r.get("graded"):
            continue
        fired_at = _ts(r["ts"])
        # a fire's window also CUTS at the next fire: evidence attributes to the fire
        # it followed most closely, or overlapping windows cross-contaminate (selftest
        # caught this: h2's correction leaked into h1's proposal).
        nxt = next((t for t in all_fire_ts if t > fired_at), None)
        after = [e for e in tl if e.get("timestamp") and _ts(e["timestamp"]) > fired_at
                 and (_ts(e["timestamp"]) - fired_at).total_seconds() <= window_min * 60
                 and (nxt is None or _ts(e["timestamp"]) <= nxt)]
        after = after[:max_entries]
        if not after and (now - fired_at).total_seconds() < window_min * 60:
            continue  # too fresh — leave for the next harvest
        ev = _scan(after, r.get("move") or "")
        kinds = {x["kind"] for x in ev}
        r["proposal"] = {
            "held": bool(kinds & {"deliberation", "self_catch", "engagement"}),
            "detected_by": ("other" if "correction" in kinds
                            else "self" if "self_catch" in kinds else "none"),
            "evidence": ev[:6],
            "method": "heuristic-v1 (loud tracks only; human confirm is the filter)",
        }
        r["harvested"] = True
        n += 1
    _save(fp, rows)
    return n


def confirm(h: str, held: bool, conclusion: str = "", outcome: str = "",
            detected: str = "", fixed: str = "", note: str = "") -> dict:
    """Human confirmation → the ONLY path into the ledger. Records the wisdom-loop
    row via outcomes.record and marks the fire graded."""
    rows = _load(FIRES)
    row = next((r for r in rows if r.get("fire_hash") == h), None)
    if row is None:
        raise ValueError(f"no fire with hash {h}")
    import outcomes
    ev = (row.get("proposal") or {}).get("evidence") or []
    track = "; ".join(f"{x['speaker']}@{x['ts']}·{x['kind']}" for x in ev[:3])
    conf = outcomes.record(
        row["move"], held, situation=row.get("situation", ""),
        note=note or "[wisdom] human-confirmed harvest proposal",
        conclusion=conclusion, outcome=outcome, detected_by=detected,
        fixed=fixed, track=track)
    row["graded"] = True
    row["grade_held"] = bool(held)
    _save(FIRES, rows)
    return conf


def _failure_rows(move: str, ledger_path: Path | None = None, id_set: set | None = None) -> list:
    """The move's PAIN rows — the wisdom content of failure. Two row shapes coexist:
    new wisdom rows (`outcome == "failed"` — held may be True: we thought AND it broke,
    which is honorable pain, def 2) and legacy pre-07-04 rows (held=False under the OLD
    did-it-work semantics; no wisdom fields present). Rows without a situation text
    can't be read back — skipped. Matching is id-aware (B1): pattern_ids intersection
    is authoritative when both sides carry ids, name equality is the legacy fallback —
    so the pain follows the move through renames/re-merges, like all trust."""
    import pattern_id
    lp = ledger_path or (HERE / "outcomes.jsonl")
    out = []
    for r in _load(lp):
        if r.get("kind") == "review" or not pattern_id.match(r, move, id_set or set()):
            continue
        if r.get("outcome") == "failed":
            out.append({**r, "legacy": False})
        elif "outcome" not in r and "conclusion" not in r and r.get("held") is False:
            out.append({**r, "legacy": True})
    return [r for r in out if (r.get("situation") or "").strip()]


def pain(move: str, v=None, text: str = "", ledger_path: Path | None = None,
         id_set: set | None = None) -> dict | None:
    """Build ④ — the READ-BACK, the design's hard requirement: outcome-equality
    (thought+failed pays like thought+succeeded) is only SAFE if the pain gets read.
    When a move fires, surface where it has BROKEN: how many recorded failures, and
    the closest failure-situation to the incoming one. SURFACING, not conditioning —
    fire scores are untouched; the whisper lands out loud and the caller decides
    (same law as everything advisory). NEVER raises (runs inside recognition);
    returns None when the move has no readable pain."""
    try:
        rows = _failure_rows(move, ledger_path, id_set=id_set)
        if not rows:
            return None
        import numpy as np
        import brain
        lp = ledger_path or (HERE / "outcomes.jsonl")
        key = (move, tuple(sorted(id_set or ())), lp.stat().st_mtime_ns)
        F = _PAIN_CACHE.get(key)
        if F is None:
            F = brain.embed([r["situation"][:300] for r in rows])
            _PAIN_CACHE.clear()  # tiny: ledger changes rarely; one live key is enough
            _PAIN_CACHE[key] = F
        if v is None:
            v = brain.embed([text])[0]
        sims = F @ v
        i = int(np.argmax(sims))
        top = float(sims[i])
        return {
            "n_failures": len(rows),
            "closest": {"situation": rows[i]["situation"][:200], "sim": round(top, 3),
                        "ts": rows[i].get("ts", ""), "legacy": rows[i]["legacy"]},
            "shaped_like_this": top >= PAIN_SIM,
            "whisper": (f"this move has BROKEN in {len(rows)} recorded situation(s)"
                        + (f" — the closest is shaped like this one (sim {top:.2f})"
                           if top >= PAIN_SIM else "")),
        }
    except Exception as e:  # fail-open: the read-back must never break recognition
        print(f"[wisdom.pain] fail-open: {e}", file=sys.stderr)
        return None


def cmd_list() -> None:
    rows = _load(FIRES)
    pending = [r for r in rows if r.get("harvested") and not r.get("graded")]
    fresh = [r for r in rows if not r.get("harvested") and not r.get("graded")]
    print(f"=== wisdom loop: {len(pending)} proposal(s) awaiting confirm"
          f" · {len(fresh)} fire(s) not yet harvested ===")
    for r in pending:
        p = r.get("proposal", {})
        print(f"\n  [{r['move']}] {r['ts']}  hash={r['fire_hash']}  caller={r.get('caller') or '?'}")
        print(f"    situation: {r.get('situation', '')[:110]!r}")
        print(f"    proposes: held={p.get('held')} · detected_by={p.get('detected_by')}")
        for x in (p.get("evidence") or [])[:4]:
            print(f"      · {x['kind']:<12} {x['speaker']:<8} {x['quote'][:90]!r}")
        print(f"    → confirm: python3 wisdom.py confirm {r['fire_hash']} <y|n> "
              f"[--conclusion adopted] [--outcome worked] [--detected self]")
    print("\nheld = a stop-to-think happened (outcome-blind). Only you know; the machine only proposes.")


def cmd_dismiss(h: str) -> None:
    rows = _load(FIRES)
    row = next((r for r in rows if r.get("fire_hash") == h), None)
    if row is None:
        print(f"no fire with hash {h}"); return
    row["graded"] = True
    row["dismissed"] = True  # rehearsed/test fire — nothing recorded (no farmed outcomes)
    _save(FIRES, rows)
    print(f"✓ dismissed {h} (marked graded, no outcome recorded).")


def selftest() -> None:
    """Deterministic, temp files only — the real stream/ledger is never touched."""
    import tempfile
    ok = 0
    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / "fires.jsonl"
        tp = Path(td) / "trialogue.jsonl"
        t0 = datetime(2026, 7, 4, 10, 0, 0, tzinfo=timezone.utc)

        def fire(sit, move, minute):
            ts = t0.replace(minute=minute).isoformat(timespec="seconds")
            row = {"fire_hash": hashlib.sha1(f"{sit}|{ts}".encode()).hexdigest()[:12],
                   "ts": ts, "caller": "test", "situation": sit, "move": move,
                   "fire": 0.4, "resolution": "ESCALATE", "directive": "", "proposed": "",
                   "trust": "", "harvested": False, "graded": False}
            with fp.open("a") as f:
                f.write(json.dumps(row) + "\n")
            return row["fire_hash"]

        def turn(minute, speaker, content):
            with tp.open("a") as f:
                f.write(json.dumps({"timestamp": t0.replace(minute=minute).isoformat(
                    timespec="seconds"), "speaker": speaker, "content": content}) + "\n")

        # fire 1: loud deliberation + self-catch after → held=True, detected=self
        h1 = fire("about to edit the config blind", "read-docs-before-editing", 0)
        turn(2, "claude", "let me verify before claiming — ran the test, caught my own mistake, reverting the edit")
        # fire 2: only an external correction after → held=False, detected=other
        h2 = fire("summarize and ship it", "plan-review-before-execution", 10)
        turn(12, "illia", "no brother, you misunderstood — that's not what i asked")
        # fire 3: silence after (window passed) → held=False, detected=none
        h3 = fire("just do the thing", "correcting-misunderstanding-through-pushback", 20)
        # fire 4: too fresh, nothing after → must stay PENDING
        h4 = fire("fresh fire", "read-docs-before-editing", 55)

        n = harvest(fires_path=fp, trialogue_path=tp, now=t0.replace(hour=12))
        # re-run harvest for h4 freshness at a time INSIDE its window with no entries:
        rows = {r["fire_hash"]: r for r in _load(fp)}
        checks = [
            ("3 proposals written, fresh fire left", n == 3),
            ("h1 held=True", rows[h1]["proposal"]["held"] is True),
            ("h1 detected=self", rows[h1]["proposal"]["detected_by"] == "self"),
            ("h2 held=False", rows[h2]["proposal"]["held"] is False),
            ("h2 detected=other", rows[h2]["proposal"]["detected_by"] == "other"),
            ("h3 held=False/none", rows[h3]["proposal"]["held"] is False
             and rows[h3]["proposal"]["detected_by"] == "none"),
            ("h4 still pending", not rows[h4].get("harvested")),
        ]
        # freshness path: harvesting h4 while inside its window leaves it pending
        n2 = harvest(fires_path=fp, trialogue_path=tp, now=t0.replace(hour=11, minute=0))
        rows2 = {r["fire_hash"]: r for r in _load(fp)}
        checks.append(("h4 pending inside window even on re-harvest",
                       not rows2[h4].get("harvested") and n2 == 0))
        # log_fire mechanics on the temp path (math + empty move skipped)
        checks.append(("log_fire skips math:*", log_fire(situation="s", move="math:solve",
                                                         fires_path=fp) == ""))
        checks.append(("log_fire skips empty move", log_fire(situation="s", move=None,
                                                             fires_path=fp) == ""))
        h5 = log_fire(situation="real fire", move="read-docs-before-editing", fires_path=fp,
                      caller="selftest")
        checks.append(("log_fire writes a pending row", bool(h5) and any(
            r["fire_hash"] == h5 and not r["harvested"] for r in _load(fp))))
        # pce-0 border regime (DEPLOYMENTS.yaml, 2026-07-05): new rows carry
        # citizenship; legacy rows without the field must keep parsing/harvesting.
        checks.append(("log_fire stamps pce-0 citizenship", any(
            r["fire_hash"] == h5 and r.get("deployment") == DEPLOYMENT
            for r in _load(fp))))
        checks.append(("legacy rows (no deployment field) still parse + harvest",
                       "deployment" not in rows[h1] and bool(rows[h1].get("proposal"))))
        # lane tag (MATHBRAIN Stage 1): default 'brain' for existing callers; L4 etc.
        # pass their own. Additive + backward-compatible like every ledger extension.
        checks.append(("log_fire defaults lane=brain", any(
            r["fire_hash"] == h5 and r.get("lane") == "brain" for r in _load(fp))))
        h6 = log_fire(situation="axiom weighed", move="check-draft-against-axiom",
                      lane="logic", fires_path=fp, caller="selftest")
        checks.append(("log_fire honors an explicit lane tag", any(
            r["fire_hash"] == h6 and r.get("lane") == "logic" for r in _load(fp))))
        checks.append(("legacy rows (no lane field) still parse", "lane" not in rows[h1]))

        # READ-BACK (build ④) — pain mechanics on a temp ledger (real embedder, local+free)
        lg = Path(td) / "ledger.jsonl"

        def led(pattern, held, situation, **kw):
            with lg.open("a") as f:
                f.write(json.dumps({"pattern": pattern, "held": held,
                                    "situation": situation, **kw}) + "\n")

        led("m-clean", True, "built the thing after reading the docs")
        led("m-burnt", True, "edited the gateway config blind and it broke",
            outcome="failed", conclusion="adopted")               # new shape: honorable pain
        led("m-burnt", False, "assumed the schema and shipped wrong fields")  # legacy miss
        led("m-burnt", True, "verified first, all good", outcome="worked")    # not pain
        checks.append(("pain None for a clean move",
                       pain("m-clean", text="anything", ledger_path=lg) is None))
        p1 = pain("m-burnt", text="about to edit the gateway config without checking",
                  ledger_path=lg)
        checks.append(("pain surfaces both failure shapes (new + legacy)",
                       bool(p1) and p1["n_failures"] == 2))
        checks.append(("closest failure is shaped like this one",
                       bool(p1) and p1["shaped_like_this"]
                       and "config" in p1["closest"]["situation"]))
        p2 = pain("m-burnt", text="the taste of coffee in the morning rain", ledger_path=lg)
        checks.append(("distant situation → pain shown but NOT shaped-like",
                       bool(p2) and not p2["shaped_like_this"]))
        # B1: pain follows raw lineage — a RENAMED move still finds its failure rows
        # via pattern_ids ∩ id_set; a name-imposter with foreign ids finds nothing.
        led("old-name-before-merge", True, "gateway config edit broke the daemon",
            outcome="failed", pattern_ids=["rid_aa", "rid_bb"])
        p3 = pain("renamed-after-merge", text="editing the gateway config again",
                  ledger_path=lg, id_set={"rid_bb", "rid_cc"})
        checks.append(("pain follows ids across a rename", bool(p3) and p3["n_failures"] == 1))
        p4 = pain("old-name-before-merge", text="editing the gateway config again",
                  ledger_path=lg, id_set={"rid_zz"})
        checks.append(("name-imposter with foreign ids gets no pain", p4 is None))

        # pce-0 border guard rides along: a broken guard must be loud HERE, in the
        # selftest habit, not discovered at the next border incident. Temp-only too.
        try:
            sys.path.insert(0, str(paths.PCE_DIR))
            import pce0_boundary
            checks.append(("pce0 border guard selftest passes",
                           pce0_boundary.selftest(quiet=True)))
        except Exception as e:
            checks.append((f"pce0 border guard selftest passes (import failed: {e})", False))

        for name, passed in checks:
            print(f"  {'✓' if passed else '✗ FAIL'}  {name}")
            ok += passed
        print(f"\n{ok}/{len(checks)} checks passed" + ("" if ok == len(checks) else " — FIX BEFORE TRUSTING"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("harvest")
    sub.add_parser("list")
    c = sub.add_parser("confirm")
    c.add_argument("hash"); c.add_argument("held", choices=["y", "n", "yes", "no"])
    c.add_argument("--conclusion", choices=["adopted", "rejected", "modified"], default="")
    c.add_argument("--outcome", choices=["worked", "failed", "unknown"], default="")
    c.add_argument("--detected", choices=["self", "other", "none"], default="")
    c.add_argument("--fixed", choices=["bounded", "unfixed"], default="")
    c.add_argument("--note", default="")
    d = sub.add_parser("dismiss"); d.add_argument("hash")
    sub.add_parser("selftest")
    a = ap.parse_args()

    if a.cmd == "harvest":
        print(f"harvested {harvest()} new fire(s) → proposals written; `wisdom.py list` to review")
    elif a.cmd == "list" or a.cmd is None:
        cmd_list()
    elif a.cmd == "confirm":
        conf = confirm(a.hash, a.held.startswith("y"), conclusion=a.conclusion,
                       outcome=a.outcome, detected=a.detected, fixed=a.fixed, note=a.note)
        print(f"✓ recorded held={a.held.startswith('y')} → Beta mean {conf['mean']} "
              f"({conf['hits']}✓/{conf['misses']}✗ — a deliberation counter, outcome-blind)")
    elif a.cmd == "dismiss":
        cmd_dismiss(a.hash)
    elif a.cmd == "selftest":
        selftest()


if __name__ == "__main__":
    main()
