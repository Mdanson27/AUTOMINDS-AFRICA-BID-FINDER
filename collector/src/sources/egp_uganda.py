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
        soup = BeautifulSoup(raw, "html.parser")
        now = datetime.now(KAMPALA)
        discovered: list[NormalizedBid] = []

        for table in soup.find_all("table"):
            headers = [self._clean(cell.get_text(" ", strip=True)).lower() for cell in table.find_all("th")]
            if not headers:
                continue

            is_standard_bid_table = (
                any("subject of procurement" in header for header in headers)
                and any("deadline" in header for header in headers)
                and any("procuring entity" in header for header in headers)
            )
            if not is_standard_bid_table:
                continue

            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 5:
                    continue

                entity_text = self._clean(cells[0].get_text(" ", strip=True))
                reference, organization = self._split_reference_and_organization(entity_text)
                procurement_type = self._clean(cells[1].get_text(" ", strip=True))
                title = self._clean(cells[2].get_text(" ", strip=True))
                published_text = self._clean(cells[3].get_text(" ", strip=True))
                deadline_text = self._clean(cells[4].get_text(" ", strip=True))

                if not title or not organization:
                    continue

                published_at = self._parse_date(published_text, end_of_day=False)
                deadline_at = self._parse_date(deadline_text, end_of_day=True)
                detail_link = cells[0].find("a", href=True) or row.find("a", href=True)
                source_url = urljoin(self.url, detail_link["href"]) if detail_link else self.url
                status = "open" if deadline_at is None or deadline_at >= now else "closed"

                discovered.append(
                    NormalizedBid(
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
                        sources=[
                            SourceRef(
                                name=self.name,
                                url=source_url,
                                detected_at=now,
                            )
                        ],
                    )
                )

        return discovered

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
