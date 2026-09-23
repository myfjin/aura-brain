# Vendoring the core — what is exempt, and why

`src/aura_brain/_core/` is the working brain, vendored. This file states the
invariant and the cost plainly, because a gate that is quietly narrowed is worse
than no gate.

## The invariant

Every file in `_core/` is **byte-identical to the canonical tree** except for the
data-path constants, which now read from `_core/paths.py`. That is the whole point:
the production system and the published copy stay **diffable**. If they drift, the
case studies stop describing the code that produced them.

## What is exempt, and why

`.github/workflows/ci.yml` and `pyproject.toml` **exclude `src/aura_brain/_core/`
by path** from `ruff check`, `ruff format --check`, and `mypy --strict`.

- The core is five thousand lines of a running system that grew without linters.
  It fails all three.
- **Reformatting it would break the invariant above** — the published copy would no
  longer be diffable against canonical, which is the drift this repository exists to
  avoid. Patching the copy would also fix the wrong target: the code is not the
  problem, its packaging is.

**What is NOT exempt:** `_core/paths.py` is the one core file we hand-wrote, so CI
lints and type-checks it explicitly by name. Everything outside `_core/` — tests,
fixtures, docs, CI — is fully gated.

## The cost, stated

A stranger reading `_core/` is reading production code, not reference code: long
functions, no type hints, module-level state. Typing it is a tracked follow-up.
Until then, treat `_core/` as **vendored source**: read it, do not lint it.

## Propagating a change

1. Change the canonical tree.
2. Re-vendor the touched files into `_core/`.
3. Re-apply the path edits (they are listed in `_core/paths.py`).
4. `git diff` proves the change is exactly what landed upstream.
