"""Mock data loader for local demos and tests."""

import json
from pathlib import Path
from typing import List, Optional, Union

from app.schemas import RawPost


DEFAULT_SAMPLE_POSTS_PATH = Path("data/sample_posts.jsonl")


def load_mock_posts(
    path: Union[str, Path] = DEFAULT_SAMPLE_POSTS_PATH,
    query_category: Optional[str] = None,
) -> List[RawPost]:
    """Load synthetic posts from JSONL and normalize them into RawPost objects."""
    posts_path = Path(path)
    posts = []

    for line in posts_path.read_text().splitlines():
        if not line.strip():
            continue

        record = json.loads(line)
        if query_category and not _matches_query_category(record, query_category):
            continue

        posts.append(RawPost.model_validate(record))

    return posts


def _matches_query_category(record: dict, query_category: str) -> bool:
    expected = query_category.strip().lower()
    raw_json = record.get("raw_json") or {}
    candidates = [
        raw_json.get("category"),
        record.get("matched_query"),
        record.get("category"),
    ]

    return any(str(candidate).strip().lower() == expected for candidate in candidates if candidate)
