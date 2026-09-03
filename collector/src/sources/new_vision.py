from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import httpx

from .base import BidSource
from .common_web import KAMPALA, clean, extract_deadline, extract_reference, infer_type, organization_from_title, parse_date
from ..models import NormalizedBid, SourceRef


class NewVisionSource(BidSource):
    name = "New Vision"
    source_id = "new-vision"
    url = "https://www.newvision.co.ug/opportunities/tenders"

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
            if "/opportunities/tenders-" not in href:
                continue
            title = clean(anchor.get("title") or anchor.get_text(" ", strip=True))
            if len(title) < 10:
                continue

            container = anchor.find_parent(["article", "li"])
            if container is None:
                container = anchor.find_parent("div")
            text = clean(container.get_text(" ", strip=True) if container else title)
            deadline = extract_deadline(text)
            status = "open" if deadline is None or deadline >= now else "closed"
            published = None
            time_node = container.find("time") if container else None
            if time_node is not None:
                published = parse_date(str(time_node.get("datetime") or time_node.get_text(" ", strip=True)))

            procurement_type = infer_type(title, text)
            bid = NormalizedBid(
                title=title,
                organization=organization_from_title(title),
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
