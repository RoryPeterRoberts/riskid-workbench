"""Every package and data file the workbench needs is declared for an installed wheel.

A package directory missing from ``pyproject.toml`` works in an editable
install and breaks a ``pipx`` one (round 9 shipped without riskid.documents).
"""

import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_every_package_is_listed_in_pyproject():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    listed = set(config["tool"]["setuptools"]["packages"])
    found = {".".join(p.parent.relative_to(ROOT).parts) for p in (ROOT / "riskid").rglob("__init__.py")}
    assert found == listed, f"in the tree, not listed: {found - listed}; listed, not in the tree: {listed - found}"


def test_data_templates_and_static_files_are_declared():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    data = config["tool"]["setuptools"]["package-data"]
    assert "data/*" in data["riskid"]
    assert {"templates/*", "static/*"} <= set(data["riskid.web"])
