import os
import json
from datetime import datetime


def load_cache(cache_file):
    if not os.path.exists(cache_file):
        return [], None

    print(f"Loading existing data from cache ({cache_file})...")
    with open(cache_file, "r") as f:
        cached_data = json.load(f)

    last_date = None
    if cached_data:
        last_date = datetime.strptime(cached_data[0]['date'], "%Y-%m-%d").date()

    return cached_data, last_date
