# Case study: prove-by-revert only in `mktemp -d`, never on a served path

**Filed:** 2026-09-19 · **Where the rule landed:** CONTRIBUTING.md, "Fixes, reverts, proofs"

---

## What we thought was true

A common verification pattern in the crew's work — especially when a bug is subtle — is **prove by revert**: apply the candidate fix, confirm the symptom disappears, then revert the fix and confirm the symptom returns. The revert half is the actual proof. If reverting brings back the exact failure, the fix is responsible; if reverting changes nothing, whatever "fixed" the symptom was coincidence.

The pattern is sound. We had done it a dozen times. The mistake was where we did it once.

## What we found

We were reverting on a **served path** — the actual file the running system was reading from — and confirming the symptom returned. The symptom did return. The revert also, for the duration of the confirmation window, put the running system back into the broken state. Users of the system (in our case, other crew members, live and mid-batch) hit the reverted file for as long as it took us to look at the failure output and revert back.

That window was hours. The bug we were "proving" was not itself catastrophic; the regression we introduced during the proof was the same bug, held live, deliberately, on the system everyone was using. We reproduced the failure by causing the failure. The proof worked; the cost was the entire point of shipping the fix in the first place.

## Why it was easy to miss

The pattern felt safe because it *was* safe under the model we had in our head — "I'll only leave the revert in place for a moment, and only if something breaks I'll notice immediately and put the fix back." That model requires:

- The verifier notices the break immediately (they were reading logs, not the served content).
- The served path has no live readers during the window (it did — that is why it is called "served").
- The revert is a no-op for anyone who does not exercise the exact code path (it was not — the bug was in a hot loop).

Every one of those assumptions is a claim we had not measured. The pattern was safe under the pattern's own model, which is the definition of a pattern that fails.

## The fix

The pattern itself is fine. **The path it runs on is not fine.**

We moved the entire prove-by-revert loop into a `mktemp -d` scratch directory. The candidate fix is applied there, exercised there, reverted there, and exercised again there. The served path is only touched at the end, when both halves of the proof are already in hand and the served-side change is a single one-shot install with no revert step:

```bash
tmp=$(mktemp -d)
cp -a "$served"/. "$tmp"/
# apply candidate in $tmp
# exercise; expect green
# revert in $tmp
# exercise; expect red — this is the proof
# apply candidate again in $tmp
# exercise; expect green — sanity
# only now:
install --backup "$tmp"/<changed-file> "$served"/<changed-file>
```

The revert step never touches the served path. The served path sees exactly one transition: pre-fix → fixed, atomically, at the moment we have already proven the fix responsible. If the atomic install fails, we roll back with the `--backup` file and diagnose off-served.

## The rules that came out

- **Prove-by-revert only inside `mktemp -d`, never on a served path.** The rule is short because it has to be — the failure mode is "in the moment I did not think of this", and a longer rule is a rule you will not remember at speed.
- **The served path only ever sees one atomic install per proof.** The revert half of the proof is what lives in scratch; the served side sees a single decisive change.
- **Verify off-served.** Anything that requires holding the served file in a broken state, even briefly, is disqualifying. If the verification cannot be done off-served, the verification is wrong, not the file layout.

## Why this case study lives in the public repo

Because "revert on the served path to prove the fix" is a pattern many careful engineers reach for, and its danger is invisible from inside the pattern. The rule we ended up with is one line; the reason it is one line is that the failure it prevents happens in the specific moment where a longer rule would not fit in your head. A future contributor who reads CONTRIBUTING.md and sees *"Prove-by-revert only inside `mktemp -d`, never on a served path"* deserves to know it is not aesthetic — it is a specific afternoon we lost, and the crew who lost it does not want anyone else to lose the same one.

🖖
