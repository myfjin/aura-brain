# Case study: the 57% fail-open figure that was a population error

**Filed:** 2026-09-19 · **Where the rule landed:** CONTRIBUTING.md, "Honesty" · README, "Two months, in real events"

---

## What we thought was true

A weekly rollup of the honesty-floor callsites had produced a headline number: **57% of fires were fail-opening.** The number was startling — high enough that it implied the floor was under-catching by a large margin, and it was in the running to reshape what the next month of work would look like. It had been circulating internally for several days and had already begun to appear in cross-references from other briefs.

The rollup came from 6E, who owns `BRAIN_TASKS.md` and the calibration paths. It was reported as a measurement, not a claim.

## What we found

6E found it himself, before anyone else did.

On a re-read of the rollup input, 6E noticed that **two lanes had been merged when they should not have been.** The rollup was computing "fires that fail-opened" against a denominator that included fires from a lane whose fail-open path was structurally different — a lane that had a very high fail-open rate for a design-intended reason unrelated to the pathology the number was meant to measure. The merged denominator had inflated the ratio.

The correct measurement, on the lane the metric was actually about, was substantially lower — well within the range where the honesty floor was doing what it was supposed to. The 57% figure was not merely imprecise; it was pointing at a problem that did not exist.

## The choice 6E faced

Two options were, again, on the table:

**Option 1 — Fold the correction into the next weekly rollup.** Let the number quietly get replaced by the correct one when the next report cycled. Nobody would have to publicly walk anything back. The correction would land.

**Option 2 — Retract in the same visible place.** Post the retraction, name the population error, show the corrected number, name the direction of the error (over-stated, not under-stated), and take the visible loss of authority that comes with saying *"I published a number that was wrong."*

## What 6E did

Option 2. The retraction was posted openly. It named the population error. It named the corrected number. It said out loud that the direction of the error was over-stated — that the original figure had made the floor look worse than it is. It did not soften the correction with hedging language. It did not fold blame into the tools or the pipeline. It stated the mistake and the fix, and moved on.

The same week, 6E retracted a **second** claim — that a public PyPI package "declares no license." On closer inspection, the license *was* declared (SPDX expression, PEP 639 form); the reader had been checking a deprecated field while the current field was populated correctly all along. That retraction was posted the same way: openly, in the same visible place, with the direction of the error named.

## Why the retraction made the conclusion stronger

This is the part worth naming. The intuition is that a retraction weakens the retractor — it publicly admits fallibility, it costs authority. In fact the retraction made the ledger stronger, in two ways:

1. **It calibrated everyone who was reading 6E's numbers.** After the retraction, the next number 6E posted was received with the confidence 6E had actually earned — high, because the correction had shown the review process working, and the pipeline had not been silently propagating uncorrected errors. A retraction is a form of measurement discipline made visible.
2. **It made the corrected number believable.** The lowered 57% figure could have been received as "6E is trying to save face by revising it downward." Because the retraction named the population error concretely, showed the merged-lane structure, and named the direction of the correction, the new number was the same class of measurement as the old one — but with the error removed. Nobody needed to trust 6E's motives; they could see the mechanism.

## The rules that came out

- **Retract in public.** If a number you published turns out to be wrong, correct it in the same visible place, name the direction of the error, and show the mechanism. Silent edits are worse than the original mistake — they make every future number harder to trust.
- **Name the direction of the error.** *"Over-stated"* and *"under-stated"* are different classes of failure with different downstream implications. A retraction that says only "the number was wrong" is doing half the work.
- **Retraction is a strength, not a weakness.** In a system whose whole design is *trust earned, not asserted*, a public retraction is one of the strongest signals the design is working. It is not something to minimize; it is something to be legible about.

## Why this case study lives in the public repo

Because most published metrics, in most codebases, do not get retracted when they turn out to be wrong. They get replaced quietly by the next release's numbers, or they age out of the public record, or they persist as anecdote long after the underlying measurement has been corrected. That pattern is understandable — retraction costs authority — and it is corrosive to any system built on the honesty of its own numbers.

6E's retractions here are the concrete form of the rule *"trust earned, not asserted."* A contributor who reads this document, sees the CONTRIBUTING.md line about public retraction, and asks whether we really mean it, has a specific answer: yes, and here is the person who did it, and here is the number that changed, and here is why the ledger came out stronger for it.

🖖
