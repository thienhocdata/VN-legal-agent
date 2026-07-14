from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .auth import Authenticator, Principal
from .config import Settings
from .coverage import coverage_view
from .database import Database
from .knowledge import KnowledgeRepository
from .models import CaseCreate, ChatRequest, ChatResponse, ContextRequest, FactConfirm, FactCreate, IntakeRequest, Provenance, ResearchRequest, ReviewRequest, Role
from .service import LegalCaseService

settings = Settings.load()
ROOT = settings.root
db = Database(settings.database_path)
service = LegalCaseService(db, KnowledgeRepository(db, settings.allow_demo_sources))
auth = Authenticator(db, settings.auth_required)
app = FastAPI(title="Minh Long Legal Agent", version="0.1.0", description="Auditable legal decision-support MVP; demo corpus is not legal advice.")
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")


@app.get("/", include_in_schema=False)
async def console(): return FileResponse(ROOT / "app" / "static" / "index.html")


@app.get("/health")
async def health(): return {"status": "ok", "product": "Minh Long Legal Agent", "legal_coverage": "demo_allowed" if settings.allow_demo_sources else "governed_only", "environment": settings.environment, "auth_required": settings.auth_required}


@app.get("/coverage")
async def coverage(): return coverage_view()


@app.post("/api/v1/cases", status_code=201)
async def create_case(req: CaseCreate, principal: Principal = Depends(auth.principal)):
    req.tenant_id, req.actor_id, req.actor_role = principal.tenant_id, principal.actor_id, principal.role
    return service.create_case(req)


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, principal: Principal = Depends(auth.principal)):
    return service.chat(req.case_id, req.message, principal.tenant_id, principal.actor_id, principal.role)


@app.get("/api/v1/cases/{case_id}/messages")
async def messages(case_id: str, principal: Principal = Depends(auth.principal)):
    return service.messages(case_id, principal.tenant_id)


@app.get("/api/v1/cases")
async def list_cases(principal: Principal = Depends(auth.principal)): return service.list_cases(principal.tenant_id)


@app.get("/api/v1/cases/{case_id}")
async def get_case(case_id: str, principal: Principal = Depends(auth.principal)): return service.get_case(case_id, principal.tenant_id)


@app.post("/api/v1/cases/{case_id}/intake")
async def intake(case_id: str, req: IntakeRequest, principal: Principal = Depends(auth.principal)):
    service.get_case(case_id, principal.tenant_id)
    return service.intake(case_id, principal.actor_id, principal.role, req.text)


@app.post("/api/v1/cases/{case_id}/facts")
async def add_fact(case_id: str, req: FactCreate, principal: Principal = Depends(auth.principal)):
    service.get_case(case_id, principal.tenant_id)
    req.actor_id = principal.actor_id
    if principal.role == Role.CASE_PARTICIPANT: req.provenance = Provenance.USER_PROVIDED
    elif req.provenance != Provenance.AGENT_INFERRED: req.provenance = Provenance.STAFF_ENTERED
    return service.add_fact(case_id, req)


@app.post("/api/v1/cases/{case_id}/facts/{fact_id}/confirm")
async def confirm_fact(case_id: str, fact_id: str, req: FactConfirm, principal: Principal = Depends(auth.principal)):
    service.get_case(case_id, principal.tenant_id)
    req.actor_id, req.actor_role = principal.actor_id, principal.role
    return service.confirm_fact(case_id, fact_id, req)


@app.post("/api/v1/cases/{case_id}/clarify")
async def clarify(case_id: str, principal: Principal = Depends(auth.principal)):
    service.get_case(case_id, principal.tenant_id)
    return service.clarify(case_id)


@app.post("/api/v1/cases/{case_id}/context")
async def context(case_id: str, req: ContextRequest, principal: Principal = Depends(auth.principal)):
    service.get_case(case_id, principal.tenant_id)
    return service.set_context(case_id, req)


@app.post("/api/v1/cases/{case_id}/research")
async def research(case_id: str, req: ResearchRequest, principal: Principal = Depends(auth.principal)):
    service.get_case(case_id, principal.tenant_id)
    return service.research(case_id, req)


@app.post("/api/v1/cases/{case_id}/analyze")
async def analyze(case_id: str, principal: Principal = Depends(auth.principal)):
    service.get_case(case_id, principal.tenant_id)
    return service.analyze(case_id)


@app.post("/api/v1/cases/{case_id}/review")
async def review(case_id: str, req: ReviewRequest, principal: Principal = Depends(auth.principal)):
    service.get_case(case_id, principal.tenant_id)
    req.actor_id, req.actor_role = principal.actor_id, principal.role
    return service.review(case_id, req)


@app.get("/api/v1/cases/{case_id}/audit")
async def audit(case_id: str, principal: Principal = Depends(auth.principal)):
    service.get_case(case_id, principal.tenant_id)
    return service.audit_log(case_id)
