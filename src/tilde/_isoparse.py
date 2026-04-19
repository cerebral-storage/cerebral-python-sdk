"""ISO 8601 datetime parsing compatible with Python 3.10.

Python 3.11 relaxed ``datetime.fromisoformat`` to accept most RFC 3339 /
ISO 8601 inputs.  3.10 is much stricter: it rejects the trailing ``Z`` suffix
and accepts exactly 0, 3, or 6 digits of fractional seconds.  Real Tilde API
responses use both ``Z`` and sub-microsecond precision (Go's ``RFC3339Nano``
emits up to 9 digits), so we normalize before parsing.
"""

from __future__ import annotations

import re
from datetime import datetime

_FRAC_RE = re.compile(r"\.(\d+)")


def parse_iso_datetime(value: str) -> datetime:
    """Parse an ISO 8601 / RFC 3339 timestamp, normalizing for Python 3.10.

    Accepts the same inputs as 3.11's ``fromisoformat`` plus the ``Z`` UTC
    suffix and arbitrary fractional-second precision.
    """
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    value = _FRAC_RE.sub(_normalize_fractional, value, count=1)
    return datetime.fromisoformat(value)


def _normalize_fractional(match: re.Match[str]) -> str:
    digits = match.group(1)
    if len(digits) in (3, 6):
        return match.group(0)
    # Pad short fractions and truncate nanosecond precision to microseconds.
    return "." + digits.ljust(6, "0")[:6]


def parse_optional(value: str | None) -> datetime | None:
    """Parse an optional ISO 8601 string, returning ``None`` for ``None`` input."""
    if value is None:
        return None
    return parse_iso_datetime(value)
