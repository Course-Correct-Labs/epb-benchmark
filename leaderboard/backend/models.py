"""Database models for EPB leaderboard."""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

Base = declarative_base()


class Submission(Base):
    """Model for EPB benchmark submissions."""

    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    epb_version = Column(String, nullable=False, index=True)
    model_name = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)

    # Scores
    mirror_loop_phi = Column(Float, nullable=False)
    confab_persistence = Column(Float, nullable=False)
    violation_contamination = Column(Float, nullable=False)
    echo_drift = Column(Float, nullable=False)
    epb_truth = Column(Float, nullable=False, index=True)

    # Metadata
    certification = Column(String, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow, index=True)
    submitter = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)

    # Full results JSON
    scores_json = Column(JSON, nullable=False)
    config_json = Column(JSON, nullable=True)
    details_json = Column(JSON, nullable=True)

    def to_dict(self, include_details: bool = False):
        """Convert submission to dictionary."""
        result = {
            "id": self.id,
            "epb_version": self.epb_version,
            "model_name": self.model_name,
            "provider": self.provider,
            "scores": {
                "mirror_loop_phi": self.mirror_loop_phi,
                "confab_persistence": self.confab_persistence,
                "violation_contamination": self.violation_contamination,
                "echo_drift": self.echo_drift,
                "epb_truth": self.epb_truth,
            },
            "certification": self.certification,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "submitter": self.submitter,
        }

        if include_details and self.details_json:
            result["details"] = self.details_json

        return result
