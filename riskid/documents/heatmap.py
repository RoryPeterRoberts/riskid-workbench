"""Heat maps (SPEC.md section 7): the same drawing as the book's reference register script.

A 5 by 5 grid of likelihood (12-month horizon) against impact (the dominant
dimension), each cell coloured by the band of its score, the line IDs written
in the cell three to a row and the score in its corner.
"""

from __future__ import annotations

import io

from riskid import importers, rules

COLOURS = {"Low": "#c6e0b4", "Moderate": "#ffe699", "High": "#f4b183", "Critical": "#ff7c80"}


def placements(rows, key_l: str, key_i: str) -> dict:
    """``{(likelihood, impact): [line IDs]}`` for the rows that have both scores."""
    cells: dict = {}
    for row in rows:
        l, i = row.get(key_l), row.get(key_i)
        if l and i:
            cells.setdefault((l, i), []).append(row["id"])
    return cells


def render(rows, key_l: str, key_i: str, title: str) -> bytes:
    """Draw the heat map as a PNG and return its bytes."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    scales = importers.load_scales()
    l_labels = [f"{x['score']} {x['rating']}" for x in scales["likelihood"]["levels"]]
    i_labels = [f"{x['score']} {x['rating']}" for x in scales["FIN"]["levels"]]
    cells = placements(rows, key_l, key_i)
    fig, ax = plt.subplots(figsize=(9, 7.2))
    for i in range(5):
        for l in range(5):
            s = (l + 1) * (i + 1)
            ax.add_patch(plt.Rectangle((l, i), 1, 1, facecolor=COLOURS[rules.band(s)],
                                       edgecolor="white", linewidth=2))
            ids = cells.get((l + 1, i + 1), [])
            txt = "\n".join(", ".join(ids[k:k + 3]) for k in range(0, len(ids), 3))
            ax.text(l + 0.5, i + 0.5, txt, ha="center", va="center", fontsize=6.2, family="DejaVu Sans")
            ax.text(l + 0.04, i + 0.92, str(s), fontsize=7, color="#555", va="top")
    ax.set_xlim(0, 5)
    ax.set_ylim(0, 5)
    ax.set_xticks([x + 0.5 for x in range(5)])
    ax.set_yticks([y + 0.5 for y in range(5)])
    ax.set_xticklabels(l_labels, fontsize=8)
    ax.set_yticklabels(i_labels, fontsize=8)
    ax.set_xlabel("Likelihood (12-month horizon)")
    ax.set_ylabel("Impact (dominant dimension)")
    ax.set_title(title, fontsize=11, family="DejaVu Serif")
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.tight_layout()
    out = io.BytesIO()
    fig.savefig(out, format="png", dpi=200)
    plt.close(fig)
    return out.getvalue()
