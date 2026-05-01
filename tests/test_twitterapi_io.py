"""Tests for TwitterAPI.io normalization."""

from app.agents.query_planner import QuerySpec
from app.collectors.twitterapi_io import _normalize_payload


def test_normalize_payload_parses_twitter_datetime_format() -> None:
    payload = {
        "tweets": [
            {
                "id": "123",
                "url": "https://x.com/example/status/123",
                "text": "Testing AI video app latency.",
                "createdAt": "Mon Dec 29 07:11:53 +0000 2025",
                "likeCount": 3,
                "replyCount": 1,
                "retweetCount": 2,
                "quoteCount": 0,
                "author": {
                    "id": "user_123",
                    "userName": "example",
                    "name": "Example",
                    "description": "AI video app builder.",
                    "followers": 100,
                    "following": 50,
                },
            }
        ]
    }

    posts = _normalize_payload(payload, QuerySpec(query="AI video generator apps"), max_results=10)

    assert len(posts) == 1
    assert posts[0].created_at.year == 2025
    assert posts[0].created_at.month == 12
    assert posts[0].created_at.tzinfo is not None
