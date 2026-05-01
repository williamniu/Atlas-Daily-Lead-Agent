"""Tests for lead scoring."""

from app.agents.lead_scorer import score_lead
from app.agents.segment_classifier import classify_post
from app.schemas import RawPost


def make_post(text: str, **overrides) -> RawPost:
    data = {
        "source": "x",
        "post_id": "post_123",
        "post_url": "https://x.com/example/status/post_123",
        "text": text,
        "username": "example",
        "author_name": "Example AI",
        "author_bio": "AI video generator app for creators.",
        "followers_count": 52000,
        "following_count": 300,
        "like_count": 100,
        "reply_count": 10,
        "repost_count": 20,
        "quote_count": 5,
        "matched_query": "AI video generator apps",
    }
    data.update(overrides)
    return RawPost(**data)


def test_fal_pricing_pain_ai_video_app_scores_high() -> None:
    post = make_post(
        "Our AI video generator app is in production. fal.ai pricing and surprise invoices hurt margins, "
        "and we need one API with fallback routing before usage doubles.",
        followers_count=88000,
    )
    classified = classify_post(post, allow_llm=False)

    lead = score_lead(post, classified)

    assert lead.score >= 85
    assert lead.lead_bucket == "Top Revenue Lead"
    assert "AI_VIDEO_GENERATOR_APP" in lead.reason_codes
    assert "FAL_PRICING_PAIN" in lead.reason_codes
    assert "ONE_API_NEED" in lead.reason_codes


def test_enterprise_is_penalized() -> None:
    post = make_post(
        "Enterprise RFP for generative media requires procurement, SSO, audit logging, and vendor risk review.",
        author_bio="Enterprise transformation office.",
        followers_count=90000,
    )
    classified = classify_post(post, allow_llm=False)

    lead = score_lead(post, classified)

    assert lead.score < 55
    assert lead.lead_bucket == "Not Qualified"
    assert "ENTERPRISE_EXCLUDED" in lead.reason_codes
    assert lead.score_breakdown.penalty_score >= 20


def test_pure_news_scores_low() -> None:
    post = make_post(
        "News: AI video startups raised more funding this week as text-to-video adoption grows.",
        username="marketpulse",
        author_name="MarketPulse AI",
        author_bio="News and analysis on AI companies.",
        followers_count=64000,
        matched_query="AI video startup news",
    )
    classified = classify_post(post, allow_llm=False)

    lead = score_lead(post, classified)

    assert lead.score < 40
    assert lead.lead_bucket == "Not Qualified"
    assert "PURE_NEWS" in lead.reason_codes


def test_kol_tutorial_is_distribution_not_revenue() -> None:
    post = make_post(
        "Tutorial: comparing Runway, Kling, and Seedance for creator app founders. Track retries and queue time.",
        username="sashateachesai",
        author_name="Sasha Teaches AI",
        author_bio="Tutorials for AI builders and creator tool founders.",
        followers_count=154000,
    )
    classified = classify_post(post, allow_llm=False)

    lead = score_lead(post, classified)

    assert lead.lead_bucket == "Distribution / Weak Lead"
    assert "KOL_DISTRIBUTION" in lead.reason_codes
    assert lead.lead_bucket != "Top Revenue Lead"
