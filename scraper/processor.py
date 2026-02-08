import re

SPLIT_PATTERN = re.compile(
    r'\n+|(?:(?<=[.!?])\s+(?=Meanwhile|Back at|Elsewhere|At\s[A-Z]|[\s]{2}))'
)
ELLIPSES_PATTERN = re.compile(r'(\.{3,}|…{2,}|…\.|\.\.…)')
BOILERPLATE_PATTERN = re.compile(
    r'^\s*(?:'
    r'Rural drama(?: series)?(?: set in Ambridge)?|'
    r'Contemporary drama in a rural setting|'
    r'The week\'s events in Ambridge|'
    r')\.?\s*$'
)
CREDIT_MARKERS = (
    "Written by", "Writer", "WRITER", "Episode written by",
    "Directed by", "Director", "DIRECTOR",
    "Edited by", "Editor", "EDITED BY",
    "Repeated on",
    "If you are feeling",  # actionline blurb
    "If you have been affected"
)


def process_episode(episode):
    text_to_process = episode.get("blurb") or episode.get("synopsis")
    raw_scenes = [s.strip() for s in SPLIT_PATTERN.split(text_to_process) if s.strip()]

    if not raw_scenes:
        return None

    scenes_to_clean = []
    for s in raw_scenes:
        if (len(s) < 100 and ELLIPSES_PATTERN.search(s)) or s.startswith(CREDIT_MARKERS):
            break
        if scenes_to_clean and s[0].islower():
            scenes_to_clean[-1] = f"{scenes_to_clean[-1]} {s}"
            continue

        scenes_to_clean.append(s)

    if not scenes_to_clean:
        scenes_to_clean = [episode.get("synopsis")]

    filtered_scenes = [
        s for s in scenes_to_clean
        if not BOILERPLATE_PATTERN.match(s.strip())
    ]

    return {
        **episode,
        "scenes": filtered_scenes
    }


def process_batch(episode_list):
    results = [process_episode(ep) for ep in episode_list]
    return [ep for ep in results if ep is not None]
