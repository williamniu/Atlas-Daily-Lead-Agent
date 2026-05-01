"""End-to-end daily lead intelligence pipeline."""

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session

from app.agents.lead_scorer import score_lead
from app.agents.query_planner import QuerySpec, load_query_specs
from app.agents.segment_classifier import classify_post
from app.collectors.mock_loader import load_mock_posts
from app.collectors.twitterapi_io import (
    MissingTwitterApiIoKeyError,
    collect_recent_posts as collect_twitterapi_io_posts,
)
from app.config import settings
from app.db.database import get_session, init_db
from app.db.models import ClassifiedPostRecord, LeadRecord, RawPostRecord, Run
from app.schemas import ClassifiedPost, Lead, RawPost


OUTPUT_DIR = Path("outputs")


@dataclass(frozen=True)
class PipelineResult:
    """Pipeline output for CLI and dashboard consumers."""

    run_id: str
    query_specs: List[QuerySpec]
    raw_posts: List[RawPost]
    classified_posts: List[ClassifiedPost]
    leads: List[Lead]
    used_mock_data: bool
    notes: str


def run_pipeline(
    use_mock: Optional[bool] = None,
    export: bool = False,
    limit: Optional[int] = None,
    prod: bool = False,
) -> PipelineResult:
    """Run the daily lead intelligence workflow."""
    run_id = _create_run_id()
    init_db()

    query_specs = load_query_specs()
    used_mock_data = bool(use_mock) or (settings.use_mock_data and not prod)
    notes = []

    if used_mock_data:
        raw_posts = load_mock_posts()
        notes.append("Loaded mock posts.")
    else:
        try:
            raw_posts, provider_note = _collect_live_posts(query_specs, limit=limit)
            notes.append(provider_note)
        except MissingTwitterApiIoKeyError as exc:
            raw_posts = load_mock_posts()
            used_mock_data = True
            notes.append(str(exc))
            notes.append("Fell back to mock posts.")

    raw_posts = _dedupe_posts(raw_posts)
    if limit is not None:
        raw_posts = raw_posts[:limit]

    classified_posts = [classify_post(post) for post in raw_posts]
    leads = [
        score_lead(raw_post, classified_post)
        for raw_post, classified_post in zip(raw_posts, classified_posts)
    ]
    leads = sorted(leads, key=lambda lead: lead.score, reverse=True)

    completed_at = datetime.utcnow()
    note_text = " ".join(notes)
    _save_pipeline_result(
        run_id=run_id,
        query_specs=query_specs,
        raw_posts=raw_posts,
        classified_posts=classified_posts,
        leads=leads,
        used_mock_data=used_mock_data,
        completed_at=completed_at,
        notes=note_text,
        prod=prod,
    )

    result = PipelineResult(
        run_id=run_id,
        query_specs=query_specs,
        raw_posts=raw_posts,
        classified_posts=classified_posts,
        leads=leads,
        used_mock_data=used_mock_data,
        notes=note_text,
    )

    if export:
        export_outputs(result)

    return result


def _collect_live_posts(query_specs: List[QuerySpec], limit: Optional[int]) -> Tuple[List[RawPost], str]:
    provider = settings.live_data_provider.lower().strip()
    max_results = limit or 50

    if provider in {"auto", "twitterapi_io"} and settings.has_twitterapi_io:
        return (
            collect_twitterapi_io_posts(query_specs=query_specs, max_results=max_results),
            "Loaded posts from TwitterAPI.io.",
        )

    raise MissingTwitterApiIoKeyError(
        "TWITTERAPI_IO_API_KEY is required for live collection with the TwitterAPI.io provider adapter."
    )


def export_outputs(result: PipelineResult, output_dir: Path = OUTPUT_DIR) -> None:
    """Export lead CSVs and a markdown daily report."""
    output_dir.mkdir(parents=True, exist_ok=True)

    _write_leads_csv(
        output_dir / "top_revenue_leads.csv",
        [lead for lead in result.leads if lead.lead_bucket == "Top Revenue Lead"],
    )
    _write_leads_csv(
        output_dir / "fal_displacement_leads.csv",
        [
            lead
            for lead in result.leads
            if "FAL_PRICING_PAIN" in lead.reason_codes or "COMPETITOR_PAIN" in lead.reason_codes
        ],
    )
    _write_leads_csv(
        output_dir / "creator_platform_watchlist.csv",
        [
            lead
            for lead in result.leads
            if lead.segment
            in {
                "AI-native creator platform",
                "Creator platform with many users",
                "iOS/mobile AI media app",
                "AI video generator app",
            }
            and lead.lead_bucket in {"Strong Lead", "Watchlist", "Distribution / Weak Lead"}
        ],
    )
    _write_leads_csv(
        output_dir / "distribution_kol_leads.csv",
        [lead for lead in result.leads if "KOL_DISTRIBUTION" in lead.reason_codes],
    )
    _write_daily_report(output_dir / "daily_report.md", result)


def print_top_leads(leads: Sequence[Lead], limit: int = 10) -> None:
    """Print the top leads to the console."""
    print("\nTop leads")
    print("---------")
    if not leads:
        print("No leads found.")
        return

    for index, lead in enumerate(leads[:limit], start=1):
        print(
            f"{index}. {lead.score:.0f} | {lead.lead_bucket} | "
            f"{lead.company_or_product or lead.username or 'Unknown'} | {lead.segment}"
        )
        print(f"   {lead.atlas_pitch_angle}")
        if lead.source_url:
            print(f"   {lead.source_url}")


def _save_pipeline_result(
    run_id: str,
    query_specs: List[QuerySpec],
    raw_posts: List[RawPost],
    classified_posts: List[ClassifiedPost],
    leads: List[Lead],
    used_mock_data: bool,
    completed_at: datetime,
    notes: str,
    prod: bool,
) -> None:
    with get_session() as session:
        run = Run(
            run_id=run_id,
            started_at=datetime.utcnow(),
            completed_at=completed_at,
            app_env="production" if prod else settings.app_env,
            use_mock_data=used_mock_data,
            source_count=len(query_specs),
            raw_post_count=len(raw_posts),
            classified_post_count=len(classified_posts),
            lead_count=len(leads),
            notes=notes,
        )
        session.add(run)

        for raw_post in raw_posts:
            _upsert_raw_post(session, raw_post)
        for classified_post in classified_posts:
            session.add(_classified_post_record(classified_post))
        for lead in leads:
            _upsert_lead(session, lead)

        session.commit()


def _upsert_raw_post(session: Session, raw_post: RawPost) -> None:
    record = session.query(RawPostRecord).filter_by(post_id=raw_post.post_id).one_or_none()
    values = {
        "source": raw_post.source,
        "post_id": raw_post.post_id,
        "post_url": raw_post.post_url,
        "text": raw_post.text,
        "author_id": raw_post.author_id,
        "username": raw_post.username,
        "author_name": raw_post.author_name,
        "author_bio": raw_post.author_bio,
        "followers_count": raw_post.followers_count,
        "following_count": raw_post.following_count,
        "like_count": raw_post.like_count,
        "reply_count": raw_post.reply_count,
        "repost_count": raw_post.repost_count,
        "quote_count": raw_post.quote_count,
        "created_at": raw_post.created_at,
        "matched_query": raw_post.matched_query,
        "raw_json": raw_post.raw_json,
    }
    if record is None:
        session.add(RawPostRecord(**values))
        return
    for key, value in values.items():
        setattr(record, key, value)


def _classified_post_record(classified_post: ClassifiedPost) -> ClassifiedPostRecord:
    return ClassifiedPostRecord(
        post_id=classified_post.post_id,
        segment=classified_post.segment,
        intent_type=classified_post.intent_type,
        pain_types=classified_post.pain_types,
        competitors=classified_post.competitors,
        model_mentions=classified_post.model_mentions,
        scale_signals=classified_post.scale_signals,
        contactability_signals=classified_post.contactability_signals,
        is_enterprise=classified_post.is_enterprise,
        is_competitor_official=classified_post.is_competitor_official,
        is_kol_distribution=classified_post.is_kol_distribution,
        classification_reason=classified_post.classification_reason,
    )


def _upsert_lead(session: Session, lead: Lead) -> None:
    record = session.query(LeadRecord).filter_by(lead_id=lead.lead_id).one_or_none()
    values = {
        "lead_id": lead.lead_id,
        "post_id": lead.post_id,
        "username": lead.username,
        "display_name": lead.display_name,
        "company_or_product": lead.company_or_product,
        "segment": lead.segment,
        "score": lead.score,
        "score_breakdown": lead.score_breakdown.model_dump(),
        "reason_codes": lead.reason_codes,
        "evidence": lead.evidence,
        "atlas_pitch_angle": lead.atlas_pitch_angle,
        "recommended_outreach": lead.recommended_outreach,
        "lead_bucket": lead.lead_bucket,
        "source_url": str(lead.source_url) if lead.source_url else None,
        "updated_at": datetime.utcnow(),
    }
    if record is None:
        session.add(LeadRecord(**values))
        return
    for key, value in values.items():
        setattr(record, key, value)


def _write_leads_csv(path: Path, leads: Iterable[Lead]) -> None:
    fieldnames = [
        "score",
        "lead_bucket",
        "company_or_product",
        "username",
        "segment",
        "reason_codes",
        "atlas_pitch_angle",
        "recommended_outreach",
        "source_url",
    ]
    rows = [_lead_csv_row(lead) for lead in leads]
    with path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _lead_csv_row(lead: Lead) -> dict:
    return {
        "score": lead.score,
        "lead_bucket": lead.lead_bucket,
        "company_or_product": lead.company_or_product,
        "username": lead.username,
        "segment": lead.segment,
        "reason_codes": ";".join(lead.reason_codes),
        "atlas_pitch_angle": lead.atlas_pitch_angle,
        "recommended_outreach": lead.recommended_outreach,
        "source_url": str(lead.source_url) if lead.source_url else "",
    }


def _write_daily_report(path: Path, result: PipelineResult) -> None:
    top_leads = result.leads[:10]
    lines = [
        f"# Atlas Daily Lead Report",
        "",
        f"- Run ID: `{result.run_id}`",
        f"- Used mock data: `{result.used_mock_data}`",
        f"- Raw posts: `{len(result.raw_posts)}`",
        f"- Classified posts: `{len(result.classified_posts)}`",
        f"- Leads: `{len(result.leads)}`",
        "",
        "## Top 10 Leads",
        "",
    ]
    if not top_leads:
        lines.append("No leads found.")
    else:
        for index, lead in enumerate(top_leads, start=1):
            lines.extend(
                [
                    f"{index}. **{lead.company_or_product or lead.username or 'Unknown'}** - {lead.score:.0f}",
                    f"   - Bucket: {lead.lead_bucket}",
                    f"   - Segment: {lead.segment}",
                    f"   - Pitch: {lead.atlas_pitch_angle}",
                    f"   - Source: {lead.source_url or ''}",
                    "",
                ]
            )
    path.write_text("\n".join(lines))


def _dedupe_posts(posts: List[RawPost]) -> List[RawPost]:
    seen = set()
    deduped = []
    for post in posts:
        if post.post_id in seen:
            continue
        seen.add(post.post_id)
        deduped.append(post)
    return deduped


def _create_run_id() -> str:
    return f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
