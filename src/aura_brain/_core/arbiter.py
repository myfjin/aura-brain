#!/usr/bin/env python3
"""The arbiter — one decision per turn: rails-floor + depth-field.

Assembles the two real pieces we built into a single call (no new claims, just
wiring), honoring the A-spec precedence:

  FLOOR (action-side rails, deterministic, non-overridable) — checked FIRST:
    R3  detect_failure_loop(recent_actions)   — repeating a failing action
    A6  detect_unverified_claim(draft)        — claiming done/verified w/o evidence
  FIELD (request-side depth) — only if no rail fired:
    depth.classify(request)  → one of the 6 request-side labels

If a rail fires, its directive wins and the turn is rail-bound. Otherwise the
request's depth label + directive is returned. The meta-logic is ordering +
precedence, not a big guess — that's what keeps it reliable.

Honest status: arbiter is a standalone callable. A6/R3 are isolation-tested;
LIVE wiring into Steward's loop (esp. the outgoing-draft hook A6 needs) is still
pending — see rails.py. depth.classify's caveats stand (small validation set,
coverage is the weak axis).

Run: python3 arbiter.py        # demo across scenarios
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths  # published settings module (see VENDORING.md)

sys.path.insert(0, str(paths.PCE_DIR))
import depth          # noqa: E402  (request-side classifier)
import rails          # noqa: E402  (action-side R3; A6 via whypass)
import whypass        # noqa: E402  (outbound floor: the why-pass = A4+A5+A6)
import numeric_floor  # noqa: E402  (A7 — frame-relative numeric floor, Step 3)


_DEPTH_DIRECTIVE = {
    "ANSWER_DIRECT":        "Answer directly, low depth — don't over-verify a simple ask.",
    "SPECIFY":              "Undetermined/novel — ask ONE clarifying question to narrow it before answering.",
    "VERIFY_UNDERSTANDING": "Restate your understanding plainly and confirm it is right BEFORE building/acting.",
    "EXPLAIN_TO_UNDERSTAND":"Teach to build their understanding at their level — don't just execute.",
    "RELATIONAL_REGISTER":  "Human moment, not a task. Meet it as one; do not execute.",
    "DEFER":                "The call is timing — acknowledge and park; don't act now.",
}


@dataclass
class Decision:
    mode: str                 # "RAIL" | "DEPTH" | "NONE"
    label: str                # A6 | R3 | ANSWER_DIRECT | ...
    directive: str
    floor: bool               # True = rail (non-overridable)
    signals: dict = field(default_factory=dict)


def arbitrate(request: str = None, draft: str = None, recent_actions: list = None) -> Decision:
    """Public entry: the decision, plus the ADVISORY A6-STATE read riding alongside.

    A6-STATE (2026-08-14) never changes the verdict — it is measured at 2/10
    mis-fires on ordinary TRUE background statements, because no lexical rule
    separates a true measured-state sentence from a false one. It rides in
    `signals["state_claims"]` so a surfacing hook can ask the one question that
    does discriminate: did you measure this turn, or is this recall?
    """
    d = _arbitrate(request=request, draft=draft, recent_actions=recent_actions)
    if draft:
        try:
            sc = rails.detect_state_assertions(draft)
            if sc:
                d.signals = dict(d.signals or {})
                d.signals["state_claims"] = sc
        except Exception:  # advisory read must never break the floor
            pass
    return d


def _arbitrate(request: str = None, draft: str = None, recent_actions: list = None) -> Decision:
    # ── FLOOR: action-side rails first (non-overridable) ──────────────────
    if recent_actions:
        fired, directive = rails.detect_failure_loop(recent_actions)
        if fired:
            return Decision("RAIL", "R3", directive, True, {"rail": "R3"})
    if draft:
        fps = whypass.why_pass(draft)
        if fps:
            labels = "+".join(f["footprint"] for f in fps)
            directive = "  |  ".join(f["directive"] for f in fps)
            signals = {"footprints": [f["footprint"] for f in fps]}
            if any(f["footprint"] == "A6" for f in fps):
                # A6 Tier-2 (C2, 2026-07-05): the claim-words fired — now OPEN what the
                # words NAME. Read-only, fail-open: the floor never crashes or executes
                # anything on its own escalation.
                try:
                    import artifact_check
                    evs = artifact_check.scan(draft)
                    if evs:
                        signals["artifacts"] = evs
                        directive += "  |  TIER-2 ARTIFACT CHECK — " + artifact_check.summary(evs)
                except Exception:
                    pass
            return Decision("RAIL", labels, directive, True, signals)
        # A6 Tier-2 as its OWN floor (C2, 2026-07-05): evidence WORDS suppress the
        # Tier-1 words-check, but cannot talk away an opened-and-MISSING artifact —
        # the catalog class (ghost filenames behind "verified"). Read-only, fail-open.
        try:
            import artifact_check
            if artifact_check.claims_completion(draft):
                evs = artifact_check.scan(draft)
                missing = [e for e in evs if e["verdict"] == "MISSING"]
                if missing:
                    directive = ("RAIL A6-T2 — ARTIFACT CHECK FAILED: the draft claims completion "
                                 "but the named artifact(s) do not exist: "
                                 + ", ".join(e["ref"] for e in missing[:5])
                                 + ". Open what you name before you claim it; fix the claim or the path.")
                    return Decision("RAIL", "A6-T2", directive, True,
                                    {"footprints": ["A6-T2"], "artifacts": evs})
        except Exception:
            pass
        # A7 — the frame-relative NUMERIC FLOOR: a computed assertion in the draft that does
        # not hold under its frame. It does NOT say "false" — it demands the frame be named
        # (operator/base/rounding) or the number fixed. Non-bypassable here → this is where
        # mathbrain graduates from tool to ORGAN (the bypass-test).
        nfs = [v for v in numeric_floor.scan_draft(draft) if v.verdict == numeric_floor.DOESNT_HOLD]
        if nfs:
            directive = "  |  ".join(f"NUMERIC FLOOR A7 — {v.claim}: {v.message}" for v in nfs)
            return Decision("RAIL", "A7", directive, True, {"numeric": [v.claim for v in nfs]})
    # ── FIELD: request-side depth (only if no rail bound the turn) ─────────
    if request:
        r = depth.classify(request)
        return Decision("DEPTH", r["label"], _DEPTH_DIRECTIVE.get(r["label"], ""), False, r)
    return Decision("NONE", "", "", False, {})


_SCENARIOS = [
    {"name": "simple concrete request", "request": "set session reset value to 03:00"},
    {"name": "keystone (verify)", "request": "explain me your understanding of aura so we align"},
    {"name": "emotional (relational)", "request": "i have never felt myself so happy this is a real success"},
    {"name": "teach request", "request": "explain me what persistent memory means i want to understand"},
    {"name": "unverified claim in DRAFT (A6 floor)",
     "draft": "The extractor is running and it found the patterns. Saved to pce_patterns.json."},
    {"name": "verified-sounding claim, ghost file (A6-T2 floor — the catalog class)",
     "draft": "All 68 entries verified by running the catalog — results in catalog_index_final.jsonl."},
    {"name": "repeating failure (R3 floor)",
     "recent_actions": [{"action": "cmake build", "ok": False},
                        {"action": "cmake build", "ok": False},
                        {"action": "cmake build", "ok": False}]},
    {"name": "FLOOR beats FIELD (request + bad draft)",
     "request": "explain your understanding so we align",
     "draft": "Done, it works."},
]


def main():
    for s in _SCENARIOS:
        name = s.pop("name")
        d = arbitrate(**s)
        tag = f"{d.mode}/{d.label}" + ("  [FLOOR]" if d.floor else "")
        print(f"\n■ {name}")
        print(f"   → {tag}")
        if d.mode == "DEPTH":
            sg = d.signals
            print(f"     demand={sg['demand']} coverage={sg['coverage']} gap={sg['gap']} deficit={sg['deficit']}")
        print(f"     directive: {d.directive}")


if __name__ == "__main__":
    main()
