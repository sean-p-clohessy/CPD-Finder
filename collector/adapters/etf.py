from __future__ import annotations

from datetime import datetime
from urllib.parse import urljoin

from collector.adapters.base import Adapter
from collector.models import Opportunity, clean


class EtfAdapter(Adapter):
    provider = "ETF"

    def extract(self, html, source_url):
        # ETF's cards are populated client-side; collect() uses the public JSON API.
        return []

    def collect(self, html, source_url, session):
        response = session.post(
            urljoin(source_url, "/Umbraco/Api/EventsApi/Events"),
            headers={"Content-Type": "application/json"},
            json={
                "searchText": "", "max": 0, "upcomingEvents": True, "previousEvents": False,
                "eventTypes": [], "eventVenues": [], "eventTags": [], "selectedDate": None,
                "page": 1, "pageSize": 250, "orderDirection": "Ascending",
                "orderColumn": "Date", "statuses": "",
            },
            timeout=(10, 25),
        )
        response.raise_for_status()
        results = []
        for raw in response.json().get("results", []):
            status = clean(raw.get("eventStatus"))
            if status.casefold() in {"cancelled", "closed", "fully booked"}:
                continue
            start = self._datetime(raw.get("startDate"))
            end = self._datetime(raw.get("endDate"))
            direct_url = clean(raw.get("externalUrl") or raw.get("eventUrl"))
            if not raw.get("name") or not start or not direct_url:
                continue
            venue = clean(raw.get("venue"))
            online = "online" in venue.casefold()
            tags = [clean(tag) for tag in raw.get("eventTags") or [] if clean(tag)]
            if any(tag.casefold() == "membership" for tag in tags):
                tags.append("Members only")
            price = clean(str(raw.get("fromPrice") or ""))
            results.append(Opportunity(
                title=clean(raw.get("name")), provider=self.provider,
                type=clean(raw.get("eventType")) or "Professional development",
                description=clean(raw.get("summary")), startDate=start.date().isoformat(),
                endDate=end.date().isoformat() if end else None,
                startTime=start.strftime("%H:%M"), endTime=end.strftime("%H:%M") if end else None,
                delivery="Online" if online else "In person", location="" if online else venue,
                cost=f"From £{price}" if price else "Unknown", isFree=True if price == "0" else None,
                url=urljoin(source_url, direct_url), sourceUrl=source_url, tags=tags,
            ))
        return results

    @staticmethod
    def _datetime(value):
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")) if value else None
        except ValueError:
            return None
