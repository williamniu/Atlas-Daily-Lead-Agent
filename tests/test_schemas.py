"""Unit tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError

from app.schemas import (
    AuthorProfile,
    ClassifiedPost,
    Lead,
    LeadScoreBreakdown,
    RawPost,
    RunMetadata,
)


def test_raw_post_accepts_required_fields() -> None:
    post = RawPost(
        source="x",
        post_id="post_123",
        post_url="https://x.com/example/status/post_123",
        text="We need faster AI video generation for mobile creators.",
    )

    assert post.post_id == "post_123"
    assert post.followers_count == 0
    assert post.raw_json == {}


def test_raw_post_rejects_empty_post_id() -> None:
    with pytest.raises(ValidationError, match="post_id cannot be empty"):
        RawPost(source="x", post_id=" ", text="Missing post id")


def test_author_profile_uses_safe_defaults() -> None:
    profile = AuthorProfile(username="creator_app")

    assert profile.username == "creator_app"
    assert profile.followers_count == 0
    assert profile.raw_json == {}


def test_classified_post_accepts_signal_lists() -> None:
    classified = ClassifiedPost(
        post_id="post_123",
        segment="AI video generator apps",
        intent_type="evaluation",
        pain_types=["latency", "render_cost"],
        competitors=["Higgsfield"],
        model_mentions=["video model"],
        scale_signals=["many users"],
        contactability_signals=["founder account"],
        classification_reason="The post describes creator video generation pain.",
    )

    assert classified.segment == "AI video generator apps"
    assert classified.is_enterprise is False


def test_lead_score_must_be_between_zero_and_one_hundred() -> None:
    with pytest.raises(ValidationError):
        Lead(
            lead_id="lead_123",
            post_id="post_123",
            segment="AI video generator apps",
            score=101,
            score_breakdown=LeadScoreBreakdown(),
        )


def test_high_score_lead_requires_reason_code() -> None:
    with pytest.raises(ValidationError, match="high-score leads above 70"):
        Lead(
            lead_id="lead_123",
            post_id="post_123",
            segment="AI video generator apps",
            score=85,
            score_breakdown=LeadScoreBreakdown(fit_score=90),
            source_url="https://example.com/post/123",
        )


def test_high_score_lead_accepts_reason_code_and_valid_url() -> None:
    lead = Lead(
        lead_id="lead_123",
        post_id="post_123",
        username="founder",
        display_name="Founder",
        company_or_product="Creator AI Studio",
        segment="Higgsfield-like AI-native creator platforms",
        score=86,
        score_breakdown=LeadScoreBreakdown(
            fit_score=92,
            intent_score=84,
            pain_score=80,
        ),
        reason_codes=["high_fit_creator_platform"],
        evidence=["The post mentions mobile AI video generation for creators."],
        atlas_pitch_angle="Position Atlas Cloud as fast AI media infrastructure.",
        recommended_outreach="Send a concise founder-led infrastructure note.",
        lead_bucket="hot",
        source_url="https://example.com/post/123",
    )

    assert lead.score == 86
    assert lead.reason_codes == ["high_fit_creator_platform"]
    assert str(lead.source_url) == "https://example.com/post/123"


def test_source_url_must_be_valid_if_present() -> None:
    with pytest.raises(ValidationError):
        Lead(
            lead_id="lead_123",
            post_id="post_123",
            segment="Digital marketing firms",
            score=40,
            score_breakdown=LeadScoreBreakdown(),
            source_url="not-a-url",
        )


def test_run_metadata_defaults() -> None:
    metadata = RunMetadata(run_id="run_123")

    assert metadata.run_id == "run_123"
    assert metadata.app_env == "development"
    assert metadata.use_mock_data is True
