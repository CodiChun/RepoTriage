from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import DATABASE_URL


class Base(DeclarativeBase):
    pass


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    POSTED = "posted"


class TriageResult(Base):
    __tablename__ = "triage_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_number = Column(Integer, nullable=False, index=True)
    issue_title = Column(String(500), nullable=False)
    issue_body = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)
    severity = Column(String(20), nullable=True)
    similar_issues = Column(JSON, default=list)
    relevant_code_files = Column(JSON, default=list)
    draft_reply = Column(Text, nullable=True)
    reasoning_log = Column(JSON, default=list)
    route_taken = Column(String(50), nullable=True)
    needs_human_review = Column(Boolean, default=True)
    review_status = Column(String(20), default=ReviewStatus.PENDING.value)
    github_comment_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_triage_result(db: Session, result: dict) -> TriageResult:
    record = TriageResult(
        issue_number=result["issue_number"],
        issue_title=result["issue_title"],
        issue_body=result.get("issue_body"),
        category=result.get("category"),
        severity=result.get("severity"),
        similar_issues=result.get("similar_issues", []),
        relevant_code_files=result.get("relevant_code_files", []),
        draft_reply=result.get("draft_reply"),
        reasoning_log=result.get("reasoning_log", []),
        route_taken=result.get("route_taken"),
        needs_human_review=result.get("needs_human_review", True),
        review_status=ReviewStatus.PENDING.value,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_pending_reviews(db: Session) -> list[TriageResult]:
    return (
        db.query(TriageResult)
        .filter(TriageResult.review_status == ReviewStatus.PENDING.value)
        .order_by(TriageResult.created_at.desc())
        .all()
    )


def get_triage_by_id(db: Session, triage_id: int) -> TriageResult | None:
    return db.query(TriageResult).filter(TriageResult.id == triage_id).first()


def get_all_triages(db: Session, limit: int = 100) -> list[TriageResult]:
    return db.query(TriageResult).order_by(TriageResult.created_at.desc()).limit(limit).all()


def update_review_status(db: Session, triage_id: int, status: str, comment_url: str | None = None) -> TriageResult | None:
    record = get_triage_by_id(db, triage_id)
    if not record:
        return None
    record.review_status = status
    if comment_url:
        record.github_comment_url = comment_url
    db.commit()
    db.refresh(record)
    return record
