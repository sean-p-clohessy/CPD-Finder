from __future__ import annotations

from datetime import datetime
from urllib.parse import urljoin

from collector.adapters.base import Adapter, soup
from collector.models import Opportunity, clean
from collector.parsing import infer_delivery, infer_type


class EtfAdapter(Adapter):
    provider = "ETF"

    def extract(self, html, source_url):
        # ETF's cards are populated client-side; collect() uses the public JSON API.
        return []

    def collect(self, html, source_url, session):
        library = "/learning-library" in source_url
        endpoint = "/Umbraco/Api/CoursesApi/Courses" if library else "/Umbraco/Api/EventsApi/Events"
        query = {
                "searchText": "", "max": 0, "upcomingEvents": True, "previousEvents": False,
                "eventTypes": [], "eventVenues": [], "eventTags": [], "selectedDate": None,
                "page": 1, "pageSize": 250, "orderDirection": "Ascending",
                "orderColumn": "Date", "statuses": "",
                "courseTypes": [], "courseTags": [],
        }
        records = []
        total = None
        for number in range(1, 101):
            query["page"] = number
            response = session.post(urljoin(source_url, endpoint), headers={"Content-Type": "application/json"}, json=dict(query), timeout=(10, 25))
            response.raise_for_status()
            payload = response.json()
            batch = payload.get("results")
            if not isinstance(batch, list):
                raise ValueError("ETF API returned no results array")
            if number > 1 and (not batch or batch == previous):
                raise ValueError("ETF pagination stopped advancing")
            records.extend(batch)
            previous = batch
            total = payload.get("total", total)
            if number >= int(payload.get("pages", 1)):
                break
        else:
            raise ValueError("ETF pagination exceeded safety limit")
        if total is not None and len(records) != int(total):
            raise ValueError(f"ETF coverage mismatch: received {len(records)} of {total} records")
        self.coverage = {"listed": len(records), "undatedExcluded": 0, "unavailableExcluded": 0, "invalidExcluded": 0}
        results = []
        for raw in records:
            status = clean(raw.get("eventStatus"))
            if status.casefold() in {"cancelled", "closed", "fully booked"}:
                self.coverage["unavailableExcluded"] += 1
                continue
            start = self._datetime(raw.get("startDate"))
            end = self._datetime(raw.get("endDate"))
            destination = raw.get("courseUrl") if library else raw.get("externalUrl") or raw.get("eventUrl")
            if isinstance(destination, dict):
                destination = destination.get("url")
            direct_url = clean(destination)
            self_paced = False
            detail_text = ""
            if library and start and start.year == 2040 and end and end.year == 1753 and direct_url:
                detail = session.get(urljoin(source_url, direct_url), timeout=(10, 25))
                detail.raise_for_status()
                page = soup(detail.text)
                main = page.find("main") or page
                detail_text = clean(main.get_text(" ", strip=True))
                self_paced = "on demand course" in detail_text.casefold() or "self-paced" in detail_text.casefold()
                if not self_paced:
                    self.coverage["undatedExcluded"] += 1
                    continue
                start = end = None
            # The library uses 1753 as a placeholder for undated programmes.
            # Do not turn these into self-paced courses or invent session dates.
            if not self_paced and (not start or start.year < 2000):
                self.coverage["undatedExcluded"] += 1
                continue
            if not raw.get("name") or not direct_url:
                self.coverage["invalidExcluded"] += 1
                continue
            venue = clean(raw.get("venue"))
            tags = [clean(tag) for tag in raw.get("courseTags" if library else "eventTags") or [] if clean(tag)]
            if any(tag.casefold() == "membership" for tag in tags):
                tags.append("Members only")
            price = clean(str(raw.get("fromPrice") if raw.get("fromPrice") is not None else ""))
            if self_paced and "free on demand course" in detail_text.casefold():
                price = "0"
            delivery, location = infer_delivery(f"{venue} {raw.get('name', '')} {raw.get('summary', '')}")
            if venue and delivery == "Unknown":
                delivery, location = "In person", venue
            if self_paced:
                delivery, location = "Online", ""
                tags.append("Self-paced")
            results.append(Opportunity(
                title=clean(raw.get("name")), provider=self.provider,
                type=clean(raw.get("eventType")) or infer_type(raw.get("name", ""), raw.get("summary") or ""),
                description=clean(raw.get("summary")), startDate=start.date().isoformat() if start else None,
                endDate=end.date().isoformat() if end else None,
                startTime=start.strftime("%H:%M") if start else None, endTime=end.strftime("%H:%M") if end else None,
                isSelfPaced=self_paced,
                delivery=delivery, location=location,
                cost=f"From £{price}" if price else "Unknown", isFree=True if price == "0" else None,
                url=urljoin(source_url, direct_url), sourceUrl=source_url, tags=tags,
            ))
        self.coverage["extracted"] = len(results)
        return results

    @staticmethod
    def _datetime(value):
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")) if value else None
        except ValueError:
            return None
