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
- `Character -[:SPOUSE|CHILD_OF|SIBLING|ROMANTIC_RELATIONSHIP|FRIEND_OF]- Character`
- `Character -[:LIVES_AT|WORKS_AT|OWNS]-> Location` (with temporal `from`/`to` properties)

Constraints: `Episode.pid` is node key, `Scene.id` is node key, `Character.slug` is unique.

### Scraper (`scraper/`)

Six Python files plus seed data:

- **`archersscrape.py`** — CLI entry point (argparse). Three subcommands: `update`, `link`, `cleanup`. Orchestrates the scrape→process→upsert→link pipeline.
- **`web_scraper.py`** — `WebScraper` class. Fetches BBC episode listing pages and individual episode pages concurrently via `ThreadPoolExecutor(max_workers=3)`. Two-batch approach: first scrape listing pages for PIDs, then fetch each episode's metadata/blurb.
- **`processor.py`** — `EpisodeProcessor` class (stateless). Splits episode blurbs into scenes using regex (newlines, transition words like "Meanwhile"/"Back at"). Detects and strips credits/boilerplate. Merges lowercase-starting fragments into previous scenes.
- **`database.py`** — `ArchersDatabase` class. Neo4j operations: batch episode/scene upserts via `MERGE`, four duplicate cleanup strategies (orphans, exact duplicates, thin repeats, date shifts), and two-pass character-to-scene linking.
- **`queries.py`** — All Cypher query strings as module-level constants (243 lines). The Pass 2 disambiguation query is 135 lines of Cypher handling family scoring, co-habitation, keywords, rival detection, and memorial exclusion.
- **`cache.py`** — Single `load_cache()` function. Reads cached episode JSON and returns the last cached date.

**Character linking algorithm:** Two-pass approach. Pass 1 links unambiguous characters (no shared aliases) via regex matching against scene text. Pass 2 handles ambiguous characters (shared aliases like "Jack", "Dan", "Justin") using a scoring system: close family in scene (weight 3), co-habitants/co-workers (weight 2), friends (weight 2), distant family (weight 1), contextual keywords (2 per match). Definite matches override scoring (full name in scene/episode, birth/death date match). Rival exclusion prevents linking when a rival's full name appears, or memorial keywords suggest a deceased character is being discussed.

**Known issues:** See `scraper/REFACTORING.md` for documented bugs and planned improvements.

Initial character/location seed data lives in `scraper/import_base_data.txt`. Requires APOC plugin for slug generation during initial setup.

## Environment Variables

Set in `.env` (not committed): `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `SERIES_ID`, `CACHE_FILE`.

## Key Conventions

- Neo4j integer parameters must use `neo4j.int()` wrapper (e.g. `neo4j.int(skip)`)
- Cypher queries use string interpolation for sort direction and optional MATCH clauses (slug filtering); parameterised for values
- Path alias `@/*` maps to project root
