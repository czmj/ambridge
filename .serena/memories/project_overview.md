# Project Overview

**Ambridge** — a searchable archive of BBC Radio 4's "The Archers" episodes.

## Tech Stack
- **Frontend**: Next.js 16 (React 19), App Router, Tailwind CSS v4 via PostCSS, TypeScript
- **Database**: Neo4j graph database (APOC plugin required for initial setup)
- **Scraper**: Python (requests, beautifulsoup4, neo4j, python-dotenv)
- **Family tree**: `family-chart` npm library

## Key directories
- `app/` — Next.js App Router pages and server actions
- `components/` — Presentational React components
- `lib/` — Shared utilities (neo4j driver, utils)
- `types/` — TypeScript types
- `scraper/` — Python scraper pipeline (6 files + seed data)

## Environment variables (`.env`, not committed)
`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `SERIES_ID`, `CACHE_FILE`
