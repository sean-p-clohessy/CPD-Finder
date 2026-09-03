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
            if "fully booked" in title.casefold():
                continue
            start, end = parse_times(text)
            delivery, location = infer_delivery(text)
            description = re.split(r"(?:Date|Time|Location)\s*:", text)[-1]
            results.append(Opportunity(title=title, provider=self.provider, type=infer_type(title, text), description=description, startDate=parse_date(text), startTime=start, endTime=end, delivery=delivery, location=location, url=urljoin(source_url, link["href"]), sourceUrl=source_url, tags=self._tags(title, text)))
        return results

    @staticmethod
    def _tags(title: str, text: str) -> list[str]:
        haystack = f"{title} {text}".casefold()
        tags = ["Automotive"]
        topics = {
            "Leadership & teams": ("team", "leadership", "performance"),
            "Wellbeing": ("wellbeing", "resilience"),
            "Electric vehicles": ("electric vehicle", "ev safety", "hydrogen", "zero-emission"),
            "Vehicle technology": ("adas", "calibration", "brake", "emissions", "ncap", "euro 7"),
            "Networking": ("forum", "network"),
        }
        tags.extend(label for label, words in topics.items() if any(word in haystack for word in words))
        if "member" in haystack:
            tags.append("Members only")
        return tags
