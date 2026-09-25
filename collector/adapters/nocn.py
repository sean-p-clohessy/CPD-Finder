from __future__ import annotations

import re
from collector.adapters.base import Adapter, soup
from collector.models import Opportunity, clean


class NocnAdapter(Adapter):
    provider = "NOCN"

    def extract(self, html: str, source_url: str) -> list[Opportunity]:
        results = []
        for table in soup(html).select(".article table"):
            heading = table.select_one("tr:first-child strong")
            login = table.select_one('a[href="https://nocn.org/login"]')
            if not heading or not login:
                continue
            title = clean(heading.get_text(" ", strip=True))
            if not title:
                continue
            description = clean(" ".join(p.get_text(" ", strip=True) for p in table.select("p")))
            price = next((clean(td.get_text(" ", strip=True)) for td in table.select("td")
                          if re.fullmatch(r"£\s*\d+(?:\.\d{2})?|Free", clean(td.get_text(" ", strip=True)), re.I)), "Unknown")
            free = True if price.casefold() == "free" else False if price.startswith("£") else None
            results.append(Opportunity(title=title, provider=self.provider, type="Course", description=description,
                delivery="Online", cost=price, isFree=free, isSelfPaced=True,
                url=source_url, sourceUrl=source_url, linkType="catalogue", tags=["Self-paced", "Registration required"]))
        return results
