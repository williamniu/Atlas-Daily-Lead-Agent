# Atlas Daily Lead Agent

Daily lead intelligence dashboard for Atlas Cloud.

## Purpose

This project will collect, enrich, score, and present daily lead signals for Atlas Cloud.

## First-Wave ICP

- Higgsfield-like AI-native creator platforms
- Creator platforms with many users
- Digital marketing firms
- iPhone and mobile AI media app teams
- AI video generator apps
- Short-form video and movie producers

## Explicit Exclusions

- Enterprise leads
- Long-cycle procurement-led opportunities
- Leads where the likely sales motion depends on slow enterprise approval paths

## Project Structure

```text
app/
  config.py
  main.py
  schemas/
  db/
  collectors/
  agents/
  services/
  dashboard/
data/
outputs/
tests/
```

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

## Dashboard

```bash
streamlit run app/dashboard/streamlit_app.py
```

## Status

This repository is currently a scaffold. Core collection, scoring, enrichment, and dashboard logic will be implemented later.

