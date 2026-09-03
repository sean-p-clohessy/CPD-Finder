from __future__ import annotations

from abc import ABC, abstractmethod
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from collector.models import Opportunity


class Adapter(ABC):
    provider = "Unknown"

    def collect(self, html: str, source_url: str, session) -> list[Opportunity]:
        return self.extract(html, source_url)

    @abstractmethod
    def extract(self, html: str, source_url: str) -> list[Opportunity]: ...


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def provider_from_url(url: str) -> str:
    host = urlparse(url).netloc.removeprefix("www.")
    return host.split(".")[0].replace("-", " ").title()
