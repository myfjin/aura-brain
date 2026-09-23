# Calibration — what the numbers mean, and how much to trust them

This file exists because the honest answer to "how well does the brain work?" is
**"we do not know yet, and here is exactly what would tell us."** A repository that
ships a threshold without saying where it came from invites a reader to assume the
threshold was measured. Some of it was; some of it was not. Both are below.

## The engine and the fuel

The brain is a **calibrated floor over a corpus**. The code is the engine; the
corpus is the fuel. This repository ships the engine and a synthetic stand-in for
the fuel, so the loop runs. It does not ship the corpus, because the corpus is
about seven months of one crew's conversations.

Consequence, stated plainly: **a number produced from `tests/fixtures/` measures
nothing about how well the brain works.** Those fixtures are authored, not
observed. They prove the machinery turns over. If you want a measurement you must
bring your own corpus and grade your own outcomes.

## The thresholds, and their provenance

Nothing here is a tuned parameter. Each is a working guess with a date and a
reason, recorded so a successor does not mistake it for a finding.

| where | value | provenance |
|---|---|---|
| `_core/ds_need.THRESHOLD` | **0.30** | **Measured, 2026-07-05.** Five diverse negative asks scored ≤ 0.208; the weakest true positive scored 0.346. 0.30 sits in the gap with margin on both sides. This is the one threshold that came from a measurement. |
| `_core/logic_lane.THRESHOLD` | 0.30 | Mirrors the ds lane. Same shape of registry, same embedder — **not** independently measured. Treat as a guess. |
| advice-floor / `arbiter` thresholds | — | The floor is a **judgement**, routed through a model, not a cosine. It is deterministic in structure and non-deterministic in outcome; see `docs/case-studies/01-nondeterministic-calibration.md`. |

A note we inherited and are honouring rather than hiding: an early gate was set at
**0.6 as a working guess, "to be retuned after N=50 labeled-outcome suggestions."**
That retune has not happened. The number is still a guess.

## The rule that keeps the ledger honest

**Influence requires that the advice arrived before the action, and had a chance
to change it.** A consult run after the work is done, or run to test the
mechanism, is **`UNKNOWABLE`** — not a "held". An honest null is data; an inflated
hold is a lie in the ledger, and it poisons every rate computed from it.

So the headline rate is never reported alone. Three numbers travel together:

- **held%** — advice that arrived in time and changed something.
- **null%** — consults that arrived in time and were ignored, or had no bearing.
- **the gap** — the difference. *This* is the number that matters.

And never folded into either: **worked / failed / unknown**. Outcome is not
accuracy. A move can be right and fail anyway.

## What a calibration would require

1. **A labelled corpus.** Situations with a graded outcome and, for each, whether
   the advice preceded the action. Our own ledger stands at tens of rows, which is
   not enough to move a threshold.
2. **The null rate reported beside every hit rate.** A lane that fires often looks
   productive until you see how often it fires on nothing.
3. **A negative control per lane.** One input that must *not* fire, asserted. If
   every input fires, the fixture is rigged — and this control is not a formality:
   on its first run it caught a lane that reported an *error* where the honest
   answer was "no patterns yet".
4. **A fail-once proof for every checker** before that checker is trusted.

Until 1–4 hold, treat every confidence score in this repository as a **shape**,
not a quantity.

## The synthetic fixtures

`tools/make_fixtures.py` authors them. Every file is named `synthetic_*` and every
row carries `"synthetic": true`. They are deterministic and contain nothing from
any real deployment — no dialogue, no ledger, no move.

They are there so that `pip install -e . && pytest` means something. They are not
there to be believed.
