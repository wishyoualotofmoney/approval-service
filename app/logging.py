from __future__ import annotations

import logging
import re
from typing import List, Pattern

# Patterns for values that must never reach logs (defense in depth). The service
# never stores these, but user-supplied free text or upstream frames might carry
# them, so we scrub anything that looks like a secret before it is emitted.
_REDACTIONS: List[tuple[Pattern[str], str]] = [
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+"), "Bearer [REDACTED]"),
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "[REDACTED_EMAIL]"),
    (re.compile(r"https?://[^\s\"']+"), "[REDACTED_URL]"),
    (re.compile(r"(?i)(token|secret|password|api[_-]?key)\"?\s*[:=]\s*\"?[^\s\",}]+"),
     r"\1=[REDACTED]"),
]


def redact(text: str) -> str:
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


class RedactionFilter(logging.Filter):
    """Scrubs secret-looking substrings from every log record's message."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = redact(message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    handler.addFilter(RedactionFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
