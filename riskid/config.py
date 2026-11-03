"""Run-time settings for the workbench (SPEC.md section 9).

Until the Settings module's list of people arrives (PLAN.md round 14), the
person recorded on each change is ``RISKID_ACTOR`` if set, else the name of
the operating-system account running the workbench.
"""

from __future__ import annotations

import getpass
import os

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def default_actor() -> str:
    """The person recorded on each change made through the screens."""
    return os.environ.get("RISKID_ACTOR", "").strip() or getpass.getuser()
