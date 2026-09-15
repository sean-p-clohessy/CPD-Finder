from urllib.parse import urlparse
from collector.adapters.etf import EtfAdapter
from collector.adapters.generic import GenericAdapter
from collector.adapters.imi import ImiAdapter
from collector.adapters.ncfe import NcfeAdapter
from collector.adapters.nocn import NocnAdapter
from collector.adapters.pearson import PearsonAdapter
from collector.adapters.vtct import VtctAdapter


def adapter_for(url: str):
    host = urlparse(url).netloc.casefold()
    for needle, adapter in (("pearson", PearsonAdapter), ("ncfe", NcfeAdapter), ("etfoundation", EtfAdapter), ("theimi", ImiAdapter), ("nocn", NocnAdapter), ("vtctskills", VtctAdapter)):
        if needle in host:
            return adapter()
    return GenericAdapter()
