"""Tests for the mock post loader."""

import json
from pathlib import Path

from app.collectors.mock_loader import load_mock_posts
from app.schemas import RawPost


def test_load_mock_posts_from_sample_file() -> None:
    posts = load_mock_posts()

    assert len(posts) >= 40
    assert all(isinstance(post, RawPost) for post in posts)
    assert posts[0].source == "x"
    assert posts[0].post_id


def test_load_mock_posts_filters_by_raw_json_category() -> None:
    posts = load_mock_posts(query_category="pricing_pain")

    assert posts
    assert all(post.raw_json.get("category") == "pricing_pain" for post in posts)


def test_load_mock_posts_filters_by_matched_query(tmp_path: Path) -> None:
    sample_file = tmp_path / "posts.jsonl"
    records = [
        {
            "source": "x",
            "post_id": "p1",
            "post_url": "https://x.com/a/status/p1",
            "text": "AI video generation pricing hurts.",
            "author_id": "u1",
            "username": "creator",
            "author_name": "Creator",
            "author_bio": "Builder",
            "followers_count": 10,
            "following_count": 5,
            "like_count": 1,
            "reply_count": 0,
            "repost_count": 0,
            "quote_count": 0,
            "created_at": "2026-05-01T10:00:00Z",
            "matched_query": "fal.ai pricing pain",
            "raw_json": {"synthetic": True},
        },
        {
            "source": "x",
            "post_id": "p2",
            "post_url": "https://x.com/b/status/p2",
            "text": "Unrelated update.",
            "author_id": "u2",
            "username": "other",
            "author_name": "Other",
            "author_bio": "Notes",
            "followers_count": 10,
            "following_count": 5,
            "like_count": 1,
            "reply_count": 0,
            "repost_count": 0,
            "quote_count": 0,
            "created_at": "2026-05-01T10:00:00Z",
            "matched_query": "irrelevant",
            "raw_json": {"synthetic": True},
        },
    ]
    sample_file.write_text("\n".join(json.dumps(record) for record in records))

    posts = load_mock_posts(sample_file, query_category="fal.ai pricing pain")

    assert len(posts) == 1
    assert posts[0].post_id == "p1"
