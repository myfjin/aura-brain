# Case study: the calibration gate that wasn't deterministic

**Filed:** 2026-09-19 · **Where the rule landed:** CONTRIBUTING.md, "Measurement" and "Failure modes"

---

## What we thought was true

We had a calibration gate in Brain that classified fires by a numeric threshold and, on a green run, emitted a stable ordering of the surviving patterns. The gate had passed its own tests dozens of times. We treated its output as ground truth for anything downstream that needed to reproduce a decision — including the audit trail that let us re-derive a close months later against the same input.

## What we found

The gate's output was not stable across processes. The same input, run in two different Python processes on the same machine, produced two different orderings of the surviving patterns. On the same process, run twice, the ordering held. On a fresh process, it drifted. The audit trail could be built cleanly on one run and re-built to a different value on the next — and both were internally consistent.

## The reproduction

6E narrowed it down: the difference was **`PYTHONHASHSEED`**. Python randomizes string hashes at process start by default, and the gate's implementation hand-rolled a step that materialized a set of strings back into a list:

```python
surviving = list({p.name for p in candidates if p.score >= threshold})
```

`{...}` is a set literal. Set iteration order in CPython, for a set of strings under default `PYTHONHASHSEED=random`, depends on the per-process hash. `list(<set>)` walks that iteration order and freezes it. Two processes, two hashes, two orderings. Every downstream comparator that assumed the surviving list was in a canonical order was silently reading whatever order the current process happened to give it.

## Why the tests missed it

The test suite ran the whole flow in a single process. `PYTHONHASHSEED` was set once, and the fixture was captured against whatever ordering that first process produced. A second run of the same test, in the same process, agreed with itself — and the test agreed with the fixture. **A green that has never been red is a green you have not tested.** We had built the check-fail-once mechanism for other paths, but not for this one.

## The fix

One line:

```python
surviving = sorted({p.name for p in candidates if p.score >= threshold})
```

`sorted()` on a set returns a list in a deterministic order — lexicographic, independent of process hash. The fixture was regenerated once, the test set `PYTHONHASHSEED` explicitly, and a companion property test now varies the seed across a range to catch this exact class of bug next time.

## The rules that came out

- **`PYTHONHASHSEED=0` in the test env is required for calibration paths.** Set in `pyproject.toml` under `[tool.pytest.ini_options].env`. Anything that materializes a set of hashable values into a list uses `sorted()`, or is written with the seed variability explicit in a property test.
- **Iteration order of any set or dict-of-set is not stable across processes.** If your code depends on that order, the code is wrong; there is no `PYTHONHASHSEED` you can pin in production that makes this okay.
- **Make the checker fail once before you trust it.** The fixture was captured *from* the buggy path, so the test agreed with the bug. A test that has never been red has verified nothing.

## Why this case study lives in the public repo

Two reasons. First, it is the concrete grounding for the `PYTHONHASHSEED=0` line in `pyproject.toml` — anyone reading that line and wondering "why is this here?" has the answer. Second, this is the exact shape of bug that hides in any codebase that treats set/dict iteration order as an implicit contract, and the code that broke us here is not remarkable — `list({...})` is a phrase you write without thinking. If it broke us, it will break someone else, and we would rather they find it in twenty minutes than in a week.

🖖
