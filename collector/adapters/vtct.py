from __future__ import annotations

import re
from urllib.parse import urljoin

from collector.adapters.base import Adapter, soup
from collector.models import Opportunity, clean, deduplicate
from collector.parsing import infer_type, parse_date, parse_times


class VtctAdapter(Adapter):
    provider = "VTCT Skills"
    request_headers = {
        "User-Agent": "CPD-Finder/1.0 (+https://github.com/sean-p-clohessy/CPD-Finder; public events indexer)",
        "Accept": "text/html,application/xhtml+xml",
    }

    def collect(self, html: str, source_url: str, session) -> list[Opportunity]:
        listing_pages = [html]
        page = soup(html)
        # VTCT's query-string pagination is rejected by its web server for
        # automated clients, while the equivalent WordPress path is stable.
        page_numbers = {
            int(link["data-page"])
            for link in page.select(".pagination a[data-page]")
            if str(link.get("data-page", "")).isdigit()
        }
        pagination_urls = {urljoin(source_url, f"page/{number}/") for number in page_numbers}
        for url in sorted(pagination_urls):
            response = session.get(url, headers=self.request_headers, timeout=(10, 25))
            response.raise_for_status()
            listing_pages.append(response.text)

        event_urls = {
            urljoin(source_url, link["href"])
            for listing in listing_pages
            for link in soup(listing).select('a.blog-posts__post[href*="/event/"]')
        }
        results = []
        for url in sorted(event_urls):
            response = session.get(url, headers=self.request_headers, timeout=(10, 25))
            response.raise_for_status()
            item = self._extract_event(response.text, source_url, url)
            if item:
                results.append(item)
        return deduplicate(results)

    def extract(self, html: str, source_url: str) -> list[Opportunity]:
        """Listing pages need their child pages, so extraction is performed in collect."""
        return []

    def _extract_event(self, html: str, source_url: str, event_url: str) -> Opportunity | None:
        page = soup(html)
        heading = page.select_one("h1")
        if not heading:
            return None
        title = clean(heading.get_text(" ", strip=True))
        main = heading.find_parent("main") or page.select_one("main") or page.body or page
        text = clean(main.get_text(" | ", strip=True))
        metadata = page.select_one(".post-header__details")
        metadata_text = clean(metadata.get_text(" | ", strip=True) if metadata else text)
        start, end = parse_times(metadata_text)
        if not start:
            time_match = re.search(r"\b([01]?\d|2[0-3]):[0-5]\d\b", metadata_text)
            start = time_match.group(0).zfill(5) if time_match else None

        registration_scope = page.select_one(".post-container__content") or main
        registration = next((
            urljoin(event_url, link["href"])
            for link in registration_scope.select("a[href]")
            if re.search(r"\b(register|book|join)\b", clean(link.get_text(" ", strip=True)), re.I)
        ), event_url)
        detail_headings = page.select(".post-container__details .details--heading")
        detail_values = {
            clean(node.get_text(" ", strip=True)).casefold(): clean(node.find_next_sibling("p").get_text(" ", strip=True))
            for node in detail_headings if node.find_next_sibling("p")
        }
        location_text = detail_values.get("location", "")
        delivery = "Online" if any(word in f"{metadata_text} {location_text}".casefold() for word in ("online", "zoom", "teams")) else "In person"
        location = "" if delivery == "Online" else location_text

        description = detail_values.get("event details", "")
        if not description:
            details = page.select_one(".post-container__content p, .event-content, .single-event__content, article")
            description = clean(details.get_text(" ", strip=True) if details else text)
        tags = self._tags(title, text)
        is_free = True if "free" in text.casefold() else None
        return Opportunity(
            title=title,
            provider=self.provider,
            type=infer_type(title, text),
            description=description,
            startDate=parse_date(metadata_text),
            startTime=start,
            endTime=end,
            delivery=delivery,
            location=location,
            cost="Free" if is_free else "Unknown",
            isFree=is_free,
            url=registration,
            sourceUrl=source_url,
            tags=tags,
        )

    @staticmethod
    def _tags(title: str, text: str) -> list[str]:
        haystack = f"{title} {text}".casefold()
        topics = {
            "Hair & Beauty": ("hair", "beauty", "barber", "aesthetic"),
            "Qualification delivery": ("qualification", "delivery", "centre"),
            "Assessment": ("assessment", "exam", "nea"),
            "Networking": ("collective", "network"),
            "Early Years": ("early years",),
            "Logistics": ("logistics",),
        }
        return [label for label, words in topics.items() if any(word in haystack for word in words)]
