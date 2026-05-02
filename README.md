# Atlas Daily Lead Intelligence Dashboard

Atlas Daily Lead Intelligence Dashboard is a daily GTM intelligence system for Atlas Cloud. It finds high-scale AI media customers from public Twitter/X posts, classifies noisy social signals, scores lead quality, explains why each lead matters, and presents the result in an executive-friendly Streamlit dashboard backed by InsForge Postgres.

## Atlas Cloud First-Wave ICP

Atlas Cloud's first-wave GTM motion focuses on fast-moving AI media customers that can adopt infrastructure quickly:

1. Higgsfield-like AI-native creator platforms
2. Platforms with many creators
3. Digital marketing firms
4. iPhone/mobile AI media app teams
5. AI video generator apps
6. Short-form video/movie producers

Enterprise leads are intentionally excluded from the first wave because enterprise sales cycles are too long for the current GTM motion. The dashboard is optimized for high-signal, faster-moving prospects rather than slow procurement-led accounts.

## How The Product Works For This ICP

The system watches public Twitter/X conversations around AI media workflows, creator platforms, AI video apps, fal.ai pain, model comparisons, latency, cost, and production reliability. It then converts those signals into lead records that answer:

- Is this account part of Atlas Cloud's first-wave ICP?
- Are they showing scale, production usage, or buying intent?
- Are they mentioning fal.ai, Replicate, Runway, Kling, Seedance, Wan, Veo, or other AI media infrastructure?
- Are they experiencing cost, queue, latency, failed generation, model coverage, or reliability pain?
- What should Atlas say if the team reaches out?

Atlas Cloud is positioned around:

- One API for all SOTA media AI models
- Best pricing package in the industry for clients with scale
- Reliable service for production workloads
- Better pricing vs fal.ai for creators and platforms

## Product Architecture

```mermaid
flowchart TD
  subgraph DATA[Data Sources]
    TWEET[TwitterAPI.io]
    MOCK[Mock JSONL]
  end

  subgraph PIPE[Agent Pipeline]
    QP[Query Planner]
    COL[TwitterAPI.io Adapter]
    NORM[Normalization & Deduplication]
    SEG[Segment Classifier]
    PAIN[Pain / Intent Classifier]
    COMP[Competitor Detector]
    SCORE[Lead Scorer]
    OUT[Outreach Angle Generator]
  end

  subgraph STORE[Storage]
    DB[InsForge Postgres]
  end

  subgraph DASH[Dashboard]
    UI[Streamlit (Render)]
  end

  subgraph AUTO[Automation]
    CI[GitHub Actions]
  end

  TWEET --> COL
  MOCK --> COL
  COL --> NORM
  NORM --> SEG
  SEG --> PAIN
  PAIN --> COMP
  COMP --> SCORE
  SCORE --> OUT
  SCORE --> DB
  OUT --> UI
  DB --> UI
  CI --> DB
  CI --> UI

  classDef box fill:#f8f9fa,stroke:#2b2b2b,stroke-width:1px;
  class DATA,PIPE,STORE,DASH,AUTO box;

  click TWEET "https://twitterapi.io" "TwitterAPI.io"
```

## End-To-End Workflow

### 1. Query Planning

The Query Planner turns the ICP into targeted search queries. It loads `data/queries.yaml`, creates `QuerySpec` objects, and builds bounded Twitter/X search queries around:

- AI-native creator platforms
- Creator platforms with scale
- iPhone/mobile AI media apps
- AI video generator apps
- Digital marketing and UGC agencies
- Short-form video/movie producers
- fal.ai pricing, latency, and reliability pain
- Replicate, Runway, Kling, Seedance, Wan, Veo, and other model/provider comparisons

Investor question: "How do you avoid searching randomly?"

Answer: The query planner starts from Atlas Cloud's ICP and business pain hypotheses. Queries are not generic. They are designed to surface posts where a prospect is likely discussing production AI media infrastructure, scale, vendor pain, or model-routing needs.

### 2. Data Collection

Production collection uses the TwitterAPI.io provider adapter. It calls TwitterAPI.io documented API endpoints and uses the API key through the `X-API-Key` header.

The collector:

- Retrieves public Twitter/X posts from the documented Advanced Search endpoint
- Keeps requests bounded for demo and daily monitoring use
- Normalizes author, engagement, post URL, timestamp, text, and raw metadata
- Implements retry/backoff and safe failure handling
- Avoids browser automation, cookie scraping, login scraping, anti-bot bypass, proxies, and write actions

Investor question: "Is this a brittle scraper?"

Answer: No. The production path uses a provider adapter around TwitterAPI.io documented API endpoints. The system also has a mock JSONL fallback so demos, tests, and local development can run without external API calls.

### 3. Normalization And Deduplication

Each collected record becomes a `RawPost` Pydantic object. The pipeline validates structure, parses timestamps, preserves public source metadata, and deduplicates by `post_id`.

Investor question: "Can we trace why a lead was selected?"

Answer: Yes. Raw post text, source URL, matched query, author metadata, reason codes, and classifier evidence are stored and shown in the dashboard.

### 4. ICP Segment Classification

The Segment Classifier identifies whether a post belongs to a target segment:

- AI-native creator platform
- Creator platform with many users
- iOS/mobile AI media app
- AI video generator app
- Digital marketing agency
- Short-form video producer
- KOL / distribution partner
- Enterprise, excluded
- Irrelevant

The classifier uses rule-based detection first, with optional OpenAI-compatible LLM support when configured.

Investor question: "Why exclude enterprise?"

Answer: Enterprise opportunities can be valuable later, but they are not ideal for this first-wave motion because sales cycles are long. The MVP is built to identify faster-moving creator and app teams that can become early revenue or design partners.

### 5. Pain, Intent, And Competitor Detection

The Pain / Intent Classifier detects:

- Cost pain
- fal.ai pricing pain
- Reliability pain
- Queue / latency
- Rate limit
- Failed generation
- Model coverage need
- One API need
- Scale need
- Buying intent
- Casual mention

The Competitor Detector identifies mentions of:

- fal.ai
- Replicate
- Runway
- Pika
- Luma
- Kling
- Seedance
- Wan
- Veo
- Hailuo
- Vidu
- OpenRouter
- RunPod
- Modal
- Fireworks
- Together

Investor question: "How does the system know a post is a real sales signal?"

Answer: It looks for the combination of ICP segment, scale signal, pain type, competitor mention, and intent. A casual AI video news post scores low. A mobile AI app complaining about fal.ai pricing and production queue latency scores much higher.

### 6. Lead Scoring

Each lead receives an explainable 0-100 score.

Score breakdown:

- Scale potential: 30
- Atlas fit: 25
- Cost / reliability pain: 20
- Buying intent: 15
- Contactability: 10

Penalties:

- Enterprise lead penalty: -20
- Competitor official account penalty: -30
- Pure news penalty: -15
- Casual individual creator penalty: -10

Lead buckets:

- 85-100: Top Revenue Lead
- 70-84: Strong Lead
- 55-69: Watchlist
- 40-54: Distribution / KOL / Weak Lead
- 0-39: Not Qualified

Example reason codes:

- `HIGGSFIELD_LIKE_PLATFORM`
- `CREATOR_PLATFORM_SCALE`
- `IOS_AI_MEDIA_APP`
- `AI_VIDEO_GENERATOR_APP`
- `DIGITAL_MARKETING_AGENCY`
- `SHORT_FORM_VIDEO_PRODUCER`
- `FAL_PRICING_PAIN`
- `COMPETITOR_PAIN`
- `VIDEO_GEN_SCALE`
- `IMAGE_VIDEO_API_NEED`
- `ONE_API_NEED`
- `MODEL_COVERAGE_NEED`
- `RELIABILITY_PAIN`
- `QUEUE_LATENCY_PAIN`
- `PRODUCTION_WORKLOAD`
- `KOL_DISTRIBUTION`
- `ENTERPRISE_EXCLUDED`
- `PURE_NEWS`
- `COMPETITOR_OFFICIAL`

Investor question: "Is this just a black box?"

Answer: No. The score is decomposed into fit, scale, pain, intent, and contactability. The dashboard shows reason codes and source evidence so a human can review and override the ranking.

### 7. Outreach Angle Generation

The Outreach Angle Generator chooses one of four Atlas pitch angles:

- One API for all SOTA media models
- Better pricing at scale
- Reliability for production workloads
- Creator platform / app infra layer

It creates concise, non-spammy outreach guidance based on the actual post evidence. The MVP does not perform automated outreach.

## Dashboard

The Streamlit dashboard is the primary product surface. It is designed for Jerry or the Atlas team to review the day's GTM opportunities quickly.

### Overview

Shows:

- Daily posts scanned
- Qualified leads
- Top revenue leads
- fal.ai displacement leads
- iOS/mobile AI app leads
- Agency/marketing leads
- Creator platform leads
- Enterprise excluded

It also visualizes segment distribution, lead bucket distribution, and competitor mentions.

### Top Revenue Leads

Prioritized leads with score, company/product, username, segment, pain types, competitors, Atlas pitch angle, and source URL.

### Fal Displacement Leads

Leads mentioning fal.ai pricing, cost, latency, queue, reliability, or alternatives. This tab matters because Atlas can offer better pricing vs fal.ai for creators and platforms with scale.

### Creator Platform Watchlist

Tracks Higgsfield-like platforms, AI creator platforms, AI video apps, mobile AI media products, and creator tools with scale potential.

### Distribution / KOL Leads

Separates tutorial authors, workflow authors, and AI video creators from direct revenue leads. These people may not buy directly but can influence creator adoption.

### Query Performance

Shows which queries generated qualified leads, average score by query category, and which ICP areas are producing signal.

### Run Logs

Shows latest daily runs, collection status, posts collected, leads generated, and errors if any.

## Data Storage

InsForge Postgres is the persistent backend. It stores:

- `runs`
- `raw_posts`
- `classified_posts`
- `leads`
- `feedback_labels`

This avoids relying on local disk or Render ephemeral storage. The application reads `INSFORGE_DATABASE_URL` from environment variables.

## Automation

GitHub Actions runs the pipeline once per day at 9 AM Eastern Time and can also be triggered manually through `workflow_dispatch`.

Workflow file:

```text
.github/workflows/daily_monitor.yml
```

Workflow behavior:

- Install dependencies
- Run `python -m app.main --prod --export`
- Write data into InsForge Postgres
- Upload CSV files and `daily_report.md` as workflow artifacts

## Technical Stack

- Python 3.11 for the agent pipeline
- Pydantic for schemas and validation
- SQLAlchemy for database access
- TwitterAPI.io provider adapter for production public Twitter/X data
- Mock JSONL fallback for local demo and testing
- InsForge Postgres for persistent storage
- Streamlit for the executive dashboard
- Render for dashboard hosting
- GitHub Actions for daily monitoring
- Optional OpenAI-compatible LLM endpoint for classification support

## Environment Variables

```bash
APP_ENV=development
USE_MOCK_DATA=true

INSFORGE_DATABASE_URL=
DATABASE_URL=

TWITTERAPI_IO_API_KEY=
TWITTERAPI_IO_BASE_URL=https://api.twitterapi.io

LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=

ALERT_SCORE_THRESHOLD=75
```

Notes:

- `TWITTERAPI_IO_API_KEY` is required for production TwitterAPI.io collection.
- `USE_MOCK_DATA=true` allows the full pipeline and dashboard to run without external API calls.
- `INSFORGE_DATABASE_URL` is recommended for production persistence.
- Local SQLite through `DATABASE_URL` is only for development or mock demo mode.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.db.migrations
python -m app.main --mock --export
streamlit run app/dashboard/streamlit_app.py
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

## Mock Demo Run

Mock mode uses `data/sample_posts.jsonl`. It is designed for demos, tests, and offline development.

```bash
python -m app.main --mock --export
```

Mock mode produces the same output structure as production:

- `outputs/top_revenue_leads.csv`
- `outputs/fal_displacement_leads.csv`
- `outputs/creator_platform_watchlist.csv`
- `outputs/distribution_kol_leads.csv`
- `outputs/daily_report.md`

## Production Run

Production mode uses TwitterAPI.io documented API endpoints.

```bash
python -m app.main --prod --export
```

Production requires `TWITTERAPI_IO_API_KEY`. When `INSFORGE_DATABASE_URL` is set, results are written to InsForge Postgres and become available in the dashboard.

## Deploying The Dashboard To Render

Render hosts the Streamlit dashboard. Persistent data should live in InsForge Postgres, not Render's local filesystem. The dashboard reads from InsForge Postgres and may fall back to CSV outputs in demo mode.

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
streamlit run app/dashboard/streamlit_app.py --server.port $PORT --server.address 0.0.0.0
```

Render environment variables:

```bash
APP_ENV=production
USE_MOCK_DATA=false
INSFORGE_DATABASE_URL=...
TWITTERAPI_IO_API_KEY=...
TWITTERAPI_IO_BASE_URL=https://api.twitterapi.io
LLM_API_KEY=...
LLM_BASE_URL=...
LLM_MODEL=...
```

## Compliance And Responsible Data Usage

- Use TwitterAPI.io documented API endpoints only.
- No browser automation.
- No cookie scraping.
- No login scraping.
- No anti-bot or rate-limit bypass.
- No automated posting, liking, following, DMs, or write actions.
- No residential proxies.
- No collection of private or non-public data.
- Store only the public post metadata needed for lead scoring and evidence.
- Respect TwitterAPI.io usage limits, credit limits, and provider terms.
- Use mock data fallback for demos, tests, and offline development.
- Keep API keys and database URLs in environment variables, Render environment variables, or GitHub Secrets only.

## Limitations

- TwitterAPI.io data availability and search behavior may vary.
- Query quality directly affects lead quality.
- Some posts may not provide enough company or contact information.
- Optional LLM classification can make mistakes, so reason codes and evidence are shown for review.
- Production precision should improve with feedback from Atlas BD and founder review.
- The MVP does not perform automated outreach.
- The MVP does not use private data.
- The MVP does not guarantee conversion; it prioritizes leads for human follow-up.

## Two-Week Roadmap

### Week 1

- Tune queries based on Jerry/BD feedback
- Add human feedback labels for good/bad leads
- Improve precision@20
- Add company enrichment from public website/profile URLs
- Add better query performance analytics
- Add Slack or email alert for high-score leads

### Week 2

- Add CRM export
- Add lead history by username/company
- Add deduplication across days
- Add weekly GTM report
- Add model-based query expansion
- Add competitor-specific reports, especially fal.ai displacement
- Add dashboard authentication if needed
- Add more robust monitoring and error alerts
