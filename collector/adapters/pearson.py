from __future__ import annotations

from datetime import datetime
import re
import time

from collector.adapters.base import soup
from collector.adapters.generic import GenericAdapter
from collector.models import Opportunity, clean
from collector.parsing import infer_type


class PearsonAdapter(GenericAdapter):
    provider = "Pearson"

    CONFIG = re.compile(
        r"calendarId:\s*['\"](?P<calendar>[0-9a-f-]+)['\"].*?authorization:\s*['\"](?P<token>[0-9a-f]+)['\"]",
        re.I | re.S,
    )
    AUTHORIZATION = re.compile(r"authorization:\s*['\"](?P<token>[0-9a-f]+)['\"]", re.I)

    def collect(self, html, source_url, session):
        """Collect Pearson's public Cvent calendar, including direct registration URLs."""
        config = self.CONFIG.search(html)
        if config:
            calendar, token = config.group("calendar"), config.group("token")
        else:
            container = soup(html).select_one("#calendar-widget-container[data-calendar-id][data-widget-id]")
            if not container:
                return self.extract(html, source_url)
            calendar = container["data-calendar-id"]
            widget = container["data-widget-id"]
            widget_url = f"https://www.cvent.com/c/calendar/{calendar}/webwidget/{widget}?showIcons=true&isPreview=false&showSpinner=false"
            widget_response = session.get(widget_url, timeout=(10, 25))
            widget_response.raise_for_status()
            authorization = self.AUTHORIZATION.search(widget_response.text)
            if not authorization:
                return []
            token = authorization.group("token")
        headers = {"Authorization": f"BEARER {token}", "Content-Type": "application/json"}
        base = f"https://www.cvent.com/api/calendar_events/v1/{calendar}"
        response = session.post(
            f"{base}/events?forMonth=false",
            headers=headers,
            json={"searchText": "", "fromDate": "", "toDate": "", "filters": []},
            timeout=(10, 25),
        )
        response.raise_for_status()
        events = response.json().get("events", {})
        results = []
        for raw in events.values():
            if raw.get("status") != "Active" or not raw.get("title"):
                continue
            detail_url = f"{base}/events/{raw['id']}?type={raw.get('type', 'EVENT')}"
            direct_url = ""
            cost = "Unknown"
            is_free = None
            try:
                detail = session.get(detail_url, headers=headers, timeout=(10, 25))
                detail.raise_for_status()
                fields = {field.get("fieldName"): field.get("fieldValue") for field in detail.json()}
                direct_url = fields.get("_calendarListView_registerButton__resx", "")
                fee = fields.get("Event Fee") or fields.get("Event Fee (GBP)")
                if fee:
                    cost = clean(str(fee))
                    is_free = cost.casefold() == "free"
                time.sleep(0.05)
            except Exception:
                # A genuine session without a resolved destination is not useful enough
                # to publish as a direct-link card; a later daily run can retry it.
                continue
            if not direct_url:
                continue
            start = self._datetime(raw.get("startDate"))
            end = self._datetime(raw.get("endDate"))
            description = clean(soup(raw.get("description", "")).get_text(" ", strip=True))
            location = clean(raw.get("location"))
            online = not location or "online" in location.casefold() or "online" in description.casefold()
            results.append(Opportunity(
                title=clean(raw.get("title")), provider=self.provider,
                type=infer_type(clean(raw.get("title")), description), description=description,
                startDate=start.date().isoformat() if start else None,
                endDate=end.date().isoformat() if end else None,
                startTime=start.strftime("%H:%M") if start else None,
                endTime=end.strftime("%H:%M") if end else None,
                delivery="Online" if online else "In person", location="" if online else location,
                cost="Free" if is_free else cost, isFree=is_free,
                url=direct_url, sourceUrl=source_url, tags=["BTEC"],
            ))
        return results

    @staticmethod
    def _datetime(value):
        try:
            return datetime.fromisoformat(value) if value else None
        except ValueError:
            return None

    def extract(self, html, source_url):
        items = super().extract(html, source_url)
        for item in items:
            item.provider = self.provider
        return items
