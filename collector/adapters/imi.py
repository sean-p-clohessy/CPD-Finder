from __future__ import annotations

import re
from urllib.parse import urljoin
from collector.adapters.base import Adapter, soup
from collector.models import Opportunity, clean
from collector.parsing import infer_delivery, infer_type, parse_date, parse_times


class ImiAdapter(Adapter):
    provider = "IMI"

    def extract(self, html: str, source_url: str) -> list[Opportunity]:
        page = soup(html)
        results: list[Opportunity] = []
        for heading in page.select("h3, h4"):
            link = heading.select_one("a[href]")
            if not link:
                continue
            container = heading.find_parent(["article", "li", "div"])
            text = clean(container.get_text(" | ", strip=True) if container else "")
            if "Date:" not in text:
                continue
            title = clean(link.get_text(" ", strip=True))
            start, end = parse_times(text)
            delivery, location = infer_delivery(text)
            description = re.split(r"(?:Date|Time|Location)\s*:", text)[-1]
            results.append(Opportunity(title=title, provider=self.provider, type=infer_type(title, text), description=description, startDate=parse_date(text), startTime=start, endTime=end, delivery=delivery, location=location, url=urljoin(source_url, link["href"]), sourceUrl=source_url))
        return results
