from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import time
from urllib.parse import urlparse
import requests
from collector.adapters import adapter_for
from collector.models import Opportunity, deduplicate, utc_now


USER_AGENT = "CPD-Finder/1.0 (+https://github.com/; polite daily educational-opportunity indexer)"


def is_direct_destination(item: Opportunity) -> bool:
    """Reject cards whose CTA merely points back to the source listing page."""
    def normalise(url: str) -> tuple[str, str, str]:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/") or "/"
        return parsed.netloc.casefold(), path.casefold(), parsed.query

    return bool(item.url and item.sourceUrl and normalise(item.url) != normalise(item.sourceUrl))


def read_sources(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]


def load_previous(path: Path) -> dict:
    if not path.exists():
        return {"opportunities": [], "sources": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"opportunities": [], "sources": []}


def collect(source_file: Path, output_file: Path, *, session=requests, today: date | None = None, delay: float = 0.75) -> dict:
    today = today or date.today()
    previous = load_previous(output_file)
    old_by_source: dict[str, list[dict]] = {}
    old_health = {item["url"]: item for item in previous.get("sources", [])}
    for item in previous.get("opportunities", []):
        old_by_source.setdefault(item.get("sourceUrl", ""), []).append(item)
    all_items: list[Opportunity] = []
    health: list[dict] = []
    now = utc_now()
    sources = read_sources(source_file)
    for index, url in enumerate(sources):
        adapter = adapter_for(url)
        try:
            response = session.get(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}, timeout=(10, 25), allow_redirects=True)
            response.raise_for_status()
            extracted = adapter.collect(response.text, url, session)
            valid = [item for item in deduplicate(extracted) if not item.expired(today) and is_direct_destination(item)]
            if not valid:
                raise ValueError("No opportunities found; retained last-known-good data")
            all_items.extend(valid)
            health.append({"url": url, "provider": adapter.provider if adapter.provider != "Unknown" else urlparse(url).netloc, "lastAttempted": now, "lastSuccessful": now, "count": len(valid), "status": "ok", "error": None})
        except Exception as error:
            retained = []
            for raw in old_by_source.get(url, []):
                try:
                    item = Opportunity(**raw)
                    if not item.expired(today) and is_direct_destination(item):
                        retained.append(item)
                except TypeError:
                    continue
            all_items.extend(retained)
            prior = old_health.get(url, {})
            health.append({"url": url, "provider": getattr(adapter, "provider", urlparse(url).netloc), "lastAttempted": now, "lastSuccessful": prior.get("lastSuccessful"), "count": len(retained), "status": "error", "error": str(error)[:240]})
        if delay and index < len(sources) - 1:
            time.sleep(delay)
    output = {"schemaVersion": 1, "generatedAt": now, "opportunities": [item.to_dict() for item in deduplicate(all_items)], "sources": health}
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output
