"""Collector for TwitterAPI.io advanced search."""

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

from dateutil import parser as date_parser
import requests

from app.agents.query_planner import QuerySpec, build_x_query
from app.config import settings
from app.schemas import RawPost


ADVANCED_SEARCH_PATH = "/twitter/tweet/advanced_search"
DEFAULT_MAX_RESULTS = 50
MAX_BACKOFF_SECONDS = 120


class MissingTwitterApiIoKeyError(RuntimeError):
    """Raised when TwitterAPI.io collection is requested without an API key."""


@dataclass(frozen=True)
class TwitterApiIoSearchResponse:
    """Normalized TwitterAPI.io response."""

    posts: List[RawPost]
    raw_json: Dict


def collect_recent_posts(
    query_specs: Iterable[QuerySpec],
    max_results: int = DEFAULT_MAX_RESULTS,
    request_session: Optional[requests.Session] = None,
    max_retries: int = 3,
) -> List[RawPost]:
    """Collect recent X/Twitter posts through TwitterAPI.io."""
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
) -> List[TwitterApiIoSearchResponse]:
    """Call TwitterAPI.io advanced search for each query spec."""
    if not settings.twitterapi_io_api_key:
        raise MissingTwitterApiIoKeyError(
            "TWITTERAPI_IO_API_KEY is not configured. Use mock_loader or configure TwitterAPI.io for live demo data."
        )

    session = request_session or requests.Session()
    headers = {"X-API-Key": settings.twitterapi_io_api_key}
    responses = []

    for query_spec in query_specs:
        response = _request_with_backoff(
            session=session,
            headers=headers,
            params={
                "query": build_x_query(query_spec),
                "queryType": "Latest",
            },
            max_retries=max_retries,
        )
        response.raise_for_status()
        payload = response.json()
        posts = _normalize_payload(payload, query_spec, max_results=max_results)
        responses.append(TwitterApiIoSearchResponse(posts=posts, raw_json=payload))

    return responses


def _request_with_backoff(
    session: requests.Session,
    headers: Dict[str, str],
    params: Dict[str, str],
    max_retries: int,
) -> requests.Response:
    attempt = 0
    while True:
        response = session.get(_advanced_search_url(), headers=headers, params=params, timeout=30)
        if response.status_code != 429 or attempt >= max_retries:
            return response
        retry_after = _parse_retry_after(response.headers.get("retry-after"))
        exponential_sleep = min(MAX_BACKOFF_SECONDS, 2**attempt)
        time.sleep(max(retry_after, exponential_sleep))
        attempt += 1


def _normalize_payload(payload: Dict, query_spec: QuerySpec, max_results: int) -> List[RawPost]:
    posts = []
    for tweet in (payload.get("tweets") or [])[:max_results]:
        author = tweet.get("author") or {}
        tweet_id = str(tweet.get("id") or "")
        if not tweet_id:
            continue
        posts.append(
            RawPost(
                source="twitterapi_io",
                post_id=tweet_id,
                post_url=tweet.get("url") or _build_post_url(author.get("userName"), tweet_id),
                text=tweet.get("text") or "",
                author_id=str(author.get("id") or "") or None,
                username=author.get("userName"),
                author_name=author.get("name"),
                author_bio=author.get("description"),
                followers_count=author.get("followers") or 0,
                following_count=author.get("following") or 0,
                like_count=tweet.get("likeCount") or 0,
                reply_count=tweet.get("replyCount") or 0,
                repost_count=tweet.get("retweetCount") or 0,
                quote_count=tweet.get("quoteCount") or 0,
                created_at=_parse_twitter_datetime(tweet.get("createdAt")),
                matched_query=query_spec.query,
                raw_json={
                    "tweet": tweet,
                    "author": author,
                    "query_category": query_spec.category,
                    "intent_hypothesis": query_spec.intent_hypothesis,
                    "provider": "twitterapi_io",
                },
            )
        )
    return posts


def _build_post_url(username: Optional[str], post_id: str) -> Optional[str]:
    if not username or not post_id:
        return None
    return f"https://x.com/{username}/status/{post_id}"


def _advanced_search_url() -> str:
    base_url = (settings.twitterapi_io_base_url or "https://api.twitterapi.io").rstrip("/")
    return f"{base_url}{ADVANCED_SEARCH_PATH}"


def _parse_retry_after(value: Optional[str]) -> int:
    if value is None:
        return 0
    try:
        return max(0, int(value))
    except ValueError:
        return 0


def _parse_twitter_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    parsed = date_parser.parse(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
