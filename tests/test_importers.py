"""Round 1 tests (PLAN.md section 4, round 1): the data packs and the model.

These are the tests the plan lists for round 1, adjusted by the round 1
assignment: the taxonomy has 42 data rows (the plan's "43" counts the header
row), and the register already counts data rows (91 lines, 23 columns).
"""

import csv
from pathlib import Path

from riskid.importers import (
    DATA_DIR,
    load_indicators,
    load_library,
    load_scales,
    load_taxonomy,
    load_version,
)
from riskid.model import LibraryLine, TaxonomyLine

# The register columns of risks.tsv, in order (SPEC.md section 4 LibraryLine).
LIBRARY_COLUMNS = [
    "id", "l1", "l2", "title", "description", "lifecycle", "role", "harmed",
    "exposure", "event", "L", "I", "dim", "V", "S", "dq", "controls", "rL",
    "rI", "owner", "kri", "reg", "sources",
]

# The five consequence dimensions (SPEC.md section 4 Assessment.impact).
DIMENSIONS = ["FIN", "REG", "REP", "IND", "OPS"]


def _read_register_header() -> list[str]:
    with (DATA_DIR / "register.tsv").open(newline="", encoding="utf-8") as fh:
        return next(csv.reader(fh, delimiter="\t"))


def test_library_has_91_lines_with_23_columns():
    library = load_library()
    assert len(library) == 91
    for line in library:
        assert isinstance(line, LibraryLine)
        assert set(line.to_dict().keys()) == set(LIBRARY_COLUMNS)
    # The TSV itself carries 23 columns plus a header.
    header = _read_register_header()
    assert header == LIBRARY_COLUMNS
    assert len(header) == 23


def test_library_scores_are_integers():
    for line in load_library():
        for col in ("L", "I", "V", "S", "rL", "rI"):
            assert isinstance(getattr(line, col), int), (line.id, col)
        # Scores sit on the 1-5 scale.
        assert 1 <= line.L <= 5 and 1 <= line.I <= 5, line.id


def test_taxonomy_has_42_entries_across_9_categories():
    taxonomy = load_taxonomy()
    assert len(taxonomy) == 42, "taxonomy.tsv has 42 data rows (not 43)"
    for row in taxonomy:
        assert isinstance(row, TaxonomyLine)
    categories = {row.l1_code for row in taxonomy}
    assert len(categories) == 9


def test_every_library_line_taxonomy_pair_exists():
    taxonomy = {(row.l1_code, row.l2_code) for row in load_taxonomy()}
    for line in load_library():
        assert (line.l1, line.l2) in taxonomy, (line.id, line.l1, line.l2)


def test_scales_have_five_levels_on_five_dimensions_plus_others():
    scales = load_scales()
    for dim in DIMENSIONS:
        levels = scales[dim]["levels"]
        assert len(levels) == 5, dim
        assert [lvl["score"] for lvl in levels] == [1, 2, 3, 4, 5], dim
        for lvl in levels:
            assert lvl["rating"] and lvl["description"], dim
    for name in ("likelihood", "vulnerability", "speed"):
        assert len(scales[name]["levels"]) == 5, name


def test_data_quality_has_four_ratings():
    levels = load_scales()["data_quality"]["levels"]
    assert [lvl["rating"] for lvl in levels] == [
        "High", "Medium", "Low", "Very Low",
    ]
    assert all(lvl["basis"] for lvl in levels)


def test_every_indicator_names_a_real_register_line():
    ids = {line.id for line in load_library()}
    indicators = load_indicators()
    assert indicators, "no indicator presets loaded"
    for preset in indicators:
        if preset.get("any_line"):
            # The book's incident preset is line-agnostic ("Any line").
            continue
        assert preset["lines"], preset["name"]
        assert any(lid in ids for lid in preset["lines"]), preset["name"]


def test_data_pack_version_loads():
    version = load_version()
    assert version, "the data-pack VERSION file is empty"
