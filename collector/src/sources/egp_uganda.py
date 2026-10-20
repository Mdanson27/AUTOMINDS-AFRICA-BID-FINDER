from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, time
import re
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import httpx

from .base import BidSource
from ..egp_lifecycle import collect_lifecycle_records
from ..models import (
    AmendmentRecord,
    BidderRecord,
    ContactPoint,
    LifecycleEvent,
    NormalizedBid,
    OpeningParticipant,
    SourceDocument,
    SourceRef,
)


KAMPALA = ZoneInfo("Africa/Kampala")
REFERENCE_RE = re.compile(r"(?P<ref>[A-Za-z0-9.&_-]+/[A-Za-z]+/\d{4}-\d{4}/\d+)")
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:\+?256|0)\s?\d{2,3}(?:[\s-]?\d{3}){2,3}")


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

    def collect_lifecycle_records(self) -> list[dict]:
        return collect_lifecycle_records(self._fetch_url)

    def parse(self, raw: str) -> Iterable[NormalizedBid]:
        """Parse advertised notices and eGP bid-opening rows from the public list."""
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
                bid = self._parse_standard_row(cells, now) if standard and len(cells) >= 5 else self._parse_quotation_row(cells, now) if quotation else None
                if bid is not None:
                    discovered.append(bid)

        unique: dict[str, NormalizedBid] = {}
        for bid in discovered:
            unique[bid.canonical_key()] = bid
        return list(unique.values())

    def enrich(self, bid: NormalizedBid) -> NormalizedBid:
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
        """Deeply extract a public eGP notice or bid-opening page.

        Missing facts remain missing: Phase 4 never guesses a fee, security,
        eligibility rule, contact, bidder, amount or lifecycle event.
        """
        soup = BeautifulSoup(raw, "html.parser")
        metadata: dict[str, str] = dict(bid.source_metadata)
        documents: list[SourceDocument] = list(bid.documents)
        bidders: list[BidderRecord] = list(bid.bidders)
        opening_participants: list[OpeningParticipant] = list(bid.opening_participants)
        amendments: list[AmendmentRecord] = list(bid.amendments)
        events: list[LifecycleEvent] = list(bid.lifecycle_events)

        notice_type = bid.notice_type
        for heading in soup.find_all(["h1", "h2", "h3"]):
            candidate = self._clean(heading.get_text(" ", strip=True))
            if candidate and candidate.lower() not in {"bid notices", "procurement notices", "particulars of procurement"}:
                notice_type = candidate
                break

        full_title = ""
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if not rows:
                continue
            header_cells = rows[0].find_all("th")
            headers = [self._clean(cell.get_text(" ", strip=True)) for cell in header_cells]
            normalized_headers = [self._norm(header) for header in headers]

            subject_index = next((i for i, h in enumerate(normalized_headers) if "subject of procurement" in h), None) if headers else None
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
                    if label and value and len(label) <= 110:
                        metadata[label] = value

            # Preserve a flattened source trail for compatibility while also
            # writing fully structured bidder records below.
            bidder_name_index = next((i for i, h in enumerate(normalized_headers) if "name" in h and "bidder" in h), None)
            amount_index = next((i for i, h in enumerate(normalized_headers) if "amount" in h or h == "price" or "prices" in h), None)
            submission_index = next((i for i, h in enumerate(normalized_headers) if "submission" in h and "date" in h), None)
            rank_index = next((i for i, h in enumerate(normalized_headers) if "rank" in h), None)
            status_index = next((i for i, h in enumerate(normalized_headers) if "status" in h), None)
            evaluation_index = next((i for i, h in enumerate(normalized_headers) if "evaluation stage" in h), None)
            reason_index = next((i for i, h in enumerate(normalized_headers) if "reason" in h), None)
            if bidder_name_index is not None:
                for row_number, row in enumerate(rows[1:], start=1):
                    cells = row.find_all("td")
                    if len(cells) <= bidder_name_index:
                        continue
                    values = [self._clean(cell.get_text(" ", strip=True)) for cell in cells]
                    raw_name = values[bidder_name_index]
                    name, address = self._split_name_address(raw_name)
                    if not name:
                        continue
                    amount = values[amount_index] if amount_index is not None and amount_index < len(values) else ""
                    submission_text = values[submission_index] if submission_index is not None and submission_index < len(values) else ""
                    reasons: list[str] = []
                    if reason_index is not None and reason_index < len(cells):
                        reasons = [self._clean(li.get_text(" ", strip=True)) for li in cells[reason_index].find_all("li") if self._clean(li.get_text(" ", strip=True))]
                        if not reasons and values[reason_index]:
                            reasons = [values[reason_index]]
                    bidder = BidderRecord(
                        name=name,
                        address=address,
                        submission_at=self._parse_datetime(submission_text),
                        amount=amount,
                        currency=self._currency(amount),
                        rank=values[rank_index] if rank_index is not None and rank_index < len(values) else "",
                        status=values[status_index] if status_index is not None and status_index < len(values) else "",
                        evaluation_stage=values[evaluation_index] if evaluation_index is not None and evaluation_index < len(values) else "",
                        reasons=reasons,
                    )
                    if not any(self._bidder_same(existing, bidder) for existing in bidders):
                        bidders.append(bidder)
                    for index, value in enumerate(values):
                        if value:
                            label = headers[index] if index < len(headers) and headers[index] else f"Field {index + 1}"
                            metadata[f"Bid opening {row_number} · {label}"] = value

            # Public opening attendance table.
            name_index = next((i for i, h in enumerate(normalized_headers) if h == "name"), None)
            department_index = next((i for i, h in enumerate(normalized_headers) if "department" in h or "company" in h), None)
            position_index = next((i for i, h in enumerate(normalized_headers) if "position" in h), None)
            address_index = next((i for i, h in enumerate(normalized_headers) if "address" in h), None)
            if name_index is not None and department_index is not None and bidder_name_index is None:
                for row in rows[1:]:
                    cells = row.find_all("td")
                    values = [self._clean(cell.get_text(" ", strip=True)) for cell in cells]
                    if len(values) <= name_index or not values[name_index]:
                        continue
                    participant = OpeningParticipant(
                        name=values[name_index],
                        address=values[address_index] if address_index is not None and address_index < len(values) else "",
                        position=values[position_index] if position_index is not None and position_index < len(values) else "",
                        department_company=values[department_index] if department_index < len(values) else "",
                    )
                    if not any(existing.name.lower() == participant.name.lower() and existing.department_company.lower() == participant.department_company.lower() for existing in opening_participants):
                        opening_participants.append(participant)

        if not full_title:
            full_title = self._metadata_value(metadata, "Subject of Procurement", "Procurement Subject", "Title of Procurement")

        application_url = str(bid.application_url) if bid.application_url else ""
        seen_documents = {str(item.url) for item in documents}
        seen_amendments = {(item.title.lower(), str(item.url or "")) for item in amendments}
        for anchor in soup.find_all("a", href=True):
            anchor_text = self._clean(anchor.get_text(" ", strip=True))
            href = urljoin(detail_url or self.url, str(anchor["href"]))
            lower_text = anchor_text.lower()
            lower_href = href.lower()
            if not application_url and any(token in lower_text for token in ("apply", "send quotation", "submit bid", "submit quotation")):
                application_url = href

            looks_like_document = lower_href.endswith((".pdf", ".xls", ".xlsx", ".doc", ".docx", ".zip", ".csv")) or any(token in lower_text for token in ("download pdf", "download excel", "bidding document", "tender document", "download document", "solicitation document"))
            if looks_like_document and href not in seen_documents:
                kind = self._document_kind(lower_href)
                documents.append(SourceDocument(title=anchor_text or "Procurement document", url=href, kind=kind))
                seen_documents.add(href)

            if any(token in f"{lower_text} {lower_href}" for token in ("addendum", "amendment", "clarification")):
                key = ((anchor_text or "Amendment / addendum").lower(), href)
                if key not in seen_amendments:
                    amendments.append(AmendmentRecord(title=anchor_text or "Amendment / addendum", url=href))
                    seen_amendments.add(key)

        description_parts = self._description_parts(soup)
        description = self._clean(" ".join(description_parts))[:5000] or bid.description
        all_text = self._clean(soup.get_text(" ", strip=True))

        reference = self._metadata_value(metadata, "Procurement Ref Number", "Procurement Reference Number") or bid.reference_number
        organization = self._metadata_value(metadata, "Procurement Entity", "Procuring Entity", "Procurement & Disposal Entity") or bid.organization
        procurement_method = self._metadata_value(metadata, "Procurement Method", "Method of Procurement") or bid.procurement_method
        category = self._metadata_value(metadata, "Category", "Procurement Category", "Type") or bid.category

        published_at = bid.published_at
        for label in ("Published", "Published on", "Publication Date", "Date of Publication"):
            parsed = self._parse_datetime(self._metadata_value(metadata, label))
            if parsed:
                published_at = parsed
                break

        deadline_at = bid.deadline_at
        deadline_precision = bid.deadline_precision
        for label, value in metadata.items():
            norm = self._norm(label)
            if any(token in norm for token in ("submission deadline", "bid submission deadline", "closing date", "deadline")):
                parsed = self._parse_datetime(value)
                if parsed:
                    deadline_at = parsed
                    deadline_precision = "datetime" if re.search(r"\d{1,2}:\d{2}", value) else "date"
                    break

        opening_at = bid.opening_at
        for label, value in metadata.items():
            norm = self._norm(label)
            if "date and time of bid opening" in norm or "opening date" in norm or "bid opening" == norm:
                parsed = self._parse_datetime(value)
                if parsed:
                    opening_at = parsed
                    break

        bids_received = bid.bids_received
        bids_received_text = self._metadata_value(metadata, "Bids received", "Number of Bids Received")
        if bids_received_text:
            match = re.search(r"\d+", bids_received_text)
            if match:
                bids_received = int(match.group(0))
        if bids_received is None and bidders:
            bids_received = len(bidders)

        bid_security = self._first_fact(metadata, ("bid security", "security declaration")) or self._extract_phrase(all_text, r"(?:bid security|security declaration)[^.;]{0,220}") or bid.bid_security
        tender_fee = self._first_fact(metadata, ("tender fee", "document fee", "bidding document fee", "non refundable fee", "non-refundable fee")) or self._extract_phrase(all_text, r"(?:non[- ]refundable[^.;]{0,80}fee|tender fee|bid document fee|bidding document fee)[^.;]{0,180}") or bid.tender_fee
        submission_method = self._first_fact(metadata, ("submission method", "method of submission", "bid submission")) or self._infer_submission_method(all_text) or bid.submission_method

        eligibility = self._extract_requirement_list(soup, ("eligibility", "eligible bidders", "eligible firms"), all_text, mode="eligibility") or list(bid.eligibility)
        mandatory_requirements = self._extract_requirement_list(soup, ("mandatory", "requirements", "documents required"), all_text, mode="mandatory") or list(bid.mandatory_requirements)
        contacts = self._extract_contacts(soup, metadata, list(bid.contacts))

        opening_committee = list(bid.opening_committee)
        for label in ("Members who have confirmed the opening", "Members who have Opened", "Opening Committee"):
            value = self._metadata_value(metadata, label)
            if value:
                for person in re.split(r"[,;|]", value):
                    person = self._clean(person)
                    if person and person not in opening_committee:
                        opening_committee.append(person)

        best_evaluated_bidder = self._metadata_value(metadata, "Name of Best Evaluated Bidder", "Best Evaluated Bidder") or bid.best_evaluated_bidder
        contract_amount = self._metadata_value(metadata, "Total Contract Price", "Contract Price", "Award Amount") or bid.contract_amount
        contract_currency = self._currency(contract_amount) or bid.contract_currency

        source_stage = bid.source_stage
        if best_evaluated_bidder:
            source_stage = "Evaluation / BEB"
        elif opening_at or bids_received is not None:
            source_stage = "Bid opening"
        elif not source_stage:
            source_stage = "Bidding / submission"

        status = bid.status
        if best_evaluated_bidder and status not in {"awarded", "cancelled"}:
            status = "evaluation"
        elif deadline_at and deadline_at < datetime.now(KAMPALA) and status not in {"awarded", "cancelled", "evaluation"}:
            status = "closed"

        if published_at:
            events = self._append_event(events, LifecycleEvent(stage="advertised", title="Procurement notice published", occurred_at=published_at, source_url=detail_url or None))
        if amendments:
            for amendment in amendments:
                events = self._append_event(events, LifecycleEvent(stage="updated", title=amendment.title or "Addendum / amendment published", occurred_at=amendment.published_at, source_url=amendment.url))
        if opening_at:
            events = self._append_event(events, LifecycleEvent(stage="bid-opening", title="Bid opening", occurred_at=opening_at, source_url=detail_url or None, details={"bidsReceived": str(bids_received or "")}))
        if status == "closed" and deadline_at:
            events = self._append_event(events, LifecycleEvent(stage="closed", title="Submission deadline passed", occurred_at=deadline_at, source_url=detail_url or None))
        if best_evaluated_bidder:
            events = self._append_event(events, LifecycleEvent(stage="evaluation", title="Best Evaluated Bidder identified", source_url=detail_url or None, details={"bestEvaluatedBidder": best_evaluated_bidder, "contractAmount": contract_amount}))

        return bid.model_copy(update={
            "title": full_title or bid.title,
            "organization": organization,
            "reference_number": reference,
            "description": description,
            "category": category,
            "procurement_method": procurement_method,
            "source_stage": source_stage,
            "published_at": published_at,
            "deadline_at": deadline_at,
            "deadline_precision": deadline_precision,
            "status": status,
            "notice_type": notice_type,
            "opening_at": opening_at,
            "application_url": application_url or None,
            "source_metadata": metadata,
            "documents": documents,
            "eligibility": eligibility,
            "mandatory_requirements": mandatory_requirements,
            "bid_security": bid_security,
            "tender_fee": tender_fee,
            "submission_method": submission_method,
            "contacts": contacts,
            "bidders": bidders,
            "bids_received": bids_received,
            "opening_participants": opening_participants,
            "opening_committee": opening_committee,
            "amendments": amendments,
            "lifecycle_events": events,
            "best_evaluated_bidder": best_evaluated_bidder,
            "contract_amount": contract_amount,
            "contract_currency": contract_currency,
        })

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

    def _make_bid(self, *, cells, now: datetime, reference: str, organization: str, procurement_type: str, title: str, published_at: datetime | None, deadline_at: datetime | None, opening_at: datetime | None) -> NormalizedBid | None:
        if not title or not organization:
            return None
        detail_link = self._find_detail_link(cells)
        source_url = urljoin(self.url, detail_link["href"]) if detail_link else self.url
        status = "open" if deadline_at is None or deadline_at >= now else "closed"
        events: list[LifecycleEvent] = []
        if published_at:
            events.append(LifecycleEvent(stage="advertised", title="Procurement notice published", occurred_at=published_at, source_url=source_url))
        if opening_at:
            events.append(LifecycleEvent(stage="bid-opening", title="Bid opening", occurred_at=opening_at, source_url=source_url))
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
            source_stage="Bid opening" if opening_at else "Bidding / submission",
            lifecycle_events=events,
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
        return any("subject of procurement" in header for header in headers) and any("deadline" in header for header in headers) and any("procuring entity" in header for header in headers)

    @staticmethod
    def _is_quotation_table(headers: list[str]) -> bool:
        return any("bid details" in header for header in headers) and any("deadline" in header for header in headers) and any("procurement" in header and "entity" in header for header in headers)

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
        return re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ")).strip()

    @classmethod
    def _norm(cls, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", cls._clean(value).lower()).strip()

    @classmethod
    def _metadata_value(cls, metadata: dict[str, str], *labels: str) -> str:
        wanted = {cls._norm(label) for label in labels}
        for key, value in metadata.items():
            if cls._norm(key) in wanted and cls._clean(value):
                return cls._clean(value)
        return ""

    @classmethod
    def _first_fact(cls, metadata: dict[str, str], tokens: tuple[str, ...]) -> str:
        for key, value in metadata.items():
            norm = cls._norm(key)
            if any(token in norm for token in tokens) and cls._clean(value):
                return cls._clean(value)
        return ""

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
    def _split_name_address(value: str) -> tuple[str, str]:
        text = re.sub(r"\s+", " ", value).strip()
        match = re.match(r"^(.*?)\s*\((.+)\)\s*$", text)
        return (match.group(1).strip(), match.group(2).strip()) if match else (text, "")

    @staticmethod
    def _currency(value: str) -> str:
        match = re.search(r"\b(UGX|USD|EUR|GBP|KES|TZS)\b", value.upper())
        return match.group(1) if match else ""

    @staticmethod
    def _document_kind(href: str) -> str:
        for suffix, kind in ((".pdf", "PDF"), (".xlsx", "Excel"), (".xls", "Excel"), (".docx", "Word"), (".doc", "Word"), (".zip", "Archive"), (".csv", "CSV")):
            if suffix in href:
                return kind
        return "Document"

    @classmethod
    def _description_parts(cls, soup: BeautifulSoup) -> list[str]:
        boilerplate = (
            "reason or description for complaint",
            "this email and any files transmitted",
            "this message contains confidential information",
            "please do not reply to this mail",
            "if you have received this email in error",
        )
        parts: list[str] = []
        seen: set[str] = set()
        for node in soup.find_all(["p", "li"]):
            text = cls._clean(node.get_text(" ", strip=True))
            lower = text.lower()
            if len(text) < 28 or any(token in lower for token in boilerplate) or text in seen:
                continue
            seen.add(text)
            parts.append(text)
            if sum(len(item) for item in parts) >= 4800:
                break
        return parts

    @classmethod
    def _extract_phrase(cls, text: str, pattern: str) -> str:
        match = re.search(pattern, text, flags=re.I)
        return cls._clean(match.group(0))[:260] if match else ""

    @classmethod
    def _infer_submission_method(cls, text: str) -> str:
        lower = text.lower()
        physical = any(token in lower for token in ("sealed bid", "sealed envelope", "hand delivered", "delivered to the address"))
        portal = any(token in lower for token in ("e-gp", "egp", "electronic procurement", "online submission", "click here to apply"))
        email = "email" in lower or "e-mail" in lower
        if physical and portal:
            return "Electronic portal or physical submission instructions published"
        if physical:
            return "Physical / sealed submission"
        if portal:
            return "Electronic eGP portal submission"
        if email:
            return "Electronic submission by email"
        return ""

    @classmethod
    def _extract_requirement_list(cls, soup: BeautifulSoup, heading_tokens: tuple[str, ...], text: str, *, mode: str) -> list[str]:
        output: list[str] = []
        for heading in soup.find_all(["h2", "h3", "h4", "strong", "b"]):
            heading_text = cls._norm(heading.get_text(" ", strip=True))
            if not any(token in heading_text for token in heading_tokens):
                continue
            parent = heading.parent
            if parent:
                for node in parent.find_all(["li", "p"], limit=16):
                    value = cls._clean(node.get_text(" ", strip=True))
                    if 12 <= len(value) <= 500 and value not in output:
                        output.append(value)
        lower = text.lower()
        patterns = (
            (("Eligible bidders", "eligible bidders"), ("Eligible firms", "eligible firms"), ("Registered in Uganda", "registered in uganda"), ("Joint venture / consortium", "joint venture"))
            if mode == "eligibility"
            else (("Tax clearance / compliance", "tax clearance"), ("Trading licence", "trading licence"), ("Certificate of incorporation / registration", "certificate of incorporation"), ("NSSF compliance", "nssf"), ("Audited financial statements", "audited financial"), ("Power of Attorney", "power of attorney"), ("Bid security", "bid security"), ("Manufacturer authorization", "manufacturer authorization"), ("Site visit / pre-bid participation", "site visit"))
        )
        for label, token in patterns:
            if token in lower and label not in output:
                output.append(label)
        return output[:20]

    @classmethod
    def _extract_contacts(cls, soup: BeautifulSoup, metadata: dict[str, str], existing: list[ContactPoint]) -> list[ContactPoint]:
        contacts = list(existing)
        seen = {(item.kind, item.value.lower()) for item in contacts}
        for key, value in metadata.items():
            norm = cls._norm(key)
            kind = "email" if "email" in norm else "phone" if "phone" in norm or "telephone" in norm or "tel" == norm else "address" if "address" in norm else "other"
            if kind != "other" and value:
                item = ContactPoint(label=key, value=cls._clean(value), kind=kind)
                marker = (item.kind, item.value.lower())
                if marker not in seen:
                    contacts.append(item)
                    seen.add(marker)
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href") or "")
            if href.lower().startswith("mailto:"):
                email = href.split(":", 1)[1].split("?", 1)[0].strip()
                marker = ("email", email.lower())
                if email and marker not in seen:
                    contacts.append(ContactPoint(label="Email", value=email, kind="email")); seen.add(marker)
        text = cls._clean(soup.get_text(" ", strip=True))
        for email in EMAIL_RE.findall(text):
            marker = ("email", email.lower())
            if marker not in seen:
                contacts.append(ContactPoint(label="Email", value=email, kind="email")); seen.add(marker)
        for phone in PHONE_RE.findall(text):
            value = cls._clean(phone)
            marker = ("phone", value.lower())
            if marker not in seen:
                contacts.append(ContactPoint(label="Phone", value=value, kind="phone")); seen.add(marker)
        return contacts[:20]

    @staticmethod
    def _bidder_same(left: BidderRecord, right: BidderRecord) -> bool:
        return left.name.lower() == right.name.lower() and left.amount == right.amount and left.submission_at == right.submission_at

    @staticmethod
    def _append_event(events: list[LifecycleEvent], event: LifecycleEvent) -> list[LifecycleEvent]:
        key = (event.stage, event.title.lower(), event.occurred_at.isoformat() if event.occurred_at else "", str(event.source_url or ""))
        for existing in events:
            existing_key = (existing.stage, existing.title.lower(), existing.occurred_at.isoformat() if existing.occurred_at else "", str(existing.source_url or ""))
            if key == existing_key:
                return events
        return [*events, event]

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
        cleaned = re.sub(r"\s+", " ", str(value)).strip()
        match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}-\d{1,2}-\d{1,2}|\d{1,2}\s+[A-Za-z]+\s+\d{4})(?:\s+(?:at\s+)?(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?))?", cleaned, flags=re.I)
        candidates = []
        if match:
            candidates.append(" ".join(part for part in match.groups() if part))
        candidates.append(cleaned)
        for candidate in candidates:
            for fmt in (
                "%d %b %Y %H:%M", "%d %B %Y %H:%M", "%d %b %Y %H:%M:%S", "%d %B %Y %H:%M:%S",
                "%d %b %Y %I:%M %p", "%d %B %Y %I:%M %p", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
                "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%d %B %Y",
            ):
                try:
                    return datetime.strptime(candidate, fmt).replace(tzinfo=KAMPALA)
                except ValueError:
                    continue
        return None
