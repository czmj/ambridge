# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ambridge is a searchable archive of BBC Radio 4's "The Archers" episodes. It's a Next.js 16 (React 19) app backed by a Neo4j graph database, with a Python scraper for ingesting episode data from the BBC website.

## Commands

```bash
npm run dev        # Start dev server at localhost:3000
npm run build      # Production build
npm run lint       # ESLint (flat config with next/core-web-vitals and TypeScript)
```

There is no test framework configured.

### Scraper

```bash
python scraper/archersscrape.py update              # Scrape new episodes
python scraper/archersscrape.py update --from-cache  # Build DB from cached json file
python scraper/archersscrape.py link --character "Name" --scenes S1 S2  # Manually link character to scenes
python scraper/archersscrape.py cleanup              # Review and merge empty scenes
```

Requires Python with `requests`, `beautifulsoup4`, `neo4j`, `python-dotenv`.

## Architecture

### Web App (Next.js App Router)

- **`app/actions.ts`** — All data fetching. Server actions that run Cypher queries against Neo4j via a shared driver (`lib/neo4j.ts`). Three main queries: `getTimeline()` (paginated episode list), `getCharacterProfile()`, `getEpisodeByDate()`.
- **Routes**: `/` (timeline), `/to/[slug]` (character-filtered timeline), `/on/[date]` (single episode detail)
- **Query params**: `?page=N&sort=asc|desc`
- **Components** are presentational, receiving data as props from server pages. No client-side state management.
- **Styling**: Tailwind CSS v4 via PostCSS.

### Neo4j Graph Model

Nodes: `Episode` (pid, date, synopsis), `Scene` (id, order, text), `Character` (name, slug, aliases, dob, dod, gender), `Location` (name)

Key relationships:
- `Scene -[:PART_OF]-> Episode`
- `Character -[:APPEARS_IN]-> Scene`
- `Character -[:SPOUSE|CHILD_OF|SIBLING|ROMANTIC_RELATIONSHIP]- Character`
- `Character -[:LIVES_AT|WORKS_AT]-> Location` (with temporal `from`/`to` properties)

Constraints: `Episode.pid` is node key, `Scene.id` is node key, `Character.slug` is unique.

### Scraper (`scraper/archersscrape.py`)

Three classes: `WebScraper` (fetches BBC episode pages concurrently), `EpisodeProcessor` (parses blurbs into scenes via regex), `ArchersDatabase` (Neo4j upserts, duplicate handling, character-to-scene linking). Character linking uses a two-pass approach: first unambiguous names, then ambiguous names weighted by relationship proximity (close family=3, distant family=2, cohabitants=2).

Initial character/location seed data lives in `scraper/import_base_data.txt`.

## Environment Variables

Set in `.env` (not committed): `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `SERIES_ID`, `CACHE_FILE`.

## Key Conventions

- Neo4j integer parameters must use `neo4j.int()` wrapper (e.g. `neo4j.int(skip)`)
- Cypher queries use string interpolation for sort direction and optional MATCH clauses (slug filtering); parameterised for values
- Path alias `@/*` maps to project root
