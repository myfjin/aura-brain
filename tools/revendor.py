#!/usr/bin/env python3
"""revendor.py — copy a module from the canonical tree into _core/, then re-apply
its data-path edits.

The invariant in VENDORING.md is only worth having if it is **checkable**. This
script makes it mechanical: the path edits live in one table here, so re-vendoring
is a command rather than a memory. A hand re-apply is how the published copy
silently stops matching the code that produced the case studies.

Usage:
    python tools/revendor.py <canonical_dir> <module> [<module> ...]
    python tools/revendor.py --check <canonical_dir>      # verify _core is in sync
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CORE = REPO / "src" / "aura_brain" / "_core"

#: module -> [(exact text in the canonical file, replacement in the published copy)]
PATH_EDITS: dict[str, list[tuple[str, str]]] = {
    "brain.py": [
        (
            'STATE_DB = Path(os.environ.get("STATE_DB", str(Path.home() / ".hermes/profiles/steward/state.db")))',
            "STATE_DB = paths.STATE_DB  # YOUR corpus; unset -> ~/.aura-brain/dialogue.db",
        ),
        (
            'OUT = Path(os.environ.get("BRAIN_OUT", str(Path.home() / "lab-from-future/brain_concepts.json")))',
            "OUT = paths.BRAIN_OUT",
        ),
    ],
    "outcomes.py": [
        ('LIB = HERE / "patterns_library.jsonl"', "LIB = paths.PATTERNS_LIBRARY"),
        ('LEDGER = HERE / "outcomes.jsonl"', "LEDGER = paths.OUTCOMES_LEDGER"),
        (
            '_LAB_ROOT = _os.environ.get("LAB_ROOT", str(Path.home()))',
            '_LAB_ROOT = _os.environ.get("LAB_ROOT", str(paths.LAB_ROOT))',
        ),
        (
            '    Path.home() / "ai-lab/task2/review-verdicts.jsonl",\n'
            '    Path.home() / "ai-lab/streams/fourthquarter/review-verdicts.jsonl",\n',
            "    *paths.REVIEW_VERDICTS,\n",
        ),
        (
            '_FIRES = Path(_LAB_ROOT) / "ai-lab/streams/brain/move-fires.jsonl"',
            "_FIRES = paths.MOVE_FIRES",
        ),
    ],
    "recognition.py": [
        ('PATTERNS = HERE / "patterns_library.jsonl"', "PATTERNS = paths.PATTERNS_LIBRARY"),
        ('LIB_VEC = HERE / "concept_library.npy"', "LIB_VEC = paths.CONCEPT_LIBRARY_NPY"),
        ('LIB_META = HERE / "concept_library.json"', "LIB_META = paths.CONCEPT_LIBRARY_JSON"),
    ],
    "advice_domain.py": [
        ('MOVES = HERE / "patterns_library.jsonl"', "MOVES = paths.PATTERNS_LIBRARY")
    ],
    "wisdom.py": [
        ('FIRES = Path.home() / "ai-lab/streams/brain/move-fires.jsonl"', "FIRES = paths.MOVE_FIRES"),
        ('TRIALOGUE = Path.home() / "ai-lab/trialogue/trialogue.jsonl"', "TRIALOGUE = paths.TRIALOGUE"),
        ('sys.path.insert(0, str(Path.home() / "ai-lab/pce0"))', "sys.path.insert(0, str(paths.PCE_DIR))"),
    ],
    "ds_need.py": [
        (
            "The registry is the 120 run-gated patterns at ~/ai-lab/patterns_ds/harvested/; the",
            "The registry is your run-gated patterns at $AURA_PATTERNS_DS (default\n~/.aura-brain/patterns_ds/harvested/); the",
        ),
        ('PATTERNS_DIR = Path.home() / "ai-lab/patterns_ds/harvested"', "PATTERNS_DIR = paths.PATTERNS_DS"),
        ('R_PATTERNS_DIR = Path.home() / "ai-lab/patterns_r/harvested"', "R_PATTERNS_DIR = paths.PATTERNS_R"),
        ('QUEUE = HERE / "math_misses.jsonl"', 'QUEUE = paths.BRAIN_HOME / "math_misses.jsonl"'),
    ],
    "logic_lane.py": [
        ('REGISTRY = HERE / "logic_registry.jsonl"', "REGISTRY = paths.LOGIC_REGISTRY"),
        ('PATTERNS_DIR = Path.home() / "ai-lab/patterns_ds/harvested"', "PATTERNS_DIR = paths.PATTERNS_DS"),
        ('R_PATTERNS_DIR = Path.home() / "ai-lab/patterns_r/harvested"', "R_PATTERNS_DIR = paths.PATTERNS_R"),
        (
            'SYS_PATTERNS_DIR = Path.home() / "ai-lab/patterns_sysadmin/harvested"',
            "SYS_PATTERNS_DIR = paths.PATTERNS_SYS",
        ),
        ('QUEUE = HERE / "logic_misses.jsonl"', 'QUEUE = paths.BRAIN_HOME / "logic_misses.jsonl"'),
        ('lib = Path.home() / "aura-pattern-library" / src', "lib = paths.PATTERN_LIBRARY_ROOT / src"),
    ],
    "arbiter.py": [
        (
            'sys.path.insert(0, str(Path.home() / ".hermes/profiles/steward/plugins/steward_aura/pce"))',
            "sys.path.insert(0, str(paths.PCE_DIR))",
        )
    ],
    "whypass.py": [
        (
            'sys.path.insert(0, str(Path.home() / ".hermes/profiles/steward/plugins/steward_aura/pce"))',
            "sys.path.insert(0, str(paths.PCE_DIR))",
        )
    ],
    "distiller.py": [
        ('ENV = Path.home() / ".hermes/profiles/steward/.env"', "ENV = paths.ENV_FILE"),
        (
            'OUT = Path("/Users/s_dio/lab-from-future/reasoning_patterns.jsonl")',
            'OUT = paths.BRAIN_HOME / "reasoning_patterns.jsonl"',
        ),
    ],
    "mathbrain.py": [
        ('QUEUE = HERE / "math_misses.jsonl"', 'QUEUE = paths.BRAIN_HOME / "math_misses.jsonl"')
    ],
    "artifact_check.py": [
        ("HOME = Path.home()", "HOME = paths.LAB_ROOT"),
        (
            "    roots = [HOME, HOME / \"ai-lab\", HERE, HOME / \".claude\",\n",
            '    roots = [HOME, HOME / "streams", HERE, HOME / ".claude",\n',
        ),
        ('             HOME / "ai-lab/streams"]', '             HOME / "workspace"]'),
        (
            "# parsing bug. (Mid-path dot-dirs were always fine: `/Users/s_dio/.hermes/…`",
            "# parsing bug. (Mid-path dot-dirs were always fine: `/u/.hermes/…`",
        ),
        (
            "# Ver's briefs, the streams. The old root list (home, ~/ai-lab, the lab dir)",
            "# briefs, the streams. The old root list (just the home dir)",
        ),
        (
            "    # A bare `rails.py` is tried against cwd, $HOME, ~/ai-lab and the lab dir. A",
            "    # A bare `rails.py` is tried against cwd, $HOME and the deployment roots. A",
        ),
        (
            "    # file living anywhere else — say ~/.hermes/profiles/steward/plugins/",
            "    # file living anywhere else — say an undeclared plugin directory",
        ),
        (
            "    # (/home/au/…), which this floor already classes UNCHECKED rather than",
            "    # (an absolute path outside the roots), which this floor classes UNCHECKED rather than",
        ),
        (
            "    # 4b. ai-lab-relative resolves; off-node absolute is UNCHECKED, never MISSING",
            "    # 4b. deployment-relative resolves; off-node absolute is UNCHECKED, never MISSING",
        ),
        (
            'ev = scan("appended to streams/brain/move-fires.jsonl and synced /home/au/backups/state.db")',
            'ev = scan("appended to streams/brain/move-fires.jsonl and synced /tmp/backups/state.db")',
        ),
    ],
    "filter_tg.py": [
        ('        "/Users/s_dio/request/telegram26.06.26/result.json"', '        str(paths.BRAIN_HOME / "export.json")'),
        ('        "/Users/s_dio/lab-from-future/clean_dialogue.jsonl"', '        str(paths.BRAIN_HOME / "clean_dialogue.jsonl")'),
    ],
    "gate.py": [
        (
            'glob.glob(str(Path.home() / ".claude/projects/**/*.jsonl"), recursive=True)',
            'glob.glob(str(paths.LAB_ROOT / ".claude/projects/**/*.jsonl"), recursive=True)',
        )
    ],
    "generator.py": [
        ('ENV = Path.home() / ".hermes/profiles/steward/.env"', "ENV = paths.ENV_FILE"),
        (
            '_PERSONA_CORPUS = Path.home() / "ai-lab/trialogue/persona_corpus.jsonl"',
            '_PERSONA_CORPUS = paths.BRAIN_HOME / "persona_corpus.jsonl"',
        ),
        (
            'CORPUS = _PERSONA_CORPUS if _PERSONA_CORPUS.exists() else HERE / "Claude+Illia.txt"',
            'CORPUS = _PERSONA_CORPUS if _PERSONA_CORPUS.exists() else paths.BRAIN_HOME / "persona.txt"',
        ),
    ],
    "identity.py": [
        (
            'F = Path(sys.argv[1] if len(sys.argv) > 1 else "/Users/s_dio/lab-from-future/Claude+Illia.txt")',
            'F = Path(sys.argv[1]) if len(sys.argv) > 1 else paths.BRAIN_HOME / "persona.txt"',
        )
    ],
}

#: modules that need `import paths` injected after their sys.path setup
NEEDS_PATHS_IMPORT = set(PATH_EDITS) | {"brain.py"}

IMP = "\nsys.path.insert(0, str(Path(__file__).resolve().parent))\nimport paths  # published settings module (see VENDORING.md)\n"
IMP_ONLY = "\nimport paths  # published settings module (see VENDORING.md)\n"
HAS_ANCHOR = {
    "brain.py", "recognition.py", "distiller.py", "arbiter.py", "whypass.py",
    "wisdom.py", "logic_lane.py", "gate.py", "generator.py",
}


def apply_paths_import(text: str) -> str:
    """Inject `import paths` at MODULE level.

    Several modules (ds_need, logic_lane) carry `sys.path.insert(0, str(HERE))`
    *inside* functions as well. Anchoring on the first occurrence put the import
    in the middle of a function body, and the module stopped parsing — which is
    how this was caught. Only column-0 anchors count.
    """
    import re

    if "import paths" in text.split("\ndef ", 1)[0]:
        return text
    for pattern, insert in (
        ("sys.path.insert(0, str(HERE))", IMP_ONLY),
        ("sys.path.insert(0, str(Path(__file__).resolve().parent))", IMP_ONLY),
        ("HERE = Path(__file__).resolve().parent", IMP),
    ):
        m = re.search(rf"^{re.escape(pattern)}$", text, re.M)
        if m:
            return text[: m.end()] + insert + text[m.end() :]
    return text


def revendor(canonical: Path, module: str) -> None:
    # accept "arbiter" or "arbiter.py" — the edit table is keyed by filename, and
    # passing a bare stem silently applied ZERO edits the first time this ran.
    stem = module[:-3] if module.endswith(".py") else module
    src = canonical / f"{stem}.py"
    text = src.read_text(encoding="utf-8")
    applied = 0
    for old, new in PATH_EDITS.get(f"{stem}.py", []):
        if new is None:
            continue
        if text.count(old) != 1:
            raise SystemExit(f"{module}.py: {text.count(old)} matches for {old[:60]!r}")
        text = text.replace(old, new)
        applied += 1
    text = apply_paths_import(text)
    (CORE / f"{stem}.py").write_text(text, encoding="utf-8")
    print(f"  re-vendored {stem}.py ({applied} path edit(s))")
    leftover = [o for o, n in PATH_EDITS.get(f"{stem}.py", []) if n is not None and o in text]
    if leftover:
        raise SystemExit(f"{stem}.py: edit did not apply: {leftover[0][:60]!r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("canonical", type=Path)
    ap.add_argument("modules", nargs="*")
    ap.add_argument("--check", action="store_true", help="only report drift")
    args = ap.parse_args()

    if args.check:
        drifted = []
        for f in sorted(CORE.glob("*.py")):
            if f.stem == "paths":
                continue
            src = args.canonical / f.name
            if not src.exists():
                drifted.append((f.name, "not in canonical tree"))
                continue
            for old, new in PATH_EDITS.get(f.stem, []):
                if new is not None and src.read_text(encoding="utf-8").count(old) != 1:
                    drifted.append((f.name, f"anchor missing: {old[:50]!r}"))
        if drifted:
            print("DRIFT:")
            for name, why in drifted:
                print(f"  {name}: {why}")
            return 1
        print(f"in sync with {args.canonical} ({len(list(CORE.glob('*.py'))) - 1} modules)")
        return 0

    for m in args.modules:
        revendor(args.canonical, m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
