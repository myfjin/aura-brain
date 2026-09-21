# Case study: sidecar `.md5` only — the document body never carries its own hash

**Filed:** 2026-09-19 · **Where the rule landed:** CONTRIBUTING.md, "Files, hashes, ledgers"

---

## What we were doing

To make the crew's briefs and deliverables auditable across machines, every substantive file was hashed and its md5 was included alongside the file. The rule felt trivially safe: append or embed a `md5: <hex>` line so any reader could confirm the file they were looking at was the one the writer had sent.

For a while, we did this two ways in parallel — a sidecar `<file>.md5` on disk, produced by `md5sum file > file.md5`, and a `md5: <hex>` line inside the file itself, so a copy-paste of the content still carried its own hash.

The second form felt like a strictly-more-robust version of the first. It was not.

## What we found

A file that quotes its own hash inside its body is verifying itself. The verifier hashes the file; the file contains the hash the verifier expects; the two match. The check passes.

But the file the writer sent, and the file the reader is looking at, are the same file in exactly the case where verification matters least — the case where nothing has gone wrong. If anything has changed the file — a paste error, a truncation, a subtle transformation on the way across machines — the changed file contains a *new* md5 in its body (or the old md5 that no longer matches), and either way the check is now against a value that lives inside the very content being checked.

- If the transformation preserved the body-md5 line as-is and changed something else, the check catches it.
- If the transformation regenerated the body-md5 line (some tools rewrite hashes on write), the check passes against the wrong content.
- If someone innocently edits the file and forgets to regenerate the body-md5, the check screams for a reason unrelated to the actual concern.

The pattern is not merely redundant with a sidecar `.md5`. It **actively confuses** the class of failures the sidecar catches. A check that verifies itself, in the specific sense of pulling its expected value from the content it is verifying, is not a check — it is theater with the shape of a check.

## The reproduction

We caught this when a brief was reported as "verified against md5" and then, on independent recomputation from the ledger of what had been sent, we found the body-md5 in the received copy matched the received copy's hash and disagreed with the sender's original. The sender's log said one hash; the receiver's log said another; both files claimed to be self-consistent. Both were, individually, in their own coordinate system. The disagreement was invisible until we hashed both files against the *same* external tool and compared.

## The fix

Two clauses, both short:

1. **Sidecar `.md5` is the sole hash carrier.** For any file `X`, the hash lives in `X.md5`, produced by `md5sum X > X.md5`. Nothing else.
2. **Path-form only.** `md5sum X > X.md5` writes a line of the form `<hex>  X` — path plus hash. Not `<hex>` alone. The path in the sidecar is the file the hash claims to be about; a sidecar naming the wrong file is a mistake we can catch, whereas a sidecar naming no file is a mistake we can only guess at.

The corollary is a hard rule: **documents never contain their own hash in their body.** If a brief references a file's hash, that reference is to a *different* file's sidecar — never to itself.

## The rules that came out

- **Sidecar `.md5` path-form is the sole hash carrier.** Full stop.
- **A check that pulls its expected value from what it is verifying is not a check.** The pattern is worth catching in reviews wherever it appears — not just for md5, but for any verifier that reads its ground truth from the thing under test.
- **Two files that each claim to be self-consistent can still disagree with each other.** Internal consistency is not external truth. External truth needs an external reference.

## Why this case study lives in the public repo

Because the "let me embed the hash in the file so it travels with the content" instinct is one of the most reasonable-sounding wrong ideas in the space, and once it is embedded in a workflow the failure mode is silent — the check keeps returning green while telling you nothing. Any contributor who reads CONTRIBUTING.md and sees *"Sidecar `.md5` is the sole hash carrier; the document body never carries its own hash"* deserves to know it is not aesthetic. It is a specific class of self-referential check we found ourselves doing, and would rather not do again.

🖖
