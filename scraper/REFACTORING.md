# Scraper Refactoring Plan

## Known Bugs

### 1. Relative path for seed data (`database.py:23`)
`setup_file="import_base_data.txt"` only works when CWD is `scraper/`. Running from the project root silently skips setup.
**Fix:** Resolve relative to module directory using `os.path.dirname(os.path.abspath(__file__))`.

### 2. Weight comment/code mismatch (`queries.py:121,128`)
Comments say distant_family=2 and friends=1, but the actual formula on line 157 is `(close_family * 3) + (cohabitant_count * 2) + (friends * 2) + distant_family + keyword_score` — so distant_family=1 and friends=2. The code values are sensible (friends in a scene are a stronger signal than distant relatives). Fix the comments, not the code.

### 3. Missing env var validation (`archersscrape.py:56-57`)
`SERIES_ID` and `CACHE_FILE` are used without checking if they're set. If `CACHE_FILE` is `None`, `load_cache(None)` crashes with a confusing `TypeError`. Add early validation; `SERIES_ID` is only needed when not using `--from-cache`.

---

## Simplifications

### 1. Convert `EpisodeProcessor` to plain functions (`processor.py`)
The class is stateless — `self` is never used for state. Convert `process_episode` and `process_batch` to module-level functions. Update import in `archersscrape.py` and remove class instantiation.

### 2. Hoist regex patterns to module level (`processor.py:6-22`)
Patterns are defined inside the method body and rebuilt on every call (~5,800 times on full rebuild). Move to module-level pre-compiled constants: `SPLIT_PATTERN`, `ELLIPSES_PATTERN`, `BOILERPLATE_PATTERN`, `CREDIT_MARKERS`.

### 3. Fix non-idiomatic check (`processor.py:42`)
`if not len(scenes_to_clean):` should be `if not scenes_to_clean:`.

### 4. Add context manager to `ArchersDatabase` (`database.py`)
Add `__enter__`/`__exit__` so callers can use `with ArchersDatabase() as db:` instead of three separate `try/finally/close()` blocks in `archersscrape.py`.

### 5. Extract `MAX_WORKERS` constant (`web_scraper.py:9`)
Replace `__init__` parameter with a module-level constant. The value is never overridden by callers.

---

## Performance Improvements

### 1. Increase thread pool workers: 3 to 5 (`web_scraper.py`)
~40% faster scraping for full rebuilds. 5 workers is still polite; no risk of BBC rate limiting.

### 2. Skip duplicate cleanup on small incremental updates (`archersscrape.py:82`)
`handle_duplicate_episodes()` runs 4 full-graph scan queries on every update, even with 1-2 new episodes. Gate behind `if from_cache or len(episodes_to_process) > 10:`. Saves ~10-20s on typical daily updates.

### 3. Batch Neo4j upserts in chunks of 500 (`database.py:59-84`)
Currently sends all episodes in a single `UNWIND`. Chunking into batches of 500 gives more predictable memory usage, prevents transaction timeouts on full rebuilds, and enables progress feedback.

---

## New Features

### 1. Timing output (`archersscrape.py`)
Wrap each phase (scrape, process, upsert, cleanup, linking) with `time.perf_counter()` timing. Zero-risk; helps diagnose performance.

### 2. `--dry-run` flag (`archersscrape.py`)
Add to `update` subparser. Runs scrape and process steps but skips all database operations. Prints episode count, date range, and scene count.

---

## Implementation Order

| Step | Category | Change | Risk | Files |
|------|----------|--------|------|-------|
| 1 | Simplify | Remove `EpisodeProcessor` class, hoist patterns, fix idiom | Very Low | `processor.py`, `archersscrape.py` |
| 2 | Simplify | Add context manager to `ArchersDatabase` | Low | `database.py`, `archersscrape.py` |
| 3 | Simplify | Extract `MAX_WORKERS` constant | Very Low | `web_scraper.py` |
| 4 | Bug fix | Fix relative path for seed data | Low | `database.py` |
| 5 | Bug fix | Fix date filter `>=` to `>` | Low | `web_scraper.py` |
| 6 | Bug fix | Fix weight comments | Very Low | `queries.py` |
| 7 | Bug fix | Validate env vars | Low | `archersscrape.py` |
| 8 | Perf | Increase workers to 5 | Low | `web_scraper.py` |
| 9 | Perf | Skip cleanup on incremental updates | Low | `archersscrape.py` |
| 10 | Perf | Batch upserts in chunks | Medium | `database.py` |
| 11 | Perf | Add retry with backoff + timeout | Low | `web_scraper.py` |
| 12 | Feature | Add timing output | Very Low | `archersscrape.py` |
| 13 | Feature | Add `--dry-run` flag | Low | `archersscrape.py` |

## What NOT to Change

- **Pass 2 Cypher query** (135 lines in `queries.py`): Complex but every section is essential. Refactoring risks changing link output.
- **`import_base_data.txt`**: Uses Cypher variable references across `;`-separated statements. Fragile but functional; restructuring has no benefit.
- **`cache.py`**: 19 lines, does one thing. Already minimal.

## Verification

No test framework exists. Verify empirically:
1. Before changes: run `update --from-cache` on a clean DB, record total APPEARS_IN count and nodes created
2. After each step: run same command, confirm identical counts
3. For the date fix (step 5): run `update` and verify today's episode is included if available
