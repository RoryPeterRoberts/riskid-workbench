"""The store's one timestamp form and the replay cutoff (SPEC.md section 4, Event).

Every event timestamp is stored as UTC to the second, ``2026-06-30T10:00:00Z``,
so the event table can be compared and ordered as text. Moved out of
``riskid/store.py`` in round 4 to keep that module under the 400-line limit
(PLAN.md section 1, rule 5); the behaviour is the one round 3 settled.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone

# A bare ISO date, e.g. 2026-06-30. In a replay cutoff it means the whole of
# that UTC day; stored as the day's midnight.
BARE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def to_utc(value):
    """Coerce a date, datetime, ISO string (or ``None``) to an aware UTC time.

    A bare date is that day's midnight; a naive datetime is taken as UTC; a
    datetime with another offset is converted to UTC; a string is parsed as
    ISO 8601, where a bare date is midnight and a trailing ``Z`` means UTC.
    ``None`` (or an empty string) is the current UTC time.
    """
    if value is None or value == "":
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    else:
        text = str(value).strip()
        if BARE_DATE.match(text):
            d = date.fromisoformat(text)
            dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        else:
            parsed = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
            dt = datetime.fromisoformat(parsed)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def stamp(value) -> str:
    """The one timestamp form the store uses: UTC to the second, ``...Z``."""
    return to_utc(value).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def now() -> str:
    """The current UTC time in the store's one timestamp form."""
    return stamp(None)


def replay_cutoff(when) -> str:
    """The last timestamp ``replay(when)`` includes.

    A bare date means the whole of that UTC day (its final second); a datetime
    means everything up to that instant.
    """
    if isinstance(when, datetime):
        return stamp(when)
    if isinstance(when, date):
        return stamp(f"{when.isoformat()}T23:59:59")
    text = str(when).strip()
    if BARE_DATE.match(text):
        return stamp(f"{text}T23:59:59")
    return stamp(when)
