"""Round 2 golden test (PLAN.md section 4, round 2): 91/91 match.

The golden file ``tests/reference/golden_register.json`` holds, for each of
the 91 library lines, the inherent score, residual score, both bands and the
materiality exactly as the book's reference ``build_register.py`` ``load()``
computes them. This test recomputes every line from ``riskid.rules`` and the
library and requires the recomputation to match the golden file line for line.

The golden file was produced by importing the reference script in a throwaway
environment (it is not committed, only the golden file is; see the round 2
note in ``docs/DECISIONS.md``).
"""

import json
from pathlib import Path

from riskid.importers import load_library
from riskid.rules import band, material, score

GOLDEN = Path(__file__).parent / "reference" / "golden_register.json"
# The fields the reference implementation computes and the golden test checks.
CHECKED = ("inherent", "residual", "inherent_band", "residual_band", "material")


def _load_golden() -> dict:
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    return {line["id"]: line for line in data["lines"]}


def test_golden_file_covers_all_91_lines():
    golden = _load_golden()
    assert len(golden) == 91
    for entry in golden.values():
        assert set(entry) == {"id"} | set(CHECKED), entry


def test_golden_matches_all_91_lines():
    golden = _load_golden()
    library = load_library()
    assert len(library) == 91, "the library must hold exactly 91 lines"

    mismatches = []
    for line in library:
        inherent = score(line.L, line.I)
        residual = score(line.rL, line.rI)
        expected = golden.get(line.id)
        assert expected is not None, f"no golden entry for {line.id}"
        recomputed = {
            "inherent": inherent,
            "residual": residual,
            "inherent_band": band(inherent),
            "residual_band": band(residual),
            "material": material(inherent, line.I),
        }
        for key in CHECKED:
            if recomputed[key] != expected[key]:
                mismatches.append(
                    f"{line.id} {key}: rules={recomputed[key]!r} "
                    f"golden={expected[key]!r}"
                )
    assert not mismatches, f"{len(mismatches)} golden mismatches: {mismatches[:10]}"
