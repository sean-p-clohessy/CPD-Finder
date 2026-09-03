from __future__ import annotations

import json
from urllib.parse import urljoin

from collector.adapters.base import Adapter, soup
from collector.models import Opportunity, clean, deduplicate
from collector.parsing import infer_type, parse_date, parse_times


class NcfeAdapter(Adapter):
    provider = "NCFE"

    def collect(self, html, source_url, session):
        page = soup(html)
        child_urls = {
            urljoin(source_url, link["href"])
            for link in page.select('a[href*="/events-webinars/"]')
            if urljoin(source_url, link["href"]).rstrip("/") != source_url.rstrip("/")
        }
        items = self.extract(html, source_url)
        for url in child_urls:
            response = session.get(url, timeout=(10, 25))
            response.raise_for_status()
            items.extend(self.extract(response.text, source_url))
        return deduplicate(items)

    def extract(self, html: str, source_url: str) -> list[Opportunity]:
        results = []
        for element in soup(html).select("[data-event-json]"):
            try:
                raw = json.loads(element["data-event-json"])
            except (json.JSONDecodeError, TypeError, KeyError):
                continue
            direct_url = clean(raw.get("eventRegisterUrl"))
            title = clean(raw.get("eventName"))
            year = clean(raw.get("eventYear"))
            if not direct_url or not title or not year:
                continue
            date_text = f"{clean(raw.get('eventDate'))} {year}"
            start, end = parse_times(clean(raw.get("eventTime")))
            delivery_text = f"{raw.get('eventTypes', '')} {raw.get('eventAdditionalDetails', '')}"
            delivery = "Online" if "online" in delivery_text.casefold() else "In person"
            tags = []
            for field in ("eventSectors", "eventQualification"):
                tags.extend(clean(value) for value in str(raw.get(field, "")).split("~") if clean(value))
            results.append(Opportunity(
                title=title, provider=self.provider,
                type=infer_type(title, delivery_text), description=clean(raw.get("eventDescription")),
                startDate=parse_date(date_text), startTime=start, endTime=end,
                delivery=delivery, location="" if delivery == "Online" else clean(raw.get("eventAdditionalDetails")),
                cost="Unknown", url=direct_url, sourceUrl=source_url, tags=tags,
            ))
        return results
