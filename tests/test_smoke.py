"""Round 0 smoke tests (PLAN.md section 4, round 0).

Covers the three done-when checks for the scaffold: importing the package
works, the root route returns the title, and ``riskid --help`` lists the
three commands.
"""

import os
import shutil
import subprocess
import sys

import riskid
from fastapi.testclient import TestClient

from riskid.app import TITLE, app

# The workbench answers only to loopback Host headers (SPEC.md section 10), so
# the client uses the address `riskid serve` listens on.
client = TestClient(app, base_url="http://127.0.0.1:8765")


def _find_riskid_script():
    """Locate the installed ``riskid`` console script.

    Prefer the script next to the running interpreter (the case when pytest
    runs inside the project virtualenv); fall back to ``PATH`` when the
    virtualenv has been activated and the script is on ``PATH``.
    """
    candidate = os.path.join(os.path.dirname(sys.executable), "riskid")
    if os.path.exists(candidate):
        return candidate
    return shutil.which("riskid")


def test_import_riskid():
    # Importing the package works and exposes its version.
    assert riskid.__version__
    assert hasattr(riskid, "app") or hasattr(riskid, "__version__")


def test_root_returns_title():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["title"] == "RiskID Workbench"
    assert TITLE == "RiskID Workbench"


def test_cli_help_lists_commands():
    binary = _find_riskid_script()
    assert binary, "the riskid console script was not found"
    out = subprocess.run([binary, "--help"], capture_output=True, text=True)
    assert out.returncode == 0
    for command in ("init", "serve", "check"):
        assert command in out.stdout, f"{command!r} not listed by riskid --help"
