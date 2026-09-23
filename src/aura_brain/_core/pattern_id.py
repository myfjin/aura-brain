#!/usr/bin/env python3
"""pattern_id.py — stable identity for patterns (B1 of BRAIN-FINISH-PLAN-2026-07-05).

The bug this kills (gap #2): outcomes keyed to the pattern NAME, but names are
DERIVED — merge.py rebuilds the library from raw on every consolidator/distiller run,
the canonical name is whichever member sits closest to the centroid, and names are
not even unique (25 dup raw names, 2 dup canonical names found 2026-07-05). Renames
silently orphaned earned trust (1 of the first 2 move-outcomes was lost this way).

The law after B1:
  - a RAW pattern's id is minted from its content at birth and NEVER changes
    (raw is append-only; the id is re-derivable from the row itself),
  - a CANONICAL pattern carries `id_set` = the raw ids of its members (merge computes
    it exactly — it knows its members) and `id` = hash of that set,
  - OUTCOMES rows carry `pattern_ids` = the canonical's id_set at record time,
  - tallies match by ID-INTERSECTION when both sides have ids; name equality is only
    the legacy fallback. Rename, remerge, resplit — the trust follows the raw lineage.
"""
from __future__ import annotations

import hashlib


def raw_id(row: dict) -> str:
    """Deterministic identity of a raw per-episode pattern. Derived from birth
    content (name at birth + distillation timestamp + grounded source ids), so any
    reader can recompute it for an unstamped legacy row."""
    core = (f"{row.get('name', '')}|{row.get('distilled_at', '')}|"
            f"{','.join(str(i) for i in row.get('source_component_ids', []))}")
    return hashlib.sha1(core.encode("utf-8")).hexdigest()[:16]


def canon_id(id_set) -> str:
    """Identity of a canonical pattern = hash of its member raw ids. Changes only
    when membership changes — which is exactly when it SHOULD change; the id_set
    itself is what outcomes intersect against."""
    return hashlib.sha1(",".join(sorted(id_set)).encode("utf-8")).hexdigest()[:16]


def match(entry: dict, name: str, id_set: set) -> bool:
    """THE matching rule, single source of truth for tallies/orphans/pain read-back:
    if both the ledger entry and the pattern carry ids → ids are authoritative
    (intersection); otherwise fall back to name equality (legacy rows)."""
    eids = set(entry.get("pattern_ids") or [])
    if id_set and eids:
        return bool(id_set & eids)
    return entry.get("pattern") == name
