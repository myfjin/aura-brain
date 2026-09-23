#!/usr/bin/env python3
"""generator.py — minimal generative dialogue engine (the Generator, v1).

Two (or more) character-models talk: each turn a character generates its next line,
conditioned on its style-signature + real example-turns + the dialogue so far. A
sim-clock advances (event-compression). A hard PER-RUN BUDGET CAP stops the run
before it can overspend — safe testing of generative dialogue is the whole point.

v1 scope (honest): characters = lightweight conditioning profiles (style + few-shot
from the real corpus), NOT yet the full grounded character-model — no recognition/A6
gating of generated turns yet (that's next). Cheap model (Haiku) for testing.

Run: python3 generator.py [--turns 8] [--budget 0.15] [--model claude-haiku-4-5]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths  # published settings module (see VENDORING.md)

import identity   # noqa: E402  (block segmentation + labeling → harvest real example turns)
import gate       # noqa: E402  (live faithfulness filter: voice-reference + scoring)

ENV = paths.ENV_FILE
# The persona corpus (all THREE voices, jsonl) once built; else the legacy Claude+Illia.txt.
_PERSONA_CORPUS = paths.BRAIN_HOME / "persona_corpus.jsonl"
CORPUS = _PERSONA_CORPUS if _PERSONA_CORPUS.exists() else paths.BRAIN_HOME / "persona.txt"

# ── BUDGET GUARD — the per-run cap (this is the part Illia asked to code) ──
_PRICES = {  # USD per 1M tokens (approx)
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-4-6": (3.0, 15.0),
}


class BudgetGuard:
    def __init__(self, max_usd: float, model: str):
        self.max_usd = max_usd
        self.in_p, self.out_p = _PRICES.get(model, (1.0, 5.0))
        self.spent = 0.0
        self.calls = self.tok_in = self.tok_out = 0

    def charge(self, ti: int, to: int) -> float:
        c = ti * self.in_p / 1e6 + to * self.out_p / 1e6
        self.spent += c; self.calls += 1; self.tok_in += ti; self.tok_out += to
        return c

    def exceeded(self) -> bool:
        return self.spent >= self.max_usd

    def report(self) -> str:
        return (f"budget: ${self.spent:.4f} / ${self.max_usd:.2f}  "
                f"({self.calls} calls · {self.tok_in} in / {self.tok_out} out)")


def _key() -> str:
    for line in ENV.read_text().splitlines():
        if line.strip().startswith("ANTHROPIC_API_KEY"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("no ANTHROPIC_API_KEY in .env")


# ── character-model (v1: style-signature + few-shot from the real corpus) ──
class Character:
    def __init__(self, name: str, sig: dict, examples: list, role: str = None, terse: bool = False):
        # role = the SEAT/function (separate from voice); terse = a router/minimal speaker.
        # (Illia's correction 2026-06-28: voice-fidelity ≠ role-fidelity — model the seat too.)
        self.name = name
        self.pool = examples            # full real-turn pool (for retry few-shot)
        if terse:
            # a router speaks in their SHORT turns — model on the briefest real ones
            shortish = sorted((e for e in examples if 8 <= len(e.strip()) <= 160),
                              key=lambda e: len(e.strip()))
            self.examples = shortish[:8] or examples[:6]
        else:
            self.examples = examples[:6]
        ex = "\n".join(f"  · {e[:200].strip()}" for e in self.examples)
        style = []
        if sig["lowercase_start"] > 0.4: style.append("often starts lowercase")
        if sig["q_per_1k"] > 0.8: style.append("asks a lot of questions")
        if sig["ellipsis_per_blk"] > 0.1: style.append("uses '...' and emoji")
        if sig["markdown_rate"] > 0.04: style.append("uses **bold** / structure")
        if not style: style.append("plain, direct")
        length = "very short — a few words to one line" if terse else f"~{sig['avg_len']} chars/turn"
        role_line = f"ROLE: {role}\n" if role else ""
        terse_line = ("Speak MINIMALLY — 1–2 short lines, often just a few words. Do NOT write "
                      "paragraphs; do NOT elaborate or reason densely.\n" if terse else "")
        self.system = (
            f"You are {name}, in a real ongoing dialogue with the other speaker(s). "
            f"Stay strictly in {name}'s voice — NOT a generic assistant.\n"
            f"{role_line}"
            f"STYLE: {length}; {', '.join(style)}.\n"
            f"{terse_line}"
            f"HOW {name} ACTUALLY TALKS (real lines):\n{ex}\n\n"
            f"Write ONE next turn as {name}. One turn only — no narration, no name label."
        )
        self.reference = gate.build_reference(examples)          # (R, vbaseline) — voice axis
        self.move_ref = gate.build_move_reference(name, examples)  # (M, fams, mbaseline) — substance axis

    def retry_system(self, floated: bool = False) -> str:
        extra = "\n".join(f"  · {e[:160].strip()}" for e in self.pool[6:14] or self.examples)
        msg = self.system + (
            f"\n\nYOUR LAST ATTEMPT DRIFTED from {self.name}'s real voice — too generic, "
            f"too polished-AI. Match these real {self.name} lines MUCH closer in rhythm, "
            f"word-choice and length:\n{extra}\nBe more {self.name}, less assistant.")
        if floated:
            msg += (
                f"\n\nAND it FLOATED — eloquent but empty, a philosophy-essay that cashes out to "
                f"nothing (the exact failure this system was built to reject). {self.name} GROUNDS: "
                f"cite a REAL thing (a file, a number, a named mechanism), make a decision or a "
                f"concrete next action. Say something that could be verified or acted on — not "
                f"abstract riffing.")
        return msg


# roles = the SEAT/function (voice-fidelity ≠ role-fidelity — model the seat too, per
# Illia's 2026-06-28 correction). The triangle's three seats:
_ROLES = {
    "illia":   "router / decider — the artist-architect who sets direction and pushes for depth",
    "claude":  "architect / honest-floor — builds, and holds the truth-floor",
    "steward": "executor / verify / commit — the understanding + action layer",
}


def _load_jsonl_groups(corpus: Path) -> dict:
    """The persona corpus is ALREADY speaker-segmented + labelled, so group straight from it
    (no identity.blocks/label needed). Light noise filter only; seeded shuffle so the few-shot
    and the 400-turn voice reference are a representative sample, not just the earliest turns."""
    import random
    groups: dict = {}
    for line in corpus.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        sp = (e.get("speaker") or "").strip().lower()
        c = (e.get("content") or "").strip()
        if not sp or len(c) < 2 or c.startswith("/") or c.lower().startswith("unknown command"):
            continue
        groups.setdefault(sp, []).append(c)
    rng = random.Random(7)
    for v in groups.values():
        rng.shuffle(v)
    return groups


def build_characters(corpus: Path) -> dict:
    # persona_corpus.jsonl is already segmented + speaker-labelled → build all THREE voices
    # straight from it. (Legacy .txt path uses identity.blocks/label, Claude+Illia only.)
    if corpus.suffix == ".jsonl":
        g = _load_jsonl_groups(corpus)
        out = {}
        for sp in ("illia", "claude", "steward"):
            ex = g.get(sp) or []
            if len(ex) < 6:
                continue
            out[sp] = Character(sp.capitalize(), identity.signature(ex), ex, role=_ROLES.get(sp))
        return out
    text = corpus.read_text(encoding="utf-8", errors="ignore")
    g = {"ILLIA": [], "CLAUDE": []}
    for b in identity.blocks(text):
        lab = identity.label(b)
        if lab in g:
            g[lab].append(b)
    return {who: Character(who.capitalize(), identity.signature(g[who]), g[who])
            for who in ("ILLIA", "CLAUDE")}


def _ask(client, system, convo, name, budget, model):
    msg = client.messages.create(
        model=model, max_tokens=350, system=system,
        messages=[{"role": "user",
                   "content": f"The dialogue so far:\n{convo}\n\nNow respond as {name} — one turn."}])
    budget.charge(int(getattr(msg.usage, "input_tokens", 0)), int(getattr(msg.usage, "output_tokens", 0)))
    return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text").strip()


def gen_turn(client, spk, convo, budget, model, max_retries: int = 3, margin: float = 0.05,
             move_hint: str = ""):
    """Generate ONE faithful turn, gated on TWO axes: VOICE (sounds like them — cosine to
    their real turns) AND CONCRETENESS (does it cash out, or float?). The voice-gate ALONE
    passes eloquent-empty essays — proven 2026-06-28: the personas floated and the gate was
    blind, because philosophical drift embeds near the real turns. concreteness.score catches
    exactly that. Retry on voice-drift OR floating (pushing back on whichever failed); keep the
    turn that passes BOTH, else the best available. Returns
    (text, vscore, baseline, tries, verdict, concreteness). Shared by the batch generator AND
    the live node's generative self-redirect — one gated path, faithfulness enforced once."""
    import concreteness
    R, vbase = spk.reference
    vbar = vbase - margin
    M, _fams, mbase = getattr(spk, "move_ref", (None, None, 0.0))
    mbar = mbase - margin
    best = None            # (rank, combo, text, cverd, vscore, mscore)
    floated_last = False
    total = 0              # honest total attempts made
    for attempt in range(max_retries + 1):
        if budget.exceeded():
            break
        system = (spk.system if attempt == 0 else spk.retry_system(floated=floated_last)) + move_hint
        text = _ask(client, system, convo, spk.name, budget, model)
        total = attempt + 1
        vscore = gate.voice_score(text, R)[0] if R is not None else 1.0
        mscore = gate.move_score(text, M)[0] if M is not None else 0.0
        cverd = concreteness.score(text)["verdict"]
        voice_ok = (R is None or vscore >= vbar)
        move_ok = (M is not None and mscore >= mbar)
        identity_ok = voice_ok or move_ok          # sounds-like-them OR reasons-like-them (novelty-safe)
        floated_last = (cverd == "FLOATING")
        cash_ok = not floated_last
        rank = 2 if (identity_ok and cash_ok) else (1 if (identity_ok or cash_ok) else 0)
        combo = max(vscore, mscore)                # continuous tiebreak on the stronger identity axis
        if best is None or (rank, combo) > (best[0], best[1]):
            best = (rank, combo, text, cverd, vscore, mscore)
        if identity_ok and cash_ok:                # passed all → done
            break
    rank, combo, text, cverd, vscore, mscore = best
    verdict = "ok" if rank == 2 else ("FLOAT(kept best)" if cverd == "FLOATING" else "DRIFT(kept best)")
    return text, vscore, vbase, total, verdict, cverd, mscore, mbase


def generate(chars: dict, seed: str, max_turns: int, budget: BudgetGuard,
             model: str, sim_min_per_turn: int = 60, max_retries: int = 3, margin: float = 0.05):
    import anthropic
    import recognition   # the Brain's move-prediction (recognition + graph successors)
    client = anthropic.Anthropic(api_key=_key(), timeout=60.0)
    order = list(chars.values())
    transcript = []
    sim = datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)   # sim-clock start
    for i in range(max_turns):
        if budget.exceeded():
            print("  [BUDGET CAP reached — run stopped]")
            break
        spk = order[i % len(order)]
        convo = "\n\n".join(f"{t['speaker']}: {t['text']}" for t in transcript[-8:]) or f"(opening) {seed}"
        # THE PREDICTION ENGINE: the Brain fires the move the SITUATION calls for (recognition +
        # graph successor); the persona then speaks THAT move in their own voice — reasoning-driven,
        # not just style-imitation. Novel situation → no hint → falls back to voice/move gating.
        situation = transcript[-1]["text"] if transcript else seed
        pred = recognition.recall(situation)
        move_hint, pred_name = "", "—"
        if pred and pred.get("fired"):
            m = pred["fired"][0]
            pred_name = m["name"]
            succ = m.get("successors") or []
            nxt = f" (which tends to lead to '{succ[0]['name']}')" if succ else ""
            move_hint = (f"\n\n[BRAIN PREDICTION] this situation calls for the move "
                         f"'{m['name']}'{nxt}: {(m.get('present_action') or '')[:220]}\n"
                         f"Make THIS move as {spk.name}, in your OWN voice — not a generic version.")
        text, score, base, tries, verdict, cverd, mscore, mbase = gen_turn(
            client, spk, convo, budget, model, max_retries, margin, move_hint=move_hint)
        sim += timedelta(minutes=sim_min_per_turn)
        transcript.append({"turn": i + 1, "speaker": spk.name,
                           "sim_time": sim.isoformat(timespec="minutes"), "text": text,
                           "fidelity": round(score, 3), "baseline": round(base, 2),
                           "concreteness": cverd, "predicted_move": pred_name,
                           "move": round(mscore, 3), "move_baseline": round(mbase, 2),
                           "retries": tries, "verdict": verdict})
        print(f"\n[{sim.strftime('%b-%d %H:%M')}] {spk.name}  "
              f"(voice {score:.2f}/{base:.2f} · move {mscore:.2f}/{mbase:.2f} · {cverd} · "
              f"pred:{pred_name[:26]} · {tries}t · {verdict}):\n  {text}")
    return transcript


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--turns", type=int, default=8)
    ap.add_argument("--budget", type=float, default=0.15)
    ap.add_argument("--model", default="claude-haiku-4-5")
    ap.add_argument("--seed", default="lets think brother — what should we actually build next for AURA?")
    args = ap.parse_args()

    chars = build_characters(CORPUS)
    budget = BudgetGuard(args.budget, args.model)
    print(f"GENERATOR v1 — {' ↔ '.join(c.name for c in chars.values())} · "
          f"model={args.model} · cap=${args.budget}\n")
    transcript = generate(chars, args.seed, args.turns, budget, args.model)
    out = HERE / "generated_dialogue.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for t in transcript:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"\n{budget.report()}")
    print(f"transcript → {out.name}")


if __name__ == "__main__":
    main()
