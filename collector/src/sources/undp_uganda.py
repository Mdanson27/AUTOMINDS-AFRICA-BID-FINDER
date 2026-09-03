from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import httpx

from .base import BidSource
from .common_web import KAMPALA, clean, infer_type, parse_date
from ..models import NormalizedBid, SourceRef


class UNDPUgandaSource(BidSource):
    name = "UNDP / UNCDF Uganda"
    source_id = "undp-uganda"
    url = "https://procurement-notices.undp.org/index.cfm"

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

        # The UNDP notice index is a public table/list. We identify Uganda rows
        # semantically so markup/class changes do not silently mix in other countries.
        for row in soup.find_all("tr"):
            text = clean(row.get_text(" ", strip=True))
            if "UGANDA" not in text.upper():
                continue
            cells = [clean(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"])]
            if len(cells) < 4:
                continue

            reference_match = re.search(r"\b(?:UNDP-UGA|UNCDF)[-A-Z0-9,./]+\b", text, flags=re.I)
            reference = clean(reference_match.group(0)) if reference_match else ""
            process = next((cell for cell in cells if re.search(r"\b(?:RFQ|RFP|ITB|IC|EOI)\b", cell, flags=re.I)), "")
            country_cell = next((cell for cell in cells if "UGANDA" in cell.upper()), "")

            anchor = row.find("a", href=True)
            title = clean(anchor.get_text(" ", strip=True)) if anchor else ""
            if len(title) < 10:
                candidates = [cell for cell in cells if len(cell) > 15 and cell not in {reference, process, country_cell}]
                title = candidates[0] if candidates else ""
            if len(title) < 10:
                continue

            deadline = None
            published = None
            for cell in cells:
                parsed = parse_date(cell) if re.search(r"\b\d{1,2}[- /][A-Za-z]{3,9}[- /]\d{2,4}|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", cell) else None
                if not parsed:
                    continue
                if "deadline" in text.lower() and deadline is None:
                    deadline = parsed
                elif published is None:
                    published = parsed
            # UNDP tables commonly place deadline before posted date. Pull those
            # labeled fragments directly when available.
            deadline_match = re.search(r"Deadline\s+(.+?)(?:Posted|$)", text, flags=re.I)
            if deadline_match:
                deadline = parse_date(deadline_match.group(1)) or deadline
            posted_match = re.search(r"Posted\s+(.+?)$", text, flags=re.I)
            if posted_match:
                published = parse_date(posted_match.group(1)) or published

            status = "open" if deadline is None or deadline >= now else "closed"
            href = urljoin(self.url, anchor.get("href", "")) if anchor else self.url
            procurement_type = process or infer_type(title, text)
            organization = "UNDP Uganda" if "UNDP-UGA" in reference.upper() else ("UNCDF Uganda" if "UNCDF" in reference.upper() else "UN Development Programme / Uganda")
            bid = NormalizedBid(
                title=title,
                organization=organization,
                reference_number=reference,
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

        # Some versions of the page render notices in div/list containers instead.
        if not discovered:
            for anchor in soup.find_all("a", href=True):
                parent = anchor.find_parent(["article", "li", "div"])
                text = clean(parent.get_text(" ", strip=True) if parent else anchor.get_text(" ", strip=True))
                if "UGANDA" not in text.upper() or not re.search(r"(?:UNDP-UGA|UNCDF)", text, flags=re.I):
                    continue
                title = clean(anchor.get_text(" ", strip=True))
                if len(title) < 10:
                    continue
                reference_match = re.search(r"\b(?:UNDP-UGA|UNCDF)[-A-Z0-9,./]+\b", text, flags=re.I)
                reference = clean(reference_match.group(0)) if reference_match else ""
                deadline_match = re.search(r"Deadline\s*:?\s*(.+?)(?:Posted|$)", text, flags=re.I)
                deadline = parse_date(deadline_match.group(1)) if deadline_match else None
                status = "open" if deadline is None or deadline >= now else "closed"
                href = urljoin(self.url, anchor.get("href", ""))
                procurement_type = infer_type(title, text)
                bid = NormalizedBid(
                    title=title,
                    organization="UNDP / UNCDF Uganda",
                    reference_number=reference,
                    description=text[:1800],
                    category=procurement_type,
                    procurement_type=procurement_type,
                    deadline_at=deadline,
                    deadline_precision="datetime" if deadline else "unknown",
                    status=status,
                    sources=[SourceRef(name=self.name, url=href, detected_at=now)],
                )
                discovered[bid.canonical_key()] = bid

        return list(discovered.values())
