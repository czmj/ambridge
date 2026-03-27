# Architecture

## Web App (Next.js App Router)

### Routes
- `/` — episode timeline (paginated, sortable)
- `/to/[slug]` — character-filtered timeline + family tree
- `/on/[date]` — single episode detail

Query params: `?page=N&sort=asc|desc`

### Data flow
All data fetching is in `app/actions.ts` (server actions, `"use server"`).
Single `executeQuery()` helper opens a session, runs read tx, closes session.

**Four exported actions:**
- `getTimeline({ page, pageSize, sort, slug })` — paginated episodes; slug filters by character
- `getCharacterProfile(slug)` — returns all Character node properties
- `getEpisodeByDate(date)` — single episode with scenes and characters
- `getFamilyTree(slug)` — traverses CHILD_OF/SPOUSE up to 3 hops; returns null if ≤1 node

### Components
All components are presentational (props from server pages). 
`FamilyTree` (`components/FamilyTree.tsx`) is the **only** `"use client"` component — uses `family-chart` library.

## Neo4j Graph Model

### Node types
- `Episode` — pid (node key), date, synopsis
- `Scene` — id (node key), order, text
- `Character` — slug (unique), name, gender; optional: birth_name, aliases, dob, dod, keywords, notes, first_appearance, last_appearance
- `Location` — name (node key)

### Relationships
- `Scene -[:PART_OF]-> Episode`
- `Character -[:APPEARS_IN]-> Scene`
- `Character -[:SPOUSE|CHILD_OF|SIBLING|ROMANTIC_RELATIONSHIP|FRIEND_OF]- Character`
- `Character -[:LIVES_AT|WORKS_AT|OWNS]-> Location` (temporal: from/to properties)

## Scraper Pipeline (`scraper/`)

`archersscrape.py` → orchestrates: scrape → process → upsert → link

- `web_scraper.py` — `WebScraper` class; concurrent fetching via ThreadPoolExecutor(5); exponential backoff
- `processor.py` — splits blurbs into scenes by regex (newlines, "Meanwhile", "Back at", etc.)
- `database.py` — `ArchersDatabase` context manager; batch MERGE in chunks of 500; two-pass character linking
- `queries.py` — all Cypher as module-level constants; Pass 2 disambiguation is 135-line query
- `cache.py` — `load_cache()` reads cached episode JSON

### Character linking
- Pass 1: unambiguous aliases → direct regex match
- Pass 2: ambiguous aliases (e.g. "Jack", "Dan") → scoring: close family (3), co-habitants/co-workers (2), friends (2), distant family (1), keywords (2 each)
- Definite override: full name in text, birth/death date match
- Rival exclusion: rival's full name present, or memorial context for deceased

### Re-scrape logic
Recent episodes (last 7 days) with only 1 scene are auto re-scraped on incremental update.
Duplicate cleanup skipped for small updates (≤10 episodes).
