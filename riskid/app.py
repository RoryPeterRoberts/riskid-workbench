"""FastAPI application for the RiskID Workbench.

Round 0 exposes a single route: the root returns the product title. Later
rounds mount the module routers here (PLAN.md section 4, round 4 on).
"""

from fastapi import FastAPI

TITLE = "RiskID Workbench"

app = FastAPI(title=TITLE)


@app.get("/")
def index():
    """Return the product title."""
    return {"title": TITLE}
