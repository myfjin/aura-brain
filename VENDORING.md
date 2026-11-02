# The published core — how it gets here, what is exempt, and why

`src/aura_brain/_core/` is the working brain, published from the private repository we
run in production. This file states how a change reaches it, which gate is narrowed for
it, and what that costs, because a gate that is quietly narrowed is worse than no gate.

## Two regions

Every file in this repository is in exactly one of two regions:

- **Public-owned:** the licence and notice, authors, conduct, contributing, security, CI,
  `pyproject.toml`, the README and docs, the tests, `tools/make_fixtures.py`,
  `src/aura_brain/__init__.py`, and `src/aura_brain/_core/paths.py`, the hand-written
  settings module. These change by pull request here, like any project.
- **Published:** every other `src/aura_brain/_core/*.py`. One script in the private
  repository writes these (`tools/publish_public.py`), never a hand and never a pull
  request here. A change proposed to a published file is made in the private tree by
  hand and arrives with the next publish. That is the only way back.

## How a publish works

The publisher exports a named private commit and gates the export before anything reaches
this repository: a personal-data scan, a check that nobody is quoted, machines named by
role, this repository's own privacy grep (read from `ci.yml`), and the private test suite
run on the exported code. Only a GREEN export can be published. The publisher then writes
the published files into a clean checkout of this repository, rewriting the private
package imports (`from aura_brain.core import brain`) into the flat form the core uses here
(`import brain`), and it refuses if:

- a published path is also public-owned, or a file here is in neither region;
- the checkout is not clean;
- a published module reads a `paths.X` (or `paths.need("X")`) that `_core/paths.py` does
  not define;
- anything outside the published list changed (proved with `git status` and
  `git diff --stat`);
- a published module does not import from this tree.

What it leaves is one change, opened as a pull request and reviewed like any other.

Until November 2026 the core was copied in by hand, file by file, with a table of edits
(`tools/revendor.py`). It drifted: by then 10 of its 52 edits still applied, and `rails.py`
was a stub. The publisher replaced it.

## What is exempt, and why

`.github/workflows/ci.yml` and `pyproject.toml` **exclude `src/aura_brain/_core/` by path**
from `ruff check`, `ruff format --check`, and `mypy --strict`.

- The core is several thousand lines of a running system that grew without these
  linters. It fails all three.
- **Reformatting it here would be undone by the next publish.** A fix to the code belongs
  in the private tree, and ships from there.

**What is NOT exempt:** `_core/paths.py` is public-owned and hand-written, so CI lints and
type-checks it explicitly by name. Everything outside `_core/` (tests, fixtures, docs, CI)
is fully gated, and the publisher imports every published module before it accepts a
publish.

## The cost, stated

A stranger reading `_core/` is reading production code, not reference code: long
functions, few type hints, module-level state. Typing it is a tracked follow-up. Until
then, treat `_core/` as **published source**: read it, do not lint it. A few calls reach
parts of the production system that are not published (the auto-merge step at the end of
`distiller.py`, for one); here they do nothing.
