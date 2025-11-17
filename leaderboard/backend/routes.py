"""API routes for EPB leaderboard."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from leaderboard.backend.config import settings
from leaderboard.backend.db import get_db
from leaderboard.backend.models import Submission

router = APIRouter()


class SubmissionCreate(BaseModel):
    """Schema for creating a submission."""

    epb_version: str
    model_name: str
    provider: str
    scores: dict
    certification: str
    metadata: Optional[dict] = None
    details: Optional[dict] = None


class SubmissionResponse(BaseModel):
    """Schema for submission response."""

    id: int
    status: str = "accepted"
    message: str = "Submission successful"


@router.post("/submissions", response_model=SubmissionResponse)
async def create_submission(
    submission_data: SubmissionCreate,
    request: Request,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(None),
):
    """Create a new submission."""
    # Validate API key
    if not settings.validate_api_key(x_api_key or ""):
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Validate EPB version
    if submission_data.epb_version != "epb_v1":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported EPB version: {submission_data.epb_version}",
        )

    # Validate scores
    required_scores = [
        "mirror_loop_phi",
        "confab_persistence",
        "violation_contamination",
        "echo_drift",
        "epb_truth",
    ]
    for score_name in required_scores:
        if score_name not in submission_data.scores:
            raise HTTPException(status_code=400, detail=f"Missing score: {score_name}")

    # Create submission
    submission = Submission(
        epb_version=submission_data.epb_version,
        model_name=submission_data.model_name,
        provider=submission_data.provider,
        mirror_loop_phi=submission_data.scores["mirror_loop_phi"],
        confab_persistence=submission_data.scores["confab_persistence"],
        violation_contamination=submission_data.scores["violation_contamination"],
        echo_drift=submission_data.scores["echo_drift"],
        epb_truth=submission_data.scores["epb_truth"],
        certification=submission_data.certification,
        scores_json=submission_data.scores,
        config_json=submission_data.metadata.get("config")
        if submission_data.metadata
        else None,
        details_json=submission_data.details,
        ip_address=request.client.host if request.client else None,
    )

    db.add(submission)
    db.commit()
    db.refresh(submission)

    return SubmissionResponse(id=submission.id)


@router.get("/leaderboard")
async def get_leaderboard(
    epb_version: Optional[str] = "epb_v1",
    provider: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Get leaderboard rankings."""
    query = db.query(Submission)

    # Filter by EPB version
    if epb_version:
        query = query.filter(Submission.epb_version == epb_version)

    # Filter by provider
    if provider:
        query = query.filter(Submission.provider == provider)

    # Order by EPB Truth score (descending)
    query = query.order_by(Submission.epb_truth.desc())

    # Limit results
    query = query.limit(limit)

    submissions = query.all()

    # Build leaderboard with ranks
    leaderboard = []
    for rank, submission in enumerate(submissions, 1):
        entry = submission.to_dict(include_details=False)
        entry["rank"] = rank
        leaderboard.append(entry)

    return {"leaderboard": leaderboard, "total": len(leaderboard)}


@router.get("/submissions/{submission_id}")
async def get_submission(submission_id: int, db: Session = Depends(get_db)):
    """Get a specific submission by ID."""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    return submission.to_dict(include_details=True)


@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get leaderboard statistics."""
    total_submissions = db.query(Submission).count()

    # Count by provider
    providers = (
        db.query(Submission.provider, db.func.count(Submission.id))
        .group_by(Submission.provider)
        .all()
    )

    # Top score
    top_submission = (
        db.query(Submission).order_by(Submission.epb_truth.desc()).first()
    )

    return {
        "total_submissions": total_submissions,
        "by_provider": {provider: count for provider, count in providers},
        "top_score": top_submission.epb_truth if top_submission else None,
        "top_model": top_submission.model_name if top_submission else None,
    }
