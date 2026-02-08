import os
import json
import argparse
import sys
import time
from datetime import datetime

from web_scraper import WebScraper
from processor import process_batch
from database import ArchersDatabase
from cache import load_cache


def scrape_episodes(series_id, cache_file, cached_data, last_cached_date):
    scraper = WebScraper()

    if not last_cached_date:
        print("No cache found. Performing full scrape...")
        episodes = scraper.get_all_episodes(series_id)
        with open(cache_file, "w") as f:
            json.dump(episodes, f)
        return episodes

    print(f"Searching for episodes newer than {last_cached_date}...")
    new_episodes = []
    current_page = 1
    found_overlap = False

    while not found_overlap:
        print(f"Checking page {current_page}...")
        page_results = scraper.get_paginated_episodes(series_id, first_page=current_page, last_page=current_page)

        if not page_results:
            break

        for ep in page_results:
            ep_date = datetime.strptime(ep['date'], "%Y-%m-%d").date()
            if ep_date > last_cached_date:
                new_episodes.append(ep)
            else:
                found_overlap = True
                break

        if not found_overlap:
            current_page += 1

    if new_episodes:
        print(f"Found {len(new_episodes)} new episode(s).")
        with open(cache_file, "w") as f:
            json.dump(new_episodes + cached_data, f)
    else:
        print("No new episodes found.")

    return new_episodes


def rescrape_single_scene_episodes(db):
    pids = db.find_single_scene_episodes()
    if not pids:
        return []

    print(f"Found {len(pids)} recent episode(s) with only 1 scene — re-scraping...")
    scraper = WebScraper()
    episodes = [scraper.get_episode(pid) for pid in pids]
    episodes = [ep for ep in episodes if ep is not None]

    rescrape_pids = [ep['pid'] for ep in episodes]
    if rescrape_pids:
        db.delete_episodes(rescrape_pids)

    return episodes


def update_db(from_cache=False, dry_run=False):
    start_time = time.perf_counter()

    cache_file = os.getenv("CACHE_FILE")
    if not cache_file:
        raise ValueError("CACHE_FILE environment variable is not set")

    if not from_cache:
        series_id = os.getenv("SERIES_ID")
        if not series_id:
            raise ValueError("SERIES_ID environment variable is not set (required when not using --from-cache)")

    cached_data, last_cached_date = load_cache(cache_file)

    if from_cache:
        if not cached_data:
            print("Error: No cache file found to reset from.")
            return
        episodes_to_process = cached_data
    else:
        scrape_start = time.perf_counter()
        episodes_to_process = scrape_episodes(series_id, cache_file, cached_data, last_cached_date)
        print(f"Scraping completed in {time.perf_counter() - scrape_start:.2f}s")

    if not episodes_to_process:
        episodes_to_process = []

    process_start = time.perf_counter()

    with ArchersDatabase() as db:
        # Re-scrape recent episodes that only had 1 scene (incomplete blurb)
        if not from_cache:
            rescraped = rescrape_single_scene_episodes(db)
            if rescraped:
                existing_pids = {ep['pid'] for ep in episodes_to_process}
                for ep in rescraped:
                    if ep['pid'] not in existing_pids:
                        episodes_to_process.append(ep)

        if not episodes_to_process:
            print("No episodes to process.")
            return

        print(f"Processing {len(episodes_to_process)} episodes...")
        detailed_episode_data = process_batch(episodes_to_process)
        print(f"Processing completed in {time.perf_counter() - process_start:.2f}s")

        if not detailed_episode_data:
            return

        if dry_run:
            total_scenes = sum(len(ep['scenes']) for ep in detailed_episode_data)
            dates = [ep['date'] for ep in detailed_episode_data]
            print(f"\n--- DRY RUN SUMMARY ---")
            print(f"Episodes to process: {len(detailed_episode_data)}")
            print(f"Date range: {min(dates)} to {max(dates)}")
            print(f"Total scenes: {total_scenes}")
            print(f"Average scenes per episode: {total_scenes / len(detailed_episode_data):.1f}")
            print(f"Dry run completed in {time.perf_counter() - start_time:.2f}s")
            return

        upsert_start = time.perf_counter()
        db.add_episodes_with_scenes(detailed_episode_data)
        print(f"Database upsert completed in {time.perf_counter() - upsert_start:.2f}s")

        if from_cache or len(detailed_episode_data) > 10:
            cleanup_start = time.perf_counter()
            db.handle_duplicate_episodes()
            print(f"Cleanup completed in {time.perf_counter() - cleanup_start:.2f}s")

        link_start = time.perf_counter()
        new_pids = [ep['pid'] for ep in detailed_episode_data]
        db.link_all_characters_to_scenes(episode_pids=new_pids)
        print(f"Character linking completed in {time.perf_counter() - link_start:.2f}s")

    print(f"\nTotal update time: {time.perf_counter() - start_time:.2f}s")

def main():
    parser = argparse.ArgumentParser(description="Neo4j Ambridge database")
    subparsers = parser.add_subparsers(dest="command")

    update_parser = subparsers.add_parser('update', help='Scrape new episodes or reset from cache')
    update_parser.add_argument('--from-cache', action='store_true', help="Clear and rebuild DB from cache")
    update_parser.add_argument('--dry-run', action='store_true', help="Run scrape and process steps without database operations")

    link_parser = subparsers.add_parser('link', help='Manually link a character to a scene')
    link_parser.add_argument('--scenes', type=str, nargs='+', required=True, help='List of scene IDs (space-separated)')
    link_parser.add_argument('--character', type=str, required=True, help='Character name or ID')

    subparsers.add_parser('cleanup', help='Review and merge empty scenes')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == 'update':
            update_db(args.from_cache, dry_run=args.dry_run)
        elif args.command == 'link':
            with ArchersDatabase() as db:
                print(f"Linking character '{args.character}' to scenes...")
                db.manual_link_character_to_scenes(args.scenes, args.character)
        elif args.command == 'cleanup':
            with ArchersDatabase() as db:
                db.cleanup_empty_scenes()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
