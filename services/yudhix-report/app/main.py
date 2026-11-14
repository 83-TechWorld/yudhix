"""yudhix-report: business reports across workspaces, as a live preview (JSON) or a PDF.

Endpoints (behind the gateway at /api/v1/reports):
  GET  /api/v1/reports/options   report types, sections, periods and the caller's workspaces
  POST /api/v1/reports/preview   the report as JSON (the web app draws it)
  POST /api/v1/reports/pdf       the same report as a PDF download

Reads the shared database in read-only mode. Works for any workspace member; a report only ever
covers workspaces the caller belongs to.
"""
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app import build, catalog, config, pdf
from app.auth import ROLE_LABELS, Principal, allowed, my_workspaces, principal
from app.db import fetch_one

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("yudhix-report")

app = FastAPI(title="Yudhix Reports", version="1.0.0", docs_url="/api/v1/reports/docs",
              openapi_url="/api/v1/reports/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Authorization", "Content-Type", "X-Tenant-Id"],
                   expose_headers=["Content-Disposition"])


class ReportRequest(BaseModel):
    audience: str = "executive"
    workspace_ids: List[str] = Field(default_factory=list, alias="workspaceIds")
    period: str = catalog.DEFAULT_PERIOD
    sections: Optional[List[str]] = None

    model_config = {"populate_by_name": True}


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
def readyz():
    try:
        fetch_one("SELECT 1 AS ok")
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(503, f"database unavailable: {type(e).__name__}")


@app.get("/api/v1/reports/options")
def options(user: Principal = Depends(principal)):
    return {**catalog.options(),
            "workspaces": [{"id": w.id, "name": w.name, "role": w.role, "roleLabel": ROLE_LABELS.get(w.role, w.role),
                            "isDemo": w.is_demo, "plan": w.plan} for w in my_workspaces(user)]}


def _report(body: ReportRequest, user: Principal) -> dict:
    if body.audience not in catalog.AUDIENCES:
        raise HTTPException(400, "Unknown report type.")
    if body.period not in catalog.PERIODS:
        raise HTTPException(400, "Unknown period.")
    workspaces = allowed(user, body.workspace_ids)
    return build.build(user, workspaces, body.audience, body.period, body.sections)


@app.post("/api/v1/reports/preview")
async def preview(body: ReportRequest, user: Principal = Depends(principal)):
    return await run_in_threadpool(_report, body, user)


@app.post("/api/v1/reports/pdf")
async def download(body: ReportRequest, user: Principal = Depends(principal)):
    report = await run_in_threadpool(_report, body, user)
    data = await run_in_threadpool(pdf.render, report)
    logger.info("PDF report %s for %s: %d workspaces, %d bytes", body.audience, user.email,
                len(report["workspaces"]), len(data))
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename(report)}"',
                             "Cache-Control": "no-store"})


def filename(report: dict) -> str:
    names = [w["name"] for w in report["workspaces"]]
    scope = names[0] if len(names) == 1 else f"{len(names)}-workspaces"
    slug = re.sub(r"[^A-Za-z0-9]+", "-", f'Yudhix {report["audience"]["label"]} report {scope}').strip("-")
    return f"{slug}-{datetime.now(timezone.utc):%Y-%m-%d}.pdf"
