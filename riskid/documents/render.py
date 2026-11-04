"""HTML for the documents, and PDF from it with WeasyPrint (SPEC.md section 9)."""

from __future__ import annotations

from pathlib import Path

import jinja2

ENV = jinja2.Environment(loader=jinja2.FileSystemLoader(Path(__file__).parent / "templates"),
                         autoescape=jinja2.select_autoescape(["html"]))


def html(template: str, **context) -> str:
    return ENV.get_template(template).render(**context)


def pdf(markup: str) -> bytes:
    import weasyprint

    return weasyprint.HTML(string=markup).write_pdf()
