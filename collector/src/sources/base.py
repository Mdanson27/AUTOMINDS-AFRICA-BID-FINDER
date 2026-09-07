from abc import ABC, abstractmethod
from collections.abc import Iterable
from ..models import NormalizedBid


class BidSource(ABC):
    name: str

    @abstractmethod
    def fetch(self) -> str:
        """Fetch only publicly accessible source content."""
        raise NotImplementedError

    @abstractmethod
    def parse(self, raw: str) -> Iterable[NormalizedBid]:
        """Return normalized bid records from raw source content."""
        raise NotImplementedError

    def enrich(self, bid: NormalizedBid) -> NormalizedBid:
        """Optionally fetch a public detail page and enrich one normalized bid.

        Source adapters that only expose listing data can keep this default
        no-op implementation. Richer sources such as eGP override it.
        """
        return bid
