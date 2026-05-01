"""Tests for outreach angle selection."""

from app.agents.outreach_angle import (
    PITCH_BETTER_PRICING,
    PITCH_INFRA_LAYER,
    PITCH_ONE_API,
    PITCH_RELIABILITY,
    build_outreach_angle,
)
from app.agents.segment_classifier import classify_post
from app.schemas import LeadScoreBreakdown, RawPost


def make_post(text: str, **overrides) -> RawPost:
    data = {
        "source": "x",
        "post_id": "post_123",
        "text": text,
        "username": "builder",
        "author_name": "Builder AI",
        "author_bio": "AI video generator app for creators.",
        "followers_count": 25000,
        "matched_query": "AI video generator apps",
    }
    data.update(overrides)
    return RawPost(**data)


def test_pricing_pain_emphasizes_better_pricing() -> None:
    post = make_post("fal.ai pricing and invoices hurt margins when campaign volume spikes.")
    classified = classify_post(post, allow_llm=False)

    result = build_outreach_angle(post, classified, LeadScoreBreakdown(pain_score=20))

    assert result.atlas_pitch_angle == PITCH_BETTER_PRICING
    assert "spend" in result.recommended_outreach or "cost" in result.recommended_outreach


def test_multiple_models_emphasize_one_api() -> None:
    post = make_post("We are comparing Runway, Kling, Seedance, and Veo for app workflows.")
    classified = classify_post(post, allow_llm=False)

    result = build_outreach_angle(post, classified, LeadScoreBreakdown(fit_score=20))

    assert result.atlas_pitch_angle == PITCH_ONE_API
    assert "one API" in result.recommended_outreach


def test_latency_and_failed_jobs_emphasize_reliability() -> None:
    post = make_post("Queue latency and failed renders are hurting launch week reliability.")
    classified = classify_post(post, allow_llm=False)

    result = build_outreach_angle(post, classified, LeadScoreBreakdown(pain_score=18))

    assert result.atlas_pitch_angle == PITCH_RELIABILITY
    assert "failed-job" in result.recommended_outreach or "latency" in result.recommended_outreach


def test_creator_mobile_app_emphasizes_infra_layer() -> None:
    post = make_post(
        "We are launching an iPhone-first mobile AI video app for creators.",
        author_bio="Founder of a mobile AI media app.",
    )
    classified = classify_post(post, allow_llm=False)

    result = build_outreach_angle(post, classified, LeadScoreBreakdown(fit_score=23, scale_score=16))

    assert result.atlas_pitch_angle == PITCH_INFRA_LAYER
    assert "infrastructure layer" in result.recommended_outreach
