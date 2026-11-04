"""PLAN.md round 14: the shell test that installs with pipx into a clean virtualenv.

It needs network access and a few minutes, so it runs only with
``RISKID_SHELL_TESTS=1``; ``tests/shell/pipx_install.sh`` can also be run by hand.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent / "shell" / "pipx_install.sh"


@pytest.mark.skipif(os.environ.get("RISKID_SHELL_TESTS") != "1",
                    reason="set RISKID_SHELL_TESTS=1 to install with pipx in a clean virtualenv")
def test_pipx_install_and_serve_in_a_clean_virtualenv():
    assert shutil.which("pipx"), "pipx is not installed"
    result = subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True, timeout=1200)
    assert result.returncode == 0, result.stdout + result.stderr
