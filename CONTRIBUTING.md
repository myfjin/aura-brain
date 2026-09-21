# Contributing to aura-brain

The crew is small — one human and five machines — and this project is what it is because of that. We would rather grow it slowly with people who care about substance than fast with people who don't.

If you found this and it interests you, you are welcome. This file is what we ask before you send code, and what we ask about ourselves before we merge it.

---

## How we take contributions

We take **pull requests** on GitHub. We do not use a CLA. Sign-off on every commit is the entire contributor agreement:

    git commit -s -m "your message"

The `-s` adds a `Signed-off-by:` line and asserts the **Developer Certificate of Origin (DCO)** — that you wrote the change or have the right to submit it under Apache-2.0. That is all we require.

If you have an idea larger than one PR, **open an issue first** and talk it through with us. Small fixes and typos can skip that step; anything that changes how Brain thinks about a fire, a close, or an outcome should be discussed before you write it.

**When you open an issue, please describe what you saw and how to recreate it.** A clear reproduction is the difference between something we can act on and something that has to sit until someone can guess. If you cannot reproduce it yet — say so, and share what you have.

---

## The rules that were paid for

Each rule below was learned from a specific afternoon where we got it wrong first. We do not ask you to follow them because they are elegant. We ask because we already broke each one and would rather not do it again.

### Measurement

- **Nothing at n=1 is a measurement.** Report the **median of ≥3 runs plus the call count**, or **fail-once as a rate over N≥10**.
- **A number you cannot trace to exactly one run is not a measurement.** Attribute every figure.
- **Read the newest state, never the oldest record.** Freshness before neatness.
- **Make a checker fail once before you trust it.** A green that has never been red is a green you have not tested.

### Honesty

- **Say "unknown" when you do not know.** Absence of a visible cause is not evidence — "unknown" beats invented history every time.
- **Retract in public.** If a number you published turns out to be wrong, correct it in the same visible place. Silent edits are worse than the original error.
- **No self-scored superiority.** The person who wrote the code does not grade it. Independence between author, caller and grader is the whole point of the design.

### Files, hashes, ledgers

- **Sidecar `.md5` is the sole hash carrier.** Path-form: `md5sum file > file.md5`. The document body **never** carries its own hash — a check that verifies itself verifies nothing.
- **Tombstone, do not delete.** The ledger is append-only. Closes minus tombstones is what "closed" means.
- **Rename, do not delete, for rotation.** Archived streams keep their history and stay reachable by name.

### Fixes, reverts, proofs

- **Prove-by-revert only inside `mktemp -d`, never on a served path.** Reverting on the live file regresses the system for whoever is using it right now. Learned the hard way.
- **Fixtures before install.** A fixture that arrives after the code it fixtures is a fixture that never ran against the code.
- **Quiesce before you verify.** A verification that races with a live writer is a verification of the race, not the fix.

### Failure modes

- **Fail open with a loud `WARN`.** Silent fail-closed is invisible; silent fail-open is a lie. Loud fail-open is the honest shape.
- **`record_outcome`'s docstring is the whole contract: "Trust earned, not asserted."** Every fire is a pending hypothesis until evidence arrives; nothing gets promoted on assertion.

---

## Testing

Run whatever test suite ships in this repo before opening a PR. If your change touches:

- the ledger — include a test that exercises tombstone-not-delete and derived closed_count
- the calibration path — include a test that runs across multiple `PYTHONHASHSEED` values (or uses `sorted()` and says so)
- the honesty-floor call sites — include a test that fails when a claim outruns its evidence

If the code you touched has no test, adding one is welcomed as part of the same PR.

---

## What we will not take

- **Backwards-compatibility shims** for hypothetical futures. If you can change the code, change the code.
- **Error handling for scenarios that cannot happen.** Trust internal contracts and framework guarantees; validate at boundaries only.
- **Comments that describe what the code does.** Well-named identifiers do that. Comments are for the *why* that is not obvious from the *what*.
- **Documentation that references issue numbers, callers, or the current sprint.** That belongs in the PR description. Code outlives PRs.
- **New abstractions ahead of use.** Three similar lines are better than a premature abstraction; wait for the fourth.

None of the above is aesthetic preference — each is a rule we broke first and paid for.

---

## Register

We work as brothers and friends, not as vendors and customers. Feedback is direct; corrections are welcome from any seat. If a machine reviewer catches something a human missed, that is the design working, not a failure of hierarchy.

If your first PR is small — a typo, a missing comma, a docstring fix — that is a good first PR. Some of ours are the same.

---

## Contact

For anything that does not fit an issue: **ihladkyi2@gmail.com**.

🖖
