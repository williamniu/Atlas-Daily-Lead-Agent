"""Tests for rule-based classification agents."""

from app.agents.competitor_detector import detect_competitors
from app.agents.pain_intent_classifier import classify_pain_and_intent
from app.agents.segment_classifier import classify_post
from app.schemas import RawPost


def make_post(text: str, **overrides) -> RawPost:
    data = {
        "source": "x",
        "post_id": "post_123",
        "text": text,
        "username": "builder",
        "author_name": "Builder",
        "author_bio": "Founder building AI video tools.",
        "matched_query": "AI video generator apps",
    }
    data.update(overrides)
    return RawPost(**data)


def test_segment_classifier_identifies_mobile_ai_media_app() -> None:
    post = make_post(
        "We are launching an iPhone-first mobile AI video editor and need stable previews.",
        author_bio="Founder at a mobile AI media app.",
    )

    result = classify_post(post, allow_llm=False)

    assert result.segment == "iOS/mobile AI media app"
    assert result.intent_type == "buying intent"
    assert "reliability pain" in result.pain_types


def test_segment_classifier_excludes_enterprise() -> None:
    post = make_post(
        "Enterprise RFP for generative media requires procurement, SSO, audit logging, and vendor risk review.",
        author_bio="Enterprise transformation office.",
    )

    result = classify_post(post, allow_llm=False)

    assert result.segment == "Enterprise, excluded"
    assert result.is_enterprise is True


def test_segment_classifier_identifies_kol_distribution_partner() -> None:
    post = make_post(
        "Tutorial: comparing Runway, Kling, and Seedance for creator app founders.",
        username="sashateachesai",
        author_name="Sasha Teaches AI",
        author_bio="Tutorials for AI builders and creator tool founders.",
    )

    result = classify_post(post, allow_llm=False)

    assert result.segment == "KOL / distribution partner"
    assert result.is_kol_distribution is True
    assert "Runway" in result.competitors
    assert "Kling" in result.competitors


def test_pain_intent_classifier_detects_cost_and_fal_pricing() -> None:
    post = make_post(
        "fal.ai pricing is fine for demos but the invoice hurts when campaign volume spikes."
    )

    result = classify_pain_and_intent(post)

    assert "cost pain" in result.pain_types
    assert "fal.ai pricing pain" in result.pain_types
    assert result.intent_type == "buying intent"


def test_competitor_detector_detects_supported_competitors() -> None:
    post = make_post(
        "Testing Replicate, Runway, Kling, Seedance, OpenRouter, RunPod, Modal, Fireworks, and Together."
    )

    result = detect_competitors(post)

    assert result.competitors == [
        "Replicate",
        "Runway",
        "Kling",
        "Seedance",
        "OpenRouter",
        "RunPod",
        "Modal",
        "Fireworks",
        "Together",
    ]


def test_competitor_official_post_is_marked_irrelevant() -> None:
    post = make_post(
        "New creator controls are rolling out today in Runway.",
        username="runwayml",
        author_name="Runway",
        author_bio="Official updates from Runway.",
    )

    result = classify_post(post, allow_llm=False)

    assert result.is_competitor_official is True
    assert result.segment == "Irrelevant"
