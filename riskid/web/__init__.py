"""The web shell: templates, static files, the per-request store and the local-only guards.

Server-rendered pages (SPEC.md sections 6 and 9). The routes are ``async``
and so is :func:`get_store`, so a request opens, uses and closes its SQLite
connection on one thread: the connection belongs to the thread that opened it.

Two guards keep the workbench local (SPEC.md section 10): the Host header must
name an allowed host, which stops a web page from reaching the workbench
through DNS rebinding, and a change (any method other than GET, HEAD or
OPTIONS) is refused when the browser says it comes from another origin, which
stops a web page from posting into the register.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.trustedhost import TrustedHostMiddleware

from riskid.store import Store
from riskid.web.modules import MODULES, NAV

WEB_DIR = Path(__file__).parent
LOOPBACK_HOSTS = ("127.0.0.1", "localhost")
_SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

templates = Jinja2Templates(directory=WEB_DIR / "templates")
templates.env.globals["zip"] = zip


async def get_store(request: Request):
    """Open the organisation file for one request and close it afterwards."""
    path = request.app.state.store_path
    if path is None:
        raise HTTPException(503, "No organisation file is open: start the workbench "
                                 "with `riskid serve <file>`.")
    if not path.exists():
        # Opening it would create an empty file and save into that instead.
        raise HTTPException(503, f"The organisation file {path} has gone; "
                                 "restore it or start the workbench on another file.")
    store = Store(path)
    try:
        yield store
    finally:
        store.close()


def render(request: Request, name: str, module: str, status_code: int = 200, **context):
    """Render a module page with the shell's header, navigation and actor."""
    return templates.TemplateResponse(
        request, name,
        {"module": MODULES[module], "nav": NAV, "actor": request.app.state.actor, **context},
        status_code=status_code)


class SameOriginWrites:
    """Refuse a change whose Origin header names another site (pure ASGI middleware)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] not in _SAFE_METHODS:
            headers = dict(scope["headers"])
            origin = headers.get(b"origin")
            host = headers.get(b"host", b"").decode("latin-1")
            if origin is not None:
                origin = origin.decode("latin-1")
                if origin == "null" or urlsplit(origin).netloc != host:
                    response = PlainTextResponse(
                        "Refused: changes must come from the workbench's own pages.",
                        status_code=403)
                    await response(scope, receive, send)
                    return
        await self.app(scope, receive, send)


def install(app, allowed_hosts) -> None:
    """Add the guards, the static files and the module routers to ``app``."""
    from riskid.web.routes_inventory import router as inventory
    from riskid.web.routes_library import router as library
    from riskid.web.routes_usecases import router as usecases
    from riskid.web.routes_workshop import router as workshop
    from riskid.web.routes_reconcile import router as reconcile
    from riskid.web.routes_assess import router as assess
    from riskid.web.routes_interact import router as interact
    from riskid.web.routes_register import router as register
    from riskid.web.routes_documents import router as documents

    app.add_middleware(SameOriginWrites)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(allowed_hosts))
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
    app.include_router(inventory)
    app.include_router(library)
    app.include_router(usecases)
    app.include_router(workshop)
    app.include_router(reconcile)
    app.include_router(assess)
    app.include_router(interact)
    app.include_router(register)
    app.include_router(documents)
