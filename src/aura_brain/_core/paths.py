"""Every path the brain touches, in one place, env-overridable.

**Nothing here points at anyone's private data.** The default root is
``$AURA_BRAIN_HOME`` (falling back to ``~/.aura-brain``), which is empty on a
fresh checkout — so each lane fails **open with a loud warning** rather than
guessing at a path that happens to exist on the author's machine.

That is deliberate. The brain is an *engine*; the corpus that makes it measure
is yours. See ``CALIBRATION.md`` and the ``Connecting your own data`` wiki page
for the shape each file must have.

Override any single path with its own environment variable, or move the whole
set at once with ``AURA_BRAIN_HOME``.
"""

from __future__ import annotations

import os
from pathlib import Path


def _env_path(name: str, default: Path) -> Path:
    """Return $name as a Path if set and non-empty, else ``default``."""
    raw = os.environ.get(name, "")
    return Path(raw).expanduser() if raw else default


# ── the root everything else hangs off ──────────────────────────────────────
BRAIN_HOME: Path = _env_path("AURA_BRAIN_HOME", Path.home() / ".aura-brain")

# ── the reasoning corpus YOU bring (sqlite) ─────────────────────────────────
# Table `messages(id, session_id, role, content, timestamp)`.
# Unset/unreadable → dialogue recall is off; every other lane still runs.
STATE_DB: Path = _env_path("STATE_DB", BRAIN_HOME / "dialogue.db")

# ── moves library + ledgers (append-only JSONL) ─────────────────────────────
PATTERNS_LIBRARY: Path = _env_path("AURA_PATTERNS_LIBRARY", BRAIN_HOME / "patterns_library.jsonl")
CONCEPT_LIBRARY_NPY: Path = _env_path(
    "AURA_CONCEPT_LIBRARY_NPY", BRAIN_HOME / "concept_library.npy"
)
CONCEPT_LIBRARY_JSON: Path = _env_path(
    "AURA_CONCEPT_LIBRARY_JSON", BRAIN_HOME / "concept_library.json"
)
OUTCOMES_LEDGER: Path = _env_path("OUTCOMES_LEDGER", BRAIN_HOME / "outcomes.jsonl")
LOGIC_REGISTRY: Path = _env_path("AURA_LOGIC_REGISTRY", BRAIN_HOME / "logic_registry.jsonl")
# The registry with each pattern re-checked against its oracles. The lanes read it only
# while it is at least as new as LOGIC_REGISTRY and covers all its ids; otherwise they
# read LOGIC_REGISTRY with nothing marked oracle-backed (logic_lane.rechecked_rows).
LOGIC_REGISTRY_CANONICAL: Path = _env_path(
    "AURA_LOGIC_REGISTRY_CANONICAL", BRAIN_HOME / "logic_registry_canonical.jsonl"
)

# ── the engine's own derived files ──────────────────────────────────────────
DATA: Path = _env_path("AURA_BRAIN_DATA", BRAIN_HOME)
REASONING_PATTERNS: Path = DATA / "reasoning_patterns.jsonl"
GRAPH: Path = DATA / "graph.json"
MATH_MISSES: Path = DATA / "math_misses.jsonl"
CLEAN_DIALOGUE: Path = DATA / "clean_dialogue.jsonl"

# ── streams / records the lanes read ────────────────────────────────────────
MOVE_FIRES: Path = _env_path("AURA_MOVE_FIRES", BRAIN_HOME / "move-fires.jsonl")
# review-verdict streams the auto-fire hooks write to (grading flips `graded` here)
REVIEW_VERDICTS: tuple[Path, ...] = (
    _env_path("AURA_REVIEW_VERDICTS_A", BRAIN_HOME / "review-verdicts.jsonl"),
    _env_path("AURA_REVIEW_VERDICTS_B", BRAIN_HOME / "streams" / "review-verdicts.jsonl"),
)
TRIALOGUE: Path = _env_path("AURA_TRIALOGUE", BRAIN_HOME / "trialogue.jsonl")
# The root the artifact floor searches when a claim names a file, and the per-agent streams.
AI_LAB: Path = _env_path("AURA_AI_LAB", BRAIN_HOME)
STREAMS: Path = _env_path("AURA_STREAMS", BRAIN_HOME / "streams")
VERDICTS_CLAUDE: Path = _env_path(
    "AURA_VERDICTS_CLAUDE", STREAMS / "claude" / "review-verdicts.jsonl"
)
VERDICTS_STEWARD: Path = _env_path(
    "AURA_VERDICTS_STEWARD", STREAMS / "steward" / "review-verdicts.jsonl"
)

# ── consult-lane registries (code you harvested, one dir per sphere) ────────
PATTERNS_DS: Path = _env_path("AURA_PATTERNS_DS", BRAIN_HOME / "patterns_ds" / "harvested")
PATTERNS_R: Path = _env_path("AURA_PATTERNS_R", BRAIN_HOME / "patterns_r" / "harvested")
PATTERNS_SYS: Path = _env_path("AURA_PATTERNS_SYS", BRAIN_HOME / "patterns_sysadmin" / "harvested")
PATTERN_LIBRARY_ROOT: Path = _env_path("AURA_PATTERN_LIBRARY", BRAIN_HOME / "pattern-library")

# ── optional helpers (absent is fine — those call sites fail open) ───────────
PCE_DIR: Path = _env_path("AURA_PCE_DIR", BRAIN_HOME / "pce")
ENV_FILE: Path = _env_path("AURA_ENV_FILE", BRAIN_HOME / ".env")
BRAIN_OUT: Path = _env_path("BRAIN_OUT", BRAIN_HOME / "brain_concepts.json")
LAB_ROOT: Path = _env_path("LAB_ROOT", BRAIN_HOME)

# ── offline corpora (the gate/generator path only — never the advice loop) ───
PERSONA_TXT: Path = _env_path("AURA_PERSONA_TXT", BRAIN_HOME / "persona.txt")
PERSONA_CORPUS: Path = _env_path("AURA_PERSONA_CORPUS", BRAIN_HOME / "persona_corpus.jsonl")
# Retired: the persona readers raise instead of reading a chat export (persona work, if
# revived, reads the trialogue). None, so a reader can never fall back to a default path.
TG_EXPORT: Path | None = None
TG_RAW_EXPORT: Path = _env_path("AURA_TG_RAW_EXPORT", BRAIN_HOME / "tgexport" / "raw.json")
MOVE_SPACES: Path = _env_path("AURA_MOVE_SPACES", BRAIN_HOME / "move-spaces")

# ── routes into another tool's store: no default; read them through need() ───
_claude_projects = os.environ.get("AURA_CLAUDE_PROJECTS", "")
CLAUDE_PROJECTS: Path | None = Path(_claude_projects).expanduser() if _claude_projects else None


def need(attr: str) -> Path:
    """The route ``attr``, or a RuntimeError naming it when it is not set."""
    p = globals().get(attr)
    if not isinstance(p, Path):
        raise RuntimeError(f"paths: {attr} is not set; set it in the environment")
    return p


def secret(name: str) -> str:
    """``$name`` from the environment, else from ``ENV_FILE`` if it exists, else ``""``."""
    v = os.environ.get(name, "")
    if v or not ENV_FILE.is_file():
        return v
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip().removeprefix("export ").strip()
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def describe() -> str:
    """One-line summary for logs and bug reports. Never includes credentials."""
    return f"AURA_BRAIN_HOME={BRAIN_HOME} (STATE_DB={STATE_DB})"
