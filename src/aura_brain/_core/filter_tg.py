#!/usr/bin/env python3
"""Filter a Telegram export down to real dialogue — strip the tool/status noise.

This is step 0 of the dialogue-reality engine: the substrate is the *conversation*,
not telemetry. We keep human + Steward prose, drop the tool traces, status pings,
and approval spam that aren't reasoning.

Usage: python3 filter_tg.py <result.json> [out.jsonl]
"""
import json
import re
import sys
import paths  # published settings module (see VENDORING.md)

# Lines that are tool-calls / status / noise, not dialogue.
_NOISE_PREFIX = ("💻", "✍️", "🔧", "🔍", "⚙️", "🐍", "💾", "📊", "⏳", "✅", "❌", "🔄",
                 "✨", "◆", "✦", "⚡", "⏱️", "🔁")
_NOISE_SUBSTR = (
    "still working", "iteration ", "approved once by human", "approved permanently",
    "approved by human", "interrupting current task", "self-improvement review",
    "terminal:", "write_file:", "read_file", "execute_code", "web_search", "patch:",
    "memory updated", "🤖", "tool:", "💭 reasoning",
    # telegram-bot status/error/reset boilerplate (was leaking into Steward's voice)
    "session reset", "starting fresh", "encountered an error", "no api key was found",
    "ollama_api_key", "is set in config.yaml", "switch to a different provider",
    "hermes config set", "hermes plugins install", "unknown command",
    "tokens (default", "context_length", "model provider is rate", "rate-limiting requests",
    "context: 256k", "provider: openrouter", "provider 'ollama",
)


# whole-MESSAGE system dumps (cron output, sync logs, preflight) — not moves
_TURN_NOISE = ("cronjob response", "job_id:", "auto-sync", "preflight compression",
               "to stop or manage this job", "started ===", "this may take a moment")


def is_noise_turn(text: str) -> bool:
    """True if the whole message is a system/cron/sync output dump, not dialogue."""
    low = text.lower()
    return any(t in low for t in _TURN_NOISE)


def _text_of(m):
    t = m.get("text")
    if isinstance(t, str):
        return t
    if isinstance(t, list):
        return "".join(x if isinstance(x, str) else x.get("text", "") for x in t)
    return ""


def _is_noise_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if s.startswith(_NOISE_PREFIX):
        return True
    low = s.lower()
    return any(tok in low for tok in _NOISE_SUBSTR)


def clean_message(text: str) -> str:
    kept = [ln for ln in text.splitlines() if not _is_noise_line(ln)]
    out = "\n".join(kept).strip()
    return out


def filter_export(path: str):
    d = json.load(open(path, encoding="utf-8"))
    raw = [m for m in d.get("messages", []) if m.get("type") == "message"]
    clean = []
    for m in raw:
        txt = clean_message(_text_of(m))
        # keep only substantive turns (≥ 20 real chars)
        if len(txt) >= 20:
            clean.append({
                "date": m.get("date", ""),
                "sender": m.get("from", "?"),
                "text": txt,
            })
    return raw, clean


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else \
        str(paths.BRAIN_HOME / "export.json")
    out = sys.argv[2] if len(sys.argv) > 2 else \
        str(paths.BRAIN_HOME / "clean_dialogue.jsonl")
    raw, clean = filter_export(src)
    with open(out, "w", encoding="utf-8") as f:
        for turn in clean:
            f.write(json.dumps(turn, ensure_ascii=False) + "\n")
    from collections import Counter
    print(f"raw messages : {len(raw)}")
    print(f"clean turns  : {len(clean)}  ({len(raw)-len(clean)} dropped as noise)")
    print(f"by sender    : {dict(Counter(t['sender'] for t in clean))}")
    print(f"written      : {out}")
