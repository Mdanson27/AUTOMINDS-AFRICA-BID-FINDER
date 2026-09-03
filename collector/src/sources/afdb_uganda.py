from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import httpx

from .base import BidSource
from .common_web import KAMPALA, clean, extract_deadline, extract_reference, infer_type, parse_date
from ..models import NormalizedBid, SourceRef


class AfDBUgandaSource(BidSource):
    name = "African Development Bank Uganda"
    source_id = "afdb-uganda"
    url = "https://www.afdb.org/en/documents/project-related-procurement/procurement-notices/invitation-for-bids?title=Uganda&tid=All&tid_1=All"

    def fetch(self) -> str:
        response = httpx.get(
            self.url,
            timeout=45,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; AutoMindsBidFinder/1.0; +https://automindsafrica.com)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        response.raise_for_status()
        return response.text

    def parse(self, raw: str) -> Iterable[NormalizedBid]:
        soup = BeautifulSoup(raw, "html.parser")
        now = datetime.now(KAMPALA)
        discovered: dict[str, NormalizedBid] = {}

        candidates: list[tuple[str, str, str]] = []
        for anchor in soup.find_all("a", href=True):
            title = clean(anchor.get_text(" ", strip=True))
            href = urljoin(self.url, anchor.get("href", ""))
            if "Uganda" not in title and "uganda" not in href.lower():
                continue
            if len(title) < 15 or "/documents/" not in href:
                continue
            parent = anchor.find_parent(["article", "li", "div"])
            text = clean(parent.get_text(" ", strip=True) if parent else title)
            candidates.append((title, href, text))

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; AutoMindsBidFinder/1.0; +https://automindsafrica.com)",
            "Accept": "text/html,application/xhtml+xml",
        }
        with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
            for title, href, listing_text in candidates[:20]:
                detail_text = listing_text
                published = None
                try:
                    response = client.get(href)
                    response.raise_for_status()
                    detail = BeautifulSoup(response.text, "html.parser")
                    detail_text = clean(detail.get_text(" ", strip=True))
                    date_node = detail.find("time")
                    if date_node:
                        published = parse_date(str(date_node.get("datetime") or date_node.get_text(" ", strip=True)))
                except Exception:
                    pass

                if published is None:
                    publication_match = re.search(r"Publication Date\s*:?\s*(\d{1,2}[- /][A-Za-z]{3,9}[- /]20\d{2}|[A-Za-z]{3,9}\s+\d{1,2},?\s+20\d{2})", detail_text, flags=re.I)
                    if publication_match:
                        published = parse_date(publication_match.group(1))
                    else:
                        date_match = re.search(r"\b(\d{1,2}[- /][A-Za-z]{3,9}[- /]20\d{2})\b", listing_text)
                        if date_match:
                            published = parse_date(date_match.group(1))

                deadline = extract_deadline(detail_text)
                status = "open" if deadline is None or deadline >= now else "closed"
                reference = extract_reference(detail_text)
                procurement_type = infer_type(title, detail_text)
                bid = NormalizedBid(
                    title=title,
                    organization="African Development Bank / Uganda project",
                    reference_number=reference,
                    description=detail_text[:1800],
                    category="Development finance procurement",
                    procurement_type=procurement_type,
                    published_at=published,
                    deadline_at=deadline,
                    deadline_precision="datetime" if deadline else "unknown",
                    status=status,
                    sources=[SourceRef(name=self.name, url=href, detected_at=now)],
                )
                discovered[bid.canonical_key()] = bid

        return list(discovered.values())
