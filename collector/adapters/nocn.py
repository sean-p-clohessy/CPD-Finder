from __future__ import annotations

from urllib.parse import urljoin
from collector.adapters.base import Adapter, soup
from collector.models import Opportunity, clean
from collector.parsing import infer_type


class NocnAdapter(Adapter):
    provider = "NOCN"

    def extract(self, html: str, source_url: str) -> list[Opportunity]:
        page = soup(html)
        results: list[Opportunity] = []
        for card in page.select("article, .card, [class*='course']"):
            heading = card.select_one("h2, h3, h4")
            link = card.select_one("a[href]")
            if not heading or not link:
                continue
            title = clean(heading.get_text(" ", strip=True))
            text = clean(card.get_text(" ", strip=True))
            if len(title) < 4 or "course" not in f"{title} {text}".casefold():
                continue
            free = True if "free" in text.casefold() else None
            results.append(Opportunity(title=title, provider=self.provider, type=infer_type(title, text), description=text.replace(title, "", 1), delivery="Online", cost="Free" if free else "Unknown", isFree=free, isSelfPaced=True, url=urljoin(source_url, link["href"]), sourceUrl=source_url, tags=["Self-paced"]))
        return results
