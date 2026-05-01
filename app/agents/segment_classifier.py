"""Hybrid segment classifier for raw lead-signal posts."""

import json
from typing import Dict, List, Optional

import requests

from app.agents.competitor_detector import detect_competitors
from app.agents.pain_intent_classifier import classify_pain_and_intent
from app.config import settings
from app.schemas import ClassifiedPost, RawPost


SEGMENT_ENTERPRISE_EXCLUDED = "Enterprise, excluded"
SEGMENT_IRRELEVANT = "Irrelevant"


def classify_post(post: RawPost, allow_llm: bool = True) -> ClassifiedPost:
    """Classify a raw post into a lead-intelligence segment."""
    rule_result = _rule_based_classification(post)
    if allow_llm and settings.has_llm:
        llm_result = _try_llm_classification(post, rule_result)
        if llm_result is not None:
            return llm_result
    return rule_result


def classify_posts(posts: List[RawPost], allow_llm: bool = True) -> List[ClassifiedPost]:
    """Classify multiple raw posts."""
    return [classify_post(post, allow_llm=allow_llm) for post in posts]


def _rule_based_classification(post: RawPost) -> ClassifiedPost:
    text = _combined_text(post)
    competitor_result = detect_competitors(post)
    pain_result = classify_pain_and_intent(post)
    segment = _detect_segment(post, text)
    is_enterprise = segment == SEGMENT_ENTERPRISE_EXCLUDED
    is_kol_distribution = segment == "KOL / distribution partner"

    reason_parts = [
        f"Segment matched by rules: {segment}.",
        f"Intent detected as {pain_result.intent_type}.",
    ]
    if pain_result.pain_types:
        reason_parts.append(f"Pain signals: {', '.join(pain_result.pain_types)}.")
    if competitor_result.competitors:
        reason_parts.append(f"Competitors mentioned: {', '.join(competitor_result.competitors)}.")
    if competitor_result.is_competitor_official:
        reason_parts.append("Post appears to be from a competitor official account.")

    return ClassifiedPost(
        post_id=post.post_id,
        segment=segment,
        intent_type=pain_result.intent_type,
        pain_types=pain_result.pain_types,
        competitors=competitor_result.competitors,
        model_mentions=competitor_result.model_mentions,
        scale_signals=pain_result.scale_signals,
        contactability_signals=pain_result.contactability_signals,
        is_enterprise=is_enterprise,
        is_competitor_official=competitor_result.is_competitor_official,
        is_kol_distribution=is_kol_distribution,
        classification_reason=" ".join(reason_parts),
    )


def _detect_segment(post: RawPost, text: str) -> str:
    if _has_any(text, ["enterprise", "procurement", "rfp", "vendor risk", "sso", "soc2", "audit logging"]):
        return SEGMENT_ENTERPRISE_EXCLUDED
    if detect_competitors(post).is_competitor_official:
        return SEGMENT_IRRELEVANT
    if _has_any(text, ["tutorial", "teaches", "breakdown", "newsletter", "kol", "audience"]):
        return "KOL / distribution partner"
    if _has_any(text, ["creator platform", "creator studio", "ai-native", "templates", "exports"]) and _has_any(
        text, ["many users", "monthly active", "1m", "600k", "120k", "exports"]
    ):
        return "Creator platform with many users"
    if _has_any(text, ["ai-native", "creator studio", "creator platform", "creatorcanvas", "hooklab"]):
        return "AI-native creator platform"
    if _has_any(text, ["iphone", "mobile app", "mobile ai", "photo app", "selfie", "ios"]):
        return "iOS/mobile AI media app"
    if _has_any(text, ["ai video generator", "video generator", "generated clips", "text-to-video"]):
        return "AI video generator app"
    if _has_any(text, ["digital marketing", "paid social", "performance creative", "ugc agency", "agency"]):
        return "Digital marketing agency"
    if _has_any(text, ["short-form", "shorts", "tiktok", "reels", "micro-movie", "short movie", "production team"]):
        return "Short-form video producer"
    if _has_any(text, ["ai video", "fal.ai", "replicate", "runway", "kling", "seedance"]):
        return "AI video generator app"
    return SEGMENT_IRRELEVANT


def _try_llm_classification(post: RawPost, fallback: ClassifiedPost) -> Optional[ClassifiedPost]:
    try:
        payload = _call_llm(post, fallback)
        if not payload:
            return None
        merged = fallback.model_dump()
        merged.update({key: value for key, value in payload.items() if value is not None})
        return ClassifiedPost.model_validate(merged)
    except Exception:
        return None


def _call_llm(post: RawPost, fallback: ClassifiedPost) -> Dict:
    response = requests.post(
        f"{settings.llm_base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Classify lead-intelligence social posts for Atlas Cloud. "
                        "Return only compact JSON matching the ClassifiedPost fields."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "raw_post": post.model_dump(mode="json"),
                            "rule_based_fallback": fallback.model_dump(mode="json"),
                        }
                    ),
                },
            ],
            "temperature": 0,
        },
        timeout=30,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def _combined_text(post: RawPost) -> str:
    return " ".join(
        [
            post.text or "",
            post.author_name or "",
            post.author_bio or "",
            post.username or "",
            post.matched_query or "",
        ]
    ).lower()


def _has_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)
