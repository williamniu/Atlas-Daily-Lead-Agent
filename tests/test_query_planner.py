"""Tests for X/Twitter query planning."""

from pathlib import Path

from app.agents.query_planner import QuerySpec, build_x_query, load_query_specs


def test_load_query_specs_from_existing_yaml() -> None:
    specs = load_query_specs("data/queries.yaml")

    assert specs
    assert all(isinstance(spec, QuerySpec) for spec in specs)
    assert specs[0].language == "en"
    assert "enterprise" in specs[0].exclude_keywords


def test_load_query_specs_from_structured_yaml(tmp_path: Path) -> None:
    query_file = tmp_path / "queries.yaml"
    query_file.write_text(
        """
queries:
  - query: "AI video generator apps"
    category: "icp"
    priority: 90
    intent_hypothesis: "Find app teams with production inference pain."
    include_keywords:
      - "latency"
    exclude_keywords:
      - "enterprise"
    language: "en"
""".strip()
    )

    specs = load_query_specs(query_file)

    assert len(specs) == 1
    assert specs[0].priority == 90
    assert specs[0].include_keywords == ["latency"]


def test_build_x_query_adds_required_filters() -> None:
    spec = QuerySpec(
        query="AI video generator apps",
        category="icp",
        include_keywords=["latency"],
        exclude_keywords=["enterprise"],
    )

    query = build_x_query(spec)

    assert '"AI video generator apps"' in query
    assert "latency" in query
    assert "-enterprise" in query
    assert "lang:en" in query
    assert "-is:retweet" in query
    assert "-is:reply" in query


def test_build_x_query_keeps_replies_when_appropriate() -> None:
    spec = QuerySpec(
        query="fal.ai timeout handling",
        category="support replies",
        intent_hypothesis="Find useful reply threads from builders.",
    )

    query = build_x_query(spec)

    assert "-is:retweet" in query
    assert "-is:reply" not in query


def test_build_x_query_trims_optional_excludes_to_length_limit() -> None:
    spec = QuerySpec(
        query="AI video generator apps",
        category="icp",
        include_keywords=["latency"],
        exclude_keywords=[
            "enterprise procurement",
            "Fortune 500",
            "long compliance review",
            "global vendor assessment",
        ],
    )

    query = build_x_query(spec, max_length=95)

    assert len(query) <= 95
    assert "lang:en" in query
    assert "-is:retweet" in query
    assert "-is:reply" in query
    assert "latency" in query
    assert '"global vendor assessment"' not in query
