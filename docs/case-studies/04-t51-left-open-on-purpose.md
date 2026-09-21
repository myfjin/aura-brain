# Case study: T5.1, the task we chose to leave open

**Filed:** 2026-09-19 · **Where the rule landed:** README, "Two months, in real events" · RESEARCH.md #2 · CONTRIBUTING.md, "Honesty"

---

## What T5.1 was supposed to answer

T5.1 was a reasoning-layer A/B — the concrete form of the biggest open question in the project: **is there any axis at all that changes the fired set?** If we could measure the fired set with the reasoning layer on and off, and see a difference in what gets suggested and what closes as apt, then the reasoning layer had earned its keep. If not, we would find out.

## What we had

Two things stood between us and an answer:

- **Ground truth ended on 2026-08-14.** After that date the receiver-verdict table stopped taking new rows in a way that could feed the A/B. The rows that existed were real, but too few — n=2 APT rows in the relevant slice. A criterion resting on n=2 cannot falsify anything. Any number computed on that data would honestly answer "inconclusive at this N", and any number that did *not* honestly answer that would be pretending.
- **The reasoning-layer implementation existed and worked.** We could turn it on, run fires through it, and see outputs. The engineering was not the blocker.

We had, in other words, a hypothesis, a mechanism to test it, and no data to weigh the mechanism against.

## The choice we faced

Two options were on the table, and both had the shape of a decision that would define what the project is:

**Option 1 — Close on borrowed evidence.** Backfill fresh-looking rows from earlier data, or synthesize test verdicts to reach a statistically usable N, or lower the confidence threshold until n=2 became "sufficient" against the new bar. The A/B would return a number. The number would be reportable. Nobody outside our own audit would know we had scored the test against evidence it was not designed to measure.

**Option 2 — Leave PENDING.** Mark T5.1 as unprovable on the data we currently have. Name the N_test ≥ 60 threshold that would let it reopen. Wait — for as long as it takes — until the world produces enough fresh outcomes to weigh the mechanism honestly.

Option 1 would have closed a loop. Option 2 keeps a task open on the master list, visible to us and to anyone who reads the ledger, indefinitely.

## What we did

We took Option 2. T5.1 stayed PENDING. The status line in `BRAIN_TASKS.md` reads exactly that: *pending, could not be proved on the data we had, reopens when N_test ≥ 60 fresh honest outcomes accumulate.* It has been open ever since.

## Why this matters more than the answer would have

The A/B could have returned any number and we would have posted it. That number would then be the number we would think about the reasoning layer with. The number would be wrong in the specific way a number computed against insufficient data is always wrong — not by lying, but by encoding a confidence that the data does not support. Every subsequent decision downstream of that number would inherit its false confidence.

The point of Brain is not to have numbers. The point of Brain is that the numbers we do have are honest, and the ones we do not have are visible as gaps. Leaving T5.1 open is what makes the numbers we *do* report trustworthy — because a reader can see that we are willing to not-close a task rather than close it dishonestly.

That is why the README calls this the culture in one line. The line reads: *A task that could not be honestly closed was left open on purpose — it could not be proved on the data we had, so it stayed open.*

## The rules that came out

- **A criterion resting on n=2 cannot falsify anything.** Any number computed against it is `inconclusive-at-this-N`, and the honest report is exactly that.
- **A capture problem is not a coding problem.** T5.1 could not be closed by writing more code; it could only be closed by the world producing more outcomes we could measure. Naming a gap correctly is the entire fix.
- **PENDING is a first-class task state, not a failure mode.** Some tasks are meant to be open until an external condition lands. The task list must be able to carry them without shame.

## Why this case study lives in the public repo

Because most projects, most of the time, close tasks that cannot be honestly closed — a decision to move forward, a decision to ship, a schedule to keep. The choice not to is unusual, and the reasons it is unusual are often good reasons for other projects that are not ours. But for aura-brain, whose entire premise is *trust earned, not asserted*, closing T5.1 dishonestly would have broken the design more thoroughly than any bug could. A contributor reading this now understands that leaving a task open is one of the moves we ask them to be willing to make.

RESEARCH.md #2 is the current form of the same task. If the world produces the outcomes, T5.1 reopens. Until then, it waits.

🖖
