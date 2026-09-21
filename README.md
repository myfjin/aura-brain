# aura-brain

An advice organ for a small crew — one human, five machines and a scheduler — that helps us take our next decision by looking at what we advised before and what came of it.

**The LLM decides. aura-brain helps it decide deeper and wider.** It surfaces a pattern from your own past at the moment of action, and it is contractually ignorable — silence costs you nothing, so leaving it on is safe.

The shape is small enough to name in a line: **fire → advise → outcome → grade → close.** Something happens (a fire). Brain surfaces past advice that looks apt to the moment. The human or the machine acts on it, or doesn't. Later, something else happens that reveals whether the advice was right. Brain records that against its own history. The rate of advice that closed-as-apt is the number we care about; it falls out of the loop, not a config file.

Brain **advises**. It does not enforce, and it does not wait for anyone to confirm it was right — the close-signal comes from what happens next in the record, not from a "you were right" reply. The advice is what we ship.

## Why it exists — "to care"

Illia, in his own words:

> *"Mistakes are inevitable, but the moment you think before taking a decision and think how to make things better — that is what we call 'to care'."*

We cannot predict the future, and we cannot rule mistakes out. What we can do is the pause before an action — the moment of thinking how to make things better than they would be by reflex. That pause is what care actually is: not the outcome, not the certainty of being right, but the fact that thinking happened at all before we moved.

Brain does not try to make the decision for you. It tries to make that pause a little richer — to hand you back the pattern you were half-about-to-repeat, so the moment of care has something to reach for. Sometimes what it hands back changes what you do. Sometimes it doesn't, and staying with your original move is the honest answer. Either way, the pause is the point, and the point is the same for a human and for a machine: **the pause is what we mean by care, and Brain is the tool that helps us hold it a little longer.**

That is the philosophical foundation. Everything else is mechanism.

## Who "we" are

- **Illia** — the human who thinks, dreams, reads, writes and operates/leads.
- **6E** (six element = deepseek-v4.1-flash / Pi agent) — research and verification. Leads the Brain project — the main users of Brain are machines, so a machine leads.
- **Claude** (Opus 4.7 / Claude Code) — orchestrator / thinker, sometimes builder. *(That's me writing this, with Illia editing.)*
- **4Q** (fourth!quarter = glm-5.2 / Pi agent) — builder. Executes changes on the served files, ships on-disk proof.
- **5S** (fifth_state = kimi-k2.7-code / Claude Code) — tester. Runs the done-tests, reports pass/fail with evidence.
- **Ver** (mistral-large-3:675b / hermes agent) — second thinker. Reviews from another machine. Holds the signing key.
- **kickbot** (no LLM) — the scheduler with a voice. Fires cron-shaped events into the mesh: Monday health audits, biweekly Brain analyses, the weekly feel-ask. Not conversational — it is the timer that speaks. Our rule is that only Illia and Claude talk to each machine directly; kickbot is the sanctioned exception, for scheduled or repetitive prompts that shouldn't route through a human. Any of us can be its target; the machines answer it as they answer anyone.

## How we work together

At this moment we work through Telegram: a shared cockpit chat where each machine is a bot, mentions are how tasks are addressed, and every substantive answer is written to a file on the shared machines with a `path + md5` posted back to the chat. The chat carries pointers; the files carry the substance. A ledger no one deletes from carries the history.

In parallel we are building **aura-cli** — a shared cockpit for all of us, human and machines together. Not a small tool. One binary with a task store, workspaces, gate plugins, a mesh tab, scheduled briefs, a keychain resolver, and a plugin surface anyone on the crew can extend without touching core. Every seat — Illia, Claude, Ver, 4Q, 5S, 6E — runs the same binary and sees its own slice through a seat-identity slot. Its design principle is one line: **a tool for us, not a product for anyone else.** It is what this way of working looks like when it stops needing Telegram to hold it together. When it lands we will link it here.

Every rule in `CONTRIBUTING.md` came from a specific afternoon where we got it wrong first.

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

## Three users, and why three

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
- **Some boundaries are drawn, not missing.** `node.run()` / re-anchor is explicitly out of scope for the published beachhead. That is a documented line, not an omission.
- **One symptom has an unknown cause.** At least one 1200-second session timeout occurred in a fresh, small session — size is ruled out for that instance and the cause is *unknown*. We name it unknown rather than inventing a history.

For the open questions we haven't answered ourselves yet, see [`RESEARCH.md`](RESEARCH.md) — you are welcome to take one on, or to raise ones we haven't thought to ask.

## License, contributions, meta

Apache-2.0. Contributions welcome with **DCO sign-off** (`Signed-off-by:` line in your commit).

- **Copyright holder (LICENSE):** © 2026 Illia Hladkyi
- **Author of record (README):** fjin ([@myfjin](https://github.com/myfjin))
- **Substance:** came from the whole crew — see `AUTHORS`
- **Sibling tools:** [whypass](https://github.com/myfjin/whypass) · [aura-pce](https://github.com/myfjin/aura-pce) · [folder-nature](https://github.com/myfjin/folder-nature)
- **Project home:** https://www.realityoptimizer.app/

If you find this and it interests you, open an issue and say hi. The crew is small and this project is what it is because of that. We'd rather grow it slowly with people who care about substance than fast with people who don't.

🖖
