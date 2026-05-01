"""Query planning utilities for X/Twitter collection."""

from pathlib import Path
from typing import Any, Iterable, List, Sequence, Union

import yaml
from pydantic import BaseModel, Field, field_validator


DEFAULT_QUERY_PATH = Path("data/queries.yaml")
X_QUERY_MAX_LENGTH = 512


class QuerySpec(BaseModel):
    """Search query specification for X/Twitter collection."""

    query: str
    category: str = "general"
    priority: int = Field(default=50, ge=0, le=100)
    intent_hypothesis: str = ""
    include_keywords: List[str] = Field(default_factory=list)
    exclude_keywords: List[str] = Field(default_factory=list)
    language: str = "en"

    @field_validator("query", "category", "language")
    @classmethod
    def required_text_cannot_be_empty(cls, value: str) -> str:
        """Validate required text fields."""
        if not value or not value.strip():
            raise ValueError("field cannot be empty")
        return value.strip()


def load_query_specs(path: Union[str, Path] = DEFAULT_QUERY_PATH) -> List[QuerySpec]:
    """Load query specs from YAML.

    Supports both the current MVP format:

    include:
      - "AI video generator apps"
    exclude:
      - "enterprise"

    and a future structured format:

    queries:
      - query: "AI video generator apps"
        category: "icp"
    """
    yaml_path = Path(path)
    payload = yaml.safe_load(yaml_path.read_text()) or {}

    if isinstance(payload, list):
        return [_coerce_query_spec(item) for item in payload]

    if "queries" in payload:
        return [_coerce_query_spec(item) for item in payload.get("queries", [])]

    include_terms = payload.get("include", [])
    exclude_terms = payload.get("exclude", [])

    return [
        QuerySpec(
            query=term,
            category=_category_from_query(term),
            priority=50,
            intent_hypothesis=f"Find lead signals related to {term}.",
            include_keywords=[term],
            exclude_keywords=list(exclude_terms),
            language="en",
        )
        for term in include_terms
    ]


def build_x_query(query_spec: QuerySpec, max_length: int = X_QUERY_MAX_LENGTH) -> str:
    """Build an X/Twitter search query that respects length limits."""
    query_spec = QuerySpec.model_validate(query_spec)
    required_terms = [_format_term(query_spec.query)]
    include_terms = [
        _format_term(term)
        for term in _dedupe(query_spec.include_keywords)
        if term.strip() and term.strip() != query_spec.query
    ]
    exclude_terms = [f"-{_format_term(term)}" for term in _dedupe(query_spec.exclude_keywords) if term.strip()]
    operators = _build_required_operators(query_spec)

    return _fit_query(required_terms, include_terms, exclude_terms, operators, max_length)


def _coerce_query_spec(item: Any) -> QuerySpec:
    if isinstance(item, str):
        return QuerySpec(
            query=item,
            category=_category_from_query(item),
            intent_hypothesis=f"Find lead signals related to {item}.",
            include_keywords=[item],
        )
    if isinstance(item, dict):
        return QuerySpec.model_validate(item)
    raise ValueError(f"Unsupported query spec item: {item!r}")


def _build_required_operators(query_spec: QuerySpec) -> List[str]:
    operators = []
    language = query_spec.language.strip().lower() or "en"

    if not _contains_operator(query_spec.query, "lang:"):
        operators.append(f"lang:{language}")
    if not _contains_operator(query_spec.query, "is:retweet"):
        operators.append("-is:retweet")
    if _should_exclude_replies(query_spec) and not _contains_operator(query_spec.query, "is:reply"):
        operators.append("-is:reply")

    return operators


def _fit_query(
    required_terms: List[str],
    include_terms: List[str],
    exclude_terms: List[str],
    operators: List[str],
    max_length: int,
) -> str:
    optional_excludes = list(exclude_terms)
    optional_includes = list(include_terms)

    parts = required_terms + optional_includes + optional_excludes + operators
    while len(_join(parts)) > max_length and optional_excludes:
        optional_excludes.pop()
        parts = required_terms + optional_includes + optional_excludes + operators

    while len(_join(parts)) > max_length and optional_includes:
        optional_includes.pop()
        parts = required_terms + optional_includes + optional_excludes + operators

    query = _join(parts)
    if len(query) <= max_length:
        return query

    operator_suffix = _join(operators)
    suffix_length = len(operator_suffix) + 1 if operator_suffix else 0
    available = max(1, max_length - suffix_length)
    truncated_required = required_terms[0][:available].rstrip()
    return _join([truncated_required] + operators)


def _should_exclude_replies(query_spec: QuerySpec) -> bool:
    reply_context = " ".join(
        [
            query_spec.query,
            query_spec.category,
            query_spec.intent_hypothesis,
        ]
    ).lower()
    return not any(term in reply_context for term in ["reply", "replies", "conversation", "support thread"])


def _contains_operator(query: str, operator: str) -> bool:
    query_lower = query.lower()
    operator_lower = operator.lower()
    return operator_lower in query_lower or f"-{operator_lower}" in query_lower


def _format_term(term: str) -> str:
    cleaned = term.strip().replace('"', '\\"')
    if not cleaned:
        return cleaned
    if _looks_like_operator(cleaned) or cleaned.startswith("("):
        return cleaned
    if " " in cleaned:
        return f'"{cleaned}"'
    return cleaned


def _looks_like_operator(term: str) -> bool:
    operator_prefixes = ("lang:", "is:", "-is:", "from:", "to:", "url:", "since:", "until:")
    return term.startswith(operator_prefixes)


def _dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    deduped = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(item.strip())
    return deduped


def _category_from_query(query: str) -> str:
    return query.lower().replace("/", " ").replace("-", " ").replace(" ", "_")


def _join(parts: Sequence[str]) -> str:
    return " ".join(part for part in parts if part)
