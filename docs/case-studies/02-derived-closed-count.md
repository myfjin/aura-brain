# Case study: closed_count, from stored number to derived quantity

**Filed:** 2026-09-19 · **Where the rule landed:** CONTRIBUTING.md, "Files, hashes, ledgers" and "Failure modes"; README, "How Brain actually works"

---

## What we thought was true

`closed_count()` returned the number of fires that had closed as apt — the headline metric of Brain's whole loop. For a while it was a **stored** number: `closed_count` lived as a counter that got incremented every time `node.close()` fired with a positive outcome. Fast, cache-friendly, easy to display.

## What we found

We were counting a **manufactured test-close** as a real one.

The path was small and, in hindsight, obvious. A test fixture had synthesized a "closed" event to exercise the closure path; the test cleaned up its own row from the ledger afterwards, but the counter increment had already fired at the moment of the synthesized event. The cleanup rolled back the row; it did not roll back the number. From then on, the counter reported one closed fire that no ledger row corroborated.

The gap surfaced when we cross-checked the counter against a fresh recomputation from the ledger — the two disagreed by one. Then we found we could not tell which was right. The counter had been the source of truth for weeks; the ledger was, by design, append-only and shouldn't have been discarding rows, but "shouldn't have been" is not evidence.

## The realer failure underneath

The specific over-count was small. The deeper failure was the design: **the number we cared about was a claim, not a measurement.** A stored counter is a promise that every future writer will remember to increment it, and that no reader will ever want to know the number under a different definition than the one baked in at increment time. The moment we asked "what if a close later got tombstoned?" we had no answer other than "the counter doesn't know."

That is the exact failure mode Brain is meant to catch in other systems — a rate reported as a fact, cut loose from the evidence that would judge it. We were doing it to ourselves.

## The fix

We rewrote `closed_count()` as a **derived** quantity, computed fresh from the ledger every time it is called:

```python
def closed_count() -> int:
    """Trust earned, not asserted. Recomputed from the ledger on every call."""
    return _count_closes() - _count_tombstones()
```

- `_count_closes()` walks the ledger and counts rows whose event is a close.
- `_count_tombstones()` walks the ledger and counts rows whose event is a tombstone.
- The subtraction is the answer.

No caching. No stored counter. If the ledger says three closes and one tombstone, `closed_count()` returns two — always, on every call, forever. If a future tombstone lands, the next call returns one, not because a counter was updated but because the ledger changed and the derivation followed.

The one performance question ("this walks the ledger on every call — expensive?") was answered by measurement, not by intuition: at current ledger size the walk is under a millisecond, and the ledger grows slowly enough that the cost stays negligible for a long horizon. If it ever stops being negligible, we cache with an explicit invalidation on ledger write — but we do not cache on speculation.

## The rules that came out

- **Tombstone, do not delete.** The ledger is append-only. Rows that get retracted get tombstoned, not removed. Whatever the "closed count" definition is, it can be re-derived from the ledger's history alone.
- **Derived beats stored, when the derivation is cheap.** A number computed from evidence on every read cannot drift away from that evidence. A number cached from a stale computation always can. The default is derive; storing is an optimization you earn.
- **`record_outcome`'s docstring is the contract.** *"Trust earned, not asserted."* If a metric can be derived from the ledger, deriving it is how trust becomes visible.

## Why this case study lives in the public repo

Because the design failure — a metric that stores rather than derives — is one of the most common shapes of dishonesty a small system falls into, and the fix does not require any exotic machinery. It requires deciding, on a case-by-case basis, whether a number is a measurement or an assertion. `closed_count()` should have been the easy one; we still got it wrong first.

The rule "tombstone, do not delete" is the audit-friendliness of this design made durable. Any future contributor who wants to know why we do not offer a `close_delete()` API has this document.

🖖
