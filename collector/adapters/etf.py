from collector.adapters.generic import GenericAdapter


class EtfAdapter(GenericAdapter):
    provider = "ETF"

    def extract(self, html, source_url):
        items = super().extract(html, source_url)
        for item in items:
            item.provider = self.provider
        return items
