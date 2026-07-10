from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agent.graph import triage_graph
from agent.tools import post_comment_to_github
from config import CORS_ORIGINS
from db.models import (
    ReviewStatus,
    TriageResult,
    get_all_triages,
    get_db,
    get_pending_reviews,
    get_triage_by_id,
    init_db,
    save_triage_result,
    update_review_status,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="RepoTriage API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TriageRequest(BaseModel):
    issue_number: int
    issue_title: str
    issue_body: str = ""


class ApproveRequest(BaseModel):
    draft_reply: Optional[str] = None


class TriageResponse(BaseModel):
    id: int
    issue_number: int
    issue_title: str
    issue_body: Optional[str]
    category: Optional[str]
    severity: Optional[str]
    similar_issues: list
    relevant_code_files: list
    draft_reply: Optional[str]
    reasoning_log: list
    route_taken: Optional[str]
    needs_human_review: bool
    review_status: str
    github_comment_url: Optional[str]
    created_at: str


def to_response(record: TriageResult) -> TriageResponse:
    return TriageResponse(
        id=record.id,
        issue_number=record.issue_number,
        issue_title=record.issue_title,
        issue_body=record.issue_body,
        category=record.category,
        severity=record.severity,
        similar_issues=record.similar_issues or [],
        relevant_code_files=record.relevant_code_files or [],
        draft_reply=record.draft_reply,
        reasoning_log=record.reasoning_log or [],
        route_taken=record.route_taken,
        needs_human_review=record.needs_human_review,
        review_status=record.review_status,
        github_comment_url=record.github_comment_url,
        created_at=record.created_at.isoformat(),
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/triage", response_model=TriageResponse)
async def triage_issue(request: TriageRequest, db: Session = Depends(get_db)):
    result = triage_graph.invoke(
        {
            "issue_number": request.issue_number,
            "issue_title": request.issue_title,
            "issue_body": request.issue_body,
            "category": None,
            "similar_issues": [],
            "relevant_code_files": [],
            "severity": None,
            "draft_reply": None,
            "needs_human_review": False,
            "reasoning_log": [],
            "route_taken": None,
        }
    )
    record = save_triage_result(db, result)
    return to_response(record)


@app.post("/webhook/github")
async def github_webhook(payload: dict, db: Session = Depends(get_db)):
    if payload.get("action") != "opened":
        return {"status": "ignored", "reason": "not an opened issue event"}

    issue = payload.get("issue", {})
    result = triage_graph.invoke(
        {
            "issue_number": issue.get("number", 0),
            "issue_title": issue.get("title", ""),
            "issue_body": issue.get("body") or "",
            "category": None,
            "similar_issues": [],
            "relevant_code_files": [],
            "severity": None,
            "draft_reply": None,
            "needs_human_review": False,
            "reasoning_log": [],
            "route_taken": None,
        }
    )
    record = save_triage_result(db, result)
    return {"status": "processed", "triage_id": record.id}


@app.get("/issues", response_model=list[TriageResponse])
async def list_issues(db: Session = Depends(get_db)):
    records = get_all_triages(db)
    return [to_response(r) for r in records]


@app.get("/issues/pending-review", response_model=list[TriageResponse])
async def get_pending(db: Session = Depends(get_db)):
    records = get_pending_reviews(db)
    return [to_response(r) for r in records]


@app.get("/issues/{triage_id}", response_model=TriageResponse)
async def get_issue(triage_id: int, db: Session = Depends(get_db)):
    record = get_triage_by_id(db, triage_id)
    if not record:
        raise HTTPException(status_code=404, detail="Triage result not found")
    return to_response(record)


@app.post("/issues/{triage_id}/approve", response_model=TriageResponse)
async def approve_reply(triage_id: int, request: ApproveRequest, db: Session = Depends(get_db)):
    record = get_triage_by_id(db, triage_id)
    if not record:
        raise HTTPException(status_code=404, detail="Triage result not found")

    reply = request.draft_reply or record.draft_reply
    if not reply:
        raise HTTPException(status_code=400, detail="No draft reply to post")

    try:
        comment = post_comment_to_github(record.issue_number, reply)
        record = update_review_status(db, triage_id, ReviewStatus.POSTED.value, comment["url"])
        if request.draft_reply:
            record.draft_reply = request.draft_reply
            db.commit()
    except Exception as e:
        record = update_review_status(db, triage_id, ReviewStatus.APPROVED.value)
        raise HTTPException(status_code=500, detail=f"Approved but failed to post to GitHub: {e}")

    return to_response(record)


@app.post("/issues/{triage_id}/reject", response_model=TriageResponse)
async def reject_reply(triage_id: int, db: Session = Depends(get_db)):
    record = update_review_status(db, triage_id, ReviewStatus.REJECTED.value)
    if not record:
        raise HTTPException(status_code=404, detail="Triage result not found")
    return to_response(record)
