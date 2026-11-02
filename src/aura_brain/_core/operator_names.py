"""The operator's name as the data on disk spells it.

Every value here is a contract with data that already exists: the speaker value other
systems write into the shared records, the label the persona tools use, and the names of
two data files. Code reads them from here and never spells them itself, so the public
copy of this repo differs from the private one in this file only (standard §7b; the
publish step rewrites it). Renaming a value here without renaming the data breaks reads.
"""
from __future__ import annotations

SPEAKER = "operator"                 # `speaker` in the trialogue and state.db-derived events
CHARACTER = "Operator"               # the persona key (gate.MOVES, load_moves)
LABEL = "OPERATOR"                   # identity.label()'s verdict for an operator turn
MOVES_STEM = "operator_moves"        # data/<stem>.npy + .json, built by experiments/personas
PERSONA_TXT_NAME = "Claude+Operator.txt"   # the legacy two-voice transcript in data/
