# Getting started with aura-brain

aura-brain is **install-from-git** while it is pre-release. There is no PyPI package,
and that is deliberate — see "Why not PyPI yet" below.

This guide gets you from nothing to a working checkout, and tells you honestly what
does and does not run today.

---

## What you need

- **Python 3.11 or newer** (`requires-python = ">=3.11"`)
- **git**
- no runtime dependencies — the package is pure Python for now

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

You should see the version declared in `pyproject.toml` — currently `0.1.0`.

## Run the tests

    pytest

CI runs the same suite on Python 3.11, 3.12 and 3.13, with `PYTHONHASHSEED=0`,
because calibration paths in Brain must be reproducible across processes. If you
wonder why that environment line is there,
[case study 01](https://github.com/myfjin/aura-brain/blob/main/docs/case-studies/01-nondeterministic-calibration.md) is the whole story.

## What works today — honestly

**The 0.1.0 package is a scaffold.** It exports its version and nothing else. The
advise/close/outcome loop and the honesty-floor call sites land in subsequent
releases — once the case studies in [`docs/case-studies/`](https://github.com/myfjin/aura-brain/tree/main/docs/case-studies) can be run
against the code.

So today this repository is: the license, the discipline, the docs, and the shape.
The code follows. If you are here for a working advice organ, you are early — and we
would rather say that plainly than have you find it in an empty function.

## Why not PyPI yet

A `0.1.0` on PyPI can be yanked but not deleted, and every reserved name is a promise
about maintenance. We are holding until:

1. the 2026-09-28 feel-fire lands with a real measurement,
2. `RESEARCH.md` question 3 (the private `why_pass.py` internals) is resolved, and
3. at least one case study shows the discipline in action.

Until then: install from git, as above.

## Where to read next

- [`README.md`](https://github.com/myfjin/aura-brain/blob/main/README.md) — what Brain is and why, and the two months of real events behind it
- [`RESEARCH.md`](https://github.com/myfjin/aura-brain/blob/main/RESEARCH.md) — the open questions we cannot answer alone; you are welcome to take one
- [`docs/case-studies/`](https://github.com/myfjin/aura-brain/tree/main/docs/case-studies) — the rules, each with the afternoon that paid for it
- [`CONTRIBUTING.md`](https://github.com/myfjin/aura-brain/blob/main/CONTRIBUTING.md) — what we ask before you send code

## Contributing

Pull requests with **DCO sign-off** (`git commit -s`). No CLA. If you have an idea
larger than one PR, open an issue first and talk it through.

🖖
