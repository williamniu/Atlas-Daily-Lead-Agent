"""Collector for the official X API recent search endpoint."""

import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import requests

from app.agents.query_planner import QuerySpec, build_x_query
from app.config import settings
from app.schemas import RawPost


RECENT_SEARCH_URL = "https://api.x.com/2/tweets/search/recent"
DEFAULT_MAX_RESULTS = 10
MAX_BACKOFF_SECONDS = 300


class MissingXBearerTokenError(RuntimeError):
    """Raised when X collection is requested without a bearer token."""


@dataclass(frozen=True)
class XRateLimit:
    """Rate limit metadata returned by X API response headers."""

    limit: Optional[int]
    remaining: Optional[int]
    reset: Optional[int]


@dataclass(frozen=True)
class XSearchResponse:
    """Normalized X search response with posts and rate limit metadata."""

    posts: List[RawPost]
    rate_limit: XRateLimit
    raw_json: Dict


def collect_recent_posts(
    query_specs: Iterable[QuerySpec],
    max_results: int = DEFAULT_MAX_RESULTS,
    request_session: Optional[requests.Session] = None,
    max_retries: int = 3,
) -> List[RawPost]:
    """Collect recent X posts for each query spec."""
    responses = search_recent_posts(
        query_specs=query_specs,
        max_results=max_results,
        request_session=request_session,
        max_retries=max_retries,
    )
    posts = []
    for response in responses:
        posts.extend(response.posts)
    return posts


def search_recent_posts(
    query_specs: Iterable[QuerySpec],
    max_results: int = DEFAULT_MAX_RESULTS,
    request_session: Optional[requests.Session] = None,
    max_retries: int = 3,
) -> List[XSearchResponse]:
    """Call X recent search for each query spec and normalize results."""
    if not settings.x_bearer_token:
        raise MissingXBearerTokenError(
            "X_BEARER_TOKEN is not configured. Use mock_loader when X API access is unavailable."
        )

    session = request_session or requests.Session()
    headers = {"Authorization": f"Bearer {settings.x_bearer_token}"}
    responses = []

    for query_spec in query_specs:
        response = _request_with_backoff(
            session=session,
            headers=headers,
            params=_build_recent_search_params(query_spec, max_results),
            max_retries=max_retries,
        )
        response.raise_for_status()
        payload = response.json()
        responses.append(
            XSearchResponse(
                posts=_normalize_recent_search_payload(payload, query_spec),
                rate_limit=_parse_rate_limit_headers(response.headers),
                raw_json=payload,
            )
        )

    return responses


def _build_recent_search_params(query_spec: QuerySpec, max_results: int) -> Dict[str, str]:
    bounded_max_results = min(100, max(10, max_results))
    return {
        "query": build_x_query(query_spec),
        "max_results": str(bounded_max_results),
        "expansions": "author_id",
        "tweet.fields": "author_id,created_at,public_metrics,lang,conversation_id,referenced_tweets",
        "user.fields": "username,name,description,public_metrics,verified,url",
    }


def _request_with_backoff(
    session: requests.Session,
    headers: Dict[str, str],
    params: Dict[str, str],
    max_retries: int,
) -> requests.Response:
    attempt = 0

    while True:
        response = session.get(RECENT_SEARCH_URL, headers=headers, params=params, timeout=30)
        if response.status_code != 429 or attempt >= max_retries:
            return response

        rate_limit = _parse_rate_limit_headers(response.headers)
        reset_sleep = _seconds_until_reset(rate_limit.reset)
        exponential_sleep = min(MAX_BACKOFF_SECONDS, 2**attempt)
        time.sleep(max(exponential_sleep, reset_sleep))
        attempt += 1


def _normalize_recent_search_payload(payload: Dict, query_spec: QuerySpec) -> List[RawPost]:
    users = {
        user.get("id"): user
        for user in payload.get("includes", {}).get("users", [])
        if user.get("id")
    }

    posts = []
    for tweet in payload.get("data", []) or []:
        author = users.get(tweet.get("author_id"), {})
        metrics = tweet.get("public_metrics") or {}
        author_metrics = author.get("public_metrics") or {}
        tweet_id = str(tweet.get("id", ""))

        posts.append(
            RawPost(
                source="x",
                post_id=tweet_id,
                post_url=_build_post_url(author.get("username"), tweet_id),
                text=tweet.get("text", ""),
                author_id=tweet.get("author_id"),
                username=author.get("username"),
                author_name=author.get("name"),
                author_bio=author.get("description"),
                followers_count=author_metrics.get("followers_count", 0),
                following_count=author_metrics.get("following_count", 0),
                like_count=metrics.get("like_count", 0),
                reply_count=metrics.get("reply_count", 0),
                repost_count=metrics.get("retweet_count", 0),
                quote_count=metrics.get("quote_count", 0),
                created_at=tweet.get("created_at"),
                matched_query=query_spec.query,
                raw_json={
                    "tweet": tweet,
                    "author": author,
                    "query_category": query_spec.category,
                    "intent_hypothesis": query_spec.intent_hypothesis,
                },
            )
        )

    return posts


def _build_post_url(username: Optional[str], post_id: str) -> Optional[str]:
    if not username or not post_id:
        return None
    return f"https://x.com/{username}/status/{post_id}"


def _parse_rate_limit_headers(headers: Dict[str, str]) -> XRateLimit:
    return XRateLimit(
        limit=_parse_optional_int(headers.get("x-rate-limit-limit")),
        remaining=_parse_optional_int(headers.get("x-rate-limit-remaining")),
        reset=_parse_optional_int(headers.get("x-rate-limit-reset")),
    )


def _parse_optional_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _seconds_until_reset(reset_timestamp: Optional[int]) -> int:
    if reset_timestamp is None:
        return 0
    return max(0, reset_timestamp - int(time.time()))
