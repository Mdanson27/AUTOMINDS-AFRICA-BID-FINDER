from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, time
import re
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import httpx

from .base import BidSource
from ..models import NormalizedBid, SourceRef


KAMPALA = ZoneInfo("Africa/Kampala")
REFERENCE_RE = re.compile(r"(?P<ref>[A-Za-z0-9.&_-]+/[A-Za-z]+/\d{4}-\d{4}/\d+)")


class EGPUgandaSource(BidSource):
    name = "eGP Uganda"
    source_id = "egp-uganda"
    url = "https://egpuganda.go.ug/bid-notices"

    def fetch(self) -> str:
        response = httpx.get(
            self.url,
            timeout=45,
            follow_redirects=True,
            headers={
                "User-Agent": "AutoMindsBidFinder/1.0 (+public procurement indexing; Uganda)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        response.raise_for_status()
        return response.text

    def parse(self, raw: str) -> Iterable[NormalizedBid]:
        """Parse the two live procurement-table shapes currently exposed by eGP.

        eGP presently exposes both the main advertised-bid table and a second
        procurement/quotation table on the public BID Notices page. We identify
        them by semantic headers instead of brittle CSS classes so minor layout
        changes do not silently break collection.
        """
        soup = BeautifulSoup(raw, "html.parser")
        now = datetime.now(KAMPALA)
        discovered: list[NormalizedBid] = []

        for table in soup.find_all("table"):
            headers = [self._clean(cell.get_text(" ", strip=True)).lower() for cell in table.find_all("th")]
            if not headers:
                continue

            standard = self._is_standard_table(headers)
            quotation = self._is_quotation_table(headers)
            if not standard and not quotation:
                continue

            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue

                if standard and len(cells) >= 5:
                    bid = self._parse_standard_row(cells, now)
                elif quotation:
                    bid = self._parse_quotation_row(cells, now)
                else:
                    bid = None

                if bid is not None:
                    discovered.append(bid)

        # Defensive in-memory deduplication before the database layer. The
        # Firestore store repeats this guarantee with a stable canonical ID.
        unique: dict[str, NormalizedBid] = {}
        for bid in discovered:
            unique[bid.canonical_key()] = bid
        return list(unique.values())

    def _parse_standard_row(self, cells, now: datetime) -> NormalizedBid | None:
        entity_text = self._clean(cells[0].get_text(" ", strip=True))
        reference, organization = self._split_reference_and_organization(entity_text)
        procurement_type = self._clean(cells[1].get_text(" ", strip=True))
        title = self._best_cell_text(cells[2])
        published_text = self._clean(cells[3].get_text(" ", strip=True))
        deadline_text = self._clean(cells[4].get_text(" ", strip=True))
        return self._make_bid(
            cells=cells,
            now=now,
            reference=reference,
            organization=organization,
            procurement_type=procurement_type,
            title=title,
            published_at=self._parse_date(published_text, end_of_day=False),
            deadline_at=self._parse_date(deadline_text, end_of_day=True),
        )

    def _parse_quotation_row(self, cells, now: datetime) -> NormalizedBid | None:
        entity_text = self._clean(cells[0].get_text(" ", strip=True))
        reference, organization = self._split_reference_and_organization(entity_text)
        procurement_type = self._clean(cells[1].get_text(" ", strip=True))
        title = self._best_cell_text(cells[2])
        deadline_text = self._clean(cells[3].get_text(" ", strip=True))
        return self._make_bid(
            cells=cells,
            now=now,
            reference=reference,
            organization=organization,
            procurement_type=procurement_type,
            title=title,
            published_at=None,
            deadline_at=self._parse_date(deadline_text, end_of_day=True),
        )

    def _make_bid(
        self,
        *,
        cells,
        now: datetime,
        reference: str,
        organization: str,
        procurement_type: str,
        title: str,
        published_at: datetime | None,
        deadline_at: datetime | None,
    ) -> NormalizedBid | None:
        if not title or not organization:
            return None

        detail_link = cells[0].find("a", href=True)
        if detail_link is None:
            for cell in cells:
                detail_link = cell.find("a", href=True)
                if detail_link is not None:
                    break
        source_url = urljoin(self.url, detail_link["href"]) if detail_link else self.url
        status = "open" if deadline_at is None or deadline_at >= now else "closed"

        return NormalizedBid(
            title=title,
            organization=organization,
            reference_number=reference,
            description="",
            category=procurement_type,
            procurement_type=procurement_type,
            published_at=published_at,
            deadline_at=deadline_at,
            deadline_precision="date" if deadline_at else "unknown",
            status=status,
            sources=[SourceRef(name=self.name, url=source_url, detected_at=now)],
        )

    @staticmethod
    def _is_standard_table(headers: list[str]) -> bool:
        return (
            any("subject of procurement" in header for header in headers)
            and any("deadline" in header for header in headers)
            and any("procuring entity" in header for header in headers)
        )

    @staticmethod
    def _is_quotation_table(headers: list[str]) -> bool:
        return (
            any("bid details" in header for header in headers)
            and any("deadline" in header for header in headers)
            and any("procurement" in header and "entity" in header for header in headers)
        )

    @classmethod
    def _best_cell_text(cls, cell) -> str:
        # Prefer an explicit title/aria-label when the visible table text is
        # truncated with ellipses; otherwise use the full text node available.
        for node in cell.find_all(True):
            for attr in ("title", "aria-label", "data-original-title"):
                candidate = cls._clean(str(node.get(attr, "")))
                if candidate and len(candidate) > 8 and candidate.lower() not in {"view details", "send quotation"}:
                    return candidate
        return cls._clean(cell.get_text(" ", strip=True))

    @staticmethod
    def _clean(value: str) -> str:
        return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()

    @staticmethod
    def _split_reference_and_organization(value: str) -> tuple[str, str]:
        match = REFERENCE_RE.search(value)
        if not match:
            return "", value.strip()
        reference = match.group("ref").strip()
        organization = (value[: match.start()] + " " + value[match.end() :]).strip(" -–—:|")
        organization = re.sub(r"\s+", " ", organization).strip()
        return reference, organization

    @staticmethod
    def _parse_date(value: str, *, end_of_day: bool) -> datetime | None:
        if not value:
            return None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                parsed = datetime.strptime(value[:10], fmt).date()
                at = time(23, 59, 59) if end_of_day else time(0, 0, 0)
                return datetime.combine(parsed, at, tzinfo=KAMPALA)
            except ValueError:
                continue
        return None
