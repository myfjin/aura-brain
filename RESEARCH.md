# Open questions in aura-brain

These are the questions we — the crew who built Brain and use it daily — cannot answer alone. Each is real; each has a reason it is still open. This file is not a roadmap: some of these we are actively walking into, some we do not yet know how to walk into, and some we may never close.

You are welcome to take one on, or to raise ones we haven't thought to ask.

---

1. **Is there any axis at all that changes the fired set?** Answerable from the existing streams + graded outcomes, no export dependency. Single most valuable open question in the project.

2. **N_test ≥ 60 fresh, honest outcomes** for the T5.1 A/B to reopen. A capture problem, not a coding problem — the world has to happen, and we have to be measuring when it does.

3. **Where does `why_pass` live?** The published core calls a private `why_pass.py` module in five places. The public [`whypass`](https://github.com/myfjin/whypass) package on PyPI (`pip install whypass`, Apache-2.0, zero deps) exports `lint / Finding / Record / grounded` and no more — the private internals used inside Brain are not there. Either upstream them so the core compiles against the public package, or port those five call sites onto the public API. Until then Brain cannot honestly say `depends on whypass`.

4. **Duplicate names in the pattern library** — 935 rows, 933 unique names. Name-keyed maps collide silently.

5. **Why do sessions time out when they are small?** 71 lifetime timeouts, at least one at the full 1200 s in a fresh session. Cause unknown; size is ruled out for that instance.

6. **Does the environment resume archived streams?** Rotation archives on rename and our selector excludes by name — whether other consumers do the same is untested.

7. **`node.run()` / re-anchor scope.** Either bring it in or document why the boundary is where it is.

8. **Is the growth rate really 50 KB/h?** That number set the 1.5 MB rotation threshold at n=1 day. Re-measure over a week.

9. **The `grader` key only reached 2 of 47 ledger rows.** Whether every future close carries it is an open invariant, not a settled one.

10. **Ver-as-grader is n=2.** More verdicts is a contribution nobody has made yet.

---

If you have thoughts, evidence, or a new question worth adding, open an issue or a PR against this file. The crew is small; questions are how the work grows.

🖖
