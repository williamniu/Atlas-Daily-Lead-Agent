"""Lead scoring logic for classified lead signals."""

from typing import List, Tuple

from app.agents.outreach_angle import build_outreach_angle
from app.schemas import ClassifiedPost, Lead, LeadScoreBreakdown, RawPost


TOP_REVENUE_LEAD = "Top Revenue Lead"
STRONG_LEAD = "Strong Lead"
WATCHLIST = "Watchlist"
DISTRIBUTION_WEAK_LEAD = "Distribution / Weak Lead"
NOT_QUALIFIED = "Not Qualified"


def score_lead(raw_post: RawPost, classified_post: ClassifiedPost) -> Lead:
    """Score a classified post and return a Lead."""
    reason_codes: List[str] = []
    scale_potential = _score_scale_potential(raw_post, classified_post, reason_codes)
    atlas_fit = _score_atlas_fit(classified_post, reason_codes)
    cost_reliability_pain = _score_cost_reliability_pain(classified_post, reason_codes)
    buying_intent = _score_buying_intent(classified_post, reason_codes)
    contactability = _score_contactability(raw_post, classified_post)
    penalty_score, penalty_codes = _score_penalties(raw_post, classified_post)
    reason_codes.extend(penalty_codes)

    if classified_post.is_kol_distribution:
        reason_codes.append("KOL_DISTRIBUTION")

    total = scale_potential + atlas_fit + cost_reliability_pain + buying_intent + contactability - penalty_score
    if "PURE_NEWS" in penalty_codes:
        total = min(total, 35)
    total = max(0, min(100, total))
    bucket = _lead_bucket(total, classified_post)

    score_breakdown = LeadScoreBreakdown(
        fit_score=atlas_fit,
        intent_score=buying_intent,
        pain_score=cost_reliability_pain,
        scale_score=scale_potential,
        contactability_score=contactability,
        timing_score=0,
        penalty_score=penalty_score,
    )
    outreach_angle = build_outreach_angle(raw_post, classified_post, score_breakdown)

    return Lead(
        lead_id=f"{raw_post.source}:{raw_post.post_id}",
        post_id=raw_post.post_id,
        username=raw_post.username,
        display_name=raw_post.author_name,
        company_or_product=_infer_company_or_product(raw_post),
        segment=classified_post.segment,
        score=total,
        score_breakdown=score_breakdown,
        reason_codes=_dedupe(reason_codes),
        evidence=_build_evidence(raw_post, classified_post),
        atlas_pitch_angle=outreach_angle.atlas_pitch_angle,
        recommended_outreach=outreach_angle.recommended_outreach,
        lead_bucket=bucket,
        source_url=raw_post.post_url,
    )


def score_leads(pairs: List[Tuple[RawPost, ClassifiedPost]]) -> List[Lead]:
    """Score multiple raw/classified post pairs."""
    return [score_lead(raw_post, classified_post) for raw_post, classified_post in pairs]


def _score_scale_potential(raw_post: RawPost, classified_post: ClassifiedPost, reason_codes: List[str]) -> float:
    score = 0.0
    if classified_post.segment == "Creator platform with many users":
        score = 30
        reason_codes.append("CREATOR_PLATFORM_SCALE")
    elif classified_post.scale_signals or raw_post.followers_count >= 50000:
        score = 24
        reason_codes.append("VIDEO_GEN_SCALE")
    elif raw_post.followers_count >= 10000:
        score = 16
    elif classified_post.is_kol_distribution:
        score = 12
    else:
        score = 8
    return score


def _score_atlas_fit(classified_post: ClassifiedPost, reason_codes: List[str]) -> float:
    segment_scores = {
        "AI-native creator platform": (25, "HIGGSFIELD_LIKE_PLATFORM"),
        "Creator platform with many users": (25, "CREATOR_PLATFORM_SCALE"),
        "iOS/mobile AI media app": (23, "IOS_AI_MEDIA_APP"),
        "AI video generator app": (24, "AI_VIDEO_GENERATOR_APP"),
        "Digital marketing agency": (20, "DIGITAL_MARKETING_AGENCY"),
        "Short-form video producer": (18, "SHORT_FORM_VIDEO_PRODUCER"),
        "KOL / distribution partner": (12, "KOL_DISTRIBUTION"),
        "Enterprise, excluded": (8, "ENTERPRISE_EXCLUDED"),
    }
    score, code = segment_scores.get(classified_post.segment, (0, None))
    if code:
        reason_codes.append(code)
    return score


def _score_cost_reliability_pain(classified_post: ClassifiedPost, reason_codes: List[str]) -> float:
    score = 0.0
    pain_types = set(classified_post.pain_types)

    if "fal.ai pricing pain" in pain_types:
        score += 10
        reason_codes.append("FAL_PRICING_PAIN")
    if classified_post.competitors and pain_types:
        score += 4
        reason_codes.append("COMPETITOR_PAIN")
    if "cost pain" in pain_types:
        score += 5
    if "reliability pain" in pain_types:
        score += 6
        reason_codes.append("RELIABILITY_PAIN")
    if "queue / latency" in pain_types:
        score += 6
        reason_codes.append("QUEUE_LATENCY_PAIN")
    if "model coverage need" in pain_types:
        score += 4
        reason_codes.append("MODEL_COVERAGE_NEED")
    if "one API need" in pain_types:
        score += 4
        reason_codes.append("ONE_API_NEED")
        reason_codes.append("IMAGE_VIDEO_API_NEED")

    return min(20, score)


def _score_buying_intent(classified_post: ClassifiedPost, reason_codes: List[str]) -> float:
    if classified_post.intent_type == "buying intent":
        reason_codes.append("PRODUCTION_WORKLOAD")
        return 15
    if classified_post.intent_type == "technical pain":
        return 9
    return 2


def _score_contactability(raw_post: RawPost, classified_post: ClassifiedPost) -> float:
    score = 0.0
    if raw_post.username:
        score += 3
    if raw_post.author_name:
        score += 2
    if raw_post.author_bio:
        score += 2
    if classified_post.contactability_signals:
        score += 3
    return min(10, score)


def _score_penalties(raw_post: RawPost, classified_post: ClassifiedPost) -> Tuple[float, List[str]]:
    penalty = 0.0
    codes = []
    text = " ".join([raw_post.text or "", raw_post.author_bio or "", raw_post.matched_query or ""]).lower()

    if classified_post.is_enterprise:
        penalty += 20
        codes.append("ENTERPRISE_EXCLUDED")
    if classified_post.is_competitor_official:
        penalty += 30
        codes.append("COMPETITOR_OFFICIAL")
    if _looks_like_pure_news(text, classified_post):
        penalty += 15
        codes.append("PURE_NEWS")
    if classified_post.intent_type == "casual mention" and classified_post.segment in {
        "Irrelevant",
        "KOL / distribution partner",
        "Short-form video producer",
    }:
        penalty += 10

    return min(75, penalty), codes


def _looks_like_pure_news(text: str, classified_post: ClassifiedPost) -> bool:
    news_markers = ["news:", "funding", "raised", "raises", "analysis", "market", "announced"]
    return any(marker in text for marker in news_markers) and classified_post.intent_type == "casual mention"


def _lead_bucket(score: float, classified_post: ClassifiedPost) -> str:
    if classified_post.is_enterprise or classified_post.is_competitor_official:
        return NOT_QUALIFIED
    if classified_post.is_kol_distribution:
        return DISTRIBUTION_WEAK_LEAD if score >= 40 else NOT_QUALIFIED
    if score >= 85:
        return TOP_REVENUE_LEAD
    if score >= 70:
        return STRONG_LEAD
    if score >= 55:
        return WATCHLIST
    if score >= 40:
        return DISTRIBUTION_WEAK_LEAD
    return NOT_QUALIFIED


def _infer_company_or_product(raw_post: RawPost) -> str:
    return raw_post.author_name or raw_post.username or "Unknown"


def _build_evidence(raw_post: RawPost, classified_post: ClassifiedPost) -> List[str]:
    evidence = [raw_post.text]
    if classified_post.classification_reason:
        evidence.append(classified_post.classification_reason)
    return evidence


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped
