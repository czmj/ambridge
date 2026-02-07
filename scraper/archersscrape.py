import os
import json
import argparse
import sys
from datetime import datetime

from web_scraper import WebScraper
from processor import EpisodeProcessor
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

def update_db(from_cache=False):
    series_id = os.getenv("SERIES_ID")
    cache_file = os.getenv("CACHE_FILE")

    cached_data, last_cached_date = load_cache(cache_file)

    if from_cache:
        if not cached_data:
            print("Error: No cache file found to reset from.")
            return
        episodes_to_process = cached_data
    else:
        episodes_to_process = scrape_episodes(series_id, cache_file, cached_data, last_cached_date)

    if not episodes_to_process:
        return

    print(f"Processing {len(episodes_to_process)} episodes...")
    processor = EpisodeProcessor()
    detailed_episode_data = processor.process_batch(episodes_to_process)

    if not detailed_episode_data:
        return

    db = ArchersDatabase()
    try:
        db.add_episodes_with_scenes(detailed_episode_data)
        db.handle_duplicate_episodes()
        new_pids = [ep['pid'] for ep in detailed_episode_data]
        db.link_all_characters_to_scenes(episode_pids=new_pids)
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="Neo4j Ambridge database")
    subparsers = parser.add_subparsers(dest="command")

    update_parser = subparsers.add_parser('update', help='Scrape new episodes or reset from cache')
    update_parser.add_argument('--from-cache', action='store_true', help="Clear and rebuild DB from cache")

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
            update_db(args.from_cache)
        elif args.command == 'link':
            db = ArchersDatabase()
            try:
                print(f"Linking character '{args.character}' to scenes...")
                db.manual_link_character_to_scenes(args.scenes, args.character)
            finally:
                db.close()
        elif args.command == 'cleanup':
            db = ArchersDatabase()
            try:
                db.cleanup_empty_scenes()
            finally:
                db.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
