import requests
import os
import re
import json
import argparse
import sys
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

class WebScraper:
    def __init__(self, max_workers=3):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        })
        self.max_workers = max_workers

    def _get_soup(self, url):
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def get_episode(self, pid):
        try:
            soup = self._get_soup(f"https://www.bbc.co.uk/programmes/{pid}")
            if not soup: return None

            heading = soup.find('h1').get_text()
            date_match = re.compile(r'(\d{2}/\d{2}/\d{4})').search(heading)

            if not date_match:
                print(f"Ignoring special episode: {heading} (PID: {pid})")
                return None
            
            date = datetime.strptime(date_match.group(1), "%d/%m/%Y").date()
            formatted_date = date.strftime('%Y-%m-%d')

            if date >= datetime.now().date(): 
                print(f"Ignoring future episode: {formatted_date} (PID: {pid})")
                return None
 
            synopsis_el = (soup.find(class_="longest-synopsis") or soup.find(class_="synopsis-toggle__short"))
            description_el = soup.find(class_="synopsis-toggle__long") or synopsis_el

            for line_break in description_el.find_all('br'):
                line_break.replace_with("\n")

            blurb_text = "\n".join([p.get_text() for p in description_el.find_all("p")])
            synopsis_text = synopsis_el.find('p').get_text(strip=True)

            if "Rpt" in blurb_text: 
                print(f"Ignoring repeat: {formatted_date} (PID: {pid})")
                return None

            return {
                'pid': pid,
                'date': date.strftime("%Y-%m-%d"),
                'blurb': blurb_text,
                'synopsis': synopsis_text
            }
        except Exception as e:
            print(f"Error getting episode data: PID {pid}", e)
            return None

    def get_paginated_episodes(self, series_id, first_page=1, last_page=1):
        all_pids = []
        pages = [f"https://www.bbc.co.uk/programmes/{series_id}/episodes/guide?page={i}" for i in range(first_page, last_page + 1)]

        # Batch 1: Concurrent Page Scraping for PIDs
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_page = {executor.submit(self._get_soup, url): url for url in pages}
            completed_pages = 0
            for future in as_completed(future_to_page):
                soup = future.result()
                if soup:
                    all_pids.extend([i['data-pid'] for i in soup.find_all(attrs={"data-pid": True})])
                completed_pages += 1
                print(f"Indexing: {completed_pages}/{len(pages)} pages processed", end='\r')
        
        print(f"\nFound {len(all_pids)} episode(s) in index")

        # Batch 2: Concurrent Metadata Retrieval
        episodes = []
        unique_pids = list(set(all_pids))
        total_pids = len(unique_pids)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_pid = {executor.submit(self.get_episode, pid): pid for pid in unique_pids}
            completed_episodes = 0

            for future in as_completed(future_to_pid):
                result = future.result()

                if result:
                    episodes.append(result)

                completed_episodes += 1
                print(f"Scraping: {completed_episodes}/{total_pids} episodes", end='\r')

        print(f"\n")
        return sorted(episodes, key=lambda x: x['date'] or '', reverse=True)

    def get_all_episodes(self, series_id):
        url = f"https://www.bbc.co.uk/programmes/{series_id}/episodes/guide"
        soup = self._get_soup(url)
        last_page_node = soup.find("li", class_="pagination__page--last")
        last_page = int(last_page_node.get_text())

        return self.get_paginated_episodes(series_id, 1, last_page)

class EpisodeProcessor:
    def process_episode(self, episode):
        split_pattern = r'\n+|(?:(?<=[.!?])\s+(?=Meanwhile|Back at|Elsewhere|At\s[A-Z]|[\s]{2}))'
        ellipses_pattern = r'(\.{3,}|…{2,}|…\.|\.\.…)'
        boilerplate_pattern = (
            r'^\s*(?:'
            r'Rural drama(?: series)?(?: set in Ambridge)?|'
            r'Contemporary drama in a rural setting|'
            r'The week\'s events in Ambridge|'
            r')\.?\s*$'
        )
        credit_markers = (
            "Written by", "Writer", "WRITER", "Episode written by",
            "Directed by", "Director", "DIRECTOR",
            "Edited by", "Editor", "EDITED BY",
            "Repeated on",
            "If you are feeling", # actionline blurb
            "If you have been affected"
        )

        text_to_process = episode.get("blurb") or episode.get("synopsis")
        raw_scenes = [s.strip() for s in re.split(split_pattern, text_to_process) if s.strip()]

        if not raw_scenes:
            return None

        scenes_to_clean = []
        for s in raw_scenes:
            # Stop processing at the credits
            if (len(s) < 100 and re.search(ellipses_pattern, s)) or s.startswith(credit_markers):
                break
            # Merge lines starting with a lowercase letter with previous scene
            if scenes_to_clean and s[0].islower():
                scenes_to_clean[-1] = f"{scenes_to_clean[-1]} {s}"
                continue

            scenes_to_clean.append(s)
        
        if not len(scenes_to_clean):
            scenes_to_clean = [episode.get("synopsis")]

        # Remove boilerplate like "Rural drama series" from each scene.
        filtered_scenes = [
            s for s in scenes_to_clean 
            if not re.match(boilerplate_pattern, s.strip())
        ]

        return {
            **episode,
            "scenes": filtered_scenes
        }

    def process_batch(self, episode_list):
        results = [self.process_episode(ep) for ep in episode_list]
        return [ep for ep in results if ep is not None]

class ArchersDatabase:
    def __init__(self, setup_file="import_base_data.txt"):

        URI = os.getenv("NEO4J_URI")
        USER = os.getenv("NEO4J_USER")
        PWD = os.getenv("NEO4J_PASSWORD")
        
        # Check if variables were loaded correctly to avoid connection errors
        if not all([URI, USER, PWD]):
            raise ValueError("Missing Neo4j credentials in .env file")
            
        self.driver = GraphDatabase.driver(URI, auth=(USER, PWD))
        self.setup_database(setup_file)

    def setup_database(self, setup_file):
        with self.driver.session() as session:
            count_res = session.run("MATCH p=()-[]->() RETURN count(p) as count").single()
            
            if count_res["count"] > 0: return None

            print(f"Database empty. Loading initial setup from {setup_file}...")

            if os.path.exists(setup_file):
                with open(setup_file, "r") as f:
                    statements = f.read().split(";")
                    
                    for statement in statements:
                        cmd = statement.strip()
                        if cmd:
                            session.run(cmd)
                print("Initial characters and constraints imported successfully.")
            else:
                print(f"Warning: {setup_file} not found. Proceeding with empty database.")

    def close(self):
        self.driver.close()

    def add_episodes_with_scenes(self, episode_list):
        query = """
        UNWIND $batch AS ep
        MERGE (e:Episode {pid: ep.pid})
        ON CREATE SET e.date = date(ep.date),
                    e.synopsis = ep.synopsis
        
        WITH e, ep
        UNWIND ep.scenes AS scene_data
        MERGE (s:Scene {id: scene_data.sid})
        SET s.order = scene_data.index,
            s.text = scene_data.text
        MERGE (s)-[:PART_OF]->(e)
        """

        formatted_batch = []
        for ep in episode_list:
            pid = ep["pid"]
            formatted_batch.append({
                "pid": pid,
                "date": ep["date"],
                "synopsis": ep["synopsis"],
                "scenes": [
                    {
                        "sid": f"{pid}_{i}",
                        "index": i, 
                        "text": text
                    } 
                    for i, text in enumerate(ep["scenes"])
                ]
            })

        with self.driver.session() as session:
            result = session.run(query, batch=formatted_batch)
            summary = result.consume()
            new_nodes = summary.counters.nodes_created

            print(f"Added {new_nodes} new node(s) to database.")

            return new_nodes

    def handle_duplicate_episodes(self):
        queries = {
            "orphans": """
                MATCH (e:Episode)
                WHERE (e.synopsis CONTAINS "The week's events in Ambridge" 
                OR e.synopsis CONTAINS "Contemporary drama in a rural setting")
                AND NOT (e)<-[:PART_OF]-(:Scene)
                DETACH DELETE e RETURN count(*) as count""",
            "exact_duplicates": """
                MATCH (s:Scene)-[:PART_OF]->(e:Episode)
                WITH e, e.synopsis as syn, s.text as txt ORDER BY e.date, s.id
                WITH e, syn, collect(txt) as seq ORDER BY e.date, e.pid
                WITH syn, seq, collect(e) as eps WHERE size(eps) > 1
                UNWIND eps[1..] as d
                OPTIONAL MATCH (ds:Scene)-[:PART_OF]->(d)
                DETACH DELETE d, ds RETURN count(d) as count""",
            "thin_repeats": """
                MATCH (s:Scene)-[:PART_OF]->(e:Episode)
                WITH e, e.date as d, count(s) as c ORDER BY d DESC, c DESC
                WITH d, collect({n: e, c: c}) as list WHERE size(list) = 2 AND list[0].c > 1 AND list[1].c = 1
                WITH list[1].n as d
                OPTIONAL MATCH (ds:Scene)-[:PART_OF]->(d)
                DETACH DELETE d, ds RETURN count(d) as count""",
            "date_shifts": """
                MATCH (e:Episode)
                WITH e.date as cur, collect(e) as list WHERE size(list) = 2
                OPTIONAL MATCH (y:Episode) WHERE y.date = cur - duration({days: 1})
                WITH cur, list, y WHERE y IS NULL

                // Calculate target date and check it isn't Saturday (6)
                WITH list[1] as target, cur, (cur - duration({days: 1})) as newDate
                WHERE newDate.dayOfWeek <> 6

                SET target.date = newDate
                RETURN count(target) as count"""
        }

        print("Cleaning up duplicates...")

        results = {}
        with self.driver.session() as session:
            for key, cypher in queries.items():
                res = session.run(cypher).single()
                results[key] = res["count"] if res else 0

        total = sum(results.values())
        if total > 0:
            print(f"Cleanup complete: {results}")
        return total
        
    def get_character_segments(self):
        shared_terms_query = """
            MATCH (c:Character)
            UNWIND (c.aliases + [c.name]) AS term
            WITH term, count(c) AS usage_count
            WHERE usage_count > 1
            RETURN collect(DISTINCT term) AS shared_terms
        """
    
        chars_query = """
            MATCH (c:Character)
            WITH c, (c.aliases + [c.name]) AS character_terms
            WHERE 
                ($find_ambiguous AND ANY(term IN character_terms WHERE term IN $shared_terms))
                OR 
                (NOT $find_ambiguous AND NONE(term IN character_terms WHERE term IN $shared_terms))
            RETURN c.name as name, c.aliases as aliases
        """

        with self.driver.session() as session:
            shared_result = session.run(shared_terms_query).single()
            shared_terms = shared_result["shared_terms"] if shared_result else []
            
            unambiguous = session.run(
                chars_query, 
                find_ambiguous=False, 
                shared_terms=shared_terms
            ).data()
            
            ambiguous = session.run(
                chars_query, 
                find_ambiguous=True, 
                shared_terms=shared_terms
            ).data()
            
            return unambiguous, ambiguous

    def link_all_characters_to_scenes(self):
        unambiguous, ambiguous = self.get_character_segments()
        
        pass1_query = """
            MATCH (c:Character {name: $name})
            MATCH (s:Scene)-[:PART_OF]->(e:Episode)
            WHERE s.text =~ $regex
              AND (c.dob IS NULL OR e.date >= c.dob)
              AND (c.dod IS NULL OR e.date <= c.dod)
              AND (c.first_appearance IS NULL OR e.date >= c.first_appearance)
              AND (c.last_appearance IS NULL OR e.date <= c.last_appearance)
            MERGE (c)-[:APPEARS_IN]->(s)
            RETURN count(s) as matches
        """

        pass2_query = """
            MATCH (c:Character {name: $name})
            MATCH (s:Scene)-[:PART_OF]->(e:Episode)
            WHERE s.text =~ $regex
              AND (c.dob IS NULL OR e.date >= c.dob)
              AND (c.dod IS NULL OR e.date <= c.dod)
              AND (c.first_appearance IS NULL OR e.date >= c.first_appearance)
              AND (c.last_appearance IS NULL OR e.date <= c.last_appearance)
            
            // Identify conflicting characters
            OPTIONAL MATCH (other:Character)
            WHERE other <> c 
              AND ANY(a IN other.aliases WHERE a IN $aliases)
              AND (other.dob IS NULL OR e.date >= other.dob)
              AND (other.first_appearance IS NULL OR e.date >= other.first_appearance)
            
            // Count total characters currently linked to the scene
            OPTIONAL MATCH (s)<-[:APPEARS_IN]-(anyone:Character)
            WITH s, c, other, count(DISTINCT anyone) AS total_others
            
            // Count family members
            OPTIONAL MATCH (s)<-[:APPEARS_IN]-(relative:Character)
            WHERE 
                (c)-[:SPOUSE]-(relative) 
                OR (relative)-[:CHILD_OF*1..2]->(c)
                OR (c)-[:CHILD_OF*1..2]->(relative)
            
            WITH s, c, 
                 count(DISTINCT other) AS active_conflicts, 
                 total_others, 
                 count(DISTINCT relative) AS family_present
            
            // Resolution Logic
            WHERE s.text CONTAINS c.name
               OR active_conflicts = 0
               OR (total_others > 0 AND (toFloat(family_present) / total_others) >= 0.5) // TODO: Weight score more towards spouses and children than grandchildren, and pick the highest weighted option

            MERGE (c)-[:APPEARS_IN]->(s)
            RETURN count(s) as matches
        """

        with self.driver.session() as session:
            total_links = 0
            
            print(f"Pass 1: Linking {len(unambiguous)} unique characters...")
            for i, char in enumerate(unambiguous):
                aliases = char['aliases'] if char['aliases'] is not None else []
                all_names = [re.escape(char['name'])] + [re.escape(a) for a in aliases]
                regex_pattern = f".*\\b({'|'.join(all_names)})\\b.*"
                
                result = session.run(pass1_query, name=char['name'], regex=regex_pattern)
                total_links += result.consume().counters.relationships_created
                print(f"Progress: {i+1}/{len(unambiguous)} | Total Links: {total_links}", end='\r')

            print(f"\nPass 2: Resolving {len(ambiguous)} ambiguous characters...")
            for i, char in enumerate(ambiguous):
                aliases = char['aliases'] if char['aliases'] is not None else []
                all_names = [re.escape(char['name'])] + [re.escape(a) for a in aliases]
                regex_pattern = f".*\\b({'|'.join(all_names)})\\b.*"
                
                result = session.run(pass2_query, name=char['name'], regex=regex_pattern, aliases=aliases)
                total_links += result.consume().counters.relationships_created
                print(f"Progress: {i+1}/{len(ambiguous)} | Total Links: {total_links}", end='\r')
            
            print(f"\nFinished. Total relationships created: {total_links}")
            return total_links

    def manual_link_character_to_scenes(self, scene_ids, character_name):
        query = """
        MATCH (c:Character {name: $char_name})
        UNWIND $scene_ids AS s_id
        MATCH (s:Scene {id: s_id})
        MERGE (c)-[r:APPEARS_IN]->(s)
        RETURN count(r) AS links_created
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, char_name=character_name, scene_ids=scene_ids)
                record = result.single()
                
                if record and record['links_created'] > 0:
                    print(f"Successfully created {record['links_created']} link(s) for '{character_name}'.")

                    return True
                else:
                    print(f"Warning: No links created. Check if character name or scene IDs exist.")
                    return False

        except Exception as e:
            print(f"Database Error: {e}")
            return False


    def cleanup_empty_scenes(self):
        query = """
        MATCH (e:Episode)<-[:PART_OF]-(empty:Scene)
        WHERE NOT (empty)<-[:APPEARS_IN]-(:Character)
        MATCH (target:Scene)-[:PART_OF]->(e)
        WHERE target.order = empty.order - 1
        RETURN empty.id AS empty_id, empty.text AS empty_text, 
            target.id AS target_id, target.text AS target_text,
            e.pid AS episode_pid
        ORDER BY empty.id ASC
        """

        with self.driver.session() as session:
            records = list(session.run(query))
            
            if not records:
                print("No empty scenes with predecessors found.")
                return

            for i, rec in enumerate(records):
                print(f"\n--- Match {i+1} of {len(records)} ---")
                print(f"PREVIOUS SCENE ({rec['target_id']}): {rec['target_text']}")
                print(f"EMPTY SCENE    ({rec['empty_id']}): {rec['empty_text']}")
                
                choice = input(f"Merge {rec['empty_id']} into {rec['target_id']}? (y/n): ").lower()
                
                if choice == 'y':
                    merge_query = """
                    MATCH (target:Scene {id: $target_id})
                    MATCH (empty:Scene {id: $empty_id})
                    SET target.text = target.text + " " + empty.text
                    DETACH DELETE empty
                    """
                    session.run(merge_query, target_id=rec['target_id'], empty_id=rec['empty_id'])
                    print(f"Merged scene {rec['empty_id']}.")
                else:
                    print("Skipped.")

def update_db(from_cache=False):
    SERIES_ID = os.getenv("SERIES_ID")
    CACHE_FILE = os.getenv("CACHE_FILE")
    cached_data = []
    last_cached_date = None
    episodes_to_process = []

    if os.path.exists(CACHE_FILE):
        print(f"Loading existing data from cache ({CACHE_FILE})...")
        with open(CACHE_FILE, "r") as f:
            cached_data = json.load(f)
            if cached_data:
                # Assumes cache is sorted by date descending
                last_cached_date = datetime.strptime(cached_data[0]['date'], "%Y-%m-%d").date()

    if from_cache:
        print("Updating database from cache...")

        if not cached_data:
            print("Error: No cache file found to reset from.")
            return

        episodes_to_process = cached_data
    else:
        scraper = WebScraper()
        new_episodes_found = []
        
        if last_cached_date:
            print(f"Searching for episodes newer than {last_cached_date}...")
            current_page = 1
            found_overlap = False

            while not found_overlap:
                print(f"Checking page {current_page}...")
                page_results = scraper.get_paginated_episodes(SERIES_ID, first_page=current_page, last_page=current_page)
                
                if not page_results:
                    break

                for ep in page_results:
                    ep_date = datetime.strptime(ep['date'], "%Y-%m-%d").date()
                    if ep_date > last_cached_date:
                        new_episodes_found.append(ep)
                    else:
                        found_overlap = True
                        break
                
                if not found_overlap:
                    current_page += 1
            
            if new_episodes_found:
                print(f"Found {len(new_episodes_found)} new episode(s).")
                data_to_cache = new_episodes_found + cached_data

                with open(CACHE_FILE, "w") as f:
                    json.dump(data_to_cache, f)
                episodes_to_process = new_episodes_found
            else:
                print("No new episodes found.")
        else:
            print("No cache found. Performing full scrape...")
            data_to_cache = scraper.get_all_episodes(SERIES_ID)

            with open(CACHE_FILE, "w") as f:
                json.dump(data_to_cache, f)

            episodes_to_process = data_to_cache

    detailed_episode_data = []
    if episodes_to_process:
        print(f"Processing {len(episodes_to_process)} episodes...")
        processor = EpisodeProcessor()
        detailed_episode_data = processor.process_batch(episodes_to_process)

    db = ArchersDatabase()
    try:
        if detailed_episode_data:
            db.add_episodes_with_scenes(detailed_episode_data)
    
        db.handle_duplicate_episodes()
        db.link_all_characters_to_scenes()
    except Exception as e:
        print(f"Database Error: {e}")
    finally:
        db.close()
    
    print("Done.")

def main():
    parser = argparse.ArgumentParser(description="Neo4j Ambridge database")
    subparsers = parser.add_subparsers(dest="command")

    update_parser = subparsers.add_parser('update', help='Scrape new episodes or reset from cache')
    update_parser.add_argument('--from-cache', action='store_true', help="Clear and rebuild DB from cache")

    link_parser = subparsers.add_parser('link', help='Manually link a character to a scene')
    link_parser.add_argument('--scenes', type=str, nargs='+', required=True, help='List of scene IDs (space-separated)')
    link_parser.add_argument('--character', type=str, required=True, help='Character name or ID')

    cleanup_parser = subparsers.add_parser('cleanup', help='Review and merge empty scenes')

    args = parser.parse_args()

    if args.command == 'link':
        db = ArchersDatabase()
        try:
            print(f"Manually linking character '{args.character}' to scenes...")
            success = db.manual_link_character_to_scenes(args.scenes, args.character)

            if success:
                print("Link established successfully.")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            db.close()
        return

    if args.command == 'update':
        update_db(args.from_cache)
    elif args.command == 'cleanup':
        db = ArchersDatabase()
        try:
            db.cleanup_empty_scenes()
        except Exception as e:
            print(f"Error: {e}")
        finally:
            db.close()
        return
    else:
        parser.print_help()

if __name__ == "__main__":
    main()