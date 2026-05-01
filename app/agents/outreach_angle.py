"""Outreach angle selection for scored leads."""

from typing import List

from pydantic import BaseModel

from app.schemas import ClassifiedPost, LeadScoreBreakdown, RawPost


PITCH_ONE_API = "One API for all SOTA media models"
PITCH_BETTER_PRICING = "Better pricing at scale"
PITCH_RELIABILITY = "Reliability for production workloads"
PITCH_INFRA_LAYER = "Creator platform / app infra layer"


class OutreachAngle(BaseModel):
    """Recommended pitch angle and concise outreach guidance."""

    atlas_pitch_angle: str
    recommended_outreach: str


def build_outreach_angle(
    raw_post: RawPost,
    classified_post: ClassifiedPost,
    score_breakdown: LeadScoreBreakdown,
) -> OutreachAngle:
    """Build a concise outreach angle from observed evidence."""
    pitch_angle = _select_pitch_angle(raw_post, classified_post, score_breakdown)
    evidence = _evidence_phrase(raw_post, classified_post)

    if classified_post.is_kol_distribution:
        outreach = (
            f"Reference their tutorial angle on {evidence}. Suggest a lightweight benchmark or educational "
            "collaboration around production media generation infrastructure."
        )
    elif classified_post.is_enterprise or classified_post.is_competitor_official:
        outreach = "Do not prioritize outbound; this signal is excluded or not a buyer lead."
    elif pitch_angle == PITCH_BETTER_PRICING:
        outreach = (
            f"Mention their cost concern around {evidence}. Position Atlas as a way to control media generation "
            "spend at campaign or app scale."
        )
    elif pitch_angle == PITCH_ONE_API:
        outreach = (
            f"Point to their comparison of {evidence}. Offer Atlas as one API for routing across leading image "
            "and video models."
        )
    elif pitch_angle == PITCH_RELIABILITY:
        outreach = (
            f"Reference the queue, latency, or failed-job issue in their post. Position Atlas around reliable "
            "production workloads, fallbacks, and predictable execution."
        )
    else:
        outreach = (
            f"Reference their creator app workflow around {evidence}. Position Atlas as the media generation "
            "infrastructure layer behind the product."
        )

    return OutreachAngle(
        atlas_pitch_angle=pitch_angle,
        recommended_outreach=outreach,
    )


def _select_pitch_angle(
    raw_post: RawPost,
    classified_post: ClassifiedPost,
    score_breakdown: LeadScoreBreakdown,
) -> str:
    text = _combined_text(raw_post, classified_post)
    pain_types = set(classified_post.pain_types)

    if "fal.ai pricing pain" in pain_types or _has_any(text, ["expensive", "pricing", "invoice", "cost", "spend"]):
        return PITCH_BETTER_PRICING
    if len(classified_post.model_mentions) >= 2 or len(classified_post.competitors) >= 2:
        return PITCH_ONE_API
    if pain_types.intersection({"queue / latency", "reliability pain", "failed generation", "rate limit"}) or _has_any(
        text,
        ["queue", "latency", "failed", "failure", "rate limit", "429", "timeout", "stuck", "retry"],
    ):
        return PITCH_RELIABILITY
    if classified_post.segment in {
        "AI-native creator platform",
        "Creator platform with many users",
        "iOS/mobile AI media app",
        "AI video generator app",
    }:
        return PITCH_INFRA_LAYER
    if score_breakdown.scale_score >= 24 and score_breakdown.fit_score >= 20:
        return PITCH_INFRA_LAYER
    return PITCH_RELIABILITY


def _evidence_phrase(raw_post: RawPost, classified_post: ClassifiedPost) -> str:
    if classified_post.competitors:
        return ", ".join(classified_post.competitors[:3])
    if classified_post.pain_types:
        return ", ".join(classified_post.pain_types[:2])
    if classified_post.segment != "Irrelevant":
        return classified_post.segment.lower()
    return _short_text(raw_post.text)


def _short_text(text: str) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= 80:
        return cleaned
    return f"{cleaned[:77].rstrip()}..."


def _combined_text(raw_post: RawPost, classified_post: ClassifiedPost) -> str:
    return " ".join(
        [
            raw_post.text or "",
            raw_post.author_bio or "",
            raw_post.matched_query or "",
            " ".join(classified_post.pain_types),
            " ".join(classified_post.competitors),
            " ".join(classified_post.model_mentions),
        ]
    ).lower()


def _has_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)
