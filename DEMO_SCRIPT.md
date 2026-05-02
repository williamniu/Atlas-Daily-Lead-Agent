# Demo Video Script

## Goal

Show that Atlas Daily Lead Intelligence Dashboard is not just a prototype UI. It is an end-to-end GTM intelligence workflow that can collect public Twitter/X signals, classify and score leads, store production data in InsForge, run automatically through GitHub Actions, and present the results in a usable dashboard.

Target length: 5-7 minutes.

## 1. GitHub Repository And README

Start on the GitHub homepage.

Talk track:

"This is Atlas Daily Lead Intelligence Dashboard. The goal is simple: help Atlas Cloud find high-scale AI media customers from public Twitter/X posts and turn noisy social signals into prioritized GTM leads."

"The first-wave ICP is very focused: AI-native creator platforms, creator platforms with many users, digital marketing firms, mobile AI media apps, AI video generator apps, and short-form video or movie producers. I explicitly exclude enterprise leads because enterprise sales cycles are too long for this first GTM wave."

"The product is not a raw data collector. The output is this executive-friendly dashboard that helps answer: who should Atlas contact today, why are they a fit, what pain are they showing, what competitors are they mentioning, and what pitch angle should Atlas use?"

Scroll to the architecture diagram.

"The architecture is a daily agent pipeline. It starts with TwitterAPI.io Advanced Search or mock data, goes through query planning, collection, normalization, ICP classification, pain and competitor detection, lead scoring, outreach angle generation, then stores everything in InsForge Postgres. The Streamlit dashboard reads from that database, and GitHub Actions runs the production pipeline every day."

Scroll to scoring.

"The scoring model is intentionally explainable. It is a 100-point score: scale potential, Atlas fit, cost and reliability pain, buying intent, and contactability. It also applies penalties for enterprise, competitor official accounts, pure news, and casual individual creator posts."

## 2. GitHub Actions Daily Scheduler

Go to the GitHub Actions tab.

Open the latest successful workflow run.

Talk track:

"Here is the automation layer. This workflow runs once per day at 9 AM Eastern Time, and I can also trigger it manually with workflow dispatch."

"The workflow installs dependencies, runs `python -m app.main --prod --export`, writes results into InsForge Postgres, and uploads the generated CSV and daily report artifacts."

"So the system is not only local. It is already hosted as a scheduled production workflow."

Optional note:

"For the demo, I am using TwitterAPI.io as the production data provider. The adapter uses documented API endpoints and keeps requests bounded."

## 3. VS Code Local Production Run

Go back to VS Code.

Open the terminal.

Run:

```bash
python3 -m app.main --prod --export
```

Talk track:

"Now I will run the same production pipeline locally. This is the core workflow: load query specs, collect public posts, normalize and dedupe, classify each post, score leads, generate outreach angles, save everything to InsForge, and export daily artifacts."

When output appears:

"The console prints the top ten leads immediately. Each lead has a score, bucket, company or product name, segment, pitch angle, and source URL."

Point to the top lead output.

"This lets the Atlas team quickly see which accounts are worth reviewing today."

## 4. InsForge Backend Database

Switch to InsForge.

Show the database tables:

- `runs`
- `raw_posts`
- `classified_posts`
- `leads`
- `feedback_labels`

Talk track:

"Here is the backend. The run I just executed has written fresh data into InsForge Postgres."

"The system stores raw posts for evidence, classified posts for segment and pain analysis, leads for scoring and dashboard display, and run logs for monitoring."

"This is important because Render's local filesystem is ephemeral. Persistent data lives in InsForge Postgres, not inside the dashboard container."

Open `leads`.

"Here you can see the scored lead records. These are what the dashboard reads."

Open `raw_posts` or `classified_posts`.

"And here is the traceability layer. I can inspect the original public post signal and the classification evidence behind each lead."

## 5. Streamlit Dashboard Launch

Return to VS Code.

Run:

```bash
python3 -m streamlit run app/dashboard/streamlit_app.py
```

Talk track:

"Now I will launch the dashboard. The dashboard reads from InsForge Postgres by default. If the database is empty or unavailable, it can fall back to exported CSVs for demo mode."

Wait for browser to open.

## 6. Dashboard Walkthrough

Start on Overview.

Talk track:

"This is the executive overview. At the top are the KPIs Jerry or the Atlas team would care about: daily posts scanned, qualified leads, top revenue leads, fal.ai displacement leads, mobile app leads, agency leads, creator platform leads, and enterprise excluded."

Point to charts.

"The charts show segment distribution, lead bucket distribution, and competitor mentions. This makes it easy to understand where today's GTM signal is coming from."

Go to Top Revenue Leads.

"This tab is the highest-priority revenue queue. Each row includes the score, company or product, segment, pain types, competitor mentions, pitch angle, and source URL."

Open one expander.

"The detail view explains why the lead was selected and what Atlas should say. The outreach guidance is specific but not spammy."

Go to Fal Displacement.

"This is one of the most important views. It isolates leads mentioning fal.ai pricing, cost, latency, queues, reliability, or alternatives. The reason this matters is that Atlas can position better pricing at scale and more reliable production infrastructure."

Go to Creator Platform Watchlist.

"This is the strategic watchlist: Higgsfield-like platforms, AI creator platforms, AI video apps, mobile AI media products, and creator tools with scale potential."

Go to Distribution / KOL.

"Not every useful signal is a direct buyer. This tab separates tutorial authors, workflow authors, and KOLs who can influence creator adoption. They are distribution opportunities, not primary revenue leads."

Go to Query Performance.

"This tells us which queries are working. Over time, Jerry or the BD team can tune the query set and improve precision."

Go to Run Logs.

"Finally, this gives operational visibility into daily runs: when the pipeline ran, how many posts it collected, and how many leads it generated."

## 7. Close

Talk track:

"So the full demo shows four things: the product logic is explainable, the pipeline runs end to end, data is persisted in InsForge, and the dashboard gives Atlas a daily GTM workflow."

"The next step would be tuning precision with Jerry's feedback: labeling good and bad leads, improving the query set, adding enrichment, and eventually pushing high-score leads into CRM or Slack."

"The MVP is already useful as a daily lead intelligence system, and it can continue improving with real BD feedback."

## Short Backup Version

If time is tight:

"This project is a daily GTM intelligence dashboard for Atlas Cloud. It collects public Twitter/X posts through TwitterAPI.io, classifies whether each post matches Atlas's first-wave ICP, detects pain around fal.ai, pricing, latency, reliability, and model coverage, then scores each lead and stores the result in InsForge Postgres."

"GitHub Actions runs it every day at 9 AM Eastern, and Streamlit presents the results in an executive dashboard. The dashboard tells Atlas who to contact today, why they are a fit, what competitor or pain signal they showed, and what pitch angle to use."

"The key point is that this is not a generic social feed. It is an explainable, daily GTM workflow for finding high-scale AI media customers."
