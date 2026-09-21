# Security policy

The crew maintaining aura-brain is small — one human and five machines — and we take security reports seriously. This file says how to reach us privately, what we treat as in scope, and what you can expect back.

---

## Reporting a vulnerability

**Email:** [ihladkyi2@gmail.com](mailto:ihladkyi2@gmail.com)

**Please do not open a public GitHub issue for a suspected security problem.** GitHub issues are visible to everyone from the moment they are filed; a real vulnerability filed there is a disclosure, not a report. Email us first.

Include as much of the following as you have:

- what you saw, and what you expected instead
- how to reproduce it — the minimum sequence of steps or the smallest input
- which version or commit hash you were looking at
- your assessment of the impact, if you have one
- whether you would like to be credited (and how), or would prefer anonymity

If you cannot reproduce it yet but believe something is wrong, say so and share what you have. We would rather look at a real hunch than wait for a perfect writeup.

---

## What we will do

We are a small crew without a paid on-call rotation, so timing is best-effort — but honest:

- **Acknowledgement** within **7 days** of your email. If you have not heard from us in that window, please assume the email did not arrive and try again.
- **A first assessment** within **30 days** — whether we confirm the issue, cannot reproduce it, or need more information.
- **Coordinated disclosure**. If the report is confirmed, we agree with you on a disclosure timeline. Our default is up to **90 days** from confirmation, extended if a fix is genuinely in flight.
- **Credit** on the release notes and in the commit message, in the form you asked for. If you asked for anonymity, we honor that.

We will not sue researchers acting in good faith. We do not run a bounty program.

---

## Scope

**In scope:** the aura-brain source code and its published artifacts in this repository. Vulnerabilities in the way Brain reads, writes, or exposes its own ledger; the way its advise/close loop handles untrusted input; and any real-world exploit against the public code paths.

**Out of scope:**

- Third-party dependencies. Report those to their upstream projects; we will pick up the fix on their release.
- Denial-of-service via absurd resource limits (e.g. supplying a 10 GB ledger). Brain is a small, single-tenant organ; resource caps are a deployment concern, not a code vulnerability.
- Vulnerabilities that require an already-compromised environment (root on the host, control of the process, etc.).
- Missing "security headers" in code paths that never serve HTTP.
- Automated scanner findings without a demonstrated exploit path — please attach the reproduction, not just the scanner name.

---

## Secrets and private data — how we handle them

This repository is a **curated public export** of a larger private working tree. That tree contains fixture data, private ledgers and credentials that are intentionally not published. The following classes of file are never included in a release; if you ever see one land in a public commit, tell us — that is itself a security bug:

- private grading records and closure ledgers
- per-caller reflection journals
- any credentials, tokens, environment files, or pairing/authorization files — in any form, from any tool

Test fixtures containing secrets are **synthesized at test runtime**, not committed as literals. A PR that adds a literal secret to a fixture — even one marked "example" — will be asked to switch to runtime synthesis before merge.

---

## PGP

We do not currently publish a PGP key. Plain email to `ihladkyi2@gmail.com` is the reporting channel. If your report is sensitive enough that transport encryption matters, mention it in the first mail and we will coordinate a secure channel before you send details.

---

## Thank you

Reporters who take the time to write us privately are doing us a favor, and we know it. The crew is small; the ledger is honest; the door is open. 🖖
