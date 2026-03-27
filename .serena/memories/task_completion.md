# When a Task is Complete

## Web app changes
1. Run `npm run lint` — fix any ESLint errors before considering done
2. Run `npm run build` — ensure no TypeScript or build errors

## Scraper changes
- No automated tests; verify logic manually with `--dry-run`
- Run `python scraper/archersscrape.py update --dry-run` to check scraper changes

## No test framework is configured for either part of the project.
