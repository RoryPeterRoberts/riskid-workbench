"""FastAPI application for the RiskID Workbench.

:func:`create_app` builds the application for one organisation file: the root
route returns the product title (round 0), and the module screens are mounted
from ``riskid.web`` (round 4 on). The module-level ``app`` has no file open;
its module screens answer 503 until the workbench is started with
``riskid serve <file>``.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from riskid import web
from riskid.config import default_actor

TITLE = "RiskID Workbench"


def create_app(store_path=None, actor: str | None = None, allowed_hosts=None) -> FastAPI:
    """Build the workbench for the organisation file at ``store_path``.

    ``actor`` is the person recorded on each change (default: see
    :mod:`riskid.config`). ``allowed_hosts`` are the Host header values
    accepted (default: loopback only, SPEC.md section 10).
    """
    application = FastAPI(title=TITLE)
    application.state.store_path = Path(store_path) if store_path is not None else None
    application.state.actor = actor or default_actor()
    application.state.default_actor = application.state.actor    # Settings can switch to a listed person

    @application.get("/")
    def index():
        """Return the product title."""
        return {"title": TITLE}

    web.install(application, allowed_hosts or web.LOOPBACK_HOSTS)
    return application


app = create_app()
