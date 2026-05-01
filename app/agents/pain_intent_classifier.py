"""Rule-based pain and intent classification."""

from dataclasses import dataclass
from typing import Dict, List

from app.schemas import RawPost


PAIN_KEYWORDS: Dict[str, List[str]] = {
    "cost pain": ["cost", "pricing", "invoice", "bill", "margin", "spend", "expensive", "budget"],
    "fal.ai pricing pain": ["fal.ai pricing", "fal pricing", "fal.ai was easy", "fal.ai", "fal"],
    "reliability pain": [
        "reliability",
        "reliable",
        "stable",
        "unstable",
        "predictability",
        "stuck",
        "timeout",
        "timeouts",
        "fragile",
    ],
    "queue / latency": ["latency", "queue", "queued", "p95", "wait time", "slow", "cold start", "under 8s"],
    "rate limit": ["rate limit", "rate-limit", "429", "quota"],
    "failed generation": ["failed render", "failed generation", "failure", "fails", "retry", "retries"],
    "model coverage need": ["model coverage", "runway vs", "kling", "seedance", "veo", "route per use case"],
    "one API need": ["one api", "single api", "provider abstraction", "routing layer", "one infra layer"],
    "scale need": ["scale", "scaling", "batch", "batches", "volume", "throughput", "many users", "monthly active"],
}

BUYING_INTENT_KEYWORDS = [
    "need",
    "looking for",
    "evaluating",
    "vendor",
    "provider",
    "invoice",
    "before launch",
    "opening self-serve",
    "production",
    "launch week",
    "route",
    "fallback",
]

CONTACTABILITY_KEYWORDS = ["founder", "dm", "email", "hiring", "builder", "agency", "studio"]
SCALE_KEYWORDS = ["1m", "600k", "120k", "many users", "monthly active", "countries", "exports", "generated clips"]


@dataclass(frozen=True)
class PainIntentResult:
    """Detected pain, intent, and supporting signals."""

    intent_type: str
    pain_types: List[str]
    scale_signals: List[str]
    contactability_signals: List[str]


def classify_pain_and_intent(post: RawPost) -> PainIntentResult:
    """Detect pain and intent signals from a raw post."""
    text = _combined_text(post)
    pain_types = [
        pain_type
        for pain_type, keywords in PAIN_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]

    intent_type = _detect_intent_type(text, pain_types)
    return PainIntentResult(
        intent_type=intent_type,
        pain_types=_dedupe(pain_types),
        scale_signals=_matched_keywords(text, SCALE_KEYWORDS),
        contactability_signals=_matched_keywords(text, CONTACTABILITY_KEYWORDS),
    )


def _detect_intent_type(text: str, pain_types: List[str]) -> str:
    if any(keyword in text for keyword in BUYING_INTENT_KEYWORDS) and pain_types:
        return "buying intent"
    if pain_types:
        return "technical pain"
    return "casual mention"


def _combined_text(post: RawPost) -> str:
    return " ".join(
        [
            post.text or "",
            post.author_name or "",
            post.author_bio or "",
            post.matched_query or "",
        ]
    ).lower()


def _matched_keywords(text: str, keywords: List[str]) -> List[str]:
    return [keyword for keyword in keywords if keyword in text]


def _dedupe(items: List[str]) -> List[str]:
    deduped = []
    seen = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped
