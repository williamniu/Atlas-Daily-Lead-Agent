"""Rule-based competitor and model mention detection."""

from dataclasses import dataclass
from typing import Dict, List, Set

from app.schemas import RawPost


COMPETITOR_KEYWORDS: Dict[str, List[str]] = {
    "fal.ai": ["fal.ai", "fal ai", "fal"],
    "Replicate": ["replicate"],
    "Runway": ["runway", "runwayml"],
    "Pika": ["pika"],
    "Luma": ["luma", "dream machine"],
    "Kling": ["kling"],
    "Seedance": ["seedance"],
    "Wan": ["wan 2", "wan2", "wan video"],
    "Veo": ["veo", "google veo"],
    "Hailuo": ["hailuo"],
    "Vidu": ["vidu"],
    "OpenRouter": ["openrouter"],
    "RunPod": ["runpod"],
    "Modal": ["modal"],
    "Fireworks": ["fireworks.ai", "fireworks ai", "fireworks"],
    "Together": ["together.ai", "together ai", "together"],
}

COMPETITOR_OFFICIAL_HANDLES = {
    "fal",
    "replicate",
    "runway",
    "runwayml",
    "pika_labs",
    "luma_ai",
    "kling_ai",
    "openrouterai",
    "runpod_io",
    "modal_labs",
    "fireworksai",
    "togethercompute",
}


@dataclass(frozen=True)
class CompetitorDetection:
    """Detected competitors and official-account status."""

    competitors: List[str]
    model_mentions: List[str]
    is_competitor_official: bool


def detect_competitors(post: RawPost) -> CompetitorDetection:
    """Detect competitor and model mentions in a raw post."""
    text = _combined_text(post)
    competitors = []

    for competitor, keywords in COMPETITOR_KEYWORDS.items():
        if any(_contains_keyword(text, keyword) for keyword in keywords):
            competitors.append(competitor)

    username = (post.username or "").strip().lower()
    author_name = (post.author_name or "").strip().lower()
    is_official = username in COMPETITOR_OFFICIAL_HANDLES or any(
        name.lower() == author_name for name in competitors
    )

    return CompetitorDetection(
        competitors=competitors,
        model_mentions=_model_mentions_from_competitors(competitors),
        is_competitor_official=is_official,
    )


def _model_mentions_from_competitors(competitors: List[str]) -> List[str]:
    model_like: Set[str] = set()
    for competitor in competitors:
        if competitor in {"Runway", "Pika", "Luma", "Kling", "Seedance", "Wan", "Veo", "Hailuo", "Vidu"}:
            model_like.add(competitor)
    return sorted(model_like)


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


def _contains_keyword(text: str, keyword: str) -> bool:
    return keyword.lower() in text
