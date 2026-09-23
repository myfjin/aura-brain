#!/usr/bin/env python3
"""outcomes → confidence — earn trust, never assert it.

A move's confidence starts at the Beta(1,1) prior (mean 0.5, max uncertainty).
Each time a move is APPLIED and we observe whether it HELD, we record a hit/miss.
Confidence becomes Beta(1+hits, 1+misses): mean = earned reliability, std = honest
uncertainty (wide at low N, tightening with evidence). Never asserted by an LLM —
only earned from recorded outcomes. (Schema: "confidence — earned from history,
not asserted".)

outcomes.jsonl is the SOURCE OF TRUTH (append-only). patterns_library.jsonl is
re-stamped from it — merge.py calls restamp() after every rebuild so earned trust
is never lost when the library is regenerated.

  python3 outcomes.py record <name|index> hit|miss ["note"] [--situation "..."]
  python3 outcomes.py show
  python3 outcomes.py restamp
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # published settings module (see VENDORING.md)

LIB = paths.PATTERNS_LIBRARY
LEDGER = paths.OUTCOMES_LEDGER

# [T7.5h2 rev-4] CLI safety: allow routing writes to a copy via --ledger flag or
# OUTCOMES_LEDGER env var.  This prevents dry-run contamination of the production
# ledger (5S dry-run wrote 2 test rows to prod on 2026-09-21 because close had no
# way to redirect).  The module-level LEDGER stays the production default; overrides
# are per-call (close_fire) or per-invocation (CLI --ledger / env var).
import os as _os
_DEFAULT_LEDGER = LEDGER


def _resolve_ledger_path(override: str = "") -> Path:
    """Resolve which ledger path to use.  Priority: explicit override > env var > default."""
    if override:
        return Path(override)
    env = _os.environ.get("OUTCOMES_LEDGER", "")
    if env:
        return Path(env)
    return _DEFAULT_LEDGER

# pce-0 citizenship (DEPLOYMENTS.yaml, sealed 2026-07-05): every ledger row this
# module writes belongs to brain-dialogue. Trust never transfers across deployments;
# legacy rows without the field parse unchanged (readers use .get()).
DEPLOYMENT = "brain-dialogue"

# review-verdict streams (written by the auto-fire hooks). Grading can flip a fire's
# `graded` flag here so grade_queue stays accurate no matter WHICH path graded it
# (the MCP record_review_outcome tool, or grade_queue itself). 2026-07-03.
_STREAMS = [
    *paths.REVIEW_VERDICTS,
]


def _mark_stream_graded(draft_hash: str, held: bool) -> bool:
    """Flip the `graded` flag on the stream fire with this draft_hash (searches both
    streams). Fail-safe: any error → return False, never raise into the caller (this runs
    on the MCP path, where an exception would drop the connection)."""
    if not draft_hash:
        return False
    for p in _STREAMS:
        try:
            if not p.exists():
                continue
            rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
            hit = False
            for r in rows:
                if r.get("draft_hash") == draft_hash:
                    r["graded"] = True
                    r["grade_held"] = bool(held)
                    hit = True
            if hit:
                p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
                return True
        except Exception:
            continue
    return False


def _load_lib() -> list:
    return [json.loads(l) for l in LIB.read_text().splitlines() if l.strip()] if LIB.exists() else []


def _load_ledger() -> list:
    return [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()] if LEDGER.exists() else []


def beta(hits: int, misses: int) -> dict:
    a, b = 1 + hits, 1 + misses
    mean = a / (a + b)
    var = a * b / ((a + b) ** 2 * (a + b + 1))
    unproven = (hits + misses == 0)
    return {
        "mean": round(mean, 3),
        "std": round(math.sqrt(var), 3),
        "hits": hits, "misses": misses,
        "method": f"Beta({a},{b})" + (" — UNPROVEN (no outcomes yet)" if unproven else ""),
    }


def _tally(pat, ledger: list):
    """Tally outcomes for a pattern. `pat` is a LIBRARY ROW (dict — id-aware matching
    via pattern_id.match: ids authoritative when both sides carry them, name equality
    as the legacy fallback) or a plain string (name/track equality only — the review:*
    tracks and legacy callers).

    [T7.5h2] Invariant (6E ratification): exactly one non-null `held` per `fire_hash`.
    Rows WITH fire_hash are deduped — latest non-null `held` wins. Rows WITHOUT
    fire_hash count individually (review track + legacy rows, byte-identical).
    This prevents amend rows from double-counting Beta while preserving the
    receiver-first flow (close held:null + amend held:true → 1 hit, not 0)."""
    import pattern_id
    if isinstance(pat, dict):
        name, ids = pat.get("name", ""), set(pat.get("id_set") or [])
    else:
        name, ids = pat, set()

    matching = [e for e in ledger if pattern_id.match(e, name, ids)]

    # Rows without fire_hash: count individually (one per row) — unchanged behavior
    no_fh = [e for e in matching if not e.get("fire_hash")]
    h = sum(1 for e in no_fh if e.get("held") is True)
    m = sum(1 for e in no_fh if e.get("held") is False)

    # Rows with fire_hash: dedupe — latest non-null held wins per fire_hash
    fh_groups: dict[str, list] = {}
    for e in matching:
        fh = e.get("fire_hash")
        if fh:
            fh_groups.setdefault(fh, []).append(e)
    for fh, rows in fh_groups.items():
        non_null = [e for e in rows if e.get("held") is not None]
        if non_null:
            latest = max(non_null, key=lambda e: e.get("ts", ""))
            if latest["held"] is True:
                h += 1
            elif latest["held"] is False:
                m += 1
        # If all rows for this fire_hash have held=null → no hit, no miss (W4)

    return h, m


def restamp() -> list:
    """Recompute every library pattern's confidence from the outcomes ledger.

    Also WARNS (to stderr) about MOVE outcomes whose pattern no longer exists in the
    library — a name changed by a merge, or a dropped pattern — so earned trust does
    not leak SILENTLY on every rebuild (found 2026-07-03: 1 of 2 move-outcomes orphaned).
    stderr, never stdout: restamp runs inside the MCP record_outcome path, where a stray
    stdout write corrupts the JSON-RPC stream.
    """
    import pattern_id
    lib, ledger = _load_lib(), _load_ledger()
    for p in lib:
        h, m = _tally(p, ledger)
        p["confidence"] = beta(h, m)
    with LIB.open("w", encoding="utf-8") as f:
        for p in lib:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    # orphan check: MOVE outcomes (NOT the separate review: track) matching NO live
    # pattern by id-intersection or name. Rows already marked `orphaned` (audited,
    # known-unrecoverable — e.g. the pre-id 06-27 row whose raw lineage predates the
    # current raw file) are skipped: warn about NEW leaks, not eternal ones.
    variant_names = set()
    for p in lib:
        for v in (p.get("variants") or []):
            variant_names.add(v)
    orphans = sorted({
        e.get("pattern") for e in ledger
        if e.get("kind") != "review"
        and not str(e.get("pattern", "")).startswith("review:")
        and not e.get("orphaned")
        and e.get("pattern") not in variant_names
        and not any(pattern_id.match(e, p.get("name", ""), set(p.get("id_set") or []))
                    for p in lib)
    })
    if orphans:
        import sys as _sys
        print(f"[restamp] ⚠ {len(orphans)} MOVE outcome(s) ORPHANED — earned trust with no "
              f"matching library pattern (renamed/merged/dropped), trust NOT applied: "
              f"{orphans}", file=_sys.stderr)
    return lib


def _resolve(token: str, lib: list) -> str:
    if token.isdigit():
        return lib[int(token)]["name"]
    names = [p["name"] for p in lib]
    if token in names:
        return token
    cand = [n for n in names if n.startswith(token)]
    if len(cand) == 1:
        return cand[0]
    # ValueError, NOT SystemExit: this is called from the MCP path (record_outcome →
    # node.close → record → _resolve). SystemExit is a BaseException that escapes FastMCP
    # and KILLS the server (-32000 Connection closed). A normal exception is returned to
    # the caller as a tool error instead. (CLI catches it in main() for a clean message.)
    raise ValueError(f"ambiguous/unknown move {token!r} (not a library pattern). "
                     f"{len(names)} known moves; e.g. {names[:5]}")


def record(move: str, held: bool, situation: str = "", note: str = "", *,
           conclusion: str = "", outcome: str = "", detected_by: str = "",
           fixed: str = "", track: str = "") -> dict:
    """Append one observed outcome for a move, restamp the library, and return the
    move's updated confidence. The loop and the CLI share this one path — every
    outcome flows here, so trust is always earned the same way.

    WISDOM-LOOP semantics for move rows (locked 2026-07-04, see
    WISDOM-LOOP-DESIGN-2026-07-04.md): `held` = a genuine STOP-TO-THINK happened
    (the fire was HEARD) — NOT whether the advice worked. Beta is a deliberation
    counter, outcome-blind. The optional fields are the wisdom content, recorded
    but never paid:
      conclusion  — what the thinking concluded: adopted|rejected|modified
      outcome     — what then happened: worked|failed|unknown (equal pay either way)
      detected_by — who noticed a failure: self|other|none (the graduation currency)
      fixed       — bounded|unfixed (fixability, the other half of the gate signature)
      track       — where the thinking is visible (loud-first: the evidence ref)
    """
    lib = _load_lib()
    if not lib:
        raise ValueError("no library — run consolidator.py + merge.py first")
    name = _resolve(move, lib)
    prow = next((p for p in lib if p.get("name") == name), {})
    evt = {
        "pattern": name, "held": bool(held),
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "situation": situation, "note": note, "deployment": DEPLOYMENT,
    }
    # B1: key the outcome to the canonical's raw-lineage ids — the trust follows
    # these through any rename/re-merge; the name above stays for humans/audit.
    if prow.get("id_set"):
        evt["pattern_ids"] = prow["id_set"]
    for k, v in (("conclusion", conclusion), ("outcome", outcome),
                 ("detected_by", detected_by), ("fixed", fixed), ("track", track)):
        if v:
            evt[k] = v
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(evt, ensure_ascii=False) + "\n")
    restamp()
    h, m = _tally(prow or name, _load_ledger())
    return beta(h, m)


REVIEW_PREFIX = "review:"


def record_review(verdict: str, held: bool, situation: str = "", note: str = "",
                  draft_hash: str = "") -> dict:
    """Close the loop on a review() SECOND-PASS verdict — a SEPARATE track from recognition
    moves. `verdict` is the rail/style label review() returned (e.g. 'A6', 'DEPTH:ANSWER_DIRECT',
    'NONE'). held=True = the read was RIGHT (the flag was a real lie / the style read was apt);
    held=False = it misfired. This is how the second-pass earns its OWN trust — per-rail
    precision, graded from real drafts.

    Namespaced 'review:<verdict>' so it never collides with a library pattern: restamp()
    tallies only library names, so review rows are inert there. No library lookup, so it
    can't raise the unknown-move error — any verdict string is a valid track."""
    key = verdict if verdict.startswith(REVIEW_PREFIX) else REVIEW_PREFIX + verdict
    evt = {
        "pattern": key, "held": bool(held), "kind": "review",
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "situation": situation, "note": note, "deployment": DEPLOYMENT,
    }
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(evt, ensure_ascii=False) + "\n")
    if draft_hash:
        _mark_stream_graded(draft_hash, held)   # keep grade_queue accurate for MCP-path grades
    h, m = _tally(key, _load_ledger())
    return beta(h, m)


def review_trust() -> list:
    """Every review-verdict track and its earned Beta — the second-pass's own scorecard."""
    ledger = _load_ledger()
    keys = sorted({e["pattern"] for e in ledger if e.get("kind") == "review"})
    return [{"verdict": k[len(REVIEW_PREFIX):], **beta(*_tally(k, ledger))} for k in keys]



# ─── T4.8: brain-close ─ the close command (M2) ─────────────────────────
# ONE shared function. T4.9/T4.10 import close_fire(); no second write path.

# Path to move-fires.jsonl (READ-ONLY — [W3], inherits T4.7 R1)
_LAB_ROOT = _os.environ.get("LAB_ROOT", str(paths.LAB_ROOT))
_FIRES = paths.MOVE_FIRES


def _load_fires() -> list:
    """Load move-fires.jsonl (read-only)."""
    if not _FIRES.exists():
        return []
    return [json.loads(l) for l in _FIRES.read_text().splitlines() if l.strip()]


def _find_fire(fire_hash: str) -> dict | None:
    """Find a fire row by fire_hash in move-fires.jsonl."""
    for row in _load_fires():
        if row.get("fire_hash") == fire_hash:
            return row
    return None


def _is_closed(fire_hash: str, ledger: list) -> bool:
    """Check if a fire has already been closed (fire_hash in ledger).
    [T7.5h2] Amendment rows (kind='amend') are excluded — an amend is not a new close,
    it carries axis-B data for an already-closed fire (Decision B)."""
    return any(e.get("fire_hash") == fire_hash and e.get("kind") != "amend"
               for e in ledger)


def close_fire(fire_hash: str, held_state: str, note: str = "", *, grader: str = "",
               ledger_path: str = "", dry_run: bool = False) -> dict:
    """Close one fire by hash. Appends exactly one row to the ledger.

    [C2] Hash must exist in move-fires.jsonl — else ValueError, nothing written.
    [C3] Move taken from the fire row, never from the caller.
    [C4] One close per fire — duplicate raises ValueError, nothing written.
    [W1] Only write is an APPEND to the existing ledger.
    [W2] Row carries existing keys + fire_hash + track:"advise-fire" (additive, new rows only).
    [W4] unknown writes held:null + outcome:"unknown" — no Beta tally change.
    [W5] ONE implementation — T4.9/T4.10 import this function.
    [T7.5h2 rev-4] ledger_path routes writes to a copy (CLI safety: --ledger / env var).
        When non-default, restamp() is skipped (don't rewrite prod library from a copy).
    [T7.5h2 rev-5] dry_run=True returns the row dict WITHOUT writing (CLI default-dry-run
        guard per 6E contamination ruling — prevents omission-based prod writes).
        Programmatic callers (T4.9/T4.10/MCP) default to dry_run=False (unchanged).

    Returns the row dict (appended if dry_run=False, printed-only if dry_run=True).
    Raises ValueError on bogus hash or duplicate close.
    """
    effective_ledger = _resolve_ledger_path(ledger_path)
    is_copy = effective_ledger != _DEFAULT_LEDGER
    # [C2] Find the fire
    fire = _find_fire(fire_hash)
    if fire is None:
        raise ValueError(f"fire_hash {fire_hash!r} not found in move-fires.jsonl")

    # [C4] Check for duplicate close (read from the EFFECTIVE ledger, not always prod)
    ledger = [json.loads(l) for l in effective_ledger.read_text().splitlines() if l.strip()] \
        if effective_ledger.exists() else []
    if _is_closed(fire_hash, ledger):
        raise ValueError(f"fire_hash {fire_hash!r} already closed (duplicate close rejected)")

    # [C3] Move from the fire row, never typed
    move = fire.get("move", "")

    # [C1] Three states only
    if held_state == "held":
        held_val = True
        outcome_val = "held"
    elif held_state == "not-held":
        held_val = False
        outcome_val = "not-held"
    elif held_state == "unknown":
        held_val = None  # [W4] null — no hit, no miss
        outcome_val = "unknown"
    else:
        raise ValueError(f"invalid held_state {held_state!r} — must be held|not-held|unknown")

    # Build the row: existing keys + two additive keys [W2]
    evt = {
        "pattern": move,
        "held": held_val,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "situation": fire.get("situation", ""),
        "note": note,
        "deployment": DEPLOYMENT,
        # Additive keys [W2] — new rows only
        "fire_hash": fire_hash,
        "track": "advise-fire",
        "outcome": outcome_val,
    }

    # [W5] Orphan handling — if move not in library, mark using existing convention
    lib = _load_lib()
    lib_names = {p.get("name", "") for p in lib}
    if move and move not in lib_names:
        evt["orphaned"] = True
        evt["orphan_reason"] = f"move {move!r} not in patterns_library.jsonl"

    # [T4.8 amendment] Report whether _mark_stream_graded succeeded — never inherit silent no-op
    # Must be computed BEFORE the write so it lands in the ledger row
    stream_graded = _mark_stream_graded(fire_hash, bool(held_val)) if held_val is not None else False
    evt["stream_graded"] = stream_graded
    if not stream_graded:
        evt["stream_graded_note"] = "fire_hash not found in review-verdicts streams (or no graded field)"

    # [T4.11 V4] Grader tag — additive key, set only when caller identifies (Ver path passes grader="ver").
    # Legacy CLI callers leave it unset → key omitted → row schema unchanged for existing paths.
    if grader:
        evt["grader"] = grader

    # [T7.5h2 rev-5] dry_run: return the row without writing (CLI default-dry-run guard)
    if dry_run:
        return evt

    # [W1] Append exactly one line to the EFFECTIVE ledger (prod or copy)
    with effective_ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(evt, ensure_ascii=False) + "\n")

    # Restamp — for unknown, _tally excludes held:null so Beta is unchanged [W4]
    # [T7.5h2 rev-4] Skip restamp when writing to a copy — don't rewrite prod library
    if not is_copy:
        restamp()

    return evt


def closed_count() -> dict:
    """[V6] Derived reader: count closed fires by the join (fire_hash in both files).

    Returns dict with total, closed, and disagreement with graded flags.
    Reproducible — reads both files fresh each call.
    """
    fires = _load_fires()
    ledger = _load_ledger()
    fire_hashes = {r.get("fire_hash") for r in fires}
    # [T7.5h2] Filter kind != "amend" — amendment rows carry the same fire_hash
    # but must NOT be counted as a separate close (Decision B: one row per fire,
    # amendments are separate rows flagged and excluded from the derived count).
    closed_hashes = {e.get("fire_hash") for e in ledger
                     if e.get("fire_hash") and e.get("kind") != "amend"}
    # [T7.5h2 rev-5] Subtract tombstoned fire_hashes (6E contamination ruling):
    # tombstone rows explicitly remove a fire from the derived count. Two kinds,
    # two semantics: amend carries data (counted by _tally), tombstone removes
    # (excluded from closed_count). Without this, appending a tombstone only
    # adds to the set — it cannot fix an inflated closed_count.
    tombstoned = {e.get("fire_hash") for e in ledger
                  if e.get("kind") == "tombstone" and e.get("fire_hash")}
    closed = (fire_hashes & closed_hashes) - tombstoned
    # Graded flags from move-fires.jsonl
    graded_true = sum(1 for r in fires if r.get("graded") is True)
    graded_false = sum(1 for r in fires if r.get("graded") is not True)
    disagreement = len(closed) - graded_true
    return {
        "total_fires": len(fires),
        "closed": len(closed),
        "closed_hashes": sorted(closed),
        "graded_true": graded_true,
        "graded_false": graded_false,
        "disagreement": disagreement,
        "disagreement_note": f"closed={len(closed)} vs graded_true={graded_true} "
                             f"(graded flags all false — divergence is expected per [W3])",
    }



def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("move")
    r.add_argument("outcome", choices=["hit", "miss"])
    r.add_argument("note", nargs="?", default="")
    r.add_argument("--situation", default="")
    sub.add_parser("show")
    sub.add_parser("restamp")
    c = sub.add_parser("close")
    c.add_argument("fire_hash")
    c.add_argument("held_state", choices=["held", "not-held", "unknown"])
    c.add_argument("--note", default="")
    c.add_argument("--grader", default="",
                   help="grader identity (e.g. 'ver', 'claude') — additive key, identity only")
    c.add_argument("--ledger", default="",
                   help="path to ledger file (default: production outcomes.jsonl; env OUTCOMES_LEDGER also supported)")
    c.add_argument("--write", action="store_true",
                   help="actually append to the ledger (default: dry-run, prints row without writing)")
    cc = sub.add_parser("closed-count")
    args = ap.parse_args()

    lib = _load_lib()
    if not lib:
        print("no library — run consolidator.py + merge.py first"); return

    if args.cmd == "record":
        try:
            c = record(args.move, args.outcome == "hit", args.situation, args.note)
        except ValueError as e:            # clean CLI message (was SystemExit before the MCP-safety fix)
            raise SystemExit(str(e))
        print(f"recorded {args.outcome} for {_resolve(args.move, lib)}")
        print(f"  confidence now {c['mean']} ± {c['std']}  (hits {c['hits']}, misses {c['misses']})")

    elif args.cmd == "restamp":
        out = restamp()
        print(f"re-stamped {len(out)} patterns from {len(_load_ledger())} recorded outcomes")

    elif args.cmd == "close":
        try:
            row = close_fire(args.fire_hash, args.held_state, args.note,
                             grader=args.grader, ledger_path=args.ledger,
                             dry_run=not args.write)
            state = {"held": "held (true)", "not-held": "not-held (false)", "unknown": "unknown (null)"}
            if not args.write:
                print(f"DRY-RUN \u2014 row not written (use --write to append):")
            else:
                print(f"closed fire {args.fire_hash} as {state[args.held_state]}")
            print(f"  pattern: {row['pattern']}")
            print(f"  outcome: {row['outcome']}")
            print(f"  track: {row['track']}")
            if row.get("orphaned"):
                print(f"  orphaned: {row['orphan_reason']}")
            if row.get("grader"):
                print(f"  grader: {row['grader']}")
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            raise SystemExit(1)

    elif args.cmd == "closed-count":
        result = closed_count()
        print(f"closed {result['closed']} of {result['total_fires']} fires")
        print(f"graded_true={result['graded_true']} graded_false={result['graded_false']}")
        print(f"disagreement: {result['disagreement_note']}")

    else:  # show
        ledger = _load_ledger()
        rows = []
        for p in lib:
            h, m = _tally(p, ledger)
            c = beta(h, m)
            rows.append((c["mean"], c["std"], h, m, p["name"], p.get("occurrence_count", 1)))
        rows.sort(key=lambda r: (-(r[2] + r[3]), -r[0]))   # proven first, then by mean
        print(f"  {'trust (earned)':>22}   seen   move")
        for mean, std, h, m, name, oc in rows:
            cell = "UNPROVEN (0 outcomes)" if h + m == 0 else f"{mean:.2f} ± {std:.2f}  ({h}✓/{m}✗)"
            print(f"  {cell:>22}   {oc:>2}×   {name}")


if __name__ == "__main__":
    main()
