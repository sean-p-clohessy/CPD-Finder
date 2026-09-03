from __future__ import annotations

import json
from urllib.parse import urljoin
from collector.adapters.base import Adapter, provider_from_url, soup
from collector.models import Opportunity, clean
from collector.parsing import infer_delivery, infer_type, parse_date


class GenericAdapter(Adapter):
    def extract(self, html: str, source_url: str) -> list[Opportunity]:
        page = soup(html)
        provider = provider_from_url(source_url)
        items: list[Opportunity] = []
        for script in page.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "null")
            except json.JSONDecodeError:
                continue
            nodes = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
            for node in nodes:
                if not isinstance(node, dict) or "Event" not in str(node.get("@type", "")):
                    continue
                location = node.get("location", {})
                location_name = location.get("name", "") if isinstance(location, dict) else ""
                mode, inferred_location = infer_delivery(f"{location_name} {node.get('eventAttendanceMode', '')}")
                items.append(Opportunity(title=clean(node.get("name")), provider=provider, type=infer_type(clean(node.get("name"))), description=clean(node.get("description")), startDate=parse_date(node.get("startDate")), endDate=parse_date(node.get("endDate")), delivery=mode, location=location_name or inferred_location, url=urljoin(source_url, node.get("url") or source_url), sourceUrl=source_url))
        if items:
            return [item for item in items if item.title]
        selectors = "article, .event, .event-card, .course-card, [class*='event-card'], [class*='event_item']"
        for card in page.select(selectors):
            heading = card.select_one("h2, h3, h4, a[title]")
            link = card.select_one("a[href]")
            text = clean(card.get_text(" ", strip=True))
            if not heading or not link or len(text) > 2500:
                continue
            title = clean(heading.get_text(" ", strip=True))
            date = parse_date(text)
            self_paced = not date and any(word in text.casefold() for word in ("self-paced", "on demand", "on-demand", "online course"))
            if not date and not self_paced:
                continue
            delivery, location = infer_delivery(text)
            items.append(Opportunity(title=title, provider=provider, type=infer_type(title, text), description=text.replace(title, "", 1), startDate=date, delivery=delivery, location=location, isSelfPaced=self_paced, url=urljoin(source_url, link["href"]), sourceUrl=source_url))
        return items
