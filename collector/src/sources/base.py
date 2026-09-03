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
