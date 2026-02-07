import re


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
