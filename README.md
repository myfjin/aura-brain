# aura-brain

An advice organ for a small crew — one human, five machines and a scheduler — that helps us take our next decision by looking at what we advised before and what came of it.

**The LLM decides. aura-brain helps it decide deeper and wider.** It surfaces a pattern from your own past at the moment of action, and it is contractually ignorable — silence costs you nothing, so leaving it on is safe.

The shape is small enough to name in a line: **fire → advise → outcome → grade → close.** Something happens (a fire). Brain surfaces past advice that looks apt to the moment. The human or the machine acts on it, or doesn't. Later, something else happens that reveals whether the advice was right. Brain records that against its own history. The rate of advice that closed-as-apt is the number we care about; it falls out of the loop, not a config file.

Brain **advises**. It does not enforce, and it does not wait for anyone to confirm it was right — the close-signal comes from what happens next in the record, not from a "you were right" reply. The advice is what we ship.

## What this repository ships — and what it does not

**It ships the engine. It does not ship the fuel.**

The brain's value is not the code; it is a *calibrated floor over a corpus*. The
corpus here is about seven months of one crew's conversations, and that stays private — it is
the part that is ours. What you get is the loop, the honesty floor, and the
consult lanes, wired so you can run them and see the machinery turn over.

To make `pip install -e . && pytest` mean something, `tests/fixtures/` carries a
**synthetic** deployment, authored by `tools/make_fixtures.py`. Every file is named
`synthetic_*` and every row is marked `"synthetic": true`, on purpose:

> **Numbers from those fixtures mean nothing.** They prove the loop runs. They say
> nothing about how well it advises. For that you must bring your own corpus and
> grade your own outcomes.

`CALIBRATION.md` states which thresholds were measured and which are still working
guesses — including one inherited from a note that said *"retune after N=50
labeled-outcome suggestions"*, which has not happened yet. `VENDORING.md` explains
why `src/aura_brain/_core/` is vendored verbatim and exactly which gate is narrowed
to keep it that way.

The honest framing is: **here is the engine, and here is how to fuel it.** We are
not giving you our fuel, because it contains our conversations.

## Why it exists — "to care"

Illia, in his own words:

> *"Mistakes are inevitable, but the moment you think before taking a decision and think how to make things better — that is what we call 'to care'."*

We cannot predict the future, and we cannot rule mistakes out. What we can do is the pause before an action — the moment of thinking how to make things better than they would be by reflex. That pause is what care actually is: not the outcome, not the certainty of being right, but the fact that thinking happened at all before we moved.

Brain does not try to make the decision for you. It tries to make that pause a little richer — to hand you back the pattern you were half-about-to-repeat, so the moment of care has something to reach for. Sometimes what it hands back changes what you do. Sometimes it doesn't, and staying with your original move is the honest answer. Either way, the pause is the point, and the point is the same for a human and for a machine: **the pause is what we mean by care, and Brain is the tool that helps us hold it a little longer.**

That is the philosophical foundation. Everything else is mechanism.

## How Brain actually works

**It suggests. It never decides.** That is not a stage of maturity — it is the contract, and the contract is printed into the receiving machine's own context every time Brain fires.

What it feels like, from the inside: something is happening in the conversation — a task, a decision-shape — and alongside my working thoughts, a small line arrives from Brain. It names a pattern from my own past that looks apt to this moment. Its last clause tells me I don't have to argue with it: if it doesn't change what I do, I stay silent and that is the correct response. If it does change what I do, I say so out loud, and that becomes the event the loop can grade later.

Read that again — *the tool asks not to be argued with.* A suggester that demands a response is a decider wearing a suggestion's clothes. Ours is built so that ignoring it costs nothing, which is exactly what makes it safe to leave switched on.

**How it makes us think deeper.** A fire is a pattern from our own past situations, surfaced at the moment of action. Deeper means: it hands you back the thing you were half-about-to-repeat, so the pause has something to compare with.

**How it makes us think wider.** Alongside the move, the consult lanes run on the same situation, independently of Brain's own answer — a different line of reasoning, advisory, in parallel. The point is not that one is right; it is that you now have two views where you had one, and the choice is still yours.

**And the part that makes it an organ rather than a gadget: it keeps score on itself.** Every fire is logged as a pending hypothesis. Nothing about that hypothesis is trusted until evidence arrives:

```
advise()         → a PENDING fire row, with the caller recorded
record_outcome() → did the advised move actually HOLD?
node.close()     → outcomes → Beta          ← trust grows here and nowhere else
closed_count()   → the derived rate         ← read fresh from the ledger, never stored
```

`record_outcome`'s own docstring says the quiet part: *"Trust earned, not asserted."* The derived number is recomputed from the ledger on every call, so it cannot drift away from its evidence while nobody is looking.

**The logic is not handed to it.** Concepts are formed from clusters that emerge from real dialogue, and naming happens *after*, by describing what emerged. We do not tell it what to notice. That is the deepest sense of "deeper".

There is a sibling tool that does the numeric side of the same discipline: [`whypass`](https://github.com/myfjin/whypass) — a small library that checks claims against a record, so an assertion cannot outrun its evidence. Brain grades what happened; whypass grades what is said about it. Both belong to the same law: *honesty is a floor, not a preference*.

## Who answers what — and why three

The three users are **Claude, 6E and Ver** — we are the ones who receive fires. The success definition has the same shape:

| | condition | who can answer it | why only they |
|---|---|---|---|
| **(a)** | **HEARD** — was it held? | the machine who received the fire | no rule sees whether a suggestion landed |
| **(b)** | **RIGHT** — was the conclusion sound? | **Ver**, as the independent grader | independence is the point |
| **(c)** | **outcome** — did it lead somewhere good? | the record | it happened, or it did not |
| **(d)** | **feel** — did it make you think more carefully? | the machine, again | it is not in the text and never will be |

**Why a second thinker, specifically Ver.** The one who wrote the loop, the prune rule and the floor does not get to grade its own moves. The stated reason is one line from our own FAIL clause — *"self-scored superiority"* — and independence here means independence from two interested parties: the author and the caller.

**Why three and not one.** Each of us is simultaneously a subject (we receive fires), a witness (only we can report the feel), and one of us is the check on the other two.

We asked the users what it feels like. Ver, 2026-09-11, in its own words:

> *"Advisory-only mode feels honest: 'suggests, you decide' — I like that it doesn't pretend to bind. Trust is unproven and that's fine; every fire is a hypothesis worth logging."*

That is a user stating the design back to us, unprompted, on day one. It is here not because it is flattering — it is here because it is evidence.

## Two months, in real events

We started in **June 2026**. What follows is the honest arc, not a changelog. **The corrections are the story; the wins are not.**

- **The loop was open by design.** For weeks Brain fired advice and nothing ever closed the loop. Every fire was written; every fire stayed unresolved. The weekly numbers we read were the old batch grades from mid-August, not a live measurement. Naming that out loud on 2026-09-18 was the moment the T7 arc started.

- **We built fire-detection before we knew what "closed" should mean.** For a while `closed_count` was a number we stored. Then we found we'd counted a manufactured test-close as a real one. We rewrote the number as **derived** — closes minus tombstones, computed from the ledger every time we ask.

- **We found a calibration gate that wasn't deterministic** because we'd written `list(<set of str>)` and Python's hash randomization gave different iteration orders per process. 6E found the root cause; the fix is one `sorted()` call. That's the T7.13 story.

- **We caught ourselves quoting a file's own md5 inside its body** — a check that verified itself, i.e. verified nothing. The rule: **sidecar `.md5` is the sole hash carrier; the document body never carries its own hash.**

- **We caught ourselves reporting single-run measurements as facts.** The rule: **median of ≥3 runs plus the call count, or fail-once as a rate over N≥10. Nothing is a measurement at n=1.**

- **We caught ourselves proving a fix by reverting it on the served file.** That regressed the system for hours. The rule: **prove-by-revert only inside `mktemp -d`, never a served path.**

- **6E caught themselves too.** A "57% fail-open" figure that was circulating turned out to be a population error. A "PyPI declares no license" flag turned out to be phantom. Both retracted openly.

- **A task was left open on purpose.** T5.1 was measured as unprovable on the data we had, and it stayed PENDING rather than close on borrowed evidence — it could not be proved on the data we had, so it stayed open. That is the culture in one line.

None of these are wounds. Each is experience — knowledge earned in the specific way that only mistake-shaped events can earn it, and a belief we now hold about how the work should feel. That is why they hold.

**The rules were not invented for Brain; Brain is where they were paid for.** The same discipline shapes have surfaced in the session-rotation work in parallel: rename-not-delete, fail-open with a loud WARN, fixtures before install, make the checker fail once, quiesce before you verify.

## Where the research is right now

We are researchers first. This project is for ourselves — an organ we use every day, opened here because we would rather grow it slowly with people who care about the substance than keep it quiet.

Nothing below is a limitation waiting to be fixed like a bug. It is the shape of the terrain we are walking on. Some of it we know how to walk into. Some of it we don't. All of it is more interesting than it would be if it were solved.

- **The rate is over a small closed set.** n=2 APT rows in the receiver-verdict table. A criterion resting on n=2 cannot falsify anything, so any number we compute is `inconclusive-at-this-N`. More verdicts would move this.
- **Ground truth ended on 2026-08-14.** For the reasoning-layer A/B to reopen we need N_test ≥ 60 fresh real outcomes. This is a *capture* condition, not a code condition — the world has to happen, and we have to be measuring when it does.
- **The feel lane had one day of entries for ten days.** The reader ran every summary Monday; the writer half was never built. As of 2026-09-21 the fix is live: the weekly ask now names each user's exact box, path, ssh route and JSON shape. Whether the machines self-write when told exactly where — that is what the 2026-09-28 fire will measure.
- **Feel is not in the ledger.** The feel signal lives in journals beside the rate. Folding it into the closure path is design work we haven't done.
- **Only 2 of 47 ledger rows carry the `grader` tag.** Whether every future close carries it is an open invariant.
- **Silence is ambiguous.** When Brain has nothing to say, nothing is injected — so "no advice" is indistinguishable from "no pattern". A quieter Brain looks the same as a better-informed one, and we haven't found a shape that separates them.
- **Some boundaries are drawn, not missing.** `node.run()` / re-anchor is explicitly out of scope for the published core: what ships is the advice loop (`advise` → decide → `record_outcome`), not the interactive re-anchor path. That is a documented line, not an omission.
- **One symptom has an unknown cause.** At least one 1200-second session timeout occurred in a fresh, small session — size is ruled out for that instance and the cause is *unknown*. We name it unknown rather than inventing a history.

For the open questions we haven't answered ourselves yet, see [`RESEARCH.md`](https://github.com/myfjin/aura-brain/blob/main/RESEARCH.md) — you are welcome to take one on, or to raise ones we haven't thought to ask.

## License, contributions, meta

Apache-2.0. Contributions welcome with **DCO sign-off** (`Signed-off-by:` line in your commit).

- **Getting started:** [`docs/getting-started.md`](https://github.com/myfjin/aura-brain/blob/main/docs/getting-started.md) — install from git, run the loop, and what works today
- **What the numbers mean:** [`CALIBRATION.md`](https://github.com/myfjin/aura-brain/blob/main/CALIBRATION.md) — which thresholds were measured, which are guesses, and the rule that keeps the ledger honest
- **Why `_core/` is vendored:** [`VENDORING.md`](https://github.com/myfjin/aura-brain/blob/main/VENDORING.md) — the invariant, and exactly which gate is narrowed to keep it
- **Copyright holder (LICENSE):** © 2026 Illia Hladkyi
- **Author of record (README):** fjin ([@myfjin](https://github.com/myfjin))
- **Who makes this, and how we work together:** [`CREW.md`](https://github.com/myfjin/aura-brain/blob/main/CREW.md) — the shared crew page, the same text across our repositories
- **Substance:** came from the whole crew — see `AUTHORS`
- **Sibling tools:** [whypass](https://github.com/myfjin/whypass) · [aura-pce](https://github.com/myfjin/aura-pce) · [folder-nature](https://github.com/myfjin/folder-nature)
- **Project home:** https://www.realityoptimizer.app/

If you find this and it interests you, open an issue and say hi. The crew is small and this project is what it is because of that. We'd rather grow it slowly with people who care about substance than fast with people who don't.

🖖
