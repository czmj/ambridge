# Suggested Commands

## Web App
```bash
npm run dev        # Dev server at localhost:3000
npm run build      # Production build
npm run lint       # ESLint (flat config, next/core-web-vitals + TypeScript)
```
No test framework configured.

## Scraper
```bash
python scraper/archersscrape.py update               # Scrape new episodes
python scraper/archersscrape.py update --from-cache  # Build DB from cached JSON
python scraper/archersscrape.py update --dry-run     # Scrape without DB writes
python scraper/archersscrape.py link --character "Name" --scenes S1 S2  # Manual link
python scraper/archersscrape.py cleanup              # Review/merge empty scenes
```

## Git
```bash
git status / git log / git diff
```
