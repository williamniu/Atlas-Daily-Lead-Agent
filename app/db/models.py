"""SQLAlchemy models for Atlas Daily Lead Agent."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class Run(Base):
    """One daily lead intelligence run."""

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    app_env: Mapped[str] = mapped_column(String(64), default="development", nullable=False)
    use_mock_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    raw_post_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    classified_post_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lead_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RawPostRecord(Base):
    """Raw post persisted after collection."""

    __tablename__ = "raw_posts"
    __table_args__ = (UniqueConstraint("post_id", name="uq_raw_posts_post_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    post_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    post_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    author_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    author_bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    followers_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    following_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reply_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    repost_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quote_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    matched_query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    inserted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ClassifiedPostRecord(Base):
    """Post classification persisted after agent analysis."""

    __tablename__ = "classified_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    segment: Mapped[str] = mapped_column(String(255), nullable=False)
    intent_type: Mapped[str] = mapped_column(String(128), nullable=False)
    pain_types: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    competitors: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    model_mentions: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    scale_signals: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    contactability_signals: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    is_enterprise: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_competitor_official: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_kol_distribution: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    classification_reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class LeadRecord(Base):
    """Scored lead persisted for dashboarding and outreach."""

    __tablename__ = "leads"
    __table_args__ = (UniqueConstraint("lead_id", name="uq_leads_lead_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    post_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company_or_product: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    segment: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    score_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    reason_codes: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    evidence: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    atlas_pitch_angle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_outreach: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lead_bucket: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class FeedbackLabel(Base):
    """Human feedback label for a surfaced lead."""

    __tablename__ = "feedback_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    feedback_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
