from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import httpx

from .base import BidSource
from .common_web import KAMPALA, clean, extract_deadline, extract_reference, infer_type, organization_from_title, parse_date
from ..models import NormalizedBid, SourceRef


class DailyMonitorSource(BidSource):
    name = "Daily Monitor"
    source_id = "daily-monitor"
    url = "https://www.monitor.co.ug/uganda/jobs/tenders"

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
        discovered: dict[str, NormalizedBid] = {}

        for anchor in soup.find_all("a", href=True):
            href = urljoin(self.url, anchor.get("href", ""))
            if "/uganda/jobs/tenders/" not in href:
                continue
            if href.rstrip("/") == self.url.rstrip("/"):
                continue
            title = clean(anchor.get_text(" ", strip=True))
            if len(title) < 12:
                continue

            container = anchor.find_parent(["article", "li"])
            if container is None:
                container = anchor.find_parent("div")
            text = clean(container.get_text(" ", strip=True) if container else title)
            if len(text) < len(title):
                text = title

            deadline = extract_deadline(text)
            status = "open" if deadline is None or deadline >= now else "closed"
            time_node = (container.find("time") if container else None)
            published = None
            if time_node is not None:
                published = parse_date(str(time_node.get("datetime") or time_node.get_text(" ", strip=True)))

            procurement_type = infer_type(title, text)
            organization = organization_from_title(title)
            bid = NormalizedBid(
                title=title,
                organization=organization,
                reference_number=extract_reference(text),
                description=text[:1800],
                category=procurement_type,
                procurement_type=procurement_type,
                published_at=published,
                deadline_at=deadline,
                deadline_precision="datetime" if deadline else "unknown",
                status=status,
                sources=[SourceRef(name=self.name, url=href, detected_at=now)],
            )
            discovered[bid.canonical_key()] = bid

        return list(discovered.values())
