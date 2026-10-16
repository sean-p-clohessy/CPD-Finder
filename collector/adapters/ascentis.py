from urllib.parse import urljoin, urlparse
import time

from collector.adapters.base import Adapter, soup
from collector.models import Opportunity, clean, deduplicate
from collector.parsing import infer_delivery, infer_type, parse_date, parse_times


class AscentisAdapter(Adapter):
    provider = "Ascentis"

    def collect(self, html, source_url, session, _refreshed=False):
        listing = soup(html).select_one("#eventList")
        if listing is None:
            raise ValueError("Ascentis event listing not found")
        items = self.extract(html, source_url)
        current = int(listing.get("data-paged", 1))
        maximum = int(listing.get("data-max-pages", 1))
        endpoint = urljoin(source_url, listing.get("data-ajax-url", ""))
        if urlparse(endpoint).netloc != urlparse(source_url).netloc:
            raise ValueError("Unexpected Ascentis pagination host")
        while current < maximum:
            if maximum > 100:
                raise ValueError("Unexpected Ascentis page count")
            response = session.post(endpoint, data={
                "action": "load_more_events", "nonce": listing.get("data-nonce", ""),
                "paged": str(current + 1), "query": listing.get("data-query", "{}"),
            }, headers={"Referer": source_url}, timeout=(10, 25))
            # WordPress page caches can outlive the AJAX nonce. Refresh once;
            # never publish only the first page when pagination fails.
            if getattr(response, "status_code", None) == 403 and not _refreshed:
                fresh = session.get(source_url, params={"cpd_refresh": time.time_ns()}, timeout=(10, 25))
                fresh.raise_for_status()
                return self.collect(fresh.text, source_url, session, _refreshed=True)
            response.raise_for_status()
            payload = response.json()
            if not payload.get("success"):
                raise ValueError("Ascentis pagination failed")
            data = payload["data"]
            if int(data.get("paged", 0)) != current + 1:
                raise ValueError("Ascentis pagination did not advance")
            page_items = self.extract('<ul id="eventList">' + data.get("html", "") + '</ul>', source_url)
            if not page_items:
                raise ValueError("Ascentis returned an empty event page")
            items.extend(page_items)
            current += 1
            maximum = int(data.get("max_pages", maximum))
        return deduplicate(items)

    def extract(self, html, source_url):
        items = []
        for card in soup(html).select("#eventList > li"):
            title_node, date_node = card.find("p"), card.find("date")
            link = card.find("a", href=True)
            if not title_node or not date_node or not link:
                continue
            title = clean(title_node.get_text(" ", strip=True))
            start_date = parse_date(date_node.get_text(" ", strip=True))
            url = urljoin(source_url, link["href"])
            if not title or not start_date or urlparse(url).scheme not in ("https", "http"):
                continue
            category_node, time_node = card.find("span"), card.find("time")
            category = clean(category_node.get_text(" ", strip=True)) if category_node else ""
            start, end = parse_times(time_node.get_text(" ", strip=True) if time_node else "")
            delivery, location = infer_delivery(title + (" online" if urlparse(url).hostname == "events.teams.microsoft.com" else ""))
            tags = [label for needle, label in (("esol", "ESOL"), ("functional skills", "Functional Skills"), ("access to he", "Access to HE"), ("quality", "Quality assurance")) if needle in (title + " " + category).casefold()]
            items.append(Opportunity(
                title=title, provider=self.provider, url=url, sourceUrl=source_url,
                startDate=start_date, startTime=start, endTime=end,
                type=infer_type(title), description=category, tags=tags,
                delivery=delivery, location=location,
            ))
        return items
