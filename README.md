# iGaming Research Agent

Production style AI research pipeline that turns raw iGaming news into scored intelligence reports.

End to end system covering data ingestion, information extraction, model driven analysis, report generation, API design, and frontend delivery.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?logo=sqlalchemy&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)
![APScheduler](https://img.shields.io/badge/APScheduler-cron%20orchestration-2E7D32)
![Anthropic](https://img.shields.io/badge/Anthropic-Claude%20Haiku%20and%20Sonnet-111111)
![Serper](https://img.shields.io/badge/Serper-News%20Search-4A90E2)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=111111)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3-06B6D4?logo=tailwindcss&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)

## Project highlights

- Full data to insight pipeline, not only a model wrapper
- Combined retrieval, scraping, filtering, scoring, and synthesis into one orchestrated system
- Implemented production style API boundaries with clear query and reporting endpoints
- Added scheduling for repeatable daily execution
- Added user feedback capture to improve scoring quality loops
- Delivered a product UI for operations, history, and report review

## End to end pipeline

1. Query management
- Users manage active search queries from the Settings page
- Backend exposes CRUD endpoints at /api/queries

2. Source discovery
- Active queries are executed through Serper News
- Results are normalized and deduplicated by URL

3. Content extraction
- Article pages are scraped for full text
- Primary extractor uses trafilatura, with Jina AI fallback for resilience

4. AI relevance gate
- Claude Haiku performs strict YES or NO relevance filtering for USA iGaming context

5. AI scoring and summarization
- Relevant items are scored 1 to 10 with structured output
- Analyzer validates output consistency before accepting results

6. Persistence and versioned reporting
- Articles and metadata are stored with SQLAlchemy models in SQLite
- Daily report snapshots preserve historical runs

7. Narrative briefing generation
- Claude Sonnet synthesizes top stories into journalist style daily briefing markdown

8. Delivery and feedback loop
- Dashboard and History pages present reports and ranked stories
- Feedback endpoint captures helpful or corrected score signals for future model tuning

## Data flow

query inputs
-> serper news results
-> full text extraction
-> relevance filter
-> score and tags
-> report entity
-> briefing markdown
-> frontend dashboard and history

## AI engineering decisions implemented

- Two stage model design to optimize quality and cost
- Deterministic relevance and scoring calls with low temperature
- Priority content extraction to reduce context noise before scoring
- Validation checks to reject inconsistent model outputs
- Explicit timeout and fallback handling in API and scraping paths

## Product capabilities

- Daily Intelligence Report view with score sorted article cards
- Show kept only versus show all screened articles
- Report History page with drill down into previous runs
- Query Manager to create, activate, deactivate, and delete search rules
- Manual Run Pipeline trigger from UI for on demand execution



## Run with Docker

1. cd igaming-research-agent
2. docker compose up --build
3. docker compose down

## Deployment notes

- Frontend supports VITE_API_BASE_URL configuration
- Railway deployment supported with separate backend and frontend services
- Root Dockerfile and railway.toml are included for repository root build scenarios

## Current scope and next upgrades

Current implementation includes full orchestration, API surface, scheduler, UI flows, and test scaffolding.
Next upgrades are deeper provider integrations and online learning workflows from user feedback.
