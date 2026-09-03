import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from collector.adapters.generic import GenericAdapter
from collector.adapters.pearson import PearsonAdapter
from collector.models import Opportunity, deduplicate
from collector.parsing import parse_date, parse_times
from collector.pipeline import collect, read_sources


class Response:
    text = "<html><title>Changed site</title></html>"
    def raise_for_status(self): pass

class Session:
    @staticmethod
    def get(*args, **kwargs): return Response()

class JsonResponse:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): pass
    def json(self): return self.payload

class PearsonSession:
    @staticmethod
    def post(*args, **kwargs):
        return JsonResponse({"events":{"event-id":{"id":"event-id","status":"Active","type":"EVENT","title":"BTEC quality nominee briefing","startDate":"2026-09-15T16:00","endDate":"2026-09-15T17:00","location":"Online","description":"A live online webinar."}}})
    @staticmethod
    def get(*args, **kwargs):
        return JsonResponse([
            {"fieldName":"_calendarListView_registerButton__resx","fieldValue":"https://pearson.cventevents.com/d/example/4W"},
            {"fieldName":"Event Fee","fieldValue":"Free"},
        ])


class CollectorTests(unittest.TestCase):
    def test_sources_ignore_comments_and_blanks(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "sources.txt"
            path.write_text("# note\n\nhttps://example.com/a\n https://example.com/b \n", encoding="utf-8")
            self.assertEqual(read_sources(path), ["https://example.com/a", "https://example.com/b"])

    def test_date_and_time_parsing(self):
        self.assertEqual(parse_date("Date: Wednesday 09th September 2026"), "2026-09-09")
        self.assertEqual(parse_times("Time: 10:00 - 14:30"), ("10:00", "14:30"))

    def test_json_ld_normalisation(self):
        html = (Path(__file__).parent / "fixtures/generic_event.html").read_text(encoding="utf-8")
        item = GenericAdapter().extract(html, "https://example.org/events")[0]
        self.assertEqual(item.startDate, "2026-10-12")
        self.assertEqual(item.delivery, "Online")

    def test_pearson_resolves_direct_registration_url(self):
        html = (Path(__file__).parent / "fixtures/pearson_cvent.html").read_text(encoding="utf-8")
        item = PearsonAdapter().collect(html, "https://qualifications.pearson.com/btec", PearsonSession)[0]
        self.assertEqual(item.url, "https://pearson.cventevents.com/d/example/4W")
        self.assertEqual(item.startTime, "16:00")
        self.assertTrue(item.isFree)

    def test_deduplication_is_conservative(self):
        base = dict(title="Weekly webinar", provider="ETF", url="https://x.test/a", sourceUrl="https://x.test")
        items = deduplicate([Opportunity(**base, startDate="2026-09-01"), Opportunity(**base, startDate="2026-09-01"), Opportunity(**base, startDate="2026-09-08")])
        self.assertEqual(len(items), 2)

    def test_expiry_keeps_self_paced(self):
        self.assertTrue(Opportunity(title="Old", provider="P", url="https://x/a", sourceUrl="https://x", startDate="2025-01-01").expired(date(2026, 9, 3)))
        self.assertFalse(Opportunity(title="Anytime", provider="P", url="https://x/b", sourceUrl="https://x", startDate="2025-01-01", isSelfPaced=True).expired(date(2026, 9, 3)))

    def test_failure_retains_last_known_good(self):
        with TemporaryDirectory() as folder:
            root = Path(folder); source = root / "sources.txt"; output = root / "out.json"
            url = "https://example.com/events"; source.write_text(url, encoding="utf-8")
            previous = {"generatedAt":"2026-09-01T00:00:00Z","opportunities":[Opportunity(title="Still useful", provider="Example", url="https://example.com/a", sourceUrl=url, startDate="2026-10-01").to_dict()],"sources":[{"url":url,"provider":"Example","lastSuccessful":"2026-09-01T00:00:00Z"}]}
            output.write_text(json.dumps(previous), encoding="utf-8")
            result = collect(source, output, session=Session, today=date(2026, 9, 3), delay=0)
            self.assertEqual(len(result["opportunities"]), 1)
            self.assertEqual(result["sources"][0]["status"], "error")
            self.assertEqual(result["sources"][0]["lastSuccessful"], "2026-09-01T00:00:00Z")


if __name__ == "__main__": unittest.main()
