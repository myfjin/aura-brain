"""rails.py — action-side rails (fail-open stub).

This is a temporary stub: the full implementation lives in the canonical tree.
The stub exposes the same API so brain_mcp.py imports and runs; all rails are
disabled (fail-open) until the real module is vendored in.
"""


def detect_failure_loop(recent_actions: list | None) -> tuple[bool, str]:
    """R3 rail: detect repeating the same failing action. Stub: never fires."""
    return False, ""


def detect_unverified_claim(text: str) -> tuple[bool, str]:
    """A6 rail: claim words without evidence. Stub: never fires."""
    return False, ""
