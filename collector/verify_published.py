"""Fail deployment when Pages is not serving the feed we just uploaded."""
import json
from pathlib import Path
import time
from urllib.request import urlopen


def verify(expected, fetch, attempts=12, delay=10):
    for attempt in range(attempts):
        try:
            if fetch() == expected:
                return
        except Exception as error:
            print(f"Published feed check: {error}")
        if attempt + 1 < attempts:
            time.sleep(delay)
    raise RuntimeError("Published feed does not match the deployed artifact")


if __name__ == "__main__":
    expected = json.loads(Path("public/data/opportunities.json").read_text(encoding="utf-8"))
    def fetch():
        url = f"https://sean-p-clohessy.github.io/CPD-Finder/data/opportunities.json?verify={time.time_ns()}"
        with urlopen(url, timeout=20) as response:
            return json.load(response)
    verify(expected, fetch)
    print(f"Verified published feed: {expected['generatedAt']}")
