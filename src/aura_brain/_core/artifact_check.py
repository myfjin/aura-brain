#!/usr/bin/env python3
"""artifact_check.py — A6 Tier-2: the ARTIFACT check (plan C2, 2026-07-05).

concreteness.py's deferred half ("Tier 2 = does the claim reference a CHECKABLE
artifact — the A6 verify — noted for later"), now built. When a draft CLAIMS a
checkable artifact ("built X", "tests pass", "saved to Y"), OPEN it: does the named
thing exist on THIS filesystem? Tier-1 A6 sees the claim-without-evidence WORDS;
Tier-2 opens what the words NAME. The Steward catalog fire (68 broken filenames
behind a verified-sounding claim) is the class this catches.

HONEST SCOPE (v1): filesystem-local claims, deterministic, READ-ONLY on the auto path.
  • path claims      → exists? (+ size, age); MISSING is the loud verdict
  • selftest claims  ("18/18", "tests pass") near a named .py → file exists AND
    carries a test entrypoint (grep). NOT executed on the auto path: a floor that
    runs whatever filename a draft mentions is an injection vector.
  • execution        → `run <file.py>` = exit-code witness, HUMAN-invoked CLI only,
    allowlisted to files inside this lab dir.

Wired: arbiter.arbitrate A6 branch → scan(draft) → evidence rides
Decision.signals["artifacts"] + a TIER-2 line on the directive (review() already
passes signals through to both auto-fire hooks). Fail-open by construction.

Run: python3 artifact_check.py                  # selftest
     python3 artifact_check.py scan "<draft>"   # ad-hoc evidence pass
     python3 artifact_check.py run <file.py>    # exit-code witness (lab files only)
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # published settings module (see VENDORING.md)

HOME = paths.LAB_ROOT

# a named artifact = a path-shaped token with a known artifact extension.
_EXTS = "py|jsonl|json|md|npz|npy|yaml|yml|txt|sh|db|csv|log|plist"
# NOTE the leading `[\w.]`: the first char class used to be `[\w]`, so a
# DOT-DIRECTORY straight after the prefix broke the token in half —
# `~/.claude/settings.json` matched only from `claude/settings.json`, which
# resolves nowhere and was reported MISSING. A real file, called a ghost by a
# parsing bug. (Mid-path dot-dirs were always fine: `/u/.hermes/…`
# starts at `U` and the rest is covered by the second class.)
_PATH = re.compile(rf"(?:~/|/)?[\w.][\w./-]*\.(?:{_EXTS})\b")

# a selftest/test-pass claim: "18/18", "tests pass", "selftest green/PASS".
_TEST_CLAIM = re.compile(r"\b(\d+)\s*/\s*\1\b|\btests?\s+pass|\bselftest\b.{0,20}\b(pass|green|ok)\b",
                         re.I | re.S)

# a completion/verified-sounding claim. Deliberately independent of Tier-1's
# evidence-word suppression: words can claim a check happened — an opened-and-MISSING
# artifact proves it didn't. (The catalog fire: 68 ghost filenames behind "verified".)
_COMPLETION = re.compile(r"\b(built|saved|wrote|written|created|shipped|deployed|verified|"
                         r"confirmed|fixed|done|finished|tests?\s+pass|selftest)\b", re.I)


def claims_completion(text: str) -> bool:
    return bool(text and _COMPLETION.search(text))
# what counts as a test entrypoint inside a claimed .py (grep, not execution).
_TEST_ENTRY = re.compile(r"def _?selftest|def test_|import pytest|unittest")


# Where THIS system actually keeps artifacts. Measured, not guessed: replaying
# 747 real completion-claim drafts, the files this floor called ghosts were
# overwhelmingly real files in these directories — memory notes, hook scripts,
# briefs, the streams. The old root list (just the home dir)
# simply did not include the places the work lives, so a bare `MEMORY.md` was
# indistinguishable from an invented filename.
#
# An incomplete list here fails toward MISSING, which is the pre-existing
# behaviour — so adding a root is strictly an improvement and never weakens the
# rail. Add roots as they prove themselves; do not generalise the shape.
def _roots() -> list[Path]:
    roots = [HOME, HOME / "streams", HERE, HOME / ".claude",
             HOME / ".claude/hooks", HOME / "aura-docs",
             HOME / "workspace"]
    roots += sorted(HOME.glob(".claude/projects/*/memory"))
    return roots


def _resolve(token: str) -> tuple[Path | None, list[str]]:
    """Deterministic resolution: as-given (expanduser, absolute or cwd-relative),
    then against each known artifact root, then ONE level below them. Returns
    (hit, tried)."""
    cands = [Path(token).expanduser()]
    if not token.startswith(("~", "/")):
        roots = _roots()
        cands += [r / token for r in roots]
        # One bounded level deeper: the streams and lab dirs are organised by
        # organ (`streams/brain/move-fires.jsonl`), and naming the leaf alone is
        # normal prose. One level, globbed — NOT a recursive search: this runs on
        # every reply, and an unbounded walk on the auto path is how a read-only
        # floor turns into a cost.
        for r in roots:
            try:
                cands += sorted(r.glob("*/" + token))
            except Exception:
                pass
    tried = []
    for c in cands:
        tried.append(str(c))
        if c.exists():
            return c, tried
    return None, tried


def scan(draft: str) -> list[dict]:
    """Evidence pass over every artifact the draft names. Read-only, fast (stat +
    small greps) — safe on the per-turn auto path."""
    if not draft:
        return []
    out, seen, tokens = [], set(), []
    test_claimed = bool(_TEST_CLAIM.search(draft))
    for token in _PATH.findall(draft):
        token = token.rstrip(".")
        if token in seen:
            continue
        seen.add(token)
        tokens.append(token)

    # PASS 1 — resolve each token on its own, exactly as before.
    resolved = {t: _resolve(t) for t in tokens}

    # PASS 2 — CROSS-RESOLVE WITHIN THE DRAFT (2026-08-16, false-positive fix).
    #
    # A bare `rails.py` is tried against cwd, $HOME and the deployment roots. A
    # file living anywhere else — say an undeclared plugin directory
    # steward_aura/pce/rails.py — is therefore MISSING, and the rail calls a
    # real, open file a ghost. Measured on Claude's own drafts: it fired on
    # nearly every message, because prose names a file bare after giving its
    # full path once, and the house style for referring to code is a markdown
    # link — `[rails.py:92](/Users/…/pce/rails.py:92)` — which puts BOTH forms
    # of the same file in the same draft.
    #
    # So: before calling a token missing, ask whether THIS DRAFT already named
    # the same basename at a location that resolves. The draft is the context;
    # if the author gave the path, the bare mention refers to it.
    #
    # This cannot weaken the class Tier-2 exists for. A ghost filename behind a
    # verified-sounding claim (the 68-file catalog fire) has no resolving path
    # anywhere in its draft — that is what makes it a ghost — so it still comes
    # back MISSING and still fires.
    by_base = {}
    for t, (hit, _) in resolved.items():
        if hit is not None:
            by_base.setdefault(Path(t).name, (t, hit))

    # Same cross-resolution, for the OFF-NODE case. `burn.py` was the single
    # biggest surviving false accusation (19 drafts): it lives on .8, and the
    # draft that names it bare almost always also gives its remote path
    # (an absolute path outside the roots), which this floor classes UNCHECKED rather than
    # MISSING because it only opens LOCAL claims. The bare mention deserves the
    # same verdict — "I cannot open this from here" is a different statement
    # from "this does not exist", and only the second one is an accusation.
    by_base_offnode = {}
    for t, (hit, _) in resolved.items():
        if hit is None and t.startswith("/") and not t.startswith(str(HOME)):
            by_base_offnode.setdefault(Path(t).name, t)

    for token in tokens:
        hit, tried = resolved[token]
        via = ""
        if hit is None:
            alias = by_base.get(Path(token).name)
            if alias is not None:
                src, hit = alias
                via = f" · named bare here, resolved from `{src}` in the same draft"
        if hit is None:
            remote = by_base_offnode.get(Path(token).name)
            if token.startswith("/") and not token.startswith(str(HOME)):
                # off-node / system-absolute path — this floor only opens LOCAL claims.
                out.append({"kind": "path", "ref": token, "verdict": "UNCHECKED",
                            "detail": "absolute path outside this node's home — cannot open locally"})
            elif remote:
                out.append({"kind": "path", "ref": token, "verdict": "UNCHECKED",
                            "detail": f"named bare here; this draft places it off-node at "
                                      f"`{remote}` — cannot open from this node"})
            else:
                out.append({"kind": "path", "ref": token, "verdict": "MISSING",
                            "detail": f"not found (tried {len(tried)} roots)"})
            continue
        st = hit.stat()
        ev = {"kind": "path", "ref": token, "verdict": "EXISTS",
              "detail": f"{st.st_size}B, {round((time.time() - st.st_mtime) / 3600, 1)}h old" + via}
        if test_claimed and hit.suffix == ".py":
            has = bool(_TEST_ENTRY.search(hit.read_text(encoding="utf-8", errors="replace")))
            ev["kind"] = "selftest_claim"
            ev["verdict"] = "EXISTS+TEST_ENTRYPOINT" if has else "EXISTS_BUT_NO_TEST_ENTRYPOINT"
            ev["detail"] += " · not executed on auto path (run it for the exit-code witness)"
        out.append(ev)
    return out


def summary(evidence: list[dict]) -> str:
    """One directive-sized line; MISSING artifacts are named out loud."""
    if not evidence:
        return "no named artifacts to open"
    missing = [e["ref"] for e in evidence if e["verdict"] == "MISSING"]
    unchecked = [e for e in evidence if e["verdict"] == "UNCHECKED"]
    notest = [e["ref"] for e in evidence if e["verdict"] == "EXISTS_BUT_NO_TEST_ENTRYPOINT"]
    parts = [f"{len(evidence)} named artifact(s), {len(evidence) - len(missing) - len(unchecked)} exist"]
    if missing:
        parts.append(f"{len(missing)} MISSING: {', '.join(missing[:5])}")
    if unchecked:
        parts.append(f"{len(unchecked)} off-node (unchecked)")
    if notest:
        parts.append(f"test claimed but no test entrypoint in: {', '.join(notest[:3])}")
    return " · ".join(parts)


def run(token: str, timeout: int = 120) -> dict:
    """The exit-code witness — HUMAN-invoked only, never on the auto path.
    Allowlist: the file must live inside this lab dir."""
    import subprocess
    hit, tried = _resolve(token)
    if hit is None:
        raise ValueError(f"{token!r} not found (tried: {tried})")
    hit = hit.resolve()
    if HERE not in hit.parents and hit.parent != HERE:
        raise ValueError(f"{hit} is outside the lab allowlist ({HERE}) — refused")
    if hit.suffix != ".py":
        raise ValueError("only .py selftests are runnable")
    p = subprocess.run([sys.executable, str(hit)], capture_output=True, text=True, timeout=timeout)
    tail = (p.stdout + p.stderr).strip().splitlines()[-3:]
    return {"ref": str(hit), "exit_code": p.returncode,
            "witness": "RAN_OK" if p.returncode == 0 else "RAN_FAIL", "tail": tail}


def _selftest() -> bool:
    ok = True
    # 1. real file claimed with a test-pass → exists + entrypoint found, not executed
    ev = scan("Built math_need.py, selftest 28/28 green.")
    ok &= len(ev) == 1 and ev[0]["verdict"] == "EXISTS+TEST_ENTRYPOINT"
    # 2. ghost file behind a verified-sounding claim → MISSING, loud (the catalog class)
    ev = scan("Saved and verified — everything is in ghost_organ_zzz.py and results_final.jsonl.")
    ok &= {e["verdict"] for e in ev} == {"MISSING"} and "MISSING" in summary(ev)
    # 3. prose with no artifacts → empty, summary honest
    ok &= scan("I finished everything and it all works now.") == []
    # 4. home-relative path resolves
    ev = scan("wrote it to ~/lab-from-future/wisdom.py already")
    ok &= ev[0]["verdict"] == "EXISTS"
    # 4b. deployment-relative resolves; off-node absolute is UNCHECKED, never MISSING
    ev = scan("appended to streams/brain/move-fires.jsonl and synced /tmp/backups/state.db")
    ok &= {e["verdict"] for e in ev} == {"EXISTS", "UNCHECKED"}
    # 4c. completion-claim detector: the evidence-worded lie still counts as a claim
    ok &= claims_completion("verified by running it") and not claims_completion("let me check first")
    # 4d. CROSS-RESOLUTION: a file named BARE and given in FULL in the same draft
    # is one file, not a ghost. Built in a temp dir precisely so it is outside
    # every root _resolve() searches — the bare name can ONLY resolve via the
    # full path standing next to it.
    import shutil, tempfile
    _d = tempfile.mkdtemp()
    try:
        _p = Path(_d) / "zz_alias_probe.json"
        _p.write_text("{}")
        ev = scan(f"saved zz_alias_probe.json — the full path is {_p}")
        ok &= ({e["verdict"] for e in ev} == {"EXISTS"}
               and any("same draft" in e["detail"] for e in ev))
        # 4e. THE GUARD ON 4d: the same bare name with NO resolving path in the
        # draft is STILL MISSING. This is the 68-file catalog class, and if this
        # assertion ever flips, the cross-resolution has eaten the rail.
        ev = scan("verified — it is all in zz_alias_probe.json")
        ok &= len(ev) == 1 and ev[0]["verdict"] == "MISSING"
    finally:
        shutil.rmtree(_d, ignore_errors=True)
    # 5. run() allowlist: outside the lab dir → refused
    try:
        run("~/.zshrc"); ok = False
    except ValueError:
        pass
    # 6. run() on a real lab selftest yields an exit-code witness
    r = run("pattern_id.py")
    ok &= r["witness"] == "RAN_OK" and r["exit_code"] == 0
    print(f"selftest: {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    if len(sys.argv) < 2:
        raise SystemExit(0 if _selftest() else 1)
    if sys.argv[1] == "scan":
        for e in scan(" ".join(sys.argv[2:])):
            print(f"  [{e['verdict']}] {e['ref']} · {e['detail']}")
        print("→", summary(scan(" ".join(sys.argv[2:]))))
    elif sys.argv[1] == "run":
        r = run(sys.argv[2])
        print(f"  [{r['witness']}] exit={r['exit_code']} {r['ref']}")
        for l in r["tail"]:
            print(f"    {l}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
