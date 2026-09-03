from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import httpx

from .base import BidSource
from .common_web import KAMPALA, clean, extract_deadline, extract_reference, infer_type, parse_date
from ..models import NormalizedBid, SourceRef


class _HtmlSource(BidSource):
    organization = "Uganda public entity"

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

    def _bid(self, *, title: str, text: str, url: str, published=None, deadline=None, reference="") -> NormalizedBid:
        now = datetime.now(KAMPALA)
        deadline = deadline or extract_deadline(text)
        published = published or self._published_from_text(text)
        status = "open" if deadline is None or deadline >= now else "closed"
        if deadline is None and published and published < now - timedelta(days=150):
            status = "closed"
        procurement_type = infer_type(title, text)
        return NormalizedBid(
            title=clean(title),
            organization=self.organization,
            reference_number=reference or extract_reference(text),
            description=clean(text)[:1800],
            category=procurement_type,
            procurement_type=procurement_type,
            published_at=published,
            deadline_at=deadline,
            deadline_precision="datetime" if deadline else "unknown",
            status=status,
            sources=[SourceRef(name=self.name, url=url, detected_at=now)],
        )

    @staticmethod
    def _published_from_text(text: str):
        month = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
        for pattern in (
            rf"(?:published|posted|date)\D{{0,20}}?(\d{{1,2}}(?:st|nd|rd|th)?[ ,/-]+{month}[ ,/-]+20\d{{2}})",
            rf"\b(\d{{1,2}}(?:st|nd|rd|th)?[ ,/-]+{month}[ ,/-]+20\d{{2}})\b",
            rf"\b({month}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+20\d{{2}})\b",
        ):
            match = re.search(pattern, text, flags=re.I)
            if match:
                parsed = parse_date(match.group(1))
                if parsed:
                    return parsed
        return None


class NITAUgandaSource(_HtmlSource):
    name = "NITA-U"
    source_id = "nita-u"
    url = "https://www.nita.go.ug/Opportunities/bids-and-tenders"
    organization = "National Information Technology Authority - Uganda"

    def parse(self, raw: str) -> Iterable[NormalizedBid]:
        soup = BeautifulSoup(raw, "html.parser")
        blocks = []
        for node in soup.find_all(string=re.compile(r"Bid Expiry", re.I)):
            parent = node.parent
            for _ in range(5):
                if parent is None:
                    break
                text = clean(parent.get_text(" ", strip=True))
                if "Bid Expiry" in text and len(text) > 40:
                    blocks.append(parent)
                    break
                parent = parent.parent

        discovered: dict[str, NormalizedBid] = {}
        for block in blocks:
            text = clean(block.get_text(" ", strip=True))
            ref_match = re.search(r"\b(?:REF:\s*)?(NITA[- ]?U[^\s,;]{0,15}/[A-Z]+/[^\s,;]+)\b", text, flags=re.I)
            reference = clean(ref_match.group(1)) if ref_match else extract_reference(text)
            deadline_match = re.search(r"Bid Expiry\s*:?\s*([^|]{4,45}?20\d{2})", text, flags=re.I)
            deadline = parse_date(deadline_match.group(1)) if deadline_match else extract_deadline(text)
            title = ""
            for heading in block.find_all(["h2", "h3", "h4", "a"]):
                candidate = clean(heading.get_text(" ", strip=True))
                if len(candidate) > 18 and "download" not in candidate.lower() and candidate.lower() != reference.lower():
                    title = candidate
                    break
            if not title:
                title = re.sub(r"^.*?\b(?:NITA[- ]?U[^\s,;]+)\b", "", text, count=1, flags=re.I).split("Bid Expiry", 1)[0].strip(" -,:|")
            if len(title) < 12:
                continue
            link = next((urljoin(self.url, a.get("href")) for a in block.find_all("a", href=True) if a.get("href")), self.url)
            bid = self._bid(title=title, text=text, url=link, deadline=deadline, reference=reference)
            discovered[bid.canonical_key()] = bid
        return list(discovered.values())


class KCCASource(_HtmlSource):
    name = "KCCA"
    source_id = "kcca"
    url = "https://www.kcca.go.ug/tenders"
    organization = "Kampala Capital City Authority"

    def parse(self, raw: str) -> Iterable[NormalizedBid]:
        soup = BeautifulSoup(raw, "html.parser")
        discovered: dict[str, NormalizedBid] = {}
        main_heading = soup.find(["h1", "h2"], string=lambda value: bool(value and "Procurement" not in value and "Tender" not in value))
        if main_heading:
            container = main_heading.parent
            text = clean(container.get_text(" ", strip=True))
            title = clean(main_heading.get_text(" ", strip=True))
            if len(title) > 15 and ("bid" in text.lower() or "procurement" in text.lower() or "proposal" in text.lower()):
                reference = extract_reference(text)
                bid = self._bid(title=title, text=text, url=self.url, reference=reference)
                discovered[bid.canonical_key()] = bid

        marker = soup.find(string=re.compile(r"More Procurement Notices", re.I))
        area = marker.parent.parent if marker and marker.parent else soup
        for anchor in area.find_all("a", href=True):
            title = clean(anchor.get_text(" ", strip=True))
            href = urljoin(self.url, anchor.get("href", ""))
            if len(title) < 15 or title.lower() in {"download document", "tenders"}:
                continue
            if not any(word in title.lower() for word in ("bid", "procurement", "tender", "consult", "expression", "addendum", "proposal", "contract")):
                continue
            sibling_text = clean(" ".join(str(value) for value in anchor.parent.stripped_strings))
            published = self._published_from_text(sibling_text)
            bid = self._bid(title=title, text=sibling_text, url=href, published=published)
            discovered[bid.canonical_key()] = bid
        return list(discovered.values())


class UCCSource(_HtmlSource):
    name = "UCC"
    source_id = "ucc"
    url = "https://www.ucc.co.ug/download-category/bid-notices/"
    organization = "Uganda Communications Commission"

    def parse(self, raw: str) -> Iterable[NormalizedBid]:
        soup = BeautifulSoup(raw, "html.parser")
        discovered: dict[str, NormalizedBid] = {}
        for heading in soup.find_all(["h2", "h3"]):
            title = clean(heading.get_text(" ", strip=True))
            if len(title) < 12 or title.lower() in {"bid notices", "recent updates"}:
                continue
            container = heading.parent
            text = clean(container.get_text(" ", strip=True))
            link_node = heading.find("a", href=True) or container.find("a", href=True)
            href = urljoin(self.url, link_node.get("href")) if link_node else self.url
            published = self._published_from_text(text)
            bid = self._bid(title=title, text=text, url=href, published=published)
            discovered[bid.canonical_key()] = bid
        return list(discovered.values())


class URASource(_HtmlSource):
    name = "URA"
    source_id = "ura"
    url = "https://ura.go.ug/en/category/opportunities/procurement-announcements/"
    organization = "Uganda Revenue Authority"

    def parse(self, raw: str) -> Iterable[NormalizedBid]:
        soup = BeautifulSoup(raw, "html.parser")
        article_links: list[tuple[str, str, str]] = []
        seen = set()
        for anchor in soup.find_all("a", href=True):
            title = clean(anchor.get_text(" ", strip=True))
            href = urljoin(self.url, anchor.get("href", ""))
            lowered = title.lower()
            if len(title) < 12 or not any(word in lowered for word in ("bid notice", "tender", "addendum", "auction", "procurement")):
                continue
            if urlparse(href).netloc not in {"ura.go.ug", "www.ura.go.ug"} or href in seen:
                continue
            seen.add(href)
            text = clean(anchor.parent.get_text(" ", strip=True))
            article_links.append((title, href, text))
            if len(article_links) >= 16:
                break

        discovered: dict[str, NormalizedBid] = {}
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; AutoMindsBidFinder/1.0; +https://automindsafrica.com)",
            "Accept": "text/html,application/xhtml+xml",
        }
        with httpx.Client(timeout=35, follow_redirects=True, headers=headers) as client:
            for listing_title, href, listing_text in article_links:
                detail_soup = None
                detail_text = listing_text
                try:
                    response = client.get(href)
                    response.raise_for_status()
                    detail_soup = BeautifulSoup(response.text, "html.parser")
                    detail_text = clean(detail_soup.get_text(" ", strip=True))
                except Exception:
                    pass

                row_created = False
                if detail_soup:
                    for row in detail_soup.find_all("tr"):
                        cells = [clean(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"])]
                        joined = " | ".join(cells)
                        reference = extract_reference(joined)
                        if not reference or len(cells) < 2:
                            continue
                        title_candidates = [cell for cell in cells if cell != reference and len(cell) > 15 and not re.fullmatch(r"[\d,.]+", cell)]
                        title = max(title_candidates, key=len) if title_candidates else listing_title
                        bid = self._bid(title=title, text=joined, url=href, reference=reference)
                        discovered[bid.canonical_key()] = bid
                        row_created = True
                if not row_created:
                    bid = self._bid(title=listing_title, text=detail_text, url=href)
                    discovered[bid.canonical_key()] = bid
        return list(discovered.values())


class MoFPEDSource(_HtmlSource):
    name = "Ministry of Finance"
    source_id = "mofped"
    url = "https://www.finance.go.ug/media-center/procurement"
    organization = "Ministry of Finance, Planning and Economic Development"

    def parse(self, raw: str) -> Iterable[NormalizedBid]:
        soup = BeautifulSoup(raw, "html.parser")
        discovered: dict[str, NormalizedBid] = {}
        for anchor in soup.find_all("a", href=True):
            title = clean(anchor.get_text(" ", strip=True))
            if len(title) < 18 or title.lower() == "read more":
                continue
            lowered = title.lower()
            if not any(word in lowered for word in ("consult", "tender", "bid", "procurement", "addendum", "supply", "provision")):
                continue
            href = urljoin(self.url, anchor.get("href", ""))
            parent = anchor.parent
            text = clean(parent.get_text(" ", strip=True))
            published = self._published_from_text(text)
            bid = self._bid(title=title, text=text, url=href, published=published)
            discovered[bid.canonical_key()] = bid
        return list(discovered.values())
