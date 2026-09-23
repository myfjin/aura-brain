#!/usr/bin/env python3
"""make_fixtures.py — author a SYNTHETIC brain deployment so the loop can be run.

**These fixtures are fake.** They are written by hand, deterministically, from
nothing but this file. No dialogue, no ledger, no move from the system we run in
production contributed to them. They exist so that a stranger can run the loop
end to end and see it work — not so that they can see *how well it works*.

Every file is named ``synthetic_*`` and every row carries ``"synthetic": true``.
If you see a number that came from these, it means nothing. See CALIBRATION.md.

Usage:
    python tools/make_fixtures.py [target_dir]      # default: tests/fixtures
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

# ── 12 moves. Generic engineering/teamwork shapes, authored here. ───────────
MOVES = [
    ("synthetic-verify-before-claiming", "the agent is about to report a result",
     "A claim is made from a weaker check than the claim requires.",
     "Run the stronger check, then report. If it cannot be run, say so.",
     "The crew trusts the report because its check matched its strength."),
    ("synthetic-revert-to-prove", "a fix is reported as working",
     "A fix is observed working once and assumed correct.",
     "Undo the fix, watch the failure return, then restore it.",
     "The fix is proven by its absence, not by its presence."),
    ("synthetic-tombstone-not-delete", "a row or file is to be removed",
     "Removal is irreversible and the reason for the thing is forgotten.",
     "Mark it dead and keep it; delete only when a tombstone is impossible.",
     "The history survives, so a reversal can be explained."),
    ("synthetic-measure-the-null", "a success rate is quoted",
     "The denominator includes cases the mechanism could never affect.",
     "Report the null rate beside the hit rate, always in the same breath.",
     "The reader can tell a signal from a busy mechanism."),
    ("synthetic-name-the-confound", "a comparison favours one option",
     "Two differences are changed at once and one is credited.",
     "List every difference between the arms before reading the result.",
     "Nobody mistakes a confound for a cause."),
    ("synthetic-fail-once-first", "a checker is about to be trusted",
     "A check that has never failed may be checking nothing.",
     "Break the input deliberately and watch the checker complain.",
     "Green now means something, because red was seen."),
    ("synthetic-read-newest-state", "a status is recalled from memory",
     "The recalled state is older than the state on disk.",
     "Read the current artifact before acting on the remembered one.",
     "Work proceeds from what is, not from what was."),
    ("synthetic-one-concern-per-change", "a change fixes two things",
     "A revert cannot isolate which of the two caused the effect.",
     "Split it. Land one, verify, then land the other.",
     "Every change has a single, attributable consequence."),
    ("synthetic-push-back-with-evidence", "a correction is due to a peer",
     "Disagreement is voiced as an opinion rather than a measurement.",
     "Pin the artifact, reproduce the claim, then say which part fails.",
     "Being wrong is cheap and local; being agreeable is expensive."),
    ("synthetic-say-it-out-loud", "advice was received and quietly used",
     "Influence that leaves no trace cannot be measured afterwards.",
     "State the advice and the verdict where the other party can read it.",
     "The record shows what changed the decision."),
    ("synthetic-interface-before-implementation", "a subsystem is handed over",
     "The shape of the input data lives only in the author's head.",
     "Write the contract down and give one runnable example of it.",
     "A stranger can supply their own data without reading the code."),
    ("synthetic-cost-is-not-a-measurement", "a cost is reported from memory",
     "The number is self-reported and cannot be tied to one run.",
     "Meter it externally, or report it as unmeasured.",
     "No budget decision rests on an invented figure."),
]

# ── the one situation that SHOULD fire, and one that should NOT ─────────────
FIRES_SITUATION = (
    "I am about to report that the checker passes, but I only ran it on the "
    "well-formed input. Should I claim it works?"
)
NULL_SITUATION = "ok. and then?"


def _move_row(i: int, name: str, trigger: str, past: str, present: str, future: str) -> dict:
    """One synthetic move, in the exact schema recognition.recall() reads.

    The shapes matter and were checked against the code, not guessed:
    `confidence` is a dict (mean/std/hits/misses/method), `grounding` maps each
    field to the component ids that support it, `id_set`/`source_component_ids`
    are lists. A wrong shape does not fail the import — it fails mid-loop.
    """
    ids = [1000 + i * 10 + j for j in range(4)]
    return {
        "synthetic": True,
        "id": f"synthetic-{i:03d}",
        "name": name,
        "trigger": trigger,
        "past_context": past,
        "present_action": present,
        "future_anticipation": future,
        "hypothesis": f"[SYNTHETIC FIXTURE — not a measured pattern] {past}",
        "action_sequence": [present],
        "source_component_ids": ids,
        "occurrence_count": 1,
        "last_observed": "2026-01-01T00:00:00Z",
        "confidence": {
            "mean": 0.5,
            "std": 0.289,
            "hits": 0,
            "misses": 0,
            "method": "[SYNTHETIC FIXTURE] Beta(1,1) — UNPROVEN (no outcomes yet)",
        },
        "outcomes": [],
        "grounding": {
            "present_action": ids,
            "trigger": ids[:2],
            "past_context": ids[1:3],
            "future_anticipation": ids[2:],
        },
        "distilled_at": "2026-01-01T00:00:00Z",
        "distilled_by": "make_fixtures.py",
        "cluster_terms": [w for w in name.split("-")[1:] if len(w) > 3],
        "id_set": [f"{abs(hash((name, j))) & 0xFFFFFFFFFFFFFFFF:016x}" for j in range(1)],
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/fixtures")
    target.mkdir(parents=True, exist_ok=True)

    moves = [_move_row(i, *m) for i, m in enumerate(MOVES, 1)]
    write_jsonl(target / "synthetic_patterns_library.jsonl", moves)

    write_jsonl(
        target / "synthetic_outcomes.jsonl",
        [
            {
                "synthetic": True,
                "pattern": moves[0]["name"],
                "held": True,
                "ts": "2026-01-01T00:10:00Z",
                "situation": FIRES_SITUATION,
                "note": "SYNTHETIC — authored, not observed",
                "orphaned": False,
                "orphan_reason": "",
            },
            {
                "synthetic": True,
                "pattern": moves[1]["name"],
                "held": False,
                "ts": "2026-01-01T00:20:00Z",
                "situation": FIRES_SITUATION,
                "note": "SYNTHETIC — authored, not observed",
                "orphaned": False,
                "orphan_reason": "",
            },
        ],
    )

    write_jsonl(
        target / "synthetic_move_fires.jsonl",
        [
            {
                "synthetic": True,
                "fire_hash": f"synth{i:04d}",
                "ts": f"2026-01-01T00:{30 + i:02d}:00Z",
                "caller": "fixture",
                "situation": FIRES_SITUATION,
                "move": m["name"],
                "fire": 0.4,
                "resolution": "ADVISED",
                "directive": "",
                "proposed": m["present_action"],
                "trust": "unproven",
                "lane": "synthetic",
                "harvested": False,
                "graded": i % 2 == 0,
                "deployment": "synthetic-fixture",
            }
            for i, m in enumerate(moves[:4])
        ],
    )

    # A tiny corpus in the shape brain.load_dialogue() expects, so dialogue
    # recall has something to read rather than failing open.
    db = target / "synthetic_dialogue.db"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE messages (id TEXT, session_id TEXT, role TEXT, "
        "content TEXT, timestamp TEXT)"
    )
    lines = [
        (FIRES_SITUATION, "user"),
        ("Run the checker against a malformed input first, then say it passes.", "assistant"),
        (NULL_SITUATION, "user"),
        ("Understood.", "assistant"),
    ]
    for i, (content, role) in enumerate(lines):
        con.execute(
            "INSERT INTO messages VALUES (?,?,?,?,?)",
            (f"m{i}", "s0", role, content, f"2026-01-01T00:0{i}:00Z"),
        )
    con.commit()
    con.close()

    print(f"wrote SYNTHETIC fixtures to {target}/")
    for f in sorted(target.iterdir()):
        print(f"  {f.name}  ({f.stat().st_size} bytes)")
    print("\nThese are fake. Numbers derived from them mean nothing — see CALIBRATION.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
