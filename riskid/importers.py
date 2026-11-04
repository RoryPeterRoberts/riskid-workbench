"""Data-pack loaders (PLAN.md section 4, round 1).

Round 1 ships the data packs in ``riskid/data/`` and the functions that read
them. The register and taxonomy are copied verbatim from the book (PLAN.md
section 2) and are read here, never retyped; ``scales.json`` and
``indicators.json`` are typed from ``docs/SPEC.md`` section 5 and the tables
in ``docs/BOOK_TABLES.md`` (chapter 9 scales, chapter 13 indicator presets).

Every loader resolves its file relative to this module so the workbench works
whether installed with ``pipx`` or run from the source tree.
"""

import csv
import json
from pathlib import Path

from riskid.model import LibraryLine, TaxonomyLine

# The data pack lives next to this module (SPEC.md section 9 repository layout).
DATA_DIR = Path(__file__).parent / "data"

# register.tsv columns that hold a 1-5 score (SPEC.md section 4 LibraryLine).
_INT_COLUMNS = ("L", "I", "V", "S", "rL", "rI")


def _read_tsv(path: Path) -> tuple[list[str], list[list[str]]]:
    """Return the header row and the data rows of a TSV file."""
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh, delimiter="\t"))
    header, data = rows[0], rows[1:]
    # A trailing blank line must not become a row.
    data = [r for r in data if any(cell.strip() for cell in r)]
    return header, data


def load_library() -> list[LibraryLine]:
    """Load the 91-line register (Appendix A) from ``register.tsv``.

    The 23 register columns map one-to-one onto :class:`LibraryLine`; the six
    1-5 score columns are kept as ints, every other column as text.
    """
    header, data = _read_tsv(DATA_DIR / "register.tsv")
    lines: list[LibraryLine] = []
    for row in data:
        record = dict(zip(header, row))
        values = {col: record[col] for col in header}
        for col in _INT_COLUMNS:
            values[col] = int(values[col])
        lines.append(LibraryLine.from_dict(values))
    return lines


def load_taxonomy() -> list[TaxonomyLine]:
    """Load the taxonomy (42 data rows across 9 L1 categories) as entries.

    ``taxonomy.tsv`` has a header plus 42 data rows; the 43rd physical line in
    the source counts, the header does not, so this returns 42 entries
    (the plan's "43 lines" wording is corrected in the round 1 assignment).
    """
    header, data = _read_tsv(DATA_DIR / "taxonomy.tsv")
    return [
        TaxonomyLine.from_dict(dict(zip(header, row)))
        for row in data
    ]


def load_scales() -> dict:
    """Load the chapter 9 scales: the five impact dimensions (5 levels each)
    plus likelihood, vulnerability, speed (5 levels) and data quality
    (4 ratings)."""
    with (DATA_DIR / "scales.json").open(encoding="utf-8") as fh:
        return json.load(fh)


def load_indicators() -> list[dict]:
    """Load the chapter 13 indicator presets.

    Each preset names the register lines a movement on it can mean, what a
    movement can mean, and who reads it. The incident preset names ``Any
    line`` in the book, so it carries no specific lines (``any_line: true``).
    """
    with (DATA_DIR / "indicators.json").open(encoding="utf-8") as fh:
        return json.load(fh)["indicators"]


def load_version() -> str:
    """Return the data-pack version string (SPEC.md section 4 DataPack)."""
    return (DATA_DIR / "VERSION").read_text(encoding="utf-8").strip()


def load_swift() -> list[dict]:
    """Load the 23 SWIFT prompts of B.4 with their register lines (``swift.json``)."""
    import json

    data = json.loads((DATA_DIR / "swift.json").read_text(encoding="utf-8"))
    return data["prompts"]


def load_flags() -> dict:
    """Load the library's rule flags (``flags.json``): which lines carry which flag."""
    import json

    return json.loads((DATA_DIR / "flags.json").read_text(encoding="utf-8"))


def load_calendar() -> list[dict]:
    """The role-and-date calendar of chapter 15 (``calendar.json``)."""
    import json

    return json.loads((DATA_DIR / "calendar.json").read_text(encoding="utf-8"))["entries"]


def load_checklist() -> list[dict]:
    """The 18 steps of the B.8 quarterly checklist (``checklist.json``)."""
    import json

    return json.loads((DATA_DIR / "checklist.json").read_text(encoding="utf-8"))["steps"]


def load_contract_clauses() -> list[dict]:
    """The 17 clauses of the B.9 contract checklist with their register lines (``contracts.json``)."""
    import json
    return json.loads((DATA_DIR / "contracts.json").read_text(encoding="utf-8"))["clauses"]
