# Getting started with aura-brain

aura-brain is **install-from-git** while it is pre-release. There is no PyPI package,
and that is deliberate — see "Why not PyPI yet" below.

This guide gets you from nothing to a **running loop**, and tells you honestly what it
does and does not do for you once it runs.

---

## What you need

- **Python 3.11 or newer** (`requires-python = ">=3.11"`)
- **git**

Runtime dependencies are declared and installed for you: the **MCP server SDK**
(`mcp`, pinned below 2 — the vendored core is written against v1) and **numpy**.
Two heavier extras are opt-in:

- `[embeddings]` — `chromadb`, for the local MiniLM embedder the consult lanes use.
  No API key, no network. Without it those lanes report *"optional dependency
  absent"* and **fail open**; the loop still runs.
- `[math]` — `sympy`, for the math front-door's exact computation.
- `[distill]` — `anthropic`, for the distillation / floor path, which needs a key.

## Install from git

    git clone https://github.com/myfjin/aura-brain.git
    cd aura-brain
    python -m venv .venv
    . .venv/bin/activate        # Windows: .venv\Scripts\activate
    python -m pip install -e ".[dev]"

The `[dev]` extra brings the tools contributors use: pytest, pytest-cov, hypothesis,
ruff and mypy.

## Check it installed

    python -c "import aura_brain; print(aura_brain.__version__)"

You should see the version declared in `pyproject.toml` — currently `0.2.0`.

## Run the tests

    pytest

That runs against a **synthetic** deployment in `tests/fixtures/`, authored by
`tools/make_fixtures.py`. It proves the machinery turns over. It says nothing about
how well the brain advises — see below.

CI runs the same suite on Python 3.11, 3.12 and 3.13, with `PYTHONHASHSEED=0`,
because calibration paths in Brain must be reproducible across processes. If you
wonder why that environment line is there,
[case study 01](https://github.com/myfjin/aura-brain/blob/main/docs/case-studies/01-nondeterministic-calibration.md) is the whole story.

## Run the loop — three commands

    export AURA_BRAIN_HOME=$PWD/tests/fixtures     # point it at the synthetic data

    python - <<'PY'
    from aura_brain import advise, record_outcome
    r = advise("I checked the fix works once. Should I call it verified?", caller="me")
    print(r["resolution"], r["consult"])           # which lanes fired, and whether any errored
    record_outcome("some-move-name", held=True, situation="...")
    PY

**Read the returned set, not its rank-1.** `advise()` hands back the top moves *plus*
alternates, and a per-lane `consult` report. A lane saying `fired: false` is honest;
a lane saying `error` may be dead. And note the distinction the core now makes
explicitly: `skipped: optional dependency absent` is a documented condition, not a
failure.

## Point it at your own corpus

The brain is a **calibrated floor over a corpus**, and it ships without one. Every
path it reads is environment-driven and defaults to an empty `~/.aura-brain`, so
until you supply data each lane fails **open with a loud warning** rather than
guessing. `src/aura_brain/_core/paths.py` is the single place all of it is declared,
and the
[Connecting your own data](https://github.com/myfjin/aura-brain/wiki/Connecting-your-own-data)
wiki page gives the shape each file must have — the moves library, the append-only
outcomes ledger, the fire log, the consult-lane registries, and the dialogue corpus
(`$STATE_DB`).

## What works today — honestly

**0.2.0 is the loop.** `advise()` → you decide → `record_outcome()` → the derived
rate moves. What that means in practice:

- the honesty floor, the consult lanes and the ledger are real code, vendored from
  the system we run in production and left byte-identical except for its data paths;
- the **corpus is not here**, because it is about seven months of one crew's conversations;
- therefore **numbers produced from `tests/fixtures/` mean nothing.** They prove the
  loop runs, not that it measures.

`CALIBRATION.md` states which thresholds were actually measured (one) and which are
still working guesses (the rest), including one inherited with the note *"retune
after N=50 labeled-outcome suggestions"* — which has not happened. `VENDORING.md`
states exactly which gate is narrowed for the vendored core, and why.

## Why not PyPI yet

A version on PyPI can be yanked but not deleted, and every reserved name is a promise
about maintenance. We are holding until:

1. the 2026-09-28 feel-fire lands with a real measurement,
2. `RESEARCH.md` question 3 (the private `why_pass.py` internals) is resolved, and
3. at least one case study shows the discipline in action.

Until then: install from git, as above.

## Where to read next

- [`README.md`](https://github.com/myfjin/aura-brain/blob/main/README.md) — what Brain is and why, and the two months of real events behind it
- [`CALIBRATION.md`](https://github.com/myfjin/aura-brain/blob/main/CALIBRATION.md) — what the numbers mean, and how much to trust them
- [`VENDORING.md`](https://github.com/myfjin/aura-brain/blob/main/VENDORING.md) — the invariant behind `_core/`, and the cost of it
- [`RESEARCH.md`](https://github.com/myfjin/aura-brain/blob/main/RESEARCH.md) — the open questions we cannot answer alone; you are welcome to take one
- [`docs/case-studies/`](https://github.com/myfjin/aura-brain/tree/main/docs/case-studies) — the rules, each with the afternoon that paid for it
- [`CONTRIBUTING.md`](https://github.com/myfjin/aura-brain/blob/main/CONTRIBUTING.md) — what we ask before you send code

## Contributing

Pull requests with **DCO sign-off** (`git commit -s`). No CLA. If you have an idea
larger than one PR, open an issue first and talk it through.

🖖
