from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, time
import re
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import httpx

from .base import BidSource
from ..models import NormalizedBid, SourceDocument, SourceRef


KAMPALA = ZoneInfo("Africa/Kampala")
REFERENCE_RE = re.compile(r"(?P<ref>[A-Za-z0-9.&_-]+/[A-Za-z]+/\d{4}-\d{4}/\d+)")


class EGPUgandaSource(BidSource):
    name = "eGP Uganda"
    source_id = "egp-uganda"
    url = "https://egpuganda.go.ug/bid-notices"

    def _fetch_url(self, url: str) -> str:
        response = httpx.get(
            url,
            timeout=45,
            follow_redirects=True,
            headers={
                "User-Agent": "AutoMindsBidFinder/1.0 (+public procurement indexing; Uganda)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        response.raise_for_status()
        return response.text

    def fetch(self) -> str:
        return self._fetch_url(self.url)

    def parse(self, raw: str) -> Iterable[NormalizedBid]:
        """Parse advertised bid notices and the public bid-opening table.

        eGP exposes more than one table shape on the Bid Notices page. Discovery
        stays table-based, while active opportunities are deep-enriched from
        their public detail pages later in enrich().
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

        unique: dict[str, NormalizedBid] = {}
        for bid in discovered:
            unique[bid.canonical_key()] = bid
        return list(unique.values())

    def enrich(self, bid: NormalizedBid) -> NormalizedBid:
        """Fetch the public eGP detail page and capture the full procurement record."""
        if not bid.sources:
            return bid
        detail_url = str(bid.sources[0].url)
        if not detail_url or detail_url.rstrip("/") == self.url.rstrip("/"):
            return bid
        try:
            raw = self._fetch_url(detail_url)
        except Exception:
            return bid
        return self.parse_detail(raw, bid, detail_url)

    def parse_detail(self, raw: str, bid: NormalizedBid, detail_url: str = "") -> NormalizedBid:
        """Merge a public eGP notice/opening-detail page into an existing bid."""
        soup = BeautifulSoup(raw, "html.parser")
        metadata: dict[str, str] = dict(bid.source_metadata)
        documents: list[SourceDocument] = list(bid.documents)

        notice_type = bid.notice_type
        heading = soup.find(["h1", "h2"])
        if heading:
            candidate = self._clean(heading.get_text(" ", strip=True))
            if candidate and candidate.lower() not in {"bid notices", "procurement notices"}:
                notice_type = candidate

        full_title = ""
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if not rows:
                continue

            header_cells = rows[0].find_all("th")
            headers = [self._clean(cell.get_text(" ", strip=True)) for cell in header_cells]
            normalized_headers = [header.lower() for header in headers]

            # Only treat an actual TH header row as a multi-column record.
            # eGP opening-detail pages also use two-column TD label/value rows,
            # where the first cell may itself say "Subject of Procurement".
            subject_index = next(
                (index for index, header in enumerate(normalized_headers) if "subject of procurement" in header),
                None,
            ) if headers else None
            if subject_index is not None:
                for row in rows[1:]:
                    cells = row.find_all("td")
                    if len(cells) > subject_index:
                        candidate = self._clean(cells[subject_index].get_text(" ", strip=True))
                        if candidate and len(candidate) > len(full_title):
                            full_title = candidate
                            break

            for row in rows:
                cells = row.find_all("td")
                if len(cells) == 2:
                    label = self._clean(cells[0].get_text(" ", strip=True)).rstrip(":")
                    value = self._clean(cells[1].get_text(" ", strip=True))
                    if label and value and len(label) <= 90:
                        metadata[label] = value

            if (
                any("name & address" in header or "name and address" in header for header in normalized_headers)
                and any("amount" in header for header in normalized_headers)
            ):
                for row_number, row in enumerate(rows[1:], start=1):
                    cells = row.find_all("td")
                    if len(cells) < 2:
                        continue
                    values = [self._clean(cell.get_text(" ", strip=True)) for cell in cells]
                    if not any(values):
                        continue
                    for index, value in enumerate(values):
                        if not value:
                            continue
                        label = headers[index] if index < len(headers) and headers[index] else f"Field {index + 1}"
                        metadata[f"Bid opening {row_number} · {label}"] = value

        if not full_title:
            for label, value in metadata.items():
                if "subject of procurement" in label.lower() and value:
                    full_title = value
                    break

        application_url = str(bid.application_url) if bid.application_url else ""
        seen_documents = {str(item.url) for item in documents}
        for anchor in soup.find_all("a", href=True):
            anchor_text = self._clean(anchor.get_text(" ", strip=True))
            href = urljoin(detail_url or self.url, anchor["href"])
            lower_text = anchor_text.lower()
            lower_href = href.lower()

            if not application_url and any(token in lower_text for token in ("apply", "send quotation", "submit bid")):
                application_url = href

            looks_like_document = (
                lower_href.endswith((".pdf", ".xls", ".xlsx", ".doc", ".docx", ".zip"))
                or any(token in lower_text for token in ("download pdf", "download excel", "bidding document", "tender document", "download document"))
            )
            if looks_like_document and href not in seen_documents:
                kind = "PDF" if ".pdf" in lower_href else "Document"
                documents.append(SourceDocument(title=anchor_text or "Procurement document", url=href, kind=kind))
                seen_documents.add(href)

        description_parts: list[str] = []
        seen_parts: set[str] = set()
        boilerplate = (
            "reason or description for complaint",
            "this email and any files transmitted",
            "this message contains confidential information",
            "please do not reply to this mail",
        )
        for node in soup.find_all(["p", "li"]):
            text = self._clean(node.get_text(" ", strip=True))
            lower = text.lower()
            if len(text) < 28 or any(token in lower for token in boilerplate):
                continue
            if text in seen_parts:
                continue
            seen_parts.add(text)
            description_parts.append(text)
            if sum(len(item) for item in description_parts) >= 3000:
                break

        description = self._clean(" ".join(description_parts))[:3200] or bid.description

        opening_at = bid.opening_at
        for label, value in metadata.items():
            if "date and time of bid opening" in label.lower() or "opening date" in label.lower():
                parsed = self._parse_datetime(value)
                if parsed:
                    opening_at = parsed
                    break

        procurement_type = bid.procurement_type
        for label, value in metadata.items():
            if "procurement method" in label.lower() and value:
                procurement_type = value
                break

        return bid.model_copy(
            update={
                "title": full_title or bid.title,
                "description": description,
                "procurement_type": procurement_type,
                "notice_type": notice_type,
                "opening_at": opening_at,
                "application_url": application_url or None,
                "source_metadata": metadata,
                "documents": documents,
            }
        )

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
            opening_at=None,
        )

    def _parse_quotation_row(self, cells, now: datetime) -> NormalizedBid | None:
        entity_text = self._clean(cells[0].get_text(" ", strip=True))
        reference, organization = self._split_reference_and_organization(entity_text)
        procurement_type = self._clean(cells[1].get_text(" ", strip=True))
        title = self._best_cell_text(cells[2])
        deadline_text = self._clean(cells[3].get_text(" ", strip=True))
        opening_text = self._clean(cells[4].get_text(" ", strip=True)) if len(cells) >= 5 else ""
        return self._make_bid(
            cells=cells,
            now=now,
            reference=reference,
            organization=organization,
            procurement_type=procurement_type,
            title=title,
            published_at=None,
            deadline_at=self._parse_date(deadline_text, end_of_day=True),
            opening_at=self._parse_datetime(opening_text),
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
        opening_at: datetime | None,
    ) -> NormalizedBid | None:
        if not title or not organization:
            return None

        detail_link = self._find_detail_link(cells)
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
            opening_at=opening_at,
            sources=[SourceRef(name=self.name, url=source_url, detected_at=now)],
        )

    @classmethod
    def _find_detail_link(cls, cells):
        anchors = []
        for cell in cells:
            anchors.extend(cell.find_all("a", href=True))
        for anchor in anchors:
            if "view detail" in cls._clean(anchor.get_text(" ", strip=True)).lower():
                return anchor
        for anchor in anchors:
            href = str(anchor.get("href", ""))
            if "/bid/notice/" in href or "/index/" in href:
                return anchor
        return anchors[0] if anchors else None

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

    @staticmethod
    def _parse_datetime(value: str) -> datetime | None:
        if not value:
            return None
        cleaned = re.sub(r"\s+", " ", value).strip()
        for fmt in (
            "%d %b %Y at %H:%M",
            "%d %B %Y at %H:%M",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
        ):
            try:
                parsed = datetime.strptime(cleaned, fmt)
                return parsed.replace(tzinfo=KAMPALA)
            except ValueError:
                continue
        match = re.search(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})\s+at\s+(\d{1,2}:\d{2})", cleaned)
        if match:
            for fmt in ("%d %b %Y %H:%M", "%d %B %Y %H:%M"):
                try:
                    return datetime.strptime(f"{match.group(1)} {match.group(2)}", fmt).replace(tzinfo=KAMPALA)
                except ValueError:
                    continue
        return None
