import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from queries import (
    CHECK_DB_EXISTS,
    ADD_EPISODES_WITH_SCENES,
    CLEANUP_ORPHANS,
    CLEANUP_EXACT_DUPLICATES,
    CLEANUP_THIN_REPEATS,
    CLEANUP_DATE_SHIFTS,
    LINK_SHARED_TERMS_PREAMBLE,
    LINK_PASS1_BODY,
    LINK_PASS2_BODY,
    MANUAL_LINK_CHARACTER,
    FIND_EMPTY_SCENES,
    MERGE_SCENES,
    FIND_SINGLE_SCENE_EPISODES,
    DELETE_EPISODES,
)

load_dotenv()


class ArchersDatabase:
    def __init__(self, setup_file="import_base_data.txt"):
        module_dir = os.path.dirname(os.path.abspath(__file__))
        self.setup_file_path = os.path.join(module_dir, setup_file)

        URI = os.getenv("NEO4J_URI")
        USER = os.getenv("NEO4J_USER")
        PWD = os.getenv("NEO4J_PASSWORD")

        if not all([URI, USER, PWD]):
            raise ValueError("Missing Neo4j credentials in .env file")

        self.driver = GraphDatabase.driver(URI, auth=(USER, PWD))
        self.setup_database()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def setup_database(self):
        with self.driver.session() as session:
            exists = session.run(CHECK_DB_EXISTS).single()

            if exists is not None: return None

            print(f"Database empty. Loading initial setup from {self.setup_file_path}...")

            if os.path.exists(self.setup_file_path):
                with open(self.setup_file_path, "r") as f:
                    statements = f.read().split(";")

                    for statement in statements:
                        cmd = statement.strip()
                        if cmd:
                            session.run(cmd)
                print("Initial characters and constraints imported successfully.")
            else:
                print(f"Warning: {self.setup_file_path} not found. Proceeding with empty database.")

    def close(self):
        self.driver.close()

    def add_episodes_with_scenes(self, episode_list):
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

        CHUNK_SIZE = 500
        total_nodes = 0

        with self.driver.session() as session:
            for i in range(0, len(formatted_batch), CHUNK_SIZE):
                chunk = formatted_batch[i:i + CHUNK_SIZE]
                result = session.run(ADD_EPISODES_WITH_SCENES, batch=chunk)
                summary = result.consume()
                chunk_nodes = summary.counters.nodes_created
                total_nodes += chunk_nodes

                if len(formatted_batch) > CHUNK_SIZE:
                    print(f"Progress: {min(i + CHUNK_SIZE, len(formatted_batch))}/{len(formatted_batch)} episodes processed")

            print(f"Added {total_nodes} new node(s) to database.")
            return total_nodes

    def handle_duplicate_episodes(self):
        queries = {
            "orphans": CLEANUP_ORPHANS,
            "exact_duplicates": CLEANUP_EXACT_DUPLICATES,
            "thin_repeats": CLEANUP_THIN_REPEATS,
            "date_shifts": CLEANUP_DATE_SHIFTS,
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

    def find_single_scene_episodes(self):
        with self.driver.session() as session:
            records = list(session.run(FIND_SINGLE_SCENE_EPISODES))
            return [rec["pid"] for rec in records]

    def delete_episodes(self, pids):
        with self.driver.session() as session:
            result = session.run(DELETE_EPISODES, pids=pids)
            record = result.single()
            count = record["count"] if record else 0
            print(f"Deleted {count} episode(s) for re-scrape.")
            return count

    def link_all_characters_to_scenes(self, episode_pids=None):
        pid_filter = "AND e.pid IN $pids" if episode_pids is not None else ""

        pass1_query = LINK_SHARED_TERMS_PREAMBLE + LINK_PASS1_BODY.format(pid_filter=pid_filter)
        pass2_query = LINK_SHARED_TERMS_PREAMBLE + LINK_PASS2_BODY.format(pid_filter=pid_filter)

        with self.driver.session() as session:
            params = {'pids': episode_pids} if episode_pids is not None else {}

            print("Pass 1: Linking unambiguous characters...")
            result = session.run(pass1_query, **params)
            pass1_links = result.consume().counters.relationships_created
            print(f"Pass 1 complete. Relationships created: {pass1_links}")

            print("Pass 2: Resolving ambiguous characters...")
            result = session.run(pass2_query, **params)
            pass2_links = result.consume().counters.relationships_created
            print(f"Pass 2 complete. Relationships created: {pass2_links}")

            total_links = pass1_links + pass2_links
            print(f"Finished. Total relationships created: {total_links}")
            return total_links

    def manual_link_character_to_scenes(self, scene_ids, character_name):
        with self.driver.session() as session:
            result = session.run(MANUAL_LINK_CHARACTER, char_name=character_name, scene_ids=scene_ids)
            record = result.single()
            links = record['links_created'] if record else 0

            if links > 0:
                print(f"Created {links} link(s) for '{character_name}'.")
            else:
                print(f"Warning: No links created. Check if character name or scene IDs exist.")


    def cleanup_empty_scenes(self):
        with self.driver.session() as session:
            records = list(session.run(FIND_EMPTY_SCENES))

            if not records:
                print("No empty scenes with predecessors found.")
                return

            for i, rec in enumerate(records):
                print(f"\n--- Match {i+1} of {len(records)} ---")
                print(f"PREVIOUS SCENE ({rec['target_id']}): {rec['target_text']}")
                print(f"EMPTY SCENE    ({rec['empty_id']}): {rec['empty_text']}")

                choice = input(f"Merge {rec['empty_id']} into {rec['target_id']}? (y/n): ").lower()

                if choice == 'y':
                    session.run(MERGE_SCENES, target_id=rec['target_id'], empty_id=rec['empty_id'])
                    print(f"Merged scene {rec['empty_id']}.")
                else:
                    print("Skipped.")
