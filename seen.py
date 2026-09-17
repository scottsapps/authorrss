import json
import os


def load_seen(path):
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return set(json.load(f))


def save_seen(path, urls):
    with open(path, "w") as f:
        json.dump(sorted(urls), f, indent=2)
