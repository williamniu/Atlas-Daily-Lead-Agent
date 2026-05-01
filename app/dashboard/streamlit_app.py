"""Streamlit dashboard for Atlas Daily Lead Agent."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.query_planner import load_query_specs
from app.config import settings
from app.db.database import normalize_database_url


OUTPUT_DIR = Path("outputs")
OVERVIEW_CHART_HEIGHT = 420
LEAD_COLUMNS = [
    "score",
    "lead_bucket",
    "company_or_product",
    "username",
    "segment",
    "pain_types",
    "competitors",
    "reason_codes",
    "atlas_pitch_angle",
    "recommended_outreach",
    "source_url",
]


st.set_page_config(page_title="Atlas Daily Lead Agent", layout="wide")


@st.cache_data(ttl=120)
def load_dashboard_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    """Load dashboard data from database, falling back to exported CSV files."""
    try:
        leads_df, runs_df = _load_from_database()
        if not leads_df.empty:
            return leads_df, runs_df, _query_performance_from_database(), "database"
    except Exception as exc:
        st.session_state["dashboard_data_warning"] = str(exc)

    leads_df = _load_from_csv_exports()
    return leads_df, pd.DataFrame(), _query_performance_from_csv(leads_df), "csv"


def _load_from_database() -> Tuple[pd.DataFrame, pd.DataFrame]:
    engine = create_engine(normalize_database_url(settings.effective_database_url), pool_pre_ping=True)

    leads_query = text(
        """
        WITH latest_classified AS (
            SELECT cp.*
            FROM classified_posts cp
            JOIN (
                SELECT post_id, MAX(id) AS id
                FROM classified_posts
                GROUP BY post_id
            ) latest ON cp.id = latest.id
        )
        SELECT
            l.score,
            l.lead_bucket,
            l.company_or_product,
            l.username,
            l.segment,
            l.reason_codes,
            l.atlas_pitch_angle,
            l.recommended_outreach,
            l.source_url,
            l.post_id,
            lc.pain_types,
            lc.competitors,
            lc.model_mentions,
            lc.intent_type,
            lc.is_enterprise,
            lc.is_competitor_official,
            lc.is_kol_distribution
        FROM leads l
        LEFT JOIN latest_classified lc ON l.post_id = lc.post_id
        ORDER BY l.score DESC
        """
    )
    runs_query = text(
        """
        SELECT
            run_id,
            started_at,
            completed_at,
            app_env,
            use_mock_data,
            raw_post_count,
            classified_post_count,
            lead_count,
            notes
        FROM runs
        ORDER BY id DESC
        LIMIT 25
        """
    )

    with engine.connect() as connection:
        leads_df = pd.read_sql(leads_query, connection)
        runs_df = pd.read_sql(runs_query, connection)

    return _normalize_lead_dataframe(leads_df), _normalize_runs_dataframe(runs_df)


def _query_performance_from_database() -> pd.DataFrame:
    engine = create_engine(normalize_database_url(settings.effective_database_url), pool_pre_ping=True)
    query = text(
        """
        SELECT
            rp.matched_query AS query,
            COUNT(DISTINCT rp.post_id) AS posts_collected,
            COUNT(DISTINCT CASE WHEN l.score >= 55 THEN l.lead_id END) AS qualified_leads,
            AVG(l.score) AS average_score
        FROM raw_posts rp
        LEFT JOIN leads l ON rp.post_id = l.post_id
        GROUP BY rp.matched_query
        ORDER BY qualified_leads DESC, posts_collected DESC
        """
    )
    with engine.connect() as connection:
        df = pd.read_sql(query, connection)

    category_map = {spec.query: spec.category for spec in load_query_specs()}
    df["category"] = df["query"].map(category_map).fillna("unknown")
    df["average_score"] = df["average_score"].fillna(0).round(1)
    return df[["query", "category", "posts_collected", "qualified_leads", "average_score"]]


def _load_from_csv_exports() -> pd.DataFrame:
    csv_files = [
        OUTPUT_DIR / "top_revenue_leads.csv",
        OUTPUT_DIR / "fal_displacement_leads.csv",
        OUTPUT_DIR / "creator_platform_watchlist.csv",
        OUTPUT_DIR / "distribution_kol_leads.csv",
    ]
    frames = []
    for path in csv_files:
        if path.exists():
            frame = pd.read_csv(path)
            frame["csv_source"] = path.name
            frames.append(frame)

    if not frames:
        return _empty_leads_df()

    df = pd.concat(frames, ignore_index=True)
    if "source_url" in df.columns:
        df = df.drop_duplicates(subset=["source_url"], keep="first")
    return _normalize_lead_dataframe(df)


def _normalize_lead_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return _empty_leads_df()

    for column in LEAD_COLUMNS:
        if column not in df.columns:
            df[column] = "" if column != "score" else 0

    df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0)
    for column in ["reason_codes", "pain_types", "competitors"]:
        df[column] = df[column].apply(_stringify_list_value)
    df["lead_bucket"] = df["lead_bucket"].fillna("Not Qualified")
    df["segment"] = df["segment"].fillna("Unknown")
    df["company_or_product"] = df["company_or_product"].fillna("")
    df["username"] = df["username"].fillna("")
    df["atlas_pitch_angle"] = df["atlas_pitch_angle"].fillna("")
    df["recommended_outreach"] = df["recommended_outreach"].fillna("")
    df["source_url"] = df["source_url"].fillna("")
    return df.sort_values("score", ascending=False)


def _normalize_runs_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df["status"] = df["completed_at"].apply(lambda value: "completed" if pd.notna(value) else "running")
    return df


def _empty_leads_df() -> pd.DataFrame:
    return pd.DataFrame(columns=LEAD_COLUMNS)


def _query_performance_from_csv(leads_df: pd.DataFrame) -> pd.DataFrame:
    if leads_df.empty:
        return pd.DataFrame(columns=["query", "category", "posts_collected", "qualified_leads", "average_score"])

    grouped = (
        leads_df.groupby("segment", dropna=False)
        .agg(
            posts_collected=("segment", "size"),
            qualified_leads=("score", lambda scores: int((scores >= 55).sum())),
            average_score=("score", "mean"),
        )
        .reset_index()
        .rename(columns={"segment": "query"})
    )
    grouped["category"] = grouped["query"].str.lower().str.replace(" ", "_", regex=False)
    grouped["average_score"] = grouped["average_score"].round(1)
    return grouped[["query", "category", "posts_collected", "qualified_leads", "average_score"]]


def render_kpi_cards(leads_df: pd.DataFrame, query_df: pd.DataFrame) -> None:
    total_posts = int(query_df["posts_collected"].sum()) if not query_df.empty else len(leads_df)
    qualified = int((leads_df["score"] >= 55).sum()) if not leads_df.empty else 0
    top_revenue = int((leads_df["lead_bucket"] == "Top Revenue Lead").sum()) if not leads_df.empty else 0
    fal_displacement = len(_fal_displacement_df(leads_df))
    mobile = len(_mobile_app_df(leads_df))
    agency = len(_agency_df(leads_df))
    creator = len(_creator_platform_df(leads_df))
    enterprise = int(leads_df["reason_codes"].str.contains("ENTERPRISE_EXCLUDED", na=False).sum()) if not leads_df.empty else 0

    metrics = [
        ("Daily Posts Scanned", total_posts),
        ("Qualified Leads", qualified),
        ("Top Revenue Leads", top_revenue),
        ("Fal Displacement Leads", fal_displacement),
        ("iOS / Mobile App Leads", mobile),
        ("Agency / Marketing Leads", agency),
        ("Creator Platform Leads", creator),
        ("Enterprise Excluded", enterprise),
    ]

    columns = st.columns(4)
    for index, (label, value) in enumerate(metrics):
        with columns[index % 4]:
            st.metric(label, value)


def render_overview(leads_df: pd.DataFrame, query_df: pd.DataFrame) -> None:
    render_kpi_cards(leads_df, query_df)
    st.divider()

    st.subheader("Segment Distribution")
    _render_bar_chart(_count_by(leads_df, "segment"), "segment", "#2563eb", label_angle=-50)

    st.subheader("Lead Bucket Distribution")
    _render_bar_chart(_count_by(leads_df, "lead_bucket"), "lead_bucket", "#059669", label_angle=0)

    st.subheader("Competitor Mentions")
    _render_bar_chart(_competitor_counts(leads_df), "competitor", "#d97706", label_angle=0)


def render_lead_table(title: str, df: pd.DataFrame, key: str, highlight: Optional[str] = None) -> None:
    st.subheader(title)
    if highlight:
        st.caption(highlight)
    if df.empty:
        st.info("No leads in this view yet.")
        return

    display_columns = [
        "score",
        "company_or_product",
        "username",
        "segment",
        "pain_types",
        "competitors",
        "atlas_pitch_angle",
        "source_url",
    ]
    st.dataframe(
        df[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config={
            "score": st.column_config.NumberColumn("Score", format="%.0f"),
            "source_url": st.column_config.LinkColumn("Source URL"),
            "atlas_pitch_angle": "Pitch Angle",
            "company_or_product": "Company / Product",
        },
    )
    st.download_button(
        "Download CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"{key}.csv",
        mime="text/csv",
        key=f"download_{key}",
    )

    st.markdown("#### Lead Detail")
    for _, row in df.head(20).iterrows():
        label = f"{row.get('score', 0):.0f} - {row.get('company_or_product') or row.get('username') or 'Unknown'}"
        with st.expander(label):
            st.write(f"**Bucket:** {row.get('lead_bucket', '')}")
            st.write(f"**Segment:** {row.get('segment', '')}")
            st.write(f"**Pain:** {row.get('pain_types', '')}")
            st.write(f"**Competitors:** {row.get('competitors', '')}")
            st.write(f"**Pitch angle:** {row.get('atlas_pitch_angle', '')}")
            st.write(f"**Recommended outreach:** {row.get('recommended_outreach', '')}")
            source_url = row.get("source_url", "")
            if source_url:
                st.markdown(f"[Open source post]({source_url})")


def render_query_performance(query_df: pd.DataFrame) -> None:
    st.subheader("Query Performance")
    if query_df.empty:
        st.info("No query performance data available.")
        return
    st.dataframe(query_df, use_container_width=True, hide_index=True)
    st.download_button(
        "Download CSV",
        data=query_df.to_csv(index=False).encode("utf-8"),
        file_name="query_performance.csv",
        mime="text/csv",
        key="download_query_performance",
    )


def render_run_logs(runs_df: pd.DataFrame) -> None:
    st.subheader("Run Logs")
    if runs_df.empty:
        st.info("No database run logs available. CSV fallback mode is active.")
        return
    st.dataframe(runs_df, use_container_width=True, hide_index=True)
    st.download_button(
        "Download CSV",
        data=runs_df.to_csv(index=False).encode("utf-8"),
        file_name="run_logs.csv",
        mime="text/csv",
        key="download_run_logs",
    )


def _count_by(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if df.empty or column not in df.columns:
        return pd.DataFrame()
    return df[column].value_counts().rename_axis(column).reset_index(name="count")


def _competitor_counts(df: pd.DataFrame) -> pd.DataFrame:
    counts: Dict[str, int] = {}
    if df.empty:
        return pd.DataFrame()
    for value in df["competitors"].fillna(""):
        for competitor in _split_semicolon_or_comma(value):
            counts[competitor] = counts.get(competitor, 0) + 1
    if not counts:
        return pd.DataFrame()
    return (
        pd.DataFrame.from_dict(counts, orient="index", columns=["count"])
        .rename_axis("competitor")
        .reset_index()
        .sort_values("count", ascending=False)
    )


def _render_bar_chart(df: pd.DataFrame, category_column: str, color: str, label_angle: int) -> None:
    if df.empty or category_column not in df.columns:
        st.info("No data available.")
        return

    chart_df = df[[category_column, "count"]].copy()
    chart_df[category_column] = chart_df[category_column].astype(str)
    bars = (
        alt.Chart(chart_df, height=OVERVIEW_CHART_HEIGHT)
        .mark_bar(color=color, cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X(
                f"{category_column}:N",
                sort="-y",
                title=None,
                axis=alt.Axis(
                    labelAngle=label_angle,
                    labelAlign="right" if label_angle else "center",
                    labelBaseline="middle",
                    labelLimit=360,
                    labelPadding=8,
                ),
            ),
            y=alt.Y(
                "count:Q",
                title=None,
                axis=alt.Axis(grid=True, tickMinStep=1),
            ),
            tooltip=[
                alt.Tooltip(f"{category_column}:N", title="Category"),
                alt.Tooltip("count:Q", title="Count"),
            ],
        )
    )
    labels = (
        alt.Chart(chart_df)
        .mark_text(dy=-8, color="#334155", fontSize=12)
        .encode(
            x=alt.X(f"{category_column}:N", sort="-y"),
            y=alt.Y("count:Q"),
            text=alt.Text("count:Q", format=".0f"),
        )
    )
    chart = (
        (bars + labels)
        .properties(width="container", height=OVERVIEW_CHART_HEIGHT)
        .configure_axis(labelFontSize=12, titleFontSize=12, labelColor="#475569")
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(chart, use_container_width=True)


def _fal_displacement_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df[
        df["reason_codes"].str.contains("FAL_PRICING_PAIN", na=False)
        | df["competitors"].str.contains("fal.ai", case=False, na=False)
    ]


def _mobile_app_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df[df["segment"].isin(["iOS/mobile AI media app"])]


def _agency_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df[df["segment"].isin(["Digital marketing agency"])]


def _creator_platform_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df[df["segment"].isin(["AI-native creator platform", "Creator platform with many users", "AI video generator app"])]


def _creator_watchlist_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    creator_df = _creator_platform_df(df)
    return creator_df[creator_df["lead_bucket"].isin(["Strong Lead", "Watchlist", "Distribution / Weak Lead"])]


def _kol_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df[
        df["reason_codes"].str.contains("KOL_DISTRIBUTION", na=False)
        | df["segment"].str.contains("KOL", na=False)
    ]


def _stringify_list_value(value) -> str:
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    if isinstance(value, tuple):
        return "; ".join(str(item) for item in value)
    if pd.isna(value):
        return ""
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return ""
        if stripped.startswith("[") or stripped.startswith("{"):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return "; ".join(str(item) for item in parsed)
            except json.JSONDecodeError:
                return stripped
        return stripped
    return str(value)


def _split_semicolon_or_comma(value: str) -> List[str]:
    if not value:
        return []
    pieces = []
    for chunk in str(value).replace(",", ";").split(";"):
        cleaned = chunk.strip()
        if cleaned:
            pieces.append(cleaned)
    return pieces


def main() -> None:
    st.title("Atlas Daily Lead Agent")
    st.caption("Daily lead intelligence dashboard for Atlas Cloud.")

    leads_df, runs_df, query_df, data_source = load_dashboard_data()
    source_label = "Database" if data_source == "database" else "CSV fallback"
    st.info(f"Data source: {source_label}")
    if "dashboard_data_warning" in st.session_state and data_source == "csv":
        st.caption(f"Database fallback reason: {st.session_state['dashboard_data_warning']}")

    overview, top_revenue, fal, creator, kol, query_perf, run_logs = st.tabs(
        [
            "Overview",
            "Top Revenue Leads",
            "Fal Displacement",
            "Creator Platform Watchlist",
            "Distribution / KOL",
            "Query Performance",
            "Run Logs",
        ]
    )

    with overview:
        render_overview(leads_df, query_df)
    with top_revenue:
        render_lead_table(
            "Top Revenue Leads",
            leads_df[leads_df["lead_bucket"] == "Top Revenue Lead"],
            "top_revenue_leads_dashboard",
        )
    with fal:
        render_lead_table(
            "Fal Displacement",
            _fal_displacement_df(leads_df),
            "fal_displacement_dashboard",
            "These leads mention fal.ai pricing or competitor pain. Lead with Atlas pricing efficiency at scale.",
        )
    with creator:
        render_lead_table(
            "Creator Platform Watchlist",
            _creator_watchlist_df(leads_df),
            "creator_platform_watchlist_dashboard",
        )
    with kol:
        render_lead_table(
            "Distribution / KOL",
            _kol_df(leads_df),
            "distribution_kol_dashboard",
            "These are education, tutorial, and distribution opportunities, not primary revenue leads.",
        )
    with query_perf:
        render_query_performance(query_df)
    with run_logs:
        render_run_logs(runs_df)


if __name__ == "__main__":
    main()
