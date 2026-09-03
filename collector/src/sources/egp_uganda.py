from collections.abc import Iterable
import httpx
from .base import BidSource
from ..models import NormalizedBid

class EGPUgandaSource(BidSource):
    name = "eGP Uganda"
    url = "https://egpuganda.go.ug/bid-notices"

    def fetch(self) -> str:
        response = httpx.get(self.url, timeout=30, follow_redirects=True, headers={"User-Agent": "AutoMindsBidFinder/0.1 (+public procurement indexing)"})
        response.raise_for_status()
        return response.text

    def parse(self, raw: str) -> Iterable[NormalizedBid]:
        # Intentionally left contract-first for the next Codex pass.
        # The source HTML/API should be inspected before selectors are finalized.
        return []
