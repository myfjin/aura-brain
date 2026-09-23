"""Test bootstrap: point the core at the SYNTHETIC fixtures before it is imported.

The core binds its path constants at import time — that is the documented
contract (set ``AURA_BRAIN_HOME``, then import). So the fixtures are laid out and
the variable is set here, at collection time, before any test imports the loop.

Nothing in here touches a real deployment. If ``AURA_BRAIN_HOME`` is already set
in the environment, this file overrides it — a test that silently read the
developer's own corpus would be worse than no test.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"

#: fixture file -> the name the code expects under $AURA_BRAIN_HOME
LAYOUT = {
    "synthetic_patterns_library.jsonl": "patterns_library.jsonl",
    "synthetic_outcomes.jsonl": "outcomes.jsonl",
    "synthetic_move_fires.jsonl": "move-fires.jsonl",
    "synthetic_dialogue.db": "dialogue.db",
}

BRAIN_HOME = Path(tempfile.mkdtemp(prefix="aura-brain-fixtures-"))

for _src, _dst in LAYOUT.items():
    shutil.copy(FIXTURES / _src, BRAIN_HOME / _dst)

# empty registries: present, but with nothing in them. That is the honest default
# for a fresh checkout, and it is the case that must fail OPEN rather than raise.
for _d in ("patterns_ds/harvested", "patterns_r/harvested", "patterns_sysadmin/harvested"):
    (BRAIN_HOME / _d).mkdir(parents=True, exist_ok=True)

os.environ["AURA_BRAIN_HOME"] = str(BRAIN_HOME)
