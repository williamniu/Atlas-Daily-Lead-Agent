"""Pydantic schemas for lead intelligence records."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class RawPost(BaseModel):
    """Raw social or web post collected from an external source."""

    source: str
    post_id: str
    post_url: Optional[str] = None
    text: str
    author_id: Optional[str] = None
    username: Optional[str] = None
    author_name: Optional[str] = None
    author_bio: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    like_count: int = 0
    reply_count: int = 0
    repost_count: int = 0
    quote_count: int = 0
    created_at: Optional[datetime] = None
    matched_query: Optional[str] = None
    raw_json: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("post_id")
    @classmethod
    def post_id_cannot_be_empty(cls, value: str) -> str:
        """Validate that the post identifier is present."""
        if not value or not value.strip():
            raise ValueError("post_id cannot be empty")
        return value


class AuthorProfile(BaseModel):
    """Normalized author profile extracted from raw source metadata."""

    author_id: Optional[str] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    profile_url: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    source: Optional[str] = None
    raw_json: Dict[str, Any] = Field(default_factory=dict)


class ClassifiedPost(BaseModel):
    """Classification output for a collected post."""

    post_id: str
    segment: str
    intent_type: str
    pain_types: List[str] = Field(default_factory=list)
    competitors: List[str] = Field(default_factory=list)
    model_mentions: List[str] = Field(default_factory=list)
    scale_signals: List[str] = Field(default_factory=list)
    contactability_signals: List[str] = Field(default_factory=list)
    is_enterprise: bool = False
    is_competitor_official: bool = False
    is_kol_distribution: bool = False
    classification_reason: str

    @field_validator("post_id")
    @classmethod
    def post_id_cannot_be_empty(cls, value: str) -> str:
        """Validate that the post identifier is present."""
        if not value or not value.strip():
            raise ValueError("post_id cannot be empty")
        return value


class LeadScoreBreakdown(BaseModel):
    """Component scores used to explain a lead score."""

    fit_score: float = Field(default=0.0, ge=0, le=100)
    intent_score: float = Field(default=0.0, ge=0, le=100)
    pain_score: float = Field(default=0.0, ge=0, le=100)
    scale_score: float = Field(default=0.0, ge=0, le=100)
    contactability_score: float = Field(default=0.0, ge=0, le=100)
    timing_score: float = Field(default=0.0, ge=0, le=100)
    penalty_score: float = Field(default=0.0, ge=0, le=100)


class Lead(BaseModel):
    """Qualified lead surfaced for Atlas Cloud outreach."""

    lead_id: str
    post_id: str
    username: Optional[str] = None
    display_name: Optional[str] = None
    company_or_product: Optional[str] = None
    segment: str
    score: float = Field(ge=0, le=100)
    score_breakdown: LeadScoreBreakdown
    reason_codes: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    atlas_pitch_angle: Optional[str] = None
    recommended_outreach: Optional[str] = None
    lead_bucket: Optional[str] = None
    source_url: Optional[HttpUrl] = None

    @field_validator("post_id")
    @classmethod
    def post_id_cannot_be_empty(cls, value: str) -> str:
        """Validate that the post identifier is present."""
        if not value or not value.strip():
            raise ValueError("post_id cannot be empty")
        return value

    @model_validator(mode="after")
    def high_score_leads_need_reason_codes(self) -> "Lead":
        """Require explanation codes for leads above the high-score threshold."""
        if self.score > 70 and not self.reason_codes:
            raise ValueError("high-score leads above 70 must have at least one reason code")
        return self


class RunMetadata(BaseModel):
    """Metadata for one lead intelligence run."""

    run_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    app_env: str = "development"
    use_mock_data: bool = True
    source_count: int = 0
    raw_post_count: int = 0
    classified_post_count: int = 0
    lead_count: int = 0
    notes: Optional[str] = None
