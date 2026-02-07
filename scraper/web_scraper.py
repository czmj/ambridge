import requests
import re
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime


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
            print(f"Error getting episode data: PID {pid}: {e}")
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
