# Code Conventions

## TypeScript / Next.js
- Path alias `@/*` maps to project root
- Server actions use `"use server"` directive; only `FamilyTree` uses `"use client"`
- Cypher queries: string interpolation for sort direction and optional MATCH clauses; parameterised for values
- Neo4j integer parameters must use `neo4j.int()` wrapper (e.g. `neo4j.int(skip)`)
- `executeQuery()` in `actions.ts` is the single point for all DB reads — don't open sessions elsewhere in the web app

## import_base_data.txt (seed data)
- `birth_name`: set when current name differs from birth name (married women, name changes)
- `aliases`: **only** for characters living post-2007 (BBC archive start); pre-2007 deceased = no aliases
- `keywords`: extra terms for disambiguation in scene text
- `notes`: factual disputes or context (e.g. disputed DOB)
- Slug auto-generated from `birth_name` (if set) else `name` by APOC query at end of file
- Character variables in the Cypher script are scoped to the whole file — variable names must be unique across all MERGE statements

## Python scraper
- Pre-compile regex at module level (see `processor.py`)
- All Cypher in `queries.py` as module-level constants — no inline Cypher elsewhere
- `ArchersDatabase` is a context manager — always use `with` block
