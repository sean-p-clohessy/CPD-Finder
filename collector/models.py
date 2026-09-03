from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
import hashlib
import re
from urllib.parse import urlsplit, urlunsplit


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def canonical_url(value: str) -> str:
    parts = urlsplit(value)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


@dataclass
class Opportunity:
    title: str
    provider: str
    url: str
    sourceUrl: str
    type: str = "Professional development"
    description: str = ""
    startDate: str | None = None
    endDate: str | None = None
    startTime: str | None = None
    endTime: str | None = None
    delivery: str = "Unknown"
    location: str = ""
    cost: str = "Unknown"
    isFree: bool | None = None
    isSelfPaced: bool = False
    tags: list[str] = field(default_factory=list)
    lastSeen: str = field(default_factory=utc_now)
    id: str = ""

    def normalise(self) -> "Opportunity":
        for name in ("title", "provider", "type", "description", "delivery", "location", "cost"):
            setattr(self, name, clean(getattr(self, name)))
        self.url = canonical_url(self.url)
        self.sourceUrl = canonical_url(self.sourceUrl)
        self.description = self.description[:280].rstrip()
        self.tags = sorted({clean(tag) for tag in self.tags if clean(tag)})
        identity = "|".join((self.provider.casefold(), self.title.casefold(), self.startDate or "anytime", self.url))
        self.id = "opp_" + hashlib.sha256(identity.encode()).hexdigest()[:16]
        return self

    def to_dict(self) -> dict:
        return asdict(self.normalise())

    def expired(self, today: date) -> bool:
        if self.isSelfPaced or not self.startDate:
            return False
        final = self.endDate or self.startDate
        try:
            return date.fromisoformat(final) < today
        except ValueError:
            return False


def deduplicate(items: list[Opportunity]) -> list[Opportunity]:
    seen: dict[tuple[str, str, str, str], Opportunity] = {}
    for item in items:
        item.normalise()
        key = (item.provider.casefold(), item.title.casefold(), item.startDate or "", item.url)
        seen.setdefault(key, item)
    return sorted(seen.values(), key=lambda item: (item.startDate is None, item.startDate or "", item.title.casefold()))
